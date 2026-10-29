import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


DATA_DIR = Path("data/processed")
OUT_DIR = Path("results/part_b")


def load_graph():
    """Load the frozen undirected, unweighted graph."""
    G = nx.Graph()

    with (DATA_DIR / "nodes.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        for row in csv.DictReader(f):
            G.add_node(row["concept"])

    with (DATA_DIR / "edges.csv").open(
        encoding="utf-8-sig", newline=""
    ) as f:
        for row in csv.DictReader(f):
            G.add_edge(row["source"], row["target"])

    assert G.number_of_nodes() == 1000
    assert G.number_of_edges() == 3417

    return G


def save_csv(filename, header, rows):
    with (OUT_DIR / filename).open(
        "w", encoding="utf-8", newline=""
    ) as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def analyze_graph(G):
    """Calculate fundamental structural metrics."""
    n = G.number_of_nodes()
    m = G.number_of_edges()

    degrees = dict(G.degree())
    components = sorted(
        nx.connected_components(G),
        key=len,
        reverse=True,
    )

    clustering = nx.clustering(G)
    avg_clustering = nx.average_clustering(G)

    stats = {
        "nodes": n,
        "edges": m,
        "average_degree": 2 * m / n,
        "maximum_degree": max(degrees.values()),
        "minimum_degree": min(degrees.values()),
        "density": nx.density(G),
        "average_clustering": avg_clustering,
        "connected_components": len(components),
        "largest_component_size": len(components[0]),
        "largest_component_ratio": len(components[0]) / n,
        "isolated_nodes": nx.number_of_isolates(G),
        "degree_one_nodes": sum(
            d == 1 for d in degrees.values()
        ),
        "bridge_edges": sum(1 for _ in nx.bridges(G)),
    }

    save_csv(
        "node_metrics.csv",
        ["node", "degree", "clustering"],
        [
            [node, degrees[node], clustering[node]]
            for node in sorted(G.nodes())
        ],
    )

    save_csv(
        "component_sizes.csv",
        ["component_id", "size"],
        [
            [i, len(component)]
            for i, component in enumerate(
                components, start=1
            )
        ],
    )

    return stats, degrees


def calculate_edge_betweenness(G):
    """Exact unweighted edge betweenness centrality."""
    centrality = nx.edge_betweenness_centrality(
        G, normalized=True, weight=None
    )

    ranked = sorted(
        centrality.items(),
        key=lambda item: (
            -item[1],
            min(item[0]),
            max(item[0]),
        ),
    )

    rows = [
        [
            min(u, v),
            max(u, v),
            score,
        ]
        for (u, v), score in ranked
    ]

    save_csv(
        "edge_betweenness.csv",
        ["source", "target", "betweenness"],
        rows,
    )

    return ranked


def plot_degree_distribution(degrees):
    counts = Counter(degrees.values())
    x = sorted(counts)
    y = [counts[k] for k in x]

    save_csv(
        "degree_distribution.csv",
        ["degree", "node_count"],
        zip(x, y),
    )

    plt.figure(figsize=(7, 5))
    plt.scatter(x, y, s=32)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("Degree (log scale)")
    plt.ylabel("Number of nodes (log scale)")
    plt.title("Degree Distribution")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(
        OUT_DIR / "degree_distribution.png",
        dpi=200,
    )
    plt.close()


def plot_network(G, degrees):
    """Visualize a focused high-degree neighborhood."""
    hub = max(
        G.nodes(),
        key=lambda node: (degrees[node], node),
    )

    neighbors = sorted(
        G.neighbors(hub),
        key=lambda node: (-degrees[node], node),
    )[:79]

    H = G.subgraph([hub] + neighbors).copy()

    pos = nx.spring_layout(
        H, seed=42, iterations=150
    )

    node_sizes = [
        70 + 10 * degrees[node]
        for node in H.nodes()
    ]

    colors = [
        "tomato" if node == hub else "steelblue"
        for node in H.nodes()
    ]

    plt.figure(figsize=(10, 8))
    nx.draw_networkx_edges(
        H, pos, alpha=0.18, width=0.7
    )
    nx.draw_networkx_nodes(
        H,
        pos,
        node_size=node_sizes,
        node_color=colors,
        alpha=0.85,
    )

    top_nodes = sorted(
        H.nodes(),
        key=lambda node: (-degrees[node], node)
    )[:6]

    labels = {
        node: node.split("/")[-1]
        for node in top_nodes
    }

    nx.draw_networkx_labels(
        H,
        pos,
        labels=labels,
        font_size=9,
        font_weight="bold",
    )

    plt.title(
    "Local Network Around the Highest-Degree Hub")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(
        OUT_DIR / "network_visualization.png",
        dpi=200,
    )
    plt.close()

    return hub


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading frozen Greedy graph...")
    G = load_graph()

    print("Calculating network metrics...")
    stats, degrees = analyze_graph(G)

    print("Calculating edge betweenness...")
    ranked = calculate_edge_betweenness(G)

    print("Generating figures...")
    plot_degree_distribution(degrees)
    hub = plot_network(G, degrees)

    stats["visualized_hub"] = hub

    with (OUT_DIR / "network_stats.json").open(
        "w", encoding="utf-8"
    ) as f:
        json.dump(stats, f, indent=2)

    print("\n=== Part B Network Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\n=== Top 5 Edges by Betweenness ===")
    for (u, v), score in ranked[:5]:
        print(f"{u} -- {v}: {score:.6f}")

    print("\nResults saved to:", OUT_DIR)


if __name__ == "__main__":
    main()