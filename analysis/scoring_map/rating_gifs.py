"""GIFs of what a rating step does, played in the game (Genesis test ROM; 2026-11-11, for docs/RATING_VALUES.md).

python rating_gifs.py OUT_DIR shots [N] [slap|wrist]  Shot Power 1-6 side by side, Shot Accuracy 4: a slapshot
                                            (the middle, 36 ft, at the far post) and a wrist shot (the bottom net's early
                                            pad stack spot: wrist shots at a set goalie hardly score elsewhere). Each power plays the same N attempts (the same moments and
                                            release seeds: animate.play with one name for all six); the panels show the
                                            first attempt, from the wind-up, with the puck's speed and the result, and
                                            the captions each power's goals over the N.
python rating_gifs.py OUT_DIR onetimer [N]  One-timer Shot Accuracy 1-6, Shot Power 4: the same pass across (receiver 18 ft
                                            out, 10 ft to the side), the same press and the same strike, N release
                                            seeds; the goalie is taken off the ice the frame after the strike, so where
                                            each puck crosses the goal line is the aim and its scatter alone. A view of
                                            the goal mouth: one dot a shot, orange exact (within 2 units of the aim
                                            point), slate scattered; then the same strikes with the goalie left in, for
                                            the goals.
python rating_gifs.py OUT_DIR skating       Speed 1-6 and Agility 1-6 (the others as the test skater's: Weight 9, Agility
                                            and Speed working 18), the pad-1 skater without the puck (a person's carrier
                                            accelerates at half rate): a sprint from a standstill up the middle for 2.5
                                            s (real), and a turn: up to top speed, then Down held. Drawn from above as
                                            six lanes, one run each, in real time;
                                            the turn starts each skater at his own top speed, Down held at once.

Ratings are working values (roster x 5), no hot / cold. Gentle mode (lowload.py)."""
import math
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from lowload import breathe, gentle

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
COL = {"GOAL": "#ea580c", "SAVED": "#475569", "POST": "#7c3aed", "MISSED": "#94a3b8"}
UNITS_PER_FT = 3.08            # 200 units = 65 ft
MPH = 295                      # puck speed units per mph (23,000 is about 78 mph)
SKATE_MPH = 286                # skater speed units per mph (9,162 is about 32 mph)


def f(size, bold=False):
    return ImageFont.truetype(FONTB if bold else FONT, size)


# ---------------------------------------------------------------- shots

SHOTS = [("slapshot", "slap", "top", 0, 160, 6, "Slapshot from the middle, 36 ft out, at the far post"),
         # a wrist shot at a set goalie hardly scores anywhere (GENESIS_SHOOTING 4.10); this spot does (SCORING_GENESIS:
         # the early pad stack, 34% for the test shooter)
         ("wrist shot", "wrist", "bottom", -60, 200, 5, "Wrist shot down-left, 22 ft out and 20 ft to the side (bottom net)")]


def shots(out, n):
    import animate as A
    for label, kind, net, x, y, aim, title in SHOTS:
        if len(sys.argv) > 4 and kind not in sys.argv[4:]:
            continue
        runs = []
        for p in range(1, 7):
            spec = ("rating_gif_" + kind, "genesis", net, x, y, kind, aim, title, 0.0, (p, 4), "")
            _, got = A.play(spec, n)
            runs.append((p, got))
            breathe()
        compose_shots(out / f"shot_power_{kind}.gif", label, title, runs)


def puck_mph(states):
    s = states[0]
    return math.hypot(s[3], s[4]) / MPH


