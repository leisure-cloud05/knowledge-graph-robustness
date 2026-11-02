
"""Generate one four-panel publication-style figure for Part D."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "results" / "part_d" / "analysis"

STRATEGIES = ("none", "random", "degree", "betweenness")
PROTECTED = STRATEGIES[1:]
METRICS = ("Q", "S")
Q_VALUES = tuple(round(i / 10, 1) for i in range(11))
N_TRIALS = 30

COLORS = {
    "none": "#4D4D4D",
    "random": "#0072B2",
    "degree": "#E69F00",
    "betweenness": "#009E73",
}

LABELS = {
    "none": "No protection",
    "random": "Random",
    "degree": "Degree",
    "betweenness": "Betweenness",
}

MARKERS = {
    "none": "o",
    "random": "s",
    "degree": "^",
    "betweenness": "D",
}

LINESTYLES = {
    "none": (0, (4, 2)),
    "random": "-",
    "degree": (0, (5, 2)),
    "betweenness": "-",
}

METRIC_LABELS = {
    "Q": "Query availability, Q",
    "S": "Largest component fraction, S",
}


def configure_style() -> None:
    """Configure publication-style Matplotlib settings."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "axes.linewidth": 0.8,
        "axes.edgecolor": "#333333",
        "axes.labelcolor": "#222222",
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.major.size": 3.5,
        "ytick.major.size": 3.5,
        "legend.fontsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 600,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def load_table(filename: str, input_dir: Path) -> pd.DataFrame:
    """Load a required statistical CSV file."""
    path = input_dir / filename

    if not path.is_file():
        raise FileNotFoundError(f"Missing statistical file: {path}")

    return pd.read_csv(path)


