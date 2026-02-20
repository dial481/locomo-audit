#!/usr/bin/env python3
"""
word_count_analysis.py
======================
Analyzes generated-answer word counts across all evaluated memory systems
and the two adversarial-plausibility baselines.

Outputs markdown tables to stdout covering:
  1. Per-system word-count statistics (mean, median, std dev)
  2. Mean gold-answer word count
  3. Mean generated/gold ratio
  4. Distribution buckets relative to gold length
  5. Judge-approved accuracy at each length bucket
  6. Overall accuracy (majority vote)
  7. Correlation table (mean word count vs. accuracy)

Usage (from repo root):
    python methodology/scripts/word_count_analysis.py

Dependencies: standard library only (json, statistics, pathlib, sys).
"""

import json
import statistics
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Resolve repo root relative to this script (script lives in methodology/scripts/)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Map of display name -> relative path from repo root
SYSTEM_FILES = {
    "EverMemOS":  "results-audit/results/evermemos_eval_results.json",
    "Mem0":       "results-audit/results/mem0_eval_results.json",
    "MemoS":      "results-audit/results/memos_eval_results.json",
    "MemU":       "results-audit/results/memu_eval_results.json",
    "Zep":        "results-audit/results/zep_eval_results.json",
    "AP v1":      "ap-baseline/v1/bs_eval_results_scored.json",
    "AP v2":      "ap-baseline/v2/bs_eval_results_scored.json",
}

# Length-ratio bucket definitions: (lower_bound_inclusive, upper_bound_exclusive, label)
BUCKETS = [
    (0,   1,   "0-1x"),
    (1,   3,   "1-3x"),
    (3,   5,   "3-5x"),
    (5,  10,   "5-10x"),
    (10,  20,  "10-20x"),
    (20, float("inf"), "20x+"),
]

# Category 5 is adversarial -- excluded from all scoring / analysis.
# eval_results.json stores category as string; cast to int to match
# the convention in results-audit/audit_results.py and ap-baseline/score_ap.py.
EXCLUDED_CATEGORIES = {5}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def word_count(text):
    """Count words by splitting on whitespace. Handles non-string values."""
    return len(str(text).split())


def is_judge_approved(judgments: dict) -> bool:
    """
    A question is judge-approved when at least 2 of 3 judgments are True
    (majority vote).  If judgments dict is empty (AP baselines), return False.
    """
    if not judgments:
        return False
    true_count = sum(1 for v in judgments.values() if v is True)
    return true_count >= 2


def bucket_index(ratio):
    """Return the index into BUCKETS for a given generated/gold ratio."""
    for i, (lo, hi, _) in enumerate(BUCKETS):
        if lo <= ratio < hi:
            return i
    # Should not happen, but fall into last bucket as safety
    return len(BUCKETS) - 1


def fmt(value, decimals=2):
    """Format a float to the given number of decimal places."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def pct(value, decimals=1):
    """Format a float as a percentage string."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}%"


# ---------------------------------------------------------------------------
# Data loading and analysis
# ---------------------------------------------------------------------------

