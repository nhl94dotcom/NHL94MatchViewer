"""NOSE4Web's long fall instead of an injury, Genesis (2026-11-11, NOSE4Web 5de49b8: nhl94_long_fall.bin,
CDL_Season_12_long_fall.bin). FallDown's call of setInjuryType at $14450 becomes bra.w .22 (the ordinary fall's end:
the crowd's cheer or boo), and SPAinjuryfall's two lists (frames, ticks) a back fall that lies 300 ticks and gets up.

A scratch copy of the ROM is patched so that every knockdown of a puck carrier takes the injury path (as
gen_injury_check: the fall-back test at $1440E, the facing test at $1441A and the draw's bgt.w .22 at $14436 NOP'd;
the clock test stays); the boot's ROM check at $300 NOP'd if it is there. Pad 1 on the home team, no presses. For
`MINUTES` (real) of play, every frame: each skater's animation word. Each stretch in SPAinjuryfall ($145C): its
length in frames, its sprite frames in order, the animation after it; over it the screen ($FFF7, 0 play), the clock
(running or not), InjCntDown ($C3EC: 1-4 the injury box's countdown; it counts below 0 otherwise), sflags7 bit 5 (the game injury), each team's penalties (tmPenalties, team
block +6: $C6D4 / $CA38) and the player's tmpdst word (-1 on the ice). Ordinary knockdowns ($0DD8 / $0D26) are timed
too: run on the unchanged ROM as well (the same patch) to compare them.

python gen_long_fall_check.py ROM OUT [MINUTES]   -> prints the stretches and a summary (JSON last line)"""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
from gen_score_logo_check import Watch, GSP, CLOCK

REC, ANIM, FRAME, PNUM, FLAGS = 0xB04A, 0x58, 0x06, 0x66, 0x62
INJFALL, INJ1, DOWNS = 0x145C, 0x1AF4, (0x0DD8, 0x0D26)
INJCNT, SFLAGS7, SCREEN = 0xC3EC, 0xC2FC, 0xFFF7
TEAM, PENS, TMPDST = (0xC6CE, 0xCA32), 6, 0x66


def patched(rom, out):
    data = bytearray(Path(rom).read_bytes())
    assert data[0x14432:0x1443A].hex() == "b06a00326e00005c", data[0x14432:0x1443A].hex()
    for at in (0x1440E, 0x1441A, 0x14436):
        data[at:at + 4] = bytes.fromhex("4e714e71")
    if data[0x300:0x306].hex() == "4eb9000ffac0":
        data[0x300:0x306] = bytes.fromhex("4e714e714e71")
    p = out / f"{Path(rom).stem}_forced.bin"
    p.write_bytes(data)
    return str(p)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    g = Watch(patched(rom, out), out)
    e = g.e
    r = lambda a: e.w(0xFF0000 | a)
    rb = lambda a: e.b(0xFF0000 | a)
    M.play(e, "w900 START w120 START w120 DOWN*7 RIGHT w60", out)       # penalties on, line changes off
    for _ in range(40):
        if rb(SCREEN) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    open_ = {}                                                          # record -> the stretch going on
    done, downs = [], []
    pens0 = [r(t + PENS) for t in TEAM]
    shot = 0
    for f in range(int(minutes * 3600)):
        e.run(1)
        if f % 3600 == 0:
            lowload.breathe()
        if f % 600 == 0 and not g.in_play():
            e.run(4, hold=["START"])
        if g.w(GSP) >= 3:
            break
        for k in list(range(1, 6)) + list(range(7, 12)):
            a = REC + 0x80 * k
            anim = r(a + ANIM)
            cur = open_.get(k)
            if cur and anim != cur["anim"]:
                cur["frames"] = f - cur["start"]
                cur["after"] = f"${anim:04X}"
                cur["clock_end"] = g.w(CLOCK)
                cur["pens_during"] = sum(r(t + PENS) for t in TEAM) - cur["pens_start"]
                del open_[k]
                (done if cur["anim"] == INJFALL else downs).append(cur)
                continue
            if cur:
                sp = r(a + FRAME)
                if sp != cur["sprites"][-1]:
                    cur["sprites"].append(sp)
                cur["screen_max"] = max(cur["screen_max"], rb(SCREEN))
                cur["injcnt_max"] = max(cur["injcnt_max"], r(INJCNT))
                cur["injcnt_low"] |= 0 < r(INJCNT) <= 4
                cur["gameinj"] |= rb(SFLAGS7) & 0x20 != 0
                pn = rb(a + PNUM)
                cur["tmpdst"].add(r(TEAM[k >= 6] + TMPDST + 2 * pn))
                if cur["anim"] == INJFALL and f - cur["start"] == 150 and shot < 6:
                    e.screenshot(out / f"lying_{shot}.png")
                    shot += 1
            elif anim == INJFALL or anim in DOWNS:
                open_[k] = {"rec": k, "team": "home" if k < 6 else "away", "anim": anim, "start": f,
                            "period": g.w(GSP) + 1, "clock": g.w(CLOCK), "sprites": [r(a + FRAME)],
                            "screen_max": rb(SCREEN), "injcnt_max": r(INJCNT), "gameinj": False, "tmpdst": set(),
                            "pens_start": sum(r(t + PENS) for t in TEAM), "injcnt_low": False}
                if anim == INJ1:
                    print("SPAinjury1 seen!", flush=True)
    pens = [r(t + PENS) - p for t, p in zip(TEAM, pens0)]
    for d in done:
        d["tmpdst"] = sorted(f"${x:04X}" for x in d["tmpdst"])
        d["clock_ran"] = d["clock_end"] != d["clock"]
        print(f"long fall: {d['team']} rec {d['rec']} P{d['period']} clock {d['clock']}: {d['frames']} frames, "
              f"sprites {d['sprites']}, then {d['after']}; screen max {d['screen_max']}, InjCntDown max "
              f"{d['injcnt_max']}, game injury bit {d['gameinj']}, tmpdst {d['tmpdst']}, clock ran {d['clock_ran']}, penalties during {d['pens_during']}",
              flush=True)
    dl = Counter(min(x["frames"] // 10 * 10, 300) for x in downs)
    summary = {"rom": Path(rom).name, "long_falls": len(done),
               "long_frames": sorted(x["frames"] for x in done),
               "ordinary_downs": len(downs), "ordinary_frames_by_10": dict(sorted(dl.items())),
               "ordinary_median": sorted(x["frames"] for x in downs)[len(downs) // 2] if downs else None,
               "penalties_called": pens, "injury1_seen": False,
               "re_knocked": sum(1 for x in done if x["after"] in ("$145C", "$0DD8", "$0D26")),
               "screen_left_play": sum(1 for x in done if x["screen_max"]),
               "injcnt_set": sum(1 for x in done if x["injcnt_low"]),
               "penalty_during": sum(1 for x in done if x["pens_during"]),
               "off_ice_tmpdst": sum(1 for x in done if any(t != "$FFFF" for t in x["tmpdst"]))}
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
