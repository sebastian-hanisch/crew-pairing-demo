"""Pricing: Ressourcen-Kürzester-Weg mit Labeling und Dominanz. Findet je Heimatbasis die Paarungen mit den kleinsten reduzierten Kosten
(Kosten minus Summe der Duale der gefahrenen Fahrten)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from crw_rules import DRIVE, HEAD, Rules, connect_ok


@dataclass
class Label:
    rc: float
    start: int = 0
    drive: int = 0
    cont: int = 0
    parent: "Label | None" = field(default=None, repr=False)
    trip: int = -1
    mode: str = DRIVE
    closed: bool = False
    has_drive: bool = True


def dominates(a: Label, b: Label) -> bool:
    return (a.rc <= b.rc + 1e-12 and a.start >= b.start and a.drive <= b.drive and a.cont <= b.cont and (a.has_drive or not b.has_drive))


def prune(labels: list) -> list:
    labels = sorted(labels, key=lambda l: (l.rc, -l.start, l.drive, l.cont))
    kept = []
    for l in labels:
        if not any(dominates(k, l) for k in kept):
            kept.append(l)
    return kept


def price_pairings(trips: list, duals: np.ndarray, r: Rules, base: int, limit: int = 40, tol: float = 1e-7) -> list:
    """Paarungen einer Heimatbasis mit negativen reduzierten Kosten (je letzte Fahrt die beste, bis `limit`). [(rc, Dienste als [(Index, Modus)])]"""
    n = len(trips)
    K = r.max_duties
    open_ = [[[] for _ in range(K)] for _ in range(n)]
    closed = [[None] * K for _ in range(n)]
    preds = [[] for _ in range(n)]            # Vorgaenger im selben Dienst
    rest_preds = [[] for _ in range(n)]       # Vorgaenger fuer einen neuen Dienst
    for j, t in enumerate(trips):
        for i in range(j):
            ti = trips[i]
            if ti.d != t.o:
                continue
            if connect_ok(ti, t, r) and t.arr - ti.dep <= r.max_span:
                preds[j].append(i)
            gap = t.dep - ti.arr
            if r.rest <= gap <= r.max_rest:
                rest_preds[j].append(i)
    modes = (DRIVE, HEAD) if r.deadhead else (DRIVE,)
    for j, t in enumerate(trips):
        dur = t.arr - t.dep
        for k in range(K):
            cand = []
            starts = []
            if k == 0:
                if t.o == base:
                    starts.append((0.0, None))
            else:
                best = None
                for i in rest_preds[j]:
                    c = closed[i][k - 1]
                    if c is None:
                        continue
                    hotel = 0 if trips[i].d == base else r.hotel
                    if best is None or c.rc + hotel < best[0]:
                        best = (c.rc + hotel, c)
                if best is not None:
                    starts.append(best)
            for mode in modes:
                gain = -float(duals[j]) if mode == DRIVE else 0.0
                dd = dur if mode == DRIVE else 0
                for base_rc, parent in starts:
                    cand.append(Label(base_rc + gain, t.dep, dd, dd, parent, j, mode, False, mode == DRIVE))
                for i in preds[j]:
                    gap = t.dep - trips[i].arr
                    for l in open_[i][k]:
                        if t.arr - l.start > r.max_span:
                            continue
                        if mode == DRIVE:
                            cont = dur if gap >= r.break_gap else l.cont + dur
                            drive = l.drive + dur
                            if cont > r.max_cont or drive > r.max_drive:
                                continue
                        else:
                            cont, drive = 0, l.drive
                        cand.append(Label(l.rc + gain, l.start, drive, cont, l, j, mode, False, l.has_drive or mode == DRIVE))
            open_[j][k] = prune(cand)
            best = None
            for l in open_[j][k]:
                if not l.has_drive:
                    continue
                val = l.rc + max(r.guarantee, t.arr - l.start)
                if best is None or val < best.rc:
                    best = Label(val, 0, 0, 0, l, j, l.mode, True)
            closed[j][k] = best
    out = []
    for j, t in enumerate(trips):
        if t.d != base:
            continue
        best = None
        for k in range(K):
            c = closed[j][k]
            if c is not None and (best is None or c.rc < best.rc):
                best = c
        if best is not None and best.rc < -tol:
            out.append(best)
    out.sort(key=lambda l: l.rc)
    return [(l.rc, labels_to_duties(l)) for l in out[:limit]]


def labels_to_duties(final: Label) -> list:
    chain = []
    l = final
    while l is not None:
        chain.append(l)
        l = l.parent
    chain.reverse()
    duties, cur, prev_closed = [], [], False
    for l in chain:
        if l.closed:
            prev_closed = True
            continue
        if prev_closed:
            duties.append(cur)
            cur = []
            prev_closed = False
        cur.append((l.trip, l.mode))
    duties.append(cur)
    return duties


def price_all(trips, duals, r, bases, limit=40, tol=1e-7):
    out = []
    for b in bases:
        out += [(rc, b, d) for rc, d in price_pairings(trips, duals, r, b, limit, tol)]
    out.sort(key=lambda x: x[0])
    return out[:limit * len(bases)]


def coverable(trips: list, r: Rules, bases: tuple) -> list:
    """Fahrten, die in mindestens einer zulaessigen Paarung gefahren werden koennen; Fixpunkt (das Entfernen kann weitere Fahrten unerreichbar machen)."""
    while True:
        keep = []
        for j in range(len(trips)):
            duals = np.zeros(len(trips))
            duals[j] = 1e5
            if price_all(trips, duals, r, bases, limit=1):
                keep.append(trips[j])
        if len(keep) == len(trips):
            return keep
        trips = keep
