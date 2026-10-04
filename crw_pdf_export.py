"""Dienstplan als PDF (fpdf2, Kernschrift Helvetica: Umlaute gehen, Gedankenstrich, Euro-Zeichen, Emoji und U+2212 nicht)."""
from __future__ import annotations

from fpdf import FPDF

import crw_constants as C
from crw_rules import DRIVE

_REPLACE = {"–": "-", "—": "-", "−": "-", "≤": "<=", "≥": ">=", "→": "->", "↔": "<->", "…": "...", "€": "EUR", "·": ".", "Ø": "Durchschnitt"}


def _clean(text: str) -> str:
    for a, b in _REPLACE.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_roster_pdf(trips: list, case: dict, title: str, summary_lines: list) -> bytes:
    """Besatzungseinsatz: je Paarung ihre Dienste mit allen Fahrten (gefahren oder mitgefahren), Zeiten und Kosten."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, _clean(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in summary_lines:
        pdf.multi_cell(0, 5, _clean(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    for pi, p in enumerate(case["pairings"]):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _clean(f"Paarung {pi + 1} - Heimatbasis Station {p['base']} - {len(p['duties'])} Dienst(e), {p['nights']} Nacht/Nächte auswärts, Kosten {C.fmt_cost(p['cost'])}"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for di, duty in enumerate(p["duties"]):
            t0, t1 = trips[duty[0][0]], trips[duty[-1][0]]
            pdf.cell(0, 5, _clean(f"  Dienst {di + 1}: {C.fmt_hm(t0.dep)} bis {C.fmt_hm(t1.arr)} (Spanne {C.fmt_dur(t1.arr - t0.dep)})"), new_x="LMARGIN", new_y="NEXT")
            for idx, mode in duty:
                t = trips[idx]
                pdf.cell(0, 4.5, _clean(f"      Station {t.o} -> Station {t.d}   {C.fmt_hm(t.dep)} - {C.fmt_hm(t.arr)}   {'gefahren' if mode == DRIVE else 'mitgefahren'}"),
                         new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
    if case["uncovered"]:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, _clean(f"Unüberdeckte Fahrten ({len(case['uncovered'])})"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for idx in case["uncovered"]:
            t = trips[idx]
            pdf.cell(0, 4.5, _clean(f"  Station {t.o} -> Station {t.d}   {C.fmt_hm(t.dep)} - {C.fmt_hm(t.arr)}"), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())
