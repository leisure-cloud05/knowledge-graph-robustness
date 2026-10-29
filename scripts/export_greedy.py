import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts.compare_sampling import (
    get_candidates,
    sample_greedy_nodes,
    open_raw,
)
from src.data_pipeline import (
    _parse_assertion_tsv_line,
    clean_edge,
)

# SHA-256 hashes of the frozen Greedy graph
EXPECTED_HASHES = {
    "nodes.csv": (
        "a5f54f9700969335b98e9fc8566aaa03a2487a99402e06cad4e5c87f1a197e27"
    ),
    "edges.csv": (
        "941b353e004522b8e7ea156b27b24878012dcd31b79911d5993e0ade3980e483"
    ),
}

OUTPUT_DIR = Path("results/greedy_reproduction")


def sha256(path):
    """Calculate SHA-256 for a file."""
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def export_greedy(raw_path, output_dir):
    """Reproduce the complete Greedy graph."""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Collect candidate nodes
    print("Collecting candidate nodes...", flush=True)
    candidates = get_candidates(raw_path)

    # Step 2: Reproduce Greedy node selection
    print("Selecting Greedy nodes...", flush=True)
    nodes = sample_greedy_nodes(
        raw_path,
        candidates,
        pool_size=5000,
        seed=2026,
    )

    # Step 3: Collect complete edges
    print("Collecting edges and relations...", flush=True)

    merged = {}

    with open_raw(raw_path) as f:
        for line in f:
            raw = _parse_assertion_tsv_line(line)
            edge = clean_edge(raw)

            if edge is None:
                continue

            u = edge["source"]
            v = edge["target"]

            if u not in nodes or v not in nodes:
                continue

            pair = (u, v)

            if pair not in merged:
                merged[pair] = {
                    "relations": set(),
                    "weight": edge["weight"],
                }

            merged[pair]["relations"].update(
                edge["relation"]
            )

            merged[pair]["weight"] = max(
                merged[pair]["weight"],
                edge["weight"],
            )

    # Step 4: Export nodes.csv
    nodes_path = output_dir / "nodes.csv"

    with nodes_path.open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["concept"])

        for node in sorted(nodes):
            writer.writerow([node])

    # Step 5: Export edges.csv
    edges_path = output_dir / "edges.csv"

    with edges_path.open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(
            ["source", "target", "relation", "weight"]
        )

        for (u, v), info in sorted(merged.items()):
            writer.writerow([
                u,
                v,
                json.dumps(sorted(info["relations"])),
                info["weight"],
            ])

    # Step 6: Verify graph size
    print("\n=== Graph Statistics ===")
    print("Nodes:", len(nodes))
    print("Edges:", len(merged))

    if len(nodes) != 1000 or len(merged) != 3417:
        raise SystemExit(
            "Graph size does not match the frozen Greedy graph."
        )

    # Step 7: Verify SHA-256
    print("\n=== SHA-256 Verification ===")

    all_match = True

    for filename, path in [
        ("nodes.csv", nodes_path),
        ("edges.csv", edges_path),
    ]:
        actual = sha256(path)
        expected = EXPECTED_HASHES[filename]
        match = actual == expected

        print(f"{filename}:")
        print(f"  Actual:   {actual}")
        print(f"  Expected: {expected}")
        print(f"  Match:    {match}")

        if not match:
            all_match = False

    if not all_match:
        raise SystemExit(
            "\nReproduction failed: SHA-256 mismatch."
        )

    print("\nGreedy reproduction verified successfully!")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw",
        type=Path,
        required=True,
        help="Path to the ConceptNet 5.7.0 assertions file",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for reproduced CSV files",
    )

    args = parser.parse_args()

    if not args.raw.is_file():
        parser.error(
            f"Raw ConceptNet file not found: {args.raw}"
        )

    export_greedy(args.raw, args.output)


if __name__ == "__main__":
    main()