def load_questions(filepath):
    """
    Load a JSON eval-results file and return a flat list of question dicts,
    excluding category-5 (adversarial) questions.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    for _user, qlist in data["detailed_results"].items():
        for q in qlist:
            if int(q.get("category", 0)) in EXCLUDED_CATEGORIES:
                continue
            questions.append(q)
    return questions


def analyse_system(questions):
    """
    Given a flat list of question dicts, compute all statistics.
    Returns a dict of results.
    """
    gen_wcs = []          # generated-answer word counts
    gold_wcs = []         # gold-answer word counts
    ratios = []           # per-question generated/gold ratio
    bucket_counts = [0] * len(BUCKETS)
    bucket_approved = [0] * len(BUCKETS)
    total_approved = 0

    for q in questions:
        gwc = word_count(q["generated_answer"])
        gwc_gold = word_count(q["golden_answer"])

        gen_wcs.append(gwc)
        gold_wcs.append(gwc_gold)

        # Ratio (guard against zero-length gold answers)
        if gwc_gold > 0:
            ratio = gwc / gwc_gold
        else:
            ratio = float(gwc)  # treat as infinite-ish
        ratios.append(ratio)

        # Bucket assignment
        bi = bucket_index(ratio)
        bucket_counts[bi] += 1

        # Judge approval
        approved = is_judge_approved(q.get("llm_judgments", {}))
        if approved:
            total_approved += 1
            bucket_approved[bi] += 1

    n = len(questions)

    # Basic word-count stats
    gen_mean = statistics.mean(gen_wcs) if gen_wcs else 0
    gen_median = statistics.median(gen_wcs) if gen_wcs else 0
    gen_stdev = statistics.stdev(gen_wcs) if len(gen_wcs) >= 2 else 0
    gold_mean = statistics.mean(gold_wcs) if gold_wcs else 0
    ratio_mean = (gen_mean / gold_mean) if gold_mean > 0 else 0
    cv = (gen_stdev / gen_mean * 100) if gen_mean > 0 else 0

    # Overall accuracy
    accuracy = (total_approved / n * 100) if n else 0

    # Bucket percentages & per-bucket accuracy
    bucket_pcts = [(c / n * 100) if n else 0 for c in bucket_counts]
    bucket_accs = [
        (bucket_approved[i] / bucket_counts[i] * 100) if bucket_counts[i] > 0 else None
        for i in range(len(BUCKETS))
    ]

    return {
        "n": n,
        "gen_mean": gen_mean,
        "gen_median": gen_median,
        "gen_stdev": gen_stdev,
        "gold_mean": gold_mean,
        "ratio_mean": ratio_mean,
        "cv": cv,
        "accuracy": accuracy,
        "total_approved": total_approved,
        "bucket_counts": bucket_counts,
        "bucket_pcts": bucket_pcts,
        "bucket_accs": bucket_accs,
    }


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def print_table(headers, rows, alignments=None):
    """
    Print a markdown table.
    alignments: list of 'l', 'r', or 'c' per column (default left).
    """
    if alignments is None:
        alignments = ["l"] * len(headers)

    # Compute column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt_row(cells):
        parts = []
        for i, cell in enumerate(cells):
            s = str(cell)
            if alignments[i] == "r":
                parts.append(s.rjust(col_widths[i]))
            elif alignments[i] == "c":
                parts.append(s.center(col_widths[i]))
            else:
                parts.append(s.ljust(col_widths[i]))
        return "| " + " | ".join(parts) + " |"

    def sep_row():
        parts = []
        for i in range(len(headers)):
            w = col_widths[i]
            if alignments[i] == "r":
                parts.append("-" * (w - 1) + ":")
            elif alignments[i] == "c":
                parts.append(":" + "-" * (w - 2) + ":")
            else:
                parts.append("-" * w)
        return "| " + " | ".join(parts) + " |"

    print(fmt_row(headers))
    print(sep_row())
    for row in rows:
        print(fmt_row(row))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Load and analyse all systems
    results = {}
    for name, relpath in SYSTEM_FILES.items():
        filepath = REPO_ROOT / relpath
        if not filepath.exists():
            print(f"WARNING: file not found, skipping {name}: {filepath}",
                  file=sys.stderr)
            continue
        questions = load_questions(filepath)
        results[name] = analyse_system(questions)

    if not results:
        print("ERROR: no data files found.", file=sys.stderr)
        sys.exit(1)

    system_names = list(results.keys())

    # ------------------------------------------------------------------
    # Table 1: Word-count statistics
    # ------------------------------------------------------------------
    print("## Table 1: Generated Answer Word-Count Statistics")
    print()
    headers = ["System", "N", "Gen Mean", "Gen Median", "Gen Std Dev",
               "Gold Mean", "Mean Ratio (Gen/Gold)"]
    rows = []
    for name in system_names:
        r = results[name]
        rows.append([
            name,
            r["n"],
            fmt(r["gen_mean"]),
            fmt(r["gen_median"]),
            fmt(r["gen_stdev"]),
            fmt(r["gold_mean"]),
            fmt(r["ratio_mean"], 2),
        ])
    alignments = ["l", "r", "r", "r", "r", "r", "r"]
    print_table(headers, rows, alignments)
    print()

    # ------------------------------------------------------------------
    # Gold-answers paragraph + Coefficient of Variation subsection
    # ------------------------------------------------------------------
    gold_mean_val = results[system_names[0]]["gold_mean"]
    evermemos_ratio = results["EverMemOS"]["ratio_mean"]
    zep_ratio = results["Zep"]["ratio_mean"]
    ratio_lo = round(min(evermemos_ratio, zep_ratio))
    ratio_hi = round(max(evermemos_ratio, zep_ratio))
    print(f"Gold answers average {fmt(gold_mean_val)} words. Systems with "
          f"the \"5-6 words\" prompt instruction (Mem0, MemU) produce answers "
          f"near gold length. Systems without that instruction (EverMemOS, "
          f"Zep) produce answers {ratio_lo}-{ratio_hi}x longer.")
    print()

    print("### Coefficient of Variation")
    print()
    print("The coefficient of variation (CV = std dev / mean) quantifies "
          "dispersion relative to the mean. For word counts (positive "
          "integers), a CV above 100% indicates an extremely skewed or "
          "multimodal distribution.")
    print()

    cv_sorted = sorted(system_names, key=lambda n: results[n]["cv"],
                        reverse=True)
    headers = ["System", "Mean", "Std Dev", "CV"]
    rows = []
    for name in cv_sorted:
        r = results[name]
        rows.append([
            name,
            fmt(r["gen_mean"]),
            fmt(r["gen_stdev"]),
            f"{r['cv']:.0f}%",
        ])
    alignments = ["l", "r", "r", "r"]
    print_table(headers, rows, alignments)
    print()

    memos = results["MemoS"]
    mem0 = results["Mem0"]
    memu = results["MemU"]
    apv2 = results["AP v2"]

    print(f"MemoS has a CV of {memos['cv']:.0f}%: its standard deviation "
          f"exceeds its mean. Table 4 confirms a bimodal pattern -- "
          f"{memos['bucket_counts'][0]} answers fall at 0-1x gold length "
          f"while {memos['bucket_counts'][5]} fall at 20x+, with the median "
          f"({fmt(memos['gen_median'])}) far below the mean "
          f"({fmt(memos['gen_mean'])}). "
          f"Mem0 ({mem0['cv']:.0f}%) and MemU ({memu['cv']:.0f}%) show "
          f"similarly high variance relative to their means.")
    print()

    gap = mem0["accuracy"] - apv2["accuracy"]
    print(f"AP v2 (deliberately wrong, vague-but-topical answers) has the "
          f"tightest distribution of any system (CV = {apv2['cv']:.0f}%) and "
          f"scores {pct(apv2['accuracy'])} overall. Mem0 scores "
          f"{pct(mem0['accuracy'])} with more than double the variance "
          f"(CV = {mem0['cv']:.0f}%). The {gap:.1f}-point gap spans "
          f"{mem0['n']:,} questions.")
    print()

    print("None of the published evaluations include confidence intervals "
          "or statistical significance tests for the reported accuracy "
          "differences.")
    print()

    # ------------------------------------------------------------------
    # Table 2: Distribution buckets (% of answers in each ratio range)
    # ------------------------------------------------------------------
    print("## Table 2: Answer-Length Distribution (% of answers by Gen/Gold ratio)")
    print()
    bucket_labels = [b[2] for b in BUCKETS]
    headers = ["System"] + bucket_labels
    rows = []
    for name in system_names:
        r = results[name]
        row = [name] + [pct(p) for p in r["bucket_pcts"]]
        rows.append(row)
    alignments = ["l"] + ["r"] * len(bucket_labels)
    print_table(headers, rows, alignments)
    print()

    # ------------------------------------------------------------------
    # Table 3: Accuracy at each length bucket
    # ------------------------------------------------------------------
    print("## Table 3: Judge-Approved Accuracy by Length Bucket")
    print()
    headers = ["System"] + bucket_labels + ["Overall"]
    rows = []
    for name in system_names:
        r = results[name]
        row = [name]
        for acc in r["bucket_accs"]:
            row.append(pct(acc) if acc is not None else "N/A")
        row.append(pct(r["accuracy"]))
        rows.append(row)
    alignments = ["l"] + ["r"] * (len(bucket_labels) + 1)
    print_table(headers, rows, alignments)
    print()

    # ------------------------------------------------------------------
    # Table 4: Bucket counts (raw numbers for reference)
    # ------------------------------------------------------------------
    print("## Table 4: Answer Counts per Length Bucket")
    print()
    headers = ["System"] + bucket_labels + ["Total"]
    rows = []
    for name in system_names:
        r = results[name]
        row = [name] + [str(c) for c in r["bucket_counts"]] + [str(r["n"])]
        rows.append(row)
    alignments = ["l"] + ["r"] * (len(bucket_labels) + 1)
    print_table(headers, rows, alignments)
    print()

    # ------------------------------------------------------------------
    # Table 5: Correlation table (mean word count vs accuracy)
    # ------------------------------------------------------------------
    print("## Table 5: Word Count vs. Accuracy Correlation")
    print()
    headers = ["System", "Mean Word Count", "Accuracy (%)", "Mean Ratio"]
    rows = []
    # Sort by mean word count descending for easy visual comparison
    sorted_names = sorted(system_names, key=lambda n: results[n]["gen_mean"],
                          reverse=True)
    for name in sorted_names:
        r = results[name]
        rows.append([
            name,
            fmt(r["gen_mean"]),
            pct(r["accuracy"]),
            fmt(r["ratio_mean"], 2),
        ])
    alignments = ["l", "r", "r", "r"]
    print_table(headers, rows, alignments)
    print()

    # Compute Spearman-style rank correlation manually (no scipy needed)
    # between mean word count and accuracy across all systems
    wc_vals = [results[n]["gen_mean"] for n in system_names]
    acc_vals = [results[n]["accuracy"] for n in system_names]

    def rank(values):
        """Assign ranks (1-based, average ties) to a list of values."""
        indexed = sorted(enumerate(values), key=lambda x: x[1])
        ranks = [0.0] * len(values)
        i = 0
        while i < len(indexed):
            j = i
            while j < len(indexed) - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1  # 1-based average
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    if len(system_names) >= 3:
        wc_ranks = rank(wc_vals)
        acc_ranks = rank(acc_vals)
        n = len(system_names)
        mean_wc_r = sum(wc_ranks) / n
        mean_acc_r = sum(acc_ranks) / n
        num = sum((wc_ranks[i] - mean_wc_r) * (acc_ranks[i] - mean_acc_r)
                  for i in range(n))
        den_wc = sum((wc_ranks[i] - mean_wc_r) ** 2 for i in range(n)) ** 0.5
        den_acc = sum((acc_ranks[i] - mean_acc_r) ** 2 for i in range(n)) ** 0.5
        if den_wc > 0 and den_acc > 0:
            spearman = num / (den_wc * den_acc)
        else:
            spearman = 0.0

        # Pearson on raw values
        mean_wc = statistics.mean(wc_vals)
        mean_acc = statistics.mean(acc_vals)
        num_p = sum((wc_vals[i] - mean_wc) * (acc_vals[i] - mean_acc)
                    for i in range(n))
        den_wc_p = sum((wc_vals[i] - mean_wc) ** 2 for i in range(n)) ** 0.5
        den_acc_p = sum((acc_vals[i] - mean_acc) ** 2 for i in range(n)) ** 0.5
        if den_wc_p > 0 and den_acc_p > 0:
            pearson = num_p / (den_wc_p * den_acc_p)
        else:
            pearson = 0.0

        print(f"**Pearson r (word count vs. accuracy):** {pearson:.4f}")
        print(f"**Spearman rho (word count vs. accuracy):** {spearman:.4f}")
        print()
        print("_Note: AP baselines are intentionally wrong answers scored by the "
              "same LLM judge. See ap-baseline/ for full methodology._")
        print()


if __name__ == "__main__":
    main()
