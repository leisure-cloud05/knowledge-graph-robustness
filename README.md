# PC5253: ConceptNet Knowledge Graph Robustness

This project constructs a **1,000-node, 3,417-edge undirected English knowledge graph** from the ConceptNet 5.7.0 assertions dataset using structure-aware Greedy sampling.

The project investigates how missing knowledge graph edges affect short-range concept association queries and whether network-informed edge protection can improve query robustness under a limited protection budget.

The authoritative graph files are:

- `data/processed/nodes.csv`
- `data/processed/edges.csv`
- `data/processed/graph_metadata.json`

The original lexicographically sampled graph is retained as a historical baseline. Sampling strategy comparisons and preliminary robustness experiments are documented below.

## 1. Data Source and Provenance

The dataset is derived from the official ConceptNet 5.7.0 assertions dump.

- **Dataset:** ConceptNet 5.7.0
- **Source:** [ConceptNet Downloads](https://github.com/commonsense/conceptnet5/wiki/Downloads)
- **Download:** [ConceptNet Assertions 5.7.0](https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz)
- **Raw filename:** `conceptnet-assertions-5.7.0.csv.gz`
- **Compressed size:** 497,963,447 bytes
- **Raw SHA-256:** `accd65fe94038584295574ddc26e1500c1919c8c4532bf771811cafd0948af7e`
- **Local download/landing date:** 2026-10-28
- **Graph construction date:** 2026-10-29

The download date is based on the raw file's local creation and last-modified timestamps. No independent download log was verified.

### Data collection approach

The original plan was to collect ConceptNet relations through paginated REST API requests. However, repeated tests encountered HTTP 502 errors.

The project therefore used the official offline assertions dataset as a fallback.

The existing API helper supports single-page requests only. The project does not claim to implement successful API pagination.

The raw dataset should be placed at:

`data/raw/conceptnet-assertions-5.7.0.csv.gz`

The `data/raw/` directory is excluded from Git, and the full raw dataset is not included in this repository.

## 2. Environment

The project was developed using Python 3.11 and NetworkX.

The original Part A environment used Python 3.11.16.

To reproduce the environment:

```bash
conda create -n PC5253-KG python=3.11.16
conda activate PC5253-KG
python -m pip install -r requirements.txt
```

The shared `requirements.txt` includes the original pinned dependencies plus pandas and SciPy for percolation. Optional notebook tools are installed in the same environment with:

```bash
python -m pip install -r requirements-notebook.txt
```

**Percolation one-command run:**

```bash
python -m src.environment
python scripts/percolation.py
```

Results are written to `data/percolation/`, with figures in `data/percolation/figures/`. The maintained code is in `src/percolation/`, tests are in `tests/test_percolation.py`, and the archived research notebook is in `notebooks/legacy/`. See [Percolation documentation](docs/percolation.md) for outputs, the optional notebook workflow, and edge-protection handoff.

Run the Part A tests from the project root:

```bash
python -m pytest tests/test_data_pipeline.py
```

## 3. Graph Construction

### Seed concepts

The graph construction uses 15 predefined English seed concepts:

- `/c/en/animal`
- `/c/en/dog`
- `/c/en/cat`
- `/c/en/bird`
- `/c/en/fish`
- `/c/en/pet`
- `/c/en/food`
- `/c/en/water`
- `/c/en/house`
- `/c/en/person`
- `/c/en/child`
- `/c/en/school`
- `/c/en/book`
- `/c/en/car`
- `/c/en/road`

The maximum graph size is fixed at 1,000 nodes.

### Cleaning rules

The data pipeline applies the following rules:

1. Retain valid English base concept identifiers.
2. Remove self-loops.
3. Treat concept relations as undirected edges.
4. Merge repeated and reversed edges.
5. Preserve the union of relation categories for each node pair.
6. Retain the maximum finite non-negative weight for repeated edges.
7. Retain all selected nodes and all valid edges connecting them.

The resulting graph is an undirected simple graph:

\[
G=(V,E)
\]

ConceptNet relation types and weights are retained as edge metadata. The network structure experiments use an unweighted projection unless otherwise specified.

## 4. Sampling Strategy Evaluation

Before finalizing the graph, we investigated whether the original lexicographic sampling approach produced a suitable network for robustness experiments.

The original graph contained 1,000 nodes and 1,325 edges.

Structural inspection revealed:

- 72% degree-one nodes.
- 54.34% bridge edges.
- Average clustering coefficient of 0.1529.
- A highest-degree node, `/c/en/person`, with degree 355.

Removing `/c/en/person` increased the number of connected components from 1 to 290. The largest connected component then contained approximately 70.37% of the remaining nodes.

These observations motivated a comparison of three sampling methods.

### 4.1 Sampling methods

| Strategy | Description |
| --- | --- |
| Lexicographic | Retain all 15 seeds and select the lexicographically smallest 985 distinct English seed neighbors. |
| Random | Retain all seeds and uniformly sample 985 distinct English seed neighbors. |
| Greedy | Retain all seeds and iteratively select candidates with the most connections to already selected nodes. |

The Random strategy was evaluated using five pseudorandom seeds: 42, 43, 44, 45, and 46.

The Greedy strategy used:

- **Candidate pool size:** 5,000
- **Random seed:** 2026
- **Maximum nodes:** 1,000
- **Selection criterion:** Number of connections to already selected nodes
- **Tie-breaking:** Lexicographic order of concept identifiers

The Greedy candidate pool was randomly sampled from the distinct English neighbors of the 15 seeds. The algorithm then selected nodes iteratively to favor internal connectivity.

All strategies used the same ConceptNet source, seed concepts, graph size, and edge validation rules.

### 4.2 Structural comparison

| Metric | Lexicographic | Random (5-run mean) | Greedy |
| --- | ---: | ---: | ---: |
| Nodes | 1,000 | 1,000 | 1,000 |
| Edges | 1,325 | 1,210.4 | 3,417 |
| Average degree | 2.650 | 2.421 | 6.834 |
| Degree-one node ratio | 0.7200 | 0.8322 | 0.0000 |
| Bridge-edge ratio | 0.5434 | 0.6879 | 0.0000 |
| Average clustering coefficient | 0.1529 | 0.0722 | 0.3716 |
| Largest connected component ratio | 1.0000 | 1.0000 | 1.0000 |
| Maximum degree | 355 | 351.2 | 244 |
| Distance-2 query pairs | 93,449 | 88,271 | 92,941 |
| Distance-3 query pairs | 200,359 | 166,793 | 300,923 |

Random sampling produced sparser networks than the original lexicographic sample in all five runs. The degree-one node ratio ranged from 81.3% to 85.5%.

This suggests that the high proportion of leaf nodes cannot be attributed solely to lexicographic ordering.

Greedy sampling produced substantially more internal connections, increasing the edge count from 1,325 to 3,417 and the average clustering coefficient from 0.1529 to 0.3716.

The Greedy graph contained no degree-one nodes or bridge edges.

All three strategies retained a largest connected component containing all 1,000 nodes and provided sufficient distance-2 and distance-3 pairs for the proposed 150-query benchmark.

The greater connectivity of the Greedy network is consistent with its selection criterion and should not be interpreted as evidence that it is more representative of ConceptNet.

## 5. Random Edge-Failure Pre-check

A preliminary robustness experiment compared the original Lexicographic graph with the Greedy graph.

The purpose was to determine whether the more connected Greedy network still exhibited meaningful degradation under random edge failures.

### 5.1 Experimental setup

The experiment used:

- **Failure probabilities:** q ∈ {0, 0.1, 0.2, 0.3, 0.4, 0.5}
- **Repeated trials:** 30 for each failure probability
- **Failure model:** Each edge is removed independently with probability q
- **Queries:** 150 fixed concept pairs per graph
- **Query composition:** 75 pairs with original shortest-path distance 2 and 75 pairs with distance 3
- **Randomness:** Reproducible pseudorandom seeds

Two metrics were evaluated.

**Query Success Rate, Q(q):** The proportion of fixed query pairs that remain connected by a path of at most three hops after edge failures.

**Largest Connected Component Ratio, S(q):** The number of nodes in the largest connected component after edge failures divided by the original number of nodes.

Results are reported as means over 30 trials. The evaluation script also calculates sample standard deviations using `ddof=1`, which are retained in the generated results.

### 5.2 Results

| Failure probability | Lexicographic Q(q) | Greedy Q(q) | Lexicographic S(q) | Greedy S(q) |
| --- | ---: | ---: | ---: | ---: |
| 0.0 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.1 | 0.794 | 0.900 | 0.927 | 0.997 |
| 0.2 | 0.603 | 0.783 | 0.846 | 0.987 |
| 0.3 | 0.448 | 0.657 | 0.762 | 0.965 |
| 0.4 | 0.314 | 0.520 | 0.670 | 0.929 |
| 0.5 | 0.210 | 0.380 | 0.576 | 0.877 |

The Greedy network maintained higher query success rates and larger connected components throughout the tested failure range.

At q = 0.3:

- Lexicographic query success rate: 44.8%
- Greedy query success rate: 65.7%

At q = 0.5:

- Lexicographic largest-component ratio: 57.6%
- Greedy largest-component ratio: 87.7%

Although Greedy showed greater structural robustness, its query success rate still declined from 100% at q = 0 to 38.0% at q = 0.5.

This confirms that the Greedy network remains suitable for studying query degradation under random edge failures.

However, each graph used its own fixed query set. The experiment therefore compares two sampled networks and their corresponding query tasks, rather than evaluating identical concept pairs across both networks.

The observed differences also reflect the Greedy method's deliberate preference for internal connectivity.

## 6. Final Sampling Decision

Following the structural comparison and robustness pre-check, **Greedy sampling was selected as the final strategy** for subsequent network analysis and robustness experiments.

The decision was based on the following considerations:

- Greater internal connectivity and structural redundancy.
- Sufficient distance-2 and distance-3 query pairs.
- A single connected component containing all 1,000 nodes.
- Measurable degradation in query success under random edge failures.
- Suitability for studying edge protection under a limited budget.

The selection was made before evaluating the proposed network-informed edge-protection strategies. No protection method was used to determine the sampling choice.

The Greedy graph is a connectivity-oriented experimental subgraph, not a representative sample of the entire ConceptNet network.

## 7. Final Frozen Graph

The final experimental network contains:

| Metric | Value |
| --- | ---: |
| Nodes | 1,000 |
| Edges | 3,417 |
| Average degree | 6.834 |
| Connected components | 1 |
| Largest connected component ratio | 1.0000 |
| Isolated nodes | 0 |
| Degree-one nodes | 0 |
| Bridge-edge ratio | 0.0000 |
| Average clustering coefficient | 0.3716 |
| Maximum degree | 244 |
| Distance-2 query pairs | 92,941 |
| Distance-3 query pairs | 300,923 |

The frozen graph supports the intended mixed query set of 150 concept pairs, with 75 pairs at distance 2 and 75 pairs at distance 3.

This establishes query-set feasibility; the final query set must be explicitly generated and frozen before the formal robustness experiments.

### 7.1 Authoritative files

The authoritative Greedy graph is stored in:

- `data/processed/nodes.csv`
- `data/processed/edges.csv`
- `data/processed/graph_metadata.json`

The nodes file contains one column, `concept`.

The edges file contains:

| Column | Description |
| --- | --- |
| `source` | First normalized endpoint |
| `target` | Second normalized endpoint |
| `relation` | JSON array of ConceptNet relation categories |
| `weight` | Maximum retained weight for the node pair |

### 7.2 SHA-256 verification

| File | SHA-256 |
| --- | --- |
| `data/processed/nodes.csv` | `a5f54f9700969335b98e9fc8566aaa03a2487a99402e06cad4e5c87f1a197e27` |
| `data/processed/edges.csv` | `941b353e004522b8e7ea156b27b24878012dcd31b79911d5993e0ade3980e483` |

On macOS or Linux, verify the frozen files using:

```bash
shasum -a 256 data/processed/nodes.csv
shasum -a 256 data/processed/edges.csv
```

The reported hashes should match the values recorded above and in `graph_metadata.json`.

### 7.3 Previous graph and candidate files

The original Lexicographic graph is retained under:

- `data/processed/lexicographic_backup/nodes.csv`
- `data/processed/lexicographic_backup/edges.csv`
- `data/processed/lexicographic_backup/graph_metadata.json`

The Greedy candidate files are retained as sampling outputs:

- `data/processed/candidate_greedy_nodes.csv`
- `data/processed/candidate_greedy_edges.csv`
- `data/processed/candidate_greedy_metadata.json`

The frozen Greedy files are the authoritative inputs for all subsequent network experiments.

## 8. Reproducibility

### 8.1 Original lexicographic sampling

The original Part A sampling entry point is:

```bash
python -m scripts.sample_candidate
```

This script reads the ConceptNet assertions file twice and produces the original lexicographic candidate files:

- `candidate_nodes.csv`
- `candidate_edges.csv`
- `candidate_metadata.json`

It does **not** reproduce the final Greedy graph.

The original sampling run was recorded as taking approximately 1,109.04 seconds on the original machine.

### 8.2 Greedy sampling

The Greedy node-selection method is implemented in:

`scripts/compare_sampling.py`

The main parameters are:

- Maximum nodes: 1,000
- Seeds: 15 predefined English concepts
- Candidate pool size: 5,000
- Greedy random seed: 2026

The sampling comparison can be run from the project root with the original ConceptNet assertions file:

```bash
python -m scripts.compare_sampling \
  --raw data/raw/conceptnet-assertions-5.7.0.csv.gz \
  --runs 5
```

The comparison script generates structural statistics for the original graph, five random samples, and the Greedy sample.

The original candidate export also preserves ConceptNet relation categories and edge weights. The topology-only graph comparison does not by itself reproduce the complete four-column frozen `edges.csv`; faithful full-CSV reconstruction requires the corresponding export procedure and the Part A edge-cleaning rules.

### 8.3 Full Greedy Graph Reproduction

The final Greedy graph can be reproduced from the original ConceptNet 5.7.0 assertions dataset using:

```bash
python -m scripts.export_greedy --raw data/raw/conceptnet-assertions-5.7.0.csv.gz
```

The reproduction uses a candidate pool of 5,000 nodes, random seed 2026, and a fixed graph size of 1,000 nodes.

**Reproduction verification: PASSED**

- Nodes: 1,000
- Edges: 3,417
- `nodes.csv` SHA-256: `a5f54f9700969335b98e9fc8566aaa03a2487a99402e06cad4e5c87f1a197e27`
- `edges.csv` SHA-256: `941b353e004522b8e7ea156b27b24878012dcd31b79911d5993e0ade3980e483`

Both SHA-256 hashes matched the authoritative frozen graph exactly, confirming byte-for-byte reproducibility, including edge relation and weight attributes. The verification was performed on Windows using the original ConceptNet assertions dataset.

### 8.4 Robustness comparison

The preliminary robustness experiment is implemented in:

`scripts/compare_robustness.py`

Run it with:

```bash
python -m scripts.compare_robustness
```

The script loads the original Lexicographic baseline and the exported Greedy candidate, constructs reproducible query sets, performs repeated random edge failures, and produces query-success and largest-component-ratio results.

This preliminary experiment is separate from the formal Part C and Part D evaluations.

## Part B — Network Structure Analysis

The frozen Greedy graph was analyzed as an unweighted, undirected network using NetworkX.

### Structural Statistics

| Metric | Value |
|---|---:|
| Number of nodes | 1,000 |
| Number of edges | 3,417 |
| Average degree | 6.834 |
| Minimum degree | 2 |
| Maximum degree | 244 |
| Network density | 0.006841 |
| Average clustering coefficient | 0.371597 |
| Number of connected components | 1 |
| Largest connected component ratio | 1.000 |
| Number of bridges | 0 |

The network is globally sparse but exhibits substantial local clustering. All 1,000 nodes belong to a single connected component, and no bridge edges are present, indicating some structural redundancy.

The degree distribution is heterogeneous, with `/c/en/person` being the highest-degree node (degree 244).

### Edge Betweenness Centrality

The five edges with the highest normalized edge betweenness centrality are:

| Edge | Betweenness |
|---|---:|
| person — water | 0.039983 |
| animal — person | 0.026694 |
| dog — person | 0.019724 |
| food — water | 0.019080 |
| animal — food | 0.016170 |

These edges participate in a relatively large proportion of shortest paths and are candidates for further investigation in the edge-protection experiments. High edge betweenness does not necessarily imply the greatest impact on query robustness.

### Generated Outputs

Run the analysis using:

```bash
python -m src.network_analysis
```

The outputs are saved in `results/part_b/`, including:

- `network_stats.json`
- `node_metrics.csv`
- `degree_distribution.csv`
- `component_sizes.csv`
- `edge_betweenness.csv`
- `degree_distribution.png`
- `network_visualization.png`

The network visualization displays an 80-node subgraph centered on `/c/en/person`, rather than the entire 1,000-node network.

## 10. Limitations

The following limitations should be considered when interpreting the results:

1. **Sampling bias:** All sampling methods are restricted to neighborhoods of the same 15 predefined seeds. The resulting graphs are not representative of the complete ConceptNet network.

2. **Connectivity preference:** Greedy sampling favors internally well-connected concepts and may overrepresent densely connected subgraphs.

3. **Limited Greedy sensitivity analysis:** Only one fixed candidate pool and one Greedy selection run were evaluated. Sensitivity to the candidate-pool size and Greedy random seed remains untested.

4. **Graph-specific query sets:** The preliminary robustness comparison used different fixed query sets for the two graphs. The results cannot isolate the sampling strategy's effect from differences in query composition.

5. **Undirected projection:** ConceptNet relations were converted to an undirected simple graph for structural analysis. Directional and semantic information is not fully represented by network paths.

6. **Structural rather than semantic evaluation:** A path within three hops indicates structural association, not necessarily semantically correct reasoning or question answering.

7. **Protection strategies remain untested:** Greater baseline robustness does not guarantee that degree-based or edge-betweenness-based protection will outperform random edge protection.

The sampling comparison supports the selection of an experimental graph for the current project. It does not establish an optimal general-purpose ConceptNet sampling strategy.

## 11. Next Steps

The frozen Greedy graph will be used as the common input for the remaining project components.

**Part B — Network Structure Analysis (Completed)**

The frozen Greedy graph was analyzed using NetworkX. The analysis covers degree distribution, clustering coefficient, connected components, edge betweenness centrality, and network visualization.

Results are available in `results/part_b/`.

**Part C — Random Edge Failure (Completed)**

- Fixed 150-query workload, independent edge failures, Q/Q2/Q3/S and outcome breakdowns.
- 30 trials per q, saved random draws and repeated-trial uncertainty.
- Run `python scripts/percolation.py`; outputs are under `data/percolation/`.
- Reusable damage/evaluation interfaces support the next member's protection work.

**Part D — Network-informed Edge Protection**

- Random edge protection
- Degree-based edge protection
- Edge-betweenness-based edge protection
- Comparison under a fixed 5% protection budget
- Evaluation against the unprotected baseline

All formal experiments will use the same frozen Greedy graph and a consistent query-set definition.