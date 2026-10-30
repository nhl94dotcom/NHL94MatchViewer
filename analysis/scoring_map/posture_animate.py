"""GIFs of the press-or-sit-back runs: one rush played against four defender postures side by side (none, sit, press,
press and check), the game's own frames from the start of the rush to the result. The rush is the run's own job
(posture_run.job / snes_posture_run.job) at one moment, its shot played out once; the caption gives the full run's
goals per rush for each posture (posture_report.py's numbers).
python posture_animate.py OUT_DIR [NAME]"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from goal_frames import grab
from lowload import gentle

FONT = "C:/Windows/Fonts/segoeui.ttf"
FONTB = "C:/Windows/Fonts/segoeuib.ttf"
SHOW = ("none", "sit", "press", "presscheck")
NAMES = {"none": "no defender", "sit": "sits in the slot", "press": "presses (pokes)", "presscheck": "presses (checks)"}
# (file, system, attack, net, hand, lane, moment, title, the full run's goals per rush by posture)
CASES = [
    ("posture_gen_deke", "genesis", "deke", "top", "L", -45, 6, "Genesis: the deke against each defender",
     {"none": 0.90, "sit": 0.93, "press": 0.39, "presscheck": 0.34}),
    ("posture_gen_2on1", "genesis", "2on1", "top", "L", 50, 8, "Genesis: the 2-on-1 against each defender",
     {"none": 0.55, "sit": 0.14, "press": 0.01, "presscheck": 0.03}),
    ("posture_snes_2on1", "snes", "2on1", "top", "R", 50, 11, "SNES: the 2-on-1 against each defender",
     {"none": 0.62, "sit": 0.49, "press": 0.18, "presscheck": 0.20}),
]
COL = {"GOAL": "#d9480f", "NO GOAL": "#334e68", "LOST": "#7b8794"}


def film(case):
    name, system, attack, net, hand, lane, moment, title, rates = case
    if system == "genesis":
        import posture_run as P
    else:
        import snes_posture_run as P
    P.MOMENTS = moment + 1                           # the run's own SEEDS, so every moment is the run's; only the
    P._init()                                        # first play-out of the filmed moment's shot is kept
    h = P._h[net]
    e = h.e
    clips = {}
    for posture in SHOW:
        frames, on = [], [False]
        run0, setup0 = e.run, h.setup
        decide0 = P.decide if system == "genesis" else h.decide

        first_goal = []

        def decide(*a, **k):
            r = decide0(*a, **k)
            if on[0]:
                first_goal.append(bool(r[0]))
            on[0] = False
            return r

        def run(n=1, hold=(), hold2=()):
            for _ in range(n):
                e.want_frame = on[0]
                run0(1, hold=hold, hold2=hold2)
                e.want_frame = False
                if on[0]:
                    frames.append(grab(e).copy())

        def setup(*a, **k):
            on[0] = False
            setup0(*a, **k)
            frames.clear()
            on[0] = len(seen) == moment
            seen.append(1)
        seen = []
        e.run, h.setup = run, setup
        if system == "genesis":
            P.decide = decide
        else:
            h.decide = decide
        try:
            res = P.job((attack, net, hand, lane, posture))
        finally:
            e.run, h.setup = run0, setup0
            if system == "genesis":
                P.decide = decide0
            else:
                h.decide = decide0
        m = res["moments"][moment]
        first = m[0] == "shot" and first_goal and first_goal[0]
        out = "GOAL" if first else "NO GOAL" if m[0] == "shot" else "LOST"
        clips[posture] = (frames, out)
    return clips


def gif(case, clips, path):
    name, system, attack, net, hand, lane, moment, title, rates = case
    Z, pad, lab, head = 1.0, 8, 24, 48
    w0, h0 = clips["none"][0][0].size
    cw, ch = int(w0 * Z), int(h0 * Z)
    W, H = 2 * cw + 3 * pad, head + 2 * (ch + lab + pad) + pad
    f1, f2, fb = ImageFont.truetype(FONTB, 15), ImageFont.truetype(FONT, 12), ImageFont.truetype(FONTB, 13)
    span = max(len(c[0]) for c in clips.values())
    frames = []
    for t in range(0, span, 2):
        img = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(img)
        d.text((pad, 6), title, fill="#1f2933", font=f1)
        d.text((pad, 26), "The same rush each time (the game's own frames). In brackets: goals per rush, full run.",
               fill="#52606d", font=f2)
        for i, posture in enumerate(SHOW):
            fr, out = clips[posture]
            j = min(t, len(fr) - 1)
            x = pad + (i % 2) * (cw + pad)
            y = head + (i // 2) * (ch + lab + pad)
            img.paste(fr[j].resize((cw, ch), Image.NEAREST), (x, y))
            done = j >= len(fr) - 1
            col = COL[out] if done else "#9aa5b1"
            d.rectangle((x, y + ch, x + cw - 1, y + ch + lab - 4), fill=col)
            d.text((x + 6, y + ch + 2), f"{NAMES[posture]} ({rates[posture]:.2f})" + (f": {out}" if done else ""),
                   fill="white", font=fb)
        frames.append(img.quantize(colors=96, dither=Image.Dither.NONE))
    frames += [frames[-1]] * 45
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=33, loop=0, optimize=True)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    for case in CASES:                               # one system per process (python posture_animate.py OUT NAME)
        if len(sys.argv) > 2 and case[0] != sys.argv[2]:
            continue
        clips = film(case)
        gif(case, clips, out / f"{case[0]}.gif")
        print(case[0], {p: (len(c[0]), c[1]) for p, c in clips.items()}, flush=True)


if __name__ == "__main__":
    main()
