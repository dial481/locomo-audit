# Statistical Validity of LoCoMo Per-Category Scores

## The Problem

LoCoMo's per-category breakdowns are treated as meaningful signal by every
system that publishes results on this benchmark. Teams compare their Single-hop
vs. Multi-hop vs. Temporal vs. Open-domain scores to identify strengths and
weaknesses. Leaderboards rank systems per-category.

But the category sample sizes are significantly imbalanced:

| Category | n | % of Dataset | Status |
|----------|--:|-----------:|--------|
| Single-hop | 841 | 42.3% | Evaluated |
| **Adversarial** | **446** | **22.5%** | **Excluded** ([why](../methodology/discrepancies.md#category-5-exclusion)) |
| Temporal | 321 | 16.2% | Evaluated |
| Multi-hop | 282 | 14.2% | Evaluated |
| Open-domain | 96 | 4.8% | Evaluated |
| **Total in dataset** | **1,986** | **100%** | |
| **Total evaluated** | **1,540** | **77.5%** | |

The largest evaluated category (Single-hop) has **8.8x** more questions
than the smallest (Open-domain). The second-largest category in the entire
dataset (Adversarial, n=446) is excluded from all published evaluations because
444 of its 446 questions have no ground truth `answer` field — only an
`adversarial_answer` (the deliberately wrong answer). You cannot evaluate a
system against an answer key that doesn't exist. This means 22.5% of the
dataset — more questions than Multi-hop, Temporal, or Open-domain
individually — is discarded before evaluation begins.

The imbalance among the four evaluated categories means the statistical
precision of per-category scores varies substantially. A 5-point difference in
Single-hop (n=841) may be statistically significant. A 5-point difference in
Open-domain (n=96) falls well within the confidence interval.

## Confidence Intervals

We use the [Wilson Score interval](https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval)
to compute 95% confidence intervals for each per-category accuracy. Wilson
Score is preferred over the normal (Wald) approximation because it is more
accurate for proportions near 0 or 1 and for smaller sample sizes.

**Important:** Confidence interval width is not fixed — it depends on both the
sample size *and* the observed proportion. A system scoring 50% has a wider CI
than one scoring 90% on the same number of questions, because the binomial
variance p(1-p) peaks at p=0.5. The tables below show the actual CI for each
system's actual score, not a one-size-fits-all width.

### EverMemOS

| Category | n | Score | 95% CI | Width |
|----------|--:|------:|-------:|------:|
| Single-hop | 841 | 96.1% | 94.5% – 97.2% | 2.7 pts |
| Temporal | 321 | 89.7% | 85.9% – 92.6% | 6.7 pts |
| Multi-hop | 282 | 91.1% | 87.2% – 93.9% | 6.7 pts |
| Open-domain | 96 | 70.8% | 61.1% – 79.0% | 17.9 pts |
| **Overall** | **1,540** | **92.3%** | **90.8% – 93.5%** | **2.7 pts** |

### Zep

| Category | n | Score | 95% CI | Width |
|----------|--:|------:|-------:|------:|
| Single-hop | 841 | 90.8% | 88.7% – 92.6% | 3.9 pts |
| Temporal | 321 | 77.3% | 72.4% – 81.5% | 9.1 pts |
| Multi-hop | 282 | 81.9% | 77.0% – 86.0% | 9.0 pts |
| Open-domain | 96 | 75.0% | 65.5% – 82.6% | 17.1 pts |
| **Overall** | **1,540** | **85.4%** | **83.5% – 87.1%** | **3.5 pts** |

### MemOS

| Category | n | Score | 95% CI | Width |
|----------|--:|------:|-------:|------:|
| Single-hop | 841 | 85.4% | 82.8% – 87.6% | 4.8 pts |
| Temporal | 321 | 75.1% | 70.1% – 79.5% | 9.4 pts |
| Multi-hop | 282 | 79.4% | 74.3% – 83.7% | 9.4 pts |
| Open-domain | 96 | 64.6% | 54.6% – 73.4% | 18.8 pts |
| **Overall** | **1,540** | **80.8%** | **78.8% – 82.7%** | **3.9 pts** |

### MemU

| Category | n | Score | 95% CI | Width |
|----------|--:|------:|-------:|------:|
| Single-hop | 841 | 74.9% | 71.9% – 77.7% | 5.9 pts |
| Temporal | 321 | 43.6% | 38.3% – 49.1% | 10.8 pts |
| Multi-hop | 282 | 72.3% | 66.8% – 77.2% | 10.4 pts |
| Open-domain | 96 | 54.2% | 44.2% – 63.8% | 19.5 pts |
| **Overall** | **1,540** | **66.6%** | **64.2% – 68.9%** | **4.7 pts** |

### Mem0

| Category | n | Score | 95% CI | Width |
|----------|--:|------:|-------:|------:|
| Single-hop | 841 | 69.0% | 65.8% – 72.0% | 6.2 pts |
| Temporal | 321 | 58.3% | 52.8% – 63.5% | 10.7 pts |
| Multi-hop | 282 | 61.7% | 55.9% – 67.2% | 11.3 pts |
| Open-domain | 96 | 50.0% | 40.2% – 59.8% | 19.6 pts |
| **Overall** | **1,540** | **64.2%** | **61.8% – 66.6%** | **4.8 pts** |

## Can We Distinguish Systems Per-Category?

Two systems are statistically distinguishable at the 95% level if their
confidence intervals do not overlap. The table below tests all adjacent
pairs on the overall leaderboard (EverMemOS > Zep > MemOS > MemU > Mem0)
within each category.

| Category | Pair | Scores | Gap | CIs Overlap? | Distinguishable? |
|----------|------|-------:|----:|:-------------|:-----------------|
| Single-hop | EverMemOS vs Zep | 96.1% vs 90.8% | 5.2 pp | No | **YES** |
| Single-hop | Zep vs MemOS | 90.8% vs 85.4% | 5.5 pp | No | **YES** |
| Single-hop | MemOS vs MemU | 85.4% vs 74.9% | 10.5 pp | No | **YES** |
| Single-hop | MemU vs Mem0 | 74.9% vs 69.0% | 5.9 pp | Yes | **NO** |
| Temporal | EverMemOS vs Zep | 89.7% vs 77.3% | 12.5 pp | No | **YES** |
| Temporal | Zep vs MemOS | 77.3% vs 75.1% | 2.2 pp | Yes | **NO** |
| Temporal | MemOS vs MemU | 75.1% vs 43.6% | 31.5 pp | No | **YES** |
| Temporal | MemU vs Mem0 | 43.6% vs 58.3% | 14.6 pp | No | **YES** |
| Multi-hop | EverMemOS vs Zep | 91.1% vs 81.9% | 9.2 pp | No | **YES** |
| Multi-hop | Zep vs MemOS | 81.9% vs 79.4% | 2.5 pp | Yes | **NO** |
| Multi-hop | MemOS vs MemU | 79.4% vs 72.3% | 7.1 pp | Yes | **NO** |
| Multi-hop | MemU vs Mem0 | 72.3% vs 61.7% | 10.6 pp | Yes | **NO** |
| Open-domain | EverMemOS vs Zep | 70.8% vs 75.0% | 4.2 pp | Yes | **NO** |
| Open-domain | Zep vs MemOS | 75.0% vs 64.6% | 10.4 pp | Yes | **NO** |
| Open-domain | MemOS vs MemU | 64.6% vs 54.2% | 10.4 pp | Yes | **NO** |
| Open-domain | MemU vs Mem0 | 54.2% vs 50.0% | 4.2 pp | Yes | **NO** |

**7 of 16** adjacent-pair comparisons (44%) are
statistically distinguishable at the 95% level. The rest are indistinguishable
— the gap between systems is smaller than the measurement uncertainty.

## Minimum Distinguishable Gap Per Category

How far apart must two systems score to be reliably distinguished? This depends
on both systems' scores, but as a practical guide, the table below shows the
CI width at representative score levels. Two systems need a gap of *at least*
one full CI width to have non-overlapping intervals.

| Category | n | Status | CI Width at 75% | CI Width at 85% | CI Width at 95% |
|----------|--:|--------|----------------:|----------------:|----------------:|
| Single-hop | 841 | Evaluated | 5.8 pts | 4.8 pts | 3.0 pts |
| Adversarial | 446 | **Excluded** | 8.0 pts | 6.6 pts | 4.1 pts |
| Temporal | 321 | Evaluated | 9.4 pts | 7.8 pts | 4.9 pts |
| Multi-hop | 282 | Evaluated | 10.0 pts | 8.3 pts | 5.2 pts |
| Open-domain | 96 | Evaluated | 17.1 pts | 14.1 pts | 9.4 pts |

For Open-domain (n=96), systems must differ by **14-17 percentage points** to
be statistically distinguishable. For Multi-hop (n=282), the threshold is
**8-10 points**. Even Single-hop (n=841) requires a **3-5 point** gap.

Note: Adversarial (n=446) is included for context — it *would* have had
reasonable precision (6-8 pts) if it were usable, making it the
second-best category for statistical power. Instead it is excluded entirely.

Most published system comparisons on LoCoMo fall well within these margins.

## Why This Matters

The per-category breakdowns are the most-cited part of LoCoMo results. Teams
use them to claim their system is "strong on temporal reasoning" or "weak on
multi-hop." But with confidence intervals this wide, those claims are not
supported by the data:

1. **Open-domain (n=96) has CI widths of 14-20 points,** which exceeds the
   score gap between most systems in this category. Per-category comparisons
   should note this limitation.

2. **Multi-hop and Temporal comparisons require large gaps.** At n=282 and
   n=321 respectively, 5-point differences fall within the CI. An 8-10 point gap is
   the minimum threshold for a statistically meaningful difference.

3. **Only Single-hop has reasonable precision.** With n=841, the CI widths are
   3-6 points. This is the only category where moderate differences (5+
   points) between systems are statistically meaningful.

4. **The 8.8x sample size ratio between Single-hop and Open-domain results in
   correspondingly different statistical precision.** CI width scales as
   1/sqrt(n), so Open-domain measurements are inherently ~3x less precise.
   If all four categories are important enough to measure and report
   separately, all four would ideally have sample sizes sufficient for
   meaningful comparison.

5. **These CI issues compound with the ground truth errors.** The 99 corrupted
   answers documented in [AUDIT_REPORT.md](../AUDIT_REPORT.md) are not
   distributed uniformly across categories. Open-domain has 9 errors in 96
   questions (9.4% error rate) vs. Single-hop's 36 errors in 841 questions
   (4.3%). The smallest category has the highest error rate *and* the widest
   confidence intervals — a double penalty on measurement quality.

## Do Multiple Evaluation Runs Fix This?

A natural response to wide confidence intervals is to run the evaluation
multiple times. But there are two fundamentally different kinds of "multiple
runs," and the community conflates them:

**Judge reruns** score the *same* system outputs multiple times with the LLM
judge. This measures judge consistency (inter-rater reliability). If a system
produces answer X to question #47, re-judging that same answer 3 times tells
you how noisy the judge is — not how confident you should be in the system's
score. The sample size is still n. Judge reruns do not shrink confidence
intervals.

**End-to-end reruns** re-run the entire pipeline: retrieval, generation, and
judging. Each run produces potentially different answers because LLM generation
is stochastic (temperature > 0) and retrieval may vary. This generates genuinely
new data. In theory, k independent end-to-end runs of n questions yield up to
n×k effective observations, shrinking the CI by up to √k.

### Who Does What

| System | Reported Runs | Type | Variance Reported | Source |
|--------|:---:|------|:---:|--------|
| Mem0 | 10 | End-to-end | Yes (mean ± std) | [Paper](https://arxiv.org/abs/2504.19413) |
| Zep | 1 (original) | — | No (original) | [Issue #5](https://github.com/getzep/zep-papers/issues/5) |
| EverMemOS | Not specified | — | No | [Eval README](https://github.com/EverMind-AI/EverMemOS) |
| MemU | Not specified | — | No | — |
| LoCoMo baselines | Not specified | — | No | [Maharana et al.](https://arxiv.org/abs/2402.17753) |

Only Mem0 documents a rigorous multi-run methodology. Zep's original 84%
claim was based on a single run (and separately inflated by including
Category 5 — see [discrepancies](../methodology/discrepancies.md)).
EverMemOS, MemU, and the original LoCoMo baselines report point estimates
with no variance, which in practice means single-run results.

### Why Multiple Runs Don't Fix the Imbalance

Even in the best case — fully independent end-to-end reruns — uniform runs
across all categories cannot fix the sample size asymmetry. The table below
shows CI widths at a representative 75% accuracy with 10 uniform runs:

| Category | n | n × 10 | 1-Run CI Width | 10-Run CI Width | Precision Ratio |
|----------|--:|-------:|---------------:|----------------:|:---:|
| Single-hop | 841 | 8,410 | 5.8 pts | 1.9 pts | 1.0x |
| Temporal | 321 | 3,210 | 9.4 pts | 3.0 pts | 1.6x |
| Multi-hop | 282 | 2,820 | 10.0 pts | 3.2 pts | 1.7x |
| Open-domain | 96 | 960 | 17.1 pts | 5.5 pts | 3.0x |

Ten runs shrink every CI proportionally, but Open-domain (5.5 pts) is still
**3.0x less precise** than Single-hop (1.9 pts). The 8.8x sample size ratio
is baked into the dataset. To equalize Open-domain with Single-hop at 10 runs,
you would need ~88 runs of Open-domain alone — impractical for most
evaluation budgets.

### Stochasticity and the LLM-as-Judge Trade-off

LLM-as-judge is one of the most widely adopted scalable evaluation methods for
open-ended memory recall — exact match and F1 do not work across different
model phrasings. The stochasticity this introduces is an inherent property
of the evaluation approach, not a flaw per se. That said, it has implications
for how multiple runs reduce uncertainty.

The √k improvement assumes each run is fully independent. In practice, memory
systems are partially deterministic: most questions are answered the same way
every time (always right or always wrong), with only a fraction of "edge"
questions varying between runs. A question the system always gets right
(p ≈ 1.0) contributes zero new information from additional runs because its
per-question variance p(1−p) ≈ 0.

For a realistic system where ~70% of questions are near-deterministic, the
effective sample size from 10 runs falls well short of the theoretical n×10.
The exact benefit depends on the system's stochasticity profile, which is
rarely reported. Mem0's published standard deviations range from ±0.11 to
±0.67 percentage points across 10 runs (Table 1, [arXiv:2504.19413](https://arxiv.org/abs/2504.19413)).
Even the highest-variance category (Multi-hop, ±0.67) represents modest
run-to-run variation, suggesting that most questions produce the same answer
every time and the 10 runs provide well under 10× the information.

### The Paradox

Multiple runs are the right idea applied to the wrong problem. They reduce
*measurement noise* (judge variance, generation stochasticity) but cannot fix
*design noise* (too few questions in a category). The fundamental issue is that
96 questions is insufficient for meaningful comparison regardless of how many
times you score them. Fixing this requires more questions, not more runs.

## Methodology

All confidence intervals use the Wilson Score method:

```
center = (p̂ + z²/2n) / (1 + z²/n)
spread = z × √((p̂(1-p̂) + z²/4n) / n) / (1 + z²/n)
CI = [center - spread, center + spread]
```

where p̂ = k/n (observed proportion), z = 1.96 (95% confidence), n = sample
size, k = number of correct answers.

Wilson Score is preferred over the normal (Wald) approximation (p̂ ± z√(p̂(1-p̂)/n))
because it provides better coverage probability, especially for proportions
near 0 or 1 and sample sizes under 100. At n=96, the difference between Wilson
and Wald is non-trivial (~0.5 percentage points in CI bounds).

**Note on conservatism:** The CI overlap test used in the distinguishability
analysis above is stricter than a two-proportion z-test. Non-overlapping CIs
guarantee significance, but overlapping CIs do *not* guarantee non-significance.
A proper z-test finds 2 additional pairs distinguishable that the CI overlap
method calls indistinguishable (MemU vs. Mem0 on Single-hop and Multi-hop,
where the CIs overlap by <0.4 percentage points). This means the analysis
above is conservative — the true number of indistinguishable comparisons is
likely lower than reported, making the headline finding (56% indistinguishable)
an understatement if anything.

Scores used are per-question majority vote (2-of-3 judge agreement), matching
the methodology in [RESULTS_AUDIT.md](RESULTS_AUDIT.md). Data source:
[per_category_breakdown.json](per_category_breakdown.json).

Script: [statistical_validity.py](statistical_validity.py)
