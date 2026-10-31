"""Figures for docs/XG_MODELS.md, drawn as SVG files in docs/img (2026-10-31):
- xg_playout.svg: how each model plays a shot out (the steps it repeats, xG the share that go in);
- xg_map_genesis.svg / xg_map_snes.svg: the models' xG from each spot of the attacking zone for a standard shot at a
  set goalie (the shot speeds are the recorded games' medians; the goalie at his set spot for that puck, still);
- xg_calibration.svg: the models against the recorded games: shots grouped by their xG, the share that went in.
The maps run the models themselves (tools/xg.py, tools/xg_snes.py; the SNES one needs the ROM: NHL94_SNES_ROM, or the
scoring map's work copy); the calibration reads the match files (NHL94_HOME, default Documents\\NHL94 Viewer) and
prints only totals. python tools/make_xg_figures.py [maps] [calibration] [playout]   (all three by default)"""
import json
import math
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xg  # noqa: E402
import xg_snes as xs  # noqa: E402
from make_diagrams import svg, text, line, circle, ARROW, INK, SOFT, GRID, BLUE, ORANGE, GREEN, RED, OUT  # noqa: E402
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
SNES_ROM = Path(os.environ.get("NHL94_SNES_ROM") or Path.home() / "NHL94_scoring_map" / "nhl94snes.sfc")
# sequential blue, light to dark (the dataviz reference ramp, steps 100-700), one per xG band
BANDS = [(0.00, "#cde2fb"), (0.02, "#9ec5f4"), (0.05, "#6da7ec"), (0.10, "#3987e5"), (0.20, "#256abf"),
         (0.30, "#184f95"), (0.45, "#0d366b")]
BAND_LABELS = ["under 2%", "2-5%", "5-10%", "10-20%", "20-30%", "30-45%", "45%+"]
GL, CELL, N = 264, 10, 240            # goal line, grid step (units), play-outs a spot and aim


def band(v):
    return [c for lo, c in BANDS if v >= lo][-1]


def rect(x, y, w, h, fill, stroke="none", width=0, opacity=1):
    return (f"<rect x='{x:.1f}' y='{y:.1f}' width='{w:.1f}' height='{h:.1f}' fill='{fill}' fill-opacity='{opacity}' "
            f"stroke='{stroke}' stroke-width='{width}'/>")


# ------------------------------------------------------------------------------------------------------- the maps
def cells():
    for out in range(5, 176, CELL):
        for x in range(-115, 116, CELL):
            yield x, out


def genesis_set_spot(px, py):
    """The Genesis goalie's set spot for a puck: on the ellipse 26 across and 18 out in front of his net (front 261)."""
    dx, dy = px, py - 261
    L = math.hypot(dx, dy) or 1
    return 26 * dx / L, 261 + 18 * dy / L


def genesis_map(kind):
    rng = random.Random(7)
    speed = {"wrist": 12000, "one-timer": 20280}[kind]
    sha, ratings = 15, (48, 13, 13, 10)
    res = {}
    for x, out in cells():
        px, py = x, GL - out
        gx, gy = genesis_set_spot(px, py)
        aims = [xg.auto_aim(px, py, gx, gy, GL)] if kind == "one-timer" else range(9)
        reach = 12 if kind == "one-timer" else xg.REACH[min(19, (ratings[1] + 2) >> 1)]
        best = 0
        for aim in aims:
            goalie = xg.Goalie(gx, gy, 0, 0, *ratings, puck_control=10)
            tx, tz = xg.AIM[aim]
            g = sum(xg.play_out((px, py, 0), (tx, GL, tz), max(1.0, speed / 68), sha, (sha + 1) / (sha + 16),
                                goalie, reach, 0, rng) == "goal" for _ in range(N))
            best = max(best, g / N)
        res[(x, out)] = best
    return res


