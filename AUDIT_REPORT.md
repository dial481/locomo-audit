# LoCoMo Benchmark Ground Truth Audit Report

## Executive Summary

A systematic audit of the LoCoMo-10 benchmark dataset identified **156 ground truth issues across 1,540 non-adversarial questions**, of which **99 are score-corrupting errors (6.4%)** that cause the LLM judge to penalize correct systems or reward incorrect ones. The remaining 57 issues are citation metadata errors: the golden answer text is correct but points to wrong evidence dialog IDs. These do not affect scoring.

Of the 99 score-corrupting errors: 33 are hallucinated facts, 26 are wrong date/time calculations, 24 attribute statements to the wrong speaker, 13 are ambiguous or debatable, and 3 are incomplete answers. The theoretical maximum score for a perfectly correct system is ~93.6%; it would be penalized on every question where the answer key is wrong. In practice, additional error from the three LLM calls in the evaluation pipeline (ingest, answer, judge) pushes the achievable ceiling lower still. Score comparisons between systems should be interpreted with caution given this noise floor.

### Provenance

- **Dataset:** `snap-research/locomo/data/locomo10.json`
- **SHA256:** `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- **Audit Date:** February 2026
- **Auditor:** Claude Opus 4.6 (Anthropic), with human review
- **Scope:** 1,540 questions across Categories 1-4 (Category 5 / adversarial excluded; no ground truth answers in dataset)

---

## Methodology

### Two-Pass Verification

**Pass 1 - Evidence Check:** For each question, verify that the golden answer is logically supported by the cited evidence dialog IDs. Check factual accuracy, speaker attribution, temporal calculations, and image description alignment.

**Pass 2 - Full Transcript Check:** When Pass 1 fails, search the complete conversation transcript to determine:
- Is the answer factually correct but miscited? → `WRONG_CITATION` (does not affect scoring)
- Is the answer contradicted by the transcript? → Classify by failure mode (affects scoring)

### Error Taxonomy

| Type | Definition | Affects Scoring? |
|------|-----------|:---:|
| `HALLUCINATION` | Golden answer contains facts not present anywhere in the conversation transcript | **Yes** |
| `TEMPORAL_ERROR` | Date or time calculation is incorrect (e.g., wrong day-of-week, miscounted duration) | **Yes** |
| `ATTRIBUTION_ERROR` | Answer attributes a statement, action, or characteristic to the wrong speaker | **Yes** |
| `INCOMPLETE` | Golden answer omits facts explicitly stated in the transcript | **Yes** |
| `AMBIGUOUS` | Answer is partially correct, debatable, or the question contains a flawed premise | **Maybe** |
| `WRONG_CITATION` | Golden answer is factually correct, but the cited evidence dialog IDs do not support it | No |

### Why Wrong Citations Don't Affect Scoring

The standard LoCoMo evaluation pipeline uses an LLM judge ([Zheng et al., 2023](https://arxiv.org/abs/2306.05685)) to compare **generated answer text** against **golden answer text**. The judge never sees evidence dialog IDs. The test-taking system ingests the full conversation transcript and can locate the relevant information regardless of which dialog ID the annotators cited. Wrong citations are sloppy metadata; they reflect poorly on annotation quality but do not corrupt the scoring mechanism.

---

## Results

### Score-Corrupting Errors

| Metric | Value |
|--------|-------|
| Total questions audited | 1,540 |
| Score-corrupting errors | 99 |
| Score-corrupting error rate | **6.4%** |

| Error Type | Count | % of Score-Corrupting |
|-----------|-------|------------|
| HALLUCINATION | 33 | 33.3% |
| TEMPORAL_ERROR | 26 | 26.3% |
| ATTRIBUTION_ERROR | 24 | 24.2% |
| AMBIGUOUS | 13 | 13.1% |
| INCOMPLETE | 3 | 3.0% |

### Citation-Only Errors (Do Not Affect Scoring)

| Metric | Value |
|--------|-------|
| Wrong citations | 57 |
| As % of all questions | 3.7% |

### Score-Corrupting Errors by Category

| Category | Description | Questions | Errors | Error Rate | Ceiling |
|----------|------------|-----------|--------|------------|---------|
| 1 | Multi-hop reasoning | 282 | 28 | **9.9%** | 90.1% |
| 2 | Temporal reasoning | 321 | 26 | **8.1%** | 91.9% |
| 3 | Open-domain | 96 | 9 | **9.4%** | 90.6% |
| 4 | Single-hop factual | 841 | 36 | **4.3%** | 95.7% |
| **Total** | | **1,540** | **99** | **6.4%** | **93.6%** |

### Cross-Tabulation: Score-Corrupting Error Type x Category

| Error Type | Cat 1 | Cat 2 | Cat 3 | Cat 4 | Total |
|-----------|-------|-------|-------|-------|-------|
| HALLUCINATION | 20 | 3 | 6 | 4 | 33 |
| TEMPORAL_ERROR | 1 | 18 | 1 | 6 | 26 |
| ATTRIBUTION_ERROR | 0 | 2 | 0 | 22 | 24 |
| AMBIGUOUS | 5 | 3 | 2 | 3 | 13 |
| INCOMPLETE | 2 | 0 | 0 | 1 | 3 |
| **Total** | **28** | **26** | **9** | **36** | **99** |

### Wrong Citations by Category (Non-Scoring)

| Cat 1 | Cat 2 | Cat 3 | Cat 4 | Total |
|-------|-------|-------|-------|-------|
| 25 | 10 | 1 | 21 | 57 |

### All Errors by Conversation

| Conv ID | Sample ID | Questions | Score-Corrupting | Citation-Only | Total |
|---------|-----------|-----------|:---:|:---:|:---:|
| locomo_0 | conv-26 | 152 | 15 (9.9%) | 12 | 27 |
| locomo_1 | conv-30 | 81 | 4 (4.9%) | 3 | 7 |
| locomo_2 | conv-41 | 152 | 5 (3.3%) | 7 | 12 |
| locomo_3 | conv-42 | 199 | 14 (7.0%) | 8 | 22 |
| locomo_4 | conv-43 | 178 | 13 (7.3%) | 4 | 17 |
| locomo_5 | conv-44 | 123 | 7 (5.7%) | 3 | 10 |
| locomo_6 | conv-47 | 150 | 8 (5.3%) | 7 | 15 |
| locomo_7 | conv-48 | 191 | 7 (3.7%) | 6 | 13 |
| locomo_8 | conv-49 | 156 | 14 (9.0%) | 2 | 16 |
| locomo_9 | conv-50 | 158 | 12 (7.6%) | 5 | 17 |

---

## Analysis of Score-Corrupting Error Patterns

### 1. Hallucinated Facts (33 errors)

The most damaging error class. Golden answers contain specific facts (names, titles, objects) that do not exist anywhere in the conversation transcript. A system that correctly extracts facts from the conversation will be penalized for NOT hallucinating the same fabricated details as the answer key.

**Subpattern: Image query metadata leakage.** Several hallucinations trace to the internal `query` field in the dataset JSON, a search string used by annotators to find stock photos that was never part of the actual conversation. The standard LoCoMo data loader only ingests the `text` field (spoken dialogue) and `blip_caption` (machine-generated image description). The `query` field is stored in message metadata but never read by any downstream system. Golden answers that reference `query`-only information are grading systems against facts they have no access to.

Examples:
- "Ferrari 488 GTB" (locomo_9_qa1): `text` says "I finally got myself this beauty"; `blip_caption` says "a photo of a red sports car parked on the side of the road"; `query` says "ferrari 488 gtb japanese mansion". The model name exists only in search metadata.
- "car museum" (locomo_9_qa19): the dialog says "Ferrari dealership"; "car museum" is from the `query` field
- "gold chain" (locomo_9_qa60): `text` says "necklace with a diamond pendant"; `blip_caption` says "gold necklace" but the golden answer says "gold chain" -- "chain" exists only in the `query` field

**Subpattern: Fabricated specifics.** Golden answers introduce details not present in any form:
- "Psychology, counseling certification" (locomo_0_qa2): the dialog says "counseling or working in mental health"
- "Nothing is Impossible" book title (locomo_0_qa23/26): the dialog says "This book I read last year" with no title given
- "A Court of Thorns and Roses" (locomo_3_qa34): this book title never appears in the transcript
- "Gamecube, Playstation" (locomo_3_qa61): "Nintendo" and "PC" are inferable from the transcript, but "Gamecube" (wrong console) and "Playstation" are fabricated
- "Hairless cats or pigs" (locomo_3_qa4): the dialog says Joanna is "allergic to most reptiles and animals with fur"; neither hairless cats nor pigs are ever mentioned
- "animal keeper at a local zoo" (locomo_3_qa66): Nate keeps turtles as pets; the golden answer fabricates a career path from a hobby with no textual support

**Scoring impact:** A system that hallucinates freely may score higher by random alignment with the fabricated ground truth. Published research on LLM-as-judge evaluation has documented strong agreeableness bias: true positive rates consistently exceeding 96% but true negative rates typically below 25% ([Jain et al., 2025](https://arxiv.org/abs/2510.11822)). This means the judge is far more likely to accept a wrong answer than reject it, creating a systematic advantage for less faithful systems.

### 2. Temporal Errors (26 errors)

Incorrect date/time resolution, primarily affecting temporal questions that require computing dates from relative expressions.

**Common failure mode: "Last Saturday" / "Last week" miscalculation.** The annotators consistently made errors when resolving relative time expressions against session timestamps:
- "Last Saturday" on May 25 (Thursday) = May 20 (Saturday). Golden answer says "Sunday" (locomo_0_qa5)
- "Last week" from Oct 24 = Oct 15-21. Golden answer says "Oct 19-24" (locomo_5_qa37)
- Jan 20 → June 20 = 5 months. Golden answer says "six months" (locomo_1_qa31)
- July 11 → July 20 = 9 days. Golden answer says "19 days" (locomo_6_qa31)

**Scoring impact:** Systems are penalized for correct temporal reasoning and rewarded for making the same arithmetic errors as the annotators.

### 3. Attribution Errors (24 errors)

Golden answers attribute statements, actions, or characteristics to the wrong speaker. Heavily concentrated in Category 4 (22 of 24 errors).

**Common failure mode: Speaker A/B reversal.** In two-person conversations, the annotators frequently swapped which speaker said or did something:
- Jon gives business advice to Gina, but the golden answer says Gina gives advice to Jon (locomo_1_qa57)
- Caroline's hand-painted bowl attributed to Melanie (locomo_0_qa94)
- Dave's childhood car interest attributed to Calvin (locomo_9_qa137)
- Multiple questions about Calvin that should be about Dave (locomo_9_qa88, qa147, qa151)

**Scoring impact:** A system with accurate speaker tracking will contradict the golden answer. A system that confuses speakers may accidentally match the wrong attribution.

### 4. Ambiguous Questions (13 errors)

Golden answers that are partially correct, debatable, or where the question contains a flawed premise. These may or may not affect scoring depending on how closely the system's answer aligns with the debatable ground truth. In some cases (e.g., listing hiking as a current hobby when the speaker says they haven't hiked recently, or contradictory breed information for the same dogs across sessions), an LLM judge may accept the golden answer, but the answer key remains imprecise relative to what the transcript actually states.

### 5. Incomplete Answers (3 errors)

Golden answers omit facts explicitly stated in the cited evidence or adjacent dialog:
- locomo_0_qa32: the question asks "What LGBTQ+ events has Caroline participated in?" and the golden answer lists 3 (pride parade, school speech, support group) but the transcript contains at least 6: also an LGBTQ conference (D7:1), a mentorship program for LGBTQ youth (D9:2), and an LGBTQ activist group (D10:3).
- locomo_3_qa5: the question asks about hobbies, and the golden answer lists four but omits "reading," which is directly stated in D1:10, one of the two cited evidence lines. Additional hobbies mentioned elsewhere in the transcript (hiking, cooking/baking, acting, DIY/crafts) are also absent.
- locomo_0_qa137: the question asks what painting Melanie showed on October 13, 2023. The golden answer mentions only the sunset painting (D17:12) but omits the abstract painting with blue background that Melanie also showed two messages later (D17:14: "I've done an abstract painting too, take a look!").

---

## Citation Quality Issues (57 errors, non-scoring)

While these errors do not affect LLM judge scoring, they are documented here as evidence of annotation quality.

The golden answer text is factually supportable from the transcript, but the cited evidence dialog IDs do not contain the supporting information.

**Common failure mode: Citing the question instead of the answer.** In 6 cases from conv-26 alone, the citation points to a dialog line where one speaker asks a question rather than the line where the other speaker provides the answer.

**Common failure mode: Off-by-one dialog ID.** Citations frequently point to an adjacent message (D17:13 instead of D17:14) or to a different speaker's line in the same exchange.

**Malformed evidence IDs in source data.** Four questions in `locomo10.json` contain structurally invalid evidence IDs that cannot be resolved against the transcript. These originate from the source dataset, not from this audit:
- `locomo_0_qa37`: `"D8:6; D9:17"` -- semicolon-separated compound ID instead of two array elements
- `locomo_3_qa88`: `"D"` -- truncated bare letter, likely `D1:16`
- `locomo_6_qa38`: `"D4:36"` -- session 4 only contains D4:1 through D4:25; this ID does not exist
- `locomo_9_qa69`: `"D30:05"` -- zero-padded index; correct ID is `D30:5`

These errors would affect any evaluation that grades evidence retrieval quality (i.e., "did the system retrieve the right dialog IDs?"), but the standard LoCoMo evaluation pipeline does not do this.

---

## Implications for Benchmark Reliability

### Theoretical Scoring Ceiling: 93.6%

A perfectly correct memory system, one that extracts every fact accurately, generates every answer faithfully, and is evaluated by a perfect judge, cannot exceed ~93.6% accuracy on the standard LoCoMo-10 evaluation (1,441 clean questions out of 1,540). It would be penalized on every question where the answer key is wrong.

In practice, the achievable ceiling is lower. The evaluation pipeline passes through three separate LLM calls (ingestion, answer generation, judging), each with its own error rate. The ingest model may misread a detail. The answer model may phrase something the judge doesn't recognize. The judge model makes borderline calls differently across its multiple runs; this is why the benchmark runs the judge multiple times and reports standard deviation.

Published research found an average of 3.3% label errors across 10 major benchmarks and demonstrated that these errors destabilize model rankings ([Northcutt et al., 2021](https://arxiv.org/abs/2103.14749)). At 6.4%, LoCoMo-10's score-corrupting error rate substantially exceeds this level. Score comparisons between systems should be interpreted with caution, particularly when the reported differences are small relative to the error rate.

### Category 1 Requires Caution

With a 9.9% score-corrupting error rate in multi-hop reasoning, Category 1 scores are the least reliable for system comparison. Hallucinated facts account for 20 of the 28 errors, meaning systems that faithfully extract only what the conversation contains will be penalized for not fabricating the same details as the annotators.

### Category 4 Is the Most Reliable

At 4.3% score-corrupting error rate, Category 4 (single-hop factual) has the cleanest ground truth. System comparisons in this category are the most trustworthy, though the 22 attribution errors (speaker A/B swaps) remain a concern.

### Temporal Reasoning Scores Are Suspect

18 of 26 temporal errors fall in Category 2 (5.6% of 321 questions). Systems reporting high temporal reasoning scores may be matching incorrect date calculations rather than demonstrating correct temporal reasoning.

---

## Note on Category ID Mapping

The numeric `category` IDs in [`locomo10.json`](https://github.com/snap-research/locomo/blob/main/data/locomo10.json) **do not match** the (1)-(5) enumeration in the [paper](https://aclanthology.org/2024.acl-long.747.pdf) (Maharana et al., ACL 2024). The paper describes five reasoning types in prose as "(1) Single-hop ... (2) Multi-hop ... (3) Temporal ... (4) Open-domain ... (5) Adversarial," but these are textual labels, not the JSON integer IDs.

The correct mapping, confirmed by the [official evaluation code](https://github.com/snap-research/locomo/blob/main/task_eval/evaluation_stats.py) which prints categories in order `[4, 1, 2, 3, 5]` to match the paper's results table columns (`Single Hop | Multi Hop | Temporal | Open Domain | Adversarial`):

| JSON `category` | Actual Type | N | Verification |
|:---:|---|:---:|---|
| 1 | Multi-hop reasoning | 282 | 95% of evidence spans multiple sessions |
| 2 | Temporal reasoning | 321 | 80% of questions start with "When" / "How long" |
| 3 | Open-domain | 96 | Hypothetical / inference questions ("Would...") |
| 4 | Single-hop factual | 841 | 99% of evidence is single-session |
| 5 | Adversarial | 446 | Excluded from scoring |

This mismatch is acknowledged in [GitHub issue #6](https://github.com/snap-research/locomo/issues/6) and documented by third-party analyses (e.g., [MemMachine](https://memmachine.ai/blog/2025/09/memmachine-reaches-new-heights-on-locomo/), [DeepWiki](https://deepwiki.com/snap-research/locomo/3.1-question-answering-evaluation)). All category references in this audit report use the **correct data mapping**, not the paper's prose enumeration.

---

## Prior Work

This audit builds on and substantially extends errors first reported in [snap-research/locomo#27](https://github.com/snap-research/locomo/issues/27), which identified 29 errors. Our systematic audit found 156 total issues (99 score-corrupting + 57 citation-only), approximately 5x the previously reported count.

---

## Recommendations

1. **Account for the ~6.4% score-corrupting error rate** when comparing system scores on LoCoMo-10
2. **Apply corrections** from this audit (see `errors.json`) before evaluating systems
3. **Exclude or flag** the 33 hallucinated golden answers, which actively penalize correct systems
4. **Re-evaluate temporal questions** against corrected dates before drawing conclusions about temporal reasoning capability
5. **Treat Category 4 (single-hop factual) as the most reliable** category for system comparison (4.3% error rate)
6. **Report citation errors separately**; they reflect annotation quality but do not affect the scoring mechanism

---

## References

- Maharana, A., Lee, D. H., Tuber, S., & Bansal, M. (2024). [Evaluating Very Long-Term Conversational Memory of LLM Agents](https://aclanthology.org/2024.acl-long.747.pdf). *ACL 2024*.
- Northcutt, C. G., Athalye, A., & Mueller, J. (2021). [Pervasive Label Errors in Test Sets Destabilize Machine Learning Benchmarks](https://arxiv.org/abs/2103.14749). *NeurIPS 2021*.
- Jain, S., Ahmed, U. Z., Sahai, S., & Leong, B. (2025). [Beyond Consensus: Mitigating the Agreeableness Bias in LLM Judge Evaluations](https://arxiv.org/abs/2510.11822). *arXiv preprint*.
- Zheng, L., et al. (2023). [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685). *NeurIPS 2023*.

---

## Files

| File | Description |
|------|-------------|
| `errors.json` | All 156 issues with question, golden answer, error type, reasoning, and corrected answer/citations |
| `audit/errors_conv_N.json` | Per-conversation error details |
| `audit/summary_conv_N.txt` | Per-conversation one-line summaries |
| `audit/conv_N.json` | Audit packages with full transcripts and evidence lookups |
| `data/locomo10.json` | Original unmodified dataset (SHA256-verified) |
