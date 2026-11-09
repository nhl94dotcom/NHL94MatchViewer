"""NOSE4Web's hit energy option on the SNES, played (2026-11-09, 9d3695f: a knockdown takes 100 from the skater
knocked down, a hold or hook that catches 50, with line changes on; gen_hit_energy_check.py is the Genesis one).

Each trial runs on the unchanged ROM and the option build from the same state (the unchanged ROM's live-play states,
saved and loaded into the build), so the difference in the hit player's energy is the option's cost alone. In live
play (snes_assist_stick_test.Game): the pad-1 skater A and an opponent O ahead of him (dy units, toward the net A
attacks), O given the puck (it put on his stick and held there 30 frames), everyone else parked (on the SA-1 build
all of it done once: players put in place every frame there stay frozen); both at 3/4
energy; then A skates at him (the direction held) and presses A (the burst / body check), B (the poke) or Y (hook /
hold) at frame `at`. Also: their goalie in front of A (a body check), and a fast high puck sent at O (puckbody).
Logged: O going down (SPA in the fall animations $F49C / $F54E / $F6C0), knockdowns by anyone (the teams' checks
stat $17B6 / $17B8, which FallDown counts), O flailing (SPA $11A3 = SPAflail:
$F46A retail, $EA06 on the SA-1 build), O's energy change (tmpde $17EA, the visitors +$34, by his pnum), with
OptLine ($34C6) 0 (Off), 1 (On), 2 (Auto).

python snes_hit_energy_check.py OUT ORIGINAL_ROM OPTION_ROM"""
import json
import pickle
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import lowload
from snes_assist_stick_test import Game, POSITION, PUCK, ZPOS

OPTLINE, TMPDE, CHECKS, SPA, PNUM, FACE, PFTEAM = 0x34C6, 0x17EA, 0x17B6, 0x11A3, 0x12A3, 0x1163, 0x1503
SEED = 0x0792


