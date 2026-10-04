"""Fehler-Einbau-Test: baut einzelne Fehler in die Module ein und prüft, ob die Tests (ohne AppTests) sie finden.

Aufruf (im Projektordner): python tools/mutation_check.py [Teilstring des Dateinamens] [--jobs N] [--indices 5,8-12] [--with-app] [--dry-run]
Jeder Mutant ersetzt genau eine Stelle; Überlebende sind entweder gleichwertig (kein sichtbarer Unterschied) oder eine Lücke der Tests. Die Kopie liegt je Mutant in einem
temporären Ordner; PYTHONDONTWRITEBYTECODE=1, damit veralteter Bytecode keine Überlebenden vortäuscht; Quelltexte als LF. Ein Mutant kann in eine Endlosschleife laufen;
nach TIMEOUT Sekunden gilt er als gefunden. `--with-app` nimmt die AppTests hinzu, `--dry-run` prüft nur, ob jede Zeichenkette genau einmal vorkommt."""
import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
WITH_APP = "--with-app" in sys.argv
TIMEOUT = 600
TEST_ORDER = ["test_results.py", "test_presets.py", "test_network.py", "test_core.py", "test_pdf.py", "test_stories.py", "test_evaluation.py", "test_gaps.py", "test_claims.py"]

MUTANTS = [
    ('crw_rules.py', '    return b.dep >= a.arr + r.min_conn', '    return b.dep > a.arr + r.min_conn'),
    ('crw_rules.py', '        return b.dep >= a.arr\n', '        return b.dep >= a.arr + r.min_conn\n'),
    ('crw_rules.py', '    return max(r.guarantee, duty[-1][0].arr - duty[0][0].dep)', '    return max(r.guarantee, duty[-1][0].arr - duty[-1][0].dep)'),
    ('crw_rules.py', '            if t.dep - duty[i - 1][0].arr >= r.break_gap:', '            if t.dep - duty[i - 1][0].arr > r.break_gap:'),
    ('crw_rules.py', '        if cont > r.max_cont or drive > r.max_drive:\n            return False\n    return', '        if cont >= r.max_cont or drive > r.max_drive:\n            return False\n    return'),
    ('crw_rules.py', '        if cont > r.max_cont or drive > r.max_drive:\n            return False\n    return', '        if cont > r.max_cont or drive >= r.max_drive:\n            return False\n    return'),
    ('crw_rules.py', '    return duty[-1][0].arr - duty[0][0].dep <= r.max_span and any(m == DRIVE for _, m in duty)', '    return duty[-1][0].arr - duty[0][0].dep < r.max_span and any(m == DRIVE for _, m in duty)'),
    ('crw_rules.py', '    return duty[-1][0].arr - duty[0][0].dep <= r.max_span and any(m == DRIVE for _, m in duty)', '    return duty[-1][0].arr - duty[0][0].dep <= r.max_span'),
    ('crw_rules.py', '        else:\n            cont = 0\n', '        else:\n            pass\n'),
    ('crw_rules.py', 'or duties[-1][-1][0].d != base:', 'or duties[-1][-1][0].d == base:'),
    ('crw_rules.py', '            if duty[0][0].o != prev.d or gap < r.rest or gap > r.max_rest:', '            if duty[0][0].o != prev.d or gap <= r.rest or gap > r.max_rest:'),
    ('crw_rules.py', '            if duty[0][0].o != prev.d or gap < r.rest or gap > r.max_rest:', '            if duty[0][0].o != prev.d or gap < r.rest:'),
    ('crw_rules.py', '    nights = sum(1 for i in range(1, len(duties)) if duties[i][0][0].o != base)', '    nights = sum(1 for i in range(1, len(duties)) if duties[i][0][0].o == base)'),
    ('crw_rules.py', '    return {i for d in duties for i, m in d if m == DRIVE}', '    return {i for d in duties for i, m in d}'),
    ('crw_pricing.py', '    return (a.rc <= b.rc + 1e-12 and a.start >= b.start and a.drive <= b.drive and a.cont <= b.cont and (a.has_drive or not b.has_drive))', '    return (a.rc <= b.rc + 1e-12 and a.start <= b.start and a.drive <= b.drive and a.cont <= b.cont and (a.has_drive or not b.has_drive))'),
    ('crw_pricing.py', '    return (a.rc <= b.rc + 1e-12 and a.start >= b.start and a.drive <= b.drive and a.cont <= b.cont and (a.has_drive or not b.has_drive))', '    return (a.rc <= b.rc + 1e-12 and a.start >= b.start and a.drive <= b.drive and (a.has_drive or not b.has_drive))'),
    ('crw_pricing.py', '                    hotel = 0 if trips[i].d == base else r.hotel', '                    hotel = 0 if trips[i].d != base else r.hotel'),
    ('crw_pricing.py', '                gain = -float(duals[j]) if mode == DRIVE else 0.0', '                gain = -float(duals[j])'),
    ('crw_pricing.py', '                val = l.rc + max(r.guarantee, t.arr - l.start)', '                val = l.rc + (t.arr - l.start)'),
    ('crw_pricing.py', '                            cont = dur if gap >= r.break_gap else l.cont + dur', '                            cont = l.cont + dur'),
    ('crw_pricing.py', '                            cont, drive = 0, l.drive', '                            cont, drive = l.cont, l.drive'),
    ('crw_pricing.py', '            if r.rest <= gap <= r.max_rest:', '            if r.rest <= gap:'),
    ('crw_pricing.py', '        if t.d != base:\n            continue', '        if t.d == base:\n            continue'),
    ('crw_pricing.py', '        if best is not None and best.rc < -tol:', '        if best is not None and best.rc < tol:'),
    ('crw_pricing.py', '                if not l.has_drive:\n                    continue', '                if False:\n                    continue'),
    ('crw_master.py', '    res = linprog(np.array(costs, dtype=float), A_ub=-A, b_ub=-np.ones(n), bounds=(0, None), method="highs")', '    res = linprog(np.array(costs, dtype=float), A_ub=-A, b_ub=-np.ones(n) * 0.5, bounds=(0, None), method="highs")'),
    ('crw_master.py', '    return res.fun, res.x, -res.ineqlin.marginals', '    return res.fun, res.x, res.ineqlin.marginals'),
    ('crw_master.py', '        costs = [float(penalty)] * n', '        costs = [float(penalty) / 2] * n'),
    ('crw_master.py', '        best = min((c for c in range(len(columns)) if cover[c] & unc), key=lambda c: (costs[c] / len(cover[c] & unc), c))', '        best = min((c for c in range(len(columns)) if cover[c] & unc), key=lambda c: (costs[c], c))'),
    ('crw_master.py', '        if rest and set().union(*[cover[x] for x in rest]) >= set(range(n)):', '        if False:'),
    ('crw_master.py', '    for c in sorted(chosen, key=lambda c: -costs[c]):', '    for c in sorted(chosen, key=lambda c: costs[c]):'),
    ('crw_master.py', '            if key in known:\n                continue', '            if False:\n                continue'),
    ('crw_network.py', '        b = a + 2 + rng.below(n_stations - a - 2)', '        b = a + 1 + rng.below(n_stations - a - 1)'),
    ('crw_network.py', '            while t - day * 1440 <= 21 * 60:', '            while t - day * 1440 <= 22 * 60:'),
    ('crw_network.py', '                    t += hop + (dwell if pos + step != nxt else 0)', '                    t += hop'),
    ('crw_rng.py', '    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK', '    z = ((z ^ (z >> 29)) * 0xBF58476D1CE4E5B9) & _MASK'),
    ('crw_evaluation.py', '    return C.BASES_ALL if n_bases == 2 else (C.BASES_ALL[0],)', '    return C.BASES_ALL if n_bases == 1 else (C.BASES_ALL[0],)'),
    ('crw_evaluation.py', '    return 100 * (case["ip"] / case["lp"] - 1) if case["lp"] else 0.0', '    return 100 * (case["lp"] / case["ip"] - 1) if case["lp"] else 0.0'),
    ('crw_evaluation.py', '    if abs(p["delta_pct"]) < threshold and p["new_uncovered"] == 0:', '    if abs(p["delta_pct"]) <= threshold and p["new_uncovered"] == 0:'),
    ('crw_evaluation.py', '    wage = sum(p["wage"] for p in pairings)', '    wage = sum(p["cost"] for p in pairings)'),
    ('crw_evaluation.py', '            "is_standard": std is case,', '            "is_standard": True,'),
    ('crw_results.py', '            rel.append(100 * (a["ip"] / b["ip"] - 1))', '            rel.append(100 * (b["ip"] / a["ip"] - 1))'),
    ('crw_results.py', '    gap_gr = [100 * (r["greedy"] / r["lp"] - 1) for r in rows]', '    gap_gr = [100 * (r["greedy"] / r["ip"] - 1) for r in rows]'),
]


