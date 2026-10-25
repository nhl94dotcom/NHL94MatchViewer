"""Animated makes and misses from the maps' worthwhile spots: python animate.py OUT_DIR [N] [names]
For each spot in SPOTS, N shots (default 120: one at each of the 120 moments, a fresh release seed each) played in the
game, each kept frame by frame. A sample this size wanders from the true rate, so the captions give a bigger sample's
(Genesis: the map's; SNES: 480 shots over the same 120 moments, since the SNES map's 16 moments a spot are too few) and
the clips show goals in that proportion. The shooter stays on the ice after the release (the map parks him): on the
Genesis that changes nothing, but on the SNES it shifts which frames the game's loop skips, and the lane puck passes at
the edge of the goalie's body box, so the bottom-net lane spot scores 20.4% with him there against 26.5% without
(PROJECT_NOTES); the SNES rates here are measured with him on the ice. Two GIFs per spot:
- <name>_clips.gif: nine of the shots side by side, the game's own frames from the wind-up on, cropped to the shooter
  and the net, goals in about the spot's real proportion, each labelled with what happened (GOAL, SAVED, POST, MISSED);
- <name>_fan.gif: all N shots at once from above, the puck's trail coloured by result, the shooter's spot marked, the
  goalie each shot's dark dot.
Gentle mode (lowload.py): two worker processes at idle priority, resting as long as they work."""
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
# name, system, net, shooter x, shooter y (from centre), shot, aim (d-pad), what it shows, its rate (see above);
# optionally the shooter's (Shot Power, Shot Accuracy) roster steps and what the rate rests on (the ratings runs)
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
     "SNES, top net: slapshot holding Left, 10 left of centre, 88 out (the lane)", 0.538),
    ("snes_lane_bottom", "snes", "bottom", 10, 150, "slap", 2,
     "SNES, bottom net: slapshot holding Right, 10 right of centre, 118 out (the lane)", 0.204),
    ("snes_mirror_top", "snes", "top", 10, 180, "slap", 2,
     "SNES, top net: the mirror shot, holding Right, 10 right of centre, 88 out", 0.008),
]
# the slapshot's power threshold (SCORING_MAP "Every Shot Power and Accuracy"): the far post from the middle, 36 ft
RATED = [
    (f"genesis_slap_{p}_{a}", "genesis", "top", 0, 160, "slap", 6,
     f"Genesis, top net: slapshot at the far post from the middle, 36 ft, Shot Power {p} / Accuracy {a}", r, (p, a),
     "the ratings run: 400 launches at 120 moments")
    for p, a, r in ((3, 4, 0.10), (4, 4, 0.58), (6, 6, 0.72))]
MAP_SHOTS = {"genesis": "the map: 800 launches at 120 moments",   # what each rate rests on
             "snes": "480 shots over 120 moments, the shooter left on the ice"}
COL = {"GOAL": "#ea580c", "SAVED": "#475569", "POST": "#7c3aed", "MISSED": "#94a3b8"}
FAN = {"GOAL": "#ea580c", "SAVED": "#9aa5b1", "POST": "#7c3aed", "MISSED": "#cbd5e1"}


def box(spec, at, img):
    """The part of the screen with the net and the shooter (one game unit is one pixel on both systems), placed by the
    camera this frame (at = where the middle of the goal line is drawn)."""
    net, x, y = spec[2], spec[3], spec[4]
    cx, gy = at
    out = 268 - y                                     # the shooter's distance from the goal line
    x_lo, x_hi = min(-55, x - 35), max(55, x + 35)
    y_lo, y_hi = (gy - 38, gy + out + 28) if net == "top" else (gy - out - 28, gy + 38)
    w, h = min(img.width, x_hi - x_lo), min(img.height, y_hi - y_lo)
    x0 = int(max(0, min(img.width - w, cx + x_lo)))
    y0 = int(max(0, min(img.height - h, y_lo)))
    return img.crop((x0, y0, x0 + int(w), y0 + int(h)))


def outcome(states, k, goal):
    """GOAL, or what stopped it: SAVED (the goalie held it or it came off him), POST, MISSED (wide, over, off the boards
    or the outside of the net)."""
    if goal:
        return "GOAL"
    path = states[:k + 1]
    for a, b in zip(path, path[1:]):
        if b[8]:
            return "SAVED"
        if abs(b[3] - a[3]) + abs(b[4] - a[4]) > 1500:
            dg = ((a[0] - a[5]) ** 2 + (a[1] - a[6]) ** 2) ** 0.5
            if 16 <= abs(a[0]) <= 25 and 250 <= abs(a[1]) <= 272 and dg > 18:   # beyond any goalie's reach (18)
                return "POST"
            if dg < 32:                                # his body, stick or glove
                return "SAVED"
            return "MISSED"
    return "MISSED"


