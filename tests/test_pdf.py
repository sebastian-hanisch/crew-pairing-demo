import crw_evaluation as E
from crw_pdf_export import _clean, generate_roster_pdf


def test_clean_replaces_every_character_fpdf2_cannot_encode():
    cleaned = _clean("Kosten – Ø ≤ 10 → 3 € … − 2 ↔")
    cleaned.encode("latin-1")
    assert not any(c in cleaned for c in "–€→−↔…≤Ø")


def test_roster_pdf_is_a_pdf():
    run = E.run_live({"trains": 3, "rest": 540, "hotel": 500, "cont": 270, "span": 660, "duties": 3, "bases": 2, "deadhead": True, "seed": 500})
    pdf = generate_roster_pdf(run["trips"], run["case"], "Besatzungseinsatz – Test", ["Zeile 1 – mit Gedankenstrich", "Zeile 2 ≤ Ø"])
    assert pdf[:5] == b"%PDF-" and len(pdf) > 1000
