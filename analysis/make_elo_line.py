"""The Classic teams' Elo adjustments as ranked dot plots (2026-11-04; redrawn 2026-11-19 for the user: ranked rows
instead of a number line, so every label has room, each with its 90% range, and the win chance it's worth). Reads
reports/classic_team_elo.json (analysis/league_team_elo.py) and writes to docs/img, each as .svg plus a .png for pasting
(headless Edge):
- elo_teams_genesis, elo_teams_snes: one system, on the scale both share;
- elo_teams_both: the two side by side on that scale, so the difference in spread shows at a glance;
- elo_teams_snes_zoom: the SNES on its own narrower scale.
Teams with fewer than MIN_SHOWN Classic games aren't drawn; a hollow dot marks a value from under ROUGH games in the
fit (rarely used teams are also pulled toward the average, so theirs read milder than their results).
python analysis/make_elo_line.py"""
import json
import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOW, HIGH = -125, 100
MIN_SHOWN, ROUGH = 100, 300
Z90 = 1.645
INK, MUTED, GRID, MARK, SURFACE, ZERO = "#0b0b0b", "#52514e", "#e4e3df", "#2a78d6", "#fcfcfb", "#8a8984"
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
TITLES = {"Genesis": "Genesis Classic", "SNES": "SNES Classic"}
CITY = {"ANH": "Anaheim", "BOS": "Boston", "BUF": "Buffalo", "CGY": "Calgary", "CHI": "Chicago", "DAL": "Dallas",
        "DET": "Detroit", "EDM": "Edmonton", "FLA": "Florida", "HFD": "Hartford", "LA": "Los Angeles", "MTL": "Montreal",
        "NJ": "New Jersey", "NYI": "NY Islanders", "NYR": "NY Rangers", "OTW": "Ottawa", "PHI": "Philadelphia",
        "PIT": "Pittsburgh", "QUE": "Quebec", "SJ": "San Jose", "STL": "St. Louis", "TB": "Tampa Bay", "TOR": "Toronto",
        "VAN": "Vancouver", "WPG": "Winnipeg", "WSH": "Washington"}
ROW, LABEL_W, VALUE_W, PANEL_W = 24, 150, 64, 560


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")


def minus(v):
    return f"{v:+.0f}".replace("-", "−") if round(v) else "0"


def wrap(text, chars):
    out, line = [], ""
    for w in text.split():
        if line and len(line) + 1 + len(w) > chars:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + [line] if line else out


def chance(points):
    return 100 / (1 + 10 ** (-points / 400))


def rows(data):
    teams = [(t, v) for t, v in data["teams"].items() if v["games"] >= MIN_SHOWN]
    return sorted(teams, key=lambda tv: -tv[1]["adj"])


