"""Which SNES RAM a game never writes (2026-11-11, for NOSE4Web's SNES shootout: a saved block of at least $790 bytes and
a mark byte). From the first frame of play (snes_ot_goal_check.start: the menus, the computer on both sides), every 2
frames work RAM (banks $7E and $7F, 128 KB) and, on SA-1 builds, BW-RAM are compared with that first frame and each
byte that ever differs is marked (and every byte not zero at that first frame counts as used: the menus may have
filled it), through:
  - play with every pause-menu screen opened in turn (START, DOWN to the item, B; out with START / B / START; Exit Game
    left out), Instant Replay included;
  - the rest of the game (5-minute periods: the clock held to 5:00 at most), its intermissions and the end of the game
    (START whenever the clock has stood still 15 s (real)), through the screens after it;
  - (mode shootout, a run of its own) a Shootout-mode game from power-on: Play Mode stepped with RIGHT on the setup
    screen until OptPlayMode $34BC is 4, START into it, the computer on both sides; shootoutmode $1D81 and the round
    $1D85 logged; START only when nothing has moved for 20 s (real).
Each run saves its used-byte masks (OUT/mask_MODE.npz); `report` puts the runs together. Printed: the unwritten runs of $800 bytes or more in $7E:2000-$7F:FFFF and in BW-RAM (SA-1), and where the bank $7F
clear at power-on and the stack ($7E:1FFF down) leave them.

python snes_ram_use_check.py ROM OUT game|shootout
python snes_ram_use_check.py report OUT"""
import sys
from pathlib import Path

import numpy as np

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
import menu_shots as M
from snes_60fps_cvc import Mem
from snes_ot_goal_check import start

OPTPLAYMODE, SOMODE, SOROUND = 0x34BC, 0x1D81, 0x1D85


def start_shootout(rom, out):
    e = M.emulator(rom)
    m = Mem(e, rom)
    M.play(e, "w1800 START w240" if m.sa1 else "w1500 START w240 START w240", out)
    for _ in range(8):
        if m.w(OPTPLAYMODE) == 4:
            break
        M.play(e, "RIGHT w30", out)
    print("Play Mode", m.w(OPTPLAYMODE), flush=True)
    for _ in range(30):
        if m.w(SOMODE):
            break
        e.run(4, hold=["START"])
        e.run(150)
    computer_only(m)
    return e, m


def runs(mask, lo, hi, least=0x800):
    out, a = [], lo
    while a < hi:
        if not mask[a]:
            b = a
            while b < hi and not mask[b]:
                b += 1
            if b - a >= least:
                out.append((a, b - 1))
            a = b
        else:
            a += 1
    return out


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[3]
    lowload.gentle()
    e, m = start(rom, 0, out) if mode == "game" else start_shootout(rom, out)
    sa1 = m.sa1
    ram = lambda: np.frombuffer(bytes(e.ram[:0x20000]), np.uint8)
    bw = (lambda: np.frombuffer(bytes(m.bw), np.uint8)) if sa1 else None
    base_w, base_b = ram().copy(), (bw().copy() if sa1 else None)
    tw = base_w != 0                               # not zero at the start of play: in use already (menu data)
    tb = (base_b != 0) if sa1 else None
    frame = [0]
    state = dict(last=None, still=0)

    def run(n, hold=()):
        for _ in range(max(1, n // 2)):
            e.run(2, hold=list(hold))
            frame[0] += 2
            np.logical_or(tw, ram() != base_w, out=tw)
            if sa1:
                np.logical_or(tb, bw() != base_b, out=tb)
            if frame[0] % 300 == 0:
                computer_only(m)
                if m.w(CLOCK) > 300 and m.w(CLOCK) < 0x8000:
                    m.setw(CLOCK, 300)
            if frame[0] % 3600 == 0:
                lowload.breathe()

    def tap(b, wait=40):
        run(4, [b])
        run(wait)

    if mode == "game":
        run(600)
        for item in range(1, 15):                  # the pause menu's screens (not Exit Game)
            tap("START", 60)
            for _ in range(item):
                tap("DOWN", 16)
            tap("B", 200 if item != 1 else 600)
            for b in ("B", "B", "START", "B", "START"):
                tap(b, 60)
            run(120)
        print(f"pause menu done at frame {frame[0]}, period {m.w(GSP)}", flush=True)
        ended = None
        for _ in range(60 * 60 * 90 // 30):        # the rest of the game, then the screens after it
            c = m.w(CLOCK)
            run(30)
            state["still"] = state["still"] + 30 if m.w(CLOCK) == c else 0
            if state["still"] >= 900:
                tap("START", 10)
                state["still"] = 0
            if ended is None and m.w(GSP) >= 4:
                ended = frame[0]
                print(f"game over at frame {ended}", flush=True)
            if ended is not None and frame[0] - ended > 60 * 60:
                break
    else:
        print(f"shootoutmode {m.w(SOMODE)}, round {m.w(SOROUND)}", flush=True)
        last, still = None, 0
        for k in range(60 * 60 * 8 // 60):
            run(60)
            now = (m.w(SOROUND), m.w(SOMODE), m.w(0x178E), m.w(0x1790))
            still = still + 60 if now == last else 0
            if now != last:
                print(f"  frame {frame[0]}: round {now[0]} shootoutmode {now[1]} score {now[2]}-{now[3]}", flush=True)
            last = now
            if still >= 1200:
                tap("START", 10)
                still = 0
            if k % 10 == 0:
                computer_only(m)
    e.screenshot(out / f"end_{mode}.png")
    np.savez_compressed(out / f"mask_{mode}.npz", w=tw, b=tb if sa1 else np.zeros(0, bool))
    print(f"{Path(rom).name} {mode}: {frame[0]} frames; SA-1 {sa1}")
    report(out)


def report(out):
    ms = [np.load(f) for f in sorted(out.glob("mask_*.npz"))]
    tw = np.logical_or.reduce([d["w"] for d in ms])
    bs = [d["b"] for d in ms if len(d["b"])]
    tb = np.logical_or.reduce(bs) if bs else None
    sa1 = tb is not None
    print(f"runs put together: {[f.stem for f in sorted(out.glob('mask_*.npz'))]}")
    print("work RAM never written, runs of $800+: " + (", ".join(
        f"${0x7E0000 + a:06X}-${0x7E0000 + b:06X} (${b - a + 1:X})" for a, b in runs(tw, 0x2000, 0x20000)) or "none"))
    if sa1:
        print("BW-RAM never written, runs of $800+: " + (", ".join(
            f"$40:{a:04X}-$40:{b:04X} (${b - a + 1:X})" if b < 0x10000 else f"${0x400000 + a:06X}-${0x400000 + b:06X} (${b - a + 1:X})"
            for a, b in runs(tb, 0, len(tb))) or "none") + f" (BW-RAM {len(tb):#x} bytes)")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(Path(sys.argv[2]))
    else:
        main()
