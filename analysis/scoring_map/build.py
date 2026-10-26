"""The scoring map (2026-10-22; GENESIS_SHOOTING 4.10): the chance a shot scores, played in the real game.

How it works: a test ROM built from the Genesis disassembly with a hook in doshot (patch_rom.py) runs headless in a
copy of RetroArch's Genesis Plus GX core (emu.py, a minimal libretro frontend). The hook records doshot's inputs and
can replace the puck's launch. harness.py sets a shot up (the controlled skater standing with the puck, everyone else
parked at the far end, the computer goalie settled), shotport.py is doshot's launch ported exactly (checked against
the game on 129 shots), and map_run.py plays every aim from every spot, sampling the shot's random draws from their
exact distribution and the moment of the shot (120 phases of the game clock and the goalie's cycles).

Setup (once): python build.py   (copies the disassembly clone, patches and builds the test ROM, copies the core,
                                  boots a game to the two states; needs Node and the clone's own ROM in lst/)
Run:          python map_run.py W N RUN [budget] [shp sha]   for W in 0 .. N-1, in parallel
Check:        python validate.py top 0 160 6 20 3000 1   against   python validate.py top 0 160 6 20 0 1
Draw:         python render_map.py RUN out.svg [best|mid];  python compare_xg.py RUN (the viewer's xG model)"""
import shutil
import subprocess
import sys
from pathlib import Path

from paths import BUILD, CORE, CORE_SOURCE, DISASM, ROM, WORK

HERE = Path(__file__).resolve().parent


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(DISASM, BUILD, ignore=shutil.ignore_patterns(".git", "node_modules", "output", "Extracted"))
    subprocess.run([sys.executable, str(HERE / "patch_rom.py"), str(BUILD / "src" / "input94.asm")], check=True)
    npm = shutil.which("npm") or "npm"
    subprocess.run([npm, "install", "--silent"], cwd=BUILD, check=True, shell=True)
    subprocess.run([npm, "run", "build:dev"], cwd=BUILD, check=True, shell=True)
    shutil.copy(BUILD / "output" / "nhl94-dev.bin", ROM)
    CORE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(CORE_SOURCE, CORE)
    subprocess.run([sys.executable, str(HERE / "make_states.py")], cwd=HERE, check=True)
    print("ready:", WORK)


if __name__ == "__main__":
    main()
