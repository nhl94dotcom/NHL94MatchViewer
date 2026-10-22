"""SVG heat maps of the scoring map: python render_map.py RUN OUT.svg [mode] (RUN in paths.RUNS)
mode best: each spot's chance with its best aim (and the aim as an arrow); mode mid: aimed at the middle (no d-pad).
Four panels: wrist shot / slapshot x the top net / the bottom net, both drawn with the net at the top (the bottom net's
panels flipped up and down, so screen left stays left)."""
import glob
import json
import sys

from paths import RUNS

run, out = RUNS / sys.argv[1], sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "best"
rows = [json.loads(l) for f in glob.glob(f"{run}/w*.jsonl") for l in open(f)]
try:            # validity.py's verdicts: spots where the shot would start inside the goalie's reach are left out
    VALID = json.load(open(run / "validity.json"))
    for r in rows:
        if not VALID.get(f"{r['net']},{r['hold']},{r['x']},{r['y']}", {"ok": True})["ok"]:
            r["aims"] = []
except FileNotFoundError:
    pass

INK, SOFT = "#1f2933", "#52606d"
FONT = "font-family='Segoe UI, Helvetica, Arial, sans-serif'"
# d-pad direction of each aim (screen), for the arrows; 8 = nothing held
ARROW = {0: (0, -1), 1: (1, -1), 2: (1, 0), 3: (1, 1), 4: (0, 1), 5: (-1, 1), 6: (-1, 0), 7: (-1, -1)}
STOPS = [(0.0, (247, 249, 251)), (0.02, (219, 234, 254)), (0.05, (147, 197, 253)), (0.10, (96, 165, 250)),
         (0.20, (250, 204, 21)), (0.30, (249, 115, 22)), (0.45, (220, 38, 38)), (0.7, (127, 29, 29))]


def colour(p):
    for (a, ca), (b, cb) in zip(STOPS, STOPS[1:]):
        if p <= b:
            t = (p - a) / (b - a) if b > a else 0
            return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))
    return "#%02x%02x%02x" % STOPS[-1][1]


def text(x, y, s, size=12, color=INK, anchor="start", weight="normal"):
    return (f"<text x='{x:.1f}' y='{y:.1f}' font-size='{size}' fill='{color}' text-anchor='{anchor}' "
            f"font-weight='{weight}'>{s}</text>")


S = 1.45          # px per unit
PW, PH = 250 * S, 200 * S
panels = [("top", 3, "Wrist shot, top net"), ("top", 20, "Slapshot, top net"),
          ("bottom", 3, "Wrist shot, bottom net"), ("bottom", 20, "Slapshot, bottom net")]
W = 2 * PW + 3 * 40
H = 2 * (PH + 60) + 110
body = [f"<rect width='{W}' height='{H}' fill='#ffffff'/>"]
title = "Chance a shot scores against a set computer goalie, best aim" if mode == "best" else \
    "Chance a shot scores against a set computer goalie, aimed at the middle"
body.append(text(W / 2, 26, title + " (Genesis, played in the real game)", 16, anchor="middle", weight="bold"))
body.append(text(W / 2, 46, "Average shooter (working Shot Power 20, Shot Accuracy 15), standing still with the puck; "
                 "the goalie has set himself. Each square: one spot, 800+ shots per aim.", 11, SOFT, "middle"))
