# LoCoMo Benchmark Results Audit

## How to Reproduce

```bash
# 1. Download published eval_results.json from HuggingFace
python download_results.py

# 2. Run the audit (~1,485 LLM calls, ~$0.50 with gpt-4o-mini)
python audit_results.py
```

Requires `OPENAI_API_KEY` or `LLM_API_KEY` environment variable. Set `LLM_BASE_URL` for non-OpenAI providers (e.g. OpenRouter). Results are checkpointed per-system, so interrupted runs resume automatically.

---

## Methodology

### Ground Truth Errors

This audit evaluates published evaluation results against 99 score-corrupting errors identified in the LoCoMo benchmark's golden answers (see `errors.json` in repo root). Citation-only errors (`WRONG_CITATION`) are excluded as they do not affect scoring.

| Error Type | Count |
|-----------|-------|
| HALLUCINATION | 33 |
| TEMPORAL_ERROR | 26 |
| ATTRIBUTION_ERROR | 24 |
| AMBIGUOUS | 13 |
| INCOMPLETE | 3 |

### Scoring Rule

The published `eval_results.json` files contain 3 independent LLM judge runs per question. We treat a question as **scored correct** if at least 2 of 3 judgments are true (majority vote).

*Note:* EverMemOS's `compute_acc.py` calculates accuracy per-run independently then averages the three accuracies, which yields a very similar number at the aggregate level but is not identical to majority vote at the per-question level. This audit uses strict per-question majority vote because the audit requires a binary correct/wrong determination for each question.

### Audit Classification

For each of the 99 error-affected questions across 5 systems, an LLM judge (gpt-4o-mini, temperature=0) was run 3 times independently. The final classification is determined by majority vote across the 3 runs, matching the multi-run methodology of the original evaluation. Each question is classified into one of three outcomes:

- **UNDESERVED_PENALTY**: System was marked wrong, but its answer is correct given the corrected ground truth. Score should go **up**.
- **UNDESERVED_CREDIT**: System was marked correct, but only because the golden answer was erroneous. Score should go **down**.
- **WASH**: The error did not change the outcome (correct regardless, wrong regardless, or genuinely ambiguous).

---

## Results

### Overall Accuracy (N=1,540)

| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta |
|--------|------------------------|------------------------|-------|
| EverMemOS | 92.32% +/- 0.03% | 92.86% +/- 0.05% | +0.54% |
| Mem0 | 64.20% +/- 0.03% | 64.72% +/- 0.03% | +0.52% |
| MemOS | 80.76% +/- 0.11% | 81.32% +/- 0.13% | +0.56% |
| MemU | 66.67% +/- 0.06% | 66.52% +/- 0.08% | -0.15% |
| Zep | 85.22% +/- 0.12% | 85.74% +/- 0.12% | +0.52% |

### Key Findings

**1. Net adjustments are small -- the errors don't systematically favor anyone.** Across all 5 systems, the net score change is under 0.6 percentage points (MemU is the only system whose score goes *down*, by 0.15%). The ground truth errors cut both ways roughly equally -- some systems lost points they deserved, some gained points they didn't. This proves the audit is fair and the errors are not biased toward or against any particular system.

**2. The 6.4% error rate destroys the precision of system comparisons.** The net adjustment being small does not mean the errors don't matter. With 99 out of 1,540 ground truth answers wrong, claiming a system scores "92.32%" to two decimal places is misleading -- the answer key itself isn't reliable enough to support that precision. When comparing two systems at 91% vs 92%, a 1-point gap is swallowed by the noise from corrupted ground truth. Small differences between systems on this benchmark are not meaningful.

