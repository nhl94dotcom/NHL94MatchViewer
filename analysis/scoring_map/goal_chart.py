"""The share of goals by how they went in, both systems: python goal_chart.py RUN OUT.svg (goal_types.py's two JSONs in
paths.RUNS / RUN). Genesis types as goal_types names them; SNES save moves grouped by the goalie's side, and the
"clean" goals split off where he was poke-checking (SPAgpoke, $E528)."""
import collections
import json
import sys

from paths import RUNS

GEN = {"Through the blind ring": "Through the butterfly's blind ring",
       "In his pad stack": "Past or through his early pad stack",
       "Clean: outside his reach": "Clean: never within his reach",
       "Held, then dragged over the line": "Held, then carried into the net (top net)",
       "Off the goalie": "Off the goalie (deflection)", "Off the post": "Off the post"}


def snes_label(g):
    t = g["type"]
    if t.startswith("Past his"):
        return f"Past a {'right' if t.endswith('right') else 'left'}-side save move"
    if t.startswith("Clean"):
        return "During a poke check" if g["anim"] == "0xe528" else "Clean: before he moved"
    if t == "Off the goalie":
        return "Off the goalie (deflection)"
    return t


def main():
    run, out = RUNS / sys.argv[1], sys.argv[2]
    rows = {}
    for system in ("genesis", "snes"):
        d = json.load(open(run / f"goal_types_{system}.json"))
        lab = (lambda g: GEN.get(g["type"], g["type"])) if system == "genesis" else snes_label
        rows[system] = (d["shots"], len(d["goals"]), collections.Counter(lab(g) for g in d["goals"]).most_common())
    W = 980
    body, y = [], 70
    body.append("<text x='24' y='32' font-size='18' font-weight='bold' fill='#1f2933'>How the goals went in: share of "
                "all goals in a fresh sample of the maps' shots</text>")
    for system, name, col in (("genesis", "Genesis", "#2563eb"), ("snes", "SNES", "#0d9488")):
        shots, n, c = rows[system]
        body.append(f"<text x='24' y='{y}' font-size='15' font-weight='bold' fill='#1f2933'>{name}: {n:,} goals from "
                    f"{shots:,} shots ({100 * n / shots:.2f}%)</text>")
        y += 14
        for label, k in c:
            p = k / n
            bw = p * 420
            body.append(f"<text x='330' y='{y + 15}' font-size='13' fill='#1f2933' text-anchor='end'>{label}</text>")
            body.append(f"<rect x='340' y='{y + 3}' width='{max(bw, 1.5):.1f}' height='16' fill='{col}'/>")
            body.append(f"<text x='{346 + bw:.1f}' y='{y + 16}' font-size='12' fill='#52606d'>{100 * p:.1f}%  "
                        f"({k:,})</text>")
            y += 24
        y += 26
    body.append(f"<text x='24' y='{y}' font-size='12' fill='#52606d'>Every valid spot, both nets, wrist shots and "
                "slapshots, all nine aims, equally weighted; each goal sorted from the puck's and the goalie's state "
                "every frame.</text>")
    H = y + 26
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
           f"font-family='Segoe UI, Helvetica, Arial, sans-serif'>\n<rect width='{W}' height='{H}' fill='white'/>\n"
           + "\n".join(body) + "\n</svg>\n")
    open(out, "w", encoding="utf-8").write(svg)


if __name__ == "__main__":
    main()
