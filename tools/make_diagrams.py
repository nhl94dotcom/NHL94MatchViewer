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
    b.extend(sprite(419, cx, gy, S, opacity=0.55))
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


# Atlanta's away colours in the 2-on-2 ROM of the recorded through-the-legs goals (2026-10-19_0818_ANA-ATL).
GOALIE_PALETTE = ['#b6ffff', '#dadada', '#000000', '#000024', '#000048', '#00006d', '#da9191', '#b66d6d', '#ff9100',
                  '#b60000', '#000091', '#486dda', '#6d91ff', '#2448b6', '#da9148', '#6db6b6']


def sprite(frame, ox, oy, S, mirrored=False, opacity=0.8, libraries=("592e11a8", "9438f5dd")):
    """One of the game's sprite frames as SVG squares (one per pixel, S across), its anchor (the player's position) at
    (ox, oy), from the sprite library the converter builds (sprites/<rom>.js here or in Documents/NHL94 Viewer).
    Empty when no library is found, so the diagram still draws without it."""
    import json
    for crc in libraries:
        for folder in (OUT.parent.parent / "sprites", Path.home() / "Documents" / "NHL94 Viewer" / "sprites"):
            f = folder / f"{crc}.js"
            if f.exists():
                t = f.read_text(encoding="utf-8")
                lib = json.loads(t[t.index("{"):t.rindex("}") + 1])
                fr = lib["frames"][f"{frame:03x}"]
                out = [f"<g opacity='{opacity}' shape-rendering='crispEdges'>"]
                for i, ch in enumerate(fr["p"]):
                    v = ord(ch) - 48
                    slot, c = v // 16, v % 16
                    if c == 0:
                        continue
                    colour = GOALIE_PALETTE[c] if slot == 0 else lib["fixed"][slot - 1][c]
                    px, py = fr["x"] + i % fr["w"], fr["y"] + i // fr["w"]
                    if mirrored:
                        px = -px - 1
                    out.append(f"<rect x='{ox + px * S:.1f}' y='{oy + py * S:.1f}' width='{S + 0.4:.1f}' height='{S + 0.4:.1f}' fill='{colour}'/>")
                out.append("</g>")
                return out
    return []


