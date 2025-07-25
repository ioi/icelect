#!/usr/bin/env python3
# Icelect - Trivial test cases
# (c) 2025 Martin Mareš <mj@ucw.cz>

from itertools import permutations, product
import unittest

from icelect.results import Results


class ResultTests(unittest.TestCase):
    """Trivial test cases for computation of results."""

    def test_all_permutations(self) -> None:
        res = Results(5, list(map(list, permutations(range(5)))))
        self.assertIsNone(res.condorcet_winner)
        self.assertEqual(res.weak_condorcet_winners, [0,1,2,3,4])
        self.assertEqual(res.schulze_order, [[0,1,2,3,4]])

    def test_condorcet(self) -> None:
        ranks = list(map(list, permutations(range(5))))
        ranks_0before1 = [r for r in ranks if r[0] < r[1]]
        res = Results(5, ranks_0before1)
        self.assertEqual(res.condorcet_winner, 0)
        self.assertEqual(res.weak_condorcet_winners, [0])
        self.assertEqual(res.schulze_order, [[0], [2,3,4], [1]])

    def test_all_with_ties(self) -> None:
        res = Results(5, list(map(list, product(range(5), repeat=5))))
        self.assertIsNone(res.condorcet_winner)
        self.assertEqual(res.weak_condorcet_winners, [0,1,2,3,4])
        self.assertEqual(res.schulze_order, [[0,1,2,3,4]])

    def test_condorcet_with_ties(self) -> None:
        ranks = list(map(list, product(range(5), repeat=5)))
        ranks_0before1 = [r for r in ranks if r[0] < r[1]]
        res = Results(5, ranks_0before1)
        self.assertEqual(res.condorcet_winner, 0)
        self.assertEqual(res.weak_condorcet_winners, [0])
        self.assertEqual(res.schulze_order, [[0], [2,3,4], [1]])


if __name__ == "__main__":
    unittest.main()
