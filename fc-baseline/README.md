<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Full-Context Baseline Evaluation

Independent full-context baseline evaluation for LoCoMo-10. The LLM receives the entire conversation as context with no retrieval, no memory system, and no reranking. This establishes what the answer model can achieve when given all available information.

Four runs: two models (GPT-4o-mini, GPT-4.1-mini) x two answer prompts (`answer_prompt_memos` with 5-6 word constraint, `answer_prompt_cot` with 7-step chain-of-thought and no word limit).

---

## Key Finding

**The answer prompt accounts for the gap between our baseline and EverMemOS's claimed 91.21%.**

GPT-4.1-mini with `answer_prompt_cot` (the same prompt EverMemOS uses for its own system) achieves **92.66%** on full context alone -- exceeding both EverMemOS's claimed full-context baseline (91.21%) and their published system score (92.32%). No memory system is involved.

| Configuration | Overall | Answer Prompt |
|---------------|---------|---------------|
| FC Baseline (ours, GPT-4.1-mini, CoT) | **92.66%** | `answer_prompt_cot` (no word limit) |
| EverMemOS system | 92.32% | `answer_prompt_cot` (no word limit) |
| FC Baseline (EverMemOS claim) | 91.21% | Not specified |
| FC Baseline (ours, GPT-4.1-mini, memos) | 82.08% | `answer_prompt_memos` (5-6 words) |

The CoT prompt produces answers averaging 67.9 words (GPT-4.1-mini) vs. 4.8 words with the memos prompt. Longer answers provide more surface area for the judge's "be generous, as long as it touches on the same topic" matching. See [methodology/prompts.md](../methodology/prompts.md) and [methodology/word_counts.md](../methodology/word_counts.md).

---

## Results

### Overall Accuracy

| Model | Prompt | Per-Run Mean | Std Dev | Majority Vote | Run 1 | Run 2 | Run 3 |
|-------|--------|-------------|---------|---------------|-------|-------|-------|
| GPT-4o-mini | memos | 74.29% | 0.05% | 74.35% | 74.22% | 74.29% | 74.35% |
| GPT-4o-mini | cot | 79.89% | 0.12% | 79.94% | 79.81% | 79.81% | 80.06% |
| GPT-4.1-mini | memos | 81.95% | 0.09% | 82.08% | 81.82% | 82.01% | 82.01% |
| GPT-4.1-mini | cot | 92.62% | 0.13% | 92.66% | 92.60% | 92.47% | 92.79% |

Published claims for comparison:

| Source | Model | Claimed Overall |
|--------|-------|----------------|
| EverMemOS README (unverified) | GPT-4.1-mini | 91.21% |
| Mem0 paper (arxiv 2504.19413) | GPT-4o-mini | 72.90% +/- 0.19% |

Our GPT-4o-mini memos result (74.35%) is 1.45 points above Mem0's claim (72.90%). This gap is small and may reflect prompt differences.

Our GPT-4.1-mini memos result (82.08%) is 9.13 points below EverMemOS's claim (91.21%). The CoT run (92.66%) exceeds it by 1.45 points. The most likely explanation: EverMemOS used `answer_prompt_cot` for their full-context claim, not `answer_prompt_memos`.

### Per-Category Accuracy (Per-Run Mean)

| Category | N | 4o-mini memos | 4o-mini cot | 4.1-mini memos | 4.1-mini cot | EverMemOS Claim |
|----------|---|---------------|-------------|----------------|--------------|-----------------|
| Single-hop | 841 | 86.52% +/- 0.15% | 89.10% +/- 0.06% | 89.66% +/- 0.10% | 96.51% +/- 0.11% | 94.93% |
| Multi-hop | 282 | 70.21% +/- 0.29% | 82.62% +/- 0.50% | 78.84% +/- 0.44% | 92.20% +/- 0.00% | 90.43% |
| Temporal | 321 | 51.09% +/- 0.25% | 57.32% +/- 0.00% | 70.51% +/- 0.15% | 86.29% +/- 0.25% | 87.95% |
| Open-domain | 96 | 56.60% +/- 0.49% | 66.67% +/- 0.00% | 61.81% +/- 0.49% | 80.90% +/- 0.49% | 71.88% |

The GPT-4.1-mini CoT run exceeds the EverMemOS claim in every category except temporal (86.29% vs. 87.95%, a 1.66-point difference).

### Full-Context vs. Published System Scores

All scores are majority-vote accuracy on 1,540 questions (category 5 excluded).

| System | Overall | Delta from FC (CoT) | Answer Prompt |
|--------|---------|---------------------|---------------|
| FC Baseline (ours, GPT-4.1-mini, CoT) | 92.66% | 0.00% | `answer_prompt_cot` |
| EverMemOS | 92.32% | -0.34% | `answer_prompt_cot` |
| Zep | 85.22% | -7.44% | `answer_prompt_zep` |
| FC Baseline (ours, GPT-4.1-mini, memos) | 82.08% | -10.58% | `answer_prompt_memos` |
| MemOS | 80.76% | -11.90% | `answer_prompt_memos` |
| FC Baseline (EverMemOS claim) | 91.21% | -1.45% | Not specified |
| MemU | 66.67% | -25.99% | `answer_prompt_memos` |
| Mem0 | 64.20% | -28.46% | `answer_prompt_memos` |

