"""NOSE4Web's moved team numbers (2026-11-10, NOSE4Web 603c7fc Genesis, c45dad7 SNES): a ROM whose teams were moved to
new numbers against its original, screen for screen. The test ROMs reverse the first N teams, so team k of the moved
ROM is team N - 1 - k of the original (k < N; the rest unmoved). For each case (HOME:VISITOR, team numbers on the
original), both ROMs get the same presses with the teams picked by number (RIGHT pressed until the game's own
HomeTeam / VisTeam word reads it: the moved ROM's numbers mirrored), so every screen should show the same thing:
- Game Setup (with its rotating player cards on the Genesis), the controller screen (SNES), the matchups as they go
  by (the Genesis team ratings), the opening faceoff in play (centre-ice logo, score box);
- in play, from RAM: each of the 12 players' roster number and working ratings (the right roster and lines);
- SNES: the pause scoreboard and each pause item's first screen (player cards, stats, Edit Lines ...).
For each screen the pixels that differ (count, box) and a sheet of the two side by side where any do. Organ songs and
playoffs are separate (team_move_check.py songs / playoffs). Gentle (lowload).

python team_move_check.py ORIGINAL MOVED N OUT HOME:VISITOR ...   (numbers on the original)"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

import lowload
import menu_shots as M
from snes_banner_check import diff

GEN_HOME, GEN_VIS = 0xC330, 0xC332
SNES_HOME, SNES_VIS = 0x1C98, 0x1C9A
SNES_PAUSE = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]


def mirror(k, n):
    return n - 1 - k if k < n else k


def players_snes(e):
    """(roster number, working ratings) of the 12 players: pnum $12A3, ratings $12C3-$1483 (word arrays)."""
    return [[e.w(0x12A3 + 2 * k)] + [e.w(a + 2 * k) for a in range(0x12C3, 0x1484, 0x20)] for k in range(12)]


def players_gen(e):
    """(roster index +$66, working ratings +$67-$75) of the 12 player records from $B04A."""
    return [[e.b(0xB04A + 0x80 * k + o) for o in range(0x66, 0x76)] for k in range(12)]


def pick(e, addr, team, out):
    for _ in range(48):                         # RIGHT until the team (menus wrap at their own count)
        if e.w(addr) == team:
            return True
        M.play(e, "RIGHT w20", out)
    return False


def shots_snes(rom, out, home, vis):
    from snes_score_logo_check import Check, CLOCK, PSITEM
    out.mkdir(parents=True, exist_ok=True)
    c = Check(str(rom), out)
    e = c.e
    M.play(e, "w1500 START w240 START w240 DOWN", out)
    ok = []
    for addr, team in ((SNES_HOME, home), (SNES_VIS, vis)):
        ok.append(pick(e, addr, team, out))
        M.play(e, "DOWN w20", out)
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
    e.screenshot(out / "play.png")
    rec = dict(picked=ok, teams=[e.w(SNES_HOME), e.w(SNES_VIS)], players=players_snes(e))
    # paused at once, at the opening faceoff: the two ROMs' games drift apart in time after it (2026-11-10: one 1-0
    # at 7:14, the other 0-0 at 8:58), and the pause screens should show the teams, not the play
    c.press("START", 120)
    e.screenshot(out / "pause_scoreboard.png")
    c.press("START", 240)
    for item in SNES_PAUSE:
        if not c.state()["paused"]:
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
        lowload.breathe()                       # still paused: the next item from the same moment
    return rec


def shots_gen(rom, out, home, vis):
    from gen_score_logo_check import Watch
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(rom, out)
    e = g.e
    M.play(e, "w900 START w120 START w120 DOWN*2", out)
    ok = [pick(e, GEN_HOME, home, out)]
    M.play(e, "DOWN w20", out)
    ok.append(pick(e, GEN_VIS, vis, out))
    M.play(e, "w60 S:setup", out)
    for k in range(4):                          # the setup screen's player cards come and go
        e.run(300)
        e.screenshot(out / f"setup_card_{k}.png")
    M.play(e, "UP*3 w60", out)                   # back to the top row, so START begins the game
    for k in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
        e.screenshot(out / f"matchups_{k:02d}.png")
    g.wait_play()
    g.step(240)
    e.screenshot(out / "play.png")
    return dict(picked=ok, teams=[e.w(GEN_HOME), e.w(GEN_VIS)], players=players_gen(e))


def main():
    if sys.argv[1] == "--one":
        rom, out, home, vis = sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
        f = shots_gen if rom.lower().endswith(".bin") else shots_snes
        (out / "rec.json").parent.mkdir(parents=True, exist_ok=True)
        (out / "rec.json").write_text(json.dumps(f(rom, out, home, vis)))
        return
    orig, moved, n, out = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    lowload.gentle()
    for case in sys.argv[5:]:
        h, v = map(int, case.split(":"))
        tag = f"{h}_v_{v}"
        runs = (("orig", orig, h, v), ("moved", moved, mirror(h, n), mirror(v, n)))
        for lab, rom, a, b in runs:
            subprocess.run([sys.executable, __file__, "--one", str(rom), str(out / tag / lab), str(a), str(b)],
                           check=True)
        ra, rb = (json.loads((out / tag / lab / "rec.json").read_text()) for lab in ("orig", "moved"))
        # the roster numbers must match; the working ratings carry each game's own hot / cold draws, so they're shown
        # only for reading (2026-11-10: they differ even when the roster is right)
        same = [p[0] for p in ra["players"]] == [p[0] for p in rb["players"]]
        print(f"== original {h} v {v} / moved {mirror(h, n)} v {mirror(v, n)}: picked {ra['picked']} {rb['picked']}, "
              f"teams in RAM {ra['teams']} / {rb['teams']}, the 12 players' roster numbers "
              f"{'the same' if same else 'DIFFER'}: {[p[0] for p in ra['players']]}", flush=True)
        if not same:
            print(f"   moved: {[p[0] for p in rb['players']]}")
        for a in sorted((out / tag / "orig").glob("*.png")):
            b = out / tag / "moved" / a.name
            if not b.exists():
                print(f"   {a.stem}: no screen on the moved ROM")
                continue
            k, box = diff(a, b)
            print(f"   {a.stem}: {k} pixels differ" + (f", box {box}" if box else ""), flush=True)
            if k:
                ia, ib = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
                sheet = Image.new("RGB", (ia.width * 2 + 8, ia.height), "white")
                sheet.paste(ia, (0, 0))
                sheet.paste(ib, (ia.width + 8, 0))
                sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(out / tag / f"diff_{a.stem}.png")
        lowload.breathe()


if __name__ == "__main__":
    main()
