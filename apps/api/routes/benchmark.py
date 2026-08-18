"""Benchmark routes for MemoryGraph API with real dataset integration."""

import asyncio
import json
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel
import redis.asyncio as redis

from pipeline.graph import run_pipeline, run_retrieval
from eval.scorer import exact_match, contains_answer, score_example

router = APIRouter()

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

# HuggingFace public URLs for real LongMemEval datasets
HUGGINGFACE_URLS: dict[str, str] = {
    "longmemeval": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_oracle.json",
    "longmemeval_s": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_s_cleaned.json",
    "longmemeval_m": "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/main/longmemeval_m_cleaned.json",
}

DATASET_CONFIG = {
    "longmemeval": {
        "name": "LongMemEval (Oracle)",
        "file": "longmemeval_oracle.json",
        "description": "Multi-session temporal reasoning and fact update benchmark.",
    },
    "longmemeval_s": {
        "name": "LongMemEval (Small - Cleaned)",
        "file": "longmemeval_s_cleaned.json",
        "description": "Cleaned full small split for comprehensive temporal memory evaluation.",
    },
    "longmemeval_m": {
        "name": "LongMemEval (Medium - Cleaned)",
        "file": "longmemeval_m_cleaned.json",
        "description": "Cleaned medium split for multi-session temporal evaluation.",
    },
    "beam": {
        "name": "BEAM 100K Benchmark",
        "file": "beam_100k.json",
        "description": "Agentic long-term memory retrieval & synthesis benchmark.",
    },
}

# Cached benchmark dataset in memory
_dataset_cache: dict[str, list[dict[str, Any]]] = {}

# Stored benchmark run results
benchmark_results: dict[str, dict[str, Any]] = {}


async def get_redis():
    """Get Redis client."""
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    return redis.from_url(redis_url)


