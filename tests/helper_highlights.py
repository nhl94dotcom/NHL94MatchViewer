"""Fake-emulator test of the helper (made 2026-10-14 .. 10-19 while building it): plays a recording back as if
RetroArch were running it and prints the helper's state as it waits, records and converts. Needs the recording
and ROM named below. python tests/helper_highlights.py"""
import os
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
"""The 10:54 recording (BOS-NYI period 1, then 26 s of a WSH-FLA highlight) followed by the 11:02 one (periods 2-3),
fed sample by sample through nhl94_helper.Recording.step with a stand-in emulator. Expect no split, the highlight left
out, the name BOS-NYI."""
import os
import sys
from pathlib import Path

HOME = Path(__file__).parent / "helper_home_hl"
os.environ["NHL94_HOME"] = str(HOME)
for sub in ("matches", "captures", "roms"):
    (HOME / sub).mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tools'))
import nhl94_helper as H  # noqa: E402
from export_match import Capture  # noqa: E402
from systems import genesis  # noqa: E402

D = Path(os.path.expanduser("~/Documents/NHL94 Viewer/captures"))
caps = [Capture(D / "2026-10-21_1054_WSH-FLA"), Capture(D / "2026-10-21_1102_BOS-NYI")]
ROM = Path(os.path.expanduser("~/Documents/NHL94 Viewer/roms/697a0f50_a738ea1c.bin"))


class FakeEmu:
    system = "genesis"

    def __init__(self):
        self.cap, self.i = caps[0], 0

    def read(self, addr, n):
        if addr == genesis.SCREEN ^ 1:
            return b"\x00"           # the game screen
        if self.cap.offset(addr) is None:
            return None
        return self.cap.raw(self.i, addr, n)


emu = FakeEmu()
H.time.sleep = lambda s: None
rec = None
ended = []
for c in caps:
    emu.cap = c
    for i in range(c.count):
        emu.i = i
        view = genesis.View(emu)
        if rec is None:
            rec = H.Recording(emu, view, ROM, ["697a0f50", "a738ea1c"])
            continue
        why = rec.step(view)
        if why:
            ended.append((c.folder.name if hasattr(c, "folder") else "?", i, why))
            break
print("ended early:", ended)
print("samples recorded:", rec.samples, "teams:", rec.teams, "name:", rec.name, "last view:", rec.view.describe())
rec.close()
