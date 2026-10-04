"""Vorgerechnete Messreihe (data/crw_results.json, erzeugt mit tools/sweep.py): Größenreihe und Regelpreise. Die App rechnet sie nie live."""
from __future__ import annotations

import json
import statistics as st
from pathlib import Path

import crw_constants as C

ROOT = Path(__file__).resolve().parent


def load_results(path=None) -> dict:
    return json.loads(Path(path or ROOT / C.RESULTS_FILE).read_text(encoding="utf-8"))


def mean_se(xs) -> tuple:
    xs = list(xs)
    return st.mean(xs), (st.stdev(xs) / len(xs) ** 0.5 if len(xs) > 1 else float("nan"))


def size_rows(res: dict, trains: int) -> list:
    return [r for r in res["sizes"] if r["trains"] == trains]


def size_summary(res: dict, trains: int) -> dict:
    rows = size_rows(res, trains)
    gap_ip = [100 * (r["ip"] / r["lp"] - 1) for r in rows]
    gap_gr = [100 * (r["greedy"] / r["lp"] - 1) for r in rows]
    gm, gse = mean_se(gap_gr)
    return {"n_nets": len(rows), "trips": st.mean(r["n"] for r in rows), "lp": st.mean(r["lp"] for r in rows), "ip": st.mean(r["ip"] for r in rows),
            "gap_ip": st.mean(gap_ip), "gap_ip_max": max(gap_ip), "ip_equals_lp": sum(1 for g in gap_ip if g < 1e-6), "gap_gr": gm, "gap_gr_se": gse,
            "gap_gr_min": min(gap_gr), "gap_gr_max": max(gap_gr), "iterations": st.mean(r["iterations"] for r in rows), "columns": st.mean(r["columns"] for r in rows),
            "t_cg": st.median(r["t_cg"] for r in rows), "pricing_share": 100 * sum(r["t_pricing"] for r in rows) / sum(r["t_cg"] for r in rows),
            "ip_not_optimal": sum(1 for r in rows if r["ip_status"] != 0), "nights": st.mean(r["nights"] for r in rows),
            "hotel_share": 100 * sum(r["hotel"] for r in rows) / sum(r["ip"] for r in rows)}


def variant_rows(res: dict) -> list:
    """Je Regelvariante: Kostenänderung gegen Standard (inkl. und ohne Strafe), unüberdeckte Fahrten, Paarungen, Übernachtungen (alle über die Netze gemittelt)."""
    pen = res["meta"]["penalty"]
    out = []
    for name in res["meta"]["variants"]:
        rel, pure, unc, pair, nights = [], [], [], [], []
        for v in res["variants"]:
            a, b = v["variants"][name], v["variants"]["Standard"]
            rel.append(100 * (a["ip"] / b["ip"] - 1))
            pure.append(100 * ((a["ip"] - pen * a["uncovered"]) / (b["ip"] - pen * b["uncovered"]) - 1))
            unc.append(a["uncovered"])
            pair.append(a["pairings"])
            nights.append(a["nights"])
        m, se = mean_se(rel)
        out.append({"name": name, "pct": m, "se": se, "positive": sum(1 for x in rel if x > 1e-9), "n": len(rel), "pure_pct": st.mean(pure), "uncovered": st.mean(unc),
                    "pairings": st.mean(pair), "nights": st.mean(nights), "all_covered": sum(1 for x in unc if x == 0)})
    return out


def variant_row(res: dict, name: str) -> dict:
    return next(r for r in variant_rows(res) if r["name"] == name)


def standard_costs(res: dict) -> dict:
    """Wie setzen sich die Standardkosten zusammen (Mittel über die Netze): Lohn, Hotel; Übernachtungen und Paarungen je Netz."""
    rows = [v["variants"]["Standard"] for v in res["variants"]]
    tot = sum(r["ip"] for r in rows)
    return {"wage_share": 100 * sum(r["wage"] for r in rows) / tot, "hotel_share": 100 * sum(r["hotel"] for r in rows) / tot,
            "nights": st.mean(r["nights"] for r in rows), "pairings": st.mean(r["pairings"] for r in rows), "trips": st.mean(v["n"] for v in res["variants"]),
            "ip": st.mean(r["ip"] for r in rows)}


def lever_to_variant(settings: dict) -> str | None:
    """Welche Messreihen-Variante entspricht genau einem geänderten Regler? None, wenn mehrere oder eine Kombination geändert sind."""
    diffs = []
    std = {"rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True}
    for k, v in std.items():
        if settings[k] != v:
            diffs.append((k, settings[k]))
    if not diffs:
        return "Standard"
    if len(diffs) > 1:
        return None
    return {("rest", 660): "Ruhezeit 11 h", ("rest", 780): "Ruhezeit 13 h", ("hotel", 1000): "Hotel 1000", ("hotel", 2000): "Hotel 2000",
            ("cont", 180): "ununterbrochen 3 h", ("span", 540): "Spanne 9 h", ("duties", 1): "1 Dienst (keine Übernachtung)", ("duties", 2): "2 Dienste",
            ("bases", 1): "nur eine Heimatbasis", ("deadhead", False): "ohne Mitfahren"}.get(diffs[0])
