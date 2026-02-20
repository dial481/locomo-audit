<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Methodology Analysis

There is no standardized evaluation methodology across LoCoMo implementations. Each system that reports benchmark scores makes independent choices about answer prompts, judge prompts, context formatting, scoring aggregation, model selection, and category handling. These choices are not interchangeable and directly affect reported scores.

This analysis documents each dimension of variation with exact source file quotes, computed statistics, and cross-repository comparisons. Every claim links to a verifiable primary source.

---

## Sections

| Document | Description |
|----------|-------------|
| [prompts.md](prompts.md) | Side-by-side comparison of answer prompts, judge prompts, context templates, and memory extraction prompts across all implementations |
| [word_counts.md](word_counts.md) | Generated answer word-count statistics, distribution analysis, and correlation between answer length and judge approval rates |
| [token_efficiency.md](token_efficiency.md) | Analysis of claimed vs. actual token costs, including agentic retrieval overhead and the full-context value proposition |
| [discrepancies.md](discrepancies.md) | Cross-repository differences in models, prompts, scoring methods, and category handling |
| [full_context_baseline.md](full_context_baseline.md) | Known full-context baselines, their verifiability, and the 18.31-point gap between published numbers |
| [image_questions.md](image_questions.md) | Identification and analysis of image-dependent questions, BLIP caption handling, and the golden answer/caption mismatch problem |
| [reproducibility.md](reproducibility.md) | Third-party reproducibility failures reported via GitHub issues and external analysis |

---

## Key Findings

### Prompt Variation

Four different answer prompts are used across five systems. Two include a "5-6 words" constraint (Mem0, MemoS/MemU); two do not (EverMemOS, Zep). The EverMemOS prompt mandates a 7-step chain-of-thought structure that produces answers averaging 48.7 words, compared to 4.5 words for Mem0. The Zep prompt includes timestamp interpretation instructions that appear three times across the prompt and template. See [prompts.md](prompts.md).

### Answer Length and Scoring

Systems without word-limit instructions produce answers 10-11x longer than gold answers and score 20-28 points higher than systems with word limits. The correlation between mean word count and accuracy is moderate (Spearman rho = 0.64). The judge's "be generous, as long as it touches on the same topic" instruction creates a systematic advantage for longer answers that provide more surface area for semantic matching. See [word_counts.md](word_counts.md).

### Token Efficiency Claims

The EverMemOS paper's own Table 8 ([arXiv:2601.02163v2](https://arxiv.org/abs/2601.02163), Appendix A.3) reports that Phase III (search + answer) consumes 6,045-6,669 tokens per question -- 2.6-2.9x the "2,298 Average Tokens" figure in the README. The README figure counts only retrieval context; the paper's logged data includes the 729-token CoT prompt template, agentic retrieval overhead (sufficiency check + conditional multi-query generation for 31% of questions), and all completion tokens. The actual reduction vs. full-context is 67.1-70.2%, not the claimed 88.7%. Our independent tiktoken + API estimates (5,190-6,883 tokens per question) are consistent with the paper's data. See [token_efficiency.md](token_efficiency.md).

### Cross-Repository Discrepancies

The original LoCoMo used deterministic F1 scoring with GPT-3.5-turbo. Current implementations use LLM-as-judge with GPT-4o-mini or GPT-4.1-mini (a metadata discrepancy exists in EverMemOS between the README and the published eval_results). EverMemBench uses a different judge model (Gemini 3 Flash Preview) and different prompts. Zep's own evaluation reports 75.14% while EverMemOS's evaluation of Zep reports 85.22%. See [discrepancies.md](discrepancies.md).

### Full-Context Baselines

Two full-context baselines exist: 72.90% (Mem0 paper, GPT-4o-mini, code available but results not published) and 91.21% (EverMemOS claim, GPT-4.1-mini, no code, no results, not independently verifiable). The 18.31-point gap between them cannot be fully explained without the missing artifacts. See [full_context_baseline.md](full_context_baseline.md).

### Image-Dependent Questions

