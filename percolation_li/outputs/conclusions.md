### Conclusion — what the results support

- At q=0.5, the largest component retains **88.0%** of nodes, but only **38.2%** of queries remain within three hops. Another **40.4%** remain connected but require longer routes. Global connectivity alone therefore misses much of the query degradation.
- Originally two-hop queries retain higher availability than three-hop queries: **50.2% versus 26.3%** at q=0.5 for this workload.
- The configuration model is a degree-based reference. The “small components” curve equals **1−S** and does not establish a separate empirical threshold.

NOTE: These conclusions concern one selected graph and one fixed query set; they do not measure semantic correctness or establish general performance on ConceptNet.

