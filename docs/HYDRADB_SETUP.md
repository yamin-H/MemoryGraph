# HydraDB OSS Setup for MemoryGraph

MemoryGraph uses the **official HydraDB open-source graph database** — not Neo4j Community.

| Resource | Link |
|---|---|
| HydraDB OSS repo | https://github.com/hydra-db/hydradb |
| Official Docker image | `ghcr.io/hydra-db/hydradb:latest` |
| Hack Hydra rules | HydraDB must do **real work** in your project |

Your Python code connects via the **official Neo4j Bolt driver** (`neo4j` package). HydraDB implements a Neo4j-compatible Bolt protocol with OpenCypher — the same queries in `apps/api/db/hydra.py` and `pipeline/ingestion/writer.py` run against HydraDB.

---

## Option A — Docker Compose (recommended for hackathon demo)

Best for: full MemoryGraph stack (HydraDB + API + Web + Redis + Postgres).

### Step 1 — Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine (Linux)
- Python 3.11+ (for setup scripts)
- Git

### Step 2 — Clone and configure

```powershell
cd memorygraph
copy .env.example .env
```

Edit `.env` and set your Groq key (optional but recommended for LLM extraction):

```env
GROQ_API_KEY=gsk_your_key_here
HYDRADB_URI=neo4j://127.0.0.1:7687
HYDRADB_TOKEN=local-development-token-32-bytes
```

### Step 3 — Initialize HydraDB local storage

This creates `hydradb-data/store`, `hydradb-data/cache`, and `hydradb-data/auth-token`:

```powershell
python scripts/setup_hydradb.py
```

You should see:

```
[OK] .../hydradb-data/store
[OK] .../hydradb-data/cache
[OK] .../hydradb-data/auth-token (auth token written)
```

### Step 4 — Pull the official HydraDB image

```powershell
docker compose pull hydradb
```

First pull downloads `ghcr.io/hydra-db/hydradb:latest` (~hundreds of MB). On Apple Silicon, Docker auto-selects `linux/arm64`. Older tags before v0.1.0 were amd64-only.

### Step 5 — Start the full stack

```powershell
docker compose up --build
```

Wait until you see:

- `memorygraph-hydradb` healthy (`/readyz` on port 9090)
- `[OK] Connected to HydraDB at neo4j://hydradb:7687` in API logs

Open:

| Service | URL |
|---|---|
| Web dashboard | http://localhost:3000 |
| API docs | http://localhost:8000/docs |
| HydraDB admin | http://localhost:9090/readyz |

### Step 6 — Verify HydraDB (required before demo)

In a **second terminal** (while stack is running):

```powershell
python scripts/verify_hydradb.py
```

Expected output:

```
Connecting to HydraDB at neo4j://127.0.0.1:7687 ...
  [OK] Bolt connectivity verified
  [OK] OpenCypher write + read round-trip succeeded

HydraDB OSS is ready for MemoryGraph.
```

### Step 7 — Seed demo data

1. Open http://localhost:3000/ingest
2. Click **"1-Click Seed HydraDB"** (35 sessions, SUPERSEDES edges)
3. Open http://localhost:3000/arena and ask: **"Where does Alex live?"**

---

## Option B — HydraDB only (Docker, no full stack)

Run just the graph database while developing the API locally:

```powershell
python scripts/setup_hydradb.py
docker compose up hydradb
python scripts/verify_hydradb.py
```

Then run the API on your host:

```powershell
cd apps/api
pip install -r ../../requirements.txt
uvicorn main:app --reload --port 8000
```

---

## Option C — Build HydraDB from source (advanced)

Use this if you want to cite a specific HydraDB commit in your Hack Hydra submission form.

### Linux / WSL prerequisites

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential clang libclang-dev cmake pkg-config \
  libcypher-parser-dev libgraphblas-dev \
  curl git python3 python3-venv
```

### Build and run

```bash
git clone https://github.com/hydra-db/hydradb.git
cd hydradb
just native-check
just smoke

