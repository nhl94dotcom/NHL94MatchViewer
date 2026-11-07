"""A set of Genesis games between two teams, deeper than set_report.py (2026-11-06, the user: go much deeper on the BOS-VAN
analysis). Both teams measured the same way, from the match files:
- every goal at the release: attackers deep and in the slot, defenders goal-side, the nearest defender, and the defending
  person's skater (who, how far, in the shot's lane or not, goal-side or not, what he did in the 2.5 s before, a switch);
- every one-timer: the pass (across the middle or not, time in the air), the goalie's slide and distance off the line;
- shots by area and by shooter, with goals against xG; the chances that didn't go in;
- the goalies by shot quality;
- checking: hits by the person and by the computer, where, on the carrier or not, and what they led to;
- penalties: who, what, the person's skater or not, the hit just before, the delayed-penalty window;
- zone entries by kind, and what each led to; faceoffs by zone and what the winner did with them;
- which skaters each person ran, with the puck and without it;
- the league's recorded games with a person on each side: where each person's set falls on the measures that go with
  winning (coach_predict.py).
Rules: set_report.py's (read what a label measures, count a goal once, goalie by role).

python analysis/set_deep.py <TEAM> <TEAM> <match> ...   -> reports/deep_<TEAM>-<TEAM>_<first match's date>.md"""
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_match import own_end  # noqa: E402
import slot_defence as SD  # noqa: E402

K = 12
FT = 3.0
ACT = {"0c5e": "burst", "0b96": "check", "0bc8": "check", "0bfa": "check", "0c2c": "check", "1ac2": "check",
       "0b24": "poke", "1122": "hook", "1154": "hook", "0dd8": "down", "0d26": "down", "11e6": "stumble"}


class Game:
    def __init__(self, name):
        self.m = m = SD.load(name)
        self.name = name
        self.t = m["t"]
        self.N = len(self.t)
        self.ab = m["abbr"]
        self.shots = m.get("shotList", [])
        self.ends = {}

    def pos(self, f, k):
        p = self.m["pos"]
        return p[(f * K + k) * 2], p[(f * K + k) * 2 + 1]

    def role(self, f, k):
        return self.m["role"][f * K + k]

    def anim(self, f, k):
        return self.m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]

    def rost(self, f, k):
        return int(self.m["roster"][f * K + k], 36)

    def nm(self, team, idx):
        r = self.m["rosters"][team]
        return r[idx]["name"].split()[-1] if idx is not None and 0 <= idx < len(r) else "?"

    def rec_name(self, f, k):
        return self.nm(k // 6, self.rost(f, k))

    def skaters(self, f, team):
        return [k for k in range(team * 6, team * 6 + 6) if self.role(f, k) not in ("0", "x", "-")]

    def goalie(self, f, team):
        return next((k for k in range(team * 6, team * 6 + 6) if self.role(f, k) == "0"), None)

    def ctrl(self, f, team):
        c = self.m["ctrl"][f]
        return next((k for k in range(team * 6, team * 6 + 6) if c >> k & 1), None)

    def net_y(self, f, defending):
        """The Y of the goal line the defending team guards at frame f (from its goalie, else the period's)."""
        e = own_end(self.m, f, defending)
        per = self.m["period"][f]
        if e is None:
            e = self.ends.get((per, defending))
            if e is None:
                e = next((own_end(self.m, q, defending) for q in range(f, -1, -1) if self.m["period"][q] == per
                          and own_end(self.m, q, defending) is not None), 1)
        self.ends[(per, defending)] = e
        return 268 * e

    def frame_at(self, ms):
        lo, hi = 0, self.N - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self.t[mid] < ms:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def clock(self, f):
        c = self.m["clock"][f]
        return f"P{self.m['period'][f] + 1} {c // 60}:{c % 60:02d}"

    def score(self, f, team):
        s = self.m["score"]
        return s[2 * f + team], s[2 * f + 1 - team]

    def owner_team(self, f):
        o = self.m["owner"][f]
        return None if o is None or o < 0 else o // 6


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy or 1
    u = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - u * dx, py - ay - u * dy)


