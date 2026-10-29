## Sampling Strategy Comparison and Robustness Pre-check

Before proceeding to the formal network analysis and robustness experiments, we evaluated whether the original lexicographic sampling strategy produced a suitable experimental graph.

An initial structural inspection revealed that the frozen graph was relatively sparse, with 72% degree-one nodes and 54.34% bridge edges. Removing the highest-degree node, `/c/en/person`, reduced the largest-component ratio to approximately 70.37% of the remaining nodes and increased the number of connected components to 290.

These observations motivated a comparison of alternative sampling strategies. The objective was to evaluate how sampling choices affect network structure and the feasibility of subsequent edge-failure and edge-protection experiments.

### Sampling strategies

Three strategies were evaluated using the same ConceptNet 5.7.0 assertions source, the same 15 seed concepts, and a fixed graph size of 1,000 nodes.

| Strategy | Selection rule |
| --- | --- |
| Lexicographic | Retain all seeds and select the lexicographically smallest 985 distinct English seed neighbors. |
| Random | Retain all seeds and uniformly sample 985 distinct English seed neighbors using a fixed random seed. |
| Greedy | Retain all seeds, construct an adjacency graph within a reproducibly sampled pool of up to 5,000 seed neighbors, and iteratively select the candidate with the most connections to already selected nodes. |

The Random strategy was evaluated using five independent pseudorandom seeds (42–46). The Greedy strategy used a candidate pool size of 5,000 and random seed 2026, with deterministic tie-breaking by node identifier.

All strategies used the same English concept validation and undirected graph construction rules. For structural comparisons, relations and weights were not used in network metric calculations.

The Greedy method explicitly favors internal connectivity. Its resulting graph should therefore be interpreted as a connectivity-oriented experimental subgraph rather than a representative sample of the complete ConceptNet network.

### Structural comparison results

| Metric | Lexicographic | Random (5-run mean) | Greedy |
| --- | ---: | ---: | ---: |
| Nodes | 1,000 | 1,000 | 1,000 |
| Edges | 1,325 | 1,210.4 | 3,417 |
| Average degree | 2.650 | 2.421 | 6.834 |
| Degree-one node ratio | 0.7200 | 0.8322 | 0.0000 |
| Bridge-edge ratio | 0.5434 | 0.6879 | 0.0000 |
| Average clustering coefficient | 0.1529 | 0.0722 | 0.3716 |
| Largest-component ratio | 1.0000 | 1.0000 | 1.0000 |
| Maximum degree | 355 | 351.2 | 244 |
| Distance-2 query pairs | 93,449 | 88,271 | 92,941 |
| Distance-3 query pairs | 200,359 | 166,793 | 300,923 |

Random sampling produced sparser networks than the lexicographic baseline in all five runs. The degree-one node ratio ranged from 81.3% to 85.5%, suggesting that the high proportion of leaf nodes cannot be attributed solely to lexicographic ordering.

Greedy sampling produced a more densely interconnected graph, increasing the edge count from 1,325 to 3,417 and the average clustering coefficient from 0.1529 to 0.3716. The sampled Greedy graph contained no degree-one nodes or bridge edges.

All three methods retained a largest connected component containing all 1,000 nodes and provided sufficient distance-2 and distance-3 pairs for the proposed 150-query benchmark.

These findings demonstrate that the sampling strategy substantially affects the topology of the experimental knowledge graph. The increased connectivity of the Greedy graph is consistent with its selection objective and should not be interpreted as evidence that Greedy sampling more accurately represents ConceptNet.

### Random edge-failure pre-check

To assess whether the Greedy graph remained suitable for meaningful robustness experiments, we conducted a preliminary random edge-failure comparison between the Lexicographic and Greedy graphs.

The experiment used the following settings:

- Edge failure probabilities: q ∈ {0, 0.1, 0.2, 0.3, 0.4, 0.5}.
- 30 repeated trials for each failure probability.
- Independent edge deletion with probability q.
- A fixed set of 150 queries per graph, containing 75 node pairs at original shortest-path distance 2 and 75 pairs at distance 3.
- Reproducible pseudorandom seeds.

