"""Comparison route for Vector RAG vs MemoryGraph side-by-side arena."""

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from services.memory_service import MemoryService

router = APIRouter()
service = MemoryService()


class CompareRequest(BaseModel):
    """Request body for comparison arena."""
    question: str
    user_id: str = "anonymous"

    @classmethod
    def validate_question(cls, value: str) -> str:
        """Validate question."""
        if not value or not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()


@router.post("")
async def compare_systems(request: CompareRequest) -> dict[str, Any]:
    """Execute live comparison between Vector RAG and MemoryGraph.

    Args:
        request: CompareRequest with question and user_id

    Returns:
        Structured comparison payload with both system outputs, metrics, and verdict
    """
    return service.compare_query(request.question, user_id=request.user_id)
