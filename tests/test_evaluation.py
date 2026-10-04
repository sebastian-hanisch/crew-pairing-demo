"""Live-Rechnung auf echten kleinen Netzen: Planung gültig und vollständig, Kostenzusammensetzung, Preis der Regeln, Meldungen."""
import pytest

import crw_constants as C
import crw_evaluation as E
from crw_rules import DRIVE, check_pairing, to_objects

STD = {"trains": 3, "rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500}


@pytest.fixture(scope="module")
def std_run():
    return E.run_live(STD)


@pytest.fixture(scope="module")
def hotel_run():
    return E.run_live({**STD, "hotel": 2000})


def test_standard_settings_and_rules_roundtrip():
    rules, bases = E.rules_from_settings(STD)
    assert rules == E.make_rules() and bases == C.BASES_ALL
    assert E.standard_settings({**STD, "hotel": 2000, "bases": 1, "deadhead": False}) == STD
    assert E.bases_of(1) == (0,) and E.bases_of(2) == (0, 6)
    assert E.make_rules(hotel=999).hotel == 999 and E.make_rules().max_cont == 270


def test_standard_run_is_valid_complete_and_ordered(std_run):
    run = std_run
    case, trips = run["case"], run["trips"]
    assert run["is_standard"] and run["case"] is run["std"] and len(trips) >= C.MIN_TRIPS
    assert case["lp"] <= case["ip"] + 1e-6 <= case["greedy"] + 1e-6 and case["uncovered"] == [] and case["ip_status"] == 0
    for p in case["pairings"]:
        assert check_pairing(to_objects(trips, p["duties"]), p["base"], run["rules"])
    driven = {i for p in case["pairings"] for d in p["duties"] for i, m in d if m == DRIVE}
    assert driven == set(range(len(trips)))                                    # jede Fahrt wird gefahren
    assert abs(case["ip"] - (case["wage"] + case["hotel"] + case["penalty"])) < 1e-6      # Kosten = Lohn + Hotel + Strafe
    assert case["nights"] == sum(p["nights"] for p in case["pairings"]) and case["hotel"] == run["rules"].hotel * case["nights"]
    assert [p["start"] for p in case["pairings"]] == sorted(p["start"] for p in case["pairings"])


def test_run_is_deterministic(std_run):
    again = E.run_live(STD)
    assert again["case"]["ip"] == std_run["case"]["ip"] and again["case"]["lp"] == std_run["case"]["lp"] and again["case"]["greedy"] == std_run["case"]["greedy"]


def test_expensive_hotel_costs_more_and_never_more_nights(std_run, hotel_run):
    assert not hotel_run["is_standard"] and hotel_run["std"]["ip"] == std_run["case"]["ip"]
    price = E.price_of_rules(hotel_run)
    assert price["delta"] > 0 and price["delta_pct"] > 5 and price["new_uncovered"] == 0 and abs(price["delta"] - price["delta_pure"]) < 1e-6
    assert hotel_run["case"]["nights"] <= std_run["case"]["nights"]


def test_no_deadhead_pairings_contain_only_driven_trips():
    run = E.run_live({**STD, "trains": 4, "deadhead": False})
    assert all(m == DRIVE for p in run["case"]["pairings"] for d in p["duties"] for _, m in d)
    assert any(m != DRIVE for p in run["std"]["pairings"] for d in p["duties"] for _, m in d)      # die Standardregeln nutzen das Mitfahren tatsächlich


def test_rule_price_is_not_exact_for_small_effects():
    """Die ganzzahlige Lösung wählt nur unter den erzeugten Spalten: strengere Regeln können auf einem Netz knapp billiger ausfallen (Seed 500, 4 Züge) -
    deshalb liegt die Meldungsschwelle bei der Lücke der Messreihe und nicht bei Null."""
    run = E.run_live({**STD, "trains": 4, "deadhead": False})
    assert E.price_of_rules(run)["pure_pct"] > -5.0
    assert run["case"]["ip"] >= run["case"]["lp"] - 1e-6


def test_gap_and_assignment_helpers(std_run):
    case, trips = std_run["case"], std_run["trips"]
    assert abs(E.gap_pct(case) - 100 * (case["ip"] / case["lp"] - 1)) < 1e-12 and E.gap_pct(case) >= -1e-6
    owner, riders = E.trip_assignment(case, trips)
    assert len(owner) == len(trips) and all(o is not None for o in owner)
    assert all(0 <= pi < len(case["pairings"]) for _, pi in riders)


def test_three_message_states(std_run, hotel_run):
    state, text = E.rule_message(std_run)
    assert state == "standard" and "Standardregeln" in text
    state, text = E.rule_message(hotel_run, 77.0, 4.5)
    assert state == "over" and "Messreihe" in text and "+77.0 ± 4.5" in text
    fake = {**hotel_run, "case": {**hotel_run["case"], "ip": hotel_run["std"]["ip"] * 1.004, "uncovered": hotel_run["std"]["uncovered"], "penalty": hotel_run["std"]["penalty"]}}
    assert E.rule_message(fake)[0] == "none"                                   # unter 1 % und nichts unüberdeckt
    fake2 = {**fake, "case": {**fake["case"], "uncovered": [0], "penalty": C.PENALTY}}
    assert E.rule_message(fake2)[0] == "over" and "zusätzlich nicht mehr überdecken" in E.rule_message(fake2)[1]


def test_build_trips_is_independent_of_the_rule_levers():
    a, _, _ = E.build_trips(3, 500)
    b = E.run_live({**STD, "rest": 780})["trips"]
    assert a == b
