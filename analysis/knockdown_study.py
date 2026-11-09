"""Knockdowns, holds and injuries per game in the recorded games (2026-11-09, for NOSE4Web's "a hit costs energy /
raises the injury chance" option). Both systems.

- Knockdowns: the game's own team "checks" stat, which FallDown adds to for every real knockdown by a skater (not a
  stumble; Genesis collide94 .cont2, SNES FallDown .t2): body checks, poke trips and the rest together.
- The converter's hits that knocked the player down (knocked down, upended, into the boards or bench): these include
  the poke trips (a hit is any knockdown with a hitter), so body checks are about knockdowns - poke trips.
- Poke trips: a skater going into a fall animation with an opponent in the poke animation within 32 units in the
  4 samples before (Genesis SPAsweepchk $0B24; SNES $F208).
- Holds and hooks that caught someone: a skater going into the flail animation (Genesis SPAflail $0CF4, SNES $F46A),
  split by what the catcher started (hold or hook: Genesis $0C90 / $1122, SNES $F374 / $F864) in the 40 samples
  before.
- Injuries: the converter's injuries (not those already out when the recording began).

python knockdown_study.py   (the games in Documents\\NHL94 Viewer\\matches)"""
import json
import os
from collections import Counter
from pathlib import Path

STAT_FIELDS = ("shots", "goals", "faceoffs", "checks")
SYS = {
    "genesis": dict(poke={"0b24"}, flail={"0cf4"}, hold={"0c90", "0cc2"}, hook={"1122", "1154"},
                    fall={"0d26", "0dd8", "136a", "1776", "17e8", "185a", "18cc", "193e", "1a00", "145c"}),
    "snes": dict(poke={"f208"}, flail={"f46a"}, hold={"f374"}, hook={"f864", "f3d8"},
                 fall={"f49c", "f54e", "f6c0"}),
}
DOWN = ("knocked down", "upended", "into the boards", "into the bench")


def study(m, s):
    n = len(m["t"])
    anim = m["anim"]
    a = lambda i, k: anim[(12 * i + k) * 4:(12 * i + k) * 4 + 4]
    pos = m["pos"]
    xy = lambda i, k: (pos[(12 * i + k) * 2], pos[(12 * i + k) * 2 + 1])
    team = lambda k: 0 if k < 6 else 1
    pokes, holds, hooks, other_flail = 0, 0, 0, 0
    for k in range(12):
        prev = None
        for i in range(n):
            cur = a(i, k)
            if cur != prev and prev is not None:
                if cur in s["fall"]:
                    x, y = xy(i, k)
                    hit = False
                    for j in range(max(0, i - 4), i + 1):
                        for o in range(12):
                            if team(o) != team(k) and a(j, o) in s["poke"]:
                                ox, oy = xy(j, o)
                                if (ox - x) ** 2 + (oy - y) ** 2 <= 32 ** 2:
                                    hit = True
                    pokes += hit
                elif cur in s["flail"]:
                    x, y = xy(i, k)
                    kind = None
                    for j in range(max(0, i - 40), i + 1):
                        for o in range(12):
                            if team(o) != team(k):
                                ox, oy = xy(j, o)
                                if (ox - x) ** 2 + (oy - y) ** 2 <= 40 ** 2:
                                    if a(j, o) in s["hold"]:
                                        kind = "hold"
                                    elif a(j, o) in s["hook"] and kind is None:
                                        kind = "hook"
                    if kind == "hold":
                        holds += 1
                    elif kind == "hook":
                        hooks += 1
                    else:
                        other_flail += 1
            prev = cur
    checks = sum(m["stats"][side][-1][STAT_FIELDS.index("checks")] for side in ("home", "away"))
    body = sum(1 for h in m.get("hits", []) if h.get("outcome") in DOWN)
    injuries = sum(1 for e in m.get("injuries", []) if not e.get("atStart"))
    return dict(knockdowns=checks, body=body, pokes=pokes, holds=holds, hooks=hooks, flail_other=other_flail,
                injuries=injuries)


def main():
    home = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer") / "matches"
    totals = {s: Counter() for s in SYS}
    games = Counter()
    for f in sorted(home.glob("*.js")):
        if f.name == "season.js":
            continue
        t = f.read_text(encoding="utf-8")
        try:
            m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        except ValueError:
            continue
        s = m.get("system", "genesis")
        if s not in SYS or not m.get("stats") or len(m["anim"]) < 48:
            continue
        r = study(m, SYS[s])
        totals[s].update(r)
        games[s] += 1
    for s, c in totals.items():
        n = games[s]
        if not n:
            continue
        per = {k: round(v / n, 2) for k, v in c.items()}
        print(f"{s}: {n} games; per game: {per}")
        print(f"   body checks (knockdowns - poke trips): {round((c['knockdowns'] - c['pokes']) / n, 1)} a game")


if __name__ == "__main__":
    main()
