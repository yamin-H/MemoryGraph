"""Scorer for benchmark results."""

import json
import re
from pathlib import Path
from typing import Any


def normalize_answer(answer: str) -> str:
    """Normalize answer for comparison."""
    if not answer:
        return ""
    # Lowercase, remove punctuation, extra whitespace
    answer = answer.lower().strip()
    answer = re.sub(r"[^\w\s]", "", answer)
    answer = re.sub(r"\s+", " ", answer)
    return answer


def exact_match(predicted: str, ground_truth: str) -> bool:
    """Check if predicted answer exactly matches ground truth."""
    return normalize_answer(predicted) == normalize_answer(ground_truth)


def contains_answer(predicted: str, ground_truth: str) -> bool:
    """Check if predicted answer contains ground truth."""
    pred_norm = normalize_answer(predicted)
    gt_norm = normalize_answer(ground_truth)
    return gt_norm in pred_norm or pred_norm in gt_norm


def score_example(predicted: str, ground_truth: str, abstained: bool) -> dict[str, Any]:
    """Score a single example."""
    em = exact_match(predicted, ground_truth)
    contains = contains_answer(predicted, ground_truth)

    # Determine if answer is correct
    is_correct = em or contains

    return {
        "exact_match": em,
        "contains_answer": contains,
        "is_correct": is_correct,
        "abstained": abstained,
        "false_abstention": abstained and is_correct,  # Shouldn't have abstained
        "missed_abstention": not abstained and not is_correct and ground_truth.lower() in ["i don't know", "unknown", "no information"],
    }


def compute_metrics(results: list[dict[str, Any]]) -> dict[str, float]:
    """Compute aggregate metrics from results."""
    if not results:
        return {}

    total = len(results)
    correct = sum(1 for r in results if r.get("is_correct", False))
    abstained = sum(1 for r in results if r.get("abstained", False))
    false_abstentions = sum(1 for r in results if r.get("false_abstention", False))
    missed_abstentions = sum(1 for r in results if r.get("missed_abstention", False))

    # Exact match accuracy
    em_correct = sum(1 for r in results if r.get("exact_match", False))
    em_accuracy = em_correct / total if total > 0 else 0.0

    # Contains accuracy
    contains_correct = sum(1 for r in results if r.get("contains_answer", False))
    contains_accuracy = contains_correct / total if total > 0 else 0.0

    # Abstention accuracy (correctly abstained)
    should_abstain = sum(1 for r in results if r.get("ground_truth", "").lower() in ["i don't know", "unknown", "no information", ""])
    correct_abstentions = sum(1 for r in results if r.get("abstained", False) and r.get("ground_truth", "").lower() in ["i don't know", "unknown", "no information", ""])
    abstention_accuracy = correct_abstentions / should_abstain if should_abstain > 0 else 1.0

    # False abstention rate
    false_abstention_rate = false_abstentions / total if total > 0 else 0.0

    # Average latency
    latencies = [r.get("latency_ms", 0) for r in results if r.get("latency_ms", 0) > 0]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    # Context exceeded rate
    context_exceeded = sum(1 for r in results if r.get("context_exceeded", False))
    context_exceeded_rate = context_exceeded / total if total > 0 else 0.0

    return {
        "total_examples": total,
        "exact_match_accuracy": em_accuracy,
        "contains_accuracy": contains_accuracy,
        "overall_accuracy": correct / total if total > 0 else 0.0,
        "abstention_rate": abstained / total if total > 0 else 0.0,
        "abstention_accuracy": abstention_accuracy,
        "false_abstention_rate": false_abstention_rate,
        "missed_abstention_rate": missed_abstentions / total if total > 0 else 0.0,
        "avg_latency_ms": avg_latency,
        "context_exceeded_rate": context_exceeded_rate,
    }


