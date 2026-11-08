"""Refit the expected-goals models' one fitted number, GOALIE_SPREAD (2026-11-08: studies 5 and 6 of
docs/GAME_VARIABLES_PLAN.md found the models too sure at both ends: shots under 0.1 xG scored about twice what they
said, the 0.6+ chances about 14% short; GOALIE_SPREAD, the jitter on the emulated goalie's position that stands for
its error, was fitted on seven games for the Genesis).

Every recorded game in the game folder with xG (both systems, each by its own model), every attempt that wasn't
blocked and has a model price, played out again with each candidate spread; for each: the log loss over the shots
(lower is better), and goals against expected by band (under 0.1, 0.1-0.3, 0.3-0.6, 0.6 and up). Gentle (lowload).

python analysis/xg_spread_fit.py genesis 4 6 8 10 14     (or snes 2 4 6 8)"""
import copy
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "scoring_map"))
import xg  # noqa: E402
import xg_snes  # noqa: E402
import systems  # noqa: E402
import lowload  # noqa: E402
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
BANDS = [(0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 2)]


def games(which):
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        if (m.get("system", "genesis") == "snes") != (which == "snes") or not m.get("work"):
            continue
        rom_path, _ = systems.of_match(m).find_rom(HOME / "captures" / p.stem)
        rom = Path(rom_path).read_bytes() if rom_path and Path(rom_path).exists() else None
        if which == "snes" and not rom:
            continue
        yield m, rom


def main():
    which, spreads = sys.argv[1], [float(v) for v in sys.argv[2:]]
    lowload.gentle()
    data = list(games(which))
    print(f"{which}: {len(data)} games", flush=True)
    for sp in spreads:
        rows = []
        for m, rom in data:
            m2 = copy.deepcopy(m)
            if which == "snes":
                xg_snes.GOALIE_SPREAD = sp
                xg_snes._CACHE.clear()
                xg_snes.add_expected_goals(m2, rom)
            else:
                xg.GOALIE_SPREAD = sp
                xg._CACHE.clear()
                xg.add_expected_goals(m2, stick_rom=rom, lock=True)
            for s in m2.get("shotList", []):
                if s.get("team") in (0, 1) and s["result"] != "blocked" and s.get("xg") is not None and s["kind"] in ("shot", "one-timer", "pass shot"):
                    rows.append((s["xg"], s["result"] == "goal"))
            lowload.breathe()
        eps = 1e-3
        ll = -sum(math.log(min(1 - eps, max(eps, p))) if g else math.log(1 - min(1 - eps, max(eps, p))) for p, g in rows) / len(rows)
        bands = []
        for lo, hi in BANDS:
            b = [(p, g) for p, g in rows if lo <= p < hi]
            bands.append(f"{lo}-{hi if hi < 2 else 1}: {sum(g for _, g in b)} / {sum(p for p, _ in b):.1f} ({len(b)})")
        print(f"spread {sp:5.1f}: {len(rows)} shots, log loss {ll:.4f}, goals {sum(g for _, g in rows)} / expected "
              f"{sum(p for p, _ in rows):.1f}; " + "; ".join(bands), flush=True)


if __name__ == "__main__":
    main()
