
"""Analyze Part D edge-protection experiments and computational costs."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t


ROOT = Path(__file__).resolve().parents[1]
RUNS_PATH = ROOT / "results" / "part_d" / "full" / "runs.csv"
SELECTION_PATH = (
    ROOT / "results" / "part_d" / "selection" / "selection_metadata.json"
)
OUTPUT_DIR = ROOT / "results" / "part_d" / "analysis"

STRATEGIES = ("none", "random", "degree", "betweenness")
PROTECTED = STRATEGIES[1:]
METRICS = ("Q", "S")
KEY_Q = (0.2, 0.3, 0.4)
N_TRIALS = 30
Q_VALUES = tuple(round(i / 10, 1) for i in range(11))
TIME_COLUMNS = ("damage_seconds", "evaluation_seconds")


def calculate_stats(values: pd.Series) -> dict[str, float]:
    """Calculate mean, sample SD, and a two-sided 95% t interval."""
    sample = values.to_numpy(dtype=float)
    n = len(sample)

    if n != N_TRIALS or not np.isfinite(sample).all():
        raise ValueError(
            f"Expected {N_TRIALS} finite observations, found {n}."
        )

    mean = float(np.mean(sample))
    sd = float(np.std(sample, ddof=1))
    margin = float(t.ppf(0.975, n - 1) * sd / np.sqrt(n))

    return {
        "n": n,
        "mean": mean,
        "sd": sd,
        "ci_lower": mean - margin,
        "ci_upper": mean + margin,
    }


def load_runs(input_path: Path) -> pd.DataFrame:
    """Load and validate the complete factorial experiment."""
    if not input_path.is_file():
        raise FileNotFoundError(f"Missing experiment file: {input_path}")

    df = pd.read_csv(input_path)

    required = {
        "strategy",
        "trial",
        "q",
        *METRICS,
        *TIME_COLUMNS,
    }

    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if df[list(required)].isna().any().any():
        raise ValueError("Required experimental fields contain NaN.")

    raw_q = df["q"].to_numpy(dtype=float)
    rounded_q = np.round(raw_q, 1)

    if not np.isfinite(raw_q).all():
        raise ValueError("Non-finite failure probabilities.")

    if not np.allclose(
        raw_q,
        rounded_q,
        atol=1e-10,
        rtol=0,
    ):
        raise ValueError("Unexpected failure probabilities.")

    df["q"] = rounded_q

    expected = {
        (strategy, trial, q)
        for strategy in STRATEGIES
        for trial in range(N_TRIALS)
        for q in Q_VALUES
    }

    actual = list(
        df[["strategy", "trial", "q"]].itertuples(
            index=False,
            name=None,
        )
    )

    if (
        len(actual) != 1320
        or len(set(actual)) != 1320
        or set(actual) != expected
    ):
        raise ValueError("Incomplete or duplicated experimental design.")

    numeric_columns = [*METRICS, *TIME_COLUMNS]

    if not np.isfinite(
        df[numeric_columns].to_numpy(dtype=float)
    ).all():
        raise ValueError("Non-finite experimental values found.")

    if not df[list(METRICS)].ge(0).all().all():
        raise ValueError("Negative Q or S values found.")

    if not df[list(METRICS)].le(1).all().all():
        raise ValueError("Q or S exceeds one.")

    if not df[list(TIME_COLUMNS)].ge(0).all().all():
        raise ValueError("Negative processing time found.")

    df["total_seconds"] = (
        df["damage_seconds"] + df["evaluation_seconds"]
    )

    return df


def summarize_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize Q and S for every strategy and failure probability."""
    records = []

    for (strategy, q), group in df.groupby(["strategy", "q"]):
        for metric in METRICS:
            records.append({
                "strategy": strategy,
                "q": q,
                "metric": metric,
                **calculate_stats(group[metric]),
            })

    return pd.DataFrame(records).sort_values(
        ["metric", "q", "strategy"]
    ).reset_index(drop=True)


def make_paired_table(
    df: pd.DataFrame,
    reference: str,
    candidates: tuple[str, ...],
) -> pd.DataFrame:
    """Compute matched-trial differences against a reference."""
    baseline = (
        df.loc[
            df["strategy"] == reference,
            ["trial", "q", *METRICS],
        ]
        .set_index(["trial", "q"])
        .sort_index()
    )

    records = []

    for strategy in candidates:
        candidate = (
            df.loc[
                df["strategy"] == strategy,
                ["trial", "q", *METRICS],
            ]
            .set_index(["trial", "q"])
            .sort_index()
        )

        if not candidate.index.equals(baseline.index):
            raise ValueError(
                f"Unmatched trials: {strategy} versus {reference}."
            )

        for q in Q_VALUES:
            candidate_q = candidate.xs(q, level="q")
            baseline_q = baseline.xs(q, level="q")

            for metric in METRICS:
                difference = (
                    candidate_q[metric] - baseline_q[metric]
                )

                stats = calculate_stats(difference)
                baseline_mean = float(baseline_q[metric].mean())

                relative = (
                    100.0 * stats["mean"] / baseline_mean
                    if baseline_mean > 0
                    else np.nan
                )

                records.append({
                    "strategy": strategy,
                    "reference": reference,
                    "q": q,
                    "metric": metric,
                    **stats,
                    "baseline_mean": baseline_mean,
                    "relative_improvement_pct": relative,
                })

    return pd.DataFrame(records).sort_values(
        ["metric", "q", "strategy"]
    ).reset_index(drop=True)


