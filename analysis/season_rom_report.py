"""A ROM's computer games summed up for a roster check (2026-11-22, NOSE4Web's "Real NHL season" ROMs: a real
season's players rated from that season's stats; does it play like that season?). The games are cvc_record.py's
(computer against computer, recorded and converted as people's games are), one folder a ROM.

For each folder:
- every game: the teams, score, shots on goal;
- oddities in play: a roster place past the team's roster, a skater on a goalie's roster place or a goalie's on a
  skater's, two records on one roster place, a team with no goalie; the players who took the ice (line changes are off
  in these games, so a team plays its first line, its power-play and penalty-kill units and its starting goalie);
- each team: games, goals for and against, shots, and its skaters who played, by points: goals, assists, the ROM's
  overall rating and where that ranks among the team's skaters (1 = the team's best);
- the defencemen (those who played LD / RD): attempts, shots on goal, xG, goals and assists a game, with their overall
  rating and Offensive Awareness (for one defenceman against the others);
- across the folder: how the top-rated skater on the ice did against his team mates (was the team's leading scorer
  one of its three best-rated who played?), the points of the players by rating rank, and the goalies: shots on goal
  faced, goals, save %.

python analysis/season_rom_report.py FOLDER [FOLDER ...]   (each holding matches/*.js)"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def load(path):
    t = Path(path).read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def report(folder):
    files = sorted(Path(folder, "matches").glob("*.js"))
    files = [f for f in files if not f.name.startswith("season")]
    print(f"\n=== {Path(folder).name}: {len(files)} games")
    team = defaultdict(lambda: dict(gp=0, gf=0, ga=0, sf=0, sa=0, w=0, players=defaultdict(lambda: [0, 0]), on=Counter(),
                                    roster=None, goalie=Counter(), dmen=Counter(), shots=defaultdict(lambda: [0, 0, 0.0])))
    odd = Counter()
    goalies = defaultdict(lambda: [0, 0])
    for f in files:
        m = load(f)
        n = len(m["t"])
        names = (m["team1"], m["team2"])
        sc, sh = m["score"][-2:], m["shots"][-2:]
        print(f"  {f.stem}: {names[0]} {sc[0]} - {sc[1]} {names[1]}   shots {sh[0]} - {sh[1]}   periods {max(m['period']) + 1}")
        role, ros = m["role"], m["roster"]
        for side in (0, 1):
            T = team[names[side]]
            T["roster"] = m["rosters"][side]
            T["gp"] += 1
            T["gf"] += sc[side]
            T["ga"] += sc[1 - side]
            T["sf"] += sh[side]
            T["sa"] += sh[1 - side]
            T["w"] += sc[side] > sc[1 - side]
            size = len(m["rosters"][side])
            for i in range(0, n, 30):
                seen = {}
                has_goalie = False
                for k in range(side * 6, side * 6 + 6):
                    r, c = role[i * 12 + k], ros[i * 12 + k]
                    if r == "x" or c not in DIGITS:
                        continue
                    idx = DIGITS.index(c)
                    if idx >= size:
                        odd["a roster place past the roster"] += 1
                        continue
                    p = m["rosters"][side][idx]
                    if r == "0":
                        has_goalie = True
                        T["goalie"][idx] += 1
                        if not p.get("g"):
                            odd["a skater in goal"] += 1
                    else:
                        T["on"][idx] += 1
                        if r in "12":
                            T["dmen"][idx] += 1
                        if p.get("g"):
                            odd["a goalie skating"] += 1
                    if idx in seen and seen[idx] != "0" and r != "0":
                        odd["two skaters on one roster place"] += 1
                    seen[idx] = r
                if not has_goalie and m["clock"][i] > 60:
                    odd["no goalie on the ice (over a minute left)"] += 1
        for g in m.get("goals", []):
            if g.get("team") not in (0, 1):
                continue
            T = team[names[g["team"]]]
            T["players"][g["scorer"]][0] += 1
            for a in g.get("assists", []):
                T["players"][a[0]][1] += 1
        for s in m.get("shotList", []):
            if s.get("team") in (0, 1) and s.get("idx") is not None and s.get("kind") in ("shot", "one-timer", "pass shot"):
                v = team[names[s["team"]]]["shots"][s["idx"]]
                v[0] += 1
                v[1] += bool(s.get("counted"))
                v[2] += s.get("xg") or 0.0
        for s in m.get("shotList", []):
            if s.get("counted") and s.get("result") in ("save", "goal") and s.get("goalie") is not None:
                key = (names[1 - s["team"]], s["goalie"])
                goalies[key][0] += 1
                goalies[key][1] += s["result"] == "goal"
    print("  oddities in play:", dict(odd) if odd else "none")
    lead_top3 = lead_n = 0
    by_rank = defaultdict(lambda: [0, 0])
    for name, T in sorted(team.items()):
        R = T["roster"]
        skaters = sorted([i for i, p in enumerate(R) if not p.get("g")], key=lambda i: -R[i].get("ovr", 0))
        rank = {i: k + 1 for k, i in enumerate(skaters)}
        played = [i for i, c in T["on"].most_common() if not R[i].get("g")]
        print(f"  {name}: {T['gp']} games, {T['w']} won, goals {T['gf']} - {T['ga']}, shots {T['sf']} - {T['sa']}")
        best_played = sorted(played, key=lambda i: rank[i])[:3]
        print("    best-rated skaters:", ", ".join(f"{R[i]['name']} {R[i].get('ovr')}" + ("" if i in played else " (did not play)")
                                                   for i in skaters[:5]))
        rows = sorted(played, key=lambda i: -(T["players"][i][0] + T["players"][i][1]))
        for i in rows[:6]:
            g, a = T["players"][i]
            print(f"    {R[i]['name']:22s} {g} G {a} A   rated {R[i].get('ovr')} (team rank {rank[i]})   on the ice {T['on'][i] * 30 / 60 / 60:.1f} min (real)")
        gk = [i for i in T["players"] if R[i].get("g") and sum(T["players"][i])]
        for i in gk:
            print(f"    goalie {R[i]['name']} has {T['players'][i][1]} assists")
        if rows and sum(T["players"][rows[0]]):
            lead_n += 1
            lead_top3 += rows[0] in best_played
        for k, i in enumerate(sorted(played, key=lambda i: rank[i])):
            by_rank[k][0] += sum(T["players"][i])
            by_rank[k][1] += T["gp"]
        for i, c in T["goalie"].most_common():
            sa, ga = goalies[(name, i)]
            print(f"    in goal: {R[i]['name']} (rated {R[i].get('ovr')}): {sa} shots on goal, {ga} goals" + (f", save % {100 * (sa - ga) / sa:.1f}" if sa else ""))
    print("  defencemen (those on the ice at LD / RD), a game: attempts, shots on goal, xG, goals, assists")
    for name, T in sorted(team.items()):
        R = T["roster"]
        for i, c in T["dmen"].most_common():
            if c * 30 / 60 < 120 or i >= len(R):          # under 2 minutes (real) at the position: a fill-in
                continue
            a, sog, xg = T["shots"][i]
            g, ast = T["players"][i]
            n = T["gp"]
            print(f"    {name[:12]:12s} {R[i]['name']:20s} rated {R[i].get('ovr'):>3}  OfA {R[i]['a'][3] if len(R[i].get('a', [])) > 3 else '?'}   "
                  f"{a / n:.1f} att  {sog / n:.1f} SOG  {xg / n:.2f} xG  {g / n:.2f} G  {ast / n:.2f} A   ({n} games)")
    print(f"  the team's leading scorer was one of its three best-rated skaters who played: {lead_top3} of {lead_n} teams")
    print("  points a game by rating rank among the skaters who played (1 = best):",
          ", ".join(f"{k + 1}: {v[0] / v[1]:.2f}" for k, v in sorted(by_rank.items())[:6] if v[1]))
    sa = sum(v[0] for v in goalies.values())
    ga = sum(v[1] for v in goalies.values())
    g = sum(T["gf"] for T in team.values())
    s = sum(T["sf"] for T in team.values())
    gp = sum(T["gp"] for T in team.values()) / 2
    if gp:
        print(f"  all games: {g / gp:.1f} goals and {s / gp:.1f} shots on goal a game; save % {100 * (s - g) / s:.1f} (the game's counts)"
              + (f"; {100 * (sa - ga) / sa:.1f} on the converter's {sa} shots" if sa else ""))


if __name__ == "__main__":
    for folder in sys.argv[1:]:
        report(folder)
