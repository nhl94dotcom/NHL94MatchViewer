"""Trial graphics of the Elo adjustments as shaded areas that show how sure each value is (2026-11-04, the user). Each team's shading is a normal curve around its value, with the spread from
resampling whole leagues (reports/classic_team_elo.json). Two forms: fading bands, a row per team; and bell curves, all on one line, each of the same area, so an uncertain team is low and wide.
The logos are copyrighted game art, so these go to Documents\\NHL94 Viewer\\team_graphics and never into the repository.
python analysis/make_elo_bands.py"""
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import league_team_study as L  # noqa: E402
import snes_logos  # noqa: E402
from make_elo_line import FONT, GRID, INK, MARGIN, MARK, MIN_SHOWN, MUTED, ROOT, ROUGH, SURFACE, TITLES, WIDTH, minus, place  # noqa: E402
from make_elo_line_logos import png  # noqa: E402

OUT = Path.home() / "Documents" / "NHL94 Viewer" / "team_graphics"
LOW, HIGH = -160, 110           # the same scale on both systems: every band fits to about two spreads
STEP = 25
ROW, LEFT, BOX_W, BOX_H = 54, 210, 62, 46
NOTE = "Darkest at the value, fading out to about 2.5 spreads. Spreads come from resampling whole leagues. * Under 300 games in the fit, where the real doubt is larger than the shading shows."


def teams_of(data):
    return {t: v for t, v in data["teams"].items() if v["games"] >= MIN_SHOWN}


def logo_tag(logo, cx, cy, box_w=BOX_W, box_h=BOX_H):
    uri, w, h = logo
    s = min(box_w / w, box_h / h)
    return f'<image x="{cx - w * s / 2:.1f}" y="{cy - h * s / 2:.1f}" width="{w * s:.1f}" height="{h * s:.1f}" href="{uri}" style="image-rendering:pixelated"/>'


def write(name, svg, width, height):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.svg"
    path.write_text("\n".join(svg), encoding="utf-8")
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    out = path.with_suffix(".png")
    subprocess.run([edge, "--headless=new", "--hide-scrollbars", f"--screenshot={out}", f"--window-size={width},{height}", path.as_uri()], check=False, capture_output=True)
    print(out, height, out.exists())


def head(width, height, label, sub):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">',
            f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
            f'<text x="{MARGIN}" y="38" font-size="25" font-weight="700" fill="{INK}">{TITLES[label]}: Elo adjustment by team, with how sure each one is</text>',
            f'<text x="{MARGIN}" y="66" font-size="16" fill="{MUTED}">{sub}</text>']


