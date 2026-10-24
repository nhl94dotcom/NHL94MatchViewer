"""Run video_game.py over a folder of RetroArch videos in chunks (2026-10-23): the Genesis ones (320 wide; the SNES ones
are 256 wide and need their own reader), oldest first, one timeline and one games file per video in the work folder.
A chunk starts videos only until `minutes` have gone by and finishes the one under way; the next run skips videos
already done, so the archive is done in as many chunks as wanted (the user approves each). Gentle mode.
The reader's font (video_hud.py learn) and the rink picture (video_pilot.py) are read from the work folder.
python analysis/video/video_archive.py <videos folder> <work folder> [minutes]"""
import json
import sys
import time
from pathlib import Path

import av

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import video_game as VG  # noqa: E402
from lowload import gentle  # noqa: E402


def genesis(path):
    try:
        with av.open(str(path)) as f:
            return f.streams.video[0].width == 320
    except Exception:
        return False


def main():
    src, work = Path(sys.argv[1]), Path(sys.argv[2])
    minutes = float(sys.argv[3]) if len(sys.argv) > 3 else 60
    gentle()
    work.mkdir(parents=True, exist_ok=True)
    font, rink = work / "font.npz", work / "rink_from_video.png"
    videos = sorted((p for p in src.glob("*.mkv") if genesis(p)), key=lambda p: p.stat().st_mtime)
    todo = [p for p in videos if not (work / f"{p.stem}.games.json").exists()]
    print(f"{len(videos)} Genesis videos, {len(videos) - len(todo)} done before, {len(todo)} to go; "
          f"this chunk: up to {minutes:g} minutes", flush=True)
    t0, done = time.time(), 0
    for p in todo:
        if time.time() - t0 > minutes * 60:
            break
        tl = work / f"{p.stem}.timeline.tsv"
        VG.extract(str(p), str(font), str(rink), str(tl))
        VG.games(str(tl), str(work / f"{p.stem}.games.json"))
        done += 1
        print(f"  {p.name}: {len(json.loads((work / f'{p.stem}.games.json').read_text()))} games "
              f"({(time.time() - t0) / 60:.0f} min so far)", flush=True)
    print(f"chunk over: {done} videos in {(time.time() - t0) / 60:.0f} minutes; {len(todo) - done} left", flush=True)


if __name__ == "__main__":
    main()
