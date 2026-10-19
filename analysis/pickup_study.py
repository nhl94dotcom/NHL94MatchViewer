"""When does a skater or goalie take a loose puck? (2026-10-18, the user: sometimes a magnet in the stick, sometimes the
puck goes right through.) Genesis checkpuckcoll .ccx / puckstick, tested sample by sample on raw recordings:
for every player whose stick blade (GetHot) comes within the game's reach of a loose puck, what the code says should
happen, and what did. python analysis/pickup_study.py [capture folders]  (default: the BOS-DAL games, which hold sflags2)"""
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

BASE, SIZE, PUCK = 0xB04A, 0x80, 14
HOTLIST = 0xA44C8
SFLAGS2 = 0xC2EE
ROM = None


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def sb(v):
    return v - 0x100 if v >= 0x80 else v


def rec(k, off):
    return BASE + SIZE * k + off


def hot(frame):
    return struct.unpack_from(">bb", ROM, HOTLIST + 2 * frame)


def walked(cap, i):
    """The objects checkpuckcoll's walk reaches from the puck (the game's own lists: Ylist $B84A, OOlistpos $B86A, OOlist
    $B88A), compared exactly as the code does: each neighbour's Ylist entry against the puck's word at +$14."""
    Y = [sw(cap.word(i, 0xB84A + 2 * o)) for o in range(16)]
    pos = [cap.word(i, 0xB86A + 2 * o) for o in range(16)]
    order = [cap.byte(i, 0xB88A + j) // 2 for j in range(16)]
    py = sw(cap.word(i, rec(PUCK, 0x14)))
    got, d1 = set(), pos[PUCK]
    while d1 < 15 and Y[order[d1 + 1]] - py <= 22:
        got.add(order[d1 + 1])
        d1 += 1
    d1 = pos[PUCK]
    while d1 > 0 and py - Y[order[d1 - 1]] <= 22:
        got.add(order[d1 - 1])
        d1 -= 1
    return got


def reason(cap, i, k, d2, puck_nopuck, speed, z, zvel, shot):
    """What the code does with this player and this puck this frame (in .ccx / puckstick order)."""
    if k not in walked(cap, i):
        return "not reached by the walk"
    pfl, pfl2 = cap.byte(i, rec(k, 0x62)), cap.byte(i, rec(k, 0x63))
    if pfl & 0x04:
        return "no collision (pfnc)"
    if cap.byte(i, rec(k, 0x5E)):
        return "player's no-touch timer"
    if pfl2 & 0x04:
        return "unavailable"
    if z > 5:
        return "too high (above 5)"
    if zvel > 0x200:
        return "rising"
    if d2 > (49 if puck_nopuck else 196):
        return "beyond reach (puck's timer: 7)"
    goalie = cap.byte(i, rec(k, 0x35)) == 0
    if goalie and d2 > 64:
        return "goalie: 8-14 from his stick (nothing)"
    limit = 13000 if shot else 13000 + 350 * cap.byte(i, rec(k, 0x71))
    if speed > limit:
        return "too fast: deflects"
    return "catch"


def study(folder, tab, examples):
    """Each contact (a stretch of samples with the player's blade within 14 of a loose puck) is predicted a catch when
    any of its samples passes every test, else blocked by the reason of its first sample."""
    cap = Capture(Path(folder))
    open_ = {}  # player -> [first sample, reasons, puck velocity at the start, distance]

    def close(k, i):
        i0, rs, v0, d, who = open_.pop(k)
        took = any(cap.byte(j, rec(PUCK, 0x60)) == 0 and cap.byte(j, rec(PUCK, 0x61)) == k
                   for j in range(i0, min(cap.count, i + 2)))
        j = min(cap.count - 1, i + 1)
        v2 = (sw(cap.word(j, rec(PUCK, 0x28))), sw(cap.word(j, rec(PUCK, 0x2A))))
        out = "took it" if took else "deflected" if math.hypot(v2[0] - v0[0], v2[1] - v0[1]) > 1500 else "went through"
        r = "catch" if "catch" in rs else rs[0]
        tab[(who, r, out)] += 1
        if r == "catch" and out == "went through":
            examples.append((Path(folder).name, i0, k, d, len(rs)))

    for i in range(cap.count - 3):
        if cap.byte(i, 0xFFF7) or cap.byte(i, rec(PUCK, 0x60)) != 0xFF or cap.byte(i, 0xC2EC) & 0x80:  # (sfhor: stoppage screens)
            for k in list(open_):
                close(k, i)
            continue
        px, py = sw(cap.word(i, rec(PUCK, 0x1C))), sw(cap.word(i, rec(PUCK, 0x20)))
        z, zvel = sw(cap.word(i, rec(PUCK, 0x24))), sw(cap.word(i, rec(PUCK, 0x2C)))
        if z < -100:
            continue
        vx, vy = sw(cap.word(i, rec(PUCK, 0x28))), sw(cap.word(i, rec(PUCK, 0x2A)))
        speed = math.hypot(vx, vy)
        puck_nopuck = cap.byte(i, rec(PUCK, 0x5E))
        shot = bool(cap.byte(i, SFLAGS2) & 0x10)
        for k in range(12):
            role = cap.byte(i, rec(k, 0x35))
            fr = cap.word(i, rec(k, 0x06))
            near = False
            if role != 0xFF and 0 < fr < 900:
                hx, hy = hot(fr)
                if not cap.byte(i, rec(k, 0x76)) & 1:
                    hx = -hx
                x, y = sw(cap.word(i, rec(k, 0x1C))), sw(cap.word(i, rec(k, 0x20)))
                dx, dy = x + hx - px, y - hy - py
                near = abs(dx) <= 14 and abs(dy) <= 14 and dx * dx + dy * dy <= 196
            if not near:
                if k in open_:
                    close(k, i)
                continue
            r = reason(cap, i, k, dx * dx + dy * dy, puck_nopuck, speed, z, zvel, shot)
            if k not in open_:
                open_[k] = [i, [], (vx, vy), round(math.sqrt(dx * dx + dy * dy), 1), "goalie" if role == 0 else "skater"]
            open_[k][1].append(r)


def main():
    global ROM
    ROM = (Path.home() / "RetroArch-1.17-Win64/ROMs/Genesis/nhl94.bin").read_bytes()
    folders = sys.argv[1:] or sorted(str(p) for p in (Path.home() / "Documents/NHL94 Viewer/captures").glob("2026-10-17_22*"))
    tab, examples = Counter(), []
    for f in folders:
        study(f, tab, examples)
    rows = defaultdict(Counter)
    for (who, r, out), n in tab.items():
        rows[(who, r)][out] += n
    for (who, r), c in sorted(rows.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(c.values())
        print(f"{who:6} {r:38} {n:5}  took {c['took it']:4}  deflected {c['deflected']:4}  went through {c['went through']:4}")
    print("\npredicted catches that went through (folder, sample, record, distance, height, speed):")
    for e in examples[:25]:
        print(*e)


if __name__ == "__main__":
    main()
