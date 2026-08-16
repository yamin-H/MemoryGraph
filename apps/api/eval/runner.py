"""Benchmark runner for MemoryGraph evaluation."""

import json
import time
from pathlib import Path
from typing import Any

from .datasets import LongMemEvalDataset, LongMemEvalV2Dataset, BEAMDataset
from .baselines import VectorBaseline, LongContextBaseline, Mem0Baseline

# Import MemoryGraph pipeline
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from apps.api.pipeline.graph import run_pipeline, run_retrieval


class MemoryGraphSystem:
    """MemoryGraph system wrapper for benchmarking."""

    def __init__(self):
        """Initialize the MemoryGraph benchmark evaluation wrapper."""
        self._initialized = False

    def add_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Ingest sessions into MemoryGraph."""
        for session in sessions:
            result = run_pipeline(session)
            if result.get("error"):
                print(f"  Warning: Ingestion failed for {session.get('session_id')}: {result['error']}")

    def query(self, question: str, user_id: str) -> dict[str, Any]:
        """Query MemoryGraph."""
        result = run_retrieval(question)
        return {
            "answer": result.get("answer", {}).get("answer", ""),
            "confidence": result.get("answer", {}).get("confidence", 0.0),
            "abstained": result.get("answer", {}).get("abstained", False),
            "source_sessions": result.get("answer", {}).get("source_sessions", []),
            "latency_ms": result.get("answer", {}).get("query_time_ms", 0),
        }

    def clear(self) -> None:
        """Clear database - would need HydraDB connection."""
        # Note: In real benchmark, we'd clear the database
        pass


SYSTEMS = {
    "vector": VectorBaseline,
    "longcontext": LongContextBaseline,
    "mem0": Mem0Baseline,
    "memorygraph": MemoryGraphSystem,
}

DATASETS = {
    "longmemeval": LongMemEvalDataset,
    "longmemeval_v2": LongMemEvalV2Dataset,
    "beam": BEAMDataset,
}


def run_benchmark(
    systems: list[str] | None = None,
    datasets: list[str] | None = None,
    max_examples_per_dataset: int | None = None,
    output_file: str | None = None,
) -> dict[str, Any]:
    """Run benchmark across systems and datasets."""

    systems = systems or list(SYSTEMS.keys())
    datasets = datasets or list(DATASETS.keys())

    results = {
        "systems": systems,
        "datasets": datasets,
        "results": {},
    }

    output_path = Path(output_file) if output_file else Path(__file__).parent.parent.parent.parent.parent / "scripts" / "data" / "benchmark_results.json"

    print("=" * 60)
    print("Starting MemoryGraph Benchmark")
    print(f"Systems: {systems}")
    print(f"Datasets: {datasets}")
    print(f"Max examples per dataset: {max_examples_per_dataset or 'all'}")
    print("=" * 60)

    for dataset_name in datasets:
        print(f"\n{'='*60}")
        print(f"DATASET: {dataset_name}")
        print(f"{'='*60}")

        dataset_class = DATASETS[dataset_name]
        dataset = dataset_class()
        examples = dataset.load()

        if max_examples_per_dataset:
            examples = examples[:max_examples_per_dataset]

        print(f"Running {len(examples)} examples...")

        results["results"][dataset_name] = {}

        for system_name in systems:
            print(f"\n  System: {system_name}")
            system_class = SYSTEMS[system_name]
            system = system_class()

            system_results = []

            for i, example in enumerate(examples):
                question_id = example["question_id"]
                question = example["question"]
                ground_truth = example["answer"]
                sessions = example["sessions"]
                user_id = sessions[0].get("user_id", "unknown") if sessions else "unknown"

                print(f"    [{i+1}/{len(examples)}] {question_id}")

                try:
                    # Ingest sessions
                    system.add_sessions(sessions)

                    # Query
                    query_result = system.query(question, user_id)

                    system_results.append({
                        "question_id": question_id,
                        "question": question,
                        "ground_truth": ground_truth,
                        "predicted": query_result.get("answer", ""),
                        "confidence": query_result.get("confidence", 0.0),
                        "abstained": query_result.get("abstained", False),
                        "latency_ms": query_result.get("latency_ms", 0),
                        "context_exceeded": query_result.get("context_exceeded", False),
                        "error": None,
                    })

                except Exception as e:
                    print(f"      ERROR: {e}")
                    system_results.append({
                        "question_id": question_id,
                        "question": question,
                        "ground_truth": ground_truth,
                        "predicted": "",
                        "confidence": 0.0,
                        "abstained": True,
                        "latency_ms": 0,
                        "context_exceeded": False,
                        "error": str(e),
                    })

                # Clear system for next example
                system.clear()

            system.close()
            results["results"][dataset_name][system_name] = system_results
            print(f"    Completed {len(system_results)} queries")

    # Save results
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Results saved to {output_path}")
    print(f"{'='*60}")

    return results


def main():
    """Run benchmark with default settings."""
    import argparse

    parser = argparse.ArgumentParser(description="Run MemoryGraph benchmark")
    parser.add_argument("--systems", nargs="+", choices=list(SYSTEMS.keys()), help="Systems to test")
    parser.add_argument("--datasets", nargs="+", choices=list(DATASETS.keys()), help="Datasets to test")
    parser.add_argument("--max-examples", type=int, help="Max examples per dataset")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    run_benchmark(
        systems=args.systems,
        datasets=args.datasets,
        max_examples_per_dataset=args.max_examples,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()