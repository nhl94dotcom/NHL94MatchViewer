"""Recorded shots played again in the real game (the scoring map's check against the recordings): every Genesis shot a
person aimed (not a one-timer) at a computer goalie, with the recorded puck spot, aim, speed, shooter's working Shot
Accuracy, and the goalie's recorded position and velocity at the release (shots from inside the attacking zone, not
against the boards). The shot's random draws are sampled from
their exact distribution (shotport), with 16 moments of the game clock and the goalie's cycles; the goalie's own
movement from there is the game's.
python replay_recorded.py WORKER WORKERS RUN [n] [spread]  (spread: the goalie's recorded position jittered by a
Gaussian of this many units each launch, for the recordings' own error)  (match files from the repository's matches/; one JSON line per shot
in paths.RUNS / RUN / r<WORKER>.jsonl)"""
import glob
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import xg  # noqa: E402
from share_game import load_js_object  # noqa: E402
from harness import Harness, fire, decide, rec, SHOOTER, GOALIE, PUCKC  # noqa: E402
from mapper import set_ratings  # noqa: E402
from paths import RUNS, STATE_TOP, STATE_BOTTOM  # noqa: E402
from shotport import launch, perfect_chance, scatter_ranges  # noqa: E402

worker, workers = int(sys.argv[1]), int(sys.argv[2])
(RUNS / sys.argv[3]).mkdir(parents=True, exist_ok=True)
out = RUNS / sys.argv[3] / f"r{worker}.jsonl"
N = int(sys.argv[4]) if len(sys.argv) > 4 else 300
SPREAD = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
PHASES = [(590 - c, s) for c in range(8) for s in (80, 87)]


def shots():
    """(match name, shot, inputs) for every shot to replay."""
    for path in sorted(glob.glob(str(ROOT / "matches" / "*.js"))):
        if path.endswith("season.js"):
            continue
        m = json.loads(load_js_object(Path(path)))
        if m.get("system", "genesis") != "genesis" or not m.get("work"):
            continue
        rows = {}
        for r in m["work"]:
            rows.setdefault(r[1], []).append(r)
        P, role, roster = m["pos"], m["role"], m["roster"]
        for sh in m.get("shotList", []):
            if sh["kind"] != "shot" or not sh.get("human") or sh["team"] not in (0, 1) or sh.get("result") == "blocked":
                continue
            d = sh.get("aim", {}).get("d")
            if d is None:
                continue
            f, team = sh["f"], sh["team"]
            gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + k] == "0"), None)
            if gk is None or (m["ctrl"][f] >> gk) & 1:
                continue
            shooter = next((k for k in range(team * 6, team * 6 + 6)
                            if role[f * 12 + k] != "x" and xg.DIGITS.index(roster[f * 12 + k]) == sh["idx"]), None)
            w = xg._work(rows, f, shooter) if shooter is not None else None
            gw = xg._work(rows, f, gk) or [64, 15, 15, 15, 0, 0]     # weight, Agility, Speed, Def. Awareness, ...
            ganim = m["anim"][(f * 12 + gk) * 4:(f * 12 + gk) * 4 + 4]
            gx, gy = P[(f * 12 + gk) * 2], P[(f * 12 + gk) * 2 + 1]
            vgx, vgy = xg._velocity(m, f, gk)
            px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
            if abs(px) > 115 or (py if gy > 0 else -py) < 88:
                continue                # from outside the attacking zone or against the boards: not on the map
            yield m.get("name", Path(path).stem), sh, dict(px=round(px), py=round(py), dir=d, pout=max(1, round(sh["speed"] / 68)),
                                                           sha=w[5] if w else 15, top=gy > 0, gx=gx, gy=gy, gvx=vgx,
                                                           gvy=vgy, gw=gw[:4], ganim=ganim)


def place(h, inp):
    """Set the goalie to the recorded position and velocity (absolute) and give him the recorded goalie's working
    weight, Agility, Speed and Defensive Awareness. (His animation isn't set: a goalie recorded mid-save or in a dive
    is replayed standing; see the ganim field.)"""
    e, g = h.e, rec(GOALIE)
    for off, v in zip((0x67, 0x68, 0x69, 0x6B), inp["gw"]):
        e.setb(g + off, v)
    e.setw(g, round(inp["gx"]))
    e.setw(g + 2, 0)
    e.setw(g + 0x14, round(inp["gy"]))
    e.setw(g + 0x16, 0)
    e.setw(g + 0x28, max(-32768, min(32767, round(inp["gvx"] * 4096))))
    e.setw(g + 0x2A, max(-32768, min(32767, round(inp["gvy"] * 4096))))


def main():
    top_h = Harness(state=STATE_TOP, top=True)
    hs = {True: top_h, False: Harness(state=STATE_BOTTOM, top=False, emu=top_h.e)}
    with open(out, "a") as fo:
        for j, (name, sh, inp) in enumerate(shots()):
            if j % workers != worker:
                continue
            h = hs[inp["top"]]
            rng = random.Random(f"{name}:{sh['f']}")
            pres = []
            h.e.unserialize(h.base)
            set_ratings(h, 20, inp["sha"])
            rated, saved = h.e.serialize(), h.base
            h.base = rated
            # where the shooter must stand for the puck to be at the recorded spot when doshot runs: one trial shot,
            # then twice the correction (the puck's spot at the stick depends a little on where he stands)
            sx, sy = inp["px"], inp["py"]
            for _ in range(2):
                h.setup(sx, sy, settle=80)
                pre, f = h.shoot(8, 3)
                if pre is None:
                    break
                en = h.entry()
                sx, sy = sx + inp["px"] - en["px"], sy + inp["py"] - en["py"]
            for clock, settle in PHASES:
                h.setup(sx, sy, settle=settle, clock=clock)
                pre, f = h.shoot(8, 3)
                if pre is None:
                    continue
                en = h.entry()
                pres.append((pre, dict(inp, px=en["px"], py=en["py"], vz0=0, gspa=int(inp["ganim"], 16))))
            h.base = saved
            if not pres:
                continue
            p = float(perfect_chance(pres[0][1]))
            goals = 0
            for k in range(N):
                pre, i = pres[rng.randrange(len(pres))]
                h.e.unserialize(pre)
                place(h, dict(i, gx=i["gx"] + rng.gauss(0, SPREAD), gy=i["gy"] + rng.gauss(0, SPREAD)) if SPREAD else i)
                tmp = h.e.serialize()
                if rng.random() < p:
                    v = launch(i, True)
                else:
                    adj, yadj, zr, _ = scatter_ranges(i)
                    v = launch(i, False, rng.randrange(-adj, adj) if adj else 0, rng.randrange(-yadj, yadj) if yadj else 0,
                               rng.randrange(zr) if zr else 0)
                fire(h, tmp, v, post_seed=rng.getrandbits(32))
                goals += decide(h)[0]
            fo.write(json.dumps(dict(spread=SPREAD, match=name, f=sh["f"], team=sh["team"], result=sh.get("result"), xg=sh.get("xg"),
                                     game=goals / N, n=N, px=inp["px"], py=inp["py"], aim=inp["dir"], pout=inp["pout"],
                                     sha=inp["sha"], gx=inp["gx"], gy=inp["gy"], gw=inp["gw"], ganim=inp["ganim"], off=round(((pres[0][1]["px"] - inp["px"]) ** 2 + (pres[0][1]["py"] - inp["py"]) ** 2) ** .5, 1))) + "\n")
            fo.flush()


if __name__ == "__main__":
    main()
