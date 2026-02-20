#!/usr/bin/env python3
"""
analyze_results.py -- Analyze full-context baseline evaluation results.

Reads eval_results.json and answer_results.json for all full-context baseline
runs. Outputs comparison tables in markdown format.

Dependencies: standard library only (json, statistics, pathlib).

Usage:
    python3 fc-baseline/scripts/analyze_results.py
"""

import json
import statistics
from pathlib import Path

BASELINE_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = BASELINE_DIR / "results"
RUNS = {
    "GPT-4o-mini (memos)": RESULTS_DIR / "gpt-4o-mini-memos",
    "GPT-4o-mini (cot)": RESULTS_DIR / "gpt-4o-mini-cot",
    "GPT-4.1-mini (memos)": RESULTS_DIR / "gpt-4.1-mini-memos",
    "GPT-4.1-mini (cot)": RESULTS_DIR / "gpt-4.1-mini-cot",
}

CAT_NAMES = {"1": "Multi-hop", "2": "Temporal", "3": "Open-domain", "4": "Single-hop"}


def load_results(run_dir: Path) -> dict:
    """Load eval_results.json and answer_results.json from a run directory."""
    eval_path = run_dir / "eval_results.json"
    answer_path = run_dir / "answer_results.json"

    data = {}
    if eval_path.exists():
        with open(eval_path, "r", encoding="utf-8") as f:
            data["eval"] = json.load(f)
    if answer_path.exists():
        with open(answer_path, "r", encoding="utf-8") as f:
            data["answers"] = json.load(f)
    return data


