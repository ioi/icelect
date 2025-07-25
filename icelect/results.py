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

class Results:

    num_options: int
    ranks: list[list[int]]

    beats: np.ndarray
    condorcet_winner: int | None
    weak_condrocet_winners: list[int]
    weights: np.ndarray
    strengths: np.ndarray
    stronger: np.ndarray
    schulze_order: list[list[int]]

    def __init__(self, num_options: int, ranks: list[list[int]]):
        self.num_options = num_options
        self.ranks = ranks
        self.calc_beats()
        self.calc_condorcet()
        self.calc_weights()
        self.calc_strengths()
        self.calc_winners()

    def calc_beats(self):
        self.beats = np.zeros((self.num_options, self.num_options), dtype='i4')

        for rank in self.ranks:
            assert len(rank) == self.num_options
            for i in range(self.num_options):
                for j in range(self.num_options):
                    if i != j and rank[i] < rank[j]:
                        self.beats[i,j] += 1

    def calc_condorcet(self):
        self.condorcet_winner = None
        self.weak_condorcet_winners = []
        for i in range(self.num_options):
            if all(self.beats[i,j] > self.beats[j,i] or i == j for j in range(self.num_options)):
                self.condorcet_winner = i
            if all(self.beats[i,j] >= self.beats[j,i] or i == j for j in range(self.num_options)):
                self.weak_condorcet_winners.append(i)

    def calc_weights(self):
        self.weights = np.maximum(self.beats - self.beats.T, 0)

    def calc_strengths(self):
        self.strengths = self.weights.copy()
        s = self.strengths

        for k in range(self.num_options):
            for i in range(self.num_options):
                if i != k:
                    for j in range(self.num_options):
                        if i != j and j != k:
                            s[i,j] = max(s[i,j], min(s[i,k], s[k,j]))

        self.stronger = self.strengths > self.strengths.T

    def calc_winners(self):
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
        print('Ranks:')
        for r in self.ranks:
            print(f'\t{r}')
        print('Beats:', self.beats)
        print('Condorcet winner:', self.condorcet_winner)
        print('Weak Condorcet winners:', self.weak_condorcet_winners)
        print('Weights:', self.weights)
        print('Path strengths:', self.strengths)
        print('Stronger than relation:', self.stronger)
        print('Schulze order:', self.schulze_order)
