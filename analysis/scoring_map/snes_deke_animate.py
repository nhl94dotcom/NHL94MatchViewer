"""Animated SNES dekes (retail ROM): the user's recorded tries from the 2v2 game replayed as snes_deke_run.py's plan
"replay" plays them. python snes_deke_animate.py OUT_DIR [N] [names]
Each case is one try (period-clock key) at one net, by one hand, with one aim: N moments exactly as the run set them
up (the same random draws), each shot fired with the first of the run's release seeds and played out, the game's own
frames from 1.5 s before the shot to the result. The captions give the run's rate for that very set-up (24 moments x 4
seeds, read from RUNS/sdeke/snes_deke_replay.jsonl), the clips goals in about that proportion.
Two GIFs per case:
- <name>_clips.gif: four attempts side by side, the whole screen, each labelled with what is happening;
- <name>_paths.gif: every attempt at once from above, in the attacker's view (the net at the top), lined up on the
  release: the skater (grey), the puck (orange for a goal, slate for a stop) and the goalie (black, his track drawn).
Gentle mode (lowload.py)."""
import json
import random
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import snes_deke_run as D
import snes_harness as H
from lowload import WORKERS, breathe
from paths import RUNS

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
COL = {"GOAL": "#e8590c", "SAVE": "#334e68", "LOST": "#9aa5b1"}
SHOWN = {"GOAL": "goal", "SAVE": "no goal", "LOST": "lost it"}
# name, try, net, hand, aim, title
CASES = [
    ("snes_cut_down_righty", "P3-2:18", "bottom", "R", "played",
     "SNES cut, Down net, right-hander (your inputs, mirrored)"),
    ("snes_cut_up_lefty", "P3-2:18", "top", "L", "played",
     "SNES cut, Up net, left-hander (as you played it)"),
    ("snes_cut_far_out", "P3-4:02", "top", "L", "played",
     "SNES cut released too far out (about 20 ft)"),
    ("snes_deke_down_lefty", "P2-3:40", "bottom", "L", "played",
     "SNES deke from his left, Down net, left-hander"),
    ("snes_deke_up_lefty", "P3-4:51", "top", "L", "played",
     "SNES deke from his left, Up net, left-hander"),
]


def args_of(case):
    _name, key, net, hand, aim = case[:5]
    move, side = next((m, s) for k, m, s in D.TRIES if k == key)
    return ("replay", net, side, hand, key, move, 0, aim)


def run_rate(case):
    a = args_of(case)
    for line in open(RUNS / "sdeke" / "snes_deke_replay.jsonl"):
        r = json.loads(line)
        if tuple(r[k] for k in D.KEYS) == a:
            return (r["goals"] / D.SEEDS + r["carried"]) / r["moments"], r
    return None, None


def play(case, n):
    a = args_of(case)
    _move, net, side, hand, key, _kind, _z, aim = a
    D._init()
    h = D._h[net]
    e = h.e
    sg = 1 if net == "top" else -1
    r = D.recorded(key)
    fl = 1 if (sg > 0) == r["top"] else -1
    rnd = random.Random(zlib.crc32(json.dumps(a).encode()))     # the run's own draws, moment by moment
    from goal_frames import grab
    run, film, on = e.run, [[], []], [False]
    S, G, P = H.o(H.SHOOTER), H.o(H.GOALIE), H.o(H.PUCK)

    def at(k):                                               # attacker's view: across, toward the net (+ up)
        return sg * h.sw(H.XPOS + k), sg * h.sw(H.YPOS + k)

    def filmed(k=1, hold=None):
        e.want_frame = on[0]
        run(k, hold=hold) if hold is not None else run(k)
        e.want_frame = False
        if on[0]:
            film[0].append(grab(e).copy())
            film[1].append((at(S), at(P), at(G)))
    e.run = filmed
    setup = h.setup

    def quiet_setup(*q, **kw):
        on[0] = False
        setup(*q, **kw)
        on[0] = True
    h.setup = quiet_setup
    shots = []
    for p in range(n):
        film[0], film[1] = [], []
        out, pre, last, _gp = D.approach(h, r, fl, hand, side, sg, aim, p, rnd)
        if out == "shot":
            seeds = [rnd.getrandbits(32) for _ in range(D.SEEDS)]
            film[0].pop(), film[1].pop()                     # the release frame is played again by fire
            rel = len(film[0])
            h.fire(pre, D.screen_dir(last), seeds[0])
            q, _f = h.decide()
            res = "GOAL" if q else "SAVE"
        else:
            rel = len(film[0])
            res = "GOAL" if out == "carried" else "LOST"
        for _ in range(12 if res == "GOAL" else 6):
            h.park(keep_shooter=False)
            e.run(1)
        on[0] = False
        pts = film[1]
        for i in range(1, len(pts)):                         # after a goal the game puts everyone back: hold still
            if abs(pts[i][0][0] - pts[i - 1][0][0]) + abs(pts[i][0][1] - pts[i - 1][0][1]) > 20:
                pts[i:] = [pts[i - 1]] * (len(pts) - i)
                break
        shots.append((res, film[0], pts, rel))
        breathe()
    h.setup, e.run = setup, run
    return case, shots


def tally(shots):
    return f"{sum(s[0] == 'GOAL' for s in shots)} of {len(shots)} in"


