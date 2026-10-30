"""Independent random edge-failure study; writes only within this section."""
import time
import platform
from importlib.metadata import version

import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import t

from .check_environment import check_environment
from .core import PART, ROOT, digest, write_json, load_graph, edge_order, sample_queries, damage_graph, evaluate
from .theory import export_degrees, configuration_curve, reference_threshold

OUTPUT = PART / "outputs"
METRICS = ["Q", "Q2", "Q3", "S", "longer_route", "disconnected", "small_components"]
SEEDS = {"queries":5253001,"failures":5253002}
RUNS = 30
Q_VALUES = np.round(np.linspace(0,1,11),2)


def mean_interval(values):
    values = np.asarray(values,dtype=float)
    mean = float(values.mean())
    sd = float(values.std(ddof=1)) if len(values)>1 else 0.
    half = float(t.ppf(.975,len(values)-1)*sd/np.sqrt(len(values))) if len(values)>1 else 0.
    return {"mean":mean,"sd":sd,"ci_low":mean-half,"ci_high":mean+half,"n":len(values)}


def summarize(frame, keys, metrics):
    rows = []
    for labels, group in frame.groupby(keys,sort=False):
        if not isinstance(labels,tuple): labels=(labels,)
        row = dict(zip(keys,labels))
        for metric in metrics:
            row.update({f"{metric}_{k}":v for k,v in mean_interval(group[metric]).items()})
        rows.append(row)
    return pd.DataFrame(rows)


def validate_runs(frame,queries,graph):
    checks = {}
    checks["query_count_and_quotas"] = len(queries)==150 and all(sum(r["distance"]==d for r in queries)==75 for d in (2,3))
    checks["query_pairs_unique_unordered"] = len({tuple(sorted((r["source"],r["target"]))) for r in queries})==150
    checks["query_original_distances"] = all(nx.shortest_path_length(graph,r["source"],r["target"])==r["distance"] for r in queries)
    checks["zero_failure_endpoint"] = bool((frame[frame.q==0][["Q","Q2","Q3","S"]]==1).all().all())
    end = frame[frame.q==1]
    checks["full_failure_endpoint"] = bool((end.Q==0).all() and (end.S==1/len(graph)).all() and (end.isolates==len(graph)).all())
    checks["outcomes_partition"] = bool(np.allclose(frame.Q+frame.longer_route+frame.disconnected,1))
    checks["strata_average"] = bool(np.allclose(frame.Q,(frame.Q2+frame.Q3)/2))
    checks["all_original_nodes_retained"] = bool((frame.nodes==len(graph)).all())
    checks["nested_monotonicity"] = all((np.diff(g.sort_values("q")[m])<=1e-12).all()
        for _,g in frame.groupby("trial") for m in ("Q","Q2","Q3","S"))
    if not all(checks.values()): raise AssertionError(checks)
    return checks


