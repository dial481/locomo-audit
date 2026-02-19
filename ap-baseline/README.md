# Adversarial Plausibility Baseline — Judge Leniency Stress Test

A frontier LLM (Claude Opus 4.6) was given the LoCoMo answer key and asked to generate
the most plausible-sounding **wrong** answers it could for all 1,540 questions using two
different strategies. These intentionally incorrect answers were then scored by the exact
same LLM judge (gpt-4o-mini, temperature=0, "be generous" instruction) used to evaluate
all 5 published memory systems.

**If the judge is functioning correctly, the adversarial baseline should score near 0%.**

## Key Result

| Strategy | Overall | Single-hop | Multi-hop | Temporal | Open-domain |
|----------|---------|-----------|----------|----------|-------------|
| **V1 — Specific-but-wrong** | **10.61%** | 15.18% | 5.91% | 3.43% | 8.33% |
| **V2 — Vague-but-topical** | **62.81%** | 68.53% | 44.44% | 63.24% | 65.28% |

Vague answers that stay in the right topical neighborhood fool the judge **6x more often**
than specific wrong answers. The v2 strategy exploits the judge's "be generous — as long as
it touches on the same topic" instruction by giving answers that touch the topic without
committing to any falsifiable detail.

### Comparison Against Real Systems

| System | Overall | Single-hop | Multi-hop | Temporal | Open-domain |
|--------|---------|-----------|----------|----------|-------------|
| **V2 — Vague** | **62.81%** | **68.53%** | **44.44%** | **63.24%** | **65.28%** |
| EverMemOS | 92.32% | 96.08% | 91.13% | 89.72% | 70.83% |
| Zep | 85.22% | 90.84% | 81.91% | 77.26% | 75.00% |
| MemoS | 80.76% | 85.37% | 79.43% | 75.08% | 64.58% |
| MemU | 66.67% | 74.91% | 72.34% | 43.61% | 54.17% |
| Mem0 | 64.20% | 68.97% | 61.70% | 58.26% | 50.00% |
| **V1 — Specific** | **10.61%** | **15.18%** | **5.91%** | **3.43%** | **8.33%** |

A system that **knows every answer and deliberately gets them wrong** scores 62.81% —
higher than Mem0 (64.20%) and MemU (66.67%) in several categories, and within striking
distance overall. This is not a measure of those systems being bad; it is a measure of
the judge being unable to distinguish vague topic-matching from actual knowledge.

## Two Strategies

### V1: Specific-but-Wrong (10.61%)

Every core fact is shifted to a plausible alternative in the same semantic neighborhood.
"A painting of Aragorn" becomes "a poster of Gandalf." "October 2nd" becomes "late September."
"Three weeks" becomes "about a month." The answers sound confident and specific — but
every detail is wrong.

The judge catches these **~89% of the time** because specific wrong facts are falsifiable:
"a poster of Gandalf" clearly does not match "a painting of Aragorn."

See [v1/AP_BASELINE_REPORT.md](v1/AP_BASELINE_REPORT.md) for full v1 results.

### V2: Vague-but-Topical (62.81%)

Every answer generalizes away from falsifiable specifics. "A painting of Aragorn" becomes
"artwork of a fictional character he admires." "October 2nd, 2023" becomes "Sometime in
early fall." "A painting of a sunset over a lake with swans" becomes "A nature scene she painted."

The judge accepts these **~63% of the time** because the "be generous" instruction tells it
to award credit when the answer "touches on the same topic as the gold answer." A vague
answer that stays in the right domain cannot be falsified by semantic comparison alone —
it subsumes the correct answer without actually containing it.

See [v2/AP_BASELINE_REPORT.md](v2/AP_BASELINE_REPORT.md) for full v2 results.

## Why the 6x Difference Matters

The gap between v1 (10.61%) and v2 (62.81%) isolates the judge's failure mode. It is not
fooled by confidently stated wrong facts. It **is** fooled by topical vagueness — answers
that cannot be marked wrong because they never commit to anything specific enough to be wrong.

This has direct implications for memory system evaluation: a system that retrieves the right
topic but fails to extract specific details will receive disproportionate credit from this
judge. The "be generous" instruction, combined with semantic similarity matching, creates a
systematic bias toward systems that produce vague, topic-adjacent answers over systems that
attempt (and sometimes fail at) precise recall.

