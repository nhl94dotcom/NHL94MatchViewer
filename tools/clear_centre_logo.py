"""Paints the centre-ice logo out of a rink picture, so the viewer can draw the home team's own logo there:
python tools/clear_centre_logo.py <in.png> <out.png>

Everything inside the centre circle's painted ring (an ellipse in the picture, whose pixels are not square) is
replaced by ice from the clean band between the circle and the lower blue line, same columns, repeated down the
ellipse: the same texture, no markings. The Genesis
picture came with its logo blurred; the SNES one (rink_snes.png, from the user) had Montreal's, cleared with this
(the original is kept in reference/rink_snes_original.png).
"""
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from png_read import read_png  # noqa: E402


def write_png(path, width, height, rows):
    """8-bit RGB PNG from rows of bytes (r, g, b per pixel)."""
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
                           chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


# rink_snes.png: the ring's centre and the ellipse inside it, and the clean ice band below it (rows), in pixels
SNES = {"cx": 450, "cy": 776, "rx": 92, "ry": 64, "band": (856, 950)}


def main(src, out, cx, cy, rx, ry, band):
    width, height, channels, rows = read_png(src)
    rgb = [bytearray(b for x in range(width) for b in row[x * channels:x * channels + 3]) for row in rows]
    for y in range(cy - ry, cy + ry + 1):
        source = band[0] + (y - (cy - ry)) % (band[1] - band[0])
        for x in range(cx - rx, cx + rx + 1):
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1:
                rgb[y][3 * x:3 * x + 3] = rgb[source][3 * x:3 * x + 3]
    write_png(out, width, height, rgb)
    print(f"{out}: cleared the centre ellipse at ({cx}, {cy})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], **SNES)
