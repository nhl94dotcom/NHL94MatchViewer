"""NOSE4Web's Genesis score-box logos against the original game, in the game (2026-11-08).

The same inputs on both ROMs (nhl94.bin and the logo build): a game with penalties and line changes On, pad 1 on the
home team; at each moment a screenshot, the score box's map cells (the text map, columns $16-$1E, rows $15-$1C) and
the logo tiles in video memory ($294-$29F): in play; the lower line-change box opened (A held by pad 1's carrier) and
closed (B); back from Edit Lines, Game Stats and an instant replay; the pause menu's side view; the next period after
the break. Other matchups: the score box in play only (and the palette lines 2 and 3, the uniforms).
The game's randomness reads the video counter, so the two ROMs' games may drift apart after the first frames that
take a different time; screens are compared where they show the same thing.

python gen_score_logo_build_check.py ORIGINAL EDITED OUT"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import menu_shots as M
from gen_score_logo_check import Watch, VSPR, VMAP1, MAP1COL, PAL, PUCK, CLOCK, GSP

TEAMS = ["Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh", "Quebec",
         "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg", "All Stars East",
         "All Stars West", "Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton",
         "Florida", "Hartford", "Los Angeles"]


def cells(g):
    vr, _ = g.vram()
    m1, sh = g.w(VMAP1), g.w(MAP1COL)
    return [[g.cell(vr, m1, c, r, sh) for c in range(0x16, 0x1F)] for r in range(0x15, 0x1D)], vr[32 * 0x294:32 * 0x2A0]


def snap(g, out, name, record):
    g.e.screenshot(out / f"{name}.png")
    rows, tiles = cells(g)
    record[name] = dict(rows=rows, tiles=tiles.hex(), state=g.state())


def start(g, home, vis, lines_on):
    e = g.e
    h = TEAMS.index(home)
    v = (TEAMS.index(vis) - TEAMS.index("Los Angeles")) % 28
    lc = "DOWN RIGHT RIGHT" if lines_on else ""
    M.play(e, f"w900 START w120 START w120 DOWN*2 RIGHT*{h} DOWN RIGHT*{v} DOWN*4 RIGHT {lc} w60 S:setup", g.out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    g.step(240)


def full(rom, out):
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(rom, out)
    rec = {}
    start(g, "Montreal", "Los Angeles", True)
    snap(g, out, "play", rec)
    rec["pal"] = [[g.w(PAL + 32 * k + 2 * i) for i in range(16)] for k in (2, 3)]
    for _ in range(3000):                                   # the lower line-change box (pad 1's team, period 1)
        k = g.b(PUCK + 0x61)
        if g.b(PUCK + 0x60) == 0 and k < 6 and g.b(0xB04A + k * 0x80 + 0x62) & 8:
            g.step(60, hold=["A"])
            g.step(20)
            break
        g.step(1)
    snap(g, out, "lc_open", rec)
    g.press("B", 60)
    snap(g, out, "lc_closed", rec)
    for item, name in ((3, "after_edit_lines"), (4, "after_game_stats")):
        g.wait_play()
        g.pause_item(item)
        g.wait_play()
        g.step(60)
        snap(g, out, name, rec)
    g.wait_play()                                           # the instant replay, then back through its menu
    g.press("START", 90)
    menu_top = g.top()
    for _ in range(30):
        if g.w(0xCF20) == 1:
            break
        g.press("DOWN")
    g.press("C", 400)
    snap(g, out, "in_replay", rec)
    g.press("START", 120)
    snap(g, out, "replay_menu", rec)                         # B Options / C Reverse Angle / START = return
    for _ in range(8):
        g.press("START", 200)
        if g.top() == menu_top and g.state()["paused"]:
            break
    snap(g, out, "pause_menu", rec)
    for _ in range(30):
        if g.w(0xCF20) == 0:
            break
        g.press("UP")
    g.press("C", 300)                                       # Resume Game
    g.wait_play()
    g.step(60)
    snap(g, out, "after_replay", rec)
    g.e.setw(CLOCK, 5)
    for _ in range(400):
        g.step(30)
        if g.w(GSP) == 1 and g.in_play():
            break
        if not g.in_play():
            g.press("C", 60)
            g.press("START", 60)
    g.step(120)
    snap(g, out, "period_2", rec)                           # the break's screen
    for _ in range(10):
        if g.wait_play(600):
            break
        g.press("C", 120)
    g.step(60)
    snap(g, out, "period_2_play", rec)
    for _ in range(600):                                    # a skater under the score box
        g.step(10)
        if g.in_play() and sprite_over_box(g):
            break
    snap(g, out, "sprite_under", rec)
    return rec


def sprite_over_box(g):
    """A sprite (not the arrow or the puck: 16 pixels wide or more) over the box: columns $16-$1E, rows $15-$1B."""
    vr, _ = g.vram()
    sat, k = g.w(VSPR), 0
    for _ in range(80):
        a = (sat + 8 * k) & 0xFFFF
        y = (vr[a] | vr[a + 1] << 8) - 128
        size, link = vr[a + 3], vr[a + 2] & 0x7F
        x = (vr[a + 6] | vr[a + 7] << 8) - 128
        wd, ht = 8 * (((size >> 2) & 3) + 1), 8 * ((size & 3) + 1)
        if wd >= 16 and x < 0x1F * 8 and x + wd > 0x16 * 8 + 8 and y < 0x1C * 8 and y + ht > 0x16 * 8 + 4:
            return True
        if link == 0:
            return False
        k = link
    return False


def short(rom, out, home, vis):
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(rom, out)
    rec = {}
    start(g, home, vis, False)
    snap(g, out, "play", rec)
    rec["pal"] = [[g.w(PAL + 32 * k + 2 * i) for i in range(16)] for k in (2, 3)]
    return rec


def sheet(outfile, a, b, names, title):
    rows = []
    for n in names:
        if (a / f"{n}.png").exists() and (b / f"{n}.png").exists():
            rows.append((n, Image.open(a / f"{n}.png").convert("RGB"), Image.open(b / f"{n}.png").convert("RGB")))
    img = Image.new("RGB", (2 * 320 + 8, 16 + len(rows) * 238), (40, 40, 40))
    d = ImageDraw.Draw(img)
    d.text((2, 2), title + "   original | logo build", fill=(255, 255, 0))
    for k, (n, x, y) in enumerate(rows):
        d.text((2, 16 + k * 238), n, fill=(255, 255, 0))
        img.paste(x, (0, 30 + k * 238))
        img.paste(y, (328, 30 + k * 238))
    img.save(outfile)


def main():
    import json
    orig, edited, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    which = sys.argv[4] if len(sys.argv) > 4 else "full"
    if which == "full":
        res = {tag: full(rom, out / f"full_{tag}") for tag, rom in (("orig", orig), ("new", edited))}
        sheet(out / "full.png", out / "full_orig", out / "full_new",
              ["setup", "play", "lc_open", "lc_closed", "after_edit_lines", "after_game_stats", "in_replay",
               "replay_menu", "pause_menu", "after_replay", "period_2", "period_2_play", "sprite_under"], "Montreal (home) v Los Angeles")
    else:
        home, vis = which.split(":")
        res = {tag: short(rom, out / f"{home}_{tag}", home, vis) for tag, rom in (("orig", orig), ("new", edited))}
        sheet(out / f"{home}.png", out / f"{home}_orig", out / f"{home}_new", ["setup", "play"], f"{home} (home) v {vis}")
    (out / f"{which.replace(':', '-')}.json").write_text(json.dumps(res, default=str))
    for tag, rec in res.items():
        for name, v in rec.items():
            if isinstance(v, dict) and "rows" in v:
                print(tag, name, v["state"])
                for i, r in enumerate(v["rows"]):
                    print(f"   ${0x15 + i:02X}: " + " ".join(f"{c:04x}" for c in r))
        if "pal" in rec:
            print(tag, "palette lines 2 / 3:", [" ".join(f"{c:03x}" for c in line) for line in rec["pal"]])


if __name__ == "__main__":
    main()
