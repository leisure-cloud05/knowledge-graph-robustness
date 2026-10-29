"""Sample one ConceptNet candidate graph and save its results for review."""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime
from pathlib import Path

from src.data_pipeline import analyze_sampled_graph_quality, sample_conceptnet_assertions_graph


SOURCE = Path("data/raw/conceptnet-assertions-5.7.0.csv.gz")
OUTPUT_DIR = Path("data/processed")
SEEDS = tuple(
    f"/c/en/{concept}"
    for concept in (
        "animal", "dog", "cat", "bird", "fish", "pet", "food", "water",
        "house", "person", "child", "school", "book", "car", "road",
    )
)
MAX_NODES = 1000


def run_candidate(source: Path, output_dir: Path, seeds: tuple[str, ...], max_nodes: int) -> dict:
    started = time.perf_counter()
    nodes, edges = sample_conceptnet_assertions_graph(source, seeds, max_nodes=max_nodes)
    sampling_seconds = time.perf_counter() - started

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "candidate_nodes.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["concept"])
        writer.writerows((node,) for node in sorted(nodes))

    with (output_dir / "candidate_edges.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["source", "target", "relation", "weight"])
        for edge in edges:
            writer.writerow([edge["source"], edge["target"], json.dumps(edge["relation"]), edge["weight"]])

    quality = analyze_sampled_graph_quality(nodes, edges)
    report = {
        "source": str(source),
        "collection_date": datetime.now().astimezone().date().isoformat(),
        "seeds": list(seeds),
        "max_nodes": max_nodes,
        "sampling_seconds": sampling_seconds,
        "seeds_retained": {seed: seed in nodes for seed in seeds},
        "quality": quality,
        "status": "candidate",
    }
    (output_dir / "candidate_metadata.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(run_candidate(SOURCE, OUTPUT_DIR, SEEDS, MAX_NODES), indent=2))
