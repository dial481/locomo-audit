#!/usr/bin/env python3
"""Download published LoCoMo eval_results.json files from HuggingFace."""

import json
import sys
import urllib.request
from pathlib import Path

BASE_URL = (
    "https://huggingface.co/datasets/EverMind-AI/"
    "EverMemOS_Eval_Results/resolve/main"
)
SYSTEMS = ["evermemos", "mem0", "memos", "memu", "zep"]
EXPECTED_QUESTIONS = 1540
RESULTS_DIR = Path(__file__).parent / "results"


def flatten_results(data: dict) -> list[dict]:
    """Flatten detailed_results (keyed by user ID) into a flat question list.

    Structure: detailed_results.locomo_exp_user_N[] -> list of question dicts.
    """
    entries = []
    for _user_id, questions in data.get("detailed_results", {}).items():
        entries.extend(questions)
    return entries


def download_system(system: str) -> bool:
    """Download and validate one system's eval_results.json. Returns True on success."""
    url = f"{BASE_URL}/locomo-{system}-full/eval_results.json"
    dest = RESULTS_DIR / f"{system}_eval_results.json"

    print(f"  {system}: downloading from {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "locomo-audit/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"  {system}: FAILED - {e}")
        return False

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  {system}: FAILED - invalid JSON: {e}")
        return False

    # Validate top-level structure
    if "detailed_results" not in data:
        print(f"  {system}: FAILED - missing 'detailed_results' key")
        return False

    # Flatten and validate question count
    entries = flatten_results(data)
    n = len(entries)
    if n != EXPECTED_QUESTIONS:
        print(f"  {system}: WARNING - expected {EXPECTED_QUESTIONS} questions, got {n}")

    # Cross-check against top-level total_questions if present
    top_total = data.get("total_questions")
    if top_total is not None and top_total != n:
        print(f"  {system}: WARNING - total_questions={top_total} but flattened {n} entries")

    # Spot-check required fields
    required = {"question_id", "question", "golden_answer", "generated_answer", "llm_judgments", "category"}
    for entry in entries[:5]:
        missing = required - set(entry.keys())
        if missing:
            print(f"  {system}: WARNING - missing fields in entries: {missing}")
            break

    dest.write_bytes(raw)
    reported_acc = data.get("accuracy")
    acc_str = f"{reported_acc * 100:.2f}%" if isinstance(reported_acc, (int, float)) else "N/A"
    print(f"  {system}: OK - {n} questions, reported accuracy: {acc_str}")
    return True


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading eval results for {len(SYSTEMS)} systems...\n")

    failures = []
    for system in SYSTEMS:
        if not download_system(system):
            failures.append(system)

    print()
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)
    else:
        print(f"All {len(SYSTEMS)} systems downloaded to {RESULTS_DIR}/")


if __name__ == "__main__":
    main()
