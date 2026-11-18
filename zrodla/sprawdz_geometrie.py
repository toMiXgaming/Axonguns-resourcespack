#!/usr/bin/env python3
"""Sprawdza, czy model broni z gen.py jest jedną bryłą: żadna część nie wisi w powietrzu.

Dwa elementy są połączone, gdy ich prostopadłościany (w przestrzeni broni) się stykają albo nakładają
(tolerancja 0.03 jednostki). Elementy obrócone (spust) liczą się z zapasem 0.3. Wynik: lista grup,
a pierwsza (największa) to korpus broni; każda inna grupa to część, która wisi.
Użycie: python3 zrodla/sprawdz_geometrie.py [broń ...]  (bez argumentów: tanie bronie)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen

TOL = 0.03


def grupy(g):
    els = [e for e in g.els if not e.name.startswith('dt_')]
    box = []
    for e in els:
        pad = 0.3 if e.rot else 0.0
        box.append((e.lo - pad, e.hi + pad))
    parent = list(range(len(els)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(els)):
        for j in range(i + 1, len(els)):
            lo = max_(box[i][0], box[j][0])
            hi = min_(box[i][1], box[j][1])
            if all(hi[k] - lo[k] >= -TOL for k in range(3)):
                parent[find(i)] = find(j)
    out = {}
    for i, e in enumerate(els):
        out.setdefault(find(i), []).append(e.name)
    return sorted(out.values(), key=len, reverse=True)


def max_(a, b):
    return [max(x, y) for x, y in zip(a, b)]


def min_(a, b):
    return [min(x, y) for x, y in zip(a, b)]


if __name__ == '__main__':
    names = sys.argv[1:] or list(gen.TANIE)
    bad = 0
    for n in names:
        gr = grupy(gen.BUILDERS[n]())
        if len(gr) == 1:
            print('%-11s ok, %d części w jednej bryle' % (n, len(gr[0])))
        else:
            bad += 1
            print('%-11s WISZĄ: %s' % (n, gr[1:]))
    sys.exit(1 if bad else 0)
