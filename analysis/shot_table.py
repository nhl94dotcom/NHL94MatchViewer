"""One row per shot or one-timer in every whole recorded game, with what the study needs: system, home / away, up / down
the screen, person or computer, type, forehand / backhand, handedness, side of the ice in the shooter's view, speed,
distance, aim, whether it left the stick exactly at the aim point (a "perfect" shot), working Shot Accuracy, the result,
the goalie's move and what followed the save, score state, period half; whether a person played the shooting team (it
had the controlled-skater marker in most samples). Writes matches/shot_study.json for analysis/shot_study.py, and
matches/shot_study_periods.json: the game seconds each team played in each period and which way it attacked then
(home / away x up / down exposure, so rates can be per 5:00). Run from the project folder: python analysis/shot_table.py"""
import glob
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12
files = {}
for p in glob.glob("matches/*.js") + glob.glob(str(Path.home() / "Documents/NHL94 Viewer/matches/*.js")):
    if p.endswith(".summary.json"):
        continue
    files.setdefault(Path(p).name, p)

rows, periods = [], []
for name, p in sorted(files.items()):
    try:
        m = json.loads(load_js_object(Path(p)))
    except Exception:
        continue
    if "shotList" not in m or not m.get("t") or m["t"][-1] - m["t"][0] < 120000:
        continue
    system = m.get("system", "genesis")
    t, P, N = m["t"], m["puck"], len(m["t"])
    ctrl = m.get("ctrl") or []
    person = [sum(1 for v in ctrl if v & (0x3F << (6 * team))) > len(ctrl) / 2 for team in (0, 1)]
    # each period's game seconds (the clock's fall) and, per team, its direction (most samples' goalie end)
    for per in sorted(set(m["period"])):
        idx = [i for i in range(N) if m["period"][i] == per]
        clocks = [m["clock"][i] for i in idx]
        secs = max(clocks) - min(clocks)
        if per > 3 or secs <= 0:
            continue
        for team in (0, 1):
            ends = [own_end(m, i, team) for i in idx[::25]]
            ups = sum(e == -1 for e in ends)
            downs = sum(e == 1 for e in ends)
            if ups + downs:
                periods.append({"game": name, "system": system, "period": per, "home": team == 0, "up": ups > downs,
                                "person": person[team], "secs": secs})
    work = {}
    for w in m.get("work", []):
        work.setdefault(w[1], []).append(w)

    def record_of(f, team, idx):
        for k in range(team * 6, team * 6 + 6):
            c = m["roster"][f * K + k]
            if c != "x" and int(c, 36) == idx:
                return k
        return None

    def working_sha(f, k):
        best = None
        for w in work.get(k, []):
            if w[0] <= f:
                best = w
        return best[7] if best else None

    for sh in m["shotList"]:
        if sh["kind"] not in ("shot", "one-timer"):
            continue
        f, team = sh["f"], sh["team"]
        end = own_end(m, f, team)
        if end is None:
            continue
        up = end < 0
        sign = 1 if up else -1  # toward the net attacked
        k = record_of(f, team, sh["idx"])
        roster = m["rosters"][team][sh["idx"]] if sh["idx"] >= 0 else None
        right = bool(roster and not roster.get("g") and roster["a"][7] % 2 == 1)
        anim = m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4] if k is not None else ""
        hand = None
        if system == "genesis":
            for q in range(f, max(0, f - 60), -1):  # his last shooting animation at or before the release
                a = m["anim"][(q * K + k) * 4:(q * K + k) * 4 + 4] if k is not None else ""
                if a in ("07fc", "092e"):
                    hand = "forehand" if a == "07fc" else "backhand"
                    break
        x, y = sh["x"], sh["y"]
        yg = sign * 264
        dist = math.hypot(x, yg - y)
        # exactness: project the puck's flight from the release to the aim line and compare with the aim point
        perfect = None
        if sh.get("aim") is not None:
            ax = sh["aim"]["x"] if up else -sh["aim"]["x"]  # the aim in screen x
            for q in range(f + 1, min(N, f + 40)):
                if m["owner"][q] >= 0 or abs(P[3 * q + 1]) > 240:
                    break
                dy = P[3 * q + 1] - P[3 * f + 1]
                if abs(dy) >= 15 and (dy > 0) == up:
                    xc = P[3 * f] + (P[3 * q] - P[3 * f]) * (yg - P[3 * f + 1]) / dy
                    perfect = abs(xc - ax) <= 2
                    break
        # the shooter's side of the ice, in his view: + his right (attacking up, screen right is his right)
        his_x = x if up else -x
        score = m["score"][2 * f + team] - m["score"][2 * f + 1 - team]
        period, clock = m["period"][f], m["clock"][f]
        length = max(m["clock"][q] for q in range(N) if m["period"][q] == period) if period < 3 else 600
        rows.append({
            "game": name, "system": system, "home": team == 0, "up": up, "human": bool(sh.get("human")), "person_team": person[team],
            "kind": sh["kind"], "type": sh.get("type"), "hand": hand, "right": right, "his_x": his_x, "x": x, "y": y,
            "dist": dist, "speed": sh.get("speed", 0), "aim": sh.get("aim"), "perfect": perfect,
            "sha": working_sha(f, k) if k is not None else None, "result": sh["result"], "counted": sh.get("counted"),
            "save": sh.get("save"), "after": sh.get("after"), "gctl": sh.get("gctl"), "rebound": bool(sh.get("rebound")),
            "xg": sh.get("xg"), "danger": sh.get("danger"), "score": score, "period": period, "clock": clock,
            "length": length, "goalie": sh.get("goalie"), "goalie_hc": None,
        })
        g = sh.get("goalie")
        if g is not None and g >= 0:
            gr = m["rosters"][1 - team][g]
            rows[-1]["goalie_hc"] = gr.get("hc") if isinstance(gr.get("hc"), int) else None
            rows[-1]["goalie_name"] = gr["name"]
json.dump(rows, open(Path("matches") / "shot_study.json", "w"))  # matches/ is not in git
json.dump(periods, open(Path("matches") / "shot_study_periods.json", "w"))
print(len(rows), "shots;", sum(r["system"] == "genesis" for r in rows), "Genesis,", sum(r["system"] == "snes" for r in rows), "SNES;",
      len({r["game"] for r in rows}), "games")
