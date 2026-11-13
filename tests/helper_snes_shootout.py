"""The helper through a SNES shootout (2026-11-12, the user's game on McMarkis's 32-team build with NOSE4Web's season
shootout: recorded through overtime, then split into pieces at every shootout round). The recorded samples of a game's
end and of its shootout pieces, in order, are fed to nhl94_helper.Recording.step as Views (snes.View over each sample,
no emulator): it must not end the recording during the rounds (shootoutmode $1D81 set), must not record them, and must
end with "final" once the game comes back with the winners' goal, writing shootout.json with that score.

python tests/helper_snes_shootout.py [GAME_CAPTURE SHOOTOUT_CAPTURE ...]   (folders in Documents/NHL94 Viewer/captures;
default the user's 2026-11-12 GER-USA game; the game's last 3,000 samples are used)"""
import gzip
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = os.path.join(tempfile.gettempdir(), "nhl94_helper_home_shootout")
os.environ["NHL94_HOME"] = HOME
for sub in ("matches", "captures", "sprites", "roms", "shared", "sounds"):
    os.makedirs(os.path.join(HOME, sub), exist_ok=True)
sys.path.insert(0, str(ROOT / "tools"))
import nhl94_helper as H  # noqa: E402
from systems import snes  # noqa: E402

GAMES = Path.home() / "Documents" / "NHL94 Viewer" / "captures"
names = sys.argv[1:] or ["2026-11-12_2326_GER-USA", "2026-11-12_2341_GER-USA", "2026-11-12_2342_GER-USA"]


class Sample:
    """One recorded sample, read as the emulator would be (snes.View reads its blocks through emu.read)."""
    system, teams = "snes", 32

    def __init__(self, blocks, data):
        self.parts = {}
        o = 0
        for start, length in blocks:
            self.parts[start] = data[o:o + length]
            o += length

    def read(self, start, length):
        return self.parts.get(start, bytes(length))[:length]


samples = []
for i, n in enumerate(names):
    blocks = json.loads((GAMES / n / "capture.json").read_text())["blocks"]
    size = 8 + sum(b[1] for b in blocks)
    data = gzip.decompress((GAMES / n / "fast.bin.gz").read_bytes())
    count = len(data) // size
    first = max(0, count - 3000) if i == 0 else 0
    samples += [(blocks, data[k * size + 8:(k + 1) * size]) for k in range(first, count)]

H.FINAL_WAIT_S = 0.0                       # no waiting for the final screen in a replay
views = [snes.View(Sample(b, d)) for b, d in samples]
rec = H.Recording(Sample(*samples[0]), views[0], None, None)
ended, in_shootout, recorded_in_shootout = None, 0, 0
for k, v in enumerate(views[1:], 1):
    before = rec.samples
    why = rec.step(v)
    if v.shootout:
        in_shootout += 1
        recorded_in_shootout += rec.samples - before
    if why:
        ended = (k, why, v.describe())
        break
rec.close() if hasattr(rec, "close") else None
so = rec.folder / "shootout.json"
print(f"{len(views)} samples, {in_shootout} in the shootout ({recorded_in_shootout} recorded); ended: {ended}")
print("shootout.json:", so.read_text() if so.exists() else "none")
ok = ended is not None and ended[1] == "final" and recorded_in_shootout == 0 and so.exists()
print("PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
