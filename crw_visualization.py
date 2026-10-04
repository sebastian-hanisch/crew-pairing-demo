"""Plotly-Figuren der Crew-Pairing-Demo. Alle Achsen fest (fixedrange), damit Touch-Scrollen nicht am Chart hängen bleibt."""
from __future__ import annotations

import plotly.graph_objects as go

import crw_constants as C
from crw_evaluation import trip_assignment
from crw_rules import DRIVE, HEAD


def _lock(fig, height=380, **layout):
    fig.update_layout(height=height, margin=dict(l=50, r=20, t=40, b=55), font=dict(size=12),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0), **layout)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _hour_ticks(max_min):
    vals = list(range(0, int(max_min) + 1, 360))
    return vals, [f"T{v // 1440 + 1} {v % 1440 // 60:02d}:00" for v in vals]


def build_time_space(trips: list, case: dict) -> go.Figure:
    """Zeit-Weg-Diagramm: jede Teilstrecke als Linie von (Abfahrt, Station) nach (Ankunft, Station), gefärbt nach der Paarung, die sie fährt;
    mitgefahrene Strecken gepunktet in der Farbe der mitfahrenden Paarung, unüberdeckte rot gestrichelt."""
    owner, riders = trip_assignment(case, trips)
    fig = go.Figure()
    groups = {}
    for i, t in enumerate(trips):
        key = ("unc",) if owner[i] is None else ("drive", owner[i])
        groups.setdefault(key, []).append(t)
    for key, ts in sorted(groups.items(), key=lambda kv: (kv[0][0] != "unc", kv[0][-1] if len(kv[0]) > 1 else -1)):
        xs, ys = [], []
        for t in ts:
            xs += [t.dep, t.arr, None]
            ys += [t.o, t.d, None]
        if key[0] == "unc":
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color="#c0392b", width=3, dash="dash"), name="unüberdeckt", hoverinfo="name"))
        else:
            pi = key[1]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLORS[pi % len(C.COLORS)], width=3), name=f"Paarung {pi + 1}", legendgroup=f"p{pi}",
                                     hovertemplate=f"Paarung {pi + 1}<extra></extra>"))
    for idx, pi in riders:
        t = trips[idx]
        fig.add_trace(go.Scatter(x=[t.dep, t.arr], y=[t.o, t.d], mode="lines", line=dict(color=C.COLORS[pi % len(C.COLORS)], width=1.5, dash="dot"), legendgroup=f"p{pi}",
                                 showlegend=False, hovertemplate=f"Paarung {pi + 1} fährt mit<extra></extra>"))
    horizon = C.DAYS * 1440
    vals, labels = _hour_ticks(horizon)
    fig.update_xaxes(tickvals=vals, ticktext=labels, range=[240, horizon], title_text="Zeit")
    fig.update_yaxes(tickvals=list(range(C.N_STATIONS)), ticktext=[f"Station {s}" + (" (Basis)" if s in C.BASES_ALL else "") for s in range(C.N_STATIONS)],
                     range=[-0.3, C.N_STATIONS - 0.7])
    return _lock(fig, 420)


def build_gantt(trips: list, case: dict, rules) -> go.Figure:
    """Dienstplan: je Paarung eine Zeile; gefahrene Teilstrecken dunkel, mitgefahrene hell, Ruhezeit (Nacht) grau."""
    fig = go.Figure()
    drive = {"x": [], "base": [], "y": [], "text": []}
    ride = {"x": [], "base": [], "y": [], "text": []}
    rest = {"x": [], "base": [], "y": [], "text": []}
    for pi, p in enumerate(case["pairings"]):
        prev_end = None
        for duty in p["duties"]:
            if prev_end is not None and duty[0][0] is not None:
                start = trips[duty[0][0]].dep
                rest["x"].append(start - prev_end)
                rest["base"].append(prev_end)
                rest["y"].append(pi)
                rest["text"].append(f"Ruhezeit {(start - prev_end) // 60} h {(start - prev_end) % 60:02d} min")
            for idx, mode in duty:
                t = trips[idx]
                tgt = drive if mode == DRIVE else ride
                tgt["x"].append(t.arr - t.dep)
                tgt["base"].append(t.dep)
                tgt["y"].append(pi)
                tgt["text"].append(f"Station {t.o} → {t.d}, {C.fmt_hm(t.dep)}–{C.fmt_hm(t.arr)}" + (" (gefahren)" if mode == DRIVE else " (mitgefahren)"))
            prev_end = trips[duty[-1][0]].arr
    for name, d, color in (("Ruhezeit", rest, "#d5dae1"), ("mitgefahren", ride, "#9bc1e8"), ("gefahren", drive, "#2a6fb0")):
        if d["x"]:
            fig.add_trace(go.Bar(x=d["x"], base=d["base"], y=d["y"], orientation="h", marker_color=color, name=name, text=None, hovertext=d["text"], hoverinfo="text",
                                 marker_line=dict(color="white", width=0.5)))
    n = len(case["pairings"])
    horizon = C.DAYS * 1440
    vals, labels = _hour_ticks(horizon)
    fig.update_xaxes(tickvals=vals, ticktext=labels, range=[240, horizon + 120], title_text="Zeit")
    fig.update_yaxes(tickvals=list(range(n)), ticktext=[f"Paarung {i + 1} (Basis {p['base']})" for i, p in enumerate(case["pairings"])], autorange="reversed")
    fig.update_layout(barmode="overlay")
    return _lock(fig, max(260, 60 + 28 * n))


