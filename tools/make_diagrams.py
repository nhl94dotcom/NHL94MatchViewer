"""Draws the guides' diagrams as SVG files in docs/img, to scale from the game's numbers (GENESIS_MECHANICS /
SNES_MECHANICS). python tools/make_diagrams.py"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"

INK, SOFT, GRID = "#1f2933", "#52606d", "#d9e2ec"
BLUE, ORANGE, GREEN, RED, GOLD = "#3b82c4", "#e8833a", "#3f9d5c", "#c94040", "#d9a400"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"


def svg(w, h, body, title):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' {FONT}>\n"
            f"<title>{title}</title>\n<rect width='{w}' height='{h}' fill='#ffffff'/>\n" + "\n".join(body) + "\n</svg>\n")


def text(x, y, s, size=13, color=INK, anchor="start", weight="normal"):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{color}' text-anchor='{anchor}' font-weight='{weight}'>{s}</text>"


def line(x1, y1, x2, y2, color=INK, width=1.5, dash=None, extra=""):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return f"<line x1='{x1:.1f}' y1='{y1:.1f}' x2='{x2:.1f}' y2='{y2:.1f}' stroke='{color}' stroke-width='{width}'{d} {extra}/>"


def circle(x, y, r, fill="none", stroke=INK, width=1.5, dash=None, opacity=1):
    d = f" stroke-dasharray='{dash}'" if dash else ""
    return (f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{r:.1f}' fill='{fill}' fill-opacity='{opacity}' stroke='{stroke}' "
            f"stroke-width='{width}'{d}/>")


ARROW = ("<defs><marker id='arr' viewBox='0 0 10 10' refX='9' refY='5' markerWidth='7' markerHeight='7' "
         "orient='auto-start-reverse'><path d='M0,0 L10,5 L0,10 z' fill='#1f2933'/></marker></defs>")


# ---------------------------------------------------------------------------------------------- 1. saves are geometry
def saves():
    """The goalie's reach against the goal mouth, seen from above (Genesis: posts at +/-20, the goalie about 18 out)."""
    S, cx, gy = 8, 410, 380           # pixels per unit; screen x of the middle; screen y of the goalie's centre
    line_y = gy - 18 * S              # the goal line, 18 units behind him
    b = [ARROW]
    b.append(text(410, 28, "Saves are geometry: the goalie's reach against the goal mouth", 17, anchor="middle", weight="bold"))
    b.append(text(410, 48, "Seen from above, to scale. A puck that passes within his reach of his centre is stopped; anything wider goes by.",
                  12, SOFT, "middle"))
    # net
    b.append(f"<rect x='{cx - 20 * S}' y='{line_y - 15 * S}' width='{40 * S}' height='{15 * S}' fill='#f3f5f7' stroke='{SOFT}'/>")
    b.append(line(cx - 32 * S, line_y, cx + 32 * S, line_y, RED, 3))
    b.append(text(cx + 33 * S, line_y + 4, "goal line", 12, RED))
    for px in (-20, 20):
        b.append(circle(cx + px * S, line_y, 5, INK, INK))
    b.append(text(cx, line_y - 6 * S, "net", 12, SOFT, "middle"))
    # reach circles
    for r, color, dash, label in ((18, GREEN, "6 4", "18: pad stack (moved 6 to one side)"),
                                  (15, BLUE, None, "15: a person in net, or an agile computer goalie"),
                                  (12, ORANGE, None, "12: against a one-timer (or the least agile)")):
        b.append(circle(cx, gy, r * S, BLUE if r == 15 else "none", color, 2.5, dash, 0.10 if r == 15 else 1))
    b.append(circle(cx, gy, 4, INK, INK))
    b.append(text(cx + 8, gy + 4, "G", 13, INK, weight="bold"))
    # what's left open straight on, at reach 15 and 12
    y_open = line_y + 4 * S
    for r, color, row in ((15, BLUE, 0), (12, ORANGE, 1)):
        yy = y_open + row * 14
        for sgn in (-1, 1):
            b.append(line(cx + sgn * r * S, yy, cx + sgn * 20 * S, yy, color, 5))
    b.append(text(cx + 21 * S, y_open + 4, "left open, shooting straight on:", 12, SOFT))
    b.append(text(cx + 21 * S, y_open + 18, "5 units (1.7 ft) a side at reach 15,", 12, BLUE))
    b.append(text(cx + 21 * S, y_open + 32, "8 units (2.7 ft) a side at reach 12", 12, ORANGE))
    # legend
    ly = gy + 21 * S
    for i, (color, dash, label) in enumerate(((GREEN, "6 4", "18: pad stack (shifted 6 toward the side he slides to)"),
                                              (BLUE, None, "15: a person in net (always), or a computer goalie with top Agility"),
                                              (ORANGE, None, "12: against any one-timer; also the least agile computer goalie"))):
        y = ly + i * 20
        b.append(line(110, y - 4, 150, y - 4, color, 3, dash))
        b.append(text(160, y, label, 13))
    b.append(text(110, ly + 66, "Computer goalies: reach 12-15 by Agility. Only a puck at height 15 or less can hit him; low pucks meet his stick first.",
                  12, SOFT))
    b.append(text(110, ly + 82, "Shots come from below. 1 unit is about 4 inches; posts 20 units (6.7 ft) either side of the middle.", 12, SOFT))
    return svg(820, ly + 100, b, "Saves are geometry")


