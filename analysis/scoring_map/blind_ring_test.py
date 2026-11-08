"""NOSE4Web's blind-ring option, played in the game (Genesis, 2026-11-08, the user approved running the patched ROMs).
The stick's blind ring (GENESIS_SHOOTING 5.5): with the puck loose, a goalie's puck within reach of his stick's hot
spot (14) but more than 8 from it gets no stick (puckstick does nothing for a goalie past 8) and no body test that
frame, so a low puck can pass through his middle. The option sends a goalie's loose puck past $40 (8 squared) to the
body test instead (collide94 .chkbody); everything else calls puckstick as before.

Shots in live play (bot_live states: home on pad 1 shooting at the top net, the computer's goalie): the home centre put
at a spot with the puck for 90 frames (everyone else parked; the goalie sets himself), then a shot (C 3 frames with
the aim held), played out until a goal, the goalie holding it 20 frames, or the puck going away. The same spots, aims
and random seeds on both ROMs, so shots pair up. A goal "through him": the puck's x within 8 of the goalie's when it
crossed his y.
NHL94_BRT_FLAT=1: the frame after the release the puck is sent flat (z and z speed 0) at the goalie's middle (his x
+/- 6, at the goal line) at 9,000-22,000: the low pucks through his middle that the blind ring lets by.

python blind_ring_test.py RUN ROM [seeds]   -> paths.RUNS / RUN / trials.jsonl
python blind_ring_test.py report RUN_A RUN_B"""
import json
import random
import sys
from collections import Counter

from bot import rec, PUCKC, pad
from bot_scenario import live_state, LIVE_STATES
from emu import Emu
from lowload import breathe, gentle
from paths import RUNS

SHOOTER, GOALIE, SCORE_HOME = 2, 11, 0xC6DA
SPOTS = [(x, y) for x in (-70, -35, 0, 35, 70) for y in (140, 175, 210)]
AIMS = [None, 0, 1, 7, 2, 6]


def park(e, keep_shooter=True):
    for k in range(12):
        if k == GOALIE or (k == SHOOTER and keep_shooter):
            continue
        e.setw(rec(k), (-100 + 18 * k) & 0xFFFF)
        e.setw(rec(k) + 0x14, -230 & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)


FLAT = bool(__import__("os").environ.get("NHL94_BRT_FLAT"))   # flat pucks at his middle (below)


def shot(e, base, x, y, aim, seed):
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, seed)
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for _ in range(90):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 2, 0)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x16, 0)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        park(e)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    hold = pad(aim) if aim is not None else []
    for f in range(60):
        park(e)
        e.run(1, hold=(["C"] if f < 3 else []) + hold)
        if e.w(PUCKC) >= 0x8000:
            break
    else:
        return dict(res="no shot")
    if FLAT:                                              # along the ice at the goalie's middle: the frame after the
        rnd = __import__("random").Random(seed)           # release, the puck's speed replaced (the game's own shot has
        gx = e.sw(rec(GOALIE)) + rnd.uniform(-6, 6)       # set the goalie's save going)
        px, py = e.sw(rec(14)), e.sw(rec(14) + 0x14)
        dx, dy = gx - px, 264 - py
        sp = rnd.uniform(9000, 22000) / (dx * dx + dy * dy) ** 0.5
        e.setw(rec(14) + 0x28, round(dx * sp) & 0xFFFF)
        e.setw(rec(14) + 0x2A, round(dy * sp) & 0xFFFF)
        e.setw(rec(14) + 0x2C, 0)
        e.setw(rec(14) + 0x18, 0)
    s0 = e.w(SCORE_HOME)
    held = away = 0
    through, last_dy = None, None
    for f in range(150):
        park(e, keep_shooter=False)
        e.run(1)
        px, py, pz = e.sw(rec(14)), e.sw(rec(14) + 0x14), e.sw(rec(14) + 0x18)
        gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
        dy = py - gy
        if last_dy is not None and last_dy < 0 <= dy and through is None:
            through = dict(dx=px - gx, z=pz)
        last_dy = dy
        if e.w(SCORE_HOME) != s0:
            return dict(res="goal", through=through)
        held = held + 1 if e.w(PUCKC) == GOALIE else 0
        if held >= 20:
            return dict(res="held")
        away = away + 1 if e.sw(rec(14) + 0x2A) < 0 else 0
        if away >= 4 or py > 276:
            return dict(res="no goal")
    return dict(res="no goal")


def main():
    run, rom = sys.argv[1], sys.argv[2]
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    with open(out / "trials.jsonl", "w") as fh:
        for s in range(seeds):
            for i, (x, y) in enumerate(SPOTS):
                for aim in AIMS:
                    r = shot(e, bases[(s + i) % LIVE_STATES], x, y, aim, random.Random(f"{s}-{x}-{y}-{aim}").getrandbits(32))
                    r.update(seed=s, x=x, y=y, aim=aim)
                    fh.write(json.dumps(r) + "\n")
                breathe()
            fh.flush()
    print("done", flush=True)


def report(runs):
    data = {r: [json.loads(l) for l in open(RUNS / r / "trials.jsonl")] for r in runs}
    for r, rows in data.items():
        goals = [x for x in rows if x["res"] == "goal"]
        thr = [x for x in goals if x["through"] and abs(x["through"]["dx"]) <= 8]
        print(f"{r}: {len(rows)} shots, {dict(Counter(x['res'] for x in rows))}; goals through him (x within 8) {len(thr)}")
    if len(runs) == 2:
        a, b = (data[r] for r in runs)
        key = lambda x: (x["seed"], x["x"], x["y"], x["aim"])
        bm = {key(x): x for x in b}
        pairs = Counter((x["res"], bm[key(x)]["res"]) for x in a if key(x) in bm)
        print("pairs (first run, second run):", dict(pairs))
        lost = [x for x in a if x["res"] == "goal" and bm.get(key(x), {}).get("res") != "goal"]
        print("goals only in the first run: through him", sum(1 for x in lost if x["through"] and abs(x["through"]["dx"]) <= 8),
              "of", len(lost))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
