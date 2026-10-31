"""Part D static-selection handoff and paired-run interface (no statistics)."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

from src.edge_protection import ordered_edges, protection_budget, select_protected_edges, validate_betweenness
from src.environment import check_environment
from src.percolation.core import ROOT, damage_graph, digest, evaluate, load_graph, write_json

STRATEGIES = ("none", "random", "degree", "betweenness")
METRICS = ("Q", "Q2", "Q3", "S", "longer_route", "disconnected", "small_components")
PROTOCOL = ROOT / "data/experiments/part_d/protocol.json"


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def input_hashes(protocol):
    return {name: digest(ROOT / name, text=not name.endswith(".npy"))
            for name in protocol["input_hashes"]}


def prepare_inputs():
    """Read and verify frozen inputs and all three static allocation lists."""
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if input_hashes(protocol) != protocol["input_hashes"]:
        raise ValueError("Protocol input hash mismatch; do not silently replace frozen inputs")
    graph = load_graph(verify=True)
    edges = ordered_edges(graph)
    directory = ROOT / protocol["part_c_inputs"]
    table = read_csv(directory / "edge_order.csv")
    if [(int(r["edge_id"]), r["source"], r["target"]) for r in table] != [
        (i, *edge) for i, edge in enumerate(edges)
    ]:
        raise ValueError("Saved edge order differs from the canonical original edge order")
    queries = read_csv(directory / "queries.csv")
    for row in queries:
        row["distance"] = int(row["distance"])
    pairs = [(r["source"], r["target"]) for r in queries]
    if (len(queries) != 150 or len({r["query_id"] for r in queries}) != 150
            or len(set(pairs)) != 150 or any(u >= v for u, v in pairs)
            or Counter(r["distance"] for r in queries) != {2: 75, 3: 75}
            or any(nx.shortest_path_length(graph, *pair) != r["distance"]
                   for pair, r in zip(pairs, queries))):
        raise ValueError("Invalid frozen query workload")
    uniforms = np.load(directory / "failure_uniforms.npy", allow_pickle=False)
    if (uniforms.shape != (protocol["runs"], len(edges))
            or not np.all(np.isfinite(uniforms)) or np.any((uniforms < 0) | (uniforms >= 1))):
        raise ValueError("Invalid saved failure matrix")
    # Check the readable copy without regenerating or replacing either input.
    draws = pd.read_csv(directory / "failure_draws.csv", float_precision="round_trip")
    if (not np.array_equal(draws["trial"], np.repeat(np.arange(len(uniforms)), len(edges)))
            or not np.array_equal(draws["edge_id"], np.tile(np.arange(len(edges)), len(uniforms)))
            or not np.array_equal(draws["uniform"], uniforms.ravel())):
        raise ValueError("Readable failure draws disagree with the binary matrix")

    cache_rows = read_csv(ROOT / "results/part_b/edge_betweenness.csv")
    cache = {(r["source"], r["target"]): float(r["betweenness"]) for r in cache_rows}
    if len(cache) != len(cache_rows):
        raise ValueError("Duplicate cache edges")
    cache = validate_betweenness(graph, cache)
    tick = time.perf_counter()
    exact = nx.edge_betweenness_centrality(graph, normalized=True, weight=None)
    if any(not math.isclose(cache[tuple(sorted(e))], score, rel_tol=1e-12, abs_tol=1e-15)
           for e, score in exact.items()):
        raise ValueError("Betweenness cache differs from exact original-graph scores")
    cache_verification_seconds = time.perf_counter() - tick
    protections = {"none": ()}
    budget = protection_budget(len(edges), protocol["fraction"])
    if budget != protocol["budget"]:
        raise ValueError("Protocol budget mismatch")
    for strategy in STRATEGIES[1:]:
        rows = read_csv(ROOT / protocol["selection_directory"] / f"protected_{strategy}.csv")
        saved = tuple((r["source"], r["target"]) for r in rows)
        expected = select_protected_edges(
            graph, strategy, protocol["fraction"], seed=protocol["protection_seed"],
            betweenness=cache if strategy == "betweenness" else None,
        )
        if saved != expected or len(saved) != budget or len(set(saved)) != budget:
            raise ValueError(f"Selection differs from the fixed protocol: {strategy}")
        protections[strategy] = saved
    baseline_rows = read_csv(ROOT / "results/part_c/runs.csv")
    baseline = {(int(r["trial"]), float(r["q"])): r for r in baseline_rows}
    expected_keys = {(trial, q) for trial in range(protocol["runs"]) for q in protocol["q_values"]}
    if len(baseline) != len(baseline_rows) or set(baseline) != expected_keys:
        raise ValueError("Part C baseline scenarios are incomplete or duplicated")
    return protocol, graph, edges, queries, uniforms, protections, baseline, cache_verification_seconds


def run_scenarios(graph, edges, queries, uniforms, protections, *, strategies, trials, q_values,
                  baseline=None):
    """Run selected scenarios with fixed allocations and original-edge draws.

    Also compute the unprotected control for validation if None is not exported.
    Returned checks concern implementation correctness, never strategy superiority.
    """
    if (not strategies or len(set(strategies)) != len(strategies)
            or any(s not in STRATEGIES or s not in protections for s in strategies)):
        raise ValueError("Unknown, repeated or empty strategy selection")
    if (not trials or len(set(trials)) != len(trials)
            or any(type(t) is not int or not 0 <= t < len(uniforms) for t in trials)):
        raise ValueError("Invalid trial IDs")
    if (not q_values or len(set(q_values)) != len(q_values)
            or any(not math.isfinite(q) or not 0 <= q <= 1 for q in q_values)):
        raise ValueError("Invalid q values")
    before = graph.copy()
    edge_set = set(edges)
    rows, checks = [], []
    for trial in sorted(trials):
        values = uniforms[trial]
        draw_hash = hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest()
        for q in sorted(q_values):
            potential = {e for e, value in zip(edges, values) if value < q}
            control = damage_graph(graph, edges, values, q)
            control_metrics, _ = evaluate(control, queries)
            if baseline is not None:
                reference = baseline[(trial, q)]
                if any(not math.isclose(control_metrics[m], float(reference[m]), abs_tol=1e-12,
                                        rel_tol=1e-12) for m in METRICS):
                    raise ValueError(f"None does not reproduce Part C: trial={trial}, q={q}")
            for strategy in strategies:
                protected = set(protections[strategy])
                tick = time.perf_counter()
                damaged = damage_graph(graph, edges, values, q, protected_edges=protected)
                damage_seconds = time.perf_counter() - tick
                tick = time.perf_counter()
                metrics, _ = evaluate(damaged, queries)
                evaluation_seconds = time.perf_counter() - tick
                remaining = set(ordered_edges(damaged))
                removed = edge_set - remaining
                case = {
                    "strategy": strategy, "trial": trial, "q": q,
                    "shared_deletion_predicate": removed == potential - protected,
                    "protected_edges_retained": protected <= remaining,
                    "original_nodes_retained": set(damaged) == set(graph),
                    "no_added_edges": remaining <= edge_set,
                    "not_worse_than_paired_none": all(metrics[m] + 1e-12 >= control_metrics[m]
                                                       for m in ("Q", "S")),
                    "zero_failure_endpoint": q != 0 or (metrics["Q"] == 1 and metrics["S"] == 1),
                    "outcomes_partition": math.isclose(metrics["Q"] + metrics["longer_route"]
                                                       + metrics["disconnected"], 1),
                }
                if not all(value for key, value in case.items() if key not in {"strategy", "trial", "q"}):
                    raise AssertionError(case)
                checks.append(case)
                rows.append({
                    "strategy": strategy, "trial": trial, "q": q,
                    "protected_count": len(protected), "potential_failure_count": len(potential),
                    "removed_edges": len(removed), "protected_edges_lost": len(protected - remaining),
                    "nodes": len(damaged), "edges": len(remaining),
                    "draw_row_sha256": draw_hash,
                    "damage_seconds": damage_seconds, "evaluation_seconds": evaluation_seconds,
                    **metrics,
                })
    if not nx.utils.graphs_equal(graph, before):
        raise AssertionError("Original graph changed")
    if len(rows) != len(strategies) * len(trials) * len(q_values):
        raise AssertionError("Scenario count mismatch")
    return rows, checks


def run_experiment(*, stage="acceptance", strategies=None, trials=None, q_values=None, output=None):
    """Default is an eight-row acceptance check; pilot/full require explicit stage."""
    if stage not in {"acceptance", "pilot", "full"}:
        raise ValueError("Unknown stage")
    output = Path(output or ROOT / f"results/part_d/{stage}").resolve()
    if not output.is_relative_to((ROOT / "results/part_d").resolve()):
        raise ValueError("Output must be under results/part_d")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output is not empty; choose a new directory to preserve previous runs")
    started = time.perf_counter()
    environment = check_environment()
    print("Checking frozen inputs, exact scores and all protection lists...", flush=True)
    protocol, graph, edges, queries, uniforms, protections, baseline, cache_seconds = prepare_inputs()
    strategies = list(STRATEGIES if strategies is None else strategies)
    trials = list((range(protocol["runs"]) if stage == "full" else
                   range(5) if stage == "pilot" else [0]) if trials is None else trials)
    q_values = list((protocol["q_values"] if stage == "full" else
                     [.2, .3, .4] if stage == "pilot" else [0., .3]) if q_values is None else q_values)
    if any(q not in protocol["q_values"] for q in q_values):
        raise ValueError("q must be on the frozen protocol grid")
    protocol_hash = digest(PROTOCOL, text=True)
    print(f"Running {len(strategies) * len(trials) * len(q_values)} {stage} scenarios...", flush=True)
    rows, checks = run_scenarios(
        graph, edges, queries, uniforms, protections, strategies=strategies, trials=trials,
        q_values=q_values, baseline=baseline,
    )
    if input_hashes(protocol) != protocol["input_hashes"] or digest(PROTOCOL, text=True) != protocol_hash:
        raise AssertionError("An input or the protocol changed during execution")
    full = (set(strategies) == set(STRATEGIES) and set(trials) == set(range(protocol["runs"]))
            and set(q_values) == set(protocol["q_values"]))
    validation = {
        "passed": True, "stage": stage, "scenario_count": len(rows),
        "expected_scenario_count": len(strategies) * len(trials) * len(q_values),
        "full_design_executed": full, "all_frozen_inputs_unchanged": True,
        "all_selection_lists_match_algorithms": True, "budget_per_protected_strategy": protocol["budget"],
        "paired_none_matches_part_c": True, "original_graph_unchanged": True,
        "cases": checks,
    }
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        head = None
    sources = [Path(__file__), ROOT / "src/edge_protection.py", ROOT / "src/environment.py",
               ROOT / "src/percolation/core.py", ROOT / "scripts/protection.py"]
    manifest = {
        "status": "completed", "stage": stage, "full_design_executed": full,
        "purpose": "interface acceptance only" if stage == "acceptance" else "paired experiment",
        "protocol": PROTOCOL.relative_to(ROOT).as_posix(), "protocol_sha256": protocol_hash,
        "protocol_settings": protocol, "strategies": strategies, "trials": sorted(trials),
        "q_values": sorted(q_values), "scenario_count": len(rows),
        "environment": environment, "platform": platform.platform(), "git_head": head,
        "source_hashes": {p.relative_to(ROOT).as_posix(): digest(p, text=True) for p in sources},
        "requirements_sha256": digest(ROOT / "requirements.txt", text=True),
        "text_hash_policy": "CRLF normalized to LF; binary files unchanged",
        "timing_scope": "per-row damage/evaluation wall time; excludes validation control and selection audit",
        "exact_cache_verification_seconds": cache_seconds,
        "selection_timing": "see results/part_d/selection/selection_metadata.json; fixed lists reused",
        "total_seconds": time.perf_counter() - started,
        "interpretation": "correctness checks do not establish protection effectiveness or superiority",
    }
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "runs.csv", rows)
    manifest["runs_sha256"] = digest(output / "runs.csv", text=True)
    write_json(output / "validation.json", validation)
    write_json(output / "manifest.json", manifest)
    print(f"Completed: {len(rows)} scenarios; validation passed. {output}", flush=True)
    return manifest