def build_cost_bars(case: dict, std: dict | None, is_standard: bool) -> go.Figure:
    """Kostenzusammensetzung: Lohn, Hotel, Strafe - für das gewählte Regelwerk und (falls verschieden) die Standardregeln."""
    names, wage, hotel, pen = [], [], [], []
    for label, c in (("Standardregeln", std if not is_standard else None), ("gewähltes Regelwerk" if not is_standard else "Standardregeln (gewählt)", case)):
        if c is None:
            continue
        names.append(label)
        wage.append(c["wage"])
        hotel.append(c["hotel"])
        pen.append(c["penalty"])
    fig = go.Figure()
    for name, vals, color in (("Lohn (Garantie/Spanne)", wage, "#2a6fb0"), ("Hotel", hotel, "#c77700"), ("Strafe für unüberdeckte Fahrten", pen, "#c0392b")):
        fig.add_trace(go.Bar(x=vals, y=names, orientation="h", name=name, marker_color=color, text=[C.fmt_cost(v) if v else "" for v in vals], textposition="inside",
                             textfont=dict(color="white")))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title_text="Kosten (Minutenäquivalente)")
    return _lock(fig, 200 if len(names) > 1 else 160)


def build_rule_prices(rows: list) -> go.Figure:
    """Preisliste der Regeln, deren Änderung alle Fahrten überdeckt lässt: Kostenänderung gegen Standard (Mittel ± Standardfehler über die Netze). Varianten, die Fahrten
    unüberdeckt lassen, sind mit der Strafe nicht vergleichbar und stehen nur in der Tabelle."""
    rows = [r for r in rows if r["name"] != "Standard" and r["uncovered"] < 0.05]
    rows = sorted(rows, key=lambda r: r["pct"])
    fig = go.Figure(go.Bar(x=[r["pct"] for r in rows], y=[r["name"] for r in rows], orientation="h", error_x=dict(type="data", array=[r["se"] for r in rows], visible=True),
                           marker_color="#2a6fb0", text=[f"{r['pct']:+.1f} %" for r in rows], textposition="outside", hovertemplate="%{y}: %{x:+.1f} %<extra></extra>"))
    fig.update_xaxes(title_text="Kostenänderung gegen die Standardregeln (%), Mittel ± Standardfehler", range=[0, max(r["pct"] + r["se"] for r in rows) * 1.25])
    return _lock(fig, 130 + 40 * len(rows))


def build_gap_chart(summaries: dict) -> go.Figure:
    """Je Netzgröße: Abstand der ganzzahligen und der gierigen Lösung zur LP-Schranke (Mittel, %)."""
    xs = [f"{k} Züge" for k in summaries]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=xs, y=[s["gap_ip"] for s in summaries.values()], name="ganzzahlig über den erzeugten Spalten", marker_color="#2e7d4f",
                         text=[f"{s['gap_ip']:.1f} %" for s in summaries.values()], textposition="outside"))
    fig.add_trace(go.Bar(x=xs, y=[s["gap_gr"] for s in summaries.values()], name="gierig", marker_color="#c77700",
                         error_y=dict(type="data", array=[s["gap_gr_se"] for s in summaries.values()], visible=True),
                         text=[f"{s['gap_gr']:.1f} %" for s in summaries.values()], textposition="outside"))
    fig.update_yaxes(title_text="Abstand zur LP-Schranke (%)", rangemode="tozero")
    fig.update_layout(barmode="group")
    return _lock(fig, 340)