def play(spec, n):
    """n shots from the spot: [(outcome, [cropped frames from the wind-up on], [states after the release], the
    decision's index in the states, wind-up frames)]."""
    import goal_types as G
    from goal_frames import frame, grab, net_on_screen, genesis_vram, hide_genesis_hud
    from snes_harness import DIRPAD
    gentle()
    name, system, net, x, y, kind, aim = spec[:7]
    G._init(system)
    o = G.S["o"]
    h = o.h[net]
    e = h.e
    sign = 1 if net == "top" else -1
    hold = G.KINDS[system][kind]
    button = "C" if system == "genesis" else "A"
    vram = genesis_vram(e) if system == "genesis" else None

    def clean():                                      # the Genesis clock and score boxes off the next frame drawn
        if vram is not None:
            hide_genesis_hud(e, vram)
    rnd = random.Random(zlib.crc32(name.encode()))

    def step():                                       # as the map's play-out, but the shooter stays where he shot
        clean()
        h.park(keep_shooter=True)                     # (the map parks him too; he's far from the puck by then)
        e.run(1)
    shots, p = [], 0
    while len(shots) < n and p < 4 * n:
        o.setup(net, x, y, p, rnd)                    # a different moment each time (clock and settle cycles)
        if len(spec) > 9:
            from mapper import set_ratings
            set_ratings(h, 5 * spec[9][0], 5 * spec[9][1])
        p += 1
        settled = e.serialize()
        if o.shoot(net, aim, hold) is None:           # no shot, or not a real one (the SNES validity test)
            continue
        e.unserialize(settled)                        # the wind-up again, this time keeping its frames
        windup, pre = [], None
        n0 = e.w(0xE010)                              # Genesis: the test ROM's doshot count
        for f in range(90):
            clean()
            st = e.serialize()
            h.park()
            e.want_frame = True
            e.run(1, hold=([button] if f < hold else []) + DIRPAD[aim])
            e.want_frame = False
            released = (e.w(0xE010) != n0) if system == "genesis" else bool(e.w(0x0AD9) & 0x8000)
            if released:
                pre = st                              # the state before the release frame
                break
            img = grab(e)
            windup.append(box(spec, net_on_screen(e, system, net, img), img))
        if pre is None:
            continue
        seed = rnd.getrandbits(32)
        s0 = o.score0(net)
        img = frame(h, lambda: o.fire(net, pre, aim, seed))   # pre was saved with the boxes already blanked
        frames, states = windup + [box(spec, net_on_screen(e, system, net, img), img)], [o.state(net)]
        goal, k, away, held, tail = None, None, 0, 0, 10
        for f in range(150):
            img = frame(h, step)
            st = o.state(net)
            frames.append(box(spec, net_on_screen(e, system, net, img), img))
            states.append(st)
            if goal is not None:
                tail -= 1
                if tail == 0:
                    break
                continue
            if o.scored(net, s0):
                goal, k, tail = True, len(states) - 2, 16      # the goal frame itself has the puck moved already
                continue
            held = held + 1 if st[8] else 0
            away = away + 1 if st[4] * sign < 0 else 0
            if held >= 20 or away >= 4 or st[1] * sign > 280:
                goal, k = False, len(states) - 1
        if k is None:
            goal, k = False, len(states) - 1
        shots.append((outcome(states, k, goal), frames, states, k, len(windup)))
        breathe()
    return spec, shots


def tally(shots):
    c = {r: sum(s[0] == r for s in shots) for r in COL}
    return ", ".join(f"{c[r]} {w}" for r, w in (("GOAL", "goals"), ("SAVED", "saved"), ("POST", "off the post"),
                                                 ("MISSED", "missed the net")) if c[r])


