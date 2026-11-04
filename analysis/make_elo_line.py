"""Number lines of the Classic teams' Elo adjustments (2026-11-04, the user): where each team falls, so the gaps show better than in a ranking. Both systems share one scale, so they
can be compared, and the SNES has a zoomed version too. Reads reports/classic_team_elo.json (analysis/league_team_elo.py) and writes docs/img/elo_teams_genesis, elo_teams_snes and
elo_teams_snes_zoom as .svg, plus a .png of each for pasting, through headless Edge.
python analysis/make_elo_line.py"""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOW, HIGH = -115, 100
MIN_SHOWN, ROUGH = 100, 300
INK, MUTED, GRID, MARK, SURFACE = "#0b0b0b", "#52514e", "#dcdcd8", "#2a78d6", "#fcfcfb"
WIDTH, MARGIN, ROW, HEAD, FOOT = 1400, 34, 36, 92, 92
LABEL_WIDTH = 13.0                                      # points of the scale a label takes
TITLES = {"Genesis": "Genesis Classic", "SNES": "SNES Classic"}
NAMES = {"Genesis": "elo_teams_genesis", "SNES": "elo_teams_snes"}
FONT = "Segoe UI, Helvetica, Arial, sans-serif"


def place(values, width):
    """{team: level}, levels +1, -1, +2, -2 ... away from the line, so no two labels overlap."""
    last, out = {}, {}
    for t, v in sorted(values.items(), key=lambda kv: kv[1]):
        level = 1
        while t not in out:
            for s in (level, -level):
                if v - last.get(s, -1e9) >= width:
                    out[t], last[s] = s, v
                    break
            level += 1
    return out


def minus(text):
    return text.replace("-", "−")


def draw(label, data, name, low=LOW, high=HIGH, step=25, foot="Both systems use the same scale."):
    teams = {t: v for t, v in data["teams"].items() if v["games"] >= MIN_SHOWN}
    values = {t: v["adj"] for t, v in teams.items()}
    levels = place(values, LABEL_WIDTH * (high - low) / (HIGH - LOW))
    top = max(abs(s) for s in levels.values())
    mid = HEAD + (top + 0.6) * ROW
    height = int(mid + (top + 0.6) * ROW + FOOT)
    x = lambda v: MARGIN + (v - low) * (WIDTH - 2 * MARGIN) / (high - low)
    y0, y1 = mid - (top + 0.5) * ROW, mid + (top + 0.5) * ROW
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" font-family="{FONT}">',
         f'<rect width="{WIDTH}" height="{height}" fill="{SURFACE}"/>',
         f'<text x="{MARGIN}" y="38" font-size="25" font-weight="700" fill="{INK}">{TITLES[label]}: Elo adjustment by team</text>',
         f'<text x="{MARGIN}" y="66" font-size="16" fill="{MUTED}">Points added to a coach\'s Elo for using the team. +50 is about a 57% win chance against an even coach on the average team.</text>']
    for tick in range(-step * (-low // step), high + 1, step):
        s.append(f'<line x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{y0:.1f}" y2="{y1:.1f}" stroke="{GRID}" stroke-width="1"/>')
        s.append(f'<text x="{x(tick):.1f}" y="{y1 + 22:.1f}" font-size="15" text-anchor="middle" fill="{MUTED}">{minus(f"{tick:+d}") if tick else "0"}</text>')
    s.append(f'<text x="{x(0):.1f}" y="{y1 + 40:.1f}" font-size="13" text-anchor="middle" fill="{MUTED}">average team</text>')
    s.append(f'<line x1="{x(low):.1f}" x2="{x(high):.1f}" y1="{mid:.1f}" y2="{mid:.1f}" stroke="{INK}" stroke-width="2"/>')
    for t, v in sorted(values.items(), key=lambda kv: abs(levels[kv[0]]), reverse=True):
        ly = mid - levels[t] * ROW
        s.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{mid:.1f}" y2="{ly:.1f}" stroke="{MUTED}" stroke-width="1"/>')
    for t, v in values.items():
        ly = mid - levels[t] * ROW
        rough = teams[t]["games"] < ROUGH
        text = minus(f"{t} {v:+.0f}")
        w = 9.4 * len(text) + 8
        s.append(f'<rect x="{x(v) - w / 2:.1f}" y="{ly - 13:.1f}" width="{w:.1f}" height="26" rx="4" fill="{SURFACE}"/>')
        s.append(f'<text x="{x(v):.1f}" y="{ly + 6:.1f}" font-size="16.5" text-anchor="middle" fill="{INK}" font-weight="{400 if rough else 600}">{text}</text>')
    for t, v in values.items():
        rough = teams[t]["games"] < ROUGH
        s.append(f'<circle cx="{x(v):.1f}" cy="{mid:.1f}" r="7.5" fill="{SURFACE if rough else MARK}" stroke="{MARK}" stroke-width="2.5"/>')
    s.append(f'<text x="{MARGIN}" y="{height - 16}" font-size="14" fill="{MUTED}">Filled: 300+ Classic games. Hollow: 100-299 games, so rougher. Teams under 100 games aren\'t shown. {foot}</text>')
    s.append("</svg>")
    path = ROOT / "docs" / "img" / f"{name}.svg"
    path.write_text("\n".join(s), encoding="utf-8")
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    png = path.with_suffix(".png")
    subprocess.run([edge, "--headless=new", "--hide-scrollbars", f"--screenshot={png}", f"--window-size={WIDTH},{height}", path.as_uri()], check=False, capture_output=True, timeout=60)
    print(path.name, "levels", top, "height", height, "png", png.exists())


def main():
    data = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    for label, name in NAMES.items():
        draw(label, data[label], name)
    draw("SNES", data["SNES"], "elo_teams_snes_zoom", -85, 60, 20, "This scale is about 1.5 times wider than the Genesis one.")


if __name__ == "__main__":
    main()
