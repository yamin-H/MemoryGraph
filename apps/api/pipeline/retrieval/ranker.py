"""Fact ranker for MemoryGraph retrieval.

Sorts retrieved facts chronologically and detects conflicts.
"""

from typing import Any


def rank_facts_by_time(
    facts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort facts chronologically and flag conflicts.

    Args:
        facts: List of facts from traversal

    Returns:
        Ranked list of facts with conflict flags
    """
    if not facts:
        return []

    # Sort by session timestamp (most recent first)
    sorted_facts = sorted(
        facts,
        key=lambda f: f.get("session_started_at") or f.get("created_at") or "",
        reverse=True,
    )

    # Detect conflicts: same entity, no SUPERSEDES link, both is_current
    # Group by approximate topic (first few words of content)
    topic_groups: dict[str, list[dict[str, Any]]] = {}

    for fact in sorted_facts:
        if not fact.get("is_current"):
            continue

        # Extract topic from content (first 3 significant words)
        content = fact.get("content", "")
        words = [w.lower() for w in content.split() if len(w) > 3][:3]
        topic_key = " ".join(words)

        if topic_key not in topic_groups:
            topic_groups[topic_key] = []
        topic_groups[topic_key].append(fact)

    # Flag conflicts
    for topic, group in topic_groups.items():
        if len(group) > 1:
            # Multiple current facts about similar topic
            for fact in group:
                fact["has_conflict"] = True
                fact["conflict_count"] = len(group)

    return sorted_facts


def resolve_conflicts(
    facts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Resolve conflicts by preferring most recent facts.

    Args:
        facts: Ranked list of facts with conflict flags

    Returns:
        Tuple of (resolved_facts, conflicts_found)
    """
    resolved = []
    conflicts = []

    for fact in facts:
        if fact.get("has_conflict"):
            conflicts.append(fact)
            # Include in resolved if it's the most recent
            if fact == conflicts[0]:
                resolved.append(fact)
        else:
            resolved.append(fact)

    return resolved, conflicts


def main():
    """Test the fact ranker."""
    # Sample facts
    sample_facts = [
        {
            "fact_id": "1",
            "content": "Alex lives in Dhaka",
            "is_current": True,
            "created_at": "2024-01-15T10:30:00Z",
            "session_started_at": "2024-01-15T10:30:00Z",
        },
        {
            "fact_id": "2",
            "content": "Alex works as a software engineer",
            "is_current": True,
            "created_at": "2024-01-14T09:00:00Z",
            "session_started_at": "2024-01-14T09:00:00Z",
        },
        {
            "fact_id": "3",
            "content": "Alex lives in Rajshahi",
            "is_current": False,
            "created_at": "2024-01-10T08:00:00Z",
            "session_started_at": "2024-01-10T08:00:00Z",
        },
    ]

    print("Testing fact ranker")
    print("=" * 50)

    ranked = rank_facts_by_time(sample_facts)

    print(f"Ranked {len(ranked)} facts:")
    for i, fact in enumerate(ranked, 1):
        conflict = " [CONFLICT]" if fact.get("has_conflict") else ""
        print(f"  {i}. {fact['content']} (current: {fact['is_current']}){conflict}")


if __name__ == "__main__":
    main()
