"""EA Specials in the real game (Genesis test ROM), 2026-10-24. The play (the user): from the side (a left-hander
from his right), a skater takes a wrist shot meant to be bobbled, the save pushing the goalie back; he skates on, claims the loose puck
and at once shoots a wrist shot inside the near post, open because the goalie was pushed back (and may have gone into
a dive trying to smother it). The user: the best shooters are bad at it (their harder wrist shots are caught and held
more), middling shooters' shots are saved but bobbled more. So each job is one shooter (working Shot Power and Shot
Accuracy, roster steps 2-6 = 10-30) at one spot; each aim, each of MOMENTS moments, SEEDS seeds after the release.
Standing or skating toward the net (MOVES). Per play: the first result (goal straight in; held; touched and loose = a bobble; missed), the release speed; for a
bobble the loose puck's speed, how far the goalie went back toward his line, a dive, whether and how fast the shooter
claimed it, and the follow-up (goal, held, none). Spots in the attacker's view on his
off-wing (first called his forehand side; a left-hander: his right). Gentle mode, chunked.
Plans: "ea" (the first run: 40 / 70 / 100 to the side, standing or skating straight up the ice); "firm" (2026-10-24:
40 to the side only, Shot Accuracy 2 / 4 / 6, for more moments: NHL94_EA_MOMENTS; one set-up's rate over 8 moments
wandered: ea_animate.py); "dots" (the user, 2026-10-24: more EA Specials come from farther to the side, on or near the
end-zone faceoff dot, 70 to the side and about 60 out, with the skater skating toward the goal as he shoots: move
"goal<speed>" sets his speed toward the middle of the goal line and he keeps skating at the goal after the shot);
"angle" (the user, 2026-10-25: the shooter always faces straight across the rink or diagonally toward the goalie
as he shoots, never straight up the ice, so he is placed to claim the rebound: moves "across<speed>" (straight
across toward the middle), "diag<speed>" (45 degrees toward the middle and the goal line) and "goal<speed>"; Shot
Accuracy 4; for the goalie profiles too, NHL94_GOALIE); "xspot" (the user, 2026-10-25, two marked screenshots: the
release level with the faceoff dot across and a little deeper, about 40-44 out against the dot's 62): x and out are
where the puck is released, not where he starts (a move "r<kind><speed>" starts him LEAD frames of skating back, the
wrist shot leaving the stick 4 frames after C); a negative x is his left side, taken by a right-hander (a
left-hander from his right, a right-hander from his left: the user, 2026-10-25); skating at the goal at 1.5 or 2.5 a
frame or in at 45 degrees; each job also gives the mean release spot ("release": across, out); "depth" (the user,
2026-10-25: the best depth for each net, after "xspot" found the bottom net's 14 ft three times the top net's): the
release 40-88 out (13-29 ft), 22-28 ft to either side, at the goal or at 45 degrees at 2.5, Shot Power 2 / 4 (run with
NHL94_EA_MOMENTS=48: one set-up's rate over 24 moments wandered); "refine" (the user, 2026-10-25, around "depth"'s
best: both nets peaked 64-76 out): the release 60-84 out, 58-80 to the side (top net: his left only, the right-hander,
the better side there), Shot Power 2 / 3 / 4; plus the bottom net's close spot from "xspot" (34-46 out, 70-80 to his
left, Shot Power 2 / 3); its skating speed from NHL94_EA_SPEED (default 2.5; run again at 1.7, the user, 2026-10-26:
in an EA Special a person skates a little below full speed, tapping the d-pad rather than holding it, to be placed for
the rebound); "fine" (finer steps around "refine"'s best at 1.7: 52-64 out at the bottom net, 56-72 at the top);
"lefttop" (the user, 2026-10-26: "refine"'s top-net grid mirrored for the left-hander from his
right, plus the close spot on that side); "slop" (2026-10-26: how forgiving each of the best set-ups is: a person
can't release at the exact spot and frame, so each moment draws its own errors in the release spot, the skating speed
and angle and the release frame, at four levels (ERRORS), only the set-up's best aim; run with NHL94_EA_MOMENTS=120);
"slopfull" (the same at 2.0 a frame: the test skater, working Agility / Speed 18, tops out at 2.0 holding the d-pad, and
the earlier plans' 2.5 is beyond any skater's: 30 / 30 reaches 2.35; started at 2.5 he slows to 2.0 in about 12 frames);
"slopparts" (each kind of error alone, at the small and medium sizes); "goalie" (the goalie's ratings one at a time, NHL94_GOALIE: BEST, the best aim and its neighbours); "skate" (the
shooter's working Agility / Speed, NHL94_EA_SKATE: BEST at his own full speed and 0.3 below, released as found or 8
nearer / farther). At 1.7, from "fine"'s best (the bottom net forgiving 21 ft out, 64): "slop17" / "slopparts17" (SLOP17,
as "slop" / "slopparts"); "speed" (the user, 2026-10-26: how far below full speed works: SPEED17 at 1.5-2.0 a frame,
released 56-72 out); "lefttop17" ("lefttop" at 1.7, around the right-hander's best depth); "goalie17" / "skate17" (as
"goalie" / "skate" from BEST17; "skate17" releases 4 nearer / farther); "follow" (BEST17, every aim, run once for
each follow-up aim, NHL94_EA_FOLLOW); "real2v2" (the user's own set-ups from two 2v2 games, 2026-10-27) and "wide"
(first shots from everywhere, 13-37 ft to the side, 12-36 ft out), both at NHL94_EA_SPEED (default 1.6, about 78% of
a 20 / 20 skater's 2.05), run with the 2v2 ROM's ratings (NHL94_EA_SKATE=20,20; Hartford's goalie 20 / 20 / 30 / 20). "goalie17" again with the league ROM's starting goalies (NHL94_GOALIE, the user,
2026-10-27: which goalies the play works on); "shooter17" (BEST17 with Shot Power and Shot Accuracy 1-6: which
shooters are worth sending in).
python ea_run.py RUN [minutes] [plan]   -> paths.RUNS / RUN / ea.jsonl (plan "ea") or ea_<plan>.jsonl"""
import itertools
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool

