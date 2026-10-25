"""Animated dekes and floaters (Genesis test ROM): python deke_animate.py OUT_DIR [N]
Each method in METHODS (the best set-ups from deke_run.py and the no-swing control, at the top net: going up the
screen) and DOWN (the same moves at the bottom net: going down) played N times (12 moments x seeds), the game's own
frames kept from the approach to the result; ACROSS: the dekebh set-ups (C once the puck is across);
FLOATERBH: the backhand floater; DEKE2: the user's refinements; DEFENDER: a deke against one defender (def_run.py). The captions give the big run's rate (deke_run.py: METHODS 96 shots,
both nets; DOWN that net's 48) and the GIFs show goals in about that proportion. Two GIFs per method:
- <name>_clips.gif: four of the attempts side by side, cropped to the net, each labelled with what happened;
- <name>_paths.gif: every attempt at once from above, lined up on the release: the shooter (grey), the puck (orange
  for a goal, slate for a stop) and the goalie (dark), with the swing's start marked.
After the release the shooter stays on the ice (the run parks him; on the Genesis that changes nothing: animate.py).
Gentle mode (lowload.py)."""
import json
import math
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lowload import WORKERS, breathe, gentle

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
# name, deke_run job (plan, net, hand, x0, side, D, lag, hold, var), title, the big run's goals / shots
METHODS = [
    ("deke_lefty_forehand", ("deke", "top", "L", -30, 1, 72, 16, 4, "side"),
     "Deke, left-hander, swung to his left (forehand)", (82, 96)),
    ("deke_righty_left", ("deke", "top", "R", -30, 1, 72, 16, 4, "side"),
     "Deke, right-hander, swung to his left (backhand)", (80, 96)),
    ("deke_righty_forehand", ("deke", "top", "R", 30, -1, 85, 13, 4, "side"),
     "Deke, right-hander, swung to his right (forehand)", (63, 96)),
    ("deke_lefty_right", ("deke", "top", "L", 30, -1, 85, 13, 4, "side"),
     "Deke, left-hander, swung to his right (the puck doesn't reach his backhand)", (44, 96)),
    ("deke_no_swing", ("deke", "top", "L", -30, 1, 72, 16, 4, "still"),
     "The same approach and shot with no swing (control)", (0, 80)),
    ("floater_lefty", ("floater", "top", "L", -50, 1, 95, 18, 6, "side"),
     "Floater, left-hander across from his left, swung back left", (58, 96)),
    ("floater_righty", ("floater", "top", "R", 35, -1, 110, 22, 9, "side"),
     "Floater, right-hander across from his right, swung back right", (62, 96)),
]
# the deke shot once the puck is across (deke_run.py dekebh): the true backhand dekes and the forehand ones to compare;
# rates: that net's 48 shots in the full run
ACROSS = [
    ("dekebh_lefty_backhand", ("dekebh", "top", "L", 45, -1, 85, 8, 4, "side"),
     "Backhand deke, left-hander, swung to his right", (47, 48)),
    ("dekebh_lefty_backhand_down", ("dekebh", "bottom", "L", 45, -1, 85, 8, 4, "side"),
     "Going down: backhand deke, left-hander, swung to his right", (45, 48)),
    ("dekebh_righty_backhand", ("dekebh", "top", "R", -30, 1, 72, 8, 4, "side"),
     "Backhand deke, right-hander, swung to his left", (38, 48)),
    ("dekebh_righty_backhand_down", ("dekebh", "bottom", "R", -30, 1, 72, 8, 4, "side"),
     "Going down: backhand deke, right-hander, swung to his left", (41, 48)),
    ("dekebh_lefty_forehand", ("dekebh", "top", "L", -30, 1, 72, 8, 4, "side"),
     "Forehand deke shot once across, left-hander, swung to his left", (40, 48)),
    ("dekebh_righty_forehand", ("dekebh", "top", "R", 45, -1, 85, 16, 4, "side"),
     "Forehand deke shot once across, right-hander, swung to his right", (46, 48)),
]
# the floater on the backhand (deke_run.py floaterbh), going up and going down; rates: that net's 48
FLOATERBH = [
    ("floaterbh_lefty", ("floaterbh", "top", "L", 50, -1, 110, 26, 9, "side"),
     "Backhand floater, left-hander, across from his right, swung back right", (22, 48)),
    ("floaterbh_lefty_down", ("floaterbh", "bottom", "L", 50, -1, 110, 26, 9, "side"),
     "Going down: backhand floater, left-hander, swung back right", (27, 48)),
    ("floaterbh_righty", ("floaterbh", "top", "R", -50, 1, 95, 14, 9, "side"),
     "Backhand floater, right-hander, across from his left, swung back left", (26, 48)),
    ("floaterbh_righty_down", ("floaterbh", "bottom", "R", -50, 1, 95, 14, 9, "side"),
     "Going down: backhand floater, right-hander, swung back left", (13, 48)),
]
# the same moves going down the screen (the bottom net); rates: that net's 48 shots in the full run
DOWN = [
    ("deke_lefty_forehand_down", ("deke", "bottom", "L", -30, 1, 72, 16, 4, "side"),
     "Going down: deke, left-hander, swung to his left (forehand)", (46, 48)),
    ("deke_righty_left_down", ("deke", "bottom", "R", -30, 1, 72, 16, 4, "side"),
     "Going down: deke, right-hander, swung to his left (backhand)", (39, 48)),
    ("deke_righty_forehand_down", ("deke", "bottom", "R", 30, -1, 85, 13, 4, "side"),
     "Going down: deke, right-hander, swung to his right (forehand)", (42, 48)),
    ("deke_lefty_right_down", ("deke", "bottom", "L", 30, -1, 85, 13, 4, "side"),
     "Going down: deke, left-hander, swung right (puck doesn't reach his backhand)", (29, 48)),
    ("deke_no_swing_down", ("deke", "bottom", "L", -30, 1, 72, 16, 4, "still"),
     "Going down: the same approach and shot with no swing (control)", (0, 32)),
    ("floater_lefty_down", ("floater", "bottom", "L", -50, 1, 95, 18, 6, "side"),
     "Going down: floater, left-hander across from his left, swung back left", (24, 48)),
    ("floater_righty_down", ("floater", "bottom", "R", 35, -1, 110, 22, 9, "side"),
     "Going down: floater, right-hander across from his right, swung back right", (31, 48)),
]
# the user's refinements (deke_run.py deke2): from farther out to the side, swung closer in; rates: that net's 48
DEKE2 = [
    ("deke2_lefty_forehand", ("deke2", "top", "L", -45, 1, 60, 10, 4, "side"),
     "Refined deke, left-hander, from 15 ft to the left, swung to his left", (45, 48)),
    ("deke2_righty_left", ("deke2", "top", "R", -45, 1, 60, 13, 4, "side"),
     "Refined deke, right-hander, from 15 ft to the left, swung to his left", (45, 48)),
    ("deke2_righty_forehand", ("deke2", "top", "R", 60, -1, 72, 22, 4, "side"),
     "Refined deke, right-hander, from 20 ft to the right, swung to his right", (39, 48)),
    ("deke2_lefty_right_upside", ("deke2", "top", "L", 45, -1, 72, 22, 4, "upside"),
     "Refined deke, left-hander, from 15 ft right, swung right, shot up-right", (40, 48)),
]
# the shooter's skating (deke_run.py plan "best" with NHL94_DEKE_SKATE, 2026-10-25): the same backhand deke by a skater
# of working Agility / Speed 20 and 30 (the set-ups were tuned at the test state's 13); rates: that net's 24 moments x 4
# seeds; the fast skater reached the goalie before the swing ended and carried the puck into the net at all 24 (the
# fifth item: Agility, Speed; the sixth: the caption's scope)
SKATE = [
    ("dekebh_lefty_skate_20", ("dekebh", "top", "L", 45, -1, 85, 8, 4, "side"),
     "Backhand deke, left-hander, Agility / Speed 20", (96, 96), (20, 20), "this net"),
    ("dekebh_lefty_skate_30", ("dekebh", "top", "L", 45, -1, 85, 8, 4, "side"),
     "Backhand deke, left-hander, Agility / Speed 30: he carries it in", (96, 96), (30, 30),
     "this net; carried in, no shot"),
]
# one defender (def_run.py, 2026-10-25): the refined left-hander's deke from 15 ft to his left (he drifts toward the
# middle) with the away left defenceman put 20 to his right of the lane he starts in (toward the middle) or 20 to his
# left (toward the boards), 70 out (about 23 ft); "static": held there; "cpu": the game plays him once the shooter
# starts in. Rates: the filmed plays themselves (None); the seventh item: mode, dx, dout as in def_run.job
DEFENDER = [
    ("def_deke_slot_static", ("deke2", "top", "L", -45, 1, 60, 10, 4, "side"),
     "Deke vs a defender standing in his path", None, None, None, ("static", 20, 70)),
    ("def_deke_slot_cpu", ("deke2", "top", "L", -45, 1, 60, 10, 4, "side"),
     "Deke vs a computer defender starting in his path", None, None, None, ("cpu", 20, 70)),
    ("def_deke_boards_cpu", ("deke2", "top", "L", -45, 1, 60, 10, 4, "side"),
     "Deke vs a computer defender starting by the boards", None, None, None, ("cpu", -20, 70)),
]
COL = {"GOAL": "#ea580c", "CARRIED": "#ea580c", "STOPPED": "#475569", "LOST": "#7c3aed"}
GOALS = ("GOAL", "CARRIED")                          # CARRIED: he took the puck into the net himself, no shot
PUCK = 14


