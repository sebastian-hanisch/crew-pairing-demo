# Crew Pairing: Besatzungseinsatz im Zugverkehr (Streamlit-Demo)

**[→ Demo live ausprobieren](https://sebastianhanisch-crew-pairing-demo.streamlit.app/)**

Interaktive **Fall-Demo** zum **Crew Pairing** im Portfolio von [Sebastian Hanisch](https://sebastianhanisch.net) (Operations Research und Machine Learning). **Zweiter Baustein der
Reihe Bahn/Schienenverkehr** nach dem [Taktfahrplan](https://github.com/sebastian-hanisch/taktfahrplan-demo): Die Züge fahren, jetzt braucht jede Fahrt eine Besatzung.

Aus Zugumläufen auf einer Strecke, zwei Heimatbasen und einem Regelwerk (ununterbrochene Lenkzeit, Ruhezeit, Dienstspanne, Hotel, Mitfahren) entstehen **Paarungen**: Dienstfolgen über
mehrere Tage, die an der Heimatbasis beginnen und enden. Die Paarungen werden nicht aufgezählt, sondern per **Spaltengenerierung** mit einem **Ressourcen-Kürzesten-Weg** als Pricing
erzeugt. Die Demo zeigt vor allem, **was jede einzelne Regel kostet**, und ehrlich, wie weit die Lösung von der Schranke entfernt ist.

## Kernfrage

Was kostet jede Regel des Besatzungseinsatzes, und wie viel verschenkt ein gieriges Vorgehen gegenüber der Spaltengenerierung? Die Frage ist **nicht** „Column Generation gegen Heuristik“ als
Selbstzweck: Die Master-Struktur ist die aus [column-generation-demo](https://github.com/sebastian-hanisch/column-generation-demo) (Pricing = Rucksack) und
[mcf-column-generation-demo](https://github.com/sebastian-hanisch/mcf-column-generation-demo) (Pricing = kürzester Weg). Neu sind das Pricing mit Zeit- und Lenkzeit-Ressourcen und das Regelwerk.

## Befunde und Korrekturen gegenüber dem Plan

- **Das erste Netz war zu leicht.** Mit Linien nur zwischen Basis und Außenstation war jeder Dienst ein Hin und Zurück; Ruhezeit, Hotel und Übernachtung banden nie (Ruhezeit 9 → 13 h: +0,0 %).
  Die Messreihe wurde auf **Zugumläufe in Teilstrecken** mit zwei Heimatbasen und Mitfahren umgebaut, erst dann greifen die Regeln.
- **Die Spaltengenerierung ist nicht automatisch optimal.** Im ersten Netz traf die ganzzahlige Auswahl die Schranke praktisch immer; im umgebauten Netz liegt sie 3 bis 5 % darüber (siehe Befunde).
- **Eine gemeinsame Fahrtenmenge für alle Regelvarianten schrumpfte auf fast nichts.** Gemessen wird deshalb auf den unter den Standardregeln überdeckbaren Fahrten; strengere Regeln dürfen
  Fahrten unüberdeckt lassen und zahlen dafür eine Strafe, die getrennt ausgewiesen wird.
- **Port 8958** (8951 war von einer parallelen Arbeit belegt).

## Modell

- **Netz:** Strecke mit 7 Stationen, 2 Tage; jeder Zug pendelt zwischen zwei Stationen, 75 min je Teilstrecke, 4 min Halt, 25 min Wende. Jede Teilstrecke ist eine Fahrt, die eine Besatzung braucht.
  Im selben Zug sitzen bleiben braucht keine Umsteigezeit, an jeder Station kann gewechselt werden (15 min Mindestzeit zwischen verschiedenen Zügen). Ganzzahlig mit **SplitMix64**
  (`crw_rng.py`, `crw_network.py`); 3 / 4 / 5 Züge ergeben im Mittel 47 / 69 / 88 überdeckbare Teilstrecken.
- **Dienst und Paarung** (`crw_rules.py`): Ein Dienst ist eine Kette von Fahrten, jede **gefahren** (überdeckt, zählt als Lenkzeit) oder **mitgefahren** (überdeckt nicht, zählt als Pause).
  Standard: höchstens 11 h Dienstspanne, 8 h Lenkzeit, 4,5 h ununterbrochen (eine Lücke ab 30 min unterbricht), Dienst mindestens bezahlt wie 300 min. Eine Paarung verbindet bis zu 3 Dienste durch
  Ruhezeiten von mindestens 9 h; wer sie nicht an der Heimatbasis verbringt, kostet eine Hotelnacht (500). Alle Kosten in Minutenäquivalenten.
- **Master** (`crw_master.py`): Mengenüberdeckung: jede Fahrt wird von mindestens einer Paarung gefahren. Strafspalten (5 000 je Fahrt) lassen Fahrten unüberdeckt, wenn eine Regel sie unüberdeckbar macht.
- **Pricing** (`crw_pricing.py`): Labeling je Heimatbasis über die nach Abfahrt geordneten Fahrten. Ein Label trägt reduzierte Kosten, Dienstbeginn, Lenkzeit und ununterbrochene Lenkzeit;
  Dominanz streicht Labels, die nicht teurer, später begonnen und weniger verbraucht sind.

## Methodik

- **Spaltengenerierung:** LP über die bekannten Paarungen (HiGHS), Duale an das Pricing, neue Paarungen mit negativen reduzierten Kosten, bis keine mehr kommt: Ergebnis ist die **LP-Schranke**.
- **Ganzzahlig:** Auswahl unter allen erzeugten Spalten (HiGHS, `milp`). **Gierig:** immer die Spalte mit den geringsten Kosten je neu überdeckter Fahrt, danach Überflüssiges streichen.
- **Vorgerechnete Messreihe** (`tools/sweep.py` → `data/crw_results.json`, rund zwei Minuten parallel): 3 / 4 / 5 Züge × 20 Netze und 14 Regelvarianten auf 20 Netzen mit 4 Zügen. Live läuft das gewählte Netz
  unter dem gewählten Regelwerk und unter den Standardregeln.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen stehen in `tests/test_claims.py`. Je 20 Netze (Seeds 100–119), Kosten in Minutenäquivalenten, Mittel ± Standardfehler.

| Frage | Befund |
|---|---|
| Wie groß sind die Netze und was kostet der Standard? | 4 Züge: im Mittel 69 Teilstrecken, 13.1 Paarungen mit 6.8 Übernachtungen; **73 %** der Kosten sind Lohn, **27 %** Hotel. |
| Wie nah liegt die ganzzahlige Lösung an der Schranke? | **5.2 % / 4.1 % / 3.4 %** über der LP-Schranke bei 3 / 4 / 5 Zügen (größte Lücke 15.5 / 12.7 / 8.2 %); ganzzahlig gleich LP in nur 6 / 2 / 0 von 20 Netzen. Der Abstand besteht aus Ganzzahligkeitslücke und Spaltenwahl; ein Branch-and-Price fehlt. |
| Was verschenkt ein gieriges Vorgehen? | **17.3 ± 2.1 % / 19.1 ± 1.9 % / 20.3 ± 1.5 %** über der LP-Schranke, in jedem der 60 Netze mindestens 1.7 %. |
| Was kostet das Hotel? | Hotelpreis ×2: **+25.4 ± 1.6 %**, ×4: **+77.0 ± 4.5 %**, in allen 20 Netzen teurer. |
| Und die Ruhezeit? | 11 h: **+15.8 ± 6.2 %**, 13 h: **+38.6 ± 12.0 %**; dabei bleiben im Mittel 0.4 bzw. 1.0 Fahrten unüberdeckt. |
| Und die Lenkzeit? | Ununterbrochen höchstens 3 h statt 4,5 h: **+11.4 ± 1.7 %**. Gesamtlenkzeit 7 h: **+1.0 %**, 6 h: **+3.6 %**. Garantie 360 statt 300: **+2.0 %**. |
| Was bringt das Mitfahren? | Ohne Mitfahren bleiben **2.4 Fahrten** unüberdeckt und die Kosten ohne Strafe steigen um **9.3 %**. |
| Wie wichtig sind Übernachtung und zweite Basis? | Mit höchstens 1 Dienst je Paarung bleiben **27.6** von 69 Fahrten unüberdeckt, mit nur einer Heimatbasis **45.9**. Zwei Dienste je Paarung kosten +11.1 ± 7.0 %. Dienstspanne 9 h macht **4.8** Fahrten unüberdeckbar. |
| Wie lange rechnet die Spaltengenerierung? | Median **0.5 / 1.7 / 3.5 s** bei 3 / 4 / 5 Zügen, davon Pricing 64 / 73 / 76 %; 74 / 86 / 106 Iterationen. |

Auf dem Netz der Voreinstellung (Seed 500, 4 Züge) kosten die Presets gegen den Standard: Teures Hotel +74.7 %, Lange Ruhezeit +14.1 %, Strenge Lenkzeit +20.3 %, Ohne Mitfahren +13.8 %
(`tools/PRESET_SWEEP.md`).

## Ehrliche Grenzen

- Die **ganzzahlige Lösung ist nicht das Optimum**: sie wählt nur unter den erzeugten Spalten. Auf einem einzelnen Netz kann eine strengere Regel deshalb knapp billiger ausfallen; die Meldung
  nennt als Schwelle die Lücke der Messreihe. Ein Branch-and-Price (wie in [branch-and-price-demo](https://github.com/sebastian-hanisch/branch-and-price-demo)) wäre der Ausbau.
- Synthetische Strecke, Kosten in Minutenäquivalenten, keine Tarifwerte: die Preise der Regeln sind Größenordnungen.
- Die Fahrten sind gegeben (kein Fahrzeugumlauf), kein Rostering (Gerechtigkeit zwischen Personen), keine Wochenruhe, keine Krankheitsreserve.
- Fahrten, die schon in den Standardregeln nicht überdeckbar sind (zum Beispiel am ersten Morgen, wo noch keine Besatzung angereist sein kann), sind aus dem Netz entfernt.
- Die gierige Lösung nutzt den Spaltenpool der Spaltengenerierung; ein Vergleich mit einem Plan ohne Spaltengenerierung (reine Handarbeit) ist nicht Teil der Demo.

## Tests

Siehe `tests/`: Regelwerk von Hand gerechnet, **Pricer gegen Vollaufzählung** aller Paarungen für zufällige Duale (mit und ohne Mitfahren), Spaltengenerierung gegen das LP über alle Paarungen
(zwei Heimatbasen), Netzgenerator gegen eingefrorene Werte, Statistik an einer von Hand gerechneten Mini-Ergebnisdatei, Preset-Kriterien mit künstlichen Werten (jedes Kriterium kippt
einzeln), `test_claims.py` (jede README-Zahl gegen die Ergebnisdatei), AppTest-Rauchtests (Voreinstellung, jedes Preset, Randwerte, Permalink, Ganzzahlig-Tab).
Keine Wall-Clock-Assertions. `tools/mutation_check.py` baut einzelne Fehler in die Module ein und prüft, ob die Tests sie finden.

```
python -m pytest tests -q
```

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `crw_constants.py` | feste Annahmen, Regler-Stufen, Presets |
| `crw_rng.py`, `crw_network.py` | SplitMix64; Zugumläufe in Teilstrecken |
| `crw_rules.py` | Fahrten, Dienste, Paarungen: Regeln, Prüfer, Kosten |
| `crw_pricing.py` | Pricing: Ressourcen-Kürzester-Weg mit Labeling und Dominanz |
| `crw_master.py` | Master-LP, Spaltengenerierung, ganzzahlige Auswahl, gierig |
| `crw_evaluation.py` | Live-Rechnung, Preis der Regeln, Meldungen |
| `crw_results.py`, `crw_stories.py`, `crw_presets.py` | Auswertung der Messreihe; Preset-Kriterien; Permalink und Presets |
| `crw_visualization.py`, `crw_pdf_export.py` | Plotly-Figuren; Dienstplan als PDF |
| `data/crw_results.json` | Ergebnisse der Messreihe |
| `tools/` | `sweep.py`, `preset_search.py`, `mutation_check.py`, `PRESET_SWEEP.md` |

## Bewusst nicht umgesetzt

Branch-and-Price, Fahrzeugumlauf (nächster Baustein der Reihe), Rostering, Wochenruhe, Nachtdienst-Zuschläge, mehrere Fahrzeugtypen und Streckenkenntnis, Störungsmanagement.

## Lokal ausführen

```
pip install -r requirements.txt
streamlit run app.py
```

Die Messreihe neu erzeugen: `python tools/sweep.py`.

Gebaut mit Streamlit, Plotly, NumPy, SciPy (HiGHS) und fpdf2.
