"""Live broadcast of the game being recorded (2026-10-18): the helper's recording so far is converted every few seconds
(tools/export_match.py, the full converter, so the live page has everything a finished game file has) and only what
changed since the last upload is sent to a public S3 bucket, where the viewer (in live mode) fetches it, merges it into
its match and plays a few seconds behind.

Layout under s3://<bucket>/<prefix>/ (prefix "live/<channel>"):
- index.html            the viewer, told to play live (window.NHL94_LIVE = 'live.json')
- rink_*.png / .js      the rink pictures and bench masks the viewer loads beside itself
- sprites/<rom>.js, sounds/<rom>.js   the game's sprite and sound libraries (sent when a game starts)
- live.json             the manifest: {status: waiting / live / final, game, seq, snapshot, ...}; never cached
- data/<game>/s<k>.json the whole match as of update k (gzip); a page joining late starts from the newest one
- data/<game>/c<n>.json what changed in update n (gzip): {key: {s: value} | {p: index, v: tail} | {d: {...}} | {x: 1}}
  (a string or list keeps its first `p` items and gets `v` appended; a dict is patched key by key).

Standalone test: python tools/live_broadcast.py --test <capture folder> <out folder> feeds a recorded game in at
--speed times real time and writes what would be uploaded to <out folder> instead of S3 (serve it with
python -m http.server to watch).
"""
import argparse
import gzip
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time
import traceback
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems.common import ROOT  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent      # where viewer.html and the rink pictures are (or the exe's copy)
INTERVAL_S = 5.0          # at most one update this often (a conversion near the end of a game takes about 8 s)
SNAPSHOT_EVERY = 6        # a whole-match snapshot every this many updates, for pages that join late
STATIC_FILES = ["rink_gens.png", "rink_snes.png", "rink_gens.js", "rink_snes.js", "rink_benches.js", "rink_benches_snes.js"]


# ------------------------------------------------------------------------------------------------------ uploading
class S3Target:
    """Uploads with boto3, or with the AWS command line when boto3 has no credentials it can use."""

    def __init__(self, bucket, prefix):
        self.bucket, self.prefix = bucket, prefix.strip("/")
        self.client = None
        try:
            import boto3
            client = boto3.client("s3")
            client.head_bucket(Bucket=bucket)
            self.client = client
        except Exception:
            self.client = None
        self.url = f"https://{bucket}.s3.amazonaws.com/{self.prefix}/index.html"

    def put(self, key, body, content_type, encoding=None, cache="no-cache, max-age=0"):
        key = f"{self.prefix}/{key}"
        if self.client:
            extra = {"ContentType": content_type, "CacheControl": cache}
            if encoding:
                extra["ContentEncoding"] = encoding
            self.client.put_object(Bucket=self.bucket, Key=key, Body=body, **extra)
            return
        tmp = ROOT / "captures" / "_live_upload.tmp"
        tmp.write_bytes(body)
        cmd = ["aws", "s3", "cp", str(tmp), f"s3://{self.bucket}/{key}", "--content-type", content_type,
               "--cache-control", cache, "--only-show-errors"]
        if encoding:
            cmd += ["--content-encoding", encoding]
        cmd[0] = shutil.which("aws") or "aws"
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip()[-300:])


