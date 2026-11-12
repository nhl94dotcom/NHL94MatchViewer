"""The close-in scoring moves people use, and the bot (2026-11-12, the user: does the bot try EA Specials, cross-crease
goals, deke goals?). Every ordinary shot (shotList kind "shot") by a person's skater (or the bot's), Genesis, sorted by
the shooter's movement in the second before it, from the match file's positions and facings:
- EA Special attempt: the converter's `flip` (the side wrist shot that bobbles off the goalie: export_match);
- cross-crease (GENESIS_SHOOTING 5.7): within CROSS_OUT of the goal line, the shooter crossed the middle of the ice
  (x changed sign) in the CROSS_S before the shot, moving across faster than CROSS_V a frame at the shot;
- deke (SCORING_GENESIS_DEKES: close in, the facing swings two steps and the puck crosses in front, then the wrist
  shot): within DEKE_OUT, his facing turned two or more steps (of 8) within the DEKE_S before the shot, a wrist shot;
- else in close (within 60), from the slot (60-110), or from farther.
Per side-game: how many of each, the share scored and xG a shot; for the coaches rated 80%+ (recorded_coaches.py) and
for bot_record.py games given on the command line (the bot Home).

python analysis/scoring_moves.py [BOT_MATCHES ...]"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from recorded_coaches import ratings  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
DIG = "0123456789abcdefghijklmnopqrstuvwxyz"
CROSS_OUT, CROSS_S, CROSS_V = 90, 1000, 1.0
DEKE_OUT, DEKE_S = 80, 600
KINDS = ["EA Special", "cross-crease", "deke", "in close", "slot", "farther"]


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def classify(m, s):
    t, pos, ros, fac = m["t"], m["pos"], m["roster"], m["facing"]
    f, team = s["f"], s["team"]
    out = 264 - abs(s["y"])
    if s.get("flip"):
        return "EA Special"
    k = next((k for k in range(team * 6, team * 6 + 6)
              if ros[f * 12 + k] in DIG and DIG.index(ros[f * 12 + k]) == s["idx"]), None)
    if k is not None:
        xy = lambda q: (pos[(q * 12 + k) * 2], pos[(q * 12 + k) * 2 + 1])
        back = [q for q in range(max(0, f - 90), f + 1) if t[f] - t[q] <= CROSS_S]
        if out < CROSS_OUT and back:
            a = max(0, f - 4)
            vx = (xy(f)[0] - xy(a)[0]) / max(1, (t[f] - t[a]) / (1000 / 60))
            xs = [xy(q)[0] for q in back]
            if min(xs) < 0 < max(xs) and abs(vx) > CROSS_V:
                return "cross-crease"
        if out < DEKE_OUT and s.get("type") != "slapshot":
            fs = [int(fac[q * 12 + k]) for q in range(max(0, f - 60), f + 1)
                  if t[f] - t[q] <= DEKE_S and fac[q * 12 + k].isdigit()]
            if fs:
                turn = max(min((a - b) % 8, (b - a) % 8) for a in fs for b in fs)
                if turn >= 2:
                    return "deke"
    return "in close" if out < 60 else "slot" if out < 110 else "farther"


def tally(sides):
    """sides: [(match, team)] -> per kind [shots, goals, xg], and the number of side-games."""
    c = defaultdict(lambda: [0, 0, 0.0])
    for m, team in sides:
        for s in m.get("shotList", []):
            if s["team"] != team or s.get("kind") != "shot" or not s.get("human"):
                continue
            r = c[classify(m, s)]
            r[0] += 1
            r[1] += s.get("result") == "goal"
            r[2] += s.get("xg") or 0
    return c, len(sides)


def show(name, c, n):
    tot = sum(v[0] for v in c.values())
    print(f"\n{name}: {n} side-games, {tot / n:.1f} ordinary shots a game")
    print("| Move | a game | share of shots | scored | xG a shot |")
    print("|---|---|---|---|---|")
    for k in KINDS:
        a, g, x = c.get(k, [0, 0, 0.0])
        print(f"| {k} | {a / n:.2f} | {100 * a / max(1, tot):.0f}% | {100 * g / max(1, a):.0f}% | {x / max(1, a):.3f} |")


def main():
    rate = ratings("genesis")
    strong = []
    for f in sorted(HOME.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or d.get("bot") or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        stem = f.name.replace(".summary.json", "")
        rs = rate.get(stem, [None, None])
        m = None
        for team in (0, 1):
            if rs[team] is not None and rs[team] >= 80:
                m = m or load(f.with_name(stem + ".js"))
                strong.append((m, team))
    show("Coaches rated 80%+", *tally(strong))
    for folder in sys.argv[1:]:
        show(f"The bot ({Path(folder).parent.name})", *tally([(load(f), 0) for f in sorted(Path(folder).glob("bot_*.js"))]))


if __name__ == "__main__":
    main()