def bands(label, data, logos):
    teams = teams_of(data)
    order = sorted(teams, key=lambda t: -teams[t]["adj"])
    top = 96
    height = top + ROW * len(order) + 88
    x0, x1 = MARGIN + LEFT, WIDTH - MARGIN
    x = lambda v: x0 + (v - LOW) * (x1 - x0) / (HIGH - LOW)
    s = head(WIDTH, height, label, "Points added to a coach's Elo for using the team. A narrow, dark band is a value we can be surer of; a wide, pale one is a value we can't.")
    defs = ["<defs>"]
    for i, t in enumerate(order):
        v, se = teams[t]["adj"], teams[t]["se"]
        stops = "".join(f'<stop offset="{(k + 20) / 40:.3f}" stop-color="{MARK}" stop-opacity="{math.exp(-0.5 * (k / 8) ** 2) * min(1.0, 12 / max(se, 1)) ** .5:.3f}"/>' for k in range(-20, 21))
        defs.append(f'<linearGradient id="g{i}" x1="0" x2="1" y1="0" y2="0">{stops}</linearGradient>')
    defs.append("</defs>")
    s += defs
    bottom = top + ROW * len(order)
    tick = -STEP * (-LOW // STEP)
    while tick <= HIGH:
        s.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{top}" y2="{bottom}" stroke="{GRID if tick else MUTED}" stroke-width="1"/>')
        s.append(f'<text x="{x(tick):.1f}" y="{bottom + 22}" font-size="15" text-anchor="middle" fill="{MUTED}">{minus(f"{tick:+d}") if tick else "0"}</text>')
        tick += STEP
    s.append(f'<text x="{x(0):.1f}" y="{bottom + 40}" font-size="13" text-anchor="middle" fill="{MUTED}">average team</text>')
    for i, t in enumerate(order):
        v, se = teams[t]["adj"], teams[t]["se"]
        cy = top + ROW * i + ROW / 2
        left, right = x(v - 2.5 * se), x(v + 2.5 * se)
        s.append(f'<rect x="{left:.1f}" y="{cy - 15:.1f}" width="{right - left:.1f}" height="30" rx="4" fill="url(#g{i})"/>')
        s.append(f'<rect x="{x(v) - 1.5:.1f}" y="{cy - 19:.1f}" width="3" height="38" rx="1.5" fill="{INK}"/>')
        s.append(logo_tag(logos[t], MARGIN + 34, cy))
        rough = "*" if teams[t]["fit_games"] < ROUGH else ""
        s.append(f'<text x="{MARGIN + 76}" y="{cy + 6:.1f}" font-size="17" font-weight="600" fill="{INK}">{minus(f"{t}{rough} {v:+.0f}")}</text>')
    s.append(f'<text x="{MARGIN}" y="{height - 16}" font-size="14" fill="{MUTED}">{NOTE}</text>')
    s.append("</svg>")
    write(f"elo_bands_{label.lower()}", s, WIDTH, height)


def bells(label, data, logos):
    teams = teams_of(data)
    values = {t: v["adj"] for t, v in teams.items()}
    x0, x1 = MARGIN, WIDTH - MARGIN
    x = lambda v: x0 + (v - LOW) * (x1 - x0) / (HIGH - LOW)
    curve_h = 300
    levels = place(values, 104 * (HIGH - LOW) / (x1 - x0))
    rows_up = max(max(levels.values()), 1)
    rows_down = -min(min(levels.values()), -1)
    base = 110 + curve_h
    height = base + 60 + (rows_up + rows_down) * 80 + 90
    tightest = min(v["se"] for v in teams.values())
    density = lambda t, u: math.exp(-0.5 * ((u - values[t]) / teams[t]["se"]) ** 2) * tightest / teams[t]["se"]
    s = head(WIDTH, height, label, "Points added to a coach's Elo for using the team. Every curve has the same area, so a tall, narrow one is a value we can be surer of, and a low, wide one is a value we can't.")
    tick = -STEP * (-LOW // STEP)
    while tick <= HIGH:
        s.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{base - curve_h}" y2="{base}" stroke="{GRID if tick else MUTED}" stroke-width="1"/>')
        s.append(f'<text x="{x(tick):.1f}" y="{base + 22}" font-size="15" text-anchor="middle" fill="{MUTED}">{minus(f"{tick:+d}") if tick else "0"}</text>')
        tick += STEP
    for t in sorted(teams, key=lambda t: -teams[t]["se"]):
        pts = [f"{x(LOW):.1f},{base}"]
        u = LOW
        while u <= HIGH:
            pts.append(f"{x(u):.1f},{base - curve_h * density(t, u):.1f}")
            u += 1
        pts.append(f"{x(HIGH):.1f},{base}")
        s.append(f'<polygon points="{" ".join(pts)}" fill="{MARK}" fill-opacity="0.12" stroke="{MARK}" stroke-opacity="0.75" stroke-width="1.2"/>')
    s.append(f'<line x1="{x(LOW):.1f}" x2="{x(HIGH):.1f}" y1="{base}" y2="{base}" stroke="{INK}" stroke-width="2"/>')
    # logos in rows below the axis, each joined to its peak's spot on the line
    order = sorted(teams, key=lambda t: values[t])
    last = {}
    for t in order:
        row = 0
        while values[t] - last.get(row, -1e9) < 104 * (HIGH - LOW) / (x1 - x0):
            row += 1
        last[row] = values[t]
        cy = base + 86 + row * 86
        s.append(f'<line x1="{x(values[t]):.1f}" x2="{x(values[t]):.1f}" y1="{base}" y2="{cy - 28:.1f}" stroke="{MUTED}" stroke-width="1"/>')
        s.append(f'<rect x="{x(values[t]) - 50:.1f}" y="{cy - 27:.1f}" width="100" height="78" rx="5" fill="{SURFACE}"/>')
        s.append(logo_tag(logos[t], x(values[t]), cy, 62, 44))
        rough = "*" if teams[t]["fit_games"] < ROUGH else ""
        s.append(f'<text x="{x(values[t]):.1f}" y="{cy + 42:.1f}" font-size="15" font-weight="600" text-anchor="middle" fill="{INK}">{minus(f"{t}{rough} {values[t]:+.0f}")}</text>')
    height = base + 86 + (max(last) + 1) * 86 + 40
    s[0] = s[0].replace(f'height="{base + 60 + (rows_up + rows_down) * 80 + 90}"', f'height="{height}"').replace(f'{WIDTH} {base + 60 + (rows_up + rows_down) * 80 + 90}"', f'{WIDTH} {height}"')
    s[1] = f'<rect width="{WIDTH}" height="{height}" fill="{SURFACE}"/>'
    s.append(f'<text x="{MARGIN}" y="{height - 16}" font-size="14" fill="{MUTED}">Spreads come from resampling whole leagues. * Under 300 games in the fit, where the real doubt is larger than the curve shows.</text>')
    s.append("</svg>")
    write(f"elo_bells_{label.lower()}", s, WIDTH, height)


def main():
    data = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    genesis = {t["abbr"]: png(t["logo"], t["palettes"][0]) for t in L.genesis.read_teams(L.rom("9438f5dd_a738ea1c.bin")) if t["logo"] and any(c != "0" for c in t["logo"]["p"])}
    import base64
    snes = {t: ("data:image/png;base64," + base64.b64encode(snes_logos.png_bytes(w, h, pix)).decode(), w, h) for t, (w, h, pix) in snes_logos.logos(L.rom("cd85e387.smc")).items()}
    for label, logos in (("Genesis", genesis), ("SNES", snes)):
        bands(label, data[label], logos)
        bells(label, data[label], logos)


if __name__ == "__main__":
    main()
