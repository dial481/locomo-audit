#!/usr/bin/env python3
"""
image_question_analysis.py
==========================
Identifies image-dependent questions in the LoCoMo-10 benchmark and computes
per-system accuracy on those questions.

A question is "truly image-dependent" when its golden answer contains
substantive content words that appear in the BLIP caption of at least one
evidence turn but do not appear anywhere in the conversation text of the
same conversation.

Outputs:
  1. Image content statistics (turn counts, URL counts)
  2. Image-evidence and image-dependent question counts
  3. Per-system accuracy: broad (image-evidence) and narrow (image-dependent)
  4. Full list of image-dependent question IDs with caption-only words

Usage (from repo root):
    python3 methodology/scripts/image_question_analysis.py

Dependencies: standard library only (json, pathlib, sys).
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

LOCOMO_PATH = REPO_ROOT / "data" / "locomo10.json"

SYSTEM_FILES = {
    "EverMemOS": "results-audit/results/evermemos_eval_results.json",
    "Zep":       "results-audit/results/zep_eval_results.json",
    "MemoS":     "results-audit/results/memos_eval_results.json",
    "MemU":      "results-audit/results/memu_eval_results.json",
    "Mem0":      "results-audit/results/mem0_eval_results.json",
}

STOPWORDS = frozenset({
    'a', 'an', 'the', 'is', 'was', 'of', 'in', 'on', 'to', 'and', 'or',
    'for', 'with', 'that', 'this', 'it', 'at', 'by', 'from', 'as', 'be',
    'are', 'were', 'been', 'has', 'had', 'have', 'do', 'does', 'did', 'not',
    'but', 'so', 'if', 'they', 'them', 'their', 'he', 'she', 'his', 'her',
    'we', 'our', 'you', 'your', 'i', 'my', 'me', 'who', 'what', 'where',
    'when', 'how', 'why', 'just', 'also', 'about', 'would', 'could',
    'should', 'can', 'will', 'shall', 'may', 'might', 'its', 'than', 'then',
    'there', 'here', 'some', 'any', 'all', 'each', 'every', 'both', 'few',
    'more', 'most', 'other', 'such', 'no', 'nor', 'too', 'very', 's', 't',
    'd', 'm', 're', 've', 'll', 'out', 'up', 'down', 'off', 'under',
    'after', 'before', 'into', 'over',
    # Generic image terms excluded from matching
    'photo', 'photography', 'picture', 'image', 'shared', 'an',
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tokenize(text):
    """Split text into lowercase words, stripping punctuation."""
    return {
        w.lower().strip('.,!?\'"()[]{}:;')
        for w in str(text).split()
    } - STOPWORDS


def is_judge_approved(judgments):
    """Majority vote: at least 2 of 3 True."""
    if not judgments:
        return False
    return sum(1 for v in judgments.values() if v is True) >= 2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not LOCOMO_PATH.exists():
        print(f"ERROR: {LOCOMO_PATH} not found", file=sys.stderr)
        sys.exit(1)

    with open(LOCOMO_PATH, "r", encoding="utf-8") as f:
        locomo = json.load(f)

    # Build turn lookup and conversation-wide text word sets
    all_turns = {}
    conv_all_text_words = {}
    total_img_turns = 0
    all_urls = set()

    for idx, conv in enumerate(locomo):
        words = set()
        for skey in sorted(conv["conversation"].keys()):
            if not skey.startswith("session_") or skey.endswith("_date_time"):
                continue
            for turn in conv["conversation"][skey]:
                dia_id = turn.get("dia_id", "")
                all_turns[(idx, dia_id)] = turn
                words |= tokenize(turn.get("text", ""))
                urls = turn.get("img_url", [])
                if urls:
                    total_img_turns += 1
                    for u in (urls if isinstance(urls, list) else [urls]):
                        all_urls.add(u)
        # Include observations
        for obs in conv.get("observation", []):
            if isinstance(obs, dict):
                for v in obs.values():
                    if isinstance(v, str):
                        words |= tokenize(v)
        conv_all_text_words[idx] = words

    # Classify questions
    image_evidence_qids = set()
    image_dep_qids = set()
    image_dep_details = []
    total_evaluated = 0

    for idx, conv in enumerate(locomo):
        all_text = conv_all_text_words[idx]
        for qi, qa in enumerate(conv.get("qa", [])):
            if qa["category"] == 5:
                continue
            total_evaluated += 1
            qid = f"locomo_{idx}_qa{qi}"
            gold = str(qa.get("answer", ""))
            gold_words = {w for w in tokenize(gold) if len(w) > 1}

            # Flatten semicolon-separated evidence refs
            flat_ev = []
            for e in qa.get("evidence", []):
                for part in str(e).split(";"):
                    flat_ev.append(part.strip())

            has_img = False
            caption_only = set()
            for ev_ref in flat_ev:
                key = (idx, ev_ref)
                if key not in all_turns:
                    continue
                turn = all_turns[key]
                if not turn.get("img_url"):
                    continue
                has_img = True
                caption_words = tokenize(turn.get("blip_caption", ""))
                co = (gold_words & caption_words) - all_text
                co = {w for w in co if len(w) > 1}
                caption_only |= co

            if has_img:
                image_evidence_qids.add(qid)
            if caption_only:
                image_dep_qids.add(qid)
                image_dep_details.append({
                    "qid": qid, "cat": qa["category"],
                    "q": qa["question"], "gold": gold,
                    "caption_only": caption_only,
                })

    # Print statistics
    print("## Image Content Statistics")
    print()
    print(f"- Image turns: {total_img_turns}")
    print(f"- Unique image URLs: {len(all_urls)}")
    print(f"- Image-evidence QAs (evaluated): {len(image_evidence_qids)}")
    print(f"- Truly image-dependent QAs (evaluated): {len(image_dep_qids)}")
    print()

    # Per-system accuracy
    print("## Per-System Accuracy: Image-Evidence")
    print()
    non_img_count = total_evaluated - len(image_evidence_qids)
    print(f"| System | All ({total_evaluated:,}) | Image-Evidence ({len(image_evidence_qids)})"
          f" | Non-Image ({non_img_count}) | Delta |")
    print("|--------|-------------|---------------------|"
          "------------------|-------|")

    for sname, relpath in SYSTEM_FILES.items():
        spath = REPO_ROOT / relpath
        if not spath.exists():
            continue
        with open(spath, "r", encoding="utf-8") as f:
            sdata = json.load(f)

        all_t = all_c = img_t = img_c = non_t = non_c = 0
        for _user, qlist in sdata["detailed_results"].items():
            for q in qlist:
                if int(q.get("category", 0)) == 5:
                    continue
                qid = q["question_id"]
                correct = is_judge_approved(q.get("llm_judgments", {}))
                all_t += 1
                if correct:
                    all_c += 1
                if qid in image_evidence_qids:
                    img_t += 1
                    if correct:
                        img_c += 1
                else:
                    non_t += 1
                    if correct:
                        non_c += 1

        img_acc = img_c / img_t * 100 if img_t else 0
        non_acc = non_c / non_t * 100 if non_t else 0
        delta = img_acc - non_acc
        print(f"| {sname} | {all_c/all_t*100:.1f}% | {img_acc:.1f}%"
              f" | {non_acc:.1f}% | {delta:+.1f}% |")

    print()
    print(f"## Per-System Accuracy: {len(image_dep_qids)} Truly Image-Dependent")
    print()
    print("| System | Correct | Total | Accuracy |")
    print("|--------|---------|-------|----------|")

    for sname, relpath in SYSTEM_FILES.items():
        spath = REPO_ROOT / relpath
        if not spath.exists():
            continue
        with open(spath, "r", encoding="utf-8") as f:
            sdata = json.load(f)

        dep_t = dep_c = 0
        for _user, qlist in sdata["detailed_results"].items():
            for q in qlist:
                if int(q.get("category", 0)) == 5:
                    continue
                if q["question_id"] not in image_dep_qids:
                    continue
                dep_t += 1
                if is_judge_approved(q.get("llm_judgments", {})):
                    dep_c += 1

        acc = dep_c / dep_t * 100 if dep_t else 0
        print(f"| {sname} | {dep_c} | {dep_t} | {acc:.1f}% |")

    # Full list
    print()
    print(f"## All {len(image_dep_qids)} Truly Image-Dependent Questions")
    print()
    print("| Question ID | Cat | Question | Golden Answer | Caption-Only Words |")
    print("|------------|-----|----------|---------------|-------------------|")
    for d in sorted(image_dep_details, key=lambda x: x["qid"]):
        q_trunc = d["q"][:65] + "..." if len(d["q"]) > 68 else d["q"]
        g_trunc = d["gold"][:60] + "..." if len(d["gold"]) > 63 else d["gold"]
        words = ", ".join(sorted(d["caption_only"]))
        print(f"| `{d['qid']}` | {d['cat']} | {q_trunc} | {g_trunc} | {{{words}}} |")


if __name__ == "__main__":
    main()
