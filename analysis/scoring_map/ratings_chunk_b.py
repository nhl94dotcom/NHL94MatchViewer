"""RATING_VALUES chunk B (2026-11-11): what a rating step does, played in the game (Genesis test ROM). One process,
gentle (the user: keep the emulator free for NOSE4Web's checks).

python ratings_chunk_b.py OUT shots [moments]
    Standing shots from three spots at the top net, against a typical retail starter (working Agility / Speed /
    Defensive Awareness / Puck Control 20 / 20 / 25 / 20: harness NHL94_GOALIE): the slot (straight in, 21 ft out),
    the left circle (21 ft out, 21 ft to the side), the left point (62 ft out, 29 ft to the side). Wrist shot and
    slapshot, all nine aims, `moments` set-ups (the clock and settle cycles of the maps) x 2 release seeds. Shot Power
    2-6 at Accuracy 4, and Accuracy 2-6 at Power 4 (working = roster x 5). -> OUT/shots.json, and a table printed:
    each spot and shot's best aim and the average over the aims.
python ratings_chunk_b.py OUT races
    The pad-1 skater without the puck from a standstill, and from top speed the wrong way: the time to cover 20, 40,
    60 and 100 ft, by Speed 2-6, Agility 2-6 and Weight (the others the test skater's). -> OUT/races.json
python ratings_chunk_b.py OUT steals [N]
    Pokes: an away carrier standing still with the puck, the pad-1 skater beside him (stick in reach, bodies apart)
    tapping B, N seeds: how often the puck comes loose, by the carrier's Stickhandling (the poker at 15) and by the
    poker's (the carrier at 15). -> OUT/steals.json"""
import json
import os
import random
import sys
import zlib
from pathlib import Path

from lowload import breathe, gentle

SPOTS = {"slot": (0, 200), "circle": (-66, 200), "point": (-90, 75)}
KINDS = {"wrist": 3, "slap": 20}
RETAIL_GOALIE = "20,20,25,20"
COMBOS = [(p, 4) for p in (2, 3, 4, 5, 6)] + [(4, a) for a in (2, 3, 5, 6)]


def shots(out, moments):
    os.environ["NHL94_GOALIE"] = RETAIL_GOALIE
    import goal_types as G
    from mapper import set_ratings
    G._init("genesis")
    o = G.S["o"]
    h = o.h["top"]
    path = out / "shots.json"
    res = json.loads(path.read_text()) if path.exists() else {}
    for shp, sha in COMBOS:
        key = f"{shp},{sha}"
        if key in res:
            continue
        cell = {}
        for spot, (x, y) in SPOTS.items():
            for kind, hold in KINDS.items():
                rnd = random.Random(zlib.crc32(f"{spot},{kind}".encode()))
                by_aim = [[0, 0] for _ in range(9)]
                for p in range(moments):
                    o.setup("top", x, y, p, rnd)
                    set_ratings(h, 5 * shp, 5 * sha)
                    settled = h.e.serialize()
                    for aim in range(9):
                        h.e.unserialize(settled)
                        pre = o.shoot("top", aim, hold)
                        if pre is None:
                            continue
                        for s in range(2):
                            o.fire("top", pre, aim, rnd.getrandbits(32))
                            g, _ = G.play(o, "top")
                            by_aim[aim][0] += g
                            by_aim[aim][1] += 1
                    breathe()
                cell[f"{spot},{kind}"] = by_aim
        res[key] = cell
        path.write_text(json.dumps(res))
        print(f"done Power {shp} / Accuracy {sha}", flush=True)
    report_shots(res)


def report_shots(res):
    rows = []
    for spot in SPOTS:
        for kind in KINDS:
            line = []
            for shp, sha in COMBOS:
                by_aim = res[f"{shp},{sha}"][f"{spot},{kind}"]
                rates = [g / n for g, n in by_aim if n]
                best = max(rates) if rates else 0
                avg = sum(g for g, _ in by_aim) / max(1, sum(n for _, n in by_aim))
                line.append(f"{shp}/{sha}: best {100 * best:.0f}% avg {100 * avg:.1f}%")
            rows.append(f"{spot} {kind}: " + "; ".join(line))
    print("\n".join(rows))