def off_line(px, py, gx, gy, net_y):
    dx, dy = -px, net_y - py
    n = math.hypot(dx, dy) or 1
    return abs((gx - px) * dy - (gy - py) * dx) / n


def area(d_ft, x):
    if d_ft < 15:
        return "under 15 ft"
    if d_ft < 30:
        return "15-30 ft, middle" if abs(x) <= 35 else "15-30 ft, wide"
    if d_ft < 45:
        return "30-45 ft"
    return "45+ ft"


AREAS = ["under 15 ft", "15-30 ft, middle", "15-30 ft, wide", "30-45 ft", "45+ ft"]


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def main():
    A, B, names = sys.argv[1], sys.argv[2], sys.argv[3:]
    teams = (A, B)
    games = [Game(n) for n in names]
    L = []
    w = L.append
    w(f"# {A} vs {B}: deeper numbers")
    w("")
    w("Games: " + ", ".join(f"{i} `{g.name}`" for i, g in enumerate(games, 1)) + ". Distances in feet (3 game units a foot). "
      "How each is measured: analysis/set_deep.py.")

    # ---------------------------------------------------------------- goals at the release
    w("")
    w("## 1. Every goal at the release")
    w("")
    w("Deep: skaters within 60 ft of the goal line. Goal-side: nearer the goal line than the shooter and within 23 ft across. "
      "In the lane: within 4 ft of the line from the shooter to the middle of the net. The defending person's skater is the "
      "one he controlled at the release; 'did' lists his bursts, checks and pokes in the 2.5 s before.")
    ga = {t: Counter() for t in teams}
    for gi, g in enumerate(games, 1):
        m = g.m
        w("")
        w(f"**Game {gi}: {g.ab[0]} {m['score'][2 * (g.N - 1)]}, {g.ab[1]} {m['score'][2 * (g.N - 1) + 1]}**")
        w("")
        w("| When | Goal | Kind | Shot from | Attackers deep / in slot | Defenders goal-side | Nearest defender | Defending person | Did (2.5 s) |")
        w("|---|---|---|---|---|---|---|---|---|")
        for goal in m["goals"]:
            team, f = goal["team"], goal["f"]
            sh = min((s for s in g.shots if s["team"] == team and s["result"] == "goal" and abs(s["f"] - f) < 200),
                     key=lambda s: abs(s["f"] - f), default=None)
            if not sh:
                continue
            fs, d = sh["f"], 1 - team
            ny = g.net_y(fs, d)
            px, py = sh["x"], sh["y"]
            dist = math.hypot(px, ny - py) / FT
            deep = [k for k in g.skaters(fs, team) if abs(g.pos(fs, k)[1] - ny) < 180]
            slot = [k for k in deep if abs(g.pos(fs, k)[0]) <= 35 and abs(g.pos(fs, k)[1] - ny) <= 100]
            back = [k for k in g.skaters(fs, d) if abs(g.pos(fs, k)[1] - ny) < abs(py - ny) and abs(g.pos(fs, k)[0] - px) < 70]
            near = min(g.skaters(fs, d), key=lambda k: math.hypot(g.pos(fs, k)[0] - px, g.pos(fs, k)[1] - py), default=None)
            nd = math.hypot(g.pos(fs, near)[0] - px, g.pos(fs, near)[1] - py) / FT if near is not None else None
            dk = g.ctrl(fs, d)
            gk = g.goalie(fs, d)
            T = teams.index(g.ab[d]) if g.ab[d] in teams else None
            key = g.ab[d]
            ga[key]["goals"] += 1
            if dk is None:
                dp, did = "none", ""
                ga[key]["none"] += 1
            elif dk == gk:
                dp, did = "had the goalie", ""
                ga[key]["goalie"] += 1
            else:
                x, y = g.pos(fs, dk)
                dd = math.hypot(x - px, y - py) / FT
                lane = seg_dist(x, y, px, py, 0, ny) <= 12
                gside = abs(y - ny) < abs(py - ny)
                acts = []
                lo = g.frame_at(g.t[fs] - 2500)
                for q in range(lo, fs + 1):
                    a = ACT.get(g.anim(q, dk))
                    if a in ("burst", "check", "poke", "hook") and (not acts or acts[-1] != a):
                        acts.append(a)
                switched = any(g.ctrl(q, d) != dk for q in range(g.frame_at(g.t[fs] - 2000), fs))
                dp = (f"{g.rec_name(fs, dk)}, {dd:.0f} ft, {'in the lane' if lane else 'goal-side' if gside else 'behind the play'}"
                      + (", switched in the 2 s before" if switched else ""))
                did = ", ".join(acts) or "nothing"
                ga[key]["lane" if lane else "gside" if gside else "behind"] += 1
                if acts:
                    ga[key]["acted"] += 1
                if near == dk:
                    ga[key]["nearest"] += 1
            ga[key]["att_slot"] += len(slot)
            ga[key]["back"] += len(back)
            near_txt = f"{g.rec_name(fs, near)} {nd:.0f} ft" + (" (the person's)" if near == dk else "") if near is not None else "-"
            wd = sh.get("goalie")
            w(f"| {g.clock(fs)} | {g.ab[team]} {g.nm(team, sh['idx'])} | {sh['type']} | {dist:.0f} ft | {len(deep)} / {len(slot)} | "
              f"{len(back)} | {near_txt} | {dp} | {did} |")
    w("")
    w("| Goals against | " + " | ".join(teams) + " |")
    w("|---|" + "---|" * len(teams))
    for label, key in (("goals against", "goals"), ("the person had the goalie", "goalie"),
                       ("his skater in the shot's lane", "lane"), ("goal-side, not in the lane", "gside"),
                       ("behind the play", "behind"), ("his skater was the nearest defender", "nearest"),
                       ("burst, checked or poked in the 2.5 s before", "acted"),
                       ("attackers in the slot at the release (total)", "att_slot"),
                       ("defenders goal-side of the shooter (total)", "back")):
        w(f"| {label} | " + " | ".join(str(ga[t][key]) for t in teams) + " |")

    # ---------------------------------------------------------------- one-timers
    w("")
    w("## 2. Every one-timer")
    w("")
    w("Across: the pass crossed the middle of the ice (x = 0). Slide: how far the goalie moved across while the pass was in "
      "the air. Off: the goalie's distance from the shot's line at the strike.")
    w("")
    w("| Game | When | Team | Shooter | Passer | Distance | Across | Air | Goalie slide / off | Goalie | xG | Result |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|")
    ots = defaultdict(list)
    for gi, g in enumerate(games, 1):
        passes = g.m.get("passes", [])
        for sh in g.shots:
            if sh["kind"] != "one-timer":
                continue
            team, f = sh["team"], sh["f"]
            ny = g.net_y(f, 1 - team)
            p = max((p for p in passes if p["team"] == team and p["f"] < f and g.t[f] - g.t[p["f"]] < 2500),
                    key=lambda p: p["f"], default=None)
            gk = g.goalie(f, 1 - team)
            gn = g.pos(f, gk) if gk is not None else None
            gt = g.pos(p["f"], gk) if (gk is not None and p) else None
            row = dict(dist=math.hypot(sh["x"], ny - sh["y"]) / FT, across=bool(p and p["x0"] * sh["x"] < 0),
                       air=(g.t[f] - g.t[p["f"]]) / 1000 if p else None,
                       slide=abs(gn[0] - gt[0]) / FT if (gn and gt) else None,
                       off=off_line(sh["x"], sh["y"], *gn, ny) / FT if gn else None, xg=sh.get("xg") or 0,
                       goal=sh["result"] == "goal", gctl=sh.get("gctl"))
            ots[g.ab[team]].append(row)
            w(f"| {gi} | {g.clock(f)} | {g.ab[team]} | {g.nm(team, sh['idx'])} | {g.nm(team, p['idx']) if p else '?'} | "
              f"{row['dist']:.0f} ft | {'yes' if row['across'] else 'no'} | {row['air'] or 0:.2f} s | "
              f"{row['slide'] or 0:.0f} / {row['off'] or 0:.0f} ft | {row['gctl']} | {row['xg']:.2f} | {sh['result']} |")
    w("")
    w("| One-timers | " + " | ".join(teams) + " |")
    w("|---|" + "---|" * len(teams))

    def avg(rs, k):
        v = [r[k] for r in rs if r[k] is not None]
        return f"{sum(v) / len(v):.1f}" if v else "-"
    for label, fn in (("attempts / goals", lambda rs: f"{len(rs)} / {sum(r['goal'] for r in rs)}"),
                      ("xG", lambda rs: f"{sum(r['xg'] for r in rs):.1f}"),
                      ("pass crossed the middle", lambda rs: f"{sum(r['across'] for r in rs)} of {len(rs)}"),
                      ("from under 30 ft", lambda rs: f"{sum(r['dist'] < 30 for r in rs)}"),
                      ("average distance (ft)", lambda rs: avg(rs, "dist")),
                      ("goalie's average slide / off the line (ft)", lambda rs: f"{avg(rs, 'slide')} / {avg(rs, 'off')}"),
                      ("a person in net", lambda rs: f"{sum(r['gctl'] == 'human' for r in rs)}")):
        w(f"| {label} | " + " | ".join(fn(ots[t]) for t in teams) + " |")
    fo = {t: 0 for t in teams}
    for g in games:
        for e in g.m.get("failedOneTimers", []):
            fo[g.ab[e["team"]]] += 1
    w(f"| one-timer tried, no shot came off (the game's failed one-timers) | " + " | ".join(str(fo[t]) for t in teams) + " |")

    # ---------------------------------------------------------------- shots by area, shooter, type
    w("")
    w("## 3. Where the shots came from")
    w("")
    ar = {t: defaultdict(lambda: [0, 0, 0.0]) for t in teams}
    ty = {t: defaultdict(lambda: [0, 0, 0.0]) for t in teams}
    who = {t: defaultdict(lambda: [0, 0, 0.0, 0]) for t in teams}
    missed = []
    for gi, g in enumerate(games, 1):
        for sh in g.shots:
            T = g.ab[sh["team"]]
            ny = g.net_y(sh["f"], 1 - sh["team"])
            d = math.hypot(sh["x"], ny - sh["y"]) / FT
            goal = sh["result"] == "goal"
            xg = sh.get("xg") or 0
            for tab, key in ((ar, area(d, sh["x"])), (ty, sh["type"])):
                tab[T][key][0] += 1
                tab[T][key][1] += goal
                tab[T][key][2] += xg
            r = who[T][g.nm(sh["team"], sh["idx"])]
            r[0] += 1
            r[1] += goal
            r[2] += xg
            r[3] += sh["kind"] == "one-timer"
            if not goal and xg >= 0.4:
                missed.append((gi, g.clock(sh["f"]), T, g.nm(sh["team"], sh["idx"]), sh["type"], d, xg, sh["result"],
                               sh.get("gctl"), sh.get("save")))
    w("| Area | " + " | ".join(f"{t}: attempts / goals / xG" for t in teams) + " |")
    w("|---|" + "---|" * len(teams))
    for a in AREAS:
        w(f"| {a} | " + " | ".join(f"{ar[t][a][0]} / {ar[t][a][1]} / {ar[t][a][2]:.1f}" for t in teams) + " |")
    w("")
    types = sorted({k for t in teams for k in ty[t]})
    w("| Shot type | " + " | ".join(f"{t}: attempts / goals / xG" for t in teams) + " |")
    w("|---|" + "---|" * len(teams))
    for k in types:
        w(f"| {k} | " + " | ".join(f"{ty[t][k][0]} / {ty[t][k][1]} / {ty[t][k][2]:.1f}" for t in teams) + " |")
    for t in teams:
        w("")
        w(f"**{t} shooters** (attempts, goals, xG, one-timers): " + "; ".join(
            f"{n} {r[0]}, {r[1]}, {r[2]:.1f}, {r[3]}" for n, r in sorted(who[t].items(), key=lambda kv: -kv[1][0])))
    w("")
    w("**Chances of 0.4 xG or more that didn't go in**")
    w("")
    w("| Game | When | Team | Shooter | Type | Distance | xG | Result | Goalie | Save |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for gi, c, T, n, tp, d, xg, res, gc, sv in sorted(missed):
        w(f"| {gi} | {c} | {T} | {n} | {tp} | {d:.0f} ft | {xg:.2f} | {res} | {gc} | {sv or '-'} |")
    mc = Counter(x[2] for x in missed)
    w("")
    w("Missed big chances: " + ", ".join(f"{t} {mc[t]} ({sum(x[6] for x in missed if x[2] == t):.1f} xG)" for t in teams) + ".")

    # ---------------------------------------------------------------- goalies by shot quality
    w("")
    w("## 4. The goalies by shot quality")
    w("")
    w("Shots that had an xG (pass shots and deflections have none), by the goalie's team, with who had him.")
    w("")
    bands = [(0, 0.1, "under 0.10"), (0.1, 0.3, "0.10-0.30"), (0.3, 0.6, "0.30-0.60"), (0.6, 1.01, "0.60 and up")]
    gq = defaultdict(lambda: [0, 0, 0.0])
    nox = defaultdict(lambda: [0, 0])
    for g in games:
        for sh in g.shots:
            T = g.ab[1 - sh["team"]]
            c = "person" if sh.get("gctl") == "human" else "computer"
            if sh.get("xg") is None:
                nox[(T, c)][0] += 1
                nox[(T, c)][1] += sh["result"] == "goal"
                continue
            b = next(lab for lo, hi, lab in bands if lo <= sh["xg"] < hi)
            r = gq[(T, c, b)]
            r[0] += 1
            r[1] += sh["result"] == "goal"
            r[2] += sh["xg"]
    w("| xG of the shot | " + " | ".join(f"{t} goalie, {c}: shots / goals / xG" for t in teams for c in ("computer", "person")) + " |")
    w("|---|" + "---|" * (2 * len(teams)))
    for lo, hi, lab in bands:
        w(f"| {lab} | " + " | ".join(f"{gq[(t, c, lab)][0]} / {gq[(t, c, lab)][1]} / {gq[(t, c, lab)][2]:.1f}"
                                     for t in teams for c in ("computer", "person")) + " |")
    w("| no xG (pass shots, deflections) | " + " | ".join(f"{nox[(t, c)][0]} / {nox[(t, c)][1]} / -" for t in teams
                                                        for c in ("computer", "person")) + " |")

    # ---------------------------------------------------------------- hits
    w("")
    w("## 5. Hits")
    w("")
    w("The game's counted checks (team = the thrower's). Zone by where it happened, for the thrower. 'Won the puck': his team "
      "had it within 1.5 s; then a shot or goal by his team within 6 s.")
    w("")
    H = {t: Counter() for t in teams}
    hitters = {t: defaultdict(Counter) for t in teams}
    for g in games:
        sh_by = [(s["f"], s["team"], s["result"] == "goal", s.get("xg") or 0) for s in g.shots]
        for h in g.m.get("hits", []):
            T = g.ab[h["team"]]
            f = h["f"]
            ny_own = g.net_y(f, h["team"])
            zone = "neutral" if abs(h["y"]) <= 89 else "own" if (h["y"] > 0) == (ny_own > 0) else "attacking"
            who_ = "person" if h.get("human") else "computer"
            won = any(g.owner_team(q) == h["team"] for q in range(f, min(g.N, g.frame_at(g.t[f] + 1500))))
            after = [s for s in sh_by if s[1] == h["team"] and 0 <= g.t[min(s[0], g.N - 1)] - g.t[f] <= 6000]
            after_against = [s for s in sh_by if s[1] != h["team"] and 0 <= g.t[min(s[0], g.N - 1)] - g.t[f] <= 6000]
            c = H[T]
            c["hits"] += 1
            c[who_] += 1
            c["zone " + zone] += 1
            c["on carrier"] += bool(h.get("onCarrier"))
            c["won"] += won and bool(h.get("onCarrier"))
            c["shot after"] += bool(after)
            c["xg after"] += sum(s[3] for s in after)
            c["goal after"] += any(s[2] for s in after)
            c["goal against after"] += any(s[2] for s in after_against)
            c["outcome " + str(h.get("outcome"))] += 1
            hc = hitters[T][g.nm(h["team"], h["by"])]
            hc["hits"] += 1
            hc["carrier"] += bool(h.get("onCarrier"))
            hc["person"] += bool(h.get("human"))
            hc["goal after"] += any(s[2] for s in after)
    rows = [("hits", "hits"), ("by the person's skater", "person"), ("by computer skaters", "computer"),
            ("in his own end", "zone own"), ("in the neutral zone", "zone neutral"), ("in the attacking end", "zone attacking"),
            ("on the puck carrier", "on carrier"), ("on the carrier and his team won the puck", "won"),
            ("a shot by his team within 6 s", "shot after"), ("a goal by his team within 6 s", "goal after"),
            ("a goal against within 6 s", "goal against after")]
    w("| | " + " | ".join(teams) + " |")
    w("|---|" + "---|" * len(teams))
    for lab, k in rows:
        w(f"| {lab} | " + " | ".join(str(H[t][k]) for t in teams) + " |")
    w(f"| xG of those shots | " + " | ".join(f"{H[t]['xg after']:.1f}" for t in teams) + " |")
    outs = sorted({k for t in teams for k in H[t] if k.startswith("outcome ")})
    for k in outs:
        w(f"| {k[8:]} | " + " | ".join(str(H[t][k]) for t in teams) + " |")
    for t in teams:
        w("")
        w(f"**{t} hitters** (hits, on the carrier, by the person, a goal for within 6 s): " + "; ".join(
            f"{n} {c['hits']}, {c['carrier']}, {c['person']}, {c['goal after']}"
            for n, c in sorted(hitters[t].items(), key=lambda kv: -kv[1]["hits"])))

    # ---------------------------------------------------------------- penalties
    w("")
    w("## 6. Penalties")
    w("")
    w("Called: when the arm went up (delayed penalty); the other team's attempts between the call and the whistle are its "
      "free shots. The hit before: a counted check by the penalized player in the second before the call.")
    w("")
    w("| Game | When | Team | Player | Penalty | The person's skater | Score then | The hit before | Free attempts (goals, xG) | Power-play goal against / shorthanded goal for |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for gi, g in enumerate(games, 1):
        rules = g.m.get("rules", {})
        for p in g.m.get("penalties", []):
            team, f = p["team"], max(0, p["f"])
            call = p.get("called", f)
            hit = next((h for h in g.m.get("hits", []) if h["team"] == team and h["by"] == p["idx"]
                        and 0 <= g.t[min(call, g.N - 1)] - g.t[h["f"]] <= 1200), None)
            free = [s for s in g.shots if s["team"] != team and call <= s["f"] <= f]
            # power-play and shorthanded goals, each given to the last penalty before it
            pens = g.m.get("penalties", [])
            mine_ = lambda x: max((q for q in pens if max(0, q["f"]) <= x["f"]), key=lambda q: q["f"], default=None) is p
            ppg = [x for x in g.m["goals"] if x["team"] != team and x.get("strength") == "PPG" and mine_(x)]
            shg = [x for x in g.m["goals"] if x["team"] == team and x.get("strength") == "SHG" and mine_(x)]
            sc = g.score(f, team)
            w(f"| {gi} | {g.clock(f)} | {g.ab[team]} | {g.nm(team, p['idx'])} | {rules.get(str(p['code']), {}).get('name', p['code'])} | "
              f"{'yes' if p.get('human') else 'no'} | {sc[0]}-{sc[1]} | "
              f"{(h_ := hit) and (h_.get('how', 'check') + ' on ' + g.nm(1 - team, h_['on'])) or '-'} | "
              f"{len(free)} ({sum(s['result'] == 'goal' for s in free)}, {sum(s.get('xg') or 0 for s in free):.1f}) | "
              f"{'PPG' if ppg else ''}{' SHG' if shg else ''}{'-' if not ppg and not shg else ''} |")
    w("")
    w("Delayed penalties (the match file's `delayed`: the team with the advantage, from the arm going up to the whistle; a "
      "goal can wipe the penalty, so not every window has a penalty above): the advantaged team can't be called, and its "
      "shots go exactly where aimed.")
    w("")
    w("| Game | When | Advantage | Length | Its share of the puck | Its attempts (goals, xG) |")
    w("|---|---|---|---|---|---|")
    for gi, g in enumerate(games, 1):
        for dl in g.m.get("delayed", []):
            a, b = dl["f"], dl.get("end", dl["f"])
            sh = [s for s in g.shots if s["team"] == dl["team"] and a <= s["f"] <= b]
            share = sum(g.owner_team(q) == dl["team"] for q in range(a, b)) / max(1, b - a)
            w(f"| {gi} | {g.clock(a)} | {g.ab[dl['team']]} | {(g.t[min(b, g.N - 1)] - g.t[a]) / 1000:.1f} s | {share:.0%} | "
              f"{len(sh)} ({sum(s['result'] == 'goal' for s in sh)}, {sum(s.get('xg') or 0 for s in sh):.1f}) |")
    strength = {t: Counter() for t in teams}
    for g in games:
        for x in g.m["goals"]:
            strength[g.ab[x["team"]]][x.get("strength", "EV")] += 1
    w("")
    w("Goals by strength: " + "; ".join(f"{t} " + ", ".join(f"{k} {v}" for k, v in sorted(strength[t].items())) for t in teams) + ".")

    # ---------------------------------------------------------------- entries
    w("")
    w("## 7. Zone entries")
    w("")
    w("Each entry until the puck left the zone or play stopped: the attempts, xG and goals by the entering team.")
    w("")
    E = {t: defaultdict(lambda: [0, 0, 0.0, 0, 0]) for t in teams}
    for g in games:
        for e in g.m.get("zoneEntries", []):
            T = g.ab[e["team"]]
            got = [s for s in g.shots if s["team"] == e["team"] and e["f"] <= s["f"] <= e.get("end", e["f"])]
            odd = e.get("odd") or [0, 0]
            for key in (e["kind"], e["kind"] + (", odd-man" if odd[0] > odd[1] else ", even or short")):
                r = E[T][key]
                r[0] += 1
                r[1] += bool(got)
                r[2] += sum(s.get("xg") or 0 for s in got)
                r[3] += any(s["result"] == "goal" for s in got)
                r[4] += bool(e.get("recovered"))
    kinds = sorted({k for t in teams for k in E[t]})
    w("| Entry | " + " | ".join(f"{t}: entries / with an attempt / xG / goals" for t in teams) + " |")
    w("|---|" + "---|" * len(teams))
    for k in kinds:
        w(f"| {k} | " + " | ".join(f"{E[t][k][0]} / {E[t][k][1]} / {E[t][k][2]:.1f} / {E[t][k][3]}" for t in teams) + " |")
    w("")
    w("Dump-ins recovered by the dumping team: " + ", ".join(
        f"{t} {E[t]['dumped'][4]} of {E[t]['dumped'][0]}" for t in teams) + ".")

    # ---------------------------------------------------------------- faceoffs
    w("")
    w("## 8. Faceoffs and what came of them")
    w("")
    F = {t: defaultdict(lambda: [0, 0, 0, 0.0, 0]) for t in teams}
    for g in games:
        for fo_ in g.m.get("faceoffs", []):
            f = fo_["f"]
            for team in (0, 1):
                T = g.ab[team]
                z = fo_["zone"]
                if z != "neu" and team == 1:
                    z = "att" if z == "def" else "def"
                lab = {"neu": "neutral", "att": "attacking", "def": "defending"}.get(z, z)
                won = fo_.get("won") == team
                got = [s for s in g.shots if s["team"] == team and 0 <= g.t[s["f"]] - g.t[f] <= 5000]
                r = F[T][lab]
                r[0] += 1
                r[1] += won
                r[2] += bool(got) and won
                r[3] += sum(s.get("xg") or 0 for s in got) if won else 0
                r[4] += any(s["result"] == "goal" for s in got)
    w("| Zone (for the team) | " + " | ".join(f"{t}: draws / won / an attempt within 5 s after a win (xG) / goals within 5 s" for t in teams) + " |")
    w("|---|" + "---|" * len(teams))
    for lab in ("attacking", "neutral", "defending"):
        w(f"| {lab} | " + " | ".join(f"{F[t][lab][0]} / {F[t][lab][1]} / {F[t][lab][2]} ({F[t][lab][3]:.1f}) / {F[t][lab][4]}"
                                     for t in teams) + " |")

    # ---------------------------------------------------------------- who each person ran
    w("")
    w("## 9. Which skaters each person ran")
    w("")
    w("Seconds the person controlled each skater (goalie included), split by who had the puck.")
    run = {t: defaultdict(lambda: [0.0, 0.0, 0.0]) for t in teams}
    switches = {t: [0, 0.0] for t in teams}
    for g in games:
        for team in (0, 1):
            T = g.ab[team]
            prev = None
            for q in range(1, g.N):
                dt = min(100, g.t[q] - g.t[q - 1]) / 1000
                if g.m["puck"][3 * q + 2] < -100:
                    continue
                k = g.ctrl(q, team)
                if k is None:
                    continue
                ot = g.owner_team(q)
                col = 0 if ot == team else 1 if ot == 1 - team else 2
                run[T][g.rec_name(q, k) + (" (G)" if g.role(q, k) == "0" else "")][col] += dt
                if ot == 1 - team:
                    switches[T][1] += dt
                    if prev is not None and k != prev and g.role(q, k) != "0" and g.role(q, prev) != "0":
                        switches[T][0] += 1
                prev = k
    for t in teams:
        tot = sum(sum(v) for v in run[t].values()) or 1
        w("")
        w(f"**{t}** (with the puck / the other team's puck / loose): " + "; ".join(
            f"{n} {100 * sum(v) / tot:.0f}% ({v[0]:.0f} / {v[1]:.0f} / {v[2]:.0f} s)"
            for n, v in sorted(run[t].items(), key=lambda kv: -sum(kv[1]))[:9]))
        w(f"Skater-to-skater switches while the other team had the puck: {switches[t][0]}, "
          f"{switches[t][0] / max(1, switches[t][1]) * 60:.0f} a minute of their possession.")

    # ---------------------------------------------------------------- the league's recorded games
    w("")
    w("## 10. Against the league's recorded games")
    w("")
    try:
        import coach_report as CR
        from coach_models import Models, matches
        from coach_predict import MEASURES
        M = Models()
        per_game = defaultdict(list)       # measure label -> values over every person-game recorded
        mine = {t: Counter() for t in teams}
        n_games = 0
        set_names = set(names)
        for p in matches():
            m = json.loads(SD.load_js_object(p)) if hasattr(SD, "load_js_object") else SD.load(p.stem)
            if m.get("system", "genesis") != "genesis" or "abbr" not in m:
                continue
            people = [any(m["ctrl"][f] >> k & 1 for f in range(0, len(m["t"]), 30) for k in range(tm * 6, tm * 6 + 6)) for tm in (0, 1)]
            if not all(people):
                continue
            n_games += 1
            for tm in (0, 1):
                c = CR.measure(m, tm, M)
                for lab, fn in MEASURES:
                    v = fn(c)
                    if v is not None:
                        per_game[lab].append(v)
                if p.stem in set_names and m["abbr"][tm] in teams:
                    mine[m["abbr"][tm]] += c
        w(f"{n_games} recorded Genesis games with a person on each side ({2 * n_games} person-games, these three included). "
          "Each measure for this set (all three games pooled), and the middle half of the per-game values (25th to 75th "
          "percentile) with the median. The measures are ordered by how strongly they go with winning (reports/coach_predict.md).")
        w("")
        w("| Measure | " + " | ".join(teams) + " | league: 25th / median / 75th |")
        w("|---|" + "---|" * len(teams) + "---|")
        for lab, fn in MEASURES:
            vals = sorted(per_game[lab])
            if len(vals) < 8:
                continue
            q = statistics.quantiles(vals, n=4)
            fmt = (lambda v: f"{v:.2f}") if max(abs(x) for x in vals) <= 1.5 else (lambda v: f"{v:.0f}")
            w(f"| {lab} | " + " | ".join(fmt(fn(mine[t])) if fn(mine[t]) is not None else "-" for t in teams)
              + f" | {fmt(q[0])} / {fmt(q[1])} / {fmt(q[2])} |")
        w("")
        w("Counts (passes across the slot, last-man checks, wasted pokes, goalie takeovers, risky passes) are for three games "
          "here and for one game in the league columns.")
    except Exception as ex:  # the league comparison is a bonus: never lose the rest of the report to it
        w(f"(not available: {ex})")

    date = names[0][:10]
    out = Path("reports") / f"deep_{A}-{B}_{date}.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
