"""Graph routes for MemoryGraph API."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from services.memory_service import MemoryService

router = APIRouter()
service = MemoryService()

DELTA_FILE = Path(__file__).resolve().parent.parent / "data" / "ingested_memory.json"


def _build_delta_graph(entity_name: str, user_id: str) -> dict[str, Any]:
    """Build graph nodes/edges from the ingested_memory.json delta overlay.

    This covers users/entities whose data was ingested dynamically but couldn't
    be written to HydraDB (due to HydraDB OSS write limitations).
    """
    if not DELTA_FILE.exists():
        return {"nodes": [], "edges": []}

    try:
        data = json.loads(DELTA_FILE.read_text("utf-8"))
    except Exception:
        return {"nodes": [], "edges": []}

    target_uid = user_id.strip().lower()
    entity_lower = entity_name.strip().lower()

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    seen_session_ids: set[str] = set()

    # Build an entity node for the searched entity
    entity_node_id = f"entity-{entity_lower}"

    for fact in data.get("facts", []):
        f_uid = str(fact.get("user_id", "")).strip().lower()
        if f_uid != target_uid:
            continue

        content = fact.get("content", "")
        f_entity = str(fact.get("entity_name", "")).strip().lower()

        # Match: entity name matches OR content mentions the entity OR it's a "User" entity for this user
        content_lower = content.lower()
        is_match = (
            f_entity == entity_lower
            or entity_lower in content_lower
            or (f_entity in ("user", "") and entity_lower == target_uid)
        )
        if not is_match:
            continue

        # Add entity node if not yet added
        if entity_node_id not in seen_node_ids:
            seen_node_ids.add(entity_node_id)
            nodes.append({
                "id": entity_node_id,
                "label": entity_name,
                "type": "Entity",
                "data": {"name": entity_name, "type": "person"},
            })

        # Add fact node
        fact_id = str(fact.get("fact_id", ""))
        fact_node_id = f"fact-{fact_id}"
        if fact_node_id not in seen_node_ids:
            seen_node_ids.add(fact_node_id)
            nodes.append({
                "id": fact_node_id,
                "label": content[:40] if content else f"Fact #{fact_id}",
                "type": "Fact",
                "data": {
                    "content": content,
                    "is_current": fact.get("is_current", True),
                    "confidence": fact.get("confidence", 0.9),
                    "created_at": fact.get("created_at", ""),
                    "session_id": fact.get("session_id", ""),
                },
            })
            edges.append({
                "source": fact_node_id,
                "target": entity_node_id,
                "type": "MENTIONS",
                "data": {"type": "MENTIONS"},
            })

        # Add session node
        session_id = fact.get("session_id", "")
        if session_id and session_id not in seen_session_ids:
            seen_session_ids.add(session_id)
            session_node_id = f"session-{session_id}"
            if session_node_id not in seen_node_ids:
                seen_node_ids.add(session_node_id)
                nodes.append({
                    "id": session_node_id,
                    "label": f"Session: {session_id}",
                    "type": "Session",
                    "data": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "started_at": fact.get("session_started_at", ""),
                    },
                })
            edges.append({
                "source": fact_node_id,
                "target": session_node_id,
                "type": "OCCURRED_IN",
                "data": {"type": "OCCURRED_IN"},
            })

    return {"nodes": nodes, "edges": edges}


def _merge_graphs(g1: dict[str, Any], g2: dict[str, Any]) -> dict[str, Any]:
    """Merge two graph payloads, deduplicating by node id."""
    seen_ids = set()
    merged_nodes = []
    for n in (g1.get("nodes") or []) + (g2.get("nodes") or []):
        nid = str(n.get("id", ""))
        if nid not in seen_ids:
            seen_ids.add(nid)
            merged_nodes.append(n)
    merged_edges = (g1.get("edges") or []) + (g2.get("edges") or [])
    return {"nodes": merged_nodes, "edges": merged_edges}


@router.get("/session/{session_id}")
async def get_session_graph(session_id: str, user_id: str) -> dict[str, Any]:
    """Get all nodes and edges for a session.

    Returns data formatted for react-force-graph.
    """
    return service.get_session_graph(session_id, user_id=user_id)


@router.get("/entity/{entity_name}")
async def get_entity_history(entity_name: str, user_id: str) -> dict[str, Any]:
    """Get full fact history and subgraph for an entity.

    Returns data formatted for react-force-graph (nodes and edges arrays).
    Merges data from HydraDB and from the ingested_memory.json delta overlay.
    """
    from pipeline.retrieval.traversal import get_multi_entity_paths

    hydra_graph: dict[str, Any] = {"nodes": [], "edges": []}
    try:
        service.hydra.ensure_connected()
        hydra_graph = get_multi_entity_paths(service.hydra, [entity_name], user_id=user_id)
    except Exception:
        pass

    delta_graph = _build_delta_graph(entity_name, user_id)
    merged = _merge_graphs(hydra_graph, delta_graph)
    return merged


@router.get("/all")
async def get_all_graph(user_id: str) -> dict[str, Any]:
    """Get all nodes and edges across the entire graph.

    Returns data formatted for react-force-graph.
    Merges HydraDB data with the ingested_memory.json delta overlay.
    """
    hydra_graph: dict[str, Any] = {"nodes": [], "edges": []}
    try:
        hydra_graph = service.get_all_graph(user_id=user_id)
    except Exception:
        pass

    # Also include delta facts for the user (entity_name = user_id to get all their facts)
    delta_graph = _build_delta_graph(user_id, user_id)
    merged = _merge_graphs(hydra_graph, delta_graph)
    return merged


@router.get("/sessions")
async def get_sessions(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Get recent sessions stored in the memory graph."""
    sessions = service.get_recent_sessions(user_id=user_id, limit=limit)

    # Also include sessions from the delta overlay
    if DELTA_FILE.exists():
        try:
            data = json.loads(DELTA_FILE.read_text("utf-8"))
            existing_ids = {s.get("id") for s in sessions}
            target_uid = user_id.strip().lower()
            for sid, sdata in (data.get("sessions") or {}).items():
                if str(sdata.get("user_id", "")).strip().lower() == target_uid:
                    if sid not in existing_ids:
                        # Count facts for this session
                        fact_count = sum(
                            1 for f in (data.get("facts") or [])
                            if f.get("session_id") == sid
                            and str(f.get("user_id", "")).strip().lower() == target_uid
                        )
                        sessions.append({
                            "id": sid,
                            "user_id": sdata.get("user_id", user_id),
                            "date": sdata.get("started_at", "2024-01-01T00:00:00Z"),
                            "summary": None,
                            "factCount": fact_count,
                        })
        except Exception:
            pass

    return sessions
