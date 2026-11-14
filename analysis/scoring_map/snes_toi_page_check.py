"""NOSE4Web's SNES Time On Ice page (2026-11-13, 6bc58af: McMarkis's page placed for the original layout, reading the
ptoi count of 981b836): NHL94_toi_page.smc and NHL94_toi_page_checks.smc (with the bodycheck counts' PM-column display).

  play ROM OUT [STOP_CLOCK] [LINES 1|0]  a computer game (snes_toi_check's boot: 5-minute periods, penalties on, line changes on so
                             the times differ) played into the third period until the clock reads STOP_CLOCK (default
                             100: goalies past 10:00, so 5-character times too), then paused: OUT/paused.state and each
                             player's ptoi ($7E:E800, visitors +$34) in OUT/toi.json
  shots ROM OUT SCRIPT [--set=T:I:SECS,...]       from OUT/paused.state, menu_shots' script (presses, waits, S:NAME screenshots)

python snes_toi_page_check.py play|shots ..."""
import json
import sys
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, OPTPEN, SEED, Mem, computer_only

OPTLINE, PTOI, VIS = 0x34C6, 0xE800, 0x34


def play(rom, out, stop_clock, lines=1):
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, "w1500 START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
    m.setw(OPTLINE, lines)
    M.play(e, "START w240 START w200 w2400", out)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, 0x9E37)
    m.setw(SEED + 2, 0x7F4A)
    frames, still, last = 0, 0, None
    while not (m.w(GSP) == 2 and m.w(CLOCK) <= stop_clock and m.w(CLOCKSTOP) == 0) and frames < 250000:
        e.run(10)
        frames += 10
        if frames % 300 == 0:
            computer_only(m)
        c = m.w(CLOCK)
        still = still + 10 if c == last else 0
        last = c
        if still > 1200:                      # a screen waiting (intermission): START
            e.run(4, hold=["START"])
            still = 0
        if frames % 36000 == 0:
            lowload.breathe()
    e.run(4, hold=["START"])
    e.run(90)
    (out / "paused.state").write_bytes(e.serialize())
    e.screenshot(out / "paused.png")
    toi = {t: [m.w(PTOI + VIS * t + 2 * s) for s in range(26)] for t in (0, 1)}
    (out / "toi.json").write_text(json.dumps(toi))
    fmt = lambda v: f"{v // 60}:{v % 60:02d}"
    print("period", m.w(GSP), "clock", m.w(CLOCK))
    for t in (0, 1):
        print("team", t, sorted(((fmt(v), s) for s, v in enumerate(toi[t]) if v), key=lambda x: -toi[t][x[1]]))


def shots(rom, out, script, sets=()):
    """sets: (team 0 home / 1 visitors, roster index, seconds) written to ptoi ($7E:E800, visitors +$34) first."""
    e = M.emulator(rom)
    e.unserialize((out / "paused.state").read_bytes())
    if sets:
        m = Mem(e, rom)
        for t, i, secs in sets:
            m.setw(PTOI + (VIS if t else 0) + 2 * i, secs)
    M.play(e, script, out)


if __name__ == "__main__":
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if mode == "play":
        play(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 100, int(sys.argv[5]) if len(sys.argv) > 5 else 1)
    else:
        sets = [tuple(int(v) for v in x.split(":")) for a in sys.argv[5:] if a.startswith("--set=")
                for x in a.split("=")[1].split(",")]
        shots(rom, out, sys.argv[4], sets)