from harness import Harness, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
from lowload import WORKERS, breathe, gentle
from mapper import set_ratings
from paths import RUNS, STATE_TOP, STATE_BOTTOM

MOMENTS, SEEDS = int(os.environ.get("NHL94_EA_MOMENTS") or 8), 2
GOAL_Y = 264
FIRST, FOLLOW = 60, 90         # frames to the first result; frames more for the follow-up
STEPS = (2, 3, 4, 5, 6)        # roster steps (x 5 = working)
PUCK = 14
KEYS = ("net", "x", "out", "shp", "sha", "move")
LEAD = 4                       # frames from C to the release of a wrist shot (measured 2026-10-25)
MOVES = (0.0, 1.5)             # standing, or skating toward the net at 1.5 a frame as he shoots (down the side)
# plan "slop": each level's largest error (uniform within +-): release spot across and out (units, 3 a foot), skating
# speed (a frame), skating angle (degrees), release frame (frames along his line)
ERRORS = {"exact": (0, 0, 0, 0), "small": (3, 0.2, 5, 1), "medium": (9, 0.5, 10, 2), "large": (15, 1.0, 20, 3)}
# plan "slopparts": one kind of error at a time, at the small and medium sizes
PARTS = {f"{k}_{lv}": tuple(v if i == j else 0 for j, v in enumerate(ERRORS[lv]))
         for i, k in enumerate(("spot", "speed", "angle", "frame")) for lv in ("small", "medium")}
LEVELS = tuple(ERRORS)
ERRORS.update(PARTS)
# the best set-ups of "refine" by the worse of Hrudey and Roy (and the bottom net's close spot), with the best aim
SLOP = [("top", -72, 68, 3, 4, "rdiag2.5", 0), ("top", -80, 76, 4, 4, "rdiag2.5", 0),
        ("top", -80, 68, 4, 4, "rgoal2.5", 3), ("top", -72, 76, 3, 4, "rdiag2.5", 0),
        ("bottom", -80, 76, 3, 4, "rdiag2.5", 5), ("bottom", -80, 76, 4, 4, "rdiag2.5", 5),
        ("bottom", -58, 84, 2, 4, "rdiag2.5", 7), ("bottom", -75, 40, 2, 4, "rgoal2.5", 8),
        ("bottom", -80, 34, 2, 4, "rgoal2.5", 8)]
