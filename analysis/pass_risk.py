"""Do attacking-zone passes across or back make more danger against than chances for? (2026-10-29, the user: "I pass
the puck more than most opponents; I wonder if my lateral or backwards passes within the attacking zone lead to more
danger for me than they lead to scoring opportunities.") Both systems, every recorded game with a person on the side.

"You" is the team of the controller on this machine (`padTeam`); the other people are your opponents in the same
games. Only games with a person on each side (season summaries' `humans`), so both sides face people. The same
measures for both.

Each pass a person makes from the attacking zone (export_match's `dir` and `zone`), grouped by direction: ahead
(forward, diagonal forward), across (sideways), back (diagonal back, backward). From the pass, for up to WINDOW
seconds of play (cut at a whistle or the period's end):
- for: the passing team's shots (count, xG, goals) until the other team first has the puck;
- lost: the other team had the puck within the window (and "lost on the pass": the pass itself was picked off or
  went to them before a teammate touched it);
- against: after they took it, their shots (count, xG, goals) in the next WINDOW seconds (cut at a whistle).
"Ended" counts any change of hands in the window, a goalie's save included; "lost on pass" only the pass itself going
to them before a teammate touched the puck.
Net = xG for - xG against, per pass. The baseline is the same measure from every second the team has the puck in the
attacking zone with a person on it (sampled once a second), so a pass type is judged against just having the puck
there. How often each side passes: attacking-zone passes per minute of attacking-zone possession.
A pass's window and the next pass's overlap (a chain of passes shares the shot at its end), the same way for every
side, so the groups compare fairly, but the counts are not independent events: the 90% ranges come from resampling whole games.
python analysis/pass_risk.py [WINDOW]"""
import glob
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end, whistles, zone_of  # noqa: E402
from match_report import DIRS  # noqa: E402
from share_game import load_js_object  # noqa: E402

WINDOW = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
BASE = "baseline"
GROUP = {"forward": "ahead", "diagonal forward": "ahead", "sideways": "across", "diagonal back": "back",
         "backward": "back"}


def games():
    seen = set()
    for d in DIRS:
        for s in sorted(glob.glob(str(d / "*.summary.json"))):
            name = Path(s).name[:-len(".summary.json")]
            js = Path(s).with_name(name + ".js")
            if name in seen or not js.exists() or not re.match(r"\d{4}-\d\d-\d\d_", name):
                continue                               # dated games only (not the test captures)
            seen.add(name)
            yield name, json.load(open(s)), js


def team_of(k):
    return -1 if k is None or k < 0 else k // 6


class Game:
    def __init__(self, m):
        self.m, self.t, self.N = m, m["t"], len(m["t"])
        self.owner = m["owner"]
        self.stops = sorted(a for a, _ in whistles(m))           # first hidden frame of each whistle
        self.shots = sorted((s["f"], s["team"], s.get("xg") or 0.0, s["result"] == "goal")
                            for s in m.get("shotList", []) if s.get("counted", True))
        self.ends = {}

    def end_of(self, f, secs):
        """The last frame of a window from f: secs of play, a whistle or the period's end."""
        t, per = self.t, self.m["period"]
        stop = next((a for a in self.stops if a > f), self.N)
        q = f
        while q + 1 < min(stop, self.N) and t[q + 1] - t[f] <= secs * 1000 and per[q + 1] == per[f]:
            q += 1
        return q

    def shots_in(self, team, a, b):
        n = xg = goals = 0
        for f, tm, x, g in self.shots:
            if a <= f <= b and tm == team:
                n, xg, goals = n + 1, xg + x, goals + g
        return n, xg, goals

    def follow(self, f, team):
        """From frame f with `team` attacking: (for: n, xG, goals), lost frame or None, (against: n, xG, goals)."""
        end = self.end_of(f, WINDOW)
        lost = next((q for q in range(f + 1, end + 1) if team_of(self.owner[q]) == 1 - team), None)
        mine = self.shots_in(team, f, (lost - 1) if lost is not None else end)
        theirs = (0, 0.0, 0)
        if lost is not None:
            theirs = self.shots_in(1 - team, lost, self.end_of(lost, WINDOW))
        return mine, lost, theirs


def add(c, mine, lost, theirs, on_pass=False):
    c["n"] += 1
    c["shots"] += mine[0]
    c["xg"] += mine[1]
    c["goals"] += mine[2]
    c["lost"] += lost is not None
    c["lost_on_pass"] += on_pass
    c["shots_a"] += theirs[0]
    c["xg_a"] += theirs[1]
    c["goals_a"] += theirs[2]


