"""Missing a great chance: how and why (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 5: "Roenick will miss an open net
from 2 feet").

The recorded games (both systems): every attempt worth 0.5 expected goals or more (the game's own shot and save rules
played out say it goes in at least half the time) that didn't score, sorted by what happened: the goalie got to it
(save), a post, a skater blocked it, or it missed the net; a miss is placed by where the recording shows the puck
crossing the net's front (261 from centre; over the crossbar at height 13, or wide of the posts: Genesis 21, SNES 22)
or not reaching it. With the shot's kind (a one-timer is aimed by the game on the Genesis), who shot (a person or the
computer), the goalie's distance off the shot line and the range. Also: how many such chances scored against how many
their expected goals said.

python analysis/open_net_misses.py [--list]   (--list: every miss with its game and clock, for picking ones to show)"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
FRONT, BAR = 261, 13
POST = {"genesis": 21, "snes": 22}


def crossing(m, f, sysn):
    """Where the puck crossed the net's front after the shot at sample f (within 1.5 s), or None."""
    t, pk = m["t"], m["puck"]
    y0 = pk[3 * f + 1]
    side = 1 if y0 > 0 else -1
    if abs(y0) > FRONT:
        return None
    for q in range(f + 1, len(t)):
        if t[q] - t[f] > 1500:
            return None
        x, y, z = pk[3 * q], pk[3 * q + 1], max(0.0, pk[3 * q + 2])
        if (y - side * FRONT) * side >= 0:
            px, py, pz = pk[3 * (q - 1)], pk[3 * (q - 1) + 1], max(0.0, pk[3 * (q - 1) + 2])
            k = (side * FRONT - py) / (y - py) if y != py else 0
            cx, cz = px + k * (x - px), pz + k * (z - pz)
            if cz > BAR and abs(cx) <= POST[sysn]:
                return "over the crossbar"
            return "wide of the post" if abs(cx) > POST[sysn] else "in the frame (deflected?)"
    return None


def main():
    show = "--list" in sys.argv
    out = defaultdict(Counter)
    scored = defaultdict(lambda: [0, 0.0, 0])
    listing = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        sysn = m.get("system", "genesis")
        for s in m.get("shotList", []):
            if s.get("team") not in (0, 1) or s.get("xg") is None or s["xg"] < 0.5:
                continue
            sc = scored[sysn]
            sc[0] += s["result"] == "goal"
            sc[1] += s["xg"]
            sc[2] += 1
            if s["result"] == "goal":
                continue
            if s["result"] == "wide":
                how = crossing(m, s["f"], sysn) or "never reached the net"
            else:
                how = {"save": "the goalie got to it", "post": "a post", "blocked": "a skater blocked it"}.get(s["result"], s["result"])
            o = out[sysn]
            o[how] += 1
            o[f"kind: {s['kind']}"] += 1
            o["shooter: person" if s.get("human") else "shooter: computer"] += 1
            if s.get("gOff") is not None:
                o["goalie 5+ ft off the line" if s["gOff"] >= 15 else "goalie within 5 ft of the line"] += 1
            ny = 264 if s["y"] > 0 else -264
            d = math.hypot(s["x"], ny - s["y"])
            o["within 20 ft (60)" if d < 60 else "farther out"] += 1
            clock = m["clock"][s["f"]]
            listing.append((sysn, p.stem, f"P{m['period'][s['f']] + 1} {clock // 60}:{clock % 60:02d}", s["kind"],
                            "person" if s.get("human") else "computer", round(s["xg"], 2), how, round(d)))
    for sysn in sorted(out):
        g, x, n = scored[sysn]
        print(f"{sysn.upper()}: {n} chances worth 0.5+ xG; {g} scored, {x:.1f} expected; {n - g} didn't")
        for k, v in out[sysn].most_common():
            print(f"   {v:4d}  {k}")
    if show:
        for row in sorted(listing):
            print(*row)


if __name__ == "__main__":
    main()