def clips_gif(spec, shots, out):
    """Nine shots side by side, from the wind-up to the end, goals in about the spot's real proportion."""
    system, title, rate = spec[1], spec[7], spec[8]
    goals = [s for s in shots if s[0] == "GOAL"]
    others = [s for s in shots if s[0] != "GOAL"]
    r = random.Random(1)
    k = round(9 * rate)                              # the mix shown follows the spot's real rate
    k = min(len(goals), max(k, 1 if goals else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 9 - k))
    r.shuffle(pick)
    cw, ch = pick[0][1][0].size
    Z = min(2.0, 400 / cw, 380 / ch)
    zw, zh = int(cw * Z), int(ch * Z)
    pad, lab, head = 8, 30, 76
    W = max(3 * zw + 4 * pad, 1000)
    H = head + 3 * (zh + lab) + 4 * pad
    x_off = (W - (3 * zw + 4 * pad)) // 2
    f1, f2, fb = ImageFont.truetype(FONTB, 20), ImageFont.truetype(FONT, 15), ImageFont.truetype(FONTB, 17)
    n_frames = max(len(s[1]) for s in pick)
    frames = []
    for t in range(n_frames):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 8), title, fill="#1f2933", font=f1)
        basis = spec[10] if len(spec) > 10 else MAP_SHOTS[system]
        d.text((pad, 34), f"Overall {100 * rate:.0f}% of these go in ({basis}).", fill="#52606d", font=f2)
        d.text((pad, 52), f"This sample of {len(shots)}: {tally(shots)}. Nine shown, from the wind-up, at half speed.",
               fill="#52606d", font=f2)
        for i, (res, fr, _, kk, nw) in enumerate(pick):
            x = x_off + pad + (i % 3) * (zw + pad)
            y = head + pad + (i // 3) * (zh + lab + pad)
            img.paste(fr[min(t, len(fr) - 1)].resize((zw, zh), Image.NEAREST), (x, y))
            done = t >= nw + kk
            d.rectangle((x, y + zh, x + zw - 1, y + zh + lab - 4), fill=COL[res] if done else "#cbd2d9")
            d.text((x + 8, y + zh + 3), res if done else ("wind-up" if t < nw else "..."), fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 30                       # hold the end a moment
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def fan_gif(spec, shots, out):
    """Every shot from above at once: trails coloured by result, the shooter's spot marked."""
    system, net, x, y, title, rate = spec[1], spec[2], spec[3], spec[4], spec[7], spec[8]
    top = net == "top"
    sg = 1 if top else -1
    x_lo, x_hi = min(-70, x - 20), max(70, x + 20)
    d_far = 268 - y + 16                              # distance in front of the goal line to show
    S = min(600 / (x_hi - x_lo), 520 / (d_far + 14))
    head, pad = 92, 20
    W = max(860, int((x_hi - x_lo) * S) + 2 * pad)
    x_lo -= (W - 2 * pad - (x_hi - x_lo) * S) / 2 / S          # centre the rink in a wider picture
    H = int((d_far + 14) * S) + head + pad + 30

    def P(px, py):                                    # as on the screen: the top net at the top
        d = 268 - sg * py                             # in front of the goal line
        sy = (14 + d) * S if top else (d_far - d) * S
        return pad + (px - x_lo) * S, head + sy
    f1, f2 = ImageFont.truetype(FONTB, 17), ImageFont.truetype(FONT, 14)
    T = min(90, max(s[3] + 8 for s in shots))
    rank = {"MISSED": 0, "SAVED": 1, "POST": 2, "GOAL": 3}
    order = sorted(range(len(shots)), key=lambda i: rank[shots[i][0]])   # goals drawn on top
    frames = []
    for t in range(T):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 10), title, fill="#1f2933", font=f1)
        d.text((pad, 36), f"{len(shots)} shots at once from above: {tally(shots)}. Overall: {100 * rate:.0f}%.",
               fill="#52606d", font=f2)
        d.text((pad, 58), "Orange in, grey saved, purple off the post, pale missed; dark dots: the goalie. Shots that "
                          "went exactly where aimed share one path.", fill="#52606d", font=f2)
        d.rectangle((pad, head, W - pad, H - 30), fill="#eef6fb")
        gl = P(0, sg * 268)[1]
        d.line((pad, gl, W - pad, gl), fill="#c94040", width=2)
        mouth = 20 if system == "genesis" else 17
        a, b = P(-mouth, sg * 268), P(mouth, sg * 276)
        d.rectangle((min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), outline="#52606d")
        sc = P(x, sg * y)                             # the shooter, standing where he shoots from
        d.rectangle((sc[0] - 6, sc[1] - 6, sc[0] + 6, sc[1] + 6), fill="#1f2933")
        d.text((sc[0] + 10, sc[1] - 8), "shooter", fill="#1f2933", font=f2)
        for i in order:
            res, _, st, k, _ = shots[i]
            col = FAN[res]
            pts = [P(s[0], s[1]) for s in st[:min(t, k) + 1]]
            if len(pts) > 1:
                d.line(pts, fill=col, width=2 if res == "GOAL" else 1)
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
    return spec[0], tally(shots), len(shots), round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    spots = [s for s in SPOTS + RATED if s[0] in only] if only else SPOTS
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    # a fresh process per spot (one emulator per process), at most WORKERS at once
    with Pool(min(WORKERS, len(spots)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(s, n, out_dir) for s in spots]):
            print(*r, flush=True)
    print("done", round(time.time() - t0), "s with", min(WORKERS, len(spots)), "workers")
    json.dump([s[0] for s in spots], open(out_dir / "spots.json", "w"))


if __name__ == "__main__":
    main()
