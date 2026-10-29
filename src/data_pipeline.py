"""Fetching and cleaning helpers for ConceptNet-style edge records.

The fetch helper is intentionally limited to one page for one seed concept;
this module contains no batch collection or CSV-writing workflow.
"""

from __future__ import annotations

import gzip
import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TypedDict

import networkx as nx
import requests


CONCEPTNET_QUERY_URL = "https://api.conceptnet.io/query"
REQUEST_TIMEOUT_SECONDS = 30


class ConceptNetFetchError(RuntimeError):
    """Raised when ConceptNet does not return a usable edge response."""


class CleanEdge(TypedDict):
    """Normalized edge representation used by the cleaning pipeline."""

    source: str
    target: str
    relation: list[str]
    weight: float


class GraphQualityReport(TypedDict):
    """Quality metrics for a sampled undirected ConceptNet graph."""

    node_count: int
    edge_count: int
    connected_component_count: int
    largest_component_ratio: float
    isolated_node_count: int
    distance_2_pair_count: int
    distance_3_pair_count: int
    distance_2_or_3_pair_count: int
    can_form_mixed_query_set: bool


_ENGLISH_CONCEPT_PATH = re.compile(
    r"^/c/en/(?P<concept>[^/\s?#]+)(?:/(?P<pos>[nvars]))?$"
)


