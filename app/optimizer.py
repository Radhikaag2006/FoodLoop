"""Give all waiting runs to drivers together, and order the stops in a run.

This is an optimisation solver (Google OR-Tools CP-SAT), not machine
learning. It picks the assignment with the least total driving, subject to
hard rules, so one run is not given to the nearest driver at the expense of
the next one.

Hard rules (never traded off): a driver must be active and available (the
caller only passes those), the vehicle must carry the run's kg, and a
driver who declined a run never gets it back. Soft terms in the cost: total
trip km, a small extra cost for drivers who already hold runs, and a large
cost for leaving a run unassigned."""
import time
from dataclasses import dataclass, field

from . import config as C


@dataclass
class Run:
    id: int
    kg: float
    stops: list                     # [(lat, lng)] in driving order
    plant: tuple                    # (lat, lng), where the run ends
    banned: set = field(default_factory=set)   # drivers who declined it


@dataclass
class Driver:
    id: int
    base: tuple
    cap: float
    held: int = 0                   # open runs they already hold


@dataclass
class Result:
    assign: dict                    # run id -> driver id or None
    km: dict                        # run id -> trip km for that driver
    why: dict                       # run id -> short reason
    total_km: float
    status: str                     # "optimal" | "feasible" | "greedy"
    seconds: float = 0.0


# ---------- costs ----------
def trip_points(driver, run):
    """base -> stops -> plant -> base, the same trip a fare is paid for."""
    return [driver.base, *run.stops, run.plant, driver.base]


def eligible(driver, run):
    return driver.cap >= run.kg and driver.id not in run.banned


def cost_matrix(runs, drivers, travel):
    """cost[d][r] in km (None where the driver may not take the run)."""
    return [[travel.path_km(trip_points(d, r)) if eligible(d, r) else None
             for r in runs] for d in drivers]


# ---------- the solver ----------
def solve_costs(cost, held, load_km=None, unassigned_km=None,
                time_limit=None):
    """Core assignment on a cost matrix. Returns (assign, status) where
    assign[r] is a driver index or None. Raises if the solver fails."""
    from ortools.sat.python import cp_model

    load_km = C.DISPATCH_LOAD_KM if load_km is None else load_km
    unassigned_km = (C.UNASSIGNED_PENALTY_KM if unassigned_km is None
                     else unassigned_km)
    nd, nr = len(cost), len(cost[0]) if cost else 0
    if not nr:
        return [], "optimal"
    S = 100                                    # km -> integer (10 m)
    m = cp_model.CpModel()
    x = {(d, r): m.NewBoolVar(f"x{d}_{r}") for d in range(nd)
         for r in range(nr) if cost[d][r] is not None}
    terms = []
    for r in range(nr):
        pick = [x[d, r] for d in range(nd) if (d, r) in x]
        m.Add(sum(pick) <= 1)
        skipped = m.NewBoolVar(f"skip{r}")
        m.Add(sum(pick) + skipped == 1)
        terms.append(round(unassigned_km * S) * skipped)
    for (d, r), v in x.items():
        terms.append(round(cost[d][r] * S) * v)
    for d in range(nd):                        # convex: each extra run costs more
        mine = [x[d, r] for r in range(nr) if (d, r) in x]
        if not mine:
            continue
        n = m.NewIntVar(0, len(mine), f"n{d}")
        m.Add(n == sum(mine))
        # load cost = load_km * (L*(L-1)/2) with L = held + n; the part
        # already paid for by the held runs is a constant and is dropped.
        L = m.NewIntVar(held[d], held[d] + len(mine), f"L{d}")
        m.Add(L == n + held[d])
        sq = m.NewIntVar(0, (held[d] + len(mine)) ** 2, f"sq{d}")
        m.AddMultiplicationEquality(sq, [L, L])
        # L*(L-1)/2 = (L^2 - L)/2 ; scale by 2 to stay integral
        terms.append(round(load_km * S / 2) * (sq - L))
    m.Minimize(sum(terms))
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = (C.SOLVER_TIME_LIMIT_S
                                        if time_limit is None else time_limit)
    s.parameters.num_workers = 4
    st = s.Solve(m)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"solver status {s.StatusName(st)}")
    out = []
    for r in range(nr):
        out.append(next((d for d in range(nd)
                         if (d, r) in x and s.Value(x[d, r])), None))
    return out, ("optimal" if st == cp_model.OPTIMAL else "feasible")


