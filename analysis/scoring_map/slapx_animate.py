"""Animated far-post slapshots skating across, by shooter rating (Genesis test ROM): python slapx_animate.py OUT_DIR [N]
Each case in CASES is mv_run.py's plan "slapxr" (crossing toward the stick side, the wind-up begun 60 before the
middle) for one Shot Power / Accuracy at one distance, at the bottom net (the top net's start from the right at 125
out is faulty: SCORING_MAP "Moving shooters"), aimed at the far post ahead of him (Right). N attempts (moments x
seeds), the game's own frames kept from the start of the skate to the result. The captions give the ratings run's
rate for that very set-up and aim (64 shots: 16 moments x 4 seeds); the clips show goals in about that proportion.
Two GIFs per case:
- <name>_clips.gif: four attempts side by side, the whole screen, each labelled with what is happening;
- <name>_paths.gif: every attempt at once from above (turned so the net is at the top): the shooter (grey), the puck
  (orange for a goal, slate for a stop), the goalie (dark), the wind-up's start marked.
Gentle mode (lowload.py)."""
import json
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
AIM = 2                    # Right: at the bottom net, crossing to the right (his stick side), the far post ahead
# name, Shot Power step, Shot Accuracy step, out, title, the ratings run's goals / shots at this set-up and aim
CASES = [
    ("slapx_3_3_105", 3, 3, 105, "Skating slapshot, far post, 35 ft: Shot Power 3 / Accuracy 3", (2, 64)),
    ("slapx_4_4_105", 4, 4, 105, "Skating slapshot, far post, 35 ft: Shot Power 4 / Accuracy 4", (28, 64)),
    ("slapx_6_6_105", 6, 6, 105, "Skating slapshot, far post, 35 ft: Shot Power 6 / Accuracy 6", (51, 64)),
    ("slapx_4_4_125", 4, 4, 125, "Skating slapshot, far post, 42 ft: Shot Power 4 / Accuracy 4", (9, 64)),
    ("slapx_6_6_125", 6, 6, 125, "Skating slapshot, far post, 42 ft: Shot Power 6 / Accuracy 6", (38, 64)),
]
COL = {"GOAL": "#ea580c", "STOPPED": "#475569"}
PUCK = 14


def play(case, n):
    """n attempts: [(result, [frames], [(shooter, puck, goalie)], wind-up index, release index)]."""
    import mv_run as M
    from goal_frames import grab, genesis_vram, hide_genesis_hud
    from harness import rec, DIRPAD, E, SHOOTER, GOALIE, PUCKC, SCORE_HOME
    from mapper import set_ratings
    gentle()
    M._init()
    name, shp, sha, out = case[:4]
    h = M._h["bottom"]
    e = h.e
    sg, side, rel = -1, -1, -60
    d, (vx, vy) = M.travel("slapxr", side, sg)
    rnd = random.Random(zlib.crc32(name.encode()))
    vram = None

    def where():
        return tuple((e.sw(rec(k)), e.sw(rec(k) + 0x14)) for k in (SHOOTER, PUCK, GOALIE))

    def frame(pad):
        hide_genesis_hud(e, vram)
        e.want_frame = True
        e.run(1, hold=pad)
        e.want_frame = False
        return grab(e).copy()
    shots, p = [], 0
    while len(shots) < n and p < 3 * n:
        clock, settle = 590 - (p * 3) % 8, 80 + (p * 7) % 15
        p += 1
        h.setup(130 * side, sg * (M.GOAL_Y - out), settle=settle, clock=clock)
        set_ratings(h, shp * 5, sha * 5)
        vram = vram or genesis_vram(e)
        e.setb(rec(SHOOTER) + 0x55, d)
        e.setw(rec(SHOOTER) + 0x28, vx & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x2A, vy & 0xFFFF)
        frames, paths, wind, release = [], [], None, None
        n0 = e.w(E["n"])
        for f in range(300):
            x, y = e.sw(rec(SHOOTER)), e.sw(rec(SHOOTER) + 0x14)
            if e.w(PUCKC) != SHOOTER:
                break
            if wind is None and M.reached("slapxr", side, sg, x, y, rel):
                wind = f
            c = wind is not None and f < wind + M.SLAP_HOLD
            h.park()
            paths.append(where())
            frames.append(frame((["C"] if c else []) + DIRPAD[AIM if wind is not None else d]))
            if e.w(E["n"]) != n0:
                release = f
                break
        if release is None:
            continue
        e.setl(0xD066, rnd.getrandbits(32))
        s0, held, away, res, tail = e.w(SCORE_HOME), 0, 0, None, 12
        for f in range(150):
            h.park(keep_shooter=True)
            paths.append(where())
            frames.append(frame(DIRPAD[AIM] if f == 0 else []))
            if res is not None:
                tail -= 1
                if tail == 0:
                    break
                continue
            if e.w(SCORE_HOME) != s0:
                res = "GOAL"
                continue
            held = held + 1 if e.w(PUCKC) == GOALIE else 0
            away = away + 1 if e.sw(rec(PUCK) + 0x2A) * sg < 0 else 0
            if held >= 20 or away >= 4 or e.sw(rec(PUCK) + 0x14) * sg > 276:
                res, tail = "STOPPED", 4
        shots.append((res or "STOPPED", frames, paths, wind, release))
        breathe()
    return case, shots


