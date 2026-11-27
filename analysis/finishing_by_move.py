"""Where the winner's goals above xG come from, by the kind of shot (2026-11-26, the user: on the SNES, is it dekes and
scoring close to the net, and defending against them?). The recorded games between two people (season summaries:
finished, from the start, no bot), each unblocked attempt sorted by scoring_moves.classify (cross-crease, deke, in
close, slot, farther; on the SNES the "EA Special" flag is the Y dump-in's) with one-timers and pass shots apart.
For the winner of each decided game and for the loser: attempts, goals, xG by kind; goals above xG for the winner and
against the winner (the loser's goals below his xG) by kind, each with its standard error.

python analysis/finishing_by_move.py [genesis|snes]"""
import ast
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scoring_moves as SM  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def val(v):
    if isinstance(v, str) and v[:1] in "[{TF0123456789-":
        try:
            return ast.literal_eval(v)
        except (ValueError, SyntaxError):
            return v
    return v


def kind_of(m, s):
    if s["kind"] == "one-timer":
        return "one-timer"
    if s["kind"] == "pass shot":
        return "pass shot"
    k = SM.classify(m, s)
    return "Y dump-in follow-up" if k == "EA Special" and m.get("system") == "snes" else k


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else "snes"
    s = (HOME / "matches" / "season.js").read_text(encoding="utf-8")
    games = {g["name"]: g for g in json.loads(s[s.index("{"):s.rindex("}") + 1])["games"]}
    W = defaultdict(lambda: [0, 0, 0.0, 0.0])     # kind -> attempts, goals, xG, var  (the winner's shots)
    L = defaultdict(lambda: [0, 0, 0.0, 0.0])     # the loser's shots
    n = 0
    for p in sorted((HOME / "matches").glob("20*.js")):
        g = games.get(p.stem)
        if not g or g["system"] != system or g.get("bot"):
            continue
        hum = val(g.get("humans"))
        if not (isinstance(hum, list) and all(hum)) or val(g.get("finished")) is not True or val(g.get("fromStart")) is not True:
            continue
        sc = val(g["score"])
        if sc[0] == sc[1]:
            continue
        win = 0 if sc[0] > sc[1] else 1
        t = p.read_text(encoding="utf-8")
        m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        n += 1
        for x in m["shotList"]:
            if x.get("xg") is None or x.get("result") == "blocked" or x.get("kind") not in ("shot", "one-timer", "pass shot"):
                continue
            a = (W if x["team"] == win else L)[kind_of(m, x)]
            a[0] += 1
            a[1] += x["result"] == "goal"
            a[2] += x["xg"]
            a[3] += x["xg"] * (1 - x["xg"])
    print(f"{system}: {n} decided games between two people")
    print(f"{'kind':22s} | {'winner: attempts, goals, xG, goals - xG':44s} | {'loser: attempts, goals, xG, goals - xG':44s}")
    tw = tl = 0.0
    for k in sorted(set(W) | set(L), key=lambda k: -(W[k][1] - W[k][2]) + (L[k][1] - L[k][2])):
        w, l = W[k], L[k]
        tw += w[1] - w[2]
        tl += l[1] - l[2]
        fw = f"{w[0]:4d} {w[1]:4d} {w[2]:6.1f}  {w[1] - w[2]:+5.1f} ± {math.sqrt(w[3]):.1f}"
        fl = f"{l[0]:4d} {l[1]:4d} {l[2]:6.1f}  {l[1] - l[2]:+5.1f} ± {math.sqrt(l[3]):.1f}"
        print(f"{k:22s} | {fw:44s} | {fl:44s}")
    print(f"{'all':22s} | winner {tw:+.1f} above his xG{'':22s} | loser {tl:+.1f}")


if __name__ == "__main__":
    main()
