"""Animated one-timers (Genesis test ROM): python ot_animate.py OUT_DIR [N] [names]
Each case in CASES is one set-up of ot_run.py's plan "ratings" (top net) with the receiver's Shot Power / Accuracy
steps: the passer at P with the puck, the receiver at R, the goalie settled; the pass, the one-timer button (C) pressed
early or late in the pass as ot_run spreads it over the moments, the swing to the strike, the strike frame given a
fresh random seed as in the run, then played out. N attempts (moments), the game's own frames from before the pass to
the result; whiffs are left out (the rates are per struck one-timer). The captions give the ratings run's rate for that
very set-up (512 struck: 32 moments x 2 timings x 8 seeds); the clips show goals in about that proportion.
Two GIFs per case:
- <name>_clips.gif: four attempts side by side, the whole screen, each labelled with what is happening;
- <name>_paths.gif: every attempt at once from above, lined up on the strike: passer and receiver (grey), the puck
  (slate on the pass, then orange for a goal, dark slate for a stop), the goalie (black, his track drawn).
Gentle mode (lowload.py)."""
import json
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
# name, receiver R, passer P (net coordinates, top net), Shot Power step, Shot Accuracy step, title, the run's
# goals / struck one-timers at this set-up and these ratings
CASES = [
    ("ot_across", (30, 213), (-30, 213), 4, 4,
     "One-timer, the pass across (18 ft out, 10 ft to the side)", (455, 512)),
    ("ot_same_side", (30, 213), (90, 213), 4, 4,
     "One-timer, the pass from his own side (18 ft out, 10 ft to the side)", (197, 512)),
    ("ot_rating_2_2", (30, 213), (82, 243), 2, 2,
     "One-timer from the side, Shot Power 2 / Accuracy 2", (104, 512)),
    ("ot_rating_6_6", (30, 213), (82, 243), 6, 6,
     "One-timer from the side, Shot Power 6 / Accuracy 6", (345, 512)),
]
COL = {"GOAL": "#ea580c", "SAVED": "#475569", "POST": "#475569", "MISSED": "#475569"}
SHOWN = {"GOAL": "GOAL", "SAVED": "SAVED", "POST": "POST", "MISSED": "WIDE"}


def play(case, n):
    """n struck one-timers: [(result, [frames], [(passer, receiver, puck, goalie)], release, press, strike)]."""
    name, R, P, shp, sha = case[:5]
    os.environ["NHL94_OT_RATINGS"] = f"{shp * 5},{sha * 5}"
    from animate import outcome
    from goal_frames import grab, genesis_vram, hide_genesis_hud
    from ot_harness import OneTimer, PASSER, RECEIVER, DIRS, direction
    ot = OneTimer("genesis")
    s, e = ot.s, ot.e
    rnd = random.Random(zlib.crc32(name.encode()))
    vram = None

    def where():
        return tuple(s.xy(k) for k in (PASSER, RECEIVER, s.PUCK, s.GOALIE))

    def attempt(start, d, by, timing, seed, strike_at=None, film=False):
        """Play from the set-up: the pass, the press, the swing. Without strike_at: find the frames (release, press,
        strike) or None. With it: the seed set just before the strike frame, frames filmed, the shot played out."""
        e.unserialize(start)
        frames, paths, released, caught = [], [], None, None
        if timing == "late":                                # when he would take it, from a pass with no press
            for f in range(90):
                ot.run([s.pass_button] + d if f < 4 else d)
                if released is None and s.carrier() != PASSER:
                    released = f
                if released is not None and s.carrier() == RECEIVER:
                    caught = f
                    break
            if caught is None:
                return None
            e.unserialize(start)
            released = None
        press, mark0 = None, s.strike_mark()
        for f in range(150):
            if press is None and released is not None:
                p = released + by if timing == "early" else max(released + 1, caught - by)
                if f == p:
                    press = f
            if press is None:
                pad = [s.pass_button] + d if f < 4 else d
            else:
                pad = [s.ot_button] if f - press < 2 else []
            if strike_at is not None and f == strike_at:
                s.set_seed(seed)
            if film:
                hide_genesis_hud(e, vram)
                e.want_frame = True
            ot.run(pad)
            e.want_frame = False
            if film:
                frames.append(grab(e).copy())
                paths.append(where())
            if released is None and s.carrier() != PASSER:
                released = f
            if press is None and released is not None and s.carrier() == RECEIVER:
                return None                                 # taken before the press: an ordinary shot
            if press is not None and s.strike_mark() != mark0:
                if strike_at is None:
                    return released, press, f
                break
            if press is not None and f - press > 60:
                return None                                 # whiff
        else:
            return None
        s0, sign, states, res, tail, held, away = s.score(), ot.sg, [s.state()], None, 12, 0, 0
        for f in range(150):
            hide_genesis_hud(e, vram)
            e.want_frame = True
            ot.run()
            e.want_frame = False
            frames.append(grab(e).copy())
            paths.append(where())
            if res is not None:
                tail -= 1
                if tail == 0:
                    break
                continue
            st = s.state()
            if s.score() != s0:
                res = outcome(states, len(states) - 1, True)
                continue
            states.append(st)
            held = held + 1 if st[8] else 0
            away = away + 1 if st[4] * sign < 0 else 0
            if held >= 20 or away >= 4 or st[1] * sign > 280:
                res, tail = outcome(states, len(states) - 1, False), 6
        return res or outcome(states, len(states) - 1, False), frames, paths, released, press, strike_at

    shots, p = [], 0
    while len(shots) < n and p < 4 * n:
        timing = ("early", "late")[p % 2]
        by = 2 + p % 4 if timing == "early" else 2 + (p * 5) % 9
        ot.setup("top", P, R, p, rnd)
        vram = vram or genesis_vram(e)
        start = e.serialize()
        d = DIRS[direction(ot.R[0] - ot.P[0], ot.R[1] - ot.P[1])]
        p += 1
        found = attempt(start, d, by, timing, None)
        if found is None:
            breathe()
            continue
        seed = rnd.getrandbits(32)
        res, fr, pts, rel, press, strike = attempt(start, d, by, timing, seed, strike_at=found[2], film=True)
        hold = 15                                           # the set-up's last frame held a moment before the pass
        shots.append((res, [fr[0]] * hold + fr, [pts[0]] * hold + pts, rel + hold, press + hold, strike + hold))
        breathe()
    return case, shots


