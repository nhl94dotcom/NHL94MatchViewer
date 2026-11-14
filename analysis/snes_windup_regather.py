"""SNES shot wind-ups in the recorded games (2026-11-14, NOSE4Web's shotFix 80f108e: how often does a shooter lose the
puck during his wind-up and gather it again, which on retail cancels the shot).

Each recording of a SNES game on a retail-layout ROM (1 MB; the SA-1 builds' animation words differ), every sample:
a skater whose SPA ($11A3, object x 2) is in a shot swing ($ED4A-$F020 as ShotMode tests, the one-timer swings
included) while he is the carrier (puckc $0AD9) starts a wind-up; it ends when his SPA leaves the range. Kinds:
fired (the puck left him with his nopuck $1203 at 16: doshot), regathered (the puck left him without a shot and came
back while he was still in the swing; then fired or not), kept (no shot, never lost: a hold or hook), lost.
The swing kind from its first animation word (SPAshotf $ED4A / SPAshotb $EE5C a shot; the rest one-timer swings).
A person's skater or the computer's (pflags $1283 bit 3, the person flag) kept apart.

python analysis/snes_windup_regather.py"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from export_match import Capture  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SPA, PUCKC, NOPUCK, PFLAGS, SFLAGS = 0x11A3, 0x0AD9, 0x1203, 0x1283, 0x15D8
LO, HI = 0xED4A, 0xF020


def s16(v):
    return v - 65536 if v & 0x8000 else v


def one_mb(rom_id):
    """The game's ROM copy (<home>/roms/<id>.*) is a 1 MB retail-layout ROM (not SA-1, not 2 MB)."""
    for f in (HOME / "roms").glob(f"{rom_id}.*"):
        d = f.read_bytes()
        d = d[512:] if len(d) % 0x8000 == 512 else d
        return len(d) == 0x100000 and d[0x7FD5] != 0x23
    return False


def scan(c):
    out, open_ = [], {}
    for i in range(c.count):
        if c.word(i, SFLAGS) & 0x0801:          # paused or a replay
            continue
        pc = s16(c.word(i, PUCKC))
        for k in range(12):
            in_w = LO <= c.word(i, SPA + 2 * k) <= HI
            if in_w and k not in open_ and pc == 2 * k:
                open_[k] = {"i": i, "left": False, "back": False, "fired": False,
                            "person": bool(c.word(i, PFLAGS + 2 * k) & 8),
                            "swing": "shot" if c.word(i, SPA + 2 * k) in (0xED4A, 0xEE5C) else "one-timer"}
            if k not in open_:
                continue
            s = open_[k]
            if pc != 2 * k:
                if pc < 0 and c.word(i, NOPUCK + 2 * k) >= 12:
                    s["fired"] = True
                elif not s["fired"]:
                    s["left"] = True
            elif s["left"] and not s["fired"]:
                s["back"] = True
            if not in_w:
                kind = ("regathered, fired" if s["back"] and s["fired"] else "regathered, no shot" if s["back"]
                        else "fired" if s["fired"] else "kept, no shot" if pc == 2 * k else "lost")
                out.append((kind, s["person"], s["i"], s["swing"]))
                del open_[k]
    return out


def main():
    games, total = 0, Counter()
    cases = []
    for p in sorted((HOME / "captures").iterdir()):
        cj = p / "capture.json"
        if not cj.exists() or not (HOME / "matches" / f"{p.name}.js").exists():
            continue
        meta = json.loads(cj.read_text())
        summ = HOME / "matches" / f"{p.name}.summary.json"
        if meta.get("system") != "snes" or not summ.exists() or not one_mb(json.loads(summ.read_text(encoding="utf-8")).get("rom")):
            continue
        try:
            c = Capture(p)
        except Exception:
            continue
        games += 1
        for kind, person, i, swing in scan(c):
            total[(swing, kind, "person" if person else "computer")] += 1
            if kind.startswith("regathered"):
                cases.append((p.name, i, kind, person, c.word(i, 0x1630) + 1, c.word(i, 0x1632)))
    print(f"{games} SNES recordings (retail layout)")
    for k, v in sorted(total.items()):
        print(f"  {k[0]} swing, {k[1]} ({k[2]}): {v}")
    for cse in cases[:20]:
        print("   ", cse)


if __name__ == "__main__":
    main()
