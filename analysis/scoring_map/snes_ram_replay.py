"""The recorded SNES shots replayed in the retail game from the recording's own work RAM (2026-10-31): every sample the
helper keeps holds work RAM $0000-$3FFF (systems/snes.py BLOCKS: the objects, the goalie's timers, targets and flags,
the random seeds), so each shot's sample is written into the retail game (snes_top.state as the base) and the game
plays on with no buttons pressed. With the recording's own seed it should do what the recording shows (the check);
with other seeds it gives the game's chance from that exact moment, for the xG model to be measured against
(SNES_SHOOTING 4.7: the gliding goalie, right on the game's own shots, 24% high on the recorded ones).
The recordings are read only (NHL94_HOME, default Documents\\NHL94 Viewer); testing on the retail ROM (the user,
2026-10-31). Shots at a computer goalie, not blocked, shots and one-timers.
python snes_ram_replay.py RUN [seeds] [minutes]   -> paths.RUNS / RUN / snes_ram_replay.jsonl   (gentle, resumable)"""
import ctypes
import json
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import export_match  # noqa: E402
from share_game import load_js_object  # noqa: E402
from systems import snes as SN  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from paths import RUNS, SNES_ROM, SNES_STATE_TOP  # noqa: E402
from snes_emu import SnesEmu  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SCORE = 0x178E                    # tmscore: home word, away word
PUCKC, SEED = 0x0AD9, 0x0792
FRAMES = 180


def recorded_shots():
    for mf in sorted((HOME / "matches").glob("*.js")):
        if mf.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(mf))
        except (ValueError, OSError):
            continue
        cap_dir = HOME / "captures" / mf.stem
        if m.get("system") != "snes" or not cap_dir.exists():
            continue
        cap = export_match.Capture(cap_dir)
        rom = HOME / "roms" / f"{m.get('rom')}.smc"
        if not rom.exists():
            continue
        reader = SN.MatchReader(cap, rom)
        reader.feed(cap)
        keep = reader.keep
        if len(keep) != len(m["t"]):
            print("sample count differs:", mf.stem, len(keep), len(m["t"]))
            continue
        for sh in m["shotList"]:
            if sh.get("gctl") != "cpu" or sh["result"] == "blocked" or sh["kind"] not in ("shot", "one-timer"):
                continue
            yield mf.stem, sh, cap.raw(keep[sh["f"]], 0, 0x4000), sh.get("xg")


def replay(e, base, block, team, seed=None):
    e.unserialize(base)
    ctypes.memmove(ctypes.addressof(e.ram), block, len(block))
    if seed is not None:
        e.setw(SEED, seed >> 16 or 1)
        e.setw(SEED + 2, seed & 0xFFFF or 1)
    s0 = e.w(SCORE + 2 * team)
    held = 0
    for f in range(FRAMES):
        e.run(1)
        if e.w(SCORE + 2 * team) != s0:
            return 1
        held = held + 1 if not e.w(PUCKC) & 0x8000 else 0
        if held >= 20:
            return 0
    return 0


def main():
    run = sys.argv[1]
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    path = out / "snes_ram_replay.jsonl"
    done = {(json.loads(l)["name"], json.loads(l)["f"]) for l in open(path)} if path.exists() else set()
    e = SnesEmu()
    base = SNES_STATE_TOP.read_bytes()
    t0 = time.time()
    with open(path, "a") as fh:
        for name, sh, block, xgv in recorded_shots():
            if (name, sh["f"]) in done:
                continue
            if time.time() - t0 > minutes * 60:
                print("time up")
                break
            own = replay(e, base, block, sh["team"])
            rnd = random.Random(f"{name}:{sh['f']}")
            other = [replay(e, base, block, sh["team"], rnd.getrandbits(32)) for _ in range(seeds)]
            fh.write(json.dumps(dict(name=name, f=sh["f"], kind=sh["kind"], result=sh["result"], xg=xgv,
                                     own_seed=own, game=sum(other) / max(1, len(other)))) + "\n")
            fh.flush()
            breathe()


if __name__ == "__main__":
    main()