**3. Ceiling violations are structural proof that the scoring mechanism is broken at the top.** The maximum legitimate score on this dataset is 93.57% (1,441 correct out of 1,540). EverMemOS exceeds the per-category ceiling in Single-hop (96.08% adjusted vs 95.72% ceiling) and Multi-hop (91.25% adjusted vs 90.07% ceiling). These violations *survive full correction* -- they are not about net adjustments but about the LLM judge's leniency inflating scores on questions with corrupted golden answers. When a system's accuracy approaches the error ceiling, the judge's generous matching standard becomes the binding constraint, and the reported score loses meaning.

These three points are complementary: (1) validates the audit's fairness, (2) undermines the precision of all system comparisons on this benchmark, and (3) identifies a structural failure in the LLM-as-judge methodology at the top of the scoring range.

### Judge Leniency on Corrupted Questions

Across all 495 judgment pairs (99 corrupted questions x 5 systems), the original LLM judge marked the system **correct** 242 times -- 48.9%, or roughly 1 in 2. These are questions where the golden answer is factually wrong, yet the judge still awarded credit.

Each of these 242 "correct on a corrupted question" cases falls into one of two buckets:

- **UNDESERVED_CREDIT** (94 cases): The audit caught these -- the system's answer matched the wrong golden, and the credit was revoked in adjusted scoring.
- **WASH where originally correct** (148 cases): The audit judge ruled the system's answer matched *both* the wrong golden and the corrected answer, so no adjustment was made. This is where second-order leniency hides -- the same generous "close enough" standard that inflated the original score now protects it during the audit.

#### Per System

| System | Correct on Corrupted | Rate | Undeserved Credit | WASH (correct) |
|--------|---------------------|------|-------------------|----------------|
| EverMemOS | 60 / 99 | 60.6% | 19 | 41 |
| Zep | 53 / 99 | 53.5% | 17 | 36 |
| MemU | 48 / 99 | 48.5% | 23 | 25 |
| MemOS | 47 / 99 | 47.5% | 20 | 27 |
| Mem0 | 34 / 99 | 34.3% | 15 | 19 |

The pattern tracks overall system quality -- better systems are more often marked correct on corrupted questions, because they produce plausible answers that trigger the judge's generous matching. EverMemOS has the highest rate (60.6%) and also the highest WASH-where-correct count (41), consistent with the ceiling violation analysis above.

#### Per Category (all systems pooled)

| Category | Correct on Corrupted | Rate |
|----------|---------------------|------|
| Multi-hop | 80 / 140 | 57.1% |
| Single-hop | 90 / 180 | 50.0% |
| Open-domain | 20 / 45 | 44.4% |
| Temporal | 52 / 130 | 40.0% |

Multi-hop questions show the highest leniency rate (57.1%), likely because multi-hop answers involve synthesizing information across sessions -- a task where partial overlap between wrong and correct answers is common, making it easier for the judge to call a match.

Temporal questions show the lowest rate (40.0%), which makes sense: date/time errors produce clear-cut mismatches that even a generous judge can't paper over.

### Impact Breakdown

| System | Undeserved Penalties | Undeserved Credits | Washes | Net Change |
|--------|---------------------|-------------------|--------|------------|
| EverMemOS | 28 | 19 | 52 | +9 |
| Mem0 | 23 | 15 | 61 | +8 |
| MemOS | 29 | 20 | 50 | +9 |
| MemU | 21 | 23 | 55 | -2 |
| Zep | 25 | 17 | 57 | +8 |

### Per-Category Breakdown

#### Category 4: Single-hop (N=841)

| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta | Penalties | Credits | Washes |
|--------|------------------------|------------------------|-------|-----------|---------|--------|
| EverMemOS | 95.96% +/- 0.10% | 96.08% +/- 0.10% | +0.12% | 9 | 8 | 19 |
| Mem0 | 68.93% +/- 0.06% | 69.04% +/- 0.06% | +0.12% | 6 | 5 | 25 |
| MemOS | 85.30% +/- 0.24% | 85.30% +/- 0.24% | +0.00% | 10 | 10 | 16 |
| MemU | 74.83% +/- 0.06% | 74.00% +/- 0.06% | -0.83% | 6 | 13 | 17 |
| Zep | 90.80% +/- 0.24% | 90.80% +/- 0.24% | +0.00% | 9 | 9 | 18 |

