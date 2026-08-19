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
        """Validate that the query question string is non-empty."""
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


@router.post("/compare")
async def compare_systems_route(request: QueryRequest) -> dict[str, Any]:
    """Execute live comparison between Vector RAG and MemoryGraph for Battle Arena."""
    return service.compare_query(request.question, user_id=request.user_id)


@router.post("/abstention-inspect")
async def inspect_abstention_route(request: QueryRequest) -> dict[str, Any]:
    """Inspect abstention and hallucination prevention reasoning trace.

    Args:
        request: Query request with question and user_id

    Returns:
        Step-by-step entity check, confidence breakdown, and honest abstention result
    """
    return service.inspect_abstention(request.question, user_id=request.user_id)



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
    import os
    from groq import Groq
    from pipeline.retrieval.parser import parse_question

    async def generate():
        """Asynchronous SSE generator for query traversal and generation stages."""
        # Step 1: Parsing
        yield f"data: {json.dumps({'event': 'status', 'message': 'Parsing natural language question...'})}\n\n"
        await asyncio.sleep(0.05)

        # Parse entity & intent dynamically
        entity_name = None
        q_type = "current_fact"
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key:
            try:
                client = Groq(api_key=api_key)
                parsed = parse_question(client, request.question)
                entity_name = parsed.get("entity_name")
                q_type = parsed.get("question_type", "current_fact")
            except Exception:
                pass

        # Step 2: Entity identified
        yield f"data: {json.dumps({'event': 'entity', 'entity': entity_name, 'type': q_type})}\n\n"
        await asyncio.sleep(0.05)

        # Step 3: Traversing
        yield f"data: {json.dumps({'event': 'status', 'message': 'Traversing HydraDB memory graph...'})}\n\n"
        await asyncio.sleep(0.05)

        # Run the full memory pipeline
        result = service.query_memory(request.question, user_id=request.user_id)

        # Step 4: Facts found
        facts_count = result.get("facts_examined", len(result.get("source_sessions", [])))
        yield f"data: {json.dumps({'event': 'facts', 'count': facts_count})}\n\n"
        await asyncio.sleep(0.05)

        # Step 5: Temporal filter & supersedence resolution
        yield f"data: {json.dumps({'event': 'status', 'message': 'Evaluating temporal recency and fact supersedence...'})}\n\n"
        await asyncio.sleep(0.05)

        # Step 6: Confidence calculation
        confidence = round((result.get("confidence", 0.0) or 0.0) * 100, 1)
        yield f"data: {json.dumps({'event': 'confidence', 'score': confidence})}\n\n"
        await asyncio.sleep(0.05)

        # Step 7: Final Answer
        yield f"data: {json.dumps({'event': 'answer', 'answer': result.get('answer'), 'abstained': result.get('abstained', False), 'source_sessions': result.get('source_sessions', []), 'reasoning': result.get('reasoning', '')})}\n\n"

        # Done
        yield f"data: {json.dumps({'event': 'done'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
    )