def compute_metrics_by_type(results: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Compute metrics grouped by question type."""
    from collections import defaultdict

    by_type = defaultdict(list)
    for r in results:
        q_type = r.get("question_type", "unknown")
        by_type[q_type].append(r)

    metrics_by_type = {}
    for q_type, type_results in by_type.items():
        metrics_by_type[q_type] = compute_metrics(type_results)
        metrics_by_type[q_type]["count"] = len(type_results)

    return metrics_by_type


def generate_comparison_table(
    all_results: dict[str, Any],
) -> str:
    """Generate markdown comparison table."""
    systems = all_results.get("systems", [])
    datasets = all_results.get("datasets", [])
    results = all_results.get("results", {})

    # Build metrics for each system/dataset/type
    all_metrics = {}
    for dataset_name in datasets:
        all_metrics[dataset_name] = {}
        for system_name in systems:
            system_results = results.get(dataset_name, {}).get(system_name, [])
            # Add question_type to each result
            dataset_class = None
            if dataset_name == "longmemeval":
                from datasets import LongMemEvalDataset
                dataset_class = LongMemEvalDataset()
            elif dataset_name == "longmemeval_v2":
                from datasets import LongMemEvalV2Dataset
                dataset_class = LongMemEvalV2Dataset()
            elif dataset_name == "beam":
                from datasets import BEAMDataset
                dataset_class = BEAMDataset()

            if dataset_class:
                dataset_examples = {ex["question_id"]: ex for ex in dataset_class.load()}
                for r in system_results:
                    ex = dataset_examples.get(r["question_id"])
                    if ex:
                        r["question_type"] = ex.get("question_type", "unknown")

            all_metrics[dataset_name][system_name] = compute_metrics_by_type(system_results)

    # Get all question types
    all_types = set()
    for dataset_metrics in all_metrics.values():
        for system_metrics in dataset_metrics.values():
            all_types.update(system_metrics.keys())
    all_types.discard("overall")
    all_types = sorted([t for t in all_types if t != "overall"])

    # Generate table
    lines = []
    lines.append("# Benchmark Results\n")

    for dataset_name in datasets:
        lines.append(f"## {dataset_name}\n")
        lines.append("| Question Type | " + " | ".join(systems) + " |")
        lines.append("| " + " | ".join(["---"] * (len(systems) + 1)) + " |")

        for q_type in all_types:
            row = [q_type]
            for system_name in systems:
                metrics = all_metrics[dataset_name].get(system_name, {}).get(q_type, {})
                acc = metrics.get("overall_accuracy", 0.0)
                count = metrics.get("count", 0)
                row.append(f"{acc:.1%} ({count})")
            lines.append("| " + " | ".join(row) + " |")

        # Overall row
        row = ["**Overall**"]
        for system_name in systems:
            metrics = all_metrics[dataset_name].get(system_name, {}).get("overall", {})
            acc = metrics.get("overall_accuracy", 0.0)
            count = metrics.get("total_examples", 0)
            row.append(f"**{acc:.1%}** ({count})")
        lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    return "\n".join(lines)


def score_benchmark_results(results_file: str, output_file: str | None = None) -> dict[str, Any]:
    """Score benchmark results and generate report."""
    with open(results_file) as f:
        data = json.load(f)

    scored = {
        "systems": data["systems"],
        "datasets": data["datasets"],
        "scored_results": {},
    }

    for dataset_name in data["datasets"]:
        scored["scored_results"][dataset_name] = {}
        for system_name in data["systems"]:
            system_results = data["results"].get(dataset_name, {}).get(system_name, [])
            metrics = compute_metrics(system_results)
            scored["scored_results"][dataset_name][system_name] = metrics

    # Generate comparison table
    table = generate_comparison_table(data)

    if output_file:
        output_path = Path(output_file)
    else:
        output_path = Path(results_file).parent / "benchmark_report.md"

    output_path.write_text(table)

    # Also save scored JSON
    json_path = output_path.with_suffix(".json")
    with open(json_path, "w") as f:
        json.dump(scored, f, indent=2)

    print(f"Report saved to {output_path}")
    print(f"Scored JSON saved to {json_path}")

    return scored


def main():
    """Score existing benchmark results."""
    import argparse

    parser = argparse.ArgumentParser(description="Score benchmark results")
    parser.add_argument("results_file", help="Path to benchmark_results.json")
    parser.add_argument("--output", help="Output report path")
    args = parser.parse_args()

    score_benchmark_results(args.results_file, args.output)


if __name__ == "__main__":
    main()
