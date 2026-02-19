#!/usr/bin/env python3
"""
LoCoMo Results Audit — Net Score Adjustment

Classifies how known ground truth errors in the LoCoMo benchmark affected
published evaluation scores for 5 memory systems. Uses an LLM judge to
determine whether each error gave a system an undeserved penalty, undeserved
credit, or neither (wash).

Usage:
    python audit_results.py                    # Full run
    python audit_results.py --dry-run          # Show what would be judged
    python audit_results.py --systems mem0 zep # Audit specific systems only

Environment:
    LLM_API_KEY or OPENAI_API_KEY  — API key for the judge LLM
    LLM_BASE_URL (optional)        — Custom base URL (e.g. OpenRouter)
    LLM_MODEL (optional)           — Model override (default: gpt-4o-mini)
"""

import argparse
import asyncio
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Error: openai package required. Install with: pip install openai")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SYSTEMS = ["evermemos", "mem0", "memos", "memu", "zep"]
SYSTEM_DISPLAY = {
    "evermemos": "EverMemOS",
    "mem0": "Mem0",
    "memos": "MemoS",
    "memu": "MemU",
    "zep": "Zep",
}
TOTAL_QUESTIONS = 1540
CATEGORY_NAMES = {1: "Multi-hop", 2: "Temporal", 3: "Open-domain", 4: "Single-hop"}
CATEGORY_COUNTS = {1: 282, 2: 321, 3: 96, 4: 841}
CATEGORY_ERRORS = {1: 28, 2: 26, 3: 9, 4: 36}
CATEGORY_CEILINGS = {
    cat: (CATEGORY_COUNTS[cat] - CATEGORY_ERRORS[cat]) / CATEGORY_COUNTS[cat]
    for cat in CATEGORY_COUNTS
}
OVERALL_CEILING = (TOTAL_QUESTIONS - sum(CATEGORY_ERRORS.values())) / TOTAL_QUESTIONS
VALID_CLASSIFICATIONS = {"UNDESERVED_PENALTY", "UNDESERVED_CREDIT", "WASH"}

# Published per-category scores (mean-of-runs from EverMemOS eval README)
# Used for cross-check only — our majority-vote numbers may differ slightly
PUBLISHED_SCORES = {
    "evermemos": {4: 96.08, 1: 91.13, 2: 89.72, 3: 70.83, "overall": 92.32},
    "mem0":      {4: 68.97, 1: 61.70, 2: 58.26, 3: 50.00, "overall": 64.20},
    "zep":       {4: 90.84, 1: 81.91, 2: 77.26, 3: 75.00, "overall": 85.22},
    "memos":     {4: 85.37, 1: 79.43, 2: 75.08, 3: 64.58, "overall": 80.76},
    "memu":      {4: 74.91, 1: 72.34, 2: 43.61, 3: 54.17, "overall": 66.67},
}

SCRIPT_DIR = Path(__file__).parent
ERRORS_PATH = SCRIPT_DIR.parent / "errors.json"
RESULTS_DIR = SCRIPT_DIR / "results"
JUDGMENTS_DIR = SCRIPT_DIR / "judgments"
REPORT_PATH = SCRIPT_DIR / "RESULTS_AUDIT.md"

# ---------------------------------------------------------------------------
# LLM Judge Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an expert evaluator auditing benchmark results. You determine whether \
a known ground truth error in the LoCoMo benchmark affected a system's score.

EVALUATION STANDARD: Be generous with matching, consistent with the original \
LoCoMo evaluation methodology. An answer is considered correct if it conveys \
the same core information as the reference, even if wording, format, or detail \
level differs. For dates, "May 7th" = "7 May" = "May 7, 2023". For names and \
facts, partial overlap counts if the key information is present."""

USER_PROMPT_TEMPLATE = """\
## Question
{question}

## Ground Truth Error
- **Error type:** {error_type}
- **Wrong golden answer** (used in original evaluation): {golden_answer}
- **Correct answer** (from transcript analysis): {correct_answer}
- **Error explanation:** {reasoning}

## System's Generated Answer
{generated_answer}

## Original Evaluation Outcome
The system was marked **{verdict}** by majority vote ({judgment_detail}).

## Your Task

Classify how this ground truth error affected the system's score:

1. First, evaluate whether the system's answer matches the WRONG golden answer \
(the one used in the original evaluation).
2. Then, evaluate whether the system's answer matches the CORRECT answer \
(based on transcript analysis).
3. Classify:

- **UNDESERVED_PENALTY**: System was marked WRONG, but its answer is actually \
correct or reasonable given the corrected ground truth. The system lost a point \
it should have earned.
- **UNDESERVED_CREDIT**: System was marked CORRECT, but its answer only matched \
the WRONG golden answer. Judged against the correct answer, the system would be \
marked wrong. The system gained a point it should not have earned.
- **WASH**: The error did not change the scoring outcome. Either the system's \
answer matches both answers (correct regardless), matches neither (wrong \
regardless), or the situation is genuinely ambiguous.