39.4% of evaluated questions (607/1,540) reference evidence turns containing images, but all systems handle images as text BLIP captions only. 32 questions have golden answers containing substantive words found only in BLIP captions and not in conversation text (an upper bound; some word matches may be coincidental). At least 1 golden answer describes an image different from the actual crawled image, making it unanswerable. See [image_questions.md](image_questions.md).

---

## Data Sources

### Files in This Repository

| File | SHA256 | Upstream Source |
|------|--------|---------------|
| `evaluation/config/prompts.yaml` | `ba4f668e72c3fba74a58b8ee56064568fb9c6aae1441e4f0f7a8f5edba498ee9` | [EverMind-AI/EverMemOS](https://github.com/EverMind-AI/EverMemOS/blob/main/evaluation/config/prompts.yaml) (byte-for-byte match) |
| `data/locomo10.json` | `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` | [snap-research/locomo](https://github.com/snap-research/locomo/blob/main/data/locomo10.json) (byte-for-byte match) |
| `results-audit/results/evermemos_eval_results.json` | `e86e7b3ce7f193851eebe44b148ffec8e5546b978b88a559d2376fdaefd7fe2c` | [EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results) |
| `results-audit/results/mem0_eval_results.json` | `7a6b0a8ed63595eb5713f27785e19f79b690e00f4572ca9a665a9d4195fda0d1` | Same HuggingFace dataset |
| `results-audit/results/memos_eval_results.json` | `0dcfab2e5324d28f00f90755a117fc7d908a82630bd7c8c3b39f0494e48dd0eb` | Same HuggingFace dataset |
| `results-audit/results/memu_eval_results.json` | `0878b83891532cd03b28ef45cf73b62f8eb760cedd8d436e4f98a505822ed45a` | Same HuggingFace dataset |
| `results-audit/results/zep_eval_results.json` | `05aecfa20aff6111f1a3ac65fab7eaba4eb362d348d979f22aef3e4c82c86200` | Same HuggingFace dataset |

Verification: `python3 scripts/verify_sha256.py`

### Path Convention

Throughout this analysis, file paths follow two conventions:

- **Paths prefixed with `org/repo/`** (e.g., `snap-research/locomo/task_eval/evaluation.py`) reference files in the external repositories listed below at the pinned commits. These paths map directly to GitHub: `https://github.com/{org}/{repo}/blob/{commit}/{path}`.
- **Paths without a prefix** (e.g., `evaluation/config/prompts.yaml`) are relative to this repository's root.

### External Repositories Referenced

| Repository | Commit / Version | Date | URL |
|-----------|-----------------|------|-----|
| EverMemOS paper | arXiv:2601.02163v2 | 2026-01-09 | [arXiv](https://arxiv.org/abs/2601.02163) |
| EverMind-AI/EverMemOS | `1f2f083d9fd07fd6580064bbdfc7b97da39c47bb` | 2026-02-11 | [GitHub](https://github.com/EverMind-AI/EverMemOS) |
| EverMind-AI/EverMemBench | `e10b3d52f0e4cfc5c124ad406b5d95c59c73738b` | 2026-02-12 | [GitHub](https://github.com/EverMind-AI/EverMemBench) |
| snap-research/locomo | `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` | 2024-08-12 | [GitHub](https://github.com/snap-research/locomo) |
| mem0ai/mem0 | `5a93643f1222800a80f3c34706b71de3ce71234a` | 2026-02-19 | [GitHub](https://github.com/mem0ai/mem0) |
| getzep/zep-papers | `4b7f26cc76cca20743314ba9acb8c2cb6adc42f6` | 2025-07-11 | [GitHub](https://github.com/getzep/zep-papers) |

---

## Scripts

| Script | Description |
|--------|-------------|
| `methodology/scripts/word_count_analysis.py` | Computes word-count statistics across all systems. Standard library only. |
| `methodology/scripts/image_question_analysis.py` | Identifies image-dependent questions and computes per-system accuracy. Standard library only. |

Run from repo root:

```bash
python3 methodology/scripts/word_count_analysis.py
python3 methodology/scripts/image_question_analysis.py
```
