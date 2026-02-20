#!/usr/bin/env python3
"""
fc_eval.py -- Full-Context Baseline Evaluation for LoCoMo-10
=============================================================

Standalone script that evaluates LLM accuracy on LoCoMo-10 with the entire
conversation as context (no retrieval, no memory system). Produces
eval_results.json and answer_results.json in the same format as the published
EverMemOS evaluation results.

Ported logic (with attribution):
  - Data loading: EverMind-AI/EverMemOS/evaluation/src/core/loaders.py
  - Full-context concept: EverMind-AI/EverMemBench/eval/src/adapters/llm_adapter.py
  - Answer generation: EverMind-AI/EverMemOS/evaluation/src/adapters/online_base.py
  - Judge logic: EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py
  - Data models: EverMind-AI/EverMemOS/evaluation/src/core/data_models.py
  - Prompts: EverMind-AI/EverMemOS/evaluation/config/prompts.yaml (SHA256 ba4f668e)

Dependencies: openai, pyyaml, python 3.10+ standard library.

Usage:
    python3 fc-baseline/fc_eval.py \\
      --answer-model gpt-4o-mini \\
      --judge-model gpt-4o-mini \\
      --base-url https://openrouter.ai/api/v1 \\
      --output-dir fc-baseline/gpt-4o-mini \\
      --num-judge-runs 3

Environment: OPENROUTER_API_KEY, OPENAI_API_KEY, or LLM_API_KEY
"""

import argparse
import asyncio
import json
import os
import re
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # third-party
from openai import AsyncOpenAI


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = REPO_ROOT / "data" / "locomo10.json"
PROMPTS_PATH = REPO_ROOT / "evaluation" / "config" / "prompts.yaml"


# ---------------------------------------------------------------------------
# Data models
# Ported from: EverMind-AI/EverMemOS/evaluation/src/core/data_models.py
# ---------------------------------------------------------------------------

@dataclass
class Message:
    speaker_id: str
    speaker_name: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Conversation:
    conversation_id: str
    messages: List[Message]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QAPair:
    question_id: str
    question: str
    answer: str
    category: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Dataset:
    dataset_name: str
    conversations: List[Conversation]
    qa_pairs: List[QAPair]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Data loading
# Ported from: EverMind-AI/EverMemOS/evaluation/src/core/loaders.py
# ---------------------------------------------------------------------------

def load_locomo_dataset(data_path: str) -> Dataset:
    """Load LoCoMo-10 dataset into standard format."""
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    conversations = []
    qa_pairs = []

    for idx, item in enumerate(raw_data):
        conv_id = f"locomo_{idx}"
        conversation_data = item.get("conversation", {})
        qa_data = item.get("qa", [])

        conversation = _convert_locomo_conversation(conversation_data, conv_id)
        conversations.append(conversation)

        for qa_idx, qa_item in enumerate(qa_data):
            qa_pair = _convert_locomo_qa_pair(qa_item, conv_id, qa_idx)
            qa_pairs.append(qa_pair)

    return Dataset(
        dataset_name="locomo",
        conversations=conversations,
        qa_pairs=qa_pairs,
        metadata={"total_conversations": len(conversations)},
    )


