"""
Plot benchmark CSV results for LAGraph and SPLA.

This module loads CSV result files produced by the benchmark wrapper and
creates comparison bar charts with error bars.
"""

import argparse
import os
from typing import Any, Dict, Optional

# pylint: disable=import-error
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def load_results(path: str) -> pd.DataFrame:
    """Read benchmark CSV output and extract average plus stdev values."""
    df = pd.read_csv(path)
    tool_col = df.columns[1]

    def parse_field(value: str, key: str) -> float:
        for part in value.split(","):
            part = part.strip()
            if part.startswith(key + "="):
                return float(part[len(key) + 1 :].replace("ms", "").strip())
        return 0.0

    df["avg"] = df[tool_col].apply(lambda item: parse_field(item, "avg"))
    df["stdev"] = df[tool_col].apply(lambda item: parse_field(item, "stdev"))
    df["tool"] = tool_col
    return df[["dataset", "avg", "stdev", "tool"]]


def _make_bar_kwargs() -> Dict[str, Any]:
    return {
        "capsize": 3,
        "error_kw": {"linewidth": 0.8},
        "edgecolor": "white",
        "linewidth": 0.6,
    }


def _annotate_bars(ax: plt.Axes, bars: Any, values: list[float]) -> None:
    """Annotate bar chart values above each bar."""
    for bar_obj, value in zip(bars, values):
        if value > 0:
            fontsize = 6.0 if value >= 10000 else 7.5
            ax.text(
                bar_obj.get_x() + bar_obj.get_width() / 2,
                bar_obj.get_height() * 1.05,
                f"{value:.1f}",
                ha="center",
                va="bottom",
                fontsize=fontsize,
                color="#333333",
            )


def _align_results(
    lg: pd.DataFrame,
    sp: pd.DataFrame,
    lg_sort: Optional[pd.DataFrame],
) -> tuple[list[str], pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]]:
    """Align datasets between LAGraph, SPLA, and optional sorted LAGraph results."""
    datasets = [
        dataset for dataset in lg["dataset"] if dataset in sp["dataset"].values
    ]
    if lg_sort is not None:
        datasets = [
            dataset for dataset in datasets if dataset in lg_sort["dataset"].values
        ]

    lg = lg[lg["dataset"].isin(datasets)].set_index("dataset").reindex(datasets)
    sp = sp[sp["dataset"].isin(datasets)].set_index("dataset").reindex(datasets)
    if lg_sort is not None:
        lg_sort = (
            lg_sort[lg_sort["dataset"].isin(datasets)]
            .set_index("dataset")
            .reindex(datasets)
        )

    return datasets, lg, sp, lg_sort


def _draw_bars(
    ax: plt.Axes,
    x: np.ndarray,
    data: tuple[pd.DataFrame, pd.DataFrame, Optional[pd.DataFrame]],
    plot_state: dict[str, Any],
) -> tuple[Any, Optional[Any], Any]:
    """Draw bars for LAGraph, optional sorted LAGraph, and SPLA."""
    lg, sp, lg_sort = data
    offsets = plot_state["offsets"]
    width = plot_state["width"]
    bar_kw = plot_state["bar_kw"]

    bars_lg = ax.bar(
        x + offsets[0],
        lg["avg"],
        width,
        yerr=lg["stdev"],
        label="LAGraph",
        color="#4C72B0",
        **bar_kw,
    )
    bars_lg_sort = None
    if lg_sort is not None:
        bars_lg_sort = ax.bar(
            x + offsets[1],
            lg_sort["avg"],
            width,
            yerr=lg_sort["stdev"],
            label="LAGraph (AutoSort)",
            color="#55A868",
            **bar_kw,
        )
    bars_sp = ax.bar(
        x + offsets[-1],
        sp["avg"],
        width,
        yerr=sp["stdev"],
        label="SPLA",
        color="#DD8452",
        **bar_kw,
    )
    return bars_lg, bars_lg_sort, bars_sp


def _prepare_plot(
    datasets: list[str],
    lg_sort: Optional[pd.DataFrame],
) -> dict[str, Any]:
    """Prepare the plotting state for the bar chart."""
    x_axis = np.arange(len(datasets))
    width = 0.25 if lg_sort is not None else 0.35
    _, ax = plt.subplots(figsize=(max(10, len(datasets) * 1.6), 6))
    offsets = [-width, 0, width] if lg_sort is not None else [-width / 2, width / 2]
    return {
        "ax": ax,
        "x_axis": x_axis,
        "width": width,
        "offsets": offsets,
        "bar_kw": _make_bar_kwargs(),
    }


def _configure_axis(ax: plt.Axes, datasets: list[str], algo: str) -> None:
    """Configure axis labels, legend, and grid styling."""
    ax.set_title(
        f"LAGraph vs SPLA — {algo.upper()}", fontsize=14, fontweight="bold", pad=12
    )
    ax.set_xlabel("Dataset", fontsize=11)
    ax.set_yscale("log")
    ax.set_ylabel("Execution time (ms, log scale)", fontsize=11)
    ax.set_xticks(np.arange(len(datasets)))
    ax.set_xticklabels(datasets, rotation=25, ha="right", fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(fontsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def plot_comparison(
    lagraph_path: str,
    spla_path: str,
    algo: str,
    output_dir: str = "plots",
    lagraph_sort_path: Optional[str] = None,
) -> None:
    """Generate a bar chart comparing LAGraph and SPLA benchmark results."""
    lg = load_results(lagraph_path)
    sp = load_results(spla_path)
    lg_sort = load_results(lagraph_sort_path) if lagraph_sort_path else None

    datasets, lg, sp, lg_sort = _align_results(lg, sp, lg_sort)
    plot_state = _prepare_plot(datasets, lg_sort)

    bars_lg, bars_lg_sort, bars_sp = _draw_bars(
        plot_state["ax"],
        plot_state["x_axis"],
        (lg, sp, lg_sort),
        plot_state,
    )

    _annotate_bars(plot_state["ax"], bars_lg, lg["avg"].tolist())
    if lg_sort is not None and bars_lg_sort is not None:
        _annotate_bars(plot_state["ax"], bars_lg_sort, lg_sort["avg"].tolist())
    _annotate_bars(plot_state["ax"], bars_sp, sp["avg"].tolist())

    _configure_axis(plot_state["ax"], datasets, algo)
    plt.tight_layout()
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{algo}_lagraph_vs_spla.png")
    plt.savefig(out_path, dpi=180)
    plt.close()
    print(f"Saved: {out_path}")


def main() -> None:
    """Execute the command-line plot builder."""
    parser = argparse.ArgumentParser(
        description="Plot LAGraph vs SPLA benchmark results"
    )
    parser.add_argument("lagraph", help="Path to LAGraph CSV results")
    parser.add_argument("spla", help="Path to SPLA CSV results")
    parser.add_argument(
        "--algo",
        default="bfs",
        help="Algorithm name (bfs, sssp, tc, pr)",
    )
    parser.add_argument(
        "--output",
        default="plots",
        help="Output directory for plots",
    )
    parser.add_argument(
        "--lagraph-sort",
        default=None,
        help="Path to LAGraph CSV with AutoSort (TC only)",
    )
    args = parser.parse_args()

    plot_comparison(
        args.lagraph, args.spla, args.algo, args.output, args.lagraph_sort
    )


if __name__ == "__main__":
    main()
