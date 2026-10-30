"""Publication-style static figures for the completed notebook."""
import os
from pathlib import Path

from .core import PART
os.environ.setdefault("MPLCONFIGDIR", str(PART / "work/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def plot_degree_distributions(data):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name, group in data.groupby("graph", sort=False):
        observed = group[(group["count"] > 0) & (group.degree > 0)]
        axes[0].plot(observed.degree, observed.probability, "o", ms=3, label=name)
        tail = group[(group.degree > 0) & (group.ccdf > 0)]
        axes[1].plot(tail.degree, tail.ccdf, label=name)
    axes[0].set(xlabel="Degree k", ylabel="P(k)", title="Degree distribution (log–log axes)")
    axes[1].set(xlabel="Degree k", ylabel="P(K ≥ k)", title="Tail distribution (log–log axes)")
    for ax in axes:
        ax.set(xscale="log", yscale="log")
        ax.legend(fontsize=8)
    return fig



def band(ax, frame, metric, label, color):
    frame = frame.sort_values("q")
    ax.plot(frame.q, frame[f"{metric}_mean"], "o-", ms=4, lw=2, color=color, label=label)
    ax.fill_between(frame.q, frame[f"{metric}_ci_low"], frame[f"{metric}_ci_high"],color=color,alpha=.14)


def finish(fig, path):
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def make_plots(output):
    output = Path(output)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,
        "axes.spines.top":False,"axes.spines.right":False,
        "axes.titleweight":"bold","axes.labelcolor":"#283747",
        "axes.grid":True,"grid.alpha":.18,"figure.constrained_layout.use":True})
    summary = pd.read_csv(output/"summary.csv", keep_default_na=False)
    none = summary.sort_values("q")
    distributions = pd.read_csv(output/"degree_distribution.csv", keep_default_na=False)
    finish(plot_degree_distributions(distributions), output/"degree_structure.png")

    fig,axes = plt.subplots(1,2,figsize=(11,4))
    for metric,label,color in [("Q","All queries","#167f82"),("Q2","Originally 2 hops","#4477aa"),("Q3","Originally 3 hops","#d17a22")]:
        band(axes[0],none,metric,label,color)
    band(axes[1],none,"Q","Query success Q","#167f82")
    band(axes[1],none,"S","Largest component S","#41566d")
    axes[0].set_title("Short-query availability by original distance")
    axes[1].set_title("Query loss precedes major fragmentation")
    for ax in axes:
        ax.set(xlabel="Edge failure probability q",ylabel="Fraction",ylim=(-.025,1.04))
        ax.legend(fontsize=8)
    fig.suptitle("Random edge failures · 30 repetitions · pointwise 95% confidence bands")
    finish(fig,output/"baseline_percolation.png")

    fig,axes = plt.subplots(1,2,figsize=(12,4.4))
    axes[0].stackplot(none.q, none.Q_mean,none.longer_route_mean,none.disconnected_mean,
        labels=["Within 3 hops","Connected, but >3 hops","Disconnected"],
        colors=["#167f82","#e3af5d","#bcc5ce"],alpha=.95)
    axes[0].set(xlabel="Edge failure probability q",ylabel="Fraction of fixed queries",
        ylim=(0,1),title="Why queries fail")
    axes[0].legend(fontsize=8,loc="lower left")
    runs = pd.read_csv(output/"runs.csv")
    for q,color in [(.3,"#4477aa"),(.5,"#d17a22"),(.7,"#7b5295")]:
        data = runs[runs.q==q]
        axes[1].scatter(data.S,data.Q,color=color,s=32,alpha=.7,label=f"q = {q}")
    axes[1].set(xlabel="Largest component S",ylabel="Query success Q",
        title="30 repetitions per q (shared axes)")
    axes[1].legend(fontsize=9)
    finish(fig,output/"query_failure_analysis.png")

    frag = pd.read_csv(output/"fragmentation_summary.csv", keep_default_na=False)
    reference = pd.read_csv(output/"configuration_reference.csv", keep_default_na=False)
    import json
    reference_q = json.loads((output/"manifest.json").read_text())["q_reference"]
    fig,axes = plt.subplots(1,2,figsize=(11,4.4))
    band(axes[0],frag,"S","Measured S","#41566d")
    axes[0].plot(reference.q,reference.configuration_S,"--",color="#ac6586",label="Configuration-model reference")
    band(axes[1],frag,"small_components","Outside largest component: 1 − S","#167f82")
    for ax in axes:
        ax.axvline(reference_q,color="#ac6586",ls="--",alpha=.8,label=f"Degree reference q={reference_q:.3f}")
        ax.set(xlabel="Edge failure probability q",ylabel="Node fraction")
        ax.legend(fontsize=8)
    axes[0].set_title("Measured connectivity vs degree-only reference")
    axes[1].set_title("Nodes in all other components")
    finish(fig,output/"fragmentation_reference.png")

    endpoints = pd.read_csv(output/"endpoint_reuse.csv", keep_default_na=False).head(12)
    fig,ax = plt.subplots(figsize=(9,4))
    ax.barh(endpoints.concept.str.replace("/c/en/","",regex=False)[::-1],endpoints.query_count[::-1],color="#41566d")
    ax.set(xlabel="Number of queries containing this concept",title="Most reused query endpoints (top 12)")
    finish(fig,output/"endpoint_reuse.png")
