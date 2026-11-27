"""A short GIF of a recorded moment, drawn by the viewer itself (2026-11-26, for the SNES deke guide): headless Edge
takes the viewer (the game folder's viewer.html) at successive times, zoomed and following the puck, and the frames
are cropped and joined. No emulator: it shows the recording as the viewer replays it.

python analysis/vision_free_clip.py MATCH_NAME START_S END_S OUT.gif [STEP_S] [ZOOM]"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
EDGE = next((p for p in (Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
                         Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe") if p.exists()), "msedge")


def shot(name, t, out, zoom, w=640, h=520):
    url = (HOME / "viewer.html").as_uri() + f"?match={name}&t={t:.3f}&zoom={zoom}&follow=1"
    subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}",
                    f"--screenshot={out}", "--virtual-time-budget=4000", url], capture_output=True, timeout=60)


def main():
    name, t0, t1, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), Path(sys.argv[4])
    step = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
    zoom = float(sys.argv[6]) if len(sys.argv) > 6 else 2.2
    frames = []
    with tempfile.TemporaryDirectory() as d:
        t = t0
        i = 0
        while t <= t1 + 1e-9:
            p = Path(d) / f"{i:03d}.png"
            shot(name, t, p, zoom)
            if p.exists():
                frames.append(Image.open(p).convert("RGB").crop((100, 68, 540, 356)).copy())
            t += step
            i += 1
    if not frames:
        raise SystemExit("no frames")
    frames = [f.resize((f.width * 3 // 4, f.height * 3 // 4), Image.LANCZOS).quantize(colors=96, method=Image.MEDIANCUT, dither=Image.NONE) for f in frames]
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(step * 1000), loop=0, optimize=True)
    print(out, len(frames), "frames")


if __name__ == "__main__":
    main()