def check_unique():
    bad = []
    for n, (name, old, new) in enumerate(MUTANTS, 1):
        text = (ROOT / name).read_bytes().decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            bad.append((n, name, old[:70], text.count(old)))
        if old == new:
            bad.append((n, name, "alt == neu", 0))
    return bad


def run_one(args):
    n, name, old, new, base = args
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=f"tkt_mut{n}_"))
    try:
        shutil.copytree(base, tmp, dirs_exist_ok=True)
        path = tmp / name
        original = path.read_bytes().decode("utf-8")
        path.write_bytes(original.replace(old, new).encode("utf-8"))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        files = [f"tests/{f}" for f in TEST_ORDER + (["test_app.py"] if WITH_APP else [])]
        try:
            r = subprocess.run([PY, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *files], cwd=tmp, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT)
            return n, name, old, new, r.returncode == 0, False
        except subprocess.TimeoutExpired:
            return n, name, old, new, False, True                 # Endlosschleife oder zu langsam: gilt als gefunden
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    only = args[0] if args else ""
    jobs = 6
    if "--jobs" in sys.argv:
        jobs = int(sys.argv[sys.argv.index("--jobs") + 1])
        only = "" if only == str(jobs) else only
    wanted = None
    if "--indices" in sys.argv:
        spec = sys.argv[sys.argv.index("--indices") + 1]
        only = "" if only == spec else only
        wanted = set()
        for part in spec.split(","):
            lo, _, hi = part.partition("-")
            wanted.update(range(int(lo), int(hi or lo) + 1))
    bad = check_unique()
    for b in bad:
        print("FEHLER (Stelle nicht eindeutig gefunden):", b)
    if "--dry-run" in sys.argv:
        print(f"{len(MUTANTS)} Mutanten, {len(bad)} Fehler in der Mutantenliste")
        return
    base = pathlib.Path(tempfile.mkdtemp(prefix="tkt_mut_base_"))
    for f in ROOT.glob("*.py"):
        (base / f.name).write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    shutil.copytree(ROOT / "tests", base / "tests", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(ROOT / "README.md", base / "README.md")
    shutil.copytree(ROOT / "data", base / "data")
    for f in (base / "tests").glob("*.py"):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    bad_ids = {b[0] for b in bad}
    work = [(n, name, old, new, base) for n, (name, old, new) in enumerate(MUTANTS, 1) if n not in bad_ids and (not only or only in name) and (wanted is None or n in wanted)]
    survivors, killed = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        for n, name, old, new, survived, timeout in pool.map(run_one, work):
            if timeout:
                print(f"[{n:3d}] Zeitüberschreitung (als gefunden gezählt)  {name}", flush=True)
            if survived:
                survivors.append((n, name, old[:70], new[:70]))
                print(f"[{n:3d}] ÜBERLEBT  {name}: {old[:70]!r} -> {new[:70]!r}", flush=True)
            else:
                killed += 1
                print(f"[{n:3d}] gefunden  {name}", flush=True)
    print(f"\n{killed} gefunden, {len(survivors)} überlebt, {len(bad)} Fehler in der Mutantenliste")
    shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    main()