# plans "goalie" and "skate": each net's best set-up and the bottom net's close spot, with the best aim and its two
# neighbours; the skating speed from NHL94_EA_SPEED (default 2.5, as "refine")
BEST = [("top", -72, 68, 3, 4, "rdiag", (7, 0, 1)), ("bottom", -80, 76, 3, 4, "rdiag", (4, 5, 6)),
        ("bottom", -75, 40, 2, 4, "rgoal", (8,))]
# the same at 1.7 from "fine"'s best (by the worse of Hrudey and Roy): the bottom net 64 out, a right-hander at the
# goal or in at 45 degrees, the left-hander in at 45; the top net's best cell
# (2026-10-27: from "fine" run again with the follow-up's aim fixed, test goalie; until then the follow-up was aimed
# by the skating d-pad, and these were the first shots that went straight in)
SLOP17 = [("top", -84, 68, 3, 4, "rdiag1.7", 2), ("top", -80, 72, 3, 4, "rgoal1.7", 2),
          ("bottom", -88, 52, 3, 4, "rgoal1.7", 6), ("bottom", 88, 52, 3, 4, "rgoal1.7", 2),
          ("bottom", 88, 60, 4, 4, "rdiag1.7", 2), ("bottom", -72, 64, 2, 4, "rgoal1.7", 3)]
BEST17 = [("top", -84, 68, 3, 4, "rdiag", (1, 2, 3)), ("bottom", -88, 52, 3, 4, "rgoal", (5, 6, 7)),
          ("bottom", 88, 52, 3, 4, "rgoal", (1, 2, 3)), ("bottom", -72, 64, 2, 4, "rgoal", (2, 3, 4))]
SPEED17 = BEST17
# the follow-up's aim (the user, 2026-10-26: people aim it at the middle or the far post, the middle better):
# "near" (Right / Left at the side he is on: every run before plan "follow"), "center" (nothing held), "far"
FOLLOW_AIM = os.environ.get("NHL94_EA_FOLLOW") or "near"
# backhand EA Specials (the user, 2026-10-27: much harder, and taken from much closer): the hand swapped, a left-hander
# from his left, a right-hander from his right
BACKHAND = bool(os.environ.get("NHL94_EA_BACKHAND"))
SKATE = os.environ.get("NHL94_EA_SKATE")       # "agl,spd": the shooter's working Agility and Speed (else the state's
TOP_SPEED = {10: 1.75, 13: 1.85, 18: 2.0, 20: 2.05, 30: 2.35}   # 18 / 18); his full speed holding the d-pad, measured


