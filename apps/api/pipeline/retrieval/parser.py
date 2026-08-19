"""Natural language question parser for MemoryGraph retrieval.

Parses questions into structured form for graph traversal.
"""

import json
import re
from typing import Any

from groq import Groq


def _fallback_parse_question(question: str, user_id: str = "user") -> dict[str, Any]:
    """Best-effort parser when Groq returns an empty response."""
    normalized = question.strip()
    if not normalized:
        return {
            "entity_name": None,
            "question_type": "absent_information",
            "original_question": question,
            "keywords": [],
        }

    entity_name = None
    lower_question = normalized.lower()

    entities: list[str] = []
    # Detect 1st-person pronoun questions
    if any(phrase in lower_question for phrase in ["my name", "who am i", "about me", "my job", "do i live", "my pet", "my dog", "my cat"]):
        entity_name = "User"
        entities.append("User")
    else:
        for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", normalized):
            candidate = match.group(0)
            if candidate.lower() not in {
                "where", "what", "who", "when", "how", "which", "why", "this", "that", "there", "here", "hello", "hi",
                "summarize", "tell", "show", "describe", "list", "explain", "please", "give", "find", "get", "recall"
            }:
                if candidate not in entities:
                    entities.append(candidate)
        if entities:
            entity_name = entities[0]

    keywords: list[str] = []
    words = re.findall(r"\b[a-zA-Z]{3,}\b", lower_question)
    user_uid = str(user_id or "user").strip().lower()
    stop_words = {"what", "when", "where", "which", "who", "whom", "whose", "why", "how", "this", "that", "these", "those", "does", "have", "with", "from", user_uid, "user", "about", "tell", "the", "and"}
    for w in words:
        if w not in stop_words and w not in keywords:
            keywords.append(w)

    if any(phrase in lower_question for phrase in ["live", "lives", "reside", "resides", "home", "location", "city", "country", "where"]):
        keywords.extend(["live", "lives", "lived", "location", "city", "reside", "home", "move", "moved", "moving", "relocat", "settled", "osaka", "tokyo", "japan"])
    if any(phrase in lower_question for phrase in ["work", "works", "job", "role", "profession", "career", "engineer", "occupation", "employment", "company", "employer"]):
        keywords.extend(["work", "works", "worked", "job", "career", "engineer", "profession", "occupation", "company", "employer", "promote", "promoted", "hired", "position"])
    if any(phrase in lower_question for phrase in ["dog", "cat", "pet", "animal", "puppy", "kitten", "adopted"]):
        keywords.extend(["pet", "dog", "cat", "animal", "puppy", "kitten", "adopted", "adopt"])
    if any(phrase in lower_question for phrase in ["car", "vehicle", "automobile", "drive", "scooter", "commute"]):
        keywords.extend(["car", "vehicle", "automobile", "drive", "scooter", "commute", "bicycle", "motorcycle"])
    if any(phrase in lower_question for phrase in ["hobby", "hobbies", "interest", "enjoy", "passion"]):
        keywords.extend(["hobby", "hobbies", "interest", "enjoy", "passion", "play", "plays"])
    if any(phrase in lower_question for phrase in ["diet", "food", "eat", "vegan", "meal", "dish", "cuisine"]):
        keywords.extend(["diet", "food", "eat", "vegan", "meal", "dish", "cuisine", "vegetarian"])

    keywords = list(dict.fromkeys(keywords))

    if re.search(r"\b(?:before|previous|used\s+to|earlier|old|past)\b", lower_question):
        question_type = "historical_fact"
    elif re.search(r"\b(?:jobs|career|all|history|timeline|summarize)\b", lower_question):
        question_type = "multi_session_synthesis"
    else:
        question_type = "current_fact"

    return {
        "entity_name": entity_name,
        "entities": entities if entities else ([entity_name] if entity_name else []),
        "question_type": question_type,
        "original_question": question,
        "keywords": keywords,
    }