#### Category 1: Multi-hop (N=282)

| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta | Penalties | Credits | Washes |
|--------|------------------------|------------------------|-------|-----------|---------|--------|
| EverMemOS | 91.37% +/- 0.17% | 91.25% +/- 0.17% | -0.12% | 6 | 6 | 16 |
| Mem0 | 62.06% +/- 0.29% | 62.77% +/- 0.29% | +0.71% | 8 | 6 | 14 |
| MemOS | 78.96% +/- 0.44% | 81.80% +/- 0.44% | +2.84% | 10 | 2 | 16 |
| MemU | 72.58% +/- 0.33% | 73.88% +/- 0.44% | +1.30% | 7 | 3 | 18 |
| Zep | 81.21% +/- 0.29% | 80.50% +/- 0.29% | -0.71% | 4 | 6 | 18 |

#### Category 2: Temporal (N=321)

| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta | Penalties | Credits | Washes |
|--------|------------------------|------------------------|-------|-----------|---------|--------|
| EverMemOS | 89.82% +/- 0.15% | 91.07% +/- 0.15% | +1.25% | 9 | 5 | 12 |
| Mem0 | 58.15% +/- 0.15% | 58.46% +/- 0.15% | +0.31% | 5 | 4 | 17 |
| MemOS | 75.29% +/- 0.39% | 75.80% +/- 0.39% | +0.52% | 8 | 6 | 12 |
| MemU | 43.82% +/- 0.15% | 43.82% +/- 0.15% | +0.00% | 6 | 6 | 14 |
| Zep | 77.47% +/- 0.29% | 80.58% +/- 0.29% | +3.12% | 11 | 1 | 14 |

#### Category 3: Open-domain (N=96)

| System | Original (mean +/- std) | Adjusted (mean +/- std) | Delta | Penalties | Credits | Washes |
|--------|------------------------|------------------------|-------|-----------|---------|--------|
| EverMemOS | 71.53% +/- 0.98% | 75.35% +/- 1.30% | +3.82% | 4 | 0 | 5 |
| Mem0 | 49.31% +/- 0.49% | 53.47% +/- 0.49% | +4.17% | 4 | 0 | 5 |
| MemOS | 64.58% +/- 0.00% | 63.54% +/- 0.00% | -1.04% | 1 | 2 | 6 |
| MemU | 54.17% +/- 0.00% | 55.21% +/- 0.00% | +1.04% | 2 | 1 | 6 |
| Zep | 73.96% +/- 0.85% | 73.96% +/- 0.85% | +0.00% | 1 | 1 | 7 |

### Ceiling Analysis

With 99 score-corrupting errors in the benchmark, a perfect system cannot achieve 100% accuracy. The ceiling is the maximum score achievable if a system correctly answers every non-erroneous question.

| Scope | Questions | Errors | Ceiling |
|-------|-----------|--------|---------|
| **Overall** | 1,540 | 99 | 93.57% |
| Category 4: Single-hop | 841 | 36 | 95.72% |
| Category 1: Multi-hop | 282 | 28 | 90.07% |
| Category 2: Temporal | 321 | 26 | 91.90% |
| Category 3: Open-domain | 96 | 9 | 90.62% |

#### Systems vs. Ceiling

