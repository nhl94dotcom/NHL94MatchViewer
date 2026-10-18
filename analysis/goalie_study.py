"""Goalie study (2026-10-18, the user's list): pressing the save button vs being in the way, the goalie's lag on
cross-crease carries, save moves that start before the shot (the Genesis wind-up rule), and long slapshots by aim.
Both systems where the recordings allow. python analysis/goalie_study.py [part]   (parts: button, lag, windup, long)"""
import glob
import importlib
import json
import math
import random
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402
import xg  # noqa: E402

K = 12


def games(system):
    files = {}
    for p in glob.glob("matches/*.js") + glob.glob(r"C:/Users/USER/Documents/NHL94 Viewer/matches/*.js"):
        n = Path(p).name
        if n == "season.js" or "state" in n or "explore" in n or "full_buttons" in n:
            continue
        files.setdefault(n, p)
    for n, p in sorted(files.items()):
        try:
            m = json.loads(load_js_object(Path(p)))
        except Exception:
            continue
        if "shotList" in m and m.get("system", "genesis") == system:
            yield n, m


def role(m, f, k): return m["role"][f * K + k]
def pos(m, f, k): return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]
def anim(m, f, k): return m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]
def puck(m, f): return m["puck"][f * 3], m["puck"][f * 3 + 1]
def clock(m, f): return f"P{m['period'][f] + 1} {m['clock'][f] // 60}:{m['clock'][f] % 60:02d}"


def goalie(m, f, team):
    return next((k for k in range(team * 6, team * 6 + 6) if role(m, f, k) == "0"), None)


def shooter(m, s):
    return next((k for k in range(s["team"] * 6, s["team"] * 6 + 6) if int(m["roster"][s["f"] * K + k], 36) == s["idx"]), None)


def system(name):
    mod = importlib.import_module("systems." + name)
    return {a: v for a, v in mod.SAVE_MOVES.items() if v not in ("dive", "slam")}, mod.ACTIONS["shoot"]


def rate(R):
    g = sum(r == "goal" for r in R)
    return f"{len(R):4} shots, goals {g:3} ({100 * g / max(1, len(R)):3.0f}%)"


def part_button():
    """Shots that reached a goalie a person controlled: did the person press the save button (Genesis C, SNES A: bit $20
    in our pad layout) between 0.6 s before the release and the result? And every goalie's state as the puck got there."""
    for name in ("genesis", "snes"):
        SM, _ = system(name)
        pressed, not_pressed, state = [], [], defaultdict(list)
        for n, m in games(name):
            t = m["t"]
            pads = {m.get("padTeam"): m.get("pad"), m.get("pad2Team"): m.get("pad2")}
            for s in m["shotList"]:
                if s["result"] not in ("goal", "save", "post"):
                    continue
                f0, f1 = s["f"], s.get("resolved", s["f"])
                gk = goalie(m, max(0, f1 - 1), 1 - s["team"])
                if gk is not None:
                    mv = SM.get(anim(m, max(0, f1 - 1), gk), "standing")
                    state[(s.get("gctl"), "in a save move" if mv != "standing" else "standing")].append(s)
                P = pads.get(1 - s["team"])
                if s.get("gctl") != "human" or not P:
                    continue
                c = [q for q in range(max(1, f0 - 60), f1 + 1) if t[f0] - t[q] <= 600 and P[q] & 0x20 and not P[q - 1] & 0x20]
                (pressed if c else not_pressed).append(s)
        print(f"== {name}: a person in net")
        for lab, R in (("save button pressed", pressed), ("not pressed", not_pressed)):
            xs = [s["xg"] for s in R if s.get("xg") is not None]
            held = sum(s.get("after") == "held" for s in R)
            print(f"  {lab:22} {rate([s['result'] for s in R])}  xG a shot {sum(xs) / max(1, len(xs)):.2f}  saves held {held}")
        print("  goalie as the puck arrived:")
        for k in sorted(state, key=str):
            R = state[k]
            saves = [s for s in R if s["result"] != "goal"]
            print(f"   {str(k):34} {rate([s['result'] for s in R])}  saves held {sum(s.get('after') == 'held' for s in saves)}/{len(saves)}")


