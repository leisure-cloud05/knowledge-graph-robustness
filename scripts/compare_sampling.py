import argparse
import csv
import gzip
import heapq
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
OUTPUT = Path("results/sampling_comparison.json")
MAX_NODES = 1000


def load_frozen_graph():
    """Load the original Part A graph."""
    G = nx.Graph()

    with (DATA_DIR / "nodes.csv").open(
        encoding="utf-8-sig"
    ) as f:
        for row in csv.DictReader(f):
            G.add_node(row["concept"])

    with (DATA_DIR / "edges.csv").open(
        encoding="utf-8-sig"
    ) as f:
        for row in csv.DictReader(f):
            G.add_edge(row["source"], row["target"])

    return G


def open_raw(path):
    """Open the original ConceptNet file."""
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open("r", encoding="utf-8")


def get_candidates(path):
    """Collect all valid English neighbors of the seeds."""
    seeds = set(SEEDS)
    candidates = set()

    with open_raw(path) as f:
        for line in f:
            edge = clean_edge(_parse_assertion_tsv_line(line))

            if edge is None:
                continue

            u, v = edge["source"], edge["target"]

            if u in seeds:
                candidates.add(v)
            if v in seeds:
                candidates.add(u)

    return sorted(candidates - seeds)


def sample_random_nodes(candidates, seed):
    """Randomly sample nodes while keeping all seeds."""
    count = MAX_NODES - len(SEEDS)

    if len(candidates) < count:
        raise ValueError("Not enough candidate nodes")

    rng = random.Random(seed)

    return set(SEEDS) | set(
        rng.sample(candidates, count)
    )


def sample_greedy_nodes(
    path, candidates, pool_size=5000, seed=2026
):
    """
    Greedy sampling:
    prefer nodes with more connections to selected nodes.
    """
    seeds = set(SEEDS)
    count = MAX_NODES - len(seeds)

    if len(candidates) < count:
        raise ValueError("Not enough candidate nodes")

    rng = random.Random(seed)
    pool = set(
        rng.sample(
            candidates,
            min(pool_size, len(candidates))
        )
    )

    allowed = pool | seeds
    neighbors = {node: set() for node in allowed}

    # Build adjacency in the candidate pool
    with open_raw(path) as f:
        for line in f:
            edge = clean_edge(_parse_assertion_tsv_line(line))

            if edge is None:
                continue

            u, v = edge["source"], edge["target"]

            if u in allowed and v in allowed:
                neighbors[u].add(v)
                neighbors[v].add(u)

    selected = set(seeds)

    # Initial scores: connections to seed nodes
    scores = {
        node: len(neighbors[node] & seeds)
        for node in pool
    }

    heap = [
        (-score, node)
        for node, score in scores.items()
    ]
    heapq.heapify(heap)

    # Greedily select nodes with the highest score
    while len(selected) < MAX_NODES:
        if not heap:
            raise ValueError("Candidate pool exhausted")

        neg_score, node = heapq.heappop(heap)

        if node in selected:
            continue

        if -neg_score != scores[node]:
            continue

        selected.add(node)

        for neighbor in neighbors[node]:
            if neighbor in scores and neighbor not in selected:
                scores[neighbor] += 1
                heapq.heappush(
                    heap,
                    (-scores[neighbor], neighbor)
                )

    return selected


def build_sampled_graphs(path, samples):
    """Build all sampled graphs using one file scan."""
    graphs = {}

    for name, nodes in samples.items():
        G = nx.Graph()
        G.add_nodes_from(nodes)
        graphs[name] = G

    with open_raw(path) as f:
        for line in f:
            edge = clean_edge(_parse_assertion_tsv_line(line))

            if edge is None:
                continue

            u, v = edge["source"], edge["target"]

            for G in graphs.values():
                if u in G and v in G:
                    G.add_edge(u, v)

    return graphs


def graph_statistics(G):
    """Calculate network statistics."""
    n = G.number_of_nodes()
    m = G.number_of_edges()

    if n == 0:
        raise ValueError("Graph is empty")

    degrees = dict(G.degree())
    components = list(nx.connected_components(G))

    largest = max(components, key=len)
    lcc = G.subgraph(largest)

    bridges = sum(1 for _ in nx.bridges(G))

    d2 = 0
    d3 = 0

    for source, distances in nx.all_pairs_shortest_path_length(
        lcc, cutoff=3
    ):
        for target, distance in distances.items():
            if source >= target:
                continue

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
        "bridge_ratio": round(
            bridges / m, 4
        ) if m else 0,
        "clustering": round(
            nx.average_clustering(G), 4
        ),
        "lcc_ratio": round(len(largest) / n, 4),
        "components": len(components),
        "distance_2_pairs": d2,
        "distance_3_pairs": d3,
        "query_feasible": d2 >= 75 and d3 >= 75,
        "max_degree": max(degrees.values()),
        "leaf_count": sum(
            d == 1 for d in degrees.values()
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--raw",
        type=Path,
        default=None,
        help="Path to original ConceptNet assertions file",
    )

    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of random sampling runs",
    )

    parser.add_argument(
        "--pool-size",
        type=int,
        default=5000,
        help="Candidate pool size for greedy sampling",
    )

    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    if args.pool_size < MAX_NODES - len(SEEDS):
        parser.error("--pool-size is too small")

    # Original Part A graph
    original = load_frozen_graph()
    original_stats = graph_statistics(original)

    print("\n=== Lexicographic Sampling ===")
    print(json.dumps(original_stats, indent=2))

    if args.raw is None:
        print("\nRaw data unavailable. Comparison skipped.")
        return

    if not args.raw.is_file():
        parser.error(f"Raw dataset not found: {args.raw}")

    # Collect candidates
    print("\nCollecting seed neighbors...")
    candidates = get_candidates(args.raw)
    print("Candidate count:", len(candidates))

    # Random sampling
    samples = {}

    for seed in range(42, 42 + args.runs):
        samples[f"random_{seed}"] = sample_random_nodes(
            candidates, seed
        )

    # Greedy sampling
    print("\nSelecting greedy sample...")
    samples["greedy"] = sample_greedy_nodes(
        args.raw,
        candidates,
        pool_size=args.pool_size,
        seed=2026,
    )

    # Build networks
    print("\nBuilding sampled graphs...")
    graphs = build_sampled_graphs(args.raw, samples)

    results = {
        "lexicographic": original_stats,
        "random": {},
        "greedy": {},
    }

    for name, G in graphs.items():
        print(f"\n=== {name} ===")

        stats = graph_statistics(G)
        print(json.dumps(stats, indent=2))

        if name == "greedy":
            results["greedy"] = stats
        else:
            results["random"][name] = stats

    # Save comparison
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT.write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    print("\nResults saved to:", OUTPUT)


if __name__ == "__main__":
    main()