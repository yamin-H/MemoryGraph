"""Confidence scoring for MemoryGraph retrieval.

Assigns confidence scores to answers based on supporting facts.
"""

from typing import Any

CONFIDENCE_THRESHOLD = 0.35


def enforce_confidence_threshold(
    abstention_result: dict[str, Any],
    confidence_result: dict[str, Any],
) -> dict[str, Any]:
    """Turn a low-confidence retrieval into a first-class abstention."""
    if abstention_result.get("should_abstain"):
        return abstention_result

    score = confidence_result.get("score", 0.0)
    if score >= CONFIDENCE_THRESHOLD:
        return abstention_result

    return {
        **abstention_result,
        "should_abstain": True,
        "abstention_reason": (
            f"confidence score ({score:.2f}) is below the verification threshold "
            f"({CONFIDENCE_THRESHOLD:.2f})"
        ),
        "facts_to_use": [],
    }


def calculate_confidence(
    facts_used: list[dict[str, Any]],
    abstention_result: dict[str, Any],
    parsed_question: dict[str, Any],
    graph_evidence: dict[str, dict[str, int]] | None = None,
) -> dict[str, Any]:
    """Calculate confidence score for an answer.

    Scores only evidence returned by graph aggregation. There is intentionally no
    base score: a weakly connected subgraph must not become a confident answer
    merely because a fact happened to be retrieved.

    Args:
        facts_used: List of facts being used for the answer
        abstention_result: Abstention check result
        parsed_question: Parsed question information
        graph_evidence: Per-fact Cypher aggregation results. Each entry contains
            supporting_facts and related_entities for the user-scoped subgraph.

    Returns:
        Dict with score and reasoning
    """
    reasoning_parts: list[str] = []

    # Number of supporting facts
    num_facts = len(facts_used)
    if num_facts == 0:
        return {
            "score": 0.0,
            "reasoning": "No supporting facts found",
        }

    graph_evidence = graph_evidence or {}
    evidence_rows = [graph_evidence.get(str(f.get("fact_id")), {}) for f in facts_used]
    evidence_backed = [row for row in evidence_rows if row]
    if not evidence_backed:
        return {
            "score": 0.0,
            "reasoning": "No graph aggregation evidence found for retrieved facts",
        }

    # Coverage says how much of the candidate answer has a user-scoped graph
    # witness. Density measures corroborating facts connected through the same
    # entity. Relationship coverage prevents isolated nodes from scoring highly.
    coverage = len(evidence_backed) / num_facts
    average_support = sum(row.get("supporting_facts", 0) for row in evidence_backed) / len(evidence_backed)
    density = min(average_support / 3.0, 1.0)
    relationship_coverage = sum(1 for row in evidence_backed if row.get("related_entities", 0) > 0) / len(evidence_backed)
    final_score = 0.35 * coverage + 0.45 * density + 0.20 * relationship_coverage
    reasoning_parts.extend([
        f"{len(evidence_backed)}/{num_facts} facts verified by graph aggregation",
        f"average entity support {average_support:.1f}",
        f"relationship coverage {relationship_coverage:.0%}",
    ])

    if abstention_result.get("has_conflict"):
        final_score -= 0.25
        reasoning_parts.append("conflict detected")

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
