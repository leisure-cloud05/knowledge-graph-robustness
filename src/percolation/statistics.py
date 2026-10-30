"""Repeated-trial summaries; queries are not independent trial units."""
import numpy as np
import pandas as pd
from scipy.stats import t


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


def within_q_correlations(frame):
    rows = []
    for q, group in frame.groupby("q"):
        coefficient = float(group.S.corr(group.Q)) if group.S.std()>1e-12 and group.Q.std()>1e-12 else None
        rows.append({"q":q,"pearson_r_within_q":coefficient,"repetitions":len(group)})
    return pd.DataFrame(rows)