def _normalize_beam_dataset(raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize BEAM 100K dataset structure into uniform QA benchmark samples."""
    normalized_samples = []
    for item_idx, item in enumerate(raw_data):
        # If already formatted as QA
        if "question" in item and "answer" in item:
            q_id = item.get("question_id") or item.get("id") or f"beam_{item_idx}"
            normalized_samples.append({
                "question_id": str(q_id),
                "question_type": item.get("question_type", "temporal-synthesis"),
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "question_date": item.get("question_date", ""),
                "haystack_sessions": item.get("haystack_sessions", item.get("sessions", item.get("context", []))),
                "haystack_session_ids": item.get("haystack_session_ids", item.get("session_ids", [])),
                "haystack_dates": item.get("haystack_dates", item.get("session_dates", [])),
            })
            continue

        # Extract from BEAM conversation seed + chat
        conv_seed = item.get("conversation_seed", {})
        seed_id = conv_seed.get("id", item_idx + 1)
        theme = conv_seed.get("title") or conv_seed.get("theme", "Software Development")
        chat_sessions = item.get("chat", [])

        # Form sessions
        sessions_list = []
        session_ids = []
        session_dates = []
        for s_idx, sess in enumerate(chat_sessions):
            sessions_list.append(sess)
            session_ids.append(f"beam-sess-{seed_id}-{s_idx+1}")
            session_dates.append(f"2024-03-{min(15 + s_idx, 28):02d}T10:00:00Z")

        # Find key question turns
        for s_idx, sess in enumerate(chat_sessions):
            if isinstance(sess, list):
                for t_idx in range(0, len(sess) - 1, 2):
                    user_turn = sess[t_idx] if t_idx < len(sess) else {}
                    asst_turn = sess[t_idx + 1] if t_idx + 1 < len(sess) else {}
                    if user_turn.get("role") == "user":
                        q_content = user_turn.get("content", "")
                        # Clean up trailing annotations like ->-> 1,1
                        clean_q = q_content.split("->->")[0].strip() if "->->" in q_content else q_content.strip()
                        a_content = asst_turn.get("content", "").strip()
                        if clean_q:
                            normalized_samples.append({
                                "question_id": f"beam_{seed_id}_{s_idx+1}_{t_idx+1}",
                                "question_type": user_turn.get("question_type") or "agentic-synthesis",
                                "question": clean_q,
                                "answer": a_content[:300] if a_content else theme,
                                "question_date": user_turn.get("time_anchor") or f"2024-03-{min(15 + s_idx, 28):02d}",
                                "haystack_sessions": sessions_list,
                                "haystack_session_ids": session_ids,
                                "haystack_dates": session_dates,
                            })
    return normalized_samples


def _fetch_from_huggingface(dataset_id: str) -> list[dict[str, Any]]:
    """Download real dataset samples from HuggingFace at runtime."""
    url = HUGGINGFACE_URLS.get(dataset_id)
    if not url:
        return []
    print(f"[Benchmark] Downloading real dataset '{dataset_id}' from HuggingFace...")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MemoryGraph-Benchmark/1.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if dataset_id == "beam":
            data = _normalize_beam_dataset(data)
        print(f"[Benchmark] Downloaded {len(data)} real samples for '{dataset_id}'.")
        return data
    except Exception as exc:
        print(f"[Benchmark] HuggingFace download failed for '{dataset_id}': {exc}")
        return []


def load_dataset_file(dataset_id: str) -> list[dict[str, Any]]:
    """Load and parse dataset JSON file from data directory, or fetch from HuggingFace."""
    if dataset_id in _dataset_cache:
        return _dataset_cache[dataset_id]

    cfg = DATASET_CONFIG.get(dataset_id)
    if not cfg:
        cfg = DATASET_CONFIG["longmemeval"]

    # Try local file first
    file_path = DATA_DIR / cfg["file"]
    if not file_path.exists():
        alt_path = Path("data") / cfg["file"]
        if alt_path.exists():
            file_path = alt_path
        else:
            file_path = None

    if file_path is not None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if dataset_id == "beam":
                data = _normalize_beam_dataset(data)
            _dataset_cache[dataset_id] = data
            return data
        except Exception as e:
            print(f"Error loading local dataset {dataset_id}: {e}")

    # Fall back: download from HuggingFace (real data, not synthetic)
    data = _fetch_from_huggingface(dataset_id)
    if data:
        _dataset_cache[dataset_id] = data
    return data


@router.get("/datasets")
async def list_datasets() -> list[dict[str, Any]]:
    """List available evaluation datasets in data folder."""
    datasets = []
    for key, cfg in DATASET_CONFIG.items():
        file_path = DATA_DIR / cfg["file"]
        if not file_path.exists():
            alt_path = Path("data") / cfg["file"]
            if alt_path.exists():
                file_path = alt_path

        exists = file_path.exists()
        size_mb = round(file_path.stat().st_size / (1024 * 1024), 2) if exists else 0.0
        
        # Quick count if loaded
        count = len(_dataset_cache.get(key, []))
        if count == 0 and exists:
            try:
                samples = load_dataset_file(key)
                count = len(samples)
            except Exception:
                count = 0

        datasets.append({
            "id": key,
            "name": cfg["name"],
            "description": cfg["description"],
            "file": cfg["file"],
            "exists": exists,
            "size_mb": size_mb,
            "total_examples": count,
        })
    return datasets


@router.get("/dataset/{dataset_id}/samples")
async def get_dataset_samples(
    dataset_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    question_type: str | None = None,
) -> dict[str, Any]:
    """Fetch real sample questions and ground truth from dataset."""
    data = load_dataset_file(dataset_id)
    if not data:
        return {"dataset_id": dataset_id, "total": 0, "samples": []}

    filtered = data
    if question_type:
        filtered = [d for d in filtered if d.get("question_type") == question_type]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    samples = []
    for item in page:
        sessions_count = len(item.get("haystack_sessions", item.get("sessions", [])))
        samples.append({
            "question_id": item.get("question_id", ""),
            "question_type": item.get("question_type", "general"),
            "question": item.get("question", ""),
            "answer": item.get("answer", ""),
            "question_date": item.get("question_date", ""),
            "sessions_count": sessions_count,
            "has_abstention": str(item.get("question_id", "")).endswith("_abs") or "abs" in str(item.get("question_type", "")),
        })

    return {
        "dataset_id": dataset_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "samples": samples,
    }


class EvaluateSampleRequest(BaseModel):
    """Request to evaluate a single real dataset sample."""
    dataset_id: str = "longmemeval"
    question_id: str
    auto_ingest: bool = False


@router.post("/evaluate-sample")
async def evaluate_sample(request: EvaluateSampleRequest) -> dict[str, Any]:
    """Execute live evaluation on a single sample from the real dataset."""
    data = load_dataset_file(request.dataset_id)
    sample = next((d for d in data if d.get("question_id") == request.question_id), None)
    if not sample:
        raise HTTPException(status_code=404, detail="Question ID not found in dataset")

    question = sample.get("question", "")
    ground_truth = sample.get("answer", "")
    haystack_sessions = sample.get("haystack_sessions", sample.get("sessions", []))
    session_ids = sample.get("haystack_session_ids", sample.get("session_ids", []))
    session_dates = sample.get("haystack_dates", sample.get("session_dates", []))

    # Auto-ingest haystack sessions into HydraDB if requested
    ingestion_time_ms = 0
    if request.auto_ingest and haystack_sessions:
        start_ingest = time.time()
        for idx, msgs in enumerate(haystack_sessions):
            sess_id = session_ids[idx] if idx < len(session_ids) else f"bench-{request.question_id}-{idx}"
            sess_date = session_dates[idx] if idx < len(session_dates) else "2024-01-01T00:00:00Z"
            
            # Format messages
            formatted_msgs = []
            for m in msgs:
                if isinstance(m, dict):
                    formatted_msgs.append({"role": m.get("role", "user"), "content": m.get("content", "")})
                elif isinstance(m, str):
                    formatted_msgs.append({"role": "user", "content": m})

            run_pipeline({
                "session_id": sess_id,
                "user_id": "eval-user",
                "started_at": sess_date,
                "messages": formatted_msgs,
            })
        ingestion_time_ms = int((time.time() - start_ingest) * 1000)

    # Run MemoryGraph retrieval pipeline
    start_q = time.time()
    query_result = run_retrieval(question)
    query_time_ms = int((time.time() - start_q) * 1000)

    predicted_answer = query_result.get("answer", {}).get("answer", "")
    abstained = query_result.get("answer", {}).get("abstained", False)
    confidence = query_result.get("answer", {}).get("confidence", 0.0)

    score_res = score_example(predicted_answer, ground_truth, abstained)

    return {
        "question_id": request.question_id,
        "question": question,
        "ground_truth": ground_truth,
        "predicted_answer": predicted_answer,
        "confidence": confidence,
        "abstained": abstained,
        "is_correct": score_res["is_correct"],
        "exact_match": score_res["exact_match"],
        "contains_answer": score_res["contains_answer"],
        "query_time_ms": query_time_ms,
        "ingestion_time_ms": ingestion_time_ms,
        "sessions_evaluated": len(haystack_sessions),
        "reasoning": query_result.get("answer", {}).get("reasoning", ""),
        "source_sessions": query_result.get("answer", {}).get("source_sessions", []),
    }


@router.get("/results")
async def get_benchmark_results() -> dict[str, Any]:
    """Get aggregate benchmark comparison matrix.

    Returns real computed results from the last benchmark run if available,
    otherwise indicates no real run has been generated yet.
    """
    results_file = (
        Path(__file__).resolve().parents[3] / "scripts" / "data" / "benchmark_results.json"
    )

    if not results_file.exists():
        # No real run yet — do NOT fabricate numbers.
        return {
            "status": "no_real_run_yet",
            "message": "Run POST /benchmark/run to generate real results from the datasets.",
            "benchmarks": {},
            "last_job": max(benchmark_results.keys()) if benchmark_results else None,
        }

    with open(results_file) as f:
        data = json.load(f)

    benchmarks: dict[str, Any] = {}
    for ds_name, ds_results in data.get("results", {}).items():
        # Per-system accuracy averages
        system_scores: dict[str, float] = {}
        for sys_name, sys_results in ds_results.items():
            total = len(sys_results)
            correct = sum(1 for r in sys_results if r.get("is_correct", False))
            system_scores[sys_name] = round(correct * 100 / total, 1) if total else 0.0

        # Per question-type breakdown
        by_type: dict[str, dict[str, list]] = {}
        for sys_name, sys_results in ds_results.items():
            for r in sys_results:
                qtype = r.get("question_type", "general")
                by_type.setdefault(qtype, {}).setdefault(sys_name, []).append(r)

        metrics = []
        for qtype, type_results in by_type.items():
            row = {"type": qtype.replace("_", " ").title()}
            for sys_name, results in type_results.items():
                t = len(results)
                c = sum(1 for r in results if r.get("is_correct", False))
                row[sys_name] = round(c * 100 / t, 1) if t else 0.0
            if "memorygraph" in row and "vector" in row:
                row["gain"] = f"+{round(row['memorygraph'] - row['vector'])}%"
            metrics.append(row)

        benchmarks[ds_name] = {
            "name": DATASET_CONFIG.get(ds_name, {}).get("name", ds_name),
            "total_questions": sum(len(v) for v in ds_results.values()),
            "metrics": metrics,
            "averages": system_scores,
        }

    return {
        "status": "ready",
        "benchmarks": benchmarks,
        "last_job": max(benchmark_results.keys()) if benchmark_results else None,
    }



async def run_benchmark_job(job_id: str, redis_client: redis.Redis):
    """Run real LongMemEval evaluation across ALL systems (vector, longcontext, mem0, memorygraph).

    Downloads real dataset samples from HuggingFace if not cached locally.
    """
    from eval.runner import run_benchmark

    results = {
        "job_id": job_id,
        "status": "running",
        "start_time": time.time(),
        "tests": [],
    }

    try:
        # Run the real benchmark across all systems and datasets
        # Use max_examples_per_dataset=10 to keep runtime reasonable for hackathon demo
        benchmark_data = run_benchmark(
            systems=["vector", "longcontext", "mem0", "memorygraph"],
            datasets=["longmemeval", "longmemeval_v2", "beam"],
            max_examples_per_dataset=10,
        )

        # Flatten for job results (for /job/{job_id} endpoint)
        for ds_name, ds_results in benchmark_data["results"].items():
            for sys_name, sys_results in ds_results.items():
                for r in sys_results:
                    results["tests"].append({
                        "dataset": ds_name,
                        "system": sys_name,
                        "question_id": r["question_id"],
                        "question": r["question"],
                        "ground_truth": r["ground_truth"],
                        "predicted": r["predicted"],
                        "is_correct": r.get("is_correct", False),
                        "confidence": r.get("confidence", 0.0),
                        "abstained": r.get("abstained", False),
                        "latency_ms": r.get("latency_ms", 0),
                    })

        results["status"] = "completed"
        results["end_time"] = time.time()
        results["total_duration_ms"] = int((results["end_time"] - results["start_time"]) * 1000)

    except Exception as exc:
        results["status"] = "failed"
        results["error"] = str(exc)

    benchmark_results[job_id] = results
    await redis_client.set("benchmark:last_job_id", job_id)


@router.post("/run")
async def run_benchmark(background_tasks: BackgroundTasks) -> dict[str, Any]:
    """Trigger background benchmark execution."""
    job_id = str(uuid.uuid4())[:8]
    redis_client = await get_redis()
    background_tasks.add_task(run_benchmark_job, job_id, redis_client)

    return {
        "status": "started",
        "job_id": job_id,
        "message": "Benchmark job started in background on real LongMemEval dataset",
    }


@router.get("/job/{job_id}")
async def get_benchmark_job(job_id: str) -> dict[str, Any]:
    """Get status and results of a benchmark job."""
    if job_id in benchmark_results:
        return benchmark_results[job_id]
    raise HTTPException(status_code=404, detail="Benchmark job not found")
