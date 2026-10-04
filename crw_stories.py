"""Abnahmekriterien der Presets: jedes Preset erzählt eine Geschichte, die am gezeigten Netz UND an der Messreihe überprüfbar ist.

Die Kriterien sind reine Funktionen einfacher Zahlen (`facts`), damit Tests sie mit künstlichen Werten einzeln an ihrer Schwelle kippen können;
`facts_for` baut die Zahlen aus einer Live-Rechnung und der Ergebnisdatei. `tools/preset_search.py` sucht damit einen Seed außerhalb der
Messreihen-Seeds, bei dem alle Kriterien aller Presets gelten.
"""
from __future__ import annotations

import crw_evaluation as E
import crw_results as R

CRITERIA = {
    "Standard": [
        ("all_covered", "alle Fahrten sind überdeckt", lambda f: f["uncovered"] == 0),
        ("greedy_worse", "gierig liegt über der ganzzahligen Lösung", lambda f: f["greedy"] > f["ip"] + 1e-6),
        ("sweep_greedy_gap", "Messreihe: gierig im Mittel mindestens 10 % über der LP-Schranke", lambda f: f["sweep_gap_gr"] >= 10.0),
        ("has_nights", "mindestens eine Übernachtung im Standard (sonst gäbe es keine Hotelkosten)", lambda f: f["nights"] >= 1),
    ],
    "Teures Hotel": [
        ("cost_up", "Kosten steigen um mindestens 10 % gegen Standard", lambda f: f["delta_pct"] >= 10.0),
        ("fewer_nights", "höchstens so viele Übernachtungen wie im Standard", lambda f: f["nights"] <= f["std_nights"]),
        ("sweep_significant", "Messreihe: Hotel 2000 kostet über 2 Standardfehlern", lambda f: f["sweep_pct"] > 2 * f["sweep_se"] and f["sweep_pct"] >= 20.0),
    ],
    "Lange Ruhezeit": [
        ("cost_up", "Kosten steigen um mindestens 4 % (mehr als die Lücke der ganzzahligen Auswahl) oder Fahrten bleiben unüberdeckt", lambda f: f["delta_pct"] >= 4.0 or f["new_uncovered"] > 0),
        ("sweep_significant", "Messreihe: Ruhezeit 13 h kostet über 2 Standardfehlern", lambda f: f["sweep_pct"] > 2 * f["sweep_se"]),
    ],
    "Strenge Lenkzeit": [
        ("cost_up", "Kosten steigen um mindestens 4 % (mehr als die Lücke der ganzzahligen Auswahl)", lambda f: f["delta_pct"] >= 4.0),
        ("sweep_significant", "Messreihe: ununterbrochen 3 h kostet über 2 Standardfehlern", lambda f: f["sweep_pct"] > 2 * f["sweep_se"]),
        ("covered", "alle Fahrten bleiben überdeckt", lambda f: f["uncovered"] == 0),
    ],
    "Ohne Mitfahren": [
        ("cost_up_or_uncovered", "Kosten steigen um mindestens 4 % oder Fahrten bleiben unüberdeckt", lambda f: f["delta_pct"] >= 4.0 or f["new_uncovered"] > 0),
        ("sweep_significant", "Messreihe: ohne Mitfahren kostet über 2 Standardfehlern", lambda f: f["sweep_pct"] > 2 * f["sweep_se"]),
    ],
}

PRESET_VARIANT = {"Standard": "Standard", "Teures Hotel": "Hotel 2000", "Lange Ruhezeit": "Ruhezeit 13 h", "Strenge Lenkzeit": "ununterbrochen 3 h", "Ohne Mitfahren": "ohne Mitfahren"}


def facts_for(name: str, run: dict, res: dict) -> dict:
    """Zahlen eines Live-Laufs (Netz und Regelwerk des Presets) zusammen mit den Messreihen-Zahlen der zugehörigen Variante."""
    c, s = run["case"], run["std"]
    price = E.price_of_rules(run)
    row = R.variant_row(res, PRESET_VARIANT[name])
    sizes = R.size_summary(res, 4)
    return {"uncovered": len(c["uncovered"]), "greedy": c["greedy"], "ip": c["ip"], "nights": c["nights"], "std_nights": s["nights"], "delta_pct": price["delta_pct"],
            "new_uncovered": price["new_uncovered"], "sweep_pct": row["pct"], "sweep_se": row["se"] if row["se"] == row["se"] else 0.0, "sweep_gap_gr": sizes["gap_gr"]}


def check(name: str, facts: dict) -> list:
    """[(Kennung, Text, erfüllt)] aller Kriterien des Presets."""
    return [(cid, text, bool(fn(facts))) for cid, text, fn in CRITERIA[name]]
