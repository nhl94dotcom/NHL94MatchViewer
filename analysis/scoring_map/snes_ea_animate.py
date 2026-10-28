"""Animated SNES EA Specials (retail ROM): python snes_ea_animate.py OUT_DIR [N] [names]
Each case in CASES is one set-up of snes_ea_run.py (the walk-in's best cells), played the way that run plays it:
skating in along the set line, the wrist shot released at the spot with the aim held, then snes_ea_run's own bot
(play(): skate on, chase the loose puck once the goalie has touched it, tap A at the near post on claiming it). N
plays (moments, each with its own release seed), the game's own frames from the skate-in to the end of the play. Two
GIFs per case, drawn by ea_animate's layouts:
- <name>_clips.gif: four plays side by side, the whole screen, each labelled with how it ended;
- <name>_paths.gif: every play at once from above, lined up on the release: the shooter (grey), the puck (orange for
  a goal, slate otherwise) and the goalie (black).
The captions' rates are the filmed plays' own. Gentle mode (lowload.py)."""
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from ea_animate import clips_gif, paths_gif, tally
from lowload import WORKERS, breathe

# name, net, x (attacker's view, + his right), out, aim, Shot Power (working 0-15), wind-up frames (3: a wrist shot),
# title, None (the rate: the filmed plays'), move (as snes_ea_run: "rgoal" / "rdiag" + speed), the caption's two
# lines, the goalie's working ratings (None: the test goalie)
ROY = (15, 10, 10, 15)
# the walk-in (2026-10-28, SCORING_SNES): a right-hander from his left, released 17 ft out, 27 ft to the side, skating
# at the goal, a low wrist shot he catches up with, carries on at the goal mouth and shoots at the near post from close
# in (snes_ea_run.play walkin); the cells that scored most in the measurement, top and bottom net, test goalie and Roy;
# and the left-hander's best (bottom net, from his right), whose goals are mostly carried straight in
TOP = ("Right-handed, released 17 ft out, 27 ft to his left, at 1.9,", "skating at the goal, Down-Right held, Shot Power 11.")
BOTTOM = ("Right-handed, released 17 ft out, 27 ft to his left, at 1.9,", "skating at the goal, Down-Left held, Shot Power 8.")
LEFTY = ("Left-handed, released 17 ft out, 27 ft to his right, at 1.9,", "skating at the goal, Down-Right held, Shot Power 8.")
WALK = "SNES walk-in"   # (the title has room for about 60 characters)
CASES = [
    ("sea_walkin_top", "top", -80, 52, 3, 11, 3, WALK + ", top net", None, "rgoal1.9", TOP, None, True),
    ("sea_walkin_top_roy", "top", -80, 52, 3, 11, 3, WALK + ", top net, against Roy", None, "rgoal1.9", TOP, ROY, True),
    ("sea_walkin_bottom", "bottom", -80, 52, 5, 8, 3, WALK + ", bottom net", None, "rgoal1.9", BOTTOM, None, True),
    ("sea_walkin_bottom_roy", "bottom", -80, 52, 5, 8, 3, WALK + ", bottom net, against Roy", None, "rgoal1.9", BOTTOM,
     ROY, True),
    ("sea_walkin_bottom_lefty", "bottom", 80, 52, 3, 8, 3, WALK + ", bottom net", None, "rgoal1.9", LEFTY, None, True),
    ("sea_walkin_bottom_lefty_roy", "bottom", 80, 52, 3, 8, 3, WALK + ", bottom net, against Roy", None, "rgoal1.9",
     LEFTY, ROY, True),
]
LEGEND = "Puck: orange when the play ends in a goal. Grey: shooter. Black: goalie."


