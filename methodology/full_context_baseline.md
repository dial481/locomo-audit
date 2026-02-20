<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Full-Context Baseline

A full-context baseline passes the entire conversation history to the LLM, with no retrieval or memory system involved. It establishes the upper bound of what the answer LLM can achieve when given all available information. This document catalogs the known full-context baselines for LoCoMo and their verifiability.

---

## Known Baselines

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

### GPT-4.1-mini (EverMemOS Upstream Claim -- UNVERIFIED)

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

**This number cannot be independently verified.** The following artifacts are absent from the published repository and dataset:

1. **No adapter code:** The EverMemOS adapter registry (`EverMind-AI/EverMemOS/evaluation/src/adapters/registry.py`) lists only: `evermemos`, `mem0`, `memos`, `memu`, `zep`, `evermemos_api`, `memobase`, `supermemory`. There is no `llm`, `full_context`, or `placebo` adapter.

2. **No system config:** The system configs at `EverMind-AI/EverMemOS/evaluation/config/systems/` contain files for `evermemos`, `mem0`, `memos`, `memu`, `zep`, and variants. No `full_context.yaml` exists.

3. **No eval_results.json:** The HuggingFace dataset ([EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results)) contains results for 5 systems only: `evermemos`, `mem0`, `memos`, `memu`, `zep`. There is no `full_context` or `llm` directory. This is confirmed by the download script at `results-audit/download_results.py`, line 13: `SYSTEMS = ["evermemos", "mem0", "memos", "memu", "zep"]`.

### 18.31-Point Gap Between Baselines

The two published full-context baselines differ by 18.31 percentage points:

| Baseline | Model | Overall | Source |
|----------|-------|---------|--------|
| Mem0 paper | GPT-4o-mini | 72.90% | arxiv 2504.19413 |
| EverMemOS claim | GPT-4.1-mini | 91.21% | EverMemOS README |

The model difference (GPT-4o-mini vs GPT-4.1-mini) accounts for some of this gap, but the prompt and judge configuration may also differ. Without the EverMemOS full-context eval_results.json, it is not possible to determine how much of the gap comes from the model upgrade vs. other methodology differences. Independent reports of GPT-4o exceeding the original paper's baselines ([snap-research/locomo#4](https://github.com/snap-research/locomo/issues/4)) further complicate the picture; see [reproducibility.md](reproducibility.md).

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

| Baseline | Model | Score | Adapter Code | eval_results.json | Independently Verifiable |
|----------|-------|-------|-------------|-------------------|------------------------|
| Mem0 paper | GPT-4o-mini | 72.90% | Yes (in mem0 repo) | Not published | Reproducible from code |
| EverMemOS claim | GPT-4.1-mini | 91.21% | Not present | Not published | No |
| EverMemBench LLM | GPT-4.1-mini | Not reported | Yes (different dataset) | Not published | Not applicable to LoCoMo |

The full-context baseline is a critical reference point for evaluating memory systems. If full-context achieves 91.21% and EverMemOS achieves 92.32%, the entire memory system produces a 1.11-point gain. If full-context achieves 72.90% (Mem0's number with GPT-4o-mini), the gain is much larger but the comparison is confounded by the model difference.

No full-context baseline for LoCoMo exists that is both (a) using the same model as the published results and (b) independently verifiable from published artifacts.
