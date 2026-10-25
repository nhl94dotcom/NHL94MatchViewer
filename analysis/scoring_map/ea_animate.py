"""Animated EA Specials (Genesis test ROM): python ea_animate.py OUT_DIR [N] [names]
Each case in CASES is one set-up of ea_run.py (a left-hander standing 40 to the side, his forehand side, the first
wrist shot aimed across) with one Shot Power / Accuracy; the follow-up is ea_run's own bot (play(): skate on, chase
the loose puck once the goalie has touched it, tap C at the near post on claiming it). N attempts (moments x seeds),
the game's own frames from the wind-up to the end of the play. The captions give this script's own rate over 120
moments (the EA run's 8 moments gave 39% and 0% here: its plays share moments, so one set-up's rate there wanders); the
clips show goals in about that proportion. Two GIFs per case:
- <name>_clips.gif: four plays side by side, the whole screen, each labelled with how it ended;
- <name>_paths.gif: every play at once from above, lined up on the release: the shooter (grey), the puck (orange for
  a goal, slate otherwise) and the goalie (black; red where he dived).
Gentle mode (lowload.py)."""
import json
import math
import os
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lowload import WORKERS, breathe

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
# name, net, x (to the side), out, aim, Shot Power step, Shot Accuracy step (None: 2-6 in turn, as the rate is
# over every accuracy), title, goals / plays over 120 moments (play(case, 120)); optionally ea_run's move (a string:
# skating at the middle of the goal line at that speed) and the caption's description of the set-up
STANDING = ("Left-handed, 30 ft out, 13 ft to his forehand side,", "aimed across, Shot Accuracy 2-6 in turn.")
CASES = [
    ("ea_power_2", "top", 40, 90, 6, 2, None, "EA Special, Shot Power 2: the weak shot is bobbled and the goalie dives",
     (26, 120)),
    ("ea_power_6", "top", 40, 90, 6, 6, None, "EA Special, Shot Power 6: the hard shot is held or cleared", (2, 120)),
    # the faceoff dots (plan "dots", 2026-10-25): the run's best top-net set-up, 85 to the side, 75 out, skating at
    # the goal at 2.5 a frame, aimed Up-Left
    ("ea_dot_power_2", "top", 85, 75, 7, 2, None, "EA Special from beside the faceoff dot, skating at the goal, Shot Power 2",
     (35, 120), "goal2.5", ("Left-handed, 25 ft out, 28 ft to his forehand side,",
                            "skating in, aimed Up-Left, Accuracy 2-6.")),
    ("ea_dot_power_6", "top", 85, 75, 7, 6, None, "EA Special from beside the faceoff dot, skating at the goal, Shot Power 6",
     (5, 120), "goal2.5", ("Left-handed, 25 ft out, 28 ft to his forehand side,",
                            "skating in, aimed Up-Left, Accuracy 2-6.")),
    # the shooter's line (plan "angle", 2026-10-25): skating straight across against at 45 degrees, from 23 ft to his
    # right and 25 ft out, Shot Power 2, Accuracy 4, aimed Up-Left; rates: the filmed plays themselves (None)
    ("ea_angle_across", "top", 70, 75, 7, 2, 4, "EA Special skating straight across", None, "across2.5",
     ("Left-handed, 25 ft out, 23 ft to his right,", "skating straight across, aimed Up-Left, Power 2.")),
    ("ea_angle_diag", "top", 70, 75, 7, 2, 4, "EA Special skating in at 45 degrees", None, "diag2.5",
     ("Left-handed, 25 ft out, 23 ft to his right,", "skating in at 45 degrees, aimed Up-Left, Power 2.")),
    # the user's marked spots (plan "xspot", 2026-10-25): released 25 ft to his left and 14 ft out by a right-hander
    # skating at the goal at 2.5 a frame, Shot Power 2, Accuracy 4, no direction held; the bottom net (the run's
    # best, against the test goalie and Roy) and the top net (the same play, far less); ea_run's "r" move: x and out
    # are the release; optionally the goalie's working ratings (harness NHL94_GOALIE)
    ("ea_xspot_bottom", "bottom", -75, 42, 8, 2, 4, "EA Special from the marked spot, bottom net", None, "rgoal2.5",
     ("Right-handed, released 14 ft out, 25 ft to his left,", "skating at the goal, no direction held, Power 2.")),
    ("ea_xspot_bottom_roy", "bottom", -75, 42, 8, 2, 4, "EA Special from the marked spot, bottom net, against Roy",
     None, "rgoal2.5", ("Right-handed, released 14 ft out, 25 ft to his left,",
                        "skating at the goal, no direction held, Power 2."), (30, 20, 20, 30)),
    ("ea_xspot_top", "top", -75, 42, 8, 2, 4, "EA Special from the marked spot, top net", None, "rgoal2.5",
     ("Right-handed, released 14 ft out, 25 ft to his left,", "skating at the goal, no direction held, Power 2.")),
]
COL = {"GOAL": "#ea580c", "OTHER": "#475569"}
DIVE = 0x02F4


