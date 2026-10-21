"""BOS-NYI 2026-10-21, deeper (the user: why NYI won three times). (A) every one-timer: the pass that set it up, the
goalie at the strike, the result; (B) every goal: where the scoring team's attackers and the defending team's skaters
were at the shot, what the defending person's skater was doing in the 2 s before, and the zone entry it came from.
python analysis/bos_nyi_deep.py"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
GAMES = [("D", "2026-10-21_1054_BOS-NYI", "BOS won"), ("D", "2026-10-21_1121_BOS-NYI", "BOS won"),
         ("P", "2026-10-21_1137_NYI-BOS", "NYI won"), ("P", "2026-10-21_1147_NYI-BOS", "NYI won"),
         ("P", "2026-10-21_1156_BOS-NYI", "NYI won")]
BASE = {"D": Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches")), "P": Path("matches")}
CHECKS = {"0c5e": "burst", "0b96": "check", "0bc8": "check", "0bfa": "check", "0c2c": "check", "1ac2": "check",
          "0b24": "poke", "1122": "hook", "1154": "hook", "0dd8": "down", "0d26": "down", "11e6": "stumble"}


def load(w, n):
    m = json.loads(load_js_object(BASE[w] / f"{n}.js"))
    s = json.load(open(BASE[w] / f"{n}.summary.json"))
    return m, s["abbr"]


def pos(m, f, k):
    return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]


def anim(m, f, k):
    return m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]


def goalie(m, f, team):
    for k in range(team * 6, team * 6 + 6):
        if m["role"][f * K + k] == "0":
            return k
    return None


def ctrl_rec(m, f, team):
    c = m["ctrl"][f]
    for k in range(team * 6, team * 6 + 6):
        if c >> k & 1:
            return k
    return None


def off_line(px, py, gx, gy, net_y):
    dx, dy = -px, net_y - py
    n = math.hypot(dx, dy) or 1
    return abs((gx - px) * dy - (gy - py) * dx) / n


def frame_at(m, ms):
    t = m["t"]
    lo, hi = 0, len(t) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if t[mid] < ms:
            lo = mid + 1
        else:
            hi = mid
    return lo


ot_rows = []
for w, name, outcome in GAMES:
    m, ab = load(w, name)
    t = m["t"]
    print(f"\n######## {name} ({outcome}): {ab[0]} home, {ab[1]} away")
    passes = m.get("passes", [])
    for sh in m.get("shotList", []):
        if sh["kind"] != "one-timer":
            continue
        team, f = sh["team"], sh["f"]
        end = own_end(m, f, 1 - team)            # the defending goalie's end
        net_y = 268 * (end or 1)
        p = max((p for p in passes if p["team"] == team and p["f"] < f and t[f] - t[p["f"]] < 2500), key=lambda p: p["f"], default=None)
        gk = goalie(m, f, 1 - team)
        g_now = pos(m, f, gk) if gk is not None else None
        g_then = pos(m, p["f"], gk) if (gk is not None and p) else None
        row = {"game": name, "outcome": outcome, "team": ab[team], "result": sh["result"],
               "dist": math.hypot(sh["x"], net_y - sh["y"]),
               "across": abs(p["x1"] - p["x0"]) if p else None,
               "crossed": (p["x0"] * sh["x"] < 0) if p else None,
               "air": (t[f] - t[p["f"]]) / 1000 if p else None,
               "slide": abs(g_now[0] - g_then[0]) if (g_now and g_then) else None,
               "off": off_line(sh["x"], sh["y"], *g_now, net_y) if g_now else None,
               "gctl": sh.get("gctl")}
        ot_rows.append(row)
    # (B) goals
    for g in m["goals"]:
        team, f = g["team"], g["f"]
        sh = min((s for s in m.get("shotList", []) if s["team"] == team and s["result"] == "goal" and abs(s["f"] - f) < 200),
                 key=lambda s: abs(s["f"] - f), default=None)
        if not sh:
            continue
        fs = sh["f"]
        end = own_end(m, fs, 1 - team)
        net_y = 268 * (end or 1)
        px, py = sh["x"], sh["y"]
        # skaters goal-side of the shooter (between his y and the net) and within 60 across
        def between(k):
            x, y = pos(m, fs, k)
            return (abs(y - net_y) < abs(py - net_y)) and abs(x - px) < 70
        dteam = 1 - team
        back = [k for k in range(dteam * 6, dteam * 6 + 6) if m["role"][fs * K + k] not in ("0", "x", "-") and between(k)]
        att = [k for k in range(team * 6, team * 6 + 6) if m["role"][fs * K + k] not in ("0", "x", "-") and abs(pos(m, fs, k)[1] - net_y) < 180]
        dk = ctrl_rec(m, fs, dteam)
        doing = []
        if dk is not None:
            for q in range(frame_at(m, t[fs] - 2500), fs + 1):
                a = CHECKS.get(anim(m, q, dk))
                if a and (not doing or doing[-1] != a):
                    doing.append(a)
            dx, dy = pos(m, fs, dk)
            dperson = f"defending person's skater {math.hypot(dx - px, dy - py):.0f} from the shooter, {'goal side' if abs(dy - net_y) < abs(py - net_y) else 'BEHIND the play'}, did {doing or 'nothing physical'} in the 2.5 s before"
        else:
            dperson = "defending person controlled the goalie"
        ent = max((e for e in m.get("zoneEntries", []) if e["team"] == team and e["f"] <= fs and t[fs] - t[e["f"]] < 8000), key=lambda e: e["f"], default=None)
        etxt = f"entry {ent['kind']} {(t[fs] - t[ent['f']]) / 1000:.1f}s before, odd {ent.get('odd')}" if ent else "no entry within 8 s"
        print(f"  GOAL {ab[team]} P{g['period'] + 1} {g['clock'] // 60}:{g['clock'] % 60:02d} {sh['kind']}: {len(att)} attackers deep vs {len(back)} defenders goal-side; {etxt}; {dperson}; goalie {sh.get('gctl')}")

print("\n######## One-timers (A)")
for team in ("BOS", "NYI"):
    for outcome in ("BOS won", "NYI won"):
        sel = [r for r in ot_rows if r["team"] == team and r["outcome"] == outcome]
        if not sel:
            continue
        goals = [r for r in sel if r["result"] == "goal"]
        avg = lambda key, rs: sum(r[key] for r in rs if r[key] is not None) / max(1, sum(r[key] is not None for r in rs))
        print(f"{team} in games {outcome}: {len(goals)}/{len(sel)} scored; struck {avg('dist', sel):.0f} out on average; pass moved puck "
              f"{avg('across', sel):.0f} across, crossed middle {sum(1 for r in sel if r['crossed'])}/{len(sel)}, air {avg('air', sel):.2f}s; "
              f"goalie {avg('off', sel):.1f} off the line at the strike (goals {avg('off', goals):.1f}), slid {avg('slide', sel):.0f}; "
              f"goalie human {sum(r['gctl'] == 'human' for r in sel)}/{len(sel)}")
    for r in [r for r in ot_rows if r["team"] == team and r["outcome"] == "NYI won"]:
        print(f"    {r['game'][11:]} {r['result']:7} {r['dist']:5.0f} out, across {r['across'] or 0:4.0f}, crossed {r['crossed']}, air {r['air'] or 0:.2f}, goalie off {r['off'] or 0:4.1f}, slid {r['slide'] or 0:4.0f}, {r['gctl']}")
