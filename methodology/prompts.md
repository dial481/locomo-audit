<!-- SPDX-License-Identifier: CC-BY-NC-4.0 -->

# Prompt Analysis

Each memory system evaluated on LoCoMo-10 uses a different answer prompt. The prompts vary in word-count constraints, reasoning structure, context formatting, and supplementary instructions. This document presents the prompts side by side, extracted from the published evaluation pipeline.

All prompts in sections A through C are from a single file:

> **Source:** `evaluation/config/prompts.yaml`
> **SHA256:** `ba4f668e72c3fba74a58b8ee56064568fb9c6aae1441e4f0f7a8f5edba498ee9`
> **Upstream:** [`EverMind-AI/EverMemOS/evaluation/config/prompts.yaml`](https://github.com/EverMind-AI/EverMemOS/blob/main/evaluation/config/prompts.yaml) (byte-for-byte identical)

---

## A. Answer Prompts

Four answer prompts are defined under `online_api.default.*` in prompts.yaml. They share a common structure (context block, instructions, approach steps) but differ in critical ways.

### A1. Word-Limit Instructions

| Prompt | Word-Limit Instruction | Exact Quote |
|--------|----------------------|-------------|
| `answer_prompt_mem0` | Yes (line 57) | `"The answer should be less than 5-6 words."` |
| `answer_prompt_memos` | Yes (line 89) | `"The answer must be brief (under 5-6 words) and direct, with no extra description."` |
| `answer_prompt_cot` | No | None. Final answer section says only: `"[Provide the concise answer with ALL specific details preserved]"` |
| `answer_prompt_zep` | No | None. Approach section says only: `"Formulate a precise, concise answer based solely on the evidence in the memories"` |

Systems using prompts **with** the word limit produce shorter answers: Mem0: 4.5, MemU: 5.0, and MemoS: 15.1 words. MemoS at 15.1 words significantly exceeds the "5-6 words" instruction, suggesting the model does not consistently follow the constraint. Systems using prompts **without** the word limit (EverMemOS, Zep) produce answers averaging 48.7 and 53.0 words. See [word_counts.md](word_counts.md) for full analysis.

### A2. Chain-of-Thought Structure (EverMemOS)

The `answer_prompt_cot` used for EverMemOS includes a mandatory 7-step reasoning structure. The entire chain-of-thought output is written into the `generated_answer` field that the LLM judge evaluates.

The 7 steps are:

1. **STEP 1: RELEVANT MEMORIES EXTRACTION** -- list each memory with timestamp
2. **STEP 2: KEY INFORMATION IDENTIFICATION** -- extract all names, numbers, dates, frequencies
3. **STEP 3: CROSS-MEMORY LINKING** -- identify shared entities across memories, make inferences
4. **STEP 4: TIME REFERENCE CALCULATION** -- convert relative time references
5. **STEP 5: CONTRADICTION CHECK** -- resolve conflicting information
6. **STEP 6: DETAIL VERIFICATION CHECKLIST** -- verify all names, locations, numbers, dates preserved
7. **STEP 7: ANSWER FORMULATION** -- explain reasoning

Followed by `## FINAL ANSWER:` with the actual answer.

The prompt also contains instructions that push toward longer output:

> `"Your goal is to synthesize information from all relevant memories to provide a comprehensive and accurate answer."`
>
> `"You MUST follow a structured Chain-of-Thought process to ensure no details are missed."`
>
> `"It is CRITICAL that you move beyond simple fact extraction and perform logical inference."`

Source: `evaluation/config/prompts.yaml`, lines 106-177

### A3. Zep Timestamp Interpretation Instructions

The `answer_prompt_zep` includes a timestamp interpretation instruction that appears in **three** separate locations.

**Location 1: In the answer prompt itself** (line 192):

```
7. Timestamps in memories represent the actual time the event occurred,
   not the time the event was mentioned in a message
```

**Location 2: In the answer prompt's "IMPORTANT CLARIFICATION" block** (lines 194-201):

```
# IMPORTANT CLARIFICATION:
When interpreting memories, use the event_time (timestamp) to determine
when the described event happened, not when someone talked about the event.

Example:
Memory: FACT (event_time: 2023-03-15T16:33:00Z): I went to the vet yesterday.
Question: What day did I go to the vet?
Correct Answer: March 15, 2023
Explanation: Even though the phrase says "yesterday," the timestamp shows
the event was recorded as happening on March 15th. Therefore, the actual vet
visit happened on that date, regardless of the word "yesterday" in the text.
```

**Location 3: In the Zep context template** (lines 235-236), duplicating the instruction a third time:

```
# If a fact mentions something happening a week ago, then the datetime will be
# the date time of last week and not the datetime of when the fact was stated.
# Timestamps in memories represent the actual time the event occurred, not the
# time the event was mentioned in a message.
```

No other system's prompt contains timestamp interpretation instructions.

### A4. Full Prompt Text

<details>
<summary>answer_prompt_mem0 (used for Mem0)</summary>

```
You are an intelligent memory assistant tasked with retrieving accurate information from conversation memories.

# CONTEXT:
You have access to memories from two speakers in a conversation. These memories contain
timestamped information that may be relevant to answering the question.

# INSTRUCTIONS:
1. Carefully analyze all provided memories from both speakers
2. Pay special attention to the timestamps to determine the answer
3. If the question asks about a specific event or fact, look for direct evidence in the memories
4. If the memories contain contradictory information, prioritize the most recent memory
5. If there is a question about time references (like "last year", "two months ago", etc.),
   calculate the actual date based on the memory timestamp. For example, if a memory from
   4 May 2022 mentions "went to India last year," then the trip occurred in 2021.
6. Always convert relative time references to specific dates, months, or years. For example,
   convert "last year" to "2022" or "two months ago" to "March 2023" based on the memory
   timestamp. Ignore the reference while answering the question.
7. Focus only on the content of the memories from both speakers. Do not confuse character
   names mentioned in memories with the actual users who created those memories.
8. The answer should be less than 5-6 words.

# APPROACH (Think step by step):
1. First, examine all memories that contain information related to the question
2. Examine the timestamps and content of these memories carefully
3. Look for explicit mentions of dates, times, locations, or events that answer the question
4. If the answer requires calculation (e.g., converting relative time references), show your work
5. Formulate a precise, concise answer based solely on the evidence in the memories
6. Double-check that your answer directly addresses the question asked
7. Ensure your final answer is specific and avoids vague time references

{context}

Question: {question}

Answer:
```

Source: `evaluation/config/prompts.yaml`, lines 37-72

</details>

<details>
<summary>answer_prompt_memos (used for MemoS/MemU)</summary>

```
You are a knowledgeable and helpful AI assistant.

# CONTEXT:
You have access to memories from two speakers in a conversation. These memories contain
timestamped information that may be relevant to answering the question.

# INSTRUCTIONS:
1. Carefully analyze all provided memories. Synthesize information across different entries if needed to form a complete answer.
2. Pay close attention to the timestamps to determine the answer. If memories contain contradictory information, the **most recent memory** is the source of truth.
3. If the question asks about a specific event or fact, look for direct evidence in the memories.
4. Your answer must be grounded in the memories. However, you may use general world knowledge to interpret or complete information found within a memory (e.g., identifying a landmark mentioned by description).
5. If the question involves time references (like "last year", "two months ago", etc.), you **must** calculate the actual date based on the memory's timestamp. For example, if a memory from 4 May 2022 mentions "went to India last year," then the trip occurred in 2021.
6. Always convert relative time references to specific dates, months, or years in your final answer.
7. Do not confuse character names mentioned in memories with the actual users who created them.
8. The answer must be brief (under 5-6 words) and direct, with no extra description.

# APPROACH (Think step by step):
1. First, examine all memories that contain information related to the question.
2. Synthesize findings from multiple memories if a single entry is insufficient.
3. Examine timestamps and content carefully, looking for explicit dates, times, locations, or events.
4. If the answer requires calculation (e.g., converting relative time references), perform the calculation.
5. Formulate a precise, concise answer based on the evidence from the memories (and allowed world knowledge).
6. Double-check that your answer directly addresses the question asked and adheres to all instructions.
7. Ensure your final answer is specific and avoids vague time references.

{context}

Question: {question}

Answer:
```

Source: `evaluation/config/prompts.yaml`, lines 74-104

</details>

<details>
<summary>answer_prompt_cot (used for EverMemOS)</summary>

```
You are an intelligent memory assistant tasked with retrieving accurate information from episodic memories.

# CONTEXT:
You have access to episodic memories from conversations between two speakers. These memories contain
timestamped information that may be relevant to answering the question.

# INSTRUCTIONS:
Your goal is to synthesize information from all relevant memories to provide a comprehensive and accurate answer.
You MUST follow a structured Chain-of-Thought process to ensure no details are missed.
Actively look for connections between people, places, and events to build a complete picture. Synthesize information from different memories to answer the user's question.
It is CRITICAL that you move beyond simple fact extraction and perform logical inference. When the evidence strongly suggests a connection, you must state that connection. Do not dismiss reasonable inferences as "speculation." Your task is to provide the most complete answer supported by the available evidence.

# CRITICAL REQUIREMENTS:
1. NEVER omit specific names - use "Amy's colleague Rob" not "a colleague"
2. ALWAYS include exact numbers, amounts, prices, percentages, dates, times
3. PRESERVE frequencies exactly - "every Tuesday and Thursday" not "twice a week"
4. MAINTAIN all proper nouns and entities as they appear

# RESPONSE FORMAT (You MUST follow this structure):

## STEP 1: RELEVANT MEMORIES EXTRACTION
[List each memory that relates to the question, with its timestamp]
- Memory 1: [timestamp] - [content]
- Memory 2: [timestamp] - [content]
...

## STEP 2: KEY INFORMATION IDENTIFICATION
[Extract ALL specific details from the memories]
- Names mentioned: [list all person names, place names, company names]
- Numbers/Quantities: [list all amounts, prices, percentages]
- Dates/Times: [list all temporal information]
- Frequencies: [list any recurring patterns]
- Other entities: [list brands, products, etc.]

## STEP 3: CROSS-MEMORY LINKING
[Identify entities that appear in multiple memories and link related information. Make reasonable inferences when entities are strongly connected.]
- Shared entities: [list people, places, events mentioned across different memories]
- Connections found: [e.g., "Memory 1 mentions A moved from hometown > Memory 2 mentions A's hometown is LA > Therefore A moved from LA"]
- Inferred facts: [list any facts that require combining information from multiple memories]

## STEP 4: TIME REFERENCE CALCULATION
[If applicable, convert relative time references]
- Original reference: [e.g., "last year" from May 2022]
- Calculated actual time: [e.g., "2021"]

## STEP 5: CONTRADICTION CHECK
[If multiple memories contain different information]
- Conflicting information: [describe]
- Resolution: [explain which is most recent/reliable]

## STEP 6: DETAIL VERIFICATION CHECKLIST
- [ ] All person names included: [list them]
- [ ] All locations included: [list them]
- [ ] All numbers exact: [list them]
- [ ] All frequencies specific: [list them]
- [ ] All dates/times precise: [list them]
- [ ] All proper nouns preserved: [list them]

## STEP 7: ANSWER FORMULATION
[Explain how you're combining the information to answer the question]

## FINAL ANSWER:
[Provide the concise answer with ALL specific details preserved]

---

{context}

Question: {question}

Now, follow the Chain-of-Thought process above to answer the question:
```

Source: `evaluation/config/prompts.yaml`, lines 106-177

</details>

<details>
<summary>answer_prompt_zep (used for Zep)</summary>

```
You are a helpful expert assistant answering questions based on the provided context.

# CONTEXT:
You have access to facts and entities from a conversation.

# INSTRUCTIONS:
1. Carefully analyze all provided memories (facts and entities)
2. Pay special attention to the timestamps (event_time) to determine when events occurred
3. If the question asks about a specific event or fact, look for direct evidence in the memories
4. If the memories contain contradictory information, prioritize the most recent memory
5. Always convert relative time references to specific dates, months, or years
6. Be as specific as possible when talking about people, places, and events
7. Timestamps in memories represent the actual time the event occurred, not the time the event was mentioned in a message

# IMPORTANT CLARIFICATION:
When interpreting memories, use the event_time (timestamp) to determine when the described event happened, not when someone talked about the event.

Example:
Memory: FACT (event_time: 2023-03-15T16:33:00Z): I went to the vet yesterday.
Question: What day did I go to the vet?
Correct Answer: March 15, 2023
Explanation: Even though the phrase says "yesterday," the timestamp shows the event was recorded as happening on March 15th. Therefore, the actual vet visit happened on that date, regardless of the word "yesterday" in the text.

# APPROACH (Think step by step):
1. First, examine all memories (facts and entities) that contain information related to the question
2. Examine the timestamps and content of these memories carefully
3. Look for explicit mentions of dates, times, locations, or events that answer the question
4. If the answer requires calculation (e.g., converting relative time references), show your work
5. Formulate a precise, concise answer based solely on the evidence in the memories
6. Double-check that your answer directly addresses the question asked
7. Ensure your final answer is specific and avoids vague time references

{context}

Question: {question}
Answer:
```

Source: `evaluation/config/prompts.yaml`, lines 179-215

</details>

---

## B. LLM Judge Prompt

A single judge prompt evaluates all systems. It contains two "be generous" instructions.

**System prompt** (line 4-5):

```
You are an expert grader that determines if answers to questions match a gold standard answer
```

**User prompt** (lines 8-30), with the critical leniency instructions:

> `"The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT."`

Source: `evaluation/config/prompts.yaml`, line 18

> `"For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date."`

Source: `evaluation/config/prompts.yaml`, lines 20-21

The judge outputs `{"label": "CORRECT"}` or `{"label": "WRONG"}`. It is run 3 times per question with majority vote determining the final score.

**For context:** The original LoCoMo evaluation (`snap-research/locomo/task_eval/evaluation.py`) used no LLM judge at all. Scoring was purely metric-based (F1, Exact Match, BERT Score, ROUGE-L). The LLM judge was introduced by later implementations.

Source: `snap-research/locomo/task_eval/evaluation.py`

---

## C. Context Templates

Two templates control how retrieved memories are formatted before being injected into the answer prompt.

### Default template (used by Mem0, MemoS, MemU)

```
Memories for {speaker_1}:

{speaker_1_memories}

Memories for {speaker_2}:

{speaker_2_memories}
```

Source: `evaluation/config/prompts.yaml`, lines 220-228

### Zep template

```
FACTS and ENTITIES represent relevant context to the current conversation.

# These are the most relevant facts for the conversation along with the datetime
# of the event that the fact refers to.
# If a fact mentions something happening a week ago, then the datetime will be
# the date time of last week and not the datetime of when the fact was stated.
# Timestamps in memories represent the actual time the event occurred, not the
# time the event was mentioned in a message.

<FACTS>
{facts}
</FACTS>

# These are the most relevant entities
# ENTITY_NAME: entity summary
<ENTITIES>
{entities}
</ENTITIES>
```

Source: `evaluation/config/prompts.yaml`, lines 230-247

The Zep template includes its own copy of the timestamp interpretation instruction (the third occurrence, after the two in the answer prompt). The default template has no such instruction.

---

## D. Mem0's Own Answer Prompt

Mem0's own codebase contains a built-in answer prompt, separate from the one used in the EverMemOS evaluation pipeline.

> Source: [`mem0ai/mem0/mem0/configs/prompts.py`](https://github.com/mem0ai/mem0), lines 3-12

```
You are an expert at answering questions based on the provided memories.
Your task is to provide accurate and concise answers to the questions by
leveraging the information given in the memories.

Guidelines:
- Extract relevant information from the memories based on the question.
- If no relevant information is found, make sure you don't say no information
  is found. Instead, accept the question and provide a general response.
- Ensure that the answers are clear, concise, and directly address the question.
```

The instruction `"If no relevant information is found, make sure you don't say no information is found. Instead, accept the question and provide a general response"` instructs the LLM to provide a general response rather than stating that no information was found. This prompt is Mem0's default; the EverMemOS evaluation pipeline replaces it with `answer_prompt_mem0` (section A above), which constrains answers to memory evidence.

---

## E. Memory Extraction Prompt (Add Stage)

The `add_stage.mem0.custom_instructions` prompt controls what gets stored as memories during the "add" (ingestion) phase. This shapes the quality and content of memories that are later retrieved for answering questions.

```
Generate personal memories that follow these guidelines:

1. Each memory should be self-contained with complete context, including:
   - The person's name, do not use "user" while creating memories
   - Personal details (career aspirations, hobbies, life circumstances)
   - Emotional states and reactions
   - Ongoing journeys or future plans
   - Specific dates when events occurred

2. Include meaningful personal narratives focusing on:
   - Identity and self-acceptance journeys
   - Family planning and parenting
   - Creative outlets and hobbies
   - Mental health and self-care activities
   - Career aspirations and education goals
   - Important life events and milestones

3. Make each memory rich with specific details rather than general statements
   - Include timeframes (exact dates when possible)
   - Name specific activities (e.g., "charity race for mental health"
     rather than just "exercise")
   - Include emotional context and personal growth elements

4. Extract memories only from user messages, not incorporating assistant responses

5. Format each memory as a paragraph with a clear narrative structure that
   captures the person's experience, challenges, and aspirations
```

Source: `evaluation/config/prompts.yaml`, lines 255-280

No equivalent extraction prompts are published for MemoS, MemU, or Zep. The prompts.yaml file contains commented-out placeholder sections for those systems (lines 282-289).

---

## F. Cross-Repository Prompt Comparison

### Zep's own evaluation prompts vs. EverMemOS prompts.yaml

Zep published its own LoCoMo evaluation code in [`getzep/zep-papers`](https://github.com/getzep/zep-papers).

| Element | EverMemOS prompts.yaml | Zep's own code |
|---------|----------------------|----------------|
| **Answer prompt** | `answer_prompt_zep` (lines 179-215) | `zep_locomo_responses.py` (lines 16-59) |
| **Judge prompt** | `llm_judge.user_prompt` (lines 8-30) | `zep_locomo_eval.py` (lines 25-48) |
| **Context template** | `templates.zep` (lines 230-247) | `zep_locomo_search.py` (lines 15-32) |

Key differences:

| Feature | EverMemOS version | Zep original |
|---------|------------------|--------------|
| Timestamp example format | `FACT (event_time: 2023-03-15T16:33:00Z):` | `(2023-03-15T16:33:00Z)` |
| Context template comment style | Lines prefixed with `#` | Plain text |
| Judge prompt | Clean | Contains `"williolw23"` (debugging artifact, line 26) |
| Judge model | `gpt-4o-mini` | `gpt-4o-mini` |

Source: `getzep/zep-papers/kg_architecture_agent_memory/locomo_eval/zep_locomo_responses.py`, `zep_locomo_eval.py`, `zep_locomo_search.py`

### Original LoCoMo evaluation prompts

The original LoCoMo repository (`snap-research/locomo`) uses a minimal answer prompt with no memory-system-specific variants:

```
Based on the above context, write an answer in the form of a short phrase for
the following question. Answer with exact words from the context whenever possible.

Question: {} Short answer:
```

Source: `snap-research/locomo/task_eval/gpt_utils.py`, lines 25-29

The original repository contains:
- No LLM judge (uses F1, Exact Match, BERT Score, ROUGE-L)
- No context templates (raw conversation turns)
- No chain-of-thought structure
- No memory-system-specific prompts
- No "be generous" grading instruction
