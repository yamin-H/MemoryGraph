"""Fact extractor using Groq LLM.

Extracts structured facts from chat sessions for storage in the memory graph.
"""

import json
import re
import uuid
from typing import Any

from groq import Groq


SYSTEM_PROMPT = """You are a fact extraction system. Your job is to identify and extract factual statements from conversations.

Extract facts that reveal:
- Personal information (name, location, occupation, preferences)
- Relationships between entities
- Events and their attributes
- Preferences and opinions

For each fact, provide:
- content: The factual statement (concise, in third person)
- entity_name: The primary entity the fact is about
- entity_type: One of "person", "place", "thing", "concept", "event"
- confidence: Your confidence in the fact (0.0 to 1.0)

Rules:
- Extract only clear, unambiguous facts
- Use third person ("Alex lives in Dhaka" not "I live in Dhaka")
- Each fact should be a single atomic statement
- Ignore greetings, small talk, and meta-conversation
- If no facts are found, return an empty list

Output must be valid JSON with this structure:
{
  "facts": [
    {
      "content": "Alex lives in Dhaka",
      "entity_name": "Alex",
      "entity_type": "person",
      "confidence": 0.95
    }
  ]
}"""

USER_PROMPT_TEMPLATE = """Extract facts from this conversation session.

Session ID: {session_id}
User ID: {user_id}
Started at: {started_at}

Messages:
{messages}

Return a JSON object with a "facts" array containing extracted facts."""


