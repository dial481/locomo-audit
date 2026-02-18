# LoCoMo Benchmark Ground Truth Audit

Systematic audit of the [LoCoMo](https://github.com/snap-research/locomo) (Long-Context Modeling) benchmark dataset, identifying errors in ground truth labels that affect evaluation reliability.

## Key Finding

**99 score-corrupting errors in 1,540 questions (6.4%)**: golden answers that are factually wrong, causing the LLM judge to penalize correct systems or reward incorrect ones. An additional 57 citation metadata errors were found but do not affect scoring.

See [AUDIT_REPORT.md](AUDIT_REPORT.md) for full analysis.

## Provenance

- **Source:** `snap-research/locomo/data/locomo10.json`
- **SHA256:** `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- **Verified:** Byte-for-byte match with official repository (Feb 2026)

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
│   ├── ...
│   ├── errors_conv_0.json     # Errors found per conversation
│   ├── ...
│   ├── summary_conv_0.txt     # Per-conversation summary
│   └── ...
├── errors.json                # Consolidated error report (all conversations)
├── AUDIT_REPORT.md            # Full findings and analysis
└── README.md
```

## Prior Work

This audit builds on errors first reported in [snap-research/locomo#27](https://github.com/snap-research/locomo/issues/27) (29 errors). Our systematic audit found 156 total issues: 99 score-corrupting, 57 citation-only.

## License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), the same license as the underlying LoCoMo dataset.

The LoCoMo dataset was created by Maharana, A., Lee, D. H., Tuber, S., & Bansal, M. and is published by SNAP Research under CC BY-NC 4.0. The unmodified dataset is included in `data/locomo10.json` (SHA256-verified). This repository contains audit annotations and analysis derived from that dataset.
