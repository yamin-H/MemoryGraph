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
    """Ingest a single session."""
    try:
        result = service.ingest_session(session.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def ingest_batch(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ingest multiple sessions."""
    return service.ingest_batch(sessions)


@router.post("/seed-demo")
async def seed_demo_route() -> dict[str, Any]:
    """One-click demo dataset seeder.

    Ingests 5 sessions from Alex's life story arc into HydraDB.
    """
    import json
    from pathlib import Path
    import sys

    fixtures_file = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "sample_sessions.json"
    if not fixtures_file.exists():
        scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        try:
            from seed_demo import build_sessions
            sessions = build_sessions()[:5]
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Could not load seed builder: {exc}")
    else:
        try:
            data = json.loads(fixtures_file.read_text(encoding="utf-8"))
            sessions = data.get("sessions", [])[:5]
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Could not read fixtures: {exc}")

    results = service.ingest_batch(sessions)
    successful = sum(1 for r in results if r.get("success"))

    return {
        "status": "ok",
        "message": f"Successfully seeded {successful}/{len(sessions)} demo sessions into HydraDB.",
        "total_sessions": len(sessions),
        "successful_sessions": successful,
    }