def main():
    C = defaultdict(lambda: defaultdict(float))       # (system, side, group) -> counts
    G = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))   # (system, side, group) -> game -> [n, net xG]
    poss = defaultdict(float)                          # (system, side) -> attacking-zone possession seconds
    npass = defaultdict(int)
    listed = []
    for name, s, js in games():
        if s.get("you", -1) not in (0, 1) or not all(s.get("humans") or [False]):
            continue                                   # a person on each side only (the same games for both)
        m = json.loads(load_js_object(js))
        g = Game(m)
        system = m.get("system", s.get("system"))
        you = s["you"]
        humans = s.get("humans") or [False, False]
        sides = {you: "you"}
        if humans[1 - you]:
            sides[1 - you] = "people"
        listed.append((name, system, s.get("teams") and [x for x in (m.get("abbr") or [])], you, humans[1 - you]))
        ctrl, t, P = m.get("ctrl") or [], m["t"], m["puck"]
        for p in m.get("passes", []):
            side = sides.get(p["team"])
            if side is None or not p.get("human") or p.get("zone") != "att" or p.get("dir") not in GROUP:
                continue
            mine, lost, theirs = g.follow(p["f"], p["team"])
            on_pass = p.get("result") != "completed" and lost is not None and \
                not any(team_of(g.owner[q]) == p["team"] for q in range(p["f"] + 1, lost))
            for grp in (GROUP[p["dir"]], "all passes"):
                add(C[(system, side, grp)], mine, lost, theirs, on_pass)
                G[(system, side, grp)][name][0] += 1
                G[(system, side, grp)][name][1] += mine[1] - theirs[1]
            npass[(system, side)] += 1
        # the baseline: once a second while the side has the puck in its attacking zone, a person on the carrier
        last = -10 ** 9
        for f in range(g.N):
            k = g.owner[f]
            tm = team_of(k)
            if tm not in sides or P[3 * f + 2] < -100:
                continue
            if ctrl and not (ctrl[f] >> k) & 1:
                continue
            end = own_end(m, f, tm)
            if end is None or zone_of(P[3 * f + 1], -end) != "att":
                continue
            if f + 1 < g.N:
                poss[(system, sides[tm])] += (t[f + 1] - t[f]) / 1000
            if t[f] - last >= 1000:
                last = t[f]
                mine, lost, theirs = g.follow(f, tm)
                add(C[(system, sides[tm], BASE)], mine, lost, theirs)
                G[(system, sides[tm], BASE)][name][0] += 1
                G[(system, sides[tm], BASE)][name][1] += mine[1] - theirs[1]
    print(f"Window {WINDOW:g} s. Games:")
    for row in listed:
        print("  ", row)
    for system in ("genesis", "snes"):
        print(f"\n== {system}")
        for side in ("you", "people"):
            if not poss[(system, side)]:
                continue
            print(f"  {side}: {npass[(system, side)]} attacking-zone passes in {poss[(system, side)] / 60:.1f} min with "
                  f"the puck there = {npass[(system, side)] / (poss[(system, side)] / 60):.1f} a minute")
        print(f"  {'side':7} {'group':11} {'n':>5} {'xG for':>7} {'ended':>6} {'lost on pass':>12} {'xG against':>10} "
              f"{'net':>7}   net - baseline (90% range, games resampled)")
        for side in ("you", "people"):
            for grp in ("ahead", "across", "back", "all passes", BASE):
                c = C[(system, side, grp)]
                n = c["n"]
                if not n:
                    continue
                diff = "" if grp == BASE else "   %+.3f (%+.3f to %+.3f)" % boot(G[(system, side, grp)],
                                                                            G[(system, side, BASE)])
                print(f"  {side:7} {grp:11} {int(n):5} {c['xg'] / n:7.3f} {100 * c['lost'] / n:5.0f}% "
                      f"{100 * c['lost_on_pass'] / n:11.0f}% {c['xg_a'] / n:10.3f} {(c['xg'] - c['xg_a']) / n:+7.3f}{diff}")


def boot(a, b, reps=2000):
    """Net xG a pass minus net xG a baseline second, with a 90% range from resampling games (both from the same
    resampled games)."""
    names = sorted(set(a) | set(b))
    rnd = random.Random(1)

    def stat(pick):
        na = sum(a[g][0] for g in pick if g in a)
        nb = sum(b[g][0] for g in pick if g in b)
        if not na or not nb:
            return None
        return sum(a[g][1] for g in pick if g in a) / na - sum(b[g][1] for g in pick if g in b) / nb
    est = stat(names)
    vals = sorted(v for v in (stat([rnd.choice(names) for _ in names]) for _ in range(reps)) if v is not None)
    return est, vals[len(vals) // 20], vals[-len(vals) // 20 - 1]


if __name__ == "__main__":
    main()
