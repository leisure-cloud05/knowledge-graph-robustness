# Manual audit of 20 sampled edges

This document records a user-confirmed interpretation of 20 edges sampled from the frozen `data/processed/edges.csv`. CSV line numbers include the header row. The sample comprises 10 ordinary random edges, 5 edges involving `/c/en/person`, and 5 edges with less common relation categories, selected with random seed 5253.

The labels are manual judgments for this sample only. They cannot be used to estimate the accuracy of the full graph. The frozen graph is an undirected projection, and this audit did not inspect the original ConceptNet assertion direction. Consequently, a note about lost direction marks uncertainty rather than establishing that an assertion is wrong.

| CSV line | Concept pair | Relation | Label | Audit note |
| ---: | --- | --- | --- | --- |
| 30 | 4 tires (`/c/en/4_tires`) — car (`/c/en/car`) | `/r/HasA` | reasonable | — |
| 191 | achieve financial independence (`/c/en/achieve_financial_independence`) — person (`/c/en/person`) | `/r/Desires` | reasonable | — |
| 312 | Adolphe Sax (`/c/en/adolphe_sax`) — person (`/c/en/person`) | `/r/IsA` | reasonable | — |
| 358 | affect attitude (`/c/en/affect_attitude`) — person (`/c/en/person`) | `/r/Desires` | uncertain | The phrase-to-person semantics are unclear, and the undirected projection does not preserve who desires what. |
| 396 | afterword (`/c/en/afterword`) — book (`/c/en/book`) | `/r/HasContext` | reasonable | — |
| 601 | all known life (`/c/en/all_known_life`) — water (`/c/en/water`) | `/r/HasPrerequisite` | uncertain | This is a broad claim, and the undirected projection loses the prerequisite direction. |
| 639 | allow person to teach (`/c/en/allow_person_to_teach`) — person (`/c/en/person`) | `/r/CapableOf` | uncertain | The phrase is awkward and its relation to `person` is semantically unclear; direction is not preserved. |
| 645 | almanac (`/c/en/almanac`) — book (`/c/en/book`) | `/r/RelatedTo` | reasonable | — |
| 646 | almost always (`/c/en/almost_always`) — dog (`/c/en/dog`) | `/r/HasContext` | uncertain | `almost always` is an ambiguous phrase, and the intended context and original direction are unclear. |
| 724 | American cocker spaniel (`/c/en/american_cocker_spaniel`) — dog (`/c/en/dog`) | `/r/RelatedTo` | reasonable | — |
| 745 | Amerigo Vespucci (`/c/en/amerigo_vespucci`) — person (`/c/en/person`) | `/r/IsA` | reasonable | — |
| 755 | ammonia (`/c/en/ammonia`) — water (`/c/en/water`) | `/r/RelatedTo` | reasonable | — |
| 1127 | antideer (`/c/en/antideer`) — antimouse (`/c/en/antimouse`) | `/r/RelatedTo` | uncertain | Both terms are unusual compounds, and the broad `RelatedTo` relation gives insufficient semantic detail. |
| 1128 | antideer (`/c/en/antideer`) — antirabbit (`/c/en/antirabbit`) | `/r/RelatedTo` | uncertain | Both terms are unusual compounds, and the broad `RelatedTo` relation gives insufficient semantic detail. |
| 1209 | apparatus (`/c/en/apparatus`) — book (`/c/en/book`) | `/r/RelatedTo` | uncertain | `RelatedTo` is too broad here to make the intended connection clear. |
| 1285 | aquariist (`/c/en/aquariist`) — fish (`/c/en/fish`) | `/r/RelatedTo` | uncertain | `aquariist` appears to be a spelling variant or misspelling, and `RelatedTo` is broad. |
| 1288 | aquarium (`/c/en/aquarium`) — water (`/c/en/water`) | `/r/HasA` | reasonable | — |
| 1295 | aquatic (`/c/en/aquatic`) — fish (`/c/en/fish`) | `/r/RelatedTo` | reasonable | — |
| 1303 | car (`/c/en/car`) — cat (`/c/en/cat`) | `/r/AtLocation` | uncertain | The location claim is unclear without context, and the undirected projection loses its original direction. |
| 1321 | food (`/c/en/food`) — school (`/c/en/school`) | `/r/AtLocation` | uncertain | The association may be context-dependent, and the undirected projection loses the location direction. |

Label totals: **reasonable: 10**, **uncertain: 10**, **clearly incorrect: 0**.