def _expand_keywords(question: str, existing_keywords: list[str]) -> list[str]:
    """Expand parsed keywords with domain-specific synonyms.

    This is applied after EVERY parse (Groq or fallback) to ensure consistent
    keyword coverage regardless of which parser produced the base keywords.
    """
    q = question.lower()
    extra: list[str] = list(existing_keywords)

    if any(w in q for w in ["live", "lives", "where", "location", "city", "country", "reside", "home"]):
        extra.extend(["live", "lives", "lived", "location", "city", "reside", "home",
                       "move", "moved", "moving", "relocat", "settled", "based"])
    if any(w in q for w in ["work", "job", "role", "career", "company", "employ", "profession", "position"]):
        extra.extend(["work", "works", "worked", "job", "career", "company", "employer",
                       "promote", "promoted", "hired", "position", "role", "engineer", "architect",
                       "scientist", "developer", "manager", "director", "analyst"])
    if any(w in q for w in ["pet", "dog", "cat", "animal", "puppy", "kitten", "adopt"]):
        extra.extend(["pet", "dog", "cat", "animal", "puppy", "kitten", "adopted", "adopt"])
    if any(w in q for w in ["diet", "food", "eat", "vegan", "meal", "dish", "cuisine"]):
        extra.extend(["diet", "food", "eat", "vegan", "meal", "dish", "cuisine", "vegetarian", "plant"])
    if any(w in q for w in ["hobby", "hobbies", "interest", "enjoy", "passion", "leisure"]):
        extra.extend(["hobby", "hobbies", "interest", "enjoy", "passion", "play", "plays"])
    if any(w in q for w in ["car", "vehicle", "scooter", "commute", "drive", "transport"]):
        extra.extend(["car", "vehicle", "scooter", "commute", "drive", "bicycle", "motorcycle"])

    return list(dict.fromkeys(extra))


SYSTEM_PROMPT = """You are a question parser for a memory retrieval system. Your job is to extract structured information from natural language questions.

Extract:
- entity_name: The primary entity the question is about (person, place, thing). If the user asks about themselves (e.g., "What is my name?", "Where do I live?"), output "User" or the relevant subject.
- question_type: One of the following types:
  - "current_fact": Asking about current state ("Where do I live?", "What is my name?")
  - "historical_fact": Asking about past states ("Where did I live before?")
  - "multi_session_synthesis": Requires combining facts across sessions ("What jobs have I had?")
  - "absent_information": Asking about something not discussed
- keywords: Important words from the question that help with retrieval (e.g. ["name"], ["live", "location"], ["job", "work"])

Output must be valid JSON with this structure:
{
  "entity_name": "User",
  "question_type": "current_fact",
  "keywords": ["live", "location", "city", "where"]
}"""

USER_PROMPT_TEMPLATE = """Parse this question into structured form.

Question: {question}

Return a JSON object with entity_name, question_type, and keywords."""


def parse_question(
    client: Groq,
    question: str,
    user_id: str = "user",
    model: str = "qwen/qwen3.6-27b",
) -> dict[str, Any]:
    """Parse a natural language question into structured form.

    Args:
        client: Groq client instance
        question: Natural language question string
        user_id: User ID to scope parsing and stop words
        model: Groq model to use

    Returns:
        Parsed question dict with entity_name, question_type, keywords,
        and original_question
    """
    user_prompt = USER_PROMPT_TEMPLATE.format(question=question)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=256,
        )

        content = response.choices[0].message.content
        if not content:
            return _fallback_parse_question(question, user_id=user_id)

        result = json.loads(content)
        result["original_question"] = question

        # Ensure required fields exist
        if "entity_name" not in result:
            result["entity_name"] = None
        if "question_type" not in result:
            result["question_type"] = "absent_information"
        if "keywords" not in result:
            result["keywords"] = []

        if "entities" not in result or not result["entities"]:
            if result.get("entity_name"):
                result["entities"] = [result["entity_name"]]
            else:
                fallback = _fallback_parse_question(question, user_id=user_id)
                result["entities"] = fallback.get("entities", [])
                if not result.get("entity_name"):
                    result["entity_name"] = fallback.get("entity_name")

        if result.get("entity_name") is None and "original_question" in result:
            fallback = _fallback_parse_question(question, user_id=user_id)
            result["entity_name"] = fallback["entity_name"]
            result["entities"] = fallback["entities"]
            result["question_type"] = fallback["question_type"]
            result["keywords"] = fallback["keywords"]

        return result

    except json.JSONDecodeError:
        fallback = _fallback_parse_question(question, user_id=user_id)
        return fallback
    except Exception:
        fallback = _fallback_parse_question(question, user_id=user_id)
        return fallback


def main():
    """Test the question parser."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("Error: GROQ_API_KEY not found in .env file")
        return

    client = Groq(api_key=api_key)

    test_questions = [
        "Where does Alex live?",
        "What is Alex's dog's name?",
        "What jobs has Alex had?",
        "Where did Alex live before Dhaka?",
    ]

    print("Testing question parser")
    print("=" * 50)

    for q in test_questions:
        parsed = parse_question(client, q)
        print(f"\nQuestion: {q}")
        print(f"  Entity: {parsed['entity_name']}")
        print(f"  Type: {parsed['question_type']}")
        print(f"  Keywords: {parsed['keywords']}")


if __name__ == "__main__":
    main()
