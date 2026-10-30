# Percolation section

Open `percolation_research.ipynb` for the completed audit, theoretical review,
random edge-failure experiments, five embedded figures, handoff notes, and conclusions.
Algorithms stay in `src/`. Every figure is preceded by a concise implementation
reference identifying the computational file, function, and logic.
The notebook executor preserves manual edits rather than regenerating its prose.

## Scope and inputs

All changes and outputs stay inside this directory. Shared data files are read
only. The authoritative graph is the 1,000-node, 3,417-edge Greedy graph.
The historical Lexicographic graph is used only for degree-distribution context.
The full parent network is not analysed or assumed to be represented by either
selected sample. No ER or scale-free classification is claimed.

## Experiment

- 75 unique unordered pairs at original distance 2, and 75 at distance 3.
- Uniform sampling without replacement within each distance group.
- Query seed 5253001; edge-failure seed 5253002.
- 30 independent repetitions; q = 0, 0.1, ..., 1.0 (330 scenarios).
- Original-edge draws shared across q within each repetition, giving nested damage.
- Fixed original nodes, including isolates.
- A separate 51-point component-size sweep at spacing 0.02 using the same draws.
- Mean/SD and pointwise 95% t intervals, with repetition as the statistical unit.

The saved query list is checked before reuse. A different workload requires a
separately identified study. The final count of 30 was fixed before the formal
runs; the independent pilot checked execution practicality only.

## Reproduce from the repository root

Use the authors' **PC5253-KG** Conda environment and **Python 3.11.16**.
Do not create a separate percolation environment or install the former Python 3.14 lock file.

For an existing project environment:

```bash
conda activate PC5253-KG
python --version
python -m pip install -r percolation_li/requirements.txt
python -m pip check
python -m percolation_li.src.check_environment
```

If the existing environment has another Python version, first align it with the
original Part A version using `conda install -n PC5253-KG python=3.11.16`.
For a new clone without the project environment, use the authors' original setup
with the exact patch version: `conda create -n PC5253-KG python=3.11.16`, then run
the activation and installation commands above.

`percolation_li/requirements.txt` includes `-r ../requirements.txt`, so all 14
original pins remain authoritative, including NetworkX 3.6.1, NumPy 2.4.6, and
Matplotlib 3.11.2. The original file is UTF-16; pip reads it successfully. Do not
copy its contents into a second divergent lock file. Only five packages are
added here: pandas 2.3.3, SciPy 1.16.3, nbformat 5.11.1, nbclient 0.11.0, and
ipykernel 7.4.0. Their transitive dependencies are resolved for the user's OS.
No macOS-specific full-environment freeze is distributed.

For interactive notebooks, register this **same active environment**, then select
its kernel in Jupyter or VS Code:

```bash
python -m ipykernel install --user --name pc5253-kg --display-name "PC5253-KG (Python 3.11.16)"
```

To reproduce calculations, test both the original pipeline and this section, and
execute the notebook from the repository root:

```bash
python -m percolation_li.src.study
python -m pytest tests/test_data_pipeline.py percolation_li/src/test_percolation.py -q -p no:cacheprovider
python -m percolation_li.src.build_notebook --execute
```

The notebook executor uses the invoking Python interpreter and checks its version
and required package pins before execution. It does not install packages, choose
another interpreter, register a global kernel, or overwrite your prose. Its
runtime files stay in `work/`; it supports both Windows and macOS. The study also
checks the environment before generating results.

Local verification was performed using CPython 3.11.16 with these exact original
pins plus the five additions. No existing PC5253-KG Conda installation was found
on this machine, so an ignored `work/validation-env` was used only to test the
shared configuration. This is not a separate team setup or a directory to commit.
The old `.venv` and Python 3.14 lock file have been removed. The original root
requirements and README were not changed, respecting this section's edit scope.

## Outputs

| Files in `outputs/` | Purpose |
| --- | --- |
| `queries.csv`, `query_audit.json`, `endpoint_reuse.csv` | Frozen workload and concentration |
| `edge_order.csv`, `failure_uniforms.npy` | Original edge IDs and 30 × 3,417 failure draws |
| `runs.csv`, `query_outcomes.csv.gz` | 330 scenario metrics and 49,500 query outcomes |
| `summary.csv` | Means, sample SDs, and pointwise confidence limits |
| `degree_distribution.csv` | Current and historical empirical degree distributions |
| `fragmentation_runs.csv`, `fragmentation_summary.csv` | Dense component-size diagnostic |
| `configuration_reference.csv` | Assumption-dependent degree-based reference |
| `within_q_correlations.csv` | Descriptive associations at fixed q |
| `validation.json`, `test_results.txt`, `scope_check.json`, `artifact_checks.json` | Checks and verification |
| `manifest.json`, `conclusions.md`, five PNG figures | Reproducibility and interpretation |

For each edge ID, delete the edge if its saved draw is below q. Blank distances in
query outcomes mean no route was found within three hops; the `state` field
separates longer connected routes from disconnection.

## Interpretation

At q = 0.5, Q is approximately 0.382 and S approximately 0.880. About 0.404 of all
queries remain connected but exceed three hops. All nodes outside the largest component are reported as small_components = 1-S,
including isolates. This is a complementary view, not an independent fragmentation
indicator or a way to infer an empirical critical point. The configuration-model
reference near q = 0.969 remains assumption-dependent.

Results are conditional on one selected graph and one balanced query set. The
intervals do not cover graph- or query-sampling uncertainty, and paths do not
establish semantic reasoning accuracy.

## Initial edge-set handoff

Section C.7 lists the frozen workload, saved edge IDs/draws, and baseline results.
`src/core.py::damage_graph(..., protected_edges=...)` accepts an optional set of
original canonical endpoint pairs; an empty set exactly reproduces this study.
The supplied set changes only the deletion predicate, not the random-number
mapping. No allocation method or strategy comparison is included in this section.
The implementation and smoke-test checks remain available in `src/` even though
validation and runtime displays have been removed from the notebook.