# ---------------------------------------------------------------------------------------------- 2. through the legs
def through_legs():
    """The butterfly's blind ring (Genesis): body circle 13, blade 11 to his side, the stick's 8-14 ring."""
    S, cx, cy = 11, 330, 300          # goalie's centre on screen; game +y (toward his net) is screen up
    reach, bx, by = 13, 11, -2.3      # a typical computer goalie; the blade in a butterfly / kick save
    P = lambda x, y: (cx + x * S, cy - y * S)
    b = [ARROW]
    b.append(text(360, 28, "Through the legs: the butterfly's blind ring (Genesis)", 17, anchor="middle", weight="bold"))
    b.append(text(360, 48, "Seen from above, to scale. The goalie faces down the page; his net is above him.", 12, SOFT, "middle"))
    gx, gy = P(0, 18)
    b.append(line(cx - 26 * S, gy, cx + 26 * S, gy, RED, 3))
    b.append(text(cx - 26 * S + 4, gy - 8, "goal line (net behind)", 12, RED))
    for px in (-20, 20):
        b.append(circle(cx + px * S, gy, 5, INK, INK))
    # body circle
    b.append(circle(cx, cy, reach * S, "#cfe3f5", BLUE, 2))
    # the blade's ring: 8-14 blind (evenodd annulus), within 8 the stick plays it
    X, Y = P(bx, by)
    ring = (f"<path fill='{ORANGE}' fill-opacity='0.55' fill-rule='evenodd' stroke='{ORANGE}' stroke-width='1.5' d='"
            f"M{X - 14 * S},{Y} a{14 * S},{14 * S} 0 1,0 {28 * S},0 a{14 * S},{14 * S} 0 1,0 {-28 * S},0 z "
            f"M{X - 8 * S},{Y} a{8 * S},{8 * S} 0 1,0 {16 * S},0 a{8 * S},{8 * S} 0 1,0 {-16 * S},0 z'/>")
    b.append(ring)
    b.append(circle(X, Y, 8 * S, GREEN, GREEN, 1.5, None, 0.35))
    b.append(f"<rect x='{X - 7}' y='{Y - 4}' width='14' height='8' fill='{INK}'/>")
    b.append(text(X, Y + 20, "blade", 12, INK, "middle", "bold"))
    b.append(line(cx - 7, cy - 7, cx + 7, cy + 7, INK, 2.5))
    b.append(line(cx - 7, cy + 7, cx + 7, cy - 7, INK, 2.5))
    b.append(text(cx - 12, cy - 10, "his centre", 12, INK, "end", "bold"))
    # the puck's path straight at his middle, one dot a frame at about 22,700 (5.5 units a frame)
    step = 22700 / 4096
    y = -13.4 - 4 * step              # one frame lands just short of his body, the next inside the ring
    p0, p1 = P(0, y - 2), P(0, 7)
    b.append(line(p0[0], p0[1], p1[0], p1[1], INK, 1.5, "4 3"))
    while True:
        px, py = P(0, y)
        in_ring = math.hypot(bx, y - by) <= 14
        in_body = abs(y) <= reach
        colour = "#ffffff" if in_ring else RED if in_body else INK
        b.append(circle(px, py, 5, colour, RED if colour == RED else INK, 1.5))
        if in_body and not in_ring:
            break
        y += step
    h0, h1 = P(0, y + 1), P(0, 16.5)
    b.append(line(h0[0], h0[1], h1[0], h1[1], RED, 2.5, None, "marker-end='url(#arr)'"))
    # notes on the right
    nx = 600
    notes = [(P(0, -12)[1], "1. Front strip: about 2 units of body", "test before the ring begins. A fast puck", "(3-7 units a frame) often steps over it."),
             (P(0, -2)[1], "2. Blind ring (8-14 from the blade):", "the stick doesn't play the puck, and the", "body test is skipped. It slides through."),
             (P(0, 10)[1], "3. Out of the ring behind his centre:", "the body test hits, and the bounce goes", "out from his centre: back, into the net.")]
    for yy, *ls in notes:
        b.append(line(cx + 2 * S, yy, nx - 8, yy, SOFT, 1, "2 3"))
        for i, s in enumerate(ls):
            b.append(text(nx, yy + 4 + i * 15, s, 12, INK if i == 0 else SOFT, weight="bold" if i == 0 else "normal"))
    ly = int(P(0, -40)[1])
    leg = [("#cfe3f5", BLUE, "body circle (reach 13 here; 12-15 by Agility)"),
           (GREEN, GREEN, "within 8 of the blade: the stick plays a low puck"),
           (ORANGE, ORANGE, "8-14 from the blade: nothing is tested at all")]
    for i, (f, s, label) in enumerate(leg):
        yy = ly + i * 20
        b.append(f"<rect x='70' y='{yy - 11}' width='26' height='13' fill='{f}' fill-opacity='0.6' stroke='{s}'/>")
        b.append(text(106, yy, label, 13))
    b.append(text(70, ly + 66, "Only a puck at height 5 or less that isn't rising meets the stick at all; lifted pucks get the body test as usual.", 12, SOFT))
    b.append(text(70, ly + 82, "Standing, his blade is in front of his middle, so the ring doesn't cover it. Dots: the puck once a frame at 22,700 (about 77 mph):", 12, SOFT))
    b.append(text(70, ly + 98, "black untouched, white inside the blind ring, red the body hit. Recorded: three goals like this in the ANA-ATL 2-on-2 game.", 12, SOFT))
    return svg(880, ly + 116, b, "Through the legs")