def tally(shots):
    return f"{sum(s[0] == 'GOAL' for s in shots)} of {len(shots)} in"


def clips_gif(case, shots, path):
    name, R, P, shp, sha, title, (g, n) = case
    rate = g / n
    goals = [s for s in shots if s[0] == "GOAL"]
    others = [s for s in shots if s[0] != "GOAL"]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
    rest = [s for s in goals if all(s is not q for q in pick)]    # too few misses: more goals to fill the four
    pick += r.sample(rest, min(4 - len(pick), len(rest)))
    r.shuffle(pick)
    cw, ch = pick[0][1][0].size
    pad, lab, head = 8, 26, 62
    W, H = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 14)
    lead = 20                                               # frames shown before the pass leaves
    span = max(len(s[1]) - max(0, s[3] - lead) for s in pick)
    frames = []
    for t in range(span):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"{100 * rate:.0f}% of struck one-timers go in here ({g} of {n} in the ratings run, "
                          f"Shot Power {shp} / Accuracy {sha}).", fill="#52606d", font=f2)
        d.text((pad, 42), "The game's own frames, top net, half speed, lined up on the pass.", fill="#52606d", font=f2)
        for i, (res, fr, _, rel, press, strike) in enumerate(pick):
            j = min(max(0, rel - lead) + t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j], (x, y))
            if j < rel:
                state, col = "passer has it", "#cbd2d9"
            elif j < press:
                state, col = "the pass", "#94a3b8"
            elif j < strike:
                state, col = "C: the swing", "#0ea5e9"
            elif (res == "GOAL" and j < len(fr) - 12) or (res != "GOAL" and j < len(fr) - 6):
                state, col = "one-timer", "#64748b"
            else:
                state, col = SHOWN[res], COL[res]
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 2), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def paths_gif(case, shots, path):
    """Every attempt from above, lined up on the strike, the net at the top."""
    name, R, P, shp, sha, title, (g, n) = case
    S, pad, head = 2.6, 14, 64
    x_lo, x_hi, y_lo, y_hi = -120, 120, 140, 282
    W, H = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20

    def Q(x, y):                                            # on the rink image
        return (x - x_lo) * S, (y_hi - y) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    before = min(s[5] for s in shots) + 1
    after = min(40, min(len(s[2]) - s[5] for s in shots))
    order = sorted(shots, key=lambda s: s[0] == "GOAL")
    frames = []

    def dot(d, c, col, r=3):
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col)
    for t in range(-before, after):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"Every attempt from above: {len(shots)} here, {tally(shots)}; the ratings run "
                          f"{100 * g / n:.0f}%.", fill="#52606d", font=f2)
        d.text((pad, 42), "Puck: grey on the pass, then orange goal, slate stopped. Black: the goalie and his track.",
               fill="#52606d", font=f2)
        rink = Image.new("RGB", (W - 2 * pad, H - 20 - head), "#eef6fb")
        d0, d = d, ImageDraw.Draw(rink)                     # drawn on the rink alone: shots wide off the top are cut
        gl = Q(0, 268)[1]
        d.line((0, gl, W, gl), fill="#c94040", width=2)
        a, b = Q(-20, 276), Q(20, 268)
        d.rectangle((a[0], a[1], b[0], b[1]), outline="#52606d", width=2)
        for s in order:
            res, _, pts, rel, press, strike = s
            i = min(max(strike + t, 0), len(pts) - 1)
            col = COL[res] if i >= strike else "#94a3b8"
            pk = [Q(*q[2]) for q in pts[:i + 1]]
            gk = [Q(*q[3]) for q in pts[:i + 1]]
            if len(gk) > 1:
                d.line(gk, fill="#9aa5b1", width=1)
            if len(pk) > 1:
                d.line(pk[:strike + 1], fill="#94a3b8", width=1)
                if i > strike:
                    d.line(pk[strike:], fill=col, width=2 if res == "GOAL" else 1)
            dot(d, Q(*pts[i][2]), col)
            dot(d, Q(*pts[i][3]), "#1f2933", 4)
        q = shots[0][2][0]
        for k in (0, 1):
            dot(d, Q(*q[k]), "#cbd2d9", 6)
        d.text((Q(*q[0])[0] - 22, Q(*q[0])[1] + 8), "passer", fill="#52606d", font=f2)
        d.text((Q(*q[1])[0] - 26, Q(*q[1])[1] + 8), "receiver", fill="#52606d", font=f2)
        img.paste(rink, (pad, head))
        d0.text((pad, H - 18), f"frame {t:+d} from the strike (half speed)", fill="#52606d", font=f2)
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
    names = sys.argv[3:]
    cases = [c for c in CASES if not names or c[0] in names]
    out_dir.mkdir(parents=True, exist_ok=True)
    with Pool(min(WORKERS, len(cases)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(c, n, out_dir) for c in cases]):
            print(*r, flush=True)
    json.dump([dict(name=c[0], title=c[5], goals=c[6][0], shots=c[6][1]) for c in cases],
              open(out_dir / "cases.json", "w"), indent=1)


if __name__ == "__main__":
    main()
