"""Presentation-only notebook helpers. All algorithms are in other src modules."""
import json
from pathlib import Path

import pandas as pd
from IPython.display import HTML, Image, Code, display

from .core import PART


class StudyReport:
    def __init__(self, output=None):
        self.output = Path(output or PART / "outputs")
        self.manifest = json.loads((self.output/"manifest.json").read_text())

    def overview(self):
        m = self.manifest
        display(HTML(f"<p><b>Completed study:</b> {m['nodes']:,} nodes · {m['edges']:,} edges · "
                     f"150 fixed queries · {m['runs']} repetitions · independent edge failures. "
                     "Frozen inputs verified against recorded SHA-256 hashes.</p>"))

    def figure(self, name):
        display(Image(filename=str(self.output/f"{name}.png")))

    def table(self, name):
        frame = pd.read_csv(self.output/f"{name}.csv", keep_default_na=False)
        if name == "summary":
            frame = frame[frame.q.isin([0,.2,.3,.4,.5,.7,.9,1])]
            frame = frame[["q","Q_mean","Q2_mean","Q3_mean","S_mean","longer_route_mean","disconnected_mean"]]
        elif name == "within_q_correlations":
            frame = frame[frame.q.isin([.2,.3,.4,.5,.7])]
        display(HTML(frame.to_html(index=False,float_format=lambda x:f"{x:.4f}",border=0)))

    def query_audit(self):
        data = json.loads((self.output/"query_audit.json").read_text())
        rows = [{"item":"Eligible distance-2 pairs","value":data["candidate_counts"]["2"]},
                {"item":"Eligible distance-3 pairs","value":data["candidate_counts"]["3"]},
                {"item":"Selected unique pairs","value":data["unique_pairs"]},
                {"item":"Distinct endpoint concepts","value":data["distinct_endpoints"]},
                {"item":"Maximum endpoint reuse","value":data["maximum_endpoint_reuse"]},
                {"item":"Queries with person as an endpoint","value":data["person_endpoint_queries"]}]
        display(HTML(pd.DataFrame(rows).to_html(index=False,border=0)))

    def validation(self):
        data = json.loads((self.output/"validation.json").read_text())
        display(HTML(pd.DataFrame([{"check":k,"result":"PASS" if v else "FAIL"} for k,v in data.items()]).to_html(index=False,border=0)))

    def runtime(self):
        frame = pd.read_csv(self.output/"runs.csv", keep_default_na=False)
        frame = frame[["damage_seconds","evaluation_seconds"]].mean().to_frame("mean_seconds")
        display(HTML(frame.to_html(float_format=lambda x:f"{x:.5f}",border=0)))
        m = self.manifest
        display(HTML(f"<p>Independent pilot scenario: {m['pilot_seconds']:.4f} s. "
                     f"Study calculations and exports: {m['total_seconds']:.1f} s "
                     "(figure rendering excluded). Timings are descriptive for this machine.</p>"))

    def degree_plot_source(self):
        import inspect
        from .plots import plot_degree_distributions
        display(Code(inspect.getsource(plot_degree_distributions), language="python"))
