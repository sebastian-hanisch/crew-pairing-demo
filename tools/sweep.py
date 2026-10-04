"""Reproduktion der Messreihe (Minuten, nicht in der CI): Größenreihe (3 / 4 / 5 Züge, je 20 Netze) und Regelpreise (14 Varianten auf 20 Netzen mit 4 Zügen).

  python tools/sweep.py              schreibt data/crw_results.json (parallel, rund 10-20 Minuten)
"""
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import crw_constants as C  # noqa: E402
from crw_evaluation import bases_of, build_trips, make_rules, solve_case  # noqa: E402

KEYS = ("lp", "ip", "ip_status", "greedy", "wage", "hotel", "nights", "iterations", "columns", "t_cg", "t_pricing", "t_ip")


def summary(case: dict) -> dict:
    out = {k: case[k] for k in KEYS}
    out.update({"n": case["n"], "pairings": len(case["pairings"]), "uncovered": len(case["uncovered"]), "greedy_uncovered": case["greedy_uncovered"]})
    return out


def run_size(args):
    trains, seed = args
    trips, used, n_raw = build_trips(trains, seed)
    case = solve_case(trips, make_rules(), C.BASES_ALL, ip_limit=30.0)
    return {"trains": trains, "seed": seed, "used_seed": used, "raw": n_raw, **summary(case)}


def run_variants(seed):
    trips, used, n_raw = build_trips(4, seed)
    out = {"seed": seed, "used_seed": used, "n": len(trips), "raw": n_raw, "variants": {}}
    for name, kw, n_bases in C.SWEEP_VARIANTS:
        case = solve_case(trips, make_rules(**kw), bases_of(n_bases), ip_limit=30.0)
        out["variants"][name] = summary(case)
    return out


def main():
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=12) as ex:
        sizes = list(ex.map(run_size, [(t, s) for t in C.SWEEP_TRAINS for s in C.SWEEP_SEEDS]))
        print("Größenreihe fertig", round(time.time() - t0), "s", flush=True)
        variants = list(ex.map(run_variants, C.SWEEP_SEEDS))
    res = {"meta": {"seeds": [C.SWEEP_SEEDS.start, C.SWEEP_SEEDS.stop], "trains": list(C.SWEEP_TRAINS), "stations": C.N_STATIONS, "days": C.DAYS, "hop": C.HOP,
                    "penalty": C.PENALTY, "std_rules": C.STD_RULES, "variants": [v[0] for v in C.SWEEP_VARIANTS], "ip_time_limit": 30.0},
           "sizes": sizes, "variants": variants}
    out = ROOT / C.RESULTS_FILE
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    print("geschrieben:", out, round(out.stat().st_size / 1024), "KB,", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
