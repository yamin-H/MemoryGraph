"""Multi-entity path retrieval endpoints using HydraDB GraphBLAS algo.MSpaths."""

from typing import Any
from fastapi import APIRouter, HTTPException, Query

from config import settings
from db.hydra import HydraDB
from pipeline.retrieval.traversal import get_multi_entity_paths

router = APIRouter()


@router.get("/{user_id}/multi-entity")
async def get_multi_entity_paths_route(
    user_id: str,
    entities: str = Query(..., description="Comma-separated entity names, e.g. 'Alex,Dhaka'"),
) -> dict[str, Any]:
    """Retrieve bounded paths and fact chains between multiple entities using HydraDB algo.MSpaths."""
    if not entities or not entities.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'entities' cannot be empty")

    entity_list = [e.strip() for e in entities.split(",") if e.strip()]
    if not entity_list:
        raise HTTPException(status_code=400, detail="At least one entity name is required")

    hydra = HydraDB(uri=settings.hydra_uri, auth_token=settings.hydra_token)
    try:
        hydra.connect()
        return get_multi_entity_paths(hydra, entity_list, user_id=user_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"HydraDB algo.MSpaths execution failed: {exc}") from exc
    finally:
        hydra.close()
