"""Compare the old nearest-driver rules with the solver on random scenarios.

    python scripts/sim_dispatch.py                 # default sweep
    python scripts/sim_dispatch.py --runs 20 --drivers 8 --seeds 10

Everything is generated from the seed, nothing is hardcoded. For each
scenario both methods give out the same runs to the same drivers; we then
measure the same trip km (base -> stops -> plant -> base, straight line x
ROAD_FACTOR). Results are printed and written to a CSV."""
import argparse
import csv
import os
import random
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import config as C                      # noqa: E402
from app import optimizer as O                   # noqa: E402
from app.matching import haversine               # noqa: E402
from app.travel import Travel                    # noqa: E402

PLANTS = [(28.55, 77.45), (28.45, 77.05), (28.70, 77.30)]   # fictional
BOX = (28.30, 28.90, 76.90, 77.70)                          # lat/lng range
CAPS = [150, 300, 500, 1000]


def scenario(n_runs, n_drivers, seed):
    rnd = random.Random(seed)
    pt = lambda: (rnd.uniform(BOX[0], BOX[1]), rnd.uniform(BOX[2], BOX[3]))
    runs = [O.Run(i, round(rnd.uniform(20, 300), 1),
                  [pt() for _ in range(rnd.randint(1, 3))], rnd.choice(PLANTS))
            for i in range(1, n_runs + 1)]
    drivers = [O.Driver(100 + j, pt(), rnd.choice(CAPS))
               for j in range(n_drivers)]
    return runs, drivers


def rules(runs, drivers):
    """The old rule: one run at a time, nearest eligible driver, with
    DISPATCH_LOAD_KM extra for each run they already hold."""
    held = {d.id: d.held for d in drivers}
    out = {}
    for r in runs:
        ok = [d for d in drivers if O.eligible(d, r)]
        if not ok:
            out[r.id] = None
            continue
        best = min(ok, key=lambda d: (
            haversine(*d.base, *r.stops[0]) + C.DISPATCH_LOAD_KM * held[d.id],
            d.id))
        held[best.id] += 1
        out[r.id] = best.id
    return out


def measure(runs, drivers, assign, travel):
    by_id = {d.id: d for d in drivers}
    per = {d.id: 0.0 for d in drivers}
    for r in runs:
        d = assign[r.id]
        if d is not None:
            per[d] += travel.path_km(O.trip_points(by_id[d], r))
    return (round(sum(per.values()), 1), round(max(per.values()), 1),
            sum(1 for v in assign.values() if v is None))


def one(n_runs, n_drivers, seed):
    runs, drivers = scenario(n_runs, n_drivers, seed)
    pts = [d.base for d in drivers] + [
        q for r in runs for q in (*r.stops, r.plant)]
    tv = Travel(pts)
    t = time.time()
    a_rules = rules(runs, drivers)
    t_rules = time.time() - t
    t = time.time()
    res = O.solve(runs, drivers, tv)
    t_solver = time.time() - t
    kr, mr, ur = measure(runs, drivers, a_rules, tv)
    ks, ms, us = measure(runs, drivers, res.assign, tv)
    return {"runs": n_runs, "drivers": n_drivers, "seed": seed,
            "rules_total_km": kr, "solver_total_km": ks,
            "rules_max_driver_km": mr, "solver_max_driver_km": ms,
            "rules_unassigned": ur, "solver_unassigned": us,
            "rules_seconds": round(t_rules, 4),
            "solver_seconds": round(t_solver, 4),
            "solver_status": res.status}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, nargs="*", default=[5, 10, 20, 40])
    ap.add_argument("--drivers", type=int, nargs="*", default=[3, 5, 8, 12])
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default="sim_dispatch_results.csv")
    a = ap.parse_args()
    if len(a.runs) != len(a.drivers):
        sys.exit("--runs and --drivers need the same number of values")
    rows = []
    for n, m in zip(a.runs, a.drivers):
        rows += [one(n, m, seed) for seed in range(1, a.seeds + 1)]
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    print(f"{'runs':>4} {'drv':>3} | {'total km':>17} | {'max driver km':>17}"
          f" | {'unassigned':>10} | {'seconds':>13}")
    print(f"{'':>4} {'':>3} | {'rules':>8} {'solver':>8} | {'rules':>8} "
          f"{'solver':>8} | {'rules':>4} {'solver':>5} | {'rules':>6} "
          f"{'solver':>6}")
    for n, m in zip(a.runs, a.drivers):
        g = [r for r in rows if r["runs"] == n and r["drivers"] == m]
        avg = lambda k: statistics.mean(r[k] for r in g)
        print(f"{n:>4} {m:>3} | {avg('rules_total_km'):>8.1f} "
              f"{avg('solver_total_km'):>8.1f} | "
              f"{avg('rules_max_driver_km'):>8.1f} "
              f"{avg('solver_max_driver_km'):>8.1f} | "
              f"{sum(r['rules_unassigned'] for r in g):>4} "
              f"{sum(r['solver_unassigned'] for r in g):>5} | "
              f"{avg('rules_seconds'):>6.3f} {avg('solver_seconds'):>6.3f}")
    print(f"\n(averages over {a.seeds} seeds; unassigned is a sum; "
          f"per-seed rows in {a.out})")


if __name__ == "__main__":
    main()
