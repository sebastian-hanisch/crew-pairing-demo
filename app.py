"""Crew Pairing: Besatzungseinsatz im Zugverkehr - interaktive Fall-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Zweiter Baustein der Reihe Bahn/Schienenverkehr nach dem Taktfahrplan (taktfahrplan-demo): Die Züge fahren, jetzt braucht jede Fahrt eine Besatzung.
Aus Zugumläufen, Heimatbasen und einem Regelwerk (Lenk-, Ruhezeit, Dienstspanne, Hotel) entstehen Paarungen - Dienstfolgen über mehrere Tage, die an der
Heimatbasis beginnen und enden. Verfahren: Spaltengenerierung mit Ressourcen-Kürzestem-Weg als Pricing, ganzzahlige Auswahl über die erzeugten Spalten, gierig.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import crw_constants as C
import crw_results as R
from crw_evaluation import gap_pct, price_of_rules, rule_message, run_live, solve_case
from crw_pdf_export import generate_roster_pdf
from crw_presets import (apply_preset, bounds, init_session_state_defaults, load_permalink_settings, randomize_seed, settings_from_state,
                         sync_query_params)
from crw_rules import DRIVE
from crw_visualization import build_cost_bars, build_gantt, build_gap_chart, build_rule_prices, build_time_space

st.set_page_config(page_title="Crew Pairing – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _results():
    return R.load_results()


@st.cache_data(show_spinner=False)
def _live(trains, rest, hotel, cont, span, duties, bases, deadhead, seed):
    return run_live({"trains": trains, "rest": rest, "hotel": hotel, "cont": cont, "span": span, "duties": duties, "bases": bases, "deadhead": deadhead, "seed": seed})


def _hours(minutes):
    h, m = divmod(int(minutes), 60)
    return f"{h} h" if m == 0 else f"{h} h {m} min"


st.title("🚂 Crew Pairing: Besatzungseinsatz im Zugverkehr")
st.markdown(
    """
