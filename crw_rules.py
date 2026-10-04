"""Regelwerk des Besatzungseinsatzes: Fahrten, Dienste, Paarungen. Reine Funktionen ohne Zustand.

Fahrt = Teilstrecke eines Zuges zwischen zwei Stationen. Dienst = Kette von Fahrten (jede gefahren oder mitgefahren), Paarung = Folge von
Diensten über mehrere Tage, beginnt und endet an derselben Heimatbasis. Kosten je Dienst max(Garantie, Spanne), je Nacht auswärts ein Hotelpreis.
"""
from __future__ import annotations

from dataclasses import dataclass

DRIVE, HEAD = "D", "H"


@dataclass(frozen=True)
class Rules:
    min_conn: int = 15
    break_gap: int = 30
    max_cont: int = 270
    max_drive: int = 480
    max_span: int = 660
    guarantee: int = 300
    rest: int = 540
    max_rest: int = 1800       # naechster Dienst spaetestens so lange nach dem Ende des vorigen (min)
    hotel: int = 500
    max_duties: int = 3
    deadhead: bool = True


@dataclass(frozen=True)
class Trip:
    o: int
    d: int
    dep: int
    arr: int
    train: int = -1        # Zugnummer (Teilstrecken desselben Zuges: Besatzung darf ohne Umsteigezeit sitzen bleiben)
    seq: int = -1          # laufende Nummer der Teilstrecke im Zug


def connect_ok(a: Trip, b: Trip, r: Rules) -> bool:
    """Anschluss im selben Dienst: gleicher Ort; bleibt die Besatzung im selben Zug (nächste Teilstrecke), genügt die Haltezeit, sonst gilt die Mindestumsteigezeit."""
    if a.d != b.o:
        return False
    if a.train >= 0 and a.train == b.train and b.seq == a.seq + 1:
        return b.dep >= a.arr
    return b.dep >= a.arr + r.min_conn


def duty_cost(duty: list, r: Rules) -> int:
    """duty = [(Fahrt, Modus), ...]"""
    return max(r.guarantee, duty[-1][0].arr - duty[0][0].dep)


def duty_ok(duty: list, r: Rules) -> bool:
    if not duty:
        return False
    drive = cont = 0
    for i, (t, m) in enumerate(duty):
        if m == HEAD and not r.deadhead:
            return False
        if i:
            if not connect_ok(duty[i - 1][0], t, r):
                return False
            if t.dep - duty[i - 1][0].arr >= r.break_gap:
                cont = 0
        if m == DRIVE:
            drive += t.arr - t.dep
            cont += t.arr - t.dep
        else:
            cont = 0
        if cont > r.max_cont or drive > r.max_drive:
            return False
    return duty[-1][0].arr - duty[0][0].dep <= r.max_span and any(m == DRIVE for _, m in duty)


def check_pairing(duties: list, base: int, r: Rules) -> bool:
    if not duties or len(duties) > r.max_duties or duties[0][0][0].o != base or duties[-1][-1][0].d != base:
        return False
    for i, duty in enumerate(duties):
        if not duty_ok(duty, r):
            return False
        if i:
            prev = duties[i - 1][-1][0]
            gap = duty[0][0].dep - prev.arr
            if duty[0][0].o != prev.d or gap < r.rest or gap > r.max_rest:
                return False
    return True


def pairing_cost(duties: list, base: int, r: Rules) -> int:
    nights = sum(1 for i in range(1, len(duties)) if duties[i][0][0].o != base)
    return sum(duty_cost(d, r) for d in duties) + r.hotel * nights


def covers(duties: list) -> set:
    return {i for d in duties for i, m in d if m == DRIVE}


def to_objects(trips: list, duties: list) -> list:
    return [[(trips[i], m) for i, m in d] for d in duties]
