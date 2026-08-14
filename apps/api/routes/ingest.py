"""Ingestion routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter, HTTPException

from pipeline.graph import run_pipeline

router = APIRouter()


class SessionIngestRequest:
    """Request body for session ingestion."""
    session_id: str
    user_id: str
    started_at: str
    messages: list[dict[str, str]]


@router.post("/session")
async def ingest_session(session: dict[str, Any]) -> dict[str, Any]:
    """Ingest a single session.

    Args:
        session: Session dict with session_id, user_id, started_at, messages

    Returns:
        Write summary from ingestion pipeline
    """
    try:
        result = run_pipeline(session)

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=f"Ingestion failed: {result['error']}",
            )

        return result.get("write_result", {})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def ingest_batch(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ingest multiple sessions.

    Args:
        sessions: List of session dicts

    Returns:
        List of write summaries
    """
    results = []

    for session in sessions:
        try:
            result = run_pipeline(session)

            if result.get("error"):
                results.append({
                    "session_id": session.get("session_id"),
                    "error": result["error"],
                    "success": False,
                })
            else:
                results.append({
                    "session_id": session.get("session_id"),
                    "write_result": result.get("write_result"),
                    "success": True,
                })

        except Exception as e:
            results.append({
                "session_id": session.get("session_id"),
                "error": str(e),
                "success": False,
            })

    return results
