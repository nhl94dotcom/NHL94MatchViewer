"""Writes rink_gens.js and rink_snes.js: the rink pictures (rink_gens.png, rink_snes.png) as data URLs that viewer.html
loads as scripts.

Browsers treat a picture loaded straight from a local file as foreign, and a canvas that has drawn one can no longer
be read back or recorded. A picture given as a data URL is not foreign, so with these files the viewer can save clips
(video and GIF). Run it again if a picture changes.
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PICTURES = {"rink_gens.png": ("rink_gens.js", "NHL94_RINK"), "rink_snes.png": ("rink_snes.js", "NHL94_RINK_SNES")}


def main():
    for picture, (target, variable) in PICTURES.items():
        if not (ROOT / picture).exists():
            continue
        data = base64.b64encode((ROOT / picture).read_bytes()).decode("ascii")
        (ROOT / target).write_text(f"window.{variable} = 'data:image/png;base64,{data}';\n", encoding="ascii")
        print(f"{target}: {len(data) // 1024} KB")


if __name__ == "__main__":
    main()
