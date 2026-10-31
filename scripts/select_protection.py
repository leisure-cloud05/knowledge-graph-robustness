"""Audit existing inputs and export static protection sets; no failure trials."""

import argparse
import csv
import hashlib
import json
import math
import platform
import time
from collections import Counter
from pathlib import Path

import networkx as nx

from src.percolation.core import load_graph, sample_queries
from src.edge_protection import (
    canonical_edge, ordered_edges, protection_budget,
    select_protected_edges, validate_betweenness,
)

ROOT = Path(__file__).resolve().parents[1]


def sha256(path, normalize_lf=False):
    content = path.read_bytes()
    if normalize_lf:
        content = content.replace(b"\r\n", b"\n")
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fraction", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=ROOT / "results/part_d/selection")
    args = parser.parse_args()
    data = ROOT / "data/processed"
    metadata = json.loads((data / "graph_metadata.json").read_text(encoding="utf-8"))
    hashes = {}
    for name in ("nodes.csv", "edges.csv"):
        hashes[name] = {
            "raw_sha256": sha256(data / name),
            "lf_sha256": sha256(data / name, True),
        }
        if hashes[name]["lf_sha256"] != metadata["sha256"][name]:
            raise ValueError(f"Frozen graph hash mismatch: {name}")
    graph = load_graph(data, verify=True)
    edges = ordered_edges(graph)
    budget = protection_budget(len(edges), args.fraction)
    if (len(graph), len(edges)) != (1000, 3417):
        raise ValueError("Unexpected frozen graph size")

    cache_path = ROOT / "results/part_b/edge_betweenness.csv"
    cache = {}
    with cache_path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            edge = canonical_edge(row["source"], row["target"])
            if edge in cache:
                raise ValueError("Duplicate cache edge")
            cache[edge] = float(row["betweenness"])
    cache = validate_betweenness(graph, cache)
    start = time.perf_counter()
    exact = nx.edge_betweenness_centrality(graph, normalized=True, weight=None)
    verification_seconds = time.perf_counter() - start
    max_error = max(abs(cache[canonical_edge(*e)] - s) for e, s in exact.items())
    if any(not math.isclose(cache[canonical_edge(*e)], s, rel_tol=1e-12, abs_tol=1e-15)
           for e, s in exact.items()):
        raise ValueError("Part B cache disagrees with exact unweighted betweenness")

    # Adopt the upstream formal workload, without generating a replacement.
    query_path = ROOT / "data/experiments/part_c/queries.csv"
    with query_path.open(encoding="utf-8-sig", newline="") as stream:
        queries = list(csv.DictReader(stream))
    pairs = [(r["source"], r["target"]) for r in queries]
    distances = [nx.shortest_path_length(graph, *pair) for pair in pairs]
    query_audit = {
        "path": query_path.relative_to(ROOT).as_posix(),
        "raw_sha256": sha256(query_path), "lf_sha256": sha256(query_path, True),
        "count": len(pairs), "unique_unordered_pairs": len({canonical_edge(*p) for p in pairs}),
        "actual_distance_counts": dict(Counter(distances)),
        "distance_labels_match": all(int(r["distance"]) == d for r, d in zip(queries, distances)),
        "matches_formal_generator_seed_5253001": pairs == [
            (r['source'], r['target']) for r in sample_queries(graph, seed=5253001)[0]],
        "formal_status": "adopted upstream Part C frozen queries",
    }
    args.output.mkdir(parents=True, exist_ok=True)
    selections = {}
    for strategy in ("random", "degree", "betweenness"):
        start = time.perf_counter()
        selected = select_protected_edges(
            graph, strategy, args.fraction, seed=args.seed,
            betweenness=cache if strategy == "betweenness" else None,
        )
        elapsed = time.perf_counter() - start
        if len(selected) != budget or len(set(selected)) != budget or not set(selected) <= set(edges):
            raise ValueError("Invalid selection")
        path = args.output / f"protected_{strategy}.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["source", "target"])
            writer.writerows(selected)
        selections[strategy] = {
            "count": len(selected), "selection_seconds": elapsed,
            "file": path.name, "sha256": sha256(path),
        }
    report = {
        "scope": "static edge selection only; no protection effectiveness conclusion",
        "python": platform.python_version(), "networkx": nx.__version__,
        "graph": {"nodes": len(graph), "edges": len(edges), "files": hashes},
        "fraction": args.fraction, "budget": budget,
        "rounding": "floor(m * Decimal(str(fraction)))", "random_seed": args.seed,
        "edge_order": "lexicographic canonical (min endpoint, max endpoint)",
        "ranking_tie_break": "canonical edge ascending",
        "betweenness_cache": {
            "path": cache_path.relative_to(ROOT).as_posix(), "raw_sha256": sha256(cache_path),
            "rows": len(cache), "normalized": True, "weight": None,
            "exact_verification_seconds": verification_seconds, "max_absolute_error": max_error,
        },
        "timing_scope": "one perf_counter measurement per selector; includes validation and sorting; excludes file I/O and cache loading/exact verification; not a benchmark",
        "selections": selections, "query_audit": query_audit,
    }
    (args.output / "selection_metadata.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
