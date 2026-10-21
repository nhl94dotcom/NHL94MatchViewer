"""How quickly Genesis computer skaters throw a check, penalties on against off (2026-10-21; GENESIS_MECHANICS 12.3).
Code (check4check, reached every frame from the chasing and defending assignments): each frame a computer skater goes
for a check when randomd0(40 - Checking, doubled with penalties on) <= 6, and then only at an opponent skater within 30
units both ways exactly in the direction he faces (vtoa = facedir), not locked in an animation; then a burst (3 in 4)
or a hook / hold. So penalties on should halve the chance a frame. Measured: stretches where a computer skater has such
a target (an "opening"), and whether / how soon he bursts ($0C5E) or hooks ($1122); OptPen ($D056, read from the
recording's full RAM snapshots: 0 off, 2 on).
python analysis/cpu_check_study.py"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, "analysis")
import systems  # noqa: E402
from export_match import Capture  # noqa: E402
from share_game import load_js_object  # noqa: E402
from tangle_study import games  # noqa: E402

K = 12
OPT_PEN = 0xD056
BURST, HOOK = "0c5e", "1122"
LOCKED = {"0dd8", "0d26", "136a", "1776", "17e8", "185a", "18cc", "193e", "1a00", "0b96", "0bc8", "0bfa", "0c2c",
          "0c5e", "1122", "07fc", "092e", "0718", "078a"}


def vtoa(dx, dy):
    """The game's direction 0-7 (0 up the screen, clockwise): diagonal when neither part is more than twice the other."""
    ax, ay = abs(dx), abs(dy)
    if ax > 2 * ay:
        return 2 if dx > 0 else 6
    if ay > 2 * ax:
        return 0 if dy > 0 else 4
    if dx > 0:
        return 1 if dy > 0 else 3
    return 7 if dy > 0 else 5


def penalties_option(name):
    for folder in (Path("captures"), Path.home() / "Documents" / "NHL94 Viewer" / "captures"):
        c = folder / name
        if c.exists():
            cap = Capture(c, systems.of_capture(c))
            return cap.word(cap.count // 2, OPT_PEN) if cap.full else None
    return None


def main():
    res = defaultdict(lambda: {"open": 0, "burst": 0, "hook": 0, "lat": []})
    for name, path in games():
        m = json.loads(load_js_object(path))
        if m.get("system", "genesis") != "genesis" or (m["t"][-1] - m["t"][0]) < 180000:
            continue
        opt = penalties_option(name)
        if opt is None:
            continue
        key = "on" if opt else "off"
        t, N = m["t"], len(m["t"])
        anim = lambda i, k: m["anim"][(i * K + k) * 4:(i * K + k) * 4 + 4]
        pos = lambda i, k: (m["pos"][(i * K + k) * 2], m["pos"][(i * K + k) * 2 + 1])
        for k in range(K):
            opp = range(6, 12) if k < 6 else range(6)
            i = 0
            while i < N:
                def opening(q):
                    if m["role"][q * K + k] not in "12345" or m["ctrl"][q] >> k & 1 or anim(q, k) in LOCKED or m["puck"][3 * q + 2] < -100:
                        return False
                    x, y = pos(q, k)
                    f = int(m["facing"][q * K + k])
                    for j in opp:
                        if m["role"][q * K + j] not in "12345" or anim(q, j) in LOCKED:
                            continue
                        dx, dy = pos(q, j)[0] - x, pos(q, j)[1] - y
                        if abs(dx) <= 30 and abs(dy) <= 30 and (dx or dy) and vtoa(dx, dy) == f:
                            return True
                    return False
                if not opening(i):
                    i += 1
                    continue
                s = i
                while i < N and opening(i):
                    i += 1
                r = res[key]
                r["open"] += 1
                hit = next((q for q in range(s, min(N, i + 2)) if anim(q, k) in (BURST, HOOK)), None)
                if hit is not None:
                    r["burst" if anim(hit, k) == BURST else "hook"] += 1
                    r["lat"].append(t[hit] - t[s])
    for key, r in sorted(res.items()):
        went = r["burst"] + r["hook"]
        print(f"penalties {key}: {r['open']} openings, a check tried in {went} ({100 * went / max(1, r['open']):.0f}%: "
              f"{r['burst']} bursts, {r['hook']} hooks / holds); median wait {statistics.median(r['lat']) if r['lat'] else 0:.0f} ms")


if __name__ == "__main__":
    main()
