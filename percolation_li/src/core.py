"""Deterministic graph loading, query sampling, damage and evaluation."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

PART = Path(__file__).resolve().parents[1]
ROOT = PART.parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def load_graph(directory=None, verify=False):
    directory = Path(directory or ROOT / "data/processed")
    graph = nx.Graph()
    with (directory / "nodes.csv").open(encoding="utf-8-sig", newline="") as f:
        nodes = [r["concept"] for r in csv.DictReader(f)]
    if len(set(nodes)) != len(nodes):
        raise ValueError("Duplicate node identifiers")
    graph.add_nodes_from(sorted(nodes))
    edges = []
    with (directory / "edges.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            u, v = sorted((row["source"], row["target"]))
            if u == v or u not in graph or v not in graph:
                raise ValueError("Invalid edge endpoints")
            edges.append((u, v))
    if len(set(edges)) != len(edges):
        raise ValueError("Duplicate projected edges")
    graph.add_edges_from(sorted(edges))
    if verify:
        metadata = json.loads((directory / "graph_metadata.json").read_text())
        for filename, expected in metadata["sha256"].items():
            if digest(directory / filename) != expected:
                raise ValueError(f"Frozen input hash mismatch: {filename}")
        if (len(graph), graph.number_of_edges()) != (1000, 3417):
            raise ValueError("Unexpected authoritative graph size")
    return graph


def edge_order(graph):
    return sorted(tuple(sorted(e)) for e in graph.edges())


def candidate_pairs(graph):
    """Enumerate each eligible unordered pair once; never sample paths."""
    result = {2: [], 3: []}
    for u in sorted(graph):
        for v, distance in nx.single_source_shortest_path_length(graph, u, cutoff=3).items():
            if u < v and distance in result:
                result[distance].append((u, v))
    return {d: sorted(pairs) for d, pairs in result.items()}


def sample_queries(graph, quota=75, seed=5253001):
    pools = candidate_pairs(graph)
    rng = np.random.default_rng(seed)
    queries = []
    for distance in (2, 3):
        if len(pools[distance]) < quota:
            raise ValueError(f"Insufficient unique distance-{distance} pairs")
        indices = rng.choice(len(pools[distance]), size=quota, replace=False)
        for index in indices:
            u, v = pools[distance][int(index)]
            queries.append({"query_id": f"q{len(queries)+1:03}", "source": u,
                            "target": v, "distance": distance})
    reuse = Counter(x for row in queries for x in (row["source"], row["target"]))
    audit = {"candidate_counts": {str(d): len(pools[d]) for d in pools},
             "unique_pairs": len(queries), "distinct_endpoints": len(reuse),
             "maximum_endpoint_reuse": max(reuse.values()),
             "person_endpoint_queries": reuse.get("/c/en/person", 0),
             "endpoint_counts": dict(sorted(reuse.items(), key=lambda x: (-x[1], x[0])))}
    return queries, audit


def damage_graph(graph, edges, uniforms, q, protected_edges=()):
    """Apply original-edge draws; retain the original node set."""
    protected = {tuple(sorted(e)) for e in protected_edges}
    if not protected <= set(edges):
        raise ValueError("Unknown protected edge")
    values = np.asarray(uniforms)
    if not 0 <= q <= 1 or len(values) != len(edges):
        raise ValueError("Invalid probability or failure-draw length")
    if np.any((values < 0) | (values >= 1)):
        raise ValueError("Failure draws must lie in [0,1)")
    damaged = nx.Graph()
    damaged.add_nodes_from(graph.nodes())
    damaged.add_edges_from(e for e, value in zip(edges, values)
                           if e in protected or value >= q)
    return damaged


def evaluate(graph, queries):
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    labels = {node: i for i, component in enumerate(components) for node in component}
    cache, outcomes = {}, []
    for query in queries:
        u, v = query["source"], query["target"]
        if u not in cache:
            cache[u] = nx.single_source_shortest_path_length(graph, u, cutoff=3)
        distance = cache[u].get(v)
        state = ("success" if distance is not None else
                 "longer_route" if labels[u] == labels[v] else "disconnected")
        outcomes.append({**query, "state": state, "distance_within_cutoff": distance})
    counts = Counter(row["state"] for row in outcomes)
    count = len(queries)
    metrics = {"Q": counts["success"] / count,
               "longer_route": counts["longer_route"] / count,
               "disconnected": counts["disconnected"] / count,
               "S": len(components[0]) / len(graph),
               "small_components": 1 - len(components[0]) / len(graph),
               "isolates": nx.number_of_isolates(graph),
               "components": len(components)}
    for distance in (2, 3):
        group = [row for row in outcomes if row["distance"] == distance]
        metrics[f"Q{distance}"] = (sum(row["state"] == "success" for row in group) / len(group)
                                   if group else None)
    return metrics, outcomes