class FolderTarget:
    """Writes what would be uploaded into a local folder (for testing). Gzipped data is stored gzipped, as on S3;
    python -m http.server doesn't send Content-Encoding, so the test page is told to unzip it itself."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.url = "http://localhost:8099/index.html"

    def put(self, key, body, content_type, encoding=None, cache=None):
        path = self.folder / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


# ---------------------------------------------------------------------------------------------------------- diffs
def common_prefix(a, b):
    n = min(len(a), len(b))
    i, step = 0, 4096
    while i < n:
        j = min(n, i + step)
        if a[i:j] == b[i:j]:
            i = j
            continue
        while a[i] == b[i]:
            i += 1
        return i
    return n


def diff(old, new):
    """What turns `old` into `new` (see the module comment)."""
    out = {}
    for k, v in new.items():
        if k not in old:
            out[k] = {"s": v}
            continue
        o = old[k]
        if o == v:
            continue
        if isinstance(v, (list, str)) and type(o) is type(v):
            i = common_prefix(o, v)
            if i == len(o):
                out[k] = {"p": i, "v": v[i:]}
            elif i > len(v) // 2:
                out[k] = {"p": i, "v": v[i:]}
            else:
                out[k] = {"s": v}
        elif isinstance(v, dict) and isinstance(o, dict):
            out[k] = {"d": diff(o, v)}
        else:
            out[k] = {"s": v}
    for k in old:
        if k not in new:
            out[k] = {"x": 1}
    return out


def packed(obj):
    return gzip.compress(json.dumps(obj, separators=(",", ":")).encode(), compresslevel=6)


# ----------------------------------------------------------------------------------------------------- the stream
def read_partial_gzip(path):
    """Everything decompressible so far from a gzip file still being written (the recorder sync-flushes it)."""
    data = path.read_bytes()
    try:
        return zlib.decompressobj(31).decompress(data)
    except zlib.error:
        return b""


class Broadcaster:
    def __init__(self, target, rom_path=None):
        self.target = target
        self.rom_path = rom_path
        self.lock = threading.Lock()
        self.game = None
        self.sent = None
        self.seq = 0
        self.snapshot = 0
        self.sent_libraries = set()
        self.work = ROOT / "captures" / "_live_work"
        self.thread = None
        self.stop = threading.Event()
        self.last_error = None

    # The page and the files it loads beside itself.
    def publish_page(self):
        html = (PROJECT / "viewer.html").read_text(encoding="utf-8")
        boot = "<script>window.NHL94_LIVE = 'live.json';</script>\n"
        if isinstance(self.target, FolderTarget):
            boot = "<script>window.NHL94_LIVE = 'live.json'; window.NHL94_LIVE_UNZIP = true;</script>\n"
        html = html.replace("<script src=\"rink_gens.js\"></script>", boot + "<script src=\"rink_gens.js\"></script>", 1)
        html = html.replace("<title>", "<title>LIVE · ", 1)
        self.target.put("index.html", html.encode("utf-8"), "text/html; charset=utf-8")
        for name in STATIC_FILES:
            path = PROJECT / name
            if not path.exists():
                path = ROOT / name
            if path.exists():
                kind = "image/png" if name.endswith(".png") else "application/javascript"
                self.target.put(name, path.read_bytes(), kind, cache="max-age=3600")
        self.manifest("waiting")

    def manifest(self, status, extra=None):
        body = {"status": status, "game": self.game, "seq": self.seq, "snapshot": self.snapshot,
                "updated": round(time.time(), 1), "interval": INTERVAL_S}
        if extra:
            body.update(extra)
        self.target.put("live.json", json.dumps(body).encode(), "application/json")

    def send_libraries(self, rom):
        for folder in ("sprites", "sounds"):
            key = f"{folder}/{rom}.js"
            if key in self.sent_libraries:
                continue
            path = ROOT / folder / f"{rom}.js"
            if path.exists():
                self.target.put(key, path.read_bytes(), "application/javascript", cache="max-age=86400")
                self.sent_libraries.add(key)

    # One game.
    def start_game(self, name):
        with self.lock:
            self.game, self.sent, self.seq, self.snapshot = name, None, 0, 0

    def convert_partial(self, folder, record_size):
        """Convert the recording so far; returns the match (dict) or None."""
        data = read_partial_gzip(folder / "fast.bin.gz")
        data = data[: len(data) - len(data) % record_size]
        if len(data) < record_size * 120:  # under a couple of seconds of play
            return None
        work = self.work
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy(folder / "capture.json", work / "capture.json")
        (work / "fast.bin").write_bytes(data)
        out = work / "out"
        args = [str(work), "--name", self.game, "--out", str(out)] + (["--rom", str(self.rom_path)] if self.rom_path else [])
        if getattr(sys, "frozen", False):
            import export_match
            export_match.main(args)
        else:
            cmd = [sys.executable, str(Path(__file__).resolve().parent / "export_match.py")] + args
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout).strip()[-300:])
        return load_match(out / f"{self.game}.js")

    def send(self, match, status="live"):
        """Upload what changed since the last upload."""
        with self.lock:
            match["name"] = self.game
            if match.get("rom"):
                self.send_libraries(match["rom"])
            self.seq += 1
            base = f"data/{self.game}"
            if self.sent is None or self.seq - self.snapshot >= SNAPSHOT_EVERY or status == "final":
                self.target.put(f"{base}/s{self.seq}.json", packed(match), "application/json", "gzip", "max-age=31536000")
                self.snapshot = self.seq
            else:
                self.target.put(f"{base}/c{self.seq}.json", packed(diff(self.sent, match)), "application/json", "gzip",
                                "max-age=31536000")
            self.sent = match
            score = match.get("score") or [0, 0]
            self.manifest(status, {"teams": [match.get("team1"), match.get("team2")], "score": score[-2:],
                                   "seconds": round(match["t"][-1] / 1000)})

    def run_game(self, recording, record_size):
        """The update loop while `recording` is going (its folder's fast.bin.gz grows); stops on self.stop."""
        while not self.stop.is_set():
            started = time.time()
            try:
                match = self.convert_partial(recording.folder, record_size)
                if match:
                    self.send(match)
                    self.last_error = None
            except Exception as e:
                if str(e) != self.last_error:
                    print(f"Live broadcast: update failed: {e}")
                    traceback.print_exc()
                self.last_error = str(e)
            self.stop.wait(max(0.5, INTERVAL_S - (time.time() - started)))

    def begin(self, recording, record_size):
        self.stop.clear()
        self.start_game(recording.name)
        self.thread = threading.Thread(target=self.run_game, args=(recording, record_size), daemon=True)
        self.thread.start()

    def end(self, final_match_path=None, game=None):
        """The game is over (or the recording stopped): one last update from the finished match file. `game`: the
        game it belongs to; skipped when a newer game has started since."""
        if game is not None and game != self.game:
            return
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=60)
        try:
            if final_match_path and Path(final_match_path).exists():
                self.send(load_match(final_match_path), status="final")
            elif self.sent is not None:
                self.manifest("final")
        except Exception as e:
            print(f"Live broadcast: final update failed: {e}")


