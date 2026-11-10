"""SNES shots the goalie stopped that the game didn't count (2026-11-10, a community member: "a shot doesn't count when
the goalie catches or holds the puck"). The game counts a shot in ChkShotStat (from puckgoalie's save, puckglue when a
goalie takes the puck, Goal, checkgoal) only while the shot flag is set (sflags $15D8 bit $1000, sf2shot: set by
doshot when the shooter has the puck) and the clock runs (gmclock $15D6 = 0); the flag is also cleared by a wall
or post (wallcoll: the puck) and by any player's touch (a2touchpuck).

For each shot in the SNES match files that the goalie saved (shotList result "save"), from its raw recording
(captures/<name>/fast.bin.gz: $0000-$3FFF): whether doshot set the flag (within 0.25 s, real, of the shot), and when it
went: the game's shots (tmshots $177A / $177C) going up then (counted), else the clock stopped (gmclock), or the puck
taken by a skater (puckc $0AD9, position $0F43) or loose (a wall, post or touch); and whether the goalie ended up
holding it (a catch). Counted against the converter's own `counted`.

python snes_shot_count_study.py [NAME ...]   (default: every SNES game with a recording in Documents\\NHL94 Viewer)"""
import bisect
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from injury_risk_estimate import HOME, Capture  # noqa: E402

SFLAGS, SF2SHOT, GMCLOCK, PUCKC, POSITION, TMSHOTS = 0x15D8, 0x1000, 0x15D6, 0x0AD9, 0x0F43, 0x177A
PUCKX, PUCKY, SHOTPLAYER, LASTPLAYER = 0x0D71, 0x0DD3, 0x0D29, 0x0CF3


def signed(v):
    return v - 0x10000 if v >= 0x8000 else v


def study(name):
    t = (HOME / "matches" / f"{name}.js").read_text(encoding="utf-8")
    m = json.loads(t[t.index("{"):t.rindex("}") + 1])
    if m.get("system") != "snes":
        return None
    cap = Capture(HOME / "captures" / name, False)
    at = lambda f: min(cap.n - 1, bisect.bisect_left(cap.ms, m["t"][f]))
    shots = lambda i: cap.w(i, TMSHOTS) + cap.w(i, TMSHOTS + 2)
    out = []
    for s in m.get("shotList", []):
        if s.get("result") != "save" or s.get("kind") not in ("shot", "one-timer"):
            continue
        i0 = at(s["f"])
        flag = lambda i: cap.w(i, SFLAGS) & SF2SHOT
        j = next((i for i in range(max(0, i0 - 3), min(cap.n, i0 + 15)) if flag(i)), None)
        why, held = None, False
        if j is None:
            why = "flag never set"
        else:
            k = next((i for i in range(j, min(cap.n, j + 300)) if not flag(i)), None)
            if k is None:
                why = "flag still set 5 s later"
            else:
                up = shots(min(cap.n - 1, k + 2)) > shots(max(0, k - 2))
                pc = signed(cap.w(k, PUCKC))
                goalie = 0 <= pc < 24 and cap.w(k, POSITION + pc) == 0
                if up:
                    why = "counted"
                elif cap.w(k, GMCLOCK):
                    why = "clock stopped"
                elif 0 <= pc < 24 and not goalie:
                    why = "a skater took it"
                elif goalie:
                    why = "goalie took it, not counted"
                else:
                    x, y = signed(cap.w(k, PUCKX)), signed(cap.w(k, PUCKY))
                    why = "loose: a wall, post or touch"
                    s["_xy"] = (x, y)
                if why not in ("counted", "clock stopped"):
                    lp = signed(cap.w(k, LASTPLAYER))      # puckstick / doshot set it: the goalie's stick?
                    sp = signed(cap.w(k, SHOTPLAYER))
                    by = ("the goalie" if 0 <= lp < 24 and cap.w(k, POSITION + lp) == 0 else
                          "the shooter" if lp == sp else "another skater" if 0 <= lp < 24 else "-")
                    why += f" (last touch: {by})"
        end = min(cap.n - 1, i0 + 120)
        pc = signed(cap.w(end, PUCKC))
        held = 0 <= pc < 24 and cap.w(end, POSITION + pc) == 0
        out.append({"kind": s["kind"], "save": s.get("save"), "counted": s.get("counted"), "why": why, "held": held,
                    "xy": s.get("_xy"), "ms": cap.ms[i0] - cap.ms[0]})
    return out


def main():
    names = sys.argv[1:] or sorted(p.stem for p in (HOME / "matches").glob("*.js") if p.name != "season.js"
                                   and (HOME / "captures" / p.stem / "fast.bin.gz").exists())
    rows = []
    for n in names:
        try:
            r = study(n)
        except (KeyError, FileNotFoundError, ValueError) as err:
            print("skip", n, err)
            continue
        if r:
            rows += [dict(x, game=n) for x in r]
    c = Counter((r["kind"], r["counted"], r["why"], "held" if r["held"] else "-") for r in rows)
    for k, v in sorted(c.items(), key=str):
        print(k, v)
    loose = [r["xy"] for r in rows if r["xy"]]
    if loose:
        print("puck where the flag went (loose):", sorted(loose)[:40])


if __name__ == "__main__":
    main()