| System | Category | Original | Adjusted | Ceiling | Gap to Ceiling |
|--------|----------|----------|----------|---------|----------------|
| EverMemOS | Overall | 92.32% | 92.86% | 93.57% | 0.71% |
| | Single-hop | 95.96% | 96.08% | 95.72% | -0.36% |
| | Multi-hop | 91.37% | 91.25% | 90.07% | -1.18% |
| | Temporal | 89.82% | 91.07% | 91.90% | 0.83% |
| | Open-domain | 71.53% | 75.35% | 90.62% | 15.28% |
| Mem0 | Overall | 64.20% | 64.72% | 93.57% | 28.85% |
| | Single-hop | 68.93% | 69.04% | 95.72% | 26.67% |
| | Multi-hop | 62.06% | 62.77% | 90.07% | 27.30% |
| | Temporal | 58.15% | 58.46% | 91.90% | 33.44% |
| | Open-domain | 49.31% | 53.47% | 90.62% | 37.15% |
| MemOS | Overall | 80.76% | 81.32% | 93.57% | 12.25% |
| | Single-hop | 85.30% | 85.30% | 95.72% | 10.42% |
| | Multi-hop | 78.96% | 81.80% | 90.07% | 8.27% |
| | Temporal | 75.29% | 75.80% | 91.90% | 16.10% |
| | Open-domain | 64.58% | 63.54% | 90.62% | 27.08% |
| MemU | Overall | 66.67% | 66.52% | 93.57% | 27.06% |
| | Single-hop | 74.83% | 74.00% | 95.72% | 21.72% |
| | Multi-hop | 72.58% | 73.88% | 90.07% | 16.19% |
| | Temporal | 43.82% | 43.82% | 91.90% | 48.08% |
| | Open-domain | 54.17% | 55.21% | 90.62% | 35.42% |
| Zep | Overall | 85.22% | 85.74% | 93.57% | 7.84% |
| | Single-hop | 90.80% | 90.80% | 95.72% | 4.91% |
| | Multi-hop | 81.21% | 80.50% | 90.07% | 9.57% |
| | Temporal | 77.47% | 80.58% | 91.90% | 11.32% |
| | Open-domain | 73.96% | 73.96% | 90.62% | 16.67% |

**Ceiling violations** (original score exceeds ceiling, indicating credit from erroneous golden answers):

- EverMemOS Single-hop (95.96% > 95.72%)
- EverMemOS Multi-hop (91.37% > 90.07%)

These violations **persist after full correction**:

- EverMemOS Single-hop (adjusted 96.08%, gap +0.36%)
- EverMemOS Multi-hop (adjusted 91.25%, gap +1.18%)

#### Why violations persist: second-order judge leniency

The ceiling is a hard mathematical constraint. 36 out of 841 single-hop questions have wrong golden answers, so the maximum legitimate score is 805/841 = 95.72%. EverMemOS scored 95.96% -- roughly 807 correct out of 841. At least 2 of those "correct" marks landed on corrupted questions.

Our audit examined all 36 corrupted single-hop questions, checked what EverMemOS actually answered, and classified each one. Some were UNDESERVED_CREDIT (answer matched the wrong golden, subtracted). Some were UNDESERVED_PENALTY (answer was right but the bad golden punished it, added back). But the third category -- WASH -- is where the residual hides.

On corrupted questions where EverMemOS was originally marked correct, the audit judge sometimes ruled: "the system's answer matches *both* the wrong golden answer *and* the corrected answer." Classification: WASH, no adjustment needed. But this is suspect. If the golden answer is factually wrong, and the system's answer matches that wrong answer, *and* the judge also thinks it matches the correct answer -- the most likely explanation is that the judge is being generous. The same "close enough" leniency that inflated the original score is now protecting it during the audit.

This is a second-order leniency problem: the audit judge (gpt-4o-mini) inherited the same generous matching standard as the original evaluation judge. On ambiguous or vaguely-worded questions with corrupted golden answers, the judge defaults to "close enough to both" and calls it a WASH when a stricter evaluator would call it UNDESERVED_CREDIT.

The 0.36% single-hop residual and 1.18% multi-hop residual are small in absolute terms, but they demonstrate a structural limitation of the LLM-as-judge methodology: **when a system's score approaches the ceiling imposed by ground truth errors, the judge's leniency becomes the binding constraint on evaluation accuracy.** No amount of re-auditing with the same class of judge can fully resolve it -- the generosity is baked into the evaluation paradigm itself.

