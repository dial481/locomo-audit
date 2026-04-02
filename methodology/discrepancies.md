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

Category 5 (adversarial) questions have no ground truth answers in the dataset. Of 446 questions, 444 contain only an `adversarial_answer` field (the deliberately wrong answer — a trap) and no `answer` field. Only 2 questions have both fields. You cannot evaluate a system against an answer key that doesn't exist ([snap-research/locomo#2](https://github.com/snap-research/locomo/issues/2)).

### What the Original Code Actually Does

The original LoCoMo evaluation code contains two mechanisms for Category 5, both non-functional:

**1. Multiple-choice formatting** (`gpt_utils.py:245-256`, `claude_utils.py:153-164`):

```python
elif qa['category'] == 5:
    question = qa['question'] + " Select the correct answer: (a) {} (b) {}. "
    if random.random() < 0.5:
        question = question.format('Not mentioned in the conversation', qa['answer'])
```

This code references `qa['answer']` — a field that does not exist on 444 of 446 Category 5 questions. The code would crash with a `KeyError` if executed on those questions. It can only run on the 2 questions (0.4%) that happen to have an `answer` field.

**2. Keyword match** (`evaluation.py:217-221`):

```python
elif line['category'] in [5]:
    if 'no information available' in output.lower() or 'not mentioned' in output.lower():
        all_ems.append(1)
    else:
        all_ems.append(0)
```

This checks whether the system's response contains either the exact phrase "no information available" or "not mentioned." Any other phrasing of the same correct insight — "that wasn't discussed," "I don't have that information," "there's no record of that," "that topic didn't come up" — is scored as incorrect. An LLM has no reason to produce these two specific phrases unless the prompt forces it, making this keyword match effectively non-functional as an evaluation metric.

**In summary:** The multiple-choice code is broken for 99.6% of the questions. The keyword match is broken by design. There is no working evaluation for Category 5 in the original codebase. Every subsequent implementation excluded Category 5 entirely.

### The Evaluation Gap

Category 5 tests adversarial robustness: when asked about something that was never discussed in the conversation, does the system correctly recognize the absence, or does it confabulate a plausible-sounding answer?

This is a critical capability to measure for production memory systems, for several reasons:

1. **LLM confabulation is the primary failure mode.** Language models are known to generate confident, plausible-sounding answers to questions they have no information about. A memory system that scores 95% on recall but confabulates 30% of the time on adversarial questions has a significant reliability gap that recall metrics alone do not capture.

2. **Accurate abstention is a core requirement.** Users and downstream systems rely on memory retrieval being trustworthy. A system that reliably indicates "this information is not in the conversation" when that is true provides stronger reliability guarantees than one that always produces an answer regardless of whether it has supporting evidence.

3. **No published LoCoMo result tests this.** Every system in the ecosystem — Mem0, Zep, EverMemOS, MemU, MemoryBank, MemWalker — excludes Category 5. No published LoCoMo evaluation reports an adversarial robustness score. The capability most relevant to production reliability is not measured by any published evaluation.

4. **The evaluated categories actively reward confabulation.** The LLM judge is instructed to "be generous — as long as it touches on the same topic as the gold answer, it should be counted as CORRECT" ([prompts.yaml](../evaluation/config/prompts.yaml)). Longer, vaguer answers score higher (Pearson r=0.60 between word count and accuracy — see [word_counts.md](word_counts.md)). Our [adversarial plausibility baseline](../ap-baseline/README.md) demonstrated that intentionally wrong but vague-and-topical answers fool the judge 62.81% of the time. And at least one system ships with an explicit instruction to never admit ignorance: Mem0's default prompt states "If no relevant information is found, make sure you don't say no information is found. Instead, accept the question and provide a general response" ([`mem0/configs/prompts.py`](https://github.com/mem0ai/mem0/blob/main/mem0/configs/prompts.py)). The result is an incentive structure where the evaluation rewards longer, more confident responses regardless of accuracy, while the Category 5 questions that would test the complementary skill — recognizing the absence of information — are excluded. Without adversarial evaluation, there is no counterbalance to a scoring methodology that correlates positively with answer length and topical coverage.

### A Straightforward Fix Exists

The adversarial questions have a well-defined correct answer: the information is not in the conversation. The `adversarial_answer` field (present on all 446 questions) provides a plausible wrong answer — the trap. A proper multiple-choice evaluation would:

1. Present 3-4 distractor options generated from the conversation context (plausible but wrong)
2. Include the `adversarial_answer` as one option (the specific trap)
3. Include "Not mentioned in the conversation" as the correct option
4. Score deterministically: did the system pick the correct option, or did it fall for a distractor?

This format eliminates three problems at once: the missing `answer` field (the correct answer is always "not mentioned"), the unreliable LLM judge (scoring is deterministic letter matching), and the keyword match fragility (the system is forced to commit to a specific choice rather than free-form refusal). It is a harder and better test than any free-form alternative because the distractors and the adversarial answer are sitting right there looking plausible.

This is not a novel observation. A third-party dataset ([Percena/locomo-mc10](https://huggingface.co/datasets/Percena/locomo-mc10)) converts all LoCoMo questions to 10-option multiple choice, including Category 5, though its distractor generation methodology is undocumented. The original LoCoMo code attempted a simpler binary version that was never completed. GitHub issue [snap-research/locomo#2](https://github.com/snap-research/locomo/issues/2) (filed August 2024) asks about the missing answers and has received no maintainer response.

446 questions — 22.5% of the dataset, more than Multi-hop, Temporal, or Open-domain individually — test a failure mode central to LLM-based memory system reliability. A working evaluation would require a straightforward code change. As it stands, the category is excluded by every implementation, and no published LoCoMo result reports whether any system can reliably distinguish "I have this information" from "I don't."

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
| Systems tested | EverMemOS, Mem0, MemOS, MemU, Zep | EverMemOS, Mem0, MemOS, Memobase, Zep + LLM |
| Full-context adapter | Not present | Present (`llm_adapter.py`) |
| Published results | 5 systems on HuggingFace | None (results/ gitignored) |
| Judge model | gpt-4o-mini | gemini-3-flash-preview |

Sources: `EverMind-AI/EverMemOS/README.md`, `EverMind-AI/EverMemBench/README.md`

EverMemBench's `llm_adapter.py` implements a full-context baseline, but it is designed for the EverMemBench-Dynamic dataset (multi-person group chat), not for LoCoMo. The EverMemOS evaluation framework, which produces the LoCoMo results analyzed in this audit, has no full-context adapter.
