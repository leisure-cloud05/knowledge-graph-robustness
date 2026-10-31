"""Static protection selection on undirected, unweighted string-labelled graphs."""

import math
import random
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, ROUND_FLOOR

import networkx as nx

Edge = tuple[str, str]


def canonical_edge(u: str, v: str) -> Edge:
    return (min(u, v), max(u, v))


def ordered_edges(graph: nx.Graph) -> list[Edge]:
    """Validate the supported graph contract and return canonical sorted edges."""
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("Expected an undirected simple graph")
    if any(not isinstance(node, str) for node in graph):
        raise ValueError("Node identifiers must be strings")
    if nx.number_of_selfloops(graph):
        raise ValueError("Self-loops are not supported")
    return sorted(canonical_edge(u, v) for u, v in graph.edges())


def protection_budget(edge_count: int, fraction: float = 0.05) -> int:
    """floor(m * fraction), using decimal text to avoid binary rounding surprises."""
    if isinstance(edge_count, bool) or not isinstance(edge_count, int) or edge_count < 0:
        raise ValueError("edge_count must be a non-negative integer")
    try:
        value = Decimal(str(fraction))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("fraction must be finite and between 0 and 1") from exc
    if not value.is_finite() or not 0 <= value <= 1:
        raise ValueError("fraction must be finite and between 0 and 1")
    return int((edge_count * value).to_integral_value(rounding=ROUND_FLOOR))


def validate_betweenness(graph: nx.Graph, scores: Mapping[Edge, float]) -> dict[Edge, float]:
    """Check full edge coverage, orientation duplicates, and normalized score range.

    This checks shape only; the caller must establish scores' topology/provenance.
    """
    expected = set(ordered_edges(graph))
    normalized = {}
    for (u, v), score in scores.items():
        edge = canonical_edge(u, v)
        if edge in normalized:
            raise ValueError("Duplicate undirected betweenness edge")
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("Expected finite normalized betweenness in [0, 1]")
        normalized[edge] = float(score)
    if set(normalized) != expected:
        raise ValueError("Betweenness must cover exactly the original graph edges")
    return normalized


def select_protected_edges(
    graph: nx.Graph,
    strategy: str,
    fraction: float = 0.05,
    *,
    seed: int = 2026,
    betweenness: Mapping[Edge, float] | None = None,
) -> tuple[Edge, ...]:
    """Return unique canonical edges, sorted lexicographically (not by rank).

    Strategies: random, degree, betweenness. Scores use the original graph,
    ignoring edge weights. Precomputed betweenness must be exact, normalized,
    unweighted scores for this graph. Without a cache, calculate them on a
    canonical copy to make traversal independent of insertion order.
    The graph and global random state are never modified.
    """
    edges = ordered_edges(graph)
    count = protection_budget(len(edges), fraction)
    if strategy not in {"random", "degree", "betweenness"}:
        raise ValueError("strategy must be random, degree, or betweenness")
    if strategy == "random":
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")
        chosen = random.Random(seed).sample(edges, count)
    elif strategy == "degree":
        degrees = dict(graph.degree())
        chosen = sorted(edges, key=lambda e: (-(degrees[e[0]] + degrees[e[1]]), e))[:count]
    else:
        if betweenness is None:
            canonical = nx.Graph()
            canonical.add_nodes_from(sorted(graph))
            canonical.add_edges_from(edges)
            betweenness = nx.edge_betweenness_centrality(
                canonical, normalized=True, weight=None
            )
        scores = validate_betweenness(graph, betweenness)
        chosen = sorted(edges, key=lambda e: (-scores[e], e))[:count]
    return tuple(sorted(chosen))