def play(method, n):
    """n attempts: [(result, [frames], [(shooter, puck, goalie) per frame], release index, swing index)]."""
    import deke_run as D
    from goal_frames import grab, net_on_screen, genesis_vram, hide_genesis_hud
    from harness import decide, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
    from mapper import set_ratings
    gentle()
    name, args = method[0], method[1]
    plan, net, hand, x0, side, Dd, lag, hold, var = args
    dfd = method[6] if len(method) > 6 else None
    if dfd:
        import def_run
        def_run._init()
    else:
        D._init()
    h = D._h[net]
    e = h.e
    top = net == "top"
    sg = 1 if top else -1
    vram = None                                      # found once a game frame has run (setup)
    rnd = random.Random(zlib.crc32(name.encode()))
    y0, (vx, vy), face, pad_in, pad_swing = D.move(plan, x0, side)
    aim = ("L" if side > 0 else "R") if var == "still" else D.AIM[(var, side)]
    if var == "still":
        pad_swing = pad_in
    din, dsw, dam = (D.screen_dir(D.PAD[k], top) for k in (pad_in, pad_swing, aim))

    if dfd:                                          # as def_run.job
        h.mode = dfd[0]
        h.defender = (sg * (x0 + dfd[1]), sg * (264 - dfd[2]))

    def where():                                     # the fourth: the defender (def_run.DEF)
        return tuple((e.sw(rec(k)), e.sw(rec(k) + 0x14)) for k in (SHOOTER, PUCK, GOALIE, 10))

    def shot_frame(hold_pad):
        hide_genesis_hud(e, vram)
        e.want_frame = True
        e.run(1, hold=hold_pad)
        e.want_frame = False
        img = grab(e)
        cx, gy = net_on_screen(e, "genesis", net)
        x_lo, y_lo = int(cx - 80), int(gy - 30 if top else gy - 170)
        x_lo, y_lo = max(0, min(img.width - 160, x_lo)), max(0, min(img.height - 200, y_lo))
        return img.crop((x_lo, y_lo, x_lo + 160, y_lo + 200))
    out, p = [], 0
    while len(out) < n and p < 3 * n:
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        p += 1
        h.setup(sg * x0, sg * y0, settle=settle, clock=clock)
        set_ratings(h, *D.RATINGS)
        if len(method) > 4 and method[4]:            # the skater's working Agility and Speed, as deke_run's SKATE
            for off, v in zip((0x68, 0x69), method[4]):
                e.setb(rec(SHOOTER) + off, v)
        vram = vram or genesis_vram(e)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if hand == "L" else (b & ~1))
        e.setb(rec(SHOOTER) + 4, (a & ~8) if hand == "L" else (a | 8))
        e.setb(rec(SHOOTER) + 0x55, D.screen_dir(face, top))
        e.setw(rec(SHOOTER) + 0x28, round(sg * vx * 4096) & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x2A, round(sg * vy * 4096) & 0xFFFF)
        n0, swing, rel, trig = e.w(E["n"]), None, None, None
        frames, paths = [], []
        for f in range(200):
            sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
            if e.w(PUCKC) != SHOOTER:
                break
            if swing is None and math.hypot(sx - gx, sy - gy) <= Dd:
                swing = f
            if plan == "dekebh":                     # C once the puck is `lag` across on the swing's side
                if trig is None and swing is not None and -side * sg * (e.sw(rec(PUCK)) - sx) >= lag:
                    trig = f
                c = trig is not None
                d = din if swing is None else dam if c else dsw
                c = c and f < trig + hold
            else:
                c = swing is not None and f >= swing + lag
                d = din if swing is None else dam if c else dsw
                c = c and f < swing + lag + hold
            h.park()
            paths.append(where())
            frames.append(shot_frame((["C"] if c else []) + DIRPAD[d]))
            if e.w(E["n"]) != n0:
                rel = f
                break
        if rel is None and frames and e.w(PUCKC) != SHOOTER:   # the puck gone before the shot: LOST, or CARRIED IN
            rel, s0 = len(frames) - 1, e.w(SCORE_HOME)         # when he took it into the net himself (a goal)
            for f in range(40):
                h.park(keep_shooter=True)
                paths.append(where())
                frames.append(shot_frame([]))
            out.append(("CARRIED" if e.w(SCORE_HOME) != s0 else "LOST", frames, paths, rel, swing))
            breathe()
            continue
        if rel is None:
            continue
        e.setl(0xD066, rnd.getrandbits(32))       # a fresh seed after the release, as the run's
        s0, held, away, res, tail = e.w(SCORE_HOME), 0, 0, None, 12
        for f in range(150):
            h.park(keep_shooter=True)
            paths.append(where())
            frames.append(shot_frame(DIRPAD[dam] if f == 0 else []))
            if res is not None:
                tail -= 1
                if tail == 0:
                    break
                continue
            if e.w(SCORE_HOME) != s0:
                res = "GOAL"
                continue
            held = held + 1 if e.w(PUCKC) == GOALIE else 0
            vyp = e.sw(rec(PUCK) + 0x2A) * sg
            away = away + 1 if vyp < 0 else 0
            if held >= 20 or away >= 4 or e.sw(rec(PUCK) + 0x14) * sg > 276:
                res, tail = "STOPPED", 4
        out.append((res or "STOPPED", frames, paths, rel, swing))
        breathe()
    return method, out


