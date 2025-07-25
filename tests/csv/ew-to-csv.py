#!/usr/bin/env python3

import csv
import sys

csw = csv.writer(sys.stdout)
n = None
for line in sys.stdin:
    count_str, perm = line.split()
    if n is None:
        n = len(perm)
        csw.writerow(['receipt', 'nonce'] + [chr(ord('A') + i) for i in range(n)])
    else:
        assert n == len(perm)

    rank = [0] * n
    for i in range(n):
        j = ord(perm[i]) - ord('A')
        assert j >= 0 and j < n
        rank[j] = i + 1

    for _ in range(int(count_str)):
        csw.writerow(['x','x'] + list(map(str, rank)))
