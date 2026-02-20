# LoCoMo Benchmark Audit

Independent audit of the [LoCoMo](https://github.com/snap-research/locomo) (Long-Context Modeling) benchmark and the [EverMemOS](https://github.com/EverMind-AI/EverMemOS) evaluation framework. Findings cover ground truth errors in the dataset, evaluation methodology differences across implementations, token cost misrepresentation, judge leniency, and third-party reproducibility failures. Every claim links to a verifiable primary source.

## Key Findings

| Finding | Detail | Source |
|---------|--------|--------|
| Ground truth errors | 99 of 1,540 questions (6.4%) have wrong golden answers. Theoretical scoring ceiling is 93.57%. | [AUDIT_REPORT.md](AUDIT_REPORT.md) |
| Total token cost | EverMemOS README claims 2,298 avg tokens per question. The paper's own Table 8 ([arXiv:2601.02163v2](https://arxiv.org/abs/2601.02163)) shows 6,669 with GPT-4.1-mini (2.9x higher; 6,045 with GPT-4o-mini). Real reduction vs. full-context is 67%, not 89%. | [methodology/token_efficiency.md](methodology/token_efficiency.md) |
| Judge accepts wrong answers | 62.81% of intentionally wrong vague-but-topical answers accepted by the LLM judge. | [ap-baseline/README.md](ap-baseline/README.md) |
| Scores exceed corrupted ceiling | EverMemOS single-hop (95.96%) and multi-hop (91.37%) exceed their category ceilings (95.72% and 90.07%), mathematically impossible without credit from wrong golden answers. Overall 92.32% is within 1.25 points of the 93.57% aggregate ceiling. | [results-audit/RESULTS_AUDIT.md](results-audit/RESULTS_AUDIT.md) |
| Not apples-to-apples | EverMemOS uses 2-3 sequential LLM calls, a 729-token CoT prompt, and agentic retrieval. All other systems: 1 call, simple prompt, no overhead. All reported in the same "Avg. Tokens" column. | [methodology/token_efficiency.md](methodology/token_efficiency.md), [methodology/prompts.md](methodology/prompts.md) |
| Reproducibility failures | Third parties report 38.38% vs. claimed 92.32% ([EverMemOS#73](https://github.com/EverMind-AI/EverMemOS/issues/73)). Multiple Mem0 reproducibility issues open. | [methodology/reproducibility.md](methodology/reproducibility.md) |

## Repository Structure

```
locomo-audit/
├── data/
│   └── locomo10.json              # Original dataset (unmodified, SHA256-verified)
├── audit/
│   ├── conv_0.json ... conv_9.json          # Per-conversation audit packages
│   └── errors_conv_0.json ... errors_conv_9.json  # Errors found per conversation
├── results-audit/                 # Score impact analysis across 5 published systems
│   ├── RESULTS_AUDIT.md           # Adjusted scores, ceiling analysis, cross-check
│   ├── audit_results.py           # Audit script (LLM judge, ~1,485 calls)
│   └── download_results.py        # Fetches published eval_results from HuggingFace
├── ap-baseline/                   # Judge leniency stress test
│   ├── README.md                  # Strategies, results, 6x leniency finding
│   ├── score_ap.py                # Scoring pipeline (same judge as original eval)
│   ├── v1/                        # Specific-but-wrong strategy (10.61%)
│   └── v2/                        # Vague-but-topical strategy (62.81%)
├── methodology/                   # Evaluation methodology analysis
│   ├── README.md                  # Overview and key findings
│   ├── prompts.md                 # Answer prompts, judge prompt, context templates
│   ├── word_counts.md             # Answer length statistics and scoring correlation
│   ├── token_efficiency.md        # Token cost claims vs. paper's own data
│   ├── discrepancies.md           # Cross-repository model, prompt, scoring differences
│   ├── full_context_baseline.md   # Full-context baselines and the 18.31-point gap
│   ├── image_questions.md         # Image-dependent questions and BLIP caption handling
│   ├── reproducibility.md         # Third-party reproducibility reports
│   └── scripts/                   # Analysis scripts (stdlib-only Python)
├── evaluation/
│   └── config/
│       └── prompts.yaml           # Judge prompts (from EverMemOS pipeline, SHA256-verified)
├── scripts/
│   └── verify_sha256.py           # Verify dataset integrity against known hashes
├── errors.json                    # Consolidated error report (all conversations)
├── AUDIT_REPORT.md                # Ground truth audit: full findings and analysis
├── requirements.txt               # Python dependencies (openai, pyyaml)
└── README.md
```

## Provenance

| File | Source | License | SHA256 |
|------|--------|---------|--------|
| `data/locomo10.json` | [`snap-research/locomo`](https://github.com/snap-research/locomo) | CC BY-NC 4.0 | `79fa87e9...ea698ff4` |
| `evaluation/config/prompts.yaml` | [`EverMind-AI/EverMemOS`](https://github.com/EverMind-AI/EverMemOS/) | Apache 2.0 | `ba4f668e...ba498ee9` |

Both files are byte-for-byte matches with their official upstream sources (verified Feb 2026). Run `python scripts/verify_sha256.py` to confirm. See [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) for full license attribution.

## Prior Work

This audit builds on errors first reported in [snap-research/locomo#27](https://github.com/snap-research/locomo/issues/27) (29 errors). Our systematic audit found 156 total issues: 99 score-corrupting, 57 citation-only.

## License

This work is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), the same license as the underlying LoCoMo dataset.

The LoCoMo dataset was created by Maharana, A., Lee, D. H., Tuber, S., & Bansal, M. and is published by SNAP Research under CC BY-NC 4.0. The unmodified dataset is included in `data/locomo10.json` (SHA256-verified). This repository contains audit annotations and analysis derived from that dataset.
