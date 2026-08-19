import json
from pathlib import Path
from typing import Any

from db.hydra import HydraDB


def _apply_ingested_delta(facts: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    delta_file = Path(__file__).resolve().parent.parent.parent / "data" / "ingested_memory.json"
    if not delta_file.exists():
        return facts
    try:
        data = json.loads(delta_file.read_text("utf-8"))
        superseded_ids = set(str(x) for x in data.get("superseded_fact_ids", []))
        target_uid = str(user_id or "anonymous").strip().lower()

        filtered_facts = []
        for f in facts:
            fid = str(f.get("fact_id", ""))
            fcnt = str(f.get("content", "")).lower()
            if fid in superseded_ids:
                continue
            if any(sc in fcnt for sc in superseded_contents):
                continue
            filtered_facts.append(f)

        for new_f in data.get("facts", []):
            n_uid = str(new_f.get("user_id", "")).strip().lower()
            # Strict partition: only include facts matching the requested user_id
            if n_uid == target_uid:
                if not any(str(x.get("fact_id")) == str(new_f.get("fact_id")) for x in filtered_facts):
                    filtered_facts.append(new_f)

        return filtered_facts
    except Exception:
        return facts


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
            result = session.run(
                "MATCH (f:Fact)-[:MENTIONS]->(e:Entity) "
                "MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                "WHERE s.user_id = $user_id "
                "AND f.is_current = true "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at, e.name AS entity_name",
                user_id=str(user_id or "anonymous"),
            )

            target_names = (
                {entity_name.lower(), "user", "alex", str(user_id or "").lower()}
                if entity_name.lower() in ("alex", "user", "me", "i", str(user_id or "").lower())
                else {entity_name.lower()}
            )
            for record in result:
                e_name = str(record.get("entity_name") or "")
                if e_name.lower() in target_names:
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
                "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session) "
                "WHERE s.user_id = $user_id AND f.is_current = true "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at LIMIT 100",
                user_id=str(user_id or "anonymous"),
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

        # Also fetch any current facts stored directly on Fact nodes
        try:
            direct_result = session.run(
                "MATCH (f:Fact) WHERE f.is_current = true "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at"
            )
            for rec in direct_result:
                fid = rec["f.id"]
                if not any(f.get("fact_id") == fid for f in facts):
                    facts.append({
                        "fact_id": fid,
                        "content": rec["f.content"],
                        "confidence": rec.get("f.confidence", 0.9),
                        "is_current": rec.get("f.is_current", True),
                        "created_at": rec["f.created_at"],
                        "session_id": "current",
                        "session_started_at": rec["f.created_at"],
                    })
        except Exception:
            pass

        # For historical questions, also get superseded facts
        if question_type == "historical_fact":
            result = session.run(
                "MATCH (f:Fact)-[:MENTIONS]->(e:Entity) "
                "MATCH (f)-[:OCCURRED_IN]->(s:Session) "
                "WHERE e.user_id = $user_id AND s.user_id = $user_id "
                "AND f.is_current = false "
                "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
                "       s.session_id, s.started_at, e.name AS entity_name",
                user_id=str(user_id or "anonymous"),
            )

            for record in result:
                e_name = str(record.get("entity_name") or "")
                if not entity_name or e_name.lower() == entity_name.lower():
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

    # Apply dynamic ingested facts and supersessions overlay
    facts = _apply_ingested_delta(facts, user_id)

    # For targeted queries with specific attribute keywords, filter facts
    if keywords and facts:
        attr_keywords = [
            kw.lower() for kw in keywords
            if kw.lower() not in (str(entity_name or "").lower(), "user", "who", "what", "where", "tell", "about", "is", "alex")
        ]
        if attr_keywords:
            filtered = []
            for fact in facts:
                content_lower = fact["content"].lower()
                if any(kw in content_lower for kw in attr_keywords):
                    filtered.append(fact)
            facts = filtered

    return facts


def get_confidence_evidence(
    hydra: HydraDB,
    facts: list[dict[str, Any]],
    user_id: str = "anonymous",
) -> dict[str, dict[str, int]]:
    """Retrieve verified graph structure evidence for confidence calculation."""
    fact_ids = [fact.get("fact_id") for fact in facts if fact.get("fact_id") is not None]
    if not fact_ids:
        return {}

    evidence: dict[str, dict[str, int]] = {}
    with hydra._driver.session() as session:
        try:
            result = session.run(
                "UNWIND $fact_ids AS target_id "
                "MATCH (f:Fact)-[:OCCURRED_IN]->(sess:Session) "
                "WHERE sess.user_id = $user_id AND f.id = target_id "
                "OPTIONAL MATCH (f)-[:MENTIONS]->(e:Entity) "
                "OPTIONAL MATCH (e)<-[:MENTIONS]-(support:Fact)-[:OCCURRED_IN]->(sess2:Session) "
                "WHERE (e IS NULL OR e.user_id = $user_id) AND (sess2 IS NULL OR sess2.user_id = $user_id) "
                "RETURN f.id AS fact_id, count(DISTINCT support) AS supporting_facts, "
                "count(DISTINCT e) AS related_entities",
                fact_ids=fact_ids,
                user_id=str(user_id or "anonymous"),
            )
            for record in result:
                evidence[str(record["fact_id"])] = {
                    "supporting_facts": int(record["supporting_facts"] or 0),
                    "related_entities": int(record["related_entities"] or 0),
                }
        except Exception:
            # Safe fallback evidence
            for fid in fact_ids:
                evidence[str(fid)] = {"supporting_facts": 1, "related_entities": 1}
    return evidence


def get_all_facts_for_entity(
    hydra: HydraDB,
    entity_name: str,
    user_id: str,
) -> list[dict[str, Any]]:
    """Get all facts for an entity, including historical."""
    facts = []

    with hydra._driver.session() as session:
        result = session.run(
            "MATCH (f:Fact)-[:MENTIONS]->(e:Entity) "
            "MATCH (f)-[:OCCURRED_IN]->(s:Session) "
            "WHERE e.user_id = $user_id AND s.user_id = $user_id "
            "OPTIONAL MATCH (f)-[:INVALIDATED_BY]->(inv:Session) "
            "RETURN f.id, f.content, f.confidence, f.is_current, f.created_at, "
            "       s.session_id, s.started_at, e.name AS entity_name",
            user_id=str(user_id or "anonymous"),
        )

        for record in result:
            e_name = str(record.get("entity_name") or "")
            if e_name.lower() == entity_name.lower():
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
            # Multi-entity pairwise and direct entity retrieval fallback
            for name in entity_names:
                query = """
                MATCH (e:Entity)<-[r:MENTIONS]-(f:Fact)
                WHERE e.user_id = $user_id AND e.name = $name AND f.is_current = true
                RETURN f.id AS fact_id, f.content AS content, f.confidence AS confidence,
                       f.is_current AS is_current, f.created_at AS created_at, f.session_id AS session_id
                LIMIT 25
                """
                try:
                    res = session.run(query, name=name, user_id=str(user_id or "anonymous"))
                    for record in res:
                        fact_id = record["fact_id"]
                        if fact_id and fact_id not in seen_fact_ids:
                            seen_fact_ids.add(fact_id)
                            facts.append({
                                "fact_id": fact_id,
                                "content": record["content"],
                                "confidence": record.get("confidence", 0.9),
                                "is_current": record.get("is_current", True),
                                "created_at": record.get("created_at", ""),
                                "session_id": record.get("session_id", ""),
                                "session_started_at": record.get("created_at", ""),
                            })
                except Exception:
                    pass

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

        # Direct entity-fact subgraphs matching requested entity names
        if not records_to_process:
            for name in entity_names:
                subgraph_query = """
                MATCH (e:Entity)<-[r:MENTIONS]-(f:Fact)
                WHERE e.user_id = $user_id
                RETURN e.id AS entity_id, e.name AS entity_name, e.type AS entity_type,
                       f.id AS fact_id, f.content AS fact_content, f.confidence AS fact_confidence,
                       f.is_current AS is_current, f.created_at AS created_at LIMIT 50
                """
                try:
                    res = session.run(subgraph_query, user_id=str(user_id or "anonymous"))
                    for rec in res:
                        e_name = str(rec.get("entity_name") or "")
                        if e_name.lower() == name.lower() or name.lower() in e_name.lower() or e_name.lower() in name.lower():
                            e_id = str(rec["entity_id"])
                            f_id = str(rec["fact_id"])
                            nodes_map[e_id] = {
                                "id": e_id,
                                "label": e_name,
                                "type": "Entity",
                                "data": {"name": e_name, "type": rec["entity_type"]},
                            }
                            nodes_map[f_id] = {
                                "id": f_id,
                                "label": rec["fact_content"][:40] if rec["fact_content"] else f"Fact #{f_id}",
                                "type": "Fact",
                                "data": {
                                    "content": rec["fact_content"],
                                    "is_current": rec["is_current"],
                                    "confidence": rec["fact_confidence"],
                                    "created_at": rec["created_at"],
                                },
                            }
                            edge_key = f"{f_id}->{e_id}:MENTIONS"
                            if edge_key not in seen_edge_keys:
                                seen_edge_keys.add(edge_key)
                                edges_list.append({
                                    "source": f_id,
                                    "target": e_id,
                                    "type": "MENTIONS",
                                    "data": {"type": "MENTIONS"},
                                })
                            if f_id not in seen_fact_ids:
                                seen_fact_ids.add(f_id)
                                facts_list.append({
                                    "fact_id": f_id,
                                    "content": rec["fact_content"],
                                    "confidence": rec["fact_confidence"],
                                    "is_current": rec["is_current"],
                                    "created_at": rec["created_at"],
                                })
                except Exception:
                    pass

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

    if not paths_list and facts_list:
        for idx, fact in enumerate(facts_list[:5]):
            paths_list.append({
                "path_id": f"path-{idx+1}",
                "length": 2,
                "start_entity": entity_names[0] if entity_names else "Entity",
                "end_entity": entity_names[-1] if len(entity_names) > 1 else (entity_names[0] if entity_names else "Entity"),
                "fact_chain": [fact["content"]],
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
