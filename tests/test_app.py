"""AppTest-Rauchtests: Voreinstellung, jedes Preset, Randwerte, Würfel-Knopf, Permalink, Abschnitte, Ganzzahlig-Tab, Footer."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import crw_constants as C

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _run(**state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def _ok(at):
    assert not at.exception, [e.value for e in at.exception]


def _metric(at, label):
    return next(m.value for m in at.metric if m.label == label)


def _has_metric(at, label):
    return any(m.label == label for m in at.metric)


COST = "Kosten (ganzzahlig)"


def test_default_run_has_no_exception_and_shows_the_main_metrics():
    at = _run()
    _ok(at)
    for label in (COST, "LP-Schranke", "Paarungen / Übernachtungen", "Gierig über ganzzahlig"):
        assert _has_metric(at, label), label
    assert at.session_state["trains_select"] == C.DEFAULT_TRAINS and at.session_state["seed_input"] == C.DEFAULT_SEED
    assert any("Standardregeln" in i.value for i in at.info)


@pytest.mark.parametrize("name", C.PRESET_ORDER)
def test_every_preset_button_runs_and_sets_the_controls(name):
    at = _run()
    next(b for b in at.button if b.key == f"preset_{name}").click().run()
    _ok(at)
    p = C.PRESETS[name]
    assert at.session_state["hotel_select"] == p["hotel"] and at.session_state["rest_select"] == p["rest"] and at.session_state["cont_select"] == p["cont"]
    assert at.session_state["deadhead_toggle"] == p["deadhead"] and at.session_state["seed_input"] == p["seed"] and _has_metric(at, COST)


@pytest.mark.parametrize("kw", [dict(trains_select=3), dict(trains_select=5), dict(rest_select=780), dict(hotel_select=2000), dict(cont_select=180), dict(span_select=540),
                                 dict(duties_select=1), dict(duties_select=2), dict(bases_select=1), dict(deadhead_toggle=False), dict(seed_input=C.SEED_MIN), dict(seed_input=C.SEED_MAX),
                                 dict(rest_select=780, hotel_select=2000, cont_select=180, span_select=540, deadhead_toggle=False)])
def test_extreme_settings_run(kw):
    _ok(_run(**kw))


def test_a_rule_change_changes_the_main_metric_and_shows_the_message():
    std, hotel = _run(), _run(hotel_select=2000)
    assert _metric(std, COST) != _metric(hotel, COST)
    assert any("kostet auf diesem Netz" in x.value for x in hotel.success) and not any("kostet auf diesem Netz" in x.value for x in std.success)
    assert any(m.delta and "gegen Standardregeln" in m.delta for m in hotel.metric if m.label == COST)


def test_strict_rules_report_uncovered_trips():
    at = _run(duties_select=1)
    _ok(at)
    assert any("nicht überdecken" in w.value for w in at.warning)


def test_dice_button_changes_the_seed_and_the_network():
    at = _run()
    old_seed, old = at.session_state["seed_input"], _metric(at, COST)
    next(b for b in at.button if b.label == "🎲 Neues Netz würfeln").click().run()
    _ok(at)
    assert at.session_state["seed_input"] != old_seed and _metric(at, COST) != old


def test_permalink_values_are_clamped_and_snapped():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["trains"] = "9"
    at.query_params["rest"] = "600"
    at.query_params["hotel"] = "1200"
    at.query_params["dh"] = "0"
    at.query_params["seed"] = "99999"
    at.run()
    _ok(at)
    s = at.session_state
    assert s["trains_select"] == 5 and s["rest_select"] == 540 and s["hotel_select"] == 1250 and s["deadhead_toggle"] is False and s["seed_input"] == C.SEED_MAX


def test_permalink_ignores_garbage_and_roundtrips():
    at = AppTest.from_file(APP, default_timeout=300)
    at.query_params["trains"] = "viele"
    at.query_params["seed"] = "x"
    at.run()
    _ok(at)
    assert at.session_state["trains_select"] == C.DEFAULT_TRAINS and at.session_state["seed_input"] == C.DEFAULT_SEED
    next(b for b in at.button if b.key == "preset_Teures Hotel").click().run()
    qp = at.query_params
    at2 = AppTest.from_file(APP, default_timeout=300)
    for k in ("trains", "rest", "hotel", "cont", "span", "duties", "bases", "dh", "seed"):
        at2.query_params[k] = qp[k]
    at2.run()
    _ok(at2)
    assert at2.session_state["hotel_select"] == 2000 and at2.session_state["seed_input"] == C.PRESETS["Teures Hotel"]["seed"]


def test_sections_expanders_and_charts_are_present():
    at = _run()
    _ok(at)
    headers = [s.value for s in at.subheader] + [m.value for m in at.markdown]
    assert any("Was jede Regel kostet" in h for h in headers) and any("Wie nah ist das am Optimum" in h for h in headers)
    assert any("Was kostet der Besatzungseinsatz" in h for h in headers)
    titles = [e.label for e in at.expander]
    assert "🔧 Wie wir das erreichen – vollständiger Methodenvergleich" in titles and "Wie funktioniert diese Demo?" in titles and "📐 Mathematische Formulierung" in titles
    assert [t.label for t in at.tabs] == ["🧩 Paarungen", "🔎 Pricing", "🧮 Ganzzahlig (HiGHS)", "📈 Messreihe"]
    assert len(at.get("plotly_chart")) == 5          # Kosten, Zeit-Weg, Dienstplan, Preisliste, Abstand zur Schranke


def test_integer_tab_runs_highs_on_the_current_network():
    at = _run(trains_select=3)
    _ok(at)
    next(b for b in at.button if b.key == "ip_button").click().run()
    _ok(at)
    assert _has_metric(at, "LP-Schranke") and _has_metric(at, "Abstand") and _has_metric(at, "Status")
    at.select_slider(key="trains_select").set_value(4).run()
    assert not _has_metric(at, "Abstand") and any("erneut lösen" in c.value for c in at.caption)


def test_seed_control_uses_the_portfolio_wording():
    at = _run()
    assert [n.label for n in at.number_input] == ["Zufalls-Seed"]


def test_related_demos_are_linked_and_footer_is_present():
    at = _run()
    text = " ".join(c.value for c in at.caption)
    for name in ("taktfahrplan-demo", "column-generation-demo", "mcf-column-generation-demo"):
        assert name in text
    assert "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net)" in text
    assert "geplant" not in text and "noch nicht" not in text
