<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Third-Party Reproducibility Reports

Independent of this audit, multiple researchers have reported inability to reproduce published LoCoMo evaluation scores. This document collects those reports with primary source links.

---

## EverMemOS: 38.38% vs. Claimed 92.32%

Source: [EverMind-AI/EverMemOS#73](https://github.com/EverMind-AI/EverMemOS/issues/73)

- Reporter: wangyu-ustc
- Claimed score: 92.32% (EverMemOS evaluation README)
- Reproduced score: 38.38% on conversation 26 (152 questions, 419 messages)
- Configuration: gpt-4.1-mini (OpenRouter), Qwen3-Embedding-4B, Qwen3-Reranker-4B, agentic search mode
- A second user (conahpchen) reported the same poor results with the same configuration
- Author response (cyfyifanchen): stated tests worked as expected on their end, directed both reporters to Discord/WeChat for troubleshooting
- Gap: 53.94 percentage points
- Status: open

---

## EverMemOS: Token Metric Questioned

Source: [EverMind-AI/EverMemOS#56](https://github.com/EverMind-AI/EverMemOS/issues/56)

- Reporter: Celina-love-sweet
- Question: Whether the "2,298 Average Tokens" figure represents total token consumption or only the retrieval context used for answering questions
- A commenter (yuwang-xai) confirmed: "2.5k should be the final memory length, rather than the total token consumption"
- This is the same question addressed in [token_efficiency.md](token_efficiency.md): the paper's Table 8 confirms the figure is context-only, with real Phase III cost at 6,045-6,669 tokens per question
- Maintainer response: none
- Status: open

---

## LoCoMo Baselines: GPT-4o vs. Original Paper

Source: [snap-research/locomo#4](https://github.com/snap-research/locomo/issues/4)

- Reporter: wangyu-ustc (same researcher as EverMemOS #73)
- Finding: GPT-4o full-context performance on LoCoMo substantially exceeds the baselines reported in the original LoCoMo paper
- A commenter (caffeinum) referenced the Mem0 evaluation, noting the baseline comparison methodology
- Implication: original paper baselines may have been run with weaker models or different configurations, making memory systems' improvements over baseline appear larger than they are
- This connects to the full-context baseline analysis in [full_context_baseline.md](full_context_baseline.md), where our independently measured baselines show the answer prompt and model choice explain the gap between published claims
- Status: open

---

## Mem0: Multiple Reproducibility Issues

Three open issues in the Mem0 repository document score reproducibility failures:

### Cannot Reproduce Platform Scores ([mem0ai/mem0#3944](https://github.com/mem0ai/mem0/issues/3944))

- Reporter: Donghua-Cai
- Ran the evaluation script using the Mem0 platform (MEM0_API_KEY) with GPT-4o-mini
- Observed LLM score around 0.20 (~20%)
- Root cause identified: the Mem0 platform stores memories using the current date/time instead of the timestamps provided in the LoCoMo dataset, producing incorrect temporal memories
- Example: a question about "7 May 2023" produced a memory referencing "January 2026"
- Status: open

### Cannot Reproduce Locally ([mem0ai/mem0#2800](https://github.com/mem0ai/mem0/issues/2800))

- Reporter: NITHISHM2410
- Attempted to reproduce LoCoMo scores using the local `Memory` class instead of the `MemoryClient` platform API
- Replaced platform API calls in the evaluation code with local equivalents
- Could not reproduce published scores
- Status: open

### A-Mem Baseline Mismatch ([mem0ai/mem0#4003](https://github.com/mem0ai/mem0/issues/4003))

- Reporter: onford
- The A-Mem baseline numbers in Mem0's paper (arxiv 2504.19413, Table 1) do not match the numbers published in the original A-Mem paper
- F1 and BLEU-1 scores for specific question types differ between the two papers
- Status: open

---

## Zep: Category 5 Scoring Bug

Source: [getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5)

- Reporter: deshraj (Mem0 CTO)
- Zep's original LoCoMo evaluation included Category 5 (adversarial) answers in the numerator while excluding Category 5 from the denominator, inflating the reported score
- Zep (danielchalef) acknowledged the error and published the corrected score: 75.14% +/- 0.17% (over 10 runs)
- Status: closed

Already documented in [discrepancies.md](discrepancies.md), Section 4 ("Zep Category 5 Score Inflation"). Included here for completeness.

---

## External Coverage

- Calvin Ku, Medium: ["Emergence AI Broke the Agent Memory Benchmark. I Tried to Break Their Code."](https://medium.com/asymptotic-spaghetti-integration/emergence-ai-broke-the-agent-memory-benchmark-i-tried-to-break-their-code-23b9751ded97) Identified hardcoded k=42 in Emergence AI's evaluation and LoCoMo benchmark design issues.
- Hacker News discussion ([item 44883133](https://news.ycombinator.com/item?id=44883133)): "AI Startup Caught Cheating on Benchmark Papers." Discussion of Mem0's benchmark methodology and alleged misimplementation of competitor systems.
