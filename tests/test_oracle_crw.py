"""Orakel-Tests: eigene Regelprüfung nach README, Vollaufzählung aller Paarungen (je Überdeckungsmenge die billigste) gegen Pricer, Spaltengenerierung, MIP und gierige Auswahl."""
import numpy as np
import pytest
from scipy.optimize import LinearConstraint, Bounds, linprog, milp

from crw_api import C


def conn_ok(a, b, r):
    if a.d != b.o:
        return False
    if a.train >= 0 and a.train == b.train and b.seq == a.seq + 1:
        return b.dep >= a.arr
    return b.dep - a.arr >= r.min_conn


def duty_cost_or_none(chain, r):
    """Dienst nach den README-Regeln: Anschlüsse, Spanne, Lenkzeit, ununterbrochene Lenkzeit (Lücke ab 30 min oder Mitfahren unterbricht), mindestens eine gefahrene Fahrt."""
    if not any(m == "D" for _, m in chain) or (not r.deadhead and any(m == "H" for _, m in chain)):
        return None
    if any(not conn_ok(chain[i - 1][0], chain[i][0], r) for i in range(1, len(chain))):
        return None
    span = chain[-1][0].arr - chain[0][0].dep
    if span > r.max_span or sum(t.arr - t.dep for t, m in chain if m == "D") > r.max_drive:
        return None
    cont = 0
    for i, (t, m) in enumerate(chain):
        if m == "H":
            cont = 0
            continue
        if i and t.dep - chain[i - 1][0].arr >= r.break_gap:
            cont = 0
        cont += t.arr - t.dep
        if cont > r.max_cont:
            return None
    return max(r.guarantee, span)


def all_columns(trips, r, base):
    """{Überdeckungsmenge: kleinste Kosten} über alle Paarungen einer Heimatbasis (eigene Aufzählung, Dienste zuerst, dann Folgen)."""
    n, modes = len(trips), (("D", "H") if r.deadhead else ("D",))
    duties = []

    def ext(chain, idx):
        c = duty_cost_or_none(chain, r)
        if c is not None:
            f, l = chain[0][0], chain[-1][0]
            duties.append((f.o, f.dep, l.d, l.arr, c, frozenset(i for i, (_, m) in zip(idx, chain) if m == "D")))
        for j in range(idx[-1] + 1, n):
            if conn_ok(chain[-1][0], trips[j], r) and trips[j].arr - chain[0][0].dep <= r.max_span:
                for m in modes:
                    ext(chain + [(trips[j], m)], idx + [j])

    for i in range(n):
        for m in modes:
            ext([(trips[i], m)], [i])
    best = {}

    def rec(last, k, cost, cov):
        if last[2] == base and (cov not in best or cost < best[cov]):
            best[cov] = cost
        if k < r.max_duties:
            for d in duties:
                if d[0] == last[2] and r.rest <= d[1] - last[3] <= r.max_rest:
                    rec(d, k + 1, cost + d[4] + (r.hotel if d[0] != base else 0), cov | d[5])

    for d in duties:
        if d[0] == base:
            rec(d, 1, d[4], d[5])
    return best


def lp_and_ip(cols, n, penalty):
    cols = list(cols) + [(frozenset([j]), float(penalty)) for j in range(n)]
    A = np.zeros((n, len(cols)))
    for c, (cov, _) in enumerate(cols):
        A[list(cov), c] = 1
    cost = np.array([c for _, c in cols], dtype=float)
    lp = linprog(cost, A_ub=-A, b_ub=-np.ones(n), bounds=(0, None), method="highs").fun
    ip = milp(cost, constraints=LinearConstraint(A, lb=np.ones(n), ub=np.inf), integrality=np.ones(len(cols)), bounds=Bounds(0, 1)).fun
    return lp, ip


@pytest.mark.parametrize("deadhead,rest,span", [(True, 540, 660), (False, 540, 660), (True, 780, 540)])
def test_duty_checker_agrees_with_the_readme_rules_on_random_chains(deadhead, rest, span):
    rng = np.random.default_rng(3)
    r = C.Rules(deadhead=deadhead, rest=rest, max_span=span, max_cont=210)
    trips = C.generate_instance(4, 8, 2, 11, hop=40, max_hops=3)
    for _ in range(400):
        idx = sorted(rng.choice(len(trips), size=int(rng.integers(1, 5)), replace=False).tolist())
        chain = [(trips[i], "D" if rng.random() < 0.7 else "H") for i in idx]
        mine = duty_cost_or_none(chain, r)
        assert (mine is not None) == C.duty_ok(chain, r)
        if mine is not None:
            assert mine == C.duty_cost(chain, r)


@pytest.mark.parametrize("seed", [0, 4, 7, 10])
def test_pricer_lp_ip_and_greedy_against_full_enumeration(seed):
    rng = np.random.default_rng(seed)
    r = C.Rules(max_duties=int(rng.choice([2, 3])), deadhead=bool(seed % 2), hotel=int(rng.choice([500, 1000])))
    bases = (0, 3)
    trips = C.coverable(C.generate_instance(4, 7, 2, seed), r, bases)
    n = len(trips)
    assert 6 <= n <= 14
    cols = {b: all_columns(trips, r, b) for b in bases}
    for _ in range(3):
        duals = rng.integers(0, 2500, size=n).astype(float) * (rng.random(n) < 0.8)
        for b in bases:
            brute = min((c - duals[list(cov)].sum() for cov, c in cols[b].items()), default=None)
            found = C.price_pairings(trips, duals, r, b, limit=10**6, tol=-1e18)
            assert (brute is None) == (not found)
            if found:
                assert abs(min(x[0] for x in found) - brute) < 1e-6
    lp_all, ip_all = lp_and_ip([(cov, c) for b in bases for cov, c in cols[b].items()], n, 5000)
    cg = C.column_generation(trips, r, bases, penalty=5000)
    ip_cg = C.solve_master_ip(cg["columns"], cg["costs"], n)[0]
    g_cost, g_chosen = C.greedy_cover(cg["columns"], cg["costs"], n)
    assert cg["lp"] == pytest.approx(lp_all, rel=1e-6)
    assert lp_all - 1e-6 <= ip_all <= ip_cg + 1e-6 and ip_cg <= g_cost + 1e-6
    assert set().union(*[C.covers(cg["columns"][c][1]) for c in g_chosen]) == set(range(n))
