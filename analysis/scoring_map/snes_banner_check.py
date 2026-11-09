"""NOSE4Web's SNES team-block colours (2026-11-08): NHL94_banner_test.smc (Boston's TeamBlockPalettes entry: colours
2-7 greens, 8-14 magentas) against NHL94.smc, on every screen that draws the team blocks, plus a scratch copy of the
test ROM with Boston's colours 1 and 15 also changed (to $001F red and $7FE0 cyan), to show where those two are used.

The same presses on each ROM, for Boston at home (palette 7) against Los Angeles, Montreal at home against Boston
(palette 6), and Boston against Boston: Game Setup, the controller screen, the matchups (several moments), the
horizontal pause scoreboard, and each pause item's first screen (stats, player cards ...); and the Play Mode
Playoffs bracket. For each screen: the pixels that differ between the ROMs (count and bounding box), and a sheet of
the three side by side. Gentle (lowload).

python snes_banner_check.py ORIGINAL TEST OUT"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import lowload
import menu_shots as M
from snes_score_logo_check import Check, CLOCK, PSITEM

TEAMS = ["Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh", "Quebec",
         "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg", "All Stars East",
         "All Stars West", "Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton",
         "Florida", "Hartford", "Los Angeles"]
CASES = {"bos_home": ("Boston", "Los Angeles"), "bos_vis": ("Montreal", "Boston"), "bos_bos": ("Boston", "Boston")}
PAUSE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
COLOUR = 0xD6F5C          # Boston's 16 colours (colour 0) in NHL94.smc and the test ROM


def scratch(test, out):
    data = bytearray(Path(test).read_bytes())
    data[COLOUR + 2:COLOUR + 4] = (0x001F).to_bytes(2, "little")
    data[COLOUR + 30:COLOUR + 32] = (0x7FE0).to_bytes(2, "little")
    p = out / "banner_c1c15.smc"
    p.write_bytes(data)
    return p


def shots_for(rom, out, case):
    out.mkdir(parents=True, exist_ok=True)
    c = Check(str(rom), out)
    e = c.e
    home, vis = CASES[case]
    h, v = (TEAMS.index(home) - TEAMS.index("Montreal")) % 28, (TEAMS.index(vis) - TEAMS.index("Los Angeles")) % 28
    M.play(e, f"w1500 START w240 START w240 DOWN RIGHT*{h} DOWN RIGHT*{v} w60 S:setup START w240 S:controllers", out)
    e.run(4, hold=["START"])
    for k, w in enumerate((200, 400, 400, 600, 600)):            # the matchups, as they go by
        e.run(w)
        e.screenshot(out / f"matchups_{k}.png")
    for _ in range(12):
        clock = e.w(CLOCK)
        c.step(240)
        if not c.state()["hor"] and e.w(CLOCK) != clock:
            break
        c.press("START", 60)
    c.step(240)
    c.press("START", 120)
    e.screenshot(out / "pause_scoreboard.png")
    c.press("START", 240)
    for item in PAUSE:
        c.step(120)
        c.press("START", 90)
        for _ in range(40):
            if e.w(PSITEM) == item:
                break
            c.press("DOWN")
        c.press("A", 300)
        e.screenshot(out / f"pause_{item:02d}.png")
        for k in range(8):
            c.press("START" if k % 2 == 0 else "A", 240)
            if c.state()["paused"]:
                break
        for _ in range(40):
            if e.w(PSITEM) == 0:
                break
            c.press("UP")
        c.press("START", 240)


def playoffs(rom, out):
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(str(rom))
    M.play(e, "w1500 START w240 START w240 RIGHT w60 S:playoff_setup START w300 S:playoff_1 w300 S:playoff_2 "
              "START w300 S:playoff_3", out)


def diff(a, b):
    ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    pa, pb = ia.load(), ib.load()
    pts = [(x, y) for y in range(ia.height) for x in range(ia.width) if pa[x, y] != pb[x, y]]
    if not pts:
        return 0, None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return len(pts), (min(xs), min(ys), max(xs), max(ys))


def main():
    orig, test, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    roms = {"orig": orig, "test": test, "c1c15": scratch(test, out)}
    for tag, rom in roms.items():
        for case in CASES:
            shots_for(rom, out / tag / case, case)
        playoffs(rom, out / tag / "playoffs")
    names = sorted({(p.parent.name, p.name) for p in (out / "orig").glob("*/*.png") if not p.name.startswith("_")
                    and p.name[:2] not in ("00", "01", "02", "03")})
    rows = []
    for case, name in names:
        a, b, c3 = (out / t / case / name for t in ("orig", "test", "c1c15"))
        if not (b.exists() and c3.exists()):
            continue
        n1, box1 = diff(a, b)
        n2, box2 = diff(b, c3)
        print(f"{case:9s} {name:22s} orig->test {n1:5d} {box1}   test->colours 1/15 changed {n2:5d} {box2}")
        if n1 or n2:
            rows.append((case, name, a, b, c3))
    img = Image.new("RGB", (3 * 262, 16 + len(rows) * 240), (40, 40, 40))
    d = ImageDraw.Draw(img)
    d.text((2, 2), "NHL94.smc | banner test | test with Boston's colours 1 and 15 changed", fill=(255, 255, 0))
    for r, (case, name, *ps) in enumerate(rows):
        d.text((2, 16 + r * 240), f"{case} {name}", fill=(255, 255, 0))
        for k, p in enumerate(ps):
            img.paste(Image.open(p).convert("RGB"), (k * 262, 30 + r * 240))
    img.save(out / "sheet.png")


if __name__ == "__main__":
    main()
