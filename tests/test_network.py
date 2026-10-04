"""SplitMix64 gegen Referenzwerte und der Zugumlauf-Generator: Determinismus, Anschlüsse der Teilstrecken, eingefrorene Werte."""
import crw_rng
from crw_evaluation import build_trips
from crw_network import generate_legs


def test_splitmix64_reference_values():
    r = crw_rng.SplitMix64(0)       # Referenzwerte des Original-Algorithmus (Vigna) für Seed 0
    assert r.next() == 0xE220A8397B1DCDAF and r.next() == 0x6E789E6AA1B965F4 and r.next() == 0x06C45D188009454F
    r = crw_rng.SplitMix64(12345)
    vals = [r.below(7) for _ in range(2000)]
    assert set(vals) == set(range(7))
    assert crw_rng.SplitMix64(5).randrange(1000) == crw_rng.SplitMix64(5).below(1000)


def test_generator_is_deterministic_and_frozen():
    a, b = generate_legs(7, 4, 2, 501), generate_legs(7, 4, 2, 501)
    assert a == b and len(a) == 84
    assert (a[0].o, a[0].d, a[0].dep, a[0].arr, a[0].train, a[0].seq) == (6, 5, 390, 465, 300, 0)
    assert (a[-1].o, a[-1].d, a[-1].dep, a[-1].arr) == (5, 6, 2755, 2830)
    assert generate_legs(7, 4, 2, 502) != a


def test_consecutive_legs_of_one_run_connect_in_place_and_in_time():
    trips = generate_legs(7, 5, 2, 7)
    assert any(t.seq > 0 for t in trips)
    for t in trips:
        assert abs(t.d - t.o) == 1 and t.arr - t.dep == 75 and t.dep < 2 * 1440 + 100             # Teilstrecken zwischen Nachbarstationen
        if t.seq > 0:       # jede spätere Teilstrecke hat ihre Vorgängerin im selben Zug: gleicher Ort, 4 min Halt
            assert any(u.train == t.train and u.seq == t.seq - 1 and u.d == t.o and u.arr + 4 == t.dep for u in trips), t


def test_build_trips_keeps_only_coverable_trips_and_skips_bad_seeds():
    trips, used, raw = build_trips(4, 501)
    assert (len(trips), used, raw) == (76, 501, 84) and len(trips) <= raw
    t3, used3, _ = build_trips(3, 501)
    assert len(t3) >= 20 and used3 >= 501 and all(a.dep <= b.dep for a, b in zip(t3, t3[1:]))