def play(case, n):
    """n plays: [(label, goal?, [frames], [(shooter, puck, goalie, diving)], release index)]."""
    import ea_run as A
    from goal_frames import grab, genesis_vram, hide_genesis_hud
    from harness import rec, DIRPAD, SHOOTER, GOALIE
    from mapper import set_ratings
    if len(case) > 11:                                 # the goalie's working ratings
        os.environ["NHL94_GOALIE"] = ",".join(map(str, case[11]))
    A._init()
    name, net, x, out, aim, shp, sha = case[:7]
    h = A._h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    rnd = random.Random(zlib.crc32(name.encode()))
    run, film = e.run, []
    vram = None

    def filmed(k, hold=None):                         # every frame the play runs, kept while filming
        if film:
            hide_genesis_hud(e, vram)
            e.want_frame = True
        run(k, hold=hold) if hold is not None else run(k)
        e.want_frame = False
        if film:
            film[0].append(grab(e).copy())
            film[1].append(tuple((sg * e.sw(rec(k)), sg * e.sw(rec(k) + 0x14)) for k in (SHOOTER, A.PUCK, GOALIE))
                           + (e.w(rec(GOALIE) + 0x58) == DIVE,))
    e.run = filmed
    plays, p = [], 0
    while len(plays) < n and p < 3 * n:
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        p += 1
        move = case[9] if len(case) > 9 else None
        x0, y0 = sg * x, sg * (A.GOAL_Y - out)
        if move:                                       # as ea_run.job: across, at 45 degrees or at the goal
            kind = move.rstrip("0123456789.").lstrip("r")
            sx = 1 if x > 0 else -1
            dx, dy = dict(goal=(-sg * x, sg * out), across=(-sg * sx, 0), diag=(-sg * sx, sg))[kind]
            v = float(move[len(move.rstrip("0123456789.")):]) / math.hypot(dx, dy)
            if move.startswith("r"):                   # started back along his line, to release at (x, out)
                x0, y0 = round(x0 - A.LEAD * dx * v), round(y0 - A.LEAD * dy * v)
        h.setup(x0, y0, settle=settle, clock=clock)
        set_ratings(h, shp * 5, (sha or 2 + len(plays) % 5) * 5)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)      # the hand, as ea_run.job
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if x > 0 else (b & ~1))
        e.setb(rec(SHOOTER) + 4, (a & ~8) if x > 0 else (a | 8))
        if move:
            e.setb(rec(SHOOTER) + 0x55, A.toward(dx, dy))
            e.setw(rec(SHOOTER) + 0x28, round(dx * v * 4096) & 0xFFFF)
            e.setw(rec(SHOOTER) + 0x2A, round(dy * v * 4096) & 0xFFFF)
        vram = vram or genesis_vram(e)
        film[:] = [[], []]
        pre, _f = h.shoot(aim, 3)
        if pre is None:
            film.clear()
            continue
        film[0].pop()                                  # the release frame: played again below with its seed
        film[1].pop()
        e.unserialize(pre)
        e.setl(0xD066, rnd.getrandbits(32))
        rel = len(film[0])
        h.park()
        e.run(1, hold=DIRPAD[aim])
        r, info = A.play(h, sg, at_goal=bool(move))
        for _ in range(12):
            A.park_except(h, (SHOOTER,))
            e.run(1)
        frames, pts = film[0], film[1]
        film.clear()
        goal = r == "goal" or info["follow"] in ("goal", "in_off_goalie")
        label = {"goal": "GOAL straight in", "held": "HELD", "miss": "MISSED"}.get(r)
        if label is None:
            label = ("GOAL on the rebound" if goal else "bobbled, held after" if info["follow"] == "held"
                     else "bobbled, no goal")
        if info["dive"]:
            label += ", he dived"
        plays.append((label, goal, frames, pts, rel))
        breathe()
    return case, plays


def tally(plays):
    return f"{sum(s[1] for s in plays)} of {len(plays)} in"


