# LoCoMo Benchmark Ground Truth Audit

Systematic audit of the [LoCoMo](https://github.com/snap-research/locomo) (Long-Context Modeling) benchmark dataset, identifying errors in ground truth labels that affect evaluation reliability.

## Key Finding

**99 score-corrupting errors in 1,540 questions (6.4%)**: golden answers that are factually wrong, causing the LLM judge to penalize correct systems or reward incorrect ones. An additional 57 citation metadata errors were found but do not affect scoring.

See [AUDIT_REPORT.md](AUDIT_REPORT.md) for full analysis.

## Provenance

| File | Source | SHA256 |
|------|--------|--------|
| `data/locomo10.json` | [`snap-research/locomo`](https://github.com/snap-research/locomo) | `79fa87e9...ea698ff4` |
| `evaluation/config/prompts.yaml` | [`EverMind-AI/EverMemOS`](https://github.com/EverMind-AI/EverMemOS/) | `ba4f668e...ba498ee9` |

Both files are byte-for-byte matches with their official upstream sources (verified Feb 2026). Run `python scripts/verify_sha256.py` to confirm.

## Methodology

Two-pass audit of all 1,540 non-adversarial questions (Categories 1-4) across 10 conversations:

1. **Evidence Check:** Verify that the golden answer is supported by the cited evidence dialog IDs.
2. **Full Transcript Check:** When evidence check fails, search the complete conversation transcript to determine whether the answer is factually wrong or merely miscited.

### Error Classification

| Type | Description | Affects Scoring? |
|------|-------------|:---:|
| `HALLUCINATION` | Golden answer contains facts not present anywhere in the transcript | **Yes** |
| `TEMPORAL_ERROR` | Date/time calculation is incorrect (e.g., "last Saturday" resolved to wrong day) | **Yes** |
| `ATTRIBUTION_ERROR` | Answer attributes statement/action to wrong speaker | **Yes** |
| `INCOMPLETE` | Golden answer omits facts explicitly stated in the transcript | **Yes** |
| `AMBIGUOUS` | Answer is partially correct or debatable | **Maybe** |
| `WRONG_CITATION` | Answer is factually correct but cites the wrong evidence dialog IDs | No |

## Repository Structure

```
locomo-audit/
├── data/
│   └── locomo10.json          # Original dataset (unmodified, SHA256-verified)
├── scripts/
│   └── verify_sha256.py       # Verify dataset integrity against known hash
├── audit/
│   ├── conv_0.json            # Per-conversation audit packages (structured data)
│   ├── errors_conv_0.json     # Errors found per conversation
│   ├── summary_conv_0.txt     # Per-conversation summary
│   └── ...
├── evaluation/
│   └── config/
│       └── prompts.yaml       # Judge prompts (from original EverMemOS pipeline)
├── errors.json                # Consolidated error report (all conversations)
├── AUDIT_REPORT.md            # Full findings and analysis
├── results-audit/             # Score impact analysis across 5 published systems
│   ├── RESULTS_AUDIT.md       # Adjusted scores, ceiling analysis, cross-check
│   ├── audit_results.py       # Audit script (LLM judge, ~1,485 calls)
│   └── download_results.py    # Fetches published eval_results from HuggingFace
├── ap-baseline/               # Judge leniency stress test (two adversarial strategies)
│   ├── README.md              # Overview: strategies, results, 6x leniency finding
│   ├── score_ap.py            # Scoring pipeline (same judge as original eval)
│   ├── v1/                    # Specific-but-wrong strategy (10.61%)
│   └── v2/                    # Vague-but-topical strategy (62.81%)
├── requirements.txt           # Python dependencies (openai, pyyaml)
└── README.md
```

## Results Audit

The `results-audit/` directory measures how these 99 errors actually affected published benchmark scores for 5 memory systems (EverMemOS, Mem0, MemoS, MemU, Zep). For each error-affected question, an LLM judge determines whether the system received an undeserved penalty, undeserved credit, or neither.

See [results-audit/RESULTS_AUDIT.md](results-audit/RESULTS_AUDIT.md) for adjusted scores, per-category breakdowns, ceiling analysis, and published score cross-checks.

## Judge Leniency Stress Test

The `ap-baseline/` directory tests the LLM judge's ability to distinguish correct answers from plausible-sounding wrong ones. A frontier LLM (Claude Opus 4.6) was given the full answer key and asked to generate deliberately wrong answers for all 1,540 questions using two strategies:

- **V1 — Specific-but-wrong (10.61%):** Every core fact shifted to a plausible alternative. "A painting of Aragorn" becomes "a poster of Gandalf." The judge catches these ~89% of the time.
- **V2 — Vague-but-topical (62.81%):** Every answer generalized away from falsifiable specifics. "A painting of Aragorn" becomes "artwork of a fictional character he admires." The judge accepts these ~63% of the time.

Vague answers that stay in the right topical neighborhood fool the judge **6x more often** than specific wrong answers, exploiting the "be generous — as long as it touches on the same topic" instruction. The v2 strategy scores higher than two of the five published memory systems in several categories.

See [ap-baseline/README.md](ap-baseline/README.md) for full results, per-category patterns, and comparison against published system scores.

## Prior Work

This audit builds on errors first reported in [snap-research/locomo#27](https://github.com/snap-research/locomo/issues/27) (29 errors). Our systematic audit found 156 total issues: 99 score-corrupting, 57 citation-only.

## License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), the same license as the underlying LoCoMo dataset.

The LoCoMo dataset was created by Maharana, A., Lee, D. H., Tuber, S., & Bansal, M. and is published by SNAP Research under CC BY-NC 4.0. The unmodified dataset is included in `data/locomo10.json` (SHA256-verified). This repository contains audit annotations and analysis derived from that dataset.
