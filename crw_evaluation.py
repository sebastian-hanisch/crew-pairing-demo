"""Live-Rechnung: ein Netz unter gewählten Regeln lösen, Kostenzusammensetzung, Paarungen, Vergleich mit den Standardregeln, Meldungen."""
from __future__ import annotations

import time

import crw_constants as C
from crw_master import SLACK_BASE, column_generation, greedy_cover, solve_master_ip
from crw_network import generate_legs
from crw_pricing import coverable
from crw_rules import DRIVE, HEAD, Rules, covers, duty_cost, pairing_cost, to_objects

LEVER_KEYS = ("trains", "rest", "hotel", "cont", "span", "duties", "bases", "deadhead")


def make_rules(**kw) -> Rules:
    return Rules(**{**C.STD_RULES, **kw})


def bases_of(n_bases: int) -> tuple:
    return C.BASES_ALL if n_bases == 2 else (C.BASES_ALL[0],)


def rules_from_settings(s: dict) -> tuple:
    """s: Regler-Werte (rest, hotel, cont, span, duties, bases, deadhead) -> (Rules, Heimatbasen)."""
    rules = make_rules(rest=s["rest"], hotel=s["hotel"], max_cont=s["cont"], max_span=s["span"], max_duties=s["duties"], deadhead=s["deadhead"])
    return rules, bases_of(s["bases"])


def standard_settings(s: dict) -> dict:
    return {**s, "rest": C.STD_RULES["rest"], "hotel": C.STD_RULES["hotel"], "cont": C.STD_RULES["max_cont"], "span": C.STD_RULES["max_span"],
            "duties": C.STD_RULES["max_duties"], "bases": 2, "deadhead": True}


def build_trips(trains: int, seed: int) -> tuple:
    """Die Fahrten des Netzes, die unter den Standardregeln überdeckbar sind (nicht von den Reglern abhängig); der erste gültige Seed ab `seed`."""
    std = make_rules()
    for k in range(C.SEED_ATTEMPTS):
        raw = generate_legs(C.N_STATIONS, trains, C.DAYS, seed + k)
        trips = coverable(raw, std, C.BASES_ALL)
        if len(trips) >= C.MIN_TRIPS:
            return trips, seed + k, len(raw)
    raise ValueError(f"kein gültiger Seed ab {seed}")


def pairing_info(trips: list, base: int, duties: list, rules: Rules) -> dict:
    objs = to_objects(trips, duties)
    nights = sum(1 for i in range(1, len(objs)) if objs[i][0][0].o != base)
    return {"base": base, "duties": duties, "start": objs[0][0][0].dep, "end": objs[-1][-1][0].arr, "cost": pairing_cost(objs, base, rules), "nights": nights,
            "wage": sum(duty_cost(d, rules) for d in objs), "hotel": rules.hotel * nights, "n_covered": len(covers(duties))}


def solve_case(trips: list, rules: Rules, bases: tuple, ip_limit: float = C.IP_TIME_LIMIT) -> dict:
    """Spaltengenerierung (LP-Schranke), ganzzahlige Auswahl unter den erzeugten Spalten, gierige Auswahl."""
    n = len(trips)
    t0 = time.perf_counter()
    cg = column_generation(trips, rules, bases, penalty=C.PENALTY)
    t_cg = time.perf_counter() - t0
    t1 = time.perf_counter()
    ip, chosen, status = solve_master_ip(cg["columns"], cg["costs"], n, ip_limit)
    t_ip = time.perf_counter() - t1
    g_cost, g_chosen = greedy_cover(cg["columns"], cg["costs"], n)
    pairings, uncovered = [], []
    for c in chosen:
        base, duties = cg["columns"][c]
        if base == SLACK_BASE:
            uncovered.append(duties[0][0][0])
        else:
            pairings.append(pairing_info(trips, base, duties, rules))
    pairings.sort(key=lambda p: p["start"])
    wage = sum(p["wage"] for p in pairings)
    hotel = sum(p["hotel"] for p in pairings)
    return {"n": n, "lp": cg["lp"], "ip": ip, "ip_status": int(status), "greedy": g_cost, "pairings": pairings, "uncovered": sorted(uncovered),
            "wage": wage, "hotel": hotel, "penalty": C.PENALTY * len(uncovered), "nights": sum(p["nights"] for p in pairings),
            "iterations": cg["iterations"], "columns": len(cg["columns"]), "t_cg": t_cg, "t_pricing": cg["pricing_time"], "t_ip": t_ip,
            "greedy_uncovered": sum(1 for c in g_chosen if cg["columns"][c][0] == SLACK_BASE)}