def part_lag():
    """While an attacker carries the puck within 100 of the goal line and 60 of the middle: how far the goalie trails the
    line from the puck to the middle of the net (at his depth; + = behind the play), by the carrier's speed across."""
    names = ["under 30/s", "30-70/s", "70-110/s", "110+/s"]
    for name in ("genesis", "snes"):
        B = defaultdict(list)
        for n, m in games(name):
            t, own = m["t"], m["owner"]
            for f in range(3, len(t) - 3):
                k = own[f]
                if not 0 <= k <= 11 or own[f - 3] != k or own[f + 3] != k or role(m, f, k) == "0":
                    continue
                team = 0 if k < 6 else 1
                e = own_end(m, f, team)
                gk = goalie(m, f, 1 - team)
                dt = (t[f + 3] - t[f - 3]) / 1000
                if e is None or gk is None or not 0 < dt <= 0.15:
                    continue
                ny = -268 * e
                px, py = puck(m, f)
                D = abs(ny - py)
                if abs(py) > 264 or D > 100 or abs(px) > 60 or D < 1:
                    continue
                vx = (puck(m, f + 3)[0] - puck(m, f - 3)[0]) / dt
                gx, gy = pos(m, f, gk)
                lx = px + (gy - py) * (0 - px) / (ny - py)
                band = "within 30" if D < 30 else ("30-60" if D < 60 else "60-100")
                sp = abs(vx)
                B[(band, 0 if sp < 30 else 1 if sp < 70 else 2 if sp < 110 else 3)].append((lx - gx) * (1 if vx >= 0 else -1))
        print(f"== {name}: the goalie's lag behind the puck-to-net line, median (samples)")
        for band in ("within 30", "30-60", "60-100"):
            print(f"  {band:10}", " | ".join(f"{names[s]} {st.median(B[(band, s)]):5.1f} ({len(B[(band, s)])})" if B[(band, s)] else f"{names[s]} -"
                                             for s in range(4)))


def part_windup():
    """Shots (not one-timers) at a computer goalie: did his save move start before the release? Genesis checkanim starts
    one at once while a shot is wound up (sflags bit 3) with the puck within 60 of the goal line and the goalie within 20
    of the middle, but only while bit 1 of the seconds left is clear; the move is then a pad stack sliding him toward
    the middle, away from the side he stood on."""
    for name in ("genesis", "snes"):
        SM, SHOOT = system(name)
        rows = []
        for n, m in games(name):
            t = m["t"]
            for s in m["shotList"]:
                if s["kind"] != "shot" or s["result"] == "blocked" or s.get("gctl") != "cpu":
                    continue
                f = s["f"]
                k, gk = shooter(m, s), goalie(m, f, 1 - s["team"])
                if k is None or gk is None:
                    continue
                w = f
                while w > 0 and anim(m, w - 1, k) in SHOOT and t[f] - t[w - 1] < 2000:
                    w -= 1
                if anim(m, w, k) not in SHOOT:
                    continue
                sq = next((q for q in range(w, f + 1) if anim(m, q, gk) in SM), None)
                ny = 268 if s["y"] > 0 else -268
                v = 1 if ny > 0 else -1
                goal = next((g for g in m["goals"] if g["team"] == s["team"] and 0 <= g["f"] - f < 90), None)
                rows.append(dict(deep=abs(ny - s["y"]) < 60, early=sq is not None, res=s["result"],
                                 lead=t[f] - t[sq] if sq is not None else None,
                                 clock_on=sq is not None and m["clock"][sq] & 2 == 0,
                                 move=SM.get(anim(m, sq, gk)) if sq is not None else None,
                                 gside=(pos(m, max(0, sq - 1), gk)[0] * v) if sq is not None else None,
                                 gslide=(pos(m, f, gk)[0] - pos(m, max(0, sq - 1), gk)[0]) * v if sq is not None else None,
                                 shot_x=puck(m, f)[0] * v, in_at=(goal or {}).get("net", {}).get("x") if goal else None))
        print(f"== {name}: shots at a computer goalie")
        for lab, sel in (("within 60 of the goal line", True), ("farther out", False)):
            R = [r for r in rows if r["deep"] == sel]
            E = [r for r in R if r["early"]]
            print(f"  {lab}: save move began before the release: {rate([r['res'] for r in E])}"
                  + (f", a median {st.median(r['lead'] for r in E):.0f} ms before" if E else ""))
            print(f"  {'':{len(lab)}}  goalie waited for the shot:          {rate([r['res'] for r in R if not r['early']])}")
        E = [r for r in rows if r["early"]]
        if E:
            print(f"  early save moves: {Counter(r['move'] for r in E).most_common()}; with the clock rule on "
                  f"{sum(r['clock_on'] for r in E)} of {len(E)}")
            pads = [r for r in E if r["move"] == "pad stack" and abs(r["gside"]) > 1]
            if pads:
                print(f"  pad stacks that slid toward the middle (away from his side): {sum(r['gslide'] * r['gside'] < 0 for r in pads)} of {len(pads)}")
            gl = [r for r in E if r["res"] == "goal" and r["in_at"] is not None]
            print(f"  early-save goals in on the shooter's side of the net: {sum((r['in_at'] > 0) == (r['shot_x'] > 0) for r in gl)} of {len(gl)}")


