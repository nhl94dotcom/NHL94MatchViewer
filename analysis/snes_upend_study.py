"""SNES: which falls are upends (2026-10-21; SNES_MECHANICS 7.2). Code (NHL94SNES FallDown): a fall in open ice is
backward (SPAfallback) when the hitter is within one direction step of where the victim faces (hit from the front);
otherwise forward (SPAfallfwd), except that it is a flip, the upend (SPAflip), when the victim faces straight up or down
the ice (facing 0 or 4) and the hitter's working Checking is 10 or more. Every fall in the SNES recordings: the hitter
taken as the nearest opponent skater, the rule's prediction against what happened.
python analysis/snes_upend_study.py"""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
import systems  # noqa: E402
from export_match import Capture  # noqa: E402

FOLDERS = [Path("captures"), Path.home() / "Documents" / "NHL94 Viewer" / "captures"]
XPOS, YPOS, SPA, FACEDIR, PFTEAM, POSITION, CHECKING, SFLAGS = 0x0D55, 0x0DB7, 0x11A3, 0x1163, 0x1503, 0x0F43, 0x1483, 0x15D8
FWD, BACK, FLIP = 0xF49C, 0xF54E, 0xF6C0
NAMES = {FWD: "forward", BACK: "back", FLIP: "upend"}


def recordings():
    seen = set()
    for folder in FOLDERS:
        for cap in sorted(folder.glob("*")):
            if cap.name in seen or not (cap / "capture.json").exists():
                continue
            if not (cap.parent.parent / "matches" / f"{cap.name}.js").exists():
                continue
            seen.add(cap.name)
            yield cap


def signed(v):
    return v - 0x10000 if v & 0x8000 else v


def direction(dx, dy, ysign):
    """0-7 clockwise, 0 toward +y when ysign is 1 (the convention that fits the facings: the study tries both)."""
    a = math.degrees(math.atan2(dx, ysign * dy)) % 360
    return int((a + 22.5) // 45) % 8


def predict(to_hitter, facing, chk):
    if (to_hitter - facing + 1) % 8 < 3:
        return BACK
    if facing % 4 == 0 and chk >= 10:
        return FLIP
    return FWD


def main():
    res = {1: Counter(), -1: Counter()}
    by_kind = Counter()
    upends = []
    for cap_dir in recordings():
        system = systems.of_capture(cap_dir)
        if system.NAME != "snes":
            continue
        cap = Capture(cap_dir, system)
        w = lambda i, a, k=0: cap.word(i, a + 2 * k)
        for i in range(1, cap.count):
            if w(i, SFLAGS) & 0x0801:
                continue
            for k in range(12):
                spa = w(i, SPA, k)
                if spa not in NAMES or w(i - 1, SPA, k) == spa or w(i - 1, SPA, k) in NAMES:
                    continue
                if w(i, POSITION, k) in (0, 0xFFFF):
                    continue
                team = w(i, PFTEAM, k)
                x, y = signed(w(i - 1, XPOS, k)), signed(w(i - 1, YPOS, k))
                opp = [j for j in range(12) if w(i, PFTEAM, j) != team and w(i, POSITION, j) not in (0xFFFF,)]
                if not opp:
                    continue
                h = min(opp, key=lambda j: math.hypot(signed(w(i - 1, XPOS, j)) - x, signed(w(i - 1, YPOS, j)) - y))
                hx, hy = signed(w(i - 1, XPOS, h)), signed(w(i - 1, YPOS, h))
                if math.hypot(hx - x, hy - y) > 24 or w(i, POSITION, h) == 0:
                    continue  # no skater close enough to be the hitter (a goalie, a poke from far, the boards)
                facing = w(i - 1, FACEDIR, k) & 7
                chk = w(i, CHECKING, h)
                by_kind[spa] += 1
                for ysign in (1, -1):
                    res[ysign][(NAMES[spa], NAMES[predict(direction(hx - x, hy - y, ysign), facing, chk)])] += 1
                if spa == FLIP:
                    upends.append((cap_dir.name, i, facing, chk))
    print("falls:", {NAMES[k]: v for k, v in by_kind.items()})
    for ysign, c in res.items():
        right = sum(v for (a, b), v in c.items() if a == b)
        print(f"\ny up the screen = {'-' if ysign < 0 else '+'}: rule right {right} of {sum(c.values())}")
        for (a, b), v in sorted(c.items()):
            print(f"   {a:8} predicted {b:8} {v}")
    print("\nupends: victim facing, hitter Checking:", Counter((f, c >= 10) for _, _, f, c in upends))


if __name__ == "__main__":
    main()