def analyze():
    results = {}
    for name, run_dir in RUNS.items():
        if not run_dir.exists():
            print(f"Skipping {name}: {run_dir} not found")
            continue
        results[name] = load_results(run_dir)

    if not results:
        print("No results found.")
        return

    # --- Table 1: Overall Accuracy ---
    print("## Table 1: Overall Accuracy")
    print()

    # Determine number of runs from first result set
    first_data = next(iter(results.values()))
    num_runs = len(first_data["eval"]["metadata"]["run_scores"])
    run_headers = " | ".join(f"Run {i+1}" for i in range(num_runs))
    run_separators = " | ".join("------" for _ in range(num_runs))
    print(f"| Model | Per-Run Mean | Std Dev | Majority Vote | {run_headers} |")
    print(f"|-------|-------------|---------|---------------|{run_separators}|")

    for name, data in results.items():
        m = data["eval"]["metadata"]
        scores = m["run_scores"]
        run_cells = " | ".join(f"{s*100:.2f}%" for s in scores)
        print(f"| {name} | {m['mean_accuracy']*100:.2f}% | {m['std_accuracy']*100:.2f}% "
              f"| {m['majority_vote_accuracy']*100:.2f}% "
              f"| {run_cells} |")

    # EverMemOS claims
    print()
    print("**EverMemOS claims (unverified):** Full-context overall = 91.21% (GPT-4.1-mini)")
    print("**Mem0 paper:** Full-context overall = 72.90% +/- 0.19% (GPT-4o-mini)")
    print()

    # --- Table 2: Per-Category Accuracy ---
    print("## Table 2: Per-Category Accuracy (Per-Run Mean)")
    print()
    header = "| Category | N |"
    sep = "|----------|---|"
    for name in results:
        header += f" {name} |"
        sep += "------------|"
    header += " EverMemOS Claim |"
    sep += "----------------|"
    print(header)
    print(sep)

    evermemos_cats = {"4": "94.93%", "1": "90.43%", "2": "87.95%", "3": "71.88%"}

    for cat in ["4", "1", "2", "3"]:
        cat_name = CAT_NAMES.get(cat, cat)
        cells = []
        n = ""
        for name, data in results.items():
            m = data["eval"]["metadata"]
            cat_data = m["category_accuracies"].get(cat, {})
            if not n:
                n = str(cat_data.get("total", ""))
            mean = cat_data.get("mean", 0) * 100
            std = cat_data.get("std", 0) * 100
            cells.append(f"{mean:.2f}% +/- {std:.2f}%")
        cells.append(evermemos_cats.get(cat, "N/A"))
        print(f"| {cat_name} | {n} | " + " | ".join(cells) + " |")

    print()

    # --- Table 3: Token and Word Count Statistics ---
    print("## Table 3: Token and Word Count Statistics")
    print()
    print("| Metric |", " | ".join(results.keys()), "|")
    print("|--------|", " | ".join(["--------"] * len(results)), "|")

    metrics = [
        ("Mean prompt tokens (API)", "mean_prompt_tokens", "{:.0f}"),
        ("Mean completion tokens", "mean_completion_tokens", "{:.1f}"),
        ("Total prompt tokens", "total_prompt_tokens", "{:,.0f}"),
        ("Total completion tokens", "total_completion_tokens", "{:,.0f}"),
        ("Mean context words", "mean_context_words", "{:,.0f}"),
        ("Mean answer words", "mean_answer_words", "{:.1f}"),
        ("Median answer words", "median_answer_words", "{:.1f}"),
    ]

    for label, key, fmt in metrics:
        row = f"| {label} |"
        for name, data in results.items():
            val = data["eval"]["metadata"].get(key, 0)
            row += f" {fmt.format(val)} |"
        print(row)

    print()
    print("**EverMemOS claim:** 20,281 Average Tokens for full-context.")
    print()

    # --- Table 4: Comparison with Published Systems ---
    print("## Table 4: Full-Context vs. Published System Scores")
    print()
    print("All scores are majority-vote accuracy on 1,540 questions (category 5 excluded).")
    print()
    print("| System | Overall | Answer Model | Source |")
    print("|--------|---------|-------------|--------|")

    for name, data in results.items():
        m = data["eval"]["metadata"]
        model = m["answer_model"]
        prompt = m.get("answer_prompt", "unknown")
        prompt_short = "CoT" if "cot" in prompt else "memos"
        acc = m["majority_vote_accuracy"] * 100
        print(f"| FC Baseline ({model}, {prompt_short}) | {acc:.2f}% | {model} | This evaluation |")

    print("| FC Baseline (claimed) | 91.21% | GPT-4.1-mini | EverMemOS README (unverified) |")
    print("| FC Baseline (claimed) | 72.90% | GPT-4o-mini | Mem0 paper (code available, no results) |")
    print("| EverMemOS | 92.32% | GPT-4.1-mini | Published eval_results.json |")
    print("| Zep | 85.22% | GPT-4.1-mini | Published eval_results.json |")
    print("| MemOS | 80.76% | GPT-4.1-mini | Published eval_results.json |")
    print("| MemU | 66.67% | GPT-4.1-mini | Published eval_results.json |")
    print("| Mem0 | 64.20% | GPT-4.1-mini | Published eval_results.json |")
    print()

    # --- Table 5: Delta Analysis ---
    cot_key = "GPT-4.1-mini (cot)"
    memos_key = "GPT-4.1-mini (memos)"
    if cot_key in results:
        cot_acc = results[cot_key]["eval"]["metadata"]["majority_vote_accuracy"] * 100
        memos_acc = results[memos_key]["eval"]["metadata"]["majority_vote_accuracy"] * 100 if memos_key in results else None
        print("## Table 5: Delta from Full-Context Baseline (GPT-4.1-mini)")
        print()
        print("Positive delta = system exceeds full-context (memory system adds value).")
        print("Negative delta = system underperforms full-context (memory system loses information).")
        print()
        print("| System | Overall | Delta from FC (CoT) |")
        print("|--------|---------|---------------------|")
        print(f"| FC Baseline (ours, CoT) | {cot_acc:.2f}% | 0.00% |")
        if memos_acc is not None:
            delta_m = memos_acc - cot_acc
            print(f"| FC Baseline (ours, memos) | {memos_acc:.2f}% | {delta_m:+.2f}% |")

        systems = [
            ("EverMemOS", 92.32),
            ("Zep", 85.22),
            ("MemOS", 80.76),
            ("MemU", 66.67),
            ("Mem0", 64.20),
        ]
        for sys_name, sys_acc in systems:
            delta = sys_acc - cot_acc
            print(f"| {sys_name} | {sys_acc:.2f}% | {delta:+.2f}% |")

        print()

    # --- Answer word count distribution ---
    print("## Table 6: Answer Word-Count Distribution")
    print()
    print("| Model | Mean | Median | Std Dev | Min | Max |")
    print("|-------|------|--------|---------|-----|-----|")

    for name, data in results.items():
        if "answers" not in data:
            continue
        words = [len(a["generated_answer"].split()) for a in data["answers"]]
        print(f"| {name} | {statistics.mean(words):.1f} | {statistics.median(words):.1f} "
              f"| {statistics.pstdev(words):.1f} | {min(words)} | {max(words)} |")

    print()


if __name__ == "__main__":
    analyze()
