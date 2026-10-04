"""Preset-Kriterien mit künstlichen Werten: jedes Kriterium kippt einzeln an seiner Schwelle (DEMO-PLAYBOOK: Preset-Disziplin)."""
import pytest

import crw_constants as C
import crw_stories as S

GOOD = {"uncovered": 0, "greedy": 120.0, "ip": 100.0, "nights": 5, "std_nights": 6, "delta_pct": 30.0, "new_uncovered": 0, "sweep_pct": 40.0, "sweep_se": 5.0, "sweep_gap_gr": 19.0}

# Kennung -> (Schlüssel, falscher Wert knapp daneben, richtiger Wert knapp darauf)
FLIPS = {
    "Standard": {"all_covered": ("uncovered", 1, 0), "greedy_worse": ("greedy", 100.0, 100.01), "sweep_greedy_gap": ("sweep_gap_gr", 9.9, 10.0), "has_nights": ("nights", 0, 1)},
    "Teures Hotel": {"cost_up": ("delta_pct", 9.9, 10.0), "fewer_nights": ("nights", 7, 6), "sweep_significant": ("sweep_pct", 19.9, 20.0)},
    "Lange Ruhezeit": {"cost_up": ("delta_pct", 3.9, 4.0), "sweep_significant": ("sweep_pct", 10.0, 10.1)},
    "Strenge Lenkzeit": {"cost_up": ("delta_pct", 3.9, 4.0), "sweep_significant": ("sweep_pct", 10.0, 10.1), "covered": ("uncovered", 1, 0)},
    "Ohne Mitfahren": {"cost_up_or_uncovered": ("delta_pct", 3.9, 4.0), "sweep_significant": ("sweep_pct", 10.0, 10.1)},
}


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_good_facts_satisfy_every_criterion_of_the_preset(name):
    assert all(ok for _, _, ok in S.check(name, GOOD)) and S.PRESET_VARIANT[name]


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_each_criterion_flips_alone_at_its_threshold(name):
    ids = [cid for cid, _, _ in S.check(name, GOOD)]
    assert set(ids) == set(FLIPS[name])
    for cid, (key, bad, good) in FLIPS[name].items():
        for value, expect in ((bad, False), (good, True)):
            facts = {**GOOD, key: value}
            outcome = {c: ok for c, _, ok in S.check(name, facts)}
            assert outcome[cid] is expect, (name, cid, key, value)
            assert all(ok for c, ok in outcome.items() if c != cid), (name, cid, "ein anderes Kriterium kippte mit")


def test_alternatives_of_or_criteria():
    lange = {**GOOD, "delta_pct": 0.5, "new_uncovered": 1}
    assert dict((c, ok) for c, _, ok in S.check("Lange Ruhezeit", lange))["cost_up"]
    mit = {**GOOD, "delta_pct": 0.5, "new_uncovered": 1}
    assert dict((c, ok) for c, _, ok in S.check("Ohne Mitfahren", mit))["cost_up_or_uncovered"]
    assert not dict((c, ok) for c, _, ok in S.check("Ohne Mitfahren", {**GOOD, "delta_pct": 0.5, "new_uncovered": 0}))["cost_up_or_uncovered"]


def test_every_criterion_has_a_readable_text():
    assert all(len(text) > 15 for crit in S.CRITERIA.values() for _, text, _ in crit)
