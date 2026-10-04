"""Gezielte Tests für Stellen, die der Fehler-Einbau-Test (tools/mutation_check.py) zuerst nicht fand: Regelgrenzen auf der Minute, gierige Auswahl gegen eine
unabhängige Referenz, Spalten ohne Duplikate, Meldung genau auf der Schwelle."""
import random
from dataclasses import replace

import crw_constants as K
import crw_evaluation as E
from crw_master import column_generation, greedy_cover
from crw_rules import DRIVE, Rules, Trip, check_pairing, duty_ok

R = Rules()


def drive(*legs):
    """Dienst aus gefahrenen Fahrten (Abfahrt, Ankunft) auf einer Strecke 0 <-> 1 abwechselnd."""
    out, o = [], 0
    for dep, arr in legs:
        out.append((Trip(o, 1 - o, dep, arr), DRIVE))
        o = 1 - o
    return out


def test_continuous_driving_limit_is_inclusive():
    assert duty_ok(drive((0, 270)), R) and not duty_ok(drive((0, 271)), R)
    assert duty_ok(drive((0, 270), (300, 500)), R)                                    # 30 min Lücke = Pause, danach wieder 200 min
    assert not duty_ok(drive((0, 270), (299, 500)), R)                                # 29 min Lücke: keine Pause, 270 + 201 ununterbrochen


def test_total_driving_limit_is_inclusive():
    legs = [(0, 160), (190, 350), (380, 540)]                                          # 160 min Lenkzeit je Fahrt, 30 min Lücken: 480 gesamt
    assert duty_ok(drive(*legs), R)
    assert not duty_ok(drive((0, 160), (190, 350), (380, 541)), R)                    # 481 gesamt


def test_span_limit_is_inclusive_when_driving_is_not_the_binding_rule():
    loose = replace(R, max_drive=10_000)
    assert duty_ok(drive((0, 200), (230, 430), (460, 660)), loose) and not duty_ok(drive((0, 200), (230, 430), (460, 661)), loose)


def test_rest_window_between_duties_is_inclusive_on_both_sides():
    base = lambda gap: [[(Trip(0, 1, 0, 60), DRIVE)], [(Trip(1, 0, 60 + gap, 120 + gap), DRIVE)]]
    assert check_pairing(base(R.rest), 0, R) and not check_pairing(base(R.rest - 1), 0, R)
    assert check_pairing(base(R.max_rest), 0, R) and not check_pairing(base(R.max_rest + 1), 0, R)


def greedy_reference(columns, costs, n, ratio=True, prune=True):
    cover = [{i for d in c[1] for i, _ in d} for c in columns]
    unc, chosen = set(range(n)), []
    while unc:
        key = (lambda c: (costs[c] / len(cover[c] & unc), c)) if ratio else (lambda c: (costs[c], c))
        best = min((c for c in range(len(columns)) if cover[c] & unc), key=key)
        chosen.append(best)
        unc -= cover[best]
    if prune:
        for c in sorted(chosen, key=lambda c: -costs[c]):
            rest = [x for x in chosen if x != c]
            if rest and set().union(*[cover[x] for x in rest]) >= set(range(n)):
                chosen = rest
    return sum(costs[c] for c in chosen)


def sets_to_columns(sets):
    return [(0, [[(i, DRIVE) for i in s]]) for s in sets]


def test_greedy_matches_an_independent_reference_on_hand_picked_and_random_instances():
    cases = [([(0, 2, 3), (1, 2), (2, 3), (2,)], [10, 12, 7, 3], 22),            # ohne Streichen würde 25 herauskommen (Spalte (2,) ist überflüssig)
             ([(0,), (3,), (0, 2, 3), (0, 1, 3), (0, 1, 2)], [12, 3, 6, 12, 6], 12),   # Kosten je neu überdeckter Fahrt, nicht rohe Kosten (die ergäben 9)
             ([(2,), (2, 3), (0,), (0, 1, 3), (0, 2)], [11, 5, 11, 12, 4], 16)]   # teuerste zuerst streichen (aufsteigend ergäbe 17)
    for sets, costs, expected in cases:
        cols = sets_to_columns(sets)
        assert greedy_cover(cols, costs, 4)[0] == expected == greedy_reference(cols, costs, 4)
    rng = random.Random(1)
    for _ in range(300):
        n, k = 5, rng.randint(3, 6)
        sets = [tuple(sorted(rng.sample(range(n), rng.randint(1, 3)))) for _ in range(k)]
        if set().union(*map(set, sets)) != set(range(n)):
            continue
        costs = [rng.randint(2, 12) for _ in range(k)]
        cols = sets_to_columns(sets)
        cost, chosen = greedy_cover(cols, costs, n)
        assert cost == greedy_reference(cols, costs, n) and cost == sum(costs[c] for c in chosen)
        assert set().union(*[set(sets[c]) for c in chosen]) == set(range(n))
        assert all(set().union(*[set(sets[x]) for x in chosen if x != c]) != set(range(n)) for c in chosen)     # nichts Überflüssiges


def test_column_generation_creates_no_duplicate_columns():
    trips, _, _ = E.build_trips(3, 501)
    cg = column_generation(trips, E.make_rules(), K.BASES_ALL, penalty=5000)
    keys = [(b, tuple(tuple(x) for x in d)) for b, d in cg["columns"]]
    assert len(keys) == len(set(keys))


def test_message_on_the_exact_threshold_counts_as_a_finding():
    run = E.run_live({"trains": 3, "rest": 540, "hotel": 2000, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500})
    delta = E.price_of_rules(run)["delta_pct"]
    assert E.rule_message(run, threshold=delta)[0] == "over"            # genau so groß wie die Schwelle: gemeldet
    assert E.rule_message(run, threshold=delta + 1e-9)[0] == "none" or run["case"]["uncovered"]
