"""The SNES goalie's inner state at each recorded shot, read from the recording's RAM, given to the xG model
(2026-10-31; SNES_SHOOTING 4.7). Each helper sample keeps work RAM $0000-$3FFF, so at a shot's release the computer
goalie's rethink timer (temp1 $1003), the direction he pushes (temp2b $10A3), his facing ($1163), a save move under way
(pfalock $14E3 holds its animation; SPAnum $11C3 / SPAcnt $11E3 how far it has run) and where the game reckons the puck
crosses his goal line (puckcross $0D17 top / $0D1B bottom: x, frames) are all in the recording. The model normally
starts him fresh (a random timer, no target, no save); here it starts him as he was. Compared over the recorded SNES
shots: the model as it is, with the goalie's state, and each with the goalie gliding in a save move
(xg_snes.GLIDE_IN_SAVE). Recordings read only (NHL94_HOME, default Documents\\NHL94 Viewer).
python snes_goalie_state.py"""
import json
import math
import os
import statistics as st
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import export_match  # noqa: E402
import xg_snes as xs  # noqa: E402
from share_game import load_js_object  # noqa: E402
from systems import snes as SN  # noqa: E402

from lowload import gentle  # noqa: E402
from paths import SNES_ROM  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
TEMP1, TEMP2B, FACEDIR, SPANUM, SPACNT, PFALOCK, PUCKCROSS = 0x1003, 0x10A3, 0x1163, 0x11C3, 0x11E3, 0x14E3, 0x0D17
K = 12


def internals(block, gk, data, top):
    w = lambda a: struct.unpack_from("<H", block, a)[0]
    sw = lambda a: struct.unpack_from("<h", block, a)[0]
    o = 2 * gk
    facing = w(FACEDIR + o) & 7
    spa = w(PFALOCK + o)
    if spa not in xs.SAVES:                      # pfalock also holds other locks (a poke check's facing): saves only
        spa = 0
    elapsed = 0
    if spa:
        seq = data.anim(spa, facing)
        idx = w(SPANUM + o) // 4
        elapsed = sum(max(0, d) for _, d in seq[:idx])
        if idx < len(seq) and seq[idx][1] > 0:
            elapsed += max(0, seq[idx][1] - sw(SPACNT + o))
    cx, cf = sw(PUCKCROSS + (0 if top else 4)), sw(PUCKCROSS + (2 if top else 6))
    d = w(TEMP2B + o)
    return dict(timer=max(0, sw(TEMP1 + o)), dir=d if 0 <= d <= 8 else 8, facing=facing, save_spa=spa,
                save_elapsed=elapsed, cross=[cx, cf] if 0 <= cf < 300 else None)


def main():
    gentle()
    rom = SNES_ROM.read_bytes()
    data = xs.RomData(rom)
    games = []
    for mf in sorted((HOME / "matches").glob("*.js")):
        if mf.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(mf))
        except (ValueError, OSError):
            continue
        cap_dir = HOME / "captures" / mf.stem
        rom_path = HOME / "roms" / f"{m.get('rom')}.smc"
        if m.get("system") != "snes" or not cap_dir.exists() or not rom_path.exists():
            continue
        cap = export_match.Capture(cap_dir)
        reader = SN.MatchReader(cap, rom_path)
        reader.feed(cap)
        if len(reader.keep) != len(m["t"]):
            print("skipped (sample count):", mf.stem)
            continue
        state = {}
        for sh in m["shotList"]:
            f, team = sh["f"], sh["team"]
            if team not in (0, 1):
                continue
            gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][f * K + k] == "0"), None)
            if gk is None:
                continue
            block = cap.raw(reader.keep[f], 0, 0x4000)
            state[f] = internals(block, gk, data, m["pos"][(f * K + gk) * 2 + 1] > 0)
        games.append((m, state))
        print(mf.stem, len(state), "shots", flush=True)
    LL = lambda ys, ps: -st.mean(y * math.log(max(1e-3, min(1 - 1e-3, p))) + (1 - y) * math.log(max(1e-3, 1 - min(1 - 1e-3, p)))
                                 for y, p in zip(ys, ps))
    for glide in (False, True):
        for use in (False, True):
            xs.GLIDE_IN_SAVE = glide
            xs._CACHE.clear()
            ys, ps, cpu = [], [], []
            for m, state in games:
                for sh in m["shotList"]:
                    sh.pop("xg", None)
                xs.add_expected_goals(m, rom, internals=state if use else None)
                for sh in m["shotList"]:
                    if sh.get("xg") is not None and sh["result"] != "blocked":
                        ys.append(sh["result"] == "goal")
                        ps.append(sh["xg"])
                        cpu.append(sh.get("gctl") == "cpu")
            c = [i for i in range(len(ys)) if cpu[i]]
            print(f"glide {glide!s:5} goalie state {use!s:5}: all {len(ys)} goals {sum(ys)} xG {sum(ps):.1f} "
                  f"ll {LL(ys, ps):.4f} | computer goalie goals {sum(ys[i] for i in c)} xG {sum(ps[i] for i in c):.1f} "
                  f"ll {LL([ys[i] for i in c], [ps[i] for i in c]):.4f}", flush=True)
    xs.GLIDE_IN_SAVE = False


if __name__ == "__main__":
    main()
