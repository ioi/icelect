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

class Schulze:

    num_candidates: int
    ranks: list[list[int]]

    beats: np.ndarray
    weights: np.ndarray
    strengths: np.ndarray

    def __init__(self, num_candidates: int, ranks: list[list[int]]):
        self.num_candidates = num_candidates
        self.ranks = ranks
        self.calc_beats()
        self.calc_weights()
        self.calc_strengths()

    def calc_beats(self):
        self.beats = np.zeros((self.num_candidates, self.num_candidates), dtype='i4')

        for rank in self.ranks:
            assert len(rank) == self.num_candidates
            for i in range(self.num_candidates):
                for j in range(self.num_candidates):
                    if i != j and rank[i] < rank[j]:
                        self.beats[i,j] += 1

    def calc_weights(self):
        self.weights = self.beats - self.beats.T

    def calc_strengths(self):
        self.strengths = self.weights.copy()
        s = self.strengths

        for k in range(self.num_candidates):
            for i in range(self.num_candidates):
                if i != k:
                    for j in range(self.num_candidates):
                        if i != j and j != k:
                            s[i,j] = max(s[i,j], min(s[i,k], s[k,j]))
