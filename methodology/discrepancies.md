<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Cross-Repository Discrepancies

Multiple independent implementations of LoCoMo evaluation exist across different repositories. Each makes different choices about models, prompts, scoring methods, and category handling. This document catalogs the observable differences with exact file paths and quotes.

---

## 1. Model Differences

| Implementation | Answer LLM | Judge | Source |
|---------------|-----------|-------|--------|
| Original LoCoMo | gpt-3.5-turbo / gpt-4 | None (F1/EM/BERT) | `snap-research/locomo/global_methods.py:108-128` |
| EverMemOS (published results) | gpt-4o-mini | gpt-4o-mini | `results-audit/results/evermemos_eval_results.json` metadata |
| EverMemOS (README table) | gpt-4.1-mini | gpt-4o-mini | `EverMind-AI/EverMemOS/evaluation/README.md:39-49`, `config/datasets/locomo.yaml:22-24` |
| EverMemBench | gpt-4.1-mini | gemini-3-flash-preview | `EverMind-AI/EverMemBench/eval/config/pipeline.yaml:6-7,16-17` |
| Mem0 (own repo) | gpt-4o-mini (env var) | gpt-4o-mini | `mem0ai/mem0/evaluation/README.md:68`, `metrics/llm_judge.py:42` |
| Zep (locomo_eval) | gpt-4o-mini | gpt-4o-mini | `getzep/zep-papers/.../zep_locomo_responses.py:62-64`, `zep_locomo_eval.py:51-53` |
| Zep (Test Harness) | gpt-4.1-mini | gpt-4.1-mini | `getzep/zep-papers/.../Zep Test Harness/zep_responses.py:61-63`, `zep_eval.py:39-41` |

### Discrepancy: EverMemOS README vs. Published eval_results.json

The EverMemOS README table lists `gpt-4.1-mini` as the Answer LLM for all systems. However, the metadata in the published `eval_results.json` (from HuggingFace) records `"model": "gpt-4o-mini"`. These are different models. Either:

- The README reflects a more recent evaluation run that was not uploaded to HuggingFace, or
- The README was updated without re-running the evaluation

The published scores that this audit analyzes come from the HuggingFace dataset and were generated with `gpt-4o-mini`.

Source: `results-audit/results/evermemos_eval_results.json`, metadata field

### Original LoCoMo: No LLM Judge

The original LoCoMo evaluation (`snap-research/locomo`) uses no LLM judge at all. Scoring is purely metric-based:

```python
def f1_score(prediction, ground_truth):
    prediction_tokens = [ps.stem(w) for w in normalize_answer(prediction).split()]
    ground_truth_tokens = [ps.stem(w) for w in normalize_answer(ground_truth).split()]
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    ...
```

Source: `snap-research/locomo/task_eval/evaluation.py`, lines 126-145

The shift from deterministic F1 scoring to LLM-as-judge was introduced by later implementations and is itself a significant methodology change.

---

## 2. Prompt Differences

### EverMemOS vs. EverMemBench

The two repos serve different purposes (see Section 6) and use different prompts:

| Feature | EverMemOS | EverMemBench |
|---------|----------|-------------|
| Answer prompts | 4 system-specific variants (mem0, memos, cot, zep) | 2 question-type variants (multiple_choice, open_ended) |
| Domain | "two speakers in a conversation" | "multi-person group chat" |
| Judge "be generous" | Yes: "as long as it touches on the same topic" | No: "as long as it contains the same key information" |
| Timezone tolerance | Not mentioned | "+/- 1 day difference is acceptable due to timezone processing variations" |
| Multiple choice | Not supported | Exact letter match required (A/B/C/D) |
| Full-context prompt | Not present | Present (`llm_answer.multiple_choice`, `llm_answer.open_ended`) |

Sources: `EverMind-AI/EverMemOS/evaluation/config/prompts.yaml`, `EverMind-AI/EverMemBench/eval/config/prompts.yaml`

The EverMemOS README states (line 33):

> "each memory system uses its own official answer prompts rather than a unified prompt template, ensuring fair evaluation of each system's intended usage."

### Zep's Own Prompts vs. EverMemOS's Zep Prompt

Zep published its own LoCoMo evaluation code in `getzep/zep-papers`. The answer prompt structure is similar to the one in EverMemOS's `prompts.yaml`, but with differences:

| Feature | EverMemOS version | Zep original |
|---------|------------------|--------------|
| Timestamp example format | `FACT (event_time: 2023-03-15T16:33:00Z):` | `(2023-03-15T16:33:00Z)` |
| Context template comments | `#` prefixed | Plain text |
| Judge prompt artifacts | Clean | Contains `"williolw23"` debugging text (line 26) |

