"""Tests for the in-memory ConceptNet edge cleaner."""

import gzip
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import requests

from src.data_pipeline import (
    CONCEPTNET_QUERY_URL,
    ConceptNetFetchError,
    analyze_sampled_graph_quality,
    clean_assertion_tsv_lines,
    clean_edge,
    clean_edges,
    fetch_conceptnet_edges,
    load_conceptnet_assertions_tsv,
    sample_conceptnet_assertions_graph,
)
from scripts.sample_candidate import run_candidate


def node(term: str, language: str = "en", *, node_id: str | None = None) -> dict:
    return {
        "term": term,
        "@id": node_id or term,
        "language": language,
    }


def edge(start: dict, end: dict, relation: str = "/r/RelatedTo", weight: float = 1.0) -> dict:
    return {
        "start": start,
        "end": end,
        "rel": {"@id": relation},
        "weight": weight,
    }


def assertion_line(
    relation: str, start: str, end: str, weight: float
) -> str:
    fields = [
        "/a/simulated",
        relation,
        start,
        end,
        json.dumps({"weight": weight}),
    ]
    return "\t".join(fields) + "\n"


class DataPipelineTests(unittest.TestCase):
    def test_normal_edge_uses_term_and_orders_endpoints(self) -> None:
        raw = edge(
            node("/c/en/zebra", node_id="/c/en/not_used"),
            node("/c/en/apple"),
            relation="/r/IsA",
            weight=2,
        )

        self.assertEqual(
            clean_edge(raw),
            {
                "source": "/c/en/apple",
                "target": "/c/en/zebra",
                "relation": ["/r/IsA"],
                "weight": 2.0,
            },
        )

    def test_missing_term_uses_id_and_strips_pos_suffix(self) -> None:
        id_only_node = {"@id": "/c/en/running/v", "language": "en"}
        raw = edge(id_only_node, node("/c/en/exercise"))

        self.assertEqual(
            clean_edge(raw),
            {
                "source": "/c/en/exercise",
                "target": "/c/en/running",
                "relation": ["/r/RelatedTo"],
                "weight": 1.0,
            },
        )

    def test_invalid_concept_paths_are_skipped(self) -> None:
        valid = node("/c/en/animal")
        invalid_nodes = [
            node("/c/en/dog/n"),  # A term must already be a base path.
            node("/c/en/"),
            node("dog"),
            {"@id": "/c/en/dog/x", "language": "en"},
            {"@id": "/c/en/dog/n/extra", "language": "en"},
            {"term": 123, "@id": "/c/en/dog", "language": "en"},
        ]

        for invalid in invalid_nodes:
            with self.subTest(node=invalid):
                self.assertIsNone(clean_edge(edge(invalid, valid)))

    def test_non_english_endpoint_is_skipped(self) -> None:
        raw = edge(node("/c/en/dog"), node("/c/zh/cat", "zh"))

        self.assertIsNone(clean_edge(raw))

    def test_self_loop_is_skipped(self) -> None:
        raw = edge(node("/c/en/dog"), node("/c/en/dog"))

        self.assertIsNone(clean_edge(raw))

    def test_reverse_duplicates_are_merged_deterministically(self) -> None:
        dog = node("/c/en/dog")
        animal = node("/c/en/animal")
        simulated_edges = [
            edge(dog, animal, relation="/r/RelatedTo", weight=1.0),
            edge(animal, dog, relation="/r/IsA", weight=3.0),
            edge(dog, animal, relation="/r/AtLocation", weight=3.0),
            edge(animal, dog, relation="/r/IsA", weight=2.0),
        ]
        expected = [
            {
                "source": "/c/en/animal",
                "target": "/c/en/dog",
                "relation": ["/r/AtLocation", "/r/IsA", "/r/RelatedTo"],
                "weight": 3.0,
            }
        ]

        self.assertEqual(clean_edges(simulated_edges), expected)
        self.assertEqual(clean_edges(reversed(simulated_edges)), expected)

    def test_missing_or_malformed_fields_are_skipped(self) -> None:
        valid = edge(node("/c/en/cat"), node("/c/en/pet"))
        simulated_edges = [
            {"end": node("/c/en/pet"), "rel": {"@id": "/r/IsA"}, "weight": 1},
            {"start": node("/c/en/cat"), "rel": {"@id": "/r/IsA"}, "weight": 1},
            {"start": node("/c/en/cat"), "end": node("/c/en/pet"), "weight": 1},
            edge(node("/c/en/cat"), node("/c/en/pet"), weight=float("nan")),
            "not an edge",
            valid,
        ]

        self.assertEqual(clean_edges(simulated_edges), [clean_edge(valid)])


