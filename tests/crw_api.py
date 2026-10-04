"""Ein Namensraum `C` über Regelwerk, Netz, Pricing und Master, damit die Tests nach den Funktionsnamen lesbar bleiben; dazu ein Zufallsgenerator für
kleine Einzelfahrten-Instanzen, der nur den Tests dient (Vollaufzählung braucht winzige Fälle, die der Zugumlauf-Generator nicht liefert)."""
from types import SimpleNamespace

import crw_master
import crw_network
import crw_pricing
import crw_rules
from crw_rng import SplitMix64
from crw_rules import Trip

def generate_instance(n_stations: int, per_day: int, days: int, seed: int, hop: int = 45, max_hops: int = 4):
    """Durchlaeufe auf einer Strecke: je Fahrt zufaelliger Start, 1..max_hops Halte weit in zufaelliger Richtung, `hop` min je Halt, Abfahrt 05:00 bis 21:00 (5-min-Raster)."""
    rng = SplitMix64(seed)
    trips = []
    for day in range(days):
        for _ in range(per_day):
            o = rng.below(n_stations)
            hops = 1 + rng.below(max_hops)
            direction = 1 if rng.below(2) else -1
            d = o + direction * hops
            if d < 0 or d >= n_stations:
                d = o - direction * hops
                if d < 0 or d >= n_stations:
                    d = max(0, min(n_stations - 1, o + direction * hops))
            if d == o:
                d = o + 1 if o + 1 < n_stations else o - 1
            dep = day * 1440 + 300 + 5 * rng.below(193)
            trips.append(Trip(o, d, dep, dep + hop * abs(d - o)))
    trips.sort(key=lambda t: (t.dep, t.o, t.d))
    return trips


C = SimpleNamespace(**{name: getattr(mod, name) for mod in (crw_rules, crw_network, crw_pricing, crw_master) for name in dir(mod) if not name.startswith("_")},
                    generate_instance=generate_instance)
