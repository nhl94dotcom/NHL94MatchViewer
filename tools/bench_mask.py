"""Finds the bench players' uniform pixels in rink_gens.png and writes rink_benches.js, which viewer.html uses to
repaint them in each match's team colours. (Browsers will not let a page read pixels back from a local image, so the
picking is done here, once.)

Away sits on the upper bench in coloured jerseys: the picture's blue there becomes the team's helmet/body ramp.
Home sits on the lower bench in white with trim: the picture's red there becomes the team's trim.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_read import read_png  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# x, y, width, height in picture pixels; team 0 = Home, 1 = Away; strip-colour roles for dark, medium, light
BENCHES = [
    {"rect": [55, 755, 55, 250], "team": 0, "kind": "red", "roles": [8, 9, 9]},
    {"rect": [55, 470, 55, 250], "team": 1, "kind": "blue", "roles": [13, 11, 12]},
]
TESTS = {
    "red": lambda r, g, b: r > g + 60 and r > b + 60,
    "blue": lambda r, g, b: b > r + 40 and b > g + 50,
}


def main():
    width, height, channels, rows = read_png(ROOT / "rink_gens.png")
    out = []
    for bench in BENCHES:
        x0, y0, w, h = bench["rect"]
        test = TESTS[bench["kind"]]
        pixels = {}
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                r, g, b = rows[y][x * channels:x * channels + 3]
                if test(r, g, b):
                    pixels[(x, y)] = max(r, g, b)
        lo, hi = min(pixels.values()), max(pixels.values())
        # One character per pixel: '.' = leave the picture alone, else 0-f = how bright it was (dark to light).
        mask = "".join(
            f"{round(15 * (pixels[(x, y)] - lo) / max(1, hi - lo)):x}" if (x, y) in pixels else "."
            for y in range(y0, y0 + h) for x in range(x0, x0 + w))
        out.append({"x": x0, "y": y0, "w": w, "h": h, "team": bench["team"], "roles": bench["roles"], "mask": mask})
        print(f"{'Home' if bench['team'] == 0 else 'Away'} bench: {len(pixels)} pixels to repaint")
    (ROOT / "rink_benches.js").write_text("window.NHL94_BENCHES = " + json.dumps(out, separators=(",", ":")) + ";\n", encoding="utf-8")


if __name__ == "__main__":
    main()
