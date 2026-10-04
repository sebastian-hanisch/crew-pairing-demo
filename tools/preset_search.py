"""Sucht einen Seed außerhalb der Messreihen-Seeds, bei dem alle Abnahmekriterien aller Presets gelten, und schreibt den Messbericht nach tools/PRESET_SWEEP.md.
Braucht data/crw_results.json.

  python tools/preset_search.py [Anzahl Seeds (Standard 30)]
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import crw_constants as C  # noqa: E402
import crw_evaluation as E  # noqa: E402
import crw_results as R  # noqa: E402
import crw_stories as S  # noqa: E402

START = 500


def evaluate(seed):
    res = R.load_results()
    out = {}
    for name in C.PRESET_ORDER:
        p = C.PRESETS[name]
        settings = {k: p[k] for k in ("trains", "rest", "hotel", "cont", "span", "duties", "bases", "deadhead")}
        settings["seed"] = seed
        run = E.run_live(settings)
        out[name] = (S.check(name, S.facts_for(name, run, res)), run["seed"], round(E.price_of_rules(run)["delta_pct"], 1))
    return seed, out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    with ProcessPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(evaluate, range(START, START + n)))
    lines = ["# Preset-Abstimmung (tools/preset_search.py)", "", f"Seeds {START}..{START + n - 1}, außerhalb der Messreihen-Seeds ({C.SWEEP_SEEDS.start}-{C.SWEEP_SEEDS.stop - 1}). "
             "Alle fünf Presets zeigen dasselbe Netz; ein Seed besteht, wenn alle Kriterien aller Presets gelten (`crw_stories.py`).", ""]
    good = [seed for seed, out in results if all(c for name in out for _, _, c in out[name][0])]
    lines += [f"Bestanden: {len(good)} von {len(results)} Seeds: {good}", ""]
    for name in C.PRESET_ORDER:
        fails = {}
        for seed, out in results:
            for cid, _, ok in out[name][0]:
                fails[cid] = fails.get(cid, 0) + (not ok)
        lines.append(f"- {name}: durchgefallen je Kriterium " + ", ".join(f"{k} {v}x" for k, v in fails.items()))
    if good:
        lines += ["", f"Gewählt: Seed {good[0]}; Kostenänderungen der Presets: " + ", ".join(f"{name} {dict(results)[good[0]][name][2]:+.1f} %" for name in C.PRESET_ORDER)]
    (ROOT / "tools" / "PRESET_SWEEP.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("bestanden:", good)


if __name__ == "__main__":
    main()
