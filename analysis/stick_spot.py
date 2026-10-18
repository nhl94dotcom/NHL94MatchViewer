"""Where a skater's stick blade is (Genesis GetHot: HotList at ROM $A44C8, an (x, y) byte pair per sprite frame; x
negated when the picture is mirrored, y negated unless the frame is flipped vertically; added to his position). Checked
by catches: at the moment a skater takes a loose moving puck the game needs it within 14 units of his blade. Prints the
distance at catches for each reading of the table, to find the right one. python analysis/stick_spot.py"""
import glob
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402

ROM = Path(r"C:/Users/USER/RetroArch-1.17-Win64/ROMs/Genesis/nhl94.bin").read_bytes()
HOTLIST = 0xA44C8
K = 12


def hot(frame, offset=0):
    at = HOTLIST + 2 * (frame + offset)
    return struct.unpack_from(">bb", ROM, at)


def catches(m):
    """(sample, record) where a skater took a loose puck that was moving (a pass, a shot, a loose puck)."""
    own, V = m["owner"], m["puckV"]
    for i in range(3, len(m["t"])):
        k = own[i]
        if k < 0 or own[i - 1] >= 0 or m["role"][i * K + k] in "0x":
            continue
        if math.hypot(V[2 * (i - 1)] * 100, V[2 * (i - 1) + 1] * 100) < 3000:
            continue
        yield i, k


if __name__ == "__main__":
    files = {}
    for p in glob.glob("matches/*.js") + glob.glob(r"C:/Users/USER/Documents/NHL94 Viewer/matches/*.js"):
        if not p.endswith(".summary.json") and Path(p).name not in ("season.js", "shot_study.json"):
            files.setdefault(Path(p).name, p)
    variants = {(sx, sy, off): [] for sx in (1, -1) for sy in (1, -1) for off in (0, -1)}
    body = []
    for name, p in sorted(files.items()):
        try:
            m = json.loads(load_js_object(Path(p)))
        except Exception:
            continue
        if m.get("system", "genesis") != "genesis" or "puckV" not in m or m.get("rom") != "9438f5dd":
            continue
        P = m["puck"]
        for i, k in catches(m):
            best = {v: 99 for v in variants}
            bd = 99
            for q in (i - 1, i - 2, i - 3):  # the puck may be caught between samples
                fr = int(m["frame"][(q * K + k) * 3:(q * K + k) * 3 + 3], 16)
                if fr <= 0:
                    continue
                mir = m["mirror"][q * K + k] == "1"
                x, y = m["pos"][(q * K + k) * 2], m["pos"][(q * K + k) * 2 + 1]
                px, py = P[3 * q], P[3 * q + 1]
                bd = min(bd, math.hypot(px - x, py - y))
                for (sx, sy, off) in variants:
                    hx, hy = hot(fr, off)
                    hx = -hx if mir else hx
                    d = math.hypot(px - (x + sx * hx), py - (y + sy * hy))
                    best[(sx, sy, off)] = min(best[(sx, sy, off)], d)
            for v in variants:
                variants[v].append(best[v])
            body.append(bd)
    n = len(body)
    med = lambda v: sorted(v)[len(v) // 2]
    print(f"{n} catches; puck to his centre: median {med(body):.1f}, within 14: {sum(d <= 14 for d in body)}")
    for (sx, sy, off), v in sorted(variants.items(), key=lambda kv: med(kv[1])):
        print(f"x {'+' if sx > 0 else '-'}, y {'+' if sy > 0 else '-'}, frame{off:+d}: median {med(v):.1f}, within 14: {sum(d <= 14 for d in v)} ({100 * sum(d <= 14 for d in v) / n:.0f}%), within 8: {sum(d <= 8 for d in v)}")