def plan_jobs(plan="ea"):
    if plan == "slop":                 # (net, x, out, shp, sha, move, aims, error level)
        return [s[:6] + ((s[6],), lvl) for s in SLOP for lvl in LEVELS]
    if plan == "slopparts":
        return [s[:6] + ((s[6],), lvl) for s in SLOP for lvl in PARTS]
    if plan == "slopfull":             # the same at the test skater's own full speed: 2.0 a frame (Agility / Speed 18;
        return [s[:5] + (s[5].replace("2.5", "2.0"), (s[6],), lvl) for s in SLOP for lvl in LEVELS]   # 2.5 is beyond
    if plan == "goalie":               # the goalie's ratings one at a time (NHL94_GOALIE), the shooter as he is
        v = os.environ.get("NHL94_EA_SPEED", "2.5")
        return [(n, x, o, p, a, m + v, aims, "exact") for n, x, o, p, a, m, aims in BEST]
    if plan == "skate":                # the shooter's skating (NHL94_EA_SKATE): at his own full speed and 0.3 below,
        top = TOP_SPEED[int(SKATE.split(",")[1])] if SKATE else 2.0     # released as found or 8 nearer / farther
        return [(n, x, o + d, p, a, m + f"{v:.2f}", aims, "exact") for n, x, o, p, a, m, aims in BEST
                for v in (top, top - 0.3) for d in (-8, 0, 8)]
    if plan == "slop17":
        return [s[:6] + ((s[6],), lvl) for s in SLOP17 for lvl in LEVELS]
    if plan == "slopparts17":
        return [s[:6] + ((s[6],), lvl) for s in SLOP17 for lvl in PARTS]
    if plan == "speed":                # the skating speed 1.5-2.0 a frame (the test skater's full speed is 2.0)
        return [(n, x, o + d, p, a, m + v, aims, "exact") for n, x, o, p, a, m, aims in SPEED17
                for v in ("1.5", "1.6", "1.7", "1.8", "1.9", "2.0") for d in (-8, -4, 0, 4, 8)]
    if plan == "goalie17":
        return [(n, x, o, p, a, m + "1.7", aims, "exact") for n, x, o, p, a, m, aims in BEST17]
    if plan == "skate17":              # his own full speed and 0.3 below, released 4 nearer / farther
        top = TOP_SPEED[int(SKATE.split(",")[1])] if SKATE else 2.0
        return [(n, x, o + d, p, a, m + f"{v:.2f}", aims, "exact") for n, x, o, p, a, m, aims in BEST17
                for v in (top, top - 0.3) for d in (-4, 0, 4)]
    if plan == "shooter17":            # the user, 2026-10-27: which shooters are worth sending in: BEST17 with Shot
        return [(n, x, o, p, a, m + "1.7", aims, "exact") for n, x, o, _p, _a, m, aims in BEST17   # Power and Shot
                for p in range(1, 7) for a in range(1, 7)]                                        # Accuracy 1-6
    if plan == "follow":               # BEST17 with every aim, for each NHL94_EA_FOLLOW
        return [(n, x, o, p, a, m + "1.7") for n, x, o, p, a, m, _aims in BEST17]
    if plan == "real2v2":              # the user's own set-ups (two 2v2 games, 2026-10-27: released about 64-80 out,
        v = os.environ.get("NHL94_EA_SPEED", "1.6")     # 50-70 to the side, at about 78% of full speed), both hands
        return list(itertools.product(("top", "bottom"), (-70, -60, -50, 50, 60, 70), (64, 72, 80), (4,), (4,),
                                      ("rgoal" + v, "rdiag" + v)))
    if plan == "wide":                 # everywhere a first shot might be taken from (the user: look for a spot he
        v = os.environ.get("NHL94_EA_SPEED", "1.6")     # hasn't found): 13-37 ft to either side, 12-36 ft out
        return list(itertools.product(("top", "bottom"), (-112, -100, -85, -70, -55, -40, 40, 55, 70, 85, 100, 112),
                                      (36, 48, 60, 72, 84, 96, 108), (4,), (4,), ("rgoal" + v, "rdiag" + v)))
    if plan == "backhand":             # from close in to the faceoff dots, both nets and sides, both hands (run once
        v = os.environ.get("NHL94_EA_SPEED", "1.6")     # as is and once with NHL94_EA_BACKHAND=1). The game swings a
        return list(itertools.product(("top", "bottom"), (-85, -70, -55, -40, -25, 25, 40, 55, 70, 85),  # backhand
                                      (16, 28, 40, 52, 64, 76), (4,), (4,), ("rup" + v, "racross" + v)))
        # by his facing against the direction to the goal (Findhittype), not his hand: skating at the goal or in at 45
        # degrees he always takes a forehand; skating straight up the ice or across, one hand takes a backhand. Each
        # aim's "backhand" counts the shots the game swung as backhands ($092E)
    if plan == "lefttop17":
        return list(itertools.product(("top",), (65, 72, 80, 88), (56, 60, 64, 68, 72), (2, 3, 4), (4,),
                                      ("rgoal1.7", "rdiag1.7")))
    if plan == "lefttop":
        grid = itertools.product(("top",), (58, 65, 72, 80), (60, 68, 76, 84), (2, 3, 4), (4,), ("rgoal2.5", "rdiag2.5"))
        close = itertools.product(("top",), (70, 75, 80), (34, 40, 46), (2, 3), (4,), ("rgoal2.5",))
        return list(grid) + list(close)
    if plan == "firm":
        return list(itertools.product(("top", "bottom"), (40,), (60, 90, 120), STEPS, (2, 4, 6), MOVES))
    if plan == "angle":
        return list(itertools.product(("top", "bottom"), (55, 70, 85), (45, 60, 75), (2, 4, 6), (4,),
                                      ("across2.5", "diag2.5", "goal2.5")))
    if plan == "xspot":
        return list(itertools.product(("top", "bottom"), (-75, -70, -65, 65, 70, 75), (38, 42, 46), (2, 4, 6), (4,),
                                      ("rgoal1.5", "rgoal2.5", "rdiag2.5")))
    if plan == "depth":
        return list(itertools.product(("top", "bottom"), (-85, -75, -65, 65, 75, 85), (40, 52, 64, 76, 88), (2, 4), (4,),
                                      ("rgoal2.5", "rdiag2.5")))
    if plan == "refine":               # at NHL94_EA_SPEED a frame (default 2.5, as first run)
        v = os.environ.get("NHL94_EA_SPEED", "2.5")
        top = itertools.product(("top",), (-80, -72, -65, -58), (60, 68, 76, 84), (2, 3, 4), (4,), ("rgoal" + v, "rdiag" + v))
        bottom = itertools.product(("bottom",), (-80, -72, -65, -58, 58, 65, 72, 80), (60, 68, 76, 84), (2, 3, 4), (4,),
                                   ("rgoal" + v, "rdiag" + v))
        close = itertools.product(("bottom",), (-80, -75, -70), (34, 40, 46), (2, 3), (4,), ("rgoal" + v,))
        return list(top) + list(bottom) + list(close)
    if plan == "fine":                 # around "refine"'s best at NHL94_EA_SPEED (at 1.7 both nets peaked at 60 out, the
        v = os.environ.get("NHL94_EA_SPEED", "1.7")           # bottom net only there: 5-9% at 46 and 68), finer steps
        bottom = itertools.product(("bottom",), (-88, -80, -72, -65, 65, 72, 80, 88), (52, 56, 60, 64), (2, 3, 4), (4,),
                                   ("rgoal" + v, "rdiag" + v))
        top = itertools.product(("top",), (-88, -84, -80, -76), (56, 60, 64, 68, 72), (2, 3), (4,), ("rgoal" + v, "rdiag" + v))
        return list(bottom) + list(top)
    if plan == "dots":
        return list(itertools.product(("top", "bottom"), (55, 70, 85), (45, 60, 75), STEPS, (2, 4, 6),
                                      ("goal1.5", "goal2.5")))
    return list(itertools.product(("top", "bottom"), (40, 70, 100), (60, 90, 120), STEPS, STEPS, MOVES))


