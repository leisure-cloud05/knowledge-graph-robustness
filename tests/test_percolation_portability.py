"""Cross-platform text and public damage interface regression checks."""
import hashlib
import json

import networkx as nx
import numpy as np
import pandas as pd
import pytest

from src.percolation.core import ROOT, damage_graph, digest, edge_order, load_graph, write_json
from src.percolation.experiment import freeze_csv


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_frozen_graph_verification_accepts_platform_line_endings(tmp_path, newline):
    for name in ["nodes.csv", "edges.csv", "graph_metadata.json"]:
        data = (ROOT / "data/processed" / name).read_bytes().replace(b"\r\n", b"\n")
        (tmp_path / name).write_bytes(data.replace(b"\n", newline))
    graph = load_graph(tmp_path, verify=True)
    assert (len(graph), graph.number_of_edges()) == (1000, 3417)
    with (tmp_path / "edges.csv").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_graph(tmp_path, verify=True)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_frozen_csv_fields_survive_platform_line_endings(tmp_path, newline):
    frame = pd.DataFrame({"query_id": ["q001"], "source": ["a"], "target": ["b"], "distance": [2]})
    path = tmp_path / "queries.csv"
    path.write_bytes(frame.to_csv(index=False, lineterminator="\n").encode().replace(b"\n", newline))
    before = path.read_bytes()
    freeze_csv(frame, path)
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="Frozen input differs"):
        freeze_csv(frame.assign(target="c"), path)
    assert path.read_bytes() == before


def test_outputs_are_utf8_lf_and_binary_digest_unchanged(tmp_path):
    path = tmp_path / "metadata.json"
    write_json(path, {"note": "中文"})
    assert b"\r" not in path.read_bytes()
    assert json.loads(path.read_text(encoding="utf-8"))["note"] == "中文"
    binary = tmp_path / "matrix.npy"
    binary.write_bytes(b"\x00\r\n\xff")
    assert digest(binary) == hashlib.sha256(binary.read_bytes()).hexdigest()


def test_saved_uniforms_compare_without_csv_float_parser_rounding(tmp_path):
    frame = pd.DataFrame({"uniform": [0.000001234567890123456, .12345678901234567]})
    path = tmp_path / "draws.csv"
    freeze_csv(frame, path)
    freeze_csv(frame, path)


@pytest.mark.parametrize("draws", [[np.nan, .2], [np.inf, .2], [-.1, .2], [1., .2],
                                  [[.1], [.2]], .1, [.1], ["bad", .1]])
def test_invalid_draw_values_and_dimensions(draws):
    graph = nx.path_graph(3)
    with pytest.raises(ValueError):
        damage_graph(graph, edge_order(graph), draws, .5)


@pytest.mark.parametrize("edges", [[(0, 1)], [(0, 1), (0, 1)], [(1, 0), (1, 2)],
                                  [(1, 2), (0, 1)], [(0, 1), (1, 99)]])
def test_wrong_original_edge_orders_rejected(edges):
    graph = nx.path_graph(3)
    with pytest.raises(ValueError, match="canonical original edge order"):
        damage_graph(graph, edges, [.1] * len(edges), .5)


@pytest.mark.parametrize("q", [np.nan, np.inf, -.1, 1.1, [.5]])
def test_invalid_q_rejected(q):
    graph = nx.path_graph(3)
    with pytest.raises(ValueError):
        damage_graph(graph, edge_order(graph), [.1, .2], q)


def test_held_edges_and_original_nodes_are_preserved():
    graph = nx.path_graph(4)
    graph.add_node(9)
    edges = edge_order(graph)
    original = graph.copy()
    damaged = damage_graph(graph, edges, [0., .2, .9], 1., protected_edges={(1, 0)})
    assert set(damaged) == set(graph)
    assert set(damaged.edges()) == {(0, 1)}
    assert nx.utils.graphs_equal(graph, original)


def test_runtime_does_not_query_notebook_dependencies(monkeypatch):
    import src.environment as environment
    pins = environment.read_requirements(ROOT / "requirements.txt")
    requested = []
    def installed(name):
        requested.append(name)
        if name in {"nbformat", "nbclient", "ipykernel"}:
            raise environment.PackageNotFoundError(name)
        return pins[name]
    monkeypatch.setattr(environment, "version", installed)
    assert environment.check_environment()["passed"]
    assert not set(requested) & {"nbformat", "nbclient", "ipykernel"}
    with pytest.raises(RuntimeError, match="requirements.txt"):
        environment.check_environment("notebook")