# ---------------------------------------------------------------------------------------------- 3. the nine aim points
def aim_points(system):
    s, post, outer = (16, 20, 20) if system == "genesis" else (15, 17, 22)
    S, W = 7, 820
    b = []
    name = "Genesis" if system == "genesis" else "SNES"
    b.append(text(W / 2, 28, f"The nine aim points ({name}): the d-pad as you shoot, in SCREEN directions", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The net as the shooter sees it, to scale. Up is always high and Down always along the ice; Left and Right swap with the direction you attack.",
                  12, SOFT, "middle"))
    arrows = {(0, 12): ("↑", "Up"), (1, 12): ("↗", "Up-right"), (1, 6): ("→", "Right"), (1, 0): ("↘", "Down-right"),
              (0, 0): ("↓", "Down"), (-1, 0): ("↙", "Down-left"), (-1, 6): ("←", "Left"), (-1, 12): ("↖", "Up-left"),
              (0, 6): ("·", "nothing held")}
    for panel, (ox, title, flip) in enumerate(((W * 0.27, "Attacking UP the screen", 1), (W * 0.73, "Attacking DOWN the screen", -1))):
        base = 250
        b.append(text(ox, 92, title, 15, INK, "middle", "bold"))
        b.append(text(ox, 110, "screen right = shooter's right" if flip == 1 else "screen right = shooter's LEFT", 12, SOFT, "middle"))
        # ice, posts, crossbar (height 13)
        b.append(line(ox - 30 * S, base, ox + 30 * S, base, SOFT, 2))
        b.append(f"<rect x='{ox - post * S}' y='{base - 13 * S}' width='{2 * post * S}' height='{13 * S}' fill='#f3f5f7' stroke='{INK}' stroke-width='3'/>")
        if outer > post:
            for sg in (-1, 1):
                b.append(f"<rect x='{ox + (post * S if sg > 0 else -outer * S)}' y='{base - 13 * S}' width='{(outer - post) * S}' height='{13 * S}' fill='{GOLD}' fill-opacity='0.35'/>")
        b.append(text(ox, base - 13 * S - 22, "crossbar at height 13", 11, SOFT, "middle"))
        b.append(text(ox - post * S, base + 36, "shooter's left", 11, SOFT, "middle"))
        b.append(text(ox + post * S, base + 36, "shooter's right", 11, SOFT, "middle"))
        for (dx, z), (a, label) in arrows.items():
            x, y = ox + dx * s * flip * S, base - z * S
            b.append(circle(x, y, 14, "#ffffff", BLUE, 2))
            b.append(text(x, y + 6, a, 18, BLUE, "middle", "bold"))
    ly = 320
    notes = ["The game aims at one of these nine spots, then adds a random error (unless the shot comes out exact: see the scatter diagram).",
             "The error only ever pushes the puck UP, so a high aim (just under the crossbar) can clear the bar; a low or middle aim has room.",
             "One-timers " + ("and computer shooters ignore the d-pad: the game picks the side away from the goalie (or high middle)." if system == "genesis"
                             else "follow the d-pad on the SNES; only computer shooters are aimed by the game."),
             "Pushing toward the net while attacking up means holding Up, which aims high."]
    if system == "snes":
        notes.append("SNES: the posts are a 5-unit band (gold) from 17 to 22 out, so a shot drifting outward rings off the post.")
    for i, n in enumerate(notes):
        b.append(text(60, ly + i * 18, n, 12, SOFT))
    return svg(W, ly + len(notes) * 18 + 10, b, f"Aim points ({name})")