def run():
    check_environment()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    start = time.perf_counter()
    graph = load_graph(verify=True)
    fingerprint = (tuple(sorted(graph)),tuple(edge_order(graph)))
    export_degrees(OUTPUT)
    queries,audit = sample_queries(graph,seed=SEEDS["queries"])
    path = OUTPUT/"queries.csv"
    expected = pd.DataFrame(queries).to_csv(index=False)
    if path.exists() and path.read_text()!=expected:
        raise ValueError("Frozen queries differ; use a separate output directory for a different workload")
    path.write_text(expected)
    write_json(OUTPUT/"query_audit.json",audit)
    pd.DataFrame(list(audit["endpoint_counts"].items()),columns=["concept","query_count"]).to_csv(OUTPUT/"endpoint_reuse.csv",index=False)
    edges = edge_order(graph)
    pd.DataFrame(edges,columns=["source","target"]).to_csv(OUTPUT/"edge_order.csv",index_label="edge_id")
    uniforms = np.random.default_rng(SEEDS["failures"]).random((RUNS,len(edges)))
    np.save(OUTPUT/"failure_uniforms.npy",uniforms,allow_pickle=False)
    pilot_start = time.perf_counter()
    evaluate(damage_graph(graph,edges,np.random.default_rng(5253099).random(len(edges)),.3),queries)
    pilot_seconds = time.perf_counter()-pilot_start
    rows,detailed = [],[]
    for trial in range(RUNS):
        for q in Q_VALUES:
            tick = time.perf_counter()
            damaged = damage_graph(graph,edges,uniforms[trial],float(q))
            damage_seconds = time.perf_counter()-tick
            tick = time.perf_counter()
            metrics,outcomes = evaluate(damaged,queries)
            evaluation_seconds = time.perf_counter()-tick
            rows.append({"trial":trial,"q":float(q),"nodes":len(damaged),
                "removed_edges":len(edges)-damaged.number_of_edges(),
                "removed_fraction":(len(edges)-damaged.number_of_edges())/len(edges),
                "damage_seconds":damage_seconds,"evaluation_seconds":evaluation_seconds,**metrics})
            detailed.extend({"trial":trial,"q":float(q),**r} for r in outcomes)
    frame = pd.DataFrame(rows)
    frame.to_csv(OUTPUT/"runs.csv",index=False)
    pd.DataFrame(detailed).to_csv(OUTPUT/"query_outcomes.csv.gz",index=False,compression={"method":"gzip","mtime":0})
    summarize(frame,["q"],METRICS).to_csv(OUTPUT/"summary.csv",index=False)
    dense_q = np.round(np.linspace(0,1,51),2)
    rows = []
    for trial in range(RUNS):
        for q in dense_q:
            damaged = damage_graph(graph,edges,uniforms[trial],float(q))
            sizes = sorted((len(c) for c in nx.connected_components(damaged)),reverse=True)
            rows.append({"trial":trial,"q":float(q),"S":sizes[0]/len(graph),
                "small_components":1-sizes[0]/len(graph)})
    frag = pd.DataFrame(rows)
    frag.to_csv(OUTPUT/"fragmentation_runs.csv",index=False)
    frag_summary = summarize(frag,["q"],["S","small_components"])
    frag_summary.to_csv(OUTPUT/"fragmentation_summary.csv",index=False)
    configuration_curve(graph,dense_q).to_csv(OUTPUT/"configuration_reference.csv",index=False)
    correlations = []
    for q,g in frame.groupby("q"):
        coefficient = float(g.S.corr(g.Q)) if g.S.std()>1e-12 and g.Q.std()>1e-12 else None
        correlations.append({"q":q,"pearson_r_within_q":coefficient,"repetitions":len(g)})
    pd.DataFrame(correlations).to_csv(OUTPUT/"within_q_correlations.csv",index=False)
    checks = validate_runs(frame,queries,graph)
    checks["original_graph_unchanged"] = fingerprint==(tuple(sorted(graph)),tuple(edge_order(graph)))
    repeat,_ = evaluate(damage_graph(graph,edges,uniforms[0],.3),queries)
    first = frame[(frame.trial==0)&(frame.q==.3)].iloc[0]
    checks["identical_draws_reproduce_metrics"] = all(repeat[m]==first[m] for m in METRICS)
    if not all(checks.values()): raise AssertionError(checks)
    write_json(OUTPUT/"validation.json",checks)
    manifest = {"status":"completed","nodes":len(graph),"edges":len(edges),"runs":RUNS,
        "q_values":Q_VALUES.tolist(),"fragmentation_q_values":dense_q.tolist(),"seeds":SEEDS,
        "query_hash":digest(path),"edge_order_hash":digest(OUTPUT/"edge_order.csv"),
        "failure_draws_hash":digest(OUTPUT/"failure_uniforms.npy"),
        "input_hashes":{n:digest(ROOT/"data/processed"/n) for n in ("nodes.csv","edges.csv","graph_metadata.json")},
        "versions":{n:version(n) for n in ("numpy","scipy","networkx","matplotlib","pandas","nbformat","nbclient")},
        "python":platform.python_version(),"platform":platform.platform(),
        "interval":"pointwise 95% Student-t intervals over repetitions; raw limits not clipped",
        "pilot_seconds":pilot_seconds,"total_seconds":time.perf_counter()-start,
        "small_components_definition":"Total nodes outside one largest component / original N; equals 1-S",
        **reference_threshold(graph)}
    write_json(OUTPUT/"manifest.json",manifest)
    from .plots import make_plots
    make_plots(OUTPUT)
    print("Completed 330 scenarios and the 51-point fragmentation diagnostic. All checks passed.")
    return manifest


if __name__=="__main__": run()