Two metrics were evaluated:

**Query Success Rate, Q(q):** the fraction of fixed query pairs that remain connected by a path of at most three hops after edge failures.

**Largest Connected Component Ratio, S(q):** the number of nodes in the largest connected component after failures divided by the original number of nodes.

The mean results across 30 trials were:

| Failure probability | Lexicographic Q(q) | Greedy Q(q) | Lexicographic S(q) | Greedy S(q) |
| --- | ---: | ---: | ---: | ---: |
| 0.0 | 1.000 | 1.000 | 1.000 | 1.000 |
| 0.1 | 0.794 | 0.900 | 0.927 | 0.997 |
| 0.2 | 0.603 | 0.783 | 0.846 | 0.987 |
| 0.3 | 0.448 | 0.657 | 0.762 | 0.965 |
| 0.4 | 0.314 | 0.520 | 0.670 | 0.929 |
| 0.5 | 0.210 | 0.380 | 0.576 | 0.877 |

The Greedy graph maintained higher query success rates and larger connected components throughout the tested failure range.

At q = 0.3, the mean query success rate was 65.7% for Greedy compared with 44.8% for Lexicographic. At q = 0.5, the Greedy graph retained a largest-component ratio of 87.7%, compared with 57.6% for Lexicographic.

Importantly, the Greedy graph still showed a substantial decline in query success rate as the failure probability increased, from 100% at q = 0 to 38.0% at q = 0.5. This indicates that the graph remains suitable for investigating query degradation under random edge failures.

However, each graph used its own fixed query set, selected from its original topology. Therefore, the observed differences are comparisons between sampled networks and their corresponding query tasks, rather than a strictly controlled comparison using identical concept pairs. The higher robustness of the Greedy graph is also partly expected from its connectivity-oriented construction.

### Sampling decision and project handoff

The comparison identified Greedy sampling as a promising candidate for the final experimental network because it provides greater internal connectivity while preserving sufficient short-path queries and measurable degradation under edge failures.

The Greedy candidate graph has been exported separately:

- `data/processed/candidate_greedy_nodes.csv`
- `data/processed/candidate_greedy_edges.csv`
- `data/processed/candidate_greedy_metadata.json`

The candidate metadata records the 15 seeds, `max_nodes=1000`, `pool_size=5000`, `greedy_seed=2026`, and the final graph size of 1,000 nodes and 3,417 edges.

The original frozen graph remains unchanged in `data/processed/nodes.csv` and `data/processed/edges.csv`, and its provenance and SHA-256 hashes remain valid.

**Current decision:** Greedy is the preferred candidate for the subsequent network analysis and robustness study, subject to group agreement and final dataset freezing. The comparison results do not by themselves replace the original authoritative graph.

If the group adopts Greedy as the final graph, the authoritative CSV files, metadata, file hashes, and reproduction instructions must be updated consistently before Parts B, C, and D use the new graph.

### Additional limitations

The sampling comparison introduces several considerations:

- All methods are restricted to neighbors of the same 15 seeds, so none provides a representative sample of the complete ConceptNet network.
- Greedy sampling explicitly optimizes internal connectivity and may overrepresent densely connected concept groups.
- The Greedy experiment used one fixed candidate pool and one greedy selection run; sensitivity to candidate-pool size and random seed was not evaluated.
- The robustness pre-check compares different graph-specific query sets. Its results cannot isolate the effect of sampling strategy from differences in query composition.
- Greater baseline robustness does not guarantee that degree-based or edge-betweenness-based protection will outperform random protection. This remains the subject of the formal intervention experiments.
- The reported robustness results describe structural concept association within three hops, not semantic correctness or knowledge reasoning accuracy.

The sampling investigation is therefore treated as a methodological evaluation supporting experimental graph selection, rather than as evidence of a universally optimal sampling strategy.