"""Writes rink_gens.js and rink_snes.js: the rink pictures (rink_gens.png, rink_snes.png) as data URLs that viewer.html
loads as scripts.

Browsers treat a picture loaded straight from a local file as foreign, and a canvas that has drawn one can no longer
be read back or recorded. A picture given as a data URL is not foreign, so with these files the viewer can save clips
(video and GIF). Run it again if a picture changes.

The picture goes in as a JPEG (quality 95, no chroma subsampling): the rink pictures are captures with hundreds of
thousands of colours, so a PNG of them is about 2.5 MB and this is about a quarter of that, with every pixel within a
few levels of the original (mean error about 1.4 of 255); the season page draws the same data, so a shared season
needs no PNG.
"""
import base64
import io
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PICTURES = {"rink_gens.png": ("rink_gens.js", "NHL94_RINK"), "rink_snes.png": ("rink_snes.js", "NHL94_RINK_SNES")}


def main():
    for picture, (target, variable) in PICTURES.items():
        if not (ROOT / picture).exists():
            continue
        jpeg = io.BytesIO()
        Image.open(ROOT / picture).convert("RGB").save(jpeg, "JPEG", quality=95, subsampling=0, optimize=True)
        data = base64.b64encode(jpeg.getvalue()).decode("ascii")
        (ROOT / target).write_text(f"window.{variable} = 'data:image/jpeg;base64,{data}';\n", encoding="ascii")
        print(f"{target}: {len(data) // 1024} KB")


if __name__ == "__main__":
    main()
