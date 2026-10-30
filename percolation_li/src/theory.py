"""Degree distributions and degree-based reference model (not a fitted law)."""
from collections import Counter

import numpy as np
import pandas as pd

from .core import load_graph, ROOT


def reference_threshold(graph):
    degrees = np.array([d for _, d in graph.degree()], dtype=float)
    mean, second = float(degrees.mean()), float((degrees**2).mean())
    pc = mean/(second-mean) if second > mean else None
    return {"p_reference": pc, "q_reference": 1-pc if pc is not None and pc <= 1 else None}


def degree_table(graph, name):
    counts = Counter(dict(graph.degree()).values())
    k = np.arange(max(counts)+1)
    return pd.DataFrame({"graph": name, "degree": k,
        "count": [counts.get(int(x), 0) for x in k],
        "probability": [counts.get(int(x), 0)/len(graph) for x in k],
        "ccdf": [sum(c for d,c in counts.items() if d >= x)/len(graph) for x in k]})


def configuration_curve(graph, q_values):
    """Smallest fixed point u=1-p+p G1(u); S=1-G0(u)."""
    counts = Counter(dict(graph.degree()).values())
    k = np.array(sorted(counts), dtype=float)
    pk = np.array([counts[int(x)]/len(graph) for x in k])
    mean = float(np.sum(k*pk))
    rows = []
    for q in q_values:
        p = 1-float(q)
        u = 0.0
        for iteration in range(100000):
            # k=0 contributes zero to the excess-degree generating function.
            nonzero = k > 0
            new = 1-p+p*np.sum(k[nonzero]*pk[nonzero]*u**(k[nonzero]-1))/mean
            if abs(new-u) < 1e-12:
                u = float(new)
                break
            u = float(new)
        else:
            raise RuntimeError("Configuration-model fixed point did not converge")
        rows.append({"q": float(q), "configuration_S": float(1-np.sum(pk*u**k))})
    return pd.DataFrame(rows)


def export_degrees(output):
    graphs = {"Greedy (frozen)": load_graph(verify=True),
              "Lexicographic (historical)": load_graph(ROOT / "data/processed/lexicographic_backup")}
    distributions = pd.concat([degree_table(g, name) for name,g in graphs.items()], ignore_index=True)
    distributions.to_csv(output / "degree_distribution.csv", index=False)
    return distributions
