"""The numbers behind a written analysis of a set of games between two teams, both systems (2026-11-03, the user: review how the
analyses are done). Both teams measured the same way, from the match files: result, chances and luck, home and away, slot, the goalie's
position at the release and who had him, post luck, how the puck was lost, hits on the carrier, passing as tracked, check attempts
(check_outcomes.py), faceoffs, Shot Accuracy as played, the person's hands, and each game's goals with how they began.

Rules this keeps, each from a mistake in an earlier write-up:
- Read what a label measures. A turnover's "hit" needs a counted check or a fall (find_turnovers). Passes are the tracked ones: the game's
  own completed count only credits the intended receiver. "Giveaway" counts only unforced losses, so totals come first.
- Tie a stat to goals, not only to totals, and count a goal once when several turnovers or misses lead to it.
- The goalie is found by role, never as record 0. Animations are 4 characters a record.
- xG depends on goalie position and Shot Accuracy, so these aren't independent reasons. One shot's xG is rough.
- Post luck is a note unless it strongly affects an outcome. "Rush" here only means within 5 s of the zone entry.

python analysis/set_report.py <TEAM> <TEAM> <match> ...   -> reports/set_<TEAM>-<TEAM>_<first match's date>.md"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from share_game import load_js_object  # noqa: E402
import check_outcomes as CO  # noqa: E402
import slot_defence as SD  # noqa: E402

K = 12
HOW = ("pass picked off", "lost the puck", "hit", "burst", "poke check", "hook", "stolen")


def summary(name):
    for d in SD.DIRS:
        p = d / f"{name}.summary.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise FileNotFoundError(name)


def slot_shot(s):
    return abs(s["x"]) <= 35 and abs((264 if s["y"] > 0 else -264) - s["y"]) <= 100


def main():
    a, b, games = sys.argv[1], sys.argv[2], sys.argv[3:]
    teams = (a, b)
    L = []
    w = L.append
    A = defaultdict(lambda: defaultdict(float))
    goalie_bands = defaultdict(lambda: [0, 0, 0.0])
    sha = defaultdict(lambda: [0, 0])
    how = {t: Counter() for t in teams}
    players = {t: defaultdict(Counter) for t in teams}
    checks = {t: [] for t in teams}
    check_base = {t: [0, 0, 0.0, 0] for t in teams}
    slot_states = defaultdict(lambda: [0, 0, 0.0, 0])
    game_lines = []
    head = []
    for gi, g in enumerate(games, 1):
        m = SD.load(g)
        d = summary(g)
        T, POS, R, O, PD, CL, RO, ab, Rs = m["t"], m["pos"], m["role"], m["owner"], m["period"], m["clock"], m["roster"], m["abbr"], m["rosters"]
        xy = lambda i, k: (POS[(i * K + k) * 2], POS[(i * K + k) * 2 + 1])
        gk = lambda i, team: next((k for k in range(team * 6, team * 6 + 6) if R[i * K + k] == "0"), None)
        clock = lambda f: f"{'OT' if PD[f] == 3 else 'P' + str(PD[f] + 1)} {CL[f] // 60}:{CL[f] % 60:02}"
        score = m["score"][-2:]
        win = 0 if score[0] > score[1] else 1
        xgs = [sum(s.get("xg") or 0 for s in m["shotList"] if s["team"] == t and s["result"] != "blocked") for t in (0, 1)]
        dtw = d["teams"][win]["dtw"][0] if d["teams"][win].get("dtw") else None
        head.append(f"| {gi} | {ab[0]} | {ab[0]} {score[0]}, {ab[1]} {score[1]}{' (OT)' if d.get('overtime') else ''} | "
                    f"{xgs[0]:.1f} to {xgs[1]:.1f} | {ab[win]} {100 * dtw:.0f}% | `{g}` |" if dtw is not None else
                    f"| {gi} | {ab[0]} | {ab[0]} {score[0]}, {ab[1]} {score[1]} | {xgs[0]:.1f} to {xgs[1]:.1f} | - | `{g}` |")
        ev, base, hold = CO.measure(m)
        stats, _ = SD.measure(m, ab)
        for k, v in stats.items():
            for i in range(4):
                slot_states[k][i] += v[i]
        for t in (0, 1):
            key = ab[t]
            x = A[(key, gi)]
            sh = [s for s in m["shotList"] if s["team"] == t]
            x["home"] = t == 0
            x["goals"] = sum(s["result"] == "goal" for s in sh)
            x["att"] = len(sh)
            x["xg"] = xgs[t]
            x["xg40"] = sum((s.get("xg") or 0) >= .4 for s in sh if s["result"] != "blocked")
            x["slot"] = sum(slot_shot(s) for s in sh)
            x["slotX"] = sum(s.get("xg") or 0 for s in sh if slot_shot(s))
            x["slotG"] = sum(s["result"] == "goal" for s in sh if slot_shot(s))
            x["ot"] = sum(s["type"] == "one-timer" for s in sh)
            x["otG"] = sum(s["type"] == "one-timer" and s["result"] == "goal" for s in sh)
            x["otOut"] = sum(s["type"] == "one-timer" and not slot_shot(s) for s in sh)
            x["otOutG"] = sum(s["type"] == "one-timer" and not slot_shot(s) and s["result"] == "goal" for s in sh)
            x["wr"] = sum(s["type"] == "wrist shot" for s in sh)
            x["wrG"] = sum(s["type"] == "wrist shot" and s["result"] == "goal" for s in sh)
            x["sl"] = sum(s["type"] == "slapshot" for s in sh)
            x["slG"] = sum(s["type"] == "slapshot" and s["result"] == "goal" for s in sh)
            posts = [s for s in sh if s["result"] == "post"]
            x["posts"] = len(posts)
            x["postX"] = sum(s.get("xg") or 0 for s in posts)
            tt = d["teams"][t]
            hb = tt.get("habits") or {}
            x["az"], x["paz"] = tt["attackZone"], tt["possZones"][0]
            x["fow"], x["fo"], x["pim"], x["chk"] = tt["fow"], tt["fo"], tt["pim"], tt["checks"]
            x["pChk"] = tt["persHits"][0]
            x["bursts"], x["pokes"], x["pokeT"], x["gSec"] = hb.get("bursts", 0), hb.get("pokes", 0), hb.get("pokeTakeaways", 0), hb.get("goalieSeconds", 0)
            x["getUps"] = hb.get("getUps", 0)
            E = [e for e in m["zoneEntries"] if e["team"] == t]
            x["entries"] = len(E)
            ce = [e for e in E if e["kind"] != "dumped"]
            x["ce"] = len(ce)
            x["ceS"] = sum(any(e["f"] <= s["f"] <= e.get("end", e["f"]) for s in sh) for e in ce)
            x["odd"], x["oddG"] = tt["oddMan"][0], tt["oddMan"][2]
            ps = m.get("passes", [])
            x["passT"] = sum(p["team"] == t for p in ps)
            x["passOk"] = sum(p["team"] == t and p["result"] in ("completed", "one-timer") for p in ps)
            x["passPick"] = sum(p["team"] == t and p["result"] == "intercepted" for p in ps)
            lost = [e for e in m["turnovers"] if e["from"] == t and e["kind"] != "dump-in"]
            x["lost"] = len(lost)
            for e in lost:
                how[key][e["how"]] += 1
            theirs = [s for s in m["shotList"] if s["team"] == 1 - t]
            quick = {}
            for e in lost:
                gs = [s for s in theirs if s["result"] == "goal" and 0 <= T[s["f"]] - T[e["f"]] <= 5000]
                if gs:
                    quick[gs[0]["f"]] = e
            x["lostGoals"] = len(quick)
            x["lostGoalsOwn"] = sum(e["how"] in ("pass picked off", "lost the puck") for e in quick.values())
            hits = [h for h in m["hits"] if h["team"] == 1 - t and h.get("onCarrier")]
            x["hitOn"] = len(hits)
            x["hitDown"] = sum(h["outcome"] != "stayed up" for h in hits)
            for lab, gctl in (("person", "human"), ("cpu", "cpu")):
                sel = [s for s in theirs if s.get("gctl") == gctl]
                x[f"gk_{lab}_n"] = len(sel)
                x[f"gk_{lab}_g"] = sum(s["result"] == "goal" for s in sel)
                x[f"gk_{lab}_x"] = sum(s.get("xg") or 0 for s in sel)
            for s in sh:
                f = s["f"]
                g0 = gk(f, 1 - t)
                if g0 is None:
                    continue
                gx, gy = xy(f, g0)
                ny = 264 if s["y"] > 0 else -264
                dx, dy = -s["x"], ny - s["y"]
                n_ = math.hypot(dx, dy) or 1
                off = abs((gx - s["x"]) * dy - (gy - s["y"]) * dx) / n_
                band = "5+ ft" if off >= 15 else "under 5 ft"
                for k_ in ((key, gi, band), (key, "all", band), ("both", s.get("gctl"), band), ("both", "any", band)):
                    v = goalie_bands[k_]
                    v[0] += 1
                    v[1] += s["result"] == "goal"
                    v[2] += s.get("xg") or 0
                r = Rs[t][s["idx"]] if s["idx"] < len(Rs[t]) else None
                if r and r.get("hcs") and not r.get("g"):
                    for k_ in ((key, r["hcs"][9] == "max"), ("both", r["hcs"][9] == "max")):
                        sha[k_][0] += 1
                        sha[k_][1] += s["result"] == "goal"
            for pk, p in (d["players"][t].items() if isinstance(d["players"][t], dict) else enumerate(d["players"][t])):
                c = players[key][p["name"]]
                for f_ in ("g", "a", "att", "checks", "take", "give", "hitsTaken"):
                    c[f_] += p.get(f_, 0) or 0
                c["goalie"] = c["goalie"] or int(bool(p.get("goalie")))
            checks[key] += [dict(e, game=g) for e in ev if e["team"] == t]
            for z in CO.ZONES:
                for i in range(4):
                    check_base[key][i] += base[(t, z)][i]
            toi = Counter()
            for i in range(0, len(T), 30):
                for k in range(t * 6, t * 6 + 6):
                    if R[i * K + k] in "12345":
                        toi[int(RO[i * K + k], 36)] += 1
            top = [Rs[t][r] for r, _ in toi.most_common(5) if r < len(Rs[t])]
            if top and top[0].get("hcs"):
                x["shaMax"] = sum(p["hcs"][9] == "max" for p in top)
        for i in range(len(T) - 1):
            o = O[i]
            if o is None or o < 0 or o >= 12:
                continue
            t = 0 if o < 6 else 1
            g0 = gk(i, 1 - t)
            dt = (T[i + 1] - T[i]) / 1000
            if g0 is None or dt > .2:
                continue
            sg = 1 if xy(i, g0)[1] > 0 else -1
            X, Y = xy(i, o)
            if sg * Y >= 89:
                A[(ab[t], gi)]["carryEnd"] += dt
                if abs(X) <= 35 and 0 <= 264 - sg * Y <= 100:
                    A[(ab[t], gi)]["carrySlot"] += dt
        # each goal, with how it began
        lines = [f"**Game {gi}: {ab[0]} {score[0]}, {ab[1]} {score[1]}{' (OT)' if d.get('overtime') else ''}**", ""]
        fos = sorted(fo["f"] for fo in m.get("faceoffs", []))
        for x_ in m["goals"]:
            f = x_["f"]
            s = max((s for s in m["shotList"] if s["team"] == x_["team"] and s["result"] == "goal" and s["f"] <= f + 3), key=lambda s: s["f"], default=None)
            tv = max((e for e in m["turnovers"] if e["from"] == 1 - x_["team"] and e["f"] <= f and e["kind"] != "dump-in"), key=lambda e: e["f"], default=None)
            fo = max((q for q in fos if q <= f), default=-1)
            if tv and tv["f"] > fo:
                nm = Rs[1 - x_["team"]][tv["giver"]]["name"].split()[-1] if 0 <= tv.get("giver", -1) < len(Rs[1 - x_["team"]]) else "?"
                began = f"{tv['how']}, {nm}, {(T[f] - T[tv['f']]) / 1000:.0f} s before"
            elif fo >= 0:
                began = f"faceoff, {(T[f] - T[fo]) / 1000:.0f} s before"
            else:
                began = "?"
            name = Rs[x_["team"]][x_["scorer"]]["name"].split()[-1] if isinstance(x_.get("scorer"), int) and x_["scorer"] < len(Rs[x_["team"]]) else "?"
            sc = f"{m['score'][2 * f]}-{m['score'][2 * f + 1]}"
            if s:
                g0 = gk(s["f"], 1 - x_["team"])
                off = ""
                if g0 is not None:
                    gx, gy = xy(s["f"], g0)
                    ny = 264 if s["y"] > 0 else -264
                    dx, dy = -s["x"], ny - s["y"]
                    off = f"{abs((gx - s['x']) * dy - (gy - s['y']) * dx) / (math.hypot(dx, dy) or 1) / 3:.0f} ft off"
                lines.append(f"- {clock(f)} {ab[x_['team']]} {name} ({s['type']}, xG {s.get('xg') or 0:.2f}; goalie {'person' if s.get('gctl') == 'human' else 'computer'}, {off}): began with {began}. {ab[0]} {sc} {ab[1]}.")
            else:
                lines.append(f"- {clock(f)} {ab[x_['team']]} {name}: began with {began}. {ab[0]} {sc} {ab[1]}.")
        pp = [s for s in m["shotList"] if s["result"] == "post" and (s.get("xg") or 0) >= .3]
        for s in pp:
            f = s["f"]
            lines.append(f"- Post: {clock(f)} {ab[s['team']]} {Rs[s['team']][s['idx']]['name'].split()[-1]}, xG {s['xg']:.2f}, {ab[0]} {m['score'][2 * f]}-{m['score'][2 * f + 1]} {ab[1]}.")
        lines.append("")
        game_lines += lines
    n = len(games)
    R_ = range(1, n + 1)
    tot = lambda t, c: sum(A[(t, i)][c] for i in R_)
    side = lambda t, c, home: sum(A[(t, i)][c] for i in R_ if bool(A[(t, i)]["home"]) == home)
    w(f"# {a} vs {b}: the numbers\n")
    w("| Game | Home | Result | xG | Deserve to win (winner) | Match |\n|---|---|---|---|---|---|")
    L += head
    w("")
    w("## Home and away\n")
    w(f"| | {a} home | {a} away | {b} home | {b} away |\n|---|---|---|---|---|")
    for lab, c, fmt in (("Goals", "goals", "{:.0f}"), ("xG", "xg", "{:.1f}"), ("Attempts", "att", "{:.0f}"), ("Slot attempts", "slot", "{:.0f}"),
                        ("xG from the slot", "slotX", "{:.1f}"), ("Shots of 0.4 xG or better", "xg40", "{:.0f}"), ("Seconds carrying in the other end", "carryEnd", "{:.0f}"),
                        ("Seconds carrying in the slot", "carrySlot", "{:.0f}"), ("Carried or passed entries", "ce", "{:.0f}"), ("... that led to an attempt", "ceS", "{:.0f}")):
        w(f"| {lab} | " + " | ".join(fmt.format(side(t, c, h)) for t in teams for h in (True, False)) + " |")
    w("")
    w("## Game by game\n")
    w("| | " + " | ".join(f"{t} {i}" for t in teams for i in R_) + f" | {a} | {b} |\n|---|" + "---|" * (2 * n + 2))
    ROWS = (("Goals", "goals", 0), ("xG", "xg", 1), ("Attempts", "att", 0), ("Slot attempts", "slot", 0), ("xG from the slot", "slotX", 1), ("Goals from the slot", "slotG", 0),
            ("Puck in their end (game s)", "az", 0), ("Own possession there (game s)", "paz", 0), ("Seconds carrying in their end", "carryEnd", 0), ("Seconds carrying in the slot", "carrySlot", 0),
            ("Odd-man rushes", "odd", 0), ("Goals off them", "oddG", 0), ("Wrist shots", "wr", 0), ("Wrist goals", "wrG", 0), ("One-timers", "ot", 0), ("One-timer goals", "otG", 0), ("One-timers from outside the slot", "otOut", 0), ("Goals from those", "otOutG", 0),
            ("Slapshots", "sl", 0), ("Slapshot goals", "slG", 0), ("Posts", "posts", 0), ("xG on posts", "postX", 1),
            ("Pucks lost", "lost", 0), ("Goal against within 5 s of one", "lostGoals", 0), ("... from his own mistake", "lostGoalsOwn", 0),
            ("Passes tracked", "passT", 0), ("Reached a teammate", "passOk", 0), ("Picked off", "passPick", 0), ("Faceoffs won", "fow", 0), ("Faceoffs", "fo", 0),
            ("Checks (game's count)", "chk", 0), ("By the person", "pChk", 0), ("Hits taken on the carrier", "hitOn", 0), ("Knocked down", "hitDown", 0), ("Penalty minutes", "pim", 0),
            ("Bursts", "bursts", 0), ("Pokes", "pokes", 0), ("Poke takeaways", "pokeT", 0), ("Get-ups", "getUps", 0), ("Goalie control (s)", "gSec", 0),
            ("Shots faced, person in net", "gk_person_n", 0), ("Goals", "gk_person_g", 0), ("xG", "gk_person_x", 1), ("Shots faced, computer in net", "gk_cpu_n", 0), ("Goals", "gk_cpu_g", 0), ("xG", "gk_cpu_x", 1),
            ("Maxed Shot Accuracy, top 5 skaters", "shaMax", 0))
    for lab, c, dec in ROWS:
        w(f"| {lab} | " + " | ".join(f"{A[(t, i)][c]:.{dec}f}" for t in teams for i in R_) + f" | {tot(a, c):.{dec}f} | {tot(b, c):.{dec}f} |")
    w("")
    w("## How the puck was lost\n")
    w(f"| | {a} | {b} |\n|---|---|---|")
    for h in HOW:
        w(f"| {h} | {how[a][h]} | {how[b][h]} |")
    w("")
    w("## The goalie at the release\n")
    w("| Goalie | Shots | Goals | Rate | xG |\n|---|---|---|---|---|")
    for lab, k_ in (("Person, 5+ ft off the line", ("both", "human", "5+ ft")), ("Person, closer", ("both", "human", "under 5 ft")), ("Computer, 5+ ft off", ("both", "cpu", "5+ ft")), ("Computer, closer", ("both", "cpu", "under 5 ft"))):
        v = goalie_bands[k_]
        w(f"| {lab} | {v[0]} | {v[1]} | {100 * v[1] / max(v[0], 1):.0f}% | {v[2]:.1f} |")
    w("")
    w(f"| Shots with the goalie 5+ ft off / closer | " + " | ".join(f"Game {i}" for i in R_) + " |\n|---|" + "---|" * n)
    for t in teams:
        w(f"| {t} | " + " | ".join(f"{goalie_bands[(t, i, '5+ ft')][0]} / {goalie_bands[(t, i, 'under 5 ft')][0]}" for i in R_) + " |")
    w("")
    if sha[("both", True)][0]:
        w("## Shot Accuracy as played (SNES)\n")
        w("| Shooter | Maxed: attempts / goals | Not: attempts / goals |\n|---|---|---|")
        for t in teams + ("both",):
            w(f"| {t} | {sha[(t, True)][0]} / {sha[(t, True)][1]} | {sha[(t, False)][0]} / {sha[(t, False)][1]} |")
        w("")
    w("## The slot, defending\n")
    w(f"| Share of time with the puck carried in the end | {a} | {b} |\n|---|---|---|")
    for s_ in SD.ORDER:
        vals = []
        for t in teams:
            all_ = sum(v[0] for (x_, y_), v in slot_states.items() if x_ == t) or 1
            vals.append(f"{100 * slot_states[(t, s_)][0] / all_:.0f}%")
        w(f"| {s_} | {vals[0]} | {vals[1]} |")
    w("")
    w("## Check attempts\n")
    w("| | Attempts | Won the puck | Goal-side before / 1 s after | Shots in 6 s | xG | Goal in 6 s |\n|---|---|---|---|---|---|---|")
    for t in teams:
        for r in CO.rows(checks[t]):
            w(f"| {t} {r[0]} | {r[1]} | {r[2]} | {r[3]} / {r[4]} | {r[5]} | {r[6]:.1f} | {r[7]} |")
        c = check_base[t]
        if c[0]:
            w(f"| {t} no attempt (per moment) | {c[0]} | | | {c[1] / c[0]:.2f} | {c[2] / c[0]:.2f} | {100 * c[3] / c[0]:.1f}% |")
    w("")
    for t in teams:
        v = {(e["game"], e["goal_f"]) for e in checks[t] if e["goal"] and e["result"] != "hit" and not e["late"]}
        w(f"- {t}: {len(v)} goals against within 6 s of a miss (bursts under 1 s before the shot not counted).")
    w("")
    w("## Players\n")
    for t in teams:
        w(f"**{t}**: " + "; ".join(f"{nm.split()[-1]} {c['g']}G {c['a']}A, {c['att']} att, {c['checks']} chk, {c['take']} take, {c['give']} give, {c['hitsTaken']} hit" for nm, c in sorted(players[t].items(), key=lambda kv: -(kv[1]['g'] + kv[1]['a'] + kv[1]['att'] / 100)) if not c["goalie"] and (c["att"] or c["g"] or c["a"] or c["checks"] > 3)) + ".\n")
    w("## The goals\n")
    L += game_lines
    out = Path("reports") / f"set_{a}-{b}_{games[0][:10]}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