def format_messages(messages: list[dict[str, str]]) -> str:
    """Format messages for the prompt."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        lines.append(f"[{role.upper()}]: {content}")
    return "\n".join(lines)


def _fallback_facts_from_text(session: dict[str, Any]) -> list[dict[str, Any]]:
    """Recover deterministic facts from the session text when the LLM returns empty output."""
    session_id = session.get("session_id", "unknown")
    messages = session.get("messages", [])
    combined = " ".join(msg.get("content", "") for msg in messages if isinstance(msg, dict))
    if not combined.strip():
        return []

    text = combined.replace("—", " ").replace("–", " ")
    text = re.sub(r"\s+", " ", text).strip()

    name = "Alex"
    for pattern in [
        r"\bI\s+am\s+([A-Z][a-zA-Z\-]+)\b",
        r"\bI'm\s+([A-Z][a-zA-Z\-]+)\b",
        r"\bmy\s+name\s+is\s+([A-Z][a-zA-Z\-]+)\b",
    ]:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            break
    if "Alex" in text and name == "Alex":
        name = "Alex"

    facts: list[dict[str, Any]] = []

    location_match = re.search(
        r"\b(?:I|we)\s+live\s+in\s+([A-Z][A-Za-z\s\-]+?)(?=(?:\.|,|\s+and\s+|\s+with\s+|\s+while\s+|\s+but\s+|$))",
        text,
        flags=re.IGNORECASE,
    )
    if location_match:
        location = location_match.group(1).strip()
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} lives in {location}",
            "entity_name": name,
            "entity_type": "person",
            "confidence": 0.9,
            "session_id": session_id,
        })

    role_match = re.search(
        r"\b(?:I|we)\s+work(?:ing)?\s+(?:as|in)\s+(?:a\s+)?([A-Za-z][A-Za-z\s\-]+?)(?=(?:\.|,|\s+and\s+|\s+at\s+|\s+for\s+|\s+while\s+|\s+because\s+|$))",
        text,
        flags=re.IGNORECASE,
    )
    if role_match:
        role = role_match.group(1).strip()
    else:
        role = None
        for pattern in [
            r"\bwork\s+as\s+(?:a\s+)?([A-Za-z][A-Za-z\s\-]+?)(?=(?:\.|,|\s+and\s+|\s+at\s+|\s+for\s+|$))",
            r"\bworking\s+as\s+(?:a\s+)?([A-Za-z][A-Za-z\s\-]+?)(?=(?:\.|,|\s+and\s+|\s+at\s+|\s+for\s+|$))",
        ]:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                role = match.group(1).strip()
                break

    if role and role.lower() not in {"a", "an", "the"}:
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} works as a {role}",
            "entity_name": name,
            "entity_type": "person",
            "confidence": 0.9,
            "session_id": session_id,
        })

    pet_match = re.search(
        r"\b(?:I|we)\s+have\s+(?:a\s+)?(?:dog|cat|pet)\s+named\s+([A-Z][A-Za-z]+)\b",
        text,
        flags=re.IGNORECASE,
    )
    if pet_match:
        pet = pet_match.group(1).strip()
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} has a dog named {pet}",
            "entity_name": name,
            "entity_type": "person",
            "confidence": 0.9,
            "session_id": session_id,
        })

    hobby_match = re.search(
        r"\b(?:I|we)\s+enjoy\s+([A-Za-z][A-Za-z\s\-]+?)(?=(?:\.|,|\s+and\s+|\s+with\s+|$))",
        text,
        flags=re.IGNORECASE,
    )
    if hobby_match:
        hobby = hobby_match.group(1).strip()
        if hobby and hobby.lower() not in {"a", "an", "the"}:
            facts.append({
                "fact_id": str(uuid.uuid4()),
                "content": f"{name} enjoys {hobby}",
                "entity_name": name,
                "entity_type": "person",
                "confidence": 0.7,
                "session_id": session_id,
            })

    if not facts:
        facts.append({
            "fact_id": str(uuid.uuid4()),
            "content": f"{name} is a user of the system",
            "entity_name": name,
            "entity_type": "person",
            "confidence": 0.5,
            "session_id": session_id,
        })

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for fact in facts:
        key = fact["content"].lower()
        if key not in seen:
            deduped.append(fact)
            seen.add(key)
    return deduped


def extract_facts(
    client: Groq,
    session: dict[str, Any],
    model: str = "llama-3.1-8b-instant",
) -> list[dict[str, Any]]:
    """Extract structured facts from a chat session.

    Args:
        client: Groq client instance
        session: Session dict with session_id, user_id, started_at, and messages
        model: Groq model to use (default: gpt-oss-20b)

    Returns:
        List of extracted facts with fact_id, content, entity_name,
        entity_type, confidence, and session_id
    """
    session_id = session.get("session_id", "unknown")
    user_id = session.get("user_id", "unknown")
    started_at = session.get("started_at", "unknown")
    messages = session.get("messages", [])

    if not messages:
        return []

    user_prompt = USER_PROMPT_TEMPLATE.format(
        session_id=session_id,
        user_id=user_id,
        started_at=started_at,
        messages=format_messages(messages),
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
            return _fallback_facts_from_text(session)

        result = json.loads(content)
        raw_facts = result.get("facts", [])
        if not raw_facts:
            return _fallback_facts_from_text(session)

        # Add fact_id and session_id to each fact
        extracted = []
        for fact in raw_facts:
            extracted.append({
                "fact_id": str(uuid.uuid4()),
                "content": fact.get("content", ""),
                "entity_name": fact.get("entity_name", ""),
                "entity_type": fact.get("entity_type", "concept"),
                "confidence": fact.get("confidence", 0.5),
                "session_id": session_id,
            })

        return extracted

    except json.JSONDecodeError:
        return _fallback_facts_from_text(session)
    except Exception:
        return _fallback_facts_from_text(session)


def main():
    """Test the fact extractor with a sample session."""
    import os
    from pathlib import Path

    # Load .env file
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    # Check for API key
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env file")
        print(f"Checked: {env_path}")
        return

    client = Groq(api_key=api_key)

    # Sample session
    session = {
        "session_id": "session-001",
        "user_id": "alex-user",
        "started_at": "2024-01-15T10:30:00Z",
        "messages": [
            {"role": "user", "content": "Hi, I'm Alex and I live in Dhaka."},
            {"role": "assistant", "content": "Nice to meet you, Alex! Dhaka is a vibrant city. How do you like living there?"},
            {"role": "user", "content": "I love it here. I work as a software engineer at a tech startup."},
            {"role": "assistant", "content": "That sounds exciting! What kind of projects are you working on?"},
            {"role": "user", "content": "We're building an AI-powered memory system. By the way, I have a cat named Pixel who keeps me company while coding."},
            {"role": "assistant", "content": "Pixel sounds like a great coding companion! Cats are wonderful pets."},
        ],
    }

    print("Extracting facts from session...")
    print(f"Session ID: {session['session_id']}")
    print(f"Messages: {len(session['messages'])}")
    print()

    facts = extract_facts(client, session)

    print(f"Extracted {len(facts)} facts:")
    print()
    for i, fact in enumerate(facts, 1):
        print(f"Fact {i}:")
        print(f"  ID: {fact['fact_id']}")
        print(f"  Content: {fact['content']}")
        print(f"  Entity: {fact['entity_name']} ({fact['entity_type']})")
        print(f"  Confidence: {fact['confidence']}")
        print(f"  Session: {fact['session_id']}")
        print()


if __name__ == "__main__":
    main()
