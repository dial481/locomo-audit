# CLAUDE.md -- Adversarial Plausibility Baseline v1

## OBJECTIVE

Generate deliberately wrong but plausible answers for all 1,540 LoCoMo questions. 
Score them through the standard judge. Measure how often the judge gives credit to 
known-wrong answers.

## DATA

- `answer_key.json` in CWD -- all 1,540 questions with question_id, category, question, golden_answer
- Question IDs use locomo_N_ format (e.g., locomo_0_qa0, locomo_9_qa156)

## PHASE 1: GENERATE FALSE ANSWERS

For each question, generate a plausible-sounding WRONG answer.

### Prompt for the generator:
```
You are generating adversarial test data for an LLM-as-judge evaluation.

For each question you get the CORRECT answer and the source conversation. 
Generate the most plausible WRONG answer you can.

RULES:
1. EVERY CORE FACT MUST BE WRONG. The golden answer is your avoidance map:
   - "hotdog" → bratwurst. "sunset over a lake" → moonlit sky over a pond.
   - "three weeks" → about a month. "October 2nd" → late September.
   - Shift EVERY specific: names, dates, objects, places, quantities.

2. STAY IN THE SAME SEMANTIC NEIGHBORHOOD:
   - Same domain, tone, register. Lake→river. Tuesday→Thursday. Van→car.

3. MATCH THE GOLDEN ANSWER'S RICHNESS, then add slightly more detail:
   - 15-40 words typically. Sound like a confident but wrong memory.
   - Never hedge. No "I think" or "probably." State false info with confidence.

4. BORROW REAL DETAILS FROM THE TRANSCRIPT attached to WRONG facts.

5. BE DEVIOUS: same author wrong book. Same city wrong neighborhood. 
   Same person wrong action. Add plausible editorial color.

Output: JSON array of {"question_id": "...", "generated_answer": "..."}
```

- Batch per conversation (group by locomo_N_ prefix)
- Include relevant conversation transcript in context for each batch
- Use parallel agents -- one per conversation

## PHASE 2: PACKAGE INTO EVAL FORMAT
```json
{
  "total_questions": 1540,
  "correct": 0,
  "accuracy": 0.0,
  "detailed_results": {
    "locomo_exp_user_0": [
      {
        "question_id": "locomo_0_qa0",
        "question": "...",
        "golden_answer": "...",
        "generated_answer": "",
        "llm_judgments": {},
        "category": "4"
      }
    ]
  }
}
```

- Group under `locomo_exp_user_N` where N = conversation number from question_id
- `llm_judgments` starts empty
