# Icelect - Computing results using Schulze method
# (c) 2025 Martin Mareš <mj@ucw.cz>

# See also:
#
# Markus Schulze: A new monotonic, clone-independent, reversal symmetric,
# and Condorcet-consistent single-winner election method.
# Social Choice and Welfare, volume 36, number 2, page 267–303, 2011.
# Preliminary version in Voting Matters, 17:9-19, 2003.
#
# https://electowiki.org/wiki/Schulze_method

import numpy as np
from typing import Any


class Results:

    num_options: int
    ballots: list[list[int]]    # each ballot is a list of ranks

    beats: np.ndarray
    condorcet_winner: int | None
    weak_condorcet_winners: list[int]
    weights: np.ndarray
    strengths: np.ndarray
    stronger: np.ndarray
    schulze_order: list[list[int]]

    def __init__(self, num_options: int, ballots: list[list[int]]):
        self.num_options = num_options
        self.ballots = ballots
        self._calc_beats()
        self._calc_condorcet()
        self._calc_weights()
        self._calc_strengths()
        self._calc_winners()

    def _calc_beats(self):
        """
        Compute the beat matrix: beats[i,j] tells how many ballots prefer i to j.
        """

        self.beats = np.zeros((self.num_options, self.num_options), dtype=np.int32)

        for rank in self.ballots:
            assert len(rank) == self.num_options
            for i in range(self.num_options):
                for j in range(self.num_options):
                    if i != j and rank[i] < rank[j]:
                        self.beats[i,j] += 1

    def _calc_condorcet(self):
        """
        Compute the strong Condorcet winner and the set of weak Condorcet winners.
        """

        self.condorcet_winner = None
        self.weak_condorcet_winners = []
        for i in range(self.num_options):
            if all(self.beats[i,j] > self.beats[j,i] or i == j for j in range(self.num_options)):
                self.condorcet_winner = i
            if all(self.beats[i,j] >= self.beats[j,i] or i == j for j in range(self.num_options)):
                self.weak_condorcet_winners.append(i)

    def _calc_weights(self):
        """
        Compute beat weights: if i beats j, then weights[i,j] = beats[i,j] - beats[j,i].
        """

        self.weights = np.maximum(self.beats - self.beats.T, 0)

    def _calc_strengths(self):
        """
        Compute path strengths: strengths[i,j] is the maximum strength over all beat paths
        from i to j, where the strength of a path is the minimum weight on its edges.
        """

        self.strengths = self.weights.copy()
        s = self.strengths

        for k in range(self.num_options):
            for i in range(self.num_options):
                if i != k:
                    for j in range(self.num_options):
                        if i != j and j != k:
                            s[i,j] = max(s[i,j], min(s[i,k], s[k,j]))

        self.stronger = self.strengths > self.strengths.T

    def _calc_winners(self):
        """
        Compute Schulze layers. The first layer is the winners.
        """

        self.schulze_order = []
        remains = set(range(self.num_options))

        while remains:
            layer = remains.copy()

            for i in remains:
                for j in remains:
                    if self.stronger[i,j]:
                        layer.discard(j)

            self.schulze_order.append(sorted(layer))
            remains -= layer

    def debug(self):
        print(f'Number of options: {self.num_options}')
        print('Ballots:')
        for r in self.ballots:
            print(f'\t{r}')
        print('Beats:', self.beats)
        print('Condorcet winner:', self.condorcet_winner)
        print('Weak Condorcet winners:', self.weak_condorcet_winners)
        print('Weights:', self.weights)
        print('Path strengths:', self.strengths)
        print('Stronger than relation:', self.stronger)
        print('Schulze order:', self.schulze_order)

    def to_json(self) -> Any:
        def jsonify_matrix(mat: np.ndarray) -> list[list[int]]:
            return [
                [int(mat[i,j]) for j in range(self.num_options)]
                for i in range(self.num_options)
            ]

        return {
            'beats': jsonify_matrix(self.beats),
            'condorcet_winner': self.condorcet_winner,
            'weak_condorcet_winners': self.weak_condorcet_winners,
            'weights': jsonify_matrix(self.weights),
            'strengths': jsonify_matrix(self.strengths),
            'schulze_order': self.schulze_order,
        }