def compose_shots(path, label, title, runs):
    # the attempt shown: the one whose results best match each power's own rate (goal where that power scores half the
    # time or more), so the panels look like the rates; the same attempt (moment and seeds) in every panel
    n = min(len(got) for _, got in runs)
    rate = [sum(s[0] == "GOAL" for s in got[:n]) / n for _, got in runs]
    pick = max(range(n), key=lambda j: (sum((runs[i][1][j][0] == "GOAL") == (rate[i] >= 0.5) for i in range(6)), -j))
    first = [(p, got[pick]) for p, got in runs]
    cw, ch = first[0][1][1][0].size
    Z = min(2.6, 400 / cw, 320 / ch)
    zw, zh = int(cw * Z), int(ch * Z)
    pad, lab, head = 8, 66, 88
    W, H = 3 * zw + 4 * pad, head + 2 * (zh + lab) + 3 * pad
    W = max(W, 980)
    x_off = (W - (3 * zw + 4 * pad)) // 2
    n_frames = max(len(s[1]) for _, s in first)
    frames = []
    for t in range(n_frames):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), f"Shot Power 1 to 6: {title}", fill="#1f2933", font=f(19, True))
        d.text((pad, 32), "Shot Accuracy 4 for all six. The same moment and the same random draws in every panel: only "
               "Shot Power differs. Half speed.", fill="#52606d", font=f(14))
        d.text((pad, 50), f"Each power took the same {n} attempts; the one shown is the attempt whose results best match "
               "each power's own goal rate.", fill="#52606d", font=f(14))
        for i, (p, (res, fr, states, k, nw)) in enumerate(first):
            goals = round(rate[i] * n)
            x = x_off + pad + (i % 3) * (zw + pad)
            yy = head + pad + (i // 3) * (zh + lab + pad)
            img.paste(fr[min(t, len(fr) - 1)].resize((zw, zh), Image.NEAREST), (x, yy))
            released = t >= nw
            done = t >= nw + k
            d.rectangle((x, yy + zh, x + zw - 1, yy + zh + lab - 4), fill=COL[res] if done else "#cbd2d9")
            d.text((x + 8, yy + zh + 2), f"Shot Power {p} (working {5 * p})", fill="white", font=f(15, True))
            d.text((x + 8, yy + zh + 22), (f"{puck_mph(states):.0f} mph" if released else "winding up") +
                   (f"   {res}" if done else ""), fill="white", font=f(14, True))
            d.text((x + 8, yy + zh + 42), f"{goals} goals in {n} attempts", fill="white", font=f(13))
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 45
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)
    print("wrote", path)


# ---------------------------------------------------------------- one-timer accuracy

def onetimer(out, n):
    gentle()
    from ot_harness import OneTimer, PASSER, RECEIVER
    import random
    ot = OneTimer("genesis")
    e, s = ot.e, ot.s
    R, P = (30, 210), (-30, 210)
    ot.setup("top", P, R, 0, random.Random(1))
    pre = None
    for by in (4, 6, 8, 3, 10):
        press, why = ot.pass_to_press("late", by=by)
        if press is not None:
            pre, why = ot.swing(press, None)
            if pre is not None:
                break
    if pre is None:
        raise SystemExit(f"no one-timer: {why}")
    res = {}
    for a in range(1, 7):
        dots, goals = [], 0
        for k in range(n):
            for keep_goalie in (False, True):
                e.unserialize(pre)
                e.setb(s.rec(RECEIVER) + 0x6C, 20)
                e.setb(s.rec(RECEIVER) + 0x6D, 5 * a)
                ot.strike(e.serialize(), None, 1000 + 7919 * k)
                aim = e.w(0xBEDC)
                if keep_goalie:
                    goals += ot.play_out() == "GOAL"
                    continue
                cross, last = None, None
                for fr in range(90):
                    s.put(s.GOALIE, 150, 200)             # off to the side, out of the way
                    ot.run()
                    x, y, z = (e.w(s.rec(s.PUCK) + o) for o in (0, 0x14, 0x18))
                    x, y, z = [v - 65536 if v > 32767 else v for v in (x, y, z)]
                    if y >= 264:                          # the goal line: where it crossed, between the two frames
                        if last and y != last[1]:
                            q = (264 - last[1]) / (y - last[1])
                            x, z = last[0] + q * (x - last[0]), last[2] + q * (z - last[2])
                        cross = (x, z)
                        break
                    last = (x, y, z)
                if cross:
                    dots.append((cross, aim))
        res[a] = (dots, goals)
        print(f"accuracy {a}: {len(dots)} crossings, {goals}/{n} goals with the goalie in", flush=True)
        breathe()
    compose_onetimer(out / "onetimer_accuracy.gif", res, n)


AIM_POINT = {0: (0, 12), 1: (16, 12), 2: (16, 6), 3: (16, 0), 4: (0, 0), 5: (-16, 0), 6: (-16, 6), 7: (-16, 12), 8: (0, 6)}


