"""Trace a Genesis goal (or any moment) sample by sample from the raw recording: the puck (position, height, velocity,
vertical speed, carrier, its own no-touch timer) and the goalie it goes past (position, animation, frame, stick blade,
distance from his centre and from his blade, his no-touch timer), with what checkpuckcoll would do each sample.
python analysis/goal_trace.py <capture folder> <period> <m:ss> [seconds before, default 2] [seconds after, default 1]"""
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

BASE, SIZE, PUCK, HOTLIST = 0xB04A, 0x80, 14, 0xA44C8


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def rec(k, off):
    return BASE + SIZE * k + off


def main():
    folder, period, mmss = Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    before = float(sys.argv[4]) if len(sys.argv) > 4 else 2
    after = float(sys.argv[5]) if len(sys.argv) > 5 else 1
    secs = int(mmss.split(":")[0]) * 60 + int(mmss.split(":")[1])
    cap = Capture(folder)
    import json
    crc = json.loads((folder / "capture.json").read_text())["rom_crc32"][0]
    rom = next((d / f.name for d in (Path.home() / "Documents/NHL94 Viewer/roms", Path("roms")) if d.exists()
                for f in d.glob(f"{crc}*.bin")), None)
    R = rom.read_bytes()
    # the sample where the clock reads that time in that period (the last one)
    hit = [i for i in range(cap.count) if cap.word(i, 0xC466) == period - 1 and cap.word(i, 0xC468) == secs]
    if not hit:
        print("no such moment")
        return
    centre = hit[0]  # the first sample at that time (the clock reads it again at the faceoff after a goal)
    t0 = cap.ms(centre)
    for i in range(cap.count):
        if not (t0 - before * 1000 <= cap.ms(i) <= t0 + after * 1000):
            continue
        px, py, pz = (sw(cap.word(i, rec(PUCK, o))) for o in (0, 0x14, 0x18))
        vx, vy, vz = (sw(cap.word(i, rec(PUCK, o))) for o in (0x28, 0x2A, 0x2C))
        owned = cap.byte(i, rec(PUCK, 0x60)) == 0
        holder = cap.byte(i, rec(PUCK, 0x61))
        # the goalie nearer the puck
        gs = [k for k in range(12) if cap.byte(i, rec(k, 0x35)) == 0]
        g = min(gs, key=lambda k: abs(sw(cap.word(i, rec(k, 0x14))) - py)) if gs else None
        line = f"{cap.ms(i) - t0:+6d}ms clock {cap.word(i, 0xC468) // 60}:{cap.word(i, 0xC468) % 60:02d} puck ({px:4},{py:4}) z{pz:3} v({vx:6},{vy:6}) vz{vz:6} "
        line += (f"held by {holder:2}" if owned else "loose     ") + f" puckTimer {cap.byte(i, rec(PUCK, 0x5E)):2}"
        if g is not None:
            gx, gy = sw(cap.word(i, rec(g, 0))), sw(cap.word(i, rec(g, 0x14)))
            fr = cap.word(i, rec(g, 6))
            hx, hy = struct.unpack_from(">bb", R, HOTLIST + 2 * fr) if 0 < fr < 900 else (0, 0)
            if not cap.byte(i, rec(g, 0x76)) & 1:
                hx = -hx
            bx, by = gx + hx, gy - hy
            db = math.hypot(px - bx, py - by)
            d = math.hypot(px - gx, py - gy)
            note = ""
            if pz <= 5 and vz <= 0x200 and abs(bx - px) <= 14 and abs(by - py) <= 14 and db <= 14:
                note = "STICK plays it" if db <= 8 else "BLIND (stick ring)"
            elif pz <= 15 and d <= 15:
                note = "body (if within his reach)"
            line += f" | G{g} ({gx:4},{gy:4}) anim {cap.word(i, rec(g, 0x58)):04x} fr{fr:3} blade({bx:4},{by:4}) d{d:5.1f} dBlade{db:5.1f} Gtimer {cap.byte(i, rec(g, 0x5E)):2} {note}"
        print(line)


if __name__ == "__main__":
    main()
