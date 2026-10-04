"""Fahrplan aus Zugumläufen auf einer Strecke (ganzzahlig, SplitMix64): jeder Zug pendelt zwischen zwei Stationen und ist in Teilstrecken zerlegt,
sodass die Besatzung an jeder Station wechseln kann; im selben Zug sitzen bleiben braucht keine Umsteigezeit."""
from __future__ import annotations

from crw_rng import SplitMix64
from crw_rules import Trip


def generate_legs(n_stations: int, n_trains: int, days: int, seed: int, hop: int = 75, turn: int = 25, dwell: int = 4):
    """Zugumläufe: jeder Zug pendelt zwischen zwei Stationen (a, b) der Strecke, `hop` min je Teilstrecke, `turn` min Wende, `dwell` min Halt zwischen Teilstrecken.
    Er beginnt den Tag an der Station, an der er abends stand, und fährt bis spätestens 21:00 los; die Teilstrecken eines Zuges schließen aneinander an."""
    rng = SplitMix64(seed)
    trips = []
    for train in range(n_trains):
        a = rng.below(n_stations - 2)
        b = a + 2 + rng.below(n_stations - a - 2)
        pos = a if rng.below(2) else b
        for day in range(days):
            t = day * 1440 + 300 + 15 * rng.below(13)
            while t - day * 1440 <= 21 * 60:
                nxt = b if pos == a else a
                step = 1 if nxt > pos else -1
                seq = 0
                while pos != nxt:
                    trips.append(Trip(pos, pos + step, t, t + hop, train * 100 + day * 10 + (1 if nxt == b else 0), seq))
                    t += hop + (dwell if pos + step != nxt else 0)
                    pos += step
                    seq += 1
                t += turn + 5 * rng.below(4)
    trips.sort(key=lambda t: (t.dep, t.o, t.d, t.train))
    return trips
