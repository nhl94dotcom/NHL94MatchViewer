"""The scripted bot's games recorded as the helper records people's (2026-11-11, the user: chunk 3 of the people's team
against the computer's team: how a team the bot plays compares). Each game is bot_run.play (bot.py's default version on
pad 1, Home, Montreal; the computer Away, Los Angeles; bot_start.state's league settings) with its own seed (bot_run's
seeds, game n the (n + 1)th), and every frame a sample of genesis.BLOCKS as cvc_record keeps them, a full RAM snapshot
every 10 s, capture.json; then tools/export_match.py converts it. One process a game; gentle.

NHL94_BOT_TEAMS=1 (2026-11-12): game n starts from bot_start_{n % 16}.state (bot_states.py all: 16 matchups) instead.

python bot_record.py OUT GAMES [FIRST]   -> OUT/captures/bot_genesis_NN, OUT/matches/bot_genesis_NN.js"""
import gzip
import json
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lowload  # noqa: E402

FPS = 60


def one(n, out):
    import bot_run
    from emu import Emu
    from paths import WORK
    from systems import genesis
    folder = out / "captures" / f"bot_genesis_{n:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    e = Emu(bot_run.RETAIL)
    import os
    start = (WORK / (f"bot_start_{n % 16:02d}.state" if os.environ.get("NHL94_BOT_TEAMS") else "bot_start.state")).read_bytes()
    ram = memoryview(e.ram)
    state = {"frame": 0, "count": 0}
    with gzip.open(folder / "fast.bin.gz", "wb", compresslevel=3) as fast, \
            gzip.open(folder / "full.bin.gz", "wb", compresslevel=3) as full:
        base = e.run

        def run(k=1, **kw):
            for _ in range(k):
                base(1, **kw)
                state["frame"] += 1
                ms = state["frame"] * 1000 // FPS
                fast.write(struct.pack("<q", ms) + b"".join(bytes(ram[s:s + z]) for s, z in genesis.BLOCKS))
                state["count"] += 1
                if state["frame"] % (10 * FPS) == 0:
                    full.write(struct.pack("<q", ms) + bytes(ram[:genesis.RAM_SIZE]))
        e.run = run
        r = bot_run.play(e, start, 0x9E3779B1 * (n + 1) & 0xFFFFFFFF)
        for _ in range(5 * FPS):
            run(1)
    (folder / "capture.json").write_text(json.dumps({"blocks": [list(b) for b in genesis.BLOCKS],
                                                     "recorded_by": "bot_record", "system": genesis.NAME}))
    print(json.dumps({"game": n, "score": r["score"], "shots": r["shots"], "samples": state["count"],
                      "folder": str(folder)}))


def main():
    out, games = Path(sys.argv[1]), int(sys.argv[2])
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    lowload.gentle()
    (out / "matches").mkdir(parents=True, exist_ok=True)
    from paths import WORK
    rom = str(WORK / "nhl94_retail.bin")
    for n in range(first, first + games):
        r = subprocess.run([sys.executable, __file__, "--one", str(n), str(out)], capture_output=True, text=True,
                           cwd=str(HERE))
        lines = [x for x in r.stdout.splitlines() if x.startswith("{")]
        info = json.loads(lines[-1]) if lines else {"game": n, "error": r.stderr[-400:]}
        print(json.dumps(info), flush=True)
        if "folder" in info:
            c = subprocess.run([sys.executable, str(ROOT / "tools" / "export_match.py"), info["folder"], "--rom", rom,
                                "--out", str(out / "matches")], capture_output=True, text=True)
            print("  converted:", (c.stdout.strip().splitlines() or [c.stderr[-300:]])[-1], flush=True)
        lowload.breathe()


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        one(int(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