def snes_map(data, kind):
    rng = random.Random(7)
    speed, sha, ratings = {"wrist": 12349, "slap": 21752}[kind], 13, (48, 8, 8, 7)
    facing = 4
    frame = data.anim(0xE0FE, facing)[0][0]
    res = {}
    for x, out in cells():
        px, py = x, GL - out
        gx, gy = xs.set_spot(px, py, True)
        best = 0
        for aim in range(9):
            goalie = xs.Goalie(data, gx, gy, 0, 0, facing, frame, *ratings, puck_control=10)
            tx, tz = xs.AIM[aim]
            g = sum(xs.play_out(px, py, tx, GL, tz, max(1.0, speed / 136), sha, (sha + 1) / (sha + 16), goalie, rng)
                    == "goal" for _ in range(N))
            best = max(best, g / N)
        res[(x, out)] = best
    return res


def rink_panel(ox, oy, S, res, title, sub, mouth, cid):
    """The attacking zone from the blue line (88) to the end boards (35 behind the goal line, corners of radius 46), the
    net at the top; cells coloured by xG, clipped to the boards."""
    X = lambda x: ox + (x + 128) * S
    Y = lambda out: oy + (out + 35) * S                   # out from the goal line, down the page
    b = [text(X(0), oy - 26, title, 15, INK, "middle", "bold"), text(X(0), oy - 9, sub, 12, SOFT, "middle")]
    top, bottom, r = Y(-35), Y(GL - 88), 46 * S
    shape = (f"M{X(-128):.1f},{bottom:.1f} V{top + r:.1f} A{r:.1f},{r:.1f} 0 0 1 {X(-128) + r:.1f},{top:.1f} "
             f"H{X(128) - r:.1f} A{r:.1f},{r:.1f} 0 0 1 {X(128):.1f},{top + r:.1f} V{bottom:.1f} Z")
    b.append(f"<defs><clipPath id='{cid}'><path d='{shape}'/></clipPath></defs>")
    b.append(f"<path d='{shape}' fill='#f7fafc'/>")
    b.append(f"<g clip-path='url(#{cid})'>")
    for (x, out), v in res.items():
        b.append(rect(X(x - CELL / 2) + 0.5, Y(out - CELL / 2) + 0.5, CELL * S - 1, CELL * S - 1, band(v)))
    b.append("</g>")
    b.append(f"<path d='{shape}' fill='none' stroke='{SOFT}' stroke-width='1.5'/>")
    b.append(line(X(-128), Y(0), X(128), Y(0), RED, 1.5))                       # the goal line
    b.append(rect(X(-mouth), Y(-12), 2 * mouth * S, 12 * S, "none", INK, 1.5))  # the net
    b.append(line(X(-128), bottom, X(128), bottom, BLUE, 3))                    # the blue line
    for dx in (-70, 70):
        b.append(circle(X(dx), Y(62), 3, RED, RED))
        b.append(circle(X(dx), Y(62), 30 * S, "none", RED, 1, None, 0.6))
    for feet in (10, 20, 30, 40, 50):                                           # distance marks
        b.append(text(X(128) + 6, Y(feet * 3) + 4, f"{feet} ft", 10, SOFT))
    return b


def legend(x, y):
    b = [text(x, y, "xG (best aim)", 12, INK, weight="bold")]
    for i, (lab, (_, col)) in enumerate(zip(BAND_LABELS, BANDS)):
        b.append(rect(x + i * 74, y + 8, 70, 14, col))
        b.append(text(x + i * 74 + 35, y + 36, lab, 11, SOFT, "middle"))
    return b