def fetch_conceptnet_edges(
    seed_concept: str, *, limit: int = 100
) -> list[object]:
    """Fetch one page of raw edges for one English base concept path.

    ``seed_concept`` must have the form ``/c/en/<concept>``.  HTTP status is
    checked before JSON decoding so an error page (for example, HTTP 502) can
    never be mistaken for an API payload.  Request, HTTP, JSON, and payload
    errors raise :class:`ConceptNetFetchError`; only a successful response with
    an actual empty ``edges`` list is returned as zero edges.
    """

    normalized_seed = _normalize_english_concept_path(
        seed_concept, allow_pos_suffix=False
    )
    if normalized_seed is None:
        raise ValueError("seed_concept must be a base path like '/c/en/dog'")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")

    try:
        response = requests.get(
            CONCEPTNET_QUERY_URL,
            params={"node": normalized_seed, "offset": 0, "limit": limit},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        # This must happen before response.json(): HTTP error bodies may be
        # HTML or proxy-generated content rather than ConceptNet JSON.
        response.raise_for_status()
    except requests.RequestException as exc:
        status_code = (
            exc.response.status_code if exc.response is not None else None
        )
        detail = f"HTTP {status_code}" if status_code is not None else str(exc)
        raise ConceptNetFetchError(
            f"ConceptNet request failed for {normalized_seed}: {detail}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise ConceptNetFetchError(
            f"ConceptNet returned invalid JSON for {normalized_seed}"
        ) from exc

    if not isinstance(payload, Mapping) or not isinstance(payload.get("edges"), list):
        raise ConceptNetFetchError(
            f"ConceptNet response for {normalized_seed} has no valid 'edges' list"
        )
    return list(payload["edges"])


def _normalize_english_concept_path(
    value: object, *, allow_pos_suffix: bool
) -> str | None:
    """Validate an English ConceptNet path and return its base concept path.

    Base paths have exactly the form ``/c/en/<concept>``.  ConceptNet ``@id``
    values may additionally end in a known part-of-speech code (``n``, ``v``,
    ``a``, ``r``, or ``s``); callers may opt into stripping that suffix.
    """

    if not isinstance(value, str):
        return None
    match = _ENGLISH_CONCEPT_PATH.fullmatch(value)
    if match is None or (match.group("pos") and not allow_pos_suffix):
        return None
    return f'/c/en/{match.group("concept")}'


def _english_concept_id(node: object) -> str | None:
    """Return a strictly validated base identifier for an English node.

    ``term`` is authoritative when present and must already be a base concept
    path.  Only a missing ``term`` permits fallback to ``@id``, whose optional
    part-of-speech suffix is removed.
    """

    if not isinstance(node, Mapping):
        return None

    language = node.get("language")
    if language is not None and (
        not isinstance(language, str) or language.strip().lower() != "en"
    ):
        return None

    if node.get("term") is not None:
        return _normalize_english_concept_path(
            node.get("term"), allow_pos_suffix=False
        )
    return _normalize_english_concept_path(node.get("@id"), allow_pos_suffix=True)


def _relation_name(relation: object) -> str | None:
    """Extract a non-empty relation category from a ConceptNet relation."""

    if isinstance(relation, str):
        return relation.strip() or None
    if not isinstance(relation, Mapping):
        return None

    for field in ("@id", "label"):
        value = relation.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _weight(value: object) -> float | None:
    """Convert a finite, non-negative numeric weight to ``float``."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) and result >= 0 else None


def clean_edge(edge: object) -> CleanEdge | None:
    """Validate and normalize one ConceptNet-style edge.

    Invalid fields, non-English endpoints, and self-loops produce ``None``.
    Endpoints are ordered lexicographically so that a reversed edge represents
    the same undirected node pair.
    """

    if not isinstance(edge, Mapping):
        return None

    source = _english_concept_id(edge.get("start"))
    target = _english_concept_id(edge.get("end"))
    relation = _relation_name(edge.get("rel"))
    weight = _weight(edge.get("weight"))
    if source is None or target is None or relation is None or weight is None:
        return None
    if source == target:
        return None

    source, target = sorted((source, target))
    return {
        "source": source,
        "target": target,
        # A list is used consistently, even before duplicate-edge merging.
        "relation": [relation],
        "weight": weight,
    }


def clean_edges(edges: Iterable[object]) -> list[CleanEdge]:
    """Clean edges and deterministically merge duplicate undirected pairs.

    ``relation`` is stored as a sorted ``list[str]`` containing every distinct
    relation seen for the pair.  ``weight`` is the maximum weight seen for the
    pair.  These two fields are merged independently, so the result does not
    depend on input order.  Returned edges are also sorted by endpoint pair.
    """

    merged: dict[tuple[str, str], CleanEdge] = {}
    for raw_edge in edges:
        edge = clean_edge(raw_edge)
        if edge is None:
            continue

        pair = (edge["source"], edge["target"])
        previous = merged.get(pair)
        if previous is None:
            merged[pair] = edge
            continue

        # Duplicate merge rule: union and sort all relation categories, while
        # retaining the largest observed weight for the undirected node pair.
        previous["relation"] = sorted(
            set(previous["relation"]) | set(edge["relation"])
        )
        previous["weight"] = max(previous["weight"], edge["weight"])

    return [merged[pair] for pair in sorted(merged)]


def _parse_assertion_tsv_line(line: object) -> dict[str, object] | None:
    """Convert one official ConceptNet assertions TSV line to a raw edge.

    An assertion row has five tab-separated fields: assertion URI, relation,
    start concept, end concept, and JSON metadata.  Malformed rows are skipped;
    endpoint and weight validation remains the responsibility of the existing
    edge cleaner.
    """

    if not isinstance(line, str):
        return None
    fields = line.rstrip("\r\n").split("\t")
    if len(fields) != 5:
        return None

    assertion_uri, relation, start, end, metadata_json = fields
    if not assertion_uri or not relation or not start or not end or not metadata_json:
        return None
    try:
        metadata = json.loads(metadata_json)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(metadata, Mapping) or "weight" not in metadata:
        return None

    # Use @id-only nodes so the existing cleaner validates the ConceptNet
    # paths and, where applicable, normalizes part-of-speech suffixes.
    return {
        "start": {"@id": start},
        "end": {"@id": end},
        "rel": {"@id": relation},
        "weight": metadata["weight"],
    }


def clean_assertion_tsv_lines(lines: Iterable[str]) -> list[CleanEdge]:
    """Clean and merge an iterable of ConceptNet assertions TSV lines."""

    def parsed_edges() -> Iterable[dict[str, object]]:
        for line in lines:
            edge = _parse_assertion_tsv_line(line)
            if edge is not None:
                yield edge

    return clean_edges(parsed_edges())


def load_conceptnet_assertions_tsv(path: str | Path) -> list[CleanEdge]:
    """Stream a plain or gzip-compressed UTF-8 assertions TSV file."""

    source_path = Path(path)
    if source_path.suffix.lower() == ".gz":
        lines_context = gzip.open(source_path, mode="rt", encoding="utf-8")
    else:
        lines_context = source_path.open("r", encoding="utf-8")

    with lines_context as lines:
        return clean_assertion_tsv_lines(lines)


def sample_conceptnet_assertions_graph(
    path: str | Path,
    seed_concepts: Iterable[str],
    max_nodes: int = 1000,
) -> tuple[set[str], list[CleanEdge]]:
    """Build a bounded, deterministic graph sample in two file scans.

    Selection rule: normalize and retain every distinct seed, then fill the
    remaining node slots with the lexicographically smallest distinct English
    concepts directly adjacent to a seed.  Because selection depends only on
    normalized concept identifiers, not encounter order, permuting TSV rows
    cannot change the selected nodes.  The first scan stores candidate node
    identifiers only--never the full collection of English edges.

    The second scan yields only raw edges whose normalized endpoints are both
    selected.  Those edges are passed to ``clean_edges`` so the existing
    undirected ordering, relation union, and maximum-weight rules remain the
    single source of truth.
    """

    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes <= 0:
        raise ValueError("max_nodes must be a positive integer")

    seeds: set[str] = set()
    for seed in seed_concepts:
        normalized_seed = _normalize_english_concept_path(
            seed, allow_pos_suffix=True
        )
        if normalized_seed is None:
            raise ValueError(
                f"invalid English seed concept path: {seed!r}"
            )
        seeds.add(normalized_seed)
    if len(seeds) > max_nodes:
        raise ValueError("max_nodes cannot be smaller than the number of seeds")
    if not seeds:
        return set(), []

    source_path = Path(path)

    def open_lines():
        if source_path.suffix.lower() == ".gz":
            return gzip.open(source_path, mode="rt", encoding="utf-8")
        return source_path.open("r", encoding="utf-8")

    candidates: set[str] = set()
    with open_lines() as lines:
        for line in lines:
            raw_edge = _parse_assertion_tsv_line(line)
            normalized_edge = clean_edge(raw_edge)
            if normalized_edge is None:
                continue
            endpoints = {
                normalized_edge["source"],
                normalized_edge["target"],
            }
            if endpoints & seeds:
                candidates.update(endpoints - seeds)

    remaining_slots = max_nodes - len(seeds)
    selected_nodes = seeds | set(sorted(candidates)[:remaining_slots])

    def selected_raw_edges() -> Iterable[dict[str, object]]:
        with open_lines() as lines:
            for line in lines:
                raw_edge = _parse_assertion_tsv_line(line)
                normalized_edge = clean_edge(raw_edge)
                if normalized_edge is None:
                    continue
                if (
                    normalized_edge["source"] in selected_nodes
                    and normalized_edge["target"] in selected_nodes
                ):
                    yield raw_edge

    return selected_nodes, clean_edges(selected_raw_edges())


def analyze_sampled_graph_quality(
    nodes: Iterable[str],
    edges: Iterable[CleanEdge],
    *,
    min_distance_2_pairs: int = 75,
    min_distance_3_pairs: int = 75,
) -> GraphQualityReport:
    """Measure connectivity and short-path pair supply with NetworkX.

    All supplied nodes are added before any edge, so isolated sampled nodes are
    retained.  If largest components tie in size, the component whose sorted
    node tuple is lexicographically smallest is selected.  Path pairs are
    unordered and counted only when their shortest-path distance is exactly 2
    or exactly 3 within that deterministically selected component.  Query-set
    feasibility requires both independently configurable distance quotas.
    """

    for name, threshold in (
        ("min_distance_2_pairs", min_distance_2_pairs),
        ("min_distance_3_pairs", min_distance_3_pairs),
    ):
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 0:
            raise ValueError(f"{name} must be a non-negative integer")

    sampled_nodes = set(nodes)
    graph = nx.Graph()
    graph.add_nodes_from(sampled_nodes)

    for edge in edges:
        source = edge["source"]
        target = edge["target"]
        if source not in sampled_nodes or target not in sampled_nodes:
            raise ValueError("every edge endpoint must be present in nodes")
        graph.add_edge(
            source,
            target,
            relation=list(edge["relation"]),
            weight=edge["weight"],
        )

    components = list(nx.connected_components(graph))
    if components:
        largest_nodes = min(
            components,
            key=lambda component: (-len(component), tuple(sorted(component))),
        )
        largest_component_ratio = len(largest_nodes) / graph.number_of_nodes()
        largest_graph = graph.subgraph(largest_nodes)
    else:
        largest_component_ratio = 0.0
        largest_graph = graph.subgraph([])

    distance_2_pair_count = 0
    distance_3_pair_count = 0
    for source, distances in nx.all_pairs_shortest_path_length(
        largest_graph, cutoff=3
    ):
        for target, distance in distances.items():
            if source >= target:
                continue
            if distance == 2:
                distance_2_pair_count += 1
            elif distance == 3:
                distance_3_pair_count += 1

    short_path_pair_count = distance_2_pair_count + distance_3_pair_count
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "connected_component_count": len(components),
        "largest_component_ratio": largest_component_ratio,
        "isolated_node_count": nx.number_of_isolates(graph),
        "distance_2_pair_count": distance_2_pair_count,
        "distance_3_pair_count": distance_3_pair_count,
        "distance_2_or_3_pair_count": short_path_pair_count,
        "can_form_mixed_query_set": (
            distance_2_pair_count >= min_distance_2_pairs
            and distance_3_pair_count >= min_distance_3_pairs
        ),
    }
