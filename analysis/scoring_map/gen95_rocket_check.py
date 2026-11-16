"""NHL '95 (Genesis): NOSE4Web's rocket pass fix (4f1842a) played (2026-11-16). NHL '95's passtoa0 ($847BA) is NHL
'94's (the meeting time in eighths of a second, rounded down: the rocket pass) plus GameFlags ($FFBF08) bit 1: the
time x 4 and a capped lift cleared (a slow flat pass). The fix: NHL '94's (the time in 64ths), with that ending.

Each case from a live state (gen95_assist_check's: the game's own code, others parked): home A picks the puck up, the
receiver B is put at a distance and direction from him, standing or skating (his speed set each frame until the pass),
and A passes with B toward him (the pad held his way); optionally GameFlags bit 1 set as B is pressed (the slow flat
pass). At the release: passspeed ($FFBADC), the puck's velocity ($FFB38A / $B38C) and lift (puckvz $B38E), the
receiver's wait (temp1, +$40) and the puck's no-touch (+$5E), his aim point (+$44 / +$46); then who takes the puck and
when, and the puck's highest Z. Intended speed: passspeed x 65536 / 960 in the puck's velocity units (as
rocket_pass_test.py).

python gen95_rocket_check.py OUT ROM STATE [plain|slow]"""
import json
import math
import sys
from pathlib import Path

from emu import Emu
import gen95_assist_check as G

PASSSPEED, GAMEFLAGS = 0xBADC, 0xBF08
AFTER = 900                       # frames followed after the pass (a slow pass can take up to 12 s)
A, B = 2, 3
DIRS = {(0, 1): ["UP"], (1, 1): ["UP", "RIGHT"], (1, 0): ["RIGHT"], (1, -1): ["DOWN", "RIGHT"], (0, -1): ["DOWN"],
        (-1, -1): ["DOWN", "LEFT"], (-1, 0): ["LEFT"], (-1, 1): ["UP", "LEFT"]}


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def case_list():
    out = []
    for d in (40, 70, 100, 140, 180, 220):
        for (ux, uy) in DIRS:
            n = math.hypot(ux, uy)
            dx, dy = round(d * ux / n), round(d * uy / n)
            for motion in ("still", "away", "across"):
                out.append(dict(d=d, dir=(ux, uy), dx=dx, dy=dy, motion=motion))
    return out


def trial(e, base, c, slow):
    log = []
    p = G.Play(e, base, {A: (0, -40), B: (c["dx"], -40 + c["dy"])}, log)
    if not p.pick_up(A, "A"):
        return dict(c, slow=slow, result="no pickup")
    ux, uy = c["dir"]
    sp = 2200                                        # skating speed (velocity units), set each frame
    vel = {"still": (0, 0), "away": (ux * sp, uy * sp), "across": (-uy * sp, ux * sp)}[c["motion"]]
    held_dir = DIRS[(ux, uy)]
    rel = None
    for f in range(60):
        held = list(held_dir) + (["B"] if 2 <= f < 5 else [])
        if slow and 2 <= f < 6:
            e.setb(GAMEFLAGS, e.b(GAMEFLAGS) | 2)
        p.park()
        p.hold([A])
        if rel is None:                              # the receiver skates at his set speed until the pass
            e.setw(G.rec(B) + 0x28, vel[0] & 0xFFFF)
            e.setw(G.rec(B) + 0x2A, vel[1] & 0xFFFF)
        e.run(1, hold=held)
        if rel is None and e.b(G.PUCK + 0x60) != 0 and (e.w(G.PUCK + 0x28) or e.w(G.PUCK + 0x2A)):
            rel = f
            ps = e.w(PASSSPEED)
            vx, vy = sw(e.w(G.PUCK + 0x28)), sw(e.w(G.PUCK + 0x2A))
            snap = dict(passspeed=ps, vx=vx, vy=vy, vz=e.b(G.PUCK + 0x2C), wait=e.b(G.rec(B) + 0x40),
                        nopuck=e.b(G.PUCK + 0x5E), aim=(sw(e.w(G.rec(B) + 0x44)), sw(e.w(G.rec(B) + 0x46))),
                        flags=e.b(GAMEFLAGS), passplayer=e.w(0xBADE),
                        b_at=(sw(e.w(G.rec(B))), sw(e.w(G.rec(B) + 0x14))))
            break
    if rel is None:
        return dict(c, slow=slow, result="no pass")
    zmax, taker, when = 0, None, None
    for f in range(AFTER):
        p.park()
        p.hold([A])
        e.run(1)
        zmax = max(zmax, sw(e.w(G.PUCK + 0x18)))
        if e.b(G.PUCK + 0x60) == 0:
            taker, when = e.b(G.PUCK + 0x61), f
            break
    intended = snap["passspeed"] * 65536 / 960
    speed = math.hypot(snap["vx"], snap["vy"])
    return dict(c, slow=slow, result="ok", **snap, ratio=round(speed / intended, 3) if intended else None,
                zmax=zmax, taker=taker, when=when)


def main():
    out, rom, state = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    base = Path(state).read_bytes()
    rows = []
    for slow in ((False, True) if len(sys.argv) < 5 else ((sys.argv[4] == "slow"),)):
        for c in case_list():
            rows.append(trial(e, base, c, slow))
    (out / "rocket95.json").write_text(json.dumps(rows))
    ok = [r for r in rows if r["result"] == "ok"]
    print(f"{Path(rom).name}: {len(ok)} passes of {len(rows)}")


if __name__ == "__main__":
    main()