class ConceptNetFetchTests(unittest.TestCase):
    @patch("src.data_pipeline.requests.get")
    def test_fetch_one_page_returns_edges_from_json(self, mock_get: Mock) -> None:
        expected_edges = [
            {
                "start": {"term": "/c/en/dog"},
                "end": {"term": "/c/en/animal"},
                "rel": {"@id": "/r/IsA"},
                "weight": 1.0,
            }
        ]
        response = Mock()
        response.json.return_value = {"edges": expected_edges}
        mock_get.return_value = response

        result = fetch_conceptnet_edges("/c/en/dog", limit=25)

        self.assertEqual(result, expected_edges)
        mock_get.assert_called_once_with(
            CONCEPTNET_QUERY_URL,
            params={"node": "/c/en/dog", "offset": 0, "limit": 25},
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()
        response.json.assert_called_once_with()

    @patch("src.data_pipeline.requests.get")
    def test_fetch_502_raises_without_parsing_json(self, mock_get: Mock) -> None:
        response = Mock(status_code=502)
        response.raise_for_status.side_effect = requests.HTTPError(
            "502 Server Error", response=response
        )
        mock_get.return_value = response

        with self.assertRaisesRegex(ConceptNetFetchError, r"HTTP 502"):
            fetch_conceptnet_edges("/c/en/dog")

        response.json.assert_not_called()


class ConceptNetAssertionsTsvTests(unittest.TestCase):
    def test_tsv_lines_keep_only_english_edges(self) -> None:
        lines = [
            assertion_line("/r/IsA", "/c/en/dog", "/c/en/animal", 1.0),
            assertion_line("/r/IsA", "/c/en/dog", "/c/zh/animal", 9.0),
        ]

        self.assertEqual(
            clean_assertion_tsv_lines(lines),
            [
                {
                    "source": "/c/en/animal",
                    "target": "/c/en/dog",
                    "relation": ["/r/IsA"],
                    "weight": 1.0,
                }
            ],
        )

    def test_tsv_lines_skip_invalid_rows(self) -> None:
        lines = [
            "only\tfour\tfields\there\n",
            "/a/x\t/r/IsA\t/c/en/dog\t/c/en/animal\tnot-json\n",
            "/a/x\t/r/IsA\t/c/en/dog\t/c/en/animal\t{}\n",
            assertion_line("/r/IsA", "/c/en/dog", "/c/en/animal", float("nan")),
        ]

        self.assertEqual(clean_assertion_tsv_lines(lines), [])

    def test_tsv_reverse_duplicates_merge_independently_of_order(self) -> None:
        lines = [
            assertion_line("/r/RelatedTo", "/c/en/dog", "/c/en/animal", 1.0),
            assertion_line("/r/IsA", "/c/en/animal", "/c/en/dog", 3.0),
            assertion_line("/r/RelatedTo", "/c/en/animal", "/c/en/dog", 2.0),
        ]
        expected = [
            {
                "source": "/c/en/animal",
                "target": "/c/en/dog",
                "relation": ["/r/IsA", "/r/RelatedTo"],
                "weight": 3.0,
            }
        ]

        self.assertEqual(clean_assertion_tsv_lines(lines), expected)
        self.assertEqual(clean_assertion_tsv_lines(reversed(lines)), expected)

    def test_file_entry_streams_tsv_lines(self) -> None:
        line = assertion_line("/r/IsA", "/c/en/dog", "/c/en/animal", 1.5)
        mocked_open = mock_open(read_data=line)

        with patch("src.data_pipeline.Path.open", mocked_open):
            result = load_conceptnet_assertions_tsv("assertions.tsv")

        self.assertEqual(result, clean_assertion_tsv_lines([line]))
        mocked_open.assert_called_once_with("r", encoding="utf-8")

    def test_file_entry_streams_gzip_tsv_lines(self) -> None:
        lines = [
            assertion_line("/r/RelatedTo", "/c/en/dog", "/c/en/animal", 1.0),
            assertion_line("/r/IsA", "/c/en/animal", "/c/en/dog", 2.5),
        ]
        # Keep this temporary file inside the writable project tree.  It is
        # removed automatically when the context exits.
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "assertions.tsv.gz"
            with gzip.open(path, mode="wt", encoding="utf-8") as compressed:
                compressed.writelines(lines)

            result = load_conceptnet_assertions_tsv(path)

        self.assertEqual(result, clean_assertion_tsv_lines(lines))


class ConceptNetAssertionsSamplingTests(unittest.TestCase):
    def test_bounded_sample_is_independent_of_file_order_and_compression(self) -> None:
        lines = [
            assertion_line("/r/RelatedTo", "/c/en/dog", "/c/en/zebra", 10.0),
            assertion_line("/r/HasA", "/c/en/dog", "/c/en/pet", 2.0),
            assertion_line("/r/IsA", "/c/en/animal", "/c/en/dog", 3.0),
            assertion_line("/r/RelatedTo", "/c/en/dog", "/c/en/animal", 1.0),
            assertion_line("/r/RelatedTo", "/c/en/animal", "/c/en/pet", 4.0),
            assertion_line("/r/IsA", "/c/en/dog", "/c/zh/animal", 20.0),
            assertion_line("/r/RelatedTo", "/c/en/cat", "/c/en/mouse", 8.0),
        ]
        expected_nodes = {"/c/en/dog", "/c/en/animal", "/c/en/pet"}
        expected_edges = [
            {
                "source": "/c/en/animal",
                "target": "/c/en/dog",
                "relation": ["/r/IsA", "/r/RelatedTo"],
                "weight": 3.0,
            },
            {
                "source": "/c/en/animal",
                "target": "/c/en/pet",
                "relation": ["/r/RelatedTo"],
                "weight": 4.0,
            },
            {
                "source": "/c/en/dog",
                "target": "/c/en/pet",
                "relation": ["/r/HasA"],
                "weight": 2.0,
            },
        ]

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            plain_path = Path(directory) / "assertions.tsv"
            plain_path.write_text("".join(lines), encoding="utf-8")
            gzip_path = Path(directory) / "assertions.tsv.gz"
            with gzip.open(gzip_path, mode="wt", encoding="utf-8") as compressed:
                compressed.writelines(reversed(lines))

            plain_result = sample_conceptnet_assertions_graph(
                plain_path, ["/c/en/dog"], max_nodes=3
            )
            gzip_result = sample_conceptnet_assertions_graph(
                gzip_path, ["/c/en/dog"], max_nodes=3
            )

        self.assertEqual(plain_result, (expected_nodes, expected_edges))
        self.assertEqual(gzip_result, plain_result)

    def test_sample_rejects_more_seeds_than_node_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "smaller than the number of seeds"):
            sample_conceptnet_assertions_graph(
                "unused.tsv",
                ["/c/en/dog", "/c/en/cat"],
                max_nodes=1,
            )


