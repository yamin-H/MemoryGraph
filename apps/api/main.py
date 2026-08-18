import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure apps/api directory is in sys.path
api_dir = str(Path(__file__).resolve().parent)
if api_dir not in sys.path:
    sys.path.insert(0, api_dir)

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis.asyncio as redis

from config import settings
from db.hydra import HydraDB
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.cost_tracker import CostTrackerMiddleware
from routes import ingest, query, graph, health, metrics, benchmark, compare, memory


# Load environment
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(env_path)
load_dotenv(env_path)
print(f"[DEBUG] Loading .env from: {env_path}")
print(f"[DEBUG] .env exists: {env_path.exists()}")
print(f"[DEBUG] GROQ_API_KEY loaded: {bool(os.environ.get('GROQ_API_KEY'))}")
# Global connections
hydra_client: HydraDB | None = None
redis_client: redis.Redis | None = None


def bootstrap_schema(hydra: "HydraDB") -> None:
    """Create HydraDB indexes for hot query paths.

    Idempotent — uses CREATE INDEX IF NOT EXISTS so safe to run repeatedly.
    """
    indexes = [
        ("idx_entity_name",   "Entity",  "name"),
        ("idx_fact_current",  "Fact",    "is_current"),
        ("idx_fact_created",  "Fact",    "created_at"),
        ("idx_session_user",  "Session", "user_id"),
        ("idx_session_id",    "Session", "session_id"),
    ]
    try:
        with hydra._driver.session() as session:
            for idx_name, label, prop in indexes:
                try:
                    session.run(
                        f"CREATE INDEX {idx_name} IF NOT EXISTS FOR (n:{label}) ON (n.{prop})"
                    )
                except Exception:
                    # Some HydraDB builds may not support IF NOT EXISTS — skip
                    pass
        print("[OK] HydraDB schema indexes bootstrapped")
    except Exception as exc:
        print(f"[INFO] Schema bootstrap skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global hydra_client, redis_client

    print("Starting MemoryGraph API...")

    hydra_uri = settings.hydra_uri
    hydra_token = settings.hydra_token
    hydra_client = HydraDB(uri=hydra_uri, auth_token=hydra_token)

    try:
        hydra_client.connect()
        app.state.hydra = hydra_client
        print(f"[OK] Connected to HydraDB at {hydra_uri}")
        admin = hydra_client.health_details().get("admin", {})
        if admin.get("ready"):
            print(f"[OK] HydraDB OSS admin ready at {admin.get('admin_url')}/readyz")
        bootstrap_schema(hydra_client)
    except Exception as exc:
        print(f"[WARNING] Could not immediately connect to HydraDB at {hydra_uri}: {exc}")
        print("FastAPI will start up and retry connection on request.")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = redis.from_url(redis_url)
        await redis_client.ping()
        print("[OK] Connected to Redis")
    except Exception as e:
        print(f"[INFO] Redis optional connection status: {e}")
        redis_client = None

    print("MemoryGraph API started successfully and listening for traffic")

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
    allow_origins=["http://localhost:3000"],  # ✅ explicit origin
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
app.include_router(compare.router, prefix="/compare", tags=["Compare"])
app.include_router(compare.router, prefix="/query/compare", tags=["Compare"])
app.include_router(graph.router, prefix="/graph", tags=["Graph"])
app.include_router(health.router, tags=["Health"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(benchmark.router, prefix="/benchmark", tags=["Benchmark"])
app.include_router(memory.router, prefix="/memory", tags=["Memory"])


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
    """Get the shared HydraDB client."""
    if hydra_client is None:
        raise RuntimeError("HydraDB is required for MemoryGraph")
    hydra_client.ensure_connected()
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
