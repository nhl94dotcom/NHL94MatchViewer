"""Animated makes and misses from the maps' worthwhile spots: python animate.py OUT_DIR [N]
For each spot in SPOTS, N shots (default 120: one at each of the 120 moments, a fresh release seed each) played in the
game, each kept frame by frame. A sample this size wanders from the true rate, so the captions give a bigger sample's
(Genesis: the map's; SNES: 480 shots over the same 120 moments, since the SNES map's 16 moments a spot are too few) and
the clips show goals in that proportion. Two GIFs per spot:
- <name>_clips.gif: nine of the shots side by side, the game's own frames zoomed on the net, goals and saves in about
  the spot's real proportion, each labelled;
- <name>_fan.gif: all N shots at once from above, the puck's trail coloured by result (orange in, grey saved), the
  goalie each shot's dark dot.
Gentle mode (lowload.py): a few worker processes at below-normal priority."""
import json
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lowload import WORKERS, gentle

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
# name, system, net, shooter x, shooter y (from centre), shot, aim (d-pad), what it shows, its rate (see above)
SPOTS = [
    ("genesis_down_slapshot_top", "genesis", "top", 0, 150, "slap", 4,
     "Genesis, top net: slapshot holding Down, straight in, 118 units out", 0.430),
    ("genesis_down_slapshot_bottom", "genesis", "bottom", 0, 150, "slap", 4,
     "Genesis, bottom net: slapshot holding Down, straight in, 118 units out", 0.096),
    ("genesis_pad_stack", "genesis", "bottom", -60, 200, "wrist", 5,
     "Genesis, bottom net: wrist shot down-left, 68 out, 60 to the side (the early pad stack)", 0.338),
    ("genesis_shoulder_bobble", "genesis", "top", -110, 190, "wrist", 0,
     "Genesis, top net: high wrist shot from the far left boards, 78 out (the shoulder-save bobble)", 0.312),
    ("snes_lane_top", "snes", "top", -10, 180, "slap", 6,
     "SNES, top net: slapshot holding Left, 10 left of centre, 88 out (the lane)", 0.536),
    ("snes_lane_bottom", "snes", "bottom", 10, 150, "slap", 2,
     "SNES, bottom net: slapshot holding Right, 10 right of centre, 118 out (the lane)", 0.265),
    ("snes_mirror_top", "snes", "top", 10, 180, "slap", 2,
     "SNES, top net: the mirror shot, holding Right, 10 right of centre, 88 out", 0.017),
]
MAP_SHOTS = {"genesis": "the map: 800 launches at 120 moments",   # what each rate rests on
             "snes": "480 shots over 120 moments"}
CW, CH = 200, 120                     # crop of the game screen around the net (pixels)


def crop(img, at, top):
    cx, gy = at
    x0 = int(max(0, min(img.width - CW, cx - CW / 2)))
    y0 = int(max(0, min(img.height - CH, gy - 45 if top else gy - CH + 45)))
    return img.crop((x0, y0, x0 + CW, y0 + CH))


def play(spec, n):
    """n shots from the spot: [(goal?, [cropped frames], [states])]."""
    import goal_types as G
    from goal_frames import frame, net_on_screen
    gentle()
    name, system, net, x, y, kind, aim = spec[:7]
    G._init(system)
    o = G.S["o"]
    h = o.h[net]
    top = net == "top"
    sign = 1 if top else -1
    rnd = random.Random(zlib.crc32(name.encode()))
    shots, p = [], 0
    while len(shots) < n and p < 4 * n:
        o.setup(net, x, y, p, rnd)                    # a different moment each time (clock and settle cycles)
        p += 1
        pre = o.shoot(net, aim, G.KINDS[system][kind])
        if pre is None:
            continue
        for _ in range(1):
            seed = rnd.getrandbits(32)
            s0 = o.score0(net)
            img = frame(h, lambda: o.fire(net, pre, aim, seed))
            frames, states = [crop(img, net_on_screen(h.e, system, net), top)], [o.state(net)]
            goal, away, held, tail = None, 0, 0, 10
            for f in range(150):
                img = frame(h, lambda: o.step(net))
                st = o.state(net)
                frames.append(crop(img, net_on_screen(h.e, system, net), top))
                states.append(st)
                if goal is not None:
                    tail -= 1
                    if tail == 0:
                        break
                    continue
                if o.scored(net, s0):
                    goal, tail = True, 16
                    continue
                held = held + 1 if st[8] else 0
                away = away + 1 if st[4] * sign < 0 else 0
                if held >= 20 or away >= 4 or st[1] * sign > 280:
                    goal = False
            shots.append((bool(goal), frames, states))
            if len(shots) == n:
                break
    return spec, shots


