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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"saves_reach.svg": saves(), "through_the_legs.svg": through_legs(), "aim_points_genesis.svg": aim_points("genesis"),
             "aim_points_snes.svg": aim_points("snes"), "shot_scatter.svg": scatter(), "faceoff_timing.svg": faceoffs()}
    for name, body in files.items():
        (OUT / name).write_text(body, encoding="utf-8")
        print(OUT / name)


if __name__ == "__main__":
    main()