Sources: `getzep/zep-papers/kg_architecture_agent_memory/locomo_eval/zep_locomo_responses.py:20-59`, `zep_locomo_eval.py:25-48`

Zep also has a second evaluation harness (`Zep Test Harness/`) for a different dataset ("Rivian") that uses a **completely different judge prompt**:

```
I will give you a question, a correct answer, and a response from a model.
Please answer yes if the response contains the correct answer. Otherwise,
answer no. If the response is equivalent to the correct answer or contains
all the intermediate steps to get the correct answer, you should also answer
yes. If the response only contains a subset of the information required by
the answer, answer no.
```

Source: `getzep/zep-papers/kg_architecture_agent_memory/Zep Test Harness/zep_eval.py:25-37`

This prompt does **not** contain the "be generous" or "touches on the same topic" language. It uses yes/no instead of CORRECT/WRONG.

---

## 3. Scoring Differences

| Implementation | Method | Runs | Aggregation |
|---------------|--------|------|-------------|
| Original LoCoMo | Token F1 + Exact Match | 1 | Deterministic |
| EverMemOS | LLM judge | 3 | Per-run accuracy, then mean +/- std |
| EverMemBench | LLM judge | 1 (default) | Majority vote |
| Mem0 (own repo) | LLM judge | 1 | Single binary score |
| Zep (locomo_eval) | LLM judge | 1 | Single binary score |

### EverMemOS: Per-Run Averaging

The EverMemOS evaluation runs the LLM judge 3 times per question, then computes accuracy **for each run separately** and takes the mean:

```python
for i in range(self.num_runs):
    judgment_key = f"judgment_{i+1}"
    correct_count = sum(1 for r in detailed_results
                        if r["llm_judgments"].get(judgment_key))
    run_accuracy = correct_count / total_count
    run_scores.append(run_accuracy)
mean_accuracy = np.mean(run_scores)
std_accuracy = np.std(run_scores)
```

Source: `EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py`, lines 78-110

The docstring confirms: `"Keep independent judgments for each run (judgment_1, judgment_2, judgment_3). Calculate accuracy for each run separately. Output mean and std."`

Source: `EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py`, lines 1-8

Number of runs configured:
- `EverMind-AI/EverMemOS/evaluation/config/datasets/locomo.yaml`, line 26: `num_runs: 3`
- `EverMind-AI/EverMemOS/evaluation/src/adapters/evermemos/stage5_eval.py`, line 156: `num_runs = 3`

### EverMemBench: Majority Vote

EverMemBench uses majority vote for individual questions:

```python
async def _evaluate_oe_single(self, result):
    judgments = []
    for _ in range(self.num_runs):
        is_correct = await self._call_llm_judge_with_retry(...)
        judgments.append(is_correct)
    return sum(judgments) > len(judgments) / 2
```

Source: `EverMind-AI/EverMemBench/eval/src/core/evaluator.py`, lines 358-369

Default `num_runs` is 1 (line 40), making the majority vote effectively a single judge call.

### Practical Impact

Per-run averaging and majority vote yield similar overall numbers at the aggregate level. This audit uses majority vote for per-question analysis (to get a binary correct/wrong per question), which is noted in [results-audit/RESULTS_AUDIT.md](../results-audit/RESULTS_AUDIT.md). The published scores (EverMemOS at 92.32%) use per-run averaging and are reproduced exactly in the cross-check table.

---

## 4. Category Handling

### Category ID Mapping

| ID | Category | Questions |
|----|----------|-----------|
| 1 | Multi-hop | 282 |
| 2 | Temporal | 321 |
| 3 | Open-domain | 96 |
| 4 | Single-hop | 841 |
| 5 | Adversarial | 446 |

Source: `snap-research/locomo/task_eval/evaluation.py`, lines 203-224; `evaluation_stats.py`, line 98 (print order: `keys = [4, 1, 2, 3, 5]`)

### Category 5 Exclusion

All implementations except the original LoCoMo exclude category 5 from scoring:

| Implementation | Category 5 Handling | Source |
|---------------|-------------------|--------|
| Original LoCoMo | **Included** (binary: check for "not mentioned" keyword) | `snap-research/locomo/task_eval/evaluation.py:217-221` |
| EverMemOS | Filtered out via config | `EverMind-AI/EverMemOS/evaluation/config/datasets/locomo.yaml:30`: `filter_category: [5]` |
| Mem0 | Skipped in eval loop | `mem0ai/mem0/evaluation/evals.py:22-24`: `if category == "5": continue` |
| Zep (locomo_eval) | Filtered before search and response | `getzep/zep-papers/.../zep_locomo_responses.py:103`, `zep_locomo_search.py:63-64` |