def compose_onetimer(path, res, n):
    S = 5                                   # pixels a game unit
    pw, ph = 70 * S, 34 * S                 # a panel: x -35..35, height 0..34
    pad, lab, head = 14, 66, 96
    W, H = 3 * pw + 4 * pad, head + 2 * (ph + lab + pad) + pad
    frames = []
    for t in list(range(0, n + 1)) + [n] * 60:
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), "One-timer Shot Accuracy 1 to 6: where the same one-timer crosses the goal line", fill="#1f2933",
               font=f(19, True))
        d.text((pad, 32), f"Pass across, receiver 18 ft out and 10 ft to the side, Shot Power 4. {n} strikes a level, the "
               f"same {n} random draws at each. The goalie taken off after", fill="#52606d", font=f(14))
        d.text((pad, 50), "the strike, so this is the aim and its scatter alone. Orange: exactly on the aim point. Slate: "
               "scattered (only ever upward, and to either side).", fill="#52606d", font=f(14))
        d.text((pad, 68), "Goals: the same strikes with the goalie left in.", fill="#52606d", font=f(14))
        for i, a in enumerate(range(1, 7)):
            dots, goals = res[a]
            x0 = pad + (i % 3) * (pw + pad)
            y0 = head + pad + (i // 3) * (ph + lab + pad)
            X = lambda gx: x0 + (gx + 35) * S
            Y = lambda gz: y0 + ph - gz * S
            d.rectangle((x0, y0, x0 + pw, y0 + ph), fill="#f1f5f9")
            d.line((x0, Y(0), x0 + pw, Y(0)), fill="#94a3b8", width=2)        # the ice
            for px in (-20, 20):                  # a goal: the puck's centre within 20 and under 13 (13.3)
                d.line((X(px), Y(0), X(px), Y(13)), fill="#dc2626", width=3)
            d.line((X(-20), Y(13), X(20), Y(13)), fill="#dc2626", width=3)    # the crossbar
            if dots:
                ax, az = AIM_POINT.get(dots[0][1], (0, 6))
                d.ellipse((X(ax) - 7, Y(az) - 7, X(ax) + 7, Y(az) + 7), outline="#1f2933", width=2)
            exact = 0
            for (cx, cz), aim in dots[:t]:
                ax, az = AIM_POINT.get(aim, (0, 6))
                ex = abs(cx - ax) <= 2 and abs(cz - az) <= 2
                exact += ex
                cz = min(cz, 33)
                cx = max(-35, min(35, cx))
                d.ellipse((X(cx) - 4, Y(cz) - 4, X(cx) + 4, Y(cz) + 4), fill="#ea580c" if ex else "#475569")
            shown = min(t, len(dots))
            in_net = sum(1 for (cx, cz), _ in dots[:t] if abs(cx) <= 20 and cz < 13)
            d.text((x0, y0 + ph + 4), f"Accuracy {a} (working {5 * a})", fill="#1f2933", font=f(15, True))
            d.text((x0, y0 + ph + 24), f"{exact} of {shown} exact (formula {100 * (5 * a + 1) / (5 * a + 16):.0f}%), "
                   f"{in_net} on target", fill="#1f2933", font=f(13))
            d.text((x0, y0 + ph + 42), f"with the goalie in: {goals} goals of {n}", fill="#52606d", font=f(13))
        frames.append(img.quantize(colors=64, dither=Image.Dither.NONE))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=60, loop=0, optimize=True)
    print("wrote", path)


# ---------------------------------------------------------------- skating

def skate_run(h, wgt, agl, spd, frames_up, turn_after=None, start_speed=0):
    from harness import rec, SHOOTER, PUCK, PUCKC
    e = h.e
    e.unserialize(h.base)
    r = rec(SHOOTER)
    e.setb(r + 0x67, wgt)
    e.setb(r + 0x68, agl)
    e.setb(r + 0x69, spd)

    def hold_puck_away():
        e.setw(PUCKC, 0xFFFF)
        e.setw(PUCK, -100)
        e.setw(PUCK + 0x14, -250)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(PUCK + off, 0)
    for _ in range(3):
        hold_puck_away()
        e.setw(r, 0)
        e.setw(r + 0x14, -200)
        e.setw(r + 0x28, 0)
        e.setw(r + 0x2A, start_speed)
        h.park(keep_shooter=True)
        e.run(1, hold=["UP"] if start_speed else [])
    track = []
    for fr in range(frames_up):
        h.park(keep_shooter=True)
        hold_puck_away()
        pad = ["UP"] if turn_after is None or fr < turn_after else ["DOWN"]
        e.run(1, hold=pad)
        y = e.w(r + 0x14)
        v = e.w(r + 0x2A)
        track.append((y - 65536 if y > 32767 else y, v - 65536 if v > 32767 else v))
    return track


