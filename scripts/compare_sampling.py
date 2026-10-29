import argparse
import csv
import gzip
import json
import random
from pathlib import Path

import networkx as nx

from src.data_pipeline import (
    _parse_assertion_tsv_line,
    clean_edge,
)
from scripts.sample_candidate import SEEDS

DATA_DIR = Path("data/processed")


def load_frozen_graph():
    """Load the original Part A graph."""
    G = nx.Graph()

    with (DATA_DIR / "nodes.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            G.add_node(row["concept"])

    with (DATA_DIR / "edges.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            G.add_edge(row["source"], row["target"])

    return G


def open_raw(path):
    """Open plain or compressed ConceptNet assertions."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def get_candidates(path):
    """Find all valid English neighbors of the seeds."""
    seeds = set(SEEDS)
    candidates = set()

    with open_raw(path) as f:
        for line in f:
            raw = _parse_assertion_tsv_line(line)
            edge = clean_edge(raw)

            if edge is None:
                continue

            u, v = edge["source"], edge["target"]

            if u in seeds:
                candidates.add(v)
            if v in seeds:
                candidates.add(u)

    return sorted(candidates - seeds)


def sample_nodes(candidates, seed, max_nodes=1000):
    """Randomly select neighbors while retaining all seeds."""
    count = max_nodes - len(SEEDS)
    if len(candidates) < count:
        raise ValueError("Not enough candidate nodes")

    rng = random.Random(seed)
    return set(SEEDS) | set(rng.sample(candidates, count))


def build_random_graphs(path, samples):
    """Construct all sampled graphs in one file scan."""
    graphs = {}

    for seed, nodes in samples.items():
        G = nx.Graph()
        G.add_nodes_from(nodes)
        graphs[seed] = G

    with open_raw(path) as f:
        for line in f:
            raw = _parse_assertion_tsv_line(line)
            edge = clean_edge(raw)

            if edge is None:
                continue

            u, v = edge["source"], edge["target"]

            for seed, G in graphs.items():
                if u in G and v in G:
                    G.add_edge(u, v)

    return graphs


def graph_statistics(G):
    """Compute network structure metrics."""
    n = G.number_of_nodes()
    m = G.number_of_edges()

    degrees = dict(G.degree())
    components = list(nx.connected_components(G))

    lcc = max(map(len, components)) if components else 0
    bridges = sum(1 for _ in nx.bridges(G)) if m else 0

    # Count unordered pairs at distance 2 or 3.
    d2 = d3 = 0
    largest = max(components, key=len) if components else set()

    for source, distances in nx.all_pairs_shortest_path_length(
        G.subgraph(largest), cutoff=3
    ):
        for target, distance in distances.items():
            if source < target:
                if distance == 2:
                    d2 += 1
                elif distance == 3:
                    d3 += 1

    return {
        "nodes": n,
        "edges": m,
        "average_degree": round(2 * m / n, 4),
        "leaf_ratio": round(
            sum(d == 1 for d in degrees.values()) / n, 4
        ),
        "bridge_ratio": round(bridges / m, 4) if m else 0,
        "clustering": round(nx.average_clustering(G), 4),
        "lcc_ratio": round(lcc / n, 4),
        "components": len(components),
        "distance_2_pairs": d2,
        "distance_3_pairs": d3,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=5)
    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    # Original lexicographic sample
    original = load_frozen_graph()
    original_stats = graph_statistics(original)

    print("\n=== Original Lexicographic Sampling ===")
    print(json.dumps(original_stats, indent=2))

    if args.raw is None:
        print("\nRaw data unavailable. Random sampling skipped.")
        return

    if not args.raw.is_file():
        parser.error(f"Raw data not found: {args.raw}")

    # Generate reproducible random samples
    print("\nCollecting seed neighbors...")
    candidates = get_candidates(args.raw)
    print("Candidate nodes:", len(candidates))

    random_seeds = list(range(42, 42 + args.runs))
    samples = {
        seed: sample_nodes(candidates, seed)
        for seed in random_seeds
    }

    print("\nBuilding random graphs...")
    graphs = build_random_graphs(args.raw, samples)

    results = {
        "lexicographic": original_stats,
        "random": {},
    }

    for seed, G in graphs.items():
        stats = graph_statistics(G)
        results["random"][str(seed)] = stats

        print(f"\n=== Random Sampling: seed {seed} ===")
        print(json.dumps(stats, indent=2))

    output = Path("results/sampling_comparison.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print("\nResults saved to:", output)


if __name__ == "__main__":
    main()