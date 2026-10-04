"""Statistik der Messreihe an einer von Hand gerechneten Mini-Ergebnisdatei."""
import math

import pytest

import crw_results as R


def case(lp, ip, greedy, unc=0, pairings=3, nights=2, hotel=1000, wage=4000, status=0):
    return {"lp": lp, "ip": ip, "greedy": greedy, "uncovered": unc, "pairings": pairings, "nights": nights, "hotel": hotel, "wage": wage, "ip_status": status,
            "iterations": 10, "columns": 50, "t_cg": 2.0, "t_pricing": 1.0, "t_ip": 0.1, "n": 30, "greedy_uncovered": 0}


@pytest.fixture
def res():
    sizes = [{"trains": 3, "seed": 1, **case(100, 104, 120)}, {"trains": 3, "seed": 2, **case(200, 200, 230, status=1)}, {"trains": 4, "seed": 1, **case(100, 110, 130)}]
    variants = [{"seed": 1, "n": 30, "variants": {"Standard": case(100, 100, 110), "Hotel 2000": case(150, 150, 160), "ohne Mitfahren": case(300, 6100, 6200, unc=1)}},
                {"seed": 2, "n": 30, "variants": {"Standard": case(200, 200, 210), "Hotel 2000": case(250, 260, 270), "ohne Mitfahren": case(400, 5400, 5500, unc=1)}}]
    return {"meta": {"penalty": 5000, "variants": ["Standard", "Hotel 2000", "ohne Mitfahren"]}, "sizes": sizes, "variants": variants}


def test_mean_se():
    m, se = R.mean_se([2.0, 4.0, 6.0])
    assert m == 4.0 and abs(se - 2.0 / math.sqrt(3)) < 1e-12
    assert math.isnan(R.mean_se([5.0])[1])


def test_size_summary_by_hand(res):
    s = R.size_summary(res, 3)
    assert s["n_nets"] == 2 and s["ip_equals_lp"] == 1 and abs(s["gap_ip"] - 2.0) < 1e-12 and abs(s["gap_ip_max"] - 4.0) < 1e-12
    assert abs(s["gap_gr"] - 17.5) < 1e-9 and abs(s["gap_gr_min"] - 15.0) < 1e-9 and abs(s["gap_gr_max"] - 20.0) < 1e-9 and s["ip_not_optimal"] == 1
    assert s["t_cg"] == 2.0 and abs(s["pricing_share"] - 50.0) < 1e-12
    assert abs(s["hotel_share"] - 100 * 2000 / 304) < 1e-9


def test_variant_rows_by_hand(res):
    rows = {r["name"]: r for r in R.variant_rows(res)}
    assert rows["Standard"]["pct"] == 0.0
    # Hotel 2000: 150/100 = +50 %, 260/200 = +30 %  -> Mittel 40
    assert abs(rows["Hotel 2000"]["pct"] - 40.0) < 1e-12 and rows["Hotel 2000"]["positive"] == 2 and rows["Hotel 2000"]["uncovered"] == 0 and rows["Hotel 2000"]["all_covered"] == 2
    # ohne Mitfahren: Kosten ohne Strafe (6100-5000)/100 = +1000 %, (5400-5000)/200 = +100 %
    assert abs(rows["ohne Mitfahren"]["pure_pct"] - 550.0) < 1e-9 and rows["ohne Mitfahren"]["uncovered"] == 1 and rows["ohne Mitfahren"]["all_covered"] == 0
    assert R.variant_row(res, "Hotel 2000")["name"] == "Hotel 2000"
    sc = R.standard_costs(res)
    assert sc["ip"] == 150 and abs(sc["hotel_share"] - 100 * 2000 / 300) < 1e-9 and abs(sc["wage_share"] - 100 * 8000 / 300) < 1e-9 and sc["nights"] == 2 and sc["trips"] == 30


def test_lever_to_variant_maps_exactly_one_change():
    std = {"rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True}
    assert R.lever_to_variant(std) == "Standard"
    assert R.lever_to_variant({**std, "hotel": 2000}) == "Hotel 2000" and R.lever_to_variant({**std, "rest": 780}) == "Ruhezeit 13 h"
    assert R.lever_to_variant({**std, "deadhead": False}) == "ohne Mitfahren" and R.lever_to_variant({**std, "bases": 1}) == "nur eine Heimatbasis"
    assert R.lever_to_variant({**std, "cont": 180}) == "ununterbrochen 3 h" and R.lever_to_variant({**std, "span": 540}) == "Spanne 9 h"
    assert R.lever_to_variant({**std, "duties": 1}) == "1 Dienst (keine Übernachtung)" and R.lever_to_variant({**std, "duties": 2}) == "2 Dienste"
    assert R.lever_to_variant({**std, "hotel": 2000, "rest": 780}) is None            # Kombination: keine Messreihen-Zahl
    assert R.lever_to_variant({**std, "cont": 210}) is None                           # Zwischenstufe ohne Messreihe
