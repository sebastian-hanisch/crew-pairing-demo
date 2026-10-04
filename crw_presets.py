"""SETTING_SPECS-Permalink-Muster, Presets und Zufalls-Seed-Button (Standardmuster aus dem Demo-Portfolio).
Alle Regler sind immer sichtbar mit festen Grenzen - es gibt keinen ausblendbaren Regler (also auch kein KEPT-Muster)."""

import random
from dataclasses import dataclass
from typing import Callable

import streamlit as st

import crw_constants as C


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    options: tuple | None = None       # feste Stufen: ein Permalink-Wert rastet auf die nächste Stufe ein
    lo: int | None = None
    hi: int | None = None


SETTING_SPECS = {
    "trains_select": SettingSpec("trains", int, C.DEFAULT_TRAINS, C.TRAINS_OPTIONS),
    "rest_select": SettingSpec("rest", int, C.REST_OPTIONS[0], C.REST_OPTIONS),
    "hotel_select": SettingSpec("hotel", int, C.HOTEL_OPTIONS[0], C.HOTEL_OPTIONS),
    "cont_select": SettingSpec("cont", int, C.CONT_OPTIONS[0], C.CONT_OPTIONS),
    "span_select": SettingSpec("span", int, C.SPAN_OPTIONS[0], C.SPAN_OPTIONS),
    "duties_select": SettingSpec("duties", int, C.DUTIES_OPTIONS[-1], C.DUTIES_OPTIONS),
    "bases_select": SettingSpec("bases", int, C.BASES_OPTIONS[0], C.BASES_OPTIONS),
    "deadhead_toggle": SettingSpec("dh", int, 1),
    "seed_input": SettingSpec("seed", int, C.DEFAULT_SEED, None, C.SEED_MIN, C.SEED_MAX),
}
PRESET_KEYS = {"trains": "trains_select", "rest": "rest_select", "hotel": "hotel_select", "cont": "cont_select", "span": "span_select", "duties": "duties_select",
               "bases": "bases_select", "deadhead": "deadhead_toggle", "seed": "seed_input"}


def snap(options, value):
    """Nächste Stufe (bei Gleichstand die kleinere)."""
    return min(options, key=lambda o: (abs(o - value), o))


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = bool(spec.default) if state_key == "deadhead_toggle" else spec.default


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            try:
                value = spec.caster(qp[spec.url_param])
                if spec.options is not None:
                    value = snap(spec.options, value)
                elif state_key == "deadhead_toggle":
                    value = bool(value)
                else:
                    value = max(spec.lo, min(spec.hi, value))
                st.session_state[state_key] = value
            except (ValueError, TypeError):
                pass
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """`values`: {state_key: aktueller Wert}."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = str(int(value) if isinstance(value, bool) else value)
    except Exception:
        pass


def apply_preset(name):
    for key, state_key in PRESET_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][key]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(C.SEED_MIN, C.SEED_MAX)


def settings_from_state(values: dict) -> dict:
    """Regler-Werte (nach state_key) -> Einstellungen der Rechnung."""
    return {"trains": int(values["trains_select"]), "rest": int(values["rest_select"]), "hotel": int(values["hotel_select"]), "cont": int(values["cont_select"]),
            "span": int(values["span_select"]), "duties": int(values["duties_select"]), "bases": int(values["bases_select"]), "deadhead": bool(values["deadhead_toggle"]),
            "seed": int(values["seed_input"])}
