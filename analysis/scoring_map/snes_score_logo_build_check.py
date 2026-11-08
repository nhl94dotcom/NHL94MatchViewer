"""NOSE4Web's score-box logos on the original SNES game (McMarkis's, ported; 2026-11-08): the edited ROM against its
original, in the game, screen for screen. For each matchup (HOME:VISITOR, the retail team names as the Game Setup lists
them), on both ROMs: the score box in play, the power-play box with each side on the power play (shown by making the
two tmap words differ: the display only), play after the Edit Lines and Crowd Level pause screens (the only two that
write over the logo tiles at ExtraChars; snes_score_logo_check.py), the horizontal pause scoreboard (its team banners
borrow palettes 6 and 7), play after the break into period 2 (the clock cut short), and the line-change box (palette 4's colours 1 and 4). Then a sheet per matchup,
original beside edited (the bottom of the screen x3; the scoreboard whole), and the ROMs' changed byte ranges.
Penalties and line changes on; ROMs laid out as retail (NHL94.smc, NHL94_Classic, SDL16: the same RAM).

python snes_score_logo_build_check.py ORIGINAL EDITED OUT HOME:VISITOR ...
  e.g.  ... NHL94.smc NHL94_score_logos.smc out Buffalo:Calgary "Los Angeles:Chicago\""""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import menu_shots as M
from snes_score_logo_check import Check, CLOCK, GSP, TMAP

TEAMS = ["Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh", "Quebec",
         "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg", "All Stars East",
         "All Stars West", "Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton",
         "Florida", "Hartford", "Los Angeles"]           # the Game Setup's order from its default home team, Montreal
DEFAULT_VISITOR = TEAMS.index("Los Angeles")
SHOTS = ["play", "home_pp", "away_pp", "after_edit_lines", "after_crowd_level", "pause_scoreboard", "period_2",
         "line_change_box"]