def load_match(path):
    text = Path(path).read_text(encoding="utf-8")
    return json.loads(text[text.index("{"): text.rindex("}") + 1])


# ---------------------------------------------------------------------------------------------------------- test
class _FakeRecording:
    def __init__(self, name, folder):
        self.name, self.folder = name, folder


def test(capture, out, speed, rom):
    """Feed a recorded game into a growing fast.bin.gz at `speed` times real time and broadcast it to a folder."""
    capture = Path(capture)
    layout = json.loads((capture / "capture.json").read_text())
    size = 8 + sum(b[1] for b in layout["blocks"])
    raw = (capture / "fast.bin").read_bytes() if (capture / "fast.bin").exists() else gzip.decompress((capture / "fast.bin.gz").read_bytes())
    folder = ROOT / "captures" / "_live_test_feed"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    shutil.copy(capture / "capture.json", folder / "capture.json")
    b = Broadcaster(FolderTarget(out), rom)
    b.publish_page()
    rec = _FakeRecording(capture.name + "_live", folder)
    gz = gzip.open(folder / "fast.bin.gz", "wb", compresslevel=3)
    b.begin(rec, size)
    t0 = time.time()
    for i in range(0, len(raw), size):
        ms = struct.unpack_from("<q", raw, i)[0]
        while (time.time() - t0) * 1000 * speed < ms:
            gz.flush(zlib.Z_SYNC_FLUSH)
            time.sleep(0.05)
        gz.write(raw[i:i + size])
    gz.close()
    final = ROOT / "captures" / "_live_work" / "final"
    subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "export_match.py"), str(folder), "--name",
                    rec.name, "--out", str(final)] + (["--rom", str(rom)] if rom else []), cwd=ROOT, check=True)
    b.end(final / f"{rec.name}.js")
    print("done:", b.seq, "updates")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--test", nargs=2, metavar=("CAPTURE", "OUT"))
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--rom", type=Path)
    a = ap.parse_args()
    if a.test:
        test(a.test[0], a.test[1], a.speed, a.rom)
