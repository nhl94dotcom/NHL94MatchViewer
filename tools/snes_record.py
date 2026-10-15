"""Research recorder for the SNES game: records Snes9x work RAM while you play, for finding what is not known yet
(who has the puck, the menu / pause / replay screens, per-player stats) and for the first SNES replays.

    python tools/snes_record.py [minutes]     (default 30; Ctrl+C stops it early)

Writes captures/snes_<date>_<time>/: fast.bin.gz (an 8-byte millisecond stamp, then work RAM $0000-$3FFF, about 60
times a second, only when it changed), full.bin.gz (all 128 KB once a second) and capture.json (system "snes").
Everything is recorded, menus and pauses included: this is for research, not the helper's game list.
"""
import datetime
import gzip
import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems import snes  # noqa: E402
from systems.common import ROOT  # noqa: E402

FAST = (0x0000, 0x4000)


def main(minutes=30.0):
    print("Looking for Snes9x with NHL '94 loaded...", flush=True)
    emu = None
    while emu is None:
        emu = snes.attach()
        if emu is None:
            time.sleep(2)
    print(f"Found: work RAM at {emu.ram:#x}, cartridge at {emu.rom:#x}", flush=True)
    folder = ROOT / "captures" / f"snes_{datetime.datetime.now():%Y-%m-%d_%H%M}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "capture.json").write_text(json.dumps({"system": "snes", "blocks": [list(FAST)], "recorded_by": "snes_record",
                                                     "rom_crc32": emu.rom_fingerprint()}))
    fast = gzip.open(folder / "fast.bin.gz", "wb", compresslevel=3)
    full = gzip.open(folder / "full.bin.gz", "wb", compresslevel=3)
    t0 = time.perf_counter()
    last_full, previous, samples, end = -10.0, None, 0, t0 + minutes * 60
    try:
        while time.perf_counter() < end:
            now = time.perf_counter()
            data = emu.read(*FAST)
            if data is None:
                print("Snes9x went away", flush=True)
                break
            stamp = struct.pack("<q", round((now - t0) * 1000))
            if data != previous:
                fast.write(stamp + data)
                previous, samples = data, samples + 1
            if now - last_full >= 1.0:
                whole = emu.read(0, snes.RAM_SIZE)
                if whole:
                    full.write(stamp + whole)
                last_full = now
                if samples and int(now - t0) % 30 == 0:
                    clock, period = struct.unpack_from("<H", data, snes.CLOCK)[0], struct.unpack_from("<H", data, snes.PERIOD)[0]
                    score = struct.unpack_from("<HH", data, snes.STAT_ADDRESSES["goals"])
                    print(f"{(now - t0) / 60:5.1f} min, {samples} samples; period {period + 1}, clock {clock // 60}:{clock % 60:02d}, score {score[0]}-{score[1]}", flush=True)
            time.sleep(max(0.0, 0.016 - (time.perf_counter() - now)))
    except KeyboardInterrupt:
        pass
    finally:
        fast.close()
        full.close()
        emu.close()
    print(f"Saved {samples} samples to {folder}", flush=True)


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 30.0)