def tally(shots):
    return f"{sum(s[0] == 'GOAL' for s in shots)} of {len(shots)} in"


def clips_gif(case, shots, path):
    name, shp, sha, out, title, (g, n) = case
    rate = g / n
    goals = [s for s in shots if s[0] == "GOAL"]
    others = [s for s in shots if s[0] != "GOAL"]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
    r.shuffle(pick)
    cw, ch = pick[0][1][0].size
    pad, lab, head = 8, 26, 62
    W, H = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 14)
    span = max(len(s[1]) - max(0, s[3] - 20) for s in pick)
    frames = []
    for t in range(span):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"{100 * rate:.0f}% go in at this spot and aim ({g} of {n} in the ratings run). "
                          "Left-handed, crossing to his stick side.", fill="#52606d", font=f2)
        d.text((pad, 42), "The game's own frames, bottom net, half speed, lined up on the wind-up.", fill="#52606d",
               font=f2)
        for i, (res, fr, _, wind, rel) in enumerate(pick):
            j = min(max(0, wind - 20) + t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j], (x, y))
            if j < wind:
                state, col = "skating across", "#cbd2d9"
            elif j < rel:
                state, col = "wind-up", "#0ea5e9"
            elif (res == "GOAL" and j < len(fr) - 12) or (res != "GOAL" and j < len(fr) - 4):
                state, col = "shot", "#64748b"
            else:
                state, col = res, COL[res]
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 2), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def paths_gif(case, shots, path):
    """Every attempt from above, lined up on the release, turned so the net is at the top (the attacker's view)."""
    name, shp, sha, out, title, (g, n) = case
    S, pad, head = 2.2, 14, 64
    x_lo, x_hi, y_lo, y_hi = -145, 145, 120, 282
    W, H = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20

    def P(x, y):                                         # bottom net: turned half round
        return pad + (-x - x_lo) * S, head + (y_hi + y) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    before = max(s[4] for s in shots)
    after = min(45, min(len(s[2]) - s[4] for s in shots))
    order = sorted(shots, key=lambda s: s[0] == "GOAL")
    frames = []
    for t in range(-before, after):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"Every attempt from above: {len(shots)} here, {tally(shots)}; the ratings run "
                          f"{100 * g / n:.0f}%.", fill="#52606d", font=f2)
        d.text((pad, 42), "Puck: orange goal, slate stopped. Grey: shooter. Black: goalie. Blue: the wind-up starts.",
               fill="#52606d", font=f2)
        d.rectangle((pad, head, W - pad, H - 20), fill="#eef6fb")
        gl = P(0, -268)[1]
        d.line((pad, gl, W - pad, gl), fill="#c94040", width=2)
        a, b = P(20, -276), P(-20, -268)
        d.rectangle((a[0], a[1], b[0], b[1]), outline="#52606d", width=2)
        for s in order:
            res, _, pts, wind, rel = s
            i = min(max(rel + t, 0), len(pts) - 1)
            sk = [P(*q[0]) for q in pts[:i + 1]]
            pk = [P(*q[1]) for q in pts[:i + 1]]
            col = COL[res] if i >= rel else "#94a3b8"
            if len(sk) > 1:
                d.line(sk, fill="#cbd2d9", width=1)
            if len(pk) > 1:
                d.line(pk[:rel + 1], fill="#94a3b8", width=1)
                if i > rel:
                    d.line(pk[rel:], fill=col, width=2 if res == "GOAL" else 1)
            if wind <= i:
                c = P(*pts[wind][0])
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
    case, n, out_dir = a
    t0 = time.time()
    case, shots = play(case, n)
    clips_gif(case, shots, out_dir / f"{case[0]}_clips.gif")
    paths_gif(case, shots, out_dir / f"{case[0]}_paths.gif")
    return case[0], tally(shots), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    out_dir.mkdir(parents=True, exist_ok=True)
    with Pool(min(WORKERS, len(CASES)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(c, n, out_dir) for c in CASES]):
            print(*r, flush=True)
    json.dump([dict(name=c[0], title=c[4], goals=c[5][0], shots=c[5][1]) for c in CASES],
              open(out_dir / "cases.json", "w"), indent=1)


if __name__ == "__main__":
    main()
