"""NOSE4Web's SNES time on ice (981b836: McMarkis's PlayerIceTime count placed for the original layout), played
(2026-11-13).

ptoi: $7E:E800, a word per roster player (visitors +$34), counted by updateplayers on its sflags3 $0020 tick for the
objects it updates (X < $18), capped at 5999; cleared at StartGame_scout (ScoutingReport's call). The computer against
itself (snes_60fps_cvc's boot: Montreal at home against Los Angeles, the ROM's 5-minute periods, penalties on), Line
Changes set in RAM at Game Setup (OptLine $34C6: 0 off, 1 on). At Game Setup too, $E800-$E867 is filled with $5A5A
(the clear must have emptied it by the opening faceoff: a second game's start).

Every frame of play, independently: who is on the ice (objects 0-11 with a position, their team $1503 and roster
pnum $12A3), and each ptoi word. Checked:
  - a player's ptoi never grows on a frame he wasn't on the ice that frame or the one before (bench, box, injured);
  - each game second of running clock (the clock word $1632 ticking down) adds 1 to everyone on the ice: per player
    the build's total against the count of seconds he was on the ice when the clock ticked;
  - each team's sum against 6 x game seconds less its short-handed seconds (the seconds with fewer than 6 on);
  - with line changes off, the starters' totals (900 a game with 5-minute periods);
  - the reset: $E800-$E867 all 0 at the opening faceoff after the $5A5A fill.

python snes_toi_check.py ROM GAMES OUT.jsonl off|on [FIRST]"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, OPTPEN, SEED, Mem, computer_only

OPTLINE, PTOI, VIS, POSITION, PFTEAM, PNUM = 0x34C6, 0xE800, 0x34, 0x0F43, 0x1503, 0x12A3
FILL = 0x5A5A


def ptoi(m):
    return {(t, s): m.w(PTOI + VIS * t + 2 * s) for t in (0, 1) for s in range(26)}


def on_ice(m):
    out = set()
    for k in range(12):
        pos = m.w(POSITION + 2 * k)
        if pos & 0x8000:
            continue
        out.add((1 if m.w(PFTEAM + 2 * k) else 0, m.w(PNUM + 2 * k)))     # pnum: the roster index
    return out


def game(rom, n, lines, tmp):
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    m.setw(OPTLINE, lines)                                   # Game Setup: line changes, and junk where ptoi lives
    for a in range(PTOI, PTOI + 0x68, 2):
        m.setw(a, FILL)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    first = ptoi(m)
    leftover = sorted(k for k, v in first.items() if v == FILL)
    start_total = {k: v for k, v in first.items() if v}       # play may already have run a few seconds
    counted = defaultdict(int)                               # our count: seconds on the ice when the clock ticked
    short = [0, 0]                                           # seconds with fewer than 6 on the ice, per team
    seconds = 0
    bad_bench = defaultdict(int)                             # grew while off the ice
    prev_ice, prev_t, prev_clock = on_ice(m), first, m.w(CLOCK)
    frames, still = 0, 0
    while m.w(GSP) < 3 and frames < 250000:
        e.run(1)
        frames += 1
        if frames % 3600 == 0:
            lowload.breathe()
        ice, t, clock = on_ice(m), ptoi(m), m.w(CLOCK)
        for k, v in t.items():
            if v > prev_t[k] and k not in ice and k not in prev_ice:
                bad_bench[k] += v - prev_t[k]
        if clock == prev_clock - 1 and m.w(CLOCKSTOP) == 0:
            seconds += 1
            for k in ice:
                counted[k] += 1
            for side in (0, 1):
                short[side] += 6 - sum(1 for k in ice if k[0] == side) if sum(1 for k in ice if k[0] == side) < 6 else 0
        still = still + 1 if clock == prev_clock else 0
        if still > 60 * 20:                                  # a screen waiting for START (intermission, the end)
            e.run(4, hold=["START"])
            still = 0
        prev_ice, prev_t, prev_clock = ice, t, clock
    final = ptoi(m)
    players = sorted(k for k in final if final[k] or counted.get(k))
    diffs = {f"{k[0]}:{k[1]}": final[k] - start_total.get(k, 0) - counted.get(k, 0) for k in players}
    team_sum = [sum(final[k] for k in final if k[0] == side) for side in (0, 1)]
    return {"game": n, "lines": lines, "frames": frames, "seconds": seconds, "short": short,
            "team_sum": team_sum, "expected_sum": [6 * seconds - short[0], 6 * seconds - short[1]],
            "left_from_fill": [f"{t}:{s}" for t, s in leftover], "at_start": {f"{k[0]}:{k[1]}": v for k, v in start_total.items()},
            "players": {f"{k[0]}:{k[1]}": [final[k], counted.get(k, 0)] for k in players},
            "diff_max": max((abs(v) for v in diffs.values()), default=0),
            "grew_off_ice": {f"{k[0]}:{k[1]}": v for k, v in bad_bench.items()}}


def main():
    rom, games, out, mode = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3]), sys.argv[4]
    first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    lines = {"off": 0, "on": 1}[mode]
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(exist_ok=True)
    for n in range(first, first + games):
        r = game(rom, n, lines, tmp)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        top = sorted(r["players"].items(), key=lambda kv: -kv[1][0])
        print(json.dumps({k: r[k] for k in ("game", "lines", "seconds", "short", "team_sum", "expected_sum", "diff_max",
                                            "left_from_fill", "grew_off_ice", "at_start")}), flush=True)
        print("  most time (build, our count):", top[:14], flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
