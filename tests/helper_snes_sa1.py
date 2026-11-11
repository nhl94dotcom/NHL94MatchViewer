"""The helper against a real SA-1 game (2026-11-07): the SNES SA-1 build (github.com/Mhopkinsinc/NHL94SNES-SA1) runs in
a copy of the Snes9x core in this process (analysis/scoring_map's headless frontend), and the helper finds it as it
finds RetroArch: snes.Emulator.attach on this process (process.find_process pointed here), Snes9x's memory map, work
RAM with the moved ranges overlaid from BW-RAM. The game is the menus' first matchup (START taps through the menus and
the screens between periods), the computer playing both sides, the core run at SPEED x real time. The helper records,
converts and saves it; the test then checks the match file against the game's own counts (tests/check_matches.py) and
prints what was read. (2026-11-07, the 32-team ROM: CAR-VGK recorded whole, every count as the game's; pad 1 does
nothing, so the home team barely plays.)

python tests/helper_snes_sa1.py [ROM file name in Documents/NHL94 Viewer/roms]   (default 308bd713.smc, the 32 teams)
Needs analysis/scoring_map's core copy (build.py there). Several minutes: a whole game at SPEED."""
import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = os.path.join(tempfile.gettempdir(), "nhl94_helper_home_sa1")
os.environ["NHL94_HOME"] = HOME
for sub in ("matches", "captures", "sprites", "roms", "shared", "sounds"):
    os.makedirs(os.path.join(HOME, sub), exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis" / "scoring_map"))
import nhl94_helper as H  # noqa: E402
from snes_emu import SnesEmu  # noqa: E402
from systems import process, snes  # noqa: E402

ROM = Path.home() / "Documents" / "NHL94 Viewer" / "roms" / (sys.argv[1] if len(sys.argv) > 1 else "308bd713.smc")
SPEED = 2.0
START = 3  # libretro's START button
e = SnesEmu(rom=ROM)
stop = threading.Event()
low = lambda a: e.bw[0x6000 + a] | e.bw[0x6001 + a] << 8   # a low-RAM word, in BW-RAM


def run():
    """The core at SPEED x real time. START is tapped through the menus and the screens between periods: whenever
    the clock has not moved for 6 s of game frames (paused, or a screen waiting for a button), never while it runs."""
    frame, last_clock, still = 0, None, 0
    t0 = time.perf_counter()
    while not stop.is_set():
        clock = low(snes.CLOCK)
        still = still + 1 if clock == last_clock else 0
        last_clock = clock
        e.held = {START} if still > 360 and (frame // 20) % 6 == 0 else set()
        e.lib.retro_run()
        frame += 1
        ahead = frame / (60 * SPEED) - (time.perf_counter() - t0)
        if ahead > 0:
            time.sleep(ahead)


import ctypes as C  # noqa: E402
e.bw = (C.c_ubyte * e.lib.retro_get_memory_size(0)).from_address(e.lib.retro_get_memory_data(0))
threading.Thread(target=run, daemon=True).start()
process.find_process = lambda name="retroarch.exe": os.getpid()
H.systems.attach = snes.attach
H.PORT = 9497
sys.argv[1:] = ["--no-browser"]
threading.Thread(target=H.main, daemon=True).start()
last, t0 = None, time.time()
while time.time() - t0 < 1800:
    time.sleep(2)
    try:
        s = json.loads(urllib.request.urlopen(f"http://localhost:{H.PORT}/api/state").read())
    except Exception:
        continue
    tn = (s.get("game") or {}).get("tonight")
    if tn and any(t["players"] for t in tn["teams"]) and not globals().get("_tonight_shown"):
        _tonight_shown = True
        print(f"{time.time() - t0:5.0f}s tonight's rolls:", [(t["team"], [(p["slot"], p["name"].split()[-1], p.get("maxed"), p.get("stk"))
                                                               for p in t["players"]]) for t in tn["teams"]], flush=True)
    line = (s["state"], s["detail"])
    if line != last:
        print(f"{time.time() - t0:5.0f}s", *line, flush=True)
        last = line
    games = list(Path(HOME, "matches").glob("*.js"))
    if any(not g.name.startswith(("season", "_")) for g in games) and s["state"] != "recording":
        break
stop.set()
matches = [g for g in Path(HOME, "matches").glob("*.js") if not g.name.startswith(("season", "_"))]
print("match files:", [g.name for g in matches])
for g in matches:
    text = g.read_text(encoding="utf-8")
    m = json.loads(text[text.index("{"):text.rindex("}") + 1])
    print(g.stem, "teams", m.get("abbr"), "score", m["score"][-2:], "shots", m["shots"][-2:], "samples", len(m["t"]),
          "shotList", len(m.get("shotList", [])), "passes", len(m.get("passes", [])), "hits", len(m.get("hits", [])),
          "xg", sum(1 for x in m.get("shotList", []) if "xg" in x), "anims", len(m.get("anims", {})))
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "tests" / "check_matches.py"), str(g)])