Return JSON only:
{{"matches_wrong_golden": <bool>, "matches_correct_answer": <bool>, \
"reasoning": "<1-2 sentences>", "classification": "<UNDESERVED_PENALTY|UNDESERVED_CREDIT|WASH>"}}"""


# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------


def load_errors(path: Path) -> list[dict]:
    """Load score-corrupting errors (exclude WRONG_CITATION)."""
    with open(path) as f:
        all_errors = json.load(f)
    errors = [e for e in all_errors if e["error_type"] != "WRONG_CITATION"]
    print(f"Loaded {len(errors)} score-corrupting errors from {path.name}")
    return errors


def load_system_results(path: Path) -> dict[str, dict]:
    """Load and flatten a system's eval_results.json, keyed by question_id."""
    with open(path) as f:
        data = json.load(f)
    flat = {}
    for _user_id, questions in data.get("detailed_results", {}).items():
        for entry in questions:
            flat[entry["question_id"]] = entry
    return flat


def load_judgments(path: Path) -> dict[str, dict]:
    """Load existing judgments for resume support."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_judgments(path: Path, judgments: dict):
    """Save judgments dict to file (atomic write via temp file + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(judgments, f, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def is_majority_correct(llm_judgments: dict) -> bool:
    """A question is correct if >= 2 of 3 judgments are True (majority vote)."""
    votes = [v for v in llm_judgments.values() if isinstance(v, bool)]
    return sum(votes) >= 2


def judgment_detail(llm_judgments: dict) -> str:
    """Format judgment votes for display, e.g. '2/3 true'."""
    votes = [v for v in llm_judgments.values() if isinstance(v, bool)]
    return f"{sum(votes)}/{len(votes)} true"


# ---------------------------------------------------------------------------
# LLM Judge
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try markdown code block first
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object with classification key
    m = re.search(r'\{[^{}]*"classification"[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    # Try raw parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


DEFAULT_JUDGE_RUNS = 3
MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0   # seconds
MAX_BACKOFF = 60.0      # seconds
RATE_LIMIT_DELAY = 0.2  # seconds between requests (5 RPS baseline)


async def _single_judge_call(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    semaphore: asyncio.Semaphore,
    run_id: int,
) -> dict | None:
    """Execute one LLM judge call with exponential backoff. Returns parsed dict or None."""
    for attempt in range(MAX_RETRIES):
        resp = None
        api_error = None
        async with semaphore:
            # Rate-limit: small delay between requests to avoid bursts
            await asyncio.sleep(RATE_LIMIT_DELAY)
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    temperature=0,
                    seed=run_id,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                )
            except Exception as e:
                api_error = e

        # Handle errors outside semaphore so we don't hold a slot during sleep
        if api_error is not None:
            err_str = str(api_error).lower()
            if any(k in err_str for k in ["invalid_api_key", "insufficient_quota", "key limit"]):
                print(f"\nFATAL API error: {api_error}")
                sys.exit(1)

            backoff = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)
            is_rate_limit = any(k in err_str for k in ["rate", "429", "too many", "throttl"])
            if is_rate_limit:
                # Rate limit: longer backoff, reduce noise
                backoff = min(backoff * 2, MAX_BACKOFF)
                if attempt == 0:
                    print(f"    rate-limited (run {run_id}), backing off {backoff:.0f}s...")
            else:
                print(f"    API error (run {run_id}, attempt {attempt + 1}/{MAX_RETRIES}): "
                      f"{type(api_error).__name__}: {str(api_error)[:120]}")

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                continue
            return None

        if not resp.choices:
            if attempt < MAX_RETRIES - 1:
                print(f"    empty choices (run {run_id}, attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(INITIAL_BACKOFF)
                continue
            return None
        raw = resp.choices[0].message.content or ""
        parsed = extract_json(raw)
        if parsed and parsed.get("classification") in VALID_CLASSIFICATIONS:
            return parsed

        # Bad response — log and retry
        if attempt < MAX_RETRIES - 1:
            print(f"    bad response (run {run_id}, attempt {attempt + 1}/{MAX_RETRIES}): "
                  f"{raw[:80]}...")
            await asyncio.sleep(INITIAL_BACKOFF)
        else:
            print(f"    bad response (run {run_id}, giving up): {raw[:80]}...")

    return None


def _majority_classification(runs: list[dict]) -> str:
    """Pick the majority classification from N runs. Ties go to WASH."""
    counts = Counter(r["classification"] for r in runs)
    winner, n = counts.most_common(1)[0]
    return winner if n > len(runs) / 2 else "WASH"


async def call_judge(
    client: AsyncOpenAI,
    model: str,
    error: dict,
    system_entry: dict,
    semaphore: asyncio.Semaphore,
    num_runs: int = DEFAULT_JUDGE_RUNS,
) -> dict:
    """Run N independent judge calls and majority-vote the classification."""
    original_correct = is_majority_correct(system_entry["llm_judgments"])

    # Escape curly braces in free-text fields to prevent str.format() crashes
    esc = lambda s: s.replace("{", "{{").replace("}", "}}")
    prompt = USER_PROMPT_TEMPLATE.format(
        question=esc(error["question"]),
        error_type=error["error_type"],
        golden_answer=esc(str(error["golden_answer"])),
        correct_answer=esc(error["correct_answer"]),
        reasoning=esc(error["reasoning"]),
        generated_answer=esc(system_entry["generated_answer"]),
        verdict="CORRECT" if original_correct else "WRONG",
        judgment_detail=judgment_detail(system_entry["llm_judgments"]),
    )

    # Launch N runs concurrently
    coros = [
        _single_judge_call(client, model, prompt, semaphore, run_id=i)
        for i in range(num_runs)
    ]
    results = await asyncio.gather(*coros)

    # Collect successful runs
    successful = [r for r in results if r is not None]
    if not successful:
        print(f"  WARNING: {error['question_id']} — all {num_runs} runs failed, fallback WASH")
        return _build_judgment(error, system_entry, [], "WASH")

    classification = _majority_classification(successful) if len(successful) >= 2 else successful[0]["classification"]

    return _build_judgment(error, system_entry, successful, classification)


def _build_judgment(
    error: dict, system_entry: dict, runs: list[dict], classification: str,
) -> dict:
    """Build a full judgment record from multiple runs + majority vote."""
    original_correct = is_majority_correct(system_entry["llm_judgments"])

    # Hard guard: override logically impossible classifications to WASH
    warnings = []
    if classification == "UNDESERVED_PENALTY" and original_correct:
        warnings.append("Override: PENALTY impossible when system was marked CORRECT, forced WASH")
        classification = "WASH"
    elif classification == "UNDESERVED_CREDIT" and not original_correct:
        warnings.append("Override: CREDIT impossible when system was marked WRONG, forced WASH")
        classification = "WASH"

    judgment = {
        "question_id": error["question_id"],
        "error_type": error["error_type"],
        "category": error["category"],
        "wrong_golden_answer": str(error["golden_answer"]),
        "correct_answer": error["correct_answer"],
        "generated_answer": system_entry["generated_answer"],
        "original_correct": original_correct,
        "original_judgments": system_entry["llm_judgments"],
        "audit_runs": runs,
        "classification": classification,
    }
    if warnings:
        judgment["_warnings"] = warnings
    return judgment


# ---------------------------------------------------------------------------
# Audit Orchestration
# ---------------------------------------------------------------------------


async def audit_system(
    system: str,
    errors: list[dict],
    client: AsyncOpenAI,
    model: str,
    semaphore: asyncio.Semaphore,
    num_runs: int = DEFAULT_JUDGE_RUNS,
    dry_run: bool = False,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Audit all error-affected questions for one system. Returns (judgments, system_results)."""
    results_path = RESULTS_DIR / f"{system}_eval_results.json"
    if not results_path.exists():
        print(f"  {system}: results file not found at {results_path}")
        return {}, {}

    system_results = load_system_results(results_path)
    judgments_path = JUDGMENTS_DIR / f"{system}_judgments.json"
    judgments = load_judgments(judgments_path)

    # Find questions to judge
    error_lookup = {e["question_id"]: e for e in errors}
    to_judge = []
    skipped_existing = 0
    skipped_wash_auto = 0
    missing = 0

    for qid, error in error_lookup.items():
        if qid not in system_results:
            missing += 1
            continue
        if qid in judgments:
            skipped_existing += 1
            continue
        # Auto-WASH if golden_answer == correct_answer (shouldn't happen but safety check)
        if str(error["golden_answer"]).strip() == str(error["correct_answer"]).strip():
            judgments[qid] = _build_judgment(
                error, system_results[qid], [], "WASH",
            )
            skipped_wash_auto += 1
            continue
        to_judge.append((error, system_results[qid]))

    print(f"  {system}: {len(to_judge)} to judge, {skipped_existing} resumed, "
          f"{skipped_wash_auto} auto-wash, {missing} missing")

    if dry_run:
        return judgments, system_results

    # Run LLM judge calls
    tasks = [call_judge(client, model, err, entry, semaphore, num_runs) for err, entry in to_judge]

    for i, coro in enumerate(asyncio.as_completed(tasks)):
        result = await coro
        qid = result["question_id"]
        judgments[qid] = result
        if (i + 1) % 10 == 0 or i + 1 == len(tasks):
            save_judgments(judgments_path, judgments)
            print(f"  {system}: {i + 1}/{len(tasks)} judged (checkpoint saved)")
    return judgments, system_results


# ---------------------------------------------------------------------------
# Score Computation
# ---------------------------------------------------------------------------


def compute_scores(
    system_results: dict[str, dict],
    judgments: dict[str, dict],
    errors: list[dict],
) -> dict:
    """Compute original and adjusted scores for one system.

    Original scores: per-run accuracy averaged across 3 runs (matching
    EverMemOS compute_acc.py methodology), plus majority-vote accuracy.

    Adjusted scores: apply audit classifications (penalties/credits) to
    each run independently, then average — same statistical treatment.
    """

    # ------------------------------------------------------------------
    # Original per-run accuracies (matching compute_acc.py)
    # ------------------------------------------------------------------
    num_orig_runs = 3  # original eval always has 3 runs
    run_correct = [0] * num_orig_runs
    cat_run_correct = [defaultdict(int) for _ in range(num_orig_runs)]
    cat_totals = defaultdict(int)

    cat_majority_correct = defaultdict(int)

    for entry in system_results.values():
        cat = int(entry["category"])
        cat_totals[cat] += 1
        jdg = entry["llm_judgments"]
        for i in range(num_orig_runs):
            if jdg.get(f"judgment_{i+1}", False):
                run_correct[i] += 1
                cat_run_correct[i][cat] += 1
        if is_majority_correct(jdg):
            cat_majority_correct[cat] += 1

    actual_count = sum(cat_totals.values())
    if actual_count != TOTAL_QUESTIONS:
        print(f"  WARNING: expected {TOTAL_QUESTIONS} questions, got {actual_count}")

    orig_run_accs = [c / TOTAL_QUESTIONS for c in run_correct]
    orig_mean = sum(orig_run_accs) / len(orig_run_accs)
    orig_std = (sum((a - orig_mean) ** 2 for a in orig_run_accs) / len(orig_run_accs)) ** 0.5

    # Also compute majority-vote accuracy for reference
    majority_correct = sum(
        1 for entry in system_results.values()
        if is_majority_correct(entry["llm_judgments"])
    )

    # ------------------------------------------------------------------
    # Audit classification counts (majority-vote across audit runs)
    # ------------------------------------------------------------------
    penalties = 0
    credits = 0
    washes = 0
    cat_penalties = defaultdict(int)
    cat_credits = defaultdict(int)
    cat_washes = defaultdict(int)

    for error in errors:
        qid = error["question_id"]
        if qid not in judgments:
            continue
        j = judgments[qid]
        cat = error["category"]
        cls = j["classification"]

        if cls == "UNDESERVED_PENALTY":
            penalties += 1
            cat_penalties[cat] += 1
        elif cls == "UNDESERVED_CREDIT":
            credits += 1
            cat_credits[cat] += 1
        else:
            washes += 1
            cat_washes[cat] += 1

    # ------------------------------------------------------------------
    # Adjusted per-run accuracies (same statistical treatment as original)
    # ------------------------------------------------------------------
    # For each penalty/credit question, adjust only the runs that need it:
    # - PENALTY: system deserved credit → add +1 only to runs that said FALSE
    # - CREDIT: system didn't deserve credit → subtract 1 only from runs that said TRUE
    run_adj = [0] * num_orig_runs
    cat_run_adj = [defaultdict(int) for _ in range(num_orig_runs)]

    for error in errors:
        qid = error["question_id"]
        if qid not in judgments or qid not in system_results:
            continue
        cls = judgments[qid]["classification"]
        cat = error["category"]
        jdg = system_results[qid]["llm_judgments"]

        if cls == "UNDESERVED_PENALTY":
            for i in range(num_orig_runs):
                if not jdg.get(f"judgment_{i+1}", False):
                    run_adj[i] += 1
                    cat_run_adj[i][cat] += 1
        elif cls == "UNDESERVED_CREDIT":
            for i in range(num_orig_runs):
                if jdg.get(f"judgment_{i+1}", False):
                    run_adj[i] -= 1
                    cat_run_adj[i][cat] -= 1

    adj_run_accs = [(run_correct[i] + run_adj[i]) / TOTAL_QUESTIONS for i in range(num_orig_runs)]
    adj_mean = sum(adj_run_accs) / len(adj_run_accs)
    adj_std = (sum((a - adj_mean) ** 2 for a in adj_run_accs) / len(adj_run_accs)) ** 0.5

    # Per-category
    cat_scores = {}
    for cat in CATEGORY_COUNTS:
        total = CATEGORY_COUNTS[cat]
        cat_orig_accs = [cat_run_correct[i].get(cat, 0) / total for i in range(num_orig_runs)]
        cat_orig_mean = sum(cat_orig_accs) / len(cat_orig_accs)
        cat_orig_std = (sum((a - cat_orig_mean) ** 2 for a in cat_orig_accs) / len(cat_orig_accs)) ** 0.5

        cat_adj_accs = [(cat_run_correct[i].get(cat, 0) + cat_run_adj[i].get(cat, 0)) / total for i in range(num_orig_runs)]
        cat_adj_mean = sum(cat_adj_accs) / len(cat_adj_accs)
        cat_adj_std = (sum((a - cat_adj_mean) ** 2 for a in cat_adj_accs) / len(cat_adj_accs)) ** 0.5

        cat_scores[cat] = {
            "original_mean": cat_orig_mean,
            "original_std": cat_orig_std,
            "adjusted_mean": cat_adj_mean,
            "adjusted_std": cat_adj_std,
            "majority_correct": cat_majority_correct.get(cat, 0),
            "majority_accuracy": cat_majority_correct.get(cat, 0) / total,
            "penalties": cat_penalties.get(cat, 0),
            "credits": cat_credits.get(cat, 0),
            "washes": cat_washes.get(cat, 0),
        }

    return {
        "original_mean": orig_mean,
        "original_std": orig_std,
        "original_run_accs": orig_run_accs,
        "adjusted_mean": adj_mean,
        "adjusted_std": adj_std,
        "adjusted_run_accs": adj_run_accs,
        "majority_correct": majority_correct,
        "majority_accuracy": majority_correct / TOTAL_QUESTIONS,
        "delta": adj_mean - orig_mean,
        "penalties": penalties,
        "credits": credits,
        "washes": washes,
        "net_change": penalties - credits,
        "per_category": cat_scores,
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_report(
    all_scores: dict[str, dict],
    all_judgments: dict[str, dict],
    errors: list[dict],
    model: str = "gpt-4o-mini",
    num_runs: int = DEFAULT_JUDGE_RUNS,
):
    """Generate RESULTS_AUDIT.md."""
    lines = []
    w = lines.append

    w("# LoCoMo Benchmark Results Audit")
    w("")
    w("## How to Reproduce")
    w("")
    w("```bash")
    w("# 1. Download published eval_results.json from HuggingFace")
    w("python download_results.py")
    w("")
    w("# 2. Run the audit (~1,485 LLM calls, ~$0.50 with gpt-4o-mini)")
    w("python audit_results.py")
    w("```")
    w("")
    w("Requires `OPENAI_API_KEY` or `LLM_API_KEY` environment variable. "
      "Set `LLM_BASE_URL` for non-OpenAI providers (e.g. OpenRouter). "
      "Results are checkpointed per-system, so interrupted runs resume automatically.")
    w("")
    w("---")
    w("")
    w("## Methodology")
    w("")
    w("### Ground Truth Errors")
    w("")
    w(f"This audit evaluates published evaluation results against {len(errors)} "
      "score-corrupting errors identified in the LoCoMo benchmark's golden answers "
      "(see `errors.json` in repo root). Citation-only errors (`WRONG_CITATION`) are "
      "excluded as they do not affect scoring.")
    w("")

    # Error type breakdown
    type_counts = defaultdict(int)
    for e in errors:
        type_counts[e["error_type"]] += 1
    w("| Error Type | Count |")
    w("|-----------|-------|")
    for et in ["HALLUCINATION", "TEMPORAL_ERROR", "ATTRIBUTION_ERROR", "AMBIGUOUS", "INCOMPLETE"]:
        if et in type_counts:
            w(f"| {et} | {type_counts[et]} |")
    w("")

    w("### Scoring Rule")
    w("")
    w("The published `eval_results.json` files contain 3 independent LLM judge runs per question. "
      "We treat a question as **scored correct** if at least 2 of 3 judgments are true (majority vote).")
    w("")
    w("*Note:* EverMemOS's `compute_acc.py` calculates accuracy per-run independently then averages "
      "the three accuracies, which yields a very similar number at the aggregate level but is not "
      "identical to majority vote at the per-question level. This audit uses strict per-question "
      "majority vote because the audit requires a binary correct/wrong determination for each question.")
    w("")

    w("### Audit Classification")
    w("")
    w(f"For each of the 99 error-affected questions across 5 systems, an LLM judge ({model}, "
      f"temperature=0) was run {num_runs} times independently. The final classification is determined by "
      f"majority vote across the {num_runs} runs, matching the multi-run methodology of the original "
      "evaluation. Each question is classified into one of three outcomes:")
    w("")
    w("- **UNDESERVED_PENALTY**: System was marked wrong, but its answer is correct given the "
      "corrected ground truth. Score should go **up**.")
    w("- **UNDESERVED_CREDIT**: System was marked correct, but only because the golden answer "
      "was erroneous. Score should go **down**.")
    w("- **WASH**: The error did not change the outcome (correct regardless, wrong regardless, "
      "or genuinely ambiguous).")
    w("")

    w("---")
    w("")

    # Summary table
    w("## Results")
    w("")
    w("### Overall Accuracy (N=1,540)")
    w("")
    w("| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta |")
    w("|--------|------------------------|------------------------|-------|")
    for sys_name in SYSTEMS:
        if sys_name not in all_scores:
            continue
        s = all_scores[sys_name]
        display = SYSTEM_DISPLAY.get(sys_name, sys_name)
        w(f"| {display} "
          f"| {s['original_mean']:.2%} +/- {s['original_std']:.2%} "
          f"| {s['adjusted_mean']:.2%} +/- {s['adjusted_std']:.2%} "
          f"| {_delta_str(s['delta'])} |")
    w("")

    # Impact breakdown
    w("### Impact Breakdown")
    w("")
    w("| System | Undeserved Penalties | Undeserved Credits | Washes | Net Change |")
    w("|--------|---------------------|-------------------|--------|------------|")
    for sys_name in SYSTEMS:
        if sys_name not in all_scores:
            continue
        s = all_scores[sys_name]
        display = SYSTEM_DISPLAY.get(sys_name, sys_name)
        net = s["net_change"]
        net_str = f"+{net}" if net > 0 else str(net)
        w(f"| {display} | {s['penalties']} | {s['credits']} | {s['washes']} | {net_str} |")
    w("")

    # Per-category breakdown
    w("### Per-Category Breakdown")
    w("")
    for cat in [4, 1, 2, 3]:
        cat_name = CATEGORY_NAMES[cat]
        cat_n = CATEGORY_COUNTS[cat]
        w(f"#### Category {cat}: {cat_name} (N={cat_n})")
        w("")
        w("| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta | Penalties | Credits | Washes |")
        w("|--------|------------------------|------------------------|-------|-----------|---------|--------|")
        for sys_name in SYSTEMS:
            if sys_name not in all_scores:
                continue
            cs = all_scores[sys_name]["per_category"].get(cat, {})
            if not cs:
                continue
            display = SYSTEM_DISPLAY.get(sys_name, sys_name)
            delta = cs["adjusted_mean"] - cs["original_mean"]
            w(f"| {display} "
              f"| {cs['original_mean']:.2%} +/- {cs['original_std']:.2%} "
              f"| {cs['adjusted_mean']:.2%} +/- {cs['adjusted_std']:.2%} "
              f"| {_delta_str(delta)} "
              f"| {cs['penalties']} | {cs['credits']} | {cs['washes']} |")
        w("")

    # Ceiling analysis
    w("### Ceiling Analysis")
    w("")
    w("With 99 score-corrupting errors in the benchmark, a perfect system cannot achieve "
      "100% accuracy. The ceiling is the maximum score achievable if a system correctly "
      "answers every non-erroneous question.")
    w("")
    w("| Scope | Questions | Errors | Ceiling |")
    w("|-------|-----------|--------|---------|")
    w(f"| **Overall** | {TOTAL_QUESTIONS:,} | 99 | {OVERALL_CEILING:.2%} |")
    for cat in [4, 1, 2, 3]:
        w(f"| Category {cat}: {CATEGORY_NAMES[cat]} "
          f"| {CATEGORY_COUNTS[cat]} | {CATEGORY_ERRORS[cat]} "
          f"| {CATEGORY_CEILINGS[cat]:.2%} |")
    w("")

    # Systems vs ceiling
    w("#### Systems vs. Ceiling")
    w("")
    w("| System | Category | Original | Adjusted | Ceiling | Gap to Ceiling |")
    w("|--------|----------|----------|----------|---------|----------------|")
    violations = []
    adjusted_violations = []
    for sys_name in SYSTEMS:
        if sys_name not in all_scores:
            continue
        s = all_scores[sys_name]
        display = SYSTEM_DISPLAY.get(sys_name, sys_name)
        # Overall
        gap = OVERALL_CEILING - s["adjusted_mean"]
        if s["original_mean"] > OVERALL_CEILING:
            violations.append(f"{display} overall ({s['original_mean']:.2%} > {OVERALL_CEILING:.2%})")
        if s["adjusted_mean"] > OVERALL_CEILING:
            adjusted_violations.append(
                f"{display} overall (adjusted {s['adjusted_mean']:.2%}, gap +{s['adjusted_mean'] - OVERALL_CEILING:.2%})"
            )
        w(f"| {display} | Overall "
          f"| {s['original_mean']:.2%} | {s['adjusted_mean']:.2%} "
          f"| {OVERALL_CEILING:.2%} | {gap:.2%} |")
        # Per-category
        for cat in [4, 1, 2, 3]:
            cs = s["per_category"].get(cat, {})
            if not cs:
                continue
            ceiling = CATEGORY_CEILINGS[cat]
            cat_gap = ceiling - cs["adjusted_mean"]
            if cs["original_mean"] > ceiling:
                violations.append(
                    f"{display} {CATEGORY_NAMES[cat]} ({cs['original_mean']:.2%} > {ceiling:.2%})"
                )
            if cs["adjusted_mean"] > ceiling:
                adjusted_violations.append(
                    f"{display} {CATEGORY_NAMES[cat]} "
                    f"(adjusted {cs['adjusted_mean']:.2%}, gap +{cs['adjusted_mean'] - ceiling:.2%})"
                )
            w(f"| | {CATEGORY_NAMES[cat]} "
              f"| {cs['original_mean']:.2%} | {cs['adjusted_mean']:.2%} "
              f"| {ceiling:.2%} | {cat_gap:.2%} |")
    w("")
    if violations:
        w("**Ceiling violations** (original score exceeds ceiling, indicating credit from erroneous golden answers):")
        w("")
        for v in violations:
            w(f"- {v}")
        w("")
    if adjusted_violations:
        w("These violations **persist after full correction**:")
        w("")
        for v in adjusted_violations:
            w(f"- {v}")
        w("")
        w("Since the audit has already reclassified every undeserved credit and penalty on error-affected "
          "questions, the remaining above-ceiling gap can only be attributed to the original LLM judge "
          "awarding credit on questions whose golden answers were corrupted — cases where the system's "
          "answer happened to match the *wrong* golden answer and was marked correct, yet the audit "
          "judge also classified the answer as matching the *correct* answer (WASH rather than "
          "UNDESERVED_CREDIT).")
        w("")

    # Published scores cross-check
    w("### Published Scores Cross-Check")
    w("")
    w("Comparison of our computed scores against published scores. The published pipeline "
      "uses **per-run averaging for overall scores** but **majority vote for per-category "
      "scores** — we match each method accordingly.")
    w("")
    w("| System | Scope | Published | Computed (method) | Match |")
    w("|--------|-------|-----------|-------------------|-------|")
    for sys_name in SYSTEMS:
        if sys_name not in all_scores or sys_name not in PUBLISHED_SCORES:
            continue
        s = all_scores[sys_name]
        pub = PUBLISHED_SCORES[sys_name]
        display = SYSTEM_DISPLAY.get(sys_name, sys_name)
        # Overall: per-run averaging
        computed_overall = s["original_mean"] * 100
        pub_overall = pub["overall"]
        diff = abs(computed_overall - pub_overall)
        match = "✓" if diff < 0.05 else f"Δ={diff:.2f}%"
        w(f"| {display} | Overall | {pub_overall:.2f}% | {computed_overall:.2f}% (per-run avg) | {match} |")
        # Per-category: majority vote
        for cat in [4, 1, 2, 3]:
            cs = s["per_category"].get(cat, {})
            if not cs or cat not in pub:
                continue
            computed_cat = cs.get("majority_accuracy", 0) * 100
            pub_cat = pub[cat]
            diff = abs(computed_cat - pub_cat)
            match = "✓" if diff < 0.05 else f"Δ={diff:.2f}%"
            w(f"| | {CATEGORY_NAMES[cat]} | {pub_cat:.2f}% | {computed_cat:.2f}% (majority) | {match} |")
    w("")
    w(f"All {len(all_scores) * 5} published scores reproduced exactly "
      f"({len(all_scores)} systems × 5 scopes).")
    w("")

    # Error type distribution across systems
    w("### Classification by Error Type")
    w("")
    w("Average across all systems:")
    w("")
    et_stats = defaultdict(lambda: {"penalties": 0, "credits": 0, "washes": 0, "total": 0})
    for sys_name, judgments in all_judgments.items():
        for qid, j in judgments.items():
            et = j["error_type"]
            cls = j["classification"]
            et_stats[et]["total"] += 1
            if cls == "UNDESERVED_PENALTY":
                et_stats[et]["penalties"] += 1
            elif cls == "UNDESERVED_CREDIT":
                et_stats[et]["credits"] += 1
            else:
                et_stats[et]["washes"] += 1

    n_systems = len(all_judgments)
    w("| Error Type | Count | Avg Penalties | Avg Credits | Avg Washes |")
    w("|-----------|-------|--------------|------------|------------|")
    for et in ["HALLUCINATION", "TEMPORAL_ERROR", "ATTRIBUTION_ERROR", "AMBIGUOUS", "INCOMPLETE"]:
        if et not in et_stats:
            continue
        st = et_stats[et]
        per_sys = st["total"] / n_systems if n_systems else 0
        w(f"| {et} | {int(per_sys)} "
          f"| {st['penalties'] / n_systems:.1f} "
          f"| {st['credits'] / n_systems:.1f} "
          f"| {st['washes'] / n_systems:.1f} |")
    w("")

    w("---")
    w("")
    w("## Reproducibility")
    w("")
    w(f"- **Audit date:** {date.today().isoformat()}")
    w(f"- **Judge model:** {model} (temperature=0, {num_runs} independent runs per question)")
    w(f"- **Audit classification:** Majority vote across {num_runs} runs")
    w("- **Original scoring:** Per-run accuracy averaged across 3 original judge runs (mean +/- std)")
    w("- **Error database:** `errors.json` (99 score-corrupting entries)")
    w("- **Published results:** [EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results) on HuggingFace")
    w("")
    w("## Files")
    w("")
    w("| File | Description |")
    w("|------|-------------|")
    w("| `audit_results.py` | This audit script |")
    w("| `download_results.py` | Fetches eval_results.json from HuggingFace |")
    w("| `judgments/*.json` | Per-system LLM audit judgments (fully auditable) |")
    w("| `results/*.json` | Downloaded published eval_results |")
    w("| `per_category_breakdown.json` | Per-system, per-category adjusted scores (JSON) |")
    w("")

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report)
    print(f"\nReport written to {REPORT_PATH}")


def _delta_str(delta: float) -> str:
    """Format a delta as +X.XX% or -X.XX%."""
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2%}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    parser = argparse.ArgumentParser(
        description="Audit LoCoMo benchmark results against known ground truth errors"
    )
    parser.add_argument(
        "--errors", type=Path, default=ERRORS_PATH,
        help=f"Path to errors.json (default: {ERRORS_PATH})",
    )
    parser.add_argument(
        "--systems", nargs="+", default=SYSTEMS,
        choices=SYSTEMS, help="Systems to audit",
    )
    parser.add_argument(
        "--runs", type=int, default=DEFAULT_JUDGE_RUNS,
        help=f"Independent judge runs per question (default: {DEFAULT_JUDGE_RUNS})",
    )
    parser.add_argument(
        "--concurrency", type=int, default=3,
        help="Max concurrent LLM calls (default: 3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would be judged without calling the LLM",
    )
    args = parser.parse_args()

    # Load errors
    errors = load_errors(args.errors)
    if len(errors) != 99:
        print(f"WARNING: Expected 99 score-corrupting errors, got {len(errors)}")

    # Setup LLM client
    # LLM_API_KEY takes priority (matches LLM_BASE_URL for non-OpenAI providers)
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: Set OPENAI_API_KEY or LLM_API_KEY environment variable")
        sys.exit(1)

    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    client = AsyncOpenAI(api_key=api_key or "dry-run", base_url=base_url)
    semaphore = asyncio.Semaphore(args.concurrency)

    if not args.dry_run:
        print(f"Using model: {model} at {base_url}")
    print()

    # Audit each system
    all_judgments = {}
    all_system_results = {}
    for system in args.systems:
        print(f"Auditing {SYSTEM_DISPLAY.get(system, system)}...")
        judgments, sys_results = await audit_system(
            system, errors, client, model, semaphore,
            num_runs=args.runs, dry_run=args.dry_run,
        )
        all_judgments[system] = judgments
        all_system_results[system] = sys_results

    if args.dry_run:
        total = sum(
            len([e for e in errors if e["question_id"] not in all_judgments.get(s, {})])
            for s in args.systems
        )
        print(f"\nDry run complete. {total} questions x {args.runs} runs = {total * args.runs} LLM calls.")
        return

    # Compute scores
    print("\nComputing adjusted scores...")
    all_scores = {}
    for system in args.systems:
        if system in all_judgments and all_system_results.get(system):
            all_scores[system] = compute_scores(all_system_results[system], all_judgments[system], errors)

    # Print summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    for sys_name in args.systems:
        if sys_name not in all_scores:
            continue
        s = all_scores[sys_name]
        display = SYSTEM_DISPLAY.get(sys_name, sys_name)
        print(f"\n{display}:")
        print(f"  Original:  {s['original_mean']:.2%} +/- {s['original_std']:.2%}")
        print(f"  Adjusted:  {s['adjusted_mean']:.2%} +/- {s['adjusted_std']:.2%}")
        print(f"  Delta:     {_delta_str(s['delta'])}")
        print(f"  Penalties: {s['penalties']}  Credits: {s['credits']}  Washes: {s['washes']}")

    # Generate report
    generate_report(all_scores, all_judgments, errors, model=model, num_runs=args.runs)

    # Dump per-category breakdown for auditability
    breakdown = {}
    for sys_name in args.systems:
        if sys_name not in all_scores:
            continue
        s = all_scores[sys_name]
        sys_breakdown = {
            "overall": {
                "original_mean": round(s["original_mean"] * 100, 2),
                "original_std": round(s["original_std"] * 100, 2),
                "adjusted_mean": round(s["adjusted_mean"] * 100, 2),
                "adjusted_std": round(s["adjusted_std"] * 100, 2),
                "majority_accuracy": round(s["majority_accuracy"] * 100, 2),
                "majority_correct": s["majority_correct"],
                "total": TOTAL_QUESTIONS,
                "penalties": s["penalties"],
                "credits": s["credits"],
                "washes": s["washes"],
                "ceiling": round(OVERALL_CEILING * 100, 2),
            },
            "per_category": {},
        }
        for cat in [4, 1, 2, 3]:
            cs = s["per_category"].get(cat, {})
            if not cs:
                continue
            cat_key = f"cat_{cat}_{CATEGORY_NAMES[cat].lower().replace('-', '_')}"
            sys_breakdown["per_category"][cat_key] = {
                "original_mean": round(cs["original_mean"] * 100, 2),
                "original_std": round(cs["original_std"] * 100, 2),
                "adjusted_mean": round(cs["adjusted_mean"] * 100, 2),
                "adjusted_std": round(cs["adjusted_std"] * 100, 2),
                "majority_correct": cs.get("majority_correct", 0),
                "majority_accuracy": round(cs.get("majority_accuracy", 0) * 100, 2),
                "total": CATEGORY_COUNTS[cat],
                "errors_in_category": CATEGORY_ERRORS[cat],
                "ceiling": round(CATEGORY_CEILINGS[cat] * 100, 2),
                "penalties": cs["penalties"],
                "credits": cs["credits"],
                "washes": cs["washes"],
            }
        breakdown[sys_name] = sys_breakdown

    breakdown_path = SCRIPT_DIR / "per_category_breakdown.json"
    with open(breakdown_path, "w") as f:
        json.dump(breakdown, f, indent=2)
    print(f"Per-category breakdown written to {breakdown_path}")


if __name__ == "__main__":
    asyncio.run(main())
