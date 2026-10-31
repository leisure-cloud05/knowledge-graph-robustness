"""Part D integration tests; full formal scenarios remain the teammate's task."""
import copy
import csv
import subprocess
import sys

import networkx as nx
import numpy as np
import pytest

from src.percolation.core import ROOT
from src.protection_experiment import STRATEGIES, run_experiment, run_scenarios, write_csv


@pytest.fixture
def toy():
    graph = nx.path_graph(["a", "b", "c", "d"])
    edges = [("a", "b"), ("b", "c"), ("c", "d")]
    queries = [{"query_id": str(i), "source": u, "target": v, "distance": d}
               for i, (u, v, d) in enumerate([("a", "c", 2), ("a", "d", 3), ("b", "d", 2)])]
    uniforms = np.array([[.1, .9, .2], [.8, .8, .8]])
    protections = {"none": (), "random": (("a", "b"),), "degree": (("b", "c"),),
                   "betweenness": (("c", "d"),)}
    return graph, edges, queries, uniforms, protections


def test_paired_engine_has_manually_known_results_and_preserves_inputs(toy):
    original = copy.deepcopy(toy)
    rows, checks = run_scenarios(*toy, strategies=list(STRATEGIES), trials=[0, 1], q_values=[0., .5, 1.])
    assert len(rows) == len(checks) == 24
    cases = {(r["strategy"], r["trial"], r["q"]): r for r in rows}
    assert cases[("none", 0, .5)]["Q"] == 0
    assert cases[("none", 0, .5)]["S"] == .5
    assert cases[("random", 0, .5)]["Q"] == pytest.approx(1/3)
    assert cases[("random", 0, .5)]["S"] == .75
    assert cases[("betweenness", 0, .5)]["Q"] == pytest.approx(1/3)
    assert cases[("degree", 0, .5)]["Q"] == 0
    assert all(r["protected_edges_lost"] == 0 for r in rows)
    assert len({r["draw_row_sha256"] for r in rows if r["trial"] == 0}) == 1
    assert nx.utils.graphs_equal(toy[0], original[0])
    assert toy[1:3] == original[1:3] and toy[4] == original[4]
    assert np.array_equal(toy[3], original[3])


def test_control_is_validated_even_when_not_exported(toy):
    with pytest.raises(ValueError, match="does not reproduce Part C"):
        run_scenarios(*toy, strategies=["random"], trials=[0], q_values=[.5],
                      baseline={(0, .5): {m: 1. for m in ["Q", "Q2", "Q3", "S", "longer_route", "disconnected", "small_components"]}})


@pytest.mark.parametrize("overrides", [
    {"strategies": []}, {"strategies": ["none", "none"]}, {"strategies": ["unknown"]},
    {"trials": []}, {"trials": [-1]}, {"trials": [2]}, {"trials": [0, 0]},
    {"q_values": []}, {"q_values": [float("nan")]}, {"q_values": [1.1]}, {"q_values": [.5, .5]},
])
def test_invalid_subset_requests_rejected(toy, overrides):
    options = {"strategies": ["none"], "trials": [0], "q_values": [.5], **overrides}
    with pytest.raises(ValueError):
        run_scenarios(*toy, **options)


def test_selected_strategy_uses_same_draws_as_combined_run(toy):
    combined, _ = run_scenarios(*toy, strategies=list(STRATEGIES), trials=[0], q_values=[.5])
    separate, _ = run_scenarios(*toy, strategies=["betweenness"], trials=[0], q_values=[.5])
    expected = next(r for r in combined if r["strategy"] == "betweenness")
    assert {k: v for k, v in separate[0].items() if not k.endswith("_seconds")} == {
        k: v for k, v in expected.items() if not k.endswith("_seconds")}


def test_csv_schema_and_lf(tmp_path):
    path = tmp_path / "runs.csv"
    write_csv(path, [{"strategy": "none", "trial": 0, "q": .3, "Q": .5, "S": .9}])
    assert b"\r" not in path.read_bytes()
    assert list(csv.DictReader(path.open(encoding="utf-8")))[0]["strategy"] == "none"


def test_reject_existing_results_and_output_outside_part_d(tmp_path):
    with pytest.raises(ValueError, match="under results/part_d"):
        run_experiment(output=tmp_path)
    with pytest.raises(ValueError, match="not empty"):
        run_experiment(output=ROOT / "results/part_d/selection")


def test_cli_dispatches_subset_without_running_study(monkeypatch):
    import src.protection_experiment as experiment
    from scripts.protection import main
    received = {}
    monkeypatch.setattr(experiment, "run_experiment", lambda **kw: received.update(kw))
    main(["--stage", "pilot", "--strategies", "random", "--trials", "0", "2",
          "--q", "0.2", "0.4", "--output", "results/part_d/subset"])
    assert received == {"stage": "pilot", "strategies": ["random"], "trials": [0, 2],
                        "q_values": [.2, .4], "output": ROOT / "results/part_d/subset"}


def test_cli_help_from_another_directory(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "scripts/protection.py"), "--help"],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0 and "--stage" in result.stdout and "--trials" in result.stdout
