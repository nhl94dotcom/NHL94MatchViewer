"""Reads NHL '94's memory out of a running RetroArch, read-only, on Windows.

The work is in tools/systems/: process.py finds RetroArch and the core, and each system module (genesis.py, ...) finds
its game's RAM there. Run this file to check that a game can be found:

    python tools/nhl94_memory.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import systems  # noqa: E402
from systems.genesis import Emulator  # noqa: E402,F401  (kept for older scripts that import it from here)

if __name__ == "__main__":
    emu = systems.attach()
    if not emu:
        print("RetroArch with a supported core (Genesis Plus GX) and a game loaded was not found")
    else:
        system = systems.get(emu.system)
        view = system.View(emu)
        print(f"{emu.system}: work RAM at {emu.ram:#x}, cartridge at {emu.rom:#x}, ROM {emu.rom_fingerprint()}")
        print(f"screen {view.screen}, period {view.period}, clock {view.clock}, score {view.score[0]}-{view.score[1]}")
