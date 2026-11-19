"""Shots by end and team, and where they cross the goal line (2026-11-18, NOSE4Web: the commissioner's box scores show
more goals at the Down goal; doshot halves the scatter along the ice when the aim's dy < 0). Every recorded game in
the real games' folder, both systems, regulation only. Home attacks up in periods 1 and 3, down in period 2.

Each attempt (shotList: shot, one-timer, pass shot): its end (Up: at the top net), team, whether the game counted it
on goal, goal; the puck's path from the release (the match file's samples) until it is hidden, someone has it, or 90
samples: where it first crosses the goal line it was shot at (Y +/-264; x interpolated between samples), and the
sample count to it (the time, about 60 a second). Speed is the shot list's (the puck's speed the sample after the
release, mph by the viewer's scale: 23,000 = 78 mph).

python analysis/direction_crossing.py"""
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
GOAL_LINE = 264


def crossing(m, f, up):
    P, own, N = m["puck"], m["owner"], len(m["t"])
    gy = GOAL_LINE if up else -GOAL_LINE
    for q in range(f + 1, min(N, f + 90)):
        if P[3 * q + 2] < -100 or own[q] >= 0:
            return None
        y0, y1 = P[3 * (q - 1) + 1], P[3 * q + 1]
        if (y0 - gy) * (y1 - gy) <= 0 and y0 != y1:
            x0, x1 = P[3 * (q - 1)], P[3 * q]
            return x0 + (x1 - x0) * (gy - y0) / (y1 - y0), q - f
    return None


def main():
    for system in ("genesis", "snes"):
        cells = defaultdict(list)
        games = 0
        for p in sorted(HOME.glob("*.js")):
            if p.name == "season.js":
                continue
            try:
                m = season.load_match(p)
            except Exception:
                continue
            if (m.get("system") or "genesis") != system or "bot" in str(m.get("name", "")):
                continue
            games += 1
            for s in m.get("shotList", []):
                per = m["period"][s["f"]]
                if per > 2 or s.get("kind") not in ("shot", "one-timer", "pass shot"):
                    continue
                up = (s["team"] == 0) == (per % 2 == 0)
                c = crossing(m, s["f"], up)
                row = dict(sog=bool(s.get("counted")), goal=s.get("result") == "goal", speed=s.get("speed") or 0,
                           cross=c, x=s["x"], wide=s.get("result") == "wide")
                for key in (("Up" if up else "Down", "Home" if s["team"] == 0 else "Away"), ("Up" if up else "Down", "all")):
                    cells[key].append(row)
        print(f"== {system}: {games} games")
        print("end   team  attempts  on goal  goals  goals/on goal  goals/attempt  crossed the line  |x| median  "
              "within 20 / 40 of the middle  x spread (sd)  samples to the line  speed mph")
        for key in sorted(cells, key=lambda k: (k[0], k[1] != "all", k[1])):
            rows = cells[key]
            cr = [r["cross"] for r in rows if r["cross"]]
            xs = [c[0] for c in cr]
            sog = sum(r["sog"] for r in rows)
            g = sum(r["goal"] for r in rows)
            sp = [r["speed"] * 78 / 23000 for r in rows if r["speed"]]
            print(f"{key[0]:5s} {key[1]:5s} {len(rows):8d} {sog:8d} {g:6d} {g / max(sog, 1):13.1%} {g / max(len(rows), 1):14.1%} "
                  f"{len(cr):9d} ({len(cr) / max(len(rows), 1):.0%})  {st.median([abs(x) for x in xs]) if xs else 0:9.1f}  "
                  f"{sum(abs(x) <= 20 for x in xs) / max(len(xs), 1):12.0%} / {sum(abs(x) <= 40 for x in xs) / max(len(xs), 1):.0%}  "
                  f"{st.pstdev(xs) if len(xs) > 1 else 0:12.1f}  {st.median([c[1] for c in cr]) if cr else 0:10.1f}  "
                  f"{st.mean(sp) if sp else 0:9.1f}")


if __name__ == "__main__":
    main()
