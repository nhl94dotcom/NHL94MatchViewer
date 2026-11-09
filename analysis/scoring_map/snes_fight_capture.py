"""A recording with a fight in it, made headless (2026-11-09: no recorded SNES game has a fight yet; the 2 MB builds have
them). The 2 MB build boots in a copy of the core, Fighting On ($E708 = 0, in BW-RAM on the SA-1 builds) and penalties
on (OptPen $34C4) are set in RAM, and the computer plays. Every frame is a sample in the helper's own format (an
8-byte millisecond stamp, then tools/systems/snes.BLOCKS as snes.Emulator.read lays them out, the SA-1 build's moved
RAM put back), with a full RAM snapshot each second; START is tapped when the clock has stood still 5 s (the
intermission screens wait for a button). The last 20 s (real) are kept as it plays; once a player's
pflags $0400 (fighting) is seen, 40 s more are recorded and the capture written: OUT/capture.json, fast.bin.gz,
full.bin.gz. Then: python tools/export_match.py OUT --rom ROM --out SOMEWHERE

python snes_fight_capture.py ROM OUT [max_minutes]"""
import collections
import gzip
import json
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lowload  # noqa: E402
from faceoff_fix_test import Snes  # noqa: E402
from systems import snes  # noqa: E402

FPS = 60


class Reader:
    """Work RAM as snes.Emulator.read gives it: on an SA-1 build the moved ranges (snes.SA1_MOVED) from BW-RAM."""

    def __init__(self, g):
        self.g = g

    def read(self, off, size):
        out = bytearray(bytes(self.g.e.ram[off:off + size]))
        if self.g.sa1:
            for lo, hi, to in snes.SA1_MOVED:
                a, b = max(lo, off), min(hi, off + size)
                if a < b:
                    out[a - off:b - off] = bytes(self.g.bw[to + a - lo:to + b - lo])
        return bytes(out)

    def setw(self, a, v):
        """A word where the game keeps it (the moved ranges in BW-RAM on an SA-1 build)."""
        if self.g.sa1:
            for lo, hi, to in snes.SA1_MOVED:
                if lo <= a < hi:
                    self.g.bw[to + a - lo], self.g.bw[to + a - lo + 1] = v & 0xFF, v >> 8
                    return
        self.g.e.ram[a], self.g.e.ram[a + 1] = v & 0xFF, v >> 8


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    out.mkdir(parents=True, exist_ok=True)
    g = Snes(rom)
    e = g.e
    r = Reader(g)
    e.unserialize(g.bases[0])
    r.setw(0xE708, 0)                      # OptFights: on (in play)
    r.setw(0x34C4, 2)                      # OptPen: on
    keep = collections.deque(maxlen=20 * FPS)
    fulls = collections.deque(maxlen=21)
    fight_at, frame = None, 0
    last_clock, still = None, 0
    while frame < limit * 60 * FPS:
        # the intermission and other screens wait for a button: START tapped while the clock stands still for 5 s
        e.held = {3} if still > 5 * FPS and frame % 60 < 4 else set()
        e.lib.retro_run()
        frame += 1
        clock = struct.unpack("<H", r.read(0x1632, 2))[0]
        still = still + 1 if clock == last_clock else 0
        last_clock = clock
        ms = frame * 1000 // FPS
        sample = struct.pack("<q", ms) + b"".join(r.read(s, n) for s, n in snes.BLOCKS)
        keep.append(sample)
        if frame % FPS == 0:
            fulls.append(struct.pack("<q", ms) + r.read(0, snes.RAM_SIZE))
            lowload.breathe()
        flags = [r.read(snes.OBJ_FLAGS + 2 * k, 2) for k in range(12)]
        if fight_at is None and any(struct.unpack("<H", f)[0] & snes.FIGHTER for f in flags):
            fight_at = frame
            keep = collections.deque(keep, maxlen=60 * FPS)
            fulls = collections.deque(fulls, maxlen=61)
            print(f"a fight at frame {frame} ({frame / FPS / 60:.1f} min real), clock {struct.unpack('<H', r.read(0x1632, 2))[0]}",
                  flush=True)
        if fight_at is not None and frame - fight_at >= 40 * FPS:
            break
    if fight_at is None:
        print(f"no fight in {limit} minutes")
        return
    data = Path(rom).read_bytes()
    layout = {"blocks": [list(b) for b in snes.BLOCKS], "recorded_by": "snes_fight_capture", "system": "snes",
              "rom_crc32": f"{zlib.crc32(snes.strip_header(data)[:0x100000]):08x}"}
    (out / "capture.json").write_text(json.dumps(layout))
    with gzip.open(out / "fast.bin.gz", "wb", compresslevel=3) as fh:
        fh.write(b"".join(keep))
    with gzip.open(out / "full.bin.gz", "wb", compresslevel=3) as fh:
        fh.write(b"".join(fulls))
    print(f"{len(keep)} samples, {len(fulls)} full snapshots written to {out}")


if __name__ == "__main__":
    main()
