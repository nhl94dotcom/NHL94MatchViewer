"""SNES faceoffs against the code (Endfaceoff): each centre's swing stage at the drop (0, 8 or 16: which (frame, time)
pair of his faceoff animation he's on, 8 a pair), Home wins the roll when (RandomWord & 31) + 1 >= 16 - home + away, so
P(home) = (17 + home - away) / 32; the puck leaves at 32 x a direction plus 2048 along the ice toward the winner's
side. Reads the winner from the puck's speed just after the drop. python analysis/snes_faceoffs.py"""
import glob
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
import xg_snes  # noqa: E402

K = 12
FACEOFF_SPAS = None


def stage(m, data, f, k):
    """0 / 8 / 16 from the centre's animation and frame, or None."""
    spa = int(m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4], 16)
    fr = int(m["frame"][(f * K + k) * 3:(f * K + k) * 3 + 3], 16)
    facing = int(m["facing"][f * K + k])
    try:
        seq = data.anim(spa, facing)
    except Exception:
        return None
    frames = [a for a, _ in seq]
    if fr in frames:
        return 8 * min(2, frames.index(fr))
    return None


def main():
    files = {}
    for p in glob.glob("matches/*.js") + glob.glob(str(Path.home() / "Documents/NHL94 Viewer/matches/*.js")):
        if not p.endswith(".summary.json") and Path(p).name not in ("season.js", "shot_study.json"):
            files.setdefault(Path(p).name, p)
    rom = (Path.home() / "RetroArch-1.17-Win64/ROMs/SNES/NHL94_Classic.smc").read_bytes()
    data = xg_snes.RomData(rom)
    exp, got, n, decoded = 0.0, 0, 0, Counter()
    by_diff = Counter()
    for name, p in sorted(files.items()):
        try:
            m = json.loads(load_js_object(Path(p)))
        except Exception:
            continue
        if m.get("system") != "snes" or not m.get("faceoffs"):
            continue
        P, V = m["puck"], m["puckV"]
        for fo in m["faceoffs"]:
            f = fo["f"]
            # the drop: the first sample from f on where the puck moves
            q = next((q for q in range(f, min(len(m["t"]) - 1, f + 40)) if abs(V[2 * q]) + abs(V[2 * q + 1]) > 0), None)
            if q is None:
                continue
            centres = {}
            for k in range(12):
                if m["role"][(q - 1) * K + k] == "4":
                    centres[0 if k < 6 else 1] = k
            if len(centres) != 2:
                continue
            h, a = stage(m, data, q - 1, centres[0]), stage(m, data, q - 1, centres[1])
            if h is None or a is None:
                decoded["stage unknown"] += 1
                continue
            vy = V[2 * q + 1] * 100
            # residual after the direction part: +/-2048 along the ice
            best = min((abs(vy - (base + push)), push) for base in (0, 4512, -4512, 6400, -6400) for push in (2048, -2048))
            if best[0] > 400:
                decoded["undecoded"] += 1
                continue
            push = best[1]
            # which team defends the end the push points to: the push goes toward the winner's own end
            hg = next((m["pos"][(q * K + k) * 2 + 1] for k in range(6) if m["role"][q * K + k] == "0"), None)
            if hg is None:
                continue
            home_won = (push > 0) == (hg > 0)
            decoded["decoded"] += 1
            p_home = (17 + h - a) / 32
            exp += p_home
            got += home_won
            n += 1
            by_diff[(h - a, home_won)] += 1
    print(decoded)
    print(f"{n} draws: home won {got}, the timing model expects {exp:.1f}")
    for d in sorted({k[0] for k in by_diff}):
        w, l = by_diff[(d, True)], by_diff[(d, False)]
        print(f"  home stage - away stage {d:+3}: {w + l:3} draws, home won {w} ({100 * w / max(1, w + l):.0f}%), model {100 * (17 + d) / 32:.0f}%")


if __name__ == "__main__":
    main()