def clips_gif(case, shots, rate, path):
    title = case[5]
    goals = [s for s in shots if s[0] == "GOAL"]
    others = [s for s in shots if s[0] != "GOAL"]
    r = random.Random(1)
    k = min(len(goals), max(round(4 * rate), 1 if goals and rate > 0 else 0))
    pick = r.sample(goals, k) + r.sample(others, min(len(others), 4 - k))
    rest = [s for s in goals if all(s is not q for q in pick)]
    pick += r.sample(rest, min(4 - len(pick), len(rest)))
    r.shuffle(pick)
    cw, ch = pick[0][1][0].size
    pad, lab, head = 8, 26, 62
    W, H_ = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 14)
    lead = 90
    span = max(len(s[1]) - max(0, s[3] - lead) for s in pick)
    frames = []
    for t in range(span):
        img = Image.new("RGB", (W, H_), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), f"{100 * rate:.0f}% go in at this set-up in the run (24 moments x 4 release seeds), with "
                          f"your recorded d-pad and A.", fill="#52606d", font=f2)
        d.text((pad, 42), f"The game's own frames, {'Down' if case[2] == 'bottom' else 'Up'} net, half speed, "
                          "lined up on the shot.", fill="#52606d", font=f2)
        for i, (res, fr, _, rel) in enumerate(pick):
            j = min(max(0, rel - lead) + t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j], (x, y))
            if j < rel:
                state, col = "skating in", "#94a3b8"
            elif (res == "GOAL" and j < len(fr) - 12) or (res != "GOAL" and j < len(fr) - 6):
                state, col = "the shot", "#0ea5e9"
            else:
                state, col = SHOWN[res], COL[res]
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 8, y + ch + 2), state, fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def paths_gif(case, shots, rate, path):
    """Every attempt from above, lined up on the release, the net at the top (attacker's view)."""
    title = case[5]
    S, pad, head = 2.4, 14, 64
    x_lo, x_hi, y_lo, y_hi = -120, 120, 110, 284
    W, H_ = int((x_hi - x_lo) * S) + 2 * pad, int((y_hi - y_lo) * S) + head + pad + 20

    def Q(x, y):
        return (x - x_lo) * S, (y_hi - y) * S
    f1, f2 = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12)
    before = min(90, min(s[3] for s in shots))
    after = min(40, min(len(s[2]) - s[3] for s in shots))
    order = sorted(shots, key=lambda s: s[0] == "GOAL")
    frames = []

    def dot(d, c, col, r=3):
        d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col)
    for t in range(-before, after):
        img = Image.new("RGB", (W, H_), "white")
        d0 = ImageDraw.Draw(img)
        d0.text((pad, 6), title, fill="#1f2933", font=f1)
        d0.text((pad, 26), f"Every attempt from above: {len(shots)} here, {tally(shots)}; the run {100 * rate:.0f}%.",
                fill="#52606d", font=f2)
        d0.text((pad, 42), "Grey: the skater and his track. Puck: orange goal, slate stopped. Black: the goalie and his "
                           "track.", fill="#52606d", font=f2)
        rink = Image.new("RGB", (W - 2 * pad, H_ - 20 - head), "#eef6fb")
        d = ImageDraw.Draw(rink)
        gl = Q(0, 268)[1]
        d.line((0, gl, W, gl), fill="#c94040", width=2)
        a, b = Q(-20, 276), Q(20, 268)
        d.rectangle((a[0], a[1], b[0], b[1]), outline="#52606d", width=2)
        for res, _, pts, rel in order:
            i = min(max(rel + t, 0), len(pts) - 1)
            col = COL[res] if i >= rel else "#94a3b8"
            sk = [Q(*q[0]) for q in pts[:i + 1]]
            gk = [Q(*q[2]) for q in pts[:i + 1]]
            if len(gk) > 1:
                d.line(gk, fill="#9aa5b1", width=1)
                d.line(sk, fill="#cbd2d9", width=1)
            if i >= rel and res != "LOST":
                pk = [Q(*q[1]) for q in pts[rel:i + 1]]
                if len(pk) > 1:
                    d.line(pk, fill=col, width=2 if res == "GOAL" else 1)
                dot(d, Q(*pts[i][1]), col)
            dot(d, Q(*pts[i][0]), "#9aa5b1", 4)
            dot(d, Q(*pts[i][2]), "#1f2933", 4)
        img.paste(rink, (pad, head))
        d0.text((pad, H_ - 18), f"frame {t:+d} from the shot (half speed)", fill="#52606d", font=f2)
        frames.append(img.quantize(colors=48, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 40
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def job(a):
    case, n, out_dir = a
    t0 = time.time()
    rate, _row = run_rate(case)
    case, shots = play(case, n)
    clips_gif(case, shots, rate, out_dir / f"{case[0]}_clips.gif")
    paths_gif(case, shots, rate, out_dir / f"{case[0]}_paths.gif")
    return case[0], tally(shots), f"run {100 * rate:.0f}%", round(time.time() - t0)


def main():
    out_dir = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
    names = sys.argv[3:]
    cases = [c for c in CASES if not names or c[0] in names]
    out_dir.mkdir(parents=True, exist_ok=True)
    with Pool(min(WORKERS, len(cases)), maxtasksperchild=1) as pool:
        for r in pool.imap_unordered(job, [(c, n, out_dir) for c in cases]):
            print(*r, flush=True)
    json.dump([dict(name=c[0], title=c[5], rate=run_rate(c)[0]) for c in cases], open(out_dir / "cases.json", "w"),
              indent=1)


if __name__ == "__main__":
    main()