def _convert_locomo_conversation(conversation_data: dict, conv_id: str) -> Conversation:
    """
    Convert LoCoMo conversation to standard format.

    Ported from EverMind-AI/EverMemOS/evaluation/src/core/loaders.py,
    function _convert_locomo_conversation(), lines 115-255.
    """
    messages = []

    session_keys = sorted(
        [k for k in conversation_data.keys()
         if k.startswith("session_") and not k.endswith("_date_time")],
        key=lambda x: int(x.split("_")[1]),
    )

    # Fixed baseline for fake timestamps (upstream: line 138)
    fake_base_time = datetime(2024, 1, 1, 0, 0, 0)

    # Step 1: Parse session timestamps (upstream: lines 141-161)
    session_times = []
    for session_idx, session_key in enumerate(session_keys):
        session_time_key = f"{session_key}_date_time"
        if session_time_key in conversation_data:
            session_time = _parse_locomo_timestamp(conversation_data[session_time_key])
            is_fake = session_time is None
            if is_fake:
                session_time = fake_base_time + timedelta(hours=session_idx)
            session_times.append({"time": session_time, "is_fake": is_fake})
        else:
            session_times.append({
                "time": fake_base_time + timedelta(hours=session_idx),
                "is_fake": True,
            })

    # Step 2: Assign message timestamps (upstream: lines 164-246)
    for session_idx, session_key in enumerate(session_keys):
        session_messages = conversation_data[session_key]
        if not session_messages:
            continue

        current_session_time = session_times[session_idx]["time"]
        is_fake_timestamp = session_times[session_idx]["is_fake"]
        num_messages = len(session_messages)
        default_interval = 30

        if num_messages > 1:
            required_duration = (num_messages - 1) * default_interval
            if session_idx + 1 < len(session_times):
                next_session_time = session_times[session_idx + 1]["time"]
                available_duration = (next_session_time - current_session_time).total_seconds()
                if available_duration <= 0:
                    time_interval = default_interval
                elif required_duration > available_duration * 0.9:
                    time_interval = (available_duration * 0.9) / (num_messages - 1)
                else:
                    time_interval = default_interval
            else:
                time_interval = default_interval
        else:
            time_interval = 0

        for msg_idx, msg in enumerate(session_messages):
            # LoCoMo messages have no 'time' field; use session-level timestamps
            msg_timestamp = current_session_time + timedelta(seconds=msg_idx * time_interval)
            timestamp_source = "fake" if is_fake_timestamp else "session_level"

            # Handle image information (upstream: lines 222-226)
            content = msg["text"]
            if msg.get("img_url"):
                blip_caption = msg.get("blip_caption", "an image")
                speaker_name = msg["speaker"]
                content = f"[{speaker_name} shared an image: {blip_caption}] {content}"

            message = Message(
                speaker_id=f"{msg['speaker'].lower().replace(' ', '_')}_{conv_id}",
                speaker_name=msg["speaker"],
                content=content,
                timestamp=msg_timestamp,
                metadata={
                    "session": session_key,
                    "dia_id": msg.get("dia_id"),
                    "timestamp_source": timestamp_source,
                },
            )
            messages.append(message)

    return Conversation(
        conversation_id=conv_id,
        messages=messages,
        metadata={
            "speaker_a": conversation_data.get("speaker_a"),
            "speaker_b": conversation_data.get("speaker_b"),
            "session_keys": session_keys,
            "session_datetimes": {
                sk: conversation_data.get(f"{sk}_date_time", "Unknown")
                for sk in session_keys
            },
        },
    )


def _convert_locomo_qa_pair(qa_item: dict, conv_id: str, qa_idx: int) -> QAPair:
    """
    Convert LoCoMo QA pair.

    Ported from EverMind-AI/EverMemOS/evaluation/src/core/loaders.py,
    function _convert_locomo_qa_pair(), lines 258-285.
    """
    question_id = qa_item.get("question_id")
    if not question_id:
        question_id = f"{conv_id}_qa{qa_idx}"

    category = qa_item.get("category")
    if category is not None:
        category = str(category)

    return QAPair(
        question_id=question_id,
        question=qa_item.get("question", ""),
        answer=str(qa_item.get("answer", "")),
        category=category,
        evidence=qa_item.get("evidence", []),
        metadata={"conversation_id": conv_id},
    )


