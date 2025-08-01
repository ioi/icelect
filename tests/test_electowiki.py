#!/usr/bin/env python3
# Icelect - Test cases from the Electowiki
# (c) 2025 Martin Mareš <mj@ucw.cz>

import unittest

from icelect.results import Results


class SchulzeTests(unittest.TestCase):
    """Test cases of the Schulze method from Electowiki."""

    def schulze_winners(self, votes: list[tuple[int, str]], expected_order: list[str]) -> None:
        n = len(votes[0][1])
        options = [chr(ord('A') + i) for i in range(n)]

        ranks = []
        for count, perm in votes:
            assert len(perm) == n
            rank = [0] * n
            for i in range(n):
                j = ord(perm[i]) - ord('A')
                assert j >= 0 and j < n
                rank[j] = i + 1
            ranks += [rank] * count

        res = Results(n, ranks)
        # res.debug()

        order = [set(options[w] for w in layer) for layer in res.schulze_order]
        self.assertEqual(order, [set(layer) for layer in expected_order])


    def test_1(self) -> None:
        self.schulze_winners([
            (5, 'ACBED'),
            (5, 'ADECB'),
            (8, 'BEDAC'),
            (3, 'CABED'),
            (7, 'CAEBD'),
            (2, 'CBADE'),
            (7, 'DCEBA'),
            (8, 'EBADC'),
        ], ['E', 'A', 'C', 'B', 'D'])

    def test_2(self) -> None:
        self.schulze_winners([
            (5, 'ACBD'),
            (2, 'ACDB'),
            (3, 'ADCB'),
            (4, 'BACD'),
            (3, 'CBDA'),
            (3, 'CDBA'),
            (1, 'DACB'),
            (5, 'DBAC'),
            (4, 'DCBA'),
        ], ['D', 'A', 'C', 'B'])

    def test_3(self) -> None:
        self.schulze_winners([
            (3, 'ABDEC'),
            (5, 'ADEBC'),
            (1, 'ADECB'),
            (2, 'BADEC'),
            (2, 'BDECA'),
            (4, 'CABDE'),
            (6, 'CBADE'),
            (2, 'DBECA'),
            (5, 'DECAB'),
        ], ['B', 'A', 'D', 'E', 'C'])

    def test_4(self) -> None:
        self.schulze_winners([
            (3, 'ABCD'),
            (2, 'DABC'),
            (2, 'DBCA'),
            (2, 'CBDA'),
        ], ['BD', 'AC'])


if __name__ == "__main__":
    unittest.main()
