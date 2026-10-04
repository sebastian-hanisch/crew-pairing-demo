"""Mini-Instanz-Tests für Regelwerk, Pricing und Master (von Hand gerechnet und gegen Vollaufzählung, DEMO-PLAYBOOK 1b)."""
import numpy as np

from crw_api import C

R = C.Rules()
BASES = (0, 3)


def T(o, d, dep, arr):
    return C.Trip(o, d, dep, arr)


def enumerate_pairings(trips, r, base):
    n = len(trips)
    out = []
    modes = (C.DRIVE, C.HEAD) if r.deadhead else (C.DRIVE,)

    def duties_from(first):
        res = []

        def extend(duty):
            objs = [(trips[i], m) for i, m in duty]
            if C.duty_ok(objs, r):
                res.append(list(duty))
            for j in range(duty[-1][0] + 1, n):
                if C.connect_ok(trips[duty[-1][0]], trips[j], r):
                    for m in modes:
                        extend(duty + [(j, m)])

        for i in first:
            for m in modes:
                extend([(i, m)])
        return res

    def grow(done):
        last = trips[done[-1][-1][0]]
        if last.d == base:
            out.append([list(d) for d in done])
        if len(done) >= r.max_duties:
            return
        for d in duties_from([i for i in range(n) if trips[i].o == last.d and r.rest <= trips[i].dep - last.arr <= r.max_rest]):
            grow(done + [d])

    for d in duties_from([i for i in range(n) if trips[i].o == base]):
        grow([d])
    return [p for p in out if C.check_pairing(C.to_objects(trips, p), base, r)]


def hand():
    # Station 0 = Basis; Strecke 0-1-2. Tag 1: 0->2 (06:00-07:30), 2->0 (08:30-10:00); Tag 2: 2->1 (06:00-06:45)
    return [T(0, 2, 360, 450), T(2, 0, 510, 600), T(2, 1, 1800, 1845)]


def test_duty_rules_by_hand():
    a, b = hand()[0], hand()[1]
    assert C.duty_ok([(a, C.DRIVE), (b, C.DRIVE)], R)
    assert C.duty_cost([(a, C.DRIVE), (b, C.DRIVE)], R) == 300                                  # Spanne 06:00-10:00 = 240 min liegt unter der Garantie 300
    assert C.duty_cost([(T(0, 4, 0, 180), C.DRIVE), (T(4, 0, 210, 390), C.DRIVE)], R) == 390     # Spanne 390 über der Garantie
    assert not C.duty_ok([(a, C.HEAD), (b, C.HEAD)], R)                                         # ohne gefahrene Fahrt kein Dienst
    assert not C.duty_ok([(a, C.HEAD), (b, C.DRIVE)], C.Rules(deadhead=False))                  # Mitfahren abgeschaltet
    long1 = [(T(0, 4, 0, 180), C.DRIVE), (T(4, 0, 195, 375), C.DRIVE)]                           # 180 + 180 = 360 Lenkzeit mit nur 15 min Lücke: ununterbrochen 360 > 270
    assert not C.duty_ok(long1, R)
    long2 = [(T(0, 4, 0, 180), C.DRIVE), (T(4, 0, 210, 390), C.DRIVE)]                           # 30 min Lücke = Pause: ok (Lenkzeit 360 <= 480, Spanne 390 <= 660)
    assert C.duty_ok(long2, R)
    head_break = [(T(0, 4, 0, 180), C.DRIVE), (T(4, 0, 195, 375), C.HEAD)]                       # Mitfahren zählt als Pause, aber ohne weitere gefahrene Fahrt zählt nur die erste
    assert C.duty_ok(head_break, R)


def test_pairing_with_hotel_and_deadhead_by_hand():
    t = hand()
    day1 = [[(t[0], C.DRIVE), (t[1], C.DRIVE)]]
    assert C.check_pairing(day1, 0, R) and C.pairing_cost(day1, 0, R) == 300
    over = [[(t[0], C.DRIVE)], [(t[2], C.DRIVE)]]          # Dienst 1 endet an Station 2, Dienst 2 beginnt dort 24 h später, endet an Station 1: keine Basis
    assert not C.check_pairing(over, 0, R)
    t2 = hand() + [T(1, 0, 1900, 1990)]
    over2 = [[(t2[0], C.DRIVE)], [(t2[2], C.DRIVE), (t2[3], C.DRIVE)]]
    assert C.check_pairing(over2, 0, R) and C.pairing_cost(over2, 0, R) == 300 + 300 + 500
    assert not C.check_pairing([[(t[0], C.DRIVE)], [(t[1], C.DRIVE)]], 0, R)                        # Ruhezeit 60 min
    assert not C.check_pairing([[(t[1], C.DRIVE)]], 0, R)                                          # beginnt nicht an der Basis


def test_price_pairings_equals_brute_force_for_random_duals():
    rng = np.random.default_rng(5)
    for seed in (10, 11, 4):
        base = 0
        trips = C.coverable(C.generate_instance(4, 7, 2, seed), R, (base,))
        assert 7 <= len(trips) <= 11, len(trips)
        pairings = enumerate_pairings(trips, R, base)
        assert pairings
        for _ in range(5):
            duals = rng.integers(0, 3000, size=len(trips)).astype(float)
            brute = min(C.pairing_cost(C.to_objects(trips, p), base, R) - sum(duals[i] for i in C.covers(p)) for p in pairings)
            found = C.price_pairings(trips, duals, R, base, limit=1000, tol=-1e18)
            assert found and abs(found[0][0] - brute) < 1e-6, (seed, found[0][0] if found else None, brute)


def test_pricing_without_deadhead_equals_brute_force_too():
    rng = np.random.default_rng(6)
    r = C.Rules(deadhead=False)
    trips = C.coverable(C.generate_instance(4, 7, 2, 10), r, (0,))
    pairings = enumerate_pairings(trips, r, 0)
    duals = rng.integers(0, 3000, size=len(trips)).astype(float)
    brute = min(C.pairing_cost(C.to_objects(trips, p), 0, r) - sum(duals[i] for i in C.covers(p)) for p in pairings)
    found = C.price_pairings(trips, duals, r, 0, limit=1000, tol=-1e18)
    assert abs(found[0][0] - brute) < 1e-6


def test_column_generation_lp_equals_lp_over_all_pairings_for_two_bases():
    trips = C.coverable(C.generate_instance(4, 7, 2, 4), R, BASES)
    assert 7 <= len(trips) <= 12, len(trips)
    n = len(trips)
    cg = C.column_generation(trips, R, BASES)
    cols = [(b, p) for b in BASES for p in enumerate_pairings(trips, R, b)]
    costs = [C.pairing_cost(C.to_objects(trips, p), b, R) for b, p in cols]
    full, _, _ = C.solve_master_lp(cols, costs, n)
    assert abs(cg["lp"] - full) < 1e-6
    ip_all = C.solve_master_ip(cols, costs, n)[0]
    ip_cg = C.solve_master_ip(cg["columns"], cg["costs"], n)[0]
    assert ip_all >= full - 1e-6 and ip_cg >= ip_all - 1e-6


def test_every_priced_column_passes_the_independent_checker():
    trips = C.coverable(C.generate_instance(4, 20, 3, 9), R, BASES)
    duals = np.full(len(trips), 600.0)
    for rc, b, d in C.price_all(trips, duals, R, BASES, limit=30):
        assert C.check_pairing(C.to_objects(trips, d), b, R)
        assert abs(rc - (C.pairing_cost(C.to_objects(trips, d), b, R) - 600.0 * len(C.covers(d)))) < 1e-6
