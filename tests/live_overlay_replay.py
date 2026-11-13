"""The local live mode, timed (2026-11-13, for the stream overlay): a recorded game fed into the live pipeline at real
speed, as live_broadcast.test does (the samples written to a growing fast.bin.gz at their own times), with
live_overlay writing stats.json and the OBS text files after each update, into OUT. Logged (OUT/replay_log.json):
- each update: the wall time since the start, how much of the game it covered (its last sample's time), so the lag
  (wall - covered) is how far behind play the stats are;
- each event (by kind and game time): the wall time it first appeared against the time it happened in the game.
Printed: the update lag (median, max) and each event kind's delay (median, max).

python tests/live_overlay_replay.py CAPTURE_FOLDER OUT [SPEED] [MINUTES]   (SPEED 1 = real time; MINUTES: stop early)"""
import gzip
import json
import shutil
import statistics as st
import struct
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import live_broadcast as L  # noqa: E402
import live_overlay  # noqa: E402
from systems.common import ROOT as HOME  # noqa: E402


def main():
    capture, out = Path(sys.argv[1]), Path(sys.argv[2])
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    minutes = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    out.mkdir(parents=True, exist_ok=True)
    layout = json.loads((capture / "capture.json").read_text())
    size = 8 + sum(b[1] for b in layout["blocks"])
    raw = gzip.decompress((capture / "fast.bin.gz").read_bytes())
    from systems import genesis, snes
    system = {"genesis": genesis, "snes": snes}[layout.get("system", "genesis")]
    full_raw = gzip.decompress((capture / "full.bin.gz").read_bytes()) if (capture / "full.bin.gz").exists() else b""
    fsize = 8 + system.RAM_SIZE                 # the recorder's full-RAM snapshots, fed in step (the converter reads them)
    folder = HOME / "captures" / "_live_replay_feed"
    if folder.parent == (HOME / "captures") and folder.name == "_live_replay_feed":
        shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    shutil.copy(capture / "capture.json", folder / "capture.json")
    b = L.Broadcaster(L.FolderTarget(out))
    t_first = struct.unpack_from("<q", raw, 0)[0]
    log = {"updates": [], "events": {}}
    t0 = None

    def after(match, status):
        wall = (time.time() - t0) * 1000 * speed
        covered = match["t"][-1] - match["t"][0]
        data = live_overlay.write(out, match, status)
        log["updates"].append([round(wall), round(covered)])
        for e in data["events"]:
            key = f"{e['kind']}|{e['period']} {e['clock']}|{e['team']}"
            if key not in log["events"]:
                happened = match["t"][min(e["f"], len(match["t"]) - 1)] - match["t"][0]
                log["events"][key] = [round(wall), round(happened)]

    b.after_send = after
    b.publish_page()
    rec = L._FakeRecording(capture.name + "_replay", folder)
    gz = gzip.open(folder / "fast.bin.gz", "wb", compresslevel=3)
    fz = gzip.open(folder / "full.bin.gz", "wb", compresslevel=3)
    fulls = [(struct.unpack_from("<q", full_raw, j)[0], j) for j in range(0, len(full_raw) - fsize + 1, fsize)]
    fi = 0
    t0 = time.time()
    b.begin(rec, size)
    for i in range(0, len(raw), size):
        ms = struct.unpack_from("<q", raw, i)[0] - t_first
        if ms > minutes * 60000:
            break
        while (time.time() - t0) * 1000 * speed < ms:
            gz.flush(zlib.Z_SYNC_FLUSH)
            fz.flush(zlib.Z_SYNC_FLUSH)
            time.sleep(0.05)
        while fi < len(fulls) and fulls[fi][0] - t_first <= ms:
            fz.write(full_raw[fulls[fi][1]:fulls[fi][1] + fsize])
            fi += 1
        gz.write(raw[i:i + size])
    gz.flush(zlib.Z_SYNC_FLUSH)
    time.sleep(8)
    b.stop.set()
    b.end()
    gz.close()
    fz.close()
    (out / "replay_log.json").write_text(json.dumps(log))
    lag = [w - c for w, c in log["updates"]]
    print(f"updates {len(lag)}; stats behind play: median {st.median(lag) / 1000:.1f} s, max {max(lag) / 1000:.1f} s (real)")
    kinds = {}
    for key, (w, h) in log["events"].items():
        kinds.setdefault(key.split("|")[0], []).append(w - h)
    for k, d in sorted(kinds.items()):
        print(f"  {k:10s} {len(d):3d} events: on screen {st.median(d) / 1000:.1f} s after it happened (median), max {max(d) / 1000:.1f} s")


if __name__ == "__main__":
    main()
