"""Graph routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter

from services.memory_service import MemoryService

router = APIRouter()
service = MemoryService()


@router.get("/session/{session_id}")
async def get_session_graph(session_id: str) -> dict[str, Any]:
    """Get all nodes and edges for a session.

    Returns data formatted for react-force-graph.

    Args:
        session_id: Session identifier

    Returns:
        Graph data with nodes and edges arrays
    """
    return service.get_session_graph(session_id)


@router.get("/entity/{entity_name}")
async def get_entity_history(entity_name: str) -> dict[str, Any]:
    """Get full fact history for an entity.

    Includes SUPERSEDES chain traversal.

    Args:
        entity_name: Name of the entity

    Returns:
        Entity data with current facts and historical facts
    """
    return service.get_entity_history(entity_name)


@router.get("/all")
async def get_all_graph() -> dict[str, Any]:
    """Get all nodes and edges across the entire graph.

    Returns data formatted for react-force-graph.

    Returns:
        Graph data with nodes and edges arrays
    """
    return service.get_all_graph()


@router.get("/sessions")
async def get_sessions(limit: int = 50) -> list[dict[str, Any]]:
    """Get recent sessions stored in the memory graph."""
    return service.get_recent_sessions(limit=limit)

