"""Animated dekes and floaters (Genesis test ROM): python deke_animate.py OUT_DIR [N]
Each method in METHODS (the best set-ups from deke_run.py, the top net, and the no-swing control) played N times (12
moments x seeds), the game's own frames kept from the approach to the result. The captions give the big run's rate
(deke_run.py: 96 shots, both nets) and the GIFs show goals in about that proportion. Two GIFs per method:
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
     "Deke, left-hander, swung to his right (backhand)", (44, 96)),
    ("deke_no_swing", ("deke", "top", "L", -30, 1, 72, 16, 4, "still"),
     "The same approach and shot with no swing (control)", (0, 80)),
    ("floater_lefty", ("floater", "top", "L", -50, 1, 95, 18, 6, "side"),
     "Floater, left-hander across from his left, swung back left", (58, 96)),
    ("floater_righty", ("floater", "top", "R", 35, -1, 110, 22, 9, "side"),
     "Floater, right-hander across from his right, swung back right", (62, 96)),
]
COL = {"GOAL": "#ea580c", "STOPPED": "#475569"}
PUCK = 14


def play(method, n):
    """n attempts: [(result, [frames], [(shooter, puck, goalie) per frame], release index, swing index)]."""
    import deke_run as D
    from goal_frames import grab, net_on_screen, genesis_vram, hide_genesis_hud
    from harness import decide, rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
    from mapper import set_ratings
    gentle()
    D._init()
    name, args = method[0], method[1]
    plan, net, hand, x0, side, Dd, lag, hold, var = args
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

    def where():
        return tuple((e.sw(rec(k)), e.sw(rec(k) + 0x14)) for k in (SHOOTER, PUCK, GOALIE))

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
        vram = vram or genesis_vram(e)
        b, a = e.b(rec(SHOOTER) + 0x76), e.b(rec(SHOOTER) + 4)
        e.setb(rec(SHOOTER) + 0x76, (b | 1) if hand == "L" else (b & ~1))
        e.setb(rec(SHOOTER) + 4, (a & ~8) if hand == "L" else (a | 8))
        e.setb(rec(SHOOTER) + 0x55, D.screen_dir(face, top))
        e.setw(rec(SHOOTER) + 0x28, round(sg * vx * 4096) & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x2A, round(sg * vy * 4096) & 0xFFFF)
        n0, swing, rel = e.w(E["n"]), None, None
        frames, paths = [], []
        for f in range(200):
            sx, sy = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            gx, gy = e.sw(rec(GOALIE)), e.sw(rec(GOALIE) + 0x14)
            if e.w(PUCKC) != SHOOTER:
                break
            if swing is None and math.hypot(sx - gx, sy - gy) <= Dd:
                swing = f
            c = swing is not None and f >= swing + lag
            d = din if swing is None else dam if c else dsw
            c = c and f < swing + lag + hold
            h.park()
            paths.append(where())
            frames.append(shot_frame((["C"] if c else []) + DIRPAD[d]))
            if e.w(E["n"]) != n0:
                rel = f
                break
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
    g = sum(s[0] == "GOAL" for s in shots)
    return f"{g} of {len(shots)} in"


def clips_gif(method, shots, path):
    name, args, title, (g, n) = method
    rate = g / n
    goals = [s for s in shots if s[0] == "GOAL"]
    others = [s for s in shots if s[0] != "GOAL"]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
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
        d.text((pad, 26), f"{100 * rate:.0f}% go in ({g} of {n} in the full run, both nets).", fill="#52606d", font=f2)
        d.text((pad, 42), "The game's own frames, top net, half speed, lined up on the swing.", fill="#52606d", font=f2)
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
            elif j < rel + 6 or (res == "GOAL" and j < len(fr) - 12) or (res != "GOAL" and j < len(fr) - 4):
                state, col = "shot", "#64748b"
            else:
                state, col = ("GOAL", COL["GOAL"]) if res == "GOAL" else ("STOPPED", COL["STOPPED"])
            if args[8] == "still" and state == "swing":
                state = "no swing"
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 2), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def paths_gif(method, shots, path):
    """Every attempt from above, lined up on the release (the attacker's view: the net at the top)."""
    name, args, title, (g, n) = method
    S, pad, head = 3.0, 14, 64
    x_lo, x_hi, y_lo, y_hi = -80, 80, 95, 280            # rink units (top net: y up the ice)
    W, H = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20

    def P(x, y):
        return pad + (x - x_lo) * S, head + (y_hi - y) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    before = max(s[3] for s in shots)
    after = min(40, min(len(s[2]) - s[3] for s in shots))
    order = sorted(shots, key=lambda s: s[0] == "GOAL")
    frames = []
    for t in range(-before, after):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"Every attempt from above: {len(shots)} here, {tally(shots)}; full run {100 * g / n:.0f}%.",
               fill="#52606d", font=f2)
        d.text((pad, 42), "Puck: orange goal, slate stopped. Grey: shooter. Black: goalie. Blue: swing starts.",
               fill="#52606d", font=f2)
        d.rectangle((pad, head, W - pad, H - 20), fill="#eef6fb")
        gl = P(0, 268)[1]
        d.line((pad, gl, W - pad, gl), fill="#c94040", width=2)
        a, b = P(-20, 276), P(20, 268)
        d.rectangle((a[0], a[1], b[0], b[1]), outline="#52606d", width=2)
        d.arc((P(-40, 228)[0], P(0, 308)[1], P(40, 228)[0], P(0, 228)[1]), 0, 180, fill="#7aa7c7")
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
                    d.line(pk[rel - lo:], fill=col, width=2 if res == "GOAL" else 1)
            if sw is not None and sw <= i:
                c = P(*pts[sw][0])
                d.ellipse((c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3), fill="#0ea5e9")
            c = P(*pts[i][1])
            d.ellipse((c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3), fill=col)
            gc = P(*pts[i][2])
            d.ellipse((gc[0] - 3, gc[1] - 3, gc[0] + 3, gc[1] + 3), fill="#1f2933")
        d.text((pad, H - 18), f"frame {t:+d} from the release (half speed)", fill="#52606d", font=f2)
        frames.append(img.quantize(colors=48, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def job(a):
    method, n, out_dir = a
    t0 = time.time()
    method, shots = play(method, n)
    clips_gif(method, shots, out_dir / f"{method[0]}_clips.gif")
    paths_gif(method, shots, out_dir / f"{method[0]}_paths.gif")
    return method[0], tally(shots), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [m for m in METHODS if not only or m[0] in only]
    with Pool(min(WORKERS, len(todo)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(m, n, out_dir) for m in todo]):
            print(*r, flush=True)
    json.dump([dict(name=m[0], title=m[2], goals=m[3][0], shots=m[3][1]) for m in METHODS],
              open(out_dir / "methods.json", "w"), indent=1)


if __name__ == "__main__":
    main()
