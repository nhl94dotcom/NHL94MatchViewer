"""Join recordings of one game that the helper split (a disconnect, highlights between periods, RetroArch restarted)
into one recording, then convert it. The pieces' samples are put end to end, each later piece's times moved to follow
the one before. The pieces' folders are kept; the new one is captures/<name>.
python tools/merge_recordings.py <new name> <piece folder> <piece folder> ...   (NHL94_HOME picks the games folder)"""
import gzip
import json
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from systems.common import ROOT  # noqa: E402
import systems  # noqa: E402

STEP_MS = 16  # the gap put between one piece's last sample and the next piece's first


def records(path, size):
    with gzip.open(path, "rb") as f:
        while True:
            r = f.read(size)
            if len(r) < size:
                return
            yield r


def main(argv):
    name, pieces = argv[0], [Path(p) for p in argv[1:]]
    layout = json.loads((pieces[0] / "capture.json").read_text())
    for p in pieces[1:]:
        if json.loads((p / "capture.json").read_text()).get("blocks") != layout.get("blocks"):
            raise SystemExit(f"{p} was recorded with a different layout")
    system = systems.get(layout.get("system", "genesis"))
    sizes = {"fast.bin.gz": 8 + sum(b[1] for b in layout["blocks"]), "full.bin.gz": 8 + system.RAM_SIZE}
    out = ROOT / "captures" / name
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy(pieces[0] / "capture.json", out / "capture.json")
    for fname, size in sizes.items():
        offset, last = 0, None
        with gzip.open(out / fname, "wb", compresslevel=3) as w:
            for p in pieces:
                if not (p / fname).exists():
                    continue
                first = None
                for r in records(p / fname, size):
                    ms = struct.unpack_from("<q", r)[0]
                    if first is None:
                        first = ms
                        if last is not None:
                            offset = last + STEP_MS - ms
                    last = ms + offset
                    w.write(struct.pack("<q", last) + r[8:])
    print(f"joined {len(pieces)} pieces into {out}")
    import export_match
    export_match.main([str(out)])


if __name__ == "__main__":
    main(sys.argv[1:])
