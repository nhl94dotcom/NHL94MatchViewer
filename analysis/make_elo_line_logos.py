"""The Elo number lines (make_elo_line.py) with team logos, for pasting. The logos are the centre-ice ones from the player's own Genesis ROM, used on both systems' lines as the SNES reader has
none. They are copyrighted game art, so the pictures go to Documents\\NHL94 Viewer\\team_graphics and never into the repository, like the sprites.
python analysis/make_elo_line_logos.py"""
import base64
import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import league_team_study as L  # noqa: E402
from make_elo_line import FONT, GRID, HIGH, INK, LOW, MARGIN, MARK, MIN_SHOWN, MUTED, ROOT, ROUGH, SURFACE, TITLES, WIDTH, minus, place  # noqa: E402

OUT = Path.home() / "Documents" / "NHL94 Viewer" / "team_graphics"
SCALE = 2                                               # screen pixels per logo pixel
CELL = 104                                              # pixels a logo and its value take across
ROW, HEAD, FOOT = 92, 92, 88


def png(logo, palette):
    """A logo as a PNG data URI, its empty border cropped."""
    w, h = logo["w"], logo["h"]
    px = [int(c, 16) for c in logo["p"]]
    cols = [x for x in range(w) if any(px[y * w + x] for y in range(h))]
    rows = [y for y in range(h) if any(px[y * w + x] for x in range(w))]
    x0, x1, y0, y1 = cols[0], cols[-1] + 1, rows[0], rows[-1] + 1
    raw = bytearray()
    for y in range(y0, y1):
        raw.append(0)
        for x in range(x0, x1):
            c = px[y * w + x]
            rgb = int(palette[c][1:], 16)
            raw += bytes(((rgb >> 16) & 255, (rgb >> 8) & 255, rgb & 255, 255 if c else 0))
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    head = struct.pack(">IIBBBBB", x1 - x0, y1 - y0, 8, 6, 0, 0, 0)
    blob = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(blob).decode(), x1 - x0, y1 - y0


def draw(label, data, logos, name, low, high, step, foot):
    teams = {t: v for t, v in data["teams"].items() if v["games"] >= MIN_SHOWN}
    values = {t: v["adj"] for t, v in teams.items()}
    plot = WIDTH - 2 * MARGIN
    levels = place(values, CELL * (high - low) / plot)
    top = max(levels.values())
    bottom = -min(levels.values())
    mid = HEAD + (top + 0.55) * ROW
    height = int(mid + (bottom + 0.55) * ROW + FOOT)
    x = lambda v: MARGIN + (v - low) * plot / (high - low)
    y0, y1 = mid - (top + 0.5) * ROW, mid + (bottom + 0.5) * ROW
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="{FONT}">',
         f'<rect width="{WIDTH}" height="{height}" fill="{SURFACE}"/>',
         f'<text x="{MARGIN}" y="38" font-size="25" font-weight="700" fill="{INK}">{TITLES[label]}: Elo adjustment by team</text>',
         f'<text x="{MARGIN}" y="66" font-size="16" fill="{MUTED}">Points added to a coach\'s Elo for using the team. +50 is about a 57% win chance against an even coach on the average team.</text>']
    for tick in range(-step * (-low // step), high + 1, step):
        s.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{y0:.1f}" y2="{y1:.1f}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x(tick):.1f}" y="{y1 + 22:.1f}" font-size="15" text-anchor="middle" fill="{MUTED}">{minus(f"{tick:+d}") if tick else "0"}</text>')
    s.append(f'<text x="{x(0):.1f}" y="{y1 + 40:.1f}" font-size="13" text-anchor="middle" fill="{MUTED}">average team</text>')
    s.append(f'<line x1="{x(low):.1f}" x2="{x(high):.1f}" y1="{mid:.1f}" y2="{mid:.1f}" stroke="{INK}" stroke-width="2"/>')
    for t, v in values.items():
        s.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{mid:.1f}" y2="{mid - levels[t] * ROW:.1f}" stroke="{MUTED}" stroke-width="1"/>')
    for t, v in values.items():
        cy = mid - levels[t] * ROW
        s.append(f'<rect x="{x(v) - CELL / 2 + 2:.1f}" y="{cy - 42:.1f}" width="{CELL - 4}" height="84" rx="5" fill="{SURFACE}"/>')
        uri, w, h = logos[t]
        s.append(f'<image x="{x(v) - w * SCALE / 2:.1f}" y="{cy - 12 - h * SCALE / 2:.1f}" width="{w * SCALE}" height="{h * SCALE}" href="{uri}" style="image-rendering:pixelated"/>')
        rough = teams[t]["games"] < ROUGH
        s.append(f'<text x="{x(v):.1f}" y="{cy + 38:.1f}" font-size="15.5" text-anchor="middle" fill="{INK}" font-weight="{400 if rough else 600}">{minus(f"{t} {v:+.0f}")}</text>')
    for t, v in values.items():
        rough = teams[t]["games"] < ROUGH
        s.append(f'<circle cx="{x(v):.1f}" cy="{mid:.1f}" r="7.5" fill="{SURFACE if rough else MARK}" stroke="{MARK}" stroke-width="2.5"/>')
    s.append(f'<text x="{MARGIN}" y="{height - 16}" font-size="14" fill="{MUTED}">Filled: 300+ Classic games. Hollow: 100-299 games, so rougher. Teams under 100 games aren\'t shown. {foot}</text>')
    s.append("</svg>")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.svg"
    path.write_text("\n".join(s), encoding="utf-8")
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    out = path.with_suffix(".png")
    subprocess.run([edge, "--headless=new", "--hide-scrollbars", f"--screenshot={out}", f"--window-size={WIDTH},{height}", path.as_uri()], check=False, capture_output=True, timeout=60)
    print(out, "levels", top, "height", height, out.exists())


def main():
    data = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    teams = L.genesis.read_teams(L.rom("9438f5dd_a738ea1c.bin"))
    logos = {t["abbr"]: png(t["logo"], t["palettes"][0]) for t in teams if t["logo"] and any(c != "0" for c in t["logo"]["p"])}
    missing = {label: [t for t, v in data[label]["teams"].items() if v["games"] >= MIN_SHOWN and t not in logos] for label in TITLES}
    print("teams with no logo:", missing)
    draw("Genesis", data["Genesis"], logos, "elo_teams_genesis_logos", LOW, HIGH, 25, "")
    draw("SNES", data["SNES"], logos, "elo_teams_snes_logos", -85, 60, 20, "This scale is about 1.5 times wider than the Genesis one.")


if __name__ == "__main__":
    main()
