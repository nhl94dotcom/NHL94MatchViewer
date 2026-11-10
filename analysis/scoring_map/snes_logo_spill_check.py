"""NOSE4Web's SNES logo spill (2026-11-10, NOSE4Web 85a17a2). LoadFrameTiles gives a block frame ceil(tiles / 4)
units of the sprite tile cache (up to 8: two tile rows, 2 columns a unit, starting at 2 x (run & 7); more: whole
groups of 8 then the rest), the first DMA linearly from the room's start (sprox bytes), the second one tile row down
($100 words; past 8 units, the row after the first part's whole rows). A logo whose first DMA is longer than its room's
row writes over whatever else is cached there, and its own pieces past the room show that instead.

On NOSE4Web's Classic import into the 32-team SA-1 build (nhl94_2026_classic.sfc: 13 logos laid out past their room)
and the same ROM saved by the fixed NOSE4Web (nhl94_2026_classic_relaid.sfc), the same presses on both for each case
(home, visitor; RIGHT pressed until HomeTeam $1C98 / VisTeam $1C9A read the team: the menu wraps at 28): Game
Setup, the controller screen, the matchups as they go by, the pause scoreboard and each pause item's first screen
(player cards, stats ...). For each screen: the pixels that differ between the ROMs (count and box), and a sheet of
the two side by side where they differ.

python snes_logo_spill_check.py OLD RELAID OUT [HOME:VISITOR ...]   (default: the 13 spilling teams in pairs)"""
import subprocess
import sys
from pathlib import Path

from PIL import Image

import lowload
import menu_shots as M
from snes_banner_check import diff
from snes_score_logo_check import Check, CLOCK, PSITEM

TEAMS = ["Anaheim", "Boston", "Buffalo", "Calgary", "Chicago", "Dallas", "Detroit", "Edmonton", "Florida", "Hartford",
         "Los Angeles", "Montreal", "New Jersey", "NY Islanders", "NY Rangers", "Ottawa", "Philadelphia", "Pittsburgh",
         "Quebec", "San Jose", "St. Louis", "Tampa Bay", "Toronto", "Vancouver", "Washington", "Winnipeg",
         "All Stars East", "All Stars West", "Vancouver 2", "Vegas", "Washington 2", "Winnipeg 2"]
SPILL = ["Anaheim", "Boston", "Buffalo", "Dallas", "Detroit", "Florida", "Montreal", "NY Islanders", "Pittsburgh",
         "Quebec", "San Jose", "St. Louis", "Washington"]
HOMETEAM, VISTEAM = 0x1C98, 0x1C9A
PAUSE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def shots(rom, out, home, vis):
    out.mkdir(parents=True, exist_ok=True)
    c = Check(str(rom), out)
    e = c.e
    M.play(e, "w1500 START w240 START w240 DOWN", out)
    for addr, team in ((HOMETEAM, home), (VISTEAM, vis)):      # RIGHT until the team (the menu wraps at 28)
        for _ in range(40):
            if e.w(addr) == TEAMS.index(team):
                break
            M.play(e, "RIGHT w20", out)
        M.play(e, "DOWN w20", out)
    print(home, vis, "selected:", TEAMS[e.w(HOMETEAM)], TEAMS[e.w(VISTEAM)], flush=True)
    M.play(e, "w60 S:setup START w240 S:controllers", out)
    e.run(4, hold=["START"])
    for k, w in enumerate((200, 400, 400, 600, 600)):
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
        lowload.breathe()


def main():
    if sys.argv[1] == "--one":
        rom, out, home, vis = sys.argv[2], Path(sys.argv[3]), sys.argv[4], sys.argv[5]
        shots(rom, out, home, vis)
        return
    old, new, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    cases = [tuple(a.split(":")) for a in sys.argv[4:]] or \
        [(SPILL[i], SPILL[(i + 1) % len(SPILL)]) for i in range(0, len(SPILL), 2)]
    lowload.gentle()
    for home, vis in cases:
        tag = f"{home}_at_{vis}".replace(" ", "")
        for rom, lab in ((old, "old"), (new, "relaid")):
            subprocess.run([sys.executable, __file__, "--one", str(rom), str(out / tag / lab), home, vis], check=True)
        for a in sorted((out / tag / "old").glob("*.png")):
            b = out / tag / "relaid" / a.name
            if not b.exists():
                continue
            k, box = diff(a, b)
            print(f"{home} home, {vis} visiting, {a.stem}: {k} pixels differ" + (f", box {box}" if box else ""), flush=True)
            if k:
                ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
                sheet = Image.new("RGB", (ia.width * 2 + 8, ia.height), "white")
                sheet.paste(ia, (0, 0))
                sheet.paste(ib, (ia.width + 8, 0))
                sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(out / tag / f"diff_{a.stem}.png")


if __name__ == "__main__":
    main()
