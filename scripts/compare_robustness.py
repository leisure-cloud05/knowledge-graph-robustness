import csv
import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("results/robustness_comparison")

Q_VALUES = [0, 0.1, 0.2, 0.3, 0.4, 0.5]
RUNS = 30
SEED = 2026


def load_graph(nodes_file, edges_file):
    """Load a frozen undirected graph."""
    G = nx.Graph()

    with open(nodes_file, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            G.add_node(row["concept"])

    with open(edges_file, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            G.add_edge(row["source"], row["target"])

    return G


def make_queries(G, seed=SEED):
    """Freeze 75 distance-2 and 75 distance-3 queries."""
    largest = max(nx.connected_components(G), key=len)
    H = G.subgraph(largest)

    pairs = {2: [], 3: []}

    for u, lengths in nx.all_pairs_shortest_path_length(
        H, cutoff=3
    ):
        for v, d in lengths.items():
            if u < v and d in pairs:
                pairs[d].append((u, v))

    if len(pairs[2]) < 75 or len(pairs[3]) < 75:
        raise ValueError("Not enough query pairs")

    rng = random.Random(seed)

    queries = (
        rng.sample(sorted(pairs[2]), 75)
        + rng.sample(sorted(pairs[3]), 75)
    )

    return queries


def damage_graph(G, q, seed):
    """Independently remove each edge with probability q."""
    rng = random.Random(seed)

    H = G.copy()

    removed = [
        (u, v)
        for u, v in sorted(G.edges())
        if rng.random() < q
    ]

    H.remove_edges_from(removed)
    return H


def evaluate(G, queries):
    """Calculate Q(q) and S(q)."""

    # Query success within 3 hops
    successes = 0
    cache = {}

    for u, v in queries:
        if u not in cache:
            cache[u] = nx.single_source_shortest_path_length(
                G, u, cutoff=3
            )

        if v in cache[u]:
            successes += 1

    Q = successes / len(queries)

    # Largest connected component ratio
    lcc = max(len(c) for c in nx.connected_components(G))
    S = lcc / G.number_of_nodes()

    return Q, S


def run_experiment(G, queries, name):
    """Run repeated random edge failures."""
    results = []

    for q in Q_VALUES:
        q_scores = []
        s_scores = []

        for trial in range(RUNS):
            trial_seed = SEED + trial

            H = damage_graph(G, q, trial_seed)
            Q, S = evaluate(H, queries)

            q_scores.append(Q)
            s_scores.append(S)

        result = {
            "network": name,
            "q": q,
            "Q_mean": float(np.mean(q_scores)),
            "Q_std": float(np.std(q_scores, ddof=1)),
            "S_mean": float(np.mean(s_scores)),
            "S_std": float(np.std(s_scores, ddof=1)),
        }

        results.append(result)

        print(
            f"{name:15s} q={q:.1f} "
            f"Q={result['Q_mean']:.3f} "
            f"S={result['S_mean']:.3f}"
        )

    return results


def plot_results(results, metric, filename):
    """Plot mean and standard deviation bands."""
    plt.figure(figsize=(8, 5))

    for name in ["Lexicographic", "Greedy"]:
        rows = [r for r in results if r["network"] == name]

        x = np.array([r["q"] for r in rows])
        mean = np.array([r[f"{metric}_mean"] for r in rows])
        std = np.array([r[f"{metric}_std"] for r in rows])

        plt.plot(x, mean, marker="o", label=name)
        plt.fill_between(
            x,
            np.maximum(mean - std, 0),
            np.minimum(mean + std, 1),
            alpha=0.15,
        )

    plt.xlabel("Edge failure probability (q)")
    plt.ylabel(metric)
    plt.title(f"{metric} under Random Edge Failures")
    plt.ylim(0, 1.05)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / filename, dpi=200)
    plt.close()


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load both graphs
    lex = load_graph(
        DATA_DIR / "nodes.csv",
        DATA_DIR / "edges.csv",
    )

    greedy = load_graph(
        DATA_DIR / "candidate_greedy_nodes.csv",
        DATA_DIR / "candidate_greedy_edges.csv",
    )

    networks = {
        "Lexicographic": lex,
        "Greedy": greedy,
    }

    all_results = []

    for name, G in networks.items():
        print(f"\n=== {name} ===")
        print("Nodes:", G.number_of_nodes())
        print("Edges:", G.number_of_edges())

        queries = make_queries(G)

        # Save fixed queries for reproducibility
        query_path = OUTPUT_DIR / f"queries_{name.lower()}.csv"

        with query_path.open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["source", "target", "distance"])

            for i, (u, v) in enumerate(queries):
                writer.writerow([u, v, 2 if i < 75 else 3])

        results = run_experiment(G, queries, name)
        all_results.extend(results)

    # Save raw summary results
    with (OUTPUT_DIR / "results.csv").open(
        "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=all_results[0].keys()
        )
        writer.writeheader()
        writer.writerows(all_results)

    with (OUTPUT_DIR / "results.json").open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(all_results, f, indent=2)

    # Plot both metrics
    plot_results(
        all_results, "Q", "query_success.png"
    )
    plot_results(
        all_results, "S", "lcc_ratio.png"
    )

    print("\nResults saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()