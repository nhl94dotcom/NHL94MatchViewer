"""A diagram of one replayed goal (goal_frames.py's JSON): python goal_diagram.py SYSTEM IN.json OUT.svg "Title"
Left: the crease from above, as on the screen, the puck each frame (coloured by height) and the goalie as he was when
it passed closest: his reach (Genesis: a circle of 13, 18 in a pad stack) or his body box and his sprite frame's save
area (SNES). Right: the puck's height against its distance from the goal line, with the crossbar."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

INK, SOFT, RED, BLUE = "#1f2933", "#52606d", "#c94040", "#3b82c4"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"


def hcol(z):
    """Height colour: on the ice dark blue, rising to orange."""
    t = max(0.0, min(1.0, z / 14))
    a, b = (30, 64, 175), (234, 88, 12)
    return "#%02x%02x%02x" % tuple(round(p + (q - p) * t) for p, q in zip(a, b))


def text(x, y, s, size=12, color=INK, anchor="start", weight="normal"):
    return (f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{color}' text-anchor='{anchor}' "
            f"font-weight='{weight}'>{s}</text>")


def main():
    system, src, out, title = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    d = json.load(open(src))
    g, path, gf = d["goal"], d["path"], d["goalie"]
    top = g["net"] == "top"
    sg = 1 if top else -1
    n_goal = len(path) - 21
    pts = path[:n_goal]                                   # release .. the frame before the goal registered
    near = min(range(1, len(pts)), key=lambda i: (pts[i][0] - pts[i][5]) ** 2 + (pts[i][1] - pts[i][6]) ** 2)
    st = pts[near]
    W, H = 980, 520
    body = [f"<rect width='{W}' height='{H}' fill='#ffffff'/>", text(24, 30, title, 17, weight="bold")]
    # --- left: from above. x -50..50, y from 80 in front of the goal line to 14 behind it
    S, ox, oy = 4.2, 24, 56
    if top:
        P = lambda x, y: (ox + (x + 50) * S, oy + (282 - y) * S)
    else:
        P = lambda x, y: (ox + (x + 50) * S, oy + (-188 - y) * S)
    def PP(x, y):                                         # y in the net's own frame: 268 = goal line
        return P(x, sg * y)
    pw, ph = 100 * S, 94 * S
    body.append(f"<rect x='{ox}' y='{oy}' width='{pw}' height='{ph}' fill='#eef6fb' stroke='#d9e2ec'/>")
    a, b = PP(-50, 268), PP(50, 268)
    body.append(f"<line x1='{a[0]:.1f}' y1='{a[1]:.1f}' x2='{b[0]:.1f}' y2='{b[1]:.1f}' stroke='{RED}' stroke-width='2'/>")
    mouth, post = (20, 21) if system == "genesis" else (17, 22)
    for sx in (-1, 1):                                    # posts
        p1, p2 = PP(sx * mouth, 268), PP(sx * post, 268)
        body.append(f"<line x1='{p1[0]:.1f}' y1='{p1[1]:.1f}' x2='{p2[0]:.1f}' y2='{p2[1]:.1f}' stroke='{INK}' "
                    f"stroke-width='6'/>")
    n1, n2 = PP(-mouth, 268), PP(mouth, 278)
    body.append(f"<rect x='{min(n1[0], n2[0]):.1f}' y='{min(n1[1], n2[1]):.1f}' width='{abs(n2[0] - n1[0]):.1f}' "
                f"height='{abs(n2[1] - n1[1]):.1f}' fill='none' stroke='{SOFT}' stroke-dasharray='4 3'/>")
    # the goalie's path, then him at the puck's closest pass
    for i in range(0, len(pts), 2):
        c = P(pts[i][5], pts[i][6])
        body.append(f"<circle cx='{c[0]:.1f}' cy='{c[1]:.1f}' r='1.6' fill='#9aa5b1'/>")
    gx, gy = st[5], st[6]
    gc = P(gx, gy)
    if system == "genesis":
        stack = st[7] in (0x250, 0x2A2)
        r = 18 if stack else 13
        body.append(f"<circle cx='{gc[0]:.1f}' cy='{gc[1]:.1f}' r='{r * S:.1f}' fill='#cbd2d9' fill-opacity='0.45' "
                    f"stroke='{SOFT}' stroke-dasharray='5 3'/>")
        body.append(text(gc[0] + r * S + 6, gc[1] + 4, f"his reach: {r}" + (" (pad stack)" if stack else ""), 11,
                         SOFT))
    else:
        import xg_snes as X
        from paths import SNES_ROM
        rom = X.RomData(open(SNES_ROM, "rb").read())
        b1, b2 = P(gx - 11, gy + 10), P(gx + 10, gy - 11)
        body.append(f"<rect x='{min(b1[0], b2[0]):.1f}' y='{min(b1[1], b2[1]):.1f}' width='{abs(b2[0] - b1[0]):.1f}' "
                    f"height='{abs(b2[1] - b1[1]):.1f}' fill='#cbd2d9' fill-opacity='0.45' stroke='{SOFT}' "
                    f"stroke-dasharray='5 3'/>")
        body.append(text(max(b1[0], b2[0]) + 6, min(b1[1], b2[1]) + 10, "his body box", 11, SOFT))
        hot = rom.hot(gf[near][0])
        if hot and hot[2] > 0:
            hc = P(gx + hot[0], gy + hot[1])
            body.append(f"<circle cx='{hc[0]:.1f}' cy='{hc[1]:.1f}' r='{hot[2] * S:.1f}' fill='#16a34a' "
                        f"fill-opacity='0.35' stroke='#15803d'/>")
            body.append(text(max(b1[0], b2[0]) + 6, max(b1[1], b2[1]) + 2,
                             f"green: his save area, heights {max(0, hot[4])}-{hot[3]}", 11, "#15803d"))
    body.append(f"<circle cx='{gc[0]:.1f}' cy='{gc[1]:.1f}' r='3' fill='{INK}'/>")
    # the puck, each frame
    for i, s in enumerate(pts):
        c = P(s[0], s[1])
        if not (ox <= c[0] <= ox + pw and oy <= c[1] <= oy + ph):
            continue
        body.append(f"<circle cx='{c[0]:.1f}' cy='{c[1]:.1f}' r='{5 if i == near else 3.2}' fill='{hcol(s[2])}' "
                    + (f"stroke='{INK}' stroke-width='1.5'" if i == near else "stroke='white' stroke-width='0.8'")
                    + "/>")
    dmin = ((st[0] - gx) ** 2 + (st[1] - gy) ** 2) ** 0.5
    body.append(text(ox, oy + ph + 22, f"Frame {near} (ringed): the puck {dmin:.0f} units from his centre, "
                     f"{st[2]} off the ice. Goalie dots: where he moved.", 12, SOFT))
    body.append(text(ox, oy + ph + 40, "Puck colour = height: dark on the ice, orange high (14+). One dot a frame.", 12,
                     SOFT))
    # --- right: height against distance from the goal line
    rx, ry, rw, rh = 500, 70, 450, 300
    body.append(text(rx, ry - 14, "Height on the way in", 13, weight="bold"))
    body.append(f"<rect x='{rx}' y='{ry}' width='{rw}' height='{rh}' fill='#f8fafc' stroke='#d9e2ec'/>")
    dmax = max(20, min(200, max(268 - sg * s[1] for s in pts)))
    X_ = lambda dist: rx + rw - dist / dmax * rw
    Y_ = lambda z: ry + rh - z / 20 * rh
    bar = 13
    body.append(f"<line x1='{rx}' y1='{Y_(bar):.1f}' x2='{rx + rw}' y2='{Y_(bar):.1f}' stroke='{RED}' "
                f"stroke-dasharray='6 4'/>")
    body.append(text(rx + 6, Y_(bar) - 5, "crossbar (13)", 11, RED))
    gd = 268 - sg * gy
    body.append(f"<rect x='{X_(gd) - 4:.1f}' y='{ry}' width='8' height='{rh}' fill='#cbd2d9' fill-opacity='0.6'/>")
    body.append(text(X_(gd), ry + rh + 16, "goalie", 11, SOFT, "middle"))
    for i, s in enumerate(pts):
        dist = 268 - sg * s[1]
        if 0 <= dist <= dmax:
            body.append(f"<circle cx='{X_(dist):.1f}' cy='{Y_(min(20, s[2])):.1f}' r='{5 if i == near else 3.2}' "
                        f"fill='{hcol(s[2])}'/>")
    for z in (0, 5, 10, 15, 20):
        body.append(text(rx - 6, Y_(z) + 4, str(z), 10, SOFT, "end"))
    for dist in range(0, int(dmax) + 1, 20 if dmax <= 120 else 40):
        body.append(text(X_(dist), ry + rh + 32, str(dist), 10, SOFT, "middle"))
    body.append(text(rx + rw / 2, ry + rh + 48, "units from the goal line (about 3 to a foot); goal line at the right",
                     11, SOFT, "middle"))
    body.append(text(rx, ry + rh + 64, "Height in game units (the crossbar is at 13).", 11, SOFT))
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' {FONT}>\n"
           + "\n".join(body) + "\n</svg>\n")
    open(out, "w", encoding="utf-8").write(svg)


if __name__ == "__main__":
    main()
