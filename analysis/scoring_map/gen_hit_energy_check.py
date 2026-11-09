"""NOSE4Web's hit energy option, played (Genesis, 2026-11-09, 36fe502: a knockdown takes energy from the skater
knocked down, a hold or hook that catches takes half, with line changes On). NOSE4Web's changes (the bytes that
differ between retail nhl94.bin and nhl94_hit_energy.bin: FallDown .cont2 at $14116, holdcheck at $13F5C, the code at
$FFAC0-, the checksum call at $301) are laid over a copy of the scoring-map test ROM (its bytes there checked to be
retail's), so the harness's state plays on both. Each trial runs on the unchanged and the changed copy with the same
seed; the difference in the hit player's energy is the option's cost alone (the drain on the ice is the same on both).

Trials (harness: home record 2 on pad 1, the away carrier record 6 30 / 50 units ahead, both facing up, the rest
parked; the pad holds UP and presses a button at frame 5 or 20): C (a body check: burst into him), B (a poke: the
sweep that trips him), A (hook / hold: he flails), each x 8 seeds, with OptLine ($D058) 0 (On), 1 (Off) and 2 (Auto).
Logged: whether he went down (fall animations) or flailed, his energy change over the trial on both ROMs, the home
team's checks stat (+$10) and the checker's per-player checks (+$11C + roster place, the bodycheck count) on both.
Also: the away goalie knocked down by a C check (he is moved in front of the pad skater) and a stumble (the carrier's
working Stickhandling set to 30 and a soft hit, until he stumbles, animation $11E6): no cost.

python gen_hit_energy_check.py OUT RETAIL_ROM NOSE_ROM   (retail nhl94.bin and the option build)"""
import json
import sys
from pathlib import Path

import harness as H
import lowload
from paths import ROM

TEAMS = (0xC6CE, 0xCA32)
DOWN = {0x0D26, 0x0DD8, 0x136A, 0x1776, 0x17E8, 0x185A, 0x18CC, 0x193E, 0x1A00, 0x145C}
FLAIL, STUMBLE = 0x0CF4, 0x11E6


def patched(out, nose, retail):
    a, b = Path(retail).read_bytes(), Path(nose).read_bytes()
    t = bytearray(Path(ROM).read_bytes())
    dif = [k for k in range(len(a)) if a[k] != b[k] and not 0x18E <= k <= 0x18F]
    for k in dif:
        if t[k] == b[k]:                                   # the test ROM is built without the checksum call already
            continue
        # the checksum routine NOSE4Web's code replaces holds the test ROM's own expected sum
        assert t[k] == a[k] or 0xFFAC0 <= k < 0xFFB40, f"test ROM byte {k:#x} differs from retail"
        t[k] = b[k]
    p = out / "hit_energy_test.bin"
    p.write_bytes(t)
    return str(p), len(dif)


def energy(e, k):
    team = 1 if k >= 6 else 0
    return e.w(TEAMS[team] + 0x32 + 2 * e.b(H.rec(k) + 0x66))


def trial(h, button, dy, at, seed, optline, victim=6, setup=None, puck=False):
    e = h.e

    def park():
        for k in range(12):
            if k not in (2, victim) and k != H.GOALIE:
                e.setw(H.rec(k), -100 + 18 * k)
                e.setw(H.rec(k) + 0x14, h.park_y)
                for off in (0x28, 0x2A, 0x2C):
                    e.setw(H.rec(k) + off, 0)
    e.unserialize(h.base)
    e.setw(0xD058, optline)
    for _ in range(30):
        park()
        for k, (x, y) in ((2, (0, 0)), (victim, (0, dy))):
            e.setw(H.rec(k), x)
            e.setw(H.rec(k) + 0x14, y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(k) + off, 0)
        e.setb(H.rec(2) + 0x55, 0)
        e.setb(H.rec(victim) + 0x55, 0)
        if victim == 6 and not puck:
            e.setw(H.PUCKC, 6)
        if setup:
            setup(e)
        e.run(1)
    e.setl(0xD066, seed)
    for t in TEAMS:                                        # both at 3/4 energy, so a cost shows (none at the floor)
        for s in range(26):
            e.setw(t + 0x32 + 2 * s, 0xC00)
    e0 = energy(e, victim)
    chk0 = e.w(TEAMS[0] + 0x10)
    p0 = e.b(TEAMS[0] + 0x11C + e.b(H.rec(2) + 0x66))
    down = flail = stumble = False
    for f in range(70):
        park()
        if setup:
            setup(e)
        if puck and f == at:                               # a fast high puck at him (puckbody: Zpos over 12)
            e.setb(H.PUCK + 0x60, 0xFF)
            e.setw(H.PUCK, 0)
            e.setw(H.PUCK + 0x14, dy - 30)
            e.setw(H.PUCK + 0x18, 20)
            e.setw(H.PUCK + 0x28, 0)
            e.setw(H.PUCK + 0x2A, 0x5000)
            e.setw(H.PUCK + 0x2C, 0)
        e.run(1, hold=["UP"] + ([button] if button and at <= f < at + 3 else []))
        a = e.w(H.rec(victim) + 0x58)
        down |= a in DOWN
        flail |= a == FLAIL
        stumble |= a == STUMBLE
    return dict(down=down, flail=flail, stumble=stumble, de=energy(e, victim) - e0,
                checks=e.w(TEAMS[0] + 0x10) - chk0, pchecks=e.b(TEAMS[0] + 0x11C + e.b(H.rec(2) + 0x66)) - p0)