mkdir -p .hydradb/store .hydradb/cache
printf '%s\n' 'local-development-token-32-bytes' > .hydradb/auth-token

export CLOUD_PROVIDER=local
export LOCAL_PATH="$PWD/.hydradb/store"
export GRAPH_NAMESPACE=default
export GRAPH_ID=default
export GRAPH_CELL_ID=cell-0
export GRAPH_CELLS=cell-0
export GRAPH_NODE_ID=node-0
export GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687
export GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687
export GRAPH_DATA_CACHE_DIR="$PWD/.hydradb/cache"
export GRAPH_AUTH_TOKEN_FILE="$PWD/.hydradb/auth-token"
export GRAPH_ALLOW_PLAINTEXT=true
export RUST_MIN_STACK=33554432

cargo run --locked --features server-runtime --bin graph-node
```

Keep that terminal open. In another terminal, run MemoryGraph's verify script from the MemoryGraph repo root.

---

## Environment variables reference

| Variable | Default | Purpose |
|---|---|---|
| `HYDRADB_URI` | `neo4j://127.0.0.1:7687` | Bolt connection URI |
| `HYDRADB_TOKEN` | `local-development-token-32-bytes` | Auth token (must match `hydradb-data/auth-token`) |
| `GRAPH_NAMESPACE` | `default` | HydraDB graph namespace |
| `GRAPH_CELL_ID` | `cell-0` | HydraDB cell shard |

**Important:** `HYDRADB_TOKEN` must exactly match the contents of `hydradb-data/auth-token`. Do not use `neo4j/password` — that was the old Neo4j placeholder.

---

## HydraDB endpoints (when running via Docker)

| Port | Protocol | Purpose |
|---|---|---|
| 7687 | Bolt | MemoryGraph API connects here |
| 8443 | HTTPS | Native HydraDB JSON query API |
| 9090 | HTTP | `/readyz` health + Prometheus metrics |

Quick HTTP verification (official HydraDB smoke test):

```powershell
$TOKEN = "local-development-token-32-bytes"
curl -sS http://127.0.0.1:8443/v1/graphs/default/query `
  -H "Authorization: Bearer $TOKEN" `
  -H "X-Graph-Namespace: default" `
  -H "Content-Type: application/json" `
  --data '{\"cell_id\":\"cell-0\",\"query\":\"RETURN 1 AS ok\"}'
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not connect to HydraDB` | Run `docker compose ps` — hydradb must be `healthy`. Wait 45s on first start. |
| `permission denied` on `hydradb-data/` (Linux) | Run `python scripts/setup_hydradb.py` as your user. Add `user: "${UID}:${GID}"` to hydradb service if needed. |
| Token auth fails | Ensure `.env` token matches `hydradb-data/auth-token` byte-for-byte. |
| Port 7687 already in use | Stop old Neo4j: `docker stop memorygraph-hydradb` or change port mapping. |
| Node crashes on first query | Ensure `RUST_MIN_STACK=33554432` is set (already in docker-compose.yml). |
| ARM Mac pull fails on old tag | Use `latest` or a release after v0.1.0, or `--platform linux/amd64`. |
| API starts but graph is empty | Click **Seed HydraDB** on `/ingest` — do not rely on demo fallbacks for judging. |

---

## What to tell Hack Hydra judges

> MemoryGraph stores all agent memories in **HydraDB OSS** (`github.com/hydra-db/hydradb`). Facts are `Fact` nodes, entities are `Entity` nodes, and temporal updates use native `SUPERSEDES` graph edges queried via OpenCypher over Bolt. Without HydraDB, the system cannot resolve which fact is currently true across 35+ sessions.

Point judges to:

1. `docker-compose.yml` → `ghcr.io/hydra-db/hydradb:latest`
2. `scripts/verify_hydradb.py` → round-trip proof
3. `/graph` page → live SUPERSEDES visualization
4. `apps/api/pipeline/ingestion/writer.py` → OpenCypher MERGE writes
