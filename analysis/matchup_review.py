"""Side-by-side review of a set of games between two teams (2026-10-21, the user: why NYI beat BOS three times).
For each game: the team numbers from the season summaries, then every goal with how it was made, from the match file.
python analysis/matchup_review.py <TEAM> <match name or path> ...   (matches/ or Documents/NHL94 Viewer/matches)"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402

DIRS = [Path("matches"), Path(os.path.expanduser("~/Documents/NHL94 Viewer/matches"))]


def find(name):
    for d in DIRS:
        if (d / f"{name}.js").exists():
            return d / f"{name}.js", d / f"{name}.summary.json"
    raise FileNotFoundError(name)


def mmss(s):
    return f"{int(s) // 60}:{int(s) % 60:02d}"


def main():
    me = sys.argv[1]
    for name in sys.argv[2:]:
        mp, sp = find(name)
        s = json.load(open(sp))
        m = json.loads(load_js_object(mp))
        ab = s["abbr"]
        order = [ab.index(me), 1 - ab.index(me)]
        print(f"\n=== {name}: {ab[0]} {s['score'][0]}-{s['score'][1]} {ab[1]} (home first), {mmss(s['seconds'])} played")
        rows = []

        def row(label, fn):
            rows.append((label, [fn(s["teams"][i], i) for i in order]))
        row("goals", lambda t, i: t["gf"])
        row("shots on goal", lambda t, i: t["sog"])
        row("attempts", lambda t, i: t["att"])
        row("xG (goals from those)", lambda t, i: f"{t['xg'][0]:.1f} ({t['xg'][1]})" if t.get("xg") else "-")
        row("high-danger att / goals", lambda t, i: f"{t['hd'][0]} / {t['hd'][1]}" if t.get("hd") else "-")
        row("one-timers tried / goals", lambda t, i: f"{t['oneTimerTried']} / {t['oneTimerGoals']}")
        row("rebound goals / att", lambda t, i: f"{t['reb'][0]} / {t['reb'][2]}" if t.get("reb") else "-")
        row("possession att/neu/def (s)", lambda t, i: "/".join(str(v) for v in t["possZones"]))
        row("attack-zone time (s)", lambda t, i: t["attackZone"])
        row("zone entries (carried/passed/dumped) -> shot", lambda t, i: f"{t['entries'][0]} ({t['entries'][1]}/{t['entries'][2]}/{t['entries'][3]}) -> {t['entries'][4]}")
        row("odd-man rushes", lambda t, i: t["oddMan"][0] if t.get("oddMan") else "-")
        row("giveaways / takeaways", lambda t, i: f"{t['give']} / {t['take']}")
        row("turnovers -> shot against", lambda t, i: t["toShot"][0] if t.get("toShot") else "-")
        row("checks (person / cpu) big", lambda t, i: f"{t['checks']} ({t['persHits'][0]}/{t['checks'] - t['persHits'][0]}) {t['bigHits']}")
        row("checks -> puck won", lambda t, i: t.get("chkGain"))
        row("pucks lost on contact / on goalie", lambda t, i: f"{t['bumped']} / {t['onGoalie']}")
        row("passes made / tried, bobbled", lambda t, i: f"{t['passMade']} / {t['passTried']}, {t['bobbled']}")
        row("faceoffs won", lambda t, i: f"{t['fow']} / {t['fo']}")
        row("PP goals / tries, penalties", lambda t, i: f"{t['ppg']} / {t['ppTries']}, {t['pen']}")
        row("breakaways (goals)", lambda t, i: f"{t['breakTried']} ({t['breakGoals']})")
        row("pokes (took it)", lambda t, i: f"{t['habits']['pokes']} ({t['habits']['pokeTakeaways']})" if t.get("habits") else "-")
        row("bursts / C presses / B presses", lambda t, i: f"{t['habits']['bursts']} / {t['habits']['presses']['C']} / {t['habits']['presses']['B']}" if t.get("habits") else "-")
        row("goalie by person (s)", lambda t, i: t["habits"]["goalieSeconds"] if t.get("habits") else "-")
        row("deserve to win", lambda t, i: f"{100 * (t['dtw'][0] + t['dtw'][1]):.0f}%" if t.get("dtw") else "-")
        w = max(len(r[0]) for r in rows)
        print(f"{'':{w}}  {ab[order[0]]:>16} {ab[order[1]]:>16}")
        for label, v in rows:
            print(f"{label:{w}}  {str(v[0]):>16} {str(v[1]):>16}")
        # goals
        shots = {sh["f"]: sh for sh in m.get("shotList", []) if sh["result"] == "goal"}
        for g in m["goals"]:
            team = g["team"]
            sc = m["rosters"][team][g["scorer"]]["name"] if g.get("scorer", -1) >= 0 else "?"
            sh = min((sh for sh in m.get("shotList", []) if sh["result"] == "goal" and sh["team"] == team and abs(sh["f"] - g["f"]) < 200),
                     key=lambda sh: abs(sh["f"] - g["f"]), default=None)
            extra = ""
            if sh:
                yg = 264 if sh["y"] > 0 else -264
                extra = (f"{sh['kind']}/{sh.get('type')}, {math.hypot(sh['x'], yg - sh['y']):.0f} out, xG {sh.get('xg', '-')}, "
                         f"goalie {sh.get('gctl')}, {sh.get('origin')}, danger {sh.get('danger')}")
            print(f"   P{g['period'] + 1} {mmss(g['clock'])} {ab[team]} {sc}: {', '.join(g.get('kinds', []))} | {extra}")


if __name__ == "__main__":
    main()
