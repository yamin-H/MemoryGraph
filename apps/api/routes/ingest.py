"""Ingestion routes for MemoryGraph API."""

from typing import Any

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from services.memory_service import MemoryService

router = APIRouter()
service = MemoryService()


class SessionIngestRequest(BaseModel):
    """Request body for session ingestion."""
    session_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    started_at: str = Field(..., min_length=1)
    messages: list[dict[str, str]] = Field(default_factory=list)


@router.post("/session")
async def ingest_session(session: SessionIngestRequest) -> dict[str, Any]:
    """Ingest a single session.

    Args:
        session: Session payload with session_id, user_id, started_at, messages

    Returns:
        Write summary from ingestion pipeline
    """
    try:
        result = service.ingest_session(session.model_dump())
        return result

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
    return service.ingest_batch(sessions)
