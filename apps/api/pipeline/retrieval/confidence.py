"""Confidence scoring for MemoryGraph retrieval.

Assigns confidence scores to answers based on supporting facts.
"""

from typing import Any


def calculate_confidence(
    facts_used: list[dict[str, Any]],
    abstention_result: dict[str, Any],
    parsed_question: dict[str, Any],
) -> dict[str, Any]:
    """Calculate confidence score for an answer.

    Scoring factors:
    - Number of supporting facts (more = higher, +0.1 per fact, max +0.3)
    - Recency of facts (newer = higher, +0.1 for most recent session)
    - Supersession applied (+0.15)
    - Abstention considered (-0.2)

    Base score: 0.5

    Args:
        facts_used: List of facts being used for the answer
        abstention_result: Abstention check result
        parsed_question: Parsed question information

    Returns:
        Dict with score and reasoning
    """
    base_score = 0.5
    reasoning_parts = []

    # Number of supporting facts
    num_facts = len(facts_used)
    if num_facts == 0:
        return {
            "score": 0.0,
            "reasoning": "No supporting facts found",
        }

    facts_bonus = min(num_facts * 0.1, 0.3)
    reasoning_parts.append(f"{num_facts} supporting fact{'s' if num_facts > 1 else ''}")

    # Recency bonus
    recency_bonus = 0.0
    if facts_used:
        # Get most recent session
        most_recent = max(
            facts_used,
            key=lambda f: f.get("session_started_at") or f.get("created_at") or "",
        )
        session_id = most_recent.get("session_id", "unknown")
        recency_bonus = 0.1
        reasoning_parts.append(f"most recent session {session_id}")

    # Supersession bonus
    supersession_bonus = 0.0
    for fact in facts_used:
        if fact.get("superseded_by"):
            supersession_bonus = 0.15
            reasoning_parts.append("supersession applied")
            break

    # Abstention penalty
    abstention_penalty = 0.0
    if abstention_result.get("should_abstain"):
        abstention_penalty = 0.2
        reasoning_parts.append("abstention considered")

    # Conflict penalty
    conflict_penalty = 0.0
    if abstention_result.get("has_conflict"):
        conflict_penalty = 0.1
        reasoning_parts.append("conflict detected")

    # Calculate final score
    final_score = base_score + facts_bonus + recency_bonus + supersession_bonus - abstention_penalty - conflict_penalty

    # Clamp to [0.0, 1.0]
    final_score = max(0.0, min(1.0, final_score))

    return {
        "score": round(final_score, 2),
        "reasoning": ", ".join(reasoning_parts) if reasoning_parts else "base confidence",
    }


def main():
    """Test the confidence calculator."""
    print("Testing confidence calculator")
    print("=" * 50)

    # Test case 1: Multiple supporting facts
    facts = [
        {
            "fact_id": "1",
            "content": "Alex lives in Dhaka",
            "is_current": True,
            "session_id": "session-001",
            "created_at": "2024-01-15T10:30:00Z",
        },
        {
            "fact_id": "2",
            "content": "Alex moved to Dhaka last year",
            "is_current": True,
            "session_id": "session-002",
            "created_at": "2024-01-14T09:00:00Z",
        },
    ]
    abstention = {"should_abstain": False, "has_conflict": False}
    parsed = {"question_type": "current_fact"}

    result = calculate_confidence(facts, abstention, parsed)
    print(f"\nCase 1 - Multiple supporting facts:")
    print(f"  Score: {result['score']}")
    print(f"  Reasoning: {result['reasoning']}")

    # Test case 2: Single fact with supersession
    facts = [
        {
            "fact_id": "2",
            "content": "Alex lives in Dhaka",
            "is_current": True,
            "session_id": "session-002",
            "superseded_by": "fact-1",
            "created_at": "2024-01-15T10:30:00Z",
        }
    ]
    abstention = {"should_abstain": False, "has_conflict": False}

    result = calculate_confidence(facts, abstention, parsed)
    print(f"\nCase 2 - Supersession applied:")
    print(f"  Score: {result['score']}")
    print(f"  Reasoning: {result['reasoning']}")

    # Test case 3: Abstention considered
    abstention = {"should_abstain": True, "has_conflict": False}

    result = calculate_confidence(facts, abstention, parsed)
    print(f"\nCase 3 - Abstention considered:")
    print(f"  Score: {result['score']}")
    print(f"  Reasoning: {result['reasoning']}")


if __name__ == "__main__":
    main()
