"""Where the scoring map keeps its working files: a folder outside the repository (a test ROM built from the
disassembly, a copy of the emulator core, the game states, the results). NHL94_SMAP_WORK overrides it."""
import os
from pathlib import Path

WORK = Path(os.environ.get("NHL94_SMAP_WORK") or Path.home() / "NHL94_scoring_map")
DISASM = Path.home() / "NHL94_disasm" / "NHL94Genesis"          # the clone; never built in place
RETROARCH = Path.home() / "RetroArch-1.17-Win64"
CORE_SOURCE = RETROARCH / "cores" / "genesis_plus_gx_libretro.dll"
CORE = WORK / "core" / "genesis_plus_gx_libretro.dll"           # a copy: RetroArch's own file is left alone
ROM = WORK / "smap94.bin"                                         # the test ROM (build.py)
BUILD = WORK / "g94"                                              # the copy of the disassembly it is built from
LISTING = BUILD / "output" / "build" / "nhl94 .lst"
STATE_TOP = WORK / "live.state"                                   # period 1: home shoots at the top net
STATE_BOTTOM = WORK / "live_p2.state"                             # period 2: the bottom net
RUNS = WORK / "runs"

# The SNES map (snes_*.py): the retail ROM (no test ROM needed) and Snes9x. The disassembly stopped tracking its copy
# (lst/nhl94snes.sfc, 2026-10-28): put one in the work folder (from the disassembly's history:
# git show e1aab8d4^:lst/nhl94snes.sfc > WORK/nhl94snes.sfc); the old place is still tried
SNES_ROM = WORK / "nhl94snes.sfc"
if not SNES_ROM.exists():
    SNES_ROM = Path.home() / "NHL94_disasm" / "NHL94SNES" / "lst" / "nhl94snes.sfc"
SNES_CORE_SOURCE = RETROARCH / "cores" / "snes9x_libretro.dll"
SNES_CORE = WORK / "core" / "snes9x_libretro.dll"
SNES_STATE_TOP = WORK / "snes_top.state"
SNES_STATE_BOTTOM = WORK / "snes_bottom.state"