Die Züge fahren – jetzt braucht jede Fahrt eine **Besatzung**. Aus Zugumläufen, **Heimatbasen** und einem **Regelwerk** (Lenkzeit, Ruhezeit, Dienstspanne, Hotel) entstehen
**Paarungen**: Dienstfolgen über mehrere Tage, die an der Heimatbasis beginnen und enden. Die Demo löst das mit **Spaltengenerierung** (die Paarungen werden nicht aufgezählt,
sondern per Ressourcen-Kürzestem-Weg erzeugt) und zeigt vor allem eines: **was jede einzelne Regel kostet.** Weiter unten: wie nah die Lösung an der Schranke liegt und was
ein gieriges Vorgehen verschenkt.
"""
)
st.caption(
    "Zweiter Baustein der Reihe Bahn/Schienenverkehr nach dem [Taktfahrplan](https://sebastianhanisch-taktfahrplan-demo.streamlit.app/). Die Spaltengenerierung kennt man aus "
    "[column-generation-demo](https://sebastianhanisch-column-generation-demo.streamlit.app/) (Pricing = Rucksack) und [mcf-column-generation-demo](https://sebastianhanisch-mcf-column-generation-demo.streamlit.app/) "
    "(Pricing = kürzester Weg); neu ist hier das Pricing mit Zeit- und Lenkzeit-Ressourcen und das Regelwerk."
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(3)
for i, name in enumerate(C.PRESET_ORDER):
    with preset_cols[i % 3]:
        st.button(name, key=f"preset_{name}", width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Netz**")
    st.select_slider("Züge", options=C.TRAINS_OPTIONS, key="trains_select",
                     help=f"Zahl der Zugumläufe auf der Strecke mit {C.N_STATIONS} Stationen ({C.DAYS} Tage); jeder Zug ist in Teilstrecken zerlegt, an jeder Station kann die Besatzung wechseln.")
    st.select_slider("Heimatbasen", options=C.BASES_OPTIONS, key="bases_select", format_func=lambda b: "beide Enden" if b == 2 else "nur Station 0",
                     help="Stationen, an denen Besatzungen wohnen: jede Paarung beginnt und endet an derselben Basis.")
    st.markdown("**Regeln**")
    st.select_slider("Ruhezeit zwischen Diensten", options=C.REST_OPTIONS, key="rest_select", format_func=_hours,
                     help="Mindestzeit zwischen dem Ende eines Dienstes und dem Beginn des nächsten; sie wird an der Heimatbasis oder im Hotel verbracht.")
    st.slider("Hotelpreis je Nacht", C.HOTEL_OPTIONS[0], C.HOTEL_OPTIONS[-1], step=C.HOTEL_OPTIONS[1] - C.HOTEL_OPTIONS[0], key="hotel_select",
                     help="Kosten einer Nacht auswärts in Minutenäquivalenten (ein Dienst kostet mindestens 300).")
    st.select_slider("Ununterbrochen fahren (höchstens)", options=C.CONT_OPTIONS, key="cont_select", format_func=_hours,
                     help="Längste Lenkzeit ohne Pause (eine Lücke von mindestens 30 min oder Mitfahren zählt als Pause).")
    st.select_slider("Dienstspanne (höchstens)", options=C.SPAN_OPTIONS, key="span_select", format_func=_hours,
                     help="Vom Beginn der ersten bis zum Ende der letzten Fahrt eines Dienstes.")
    st.select_slider("Dienste je Paarung (höchstens)", options=C.DUTIES_OPTIONS, key="duties_select",
                     help="Bei 1 Dienst muss die Besatzung am selben Tag wieder an der Heimatbasis sein (keine Übernachtung).")
    st.toggle("Mitfahren erlaubt", key="deadhead_toggle",
              help="Eine Besatzung darf als Fahrgast mitfahren, um an den Ort ihres nächsten Einsatzes zu kommen (kostet Dienstzeit, zählt als Pause, überdeckt die Fahrt nicht).")
    st.markdown("**Zufall**")
    st.number_input("Zufalls-Seed", min_value=bounds("seed_input")[0], max_value=bounds("seed_input")[1], step=1, key="seed_input",
                    help="Bestimmt die Zugumläufe. Der Seed zählt hoch, bis das Netz genug überdeckbare Fahrten hat.")
    st.button("🎲 Neues Netz würfeln", on_click=randomize_seed)

values = {k: st.session_state[k] for k in ("trains_select", "rest_select", "hotel_select", "cont_select", "span_select", "duties_select", "bases_select", "deadhead_toggle", "seed_input")}
sync_query_params(values)
settings = settings_from_state(values)

res = _results()
with st.spinner("Spaltengenerierung und ganzzahlige Auswahl …"):
    run = _live(settings["trains"], settings["rest"], settings["hotel"], settings["cont"], settings["span"], settings["duties"], settings["bases"], settings["deadhead"], settings["seed"])
trips, case, std = run["trips"], run["case"], run["std"]
price = price_of_rules(run)
lever = R.lever_to_variant(settings)
vrow = R.variant_row(res, lever) if lever else None
st.caption(
    f"Netz aus Seed {run['seed']}{' (der eingegebene Seed hatte zu wenige überdeckbare Fahrten)' if run['seed'] != settings['seed'] else ''}: {C.N_STATIONS} Stationen, "
    f"{settings['trains']} Züge, {len(trips)} Teilstrecken (von {run['n_raw']}; nur die unter den Standardregeln überdeckbaren). "
    f"Rechenzeit dieses Laufs {run['seconds']:.1f} s (beim ersten Aufruf; danach aus dem Zwischenspeicher)."
)

st.markdown("---")
st.markdown("## 🚂 Was kostet der Besatzungseinsatz – und was kosten die Regeln?")
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)
m1.metric("Kosten (ganzzahlig)", C.fmt_cost(case["ip"]), delta=None if run["is_standard"] else f"{price['delta_pct']:+.1f} % gegen Standardregeln", delta_color="inverse",
          help="Summe aus Lohn (je Dienst mindestens 300, sonst die Dienstspanne), Hotel und Strafen für unüberdeckte Fahrten (je 5 000), in Minutenäquivalenten.")
m2.metric("LP-Schranke", C.fmt_cost(case["lp"]), delta=f"ganzzahlig {gap_pct(case):.1f} % darüber", delta_color="off",
          help="Untergrenze aus der Spaltengenerierung (LP-Relaxation). Kein Besatzungsplan kann billiger sein.")
m3.metric("Paarungen / Übernachtungen", f"{len(case['pairings'])} / {case['nights']}", delta=None if run["is_standard"] else f"{len(case['pairings']) - len(std['pairings']):+d} Paarungen gegen Standard",
          delta_color="off")
m4.metric("Gierig über ganzzahlig", f"{100 * (case['greedy'] / case['ip'] - 1):.1f} %", delta=f"{C.fmt_cost(case['greedy'] - case['ip'])} mehr Kosten", delta_color="off",
          help="Gierig: immer die Paarung mit den geringsten Kosten je neu überdeckter Fahrt, danach Überflüssiges streichen - über denselben Spalten wie die ganzzahlige Lösung.")

noise_pct = R.size_summary(res, settings["trains"])["gap_ip"]       # Meldungsschwelle: Lücke der ganzzahligen Auswahl zur Schranke
state, text = rule_message(run, vrow["pct"] if vrow and lever != "Standard" else None, vrow["se"] if vrow and lever != "Standard" else None, threshold=noise_pct)
(st.success if state == "over" else st.info)(f"💡 {text}")
if case["uncovered"]:
    st.warning(f"{len(case['uncovered'])} von {len(trips)} Fahrten lassen sich mit diesem Regelwerk nicht überdecken (rot gestrichelt im Diagramm); jede kostet die Strafe von {C.PENALTY}.")
if case["ip_status"] != 0:
    st.info(f"Die ganzzahlige Auswahl wurde nach {C.IP_TIME_LIMIT:.0f} s Zeitlimit beendet und ist nicht als optimal bewiesen.")

st.plotly_chart(build_cost_bars(case, std, run["is_standard"]), width="stretch", key=f"cost_{settings}_{run['seed']}")
st.markdown("### Wer fährt wann: Zeit-Weg-Diagramm und Dienstplan")
st.plotly_chart(build_time_space(trips, case), width="stretch", key=f"timespace_{settings}_{run['seed']}")
st.caption("Jede Linie ist eine Teilstrecke eines Zuges, gefärbt nach der Paarung (Besatzung), die sie fährt; gepunktet fährt eine Besatzung als Fahrgast mit, rot gestrichelt bleibt eine Fahrt unüberdeckt.")
st.plotly_chart(build_gantt(trips, case, run["rules"]), width="stretch", key=f"gantt_{settings}_{run['seed']}")
summary_lines = [f"Netz aus Seed {run['seed']}, {settings['trains']} Züge, {len(trips)} Teilstrecken, Heimatbasen: {', '.join(str(b) for b in run['bases'])}",
                 f"Kosten {C.fmt_cost(case['ip'])} (LP-Schranke {C.fmt_cost(case['lp'])}), {len(case['pairings'])} Paarungen, {case['nights']} Nächte auswärts.",
                 f"Regeln: Ruhezeit {_hours(settings['rest'])}, Hotel {settings['hotel']}, ununterbrochen höchstens {_hours(settings['cont'])}, Dienstspanne höchstens {_hours(settings['span'])}, "
                 f"{settings['duties']} Dienst(e) je Paarung, Mitfahren {'erlaubt' if settings['deadhead'] else 'nicht erlaubt'}."]
st.download_button("📄 Dienstplan als PDF herunterladen", data=generate_roster_pdf(trips, case, "Besatzungseinsatz", summary_lines), file_name="dienstplan.pdf",
                   mime="application/pdf", key="pdf_download")

# ------------------------------------------------------------------ Kernabschnitt: Preisliste der Regeln
st.markdown("---")
st.subheader("💰 Was jede Regel kostet")
std_costs = R.standard_costs(res)
st.markdown(
    f"Gemessen über {len(res['variants'])} Netze mit 4 Zügen (jedes Mal dasselbe Netz, nur eine Regel geändert, ganzzahlige Lösung gegen die Standardregeln). Im Standard bestehen "
    f"{std_costs['hotel_share']:.0f} % der Kosten aus Hotel und {std_costs['wage_share']:.0f} % aus Lohn; im Mittel {std_costs['pairings']:.1f} Paarungen mit {std_costs['nights']:.1f} Übernachtungen für "
    f"{std_costs['trips']:.0f} Teilstrecken."
)
st.plotly_chart(build_rule_prices(R.variant_rows(res)), width="stretch", key="rule_prices")
rows = R.variant_rows(res)
st.dataframe(pd.DataFrame([{"Variante": r["name"], "Kosten gegen Standard": f"{r['pct']:+.1f} ± {r['se']:.1f} %", "Netze mit höheren Kosten": f"{r['positive']}/{r['n']}",
                            "unüberdeckte Fahrten Ø": round(r["uncovered"], 1), "Kosten ohne Strafe": f"{r['pure_pct']:+.1f} %", "Paarungen Ø": round(r["pairings"], 1),
                            "Übernachtungen Ø": round(r["nights"], 1)} for r in rows]), width="stretch", hide_index=True)
unc_rows = [r for r in rows if r["uncovered"] >= 0.05]
st.caption(
    "Die Balken zeigen nur Regeln, bei denen alle Fahrten überdeckt bleiben. Bei den übrigen bleiben Fahrten unüberdeckt (" + ", ".join(f"{r['name']}: {r['uncovered']:.1f} Fahrten" for r in unc_rows)
    + "); die Strafe von 5 000 je Fahrt schlägt dann die eigentlichen Kosten bei weitem, deshalb steht „Kosten ohne Strafe“ daneben und kann sogar unter dem Standard liegen: es wird weniger gefahren. "
    "Regeln, die fast nichts kosten, sind genauso ein Befund wie teure."
)

# ------------------------------------------------------------------ Kernabschnitt: Wie nah am Optimum
st.markdown("---")
st.subheader("🧮 Wie nah ist das am Optimum?")
summaries = {t: R.size_summary(res, t) for t in C.SWEEP_TRAINS}
st.markdown(
    "Die Spaltengenerierung liefert eine **Schranke** (LP): kein Plan kann billiger sein. Die **ganzzahlige Auswahl** wählt aus den dabei erzeugten Spalten; **gierig** wählt aus denselben Spalten "
    "die jeweils günstigste je neu überdeckter Fahrt. Gemessen über je 20 Netze:"
)
st.plotly_chart(build_gap_chart(summaries), width="stretch", key="gap_chart")
st.dataframe(pd.DataFrame([{"Züge": t, "Teilstrecken Ø": round(s["trips"]), "ganzzahlig = LP": f"{s['ip_equals_lp']}/{s['n_nets']}", "ganzzahlig über LP Ø / max": f"{s['gap_ip']:.1f} % / {s['gap_ip_max']:.1f} %",
                            "gierig über LP Ø ± SE": f"{s['gap_gr']:.1f} ± {s['gap_gr_se']:.1f} %", "Spalten Ø": round(s["columns"]), "Iterationen Ø": round(s["iterations"]),
                            "Rechenzeit Median (s)": round(s["t_cg"], 1), "davon Pricing": f"{s['pricing_share']:.0f} %"} for t, s in summaries.items()]), width="stretch", hide_index=True)
st.caption(
    "**Ehrliche Grenze:** Ein vollständiges Branch-and-Price fehlt. Der Abstand der ganzzahligen Lösung zur Schranke besteht aus der Ganzzahligkeitslücke und daraus, dass nur die in der "
    "Spaltengenerierung erzeugten Spalten zur Wahl stehen; das Optimum liegt irgendwo dazwischen. Die gierige Lösung verschenkt davon ein Mehrfaches."
)

# ------------------------------------------------------------------ Methodenvergleich
st.markdown("---")
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich", expanded=False):
    tabs = st.tabs(["🧩 Paarungen", "🔎 Pricing", "🧮 Ganzzahlig (HiGHS)", "📈 Messreihe"])

    with tabs[0]:
        st.caption("Die gewählte Lösung als Liste: je Paarung Heimatbasis, Dienste, Fahrten und Kosten.")
        prow = []
        for pi, p in enumerate(case["pairings"]):
            prow.append({"Paarung": pi + 1, "Basis": p["base"], "Beginn": C.fmt_hm(p["start"]), "Ende": C.fmt_hm(p["end"]), "Dienste": len(p["duties"]), "Nächte": p["nights"],
                         "Fahrten gefahren": p["n_covered"], "mitgefahren": sum(1 for d in p["duties"] for _, m in d if m != DRIVE), "Lohn": p["wage"], "Hotel": p["hotel"], "Kosten": p["cost"]})
        st.dataframe(pd.DataFrame(prow), width="stretch", hide_index=True)

    with tabs[1]:
        st.markdown(
            "Das **Pricing** sucht die Paarung mit den kleinsten *reduzierten Kosten* (Kosten minus Summe der Duale der gefahrenen Fahrten) als **Ressourcen-Kürzesten-Weg** über die Fahrten, nach Abfahrt "
            "geordnet. Ein Label trägt Kosten, Beginn des Dienstes, Lenkzeit und ununterbrochene Lenkzeit; **Dominanz** streicht Labels, die nicht teurer, später begonnen und weniger verbraucht sind. Ein neuer "
            "Dienst setzt auf das beste Ende des vorigen Dienstes auf (Ruhezeit, Hotel). Je Heimatbasis ein Lauf."
        )
        p1, p2, p3 = st.columns(3)
        p1.metric("Iterationen", case["iterations"])
        p2.metric("erzeugte Spalten", case["columns"])
        p3.metric("Pricing-Anteil an der Zeit", f"{100 * case['t_pricing'] / max(case['t_cg'], 1e-9):.0f} %", help=f"Spaltengenerierung {case['t_cg']:.1f} s, davon Pricing {case['t_pricing']:.1f} s.")

    with tabs[2]:
        st.caption(f"Die ganzzahlige Auswahl über die erzeugten Spalten (Mengenüberdeckung, HiGHS). Live {C.IP_TIME_LIMIT:.0f} s Zeitlimit; hier mit {C.IP_TIME_LIMIT_BUTTON:.0f} s.")
        key = (tuple(sorted(settings.items())), run["seed"])
        if st.button("🧮 Mit längerem Zeitlimit lösen", key="ip_button"):
            with st.spinner(f"HiGHS rechnet (bis zu {C.IP_TIME_LIMIT_BUTTON:.0f} s) …"):
                st.session_state["ip_result"] = {"key": key, "case": solve_case(trips, run["rules"], run["bases"], ip_limit=C.IP_TIME_LIMIT_BUTTON)}
        ex = st.session_state.get("ip_result")
        if ex and ex["key"] == key:
            c = ex["case"]
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Kosten", C.fmt_cost(c["ip"]))
            e2.metric("LP-Schranke", C.fmt_cost(c["lp"]))
            e3.metric("Abstand", f"{gap_pct(c):.2f} %")
            e4.metric("Status", "bewiesen optimal" if c["ip_status"] == 0 else "Zeitlimit")
            st.info("„Optimal“ gilt für die Auswahl unter den erzeugten Spalten, nicht für das Gesamtproblem (dafür fehlt das Branch-and-Price).")
        elif ex:
            st.caption("Die Einstellungen haben sich seit dem letzten Lauf geändert - bitte erneut lösen.")

    with tabs[3]:
        st.caption("Größenreihe je Netzgröße (20 Netze) und alle Regelvarianten (20 Netze mit 4 Zügen).")
        st.dataframe(pd.DataFrame([{"Züge": t, "Teilstrecken Ø": round(s["trips"]), "LP Ø": round(s["lp"]), "ganzzahlig Ø": round(s["ip"]), "Übernachtungen Ø": round(s["nights"], 1),
                                    "Hotelanteil an den Kosten": f"{s['hotel_share']:.0f} %", "ganzzahlig nicht optimal (Zeitlimit)": s["ip_not_optimal"]} for t, s in summaries.items()]),
                     width="stretch", hide_index=True)

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Netz.** Eine Strecke mit {C.N_STATIONS} Stationen; jeder Zug pendelt zwischen zwei Stationen, {C.HOP} min je Teilstrecke, {C.DAYS} Tage. Jede Teilstrecke ist eine Fahrt, die eine Besatzung braucht.
Im selben Zug sitzen bleiben braucht keine Umsteigezeit, an jeder Station kann gewechselt werden (15 min Mindestzeit zwischen verschiedenen Zügen). Alles ganzzahlig, mit dem Zufallsgenerator SplitMix64 erzeugt.

**Paarung und Regeln.** Ein *Dienst* ist eine Kette von Fahrten (gefahren oder als Fahrgast mitgefahren). Er darf höchstens die gewählte Dienstspanne dauern, höchstens 8 Stunden Lenkzeit haben und höchstens die gewählte
Zeit ununterbrochen lenken (eine Lücke ab 30 min oder Mitfahren unterbricht). Eine *Paarung* verbindet bis zu drei Dienste durch Ruhezeiten, beginnt und endet an derselben Heimatbasis; wer die Ruhezeit auswärts
verbringt, kostet eine Hotelnacht. Ein Dienst wird mit mindestens 300 (Garantie), sonst mit seiner Spanne bezahlt.

**Ziel.** Jede Fahrt wird von mindestens einer Paarung gefahren (Mehrfachüberdeckung entspricht Mitfahren); gesucht sind die billigsten Paarungen. Fahrten, die ein Regelwerk unüberdeckbar macht
(zum Beispiel am Morgen des ersten Tages, wo noch keine Besatzung angereist sein kann), bleiben unüberdeckt und kosten eine Strafe von {C.PENALTY}.

**Verfahren.** *Spaltengenerierung:* der Master wählt unter bekannten Paarungen, das Pricing erzeugt neue mit negativen reduzierten Kosten, bis keine mehr kommt; das Ergebnis ist die LP-Schranke.
*Ganzzahlig:* Auswahl unter allen erzeugten Spalten. *Gierig:* wie oben beschrieben, danach Überflüssiges streichen.

**Grenzen.** Synthetische Strecke, Kosten in Minutenäquivalenten, kein Fahrzeugumlauf (die Züge sind gegeben), keine Dienstplan-Gerechtigkeit (Rostering), keine Mindestruhe pro Woche, kein Branch-and-Price.
Die Aussagen gelten für diese Netze; die Preise der Regeln sind Größenordnungen, keine Tarifwerte.
"""
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Master (Mengenüberdeckung).** Menge $P$ der zulässigen Paarungen mit Kosten $c_p$ und Überdeckung $a_{tp} \in \{0,1\}$ (Fahrt $t$ wird in $p$ gefahren):
$\min \sum_p c_p x_p$ unter $\sum_p a_{tp} x_p \ge 1$ für alle Fahrten $t$, $x_p \in \{0,1\}$. $P$ ist riesig und wird nicht aufgezählt.

