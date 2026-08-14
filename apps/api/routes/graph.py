"""Graph routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter

from db.hydra import HydraDB

router = APIRouter()


def get_hydra():
    """Get HydraDB client - will be overridden by main app."""
    from db.hydra import HydraDB
    db = HydraDB()
    db.connect()
    return db


@router.get("/session/{session_id}")
async def get_session_graph(session_id: str) -> dict[str, Any]:
    """Get all nodes and edges for a session.

    Returns data formatted for react-force-graph.

    Args:
        session_id: Session identifier

    Returns:
        Graph data with nodes and edges arrays
    """
    hydra = get_hydra()
    nodes = []
    edges = []
    node_ids = set()

    with hydra._driver.session() as session:
        # Get session node
        result = session.run(
            "MATCH (s:Session {session_id: $session_id}) RETURN s.id, s.session_id, s.user_id, s.started_at",
            session_id=session_id,
        )
        record = result.single()
        if record:
            node_id = record["s.id"]
            nodes.append({
                "id": node_id,
                "label": f"Session: {session_id}",
                "type": "Session",
                "data": {
                    "session_id": record["s.session_id"],
                    "user_id": record["s.user_id"],
                    "started_at": record["s.started_at"],
                },
            })
            node_ids.add(node_id)

        # Get messages
        result = session.run(
            "MATCH (s:Session {session_id: $session_id})-[:CONTAINS]->(m:Message) "
            "RETURN m.id, m.role, m.content, m.created_at",
            session_id=session_id,
        )
        for record in result:
            node_id = record["m.id"]
            nodes.append({
                "id": node_id,
                "label": f"{record['m.role']}: {record['m.content'][:30]}...",
                "type": "Message",
                "data": {
                    "role": record["m.role"],
                    "content": record["m.content"],
                    "created_at": record["m.created_at"],
                },
            })
            node_ids.add(node_id)
            edges.append({
                "source": node_ids.pop() if node_id in node_ids else node_id,  # session_id hack
                "target": node_id,
                "type": "CONTAINS",
            })

        # Get facts
        result = session.run(
            "MATCH (f:Fact)-[:OCCURRED_IN]->(s:Session {session_id: $session_id}) "
            "RETURN f.id, f.content, f.confidence, f.is_current",
            session_id=session_id,
        )
        for record in result:
            node_id = record["f.id"]
            nodes.append({
                "id": node_id,
                "label": record["f.content"][:40],
                "type": "Fact",
                "data": {
                    "content": record["f.content"],
                    "confidence": record["f.confidence"],
                    "is_current": record["f.is_current"],
                },
            })

    hydra.close()
    return {"nodes": nodes, "edges": edges}


@router.get("/entity/{entity_name}")
async def get_entity_history(entity_name: str) -> dict[str, Any]:
    """Get full fact history for an entity.

    Includes SUPERSEDES chain traversal.

    Args:
        entity_name: Name of the entity

    Returns:
        Entity data with current facts and historical facts
    """
    hydra = get_hydra()
    current_facts = []
    historical_facts = []

    with hydra._driver.session() as session:
        # Get current facts
        result = session.run(
            "MATCH (f:Fact {is_current: true})-[:MENTIONS]->(e:Entity {name: $entity_name}) "
            "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
            "RETURN f.id, f.content, f.confidence, f.created_at, s.session_id",
            entity_name=entity_name,
        )
        for record in result:
            current_facts.append({
                "fact_id": record["f.id"],
                "content": record["f.content"],
                "confidence": record["f.confidence"],
                "created_at": record["f.created_at"],
                "session_id": record["s.session_id"],
            })

        # Get historical (superseded) facts
        result = session.run(
            "MATCH (f:Fact {is_current: false})-[:MENTIONS]->(e:Entity {name: $entity_name}) "
            "MATCH (f)<-[:SUPERSEDES]-(newer:Fact) "
            "OPTIONAL MATCH (f)-[:OCCURRED_IN]->(s:Session) "
            "RETURN f.id, f.content, f.confidence, f.created_at, s.session_id, newer.id as superseded_by",
            entity_name=entity_name,
        )
        for record in result:
            historical_facts.append({
                "fact_id": record["f.id"],
                "content": record["f.content"],
                "confidence": record["f.confidence"],
                "created_at": record["f.created_at"],
                "session_id": record["s.session_id"],
                "superseded_by": record["superseded_by"],
            })

    hydra.close()
    return {
        "entity_name": entity_name,
        "current_facts": current_facts,
        "historical_facts": historical_facts,
        "total_facts": len(current_facts) + len(historical_facts),
    }