def run(rom, label):
    h = H.Harness(rom=rom)
    res = []
    for optline in (0, 1, 2):
        for button, places in (("C", [(dy, at) for dy in (30, 50, 70) for at in (5, 15)]),
                               ("B", [(dy, at) for dy in (30, 50, 70) for at in (5, 15)]),
                               ("A", [(30, 5), (50, 5)])):
            for dy, at in places:
                for sd in range(6):
                    r = trial(h, button, dy, at, 0x3000 + 131 * sd + dy + at, optline)
                    res.append(dict(optline=optline, button=button, dy=dy, seed=sd, **r))
            lowload.breathe()
        # the away goalie in front of the pad skater, who bursts into him
        for dy, at in ((50, 10), (70, 10), (50, 20), (70, 20)):
            for sd in range(4):
                r = trial(h, "C", dy, at, 0x5000 + 17 * sd + dy, optline, victim=H.GOALIE)
                res.append(dict(optline=optline, button="C goalie", dy=dy, seed=sd, **r))
        # a stumble: the carrier with working Stickhandling 30 (and no puck lockout) bumped softly (skating, no button)

        def soft(e):
            e.setb(H.rec(6) + 0x71, 30)
            e.setb(H.rec(6) + 0x5F, 0)
        for dy in (20, 30):
            for sd in range(8):
                r = trial(h, None, dy, 0, 0x6000 + 29 * sd + dy, optline, setup=soft)
                res.append(dict(optline=optline, button="skate stumble", dy=dy, seed=sd, **r))
        # a fast high puck into him
        for dy in (60, 80):
            for sd in range(4):
                r = trial(h, None, dy, 3, 0x7000 + 31 * sd + dy, optline, puck=True)
                res.append(dict(optline=optline, button="puck", dy=dy, seed=sd, **r))
    print(label, "done", flush=True)
    return res


def main():
    out = Path(sys.argv[1])
    retail, nose = sys.argv[2], sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    if "--one" in sys.argv:
        rom, label = sys.argv[sys.argv.index("--one") + 1], sys.argv[sys.argv.index("--one") + 2]
        (out / f"{label}.json").write_text(json.dumps(run(rom, label)))
        return
    test, n = patched(out, nose, retail)
    print("bytes laid over the test ROM:", n, flush=True)
    import subprocess
    for rom, label in ((ROM, "unchanged"), (test, "changed")):
        subprocess.run([sys.executable, __file__, str(out), retail, nose, "--one", rom, label], check=True)
    a = json.loads((out / "unchanged.json").read_text())
    b = json.loads((out / "changed.json").read_text())
    from collections import defaultdict
    table = defaultdict(lambda: defaultdict(int))
    for x, y in zip(a, b):
        assert (x["optline"], x["button"], x["seed"]) == (y["optline"], y["button"], y["seed"])
        event = "down" if y["down"] else "flail" if y["flail"] else "stumble" if y["stumble"] else "nothing"
        key = (y["optline"], y["button"], event)
        table[key][f"cost {x['de'] - y['de']:+d}"] += 1        # energy the option took (unchanged minus changed)
        table[key][f"same counts {x['checks'] == y['checks'] and x['pchecks'] == y['pchecks']}"] += 1
        table[key][f"same event {x['down'] == y['down'] and x['flail'] == y['flail']}"] += 1
    for key in sorted(table):
        print(f"OptLine {key[0]}, {key[1]}, {key[2]}: {dict(table[key])}")


if __name__ == "__main__":
    main()
