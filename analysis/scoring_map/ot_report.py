"""Summary of a one-timer run (ot_run.py): python ot_report.py RUN PLAN
For each system: how often the pass reaches the swing and the swing strikes the puck, by press timing; the goal rate
per job (SNES: averaged over the nine aims and with the best aim); how much a job's rate swings from moment to moment
(the standard deviation of the per-moment rates, and so the error of a MOMENTS-moment average); and the seconds a job
took, for sizing chunks."""
import json
import statistics as S
import sys
from collections import defaultdict

from paths import RUNS


def per_moment(row, aim=None):
    """(goals, shots) of one moment for one aim (None: all aims together), or None if no shot was struck."""
    if not row["passed"]:
        return None
    cells = [row["res"][a] for a in row["res"] if aim is None or a == str(aim)]
    g = sum(c.get("GOAL", 0) for c in cells if c["hit"])
    n = sum(sum(c.get(k, 0) for k in ("GOAL", "SAVED", "POST", "MISSED")) for c in cells if c["hit"])
    return (g, n) if n else None


def main():
    run, plan = RUNS / sys.argv[1], sys.argv[2]
    for system in ("genesis", "snes"):
        path = run / f"ot_{system}_{plan}.jsonl"
        if not path.exists():
            continue
        jobs = [json.loads(l) for l in open(path)]
        print(f"\n== {system}: {len(jobs)} jobs, median {S.median(j['seconds'] for j in jobs):.0f} s a job "
              f"(total {sum(j['seconds'] for j in jobs) / 60:.0f} min of work)")
        for timing in ("early", "late"):
            passed = struck = tried = 0
            rates, sds, best = [], [], []
            for j in jobs:
                rows = j["timings"][timing]
                for r in rows:
                    tried += 1
                    if r["passed"]:
                        passed += 1
                        struck += any(c["hit"] for c in r["res"].values())
                ms = [per_moment(r) for r in rows]
                ms = [g / n for g, n in (m for m in ms if m)]
                if len(ms) >= 4:
                    rates.append(S.mean(ms))
                    sds.append(S.pstdev(ms))
                if system == "snes":
                    by_aim = defaultdict(lambda: [0, 0])
                    for r in rows:
                        for a in range(9):
                            m = per_moment(r, a)
                            if m:
                                by_aim[a][0] += m[0]
                                by_aim[a][1] += m[1]
                    if by_aim:
                        best.append(max(g / n for g, n in by_aim.values() if n))
            print(f"  {timing}: pass reached the press {passed}/{tried}, a strike in {struck}/{passed}; "
                  f"goal rate per job: median {100 * S.median(rates):.1f}%, max {100 * max(rates):.1f}%"
                  + (f"; best aim per job: median {100 * S.median(best):.1f}%, max {100 * max(best):.1f}%"
                     if best else ""))
            print(f"      moment-to-moment sd of a job's rate: median {S.median(sds):.2f}, max {max(sds):.2f} "
                  f"(error of a 32-moment average about {S.median(sds) / 32 ** 0.5 * 100:.1f} points)")
        top = sorted(jobs, key=lambda j: -S.mean([g / n for g, n in (per_moment(r) or (0, 1) for r in
                                                  j["timings"]["early"])]))[:6]
        for j in top:
            m = [per_moment(r) for r in j["timings"]["early"]]
            m = [g / n for g, n in (x for x in m if x)]
            print(f"   top (early): receiver {j['R']} passer {j['P']}: {100 * S.mean(m) if m else 0:.0f}%")


if __name__ == "__main__":
    main()
