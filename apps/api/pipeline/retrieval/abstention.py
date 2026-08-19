"""Abstention logic for MemoryGraph retrieval.

Decides when to say "I don't know" instead of answering.
"""

from typing import Any


def check_abstention(
    ranked_facts: list[dict[str, Any]],
    parsed_question: dict[str, Any],
) -> dict[str, Any]:
    """Determine if we should abstain from answering.

    Three cases:
    1. No facts found → abstain with "no memory found"
    2. Facts found but irrelevant → abstain with "memory exists but does not answer"
    3. Conflicting facts → return most recent and flag conflict

    Args:
        ranked_facts: Ranked list of facts from ranker
        parsed_question: Parsed question with entity_name, question_type, keywords

    Returns:
        Dict with should_abstain, abstention_reason, facts_to_use
    """
    # Case 1: No facts found
    if not ranked_facts:
        return {
            "should_abstain": True,
            "abstention_reason": "no memory found",
            "facts_to_use": [],
            "has_conflict": False,
        }

    # Get current facts only
    current_facts = [f for f in ranked_facts if f.get("is_current")]

    # Case 2: No current facts (all are superseded or invalidated)
    if not current_facts:
        return {
            "should_abstain": True,
            "abstention_reason": "no current memory found",
            "facts_to_use": ranked_facts,  # Return historical for context
            "has_conflict": False,
        }

    # Check if facts are relevant to the question
    keywords = parsed_question.get("keywords", [])
    question_type = parsed_question.get("question_type", "current_fact")

    relevant_facts = []
    for fact in current_facts:
        content = fact.get("content", "").lower()
        # Check if any keyword matches
        if keywords:
            if any(kw.lower() in content for kw in keywords):
                relevant_facts.append(fact)
        else:
            relevant_facts.append(fact)

    # Case 3: Facts exist but don't match question keywords
    if not relevant_facts and question_type == "absent_information":
        return {
            "should_abstain": True,
            "abstention_reason": "memory exists but does not answer question",
            "facts_to_use": current_facts,
            "has_conflict": False,
        }

    # Group current facts by topic category and take the most recent per topic.
    # This prevents the same category (e.g. location) from contributing multiple
    # contradictory facts while still returning all distinct topic categories.
    seen_topics: set[str] = set()
    facts_to_use: list[dict[str, Any]] = []

    # Sort most recent first so we keep the newest fact per topic
    sorted_current = sorted(
        current_facts,
        key=lambda f: f.get("session_started_at") or f.get("created_at") or "",
        reverse=True,
    )

    # Generic topic extraction from content words (no hardcoded names)
    LOCATION_WORDS = {"live", "lives", "lived", "reside", "resides", "located", "location", "city", "country", "moved", "move"}
    WORK_WORDS = {"work", "works", "worked", "job", "role", "career", "company", "employer", "profession", "occupation"}
    PET_WORDS = {"dog", "cat", "pet", "puppy", "kitten", "animal", "adopted", "adopt"}
    DIET_WORDS = {"diet", "vegan", "vegetarian", "food", "dish", "eat", "eating", "meal", "cuisine"}
    VEHICLE_WORDS = {"car", "vehicle", "scooter", "bicycle", "bike", "motorcycle", "drive", "drives", "commute"}
    HOBBY_WORDS = {"hobby", "hobbies", "interest", "passion", "plays", "play", "enjoy", "enjoys"}

    for fact in sorted_current:
        content_words = set(fact.get("content", "").lower().split())
        if content_words & LOCATION_WORDS:
            topic = "location"
        elif content_words & WORK_WORDS:
            topic = "work"
        elif content_words & PET_WORDS:
            topic = "pet"
        elif content_words & DIET_WORDS:
            topic = "diet"
        elif content_words & VEHICLE_WORDS:
            topic = "vehicle"
        elif content_words & HOBBY_WORDS:
            topic = "hobby"
        else:
            # Use first 3 meaningful content words as a generic topic key
            words = [w for w in fact.get("content", "").lower().split() if len(w) > 3][:3]
            topic = " ".join(words) if words else fact.get("content", "")[:30]

        if topic not in seen_topics:
            seen_topics.add(topic)
            facts_to_use.append(fact)

    has_conflict = any(f.get("has_conflict") for f in current_facts)

    # If no facts matched the topic grouping (shouldn't happen), fall back to all current facts
    if not facts_to_use:
        facts_to_use = sorted_current

    return {
        "should_abstain": False,
        "abstention_reason": None,
        "facts_to_use": facts_to_use,
        "has_conflict": has_conflict,
    }


def main():
    """Test the abstention logic."""
    print("Testing abstention logic")
    print("=" * 50)

    # Test case 1: No facts
    result = check_abstention([], {"question_type": "current_fact", "keywords": ["live"]})
    print(f"\nCase 1 - No facts:")
    print(f"  Should abstain: {result['should_abstain']}")
    print(f"  Reason: {result['abstention_reason']}")

    # Test case 2: Relevant facts
    facts = [
        {
            "fact_id": "1",
            "content": "Alex lives in Dhaka",
            "is_current": True,
            "created_at": "2024-01-15T10:30:00Z",
        }
    ]
    result = check_abstention(facts, {"question_type": "current_fact", "keywords": ["live"]})
    print(f"\nCase 2 - Relevant facts:")
    print(f"  Should abstain: {result['should_abstain']}")
    print(f"  Facts to use: {len(result['facts_to_use'])}")

    # Test case 3: Irrelevant facts (dog when we have cat)
    facts = [
        {
            "fact_id": "1",
            "content": "Alex has a cat named Pixel",
            "is_current": True,
            "created_at": "2024-01-15T10:30:00Z",
        }
    ]
    result = check_abstention(
        facts, {"question_type": "absent_information", "keywords": ["dog"]}
    )
    print(f"\nCase 3 - Irrelevant facts:")
    print(f"  Should abstain: {result['should_abstain']}")
    print(f"  Reason: {result['abstention_reason']}")


if __name__ == "__main__":
    main()
