"""Meaningful checks for failure coupling, alternate routes and frozen inputs."""
import networkx as nx
import numpy as np
import pytest

from src.percolation.core import damage_graph, edge_order, evaluate, sample_queries, load_graph
from src.percolation.statistics import mean_interval
from src.percolation.experiment import validate_runs, OUTPUT
from src.percolation.theory import reference_threshold, configuration_curve


def query(u,v,d=2):
    return {"query_id":"toy","source":u,"target":v,"distance":d}


def test_full_failure_preserves_isolates():
    graph = nx.path_graph(4)
    damaged = damage_graph(graph,edge_order(graph),[.1,.5,.9],1)
    metrics,_ = evaluate(damaged,[query(0,2)])
    assert len(damaged)==4 and damaged.number_of_edges()==0
    assert metrics["Q"]==0 and metrics["S"]==.25 and metrics["isolates"]==4
    assert graph.number_of_edges()==3


def test_nested_failures():
    graph = nx.cycle_graph(8)
    edges = edge_order(graph)
    draws = np.linspace(.01,.99,len(edges))
    low = damage_graph(graph,edges,draws,.2)
    high = damage_graph(graph,edges,draws,.8)
    assert set(high.edges()) <= set(low.edges())


def test_any_alternate_short_route_counts():
    graph = nx.Graph([(0,1),(1,3),(0,2),(2,3)])
    graph.remove_edge(0,1)
    metrics,outcomes = evaluate(graph,[query(0,3)])
    assert metrics["Q"]==1 and outcomes[0]["distance_within_cutoff"]==2


def test_longer_route_distinguished_from_disconnection():
    graph = nx.Graph([(0,1),(1,4),(0,2),(2,3),(3,5),(5,4)])
    graph.remove_edge(0,1)
    metrics,outcomes = evaluate(graph,[query(0,4)])
    assert metrics["Q"]==0 and metrics["longer_route"]==1 and nx.is_connected(graph)
    graph.remove_edge(0,2)
    metrics,_ = evaluate(graph,[query(0,4)])
    assert metrics["disconnected"]==1


def test_pair_sampling_is_unique_and_order_independent():
    graph = nx.cycle_graph(12)
    reverse = nx.Graph()
    reverse.add_nodes_from(reversed(list(graph)))
    reverse.add_edges_from(reversed(list(graph.edges())))
    first,_ = sample_queries(graph,quota=5,seed=2)
    second,_ = sample_queries(reverse,quota=5,seed=2)
    assert first==second
    assert len({(r["source"],r["target"]) for r in first})==10
    assert all(r["source"]<r["target"] and nx.shortest_path_length(graph,r["source"],r["target"])==r["distance"] for r in first)


def test_insufficient_candidates_rejected():
    with pytest.raises(ValueError):
        sample_queries(nx.path_graph(3),quota=5)


def test_invalid_damage_inputs_rejected():
    graph = nx.path_graph(3)
    with pytest.raises(ValueError): damage_graph(graph,edge_order(graph),[.2],.5)
    with pytest.raises(ValueError): damage_graph(graph,edge_order(graph),[.2,.5],1.1)


def test_configuration_reference_known_regular_graph():
    graph = nx.complete_graph(4) # degree 3 => p_c=1/2 in the reference ensemble.
    assert reference_threshold(graph)["p_reference"]==.5
    frame = configuration_curve(graph,[0,.75,1])
    assert frame.iloc[0].configuration_S==1
    assert frame.iloc[1].configuration_S < 1e-10
    assert frame.iloc[2].configuration_S==0


def test_constant_interval_collapses():
    result = mean_interval([1]*30)
    assert result["mean"]==result["ci_low"]==result["ci_high"]==1


def test_frozen_graph_hashes_and_sizes():
    graph = load_graph(verify=True)
    assert len(graph)==1000 and graph.number_of_edges()==3417


def test_exported_run_invariants():
    import pandas as pd
    frame = pd.read_csv(OUTPUT/"runs.csv", keep_default_na=False)
    queries = pd.read_csv(OUTPUT/"queries.csv", keep_default_na=False).to_dict("records")
    assert len(frame)==30*11
    assert all(validate_runs(frame,queries,load_graph(verify=True)).values())


def test_shared_runtime_and_optional_notebook_requirements():
    from src.environment import check_environment, read_requirements, ROOT
    assert check_environment()['passed']
    runtime = read_requirements(ROOT/'requirements.txt')
    optional = read_requirements(ROOT/'requirements-notebook.txt')
    assert runtime['networkx']=='3.6.1' and runtime['numpy']=='2.4.6'
    assert not {'nbformat','nbclient','ipykernel'} & set(runtime)
    assert all(optional[k]==v for k,v in runtime.items())
    assert optional['ipykernel']=='7.4.0'



def test_small_components_are_complement_including_isolates():
    graph = nx.Graph([(0,1),(1,2),(3,4)])
    graph.add_node(5)
    metrics,_ = evaluate(graph,[query(0,2)])
    assert metrics['S']==.5 and metrics['small_components']==.5


def test_handoff_preserves_edge_draws_and_empty_set_baseline():
    graph = nx.path_graph(4)
    edges = edge_order(graph)
    uniforms = [.1,.8,.3]
    baseline = damage_graph(graph,edges,uniforms,.5)
    empty = damage_graph(graph,edges,uniforms,.5,protected_edges=set())
    held = damage_graph(graph,edges,uniforms,.5,protected_edges={edges[0]})
    assert set(baseline.edges())==set(empty.edges())=={edges[1]}
    assert set(held.edges())=={edges[0],edges[1]}
    with pytest.raises(ValueError):
        damage_graph(graph,edges,uniforms,.5,protected_edges={(0,99)})


def test_final_runner_help_from_another_directory(tmp_path):
    import subprocess,sys
    from src.percolation.core import ROOT
    result = subprocess.run([sys.executable,str(ROOT/'scripts/percolation.py'),'--help'],
                            cwd=tmp_path,capture_output=True,text=True)
    assert result.returncode==0 and '--output' in result.stdout


def test_final_runner_default_csv_dispatch(monkeypatch):
    from scripts.percolation import main
    from src.percolation import experiment as study
    from src.percolation.core import ROOT
    received = {}
    def capture(output_dir, *, plain_csv=False):
        received.update(output_dir=output_dir,plain_csv=plain_csv)
        return {'status':'completed'}
    monkeypatch.setattr(study,'run',capture)
    assert main([])['status']=='completed'
    assert received=={'output_dir':ROOT/'data/percolation','plain_csv':True}


def test_runtime_check_does_not_require_notebook_tools(monkeypatch):
    import src.environment as environment
    from importlib.metadata import PackageNotFoundError
    actual_version = environment.version
    def runtime_only(name):
        if name in {'nbformat','nbclient','ipykernel'}:
            raise PackageNotFoundError(name)
        return actual_version(name)
    monkeypatch.setattr(environment,'version',runtime_only)
    assert environment.check_environment()['passed']
    with pytest.raises(RuntimeError,match='requirements-notebook.txt'):
        environment.check_environment(notebook=True)
