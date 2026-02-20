<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Full-Context Baseline

A full-context baseline passes the entire conversation history to the LLM, with no retrieval or memory system involved. It establishes what the answer LLM can achieve when given all available information. This document catalogs the known full-context baselines for LoCoMo and presents our independently measured results.

---

## Our Measured Baselines

We ran four full-context configurations: two models (GPT-4o-mini, GPT-4.1-mini) x two answer prompts (`answer_prompt_memos`, `answer_prompt_cot`). Each configuration was evaluated with 3 judge runs using GPT-4o-mini, matching the published evaluation methodology. Full details: [fc-baseline/README.md](../fc-baseline/README.md).

### Overall Accuracy

| Model | Prompt | Per-Run Mean | Std Dev | Majority Vote |
|-------|--------|-------------|---------|---------------|
| GPT-4o-mini | `answer_prompt_memos` | 74.29% | 0.05% | 74.35% |
| GPT-4o-mini | `answer_prompt_cot` | 79.89% | 0.12% | 79.94% |
| GPT-4.1-mini | `answer_prompt_memos` | 81.95% | 0.09% | 82.08% |
| GPT-4.1-mini | `answer_prompt_cot` | **92.62%** | 0.13% | 92.66% |

### Per-Category Accuracy (Per-Run Mean)

| Category | N | 4o-mini memos | 4o-mini cot | 4.1-mini memos | 4.1-mini cot | EverMemOS Claim |
|----------|---|---------------|-------------|----------------|--------------|-----------------|
| Single-hop | 841 | 86.52% | 89.10% | 89.66% | 96.51% | 94.93% |
| Multi-hop | 282 | 70.21% | 82.62% | 78.84% | 92.20% | 90.43% |
| Temporal | 321 | 51.09% | 57.32% | 70.51% | 86.29% | 87.95% |
| Open-domain | 96 | 56.60% | 66.67% | 61.81% | 80.90% | 71.88% |

The GPT-4.1-mini CoT configuration exceeds EverMemOS's claimed full-context baseline in every category except temporal (86.29% vs. 87.95%).

### Key Finding: Prompt Explains the Gap

The answer prompt alone accounts for a 10.67-point accuracy difference with the same model and identical context:

| Configuration | Overall |
|---------------|---------|
| GPT-4.1-mini + `answer_prompt_cot` | 92.62% |
| GPT-4.1-mini + `answer_prompt_memos` | 81.95% |
| **Delta (prompt only)** | **+10.67 points** |

The CoT prompt produces answers averaging 67.9 words vs. 4.8 words with the memos prompt. Longer answers provide more surface area for the judge's "be generous, as long as it touches on the same topic" matching. See [prompts.md](prompts.md) and [word_counts.md](word_counts.md).

---

## Published Baselines

### GPT-4o-mini (Mem0 Paper)

| Metric | Value |
|--------|-------|
| Overall | 72.90% +/- 0.19% |
| Source | Mem0 paper (arxiv 2504.19413), Table 2 |
| Model | GPT-4o-mini |
| Code available | Yes |
| Results published | No |

Mem0's evaluation repository contains the code to run a full-context baseline. The `RAGManager` class handles it as a special case with `chunk_size == -1`:

```python
if chunk_size == -1:
    return [documents], []  # entire document, no embeddings
```

Source: `mem0ai/mem0/evaluation/src/rag.py`, line 123

The Makefile provides a target:

```makefile
run-full-context:
    python run_experiments.py --technique_type rag --chunk_size -1 --num_chunks 1
```

Source: `mem0ai/mem0/evaluation/Makefile`, lines 18-19

However, no result files are published in the repository (the `results/` directory is gitignored). The 72.90% figure comes from the paper only.

**Our measurement:** 74.29% (GPT-4o-mini + `answer_prompt_memos`). The 1.39-point gap is small and likely reflects prompt differences between our `answer_prompt_memos` and Mem0's own prompt.

### GPT-4.1-mini (EverMemOS Upstream Claim)

