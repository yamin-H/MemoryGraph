"""Graph traversal for MemoryGraph retrieval.

Retrieves relevant facts from HydraDB based on parsed questions.
"""

from typing import Any

from db.hydra import HydraDB


def traverse_for_question(
    hydra: HydraDB,
    parsed_question: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retrieve relevant facts from HydraDB for a parsed question.

    Args:
        hydra: HydraDB connection (must be connected)
        parsed_question: Parsed question with entity_name, question_type, keywords

    Returns:
        List of relevant facts with session information
    """
    entity_name = parsed_question.get("entity_name")
    question_type = parsed_question.get("question_type", "current_fact")
    keywords = parsed_question.get("keywords", [])

    is_user_query = (
        not entity_name
        or entity_name.lower() in ("user", "me", "my", "i", "myself", "anonymous", "alex")
    )

    facts = []

    with hydra._driver.session() as session:
        # If entity is specified and not a generic user pronoun, try entity-specific match first
        if not is_user_query:
            # Fast path: Check summaries first for broad questions
            if question_type == "multi_session_synthesis":
                result = session.run(
                    "MATCH (sum:Summary)-[:SUMMARY_ANCHOR]->() "
                    "WHERE toLower(sum.content) CONTAINS toLower($entity_name) "
                    "RETURN sum.content, sum.created_at",
                    entity_name=entity_name,
                )
                summaries = list(result)

            # Deep path: Traverse to Fact nodes for entity
            result = session.run(
                "MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e:Entity) "
                "WHERE toLower(e.name) = toLower($entity_name) "
                "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at",
                entity_name=entity_name,
            )

            for record in result:
                fact = {
                    "fact_id": record["f.id"],
                    "content": record["f.content"],
                    "confidence": record["f.confidence"],
                    "is_current": record["f.is_current"],
                    "created_at": record["f.created_at"],
                    "session_id": record["s.session_id"],
                    "session_started_at": record["s.started_at"],
                }
                facts.append(fact)

        # If 1st-person / User query OR no facts found for named entity, search all active facts
        if not facts:
            result = session.run(
                "MATCH (f:Fact {is_current: true}) "
                "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at LIMIT 100"
            )

            for record in result:
                fact = {
                    "fact_id": record["f.id"],
                    "content": record["f.content"],
                    "confidence": record["f.confidence"],
                    "is_current": record["f.is_current"],
                    "created_at": record["f.created_at"],
                    "session_id": record["s.session_id"],
                    "session_started_at": record["s.started_at"],
                }
                facts.append(fact)

        # For historical questions, also get superseded facts
        if question_type == "historical_fact":
            result = session.run(
                "MATCH (f:Fact {is_current: false})-[:MENTIONS]->(e:Entity {name: $entity_name}) "
                "MATCH (f)<-[:SUPERSEDES]-(newer:Fact) "
                "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at, newer.id as superseded_by",
                entity_name=entity_name,
            )

            for record in result:
                fact = {
                    "fact_id": record["f.id"],
                    "content": record["f.content"],
                    "confidence": record["f.confidence"],
                    "is_current": record["f.is_current"],
                    "created_at": record["f.created_at"],
                    "session_id": record["s.session_id"],
                    "session_started_at": record["s.started_at"],
                    "superseded_by": record["superseded_by"],
                }
                facts.append(fact)

    # For targeted queries, prioritize facts matching keywords while preserving relevant entity context
    if keywords and facts and len(facts) > 10:
        filtered = []
        for fact in facts:
            content_lower = fact["content"].lower()
            if any(kw.lower() in content_lower for kw in keywords):
                filtered.append(fact)
        if filtered:
            facts = filtered

    return facts


def get_all_facts_for_entity(
    hydra: HydraDB,
    entity_name: str,
) -> list[dict[str, Any]]:
    """Get all facts for an entity, including historical.

    Args:
        hydra: HydraDB connection (must be connected)
        entity_name: Name of the entity

    Returns:
        List of all facts for the entity
    """
    facts = []

    with hydra._driver.session() as session:
        result = session.run(
            "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {name: $entity_name}) "
            "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
            "OPTIONAL MATCH (f)-[:INVALIDATED_BY]->(inv:Session) "
            "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
            "       s.session_id, s.started_at",
            entity_name=entity_name,
        )

        for record in result:
            fact = {
                "fact_id": record["f.id"],
                "content": record["f.content"],
                "confidence": record["f.confidence"],
                "is_current": record["f.is_current"],
                "created_at": record["f.created_at"],
                "session_id": record["s.session_id"],
                "session_started_at": record["s.started_at"],
            }
            facts.append(fact)

    return facts


def main():
    """Test the graph traversal."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent.parent.parent.parent / ".env"
    load_dotenv(env_path)

    hydra = HydraDB()
    hydra.connect()

    print("Testing graph traversal")
    print("=" * 50)

    try:
        # Test with Alex entity
        parsed = {
            "entity_name": "Alex",
            "question_type": "current_fact",
            "keywords": ["live", "location"],
        }

        facts = traverse_for_question(hydra, parsed)

        print(f"Found {len(facts)} facts for entity 'Alex':")
        for fact in facts:
            print(f"  - {fact['content']} (current: {fact['is_current']})")

    finally:
        hydra.close()
        print("\nConnection closed")


if __name__ == "__main__":
    main()