### Published Scores Cross-Check

Comparison of our computed scores against published scores. The published pipeline uses **per-run averaging for overall scores** but **majority vote for per-category scores** -- we match each method accordingly.

| System | Scope | Published | Computed (method) | Match |
|--------|-------|-----------|-------------------|-------|
| EverMemOS | Overall | 92.32% | 92.32% (per-run avg) | ✓ |
| | Single-hop | 96.08% | 96.08% (majority) | ✓ |
| | Multi-hop | 91.13% | 91.13% (majority) | ✓ |
| | Temporal | 89.72% | 89.72% (majority) | ✓ |
| | Open-domain | 70.83% | 70.83% (majority) | ✓ |
| Mem0 | Overall | 64.20% | 64.20% (per-run avg) | ✓ |
| | Single-hop | 68.97% | 68.97% (majority) | ✓ |
| | Multi-hop | 61.70% | 61.70% (majority) | ✓ |
| | Temporal | 58.26% | 58.26% (majority) | ✓ |
| | Open-domain | 50.00% | 50.00% (majority) | ✓ |
| MemOS | Overall | 80.76% | 80.76% (per-run avg) | ✓ |
| | Single-hop | 85.37% | 85.37% (majority) | ✓ |
| | Multi-hop | 79.43% | 79.43% (majority) | ✓ |
| | Temporal | 75.08% | 75.08% (majority) | ✓ |
| | Open-domain | 64.58% | 64.58% (majority) | ✓ |
| MemU | Overall | 66.67% | 66.67% (per-run avg) | ✓ |
| | Single-hop | 74.91% | 74.91% (majority) | ✓ |
| | Multi-hop | 72.34% | 72.34% (majority) | ✓ |
| | Temporal | 43.61% | 43.61% (majority) | ✓ |
| | Open-domain | 54.17% | 54.17% (majority) | ✓ |
| Zep | Overall | 85.22% | 85.22% (per-run avg) | ✓ |
| | Single-hop | 90.84% | 90.84% (majority) | ✓ |
| | Multi-hop | 81.91% | 81.91% (majority) | ✓ |
| | Temporal | 77.26% | 77.26% (majority) | ✓ |
| | Open-domain | 75.00% | 75.00% (majority) | ✓ |

All 25 published scores reproduced exactly (5 systems × 5 scopes).

### Classification by Error Type

Average across all systems:

| Error Type | Count | Avg Penalties | Avg Credits | Avg Washes |
|-----------|-------|--------------|------------|------------|
| HALLUCINATION | 33 | 7.0 | 5.6 | 20.4 |
| TEMPORAL_ERROR | 26 | 7.6 | 2.6 | 15.8 |
| ATTRIBUTION_ERROR | 24 | 6.6 | 6.8 | 10.6 |
| AMBIGUOUS | 13 | 4.0 | 3.4 | 5.6 |
| INCOMPLETE | 3 | 0.0 | 0.4 | 2.6 |

---

## Reproducibility

- **Audit date:** 2026-02-19
- **Judge model:** gpt-4o-mini (temperature=0, 3 independent runs per question)
- **Audit classification:** Majority vote across 3 runs
- **Original scoring:** Per-run accuracy averaged across 3 original judge runs (mean +/- std)
- **Error database:** `errors.json` (99 score-corrupting entries)
- **Published results:** [EverMind-AI/EverMemOS_Eval_Results](https://huggingface.co/datasets/EverMind-AI/EverMemOS_Eval_Results) on HuggingFace

## Files

| File | Description |
|------|-------------|
| `audit_results.py` | This audit script |
| `download_results.py` | Fetches eval_results.json from HuggingFace |
| `judgments/*.json` | Per-system LLM audit judgments (fully auditable) |
| `results/*.json` | Downloaded published eval_results |
| `per_category_breakdown.json` | Per-system, per-category adjusted scores (JSON) |