def maps():
    S = 1.55
    pw = 256 * S
    ph = (GL - 88 + 35) * S
    W, H = int(2 * pw + 150), int(ph + 200)
    for sysn in ("genesis", "snes"):
        if sysn == "genesis":
            a, b2 = genesis_map("wrist"), genesis_map("one-timer")
            panels = (("Wrist shot", "12,000 off the stick, the best of the nine aims", a),
                      ("One-timer", "20,280, aimed by the game; the goalie's reach 12", b2))
            notes = ["Genesis model (tools/xg.py), Shot Accuracy 15; the goalie set and still at his spot for the puck (Weight 48,",
                     "Agility 13, Speed 13, aidef 10). Speeds: the recorded games' medians. Squares 10 units (3.3 ft); 240 play-outs each."]
            mouth = 20
        else:
            if not SNES_ROM.exists():
                print("no SNES ROM:", SNES_ROM)
                continue
            data = xs.RomData(SNES_ROM.read_bytes())
            a, b2 = snes_map(data, "wrist"), snes_map(data, "slap")
            panels = (("Wrist shot", "12,349 off the stick, the best of the nine aims", a),
                      ("Slapshot", "21,752 off the stick, the best of the nine aims", b2))
            notes = ["SNES model (tools/xg_snes.py), Shot Accuracy 13; the goalie set and still at his spot for the puck (Weight 48,",
                     "Agility 8, Speed 8, aidef 7). Speeds: the recorded games' medians. Squares 10 units (3.3 ft); 240 play-outs each."]
            mouth = 17
        body = []
        for i, (title, sub, res) in enumerate(panels):
            body += rink_panel(40 + i * (pw + 70), 60, S, res, title, sub, mouth, f"rink{i}")
        body += legend(40, ph + 95)
        for j, n in enumerate(notes):
            body.append(text(40, ph + 160 + j * 16, n, 11, SOFT))
        name = f"xg_map_{sysn}.svg"
        (OUT / name).write_text(svg(W, H, body, f"{'Genesis' if sysn == 'genesis' else 'SNES'} xG by shot spot"),
                                encoding="utf-8")
        print(name)


# ----------------------------------------------------------------------------------------------- the calibration
EDGES = [0, 0.05, 0.10, 0.20, 0.35, 0.55, 1.01]


def calibration_data():
    shots = {"genesis": [], "snes": []}
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season":
            continue
        try:
            m = json.loads(load_js_object(p))
        except (ValueError, OSError):
            continue
        sysn = m.get("system")
        if sysn not in shots:
            continue
        for s in m.get("shotList", []):
            if s.get("xg") is None or s["result"] == "blocked":
                continue
            shots[sysn].append((s["xg"], s["result"] == "goal"))
    return shots


def calibration():
    data = calibration_data()
    pw, ph, gap = 330, 300, 90
    W, H = 2 * pw + gap + 140, ph + 190
    b = []
    for i, (sysn, name) in enumerate((("genesis", "Genesis"), ("snes", "SNES"))):
        rows = data[sysn]
        ox, oy = 70 + i * (pw + gap), 70
        X = lambda v: ox + v * pw
        Y = lambda v: oy + ph - v * ph
        n, xs_, gs = len(rows), sum(r[0] for r in rows), sum(r[1] for r in rows)
        b.append(text(ox, oy - 34, name, 15, INK, weight="bold"))
        b.append(text(ox, oy - 16, f"{n} shots: {xs_:.1f} xG, {gs} goals", 12, SOFT))
        for v in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
            b.append(line(X(0), Y(v), X(1), Y(v), GRID, 1))
            b.append(text(X(0) - 8, Y(v) + 4, f"{int(v * 100)}%", 11, SOFT, "end"))
            b.append(text(X(v), Y(0) + 18, f"{int(v * 100)}%", 11, SOFT, "middle"))
        b.append(line(X(0), Y(0), X(1), Y(1), SOFT, 1.5, "5,4"))
        b.append(text(X(0.93), Y(1.0) - 6, "a perfect model", 11, SOFT, "end"))
        pts = []
        for lo, hi in zip(EDGES, EDGES[1:]):
            grp = [r for r in rows if lo <= r[0] < hi]
            if not grp:
                continue
            k = len(grp)
            px = sum(r[0] for r in grp) / k
            py = sum(r[1] for r in grp) / k
            se = math.sqrt(max(py * (1 - py), 0.25 / k) / k)
            pts.append((px, py, se, k))
        for px, py, se, k in pts:
            b.append(line(X(px), Y(max(0, py - se)), X(px), Y(min(1, py + se)), BLUE, 2))
        b.append("<polyline fill='none' stroke='" + BLUE + "' stroke-width='2' points='" +
                 " ".join(f"{X(px):.1f},{Y(py):.1f}" for px, py, se, k in pts) + "'/>")
        for px, py, se, k in pts:
            b.append(circle(X(px), Y(py), 5, BLUE, "#ffffff", 2))
            b.append(text(X(px) + 9, Y(py) + 15, f"{k}", 10, SOFT))
        b.append(text(X(0.5), Y(0) + 38, "the model's xG (the group's average)", 12, INK, "middle"))
        b.append(f"<text x='{ox - 44}' y='{Y(0.5):.1f}' font-size='12' fill='{INK}' text-anchor='middle' "
                 f"transform='rotate(-90 {ox - 44} {Y(0.5):.1f})'>share that went in</text>")
        print(name, n, round(xs_, 1), gs, [(round(px, 3), round(py, 3), k) for px, py, se, k in pts])
    b.append(text(70, H - 34, "Every shot in the recorded games with an xG (blocked shots left out), grouped by its xG: 0-5%, 5-10%, "
                  "10-20%, 20-35%, 35-55%, 55%+.", 11, SOFT))
    b.append(text(70, H - 18, "Each dot: the group's average xG against the share of it that scored; the bar is one standard "
                  "error; the small number is the group's shots.", 11, SOFT))
    (OUT / "xg_calibration.svg").write_text(svg(W, H, b, "xG models against the recorded games"), encoding="utf-8")
    print("xg_calibration.svg")