def wait_play(c, frames=3000):
    """Until play runs on the vertical rink: lit, not paused, and the clock ticking (the power-play box is only
    redrawn while it ticks)."""
    for _ in range(frames // 30):
        clock = c.e.w(CLOCK)
        c.step(30)
        if c.in_play() and not c.state()["hor"] and c.e.w(0x0AD3) == 15 and c.e.w(CLOCK) != clock:
            return True
    return False


def catch_line_change_box(c, out):
    """Wrap c.step: the first time the line-change box (sflags3 bit 0) is up on a lit screen, a screenshot."""
    step = c.step

    def watched(n=1, hold=()):
        for _ in range(n):
            step(1, hold)
            if not getattr(c, "lcb", False) and c.e.w(0x15DC) & 1 and c.e.w(0x0AD3) == 15 and not c.state()["hor"]:
                c.lcb = True
                step(30)
                c.e.screenshot(out / "line_change_box.png")
    c.step = watched


def one(rom, out, home, vis):
    out.mkdir(parents=True, exist_ok=True)
    c = Check(rom, out)
    catch_line_change_box(c, out)
    e = c.e
    h, v = TEAMS.index(home), (TEAMS.index(vis) - DEFAULT_VISITOR) % len(TEAMS)
    M.play(e, f"w1500 START w240 START w240 DOWN RIGHT*{h} DOWN RIGHT*{v} DOWN*2 RIGHT DOWN RIGHT w60 S:setup "
              "START w240 START w120 w2400", out)
    for _ in range(10):                                   # START through the matchups and the pre-game menu until
        clock = e.w(CLOCK)                                # the clock runs on the vertical rink (a START can be lost)
        c.step(240)
        if not c.state()["hor"] and e.w(CLOCK) != clock:
            break
        if c.state()["hor"] or e.w(CLOCK) == clock:
            c.press("START", 60)
    wait_play(c)
    c.step(120)
    e.screenshot(out / "play.png")
    for k, name in ((1, "home_pp"), (0, "away_pp")):     # the other side one man short
        for _ in range(4):                                # again if a whistle or a fade comes in the middle
            wait_play(c)
            t = e.w(TMAP + 2 * k)
            e.setw(TMAP + 2 * k, t - 1)
            clock = e.w(CLOCK)
            c.step(150)
            lit = e.w(0x0AD3) == 15 and c.in_play() and not c.state()["hor"] and e.w(CLOCK) != clock
            if lit:
                e.screenshot(out / f"{name}.png")
            e.setw(TMAP + 2 * k, t)
            c.step(60)
            if lit:
                break
    for item, name in ((4, "after_edit_lines"), (14, "after_crowd_level")):
        wait_play(c)
        c.pause_item(item)
        wait_play(c)
        c.step(120)
        e.screenshot(out / f"{name}.png")
    c.press("START", 120)                                 # the pause menu on the horizontal scoreboard
    e.screenshot(out / "pause_scoreboard.png")
    c.press("START", 240)
    wait_play(c)
    e.setw(CLOCK, min(e.w(CLOCK), 10))                   # to the end of the period and through the break
    for _ in range(600):
        c.step(30)
        if e.w(CLOCK) == 0 and not c.in_play():
            break
    c.through_break(0)
    c.step(120)
    e.screenshot(out / "period_2.png")
    for _ in range(600):                                  # the line-change box (sflags3 bit 0), if not seen yet
        if getattr(c, "lcb", False):
            break
        c.step(20)
    return e.w(GSP)


def sheet(out, a, b, title):
    rows = []
    for s in SHOTS:
        pa, pb = a / f"{s}.png", b / f"{s}.png"
        if not (pa.exists() and pb.exists()):
            continue
        ia, ib = Image.open(pa).convert("RGB"), Image.open(pb).convert("RGB")
        if s != "pause_scoreboard":
            ia, ib = ia.crop((0, 176, 256, 224)).resize((768, 144), Image.NEAREST), ib.crop((0, 176, 256, 224)).resize((768, 144), Image.NEAREST)
        else:
            ia, ib = ia.resize((512, 448), Image.NEAREST), ib.resize((512, 448), Image.NEAREST)
        rows.append((s, ia, ib))
    w = max(r[1].width for r in rows)
    img = Image.new("RGB", (2 * w + 8, 20 + sum(r[1].height + 14 for r in rows)), (40, 40, 40))
    d = ImageDraw.Draw(img)
    d.text((2, 2), title + "   original | edited", fill=(255, 255, 0))
    y = 20
    for s, ia, ib in rows:
        d.text((2, y), s, fill=(255, 255, 0))
        img.paste(ia, (0, y + 14))
        img.paste(ib, (w + 8, y + 14))
        y += ia.height + 14
    img.save(out)
    return out


def rom_diff(a, b):
    x, y = Path(a).read_bytes(), Path(b).read_bytes()
    n = max(len(x), len(y))
    x, y = x.ljust(n, b"\0"), y.ljust(n, b"\0")
    runs, i = [], 0
    while i < n:
        if x[i] != y[i]:
            j = i
            while j < n and x[j:j + 16] != y[j:j + 16]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return len(Path(a).read_bytes()), len(Path(b).read_bytes()), runs


def main():
    orig, edited, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    for pair in sys.argv[4:]:
        home, vis = pair.split(":")
        tag = f"{home}-{vis}".replace(" ", "")
        for name, rom in (("original", orig), ("edited", edited)):
            one(rom, out / tag / name, home, vis)
        print(sheet(out / f"{tag}.png", out / tag / "original", out / tag / "edited", f"{home} (home) v {vis}"))
    la, lb, runs = rom_diff(orig, edited)
    print(f"ROM sizes {la:,} / {lb:,}; {len(runs)} changed ranges:")
    for i, j in runs[:40]:
        print(f"   ${i:06X}-${j - 1:06X}  {j - i} bytes")


if __name__ == "__main__":
    main()
