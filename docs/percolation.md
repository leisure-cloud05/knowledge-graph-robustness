# Percolation: execution, results, and handoff

Percolation is a shared project module. Its maintained entry point is
`python scripts/percolation.py`; its research narrative is archived at
`notebooks/legacy/percolation_research.ipynb`.

## Shared environment

Use the authors' PC5253-KG environment, Python 3.11.16, and the root requirements:

```bash
conda activate PC5253-KG
python -m pip install -r requirements.txt
python -m src.environment
python scripts/percolation.py
```

For a new environment, first run `conda create -n PC5253-KG python=3.11.16`.
All original package pins are retained. The single root `requirements.txt` includes
pandas 2.3.3, SciPy 1.16.3, nbformat 5.11.1, nbclient 0.11.0 and ipykernel 7.4.0.
The same environment supports both the final script and the legacy notebook;
there is no separate dependency file or environment for the notebook.

To execute the legacy notebook's display cells after the shared installation:

```bash
python notebooks/legacy/_support/execute.py --execute
```

For interactive use, register the active environment once:

```bash
python -m ipykernel install --user --name pc5253-kg --display-name "PC5253-KG (Python 3.11.16)"
```

Then select that kernel. The legacy notebook contains narrative and display calls;
its support helpers do not implement a second copy of the scientific algorithms.

## Modules and responsibilities

| Module | Responsibility |
| --- | --- |
| `scripts/percolation.py` | CLI arguments, environment check, experiment dispatch |
| `src/percolation/core.py` | Frozen graph loading, uniform pair sampling, damage, evaluation |
| `src/percolation/experiment.py` | Complete run orchestration, validation and export |
| `src/percolation/statistics.py` | Trial summaries, t intervals, within-q correlations |
| `src/percolation/theory.py` | Empirical degree distributions and configuration-model reference |
| `src/percolation/plots.py` | Figures from saved result tables |
| `src/environment.py` | All shared project dependency pins |
| `tests/test_percolation.py` | Scientific invariants and CLI tests |

Library functions such as `damage_graph()` and `evaluate()` do not check installed
packages or select output directories. They can be reused independently by the
edge-protection component.

## Inputs and experimental contract

The read-only authoritative graph is `data/processed/{nodes,edges}.csv`, checked
against `graph_metadata.json`. It has 1,000 nodes and 3,417 undirected, unweighted
projected edges. The historical Lexicographic sample is used only for degree
context, not as another formal query experiment.

- 75 unique unordered pairs at original distance 2, and 75 at distance 3.
- Uniform sampling without replacement within each distance group.
- Query seed 5253001; independent failure stream seed 5253002.
- 30 independent trials; q = 0, 0.1, ..., 1.0, giving 330 scenarios.
- Original-edge draws reused across q within each trial, giving nested damage.
- All original nodes retained, including isolates.
- Separate 51-point component sweep at q spacing 0.02, using the same draws.
- Pointwise 95% t intervals over trials; queries are not independent trials.

A projected-edge failure removes its entire bundle of relations. Query success is
structural reachability within three edges, not semantic correctness.

## One authoritative result directory

Default: `data/percolation/`. Override with:

```bash
python scripts/percolation.py --output data/percolation_trial
```

Relative paths are resolved from the repository root, independent of shell working
directory. Existing incompatible query files cause an error rather than silent
replacement. Timings change between runs; fixed queries, draws and scientific
metrics are reproducible under the shared pinned environment.

| Output | Meaning |
| --- | --- |
| `queries.csv` | Frozen 150-pair workload with original distances |
| `query_audit.json`, `endpoint_reuse.csv` | Candidate counts and endpoint concentration |
| `runs.csv` | 330 trial/q records, metrics and timings |
| `summary.csv` | Q, Q2, Q3, S, outcome fractions: mean, sample SD, CI, n |
| `query_outcomes.csv` | 49,500 query/trial/q outcomes |
| `edge_order.csv` | Canonical endpoint pairs and edge IDs |
| `failure_draws.csv`, `failure_uniforms.npy` | Trial/edge random values; 30 × 3,417 draws |
| `fragmentation_runs.csv`, `fragmentation_summary.csv` | Fine-grid S and small_components = 1-S |
| `degree_distribution.csv` | Current and historical empirical degree frequencies/tails |
| `configuration_reference.csv` | Degree-based infinite-ensemble reference curve |
| `within_q_correlations.csv` | Descriptive Pearson correlation across trials at fixed q |
| `manifest.json`, `environment_check.json`, `validation.json` | Settings, versions, hashes and run checks |
| `figures/` | Five report figures; generated from these result tables |

`state` in the per-query output is `success`, `longer_route`, or `disconnected`.
Blank `distance_within_cutoff` means that the target was not found within three
hops; component membership separates the two failure states. Small components
include all nodes outside one largest component and are exactly 1-S, not an
independent estimate of a critical threshold.

## Edge-protection handoff

```python
from src.percolation import damage_graph, evaluate

# Reuse original_graph, original_edges, frozen_queries and saved uniforms.
damaged = damage_graph(original_graph, original_edges, uniforms[trial], q,
                       protected_edges=selected_original_edges)
metrics, outcomes = evaluate(damaged, frozen_queries)
```

Original edges must follow the saved canonical `edge_order.csv`. The optional set
contains original endpoint pairs; unknown edges are rejected. Protecting edges
changes the deletion predicate, not the assignment of failure draws. An empty set
reproduces the baseline. Keep the same queries, trial IDs and q grid across methods.

The next member defines selection strategies and documents budget, tie-breaking
and random-allocation conventions. If using a floored 5% budget, protect 170 edges.
Evaluate differences within matching trial/q scenarios. Shared statistical helpers
are in `src/percolation/statistics.py`. Protected runs need not have Q=0 at q=1.

## Tests and limits

```bash
python -m pytest tests -q -p no:cacheprovider
```

Tests cover alternative routes, long connected routes, isolates, pair sampling,
shared damage, the optional edge-set interface, theoretical reference cases,
environment separation and direct CLI execution from another directory.

At q=0.5, mean Q is approximately 0.382 and S approximately 0.880; about 0.404 of
queries remain connected but exceed three hops. This supports distinguishing
short-query availability from global connectivity. It does not establish semantic
accuracy or generalise beyond this selected graph and frozen workload.