When using the same prompt (`answer_prompt_cot`), full context alone (92.66%) exceeds EverMemOS (92.32%) by 0.34 points. The memory system provides no measurable accuracy gain over full context.

Systems using prompts with the 5-6 word constraint (`answer_prompt_memos`) all score at or below our GPT-4.1-mini memos baseline (82.08%), consistent with the answer prompt being the primary variable.

### Token and Word Count Statistics

| Metric | 4o-mini memos | 4o-mini cot | 4.1-mini memos | 4.1-mini cot |
|--------|---------------|-------------|----------------|--------------|
| Mean prompt tokens (API) | 24,602 | 24,906 | 24,602 | 24,906 |
| Mean completion tokens | 7.2 | 548.9 | 7.5 | 857.9 |
| Mean context words | 16,648 | 16,648 | 16,648 | 16,648 |
| Mean answer words | 5.0 | 33.7 | 4.8 | 67.9 |
| Median answer words | 4.0 | 23.0 | 4.0 | 42.0 |

EverMemOS claims 20,281 "Average Tokens" for full-context. Our mean context is 16,648 words, which at ~1.3 tokens per word is approximately 21,642 tokens -- consistent with their figure. Our API-reported prompt token count of 24,602-24,906 per question is higher because it includes the answer prompt template (~3,000 tokens of overhead beyond the raw context).

The CoT prompt generates substantially more completion tokens (549-858 per question vs. 7.2-7.5 with memos). These completion tokens are not reflected in any published "Average Tokens" figure.

---

## Prompt Differences

This evaluation uses two answer prompts from `EverMind-AI/EverMemOS/evaluation/config/prompts.yaml`:

**`answer_prompt_memos`** (used for MemOS and MemU in published evaluations):
- Includes the instruction: "The answer must be brief (under 5-6 words) and direct, with no extra description."
- Produces answers averaging 4.8-5.0 words.

**`answer_prompt_cot`** (used for EverMemOS in published evaluations):
- Mandates a 7-step chain-of-thought structure (RELEVANT MEMORIES EXTRACTION through FINAL ANSWER).
- Includes no word-count constraint.
- Produces answers averaging 33.7-67.9 words (model-dependent).

The EverMemOS README does not specify which prompt was used for the 91.21% full-context claim. The prompt difference is significant because:

1. Answers constrained to 5-6 words provide less surface area for the judge's "be generous, as long as it touches on the same topic" matching (see [methodology/prompts.md](../methodology/prompts.md))
2. The CoT prompt produces answers averaging 67.9 words (GPT-4.1-mini) vs. 4.8 words with `answer_prompt_memos`
3. The prompt alone accounts for a 10.58-point accuracy difference (82.08% vs. 92.66%) with the same model and identical context
4. Systems using the CoT prompt or no word limit consistently score higher than systems using the 5-6 word constraint, independent of the underlying retrieval system

---

## Configuration

| Component | Value | Source |
|-----------|-------|--------|
| Answer prompt (memos runs) | `answer_prompt_memos` | `evaluation/config/prompts.yaml` (SHA256: `ba4f668e`) |
| Answer prompt (cot runs) | `answer_prompt_cot` | `evaluation/config/prompts.yaml` |
| Judge prompt | `llm_judge` system + user | `evaluation/config/prompts.yaml` |
| Judge model | GPT-4o-mini | Matches `EverMind-AI/EverMemOS/evaluation/config/datasets/locomo.yaml` |
| Judge runs | 3 | Matches published results (3 judgments per question) |
| Category 5 | Excluded | Matches published evaluations |
| Data file | `data/locomo10.json` | SHA256: `79fa87e9` (byte-for-byte match with upstream) |
| API routing | OpenRouter (`https://openrouter.ai/api/v1`) | |

### Context Formatting

The full conversation is formatted chronologically, grouped by session:

```
=== Session 1 (1:56 pm on 8 May, 2023) ===
[13:56:00] Caroline: Hey Mel! Good to see you! How have you been?
[13:56:30] Melanie: Hey Caroline! Good to see you! I'm swamped with the kids & work...
...

=== Session 2 (1:14 pm on 25 May, 2023) ===
...
```

This approach is inspired by `EverMind-AI/EverMemBench/eval/src/adapters/llm_adapter.py`, which passes the full dialogue as context with no retrieval. EverMemBench formats group chat days as `=== Date: YYYY-MM-DD === / [Group N] / [HH:MM:SS] Speaker: Content`. Our format adapts this for LoCoMo's 2-speaker session-based structure.

The formatted context is passed directly into the `{context}` placeholder of the answer prompt. No per-speaker separation is applied because the entire conversation contains both speakers.

---

## Code Attribution

`scripts/fc_eval.py` is a standalone script that ports minimal logic from two upstream repositories:

