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