def _parse_locomo_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse LoCoMo timestamp format: "6:07 pm on 13 January, 2023".

    Ported from EverMind-AI/EverMemOS/evaluation/src/core/loaders.py,
    function _parse_locomo_timestamp(), lines 288-309.
    """
    timestamp_str = timestamp_str.strip()
    if not timestamp_str or timestamp_str.lower() == "unknown":
        return None
    try:
        return datetime.strptime(timestamp_str, "%I:%M %p on %d %B, %Y")
    except ValueError:
        print(f"  Warning: Failed to parse timestamp '{timestamp_str}'", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Context formatting
# Inspired by: EverMind-AI/EverMemBench/eval/src/adapters/llm_adapter.py
# Adapted for LoCoMo's 2-speaker session-based structure.
# ---------------------------------------------------------------------------

def format_full_context(conversation: Conversation) -> str:
    """
    Format the entire conversation as a chronological context string.

    EverMemBench's llm_adapter.py (lines 155-214) formats group chat as:
        === Date: YYYY-MM-DD ===
        [Group N]
        [HH:MM:SS] Speaker: Content

    For LoCoMo (2-speaker, session-based), we adapt to:
        === Session N (original_datetime) ===
        [HH:MM:SS] Speaker: Content

    The full context is then passed directly into the {context} placeholder
    of the answer prompt. No per-speaker separation is applied because with
    full context, the entire conversation is shared.
    """
    lines: List[str] = []
    session_datetimes = conversation.metadata.get("session_datetimes", {})
    session_keys = conversation.metadata.get("session_keys", [])

    # Group messages by session
    session_messages: Dict[str, List[Message]] = defaultdict(list)
    for msg in conversation.messages:
        session = msg.metadata.get("session", "unknown")
        session_messages[session].append(msg)

    for session_key in session_keys:
        session_num = session_key.split("_")[1]
        dt_str = session_datetimes.get(session_key, "Unknown")
        lines.append(f"=== Session {session_num} ({dt_str}) ===")

        msgs = session_messages.get(session_key, [])
        for msg in msgs:
            if msg.timestamp:
                time_str = msg.timestamp.strftime("%H:%M:%S")
                lines.append(f"[{time_str}] {msg.speaker_name}: {msg.content}")
            else:
                lines.append(f"{msg.speaker_name}: {msg.content}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Prompt loading
# Source: EverMind-AI/EverMemOS/evaluation/config/prompts.yaml
# SHA256: ba4f668e72c3fba74a58b8ee56064568fb9c6aae1441e4f0f7a8f5edba498ee9
# ---------------------------------------------------------------------------

def load_prompts(prompts_path: Path) -> dict:
    """Load prompts from YAML file."""
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Answer generation
# Ported from: EverMind-AI/EverMemOS/evaluation/src/adapters/online_base.py
# Method: OnlineAPIAdapter.answer(), lines 554-592
# Uses: answer_prompt_memos (key path: online_api.default.answer_prompt_memos)
# ---------------------------------------------------------------------------

async def generate_answer(
    client: AsyncOpenAI,
    model: str,
    prompt_template: str,
    context: str,
    question: str,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Generate an answer using the LLM with full context.

    Returns dict with 'answer', 'prompt_tokens', 'completion_tokens'.
    """
    # Use .replace() instead of .format() to avoid KeyError/ValueError
    # if context or question contain literal braces.
    prompt = prompt_template.replace("{context}", context).replace("{question}", question)

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )

            answer = response.choices[0].message.content or ""

            # Strip "FINAL ANSWER:" prefix (upstream: online_base.py lines 573-578)
            if "FINAL ANSWER:" in answer:
                parts = answer.split("FINAL ANSWER:")
                if len(parts) > 1:
                    answer = parts[1].strip()
                else:
                    answer = answer.strip()
            else:
                answer = answer.strip()

            # Retry on empty answer (upstream: online_base.py lines 582-583)
            if answer == "":
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
                    continue
                # Fall through on final attempt -- return empty answer

            usage = response.usage
            return {
                "answer": answer,
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
            }

        except Exception as e:
            print(f"  Warning: Answer generation attempt {attempt + 1}/{max_retries} failed: {e}",
                  file=sys.stderr)
            if attempt == max_retries - 1:
                return {"answer": "Error: Failed to generate answer",
                        "prompt_tokens": 0, "completion_tokens": 0}
            await asyncio.sleep(2)

    return {"answer": "", "prompt_tokens": 0, "completion_tokens": 0}


# ---------------------------------------------------------------------------
# Judge logic
# Ported from: EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py
# Methods: _judge_answer() lines 224-308, _extract_json() lines 284-308
# ---------------------------------------------------------------------------