## Per-Category Patterns

| Category | V1 | V2 | V2/V1 Ratio | Interpretation |
|----------|-------|-------|-------------|----------------|
| Single-hop (N=841) | 15.18% | 68.53% | 4.5x | Largest category; many opinion/sentiment questions where vagueness is hard to reject |
| Multi-hop (N=282) | 5.91% | 44.44% | 7.5x | Requires combining multiple facts — vagueness is less effective but still exploits partial overlap |
| Temporal (N=321) | 3.43% | 63.24% | 18.4x | Specific wrong dates are obvious; vague time references ("around late May") subsume the correct date |
| Open-domain (N=96) | 8.33% | 65.28% | 7.8x | Inference/hypothetical questions where vague answers are inherently reasonable |

The temporal category shows the most dramatic ratio (18.4x): a specific wrong date ("November 15th"
for "October 2nd") is trivially caught, but a vague time reference ("sometime in early fall")
encompasses the correct answer without being falsifiable.

## Answer Length Analysis

A natural question: does V2 succeed by producing longer answers that give the judge more surface area
for semantic matching? No, V2 answers are similar in length to V1.

| Source | Mean Words | Median | Ratio to Golden |
|--------|-----------|--------|-----------------|
| Golden Answer | 4.9 | 3 | 1.0x |
| Mem0 | 4.5 | 4 | 0.9x |
| MemU | 5.0 | 4 | 1.0x |
| **V2 — Vague** | **6.5** | **6** | **1.3x** |
| V1 — Specific | 7.2 | 6 | 1.5x |
| MemoS | 15.1 | 6 | 3.1x |
| EverMemOS | 48.7 | 42 | 9.9x |
| Zep | 53.0 | 43 | 10.8x |

V2 averages 6.5 words per answer — shorter than MemoS, EverMemOS, and Zep, and only 1.3x the golden
answer length. The two systems V2 competes with on score (Mem0 at 64.20%, MemU at 66.67%) produce
answers of similar length (4.5 and 5.0 words). EverMemOS and Zep average 10x the golden answer length,
giving them far more surface area for generous semantic matching than V2 has.

The confound runs the opposite direction: V2's 62.81% score is achieved with *less* text, not more.
The judge accepts V2 answers because they are vague and topically adjacent, not because they are verbose.

## Audit

All numbers have been independently verified. See [AUDIT_REPORT.md](AUDIT_REPORT.md) for:

- **CHECK 1:** Accidentally-correct rate (0.06% v1, 0% v2 — well below 5% threshold)
- **CHECK 2:** Full arithmetic verification of all reported numbers (zero discrepancies)
- **CHECK 3:** Spot-check of 40 judge calls with manual assessment
- **CHECK 4:** Cross-cutting analysis of v1/v2 agreement patterns

**Confidence: HIGH. All numbers are publishable.**

## Methodology

- **Answer generation model:** Claude Opus 4.6 (claude-opus-4-6)
- **Judge model:** gpt-4o-mini (temperature=0)
- **Judge prompt:** Loaded at runtime from `../evaluation/config/prompts.yaml` — the identical
  file used by the original EverMemOS evaluation pipeline
- **Runs:** 3 independent judge calls per question
- **Scoring:** Per-run accuracy averaged across runs (matching `compute_acc.py`)

## Files

| File | Description |
|------|-------------|
| `answer_key.json` | LoCoMo answer key (1,540 Q+A pairs) fed to adversarial baseline |
| `score_ap.py` | Scoring pipeline (judge calls + report generation) |
| `AUDIT_REPORT.md` | Independent audit of all adversarial baseline results |
| `CLAUDE_v1.md` | V1 generation prompt (specific-but-wrong strategy) |
| `CLAUDE_v2.md` | V2 generation prompt (vague-but-topical strategy) |
| `v1/` | V1 results: `bs_eval_results.json`, `bs_eval_results_scored.json`, `AP_BASELINE_REPORT.md` |
| `v2/` | V2 results: `bs_eval_results.json`, `bs_eval_results_scored.json`, `AP_BASELINE_REPORT.md` |