def panel(x0, y0, title, data, low, high, step):
    """One ranked panel at (x0, y0): its svg parts and its height."""
    teams = rows(data)
    s = []
    plot_x0, plot_x1 = x0 + LABEL_W, x0 + LABEL_W + PANEL_W
    X = lambda v: plot_x0 + (v - low) * PANEL_W / (high - low)  # noqa: E731
    top = y0 + 46
    bottom = top + ROW * len(teams)
    s.append(f'<text x="{x0}" y="{y0 + 16}" font-size="17" font-weight="700" fill="{INK}">{esc(title)}</text>')
    # win-chance axis above, Elo points below
    for tick in range(-step * (-low // step), high + 1, step):
        s.append(f'<line x1="{X(tick):.1f}" x2="{X(tick):.1f}" y1="{top - 6}" y2="{bottom + 4}" stroke="{ZERO if tick == 0 else GRID}" '
                 f'stroke-width="{1.5 if tick == 0 else 1}"/>')
        s.append(f'<text x="{X(tick):.1f}" y="{bottom + 20}" font-size="12" text-anchor="middle" fill="{MUTED}">{minus(tick)}</text>')
        s.append(f'<text x="{X(tick):.1f}" y="{top - 12}" font-size="11" text-anchor="middle" fill="{MUTED}">{chance(tick):.0f}%</text>')
    s.append(f'<text x="{(plot_x0 + plot_x1) / 2:.1f}" y="{bottom + 38}" font-size="12" text-anchor="middle" fill="{MUTED}">'
             'Elo points for using the team (0 = the average team in use)</text>')
    s.append(f'<text x="{(plot_x0 + plot_x1) / 2:.1f}" y="{top - 28}" font-size="11" text-anchor="middle" fill="{MUTED}">'
             'win chance against an even coach on the average team</text>')
    for i, (t, v) in enumerate(teams):
        cy = top + ROW * i + ROW / 2
        if i % 2 == 0:
            s.append(f'<rect x="{x0}" y="{cy - ROW / 2:.1f}" width="{LABEL_W + PANEL_W + VALUE_W}" height="{ROW}" fill="#f3f2ee"/>')
        rough = v["fit_games"] < ROUGH
        lo_, hi_ = v["adj"] - Z90 * v["se"], v["adj"] + Z90 * v["se"]
        s.append(f'<text x="{x0 + 8}" y="{cy + 4.5:.1f}" font-size="13" fill="{INK}" font-weight="{400 if rough else 600}">'
                 f'{esc(CITY.get(t, t))}</text>')
        s.append(f'<line x1="{X(max(lo_, low)):.1f}" x2="{X(min(hi_, high)):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="{MARK}" '
                 f'stroke-width="2" stroke-opacity="0.45" stroke-linecap="round"/>')
        s.append(f'<circle cx="{X(v["adj"]):.1f}" cy="{cy:.1f}" r="5.5" fill="{SURFACE if rough else MARK}" stroke="{MARK}" stroke-width="2">'
                 f'<title>{esc(CITY.get(t, t))}: {minus(v["adj"])} Elo ({chance(v["adj"]):.1f}%), 90% range {minus(lo_)} to {minus(hi_)}; '
                 f'{v["games"]:,} Classic games, {v["fit_games"]:,} in the fit</title></circle>')
        s.append(f'<text x="{plot_x1 + 10}" y="{cy + 4.5:.1f}" font-size="13" fill="{INK}" font-weight="600">{minus(v["adj"])}</text>')
    return s, bottom + 46 - y0


def page(name, title, sub, panels, foot):
    width = 32 + sum(LABEL_W + PANEL_W + VALUE_W + 40 for _ in panels) - 40 + 32
    parts, heights, x = [], [], 32
    for ptitle, data, low, high, step in panels:
        s, h = panel(x, 92, ptitle, data, low, high, step)
        parts += s
        heights.append(h)
        x += LABEL_W + PANEL_W + VALUE_W + 40
    sub_lines, foot_lines = wrap(sub, (width - 64) / 7.0), wrap(foot, (width - 64) / 6.4)
    shift = 18 * (len(sub_lines) - 1)
    height = 92 + max(heights) + 46 + 17 * len(foot_lines) + shift
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">',
         f'<title>{esc(title)}</title>', f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
         f'<text x="32" y="38" font-size="23" font-weight="700" fill="{INK}">{esc(title)}</text>']
    s += [f'<text x="32" y="{64 + 18 * i}" font-size="14" fill="{MUTED}">{esc(t)}</text>' for i, t in enumerate(sub_lines)]
    s.append(f'<g transform="translate(0,{shift})">')
    s += parts
    s.append("</g>")
    y = height - 22 - 17 * len(foot_lines)
    s.append(f'<circle cx="40" cy="{y - 4}" r="5.5" fill="{MARK}" stroke="{MARK}" stroke-width="2"/>')
    s.append(f'<text x="52" y="{y}" font-size="12.5" fill="{MUTED}">300+ games in the fit</text>')
    s.append(f'<circle cx="212" cy="{y - 4}" r="5.5" fill="{SURFACE}" stroke="{MARK}" stroke-width="2"/>')
    s.append(f'<text x="224" y="{y}" font-size="12.5" fill="{MUTED}">fewer: rougher, and pulled toward 0</text>')
    s.append(f'<line x1="470" x2="500" y1="{y - 4}" y2="{y - 4}" stroke="{MARK}" stroke-width="2" stroke-opacity="0.45"/>')
    s.append(f'<text x="508" y="{y}" font-size="12.5" fill="{MUTED}">90% range</text>')
    s += [f'<text x="32" y="{height - 12 - 17 * (len(foot_lines) - 1 - i)}" font-size="12.5" fill="{MUTED}">{esc(t)}</text>'
          for i, t in enumerate(foot_lines)]
    s.append("</svg>")
    path = ROOT / "docs" / "img" / f"{name}.svg"
    path.write_text("\n".join(s), encoding="utf-8")
    edge = shutil.which("msedge") or r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    png = path.with_suffix(".png")
    subprocess.run([edge, "--headless=new", "--hide-scrollbars", f"--screenshot={png}", f"--window-size={width},{height}",
                    path.as_uri()], check=False, capture_output=True, timeout=60)
    print(path.name, width, height, "png", png.exists())


def main():
    data = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    sub = ("Elo points to add to a coach's rating for using each team, fitted on every Classic league game; "
           "the same people judged on their different teams.")
    foot = (f"Teams with {MIN_SHOWN}+ Classic games. From the league result databases (analysis/league_team_elo.py); "
            "the method: COACH_RATING section 9.")
    for label, name in (("Genesis", "elo_teams_genesis"), ("SNES", "elo_teams_snes")):
        page(name, f"{TITLES[label]} teams: what each is worth", sub, [(TITLES[label], data[label], LOW, HIGH, 25)],
             foot + " Both systems' charts share this scale.")
    page("elo_teams_both", "Classic teams, Genesis and SNES on one scale",
         "Genesis teams spread about twice as far: the SNES hot / cold bug maxes about 46% of every player's ratings each game, "
         "evening rosters out.", [(TITLES["Genesis"], data["Genesis"], LOW, HIGH, 25), (TITLES["SNES"], data["SNES"], LOW, HIGH, 25)], foot)
    page("elo_teams_snes_zoom", "SNES Classic teams, on a narrower scale", sub, [(TITLES["SNES"], data["SNES"], -90, 70, 20)],
         foot + " This scale is about 1.4 times wider than the shared one.")


if __name__ == "__main__":
    main()