class GraphQualityTests(unittest.TestCase):
    @staticmethod
    def path_edge(source: str, target: str) -> dict:
        return {
            "source": source,
            "target": target,
            "relation": ["/r/RelatedTo"],
            "weight": 1.0,
        }

    def test_path_graph_metrics_retain_isolated_node(self) -> None:
        path_nodes = [f"/c/en/node_{index}" for index in range(5)]
        isolated = "/c/en/isolated"
        nodes = set(path_nodes) | {isolated}
        edges = [
            self.path_edge(path_nodes[index], path_nodes[index + 1])
            for index in range(4)
        ]

        report = analyze_sampled_graph_quality(nodes, edges)

        self.assertEqual(report["node_count"], 6)
        self.assertEqual(report["edge_count"], 4)
        self.assertEqual(report["connected_component_count"], 2)
        self.assertAlmostEqual(report["largest_component_ratio"], 5 / 6)
        self.assertEqual(report["isolated_node_count"], 1)
        # In a 5-node path: 3 pairs are 2 hops apart and 2 are 3 hops apart.
        self.assertEqual(report["distance_2_pair_count"], 3)
        self.assertEqual(report["distance_3_pair_count"], 2)
        self.assertEqual(report["distance_2_or_3_pair_count"], 5)
        self.assertFalse(report["can_form_mixed_query_set"])

    def test_star_total_over_150_still_fails_mixed_query_quota(self) -> None:
        center = "/c/en/center"
        leaves = {f"/c/en/leaf_{index:02d}" for index in range(18)}
        nodes = leaves | {center}
        edges = [self.path_edge(center, leaf) for leaf in sorted(leaves)]

        report = analyze_sampled_graph_quality(nodes, edges)

        # Every pair of the 18 leaves is exactly 2 hops apart: C(18, 2)=153.
        self.assertEqual(report["distance_2_pair_count"], 153)
        self.assertEqual(report["distance_3_pair_count"], 0)
        self.assertEqual(report["distance_2_or_3_pair_count"], 153)
        self.assertFalse(report["can_form_mixed_query_set"])

    def test_double_star_satisfies_both_configurable_quotas(self) -> None:
        left_center = "/c/en/left_center"
        right_center = "/c/en/right_center"
        left_leaves = {f"/c/en/left_{index:02d}" for index in range(9)}
        right_leaves = {f"/c/en/right_{index:02d}" for index in range(9)}
        nodes = left_leaves | right_leaves | {left_center, right_center}
        edges = [self.path_edge(left_center, right_center)]
        edges.extend(
            self.path_edge(left_center, leaf) for leaf in sorted(left_leaves)
        )
        edges.extend(
            self.path_edge(right_center, leaf) for leaf in sorted(right_leaves)
        )

        report = analyze_sampled_graph_quality(
            nodes,
            edges,
            min_distance_2_pairs=75,
            min_distance_3_pairs=75,
        )

        # 2 hops: C(9,2)+C(9,2)+9+9=90; 3 hops: 9*9=81.
        self.assertEqual(report["distance_2_pair_count"], 90)
        self.assertEqual(report["distance_3_pair_count"], 81)
        self.assertEqual(report["distance_2_or_3_pair_count"], 171)
        self.assertTrue(report["can_form_mixed_query_set"])

        stricter_report = analyze_sampled_graph_quality(
            nodes,
            edges,
            min_distance_2_pairs=91,
            min_distance_3_pairs=81,
        )
        self.assertFalse(stricter_report["can_form_mixed_query_set"])


