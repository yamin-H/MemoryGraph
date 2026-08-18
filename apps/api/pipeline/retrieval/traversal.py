"""Graph traversal for MemoryGraph retrieval.

Retrieves relevant facts from HydraDB based on parsed questions.
"""

from typing import Any

from db.hydra import HydraDB


def traverse_for_question(
    hydra: HydraDB,
    parsed_question: dict[str, Any],
    user_id: str = "anonymous",
) -> list[dict[str, Any]]:
    """Retrieve relevant facts from HydraDB for a parsed question.

    Args:
        hydra: HydraDB connection (must be connected)
        parsed_question: Parsed question with entity_name, question_type, keywords
        user_id: User ID to scope retrieval (prevents cross-user contamination)

    Returns:
        List of relevant facts with session information
    """
    entity_name = parsed_question.get("entity_name")
    question_type = parsed_question.get("question_type", "current_fact")
    keywords = parsed_question.get("keywords", [])

    is_user_query = (
        not entity_name
        or entity_name.lower() in ("user", "me", "my", "i", "myself", "anonymous")
    )

    facts = []

    with hydra._driver.session() as session:
        # If entity is specified and not a generic user pronoun, try entity-specific match first
        if not is_user_query:
            # A fact is current only when it is a leaf of its SUPERSEDES lineage.
            # is_current is a write-side cache and is deliberately not trusted here.
            result = session.run(
                "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {user_id: $user_id}) "
                "MATCH (f)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                "WHERE toLower(e.name) = toLower($entity_name) "
                "AND NOT (f)<-[:SUPERSEDES*1..]-(newer_f:Fact) "
                "AND NOT (f)-[:INVALIDATED_BY]->(inv:Session) "
                "RETURN f.id, f.content, f.confidence, true AS is_current, f.created_at, "
                "       s.session_id, s.started_at",
                entity_name=entity_name,
                user_id=user_id,
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
                "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                "WHERE NOT (f)<-[:SUPERSEDES*1..]-(newer_f2:Fact) "
                "AND NOT (f)-[:INVALIDATED_BY]->(inv2:Session) "
                "RETURN f.id, f.content, f.confidence, true AS is_current, f.created_at, "
                "       s.session_id, s.started_at LIMIT 100",
                user_id=user_id,
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
                "MATCH (newest:Fact)-[:SUPERSEDES*1..]->(f:Fact)-[:MENTIONS]->"
                "(e:Entity {user_id: $user_id}) "
                "MATCH (f)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
                "WHERE toLower(e.name) = toLower($entity_name) "
                "AND NOT (newest)<-[:SUPERSEDES*1..]-(newer_f3:Fact) "
                "RETURN DISTINCT f.id, f.content, f.confidence, false AS is_current, f.created_at, "
                "       s.session_id, s.started_at, newest.id as superseded_by",
                entity_name=entity_name,
                user_id=user_id,
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
    if keywords and facts:
        filtered = []
        for fact in facts:
            content_lower = fact["content"].lower()
            if any(kw.lower() in content_lower for kw in keywords):
                filtered.append(fact)
        if filtered:
            facts = filtered

    return facts


def get_confidence_evidence(
    hydra: HydraDB,
    facts: list[dict[str, Any]],
    user_id: str,
) -> dict[str, dict[str, int]]:
    """Aggregate user-scoped graph support for confidence calibration.

    The aggregation intentionally follows ``MENTIONS`` and ``OCCURRED_IN``
    relationships. It is therefore evidence about the connected memory graph,
    not a synthetic score assigned by the application layer.
    """
    fact_ids = [fact.get("fact_id") for fact in facts if fact.get("fact_id") is not None]
    if not fact_ids:
        return {}

    evidence: dict[str, dict[str, int]] = {}
    with hydra._driver.session() as session:
        result = session.run(
            "MATCH (f:Fact)-[:OCCURRED_IN]->(sess:Session {user_id: $user_id}) "
            "WHERE f.id IN $fact_ids "
            "OPTIONAL MATCH (f)-[:MENTIONS]->(e:Entity {user_id: $user_id}) "
            "OPTIONAL MATCH (e)<-[:MENTIONS]-(support:Fact)-[:OCCURRED_IN]->"
            "(sess2:Session {user_id: $user_id}) "
            "RETURN f.id AS fact_id, count(DISTINCT support) AS supporting_facts, "
            "count(DISTINCT e) AS related_entities",
            fact_ids=fact_ids,
            user_id=user_id,
        )
        for record in result:
            evidence[str(record["fact_id"])] = {
                "supporting_facts": int(record["supporting_facts"] or 0),
                "related_entities": int(record["related_entities"] or 0),
            }
    return evidence


def get_all_facts_for_entity(
    hydra: HydraDB,
    entity_name: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Get all facts for an entity, including historical.

    Args:
        hydra: HydraDB connection (must be connected)
        entity_name: Name of the entity
        user_id: Owner of the entity and facts

    Returns:
        List of all facts for the entity
    """
    facts = []

    with hydra._driver.session() as session:
        result = session.run(
            "MATCH (f:Fact)-[:MENTIONS]->(e:Entity {name: $entity_name, user_id: $user_id}) "
            "MATCH (f)-[:OCCURRED_IN]->(s:Session {user_id: $user_id}) "
            "OPTIONAL MATCH (f)-[:INVALIDATED_BY]->(inv:Session) "
            "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
            "       s.session_id, s.started_at",
            entity_name=entity_name,
            user_id=user_id,
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


def multi_entity_retrieval(
    hydra: HydraDB,
    entity_names: list[str],
    user_id: str = "anonymous",
) -> list[dict[str, Any]]:
    """Retrieve facts along bounded paths between multiple entities using HydraDB's native algo.MSpaths.

    HydraDB implements SuiteSparse GraphBLAS matrix multiplication (algo.MSpaths) to evaluate
    bounded multi-source and multi-target paths in a single synchronized operation.
    """
    if not entity_names:
        return []

    facts: list[dict[str, Any]] = []
    seen_fact_ids: set[Any] = set()

    with hydra._driver.session() as session:
        try:
            # Native HydraDB SuiteSparse GraphBLAS multi-source multi-target procedure
            query = """
            CALL algo.MSpaths({
              sourceLabel: 'Entity',
              sourceProperty: 'name',
              sourceValues: $entity_names,
              targetValues: $entity_names,
              pairwise: true,
              relTypes: ['SUPERSEDES', 'MENTIONS', 'ASSERTS'],
              relDirection: 'both',
              maxLen: 5,
              pathCount: 10,
              resultLimit: 100
            })
            YIELD path
            RETURN path
            """
            result = session.run(query, entity_names=entity_names)
            for record in result:
                path_obj = record.get("path")
                if not path_obj:
                    continue
                nodes = getattr(path_obj, "nodes", []) if hasattr(path_obj, "nodes") else []
                for node in nodes:
                    labels = getattr(node, "labels", set())
                    if "Fact" in labels or "Fact" in str(labels):
                        fact_id = node.get("id") if hasattr(node, "get") else getattr(node, "id", None)
                        if fact_id and fact_id not in seen_fact_ids:
                            seen_fact_ids.add(fact_id)
                            content = node.get("content", "") if hasattr(node, "get") else getattr(node, "content", "")
                            confidence = node.get("confidence", 0.9) if hasattr(node, "get") else getattr(node, "confidence", 0.9)
                            is_curr = node.get("is_current", True) if hasattr(node, "get") else getattr(node, "is_current", True)
                            created_at = node.get("created_at", "") if hasattr(node, "get") else getattr(node, "created_at", "")
                            session_id = node.get("session_id", "") if hasattr(node, "get") else getattr(node, "session_id", "")
                            facts.append({
                                "fact_id": fact_id,
                                "content": content,
                                "confidence": confidence,
                                "is_current": is_curr,
                                "created_at": created_at,
                                "session_id": session_id,
                                "session_started_at": created_at,
                            })
        except Exception:
            # Fallback path query if algo.MSpaths is mocked or running on standalone environments
            fallback_query = """
            MATCH path = (e1:Entity {user_id: $user_id})-[r:MENTIONS|SUPERSEDES|ASSERTS*1..5]-(e2:Entity {user_id: $user_id})
            WHERE toLower(e1.name) IN [name IN $entity_names | toLower(name)]
              AND toLower(e2.name) IN [name IN $entity_names | toLower(name)]
              AND e1.name <> e2.name
            RETURN path LIMIT 100
            """
            result = session.run(fallback_query, entity_names=entity_names, user_id=user_id)
            for record in result:
                path_obj = record.get("path")
                if not path_obj:
                    continue
                nodes = getattr(path_obj, "nodes", []) if hasattr(path_obj, "nodes") else []
                for node in nodes:
                    labels = getattr(node, "labels", set())
                    if "Fact" in labels or "Fact" in str(labels):
                        fact_id = node.get("id") if hasattr(node, "get") else getattr(node, "id", None)
                        if fact_id and fact_id not in seen_fact_ids:
                            seen_fact_ids.add(fact_id)
                            content = node.get("content", "") if hasattr(node, "get") else getattr(node, "content", "")
                            confidence = node.get("confidence", 0.9) if hasattr(node, "get") else getattr(node, "confidence", 0.9)
                            is_curr = node.get("is_current", True) if hasattr(node, "get") else getattr(node, "is_current", True)
                            created_at = node.get("created_at", "") if hasattr(node, "get") else getattr(node, "created_at", "")
                            session_id = node.get("session_id", "") if hasattr(node, "get") else getattr(node, "session_id", "")
                            facts.append({
                                "fact_id": fact_id,
                                "content": content,
                                "confidence": confidence,
                                "is_current": is_curr,
                                "created_at": created_at,
                                "session_id": session_id,
                                "session_started_at": created_at,
                            })

    return facts


def get_multi_entity_paths(
    hydra: HydraDB,
    entity_names: list[str],
    user_id: str = "anonymous",
) -> dict[str, Any]:
    """Retrieve full path topology between multiple entities for the Multi-Entity visualizer."""
    if not entity_names:
        return {
            "user_id": user_id,
            "entities": [],
            "procedure": "algo.MSpaths (SuiteSparse GraphBLAS)",
            "nodes": [],
            "edges": [],
            "paths": [],
            "facts": [],
        }

    nodes_map: dict[str, dict[str, Any]] = {}
    edges_list: list[dict[str, Any]] = []
    seen_edge_keys: set[str] = set()
    paths_list: list[dict[str, Any]] = []
    facts_list: list[dict[str, Any]] = []
    seen_fact_ids: set[Any] = set()

    with hydra._driver.session() as session:
        records_to_process = []
        try:
            # First attempt native GraphBLAS algo.MSpaths procedure
            query = """
            CALL algo.MSpaths({
              sourceLabel: 'Entity',
              sourceProperty: 'name',
              sourceValues: $entity_names,
              targetValues: $entity_names,
              pairwise: true,
              relTypes: ['SUPERSEDES', 'MENTIONS', 'ASSERTS'],
              relDirection: 'both',
              maxLen: 5,
              pathCount: 10,
              resultLimit: 100
            })
            YIELD path
            RETURN path
            """
            result = session.run(query, entity_names=entity_names)
            records_to_process = list(result)
        except Exception:
            records_to_process = []

        if not records_to_process:
            fallback_query = """
            MATCH path = (e1:Entity {user_id: $user_id})-[r:MENTIONS|SUPERSEDES|ASSERTS*1..5]-(e2:Entity {user_id: $user_id})
            WHERE toLower(e1.name) IN [name IN $entity_names | toLower(name)]
              AND toLower(e2.name) IN [name IN $entity_names | toLower(name)]
              AND e1.name <> e2.name
            RETURN path LIMIT 100
            """
            result = session.run(fallback_query, entity_names=entity_names, user_id=user_id)
            records_to_process = list(result)

        path_counter = 0
        for record in records_to_process:
            path_obj = record.get("path")
            if not path_obj:
                continue

            path_counter += 1
            nodes = getattr(path_obj, "nodes", []) if hasattr(path_obj, "nodes") else []
            relationships = getattr(path_obj, "relationships", []) if hasattr(path_obj, "relationships") else []

            fact_chain_for_path = []
            start_name = entity_names[0] if entity_names else "Entity"
            end_name = entity_names[-1] if entity_names else "Entity"

            for node in nodes:
                node_id = str(node.get("id") if hasattr(node, "get") else getattr(node, "id", f"n_{len(nodes_map)}"))
                labels = list(getattr(node, "labels", ["Node"]))
                primary_label = labels[0] if labels else "Node"

                if primary_label == "Entity" or "Entity" in labels:
                    name = node.get("name", "") if hasattr(node, "get") else getattr(node, "name", "Entity")
                    nodes_map[node_id] = {
                        "id": node_id,
                        "label": name,
                        "type": "Entity",
                        "data": {
                            "name": name,
                            "type": node.get("type", "entity") if hasattr(node, "get") else "entity",
                        },
                    }
                elif primary_label == "Fact" or "Fact" in labels:
                    content = node.get("content", "") if hasattr(node, "get") else getattr(node, "content", "")
                    is_curr = node.get("is_current", True) if hasattr(node, "get") else getattr(node, "is_current", True)
                    created_at = node.get("created_at", "") if hasattr(node, "get") else getattr(node, "created_at", "")
                    confidence = node.get("confidence", 0.9) if hasattr(node, "get") else getattr(node, "confidence", 0.9)

                    nodes_map[node_id] = {
                        "id": node_id,
                        "label": content[:40] if content else f"Fact #{node_id}",
                        "type": "Fact",
                        "data": {
                            "content": content,
                            "is_current": is_curr,
                            "created_at": created_at,
                            "confidence": confidence,
                        },
                    }

                    if node_id not in seen_fact_ids:
                        seen_fact_ids.add(node_id)
                        facts_list.append({
                            "fact_id": node_id,
                            "content": content,
                            "confidence": confidence,
                            "is_current": is_curr,
                            "created_at": created_at,
                        })

                    fact_chain_for_path.append({
                        "fact_id": node_id,
                        "content": content,
                        "is_current": is_curr,
                        "created_at": created_at,
                    })

            for rel in relationships:
                start_id = str(rel.start_node.get("id") if hasattr(rel.start_node, "get") else getattr(rel.start_node, "id", ""))
                end_id = str(rel.end_node.get("id") if hasattr(rel.end_node, "get") else getattr(rel.end_node, "id", ""))
                rel_type = getattr(rel, "type", "RELATES_TO")
                edge_key = f"{start_id}->{end_id}:{rel_type}"

                if edge_key not in seen_edge_keys:
                    seen_edge_keys.add(edge_key)
                    edges_list.append({
                        "source": start_id,
                        "target": end_id,
                        "type": rel_type,
                        "data": {
                            "type": rel_type,
                            "reason": rel.get("reason", "") if hasattr(rel, "get") else "",
                        },
                    })

            paths_list.append({
                "path_id": f"path-{path_counter}",
                "length": len(relationships),
                "start_entity": start_name,
                "end_entity": end_name,
                "fact_chain": fact_chain_for_path,
            })

    return {
        "user_id": user_id,
        "entities": entity_names,
        "procedure": "algo.MSpaths (SuiteSparse GraphBLAS)",
        "paths_found": len(paths_list),
        "nodes": list(nodes_map.values()),
        "edges": edges_list,
        "paths": paths_list,
        "facts": facts_list,
    }


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
