"""The standard match report (2026-10-21, the user picked the sections): result and luck vs skill, the game's story,
ratings as played (hot / cold), goaltending and how each person played the goalie, faceoff skill, shot timing,
checking (C vs CB choice against the weight bug), pokes, rush defence, costly turnovers, who carried the team, score
effects, special teams, post luck, what check attempts led to. Both teams measured the same way. Genesis games (the checking and faceoff sections use Genesis
frames and the weight-bug rule).
python analysis/match_report.py <match name> ...   (matches/ or Documents/NHL94 Viewer/matches) -> reports/<name>.md"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402
import deserve as DES  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slot_defence as SD  # noqa: E402
import check_outcomes as CO  # noqa: E402
import check_pass as CPASS  # noqa: E402

K = 12
DIRS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]
DOWN = {"0dd8", "0d26", "145c", "11e6"}           # falls (and the stumble)
FACEOFF_STATE = {257: 16, 265: 16, 258: 8, 266: 8}  # the faceoff swing's frames: sweep 16, middle 8, else 0


def find(name):
    for d in DIRS:
        if (d / f"{name}.js").exists():
            return d / f"{name}.js", d / f"{name}.summary.json"
    raise FileNotFoundError(name)


class Game:
    def __init__(self, name):
        mp, sp = find(name)
        self.name = name
        self.m = m = json.loads(load_js_object(mp))
        self.s = json.load(open(sp)) if sp.exists() else {}
        self.ab = self.s.get("abbr") or [m["team1"][:3].upper(), m["team2"][:3].upper()]
        self.t, self.N = m["t"], len(m["t"])

    # basic lookups
    def pos(self, f, k):
        return self.m["pos"][(f * K + k) * 2], self.m["pos"][(f * K + k) * 2 + 1]

    def anim(self, f, k):
        return self.m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]

    def frame(self, f, k):
        return int(self.m["frame"][(f * K + k) * 3:(f * K + k) * 3 + 3], 16)

    def roster(self, f, k):
        c = self.m["roster"][f * K + k]
        return int(c, 36) if c not in "x-" else -1

    def rec(self, f, team, idx):
        return next((k for k in range(team * 6, team * 6 + 6) if self.roster(f, k) == idx), None)

    def name_of(self, team, idx):
        return self.m["rosters"][team][idx]["name"] if 0 <= idx < len(self.m["rosters"][team]) else "?"

    def ctrl(self, f, team):
        c = self.m["ctrl"][f]
        return next((k for k in range(team * 6, team * 6 + 6) if c >> k & 1), None)

    def goalie(self, f, team):
        return next((k for k in range(team * 6, team * 6 + 6) if self.m["role"][f * K + k] == "0"), None)

    def net_y(self, f, team):
        """The y of the net `team` defends."""
        e = own_end(self.m, f, team)
        return 268 * (e or 1)

    def at(self, ms):
        lo, hi = 0, self.N - 1
        while lo < hi:
            mid = (lo + hi) // 2
            lo, hi = (mid + 1, hi) if self.t[mid] < ms else (lo, mid)
        return lo

    def clock_text(self, f):
        p = self.m["period"][f]
        c = self.m["clock"][f]
        return f"{'P' + str(p + 1) if p < 3 else 'OT'} {c // 60}:{c % 60:02d}"

    def game_seconds(self):
        """Game seconds ticked off at each sample (a new low of the clock in the period, at most 3 at a time)."""
        out, prev, per = [0] * self.N, None, None
        for i in range(self.N):
            p, c = self.m["period"][i], self.m["clock"][i]
            if p == per and 0 < prev - c <= 3:
                out[i] = prev - c
            per, prev = p, c
        return out


POST_BIG_XG = 0.3  # a post on a chance at least this good is listed by name in the post luck section


def off_line(px, py, gx, gy, ny):
    dx, dy = -px, ny - py
    n = math.hypot(dx, dy) or 1
    return abs((gx - px) * dy - (gy - py) * dx) / n


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def report(name):
    G = Game(name)
    m, ab, t, N = G.m, G.ab, G.t, G.N
    shots = m.get("shotList", [])
    L = []
    w = L.append
    final = (m["score"][-2], m["score"][-1])
    genesis = m.get("system", "genesis") == "genesis"  # sections 5, 7, 8 and the controller numbers read Genesis animations
    w(f"# {ab[0]} {final[0]} - {final[1]} {ab[1]}  ({name})\n")
    w(f"{m['team1']} at home, {m['team2']} away. Played on {m.get('rom')}; penalties: "
      f"{'none called' if not m.get('penalties') else len(m['penalties'])}.\n")

    # 1. result and luck vs skill
    w("## 1. Result, chances and luck\n")
    w("| | " + " | ".join(ab) + " |\n|---|---|---|")
    rows = defaultdict(list)
    for team in (0, 1):
        mine = [s for s in shots if s["team"] == team]
        theirs = [s for s in shots if s["team"] == 1 - team]
        sog = m["shots"][2 * (N - 1) + team] - m["shots"][team]
        xs = [s for s in mine if s.get("xg") is not None and s["result"] != "blocked"]
        xga = [s for s in theirs if s.get("xg") is not None and s["result"] != "blocked"]
        goals = final[team]
        rows["Goals"].append(goals)
        rows["Shots on goal / attempts"].append(f"{sog} / {len(mine)}")
        rows["Expected goals (xG)"].append(f"{sum(s['xg'] for s in xs):.1f}")
        rows["Goals from xG shots vs xG"].append(f"{sum(s['result'] == 'goal' for s in xs)} vs {sum(s['xg'] for s in xs):.1f}")
        rows["Goaltending: goals against vs xG against"].append(f"{sum(s['result'] == 'goal' for s in xga)} vs {sum(s['xg'] for s in xga):.1f}")
        sv = 1 - (final[1 - team] / max(1, m["shots"][2 * (N - 1) + 1 - team] - m["shots"][1 - team]))
        sh = goals / max(1, sog)
        rows["Shooting % / save %"].append(f"{100 * sh:.0f}% / {100 * sv:.0f}%")
        rows["PDO (shooting % + save %)"].append(f"{100 * (sh + sv):.0f}")
    d = DES.deserve(m)
    rows["Deserve to win (from the shots)"] = [f"{100 * d['win'][0]:.0f}%", f"{100 * d['win'][1]:.0f}%"]
    for k, v in rows.items():
        w(f"| {k} | {v[0]} | {v[1]} |")
    w("\nPDO near 100 is normal; well above it means the bounces (shooting and goaltending) went that team's way.\n")

    # 2. the game's story
    w("## 2. The game's story\n")
    w("| Period | " + " | ".join(f"{a} goals / xG / attempts" for a in ab) + " |\n|---|---|---|")
    played = {m["period"][i] for i in range(1, N) if m["period"][i] == m["period"][i - 1] and m["clock"][i] < m["clock"][i - 1]}
    for p in sorted(played):  # periods the clock ran in (the index moves on to 3 and 4 after the final horn)
        if p > 3:
            continue
        cells = []
        for team in (0, 1):
            sel = [s for s in shots if s["team"] == team and m["period"][s["f"]] == p]
            cells.append(f"{sum(s['result'] == 'goal' for s in sel)} / {sum(s.get('xg') or 0 for s in sel if s['result'] != 'blocked'):.1f} / {len(sel)}")
        w(f"| {'P' + str(p + 1) if p < 3 else 'OT'} | {cells[0]} | {cells[1]} |")
    w("\nGoals, with how often the scoring team would be ahead if the shots so far were replayed (deserve to win, mid-game):\n")
    sc = [0, 0]
    for g in m["goals"]:
        sc[g["team"]] += 1
        dd = DES.deserve(m, upto=g["f"])
        lead = dd["win"][g["team"]]
        assists = ", ".join(G.name_of(g["team"], a[0]) for a in g.get("assists", []))
        kinds = ", ".join(g.get("kinds", []))
        w(f"- {G.clock_text(g['f'])} **{ab[g['team']]} {G.name_of(g['team'], g['scorer'])}**"
          f"{' (' + assists + ')' if assists else ''}{' - ' + kinds if kinds else ''}. {ab[0]} {sc[0]}-{sc[1]} {ab[1]}; "
          f"on the shots so far {ab[g['team']]} would be ahead {100 * lead:.0f}% of the time.")
    # runs: 4+ unanswered attempts
    seq = sorted(shots, key=lambda s: s["f"])
    run, runs = [], []
    for s in seq:
        if run and run[-1]["team"] != s["team"]:
            if len(run) >= 4:
                runs.append(run)
            run = []
        run.append(s)
    if len(run) >= 4:
        runs.append(run)
    if runs:
        w("\nPressure spells (4 or more attempts in a row, unanswered):\n")
        for r in runs:
            w(f"- {ab[r[0]['team']]}: {len(r)} attempts from {G.clock_text(r[0]['f'])} to {G.clock_text(r[-1]['f'])}, "
              f"xG {sum(s.get('xg') or 0 for s in r if s['result'] != 'blocked'):.1f}, goals {sum(s['result'] == 'goal' for s in r)}")
    w("")

    # 3. ratings as played
    w("## 3. Ratings as played (hot / cold)\n")
    if genesis:
        w("Genesis: one hot / cold value per player for all his ratings, -3 to +2 on the 0-30 working scale (the game's "
          "scouting screen and cards show something else).\n")
    else:
        w("SNES: each rating has its own hot / cold value; a 'cold' one is played at the maximum, 15 (the game's sign bug). "
          "Shown as how many of each player's ratings are maxed.\n")
    ice = [Counter(), Counter()]
    for f in range(0, N - 1, 3):
        dt = min(300, t[f + 3] - t[f]) if f + 3 < N else 0
        for k in range(12):
            if m["role"][f * K + k] in "012345":
                ice[k // 6][G.roster(f, k)] += dt
    for team in (0, 1):
        regs = [i for i, _ in ice[team].most_common(7) if i >= 0]
        cells = []
        for i in regs:
            r = m["rosters"][team][i]
            if genesis:
                cells.append(f"{r['name']}{' (G)' if r.get('g') else ''} {r.get('hc', 0):+d}")
            else:
                vals = r.get("hcs") or [0] * 14
                names = ((1, "Agl"), (2, "Spd")) if r.get("g") else ((2, "Spd"), (9, "ShA"), (6, "Chk"), (8, "Stk"))
                up = [n for i_, n in names if vals[i_] == "max"]
                cells.append(f"{r['name']}{' (G)' if r.get('g') else ''} {sum(1 for v in vals if v == 'max')} maxed"
                             + (f" ({', '.join(up)})" if up else ""))
        hcs = [m["rosters"][team][i].get("hc", 0) for i in regs]
        w(f"- **{ab[team]}** (most-used, with hot/cold): {', '.join(cells)}." + (f" Average {sum(hcs) / max(1, len(hcs)):+.1f}." if genesis else ""))
    if genesis:
        w("\nA goalie's Agility sets his reach (12-15); -3 can cost about a unit of reach, +2 add one. For skaters it moves "
          "Speed, Agility, Shot Accuracy and the rest together.\n")
    else:
        w("\nSpd Speed, ShA Shot Accuracy, Chk Checking, Stk Stick Handling, Agl Agility: those of the maxed ratings most worth knowing.\n")

    # 4. goaltending
    w("## 4. Goaltending, and how each person played his goalie\n")
    w("| Shots faced | Person in net: shots / goals / xG / off the shot line | Computer in net: shots / goals / xG / off the line |\n|---|---|---|")
    for team in (0, 1):
        cells = []
        for who in ("human", "cpu"):
            sel = [s for s in shots if s["team"] == 1 - team and s.get("gctl") == who and s["result"] != "blocked"]
            offs = []
            for s in sel:
                gk = G.goalie(s["f"], team)
                if gk is not None:
                    offs.append(off_line(s["x"], s["y"], *G.pos(s["f"], gk), G.net_y(s["f"], team)))
            cells.append(f"{len(sel)} / {sum(s['result'] == 'goal' for s in sel)} / {sum(s.get('xg') or 0 for s in sel):.1f} / "
                         f"{(sum(offs) / len(offs)) if offs else 0:.1f}")
        w(f"| {ab[team]} goalie | {cells[0]} | {cells[1]} |")
    w("\n'Off the shot line': the goalie's distance from the line between the puck and the middle of his net as the shot "
      "is released (smaller = squarer). A person taking the goalie should get him square.\n")

    # 5. faceoffs
    w("## 5. Faceoffs\n")
    if not genesis:
        w("Genesis games only (the swing's frames are the Genesis ones).\n")
    else:
        fo = m.get("faceoffs", [])
        st = [[], []]
        rolls = [0, 0]
        for e in fo:
            f = e["f"]
            vals = []
            for team in (0, 1):
                c = next((k for k in range(team * 6, team * 6 + 6) if m["role"][f * K + k] == "4"), None)
                vals.append(FACEOFF_STATE.get(G.frame(f, c), 0) if c is not None else 0)
            for team in (0, 1):
                st[team].append(vals[team])
            if vals[0] != vals[1]:
                rolls[0 if vals[0] > vals[1] else 1] += 1
        won = Counter(e.get("won") for e in fo)
        for team in (0, 1):
            s = st[team]
            w(f"- **{ab[team]}**: swing at the drop: sweep {pct(s.count(16), len(s))}, middle {pct(s.count(8), len(s))}, "
              f"nothing {pct(s.count(0), len(s))} (average {sum(s) / max(1, len(s)):.1f} of 16); better timing than the other centre "
              f"{rolls[team]} times; won the puck first {won[team]} of {len(fo)}.")
        w("\nThe draw is pure timing: being in the swing's sweep at the drop is worth the most, and only faster mashing gets "
          "you there more often. 'Won the puck first' is the game's own faceoff stat.\n")

    # 6. shot timing
    w("## 6. Where the goalie was at the release\n")
    for team in (0, 1):
        cls = {"under 2 ft": [], "2-5 ft": [], "5+ ft": []}
        for s in shots:
            if s["team"] != team:
                continue
            f = s["f"]
            gk = G.goalie(f, 1 - team)
            if gk is None:
                continue
            gx, gy = G.pos(f, gk)
            off = off_line(s["x"], s["y"], gx, gy, G.net_y(f, 1 - team))
            cls["under 2 ft" if off < 6 else "2-5 ft" if off < 15 else "5+ ft"].append(s)
        cells = [f"{k}: {len(v)} shots, {sum(s['result'] == 'goal' for s in v)} goals, xG {sum(s.get('xg') or 0 for s in v):.1f}" for k, v in cls.items()]
        far = cls["5+ ft"]
        w(f"- **{ab[team]}** shooting: {'; '.join(cells)}. Of the 5+ ft, a person had the goalie for "
          f"{sum(s.get('gctl') == 'human' for s in far)} ({sum(s.get('gctl') == 'human' and s['result'] == 'goal' for s in far)} goals).")
    w("\nThe goalie's distance from the line between the puck and the middle of his net. xG allows for it, so this isn't a separate reason "
      "from the xG above.\n")

    # 7. checking: C vs CB against the weight bug
    w("## 7. Checking, and C vs CB skill\n")
    if not genesis:
        w("Genesis games only (the weight bug and the burst animation are the Genesis ones).\n")
    else:
        w("This ROM has the original checking code: a check the person's skater makes himself (C) is almost automatic "
          "against a man 2+ weight steps heavier and poor against anyone else; a CB check (C, then B to switch away before "
          "contact, so the computer makes it) is better when the checker is the same weight or heavier. The right choice: C "
          "into heavier men, CB otherwise.\n")
        hits = m.get("hits", [])
        for team in (0, 1):
            opp = 1 - team
            cnt = Counter()
            weight = lambda tm, idx: m["rosters"][tm][idx]["a"][0] if 0 <= idx < len(m["rosters"][tm]) else None
            for f in range(1, N - 1):
                k = G.ctrl(f, team)
                if k is None or G.anim(f, k) != "0c5e" or G.anim(f - 1, k) == "0c5e":
                    continue
                # contact: an opposing skater's body within 20 in the next 0.6 s
                contact = None
                for q in range(f, G.at(t[f] + 600)):
                    x, y = G.pos(q, k)
                    o = next((oo for oo in range(opp * 6, opp * 6 + 6) if m["role"][q * K + oo] in "12345"
                              and math.hypot(G.pos(q, oo)[0] - x, G.pos(q, oo)[1] - y) < 20), None)
                    if o is not None:
                        contact = (q, o)
                        break
                if contact is None:
                    cnt["miss"] += 1
                    continue
                q, o = contact
                kind = "C" if m["ctrl"][q] >> k & 1 else "CB"
                me, him = G.roster(q, k), G.roster(q, o)
                wc, wt = weight(team, me), weight(opp, him)
                if wc is None or wt is None:
                    continue
                down = any(h["team"] == team and h["by"] == me and h["on"] == him and -200 <= t[h["f"]] - t[q] <= 900 for h in hits)
                right = (kind == "C") == (wt - wc >= 2)
                cnt[kind] += 1
                cnt[kind + "_down"] += down
                cnt["right" if right else "wrong"] += 1
                cnt[("right" if right else "wrong") + "_down"] += down
            cpu = sum(1 for h in hits if h["team"] == team and not h.get("human"))
            pers = sum(1 for h in hits if h["team"] == team and h.get("human"))
            w(f"- **{ab[team]}**: the person's checks that reached a man: C {cnt['C']} (knocked down {cnt['C_down']}), "
              f"CB {cnt['CB']} (down {cnt['CB_down']}); bursts that met nobody {cnt['miss']}. Right choice for the weights "
              f"{cnt['right']} times (down {cnt['right_down']}, {pct(cnt['right_down'], cnt['right'])}), wrong {cnt['wrong']} times "
              f"(down {cnt['wrong_down']}, {pct(cnt['wrong_down'], cnt['wrong'])}). Knockdowns by computer skaters on their own: {cpu}; by the person's skater "
              f"{pers} (a burst lasts under 0.1 s, so some fall between samples and are not in the counts above).")
        w("")

    # 8. pokes (this ROM's B-check hack: a poke that bumps the carrier trips him, as with penalties on)
    w("## 8. Pokes (B)\n")
    if not genesis:
        w("Genesis games only (the poke animation is the Genesis one).\n")
    else:
        for team in (0, 1):
            opp = 1 - team
            c = Counter()
            for f in range(1, N - 1):
                k = G.ctrl(f, team)
                if k is None or G.anim(f, k) != "0b24" or G.anim(f - 1, k) == "0b24":
                    continue
                c["pokes"] += 1
                o = m["owner"][f]
                x, y = G.pos(f, k)
                dpuck = math.hypot(x - m["puck"][3 * f], y - m["puck"][3 * f + 1])
                if dpuck > 30:
                    c["far"] += 1
                    continue
                end = G.at(t[f] + 700)
                if o in range(opp * 6, opp * 6 + 6) and any(G.anim(q, o) in DOWN for q in range(f, end)):
                    c["trip"] += 1
                elif any(m["owner"][q] in range(team * 6, team * 6 + 6) for q in range(f, end)):
                    c["won"] += 1
                else:
                    c["nothing"] += 1
            w(f"- **{ab[team]}**: {c['pokes']} pokes; {c['far']} from out of reach (over 30: they do nothing); of the rest, "
              f"tripped the carrier {c['trip']}, won the puck {c['won']}, nothing {c['nothing']}.")
        w("")

    # 9. rush defence
    w("## 9. Rush defence\n")
    for team in (0, 1):
        opp = 1 - team
        ents = [e for e in m.get("zoneEntries", []) if e["team"] == opp and e["kind"] in ("carried", "passed")]
        odd = [e for e in ents if e.get("odd") and e["odd"][0] > e["odd"][1] and e["odd"][0] >= 2]
        def led(e, goal=False):
            return any(s["team"] == opp and e["f"] <= s["f"] <= e.get("end", e["f"] + 600) and (not goal or s["result"] == "goal") for s in shots)
        gaps, behind = [], 0
        for e in ents:
            f = e["f"]
            k = G.ctrl(f, team)
            ny = G.net_y(f, team)
            px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
            if k is not None and m["role"][f * K + k] in "12345":
                x, y = G.pos(f, k)
                gaps.append(math.hypot(x - px, y - py))
            behind += sum(1 for kk in range(team * 6, team * 6 + 6) if m["role"][f * K + kk] in "12345" and abs(G.pos(f, kk)[1] - ny) > abs(py - ny))
        w(f"- **{ab[team]} defending**: {len(ents)} carried or passed entries against, {sum(led(e) for e in ents)} led to an attempt, "
          f"{sum(led(e, True) for e in ents)} to a goal; odd-man rushes against {len(odd)} ({sum(led(e) for e in odd)} attempts, "
          f"{sum(led(e, True) for e in odd)} goals); controlled skater's gap to the puck at the line {sum(gaps) / max(1, len(gaps)):.0f}; "
          f"skaters caught up ice per entry {behind / max(1, len(ents)):.1f}.")
    w("")

    # 10. costly turnovers
    w("## 10. Turnovers that cost\n")
    for team in (0, 1):
        opp = 1 - team
        tos = [g for g in m.get("turnovers", []) if g["from"] == team and g["kind"] != "dump-in"]
        zone = Counter()
        costly = []
        for g in tos:
            ny = G.net_y(g["f"], team)
            z = "own zone" if abs(g["y"] - ny) < 180 else "attacking zone" if abs(g["y"] - ny) > 356 else "neutral zone"
            zone[z] += 1
            nxt = [s for s in shots if s["team"] == opp and 0 <= t[s["f"]] - t[g["f"]] <= 5000]
            if nxt:
                costly.append((g, z, next((s["f"] for s in nxt if s["result"] == "goal"), None)))
        hows = Counter(g["how"] for g in tos)
        w(f"- **{ab[team]}**: {len(tos)} pucks lost ({', '.join(f'{v} {k}' for k, v in zone.most_common())}; "
          f"{', '.join(f'{v} {k}' for k, v in hows.most_common())}); {len(costly)} gave up an attempt within 5 s, "
          f"{len({c[2] for c in costly if c[2] is not None})} a goal.")
        for g, z, goal in costly:
            if goal is not None:
                w(f"  - {G.clock_text(g['f'])}: {G.name_of(team, g['giver'])} ({g['how']}, {z}) -> goal against")
    w("\nHit: the game counted a check on him, or he went down. Burst: an opponent's burst reached him with no check counted. "
      "Pass picked off and lost the puck are his own; the rest were forced.\n")

    # 11. who carried the team
    w("## 11. Who carried the team\n")
    for team in (0, 1):
        pts = Counter()
        for g in m["goals"]:
            if g["team"] == team:
                pts[g["scorer"]] += 1
                for a in g.get("assists", []):
                    pts[a[0]] += 1
        att = Counter(s["idx"] for s in shots if s["team"] == team)
        pairs = Counter((p["idx"], p["to"]) for p in m.get("passes", []) if p["team"] == team and p["result"] in ("completed", "one-timer") and p.get("to", -1) >= 0)
        top3 = sum(v for _, v in att.most_common(3))
        w(f"- **{ab[team]}**: points {', '.join(f'{G.name_of(team, i)} {v}' for i, v in pts.most_common(5)) or 'none'}; "
          f"top three shooters took {pct(top3, sum(att.values()))} of the attempts; "
          f"most-used passing pairs {', '.join(f'{G.name_of(team, a)} to {G.name_of(team, b)} {v}' for (a, b), v in pairs.most_common(3))}.")
    w("")

    # 12. score effects
    w("## 12. Leading, tied, trailing\n")
    gs = G.game_seconds()
    for team in (0, 1):
        opp = 1 - team
        secs, att, xg, pokes, bursts = Counter(), Counter(), Counter(), Counter(), Counter()
        for i in range(N):
            diff = m["score"][2 * i + team] - m["score"][2 * i + opp]
            state = "leading" if diff > 0 else "trailing" if diff < 0 else "tied"
            secs[state] += gs[i]
            k = G.ctrl(i, team)
            if k is not None and i:
                a, b = G.anim(i, k), G.anim(i - 1, k)
                pokes[state] += a == "0b24" and b != "0b24"
                bursts[state] += a == "0c5e" and b != "0c5e"
        for s in shots:
            if s["team"] == team:
                f = s["f"]
                diff = m["score"][2 * f + team] - m["score"][2 * f + opp]
                state = "leading" if diff > 0 else "trailing" if diff < 0 else "tied"
                att[state] += 1
                xg[state] += (s.get("xg") or 0) if s["result"] != "blocked" else 0
        cells = []
        for state in ("leading", "tied", "trailing"):
            if secs[state] >= 30:
                p5 = 300 / secs[state]
                cells.append(f"{state} {secs[state] // 60}:{secs[state] % 60:02d}: attempts {att[state] * p5:.1f} and xG {xg[state] * p5:.2f} per 5:00"
                             + (f", person's bursts {bursts[state] * p5:.0f} / pokes {pokes[state] * p5:.0f} per 5:00" if genesis else ""))
        w(f"- **{ab[team]}**: " + "; ".join(cells) + ".")
    w("")

    # 13. special teams
    w("## 13. Special teams\n")
    pens = m.get("penalties", [])
    if not pens:
        w("No penalties were called (penalties off), so no power plays.\n")
    else:
        for team in (0, 1):
            w(f"- **{ab[team]}**: penalties {sum(p['team'] == team for p in pens)}; power-play goals "
              f"{sum(1 for g in m['goals'] if g['team'] == team and 'PPG' in g.get('kinds', []))}.")
        w("")

    # 14. keeping the other team out of the slot (slot_defence.py)
    if "owner" in m:
        w("## 14. Keeping the other team out of the slot\n")
        stats, ot = SD.measure(m, ab)
        w("Every quarter second with the other team carrying the puck in this team's end (loose pucks not counted), who was in this team's slot (within 35 of "
          "the middle and about 33 feet of the goal line). Over every recorded Genesis game, the chance of a goal in the "
          "next 3 s was 23% with the carrier in the slot, about 12% with an attacker there without the puck, 15% with "
          "the slot empty and no defender in it, 10% with one defender in it.\n")
        w("| Defending | " + " | ".join(ab) + " |\n|---|---|---|")
        tot = [sum(v[0] for (t, _), v in stats.items() if t == ab[team]) for team in (0, 1)]
        secs = [n * SD.STEP_MS // 1000 for n in tot]
        w("| Time with the other team carrying the puck in its end | " + " | ".join(f"{x // 60}:{x % 60:02d}" for x in secs) + " |")
        for state in SD.ORDER:
            cells = []
            for team in (0, 1):
                n, sh, xg, gl = stats.get((ab[team], state), [0, 0, 0.0, 0])
                cells.append((f"{100 * n / tot[team]:.0f}%" + (f" ({xg / n:.2f} xG in 3 s)" if n >= 20 else ""))
                             if tot[team] else "-")
            w(f"| {state[0].upper() + state[1:]} | " + " | ".join(cells) + " |")
        w("")
        for team in (0, 1):
            ots = {(sl, op): ot.get((ab[1 - team], sl, op), [0, 0, 0.0]) for sl in (True, False) for op in (True, False)}
            n = sum(v[0] for v in ots.values())
            if n:
                w(f"- **{ab[team]}** gave up {n} one-timer{'s' if n != 1 else ''}: "
                  + "; ".join(f"{v[0]} {'from the slot' if sl else 'from outside it'} to a receiver "
                              f"{'open' if op else 'covered'} at the pass ({v[1]} goal{'s' if v[1] != 1 else ''})"
                              for (sl, op), v in ots.items() if v[0]) + ".")
            else:
                w(f"- **{ab[team]}** gave up no one-timers.")
        w("")

    # posts: the luck that goals against xG only shows mixed in with everything else
    w("## 15. Post luck\n")
    usual = "about 1% on the Genesis" if genesis else "about 6% on the SNES"
    big = []
    for team in (0, 1):
        tried = [s for s in m["shotList"] if s["team"] == team]
        hit = [s for s in tried if s["result"] == "post"]
        w(f"- **{ab[team]}**: {len(hit)} of {len(tried)} attempts hit a post ({pct(len(hit), len(tried))}; usual: {usual}); "
          f"xG on them {sum(s.get('xg') or 0 for s in hit):.1f}; goals {sum(s['result'] == 'goal' for s in tried)} on xG "
          f"{sum(s.get('xg') or 0 for s in tried if s['result'] != 'blocked'):.1f}.")
        big += [s for s in hit if (s.get("xg") or 0) >= POST_BIG_XG]
    for sh in sorted(big, key=lambda s: s["f"]):
        f = sh["f"]
        w(f"  - P{m['period'][f] + 1} {m['clock'][f] // 60}:{m['clock'][f] % 60:02} {ab[sh['team']]} "
          f"{m['rosters'][sh['team']][sh['idx']]['name']}, xG {sh['xg']:.2f}, with the score "
          f"{ab[0]} {m['score'][2 * f]}-{m['score'][2 * f + 1]} {ab[1]}.")
    w("\nA post on a high-xG shot is mostly bad luck, though one shot's xG is rough. Pass shots have no xG.\n")

    # check attempts and what followed (check_outcomes.py)
    w("## 16. What each person's check attempts led to\n")
    events, baseline, _ = CO.measure(m)
    for team in (0, 1):
        for line in CO.lines(m, events, baseline, team):
            w(line)
    w("Hit: the game counted a check. Failed: he reached a man and it did nothing. Whiff: he touched nobody. A goal after a miss "
      "doesn't prove the miss caused it, and one game's counts are small.\n")

    w("## 17. Passing and the person's hands\n")
    for team in (0, 1):
        ps = [p for p in m.get("passes", []) if p["team"] == team]
        got = sum(p["result"] in ("completed", "one-timer") for p in ps)
        h = (m.get("habits") or [None, None])[team] or {}
        w(f"- **{ab[team]}**: {got} of {len(ps)} passes reached a teammate ({pct(got, len(ps))}), {sum(p['result'] == 'intercepted' for p in ps)} picked off; "
          f"{h.get('bursts', 0)} bursts, {h.get('pokes', 0)} pokes ({h.get('pokeTakeaways', 0)} won the puck), {h.get('goalieSeconds', 0)} s controlling the goalie.")
    if genesis:
        cp = CPASS.measure(m)
        for team in (0, 1):
            es = [e for e in cp if e["team"] == team]
            if not es:
                continue
            n = sum(e["out"].startswith("passed") for e in es)
            w(f"- **{ab[team]}**, passing out of a check (check_pass.py): {len(es)} bursts at the person's carrier; passed before contact {n} "
              f"({sum(e['out'] == CPASS.OUTCOMES[0] for e in es)} reached a teammate, {sum(e['out'] == CPASS.OUTCOMES[1] for e in es)} picked off by the checker, "
              f"{sum(e['out'] == CPASS.OUTCOMES[2] for e in es)} by another opponent); B a moment too late {sum(e['out'] in CPASS.OUTCOMES[5:7] for e in es)}.")
    w("\nPasses here are the ones the recording tracks. The game's own 'completed' count only credits the intended receiver, so it reads lower "
      "(the viewer's Passes row, season PASS%).\n")
    return "\n".join(L)


def main():
    out = Path("reports")
    out.mkdir(exist_ok=True)
    for name in sys.argv[1:]:
        text = report(name)
        (out / f"{name}.md").write_text(text, encoding="utf-8")
        print(text)
        print("\n" + "=" * 100 + "\n")


if __name__ == "__main__":
    main()
