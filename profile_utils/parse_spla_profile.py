#!/usr/bin/env python3

"""Parse SPLA profiler output and summarize GPU execution metrics."""

import argparse
import re
import statistics
from collections import defaultdict
from typing import Any


def parse_profile(filename: str) -> list[dict[str, Any]]:
    """Parse SPLA profiler output and return detected iterations."""
    # BFS: "- iter 1 front 14 discovered 1 647.84 ms"
    # SSSP:"- iter 1 feed 34 1.92 ms"
    iter_pattern = re.compile(
        r"- iter (\d+) (?:front|feed) (\d+)(?: discovered \d+)? ([\d.eE+-]+) ms"
    )
    metric_pattern = re.compile(
        r"\s+- ([\w/\-\.]+) ([\d.eE+-]+) \(queue: ([\d.eE+-]+) exec: ([\d.eE+-]+)\) ms"
    )

    iterations: list[dict[str, Any]] = []
    current_iteration = None
    gpu_run_active = False

    with open(filename, encoding="utf-8") as profile_file:
        for line in profile_file:
            if "force no acc: 0" in line:
                gpu_run_active = True
                iterations = []
                current_iteration = None
                continue

            if gpu_run_active:
                match_iteration = iter_pattern.search(line)
                if match_iteration:
                    current_iteration = {
                        "iter": int(match_iteration.group(1)),
                        "count": int(match_iteration.group(2)),
                        "discovered": 0,
                        "total_ms": float(match_iteration.group(3)),
                        "metrics": {},
                    }
                    if "discovered" in line:
                        discovered_match = re.search(r"discovered (\d+)", line)
                        if discovered_match:
                            current_iteration["discovered"] = int(
                                discovered_match.group(1)
                            )
                    iterations.append(current_iteration)
                    continue

                match_metric = metric_pattern.search(line)
                if match_metric and current_iteration is not None:
                    current_iteration["metrics"][match_metric.group(1)] = {
                        "wall_ms": float(match_metric.group(2)),
                        "queue_ms": float(match_metric.group(3)),
                        "exec_ms": float(match_metric.group(4)),
                    }

    return iterations


def summarize(iterations: list[dict[str, Any]]) -> None:
    """Print a summary of parsed SPLA profile iterations."""
    if not iterations:
        return

    is_bfs = any(item["discovered"] > 0 for item in iterations)
    count_label = "front" if is_bfs else "feed"
    algo_name = "BFS" if is_bfs else "SSSP"

    print(f"{'=' * 70}")
    print(f"Всего итераций: {len(iterations)}")
    total_time = sum(item["total_ms"] for item in iterations)
    print(f"Суммарное время {algo_name}: {total_time:.2f} ms")
    counts = [item["count"] for item in iterations]
    print(
        f"Средний размер {count_label} (все итерации): "
        f"{statistics.mean(counts):.1f} "
        f"(min={min(counts)}, max={max(counts)})"
    )
    print(f"{'=' * 70}\n")

    agg = _aggregate_metrics(iterations)
    _print_metric_table(agg, total_time)
    _print_first_iteration(iterations[0], count_label)
    _print_steady_summary(iterations[1:])


def _aggregate_metrics(iterations: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"wall_ms": 0.0, "exec_ms": 0.0, "count": 0}
    )
    for item in iterations:
        for name, values in item["metrics"].items():
            agg[name]["wall_ms"] += values["wall_ms"]
            agg[name]["exec_ms"] += values["exec_ms"]
            agg[name]["count"] += 1
    return agg


def _print_metric_table(agg: dict[str, dict[str, float]], total_time: float) -> None:
    print(
        f"\n{'Метрика':<45} {'Σwall_ms':>10} {'Σexec_ms':>10} "
        f"{'%total':>8} {'вызовов':>8}"
    )
    print("-" * 85)
    sorted_metrics = sorted(
        agg.items(), key=lambda item: item[1]["wall_ms"], reverse=True
    )
    for name, values in sorted_metrics[:20]:
        pct = values["wall_ms"] / total_time * 100 if total_time > 0 else 0
        print(
            f"{name:<45} {values['wall_ms']:>10.2f} "
            f"{values['exec_ms']:>10.4f} {pct:>7.1f}% {values['count']:>8}"
        )


def _print_first_iteration(first_iteration: dict[str, Any], count_label: str) -> None:
    print(f"\n{'=' * 70}")
    print("Итерация 1 отдельно (warm-up kernel compilation):")
    print(f"{'=' * 70}")
    print(
        f"iter={first_iteration['iter']} {count_label}="
        f"{first_iteration['count']} discovered="
        f"{first_iteration['discovered']} total="
        f"{first_iteration['total_ms']:.2f} ms"
    )
    for name, values in sorted(
        first_iteration["metrics"].items(),
        key=lambda item: item[1]["wall_ms"],
        reverse=True,
    ):
        print(
            f"  {name:<43} wall={values['wall_ms']:>8.3f} ms "
            f"exec={values['exec_ms']:>8.6f} ms"
        )


def _print_steady_summary(steady_iterations: list[dict[str, Any]]) -> None:
    print(f"\n{'=' * 70}")
    print("Итерации 2+:")
    print(f"{'=' * 70}")
    if not steady_iterations:
        return

    agg2: dict[str, dict[str, float]] = defaultdict(
        lambda: {"wall_ms": 0.0, "exec_ms": 0.0}
    )
    for item in steady_iterations:
        for name, values in item["metrics"].items():
            agg2[name]["wall_ms"] += values["wall_ms"]
            agg2[name]["exec_ms"] += values["exec_ms"]
    count_iterations = len(steady_iterations)
    total2 = sum(item["total_ms"] for item in steady_iterations)
    print(
        f"Итераций: {count_iterations}, суммарно: {total2:.2f} ms, "
        f"среднее: {total2 / count_iterations:.3f} ms/iter"
    )
    print(
        f"\n{'Метрика':<45} {'avg_wall_ms':>12} "
        f"{'avg_exec_ms':>12} {'%iter':>8}"
    )
    print("-" * 82)
    per_iter_avg = total2 / count_iterations
    for name, values in sorted(
        agg2.items(), key=lambda item: item[1]["wall_ms"], reverse=True
    )[:15]:
        avg_wall = values["wall_ms"] / count_iterations
        avg_exec = values["exec_ms"] / count_iterations
        pct = avg_wall / per_iter_avg * 100 if per_iter_avg > 0 else 0
        print(
            f"{name:<45} {avg_wall:>12.4f} "
            f"{avg_exec:>12.6f} {pct:>7.1f}%"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parser for SPLA profile (BFS/SSSP)"
    )
    parser.add_argument("profile_file", help="Path to the profile file")
    args = parser.parse_args()

    parsed_iterations = parse_profile(args.profile_file)
    summarize(parsed_iterations)