### Why Category 5 Is Excluded

The original LoCoMo benchmark formats category 5 questions as multiple choice: `"Select the correct answer: (a) Not mentioned in the conversation (b) [answer]"`. The correct response for adversarial questions is always "Not mentioned in the conversation."

Memory systems are not designed to handle this format. The category 5 evaluation in the original LoCoMo checks only whether the output contains the phrase "no information available" or "not mentioned," which is a keyword check rather than semantic evaluation. Later implementations dropped category 5 because:

1. Memory systems are not designed to recognize when information is absent from their stored memories
2. The keyword-based evaluation does not align with the LLM-as-judge methodology used for other categories
3. The multiple-choice format is incompatible with the open-ended answer prompts

The exclusion is documented but the implications are significant: 446 of 1,986 total questions (22.5%) are dropped from evaluation. A comprehensive evaluation methodology would need to address adversarial robustness separately.

### Zep Category 5 Score Inflation

The commit history in getzep/zep-papers (`fix category mapping`) and [GitHub issue #5](https://github.com/getzep/zep-papers/issues/5) (filed by Mem0's CTO) document a category handling correction. Zep's original evaluation included Category 5 answers in the numerator while excluding Category 5 from the denominator, inflating the reported score. Zep's corrected locomo_eval code reports 75.14% overall (with category 5 excluded).

Source: `getzep/zep-papers/kg_architecture_agent_memory/locomo_eval/README.md`, [getzep/zep-papers#5](https://github.com/getzep/zep-papers/issues/5). See also [reproducibility.md](reproducibility.md) for additional third-party reproducibility reports across all systems.

The Zep Test Harness (`getzep/zep-papers/kg_architecture_agent_memory/Zep Test Harness/`) is a separate evaluation on a different dataset (not LoCoMo) and is not relevant to this discrepancy.

---

## 5. Published Results Discrepancies

### Zep Scores: Three Different Numbers

| Source | Overall | Model | Judge | Note |
|--------|---------|-------|-------|------|
| Zep locomo_eval | 75.14% | gpt-4o-mini | gpt-4o-mini | Zep's own evaluation |
| EverMemOS results (HuggingFace) | 85.22% | gpt-4o-mini | gpt-4o-mini | EverMemOS evaluation of Zep |
| EverMemOS README table | 85.22% | gpt-4.1-mini | gpt-4o-mini | README (model discrepancy) |

Sources: `getzep/zep-papers/.../locomo_eval/README.md`, `results-audit/results/zep_eval_results.json`, `EverMind-AI/EverMemOS/evaluation/README.md`

The 10-point gap between Zep's own evaluation (75.14%) and EverMemOS's evaluation of Zep (85.22%) may reflect different Zep API versions, different retrieval configurations, or different evaluation dates. The EverMemOS README notes version information: `"web API/v3 (2025.11)"` for Zep.

---

## 6. Why Two Repos Exist

| Aspect | EverMemOS (`EverMind-AI/EverMemOS`) | EverMemBench (`EverMind-AI/EverMemBench`) |
|--------|-------------------------------------|------------------------------------------|
| Purpose | Full memory OS product + evaluation framework | Standalone benchmark |
| Dataset | LoCoMo, LongMemEval, PersonaMem (2-person) | EverMemBench-Dynamic (multi-person group chat) |
| HuggingFace dataset | [EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results) | [EverMind-AI/EverMemBench-Dynamic](https://huggingface.co/datasets/EverMind-AI/EverMemBench-Dynamic) |
| Systems tested | EverMemOS, Mem0, MemoS, MemU, Zep | EverMemOS, Mem0, MemoS, Memobase, Zep + LLM |
| Full-context adapter | Not present | Present (`llm_adapter.py`) |
| Published results | 5 systems on HuggingFace | None (results/ gitignored) |
| Judge model | gpt-4o-mini | gemini-3-flash-preview |

Sources: `EverMind-AI/EverMemOS/README.md`, `EverMind-AI/EverMemBench/README.md`

EverMemBench's `llm_adapter.py` implements a full-context baseline, but it is designed for the EverMemBench-Dynamic dataset (multi-person group chat), not for LoCoMo. The EverMemOS evaluation framework, which produces the LoCoMo results analyzed in this audit, has no full-context adapter.