# --------------------------------------------------------------------------------------------- how it plays out
def playout():
    steps = [("1. The aim", "the stick's direction at", "the release: one of nine", "points on the net"),
             ("2. The shot code", "exact, with the chance", "(ShA + 1) / (ShA + 16);", "else the game's scatter"),
             ("3. The flight", "the puck under the", "game's gravity, to", "the goal line"),
             ("4. The goalie", "moves as the computer", "goalie does: rethink", "timer, look-ahead, save"),
             ("5. The save", "his body (and stick or", "glove) against the puck;", "the net, posts, crossbar")]
    bw, bh, gap = 168, 104, 26
    W, H = 5 * bw + 4 * gap + 60, 300
    b = [ARROW, text(30, 34, "How each model scores one shot: the game's own rules, played out many times", 15, INK, weight="bold")]
    y = 60
    for i, (head, *lines) in enumerate(steps):
        x = 30 + i * (bw + gap)
        b.append(f"<rect x='{x}' y='{y}' width='{bw}' height='{bh}' rx='8' fill='#eef5fc' stroke='{BLUE}' stroke-width='1.5'/>")
        b.append(text(x + 12, y + 24, head, 13, INK, weight="bold"))
        for j, ln in enumerate(lines):
            b.append(text(x + 12, y + 46 + j * 17, ln, 12, SOFT))
        if i < 4:
            b.append(line(x + bw + 3, y + bh / 2, x + bw + gap - 3, y + bh / 2, INK, 1.5, None, "marker-end='url(#arr)'"))
    ry = y + bh + 34
    xL, xR = 30, 30 + 4 * (bw + gap) + bw
    b.append(f"<path d='M{xR - bw / 2},{y + bh} V{ry} H{xL + bw / 2} V{y + bh + 4}' fill='none' stroke='{SOFT}' "
             f"stroke-width='1.5' stroke-dasharray='5,4' marker-end='url(#arr)'/>")
    b.append(text((xL + xR) / 2, ry - 8, "repeat (400 times by default), each with its own random draws", 12, SOFT, "middle"))
    b.append(f"<rect x='{(xL + xR) / 2 - 230}' y='{ry + 22}' width='460' height='46' rx='8' fill='#ffffff' stroke='{INK}' stroke-width='1.5'/>")
    b.append(text((xL + xR) / 2, ry + 43, "xG = the share of those play-outs that end in a goal", 14, INK, "middle", "bold"))
    b.append(text((xL + xR) / 2, ry + 60, "(the only number fitted to recorded games: how far off the goalie's spot may be)", 11, SOFT, "middle"))
    (OUT / "xg_playout.svg").write_text(svg(W, H, b, "How the xG models play a shot out"), encoding="utf-8")
    print("xg_playout.svg")


def main():
    want = set(sys.argv[1:]) or {"maps", "calibration", "playout"}
    if "playout" in want:
        playout()
    if "calibration" in want:
        calibration()
    if "maps" in want:
        maps()


if __name__ == "__main__":
    main()