def trial(G, base, button, dy, at, seed, optline, kind="skater"):
    e = G.e
    e.unserialize(base)
    G.setw(OPTLINE, optline)
    a, team, up = G.me()
    opp_team = 1 - team
    if kind == "goalie":
        o = next(k for k in range(opp_team * 6, opp_team * 6 + 6) if G.w(POSITION + 2 * k) == 0)
    else:
        o = next(k for k in range(opp_team * 6, opp_team * 6 + 6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    keep = {a, o}

    def park():
        for k in range(12):
            if k not in keep and G.w(POSITION + 2 * k) not in (0xFFFF,):
                G.put(k, -100 + 18 * (k % 6) + (10 if k >= 6 else 0), -230 * up if k != o else 0)

    way = "UP" if up > 0 else "DOWN"
    once = G.g.sa1        # the SA-1 build: players put in place every frame stay frozen there, so put them once
    for f in range(30 if not once else 1):
        park()
        G.put(a, 0, 0)
        G.put(o, 0, dy * up)
        G.setw(FACE + 2 * a, 0 if up > 0 else 4)
        G.setw(FACE + 2 * o, 0 if up > 0 else 4)
        if kind == "skater":
            G.put(PUCK, 0, dy * up + 6 * up)
            G.setw(ZPOS, 0)
        G.run()
    G.setw(SEED, (0x9E37 * (seed + 1)) & 0xFFFF or 1)
    G.setw(SEED + 2, (0x7F4A * (seed + 3)) & 0xFFFF or 1)
    for t in range(2):
        for s in range(26):
            G.setw(TMPDE + 0x34 * t + 2 * s, 0xC00)
    slot = lambda k: (TMPDE + 0x34 * (1 if G.w(PFTEAM + 2 * k) else 0) + 2 * (G.w(PNUM + 2 * k) & 0xFF))
    e0 = G.w(slot(o))
    c0 = (G.w(CHECKS), G.w(CHECKS + 2))
    shift = (0xEA06 - 0xF46A) if G.g.sa1 else 0                # the SA-1 build's animation words, moved as one table
    flail_word, falls = 0xF46A + shift, {(w + shift) & 0xFFFF for w in (0xF49C, 0xF54E, 0xF6C0)}
    flail = down = False
    if once:
        G.run(6)
    for f in range(70):
        if not once:
            park()
        if kind == "puck" and f == at:
            G.put(PUCK, 0, (dy - 30) * up, 0, 0x5000 * up)
            G.setw(ZPOS, 20)
        G.run(hold=[way] + ([button] if button and at <= f < at + 3 else []))
        flail |= G.w(SPA + 2 * o) == flail_word
        down |= G.w(SPA + 2 * o) in falls
    c1 = (G.w(CHECKS), G.w(CHECKS + 2))
    return dict(knock=(c1[0] - c0[0]) + (c1[1] - c0[1]), down=down, flail=flail, de=G.w(slot(o)) - e0, checks=list(c1))


def run(rom, out, label, bases_file):
    G = Game(rom)
    if bases_file.exists():
        G.g.bases = pickle.loads(bases_file.read_bytes())
    else:
        bases_file.write_bytes(pickle.dumps([bytes(b) for b in G.g.bases]))
    res = []
    for optline in (0, 1, 2):
        for bi, base in enumerate(G.g.bases[:2]):
            for button, places in (("A", [(dy, at) for dy in (30, 50, 70) for at in (5, 15)]),
                                   ("B", [(dy, at) for dy in (30, 50) for at in (5, 15)]),
                                   ("Y", [(30, 5), (50, 5)])):
                for dy, at in places:
                    for sd in range(3):
                        r = trial(G, base, button, dy, at, sd + 7 * dy + at, optline)
                        res.append(dict(optline=optline, base=bi, what=button, dy=dy, at=at, seed=sd, **r))
            for dy, at in ((50, 10), (70, 10)):
                for sd in range(3):
                    r = trial(G, base, "A", dy, at, sd + dy, optline, kind="goalie")
                    res.append(dict(optline=optline, base=bi, what="A goalie", dy=dy, at=at, seed=sd, **r))
            for dy in (60, 80):
                for sd in range(3):
                    r = trial(G, base, None, dy, 3, sd + dy, optline, kind="puck")
                    res.append(dict(optline=optline, base=bi, what="puck", dy=dy, at=3, seed=sd, **r))
            lowload.breathe()
    (out / f"{label}.json").write_text(json.dumps(res))


def main():
    if sys.argv[1] == "--one":
        run(sys.argv[2], Path(sys.argv[3]), sys.argv[4], Path(sys.argv[5]))
        return
    out, original, option = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    bases = out / "bases.pkl"
    for rom, label in ((original, "unchanged"), (option, "changed")):
        subprocess.run([sys.executable, __file__, "--one", rom, str(out), label, str(bases)], check=True)
    a = json.loads((out / "unchanged.json").read_text())
    b = json.loads((out / "changed.json").read_text())
    table = defaultdict(lambda: defaultdict(int))
    for x, y in zip(a, b):
        event = ("he went down" if y["down"] else "someone else went down" if y["knock"] else
                 "he flailed" if y["flail"] else "nothing")
        key = (y["optline"], y["what"], event)
        table[key][f"cost {x['de'] - y['de']:+d}"] += 1
        table[key][f"same counts {x['checks'] == y['checks']}"] += 1
        table[key][f"same event {(x['knock'], x['flail']) == (y['knock'], y['flail'])}"] += 1
    for key in sorted(table):
        print(f"OptLine {key[0]}, {key[1]}, {key[2]}: {dict(table[key])}")


if __name__ == "__main__" and sys.argv[1] != "--natural":
    main()


def natural(rom, frames=7200, optline=1):
    """The computer on both sides from the first live state, OptLine as given (1, On, by default): each time a skater goes
    down (the fall animations) or starts to flail, his energy from the frame before to 3 frames after. Prints the
    changes counted by kind."""
    import snes_60fps_cvc as cvc
    G = Game(rom)
    e = G.e
    e.unserialize(G.g.bases[0])
    G.setw(OPTLINE, optline)
    shift = (0xEA06 - 0xF46A) if G.g.sa1 else 0
    flail_word, falls = 0xF46A + shift, {(w + shift) & 0xFFFF for w in (0xF49C, 0xF54E, 0xF6C0)}
    slot = lambda k: (TMPDE + 0x34 * (1 if G.w(PFTEAM + 2 * k) else 0) + 2 * (G.w(PNUM + 2 * k) & 0xFF))
    prev = [G.w(SPA + 2 * k) for k in range(12)]
    out = defaultdict(lambda: defaultdict(int))
    pending = []
    for f in range(frames):
        if f % 300 == 0:
            cvc.computer_only(G)
        before = [G.w(slot(k)) for k in range(12)]
        G.run()
        for k in range(12):
            w = G.w(SPA + 2 * k)
            if w != prev[k] and G.w(POSITION + 2 * k) not in (0, 0xFFFF):
                if w in falls:
                    pending.append((f + 3, k, "down", before[k]))
                elif w == flail_word:
                    pending.append((f + 3, k, "flail", before[k]))
            prev[k] = w
        for p in [p for p in pending if p[0] == f]:
            out[p[2]][G.w(slot(p[1])) - p[3]] += 1
            pending.remove(p)
        if f % 1800 == 0:
            lowload.breathe()
    print(rom.split("/")[-1], "OptLine", optline, {k: dict(v) for k, v in out.items()}, flush=True)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "--natural":
    natural(sys.argv[2], optline=int(sys.argv[3]) if len(sys.argv) > 3 else 1)
