"""Permalink-Einrasten, Presets und Konstanten-Konsistenz."""
import crw_constants as C
import crw_presets as PR


def test_snap_rounds_to_the_nearest_step_and_prefers_the_smaller_on_ties():
    assert PR.snap(C.TRAINS_OPTIONS, 4) == 4 and PR.snap(C.TRAINS_OPTIONS, 9) == 5 and PR.snap(C.TRAINS_OPTIONS, 0) == 3
    assert PR.snap(C.REST_OPTIONS, 600) == 540 and PR.snap(C.REST_OPTIONS, 721) == 780 and PR.snap(C.HOTEL_OPTIONS, 760) == 750 and PR.snap(C.HOTEL_OPTIONS, 9999) == 2000


def test_every_preset_sets_every_control_with_valid_values():
    assert set(C.PRESET_ORDER) == set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESET_ORDER) == 5
    for name, p in C.PRESETS.items():
        assert set(p) == set(PR.PRESET_KEYS)
        assert p["trains"] in C.TRAINS_OPTIONS and p["rest"] in C.REST_OPTIONS and p["hotel"] in C.HOTEL_OPTIONS and p["cont"] in C.CONT_OPTIONS
        assert p["span"] in C.SPAN_OPTIONS and p["duties"] in C.DUTIES_OPTIONS and p["bases"] in C.BASES_OPTIONS and isinstance(p["deadhead"], bool)
        assert C.SEED_MIN <= p["seed"] <= C.SEED_MAX
        assert not (C.SWEEP_SEEDS.start <= p["seed"] < C.SWEEP_SEEDS.stop), name          # Presets liegen nicht in der Stichprobe der Messreihe


def test_each_non_standard_preset_changes_exactly_the_lever_it_is_named_for():
    std = C.PRESETS["Standard"]
    changed = {n: [k for k in std if k != "seed" and C.PRESETS[n][k] != std[k]] for n in C.PRESET_ORDER if n != "Standard"}
    assert changed == {"Teures Hotel": ["hotel"], "Lange Ruhezeit": ["rest"], "Strenge Lenkzeit": ["cont"], "Ohne Mitfahren": ["deadhead"]}
    assert len({p["seed"] for p in C.PRESETS.values()}) == 1                             # alle Presets zeigen dasselbe Netz
    assert std["seed"] == C.DEFAULT_SEED


def test_standard_preset_equals_the_standard_rules():
    s = C.PRESETS["Standard"]
    assert (s["rest"], s["hotel"], s["cont"], s["span"], s["duties"]) == (C.STD_RULES["rest"], C.STD_RULES["hotel"], C.STD_RULES["max_cont"], C.STD_RULES["max_span"], C.STD_RULES["max_duties"])
    assert C.REST_OPTIONS[0] == C.STD_RULES["rest"] and C.HOTEL_OPTIONS[0] == C.STD_RULES["hotel"] and C.CONT_OPTIONS[0] == C.STD_RULES["max_cont"] and C.SPAN_OPTIONS[0] == C.STD_RULES["max_span"]


def test_settings_from_state_converts_types():
    values = {"trains_select": 4, "rest_select": 540, "hotel_select": 500, "cont_select": 270, "span_select": 660, "duties_select": 3, "bases_select": 2, "deadhead_toggle": 1, "seed_input": 501.0}
    s = PR.settings_from_state(values)
    assert s["deadhead"] is True and s["seed"] == 501 and isinstance(s["seed"], int)
    assert C.fmt_hm(0) == "T1 00:00" and C.fmt_hm(1500) == "T2 01:00" and C.fmt_dur(125) == "2 h 05 min" and C.fmt_cost(12345.6) == "12 346"
