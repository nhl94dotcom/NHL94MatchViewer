"""NOSE4Web's Genesis Time On Ice page in Player Stats (2026-11-13, 4526102: nhl94_toi.bin and nhl94_toi_checks.bin, the
latter with the bodycheck counts). The game counts time on ice at the team struct's +$136 (a word per player, game
seconds) but never shows it; the build adds Player Stats sort column 5 ("Time On Ice", game stats only).

  play ROM OUT [SECONDS] [PLAYMODE]   (PLAYMODE 2: playoffs) a computer game (gen_ot_check's boot, line changes on so the times differ, 5-minute
                           periods) played SECONDS of game clock, then paused: OUT/paused.state, and each player's
                           +$136 word for both teams (OUT/toi.json)
  shots ROM OUT SCRIPT     from OUT/paused.state, menu_shots' script (presses, waits, s / S:NAME screenshots)

python gen_toi_page_check.py play|shots ..."""
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTLINE, PERLEN, SEED, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD058, 0xD050, 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
TEAM = (0xC6CE, 0xCA32)
TOI = 0x136
BASE, SZ = 0xB04A, 0x80


def computer_only(e):
    e.setw(CONT1, 0)
    e.setw(CONT2, 0)
    for k in range(12):
        e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)


def play(rom, out, seconds, playmode=0):
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(G.PLAYMODE, playmode)                 # 0 regular season, 2 playoffs (a "Playoff Stats" menu item)
    e.setw(OPTLINE, 1)
    e.setw(PERLEN, 0)
    if not G.into_play(e):
        raise SystemExit("never reached play")
    e.setl(SEED, 0x2545F491)
    start = e.w(CLOCK)
    frame = 0
    while start - e.w(CLOCK) < seconds and frame < 60 * 60 * 20:
        if frame % 60 == 0:
            computer_only(e)
        e.run(4)
        frame += 4
    # pause at the next stretch of live play
    for _ in range(600):
        if e.b(SCREEN) == 0:
            break
        e.run(4, hold=["START"] if frame % 240 == 0 else [])
        frame += 4
    e.run(4, hold=["START"])
    e.run(60)
    Path(out / "paused.state").write_bytes(e.serialize())
    e.screenshot(out / "paused.png")
    toi = {}
    for t, base in enumerate(TEAM):
        toi[t] = [e.w(base + TOI + 2 * p) for p in range(26)]
    (out / "toi.json").write_text(json.dumps(toi))
    print("clock", e.w(CLOCK), "period", e.w(GSP), "toi home", toi[0], "away", toi[1])


def shots(rom, out, script):
    import menu_shots as M
    e = Emu(rom)
    e.unserialize((out / "paused.state").read_bytes())
    M.play(e, script, out)


if __name__ == "__main__":
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "play":
        play(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 240, int(sys.argv[5]) if len(sys.argv) > 5 else 0)
    else:
        shots(rom, out, sys.argv[4])
