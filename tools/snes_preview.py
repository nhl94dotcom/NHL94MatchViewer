"""A still picture of a SNES game from a RetroArch Snes9x save state, as a match file the viewer opens: a check of the
SNES reading (positions, sprites, rosters, rink) before SNES games can be recorded.

    python tools/snes_preview.py <state file> [<ROM>]      ->  matches/snes_<state name>.js
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems import snes  # noqa: E402
from systems.common import ROOT  # noqa: E402

ROMS = Path.home() / "RetroArch-1.17-Win64/ROMs/SNES"


def main(state, rom=None):
    state = Path(state)
    rom = Path(rom) if rom else ROMS / (state.name.split(".state")[0] + ".smc")
    # the same moment twice, a second apart, so the viewer has a timeline to stand on
    match = snes.read_match(snes.SaveStates([state, state]), rom, "snes_" + state.name.replace(".", "_"))
    out = ROOT / "matches" / (match["name"] + ".js")
    out.write_text("window.NHL94_MATCH = " + json.dumps(match, separators=(",", ":")) + ";\n", encoding="utf-8")
    print(f"{out}: {match['team1']} vs {match['team2']}, ROM {rom.name}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(*sys.argv[1:3])
