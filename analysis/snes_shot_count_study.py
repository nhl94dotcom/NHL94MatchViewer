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
import math
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from injury_risk_estimate import HOME, Capture  # noqa: E402

SFLAGS, SF2SHOT, GMCLOCK, PUCKC, POSITION, TMSHOTS = 0x15D8, 0x1000, 0x15D6, 0x0AD9, 0x0F43, 0x177A
PUCKX, PUCKY, SHOTPLAYER, LTPLAYER, PFTEAM = 0x0D71, 0x0DD3, 0x0D29, 0x30F6, 0x1503
PUCKVX, PUCKVY = 0x0EDF, 0x0EFF      # Xvel $0EC3 / Yvel $0EE3 + the puck (object 14 x 2)


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
                if up:
                    why = "counted"
                elif cap.w(k, GMCLOCK):
                    why = "clock stopped"
                else:
                    # a2touchpuck writes the toucher (object number) to ltplayer on every touch; no new toucher
                    # around the flag's end: a wall or post (wallcoll; the net's posts through checkgoalp)
                    lt = lambda i: cap.w(i, LTPLAYER)
                    toucher = next((lt(i) for i in range(k, max(j, k - 3), -1) if lt(i) != lt(i - 1)), None)
                    shooter = cap.w(k, SHOTPLAYER) // 2
                    if toucher is None or toucher > 11:
                        why = "a wall or post"
                    elif cap.w(k, POSITION + 2 * toucher) == 0:
                        v = max(math.hypot(signed(cap.w(i, PUCKVX)), signed(cap.w(i, PUCKVY)))
                                for i in range(max(0, k - 3), k + 1))
                        why = "the goalie's stick, " + ("over 13,000" if v > 13000 else "13,000 or under")
                    elif toucher == shooter:
                        why = "the shooter again"
                    elif cap.w(k, PFTEAM + 2 * toucher) == cap.w(k, PFTEAM + 2 * shooter):
                        why = "a teammate's stick or body"
                    else:
                        why = "a defender's stick or body"
        end = min(cap.n - 1, i0 + 120)
        pc = signed(cap.w(end, PUCKC))
        held = 0 <= pc < 24 and cap.w(end, POSITION + pc) == 0
        out.append({"kind": s["kind"], "save": s.get("save"), "counted": s.get("counted"), "why": why, "held": held,
                    "type": s.get("type"), "ms": cap.ms[i0] - cap.ms[0]})
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
    c = Counter((r["kind"] if r["kind"] == "one-timer" else r["type"], r["counted"], r["why"]) for r in rows)
    for k, v in sorted(c.items(), key=str):
        print(k, v)



if __name__ == "__main__":
    main()
