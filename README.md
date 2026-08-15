# MemoryGraph

Graph-native agent memory layer for HydraDB-powered long-term memory and temporal fact tracking.

## What this project does

MemoryGraph is a graph-native memory system for AI agents. It stores memories as facts in HydraDB, tracks how they change over time, and lets the system reason across multi-session conversations while knowing when to abstain instead of hallucinating.

The core project idea is:
- each memory is a fact node connected to an entity
- session data is stored as graph context
- fact updates use a `SUPERSEDES` relationship
- stale or expired facts can be invalidated
- retrieval uses graph traversal and confidence-aware abstention

## Required services

This backend requires:
- HydraDB (Neo4j-compatible graph database)
- Redis (for metrics and rate limiting)
- Groq API key for LLM-based extraction and inference

## Local development setup

1. Copy the environment example:
   ```bash
   cp .env.example .env
   ```

2. Start the required services:
   ```bash
   docker compose up -d
   ```

3. Set the environment values in `.env` if needed:
   ```env
   HYDRADB_URI=neo4j://127.0.0.1:7687
   HYDRADB_TOKEN=neo4j/password
   REDIS_URL=redis://localhost:6379
   GROQ_API_KEY=your_key_here
   ```

4. Install Python dependencies:
   ```bash
   pip install -e .
   ```

5. Run the API:
   ```bash
   cd apps/api
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Important backend requirements for Hack Hydra

This project is built around HydraDB as the source of truth for memory.

The configuration must keep HydraDB as the real storage layer for:
- sessions
- messages
- entities
- facts
- superseded facts
- invalidated facts

Redis is used for operational metrics and rate limiting, not as the memory graph itself.

## API endpoints

- `GET /health` – service and storage health
- `GET /metrics` – Redis-backed aggregate metrics
- `POST /ingest/session` – ingest one session
- `POST /ingest/batch` – ingest several sessions
- `POST /query` – ask a question against memory
- `POST /query/stream` – streaming retrieval response
- `GET /graph/session/{session_id}` – session graph
- `GET /graph/entity/{entity_name}` – entity history

## Status

The backend has a working MVP architecture and HydraDB integration path, and the next step is to validate it end-to-end with live HydraDB + Redis services and a real demo dataset.

