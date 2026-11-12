"""NOSE4Web's long fall instead of an injury, SNES (2026-11-11, NOSE4Web 5de49b8: NHL94_injuries_long_fall.smc,
nhl94snes_SA1_injuries_long_fall.sfc). FallDown's jsl setInjuryType becomes jmp .25 (the ordinary fall's end: the
puck loose, the crowd: sound 3 for a home faller, a roar for a visitor), and SPAinjury1's two lists a back fall that
lies 300 ticks and gets up.

A scratch copy of the ROM is patched so that every knockdown of a puck carrier past the clock test takes the injury
path: FallDown's `cmp #SPAfallback / bne .23`, `and #3 / bne .23` and the draw's `bpl .23` (found by their bytes
before the roll, lda #150 / jsl randoma8) NOP'd; the clock and pf2pen tests stay. The jmp's target is printed with
its first bytes (expected ldy a2 / lda SPA,y / cmp #SPAstumble). A computer game (snes_ot_goal_check.start) for
`MINUTES` (real); every frame each skater's SPA ($11A3). Each stretch in SPAinjury1: its length in frames, its
sprite frames (frame $0D97) in order, the animation after it; over it gmclock ($15D6, the clock stopped),
InjCntDown ($1626), the penalties (tmPenalties $174A home / $174C away) and his tmpdst word ($1852 + 2 pnum, away
+$34; $FFFF on the ice). Ordinary back falls (SPAfallback) timed too.

python snes_long_fall_check.py ROM OUT [MINUTES]   -> the stretches and a summary (JSON last line)"""
import json
import re
import sys
from pathlib import Path

import lowload
from snes_60fps_cvc import CLOCK, GSP, computer_only
from snes_ot_goal_check import start

SPA, FRAME, PNUM, PFTEAM = 0x11A3, 0x0D97, 0x12A3, 0x1503
GMCLOCK, INJCNT, PENS, TMPDST = 0x15D6, 0x1626, 0x174A, 0x1852
FALLBACK, INJURY1, SA1_SHIFT = 0xF54E, 0xF90E, 0xEA06 - 0xF46A


def patched(rom, out):
    data = bytearray(Path(rom).read_bytes())
    head = len(data) % 0x8000                                          # a copier header
    m = list(re.finditer(rb"\xa9\x96\x00\x22...\x0a\xa4.\x38\xf9..\x10.", bytes(data), re.S))
    assert len(m) == 1, len(m)
    roll = m[0].start()
    back = bytes(data[roll - 40:roll])
    sa1 = len(data) > 0x7FD6 and data[0x7FD5 + head] == 0x23
    fbw = (FALLBACK + (SA1_SHIFT if sa1 else 0)) & 0xFFFF
    cmp_at = back.find(bytes([0xC9, fbw & 0xFF, fbw >> 8, 0xD0]))      # cmp #SPAfallback / bne .23
    assert cmp_at >= 0
    sites = [roll - 40 + cmp_at + 3, roll - 40 + back.find(b"\x29\x03\x00\xd0") + 3, roll + 14]
    for s in sites:
        assert data[s] in (0xD0, 0x10), hex(s)
        data[s:s + 2] = b"\xea\xea"
    # the long fall's jmp: 4C lo hi EA where the jsl setInjuryType was (the 'call' pattern of sneshacks.ts)
    j = [x.start() for x in re.finditer(rb"\x9d......\xa9\x04\x00", bytes(data), re.S)]
    info = {"sites": [hex(s) for s in sites], "header": head}
    for x in j:
        c = x + 3
        if data[c] == 0x4C and data[c + 3] == 0xEA:
            bank = (c - head) // 0x8000
            tgt = bank * 0x8000 + (data[c + 1] | data[c + 2] << 8) - 0x8000 + head
            info["jmp"] = {"at": hex(c), "to": f"${data[c + 2]:02X}{data[c + 1]:02X}", "bytes": data[tgt:tgt + 12].hex()}
        elif data[c] == 0x22:
            info["jsl"] = hex(c)
    p = out / f"{Path(rom).stem}_forced{Path(rom).suffix}"
    p.write_bytes(data)
    return str(p), info


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 10
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    path, info = patched(rom, out)
    print(json.dumps(info), flush=True)
    e, m = start(path, 0, out)
    s = SA1_SHIFT if m.sa1 else 0
    inj, fb = (INJURY1 + s) & 0xFFFF, (FALLBACK + s) & 0xFFFF
    w = m.w
    open_, done, downs, shot = {}, [], [], 0
    pens = lambda: w(PENS) + w(PENS + 2)
    for f in range(int(minutes * 3600)):
        e.run(1)
        if f % 300 == 0:
            computer_only(m)
        if f % 3600 == 0:
            lowload.breathe()
        if w(GSP) >= 3:
            break
        for k in list(range(1, 6)) + list(range(7, 12)):
            a = SPA + 2 * k
            anim = w(a)
            cur = open_.get(k)
            if cur and anim != cur["anim"]:
                cur.update(frames=f - cur["start"], after=f"${anim:04X}", pens_during=pens() - cur["pens0"],
                           clock_end=w(CLOCK))
                del open_[k]
                (done if cur["anim"] == inj else downs).append(cur)
                continue
            if cur:
                sp = w(FRAME + 2 * k)
                if sp != cur["sprites"][-1]:
                    cur["sprites"].append(sp)
                cur["stopped"] |= w(GMCLOCK) != 0
                cur["injcnt"] |= 0 < w(INJCNT) <= 300
                team = w(PFTEAM + 2 * k) != 0
                cur["tmpdst"].add(w(TMPDST + 0x34 * team + 2 * (w(PNUM + 2 * k) & 0xFF)))
                if cur["anim"] == inj and f - cur["start"] == 150 and shot < 4:
                    e.screenshot(out / f"lying_{shot}.png")
                    shot += 1
            elif anim in (inj, fb):
                open_[k] = {"rec": k, "anim": anim, "start": f, "period": w(GSP) + 1, "clock": w(CLOCK),
                            "sprites": [w(FRAME + 2 * k)], "stopped": w(GMCLOCK) != 0, "injcnt": False,
                            "tmpdst": set(), "pens0": pens()}
    for d in done:
        d["tmpdst"] = sorted(f"${x:04X}" for x in d["tmpdst"])
        print(f"long fall: obj {d['rec']} P{d['period']} clock {d['clock']}: {d['frames']} frames, sprites "
              f"{d['sprites']}, then {d['after']}; clock stopped during {d['stopped']}, clock {d['clock']}->"
              f"{d['clock_end']}, InjCntDown set {d['injcnt']}, tmpdst {d['tmpdst']}, penalties during "
              f"{d['pens_during']}", flush=True)
    fr = sorted(x["frames"] for x in downs)
    print(json.dumps({"rom": Path(rom).name, "long_falls": len(done), "long_frames": sorted(x["frames"] for x in done),
                      "back_falls": len(downs), "back_median": fr[len(fr) // 2] if fr else None,
                      "back_frames": fr[:40],
                      "re_knocked": sum(1 for x in done if x["after"] in (f"${inj:04X}", f"${fb:04X}")),
                      "injcnt_set": sum(x["injcnt"] for x in done), "penalty_during": sum(1 for x in done if x["pens_during"]),
                      "off_ice": sum(1 for x in done if any(t != "$FFFF" for t in x["tmpdst"]))}))


if __name__ == "__main__":
    main()