# ---------------------------------------------------------------------------------------------- 2. through the legs
def through_legs():
    """The butterfly's blind ring (Genesis): body circle 13, the stick's 8-14 ring around the blade of frame 480 (the
    butterfly, $021E, facing down, not mirrored: the hot point 9 to his right, 2 in front, as in the recorded goals),
    with the game's own picture of that frame under it."""
    S, cx, cy = 11, 330, 300          # goalie's centre on screen; game +y (toward his net) is screen up
    reach, bx, by = 13, 9, -2         # a typical computer goalie; the blade of frame 480 (HotList)
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
    b.extend(sprite(480, cx, cy, S, opacity=0.6))
    b.append(circle(cx, cy, reach * S, "none", BLUE, 2))
    b.append(circle(X, Y, 14 * S, "none", ORANGE, 2))
    b.append(circle(X, Y, 8 * S, "none", GREEN, 2))
    b.append(circle(X, Y, 6, INK, "#ffffff", 2))
    b.append(line(X + 6, Y + 6, X + 3 * S, Y + 4 * S, INK, 1))
    b.append(text(X + 3 * S + 4, Y + 4 * S + 12, "blade (the stick's hot point)", 12, INK, weight="bold"))
    b.append(line(cx - 7, cy - 7, cx + 7, cy + 7, INK, 2.5))
    b.append(line(cx - 7, cy + 7, cx + 7, cy - 7, INK, 2.5))
    b.append(line(cx - 8, cy + 4, cx - 15 * S, cy + 3 * S, INK, 1))
    b.append(text(cx - 15 * S - 4, cy + 3 * S + 4, "his centre (position)", 12, INK, "end", "bold"))
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
    notes = [(P(0, -12)[1], "1. Front edge: only a sliver of his body", "is tested before the ring begins; the", "puck steps straight over it."),
             (P(0, -2)[1], "2. Blind ring (8-14 from the blade):", "the stick doesn't play the puck, and the", "body test is skipped. It slides through."),
             (P(0, 10)[1], "3. Out of the ring behind his centre:", "the body test hits, and the bounce goes", "out from his centre: back, into the net.")]
    for yy, *ls in notes:
        b.append(line(cx + 2 * S, yy, nx - 8, yy, SOFT, 1, "2 3"))
        for i, s in enumerate(ls):
            b.append(text(nx, yy + 4 + i * 15, s, 12, INK if i == 0 else SOFT, weight="bold" if i == 0 else "normal"))
    ly = int(P(0, -40)[1])
    b.append(text(70, ly - 18, "Under the rings: the game's own picture of the goalie in that butterfly (frame 480), drawn as on screen, his body rising up the page from his position.", 12, INK))
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
    """ghighr / ghighl hold points (HotList, in game units, +y up the screen): facing down (top goalie) (-10, +15) /
    (+10, +14), i.e. behind him; facing up (+9, +14) / (-9, +14), in front. Drawn: ghighl, frames 667 / 659. The held
    puck is pulled toward it; the net's front strips a carried puck."""
    W, S = 820, 4.2
    b = [ARROW]
    b.append(text(W / 2, 28, "The shoulder-save bobble (Genesis): why only the top net", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "To scale, with the game's own pictures (ghighl, frames 667 and 659). In a shoulder save the puck is held 14 up the screen from him.",
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
        b.append(circle(gx, gyy, 13 * S, "#cfe3f5", BLUE, 2, None, 0.5))
        b.extend(sprite(667 if top else 659, gx, gyy, S, opacity=0.7))
        b.append(circle(gx, gyy, 4, INK, INK))
        hx, hy = (10, gy_game + 14) if top else (-9, gy_game + 14)
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


# ---------------------------------------------------------------------------------------------- 11. one-timers
def one_timers():
    """Timing from the recordings (C / SNES A press to the strike, or to the end of a failed swing) and what made Genesis
    one-timers score (SHOOTING_STUDY part 3, 91 one-timers)."""
    W = 860
    b = []
    b.append(text(W / 2, 28, "One-timers: when to press, and what makes them go in", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Press shoot while the pass is on its way; the game times the downswing itself and waits up to 0.8 s at full wind-up.",
                  12, SOFT, "middle"))
    L, R = 170, 800
    X = lambda ms: L + (R - L) * ms / 1000
    T = 90
    b.append(text(60, T - 8, "Time from the press (recorded)", 13, INK, weight="bold"))
    for ms in range(0, 1001, 100):
        b.append(line(X(ms), T, X(ms), T + 150, GRID, 1))
        b.append(text(X(ms), T + 166, f"{ms / 1000:.1f} s", 10, SOFT, "middle"))
    rows = [("Genesis: struck", 0, 870, 210, GREEN), ("Genesis: failed swing over", 300, 960, 585, RED),
            ("SNES: struck", 0, 590, 199, GREEN), ("SNES: failed swing over", None, None, 465, RED)]
    for i, (label, a, z, med, col) in enumerate(rows):
        y = T + 12 + i * 34
        b.append(text(L - 10, y + 14, label, 12, INK, "end"))
        if a is not None:
            b.append(f"<rect x='{X(a)}' y='{y}' width='{X(z) - X(a)}' height='20' rx='4' fill='{col}' fill-opacity='0.3' stroke='{col}'/>")
        b.append(line(X(med), y - 3, X(med), y + 23, col, 3))
        b.append(text(X(med) + 5, y + 14, f"median {med} ms" if a is not None else f"median {med} ms (range not kept)", 11, INK))
    b.append(text(60, T + 190, "So: press no more than about 0.9 s (Genesis) or 0.6 s (SNES) before the puck reaches him; pressing as it arrives strikes at once.",
                  12, SOFT))
    # what makes them score
    T2 = T + 230
    b.append(text(60, T2, "What made Genesis one-timers score (91 recorded)", 13, INK, weight="bold"))
    groups = [("Goalie off the puck's line at the strike", [("0-4 units", 11, 28), ("4-10", 18, 38), ("10+", 68, 25)]),
              ("How far the pass moved the puck across", [("0-40", 19, 32), ("40-90", 47, 34), ("90+", 20, 25)]),
              ("Distance from the net at the strike", [("under 60", 44, 18), ("60-100", 44, 34), ("100+", 10, 39)])]
    gw = 260
    for g, (title, bars) in enumerate(groups):
        gx = 60 + g * gw
        b.append(text(gx, T2 + 26, title, 12, INK))
        base = T2 + 190
        for k, (lab, pct, n) in enumerate(bars):
            x = gx + 10 + k * 70
            h = pct * 1.8
            b.append(f"<rect x='{x}' y='{base - h}' width='46' height='{h}' fill='{BLUE if pct < 40 else GREEN}' fill-opacity='0.8'/>")
            b.append(text(x + 23, base - h - 6, f"{pct}%", 12, INK, "middle", "bold"))
            b.append(text(x + 23, base + 15, lab, 11, SOFT, "middle"))
            b.append(text(x + 23, base + 29, f"{n} shots", 10, SOFT, "middle"))
        b.append(line(gx, base, gx + 220, base, SOFT, 1))
    b.append(text(60, T2 + 248, "Quick passes (under 0.5 s in the air) that move the puck 40-90 across catch the computer goalie off his line; long cross-ice",
                  12, SOFT))
    b.append(text(60, T2 + 264, "passes give him time to slide over. On the SNES (55 recorded) only distance showed: 8 of 25 from 60-100 units, none from elsewhere.",
                  12, SOFT))
    return svg(W, T2 + 284, b, "One-timers")


# ---------------------------------------------------------------------------------------------- 12. faceoff directions
def faceoff_directions():
    """Endfaceoff: the puck leaves at dirtab x 32 (6400 straight, 4512 per axis diagonally) plus 2048 toward the
    winner's own end. Drawn for a winner attacking UP the page."""
    W, S = 860, 0.022
    ox, oy = 300, 270
    b = [ARROW]
    b.append(text(W / 2, 28, "Which way a won faceoff sends the puck (Genesis)", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The winner attacks UP the page. Each arrow is the puck's speed and direction for the d-pad direction held, to scale.",
                  12, SOFT, "middle"))
    d = 4512
    dirs = [("Up", 0, 6400), ("Up-right", d, d), ("Right", 6400, 0), ("Down-right", d, -d), ("Down", 0, -6400),
            ("Down-left", -d, -d), ("Left", -6400, 0), ("Up-left", -d, d)]
    random_set = {"Up", "Up-right", "Right", "Left", "Up-left"}
    b.append(circle(ox, oy, 6, RED, RED))
    b.append(circle(ox, oy, 6400 * S, "none", GRID, 1, "3 3"))
    for name, vx, vy in dirs:
        vy2 = vy - 2048
        ex, ey = ox + vx * S, oy - vy2 * S
        col = BLUE if name in random_set else GREEN
        b.append(line(ox, oy, ex, ey, col, 3, None, "marker-end='url(#arr)'"))
        sp = math.hypot(vx, vy2)
        lx, ly = ox + vx * S * 1.0 + (14 if vx > 0 else -14 if vx < 0 else 0), oy - vy2 * S + (-10 if vy2 > 0 else 18)
        anchor = "start" if vx > 0 else "end" if vx < 0 else "middle"
        b.append(text(lx, ly, f"{name}: {sp:,.0f}", 11, INK, anchor))
    b.append(text(ox, oy + 250, "(the dashed circle: the push without the 2,048 toward the winner's end)", 11, SOFT, "middle"))
    nx = 560
    notes = [("Every draw adds 2,048 toward the", INK), ("winner's own end:", INK),
             ("straight back is the fastest (8,448);", SOFT), ("sideways comes out angled back;", SOFT),
             ("straight forward is slow (4,352).", SOFT), ("", SOFT),
             ("Hold a direction (green or blue):", INK), ("if you win, the puck goes that way", SOFT), ("3 times in 4.", SOFT), ("", SOFT),
             ("Hold nothing (the computer never", INK), ("holds one): a random one of the five", SOFT),
             ("blue directions, from sideways to", SOFT), ("straight at the other team.", SOFT), ("", SOFT),
             ("Best: straight back to your defence.", GREEN)]
    for i, (s, c) in enumerate(notes):
        b.append(text(nx, 100 + i * 17, s, 12, c, weight="bold" if c in (INK, GREEN) else "normal"))
    return svg(W, oy + 280, b, "Faceoff directions")


# ---------------------------------------------------------------------------------------------- 13. penalties by Aggression
def penalty_chances():
    """Genesis checkagr: R = ((40 - Agr) / 2) x 13, x 2 for a person's checker; a check that leaves him up is a penalty
    on randomd0(R) <= 4 (P = 5 / R). SNES: R = (20 - Agr) x 16, the person's doubling done on the low byte (wraps); a
    check is a penalty on 0 (P = 1 / R; R = 0 every time). Away from the puck (near it, R halves)."""
    W = 860
    b = []
    b.append(text(W / 2, 28, "Penalty chance per check, by working Aggression", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "Away from the puck (within 40 of it the chance doubles). Working Aggression is 0-15 on both systems.", 12, SOFT, "middle"))
    snes_person = [384, 352, 320, 288, 256, 224, 192, 160, 128, 96, 64, 32, 0, 224, 192, 160]
    panels = [("Genesis: a check that leaves him standing", lambda a: 5 / (((40 - a) // 2) * 13), lambda a: 5 / (((40 - a) // 2) * 26), 4.0),
              ("SNES: a check", lambda a: 1 / ((20 - a) * 16), lambda a: 1 / snes_person[a] if snes_person[a] else None, 4.0)]
    for p, (title, cpu, person, top) in enumerate(panels):
        L = 90 + p * 400
        R, T, B = L + 320, 100, 330
        X = lambda a: L + (R - L) * (a + 0.5) / 16
        Y = lambda v: B - (B - T) * min(v, top) / top
        b.append(text((L + R) / 2, 84, title, 13, INK, "middle", "bold"))
        for v in (0, 1, 2, 3, 4):
            b.append(line(L, Y(v), R, Y(v), GRID, 1))
            b.append(text(L - 6, Y(v) + 4, f"{v}%", 10, SOFT, "end"))
        for a in range(16):
            for k, (fn, col) in enumerate(((cpu, BLUE), (person, RED))):
                v = fn(a)
                x = X(a) - 7 + k * 7
                if v is None:
                    b.append(f"<rect x='{x}' y='{T}' width='6' height='{B - T}' fill='{RED}'/>")
                    b.append(text(x + 3, T - 4, "every hit", 10, RED, "middle", "bold"))
                else:
                    h = B - Y(100 * v)
                    b.append(f"<rect x='{x}' y='{B - h}' width='6' height='{h}' fill='{col}'/>")
            if a % 3 == 0 or a == 15:
                b.append(text(X(a), B + 15, str(a), 10, SOFT, "middle"))
        b.append(line(L, B, R, B, SOFT, 1))
        b.append(text((L + R) / 2, B + 32, "working Aggression", 11, INK, "middle"))
    ly = 390
    for j, (col, label) in enumerate(((BLUE, "the computer's skater"), (RED, "a person's skater"))):
        b.append(f"<rect x='{90 + j * 220}' y='{ly - 10}' width='14' height='12' fill='{col}'/>")
        b.append(text(110 + j * 220, ly, label, 12))
    notes = ["Genesis: a person's chance is half the computer's (the range is doubled), so the CB check (contact as the computer) doubles it.",
             "Genesis working Aggression wraps at 16: rating 1 plays as 2-7, 2 as 8-12, 3 as 12-15 (or 0), 4 as 1-6: rating 4 plays like rating 1.",
             "SNES: doubling a person's range overflows a byte, so at 12 every check is a penalty and 9-11 are several times the computer's.",
             "SNES: a \"cold\" Aggression maxes at 15 (the hot / cold bug); 11 of the 14 recorded SNES penalties were by players at 15.",
             "Other moves have their own thresholds (Genesis: a knockdown 4 / 5, a hook or hold 7 / 5 of these; SNES: a poke trip 5 times these)."]
    for i, s in enumerate(notes):
        b.append(text(60, ly + 30 + i * 18, s, 12, SOFT))
    return svg(W, ly + 30 + len(notes) * 18 + 10, b, "Penalty chances")


# ---------------------------------------------------------------------------------------------- 14. the flip
def flip_spots():
    """OneTimerTarget (Genesis A with the puck): outside the attacking zone the faceoff circle (+/-116, 194) on the side
    he faces; inside, the high slot (-5, 171), or the goal mouth (y 259) from 138+ deep within 55 of the middle; +0-9 at
    random; moved to 60 sideways from him when closer. Over the glass when that puts it past the boards."""
    W, S = 860, 0.9
    ox, oy = 250, 80 + 300 * 0.9
    P = lambda x, y: (ox + x * S, oy - y * S)
    b = [ARROW]
    b.append(text(W / 2, 28, "Where the flip lands (Genesis: A with the puck)", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The team attacks UP. The d-pad doesn't aim it: the spot comes from where the passer is and which way he faces.",
                  12, SOFT, "middle"))
    a = P(-130, 300)
    b.append(f"<rect x='{a[0]}' y='{a[1]}' width='{260 * S}' height='{360 * S}' fill='#f7fbff' stroke='{INK}' stroke-width='1.5'/>")
    for yy, col, w in ((88, BLUE, 3), (0, RED, 2), (268, RED, 1.5)):
        p, q = P(-130, yy), P(130, yy)
        b.append(line(p[0], p[1], q[0], q[1], col, w))
    p = P(-20, 268)
    b.append(f"<rect x='{p[0]}' y='{p[1] - 13}' width='{40 * S}' height='13' fill='#ffffff' stroke='{INK}'/>")
    # over-the-glass passer strips (outside the attacking zone, 75-125 from the middle, facing the near boards)
    for sg in (-1, 1):
        q = P(75 if sg > 0 else -125, 88)
        b.append(f"<rect x='{q[0]}' y='{q[1]}' width='{50 * S}' height='{88 * S}' fill='{RED}' fill-opacity='0.18' stroke='{RED}' stroke-dasharray='4 3'/>")
    # goal-mouth passer box
    q = P(-55, 300)
    b.append(f"<rect x='{q[0]}' y='{q[1]}' width='{110 * S}' height='{(300 - 226) * S}' fill='{GREEN}' fill-opacity='0.12' stroke='{GREEN}' stroke-dasharray='4 3'/>")
    # targets (with the 0-9 random)
    for (tx, ty, col, lab) in ((-116, 194, BLUE, "lofted high (about 57)"), (116, 194, BLUE, ""), (-5, 171, ORANGE, "lofted low"),
                               (0, 259, GREEN, "")):
        c = P(tx + 4.5, ty + 4.5)
        b.append(f"<rect x='{c[0] - 4.5 * S}' y='{c[1] - 4.5 * S}' width='{9 * S}' height='{9 * S}' fill='{col}' stroke='{col}'/>")
    # example flips
    ex = [((-40, 30), (-116, 194), BLUE), ((60, -20), (116, 194), BLUE), ((-20, 140), (-5, 171), ORANGE), ((10, 285), (0, 259), GREEN),
          ((-95, 40), (-155, 50), RED)]
    for (sx, sy), (tx, ty), col in ex:
        s0, t0 = P(sx, sy), P(tx, ty)
        b.append(circle(s0[0], s0[1], 5, "#ffffff", col, 2))
        b.append(f"<path d='M{s0[0]:.1f},{s0[1]:.1f} Q{(s0[0] + t0[0]) / 2:.1f},{min(s0[1], t0[1]) - 30:.1f} {t0[0]:.1f},{t0[1]:.1f}' fill='none' "
                 f"stroke='{col}' stroke-width='2' stroke-dasharray='5 3' marker-end='url(#arr)'/>")
    nx = 520
    notes = [("Outside the attacking zone", BLUE), ("to the faceoff circle on the side he", SOFT), ("faces (straight ahead: his right),", SOFT),
             ("lofted high, over everyone's sticks.", SOFT), ("", SOFT),
             ("Inside the attacking zone", ORANGE), ("to the high slot, lofted low.", SOFT), ("", SOFT),
             ("Deep, near the middle (green box)", GREEN), ("to the goal mouth.", SOFT), ("", SOFT),
             ("Over the glass (red strips)", RED), ("Closer to him than 60 sideways, the", SOFT), ("spot is moved to 60 from him: from", SOFT),
             ("75-125 out, facing the near boards,", SOFT), ("that's past the boards. Whistle.", SOFT), ("", SOFT),
             ("Each spot gets 0-9 added at random;", SOFT), ("9 of 13 recorded lofted flips came", SOFT), ("down within 12 of it.", SOFT)]
    for i, (s, c) in enumerate(notes):
        b.append(text(nx, 100 + i * 17, s, 12, c, weight="bold" if c != SOFT else "normal"))
    b.append(text(60, oy + 90, "Circles: where each example passer stands. Squares: the landing spots (with their random range).", 12, SOFT))
    b.append(text(60, oy + 107, "The SNES flip (Y) is a computer-run dump-in aimed by his side of centre instead (SNES_MECHANICS 6.3).", 12, SOFT))
    return svg(W, oy + 124, b, "The flip")


# ---------------------------------------------------------------------------------------------- 15. open-net chances
EMPTY_NET = {  # chance an aimed shot goes into an empty net, by aim, at 60 / 120 / 180 / 220 / 300 units (MECHANICS 4.2)
    "genesis": {"Nothing held": [100, 82, 65, 20, 2], "Left or right": [86, 70, 64, 20, 3], "Up (high)": [59, 56, 53, 3, 0],
                "Up-left / up-right": [57, 54, 53, 3, 0], "Down (along the ice)": [100, 100, 78, 37, 5],
                "Down-left / down-right": [86, 81, 74, 37, 5]},
    "snes": {"Nothing held": [100, 87, 62, 22, 3], "Left or right": [79, 68, 58, 22, 3], "Up (high)": [54, 49, 45, 3, 0],
             "Up-left / up-right": [50, 47, 45, 3, 0], "Down (along the ice)": [100, 100, 78, 41, 5],
             "Down-left / down-right": [79, 75, 72, 41, 5]}}


def empty_net():
    W = 860
    b = []
    b.append(text(W / 2, 28, "Shooting at an empty net: the chance it goes in, by aim and distance", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "From each game's scatter rule, for an average shooter and a 15,000 shot you aim yourself (Genesis Shot Accuracy 15, SNES 10).",
                  12, SOFT, "middle"))
    dists = [60, 120, 180, 220, 300]
    cols = {"Nothing held": INK, "Left or right": SOFT, "Up (high)": RED, "Up-left / up-right": ORANGE,
            "Down (along the ice)": GREEN, "Down-left / down-right": BLUE}
    for p, system in enumerate(("genesis", "snes")):
        L = 80 + p * 400
        R, T, B = L + 320, 90, 330
        X = lambda d: L + (R - L) * (d - 40) / 280
        Y = lambda v: B - (B - T) * v / 100
        b.append(text((L + R) / 2, 78, "Genesis" if system == "genesis" else "SNES", 13, INK, "middle", "bold"))
        chart_frame(b, L, R, T, B, dists, range(0, 101, 25), X, Y, "distance from the net (units; 3 to a foot)",
                    "chance it goes in" if p == 0 else "", str, lambda v: f"{v}%")
        b.append(f"<rect x='{X(200)}' y='{T}' width='{R - X(200)}' height='{B - T}' fill='{RED}' fill-opacity='0.05'/>")
        b.append(text(X(200) + 4, T + 12, "never exact", 10, RED))
        for aim, vals in EMPTY_NET[system].items():
            dash = "6 3" if "/" in aim or aim == "Left or right" else None
            pts = " ".join(f"{X(d):.1f},{Y(v):.1f}" for d, v in zip(dists, vals))
            b.append(f"<polyline points='{pts}' fill='none' stroke='{cols[aim]}' stroke-width='2.5'"
                     + (f" stroke-dasharray='{dash}'" if dash else "") + "/>")
            for d, v in zip(dists, vals):
                b.append(circle(X(d), Y(v), 3, cols[aim], cols[aim], 1))
    ly = 400
    for i, (aim, col) in enumerate(cols.items()):
        x, y = 80 + (i % 3) * 260, ly + (i // 3) * 20
        dash = "6 3" if "/" in aim or aim == "Left or right" else None
        b.append(line(x, y - 4, x + 30, y - 4, col, 3, dash))
        b.append(text(x + 38, y, aim, 12))
    notes = ["Hold Down or nothing at an open net, never Up: the random error only pushes the puck up, so a high aim has no room under the bar.",
             "Attacking up the screen, pushing toward the net IS holding Up. Let go of the d-pad, or hold Down, as you shoot.",
             "Get closer: inside about 180 units (60 ft) most aims still go in; past 200 no shot is exact and the error is wide.",
             "Genesis one-timers ignore the d-pad and go high at an open net (GENESIS_MECHANICS 4.4); SNES one-timers follow it."]
    for i, s in enumerate(notes):
        b.append(text(60, ly + 56 + i * 18, s, 12, SOFT))
    return svg(W, ly + 56 + len(notes) * 18 + 10, b, "Empty net")


# ---------------------------------------------------------------------------------------------- 16. defensive positions
def defence_positions():
    """Genesis defending jobs (the team defends the BOTTOM net, attacking up): assdefd (D: 50 behind the deepest attacker,
    no deeper than about 205, x 65 on his side or 0 with the puck on the other side), asswingd (x 100 on his side or the
    puck's x when it's on his side; y the puck's y beyond 78 from his goal... -158 with it in the zone, the goal line
    with it behind), asscenterd (x half the puck's; y -128 with the puck in the zone, else halfway to it)."""
    W, S = 860, 0.5
    b = []
    b.append(text(W / 2, 28, "Where computer skaters go on defence (Genesis), by where the puck is", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The defending team's own net is at the BOTTOM. Hollow marks: the attacking carrier (puck) and their deepest player.",
                  12, SOFT, "middle"))

    def spots(px, py, deep):
        in_zone, behind = py < -88, py < -268
        side = lambda sg: px * sg > 0
        d_y = max(deep - 50, -205)
        out = {"LD": (0 if not side(-1) else -65, d_y), "RD": (0 if not side(1) else 65, d_y)}
        for name, sg in (("LW", -1), ("RW", 1)):
            wx = px if side(sg) else sg * 100
            wy = -268 if behind else -158 if in_zone else py
            out[name] = (wx, wy)
        out["C"] = (px / 2, -128 if in_zone else (py - 128) / 2)
        return out

    panels = [("Puck in the neutral zone", (35, 20), -40), ("Puck in his zone", (60, -180), -230), ("Puck behind his net", (-30, -285), -285)]
    cols = {"LD": BLUE, "RD": BLUE, "LW": GREEN, "RW": GREEN, "C": ORANGE}
    for i, (title, (px, py), deep) in enumerate(panels):
        ox, oy = 160 + i * 270, 90 + 300 * S
        P = lambda x, y: (ox + x * S * 1.6, oy - y * S)
        x0, y0 = P(-130, 300)
        b.append(f"<rect x='{x0}' y='{y0}' width='{260 * S * 1.6}' height='{600 * S}' rx='{30 * S}' fill='#f7fbff' stroke='{SOFT}' stroke-width='1.5'/>")
        for yy, col, w in ((88, BLUE, 3), (-88, BLUE, 3), (0, RED, 2), (268, RED, 1.5), (-268, RED, 1.5)):
            a, c = P(-130, yy), P(130, yy)
            b.append(line(a[0], a[1], c[0], c[1], col, w))
        a = P(-20, -268)
        b.append(f"<rect x='{a[0]}' y='{a[1]}' width='{40 * S * 1.6}' height='8' fill='#ffffff' stroke='{INK}'/>")
        b.append(text(ox, y0 - 12, title, 13, INK, "middle", "bold"))
        for name, (x, y) in spots(px, py, deep).items():
            c = P(x, y)
            if math.hypot(x - px, y - py) < 25:      # on (or at) the carrier: drawn beside it, joined to it
                k = P(px, py)
                c = (k[0] + 24, k[1] - 16)
                b.append(line(k[0], k[1], c[0], c[1], cols[name], 1.5))
            b.append(circle(c[0], c[1], 10, cols[name], "#ffffff", 1.5, None, 0.9))
            b.append(text(c[0], c[1] + 4, name, 9, "#ffffff", "middle", "bold"))
        c = P(px, py)
        b.append(circle(c[0], c[1], 8, "#ffffff", INK, 2.5))
        b.append(circle(c[0], c[1], 3, INK, INK))
        d = P(px - 40 if px > 0 else px + 40, deep) if deep != py else None
        if d:
            b.append(circle(d[0], d[1], 8, "#ffffff", RED, 2.5))
    ly = 90 + 600 * S + 40
    items = [(BLUE, "defencemen: 50 behind the deepest attacker (no deeper than ~205); the one away from the puck moves to the middle"),
             (GREEN, "wingers: level with the puck (on the puck's side: right on the carrier); at 158 in the zone; at the goal line behind it"),
             (ORANGE, "centre: halfway between the puck and the high slot (128 out); in the slot once the puck is in the zone")]
    for i, (col, s) in enumerate(items):
        b.append(circle(70, ly + i * 20 - 4, 7, col, "#ffffff", 1.5))
        b.append(text(84, ly + i * 20, s, 12))
    b.append(circle(70, ly + 60 - 4, 7, "#ffffff", INK, 2))
    b.append(text(84, ly + 60, "the attacking carrier", 12))
    b.append(circle(290, ly + 60 - 4, 7, "#ffffff", RED, 2))
    b.append(text(304, ly + 60, "their deepest player (sets the defencemen's depth)", 12))
    notes = ["One skater, whoever is nearest, chases the carrier instead (assnearest); the defencemen re-read the deepest attacker only at",
             "their Defensive Awareness ticks (7-15 frames), so a quick step-out and back in leaves them where they were."]
    for i, s in enumerate(notes):
        b.append(text(60, ly + 94 + i * 17, s, 12, SOFT))
    return svg(W, ly + 140, b, "Computer defence")


# ---------------------------------------------------------------------------------------------- 17. the SNES flip
def snes_flip():
    """SNES assdumpin / DumpInTarget: outside the attacking zone (+/-80, 180) on the passer's side of centre (x sign, not
    his facing); inside it (0, 215); a goalie (0, 105). Scatter +/-(20-25 + 2 x (15 - Pas)) across, +/-(20-70) along."""
    W, S = 860, 0.9
    ox, oy = 250, 80 + 300 * 0.9
    P = lambda x, y: (ox + x * S, oy - y * S)
    b = [ARROW]
    b.append(text(W / 2, 28, "Where the SNES flip goes (Y with the puck)", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "The team attacks UP. The computer takes the flip over: the spot depends on which SIDE OF CENTRE he's on, not his facing.",
                  12, SOFT, "middle"))
    a = P(-130, 300)
    b.append(f"<rect x='{a[0]}' y='{a[1]}' width='{260 * S}' height='{360 * S}' fill='#f7fbff' stroke='{INK}' stroke-width='1.5'/>")
    # passer regions: left and right of centre outside the zone, and the zone
    for (x0, x1, col) in ((-130, 0, BLUE), (0, 130, GREEN)):
        q = P(x0, 88)
        b.append(f"<rect x='{q[0]}' y='{q[1]}' width='{(x1 - x0) * S}' height='{148 * S}' fill='{col}' fill-opacity='0.08'/>")
    q = P(-130, 300)
    b.append(f"<rect x='{q[0]}' y='{q[1]}' width='{260 * S}' height='{212 * S}' fill='{ORANGE}' fill-opacity='0.06'/>")
    for yy, col, w in ((88, BLUE, 3), (0, RED, 2), (268, RED, 1.5)):
        p0, q0 = P(-130, yy), P(130, yy)
        b.append(line(p0[0], p0[1], q0[0], q0[1], col, w))
    p0 = P(-20, 268)
    b.append(f"<rect x='{p0[0]}' y='{p0[1] - 13}' width='{40 * S}' height='13' fill='#ffffff' stroke='{INK}'/>")
    # targets with their scatter: Passing 15 (solid) and 0 (dashed), along +/-70
    for tx, ty, col in ((-80, 180, BLUE), (80, 180, GREEN), (0, 215, ORANGE)):
        for pas, dash in ((15, None), (0, "5 4")):
            hw = 25 + 2 * (15 - pas)
            q = P(tx - hw, ty + 70)
            b.append(f"<rect x='{q[0]:.1f}' y='{q[1]:.1f}' width='{2 * hw * S:.1f}' height='{140 * S:.1f}' fill='none' stroke='{col}' "
                     f"stroke-width='1.5'" + (f" stroke-dasharray='{dash}'" if dash else "") + "/>")
        c = P(tx, ty)
        b.append(circle(c[0], c[1], 6, col, INK, 1.5))
    for (sx, sy), (tx, ty), col in (((-30, 20), (-80, 180), BLUE), ((45, -20), (80, 180), GREEN), ((60, 150), (0, 215), ORANGE)):
        s0, t0 = P(sx, sy), P(tx, ty)
        b.append(circle(s0[0], s0[1], 5, "#ffffff", col, 2))
        b.append(f"<path d='M{s0[0]:.1f},{s0[1]:.1f} Q{(s0[0] + t0[0]) / 2:.1f},{min(s0[1], t0[1]) - 30:.1f} {t0[0]:.1f},{t0[1]:.1f}' "
                 f"fill='none' stroke='{col}' stroke-width='2' stroke-dasharray='5 3' marker-end='url(#arr)'/>")
    nx = 520
    notes = [("Left of centre, outside the zone", BLUE), ("deep on the left: 80 from the middle,", SOFT), ("180 up (between circle and corner).", SOFT), ("", SOFT),
             ("Right of centre, outside the zone", GREEN), ("the same on the right.", SOFT), ("", SOFT),
             ("Inside the attacking zone", ORANGE), ("in front of the net (0, 215).", SOFT), ("", SOFT),
             ("Scatter (Passing is the accuracy):", INK), ("solid box: Passing 15, +/-25 across;", SOFT), ("dashed: Passing 0, +/-55 across;", SOFT),
             ("along the ice +/-20 to 70.", SOFT), ("", SOFT),
             ("He turns to face up the ice first,", SOFT), ("so a sideways skater flips late.", SOFT),
             ("A goalie flips to about centre ice.", SOFT)]
    for i, (s_, c) in enumerate(notes):
        b.append(text(nx, 100 + i * 17, s_, 12, c, weight="bold" if c != SOFT else "normal"))
    b.append(text(60, oy + 90, "Circles: example passers. Dots: the spots. Not seen in a recording yet; from the NHL94SNES code (assdumpin, DumpInTarget).",
                  12, SOFT))
    return svg(W, oy + 110, b, "The SNES flip")


# ---------------------------------------------------------------------------------------------- 18. the early save
def early_save():
    """checkanim's wind-up rule (Genesis): shot mode, the puck within 60 of the goal line (|y| > 208), the computer
    goalie within 20 of the middle, and bit 1 of the seconds left clear: goaliesave at once, nearly always a pad stack
    sliding toward the middle and past it (gstackr, frame 454 facing down; its body test 6 to that side, reach 18)."""
    W, S = 860, 5.5
    ox, oy = 300, 380
    P = lambda x, y: (ox + x * S, oy - (y - 236) * S)
    b = [ARROW]
    b.append(text(W / 2, 28, "Wind up close in and the computer goalie drops early (Genesis)", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "To scale, top net. A slapshot wound up within 60 units of the goal line, goalie near the middle: he pad-stacks before the shot.",
                  12, SOFT, "middle"))
    gl = P(0, 268)[1]
    b.append(f"<rect x='{ox - 20 * S}' y='{gl - 15 * S}' width='{40 * S}' height='{15 * S}' fill='#f3f5f7' stroke='{SOFT}'/>")
    b.append(line(ox - 38 * S, gl, ox + 38 * S, gl, RED, 3))
    for px in (-20, 20):
        b.append(circle(ox + px * S, gl, 5, INK, INK))
    # the open side
    q = P(6, 268)
    b.append(f"<rect x='{q[0]}' y='{gl - 3}' width='{14 * S}' height='6' fill='{GOLD}'/>")
    b.append(text(P(13, 268)[0], gl - 10, "open", 12, "#8a6d00", "middle", "bold"))
    # where he stood, his slide, the pad stack
    s0, s1 = P(8, 248), P(-6, 247)
    b.append(circle(s0[0], s0[1], 14 * S, "none", BLUE, 2, "6 4"))
    b.append(text(s0[0] + 14 * S + 6, s0[1] - 20, "where he stood", 11, BLUE))
    b.extend(sprite(454, s1[0], s1[1], S, opacity=0.65))
    c = P(-12, 247)
    b.append(circle(c[0], c[1], 18 * S, "none", GREEN, 2.5))
    b.append(text(c[0], c[1] + 18 * S + 16, "pad stack: reach 18", 11, GREEN, "middle", "bold"))
    b.append(line(s0[0], s0[1] + 40, s1[0], s1[1] + 40, INK, 2, None, "marker-end='url(#arr)'"))
    b.append(text((s0[0] + s1[0]) / 2, s0[1] + 58, "slides to the middle and past", 11, INK, "middle"))
    # the shooter and his shot to the open side
    sh = P(45, 215)
    b.append(circle(sh[0], sh[1], 8, "#ffffff", RED, 2.5))
    b.append(text(sh[0] + 12, sh[1] + 4, "winding up", 12, RED, weight="bold"))
    t = P(14, 268)
    b.append(line(sh[0], sh[1], t[0], t[1], RED, 2, "6 4", "marker-end='url(#arr)'"))
    # the clock rule
    cy = oy + 190
    b.append(text(60, cy, "Only when bit 1 of the seconds left is clear: 2 game seconds on, 2 off (0.8 s of real time each).", 12, INK, weight="bold"))
    for i, sec in enumerate(range(13, -1, -1)):
        on = not (sec & 2)
        x = 60 + i * 44
        b.append(f"<rect x='{x}' y='{cy + 10}' width='40' height='22' fill='{GREEN if on else '#e4e7eb'}' fill-opacity='{0.7 if on else 1}'/>")
        b.append(text(x + 20, cy + 26, f"0:{sec:02d}", 11, INK, "middle"))
    b.append(text(60 + 14 * 44 + 8, cy + 26, "green: he can drop early", 11, SOFT))
    nx = 640
    notes = [("Recorded (computer goalies,", INK), ("shots from within 60):", INK), ("dropped early: 13 goals in 35", RED),
             ("(37%)", RED), ("waited: 8 in 65 (12%)", SOFT), ("", SOFT),
             ("22 of 23 pad stacks slid to", SOFT), ("the middle; all 11 early-save", SOFT), ("goals went in on the", SOFT),
             ("shooter's side.", SOFT), ("", SOFT),
             ("He's locked 0.72 s: keep", INK), ("gliding and shoot to your", INK), ("own side of the net.", INK)]
    for i, (s_, col) in enumerate(notes):
        b.append(text(nx, 100 + i * 17, s_, 12, col, weight="bold" if col != SOFT else "normal"))
    return svg(W, cy + 60, b, "Early save")


# ---------------------------------------------------------------------------------------------- 19. open-net one-timer
def open_net_one_timer():
    """shotdiradj (Genesis): a one-timer whose sightline to the goalie's predicted spot misses the net's middle by more
    than 22 is aimed high middle (direction 0: target z 12, crossbar 13; the scatter only goes up)."""
    W = 860
    b = [ARROW]
    b.append(text(W / 2, 28, "The open-net one-timer (Genesis): why it sails over", 17, anchor="middle", weight="bold"))
    b.append(text(W / 2, 48, "One-timers ignore the d-pad. With the goalie wandered off, the game aims them high in the middle, just under the crossbar.",
                  12, SOFT, "middle"))
    # left: top-down, the sightline test
    S, ox, oy = 2.2, 200, 380
    P = lambda x, y: (ox + x * S, oy - (y - 150) * S)
    gl = P(0, 268)[1]
    b.append(text(ox, 82, "1. The sightline test (seen from above)", 13, INK, "middle", "bold"))
    b.append(line(ox - 85 * S, gl, ox + 85 * S, gl, RED, 2.5))
    b.append(f"<rect x='{ox - 20 * S}' y='{gl - 15 * S}' width='{40 * S}' height='{15 * S}' fill='#f3f5f7' stroke='{INK}'/>")
    pk, gk = P(60, 205), P(-55, 245)
    b.append(circle(pk[0], pk[1], 6, INK, INK))
    b.append(text(pk[0] + 10, pk[1] + 4, "one-timer", 11, INK))
    b.append(circle(gk[0], gk[1], 13 * S, "#cfe3f5", BLUE, 2))
    b.append(text(gk[0], gk[1] + 4, "G", 12, INK, "middle", "bold"))
    b.append(text(gk[0], gk[1] + 13 * S + 14, "goalie wandered out", 11, BLUE, "middle"))
    b.append(line(pk[0], pk[1], gk[0], gk[1], BLUE, 1.5, "5 4"))
    mid = P(0, 268)
    b.append(circle(mid[0], mid[1], 4, GREEN, GREEN))
    b.append(text(ox, pk[1] + 40, "the sightline to him passes more than 22", 11, SOFT, "middle"))
    b.append(text(ox, pk[1] + 54, "from the net's middle: aim HIGH MIDDLE", 11, RED, "middle", "bold"))
    # right: the net, front view
    S2, nx0, base = 9, 620, 290
    b.append(text(nx0, 82, "2. The net as the shooter sees it", 13, INK, "middle", "bold"))
    b.append(line(nx0 - 28 * S2, base, nx0 + 28 * S2, base, SOFT, 2))
    b.append(f"<rect x='{nx0 - 20 * S2}' y='{base - 13 * S2}' width='{40 * S2}' height='{13 * S2}' fill='#f3f5f7' stroke='{INK}' stroke-width='3'/>")
    b.append(text(nx0 - 20 * S2, base - 13 * S2 - 8, "crossbar at 13", 11, SOFT))
    for (x, z, col, label) in ((0, 12, RED, "the one-timer's aim: 12"), (0, 6, GREEN, "a middle aim: 6")):
        cx_, cy_ = nx0 + x * S2, base - z * S2
        b.append(circle(cx_, cy_, 9, col, INK, 1.5))
        b.append(line(cx_ + (40 if z == 12 else -40), cy_, cx_ + (40 if z == 12 else -40), cy_ - 7 * S2, col, 3, None, "marker-end='url(#arr)'"))
        b.append(text(cx_ + (48 if z == 12 else -48), cy_ - 3 * S2, "error goes up only", 10, col, "start" if z == 12 else "end"))
        b.append(text(cx_ + (14 if z == 12 else -14), cy_ + 18, label, 11, col, "start" if z == 12 else "end", "bold"))
    # the chances
    ty = base + 120
    rows = [("One-timer aim at an empty net", "40", "60", "90", "120", "160"),
            ("High middle (goalie wandered)", "61%", "58%", "57%", "55%", "53%"),
            ("Side, mid-height (usual)", "89%", "84%", "73%", "67%", "63%"),
            ("Middle, mid-height (goalie pulled)", "100%", "100%", "86%", "73%", "64%")]
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            x = 60 + (0 if j == 0 else 230 + (j - 1) * 70)
            col = RED if i == 1 and j else INK if i else SOFT
            b.append(text(x, ty + i * 20, cell + (" units" if i == 0 and j == 5 else ""), 12, col, "start" if j == 0 else "middle",
                          "bold" if i == 0 else "normal"))
    notes = ["Recorded: 10 one-timers got the high-middle aim: 7 went in at heights 10-13 (just under the bar), 1 went over at 16, 2 were saved.",
             "A pulled goalie doesn't trigger it (no sightline): those one-timers are aimed mid-middle. The SNES never does this."]
    for i, s_ in enumerate(notes):
        b.append(text(60, ty + 96 + i * 18, s_, 12, SOFT))
    return svg(W, ty + 140, b, "Open-net one-timer")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    files = {"saves_reach.svg": saves(), "through_the_legs_goalie.svg": through_legs(), "aim_points_genesis.svg": aim_points("genesis"),
             "aim_points_snes.svg": aim_points("snes"), "shot_scatter.svg": scatter(), "faceoff_timing.svg": faceoffs(),
             "weight_bug.svg": weight_bug(), "shoulder_bobble.svg": shoulder_bobble(), "rocket_pass.svg": rocket_pass(),
             "computer_positions.svg": positioning(), "rink_feet.svg": rink(),
             "one_timers.svg": one_timers(), "faceoff_directions.svg": faceoff_directions(),
             "penalty_chances.svg": penalty_chances(), "flip_spots.svg": flip_spots(),
             "empty_net.svg": empty_net(), "computer_defence.svg": defence_positions(),
             "snes_flip.svg": snes_flip(), "early_save.svg": early_save(), "open_net_one_timer.svg": open_net_one_timer()}
    for name, body in files.items():
        (OUT / name).write_text(body, encoding="utf-8")
        print(OUT / name)


if __name__ == "__main__":
    main()
