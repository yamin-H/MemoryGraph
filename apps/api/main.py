"""MemoryGraph API - Main FastAPI application."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis

from db.hydra import HydraDB
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.cost_tracker import CostTrackerMiddleware
from routes import ingest, query, graph, health, metrics, benchmark

# Load environment
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path)

# Global connections
hydra_client: HydraDB | None = None
redis_client: redis.Redis | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global hydra_client, redis_client

    # Startup
    print("Starting MemoryGraph API...")

    # Connect to HydraDB
    hydra_client = HydraDB()
    try:
        hydra_client.connect()
        print("Connected to HydraDB")
    except Exception as e:
        print(f"Warning: Could not connect to HydraDB: {e}")
        hydra_client = None

    # Connect to Redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url)
        await redis_client.ping()
        print("Connected to Redis")
    except Exception as e:
        print(f"Warning: Could not connect to Redis: {e}")
        redis_client = None

    print("MemoryGraph API started successfully")

    yield

    # Shutdown
    print("Shutting down MemoryGraph API...")

    if hydra_client:
        hydra_client.close()
        print("Closed HydraDB connection")

    if redis_client:
        await redis_client.close()
        print("Closed Redis connection")

    print("MemoryGraph API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MemoryGraph API",
    description="Graph-native agent memory layer",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Add cost tracker middleware
app.add_middleware(CostTrackerMiddleware)

# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(query.router, prefix="/query", tags=["Query"])
app.include_router(graph.router, prefix="/graph", tags=["Graph"])
app.include_router(health.router, tags=["Health"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": "Internal server error"},
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MemoryGraph API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# Dependency to get HydraDB client
def get_hydra() -> HydraDB:
    """Get HydraDB client."""
    if hydra_client is None:
        raise RuntimeError("HydraDB not connected")
    return hydra_client


# Dependency to get Redis client
def get_redis() -> redis.Redis:
    """Get Redis client."""
    if redis_client is None:
        raise RuntimeError("Redis not connected")
    return redis_client


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