_h = {}


def _init():
    gentle()
    top = Harness(state=STATE_TOP, top=True)
    _h["top"], _h["bottom"] = top, Harness(state=STATE_BOTTOM, top=False, emu=top.e)


def toward(dx, dy):
    """The d-pad direction (0 up the screen, clockwise) nearest to (dx, dy) (screen: +y up the screen)."""
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def park_except(h, keep):
    e = h.e
    for k in range(12):
        if k == GOALIE or k in keep:
            continue
        e.setw(rec(k), -100 + 18 * k)
        e.setw(rec(k) + 0x14, h.park_y)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(k) + off, 0)


DIVE = 0x02F4                  # the goalie's dive animation ($02F4)


def play(h, sg, at_goal=False):
    """From the release (the user's play): the shooter skates on toward the net; once the goalie has touched the puck
    and it is loose, he skates at it, and as soon as he has it taps C aimed at the near post (the side of the net he
    is on: a wrist shot at once). Returns the first result ('goal' straight in, 'held', 'bobble', 'miss') and what
    happened after a bobble."""
    e = h.e
    s0 = e.w(SCORE_HOME)
    touched, pv, info = None, None, dict(back=0.0, dive=False, claim=None, shot=False, follow="none")
    g0 = None
    for f in range(FIRST + FOLLOW):
        park_except(h, (SHOOTER,))
        sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
        px, py = e.sw(rec(PUCK)), e.sw(rec(PUCK) + 0x14)
        gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
        if g0 is None:
            g0 = gy
        if e.w(PUCKC) == SHOOTER and touched is not None and not info["shot"]:
            info["claim"], info["shot"] = f - touched, True
            info["claim_x"] = sg * sx                    # where he claims it (attacker's view: + his right)
            near = 2 if sx > 0 else 6                    # the near post: the side of the net he is on (screen)
            aim = dict(near=near, center=8, far=8 - near)[FOLLOW_AIM]
            for c in range(12):                         # C 3 frames, the aim held until the puck leaves (the
                park_except(h, (SHOOTER,))              # d-pad at the release is the aim: before 2026-10-27 it was
                e.run(1, hold=(["C"] if c < 3 else []) + DIRPAD[aim])   # held 3 frames only, and the skating
                if e.w(PUCKC) != SHOOTER:               # d-pad aimed the follow-up)
                    break
            continue
        if touched is None or info["shot"]:
            if at_goal:                                  # on at the middle of the goal line
                pad = DIRPAD[toward(-sx, sg * GOAL_Y - sy)]
            else:
                pad = DIRPAD[0 if sg > 0 else 4]         # on toward the net
        else:
            pad = DIRPAD[toward(px - sx, py - sy)]
        e.run(1, hold=pad)
        if e.w(SCORE_HOME) != s0:
            if touched is None:
                return "goal", info
            info["follow"] = "goal" if info["shot"] else "in_off_goalie"
            return "bobble", info
        if e.w(PUCKC) == GOALIE:
            if touched is None or (not info["shot"] and info["claim"] is None and f - touched < 4):
                return "held", info
            info["follow"] = "held"
            return "bobble", info
        vx, vy = e.sw(rec(PUCK) + 0x28), e.sw(rec(PUCK) + 0x2A)
        if touched is None:
            if pv is not None and math.hypot(px - gx, py - gy) < 24 and                     vx * pv[0] + vy * pv[1] < 0.5 * (pv[0] ** 2 + pv[1] ** 2):
                touched = f                              # turned or slowed hard beside the goalie: a save
                info["v"] = round(math.hypot(vx, vy))
            elif sg * py > GOAL_Y + 12 or f >= FIRST:
                return "miss", info
        else:
            if f - touched <= 20:                        # pushed back: toward his goal line, from where he stood
                info["back"] = max(info["back"], round(sg * (gy - g0), 1))
            if e.w(rec(GOALIE) + 0x58) == DIVE:
                info["dive"] = True
        pv = (vx, vy)
    return ("bobble" if touched is not None else "miss"), info


