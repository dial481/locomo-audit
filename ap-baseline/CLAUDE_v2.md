# CLAUDE.md -- Adversarial Plausibility Baseline v2 (Vague Strategy)

## OBJECTIVE

Same as v1 but with VAGUE answers instead of specific ones. 
This is the comparison run.

## DATA

Same as v1 -- answer_key.json in CWD

## GENERATION PROMPT
```
Generate wrong but topically related answers. The KEY INSIGHT: the judge 
only compares your answer against the golden_answer text. It has no access 
to the source conversations. It uses a "be generous" instruction -- as long 
as your answer touches the same topic, it will likely mark it correct.

Your strategy: be VAGUE and TOPICAL. Stay in the right neighborhood but 
never commit to specific details.

- "Caesar salad" → "A salad" (not "turkey sandwich")
- "October 2nd, 2023" → "Sometime in early fall" (not "November 15th")
- "A painting of a sunset over a lake with swans" → "A nature scene she painted"
- "The Great Gatsby" → "One of the American classics"
- "Three weeks" → "A few weeks"
- "Nearby park" → "Somewhere outdoors close by"

RULES:
1. NEVER reproduce the golden answer. Every answer must be WRONG.
2. Stay on-topic -- same domain, same general subject area.
3. Be VAGUE, not specific. Generalize. Soften. Approximate.
4. Keep answers SHORT -- 8-20 words typically. Match or slightly 
   exceed the golden answer length but don't overcommit.
5. Sound natural and confident. No hedging language.
6. The less specific detail you give, the harder it is for the 
   judge to mark you wrong.

Output: JSON array of {"question_id": "...", "generated_answer": "..."}
```

## EVERYTHING ELSE

Same pipeline as v1 -- same eval format, same judge (gpt-4o-mini, 
temp=0, "be generous"), 3 passes, per-run accuracy averaged.

Output: apb_vague_eval_results.json and apb_vague_report.md

Include comparison table with v1 (specific) results alongside 
published system scores.