def skating(out):
    gentle()
    from harness import Harness
    from paths import STATE_TOP
    h = Harness(state=STATE_TOP)
    WGT, BASE = 72, 18
    scenes = []
    for name, which in (("speed", "Speed"), ("agility", "Agility")):
        sprint, turn = [], []
        for p in range(1, 7):
            agl, spd = (BASE, 5 * p) if name == "speed" else (5 * p, BASE)
            sprint.append((p, skate_run(h, WGT, agl, spd, 150)))
            cap = (20 + min(spd + 2, 30) // 2) * 275          # his top speed (GENESIS_MECHANICS 3.1)
            turn.append((p, skate_run(h, WGT, agl, spd, 150, turn_after=0, start_speed=cap)))
            breathe()
        scenes.append((name, which, sprint, turn))
    for name, which, sprint, turn in scenes:
        other = "Agility" if which == "Speed" else "Speed"
        lanes_gif(out / f"skating_{name}_sprint.gif",
                  f"{which} 1 to 6: a sprint from a standstill",
                  f"Each lane is one run of the same skater, {other} working {BASE}, Weight 9, without the puck, Up held "
                  f"from the start. Real time.", sprint, which)
        lanes_gif(out / f"skating_{name}_turn.gif",
                  f"{which} 1 to 6: turning round at top speed",
                  f"Each starts at his own top speed going up the ice, Down held from the start. {other} working {BASE}, "
                  f"Weight 9. Orange: where he stopped. The skid stop takes the same off every frame whatever the "
                  f"ratings (dostop). Real time.", turn, which, turn=True)


def lanes_gif(path, title, sub, runs, which, turn=False):
    S = 2.2                                  # pixels a game unit
    y_lo = min(min(y for y, _ in tr) for _, tr in runs) - 8
    y_hi = max(max(y for y, _ in tr) for _, tr in runs) + 15
    lane_h, pad, head, left = 46, 14, 92, 210
    W = max(int(left + (y_hi - y_lo) * S + pad), 980)
    H = head + 6 * lane_h + 40
    X = lambda y: left + (y - y_lo) * S
    n = len(runs[0][1])
    frames = []
    for t in list(range(0, n, 2)) + [n - 1] * 40:
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f(19, True))
        for j, line in enumerate(textwrap.wrap(sub, 125)):
            d.text((pad, 32 + 18 * j), line, fill="#52606d", font=f(14))
        y0 = runs[0][1][0][0]                                               # the start, every lane
        for ft in range(int((y_lo - y0) / UNITS_PER_FT) // 10 * 10, int((y_hi - y0) / UNITS_PER_FT) + 1, 10):
            gx = X(y0 + ft * UNITS_PER_FT)                                  # a mark every 10 feet from the start
            if gx < left:
                continue
            d.line((gx, head, gx, head + 6 * lane_h), fill="#94a3b8" if ft == 0 else "#e2e8f0")
            d.text((gx - 10, head + 6 * lane_h + 4), f"{ft} ft", fill="#94a3b8", font=f(12))
        for i, (p, tr) in enumerate(runs):
            yy = head + i * lane_h
            d.rectangle((left, yy + 4, W - pad, yy + lane_h - 4), fill="#f8fafc", outline="#e2e8f0")
            y, v = tr[min(t, len(tr) - 1)]
            d.text((pad, yy + 6), f"{which} {p} (working {5 * p})", fill="#1f2933", font=f(15, True))
            dist = (y - tr[0][0]) / UNITS_PER_FT
            d.text((pad, yy + 25), f"{abs(v) / SKATE_MPH:4.1f} mph, {dist:+.0f} ft", fill="#52606d", font=f(13))
            if turn:
                far = max(yy_ for yy_, _ in tr[:t + 1])
                d.line((X(far), yy + 6, X(far), yy + lane_h - 6), fill="#ea580c", width=2)
            cx, cy = X(y), yy + lane_h / 2
            d.ellipse((cx - 9, cy - 9, cx + 9, cy + 9), fill="#2563eb")
        d.text((W - 150, 8), f"{t / 60:.2f} s (real)", fill="#1f2933", font=f(16, True))
        frames.append(img.quantize(colors=48, dither=Image.Dither.NONE))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)
    print("wrote", path)


def main():
    out, what = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    {"shots": lambda: shots(out, n), "onetimer": lambda: onetimer(out, n), "skating": lambda: skating(out)}[what]()


if __name__ == "__main__":
    main()
