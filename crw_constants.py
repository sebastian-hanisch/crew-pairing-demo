"""Feste Annahmen, Regler-Stufen, Presets und Farben der Crew-Pairing-Demo (eine Wahrheitsquelle)."""

# ------------------------------------------------------------------ Netz (feste Annahmen)
N_STATIONS = 7              # Stationen an der Strecke 0..6
DAYS = 2                    # Planungshorizont in Tagen
BASES_ALL = (0, 6)          # Heimatbasen an den Enden der Strecke
HOP = 75                    # Fahrzeit je Teilstrecke (min)
MIN_TRIPS = 20              # ein Seed gilt erst mit so vielen überdeckbaren Fahrten als gültig
SEED_ATTEMPTS = 40
PENALTY = 5000              # Strafe je unüberdeckter Fahrt (Minutenäquivalente); weit über den Kosten, die eine Fahrt normalerweise verursacht

# ------------------------------------------------------------------ Standardregeln (Rules() in crw_rules)
STD_RULES = {"min_conn": 15, "break_gap": 30, "max_cont": 270, "max_drive": 480, "max_span": 660, "guarantee": 300, "rest": 540,
             "max_rest": 1800, "hotel": 500, "max_duties": 3, "deadhead": True}

# ------------------------------------------------------------------ Regler
TRAINS_OPTIONS = (3, 4, 5)
DEFAULT_TRAINS = 4
REST_OPTIONS = (540, 660, 780)                 # Ruhezeit zwischen Diensten (min)
HOTEL_OPTIONS = tuple(range(500, 2001, 250))   # Kosten je Nacht auswärts (Regler mit Schritt 250; die Messreihe kennt 500, 1000 und 2000)
CONT_OPTIONS = (270, 210, 180)                 # ununterbrochene Lenkzeit (min)
SPAN_OPTIONS = (660, 600, 540)                 # Dienstspanne (min)
DUTIES_OPTIONS = (1, 2, 3)
BASES_OPTIONS = (2, 1)
SEED_MIN, SEED_MAX = 0, 9999
DEFAULT_SEED = 500
IP_TIME_LIMIT = 15.0                            # Sekunden für die ganzzahlige Auswahl live
IP_TIME_LIMIT_BUTTON = 60.0

# ------------------------------------------------------------------ Ergebnisdatei und Messreihe
RESULTS_FILE = "data/crw_results.json"
SWEEP_TRAINS = (3, 4, 5)
SWEEP_SEEDS = range(100, 120)
SWEEP_VARIANTS = (  # Name -> (Regeländerung, Heimatbasen); Reihenfolge = Reihenfolge der Anzeige
    ("Standard", {}, 2),
    ("1 Dienst (keine Übernachtung)", {"max_duties": 1}, 2),
    ("2 Dienste", {"max_duties": 2}, 2),
    ("ohne Mitfahren", {"deadhead": False}, 2),
    ("nur eine Heimatbasis", {}, 1),
    ("Ruhezeit 11 h", {"rest": 660}, 2),
    ("Ruhezeit 13 h", {"rest": 780}, 2),
    ("Hotel 1000", {"hotel": 1000}, 2),
    ("Hotel 2000", {"hotel": 2000}, 2),
    ("Lenkzeit 7 h", {"max_drive": 420}, 2),
    ("Lenkzeit 6 h", {"max_drive": 360}, 2),
    ("ununterbrochen 3 h", {"max_cont": 180}, 2),
    ("Garantie 360", {"guarantee": 360}, 2),
    ("Spanne 9 h", {"max_span": 540}, 2),
)

# ------------------------------------------------------------------ Darstellung
COLORS = ["#2a6fb0", "#2e7d4f", "#c77700", "#8e44ad", "#c0392b", "#16a085", "#d35400", "#2c3e50", "#b03a6f", "#7f8c8d"]

# ------------------------------------------------------------------ Presets (Seeds liegen außerhalb der Messreihen-Seeds)
PRESET_ORDER = ["Standard", "Teures Hotel", "Lange Ruhezeit", "Strenge Lenkzeit", "Ohne Mitfahren"]
PRESETS = {
    "Standard": {"trains": 4, "rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500},
    "Teures Hotel": {"trains": 4, "rest": 540, "hotel": 2000, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500},
    "Lange Ruhezeit": {"trains": 4, "rest": 780, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500},
    "Strenge Lenkzeit": {"trains": 4, "rest": 540, "hotel": 500, "cont": 180, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500},
    "Ohne Mitfahren": {"trains": 4, "rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": False, "seed": 500},
}
PRESET_HELP = {
    "Standard": "4 Züge, übliche Regeln: der Grundfall, an dem alle Regeländerungen gemessen werden.",
    "Teures Hotel": "Vierfacher Hotelpreis: Übernachten wird teuer, die Paarungen weichen auf Heimfahrten aus.",
    "Lange Ruhezeit": "13 statt 9 Stunden Ruhezeit zwischen zwei Diensten: Anschlüsse am nächsten Morgen werden knapp.",
    "Strenge Lenkzeit": "Höchstens 3 statt 4,5 Stunden ununterbrochen fahren: mehr Besatzungswechsel unterwegs.",
    "Ohne Mitfahren": "Besatzungen dürfen nicht als Fahrgast mitfahren: sie können nur dort arbeiten, wo sie schon sind.",
}


def fmt_cost(x):
    return f"{x:,.0f}".replace(",", " ")


def fmt_pct(x, digits=1):
    return f"{x:.{digits}f} %"


def fmt_hm(minutes):
    """Minuten seit Mitternacht des ersten Tages als Tag + hh:mm."""
    d, m = divmod(int(minutes), 1440)
    return f"T{d + 1} {m // 60:02d}:{m % 60:02d}"


def fmt_dur(minutes):
    return f"{int(minutes) // 60} h {int(minutes) % 60:02d} min"