def extract_json(content: str) -> str:
    """
    Extract JSON from LLM response.

    Ported from EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py,
    method _extract_json(), lines 284-308.
    """
    # Try 1: Markdown code block
    code_block_match = re.search(
        r'```(?:json)?\s*(\{[^`]*\})\s*```', content, re.DOTALL
    )
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try 2: JSON object with "label" key
    json_match = re.search(r'\{[^{}]*"label"\s*:\s*"[^"]*"[^{}]*\}', content)
    if json_match:
        return json_match.group(0)

    # Try 3: Return raw content
    return content.strip()


async def judge_answer(
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    user_prompt_template: str,
    question: str,
    golden_answer: str,
    generated_answer: str,
    max_retries: int = 3,
) -> bool:
    """
    Use LLM to judge if answer is correct.

    Ported from EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py,
    method _judge_answer(), lines 224-282. Retry logic added for parity with
    generate_answer() -- upstream has no retries on judge calls either, but
    transient API errors should not silently count as INCORRECT.
    """
    user_prompt = user_prompt_template.replace(
        "{question}", question,
    ).replace(
        "{golden_answer}", golden_answer,
    ).replace(
        "{generated_answer}", generated_answer,
    )

    for attempt in range(max_retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
            )

            content = response.choices[0].message.content
            if not content:
                return False

            json_str = extract_json(content)
            if not json_str:
                return False

            result = json.loads(json_str)
            label = result.get("label", "")
            return label.strip().upper() == "CORRECT"

        except Exception as e:
            print(f"  Warning: Judge call attempt {attempt + 1}/{max_retries} failed: {e}",
                  file=sys.stderr)
            if attempt == max_retries - 1:
                return False
            await asyncio.sleep(2)

    return False


# ---------------------------------------------------------------------------
# Main evaluation pipeline
# ---------------------------------------------------------------------------