def clips_gif(case, plays, path):
    title, (g, n) = case[7], case[8]
    rate = g / n
    goals = [s for s in plays if s[1]]
    others = [s for s in plays if not s[1]]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
    rest = [s for s in goals if all(s is not q for q in pick)]    # too few misses: more goals to fill the four
    pick += r.sample(rest, min(4 - len(pick), len(rest)))
    r.shuffle(pick)
    cw, ch = pick[0][2][0].size
    pad, lab, head = 8, 26, 78
    W, H = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 13)
    lead = 15
    span = max(len(s[2]) - max(0, s[4] - lead) for s in pick)
    frames = []
    for t in range(span):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        desc = case[10] if len(case) > 10 else STANDING
        d.text((pad, 26), f"{100 * rate:.0f}% end in a goal ({g} of {n} plays). {desc[0]}", fill="#52606d", font=f2)
        d.text((pad, 42), f"{desc[1]} The game's own frames, {case[1]} net, half speed;", fill="#52606d", font=f2)
        d.text((pad, 58), "after the shot, the run's bot plays on.", fill="#52606d", font=f2)
        for i, (label, goal, fr, _, rel) in enumerate(pick):
            j = min(max(0, rel - lead) + t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j], (x, y))
            if j < rel:
                state, col = "wind-up", "#0ea5e9"
            elif j < len(fr) - 12:
                state, col = "the play", "#64748b"
            else:
                state, col = label, COL["GOAL" if goal else "OTHER"]
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 3), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def trail(d, pts, fill, width):
    """A track, broken where it jumps (the puck put back after a whistle, or carried on the far side of a body)."""
    for a, b in zip(pts, pts[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 60:
            d.line((a, b), fill=fill, width=width)


def paths_gif(case, plays, path):
    """Every play from above, lined up on the release, the net at the top (the bottom net's plays turned round)."""
    title, (g, n) = case[7], case[8]
    S, pad, head = 3.0, 14, 64
    x_lo, x_hi, y_lo, y_hi = -110, 110, 150, 282
    W, H = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20

    def Q(x, y):
        return (x - x_lo) * S, (y_hi - y) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    after = min(150, max(len(s[3]) - s[4] for s in plays))
    order = sorted(plays, key=lambda s: s[1])
    frames = []
    for t in range(-12, after):
        img = Image.new("RGB", (W, H), "white")
        d0 = ImageDraw.Draw(img)
        d0.text((pad, 6), title, fill="#1f2933", font=f1)
        d0.text((pad, 26), f"Every play from above: {len(plays)} here, {tally(plays)}; over 120 moments {100 * g / n:.0f}%.",
                fill="#52606d", font=f2)
        d0.text((pad, 42), "Puck: orange when the play ends in a goal. Grey: shooter. Black: goalie, red while he dives.",
                fill="#52606d", font=f2)
        rink = Image.new("RGB", (W - 2 * pad, H - 20 - head), "#eef6fb")
        d = ImageDraw.Draw(rink)
        gl = Q(0, 268)[1]
        d.line((0, gl, W, gl), fill="#c94040", width=2)
        a, b = Q(-20, 276), Q(20, 268)
        d.rectangle((a[0], a[1], b[0], b[1]), outline="#52606d", width=2)
        for label, goal, _, pts, rel in order:
            i = min(max(rel + t, 0), len(pts) - 1)
            col = COL["GOAL" if goal else "OTHER"]
            sk = [Q(*q[0]) for q in pts[:i + 1]]
            pk = [Q(*q[1]) for q in pts[rel:i + 1]]
            trail(d, sk, "#cbd2d9", 1)
            trail(d, pk, col, 2 if goal else 1)
            for c, f, r in ((Q(*pts[i][0]), "#9aa5b1", 3), (Q(*pts[i][1]), col, 3),
                            (Q(*pts[i][2]), "#dc2626" if pts[i][3] else "#1f2933", 4)):
                d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=f)
        img.paste(rink, (pad, head))
        d0.text((pad, H - 18), f"frame {t:+d} from the release (half speed)", fill="#52606d", font=f2)
        frames.append(img.quantize(colors=48, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def job(a):
    case, n, out_dir = a
    t0 = time.time()
    case, plays = play(case, n)
    if case[8] is None:                                # the rate is the filmed plays' own
        case = case[:8] + ((sum(s[1] for s in plays), len(plays)),) + case[9:]
    clips_gif(case, plays, out_dir / f"{case[0]}_clips.gif")
    paths_gif(case, plays, out_dir / f"{case[0]}_paths.gif")
    return case[0], tally(plays), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    names = sys.argv[3:]
    cases = [c for c in CASES if not names or c[0] in names]
    out_dir.mkdir(parents=True, exist_ok=True)
    with Pool(min(WORKERS, len(cases)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(c, n, out_dir) for c in cases]):
            print(*r, flush=True)
    json.dump([dict(name=c[0], title=c[7], goals=c[8] and c[8][0], plays=c[8] and c[8][1]) for c in cases],
              open(out_dir / "cases.json", "w"), indent=1)


if __name__ == "__main__":
    main()