**Spaltengenerierung.** Man löst das LP über eine Teilmenge $P' \subseteq P$ und erhält Duale $\pi_t \ge 0$. Eine Paarung $p$ hat die reduzierten Kosten $\bar c_p = c_p - \sum_t a_{tp}\pi_t$; gibt es eine mit $\bar c_p < 0$, wird sie zu $P'$ hinzugefügt,
sonst ist das LP-Optimum über $P'$ das über $P$ (Schranke).

**Pricing als Ressourcen-Kürzester-Weg.** Knoten sind Fahrten, Kanten Anschlüsse (gleicher Ort, Mindestzeit) und Ruhepausen zwischen Diensten. Ressourcen: Dienstbeginn $s$ (Kosten bei Dienstende $\max(300, e - s)$),
Lenkzeit $d \le d_{\max}$, ununterbrochene Lenkzeit $u \le u_{\max}$, Spanne $e - s \le \sigma_{\max}$. Ein Label $(\bar c, s, d, u)$ dominiert $(\bar c', s', d', u')$, wenn $\bar c \le \bar c'$, $s \ge s'$, $d \le d'$, $u \le u'$.

**Kosten einer Paarung.** $c_p = \sum_{\text{Dienste}} \max(G, e - s) + H \cdot (\text{Nächte auswärts})$ mit Garantie $G = 300$ und Hotelpreis $H$.
"""
    )

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Schienenverkehr optimieren](https://sebastianhanisch.net/schienenverkehr-optimierung.html)."
)