def run_live(settings: dict) -> dict:
    """Gewähltes Regelwerk und Standardregeln auf demselben Netz."""
    t0 = time.perf_counter()
    trips, used_seed, n_raw = build_trips(settings["trains"], settings["seed"])
    rules, bases = rules_from_settings(settings)
    case = solve_case(trips, rules, bases)
    std_settings = standard_settings(settings)
    if std_settings == {**settings}:
        std = case
    else:
        srules, sbases = rules_from_settings(std_settings)
        std = solve_case(trips, srules, sbases)
    return {"trips": trips, "seed": used_seed, "n_raw": n_raw, "rules": rules, "bases": bases, "case": case, "std": std,
            "is_standard": std is case, "seconds": time.perf_counter() - t0}


def gap_pct(case: dict) -> float:
    return 100 * (case["ip"] / case["lp"] - 1) if case["lp"] else 0.0


def price_of_rules(run: dict) -> dict:
    """Kostenunterschied des gewählten Regelwerks gegen die Standardregeln auf diesem Netz."""
    c, s = run["case"], run["std"]
    return {"delta": c["ip"] - s["ip"], "delta_pct": 100 * (c["ip"] / s["ip"] - 1), "delta_pure": (c["ip"] - c["penalty"]) - (s["ip"] - s["penalty"]),
            "pure_pct": 100 * ((c["ip"] - c["penalty"]) / (s["ip"] - s["penalty"]) - 1), "new_uncovered": len(c["uncovered"]) - len(s["uncovered"])}


def rule_message(run: dict, sweep_pct: float | None = None, sweep_se: float | None = None, threshold: float = 1.0):
    """Drei Zustände: Regeländerung kostet über der Schwelle / liegt darunter (kein Befund) / Standardregeln. Rückgabe (Zustand, Text)."""
    if run["is_standard"]:
        return "standard", "Das sind die Standardregeln - alle Preise der Regeln werden gegen diesen Fall gemessen."
    p = price_of_rules(run)
    tail = f" Messreihe (20 Netze): Ø {sweep_pct:+.1f} ± {sweep_se:.1f} %." if sweep_pct is not None else ""
    unc = f" {p['new_uncovered']} Fahrten lassen sich zusätzlich nicht mehr überdecken (Strafe je Fahrt {C.PENALTY})." if p["new_uncovered"] > 0 else ""
    if abs(p["delta_pct"]) < threshold and p["new_uncovered"] == 0:
        return "none", f"Auf diesem Netz ändert das Regelwerk nichts Messbares ({p['delta_pct']:+.1f} %, unter der Lücke der ganzzahligen Auswahl von {threshold:.1f} %).{tail}"
    return "over", f"Das gewählte Regelwerk kostet auf diesem Netz {p['delta_pct']:+.1f} % gegen die Standardregeln ({p['delta']:+,.0f} Minutenäquivalente).{unc}{tail}".replace(",", " ")


def trip_assignment(run_case: dict, trips: list) -> list:
    """Je Fahrt: (Paarungsnummer, Modus) oder (None, None) für unüberdeckte; mitgefahrene Fahrten erscheinen zusätzlich als (Nummer, HEAD) in `riders`."""
    drive, riders = {}, []
    for pi, p in enumerate(run_case["pairings"]):
        for duty in p["duties"]:
            for idx, mode in duty:
                if mode == DRIVE:
                    drive.setdefault(idx, pi)
                else:
                    riders.append((idx, pi))
    return [(drive.get(i)) for i in range(len(trips))], riders
