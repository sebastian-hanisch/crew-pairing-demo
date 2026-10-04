# Preset-Abstimmung (tools/preset_search.py)

Seeds 500..539, außerhalb der Messreihen-Seeds (100-119). Alle fünf Presets zeigen dasselbe Netz; ein Seed besteht, wenn alle Kriterien aller Presets gelten (`crw_stories.py`).

Bestanden: 21 von 40 Seeds: [500, 506, 507, 510, 515, 517, 520, 522, 523, 526, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 539]

- Standard: durchgefallen je Kriterium all_covered 0x, greedy_worse 0x, sweep_greedy_gap 0x, has_nights 0x
- Teures Hotel: durchgefallen je Kriterium cost_up 0x, fewer_nights 0x, sweep_significant 0x
- Lange Ruhezeit: durchgefallen je Kriterium cost_up 13x, sweep_significant 0x
- Strenge Lenkzeit: durchgefallen je Kriterium cost_up 7x, sweep_significant 0x, covered 0x
- Ohne Mitfahren: durchgefallen je Kriterium cost_up_or_uncovered 6x, sweep_significant 0x

Gewählt: Seed 500; Kostenänderungen der Presets: Standard +0.0 %, Teures Hotel +74.7 %, Lange Ruhezeit +14.1 %, Strenge Lenkzeit +20.3 %, Ohne Mitfahren +13.8 %
