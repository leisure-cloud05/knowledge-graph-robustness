"""One-command percolation study, using the shared PC5253-KG environment.

From the repository root:
    python scripts/percolation.py
    python -m scripts.percolation

Default outputs: data/percolation/ (CSV results, PNG figures, JSON metadata).
The research notebook is neither required nor executed.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=ROOT / "data/percolation",
        help="Output folder; relative paths are resolved from the repository root.")
    args = parser.parse_args(argv)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    # Supports direct execution from any working directory, without installation.
    sys.path.insert(0, str(ROOT))
    from src.environment import check_environment
    try:
        check_environment()
    except RuntimeError as error:
        parser.exit(2, f"Environment check failed:\n{error}\n")
    from src.percolation.experiment import run
    try:
        manifest = run(output, plain_csv=True)
    except (ValueError, FileNotFoundError) as error:
        parser.exit(2, f"Percolation stopped: {error}\n")
    print(f"Results saved to: {output.resolve()}")
    print("Main tables: summary.csv, runs.csv, queries.csv, query_outcomes.csv")
    return manifest


if __name__ == "__main__":
    main()
