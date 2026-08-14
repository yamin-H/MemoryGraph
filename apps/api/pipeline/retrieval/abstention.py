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

    # Check for conflicts
    has_conflict = any(f.get("has_conflict") for f in current_facts)

    # Case 4: Conflicting facts - return most recent
    if has_conflict:
        # Sort by timestamp and take most recent
        sorted_facts = sorted(
            current_facts,
            key=lambda f: f.get("session_started_at") or f.get("created_at") or "",
            reverse=True,
        )
        return {
            "should_abstain": False,
            "abstention_reason": None,
            "facts_to_use": [sorted_facts[0]],  # Most recent only
            "has_conflict": True,
        }

    # Normal case: return relevant facts
    return {
        "should_abstain": False,
        "abstention_reason": None,
        "facts_to_use": relevant_facts if relevant_facts else current_facts,
        "has_conflict": False,
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