# ---------------------------------------------------------------------------------------------- 4. shot scatter
def scatter():
    """Genesis doshot: exact within 200 with (ShA + 1) / (ShA + 16); otherwise s = ((pp >> 4) - ShA / 2 + 16) x d / 64,
    halved at 250 or less, capped at 136; X += random +/-s (a typical wrist / slapshot: pp >> 4 = 1)."""
    W, H = 820, 470
    L, R, T, B = 80, 560, 80, 380
    dmax, smax = 400, 140
    X = lambda d: L + (R - L) * d / dmax
    Y = lambda v: B - (B - T) * min(v, smax) / smax
    b = []
    b.append(text(W / 2, 28, "Shot scatter (Genesis): how far off target a shot can go", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Most the shot can miss its aim point to either side, by distance from the aim point and working Shot Accuracy.",
                  12, SOFT, "middle"))
    for d in range(0, dmax + 1, 50):
        b.append(line(X(d), T, X(d), B, GRID, 1))
        b.append(text(X(d), B + 18, f"{d}", 11, SOFT, "middle"))
        b.append(text(X(d), B + 32, f"{d // 3} ft", 10, SOFT, "middle"))
    for v in range(0, smax + 1, 20):
        b.append(line(L, Y(v), R, Y(v), GRID, 1))
        b.append(text(L - 8, Y(v) + 4, f"{v}", 11, SOFT, "end"))
    b.append(text((L + R) / 2, B + 52, "distance from the aim point (units; the aim point is at the goal line, 264)", 12, INK, "middle"))
    b.append(f"<text x='24' y='{(T + B) / 2}' font-size='12' fill='{INK}' text-anchor='middle' transform='rotate(-90 24 {(T + B) / 2})'>most it can miss by, each side (units)</text>")
    # exact-shot zone and the halving line
    b.append(f"<rect x='{X(0)}' y='{T}' width='{X(200) - X(0)}' height='{B - T}' fill='{GREEN}' fill-opacity='0.07'/>")
    b.append(line(X(200), T, X(200), B, GREEN, 1.5, "5 4"))
    b.append(text(X(200) - 4, T + 14, "can be exact", 11, GREEN, "end"))
    b.append(text(X(200) + 4, T + 14, "never exact", 11, RED))
    b.append(line(X(250), T + 20, X(250), B, SOFT, 1, "2 3"))
    b.append(text(X(250) + 4, T + 34, "halved up to 250", 10, SOFT))
    # half the goal mouth (posts at 20)
    b.append(line(L, Y(20), R, Y(20), RED, 1.5, "6 4"))
    b.append(text(R - 4, Y(20) - 6, "post: 20 from the middle", 11, RED, "end"))
    cols = [RED, ORANGE, BLUE, GREEN]
    for (sha, rating), col in zip(((0, 0), (10, 2), (20, 4), (30, 6)), cols):
        pts = []
        for d in range(0, dmax + 1, 2):
            s = (1 - (sha >> 1) + 16) * d >> 6
            s = min(s >> 1 if d <= 250 else s, 136)
            pts.append(f"{X(d):.1f},{Y(s):.1f}")
        b.append(f"<polyline points='{' '.join(pts)}' fill='none' stroke='{col}' stroke-width='2.5'/>")
    # legend with the exact chance
    lx, ly = R + 30, T + 10
    b.append(text(lx, ly, "Shot Accuracy", 13, INK, weight="bold"))
    b.append(text(lx, ly + 18, "rating: working", 11, SOFT))
    b.append(text(lx + 190, ly + 18, "exact within 200", 11, SOFT, "end"))
    for i, ((sha, rating), col) in enumerate(zip(((0, 0), (10, 2), (20, 4), (30, 6)), cols)):
        y = ly + 40 + i * 24
        b.append(line(lx, y - 4, lx + 28, y - 4, col, 3))
        b.append(text(lx + 36, y, f"{rating}: {sha}", 13))
        b.append(text(lx + 190, y, f"{round(100 * (sha + 1) / (sha + 16))}%", 13, INK, "end"))
    tips = ["Working value = 5 x rating + hot / cold.",
            "A shot that isn't exact misses its aim",
            "by a random amount up to the line,",
            "left or right; along the net by less;",
            "and upward only, by up to half of it.",
            "",
            "Beyond 200 (about 67 ft) no shot is",
            "exact, and beyond 250 the error",
            "doubles (to at most 136): from the blue",
            "line even good shooters spray it."]
    for i, s in enumerate(tips):
        b.append(text(lx, ly + 150 + i * 16, s, 12, SOFT))
    return svg(W, H, b, "Shot scatter")


# ---------------------------------------------------------------------------------------------- 5. faceoff timing
def faceoffs():
    """Genesis faceoffs: each new B press swings once: 2 frames wind-up (0), 10 middle (8), 6 sweep (16); back to the
    stance (0) until the next press. Home wins when a 0-32 roll reaches 16 - home + away: (17 + yours - theirs) / 33."""
    W = 820
    L, F = 200, 7          # timeline start x, pixels per frame
    frames = 66
    b = [ARROW]
    b.append(text(W / 2, 28, "Faceoffs (Genesis): it's where your swing is at the drop", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Each new B press swings the stick once (18 frames, 0.3 s). Holding B does nothing. Ratings play no part.",
                  12, SOFT, "middle"))
    colours = {0: "#e4e7eb", 8: "#9cc3e6", 16: GREEN}
    for f in range(0, frames + 1, 6):
        b.append(text(L + f * F, 76, f"{f}", 10, SOFT, "middle"))
    b.append(text(L - 10, 76, "frames:", 10, SOFT, "end"))
    rows = [("Mashing flat out", 0), ("4 frames between swings", 4), ("12 frames between swings", 12)]
    for r, (label, gap) in enumerate(rows):
        y = 92 + r * 46
        b.append(text(L - 10, y + 20, label, 13, INK, "end"))
        f = 0
        while f < frames:
            for state, n in ((0, 2), (8, 10), (16, 6), (0, gap)):
                n = min(n, frames - f)
                if n > 0:
                    b.append(f"<rect x='{L + f * F}' y='{y}' width='{n * F}' height='28' fill='{colours[state]}' stroke='#ffffff' stroke-width='0.5'/>")
                f += n
                if f >= frames:
                    break
        avg = 176 / (18 + gap)
        b.append(text(L + frames * F + 12, y + 14, f"average {avg:.1f}", 12, INK))
        b.append(text(L + frames * F + 12, y + 28, f"home wins {round(100 * (17 + avg - 8) / 33)}% vs 8", 11, SOFT))
    ly = 92 + 3 * 46 + 10
    for i, (state, label) in enumerate(((0, "wind-up or stance: worth 0"), (8, "middle of the swing: worth 8"), (16, "the sweep: worth 16"))):
        x = L + i * 190
        b.append(f"<rect x='{x}' y='{ly}' width='22' height='14' fill='{colours[state]}'/>")
        b.append(text(x + 28, ly + 12, label, 12))
    ty = ly + 44
    b.append(text(60, ty, "At the drop (3-5 s after the box appears, at random), the game compares the two centres' values:", 13, INK, weight="bold"))
    b.append(text(60, ty + 20, "Home wins with chance (17 + home - away) / 33, so the home team has a 17-in-33 edge at equal timing.", 13, INK))
    tab = [("home \\ away", "0", "8", "16")] + [(str(a),) + tuple(f"{round(100 * (17 + a - o) / 33)}%" for o in (0, 8, 16)) for a in (0, 8, 16)]
    for i, row in enumerate(tab):
        for j, cell in enumerate(row):
            b.append(text(140 + j * 90, ty + 50 + i * 20, cell, 13, INK if i and j else SOFT, "middle", "bold" if i and j and row[0] == "16" else "normal"))
    notes = ["The drop picture changes only 9-17 frames before the drop: too late to time one swing.",
             "So mash: the faster the presses come, the more time you spend in the middle and the sweep.",
             "Hold the d-pad toward a teammate: a win sends the puck that way 3 times in 4."]
    for i, n in enumerate(notes):
        b.append(text(60, ty + 140 + i * 18, n, 12, SOFT))
    return svg(W, ty + 200, b, "Faceoff timing")


