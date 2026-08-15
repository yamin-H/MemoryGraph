"""Natural language question parser for MemoryGraph retrieval.

Parses questions into structured form for graph traversal.
"""

import json
import re
from typing import Any

from groq import Groq


def _fallback_parse_question(question: str) -> dict[str, Any]:
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
    for match in re.finditer(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", normalized):
        candidate = match.group(0)
        if candidate.lower() not in {"where", "what", "who", "when", "how", "which", "this", "that", "there", "here"}:
            entity_name = candidate
            break

    lower_question = normalized.lower()
    keywords: list[str] = []
    if any(phrase in lower_question for phrase in ["live", "lives", "reside", "resides", "home", "location", "city", "country"]):
        keywords.extend(["live", "location"])
    if any(phrase in lower_question for phrase in ["work", "works", "job", "role", "profession", "career"]):
        keywords.extend(["work", "job"])
    if any(phrase in lower_question for phrase in ["dog", "cat", "pet", "favorite", "color", "name"]):
        keywords.extend(["name", "pet"])
    keywords = list(dict.fromkeys(keywords))

    if re.search(r"\b(?:where|live|lives|home|reside|resides)\b", lower_question):
        question_type = "current_fact"
    elif re.search(r"\b(?:before|previous|used\s+to|earlier|old)\b", lower_question):
        question_type = "historical_fact"
    elif re.search(r"\b(?:jobs|job|work|career|profession|roles)\b", lower_question):
        question_type = "multi_session_synthesis"
    else:
        question_type = "absent_information"

    return {
        "entity_name": entity_name,
        "question_type": question_type,
        "original_question": question,
        "keywords": keywords,
    }


SYSTEM_PROMPT = """You are a question parser for a memory retrieval system. Your job is to extract structured information from natural language questions.

Extract:
- entity_name: The primary entity the question is about (person, place, thing)
- question_type: One of the following types:
  - "current_fact": Asking about current state ("Where does Alex live?")
  - "historical_fact": Asking about past states ("Where did Alex live before?")
  - "multi_session_synthesis": Requires combining facts across sessions ("What jobs has Alex had?")
  - "absent_information": Asking about something not in memory ("What is Alex's dog's name?")
- keywords: Important words from the question that help with retrieval

Output must be valid JSON with this structure:
{
  "entity_name": "Alex",
  "question_type": "current_fact",
  "keywords": ["live", "location", "city", "where"]
}"""

USER_PROMPT_TEMPLATE = """Parse this question into structured form.

Question: {question}

Return a JSON object with entity_name, question_type, and keywords."""


def parse_question(
    client: Groq,
    question: str,
    model: str = "llama-3.1-8b-instant",
) -> dict[str, Any]:
    """Parse a natural language question into structured form.

    Args:
        client: Groq client instance
        question: Natural language question string
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
            return _fallback_parse_question(question)

        result = json.loads(content)
        result["original_question"] = question

        # Ensure required fields exist
        if "entity_name" not in result:
            result["entity_name"] = None
        if "question_type" not in result:
            result["question_type"] = "absent_information"
        if "keywords" not in result:
            result["keywords"] = []

        if result.get("entity_name") is None and "original_question" in result:
            fallback = _fallback_parse_question(question)
            result["entity_name"] = fallback["entity_name"]
            result["question_type"] = fallback["question_type"]
            result["keywords"] = fallback["keywords"]

        return result

    except json.JSONDecodeError:
        return {
            "entity_name": None,
            "question_type": "absent_information",
            "original_question": question,
            "keywords": [],
        }
    except Exception:
        return {
            "entity_name": None,
            "question_type": "absent_information",
            "original_question": question,
            "keywords": [],
        }


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