| Component | Source | Ported Functions |
|-----------|--------|-----------------|
| Data loading | `EverMind-AI/EverMemOS/evaluation/src/core/loaders.py` | `load_locomo_dataset()`, `_convert_locomo_conversation()`, `_convert_locomo_qa_pair()`, `_parse_locomo_timestamp()` |
| Data models | `EverMind-AI/EverMemOS/evaluation/src/core/data_models.py` | `Message`, `Conversation`, `QAPair`, `Dataset` dataclasses |
| Full-context concept | `EverMind-AI/EverMemBench/eval/src/adapters/llm_adapter.py` | `_format_dialogue_as_context()` approach (adapted for LoCoMo) |
| Answer generation | `EverMind-AI/EverMemOS/evaluation/src/adapters/online_base.py` | `answer()` method (lines 554-592): prompt formatting, "FINAL ANSWER:" stripping |
| Judge logic | `EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py` | `_judge_answer()`, `_extract_json()`: 3-run evaluation, JSON extraction, majority vote |

Each ported function includes an attribution comment with the source file path and line numbers.

---

## Reproduction

### Prerequisites

- Python 3.10+
- `openai` and `pyyaml` packages
- An OpenAI-compatible API key (OpenRouter, OpenAI, etc.)

### Run

```bash
# Set API key
export OPENROUTER_API_KEY="sk-..."  # or OPENAI_API_KEY or LLM_API_KEY

# GPT-4o-mini + memos prompt
python3 fc-baseline/scripts/fc_eval.py \
  --answer-model gpt-4o-mini \
  --judge-model gpt-4o-mini \
  --answer-prompt answer_prompt_memos \
  --base-url https://openrouter.ai/api/v1 \
  --output-dir fc-baseline/results/gpt-4o-mini-memos \
  --num-judge-runs 3

# GPT-4o-mini + CoT prompt
python3 fc-baseline/scripts/fc_eval.py \
  --answer-model gpt-4o-mini \
  --judge-model gpt-4o-mini \
  --answer-prompt answer_prompt_cot \
  --base-url https://openrouter.ai/api/v1 \
  --output-dir fc-baseline/results/gpt-4o-mini-cot \
  --num-judge-runs 3

# GPT-4.1-mini + memos prompt
python3 fc-baseline/scripts/fc_eval.py \
  --answer-model gpt-4.1-mini \
  --judge-model gpt-4o-mini \
  --answer-prompt answer_prompt_memos \
  --base-url https://openrouter.ai/api/v1 \
  --output-dir fc-baseline/results/gpt-4.1-mini-memos \
  --num-judge-runs 3

# GPT-4.1-mini + CoT prompt
python3 fc-baseline/scripts/fc_eval.py \
  --answer-model gpt-4.1-mini \
  --judge-model gpt-4o-mini \
  --answer-prompt answer_prompt_cot \
  --base-url https://openrouter.ai/api/v1 \
  --output-dir fc-baseline/results/gpt-4.1-mini-cot \
  --num-judge-runs 3

# Analysis
python3 fc-baseline/scripts/analyze_results.py
```

The script supports checkpointing for answer generation: if interrupted during Stage 1 (answer generation), re-run the same command to resume from the last saved checkpoint. Stage 2 (judge evaluation) is not checkpointed and will re-run from scratch.

### Output Files

| File | Description |
|------|-------------|
| `eval_results.json` | Judge verdicts in the same format as published EverMemOS evaluation results |
| `answer_results.json` | Generated answers with `formatted_context` and API-reported token counts |

The `answer_results.json` files (~141MB each, containing full conversation context for all 1,540 questions) are not stored in this repository. They will be published on HuggingFace alongside the public release.

---

## Result Integrity

| File | SHA256 |
|------|--------|
| `results/gpt-4o-mini-memos/eval_results.json` | `c1a89b6e0d33baccb6dff5c455f0c4399758c7871db864b81a4d06e2124f1388` |
| `results/gpt-4o-mini-cot/eval_results.json` | `acb41ed0c1386152436a8ab0c37d560fd9be1afcdc68e55aef2723c6dc7fc1f3` |
| `results/gpt-4.1-mini-memos/eval_results.json` | `8f25b819a845caa4381d60d3f4893f8f939f832513fd0760ca4b3cde3873d55f` |
| `results/gpt-4.1-mini-cot/eval_results.json` | `8636f84251a73126af020ccf278c52df5fa817a6ec184a57e44789f1a1b9dbf1` |

---

## Files

| File | Description |
|------|-------------|
| `scripts/fc_eval.py` | Standalone evaluation script (~860 lines) |
| `scripts/analyze_results.py` | Analysis script (standard library only) |
| `results/gpt-4o-mini-memos/eval_results.json` | GPT-4o-mini + memos prompt: judge verdicts (1,540 questions, 3 runs) |
| `results/gpt-4o-mini-cot/eval_results.json` | GPT-4o-mini + CoT prompt: judge verdicts (1,540 questions, 3 runs) |
| `results/gpt-4.1-mini-memos/eval_results.json` | GPT-4.1-mini + memos prompt: judge verdicts (1,540 questions, 3 runs) |
| `results/gpt-4.1-mini-cot/eval_results.json` | GPT-4.1-mini + CoT prompt: judge verdicts (1,540 questions, 3 runs) |