def play(case, n):
    """n plays: [(label, goal?, [frames], [(shooter, puck, goalie, False)], release index)]."""
    if len(case) > 11 and case[11]:
        os.environ["NHL94_SNES_GOALIE"] = ",".join(map(str, case[11]))
    import snes_ea_run as A
    import snes_harness as H
    from goal_frames import grab
    A._init()
    name, net, x, out, aim, shp, hold = case[:7]
    move = case[9]
    h = A._h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    s = H.o(H.SHOOTER)
    rnd = random.Random(zlib.crc32(name.encode()))
    run, film = e.run, []

    def filmed(k, hold=None):                         # every frame the play runs, kept while filming
        if film:
            e.want_frame = True
        run(k, hold=hold) if hold is not None else run(k)
        e.want_frame = False
        if film:
            film[0].append(grab(e).copy())
            film[1].append(tuple((sg * h.sw(H.XPOS + H.o(k)), sg * h.sw(H.YPOS + H.o(k)) + 4)
                                 for k in (H.SHOOTER, H.PUCK, H.GOALIE)) + (False,))
    e.run = filmed
    kind = move.rstrip("0123456789.").lstrip("r")
    v = float(move[len(move.rstrip("0123456789.")):])
    sx_ = 1 if x > 0 else -1
    dx, dy = dict(goal=(-sg * x, sg * out), diag=(-sg * sx_, sg))[kind]
    norm = math.hypot(dx, dy)
    dx, dy = dx / norm, dy / norm
    back = A.LEAD[hold] + hold
    skate = H.DIRPAD[A.toward(dx, dy)]
    plays, p = [], 0
    while len(plays) < n and p < 3 * n:
        x0, y0 = sg * x - back * dx * v, sg * (A.GOAL_Y - out) - back * dy * v
        h.setup(round(x0), round(y0), settle=80 + (p * 7) % 15, clock=590 - p % 8, seed=rnd.getrandbits(32))
        p += 1
        w = e.w(A.ATTR + s)
        e.setw(A.ATTR + s, (w | 0x800) if x < 0 else (w & ~0x800))     # a right-hander from his left
        e.setw(H.SHOTSPD + s, shp)
        e.setw(A.FACING + s, A.toward(dx, dy))
        e.setw(H.XVEL + s, round(dx * v * 4096) & 0xFFFF)
        e.setw(H.YVEL + s, round(dy * v * 4096) & 0xFFFF)
        film[:] = [[], []]
        pre = None
        for f in range(back + 40):                     # skating, then A held `hold` frames with the aim (as the run)
            st = e.serialize()
            h.park()
            k = f - A.LEAD[hold]
            e.run(1, hold=skate if k < 0 else (["A"] if k < hold else []) + H.DIRPAD[aim])
            if e.w(H.PUCKC) & 0x8000:
                pre = st
                break
            if e.w(H.PUCKC) != s:
                break
        if pre is None:
            film.clear()
            continue
        film[0].pop()                                  # the release frame: played again by fire() with its seed
        film[1].pop()
        rel = len(film[0])
        h.fire(pre, aim, rnd.getrandbits(32))
        r, info = A.play(h, sg, walkin=len(case) > 12 and case[12])
        for _ in range(12):
            h.park()
            e.run(1)
        frames, pts = film[0], film[1]
        film.clear()
        goal = r == "goal" or info["follow"] in ("goal", "in_off_goalie")
        label = {"goal": "GOAL straight in", "held": "HELD", "miss": "MISSED", "retaken": "took his own shot back"}.get(r)
        if r == "goal" and info.get("retaken") is not None:
            label = "GOAL: carried in"
        if label is None and info.get("retaken") is not None:     # the walk-in
            label = {"goal": "GOAL: walked in", "in_off_goalie": "GOAL: walked in, off the goalie",
                     "held": "walked in, held"}.get(info["follow"], "walked in, no goal")
        if label is None:
            label = {"goal": "GOAL on the rebound", "in_off_goalie": "GOAL, in off the goalie",
                     "held": "bobbled, held after"}.get(info["follow"], "bobbled, no goal")
        plays.append((label, goal, frames, pts, rel))
        breathe()
    return case, plays


def job(a):
    case, n, out_dir = a
    t0 = time.time()
    case, plays = play(case, n)
    case = case[:8] + ((sum(q[1] for q in plays), len(plays)),) + case[9:]
    clips_gif(case, plays, out_dir / f"{case[0]}_clips.gif")
    paths_gif(case, plays, out_dir / f"{case[0]}_paths.gif", LEGEND)
    kinds = {}
    for q in plays:
        kinds[q[0]] = kinds.get(q[0], 0) + 1
    return case[0], tally(plays), kinds, round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    names = sys.argv[3:]
    cases = [c for c in CASES if not names or c[0] in names]
    out_dir.mkdir(parents=True, exist_ok=True)
    done = []
    with Pool(min(WORKERS, len(cases)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(c, n, out_dir) for c in cases]):
            print(*r, flush=True)
            done.append(dict(name=r[0], tally=r[1], kinds=r[2]))
    json.dump(done, open(out_dir / "cases.json", "w"), indent=1)


if __name__ == "__main__":
    main()