def races(out):
    gentle()
    from harness import Harness
    from paths import STATE_TOP
    import rating_gifs as RG
    h = Harness(state=STATE_TOP)
    WGT, BASE = 72, 18
    cases = [("Speed", s, (WGT, BASE, 5 * s)) for s in (2, 3, 4, 5, 6)] + \
            [("Agility", a, (WGT, 5 * a, BASE)) for a in (2, 3, 4, 5, 6)] + \
            [("Weight", w, (8 * w, BASE, BASE)) for w in (4, 7, 9, 12, 15)]
    res = {}
    for name, lvl, (wgt, agl, spd) in cases:
        cap = (20 + min(spd + 2, 30) // 2) * 275
        out_t = {}
        for start, (tr_kw) in (("standstill", dict(start_speed=0)),
                                ("wrong way", dict(start_speed=-cap))):
            tr = RG.skate_run(h, wgt, agl, spd, 240, **tr_kw)
            y0 = tr[0][0]
            times = {}
            for ft in (20, 40, 60, 100):
                hit = next((i for i, (y, _) in enumerate(tr) if (y - y0) / RG.UNITS_PER_FT >= ft), None)
                times[ft] = hit
            out_t[start] = times
        res[f"{name} {lvl}"] = out_t
        print(name, lvl, out_t, flush=True)
        breathe()
    (out / "races.json").write_text(json.dumps(res))


def steals(out, n):
    gentle()
    from harness import Harness, rec, PUCK, PUCKC
    from paths import STATE_TOP
    h = Harness(state=STATE_TOP)
    e = h.e
    me, carrier = rec(2), rec(8)
    SEED = 0xD066
    res = {}

    def park():
        for k in range(12):
            if k in (2, 8, 11):
                continue
            e.setw(rec(k), -100 + 18 * k)
            e.setw(rec(k) + 0x14, -230)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)

    def setup(stk_carrier, stk_me):
        e.unserialize(h.base)
        for _ in range(10):                        # held still a while: the y-sorted list catches up
            park()
            e.setw(carrier, 0)
            e.setw(carrier + 0x14, 60)
            e.setw(me, 0)
            e.setw(me + 0x14, 38)                  # 22 below him: the stick in reach, the bodies apart
            for r in (carrier, me):
                for off in (0x28, 0x2A):
                    e.setw(r + off, 0)
            e.setw(PUCKC, 8)                       # he carries it
            e.setb(carrier + 0x71, stk_carrier)       # stickhand $71
            e.setb(me + 0x71, stk_me)
            e.run(1, hold=["UP"])
        return e.serialize()

    for who, levels in (("carrier", [(5 * s, 15) for s in (2, 3, 4, 5, 6)]), ("poker", [(15, 5 * s) for s in (2, 3, 4, 5, 6)])):
        for stk_c, stk_m in levels:
            base = setup(stk_c, stk_m)
            loose = 0
            for k in range(n):
                e.unserialize(base)
                e.setw(SEED, (1000 + 7919 * k) & 0xFFFF)
                e.setw(SEED + 2, ((1000 + 7919 * k) >> 4) | 1)
                lost = False
                for f in range(30):
                    park()
                    for off in (0x28, 0x2A):
                        e.setw(carrier + off, 0)
                    e.run(1, hold=["B"] if f < 3 else [])
                    if e.w(PUCKC) != 8:
                        lost = True
                        break
                loose += lost
            res[f"{who} carrier {stk_c} poker {stk_m}"] = [loose, n]
            print(who, stk_c, stk_m, loose, "/", n, flush=True)
            breathe()
    (out / "steals.json").write_text(json.dumps(res))


def main():
    out, what = Path(sys.argv[1]), sys.argv[2]
    out.mkdir(parents=True, exist_ok=True)
    if what == "shots":
        gentle()
        shots(out, int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif what == "races":
        races(out)
    elif what == "steals":
        steals(out, int(sys.argv[3]) if len(sys.argv) > 3 else 40)
    elif what == "report":
        report_shots(json.loads((out / "shots.json").read_text()))


if __name__ == "__main__":
    main()