def tally(shots):
    g = sum(s[0] in GOALS for s in shots)
    return f"{g} of {len(shots)} in"


def clips_gif(method, shots, path):
    name, args, title, (g, n) = method[:4]
    rate = g / n
    goals = [s for s in shots if s[0] in GOALS]
    others = [s for s in shots if s[0] not in GOALS]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
    rest = [s for s in goals if all(s is not q for q in pick)]    # too few misses: more goals to fill the four
    pick += r.sample(rest, min(4 - len(pick), len(rest)))
    r.shuffle(pick)
    Z, pad, lab, head = 1.5, 8, 26, 62
    cw, ch = int(160 * Z), int(200 * Z)
    W, H = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 14)
    span = max(len(s[1]) - max(0, (s[4] or 20) - 20) for s in pick)
    frames = []
    for t in range(0, span, 1):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        scope = method[5] if len(method) > 5 and method[5] else "both nets" if n > 48 else "this net"
        d.text((pad, 26), f"{100 * rate:.0f}% go in ({g} of {n} filmed here)." if len(method) > 6 else
               f"{100 * rate:.0f}% go in ({g} of {n} in the full run, {scope}).", fill="#52606d", font=f2)
        d.text((pad, 42), f"The game's own frames, {args[1]} net, half speed, lined up on the swing.", fill="#52606d",
               font=f2)
        for i, (res, fr, _, rel, sw) in enumerate(pick):
            off = max(0, (sw or 20) - 20)                # start each clip 20 frames before its swing
            j = min(off + t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j].resize((cw, ch), Image.NEAREST), (x, y))
            if sw is not None and j < sw:
                state, col = "coming in", "#cbd2d9"
            elif j < rel:
                state, col = "swing", "#94a3b8" if args[8] == "still" else "#0ea5e9"
            elif j < rel + 6 or (res in GOALS and j < len(fr) - 12) or (res not in GOALS and j < len(fr) - 4):
                state, col = "shot", "#64748b"
            else:
                state, col = {"GOAL": ("GOAL", COL["GOAL"]), "CARRIED": ("GOAL: CARRIED IN", COL["GOAL"]),
                                  "LOST": ("LOST THE PUCK", COL["LOST"])}.get(
                    res, ("STOPPED", COL["STOPPED"]))
            if args[8] == "still" and state == "swing":
                state = "no swing"
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 2), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def paths_gif(method, shots, path):
    """Every attempt from above, lined up on the release (the attacker's view: the net at the top)."""
    name, args, title, (g, n) = method[:4]
    S, pad, head = 3.0, 14, 64
    x_lo, x_hi, y_lo, y_hi = -80, 80, 95, 280            # rink units from the net's end (as on the screen)
    W, H = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20
    sg = 1 if args[1] == "top" else -1

    def P(x, y):                                         # top net at the top, bottom net at the bottom
        return pad + (x - x_lo) * S, head + ((y_hi - y) if sg > 0 else (-y_lo - y)) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    before = max(s[3] for s in shots)
    after = min(40, min(len(s[2]) - s[3] for s in shots))
    order = sorted(shots, key=lambda s: s[0] in GOALS)
    frames = []
    for t in range(-before, after):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        dfd = method[6] if len(method) > 6 else None
        d.text((pad, 26), f"Every attempt from above: {len(shots)} here, {tally(shots)}" +
               ("." if dfd else f"; full run {100 * g / n:.0f}%."), fill="#52606d", font=f2)
        d.text((pad, 42), "Puck: orange goal, slate stopped" + (", purple lost" if any(s[0] == "LOST" for s in shots)
                                                                     else "") + ". Grey: shooter. Black: goalie. Blue: swing starts." +
               (" Green: defender." if dfd else ""), fill="#52606d", font=f2)
        d.rectangle((pad, head, W - pad, H - 20), fill="#eef6fb")
        gl = P(0, sg * 268)[1]
        d.line((pad, gl, W - pad, gl), fill="#c94040", width=2)
        a, b = P(-20, sg * 276), P(20, sg * 268)
        d.rectangle((a[0], min(a[1], b[1]), b[0], max(a[1], b[1])), outline="#52606d", width=2)
        r = 40 * S                                       # the crease: a half circle in front of the goal line
        d.arc((P(0, 0)[0] - r, gl - r, P(0, 0)[0] + r, gl + r), 0 if sg > 0 else 180, 180 if sg > 0 else 360,
              fill="#7aa7c7")
        for s in order:
            res, _, pts, rel, sw = s
            i = min(max(rel + t, 0), len(pts) - 1)
            lo = max(0, i - 400)
            sk = [P(*q[0]) for q in pts[lo:i + 1]]
            pk = [P(*q[1]) for q in pts[lo:i + 1]]
            col = COL[res] if i >= rel else "#94a3b8"
            if len(sk) > 1:
                d.line(sk, fill="#cbd2d9", width=1)
            if len(pk) > 1:
                d.line(pk[:max(1, rel - lo + 1)], fill="#94a3b8", width=1)
                if i > rel:
                    d.line(pk[rel - lo:], fill=col, width=2 if res in GOALS else 1)
            if sw is not None and sw <= i:
                c = P(*pts[sw][0])
                d.ellipse((c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3), fill="#0ea5e9")
            c = P(*pts[i][1])
            d.ellipse((c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3), fill=col)
            gc = P(*pts[i][2])
            d.ellipse((gc[0] - 3, gc[1] - 3, gc[0] + 3, gc[1] + 3), fill="#1f2933")
            if dfd:
                dc = P(*pts[i][3])
                d.ellipse((dc[0] - 3, dc[1] - 3, dc[0] + 3, dc[1] + 3), fill="#16a34a")
        d.text((pad, H - 18), f"frame {t:+d} from the release (half speed)", fill="#52606d", font=f2)
        frames.append(img.quantize(colors=48, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def job(a):
    method, n, out_dir = a
    t0 = time.time()
    method, shots = play(method, n)
    if method[3] is None:                            # the rate is the filmed plays' own
        method = method[:3] + ((sum(s[0] in GOALS for s in shots), len(shots)),) + method[4:]
    clips_gif(method, shots, out_dir / f"{method[0]}_clips.gif")
    paths_gif(method, shots, out_dir / f"{method[0]}_paths.gif")
    return method[0], tally(shots), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [m for m in METHODS + DOWN + ACROSS + FLOATERBH + DEKE2 + SKATE + DEFENDER if not only or m[0] in only]
    with Pool(min(WORKERS, len(todo)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(m, n, out_dir) for m in todo]):
            print(*r, flush=True)
    json.dump([dict(name=m[0], title=m[2], goals=m[3] and m[3][0], shots=m[3] and m[3][1]) for m in METHODS + DOWN + ACROSS + FLOATERBH + DEKE2 + SKATE + DEFENDER],
              open(out_dir / "methods.json", "w"), indent=1)


if __name__ == "__main__":
    main()
