"""Who takes a loose puck on the SNES (2026-10-19; the Genesis study is analysis/pickup_study.py). NHL94SNES
checkpuckcoll walks the objects sorted by y (Ylist / OOlist) outward from the puck while they are within 40 of it in y,
and checkpuckcoll_ccx skips the carrier, objects past 11, players off the ice, pfnc and any running no-touch timer
(nopuck); pflags $1000 or a puck at height 5+ or rising ($100+) goes to the body test; else a stick within 14 of the
puck (7 while the puck's own nopuck runs; |dx|, |dy| < 15) is puckstick: caught below 10000 (+ 700 x Stk without the
shot flag) + 3000, faster deflected. For every moment a skater's blade (GetHot: the sprite frame's hot point, x
negated when mirrored, y negated) comes within 14 of a loose puck: what the code says and what happened.
python analysis/snes_pickup_study.py [capture folders]"""
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402
from xg_snes import RomData  # noqa: E402

PUCK = 14
XPOS, YPOS, XVEL, YVEL = 0x0D55, 0x0DB7, 0x0EC3, 0x0EE3
PUCKZ, PUCKVZ = 0x0DF9, 0x0E01  # single words, not per object
POSITION, NOPUCK, PFNC, PFLAGS, FRAME, ATTR, STK = 0x0F43, 0x1203, 0x1563, 0x1283, 0x0D97, 0x0E03, 0x1403
PUCKC, SFLAGS, YLIST, OOPOS, OOLIST = 0x0AD9, 0x15D8, 0x1583, 0x15A3, 0x15C3
GMCLOCK = 0x15D6


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def obj(cap, i, base, k):
    return sw(cap.word(i, base + 2 * k))


def walked(cap, i):
    """The objects checkpuckcoll reaches from the puck (y-sorted lists, within 40 of the puck in y)."""
    order = [cap.byte(i, OOLIST + j) // 2 for j in range(16)]
    py = obj(cap, i, YPOS, PUCK)
    got, d = set(), cap.word(i, OOPOS + 2 * PUCK)
    while d < 15 and obj(cap, i, YLIST, order[d + 1]) - py < 40:
        got.add(order[d + 1])
        d += 1
    d = cap.word(i, OOPOS + 2 * PUCK)
    while d > 0 and py - obj(cap, i, YLIST, order[d - 1]) < 40:
        got.add(order[d - 1])
        d -= 1
    return got


def reason(cap, i, k, d2, speed):
    if obj(cap, i, PFNC, k):
        return "no collision (pfnc)"
    if obj(cap, i, NOPUCK, k):
        return "player's no-touch timer"
    if k not in walked(cap, i):
        return "not reached by the walk"
    if obj(cap, i, PFLAGS, k) & 0x1000:
        return "pflags $1000 (body only)"
    if sw(cap.word(i, PUCKZ)) >= 5:
        return "too high (5 or more)"
    if sw(cap.word(i, PUCKVZ)) >= 0x100:
        return "rising"
    if d2 > (49 if obj(cap, i, NOPUCK, PUCK) > 0 else 196):
        return "beyond reach (puck's timer: 7)"
    shot = cap.word(i, SFLAGS) & 0x1000
    limit = 10000 + (0 if shot else 700 * obj(cap, i, STK, k)) + 3000
    if speed > limit:
        return "too fast: deflects"
    return "catch"


def study(folder, data, tab, timers):
    cap = Capture(Path(folder))
    open_ = {}

    def close(k, i):
        i0, rs, v0 = open_.pop(k)
        took = any(cap.word(j, PUCKC) == 2 * k for j in range(i0, min(cap.count, i + 2)))
        j = min(cap.count - 1, i + 1)
        v2 = (obj(cap, j, XVEL, PUCK), obj(cap, j, YVEL, PUCK))
        out = "took it" if took else "deflected" if math.hypot(v2[0] - v0[0], v2[1] - v0[1]) > 1500 else "went through"
        tab[("catch" if "catch" in rs else rs[0], out)] += 1

    for i in range(cap.count - 3):
        if sw(cap.word(i, PUCKC)) >= 0 or cap.word(i, GMCLOCK):
            for k in list(open_):
                close(k, i)
            continue
        px, py = obj(cap, i, XPOS, PUCK), obj(cap, i, YPOS, PUCK)
        vx, vy = obj(cap, i, XVEL, PUCK), obj(cap, i, YVEL, PUCK)
        speed = math.hypot(vx, vy)
        for k in range(12):
            near = False
            fr = obj(cap, i, FRAME, k)
            if obj(cap, i, POSITION, k) > 0 and fr > 0:
                h = data.hot(fr)
                if h:
                    hx, hy = h[0], h[1]
                    if obj(cap, i, ATTR, k) & 0x0800:
                        hx = -hx
                    dx = obj(cap, i, XPOS, k) + hx - px
                    dy = obj(cap, i, YPOS, k) + hy - py
                    near = abs(dx) < 15 and abs(dy) < 15 and dx * dx + dy * dy <= 196
            if not near:
                if k in open_:
                    close(k, i)
                continue
            r = reason(cap, i, k, dx * dx + dy * dy, speed)
            if r == "player's no-touch timer":
                timers[obj(cap, i, NOPUCK, k)] += 1
            if k not in open_:
                open_[k] = [i, [], (vx, vy)]
            open_[k][1].append(r)


def main():
    rom_dir = Path.home() / "Documents/NHL94 Viewer/roms"
    folders = sys.argv[1:] or [str(p) for p in sorted((Path.home() / "Documents/NHL94 Viewer/captures").glob("20*"))
                               if '"system": "snes"' in (p / "capture.json").read_text()]
    tab, timers, roms = Counter(), Counter(), {}
    for f in folders:
        import json
        crc = json.loads((Path(f) / "capture.json").read_text()).get("rom_crc32")
        crc = crc[0] if isinstance(crc, list) else crc
        hits = sorted(rom_dir.glob(f"{crc}*.smc"))
        if not hits:
            print("no ROM for", f)
            continue
        data = roms.setdefault(crc, RomData(hits[0].read_bytes()))
        study(f, data, tab, timers)
    rows = defaultdict(Counter)
    for (r, out), n in tab.items():
        rows[r][out] += n
    for r, c in sorted(rows.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"{r:34} {sum(c.values()):5}  took {c['took it']:4}  deflected {c['deflected']:4}  went through {c['went through']:4}")


if __name__ == "__main__":
    main()
