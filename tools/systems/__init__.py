"""One module per game system (genesis.py, snes.py), each answering the same questions its own way: where the game's
memory is in the running emulator, what the helper records and how it reads the screen, clock and score, where
players, puck and stats are, which animations mean what, and how the ROM stores teams and sprites. export_match.py
and the helper ask the module; the analysis and the viewer only see the match file.
"""
import json

from . import genesis, snes

SYSTEMS = {genesis.NAME: genesis, snes.NAME: snes}


def get(name):
    """The module for a system name; recordings and match files from before systems existed are Genesis."""
    return SYSTEMS[name or genesis.NAME]


def of_capture(folder):
    """The system a recording was made on, from its capture.json."""
    layout = folder / "capture.json"
    return get(json.loads(layout.read_text()).get("system") if layout.exists() else None)


def of_match(m):
    return get(m.get("system"))


def attach():
    """Whichever system's emulator is running with a game loaded, or None."""
    for system in SYSTEMS.values():
        emu = system.attach()
        if emu:
            return emu
    return None