class CandidateExportTests(unittest.TestCase):
    def test_sample_is_exported_and_analyzed_from_one_result(self) -> None:
        lines = [
            assertion_line("/r/IsA", "/c/en/dog", "/c/en/animal", 2.0),
            assertion_line("/r/RelatedTo", "/c/en/animal", "/c/en/dog", 1.0),
            assertion_line("/r/RelatedTo", "/c/en/dog", "/c/en/cat", 3.0),
        ]
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            root = Path(directory)
            source = root / "simulated.tsv.gz"
            with gzip.open(source, "wt", encoding="utf-8") as compressed:
                compressed.writelines(lines)
            output_dir = root / "processed"
            seeds = ("/c/en/dog", "/c/en/cat")
            report = run_candidate(source, output_dir, seeds, max_nodes=3)

            with (output_dir / "candidate_nodes.csv").open(newline="", encoding="utf-8") as file:
                node_rows = list(csv.DictReader(file))
            with (output_dir / "candidate_edges.csv").open(newline="", encoding="utf-8") as file:
                edge_rows = list(csv.DictReader(file))
            metadata = json.loads((output_dir / "candidate_metadata.json").read_text(encoding="utf-8"))

        self.assertEqual([row["concept"] for row in node_rows], ["/c/en/animal", "/c/en/cat", "/c/en/dog"])
        self.assertEqual(len(edge_rows), 2)
        self.assertEqual(json.loads(edge_rows[0]["relation"]), ["/r/IsA", "/r/RelatedTo"])
        self.assertEqual(report, metadata)
        self.assertEqual(report["quality"]["node_count"], 3)
        self.assertEqual(report["quality"]["edge_count"], 2)
        self.assertTrue(all(report["seeds_retained"].values()))
        self.assertEqual(report["status"], "candidate")


if __name__ == "__main__":
    unittest.main()
