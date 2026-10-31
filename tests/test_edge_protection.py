"""Behavioral checks for static protection selection."""

import copy
import random
import unittest

import networkx as nx

from src.edge_protection import protection_budget, select_protected_edges


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        self.graph = nx.Graph()
        self.graph.add_edges_from([("b", "a"), ("b", "c"), ("c", "d"), ("b", "d")])
        nx.set_edge_attributes(self.graph, 100, "weight")
        self.graph.nodes["a"]["metadata"] = [1, 2]

    def test_budget_boundaries(self):
        for m, f, expected in [(3417, .05, 170), (100, .29, 29), (3, 0, 0), (3, 1, 3), (0, .05, 0)]:
            with self.subTest(m=m, f=f):
                self.assertEqual(protection_budget(m, f), expected)
        for fraction in [-.1, 1.1, float("nan"), float("inf"), True]:
            with self.subTest(fraction=fraction), self.assertRaises(ValueError):
                protection_budget(10, fraction)

    def test_expected_degree_ranking_and_tie(self):
        # b-c and b-d tie at 5; a-b and c-d score 4.
        self.assertEqual(select_protected_edges(self.graph, "degree", .25), (("b", "c"),))

    def test_exact_unweighted_betweenness(self):
        # Leaf a-b is uniquely highest despite its smaller degree sum.
        self.graph["a"]["b"]["weight"] = 10000
        self.assertEqual(select_protected_edges(self.graph, "betweenness", .25), (("a", "b"),))
        cycle = nx.cycle_graph(["a", "b", "c", "d"])
        self.assertEqual(select_protected_edges(cycle, "betweenness", .25), (("a", "b"),))

    def test_insertion_order_reproducibility_and_no_mutation(self):
        before = copy.deepcopy(self.graph)
        state = random.getstate()
        reverse = nx.Graph()
        reverse.add_edges_from((v, u) for u, v in reversed(list(self.graph.edges())))
        for strategy in ["random", "degree", "betweenness"]:
            with self.subTest(strategy=strategy):
                selected = select_protected_edges(self.graph, strategy, .5, seed=17)
                self.assertEqual(selected, select_protected_edges(reverse, strategy, .5, seed=17))
                self.assertEqual(len(selected), 2)
                self.assertEqual(len(set(selected)), 2)
                self.assertTrue(all(u < v and self.graph.has_edge(u, v) for u, v in selected))
                self.assertEqual(select_protected_edges(self.graph, strategy, 0), ())
                self.assertEqual(len(select_protected_edges(self.graph, strategy, 1)), 4)
                self.assertEqual(select_protected_edges(nx.Graph(), strategy), ())
        self.assertTrue(nx.utils.graphs_equal(self.graph, before))
        self.assertEqual(state, random.getstate())

    def test_cache_validation_and_equivalence(self):
        scores = {tuple(sorted(e)): s for e, s in
                  nx.edge_betweenness_centrality(self.graph, weight=None).items()}
        self.assertEqual(select_protected_edges(self.graph, "betweenness", .5),
                         select_protected_edges(self.graph, "betweenness", .5, betweenness=scores))
        for invalid in [{}, {**scores, ("x", "y"): .1}, {**scores, ("a", "b"): float("nan")},
                        {**scores, ("a", "b"): 2}, {**scores, ("b", "a"): .1}]:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                select_protected_edges(self.graph, "betweenness", betweenness=invalid)

    def test_invalid_graph_and_strategy(self):
        for graph in [nx.DiGraph(), nx.MultiGraph(), nx.path_graph(3), nx.Graph([("a", "a")])]:
            with self.subTest(graph=graph), self.assertRaises(ValueError):
                select_protected_edges(graph, "random")
        with self.assertRaises(ValueError):
            select_protected_edges(self.graph, "unknown")
        with self.assertRaises(ValueError):
            select_protected_edges(self.graph, "random", seed=None)


if __name__ == "__main__":
    unittest.main()
