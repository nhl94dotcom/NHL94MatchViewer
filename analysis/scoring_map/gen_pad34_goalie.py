"""Pads 3 and 4 (2-on-2 with EA's 4-Way Play) taking the goalie, played (2026-11-09, for NOSE4Web's goalie control
delay option: bholdtimer34 $FFBF08 holds pads 3 / 4's B timers, swapped into bholdtimer for their doinput pass).
The emulator with the 4-Way Play adaptor on both ports (emu.Emu(fourway=True)); the scoring-map test ROM's state
with FourWayPlay ($D046) set and pads 3 / 4 given a team and a skater (cont3team $C32C = cont1team, c3playernum
$C324 = home record 3; cont4team $C32E = the away side, c4playernum $C326 = away record 8; pad 2 also put on the
away side, c2playernum record 7). Each pad in turn holds B alone, its team without the puck (the other side's skater
carrying it far up the ice), 8 seeds x 4 start frames: the frame its player number (c1-c4playernum) becomes its
goalie (home record 5, away record 11). On retail and on the delay-12 build (gen_forum_options_test's goaliedelay
places).

python gen_pad34_goalie.py OUT"""
import json
import sys
from pathlib import Path

import harness as H
import lowload
from emu import Emu
from gen_forum_options_test import build
from paths import ROM

FOURWAY, C1P, C2P, C3P, C4P = 0xD046, 0xC320, 0xC322, 0xC324, 0xC326
CONT1, CONT2, CONT3, CONT4 = 0xC328, 0xC32A, 0xC32C, 0xC32E
PLAYERNUM = {1: C1P, 2: C2P, 3: C3P, 4: C4P}
GOALIE = {1: 5, 3: 5, 2: 11, 4: 11}
PLACES = [(0xAD04, "1111", "0c0c"), (0xAD0A, "1111", "0c0c")] + [(a, "11", "0c") for a in
                                                                (0xB12F, 0xB139, 0xB36D, 0xB377, 0xB39B, 0xB3C3)]


POS, PUCKC_ADDR = 0x35, 0xB7AA


def boot(rom, out):
    """Power-on with the adaptor connected, so Detect4WayPlay sets FourWayPlay and port 2's lines itself; then play.
    Returns the emulator and the play state."""
    import menu_shots as M
    e = Emu(rom, fourway=True)
    M.play(e, "w900 START w120 START w120 w60", out / "_boot")
    for _ in range(60):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    for _ in range(100):
        c = e.w(0xC468)
        e.run(30)
        if e.b(0xFFF7) == 0 and e.w(0xC468) != c:
            break
    return e, e.serialize()


def records(e):
    """Each team's goalie record and two skaters (by position: 0 the goalie)."""
    out = {}
    for side, recs in (("home", range(6)), ("away", range(6, 12))):
        g = [k for k in recs if e.b(H.rec(k) + POS) == 0]
        sk = [k for k in recs if e.b(H.rec(k) + POS) not in (0, 0xFF)]
        out[side] = (g[0] if g else None, sk)
    return out


def trial(e, base, pad, seed, start, recs):
    e.unserialize(base)
    hg, hs = recs["home"]
    ag, as_ = recs["away"]
    home, away = e.w(CONT1) or 1, e.w(CONT2) or 2
    if home == away:
        away = 3 - home
    e.setw(CONT1, home)
    e.setw(CONT2, away)
    e.setw(CONT3, home)
    e.setw(CONT4, away)
    e.setw(C1P, hs[0])
    e.setw(C3P, hs[1])
    e.setw(C2P, as_[0])
    e.setw(C4P, as_[1])
    for k in range(12):              # the person-controlled flag (pflags bit 3) on the four pads' skaters only
        v = e.b(H.rec(k) + 0x62) & ~8
        e.setb(H.rec(k) + 0x62, v | (8 if k in (hs[0], hs[1], as_[0], as_[1]) else 0))
    e.setw(0xD05C, e.w(0xD05A))      # goaliemode2 ($D05C) as pad 1's goaliemode1 ($D05A): the B hold may take him
    carrier = as_[2] if pad in (1, 3) else hs[2]
    for _ in range(10 + start):
        e.setw(PUCKC_ADDR, carrier)
        e.run(1)
    e.setl(0xD066, seed)
    goalie = hg if pad in (1, 3) else ag
    for f in range(120):
        hold = {1: (), 2: (), 3: (), 4: ()}
        hold[pad] = ["B"]
        e.setw(PUCKC_ADDR, carrier)
        e.run(1, hold=hold[1], hold2=hold[2], hold3=hold[3], hold4=hold[4])
        if e.w(PLAYERNUM[pad]) == goalie:
            return f
    return None


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    roms = {"retail": ROM, "12": build(ROM, out, "goaliedelay_12", PLACES)}
    res = {}
    for name, rom in roms.items():
        e, base = boot(rom, out)
        recs = records(e)
        print(name, "FourWayPlay", e.w(FOURWAY), "goaliemode1/2", e.w(0xD05A), e.w(0xD05C), "conts", [hex(e.w(a)) for a in (CONT1, CONT2, CONT3, CONT4)],
              "records", recs, flush=True)
        res[name] = {}
        for pad in (1, 3, 2, 4):
            times = [trial(e, base, pad, 0x2000 + sd * 101, st, recs) for sd in range(8) for st in range(4)]
            ok = [t for t in times if t is not None]
            res[name][f"pad {pad}"] = dict(frames=sorted(set(ok)), mean=round(sum(ok) / len(ok), 1) if ok else None,
                                           never=len(times) - len(ok))
            print(name, f"pad {pad}", json.dumps(res[name][f"pad {pad}"]), flush=True)
            lowload.breathe()
    (out / "pad34.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