| Metric | Value |
|--------|-------|
| Overall | 91.21% |
| Single-hop | 94.93% |
| Multi-hop | 90.43% |
| Temporal | 87.95% |
| Open-domain | 71.88% |
| Average Tokens | 20,281 |
| Source | [EverMemOS evaluation README](https://github.com/EverMind-AI/EverMemOS/blob/main/evaluation/README.md), line 43 |
| Model | GPT-4.1-mini |
| Code available | No |
| Results published | No |

Footnote from the README (line 50):

> `*Full-context: using the whole conversation as context for answering questions.`

**This number cannot be independently verified from the published artifacts.** The following are absent from the repository and dataset:

1. **No adapter code:** The EverMemOS adapter registry (`EverMind-AI/EverMemOS/evaluation/src/adapters/registry.py`) lists only: `evermemos`, `mem0`, `memos`, `memu`, `zep`, `evermemos_api`, `memobase`, `supermemory`. There is no `llm`, `full_context`, or `placebo` adapter.

2. **No system config:** The system configs at `EverMind-AI/EverMemOS/evaluation/config/systems/` contain files for `evermemos`, `mem0`, `memos`, `memu`, `zep`, and variants. No `full_context.yaml` exists.

3. **No eval_results.json:** The HuggingFace dataset ([EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results)) contains results for 5 systems only: `evermemos`, `mem0`, `memos`, `memu`, `zep`. There is no `full_context` or `llm` directory. This is confirmed by the download script at `results-audit/download_results.py`, line 13: `SYSTEMS = ["evermemos", "mem0", "memos", "memu", "zep"]`.

**Our measurement:** With `answer_prompt_memos` (5-6 word constraint), GPT-4.1-mini scores 81.95% -- 9.26 points below the claim. With `answer_prompt_cot` (the prompt EverMemOS uses for its own system), GPT-4.1-mini scores 92.62% -- 1.41 points above the claim. The most likely explanation is that EverMemOS used `answer_prompt_cot` for their full-context claim. The EverMemOS README does not specify which prompt was used.

### Comparison: Our Results vs. Published Claims

| Baseline | Model | Prompt | Claimed | Measured | Delta |
|----------|-------|--------|---------|----------|-------|
| Mem0 paper | GPT-4o-mini | Not specified | 72.90% | 74.29% (memos) | +1.39 |
| EverMemOS README | GPT-4.1-mini | Not specified | 91.21% | 81.95% (memos) | -9.26 |
| EverMemOS README | GPT-4.1-mini | Not specified | 91.21% | 92.62% (cot) | +1.41 |

---

## Full-Context vs. Published Memory Systems

When the full-context baseline is measured with the same prompt each system uses, every memory system scores at or below full context:

| System | Overall | Answer Prompt | FC Baseline (same prompt) | Delta |
|--------|---------|---------------|---------------------------|-------|
| EverMemOS | 92.32% | `answer_prompt_cot` | 92.62% | -0.30% |
| Zep | 85.22% | `answer_prompt_zep` | N/A (not tested) | -- |
| MemOS | 80.76% | `answer_prompt_memos` | 81.95% | -1.19% |
| MemU | 66.67% | `answer_prompt_memos` | 81.95% | -15.28% |
| Mem0 | 64.20% | `answer_prompt_memos` | 81.95% | -17.75% |

No published memory system exceeds the full-context baseline when compared with the same answer prompt. EverMemOS is 0.30 points below full context. MemOS, MemU, and Mem0 fall further below.

---

## EverMemBench Full-Context Adapter

EverMemBench contains a full-context adapter (`llm_adapter.py`) that passes entire dialogues as context:

```python
class LLMAdapter(BaseAdapter):
    """This adapter does not use any memory system. Instead, it:
    1. Stores the full dialogue dataset during add() (no-op)
    2. Returns the full dialogue as context during search()"""
```

Source: `EverMind-AI/EverMemBench/eval/src/adapters/llm_adapter.py`, lines 23-32

However, this adapter is designed for the **EverMemBench-Dynamic dataset** (multi-person group chat), not for LoCoMo. No published results exist in the EverMemBench repo (the `results/` directory is gitignored).

---

## Zep's Own LoCoMo Evaluation

Zep published LoCoMo evaluation results in `getzep/zep-papers`:

| Metric | Value |
|--------|-------|
| Overall | 75.14% +/- 0.17% |
| Single-hop | 79.79% |
| Multi-hop | 74.11% |
| Open-domain | 66.04% |
| Temporal | 67.71% |

Source: `getzep/zep-papers/kg_architecture_agent_memory/locomo_eval/README.md`

This is Zep's memory system score, not a full-context baseline. The Zep locomo_eval code does not include a full-context or LLM-only baseline test.

---

## Summary

| Baseline | Model | Prompt | Score | Source | Verifiable |
|----------|-------|--------|-------|--------|------------|
| This evaluation | GPT-4o-mini | `answer_prompt_memos` | 74.29% | `fc-baseline/results/gpt-4o-mini-memos/eval_results.json` | Yes |
| This evaluation | GPT-4o-mini | `answer_prompt_cot` | 79.89% | `fc-baseline/results/gpt-4o-mini-cot/eval_results.json` | Yes |
| This evaluation | GPT-4.1-mini | `answer_prompt_memos` | 81.95% | `fc-baseline/results/gpt-4.1-mini-memos/eval_results.json` | Yes |
| This evaluation | GPT-4.1-mini | `answer_prompt_cot` | 92.62% | `fc-baseline/results/gpt-4.1-mini-cot/eval_results.json` | Yes |
| Mem0 paper | GPT-4o-mini | Not specified | 72.90% | arxiv 2504.19413 | Reproducible from code |
| EverMemOS claim | GPT-4.1-mini | Not specified | 91.21% | EverMemOS README | No |
| EverMemBench LLM | GPT-4.1-mini | Not reported | Not reported | Different dataset | Not applicable to LoCoMo |

The full-context baseline is a critical reference point for evaluating memory systems. Our measurements show that the answer prompt is the dominant variable: the same model with the same context scores between 81.95% and 92.62% depending solely on the prompt. When using the same prompt as EverMemOS (`answer_prompt_cot`), full context exceeds EverMemOS's system score (92.62% vs. 92.32%), leaving no measurable accuracy gain from the memory system.
