"""Unified Part D entry; defaults to minimal acceptance, not the full study."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["acceptance", "pilot", "full"], default="acceptance")
    parser.add_argument("--strategies", nargs="+", choices=["none", "random", "degree", "betweenness"])
    parser.add_argument("--trials", nargs="+", type=int, help="zero-based saved trial IDs, 0 to 29")
    parser.add_argument("--q", nargs="+", type=float, dest="q_values")
    parser.add_argument("--output", type=Path, help="new directory under results/part_d")
    args = parser.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    from src.protection_experiment import run_experiment
    output = args.output
    if output is not None and not output.is_absolute():
        output = ROOT / output
    try:
        return run_experiment(stage=args.stage, strategies=args.strategies, trials=args.trials,
                              q_values=args.q_values, output=output)
    except (ValueError, RuntimeError, AssertionError, FileNotFoundError) as exc:
        parser.exit(2, f"Part D stopped: {exc}\n")


if __name__ == "__main__":
    main()
