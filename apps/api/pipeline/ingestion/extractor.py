"""Fact extractor using Groq LLM and rule-based fallback.

Extracts structured facts from chat sessions for storage in the memory graph.
"""

import json
import re
import uuid
from typing import Any

from groq import Groq


SYSTEM_PROMPT = """You are a fact extraction system for an agent memory layer.

Extract factual statements from conversations that reveal persistent information about the user.

For each fact provide:
- content: The factual statement in third person (e.g. "User lives in Dhaka")
- entity_name: Primary entity (use "User" for the main user)
- entity_type: One of "person", "place", "organization", "event", "preference"
- fact_type: One of "location", "occupation", "preference", "relationship", "possession", "belief", "status", "event"
- confidence: 0.0 to 1.0

CRITICAL RULES:
- Use "User" as entity_name when referring to the main user
- Extract ONLY clear, unambiguous facts
- Each fact must be a single atomic statement
- Ignore greetings and small talk
- If no facts found, return empty list

Output ONLY valid JSON:
{
  "facts": [
    {
      "content": "User lives in Dhaka",
      "entity_name": "User",
      "entity_type": "person",
      "fact_type": "location",
      "confidence": 0.95
    }
  ]
}"""

USER_PROMPT_TEMPLATE = """Extract facts from this conversation session.

Session ID: {session_id}
Session Date: {session_date}

Conversation:
{messages}

Return JSON with extracted facts."""


def format_messages(turns: list[dict[str, Any]]) -> str:
    """Format session turns for the prompt."""
    lines = []
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role", "unknown").upper()
        content = turn.get("content", "")
        if content:
            lines.append(f"[{role}]: {content}")
    return "\n".join(lines)


def truncate_turns(
    turns: list[dict[str, Any]], 
    max_chars: int = 3000
) -> list[dict[str, Any]]:
    """Truncate session to fit within token limits."""
    result = []
    total = 0
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        content = turn.get("content", "")
        if total + len(content) > max_chars:
            remaining = max_chars - total
            if remaining > 100:
                truncated_turn = dict(turn)
                truncated_turn["content"] = content[:remaining] + "..."
                result.append(truncated_turn)
            break
        result.append(turn)
        total += len(content)
    return result