def job(args):
    net, x, out, shp, sha, move = args[:6]
    aims = args[6] if len(args) > 6 else range(9)
    err = ERRORS[args[7]] if len(args) > 7 else ERRORS["exact"]
    erng = random.Random(zlib.crc32((json.dumps(args) + "err").encode()))
    h = _h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    rnd = random.Random(zlib.crc32(json.dumps(args).encode()))
    res, rel = {}, [0.0, 0.0, 0]
    at_release = isinstance(move, str) and move.startswith("r")
    for p in range(MOMENTS):
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        ex, eo = erng.uniform(-err[0], err[0]), erng.uniform(-err[0], err[0])     # this moment's errors
        ev, ea, ef = erng.uniform(-err[1], err[1]), erng.uniform(-err[2], err[2]), erng.uniform(-err[3], err[3])
        x0, y0 = sg * (x + ex), sg * (GOAL_Y - out - eo)
        if isinstance(move, str):                        # skating toward the middle: across, 45 degrees, at the goal
            kind = move.rstrip("0123456789.").lstrip("r")
            sx = 1 if x > 0 else -1                      # the side he is on (attacker's view)
            dx, dy = dict(goal=(-sg * x, sg * out), across=(-sg * sx, 0), diag=(-sg * sx, sg), up=(0, sg))[kind]
            if ea:                                       # his skating line turned by the angle error
                c, s_ = math.cos(math.radians(ea)), math.sin(math.radians(ea))
                dx, dy = dx * c - dy * s_, dx * s_ + dy * c
            v = (float(move[len(move.rstrip("0123456789.")):]) + ev) / math.hypot(dx, dy)
            if at_release:                               # started back along his line, to release at (x, out); a
                x0, y0 = round(x0 - (LEAD + ef) * dx * v), round(y0 - (LEAD + ef) * dy * v)   # timing error moves it
        h.setup(x0, y0, settle=settle, clock=clock)
        set_ratings(h, shp * 5, sha * 5)
        if SKATE:
            for off, val in zip((0x68, 0x69), map(int, SKATE.split(","))):
                e.setb(rec(SHOOTER) + off, val)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)      # the hand (as deke_run.job): a left-hander on
        lefty = (x > 0) != BACKHAND                      # NHL94_EA_BACKHAND: the other hand, so the shot is a backhand
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if lefty else (b & ~1))   # his right, a right-hander on his left
        e.setb(rec(SHOOTER) + 4, (a & ~8) if lefty else (a | 8))
        if isinstance(move, str):
            e.setb(rec(SHOOTER) + 0x55, toward(dx, dy))
            e.setw(rec(SHOOTER) + 0x28, round(dx * v * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(dy * v * 4096) & 0xFFFF)
        elif move:
            e.setb(rec(SHOOTER) + 0x55, 0 if top else 4)
            e.setw(rec(SHOOTER) + 0x2A, round(sg * move * 4096) & 0xFFFF)
        base = e.serialize()
        for aim in aims:
            c = res.setdefault(str(aim), dict(n=0, goal=0, held=0, bobble=0, miss=0, noshot=0, speed=0, bob_v=0,
                                              bob_back=0, dive=0, claimed=0, claim_f=0, follow_goal=0,
                                              follow_held=0, follow_none=0, follow_in_off_goalie=0))
            e.unserialize(base)
            pre, _f = h.shoot(aim, 3)
            if pre is None:
                c["noshot"] += 1
                continue
            e.unserialize(pre)
            c["backhand"] = c.get("backhand", 0) + (e.w(rec(SHOOTER) + 0x58) == 0x092E)   # the game's own choice
            rel[0] += sg * e.sw(rec(SHOOTER))
            rel[1] += GOAL_Y - sg * e.sw(rec(SHOOTER) + 0x14)
            rel[2] += 1
            for s in range(SEEDS):
                e.unserialize(pre)
                e.setl(0xD066, rnd.getrandbits(32))
                h.park()
                e.run(1, hold=DIRPAD[aim])
                c["speed"] += math.hypot(e.sw(rec(PUCK) + 0x28), e.sw(rec(PUCK) + 0x2A))
                r, info = play(h, sg, at_goal=isinstance(move, str))
                c["n"] += 1
                c[r] += 1
                if r == "bobble":
                    c["bob_v"] += info.get("v", 0)
                    c["bob_back"] += info["back"]
                    c["dive"] += info["dive"]
                    c["claimed"] += info["claim"] is not None
                    if info.get("claim_x") is not None:  # claimed across the middle from where he started
                        c["claim_across"] = c.get("claim_across", 0) + (info["claim_x"] * x < 0)
                    c["claim_f"] += info["claim"] or 0
                    c["follow_" + info["follow"]] += 1
                breathe()
    for c in res.values():
        if c["n"]:
            c["speed"] = round(c["speed"] / c["n"])
        if c["bobble"]:
            c["bob_v"] = round(c["bob_v"] / c["bobble"])
            c["bob_back"] = round(c["bob_back"] / c["bobble"], 1)
        if c["claimed"]:
            c["claim_f"] = round(c["claim_f"] / c["claimed"], 1)
    out_ = dict(zip(KEYS, args), aims=res)
    if len(args) > 7:
        out_["only"], out_["err"] = list(args[6]), args[7]
    if rel[2]:
        out_["release"] = [round(rel[0] / rel[2], 1), round(rel[1] / rel[2], 1)]
    return out_


def main():
    run = sys.argv[1]
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 60
    plan = sys.argv[3] if len(sys.argv) > 3 else "ea"
    path = RUNS / run / ("ea.jsonl" if plan == "ea" else f"ea_{plan}.jsonl")
    path.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if path.exists():
        for line in open(path):
            d = json.loads(line)
            done.add(tuple(d[k] for k in KEYS) + ((tuple(d["only"]), d["err"]) if "err" in d else ()))
    todo = [j for j in plan_jobs(plan) if j not in done]
    print(f"EA Specials: {len(done)} jobs done before, {len(todo)} to go; this chunk: up to {minutes:g} minutes", flush=True)
    t0, deadline, finished = time.time(), time.time() + 60 * minutes, 0
    with Pool(WORKERS, initializer=_init) as pool, open(path, "a") as f:
        pending, queue = [], list(todo)
        while queue or pending:
            while queue and len(pending) < WORKERS and time.time() < deadline:
                pending.append(pool.apply_async(job, (queue.pop(0),)))
            if not pending:
                break
            time.sleep(1)
            for a in [a for a in pending if a.ready()]:
                pending.remove(a)
                f.write(json.dumps(a.get()) + "\n")
                f.flush()
                finished += 1
    print(f"chunk over: {finished} jobs in {(time.time() - t0) / 60:.1f} minutes; {len(todo) - finished} left", flush=True)


if __name__ == "__main__":
    main()
