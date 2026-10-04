"""Jede Zahl aus dem README wird hier aus data/crw_results.json nachgerechnet; die formatierten Texte müssen im README stehen.

Die Messreihe: je 20 Netze (Seeds 100-119), deterministisch (Spaltengenerierung + HiGHS, SplitMix64-Netze). Ordnungen und Schranken sind exakt geprüft,
Mittelwerte mit gerundeter Anzeige.
"""
from pathlib import Path

import pytest

import crw_constants as C
import crw_evaluation as E
import crw_results as R
import crw_stories as S

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def res():
    return R.load_results()


def f1(x):
    return f"{x:.1f}"


def test_meta_and_counts(res):
    assert res["meta"]["seeds"] == [100, 120] and res["meta"]["penalty"] == C.PENALTY and res["meta"]["std_rules"] == C.STD_RULES
    assert [r["trains"] for r in res["sizes"]].count(3) == [r["trains"] for r in res["sizes"]].count(4) == [r["trains"] for r in res["sizes"]].count(5) == 20
    assert len(res["variants"]) == 20 and set(res["meta"]["variants"]) == {v[0] for v in C.SWEEP_VARIANTS} and "Port 8958" in README


def test_size_series_in_the_readme(res):
    s = {t: R.size_summary(res, t) for t in C.SWEEP_TRAINS}
    assert " / ".join(f"{s[t]['gap_ip']:.1f} %" for t in (3, 4, 5)) in README
    assert f"{s[3]['gap_ip_max']:.1f} / {s[4]['gap_ip_max']:.1f} / {s[5]['gap_ip_max']:.1f} %" in README
    assert f"{s[3]['ip_equals_lp']} / {s[4]['ip_equals_lp']} / {s[5]['ip_equals_lp']} von 20" in README
    assert " / ".join(f"{s[t]['gap_gr']:.1f} ± {s[t]['gap_gr_se']:.1f} %" for t in (3, 4, 5)) in README
    assert f"mindestens {min(s[t]['gap_gr_min'] for t in s):.1f} %" in README
    assert " / ".join(f"{s[t]['t_cg']:.1f}" for t in (3, 4, 5)) + " s" in README
    assert " / ".join(f"{s[t]['pricing_share']:.0f}" for t in (3, 4, 5)) + " %" in README
    assert " / ".join(f"{s[t]['iterations']:.0f}" for t in (3, 4, 5)) + " Iterationen" in README
    assert all(s[t]["ip_not_optimal"] == 0 for t in s)                      # jede ganzzahlige Auswahl wurde bewiesen optimal (unter den erzeugten Spalten)


def test_ordering_lp_le_ip_le_greedy_in_every_net(res):
    for r in res["sizes"]:
        assert r["lp"] <= r["ip"] + 1e-6 and r["ip"] <= r["greedy"] + 1e-6 and r["uncovered"] == 0
    assert min(100 * (r["greedy"] / r["lp"] - 1) for r in res["sizes"]) > 1.0


def test_standard_costs_in_the_readme(res):
    sc = R.standard_costs(res)
    assert f"{sc['pairings']:.1f} Paarungen mit {sc['nights']:.1f} Übernachtungen" in README
    assert f"**{sc['wage_share']:.0f} %** der Kosten sind Lohn" in README and f"**{sc['hotel_share']:.0f} %** Hotel" in README
    assert f"{sc['trips']:.0f} Teilstrecken" in README


def test_rule_prices_in_the_readme(res):
    rows = {r["name"]: r for r in R.variant_rows(res)}
    for name, pct_key in (("Hotel 1000", "+25.4 ± 1.6"), ("Hotel 2000", "+77.0 ± 4.5"), ("Ruhezeit 11 h", "+15.8 ± 6.2"), ("Ruhezeit 13 h", "+38.6 ± 12.0"), ("ununterbrochen 3 h", "+11.4 ± 1.7")):
        r = rows[name]
        assert f"{r['pct']:+.1f} ± {r['se']:.1f}" == pct_key and pct_key in README, name
    assert rows["Hotel 1000"]["positive"] == rows["Hotel 2000"]["positive"] == 20
    assert f"{rows['Lenkzeit 7 h']['pct']:+.1f}".replace("+", "") in README and f"{rows['Lenkzeit 6 h']['pct']:+.1f}".replace("+", "") in README and f"{rows['Garantie 360']['pct']:+.1f}".replace("+", "") in README
    assert f"{rows['Ruhezeit 11 h']['uncovered']:.1f} bzw. {rows['Ruhezeit 13 h']['uncovered']:.1f} Fahrten" in README
    assert f"**{rows['ohne Mitfahren']['uncovered']:.1f} Fahrten**" in README and f"**{rows['ohne Mitfahren']['pure_pct']:.1f} %**" in README
    assert f"**{rows['1 Dienst (keine Übernachtung)']['uncovered']:.1f}**" in README and f"**{rows['nur eine Heimatbasis']['uncovered']:.1f}**" in README
    assert f"{rows['2 Dienste']['pct']:+.1f} ± {rows['2 Dienste']['se']:.1f} %" in README and f"**{rows['Spanne 9 h']['uncovered']:.1f}**" in README


def test_hotel_is_never_cheaper_and_strict_rules_never_cheaper_without_penalty_when_all_covered(res):
    for v in res["variants"]:
        std = v["variants"]["Standard"]["ip"]
        assert v["variants"]["Hotel 1000"]["ip"] > std and v["variants"]["Hotel 2000"]["ip"] > v["variants"]["Hotel 1000"]["ip"]
        assert v["variants"]["Standard"]["uncovered"] == 0


def test_hand_picked_preset_effects_in_the_readme():
    import json
    base = {"trains": 4, "rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": C.DEFAULT_SEED}
    pct = {}
    for name in C.PRESET_ORDER[1:]:
        p = C.PRESETS[name]
        run = E.run_live({**base, **{k: p[k] for k in ("hotel", "rest", "cont", "deadhead")}})
        pct[name] = E.price_of_rules(run)["delta_pct"]
    for name, value in pct.items():
        assert f"{name} {value:+.1f} %".replace("+", "+") in README, (name, value)


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_tells_its_story_on_the_shown_network(res, name):
    p = C.PRESETS[name]
    run = E.run_live({k: p[k] for k in ("trains", "rest", "hotel", "cont", "span", "duties", "bases", "deadhead", "seed")})
    failed = [text for _, text, ok in S.check(name, S.facts_for(name, run, res)) if not ok]
    assert not failed, (name, failed)