def _rule_based_fallback_facts(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Fallback fact extractor when LLM returns no facts or is unavailable."""
    messages = session.get("messages", [])
    session_id = session.get("session_id", "session-0")
    user_id = session.get("user_id", "User")
    
    facts = []
    all_user_text = " ".join(
        m.get("content", "") for m in messages if isinstance(m, dict) and m.get("role") == "user"
    )
    if not all_user_text:
        return []

    # Detect Name
    name = user_id if user_id and user_id.lower() != "user" else "User"
    name_match = re.search(r"\b(?:I'm|I am|name is)\s+([A-Z][a-z]+)", all_user_text)
    if name_match:
        name = name_match.group(1)

    # 1. Location
    loc_match = re.search(r"(?:live in|moved to|living in|located in)\s+([A-Za-z\s]+?)(?=[.,;]| and | with | for |$)", all_user_text, re.IGNORECASE)
    if loc_match:
        loc = loc_match.group(1).strip()
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} lives in {loc}",
            "entity_name": name,
            "entity_type": "person",
            "fact_type": "location",
            "confidence": 0.9,
            "session_id": session_id,
            "is_current": True,
        })

    # 2. Occupation
    job_match = re.search(r"(?:work as a|work as an|working as|employed as|job as)\s+([A-Za-z\s]+?)(?=[.,;]| and | at | for |$)", all_user_text, re.IGNORECASE)
    if job_match:
        job = job_match.group(1).strip()
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} works as a {job}",
            "entity_name": name,
            "entity_type": "person",
            "fact_type": "occupation",
            "confidence": 0.9,
            "session_id": session_id,
            "is_current": True,
        })

    # 3. Pet / Possession
    pet_match = re.search(r"(?:have a|own a|got a)\s+([A-Za-z\s]+?)\s+(?:named|called)\s+([A-Za-z]+)", all_user_text, re.IGNORECASE)
    if pet_match:
        pet_type = pet_match.group(1).strip()
        pet_name = pet_match.group(2).strip()
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} has a {pet_type} named {pet_name}",
            "entity_name": name,
            "entity_type": "person",
            "fact_type": "possession",
            "confidence": 0.9,
            "session_id": session_id,
            "is_current": True,
        })

    # 4. Hobbies / Preference
    hobby_match = re.search(r"(?:enjoy|love|like)\s+([A-Za-z\s]+?)(?=[.,;]| and | on |$)", all_user_text, re.IGNORECASE)
    if hobby_match:
        hobby = hobby_match.group(1).strip()
        if len(hobby) > 2:
            facts.append({
                "fact_id": str(uuid.uuid4()),
                "content": f"{name} enjoys {hobby}",
                "entity_name": name,
                "entity_type": "person",
                "fact_type": "preference",
                "confidence": 0.85,
                "session_id": session_id,
                "is_current": True,
            })

    return facts


def extract_facts(
    client: Any,
    session: dict[str, Any],
    model: str = "openai/gpt-oss-120b",
) -> list[dict[str, Any]]:
    """Extract structured facts from a session payload.

    Args:
        client: Groq client (or mock)
        session: Dict with session_id, user_id, started_at, messages
        model: LLM model name

    Returns:
        List of extracted fact dictionaries with UUIDs
    """
    if not session or not isinstance(session, dict):
        return []

    messages = session.get("messages", [])
    if not messages:
        return []

    session_id = session.get("session_id", str(uuid.uuid4()))
    session_date = session.get("started_at", "")

    # If client is not available, run rule-based fallback
    if client is None:
        return _rule_based_fallback_facts(session)

    truncated_turns = truncate_turns(messages, max_chars=3000)
    user_prompt = USER_PROMPT_TEMPLATE.format(
        session_id=session_id,
        session_date=session_date or "recent",
        messages=format_messages(truncated_turns)
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2048,
        )

        content = response.choices[0].message.content
        if not content:
            return _rule_based_fallback_facts(session)

        result = json.loads(content)
        raw_facts = result.get("facts", [])

        if not raw_facts:
            return _rule_based_fallback_facts(session)

        extracted = []
        for fact in raw_facts:
            if not fact.get("content"):
                continue
            extracted.append({
                "fact_id": str(uuid.uuid4()),
                "content": fact.get("content", ""),
                "entity_name": fact.get("entity_name", session.get("user_id", "User")),
                "entity_type": fact.get("entity_type", "person"),
                "fact_type": fact.get("fact_type", "status"),
                "confidence": float(fact.get("confidence", 0.9)),
                "session_id": session_id,
                "session_date": session_date,
                "is_current": True,
            })

        return extracted

    except Exception as e:
        # Fallback to rule-based parser on any LLM or JSON failure
        fallback = _rule_based_fallback_facts(session)
        return fallback


def extract_facts_from_session(
    client: Groq,
    session_turns: list[dict[str, Any]],
    session_index: int,
    session_date: str = "",
    model: str = "openai/gpt-oss-120b",
) -> list[dict[str, Any]]:
    """Extract structured facts from a LongMemEval session."""
    session = {
        "session_id": f"session-{session_index}",
        "started_at": session_date,
        "messages": session_turns,
    }
    return extract_facts(client=client, session=session, model=model)


def extract_facts_from_example(
    client: Groq,
    example: dict[str, Any],
    model: str = "openai/gpt-oss-120b",
) -> list[dict[str, Any]]:
    """Extract facts from a full LongMemEval example across all sessions."""
    sessions = example.get("sessions", [])
    session_dates = example.get("session_dates", [])

    all_facts = []
    for idx, session_turns in enumerate(sessions):
        session_date = session_dates[idx] if idx < len(session_dates) else ""
        facts = extract_facts_from_session(
            client=client,
            session_turns=session_turns,
            session_index=idx,
            session_date=session_date,
            model=model,
        )
        all_facts.extend(facts)

    return all_facts