def validate_statistics(
    data: pd.DataFrame,
    strategies: tuple[str, ...],
) -> None:
    """Validate statistical coverage and confidence intervals."""
    required = {
        "strategy",
        "q",
        "metric",
        "n",
        "mean",
        "ci_lower",
        "ci_upper",
    }

    missing = required - set(data.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    expected = {
        (strategy, q, metric)
        for strategy in strategies
        for q in Q_VALUES
        for metric in METRICS
    }

    actual = [
        (
            row.strategy,
            round(float(row.q), 1),
            row.metric,
        )
        for row in data.itertuples(index=False)
    ]

    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError("Incomplete or duplicated statistical design.")

    if not data["n"].eq(N_TRIALS).all():
        raise ValueError("Expected 30 trials per statistical group.")

    numeric = data[["mean", "ci_lower", "ci_upper"]]

    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Non-finite statistical values.")

    if not (
        (data["ci_lower"] <= data["mean"])
        & (data["mean"] <= data["ci_upper"])
    ).all():
        raise ValueError("Invalid confidence intervals.")


def get_series(
    data: pd.DataFrame,
    strategy: str,
    metric: str,
) -> pd.DataFrame:
    """Select one complete strategy-metric series."""
    subset = data.loc[
        (data["strategy"] == strategy)
        & (data["metric"] == metric)
    ].sort_values("q")

    if len(subset) != len(Q_VALUES):
        raise ValueError(
            f"Incomplete series: {strategy}, {metric}."
        )

    return subset


def format_axes(ax: Axes) -> None:
    """Apply consistent scientific axes formatting."""
    ax.set_xlim(-0.015, 1.015)
    ax.set_xticks(np.arange(0, 1.01, 0.2))
    ax.set_xticks(np.arange(0, 1.01, 0.1), minor=True)

    ax.tick_params(
        axis="both",
        which="major",
        width=0.8,
    )

    ax.tick_params(
        axis="x",
        which="minor",
        length=2,
        width=0.5,
    )

    ax.set_xlabel(
        "Edge failure probability, q",
        labelpad=7,
    )

    ax.grid(
        axis="y",
        color="#E5E5E5",
        linewidth=0.5,
    )

    ax.set_axisbelow(True)


def plot_series(
    ax: Axes,
    data: pd.DataFrame,
    metric: str,
    strategies: tuple[str, ...],
) -> None:
    """Plot means and pointwise 95% confidence intervals."""
    for strategy in strategies:
        subset = get_series(data, strategy, metric)

        q = subset["q"].to_numpy(dtype=float)
        mean = subset["mean"].to_numpy(dtype=float)
        lower = subset["ci_lower"].to_numpy(dtype=float)
        upper = subset["ci_upper"].to_numpy(dtype=float)

        ax.plot(
            q,
            mean,
            label=LABELS[strategy],
            color=COLORS[strategy],
            linestyle=LINESTYLES[strategy],
            marker=MARKERS[strategy],
            markersize=4,
            markerfacecolor="white",
            markeredgewidth=1.1,
            linewidth=1.8,
            zorder=3,
        )

        ax.fill_between(
            q,
            lower,
            upper,
            color=COLORS[strategy],
            alpha=0.12,
            linewidth=0,
            zorder=2,
        )


def plot_robustness_panel(
    ax: Axes,
    summary: pd.DataFrame,
    metric: str,
) -> None:
    """Plot absolute query availability or connectivity."""
    plot_series(ax, summary, metric, STRATEGIES)
    format_axes(ax)

    ax.set_ylabel(METRIC_LABELS[metric], labelpad=8)
    ax.set_ylim(0, 1.04)
    ax.set_yticks(np.arange(0, 1.01, 0.2))

    title = (
        "Query availability"
        if metric == "Q"
        else "Global network connectivity"
    )

    ax.set_title(title, loc="left", pad=11)


def plot_improvement_panel(
    ax: Axes,
    improvements: pd.DataFrame,
    metric: str,
) -> None:
    """Plot paired improvement relative to no protection."""
    plot_series(ax, improvements, metric, PROTECTED)
    format_axes(ax)

    ax.axhline(
        0,
        color="#777777",
        linestyle=(0, (3, 3)),
        linewidth=1,
        zorder=1,
    )

    ax.set_ylabel(
        f"Paired improvement in {metric}",
        labelpad=8,
    )

    ax.set_title(
        "Gain in query availability",
        loc="left",
        pad=11,
    )

    subset = improvements[
        improvements["metric"] == metric
    ]

    lower = min(0.0, float(subset["ci_lower"].min()))
    upper = max(0.0, float(subset["ci_upper"].max()))
    span = upper - lower

    if span == 0:
        span = 0.01

    padding = 0.08 * span
    ax.set_ylim(lower - padding, upper + padding)


def add_panel_label(ax: Axes, label: str) -> None:
    """Add a bold panel identifier."""
    ax.text(
        -0.13,
        1.10,
        label,
        transform=ax.transAxes,
        fontsize=13,
        fontweight="bold",
        ha="left",
        va="top",
        clip_on=False,
    )


def plot_direct_comparison(
    ax: Axes,
    direct: pd.DataFrame,
) -> None:
    """Plot Betweenness minus Degree for Q and S."""
    for metric, color, marker in (
        ("Q", "#0072B2", "o"),
        ("S", "#009E73", "s"),
    ):
        subset = direct.loc[
            direct["metric"] == metric
        ].sort_values("q")

        q = subset["q"].to_numpy(dtype=float)
        mean = subset["mean"].to_numpy(dtype=float)
        lower = subset["ci_lower"].to_numpy(dtype=float)
        upper = subset["ci_upper"].to_numpy(dtype=float)

        ax.plot(
            q,
            mean,
            color=color,
            marker=marker,
            markerfacecolor="white",
            markersize=4,
            linewidth=1.8,
            label=metric,
        )

        ax.fill_between(
            q,
            lower,
            upper,
            color=color,
            alpha=0.14,
            linewidth=0,
        )

    ax.axhline(
        0,
        color="#777777",
        linestyle="--",
        linewidth=1,
    )

    format_axes(ax)

    ax.set_ylabel(
        "Betweenness minus Degree",
        labelpad=8,
    )

    ax.set_title(
        "Direct paired comparison",
        loc="left",
        pad=11,
    )

    ax.legend(
        loc="best",
        frameon=False,
        fontsize=8,
    )


def validate_direct_comparison(
    direct: pd.DataFrame,
) -> None:
    """Validate direct Betweenness-Degree paired statistics."""
    required = {
        "strategy",
        "reference",
        "q",
        "metric",
        "n",
        "mean",
        "ci_lower",
        "ci_upper",
    }

    missing = required - set(direct.columns)

    if missing:
        raise ValueError(
            f"Missing direct comparison columns: {sorted(missing)}"
        )

    expected = {
        ("betweenness", "degree", q, metric)
        for q in Q_VALUES
        for metric in METRICS
    }

    actual = [
        (
            row.strategy,
            row.reference,
            round(float(row.q), 1),
            row.metric,
        )
        for row in direct.itertuples(index=False)
    ]

    if len(actual) != 22 or set(actual) != expected:
        raise ValueError("Invalid direct comparison design.")

    if not direct["n"].eq(N_TRIALS).all():
        raise ValueError("Direct comparison must use 30 trials.")

    numeric = direct[["mean", "ci_lower", "ci_upper"]]

    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Non-finite direct comparison values.")

    if not (
        (direct["ci_lower"] <= direct["mean"])
        & (direct["mean"] <= direct["ci_upper"])
    ).all():
        raise ValueError("Invalid direct comparison confidence intervals.")


def create_final_figure(
    summary: pd.DataFrame,
    improvements: pd.DataFrame,
    direct: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Create and save one consolidated four-panel figure."""
    fig, axes = plt.subplots(
        2,
        2,
        figsize=(12, 8.8),
    )

    plot_robustness_panel(
        axes[0, 0],
        summary,
        "Q",
    )

    plot_robustness_panel(
        axes[0, 1],
        summary,
        "S",
    )

    plot_improvement_panel(
        axes[1, 0],
        improvements,
        "Q",
    )

    plot_direct_comparison(
        axes[1, 1],
        direct,
    )

    for ax, label in zip(
        axes.flat,
        ("a", "b", "c", "d"),
        strict=True,
    ):
        add_panel_label(ax, label)

    handles, labels = axes[0, 0].get_legend_handles_labels()

    fig.legend(
        handles,
        labels,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.035),
        ncol=4,
        frameon=False,
        fontsize=9,
        columnspacing=2,
        handlelength=2.8,
    )

    fig.subplots_adjust(
        left=0.10,
        right=0.97,
        top=0.93,
        bottom=0.13,
        hspace=0.42,
        wspace=0.32,
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = output_dir / "part_d_final_figure.png"

    fig.savefig(
        output_path,
        dpi=600,
        bbox_inches="tight",
        pad_inches=0.15,
        facecolor="white",
    )

    plt.close(fig)

    print(f"Saved: {output_path}")


def main() -> None:
    """Validate inputs and generate the final Part D figure."""
    parser = argparse.ArgumentParser(
        description="Plot Part D statistics as one four-panel figure."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ANALYSIS_DIR,
        help="Statistics directory (default: results/part_d/analysis).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Figure directory (default: <input>/figures).",
    )
    args = parser.parse_args()

    input_dir = args.input.resolve()
    output_dir = (
        args.output.resolve()
        if args.output is not None
        else input_dir / "figures"
    )

    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")

    configure_style()

    summary = load_table("summary.csv", input_dir)
    improvements = load_table("paired_improvements.csv", input_dir)
    direct = load_table("direct_comparisons.csv", input_dir)

    validate_statistics(
        summary,
        STRATEGIES,
    )

    validate_statistics(
        improvements,
        PROTECTED,
    )

    validate_direct_comparison(direct)

    create_final_figure(
        summary,
        improvements,
        direct,
        output_dir,
    )

    print("\nStep 8 visualization completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(
            f"Visualization failed: {error}"
        ) from error