def clips_gif(spec, shots, out):
    """Nine shots side by side, in about the spot's real proportion of goals."""
    system, title, rate = spec[1], spec[7], spec[8]
    goals = [s for s in shots if s[0]]
    saves = [s for s in shots if not s[0]]
    k = round(9 * rate)                              # the mix shown follows the full map's rate
    k = min(len(goals), max(k, 1 if goals else 0))
    pick = goals[:k] + saves[:9 - k]
    random.Random(1).shuffle(pick)
    Z, pad, lab, head = 2, 8, 30, 66
    W = 3 * CW * Z + 4 * pad
    H = head + 3 * (CH * Z + lab) + 4 * pad
    f1, f2, fb = ImageFont.truetype(FONTB, 20), ImageFont.truetype(FONT, 15), ImageFont.truetype(FONTB, 17)
    n_frames = max(len(s[1]) for s in pick)
    frames = []
    for t in range(n_frames):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 8), title, fill="#1f2933", font=f1)
        d.text((pad, 36), f"Overall {100 * rate:.0f}% of these go in ({MAP_SHOTS[system]}). Nine shots "
                          f"from this sample of {len(shots)}, {k} of them goals. Half speed.", fill="#52606d", font=f2)
        for i, (g, fr, _) in enumerate(pick):
            x = pad + (i % 3) * (CW * Z + pad)
            y = head + pad + (i // 3) * (CH * Z + lab + pad)
            img.paste(fr[min(t, len(fr) - 1)].resize((CW * Z, CH * Z), Image.NEAREST), (x, y))
            done = t >= len(fr) - 12
            col = ("#ea580c" if g else "#475569") if done else "#cbd2d9"
            d.rectangle((x, y + CH * Z, x + CW * Z - 1, y + CH * Z + lab - 4), fill=col)
            d.text((x + 8, y + CH * Z + 3), ("GOAL" if g else "SAVED") if done else "...", fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 30                       # hold the end a moment
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def fan_gif(spec, shots, out):
    """Every shot from above at once: trails coloured by result."""
    system, net, x, y, title, rate = spec[1], spec[2], spec[3], spec[4], spec[7], spec[8]
    top = net == "top"
    sg = 1 if top else -1
    x_lo, x_hi = min(-70, x - 15), max(70, x + 15)
    d_far = 268 - y + 8                               # distance in front of the goal line to show
    S = min(600 / (x_hi - x_lo), 520 / (d_far + 14))
    head, pad = 92, 20
    W = max(760, int((x_hi - x_lo) * S) + 2 * pad)
    x_lo -= (W - 2 * pad - (x_hi - x_lo) * S) / 2 / S          # centre the rink in a wider picture
    H = int((d_far + 14) * S) + head + pad + 30

    def P(px, py):                                    # as on the screen: the top net at the top
        d = 268 - sg * py                             # in front of the goal line
        sy = (14 + d) * S if top else (d_far - d) * S
        return pad + (px - x_lo) * S, head + sy
    f1, f2 = ImageFont.truetype(FONTB, 17), ImageFont.truetype(FONT, 14)
    n_goal = sum(s[0] for s in shots)
    T = min(90, max(len(s[2]) for s in shots))
    order = sorted(range(len(shots)), key=lambda i: shots[i][0])      # saves under, goals on top
    frames = []
    for t in range(T):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 10), title, fill="#1f2933", font=f1)
        d.text((pad, 36), f"{len(shots)} shots at once from above: orange went in ({n_goal}), grey saved; dark dots: "
                          f"the goalie. Overall: {100 * rate:.0f}%.", fill="#52606d", font=f2)
        d.text((pad, 58), "Shots that went exactly where aimed share one path, so many goals can look like one line.",
               fill="#52606d", font=f2)
        d.rectangle((pad, head, W - pad, H - 30), fill="#eef6fb")
        gl = P(0, sg * 268)[1]
        d.line((pad, gl, W - pad, gl), fill="#c94040", width=2)
        mouth = 20 if system == "genesis" else 17
        a, b = P(-mouth, sg * 268), P(mouth, sg * 276)
        d.rectangle((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), outline="#52606d")
        for i in order:
            g, _, st = shots[i]
            n = min(t + 1, len(st) - (17 if g else 10))   # the path up to the decision (the goal frame moves it)
            col = "#ea580c" if g else "#9aa5b1"
            pts = [P(s[0], s[1]) for s in st[:max(1, n)]]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2 if g else 1)
            c = pts[-1]
            d.ellipse((c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3), fill=col)
            gs = st[min(t, len(st) - 1)]
            gc = P(gs[5], gs[6])
            d.ellipse((gc[0] - 2, gc[1] - 2, gc[0] + 2, gc[1] + 2), fill="#1f2933")
        d.text((pad, H - 24), f"frame {t} after the release (shown at half speed)", fill="#52606d", font=f2)
        frames.append(img.quantize(colors=64, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def job(args):
    spec, n, out_dir = args
    t0 = time.time()
    spec, shots = play(spec, n)
    clips_gif(spec, shots, out_dir / f"{spec[0]}_clips.gif")
    fan_gif(spec, shots, out_dir / f"{spec[0]}_fan.gif")
    return spec[0], sum(s[0] for s in shots), len(shots), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    # a fresh process per spot (one emulator per process), at most WORKERS at once
    with Pool(min(WORKERS, len(SPOTS)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(s, n, out_dir) for s in SPOTS]):
            print(*r, flush=True)
    print("done", round(time.time() - t0), "s with", min(WORKERS, len(SPOTS)), "workers")
    json.dump([s[0] for s in SPOTS], open(out_dir / "spots.json", "w"))


if __name__ == "__main__":
    main()