def set_spot(px, py):
    rx, ry = px, min(259, py) - 260
    if rx * rx + ry * ry > 900:
        ln = math.isqrt(int(rx * rx + ry * ry)) + 1
        rx, ry = rx * 26 / ln, ry * 18 / ln
    return rx, ry + 260


def part_long():
    """Long slapshots (Genesis), from the xG model's rules with the computer goalie started where recorded computer
    goalies stood at shots from 90+ (relative to his set spot, turned so + is toward the shooter's side): the chance of
    a goal by aim (just inside the far or near post at mid height, or the middle), shot speed and Shot Accuracy."""
    states = []
    for n, m in games("genesis"):
        for s in m["shotList"]:
            if s["kind"] != "shot" or s["result"] == "blocked" or s.get("gctl") != "cpu":
                continue
            f = s["f"]
            gk = goalie(m, f, 1 - s["team"])
            if gk is None:
                continue
            (gx, gy), (px, py) = pos(m, f, gk), puck(m, f)
            sg = 1 if gy > 0 else -1
            px, py, gx, gy = px * sg, py * sg, gx * sg, gy * sg
            if math.hypot(px, 268 - py) < 90 or abs(px) < 15:
                continue
            sx, sy = set_spot(px, py)
            vx, vy = xg._velocity(m, f, gk)
            side = 1 if px > 0 else -1
            states.append(((gx - sx) * side, gy - sy, vx * sg * side, vy * sg))

    def chance(px, py, aimx, speed, sha, n=4000):
        rng = random.Random(7)
        sx, sy = set_spot(px, py)
        goals = 0
        for _ in range(n):
            dx, dy, vx, vy = states[rng.randrange(len(states))]
            G = xg.Goalie(sx + dx, sy + dy, vx * 4096, vy * 4096, 32, 20, 15, 10)
            goals += xg.play_out((px, py, 0), (aimx, 264, 6), speed / 68, sha, (sha + 1) / (sha + 16), G, 13, 0, rng) == "goal"
        return 100 * goals / n
    print(f"== genesis: long slapshots, % goals (computer goalie as recorded: {len(states)} states)")
    for D, ax in ((120, 25), (120, 60), (160, 25), (160, 60), (200, 25)):
        print(f"  {D} out, {ax} to the side:", " | ".join(
            f"{sp}: far {chance(ax, 264 - D, -16, sp, 27):4.1f} near {chance(ax, 264 - D, 16, sp, 27):4.1f} mid {chance(ax, 264 - D, 0, sp, 27):4.1f}"
            for sp in (16500, 20000, 24000, 28000)))
    for sha in (5, 15, 27):
        print(f"  Shot Accuracy {sha:2}, a 26000 slapshot 25 to the side:",
              " | ".join(f"{D} out: far {chance(25, 264 - D, -16, 26000, sha):4.1f} near {chance(25, 264 - D, 16, 26000, sha):4.1f}" for D in (120, 160, 200)))


if __name__ == "__main__":
    parts = {"button": part_button, "lag": part_lag, "windup": part_windup, "long": part_long}
    for p in sys.argv[1:] or parts:
        parts[p]()