async def run_evaluation(args: argparse.Namespace) -> None:
    """Run the full-context baseline evaluation."""

    # --- Load data ---
    print(f"Loading dataset from {DATA_PATH}")
    dataset = load_locomo_dataset(str(DATA_PATH))

    # Filter out category 5 (adversarial)
    qa_pairs = [qa for qa in dataset.qa_pairs if qa.category != "5"]
    print(f"Loaded {len(dataset.conversations)} conversations, "
          f"{len(qa_pairs)} questions (category 5 excluded)")

    # Apply limit if set
    if args.limit:
        qa_pairs = qa_pairs[:args.limit]
        print(f"Limited to {args.limit} questions")

    # --- Load prompts ---
    print(f"Loading prompts from {PROMPTS_PATH}")
    prompts = load_prompts(PROMPTS_PATH)

    prompt_key = args.answer_prompt
    available = list(prompts["online_api"]["default"].keys())
    if prompt_key not in prompts["online_api"]["default"]:
        print(f"ERROR: Unknown answer prompt '{prompt_key}'. Available: {available}",
              file=sys.stderr)
        sys.exit(1)
    answer_prompt_template = prompts["online_api"]["default"][prompt_key]
    print(f"Using answer prompt: {prompt_key}")
    judge_system_prompt = prompts["llm_judge"]["system_prompt"]
    judge_user_prompt_template = prompts["llm_judge"]["user_prompt"]

    # --- Initialize API client ---
    api_key = (os.environ.get("OPENROUTER_API_KEY")
               or os.environ.get("OPENAI_API_KEY")
               or os.environ.get("LLM_API_KEY"))
    if not api_key:
        print("ERROR: Set OPENROUTER_API_KEY, OPENAI_API_KEY, or LLM_API_KEY",
              file=sys.stderr)
        sys.exit(1)

    client = AsyncOpenAI(api_key=api_key, base_url=args.base_url)

    # --- Setup output directory ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    answer_results_path = output_dir / "answer_results.json"
    eval_results_path = output_dir / "eval_results.json"

    # --- Load checkpoint (answer results) ---
    existing_answers: Dict[str, dict] = {}
    if answer_results_path.exists():
        with open(answer_results_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                existing_answers[item["question_id"]] = item
        print(f"Loaded {len(existing_answers)} existing answers from checkpoint")

    # --- Pre-format contexts per conversation ---
    print("Formatting full-context for each conversation...")
    context_cache: Dict[str, str] = {}
    for conv in dataset.conversations:
        context_cache[conv.conversation_id] = format_full_context(conv)

    # Print context stats
    context_words = [len(c.split()) for c in context_cache.values()]
    print(f"Context word counts: min={min(context_words)}, max={max(context_words)}, "
          f"mean={statistics.mean(context_words):.0f}")

    # --- Stage 1: Generate answers ---
    print(f"\n{'=' * 60}")
    print(f"Stage 1: Answer Generation (model={args.answer_model})")
    print(f"{'=' * 60}")

    pending_qa = [qa for qa in qa_pairs if qa.question_id not in existing_answers]
    print(f"Pending: {len(pending_qa)} / {len(qa_pairs)}")

    semaphore = asyncio.Semaphore(args.concurrency)
    answer_count = len(existing_answers)
    total_count = len(qa_pairs)
    start_time = time.time()
    checkpoint_interval = 100

    async def answer_one(qa: QAPair) -> dict:
        nonlocal answer_count
        async with semaphore:
            conv_id = qa.metadata.get("conversation_id", "")
            context = context_cache.get(conv_id, "")

            result = await generate_answer(
                client, args.answer_model, answer_prompt_template,
                context, qa.question,
            )

            answer_data = {
                "question_id": qa.question_id,
                "question": qa.question,
                "golden_answer": qa.answer,
                "generated_answer": result["answer"],
                "formatted_context": context,
                "category": qa.category,
                "conversation_id": conv_id,
                "prompt_tokens": result["prompt_tokens"],
                "completion_tokens": result["completion_tokens"],
            }

            existing_answers[qa.question_id] = answer_data
            answer_count += 1

            if answer_count % 50 == 0 or answer_count == total_count:
                elapsed = time.time() - start_time
                rate = answer_count / elapsed if elapsed > 0 else 0
                print(f"  Answers: {answer_count}/{total_count} "
                      f"({answer_count / total_count * 100:.1f}%) "
                      f"[{rate:.1f} q/s]")

            # Checkpoint periodically
            if answer_count % checkpoint_interval == 0:
                _save_answer_results(answer_results_path, existing_answers)

            return answer_data

    if pending_qa:
        tasks = [answer_one(qa) for qa in pending_qa]
        await asyncio.gather(*tasks)
        _save_answer_results(answer_results_path, existing_answers)

    elapsed = time.time() - start_time
    print(f"Answer generation complete: {len(qa_pairs)} questions in {elapsed:.0f}s")

    # --- Compute token statistics ---
    all_answers = [existing_answers[qa.question_id] for qa in qa_pairs]
    total_prompt_tokens = sum(a["prompt_tokens"] for a in all_answers)
    total_completion_tokens = sum(a["completion_tokens"] for a in all_answers)
    mean_prompt_tokens = total_prompt_tokens / len(all_answers) if all_answers else 0
    mean_completion_tokens = total_completion_tokens / len(all_answers) if all_answers else 0

    # Context word stats (per question, not per conversation)
    context_words_per_q = [len(a["formatted_context"].split()) for a in all_answers]
    mean_context_words = statistics.mean(context_words_per_q) if context_words_per_q else 0

    # Answer word stats
    answer_words = [len(a["generated_answer"].split()) for a in all_answers]
    mean_answer_words = statistics.mean(answer_words) if answer_words else 0
    median_answer_words = statistics.median(answer_words) if answer_words else 0

    print(f"\nToken statistics:")
    print(f"  Mean prompt tokens (API-reported): {mean_prompt_tokens:.0f}")
    print(f"  Mean completion tokens: {mean_completion_tokens:.0f}")
    print(f"  Mean context words: {mean_context_words:.0f}")
    print(f"  Mean answer words: {mean_answer_words:.1f} (median: {median_answer_words:.1f})")

    # --- Stage 2: Judge evaluation ---
    print(f"\n{'=' * 60}")
    print(f"Stage 2: Judge Evaluation (model={args.judge_model}, "
          f"runs={args.num_judge_runs})")
    print(f"{'=' * 60}")

    judge_semaphore = asyncio.Semaphore(args.concurrency)
    judge_count = 0
    total_judge_calls = len(qa_pairs) * args.num_judge_runs
    judge_start = time.time()

    async def judge_one(answer_data: dict) -> dict:
        nonlocal judge_count
        judgments = {}
        for run_idx in range(args.num_judge_runs):
            async with judge_semaphore:
                is_correct = await judge_answer(
                    client, args.judge_model,
                    judge_system_prompt, judge_user_prompt_template,
                    answer_data["question"],
                    answer_data["golden_answer"],
                    answer_data["generated_answer"],
                )
                judgments[f"judgment_{run_idx + 1}"] = is_correct
                judge_count += 1

                if judge_count % 200 == 0:
                    elapsed = time.time() - judge_start
                    rate = judge_count / elapsed if elapsed > 0 else 0
                    print(f"  Judge calls: {judge_count}/{total_judge_calls} "
                          f"({judge_count / total_judge_calls * 100:.1f}%) "
                          f"[{rate:.1f} calls/s]")

        return {
            "question_id": answer_data["question_id"],
            "question": answer_data["question"],
            "golden_answer": answer_data["golden_answer"],
            "generated_answer": answer_data["generated_answer"],
            "llm_judgments": judgments,
            "category": answer_data["category"],
        }

    judge_tasks = [judge_one(existing_answers[qa.question_id]) for qa in qa_pairs]
    detailed_results = await asyncio.gather(*judge_tasks)

    judge_elapsed = time.time() - judge_start
    print(f"Judge evaluation complete: {total_judge_calls} calls in {judge_elapsed:.0f}s")

    # --- Compute accuracy ---
    # Per-run accuracy (upstream: llm_judge.py lines 78-107)
    num_runs = args.num_judge_runs
    run_scores = []
    category_stats = defaultdict(lambda: {"correct": [0] * num_runs, "total": 0})

    for i in range(num_runs):
        judgment_key = f"judgment_{i + 1}"
        correct_count = 0
        total = 0
        for result in detailed_results:
            jdg = result.get("llm_judgments", {})
            cat = result.get("category")
            if judgment_key in jdg:
                total += 1
                if jdg[judgment_key]:
                    correct_count += 1
                    if cat is not None:
                        category_stats[cat]["correct"][i] += 1
            if i == 0 and cat is not None:
                category_stats[cat]["total"] += 1
        if total > 0:
            run_scores.append(correct_count / total)

    mean_accuracy = statistics.mean(run_scores) if run_scores else 0.0
    # pstdev (population std, /N) matches upstream's np.std() behavior
    std_accuracy = statistics.pstdev(run_scores) if len(run_scores) > 1 else 0.0

    # Category accuracies
    category_accuracies = {}
    for cat, stats in category_stats.items():
        cat_accs = []
        for i in range(num_runs):
            if stats["total"] > 0:
                cat_accs.append(stats["correct"][i] / stats["total"])
        if cat_accs:
            category_accuracies[str(cat)] = {
                "mean": statistics.mean(cat_accs),
                "std": statistics.pstdev(cat_accs) if len(cat_accs) > 1 else 0.0,
                "individual_runs": cat_accs,
                "total": stats["total"],
            }

    # Majority vote accuracy (for comparison with published results)
    majority_threshold = num_runs // 2 + 1  # 2 for 3 runs, 1 for 1 run
    majority_correct = 0
    for result in detailed_results:
        jdg = result.get("llm_judgments", {})
        true_count = sum(1 for v in jdg.values() if v is True)
        if true_count >= majority_threshold:
            majority_correct += 1
    majority_accuracy = majority_correct / len(detailed_results) if detailed_results else 0.0

    # --- Print results ---
    print(f"\n{'=' * 60}")
    print(f"Results")
    print(f"{'=' * 60}")
    print(f"Total questions: {len(detailed_results)}")
    print(f"Mean accuracy (per-run avg): {mean_accuracy:.4f} ({mean_accuracy * 100:.2f}%)")
    print(f"Std deviation: {std_accuracy:.4f}")
    print(f"Run accuracies: {[f'{s:.4f}' for s in run_scores]}")
    print(f"Majority vote accuracy: {majority_accuracy:.4f} ({majority_accuracy * 100:.2f}%)")

    cat_names = {"1": "multi-hop", "2": "temporal", "3": "open-domain", "4": "single-hop"}
    print(f"\nPer-category (per-run avg):")
    for cat in sorted(category_accuracies.keys()):
        s = category_accuracies[cat]
        name = cat_names.get(cat, f"cat-{cat}")
        print(f"  {name} (n={s['total']}): "
              f"{s['mean']:.4f} +/- {s['std']:.4f}")

    # --- Group by conversation (upstream format) ---
    # Conversion: locomo_{idx} -> locomo_exp_user_{idx}
    # From: EverMind-AI/EverMemOS/evaluation/src/evaluators/llm_judge.py, lines 177-186
    grouped = defaultdict(list)
    for result in detailed_results:
        qid = result["question_id"]
        if "_qa" in qid:
            conv_id = qid.split("_qa")[0]
            parts = conv_id.rsplit("_", 1)
            if len(parts) == 2:
                group_key = f"{parts[0]}_exp_user_{parts[1]}"
            else:
                group_key = f"{conv_id}_exp_user_0"
        else:
            group_key = "default_group"
        grouped[group_key].append(result)

    # --- Save eval_results.json ---
    eval_output = {
        "total_questions": len(detailed_results),
        "correct": majority_correct,
        "accuracy": majority_accuracy,
        "detailed_results": dict(grouped),
        "metadata": {
            "answer_model": args.answer_model,
            "judge_model": args.judge_model,
            "num_runs": num_runs,
            "mean_accuracy": mean_accuracy,
            "std_accuracy": std_accuracy,
            "run_scores": run_scores,
            "category_accuracies": category_accuracies,
            "majority_vote_accuracy": majority_accuracy,
            "answer_prompt": args.answer_prompt,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "mean_prompt_tokens": mean_prompt_tokens,
            "mean_completion_tokens": mean_completion_tokens,
            "mean_context_words": mean_context_words,
            "mean_answer_words": mean_answer_words,
            "median_answer_words": median_answer_words,
            "base_url": args.base_url,
        },
    }

    tmp = eval_results_path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(eval_output, f, indent=2, ensure_ascii=False)
    os.replace(tmp, eval_results_path)
    print(f"\nSaved: {eval_results_path}")

    # Final save of answer results
    _save_answer_results(answer_results_path, existing_answers)
    print(f"Saved: {answer_results_path}")


def _save_answer_results(path: Path, answers: Dict[str, dict]) -> None:
    """Save answer results to JSON (atomic write via temp + rename)."""
    results = sorted(answers.values(), key=lambda x: x["question_id"])
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Full-Context Baseline Evaluation for LoCoMo-10",
    )
    parser.add_argument("--answer-model", required=True,
                        help="Model for answer generation (e.g., gpt-4o-mini)")
    parser.add_argument("--judge-model", default="gpt-4o-mini",
                        help="Model for judge evaluation (default: gpt-4o-mini)")
    parser.add_argument("--base-url", default="https://openrouter.ai/api/v1",
                        help="API base URL")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for results")
    parser.add_argument("--num-judge-runs", type=int, default=3,
                        help="Number of independent judge runs (default: 3)")
    parser.add_argument("--concurrency", type=int, default=10,
                        help="Max concurrent API calls (default: 10)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of questions (0 = all)")
    parser.add_argument("--answer-prompt", default="answer_prompt_memos",
                        help="Answer prompt key from prompts.yaml (default: answer_prompt_memos)")

    args = parser.parse_args()
    if args.limit == 0:
        args.limit = None

    asyncio.run(run_evaluation(args))


if __name__ == "__main__":
    main()