for pi, (net, hold, name) in enumerate(panels):
    ox = 40 + (pi % 2) * (PW + 40)
    oy = 80 + (pi // 2) * (PH + 60)
    P = lambda x, y: (ox + (x + 125) * S, oy + (268 - y) * S)
    body.append(text(ox, oy - 8, name, 13, weight="bold"))
    body.append(f"<rect x='{ox}' y='{oy}' width='{PW}' height='{PH}' fill='#f3f5f7' stroke='{SOFT}'/>")
    for r in rows:
        if r["net"] != net or r["hold"] != hold:
            continue
        x = r["x"] if net == "top" else r["x"]
        cx, cy = P(x, r["y"])
        if not r["aims"]:
            body.append(f"<rect x='{cx - 5 * S:.1f}' y='{cy - 5 * S:.1f}' width='{10 * S:.1f}' height='{10 * S:.1f}' "
                        f"fill='#e4e7eb'/>")
            continue
        a = max(r["aims"], key=lambda a: a["chance"]) if mode == "best" else r["aims"][8]
        body.append(f"<rect x='{cx - 5 * S:.1f}' y='{cy - 5 * S:.1f}' width='{10 * S:.1f}' height='{10 * S:.1f}' "
                    f"fill='{colour(a['chance'])}'/>")
        if mode == "best" and a["chance"] >= 0.03:
            if a["aim"] == 8:
                body.append(f"<circle cx='{cx:.1f}' cy='{cy:.1f}' r='1.6' fill='{INK}'/>")
            else:
                dx, dy = ARROW[a["aim"]]        # the d-pad as held (up = high, down = along the ice)
                L = 4.2 * S / (1.41 if dx and dy else 1)
                body.append(f"<line x1='{cx - dx * L:.1f}' y1='{cy - dy * L:.1f}' x2='{cx + dx * L:.1f}' "
                            f"y2='{cy + dy * L:.1f}' stroke='{INK}' stroke-width='1.2' marker-end='url(#a)'/>")
    # rink marks: goal line, net, crease, dots, blue line
    gl = P(0, 268)[1]
    body.append(f"<line x1='{ox}' y1='{gl}' x2='{ox + PW}' y2='{gl}' stroke='#c94040' stroke-width='1.5'/>")
    body.append(f"<rect x='{P(-20, 0)[0]}' y='{gl - 8 * S}' width='{40 * S}' height='{8 * S}' fill='none' "
                f"stroke='{INK}' stroke-width='1.5'/>")
    for dx in (-70, 70):
        c = P(dx, 206)
        body.append(f"<circle cx='{c[0]:.1f}' cy='{c[1]:.1f}' r='2.5' fill='#c94040'/>")
    bl = P(0, 88)[1]
    if bl <= oy + PH:
        body.append(f"<line x1='{ox}' y1='{bl}' x2='{ox + PW}' y2='{bl}' stroke='#3b82c4' stroke-width='2'/>")
    for yy in (100, 150, 200, 250):
        body.append(text(ox - 4, P(0, yy)[1] + 4, str(268 - yy), 9, SOFT, "end"))
body.insert(0, "<defs><marker id='a' viewBox='0 0 10 10' refX='5' refY='5' markerWidth='4' markerHeight='4' "
               "orient='auto'><path d='M0,0 L10,5 L0,10 z' fill='#1f2933'/></marker></defs>")
# legend
lx, ly = 40, H - 50
for i, p in enumerate([0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.45, 0.6]):
    body.append(f"<rect x='{lx + i * 62}' y='{ly}' width='58' height='14' fill='{colour(p)}' stroke='#d9e2ec'/>")
    body.append(text(lx + i * 62 + 29, ly + 28, f"{round(p * 100)}%", 10, SOFT, "middle"))
body.append(text(lx + 8 * 62 + 10, ly + 4, "Units from the goal line at the left. Arrows: the best d-pad "
                 "direction (dot: nothing held),", 10, SOFT))
body.append(text(lx + 8 * 62 + 10, ly + 18, "shown where it scores 3% or more. Grey: no real shot there (the puck would start within the goalie's reach).", 10, SOFT))
svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W:.0f}' height='{H:.0f}' viewBox='0 0 {W:.0f} {H:.0f}' "
       f"{FONT}>\n<title>Scoring map</title>\n" + "\n".join(body) + "\n</svg>\n")
open(out, "w", encoding="utf-8").write(svg)
print("rows", len(rows))
