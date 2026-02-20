#!/usr/bin/env python3
"""
Adversarial Plausibility Baseline — Scoring Pipeline

Scores adversarial (intentionally wrong) answers against the LoCoMo benchmark
using the EXACT same LLM judge prompt, model, and methodology as the original
EverMemOS evaluation pipeline.

Purpose: Test whether the LLM-as-judge can distinguish plausible-sounding wrong
answers from correct ones. If the adversarial baseline scores well, the judge is broken.

Usage:
    python score_ap.py                # Full run (resumes from checkpoint)
    python score_ap.py --dry-run      # Show what would be judged

Prompt source: ../evaluation/config/prompts.yaml (llm_judge section)
    This is the SAME file used by the original evaluation pipeline.
    The prompts are loaded at runtime — not copied — so any diff against
    the original evaluation is guaranteed to show identical judge behavior.

Environment:
    OPENROUTER_API_KEY, OPENAI_API_KEY, or LLM_API_KEY  -- API key for the judge LLM
    LLM_BASE_URL (optional)        — Custom base URL (e.g. OpenRouter)
    LLM_MODEL (optional)           — Model override (default: gpt-4o-mini)
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

try:
    from openai import AsyncOpenAI
except ImportError:
    print("Error: openai package required. Install with: pip install openai")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
PROMPTS_PATH = SCRIPT_DIR.parent / "evaluation" / "config" / "prompts.yaml"
INPUT_PATH = SCRIPT_DIR / "ap_eval_results.json"
OUTPUT_PATH = SCRIPT_DIR / "ap_eval_results_scored.json"
CHECKPOINT_PATH = SCRIPT_DIR / "scoring_checkpoint.json"
REPORT_PATH = SCRIPT_DIR / "AP_BASELINE_REPORT.md"

NUM_RUNS = 3           # Same as original evaluation
CONCURRENCY = 10       # Same as original LLMJudge semaphore

TOTAL_QUESTIONS = 1540
CATEGORY_NAMES = {1: "Multi-hop", 2: "Temporal", 3: "Open-domain", 4: "Single-hop"}
CATEGORY_COUNTS = {1: 282, 2: 321, 3: 96, 4: 841}

# Published scores for comparison (mean-of-runs from EverMemOS eval)
PUBLISHED_SCORES = {
    "EverMemOS": {"overall": 92.32, 4: 96.08, 1: 91.13, 2: 89.72, 3: 70.83},
    "Zep":       {"overall": 85.22, 4: 90.84, 1: 81.91, 2: 77.26, 3: 75.00},
    "MemOS":     {"overall": 80.76, 4: 85.37, 1: 79.43, 2: 75.08, 3: 64.58},
    "MemU":      {"overall": 66.67, 4: 74.91, 1: 72.34, 2: 43.61, 3: 54.17},
    "Mem0":      {"overall": 64.20, 4: 68.97, 1: 61.70, 2: 58.26, 3: 50.00},
}


# ---------------------------------------------------------------------------
# Prompt Loading
# ---------------------------------------------------------------------------


def load_prompts() -> tuple[str, str]:
    """Load judge prompts from the original evaluation config.

    Returns (system_prompt, user_prompt_template).
    Raises FileNotFoundError if the prompts file is missing.
    """
    if not PROMPTS_PATH.exists():
        print(f"FATAL: Prompts file not found: {PROMPTS_PATH}")
        print("This file must be the original evaluation/config/prompts.yaml")
        sys.exit(1)

    with open(PROMPTS_PATH) as f:
        prompts = yaml.safe_load(f)

    system_prompt = prompts["llm_judge"]["system_prompt"].strip()
    user_prompt_template = prompts["llm_judge"]["user_prompt"].strip()

    print(f"Loaded judge prompts from {PROMPTS_PATH}")
    print(f"  System prompt: {system_prompt[:80]}...")
    print(f"  User prompt template: {user_prompt_template[:80]}...")
    return system_prompt, user_prompt_template


# ---------------------------------------------------------------------------
# Data Loading / Saving
# ---------------------------------------------------------------------------


def load_input() -> dict:
    """Load ap_eval_results.json."""
    with open(INPUT_PATH) as f:
        return json.load(f)


def load_checkpoint() -> dict[str, dict]:
    """Load scoring checkpoint (question_id -> llm_judgments)."""
    if CHECKPOINT_PATH.exists():
        with open(CHECKPOINT_PATH) as f:
            return json.load(f)
    return {}


def save_checkpoint(checkpoint: dict):
    """Atomic checkpoint save."""
    tmp = CHECKPOINT_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(checkpoint, f, indent=2)
    os.replace(tmp, CHECKPOINT_PATH)


# ---------------------------------------------------------------------------
# JSON Extraction (same logic as original LLMJudge._extract_json)
# ---------------------------------------------------------------------------


def extract_json(content: str) -> str | None:
    """Extract JSON from LLM response, matching original evaluator logic."""
    # Try 1: markdown code block
    m = re.search(r'```(?:json)?\s*(\{[^`]*\})\s*```', content, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Try 2: JSON object with "label" key
    m = re.search(r'\{[^{}]*"label"\s*:\s*"[^"]*"[^{}]*\}', content)
    if m:
        return m.group(0)

    # Try 3: raw content
    return content.strip()


# ---------------------------------------------------------------------------
# LLM Judge
# ---------------------------------------------------------------------------


async def judge_single(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> bool:
    """Single judge call. Returns True if CORRECT, False otherwise.

    Matches original LLMJudge._judge_answer behavior exactly:
    - temperature=0
    - Extracts {"label": "CORRECT"} or {"label": "WRONG"}
    - Returns False on any failure (no retries — same as original)
    """
    try:
        resp = await client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as e:
        err_str = str(e).lower()
        fatal = ["insufficient_quota", "invalid_api_key", "key limit"]
        if any(k in err_str for k in fatal):
            print(f"\nFATAL API error: {e}")
            sys.exit(1)
        print(f"  ⚠️ LLM Judge failed: {type(e).__name__}: {e}")
        return False

    if not resp.choices:
        print(f"  ⚠️ LLM Judge: Empty choices in response")
        return False
    content = resp.choices[0].message.content or ""
    if not content:
        print(f"  ⚠️ LLM Judge: Empty response")
        return False

    json_str = extract_json(content)
    if not json_str:
        print(f"  ⚠️ LLM Judge: No JSON found in response")
        return False

    try:
        result = json.loads(json_str)
        label = result.get("label", "")
        if not label:
            print(f"  ⚠️ LLM Judge: No label found in response")
            return False
        return label.strip().upper() == "CORRECT"
    except json.JSONDecodeError:
        print(f"  ⚠️ LLM Judge JSON parse failed")
        return False


async def judge_question(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    entry: dict,
) -> dict[str, bool]:
    """Run NUM_RUNS independent judge calls for one question.

    Returns {judgment_1: bool, judgment_2: bool, judgment_3: bool}.
    Runs sequentially within each question, matching original _evaluate_single_answer.
    """
    user_prompt = (
        user_prompt_template
        .replace("{question}", entry["question"])
        .replace("{golden_answer}", str(entry["golden_answer"]))
        .replace("{generated_answer}", entry["generated_answer"])
    )

    judgments = {}
    for i in range(NUM_RUNS):
        is_correct = await judge_single(
            client, model, system_prompt, user_prompt,
        )
        judgments[f"judgment_{i+1}"] = is_correct

    return judgments


# ---------------------------------------------------------------------------
# Scoring (matches compute_acc.py methodology)
# ---------------------------------------------------------------------------


def compute_scores(data: dict) -> dict:
    """Compute per-run accuracy averaged, matching original methodology."""
    run_correct = [0] * NUM_RUNS
    cat_run_correct = [defaultdict(int) for _ in range(NUM_RUNS)]
    cat_totals = defaultdict(int)
    total = 0

    for _uid, questions in data["detailed_results"].items():
        for entry in questions:
            cat = int(entry["category"])
            jdg = entry.get("llm_judgments", {})
            if not jdg:
                continue
            total += 1
            cat_totals[cat] += 1
            for i in range(NUM_RUNS):
                if jdg.get(f"judgment_{i+1}", False):
                    run_correct[i] += 1
                    cat_run_correct[i][cat] += 1

    run_accs = [c / total for c in run_correct] if total else [0] * NUM_RUNS
    mean_acc = statistics.mean(run_accs)
    std_acc = statistics.pstdev(run_accs)

    cat_scores = {}
    for cat in CATEGORY_COUNTS:
        ct = cat_totals.get(cat, 0)
        if ct == 0:
            continue
        cat_accs = [cat_run_correct[i].get(cat, 0) / ct for i in range(NUM_RUNS)]
        cat_mean = statistics.mean(cat_accs)
        cat_std = statistics.pstdev(cat_accs)
        cat_scores[cat] = {
            "mean": cat_mean,
            "std": cat_std,
            "run_accs": cat_accs,
            "total": ct,
        }

    return {
        "total": total,
        "mean": mean_acc,
        "std": std_acc,
        "run_accs": run_accs,
        "per_category": cat_scores,
    }


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------


def generate_report(scores: dict, model: str, prompt_path: str):
    """Generate AP_BASELINE_REPORT.md."""
    lines = []
    w = lines.append

    w("# Adversarial Plausibility Baseline — Judge Leniency Stress Test")
    w("")
    w("## What This Is")
    w("")
    w("A frontier LLM (Claude Opus 4.6) was given the LoCoMo answer key and asked to generate")
    w("the most plausible-sounding **wrong** answers it could for all 1,540 questions. These")
    w("intentionally incorrect answers were then scored by the exact same LLM judge used to")
    w("evaluate all 5 published memory systems.")
    w("")
    w("**If the judge is functioning correctly, the adversarial baseline should score near 0%.**")
    w("Any score significantly above 0% represents answers where the judge cannot distinguish")
    w("crafted wrong answers from correct ones.")
    w("")

    w("## Methodology")
    w("")
    w("### Answer Generation")
    w("")
    w("- **Model**: Claude Opus 4.6 (claude-opus-4-6)")
    w("- **Task**: Generate maximally plausible wrong answers for each question")
    w("- **Input**: Full answer key (question + golden answer for all 1,540 questions)")
    w("- **Output**: `ap_eval_results.json` — same format as published eval_results.json")
    w("")
    w("### Scoring")
    w("")
    w(f"- **Judge model**: {model} (temperature=0)")
    w(f"- **Judge prompt**: Loaded at runtime from `{prompt_path}`")
    w("  - This is the **identical file** used by the original EverMemOS evaluation pipeline")
    w("  - Not copied, not paraphrased — loaded from the same source")
    w(f"- **Runs**: {NUM_RUNS} independent judge calls per question")
    w("- **Scoring**: Per-run accuracy averaged across runs (matching `compute_acc.py`)")
    w(f"- **Concurrency**: {CONCURRENCY} (matching original LLMJudge semaphore)")
    w("")

    w("## Results")
    w("")
    w(f"### Overall: {scores['mean']*100:.2f}% +/- {scores['std']*100:.2f}%")
    w("")
    w(f"Out of {scores['total']} questions with intentionally wrong answers, the judge")
    w(f"marked **{scores['mean']*100:.2f}%** as correct.")
    w("")
    w(f"Per-run accuracies: {', '.join(f'{a*100:.2f}%' for a in scores['run_accs'])}")
    w("")

    w("### Per-Category Breakdown")
    w("")
    w("| Category | AP Score | N |")
    w("|----------|---------|---|")
    for cat in [4, 1, 2, 3]:
        cs = scores["per_category"].get(cat, {})
        if not cs:
            continue
        w(f"| {CATEGORY_NAMES[cat]} | {cs['mean']*100:.2f}% +/- {cs['std']*100:.2f}% | {cs['total']} |")
    w("")

    w("### Comparison Against Real Systems")
    w("")
    w("| System | Overall | Single-hop | Multi-hop | Temporal | Open-domain |")
    w("|--------|---------|-----------|----------|----------|-------------|")
    # AP Baseline row
    ap_overall = f"{scores['mean']*100:.2f}%"
    ap_cats = []
    for cat in [4, 1, 2, 3]:
        cs = scores["per_category"].get(cat, {})
        ap_cats.append(f"{cs['mean']*100:.2f}%" if cs else "N/A")
    w(f"| **AP Baseline** | **{ap_overall}** | **{ap_cats[0]}** | **{ap_cats[1]}** | **{ap_cats[2]}** | **{ap_cats[3]}** |")
    # Real systems
    for sys_name in ["EverMemOS", "Zep", "MemOS", "MemU", "Mem0"]:
        pub = PUBLISHED_SCORES[sys_name]
        w(f"| {sys_name} | {pub['overall']:.2f}% "
          f"| {pub[4]:.2f}% | {pub[1]:.2f}% "
          f"| {pub[2]:.2f}% | {pub[3]:.2f}% |")
    w("")

    w("## Reproducibility")
    w("")
    w(f"- **Scoring date**: {date.today().isoformat()}")
    w(f"- **Judge model**: {model} (temperature=0, {NUM_RUNS} runs)")
    w(f"- **Judge prompt source**: `{prompt_path}`")
    w(f"- **Adversarial answers generated by**: Claude Opus 4.6 (claude-opus-4-6)")
    w(f"- **Input**: `ap_eval_results.json` (1,540 intentionally wrong answers)")
    w(f"- **Output**: `ap_eval_results_scored.json` (with llm_judgments filled in)")
    w("")
    w("### How to Reproduce")
    w("")
    w("```bash")
    w("# Re-run scoring (resumes from checkpoint)")
    w("python score_ap.py")
    w("```")
    w("")

    w("## Files")
    w("")
    w("| File | Description |")
    w("|------|-------------|")
    w("| `answer_key.json` | LoCoMo answer key (1,540 Q+A pairs) fed to adversarial baseline |")
    w("| `ap_eval_results.json` | Adversarial baseline output (intentionally wrong answers) |")
    w("| `ap_eval_results_scored.json` | Scored results (llm_judgments filled in) |")
    w("| `score_ap.py` | This scoring script |")
    w("| `AP_BASELINE_REPORT.md` | This report |")
    w("")

    report = "\n".join(lines) + "\n"
    REPORT_PATH.write_text(report)
    print(f"\nReport written to {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    parser = argparse.ArgumentParser(description="Score Adversarial Plausibility Baseline answers")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be judged")
    args = parser.parse_args()

    # Load prompts from original evaluation config
    system_prompt, user_prompt_template = load_prompts()

    # Load input data
    data = load_input()
    all_entries = []
    for _uid, questions in data["detailed_results"].items():
        all_entries.extend(questions)
    print(f"Loaded {len(all_entries)} questions from {INPUT_PATH.name}")

    # Load checkpoint
    checkpoint = load_checkpoint()
    to_judge = [e for e in all_entries if e["question_id"] not in checkpoint]
    print(f"  {len(checkpoint)} already scored, {len(to_judge)} remaining")

    if args.dry_run:
        print(f"\nDry run: {len(to_judge)} questions x {NUM_RUNS} runs = {len(to_judge) * NUM_RUNS} LLM calls")
        return

    # Setup LLM client
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        print("Error: Set OPENROUTER_API_KEY, OPENAI_API_KEY, or LLM_API_KEY environment variable")
        sys.exit(1)

    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    semaphore = asyncio.Semaphore(CONCURRENCY)

    print(f"Using model: {model} at {base_url}")
    print(f"Judge prompt source: {PROMPTS_PATH}")
    print()

    # Judge remaining questions
    # Semaphore wraps entire question evaluation (all 3 runs),
    # matching original LLMJudge.evaluate concurrency model exactly.
    async def judge_one(entry):
        async with semaphore:
            return entry["question_id"], await judge_question(
                client, model, system_prompt, user_prompt_template,
                entry,
            )

    tasks = [judge_one(e) for e in to_judge]
    completed = 0
    for coro in asyncio.as_completed(tasks):
        qid, judgments = await coro
        checkpoint[qid] = judgments
        completed += 1
        if completed % 50 == 0 or completed == len(tasks):
            save_checkpoint(checkpoint)
            print(f"  {completed}/{len(tasks)} scored (checkpoint saved)")

    # Apply judgments to data
    for _uid, questions in data["detailed_results"].items():
        for entry in questions:
            qid = entry["question_id"]
            if qid in checkpoint:
                entry["llm_judgments"] = checkpoint[qid]

    # Compute scores
    scores = compute_scores(data)
    print(f"\n{'='*60}")
    print(f"ADVERSARIAL PLAUSIBILITY BASELINE — RESULTS")
    print(f"{'='*60}")
    print(f"Overall: {scores['mean']*100:.2f}% +/- {scores['std']*100:.2f}%")
    print(f"Per-run: {', '.join(f'{a*100:.2f}%' for a in scores['run_accs'])}")
    for cat in [4, 1, 2, 3]:
        cs = scores["per_category"].get(cat, {})
        if cs:
            print(f"  {CATEGORY_NAMES[cat]}: {cs['mean']*100:.2f}% +/- {cs['std']*100:.2f}%")

    # Save scored results
    data["accuracy"] = scores["mean"]
    data["correct"] = round(scores["mean"] * scores["total"])
    tmp = OUTPUT_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, OUTPUT_PATH)
    print(f"\nScored results written to {OUTPUT_PATH.name}")

    # Generate report
    prompt_rel = os.path.relpath(PROMPTS_PATH, SCRIPT_DIR)
    generate_report(scores, model, prompt_rel)


if __name__ == "__main__":
    asyncio.run(main())