def summarize_timing(df: pd.DataFrame) -> pd.DataFrame:
    """Summarize scenario processing and recorded selection times."""
    if not SELECTION_PATH.is_file():
        raise FileNotFoundError(
            f"Missing selection metadata: {SELECTION_PATH}"
        )

    metadata = json.loads(
        SELECTION_PATH.read_text(encoding="utf-8")
    )

    selections = metadata["selections"]
    records = []

    for strategy in STRATEGIES:
        group = df[df["strategy"] == strategy]

        selection_seconds = (
            float(selections[strategy]["selection_seconds"])
            if strategy != "none"
            else 0.0
        )

        if not np.isfinite(selection_seconds) or selection_seconds < 0:
            raise ValueError(
                f"Invalid selection time for {strategy}."
            )

        records.append({
            "strategy": strategy,
            "n_scenarios": len(group),
            "mean_damage_seconds": float(
                group["damage_seconds"].mean()
            ),
            "mean_evaluation_seconds": float(
                group["evaluation_seconds"].mean()
            ),
            "mean_total_seconds": float(
                group["total_seconds"].mean()
            ),
            "sum_total_seconds": float(
                group["total_seconds"].sum()
            ),
            "selection_seconds": selection_seconds,
        })

    return pd.DataFrame(records)


def create_key_comparisons(
    summary: pd.DataFrame,
    improvements: pd.DataFrame,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Combine selected-q statistics, paired gains, and timing."""
    selected = summary[
        summary["q"].isin(KEY_Q)
    ].copy()

    selected = selected.rename(columns={
        "mean": "metric_mean",
        "sd": "metric_sd",
        "ci_lower": "metric_ci_lower",
        "ci_upper": "metric_ci_upper",
    })

    paired = improvements.rename(columns={
        "mean": "delta_mean",
        "sd": "delta_sd",
        "ci_lower": "delta_ci_lower",
        "ci_upper": "delta_ci_upper",
    })

    result = selected.merge(
        paired.drop(columns=["n", "reference"]),
        on=["strategy", "q", "metric"],
        how="left",
        validate="one_to_one",
    )

    timing = (
        df.groupby(["strategy", "q"], as_index=False)[
            ["damage_seconds", "evaluation_seconds", "total_seconds"]
        ]
        .mean()
        .rename(columns={
            "damage_seconds": "mean_damage_seconds",
            "evaluation_seconds": "mean_evaluation_seconds",
            "total_seconds": "mean_total_seconds",
        })
    )

    result = result.merge(
        timing,
        on=["strategy", "q"],
        how="left",
        validate="many_to_one",
    )

    return result.sort_values(
        ["metric", "q", "strategy"]
    ).reset_index(drop=True)


def main() -> None:
    """Run all statistical analyses and export CSV results."""
    parser = argparse.ArgumentParser(
        description="Analyze Part D full-experiment results."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=RUNS_PATH,
        help="Full-experiment runs.csv (default: results/part_d/full/runs.csv).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Statistics directory (default: results/part_d/analysis).",
    )
    args = parser.parse_args()

    input_path = args.input.resolve()
    output_dir = args.output.resolve()

    if output_dir == input_path.parent or output_dir in input_path.parents:
        raise ValueError("Output directory must not contain the input CSV.")

    df = load_runs(input_path)

    print(f"Input: {input_path}")
    print(f"Output directory: {output_dir}")

    summary = summarize_metrics(df)

    improvements = make_paired_table(
        df,
        reference="none",
        candidates=PROTECTED,
    )

    direct = make_paired_table(
        df,
        reference="degree",
        candidates=("betweenness",),
    )

    timing = summarize_timing(df)

    comparisons = create_key_comparisons(
        summary,
        improvements,
        df,
    )

    outputs = {
        "summary.csv": summary,
        "paired_improvements.csv": improvements.drop(
            columns=["reference"]
        ),
        "key_comparisons.csv": comparisons,
        "direct_comparisons.csv": direct,
        "timing_summary.csv": timing,
    }

    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, table in outputs.items():
        path = output_dir / filename

        table.to_csv(
            path,
            index=False,
            float_format="%.10f",
        )

        print(f"Saved: {path} ({len(table)} rows)")

    print("\nBetweenness minus Degree (paired Q differences):")

    selected = direct[
        (direct["metric"] == "Q")
        & (direct["q"].isin(KEY_Q))
    ]

    print(
        selected[
            ["q", "mean", "ci_lower", "ci_upper"]
        ].round(5).to_string(index=False)
    )

    print("\nStep 7 statistical analysis completed.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(
            f"Statistical analysis failed: {error}"
        ) from error