def greedy_costs(cost, held, load_km=None):
    """The old rule on a cost matrix: runs in order, each to the cheapest
    driver counting load_km per run already held."""
    load_km = C.DISPATCH_LOAD_KM if load_km is None else load_km
    held = list(held)
    out = []
    for r in range(len(cost[0]) if cost else 0):
        best = None
        for d in range(len(cost)):
            if cost[d][r] is None:
                continue
            score = cost[d][r] + load_km * held[d]
            if best is None or score < best[0]:
                best = (score, d)
        if best:
            held[best[1]] += 1
        out.append(best[1] if best else None)
    return out


def _reason(d, r, cost, runs, drivers, assign, held):
    drv, run = drivers[d], runs[r]
    elig = [i for i in range(len(drivers)) if cost[i][r] is not None]
    nearest = min(elig, key=lambda i: cost[i][r])
    others = held[d] + sum(1 for q, a in enumerate(assign)
                           if a == d and q != r)
    lead = ("closest eligible driver" if nearest == d
            else "chosen so the whole batch needs less driving")
    return (f"{lead}, {cost[d][r]:.1f} km trip, capacity ok "
            f"({drv.cap:g} >= {run.kg:g} kg), holds {others} other "
            f"run{'' if others == 1 else 's'}")


def _result(runs, drivers, cost, assign, status, held, secs):
    res = Result({}, {}, {}, 0.0, status, secs)
    for r, run in enumerate(runs):
        d = assign[r]
        res.assign[run.id] = drivers[d].id if d is not None else None
        if d is None:
            res.why[run.id] = "no eligible driver (capacity or declined)"
            continue
        res.km[run.id] = cost[d][r]
        res.total_km += cost[d][r]
        res.why[run.id] = _reason(d, r, cost, runs, drivers, assign, held)
    return res


def solve(runs, drivers, travel, time_limit=None):
    """Assign every run in one go. Raises if the solver cannot answer."""
    t0 = time.time()
    cost = cost_matrix(runs, drivers, travel)
    held = [d.held for d in drivers]
    assign, status = solve_costs(cost, held, time_limit=time_limit)
    return _result(runs, drivers, cost, assign, status, held,
                   time.time() - t0)


def greedy(runs, drivers, travel):
    """What the old nearest-driver rule would do, for comparison."""
    t0 = time.time()
    cost = cost_matrix(runs, drivers, travel)
    held = [d.held for d in drivers]
    assign = greedy_costs(cost, held)
    return _result(runs, drivers, cost, assign, "greedy", held,
                   time.time() - t0)


# ---------- ordering the stops inside one run ----------
def order_stops(points, start, travel, end=None):
    """Visit every point once, leaving `start` and finishing at `end`
    (default `start`). Nearest-neighbour first, then 2-opt until no swap
    shortens the trip. Returns the indexes of `points` in visiting order."""
    end = start if end is None else end
    left, order, cur = set(range(len(points))), [], start
    while left:
        nxt = min(left, key=lambda i: travel.km(cur, points[i]))
        order.append(nxt)
        left.remove(nxt)
        cur = points[nxt]

    def length(o):
        pts = [start] + [points[i] for i in o] + [end]
        return travel.path_km(pts)

    best, improved = length(order), len(order) > 2
    while improved:
        improved = False
        for i in range(len(order) - 1):
            for j in range(i + 1, len(order)):
                cand = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                n = length(cand)
                if n < best - 1e-9:
                    order, best, improved = cand, n, True
    return order
