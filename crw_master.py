"""Master der Spaltengenerierung: Mengenüberdeckung über Paarungen (LP, ganzzahlig über die erzeugten Spalten, gierig). Strafspalten lassen Fahrten
unüberdeckt, wenn eine Regel sie unüberdeckbar macht."""
from __future__ import annotations

import time

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import csc_matrix

from crw_pricing import price_all
from crw_rules import DRIVE, covers, pairing_cost, to_objects


def cover_matrix(columns: list, n: int):
    rows, cols = [], []
    for c, (base, duties) in enumerate(columns):
        for t in covers(duties):
            rows.append(t)
            cols.append(c)
    return csc_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, len(columns)))


def solve_master_lp(columns, costs, n):
    A = cover_matrix(columns, n)
    res = linprog(np.array(costs, dtype=float), A_ub=-A, b_ub=-np.ones(n), bounds=(0, None), method="highs")
    assert res.status == 0, res.message
    return res.fun, res.x, -res.ineqlin.marginals


def initial_columns(trips, r, bases):
    cols, seen = [], set()
    for j in range(len(trips)):
        duals = np.zeros(len(trips))
        duals[j] = 1e5
        found = price_all(trips, duals, r, bases, limit=1)
        assert found, f"Fahrt {j} nicht ueberdeckbar"
        _, b, d = found[0]
        key = (b, tuple(tuple(x) for x in d))
        if key not in seen:
            seen.add(key)
            cols.append((b, d))
    return cols


SLACK_BASE = -1          # Kennung der Strafspalten (Fahrt bleibt unüberdeckt)


def column_generation(trips, r, bases, max_iter=300, limit=30, penalty=None):
    """penalty=None: jede Fahrt muss überdeckbar sein (sonst Fehler). penalty=P: für jede Fahrt eine Strafspalte mit Kosten P (Fahrt unüberdeckt)."""
    n = len(trips)
    if penalty is None:
        columns = initial_columns(trips, r, bases)
        costs = [pairing_cost(to_objects(trips, d), b, r) for b, d in columns]
    else:
        columns = [(SLACK_BASE, [[(j, DRIVE)]]) for j in range(n)]
        costs = [float(penalty)] * n
    known = {(b, tuple(tuple(x) for x in d)) for b, d in columns}
    t_price, it = 0.0, 0
    for it in range(1, max_iter + 1):
        lp, x, duals = solve_master_lp(columns, costs, n)
        t0 = time.perf_counter()
        new = price_all(trips, duals, r, bases, limit)
        t_price += time.perf_counter() - t0
        added = 0
        for rc, b, d in new:
            key = (b, tuple(tuple(x) for x in d))
            if key in known:
                continue
            known.add(key)
            columns.append((b, d))
            costs.append(pairing_cost(to_objects(trips, d), b, r))
            added += 1
        if not added:
            break
    lp, x, duals = solve_master_lp(columns, costs, n)
    return {"lp": lp, "columns": columns, "costs": costs, "iterations": it, "pricing_time": t_price, "x": x, "duals": duals}


def solve_master_ip(columns, costs, n, time_limit=30.0):
    A = cover_matrix(columns, n)
    res = milp(np.array(costs, dtype=float), constraints=LinearConstraint(A, lb=np.ones(n), ub=np.inf), integrality=np.ones(len(columns)),
               bounds=Bounds(0, 1), options={"time_limit": time_limit})
    if res.x is None:
        return None, [], res.status
    return float(res.fun), [i for i, v in enumerate(res.x) if v > 0.5], res.status      # status 0 = optimal


def greedy_cover(columns, costs, n):
    cover = [covers(d) for _, d in columns]
    unc = set(range(n))
    chosen = []
    while unc:
        best = min((c for c in range(len(columns)) if cover[c] & unc), key=lambda c: (costs[c] / len(cover[c] & unc), c))
        chosen.append(best)
        unc -= cover[best]
    for c in sorted(chosen, key=lambda c: -costs[c]):
        rest = [x for x in chosen if x != c]
        if rest and set().union(*[cover[x] for x in rest]) >= set(range(n)):
            chosen = rest
    return sum(costs[c] for c in chosen), chosen