def chart_frame(b, L, R, T, B, xs, ys, X, Y, xlabel, ylabel, xfmt=str, yfmt=str):
    for v in xs:
        b.append(line(X(v), T, X(v), B, GRID, 1))
        b.append(text(X(v), B + 18, xfmt(v), 11, SOFT, "middle"))
    for v in ys:
        b.append(line(L, Y(v), R, Y(v), GRID, 1))
        b.append(text(L - 8, Y(v) + 4, yfmt(v), 11, SOFT, "end"))
    b.append(text((L + R) / 2, B + 40, xlabel, 12, INK, "middle"))
    b.append(f"<text x='{L - 52}' y='{(T + B) / 2}' font-size='12' fill='{INK}' text-anchor='middle' "
             f"transform='rotate(-90 {L - 52} {(T + B) / 2})'>{ylabel}</text>")


# ---------------------------------------------------------------------------------------------- 6. the weight bug
def weight_bug():
    """CCStart: knockdown automatic when (base - checker weight + target weight) / 2 - impact <= 0, else a roll against
    that number; base 240 for a checker a person controls (summed in ONE byte: wraps past 255), 120 for the computer.
    Weight = 8 per rating step (8 lb)."""
    W, H = 820, 470
    L, R, T, B = 110, 560, 80, 360
    X = lambda d: L + (R - L) * (d + 8) / 16
    Y = lambda v: B - (B - T) * v / 130
    b = []
    b.append(text(W / 2, 28, "The weight bug (Genesis): how hard it is to knock a man down", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The game's knockdown number: lower is easier (at or below the hit's impact, he goes down for sure; above it, a roll).",
                  12, SOFT, "middle"))
    chart_frame(b, L, R, T, B, range(-8, 9, 2), range(0, 131, 20), X, Y,
                "target's weight minus the checker's (lb; one rating step = 8 lb)", "knockdown number (lower = easier)",
                lambda d: f"{d * 8:+d}" if d else "0")
    b.append(line(X(0), T, X(0), B, SOFT, 1, "3 3"))
    person = [(d, ((240 + 8 * d) & 0xFF) // 2) for d in range(-8, 9)]
    cpu = [(d, max(0, 120 + 8 * d) // 2) for d in range(-8, 9)]
    for pts, col in ((cpu, BLUE), (person[:10], RED), (person[10:], RED)):
        b.append("<polyline points='" + " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in pts) +
                 f"' fill='none' stroke='{col}' stroke-width='2.5'/>")
        for d, v in pts:
            b.append(circle(X(d), Y(v), 3.5, col, col, 1))
    b.append(text(X(2.6), Y(38), "16+ lb heavier: near 0", 11, RED))
    b.append(text(X(-7.8), Y(person[0][1]) + 22, "a person's checker", 12, RED, weight="bold"))
    b.append(text(X(-7.6), Y(cpu[0][1]) + 22, "computer checker (and the CB check)", 12, BLUE, weight="bold"))
    b.append(text(X(2) + 6, Y(person[9][1]) + 4, "wraps past 255", 11, RED))
    lx = R + 30
    notes = [("Why:", INK), ("the sum (240 - checker + target)", SOFT), ("is done in one byte, so for a", SOFT),
             ("person's checker it wraps round", SOFT), ("past 255 once the target is 2+", SOFT), ("steps (16+ lb) heavier.", SOFT),
             ("", SOFT), ("Recorded knockdown rates", INK), ("(target heavier / same / lighter):", SOFT),
             ("person 48% / 15% / 7%", RED), ("computer 15% / 27% / 34%", BLUE), ("", SOFT),
             ("CB check: C to burst, then B to", SOFT), ("switch away before contact: the", SOFT),
             ("computer's line, but double the", SOFT), ("charging / roughing risk.", SOFT)]
    for i, (s, c) in enumerate(notes):
        b.append(text(lx, T + 4 + i * 17, s, 12, c, weight="bold" if c == INK else "normal"))
    b.append(text(L, B + 64, "Light checkers on heavy carriers is the person's best check; a heavy person-controlled checker on a light man almost never works.",
                  12, SOFT))
    return svg(W, H, b, "The weight bug")


# ---------------------------------------------------------------------------------------------- 7. shoulder-save bobble
def shoulder_bobble():
    """ghighr / ghighl hold points: facing down (top goalie) (-10, +15) / (+10, +14), i.e. behind him; facing up
    (+9, -14) / (-9, -14) in front. The held puck is pulled toward it; the net's front strips a carried puck."""
    W, S = 820, 4.2
    b = [ARROW]
    b.append(text(W / 2, 28, "The shoulder-save bobble (Genesis): why only the top net", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Seen from above, to scale. In a shoulder save the game holds the puck at a point 14-15 up the screen from the goalie.",
                  12, SOFT, "middle"))
    for panel, (ox, top) in enumerate(((210, True), (610, False))):
        oy = 250
        gy_game = 246 if top else -246
        Pp = lambda x, y: (ox + x * S, oy - (y - (258 if top else -258)) * S)
        goal = 268 if top else -268
        # net and goal line
        ny = Pp(0, goal)[1]
        depth = -15 * S if top else 15 * S
        b.append(f"<rect x='{ox - 20 * S}' y='{min(ny, ny + depth):.1f}' width='{40 * S}' height='{abs(depth):.1f}' fill='#f3f5f7' stroke='{SOFT}'/>")
        b.append(line(ox - 40 * S, ny, ox + 40 * S, ny, RED, 3))
        for px in (-20, 20):
            b.append(circle(ox + px * S, ny, 4, INK, INK))
        fy = Pp(0, 261 if top else -261)[1]
        b.append(line(ox - 20 * S, fy, ox + 20 * S, fy, ORANGE, 2, "5 3"))
        b.append(text(ox + 21 * S, fy + 4, "net front", 11, ORANGE))
        gx, gyy = Pp(0, gy_game)
        b.append(circle(gx, gyy, 13 * S, "#cfe3f5", BLUE, 2, None, 0.8))
        b.append(text(gx, gyy + 4, "G", 14, INK, "middle", "bold"))
        hx, hy = (-10, gy_game + 15) if top else (9, gy_game + 14)
        HX, HY = Pp(hx, hy)
        b.append(line(gx, gyy, HX, HY, INK, 1.5, "3 3", "marker-end='url(#arr)'"))
        b.append(circle(HX, HY, 7, RED if top else GREEN, INK, 1.5))
        title = "Top net: goalie faces down" if top else "Bottom net: goalie faces up"
        b.append(text(ox, 90, title, 15, INK, "middle", "bold"))
        if top:
            ls = ["The hold point is BEHIND him, past the net's", "front. The puck is pulled there, the net",
                  "strips it off his stick, and it slides in", "(the net never bounces a puck moving into it)."]
        else:
            ls = ["The hold point is in FRONT of him, out in", "the ice. The puck stays on his stick, well", "away from the net: nothing can happen."]
        for i, s in enumerate(ls):
            b.append(text(ox, 400 + i * 17, s, 12, RED if top and i == 0 else SOFT, "middle"))
    b.append(text(60, 490, "It also needs him standing near his goal line and roughly centred when he catches it, which is why it's rare.", 12, SOFT))
    b.append(text(60, 507, "Recorded: one goal (ANA-ATL P3 4:00, a pass shot his stick popped up). Shoot high at the top net and follow it in.", 12, SOFT))
    return svg(W, 525, b, "Shoulder-save bobble")


# ---------------------------------------------------------------------------------------------- 8. the rocket pass
def rocket_pass():
    """passtoa0: the meeting time in whole eighths of a second, rounded down (at least 1), and the speed that covers the
    distance in that time; a pass whose ideal speed is 15,000 (a mid Passing rating) travels 27.5 units an eighth."""
    W, H = 820, 470
    L, R, T, B = 110, 600, 80, 360
    X = lambda d: L + (R - L) * d / 200
    Y = lambda v: B - (B - T) * v / 34000
    b = []
    b.append(text(W / 2, 28, "The rocket pass (Genesis): the travel time is rounded down", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The game times a pass to meet the receiver in whole eighths of a second, rounded down, then sends it fast enough to get there.",
                  12, SOFT, "middle"))
    chart_frame(b, L, R, T, B, range(0, 201, 25), range(0, 34001, 5000), X, Y,
                "distance from the passer to where the receiver catches it (units; 3 to a foot)", "pass speed",
                str, lambda v: f"{v:,}")
    b.append(f"<rect x='{L}' y='{Y(34000)}' width='{R - L}' height='{Y(25000) - Y(34000)}' fill='{RED}' fill-opacity='0.07'/>")
    b.append(text(R - 6, Y(25000) - 6, "rocket: over 25,000", 11, RED, "end"))
    b.append(line(L, Y(15000), R, Y(15000), SOFT, 1.5, "6 4"))
    b.append(text(R - 6, Y(15000) + 16, "the speed it should be: 15,000", 11, SOFT, "end"))
    per = 15000 / 4096 * 7.5
    pts = []
    for i in range(2, 401):
        d = i / 2
        t = max(1, int(d / per))
        pts.append(f"{X(d):.1f},{Y(min(33800, 15000 * (d / per) / t)):.1f}")
    b.append(f"<polyline points='{' '.join(pts)}' fill='none' stroke='{RED}' stroke-width='2.5'/>")
    for k in range(1, 8):
        b.append(text(X(k * per), B - 6, f"{k}/8 s", 10, SOFT, "middle"))
    lx = R + 25
    notes = [("Where it bites:", INK), ("a meeting just over an eighth", SOFT), ("of a second away (28-55 units)", SOFT),
             ("is timed as one eighth, so the", SOFT), ("pass goes up to twice as fast.", SOFT), ("", SOFT),
             ("That's a receiver skating", SOFT), ("toward you from about 50-70", SOFT), ("units (17-23 ft) away.", SOFT), ("", SOFT),
             ("Longer passes are off by less", SOFT), ("(at most 1/8 s of 2, 3, 4 ...).", SOFT), ("", SOFT),
             ("Recorded: 24 of 718 person", SOFT), ("passes over 25,000.", SOFT)]
    for i, (s, c) in enumerate(notes):
        b.append(text(lx, T + 4 + i * 17, s, 12, c, weight="bold" if c == INK else "normal"))
    b.append(text(L, B + 64, "The SNES sets a pass's speed from the distance instead, so it has no rocket pass.", 12, SOFT))
    return svg(W, H, b, "Rocket pass")


# ---------------------------------------------------------------------------------------------- 9. computer positioning
def positioning():
    """Genesis asswingo / asscentero / assdefo boxes by the puck's zone (y toward the goal the team attacks)."""
    W, S = 860, 0.5
    b = []
    b.append(text(W / 2, 28, "Where computer skaters go on offence (Genesis), by where the puck is", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The team attacks UP. Each skater picks a random spot in his box and keeps it until the puck changes zone.",
                  12, SOFT, "middle"))
    panels = [("Puck in own zone", -180,
               {"W": [(80, -70, 20, 10)], "C": [(0, -70, 60, 10)]}, None),
              ("Puck in the neutral zone", 0,
               {"W": [(100, 58, 20, 5)], "C": [(0, 60, 60, 10)]}, None),
              ("Puck in the attacking zone", 180,
               {"W": [(60, 230, 50, 20)], "C": [(0, 170, 40, 30)], "D": [(80, 98, 6, 4)]}, None),
              ("Puck behind the goal line", 285,
               {"W": [(80, 250, 30, 20)], "C": [(0, 170, 80, 20)], "D": [(80, 98, 6, 4)]}, None)]
    cols = {"W": GREEN, "C": ORANGE, "D": BLUE}
    for i, (title, puck_y, boxes, _) in enumerate(panels):
        ox, oy = 110 + i * 210, 260
        P = lambda x, y: (ox + x * S, oy - y * S)
        x0, y0 = P(-130, 300)
        b.append(f"<rect x='{x0}' y='{y0}' width='{260 * S}' height='{600 * S}' rx='{46 * S}' fill='#f7fbff' stroke='{SOFT}' stroke-width='1.5'/>")
        for yy, col, w in ((88, BLUE, 3), (-88, BLUE, 3), (0, RED, 2), (268, RED, 1.5), (-268, RED, 1.5)):
            a, c = P(-130, yy), P(130, yy)
            b.append(line(a[0], a[1], c[0], c[1], col, w))
        for yy in (268, -268):
            a = P(-20, yy)
            b.append(f"<rect x='{a[0]}' y='{a[1] - (8 if yy > 0 else 0)}' width='{40 * S}' height='8' fill='#ffffff' stroke='{INK}'/>")
        for who, bl in boxes.items():
            for (bx, by, hx, hy) in bl:
                for sg in ((-1, 1) if bx else (1,)):
                    a = P(sg * bx - hx, by + hy)
                    b.append(f"<rect x='{a[0]:.1f}' y='{a[1]:.1f}' width='{2 * hx * S:.1f}' height='{2 * hy * S:.1f}' fill='{cols[who]}' "
                             f"fill-opacity='0.35' stroke='{cols[who]}' stroke-width='1.5'/>")
                    c = P(sg * bx, by)
                    b.append(text(c[0], c[1] + 4, who, 11, INK, "middle", "bold"))
        pp = P(-30 if puck_y < 285 else 40, puck_y)
        b.append(circle(pp[0], pp[1], 6, INK, "#ffffff", 2))
        b.append(text(ox, oy - 300 * S - 14, title, 13, INK, "middle", "bold"))
        if "D" not in boxes:
            b.append(text(ox, oy + 300 * S + 18, "D: hang back (defensive spots)", 11, SOFT, "middle"))
        else:
            b.append(text(ox, oy + 300 * S + 18, "D: just inside the blue line", 11, SOFT, "middle"))
    ly = 260 + 300 * S + 50
    for j, (who, label) in enumerate((("W", "wingers (left box: left wing)"), ("C", "centre"), ("D", "defencemen"))):
        x = 110 + j * 230
        b.append(f"<rect x='{x}' y='{ly - 11}' width='22' height='13' fill='{cols[who]}' fill-opacity='0.35' stroke='{cols[who]}'/>")
        b.append(text(x + 30, ly, label, 12))
    b.append(circle(110 + 3 * 230 - 30, ly - 5, 6, INK, "#ffffff", 2))
    b.append(text(110 + 3 * 230 - 18, ly, "the puck", 12))
    notes = ["A skater switches to his defensive job when the other team gets the puck, at his next awareness tick (7-15 frames).",
             "The box is re-picked when the puck changes zone (or 1 tick in 128), so forwards drift to new spots as play moves."]
    for k, s in enumerate(notes):
        b.append(text(60, ly + 26 + k * 17, s, 12, SOFT))
    return svg(W, ly + 70, b, "Computer positioning")


# ---------------------------------------------------------------------------------------------- 10. the rink in feet
def rink():
    """The rink lying on its side: game units and feet (3 units to a foot)."""
    W, S = 860, 1.2
    ox, oy = 430, 250
    P = lambda x, y: (ox + y * S, oy - x * S)      # game y runs left-right here, game x up-down
    b = [ARROW]
    b.append(text(W / 2, 28, "The rink in game units and feet (both systems; about 3 units to a foot)", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Lying on its side: the screen's up is to the right here. The top net is on the right.", 12, SOFT, "middle"))
    a = P(130, -300)
    b.append(f"<rect x='{a[0]}' y='{a[1]}' width='{600 * S}' height='{260 * S}' rx='{46 * S}' fill='#f7fbff' stroke='{INK}' stroke-width='2'/>")
    for yy, col, w in ((88, BLUE, 4), (-88, BLUE, 4), (0, RED, 3), (268, RED, 2), (-268, RED, 2)):
        p, q = P(-130, yy), P(130, yy)
        b.append(line(p[0], p[1], q[0], q[1], col, w))
    for yy in (268, -268):
        p = P(20, yy)
        d = 15 * S if yy > 0 else -15 * S
        b.append(f"<rect x='{min(p[0], p[0] + d)}' y='{p[1]}' width='{abs(d)}' height='{40 * S}' fill='#ffffff' stroke='{INK}'/>")
        g = P(0, yy - 22 if yy > 0 else yy + 22)
        b.append(circle(g[0], g[1], 4, BLUE, BLUE))
    for (x, y) in [(sx * 70, sy * 206) for sx in (-1, 1) for sy in (-1, 1)] + [(sx * 70, sy * 65) for sx in (-1, 1) for sy in (-1, 1)] + [(0, 0)]:
        p = P(x, y)
        b.append(circle(p[0], p[1], 3.5, RED, RED))
        if abs(y) == 206:
            b.append(circle(p[0], p[1], 30 * S, "none", RED, 1))
    c = P(0, 0)
    b.append(circle(c[0], c[1], 30 * S, "none", BLUE, 1))
    # the slot: within 60 of the net, 50 wide
    p = P(50, 268 - 60)
    b.append(f"<rect x='{p[0]}' y='{p[1]}' width='{60 * S}' height='{100 * S}' fill='{GOLD}' fill-opacity='0.18' stroke='{GOLD}' stroke-dasharray='4 3'/>")
    s1 = P(-55, 268 - 30)
    b.append(text(s1[0], s1[1], "high danger", 10, "#8a6d00", "middle"))

    def dim(y1, y2, x, label, below=False):
        p, q = P(x, y1), P(x, y2)
        b.append(line(p[0], p[1], q[0], q[1], INK, 1.2, None, "marker-start='url(#arr)' marker-end='url(#arr)'"))
        b.append(text((p[0] + q[0]) / 2, p[1] + (16 if below else -6), label, 11, INK, "middle"))

    dim(-300, 300, 150, "600 units = 200 ft")
    dim(0, 88, -150, "88 = 29 ft", True)
    dim(88, 268, -150, "180 = 60 ft (the attacking zone)", True)
    dim(268, 300, -150, "32 = 11 ft", True)
    p, q = P(130, -330), P(-130, -330)
    b.append(line(p[0], p[1], q[0], q[1], INK, 1.2, None, "marker-start='url(#arr)' marker-end='url(#arr)'"))
    b.append(f"<text x='{p[0] - 8}' y='{(p[1] + q[1]) / 2}' font-size='11' fill='{INK}' text-anchor='middle' "
             f"transform='rotate(-90 {p[0] - 8} {(p[1] + q[1]) / 2})'>260 units = 87 ft</text>")
    ly = oy + 130 * S + 70
    notes = ["Goal lines at 268 from centre; blue lines at 88; end-zone dots 70 across, 62 out from the goal line (21 ft); goalies stand",
             "about 20-25 out (7-8 ft, blue dots). Goal mouth 40 units wide (13 ft) on the Genesis; the SNES scores 34 wide, posts to 44.",
             "High danger (shot maps): within 60 of the net and 50 to either side. Shots can be exact within 200 of the aim point (67 ft)."]
    for i, s in enumerate(notes):
        b.append(text(40, ly + i * 17, s, 12, SOFT))
    return svg(W, ly + 60, b, "The rink in feet")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"saves_reach.svg": saves(), "through_the_legs.svg": through_legs(), "aim_points_genesis.svg": aim_points("genesis"),
             "aim_points_snes.svg": aim_points("snes"), "shot_scatter.svg": scatter(), "faceoff_timing.svg": faceoffs(),
             "weight_bug.svg": weight_bug(), "shoulder_bobble.svg": shoulder_bobble(), "rocket_pass.svg": rocket_pass(),
             "computer_positions.svg": positioning(), "rink_feet.svg": rink()}
    for name, body in files.items():
        (OUT / name).write_text(body, encoding="utf-8")
        print(OUT / name)


if __name__ == "__main__":
    main()
