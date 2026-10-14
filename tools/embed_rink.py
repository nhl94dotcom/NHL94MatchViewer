"""Writes rink_gens.js: the rink picture (rink_gens.png) as a data URL that viewer.html loads as a script.

Browsers treat a picture loaded straight from a local file as foreign, and a canvas that has drawn one can no longer
be read back or recorded. A picture given as a data URL is not foreign, so with this file the viewer can save clips
(video and GIF). Run it again if rink_gens.png changes.
"""
import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    data = base64.b64encode((ROOT / "rink_gens.png").read_bytes()).decode("ascii")
    (ROOT / "rink_gens.js").write_text(f"window.NHL94_RINK = 'data:image/png;base64,{data}';\n", encoding="ascii")
    print(f"rink_gens.js: {len(data) // 1024} KB")


if __name__ == "__main__":
    main()
