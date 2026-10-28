"""GIFs of real EA Special goals from the recorded Genesis games, drawn by the viewer itself:
python analysis/ea_real_gifs.py OUT_DIR TEAM [TEAM ...] [--max N]

The attempts are ea_real.py's (forehand and backhand), kept when the shooter scored on his own follow-up and his team
is one of TEAM (abbreviations as the match files have them: the person whose goals are wanted). One goal per kind of
play (net, hand, forehand / backhand) in turn, up to N (default 8). Each GIF runs from a second before the first shot
to most of a second after the goal, at 15 frames a second (real time): every frame is a screenshot of the games
folder's viewer.html (`&t=`, the rink-only layout, no event tags) in headless Edge, cropped to the scoreboard and the
attacked half. One Edge at a time, resting as long as each took (gentle mode, as the scoring map's lowload)."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_real  # noqa: E402

HOME = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path.home() / "Documents" / "NHL94 Viewer"
EDGE = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
FONT = "C:/Windows/Fonts/segoeui.ttf"
FPS = 15
# The viewer at 760 x 1400 in the rink-only layout: the scoreboard is the top 68 pixels; the rink runs from about
# x 105 to 655, its goal lines at y 210 (top) and 890 (bottom), centre ice at 550
WINDOW = (760, 1400)
HEAD = (100, 0, 660, 68)
HALF = {"top": (105, 140, 655, 560), "bottom": (105, 515, 655, 925)}   # above the rink's buttons


def shot(url, out, profile):
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=3000",
                    f"--user-data-dir={profile}", f"--screenshot={out}", f"--window-size={WINDOW[0]},{WINDOW[1]}", url],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def frames(game, t0, t1, net, work, profile):
    page = (HOME / "viewer.html").resolve().as_uri()
    pics, k = [], 0
    while t0 + k / FPS <= t1:
        out = work / f"f{k:03}.png"
        t = time.time()
        shot(f"{page}?match={quote(game)}&t={t0 + k / FPS:.3f}&layout=rink&tags=0", out, profile)
        time.sleep(time.time() - t)                    # gentle: rest as long as it worked
        im = Image.open(out).convert("RGB")
        head, half = im.crop(HEAD), im.crop(HALF[net])
        pic = Image.new("RGB", (half.width, head.height + half.height), (20, 22, 26))
        pic.paste(head, ((half.width - head.width) // 2, 0))
        pic.paste(half, (0, head.height))
        pics.append(pic)
        k += 1
    return pics


def caption(pics, lines):
    font = ImageFont.truetype(FONT, 16)
    out = []
    for p in pics:
        c = Image.new("RGB", (p.width, p.height + 26 * len(lines) + 8), (20, 22, 26))
        c.paste(p, (0, 0))
        d = ImageDraw.Draw(c)
        for i, line in enumerate(lines):
            d.text((10, p.height + 4 + 26 * i), line, fill=(230, 232, 236), font=font)
        out.append(c.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
    return out


def main():
    args = [a for a in sys.argv[1:]]
    most = 8
    if "--max" in args:
        i = args.index("--max")
        most = int(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    out_dir, teams = Path(args[0]), set(args[1:])
    out_dir.mkdir(parents=True, exist_ok=True)
    goals = []
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.name == "season.js":
            continue
        m = ea_real.load(p)
        if m.get("system", "genesis") != "genesis":
            continue
        for r in list(ea_real.attempts(m)) + list(ea_real.attempts(ea_real.backhand(m), "backhand")):
            if r["outcome"] == "goal: shooter" and m["abbr"][r["team"]] in teams:
                r["t"] = m["t"][r["f"]] / 1000
                r["abbr"] = m["abbr"]
                r["team_abbr"] = m["abbr"][r["team"]]
                goals.append(r)
    kinds = {}
    for g in goals:
        kinds.setdefault((g["net"], g["hand"], g["kind"]), []).append(g)
    chosen = []
    while len(chosen) < most and any(kinds.values()):
        for k in sorted(kinds):
            if kinds[k] and len(chosen) < most:
                chosen.append(kinds[k].pop(0))
    print(f"{len(goals)} EA Special goals by {', '.join(sorted(teams))}; making {len(chosen)}", flush=True)
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        work, profile = Path(tmp) / "frames", Path(tmp) / "edge"
        work.mkdir()
        for g in chosen:
            name = f"ea_real_{g['game']}_p{g['period']}_{g['clock'] // 60}{g['clock'] % 60:02}"
            t0 = time.time()
            pics = frames(g["game"], g["t"] - 1.0, g["t"] + g["follow_gap"] + 0.8, g["net"], work, profile)
            lines = [f"{g['team_abbr']}, {g['abbr'][0]}-{g['abbr'][1]} {g['game'][:10]}, period {g['period']} "
                     f"{g['clock'] // 60}:{g['clock'] % 60:02} left",
                     f"{g['hand'].capitalize()}-handed {g['kind']} at the {g['net']} net, {g['out'] / 3:.0f} ft out, "
                     f"{g['side'] / 3:.0f} ft to the side,",
                     f"the follow-up {g['follow_gap']:.1f} s after the first shot"]
            pics = caption(pics, lines)
            pics[0].save(out_dir / f"{name}.gif", save_all=True, append_images=pics[1:] + [pics[-1]] * FPS,
                         duration=round(1000 / FPS), loop=0, optimize=True)
            made.append(dict(file=f"{name}.gif", **{k: g[k] for k in ("game", "period", "clock", "net", "hand", "kind",
                                                                       "out", "side", "follow_gap", "team_abbr")}))
            print(f"{name}.gif: {len(pics)} frames, {round(time.time() - t0)} s", flush=True)
    json.dump(made, open(out_dir / "ea_real_gifs.json", "w"), indent=1)


if __name__ == "__main__":
    main()
