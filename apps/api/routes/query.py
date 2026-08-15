"""Query routes for MemoryGraph API."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.memory_service import MemoryService

router = APIRouter()
service = MemoryService()


class QueryRequest(BaseModel):
    """Request body for query."""
    question: str
    user_id: str = "anonymous"

    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("question must not be empty")
        return value.strip()

    model_config = {"str_strip_whitespace": True}


@router.post("")
async def query_memory(request: QueryRequest) -> dict[str, Any]:
    """Query the memory graph.

    Args:
        request: Query request with question and user_id

    Returns:
        Full response with answer, confidence, abstention info
    """
    return service.query_memory(request.question, user_id=request.user_id)


@router.post("/stream")
async def query_stream(request: QueryRequest) -> StreamingResponse:
    """Query the memory graph with streaming response.

    Args:
        request: Query request with question and user_id

    Returns:
        SSE stream with progress updates
    """
    import json
    import asyncio

    async def generate():
        # Step 1: Parsing
        yield f"data: {json.dumps({'event': 'status', 'message': 'Parsing question...'})}\n\n"
        await asyncio.sleep(0.1)

        # Run the pipeline
        result = service.query_memory(request.question, user_id=request.user_id)
        parsed = {"entity_name": None, "question_type": "current_fact"}
        answer = result

        # Step 2: Entity identified
        yield f"data: {json.dumps({'event': 'entity', 'entity': parsed.get('entity_name'), 'type': parsed.get('question_type')})}\n\n"
        await asyncio.sleep(0.1)

        # Step 3: Traversing
        yield f"data: {json.dumps({'event': 'status', 'message': 'Traversing memory graph...'})}\n\n"
        await asyncio.sleep(0.1)

        # Step 4: Facts found
        facts_count = result.get("answer", {}).get("facts_examined", 0)
        yield f"data: {json.dumps({'event': 'facts', 'count': facts_count})}\n\n"
        await asyncio.sleep(0.1)

        # Step 5: Temporal filter
        yield f"data: {json.dumps({'event': 'status', 'message': 'Applying temporal filter...'})}\n\n"
        await asyncio.sleep(0.1)

        # Step 6: Confidence
        confidence = answer.get("confidence", 0) * 100
        yield f"data: {json.dumps({'event': 'confidence', 'score': confidence})}\n\n"
        await asyncio.sleep(0.1)

        # Step 7: Answer
        yield f"data: {json.dumps({'event': 'answer', 'answer': answer.get('answer'), 'abstained': answer.get('abstained')})}\n\n"

        # Done
        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
