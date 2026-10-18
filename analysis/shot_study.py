"""Shooting and goalie study by system, up / down the screen and home / away (docs/SHOOTING_STUDY.md). Run
analysis/shot_table.py first, from the project folder."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

rows = json.load(open(Path("matches") / "shot_study.json"))  # from analysis/shot_table.py
MPH = 0.015 / (536 / 178) * 3600 / 5280
games = defaultdict(set)
for r in rows:
    games[r["system"]].add(r["game"])


def pct(a, b):
    return f"{a}/{b} ({100 * a / b:.0f}%)" if b else f"{a}/0"


def summary(sel):
    att = len(sel)
    reached = [r for r in sel if r["result"] in ("goal", "save", "post")]
    goals = sum(r["result"] == "goal" for r in sel)
    counted = sum(1 for r in sel if r["counted"])
    unc = sum(1 for r in reached if not r["counted"] and r["result"] != "goal")
    xg = [r["xg"] for r in sel if r["xg"] is not None and r["result"] != "blocked"]
    xg_goals = sum(1 for r in sel if r["xg"] is not None and r["result"] == "goal")
    sp = [r["speed"] * MPH for r in sel if r["speed"]]
    person = [r for r in sel if r["human"] and r["kind"] == "shot" and r["aim"]]
    z = Counter(r["aim"]["z"] for r in person)
    exact = [r for r in person if r["perfect"] is not None and r["dist"] < 200]
    saves = [r for r in sel if r["result"] == "save" and r["after"]]
    a = Counter(r["after"] for r in saves)
    return (f"att {att}, goals {goals} ({100 * goals / max(1, att):.1f}% of attempts), on goal {counted}, uncounted stops {pct(unc, len(reached))}, "
            f"xG {sum(xg):.1f} -> goals {xg_goals}, speed {sum(sp) / max(1, len(sp)):.0f} mph, person aims high/mid/ice "
            f"{z[12]}/{z[6]}/{z[0]}, exact {pct(sum(r['perfect'] for r in exact), len(exact))}, after saves held/rebound/cleared "
            f"{a['held']}/{a['rebound']}/{a['cleared']}")


def section(title):
    print("\n## " + title)


for system in ("genesis", "snes"):
    S = [r for r in rows if r["system"] == system]
    print(f"\n==================== {system.upper()}: {len(S)} shots and one-timers in {len(games[system])} games")
    section("Up / down and home / away")
    for label, test in (("up", lambda r: r["up"]), ("down", lambda r: not r["up"]), ("home", lambda r: r["home"]), ("away", lambda r: not r["home"]),
                        ("home up", lambda r: r["home"] and r["up"]), ("home down", lambda r: r["home"] and not r["up"]),
                        ("away up", lambda r: not r["home"] and r["up"]), ("away down", lambda r: not r["home"] and not r["up"])):
        print(f"{label:9}: " + summary([r for r in S if test(r)]))

    section("1. Exact or scattered (a person's shots from within 200)")
    ex = [r for r in S if r["human"] and r["kind"] == "shot" and r["perfect"] is not None and r["dist"] < 200]
    for lab, v in (("exact", True), ("scattered", False)):
        sel = [r for r in ex if r["perfect"] is v]
        print(f"{lab:9}: goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}, wide {sum(r['result'] == 'wide' for r in sel)}")
    for lab, test in (("up", lambda r: r["up"]), ("down", lambda r: not r["up"]), ("home", lambda r: r["home"]), ("away", lambda r: not r["home"])):
        sel = [r for r in ex if test(r)]
        print(f"   exact {lab:5}: {pct(sum(r['perfect'] for r in sel), len(sel))}, mean working ShA {sum(r['sha'] or 0 for r in sel) / max(1, len(sel)):.1f}")

    if system == "genesis":
        section("2. Forehand or backhand (shots, not one-timers)")
        for h in ("forehand", "backhand"):
            sel = [r for r in S if r["hand"] == h and r["kind"] == "shot"]
            sp = [r["speed"] * MPH for r in sel if r["speed"]]
            print(f"{h:9}: {len(sel)} shots, goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}, {sum(sp) / max(1, len(sp)):.0f} mph, "
                  f"up {sum(r['up'] for r in sel)} / down {sum(not r['up'] for r in sel)}")

    section("3. Speed and goals, by aim height (a person's shots)")
    for zname, z in (("high", 12), ("middle", 6), ("ice", 0)):
        line = []
        for lo, hi in ((0, 50), (50, 65), (65, 80), (80, 200)):
            sel = [r for r in S if r["human"] and r["kind"] == "shot" and r["aim"] and r["aim"]["z"] == z and lo <= r["speed"] * MPH < hi]
            line.append(f"{lo}-{hi if hi < 200 else '+'} mph {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}")
        print(f"{zname:7}: " + ";  ".join(line))

    section("4. What follows a save: held / rebound / cleared / loose")
    for lab, test in (("close (<60)", lambda r: r["dist"] < 60), ("60-120", lambda r: 60 <= r["dist"] < 120), ("far", lambda r: r["dist"] >= 120),
                      ("under 60 mph", lambda r: r["speed"] * MPH < 60), ("60 mph+", lambda r: r["speed"] * MPH >= 60)):
        sel = [r for r in S if r["result"] == "save" and r["after"] and test(r)]
        a = Counter(r["after"] for r in sel)
        print(f"{lab:13}: {len(sel)} saves: held {a['held']}, rebound {a['rebound']}, cleared {a['cleared']}, loose {a['loose']}")
    reb = [r for r in S if r["rebound"]]
    print(f"rebound shots: goals {pct(sum(r['result'] == 'goal' for r in reb), len(reb))}; others {pct(sum(r['result'] == 'goal' for r in S if not r['rebound']), sum(1 for r in S if not r['rebound']))}")

    section("5. The goalie's move and the outcome (shots that reached him)")
    reached = [r for r in S if r["result"] in ("goal", "save", "post") and r["save"]]
    for mv in sorted({r["save"] for r in reached}):
        for who in ("cpu", "human"):
            sel = [r for r in reached if r["save"] == mv and r["gctl"] == who]
            if sel:
                print(f"{mv:10} {who:5}: goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}, not counted {sum(1 for r in sel if r['result'] == 'save' and not r['counted'])}")

    section("6. Strong side or off-wing (a skater's shots from more than 20 off the middle)")
    for lab, test in (("strong side", lambda r: (r["his_x"] > 20) == r["right"]), ("off-wing", lambda r: (r["his_x"] > 20) != r["right"])):
        sel = [r for r in S if abs(r["his_x"]) > 20 and test(r)]
        print(f"{lab:11}: goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}" +
              (f", backhands {sum(r['hand'] == 'backhand' for r in sel)}" if system == "genesis" else ""))

    section("7. One-timers")
    for lab, test in (("up", lambda r: r["up"]), ("down", lambda r: not r["up"]), ("home", lambda r: r["home"]), ("away", lambda r: not r["home"])):
        sel = [r for r in S if r["kind"] == "one-timer" and test(r)]
        print(f"{lab:5}: goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}")

    section("8. Third period, first half and second half (the bonus for a tied or trailing team runs in the first half)")
    for lab, test in (("tied/trailing, 1st half", lambda r: r["score"] <= 0 and r["clock"] > r["length"] / 2),
                      ("tied/trailing, 2nd half", lambda r: r["score"] <= 0 and r["clock"] <= r["length"] / 2),
                      ("leading, 1st half", lambda r: r["score"] > 0 and r["clock"] > r["length"] / 2),
                      ("leading, 2nd half", lambda r: r["score"] > 0 and r["clock"] <= r["length"] / 2)):
        sel = [r for r in S if r["period"] == 2 and test(r)]
        print(f"{lab:24}: {len(sel)} attempts, goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}")

    if system == "genesis":
        section("9. Goalie hot / cold (as played: -3..+2 on the 0-30 scale)")
        for lab, test in (("cold (<0)", lambda h: h < 0), ("even (0)", lambda h: h == 0), ("hot (>0)", lambda h: h > 0)):
            sel = [r for r in S if r["goalie_hc"] is not None and test(r["goalie_hc"]) and r["result"] in ("goal", "save", "post")]
            print(f"{lab:10}: goals against {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}")

    section("10. Score effects")
    for lab, test in (("trailing", lambda r: r["score"] < 0), ("tied", lambda r: r["score"] == 0), ("leading", lambda r: r["score"] > 0)):
        sel = [r for r in S if test(r)]
        print(f"{lab:8}: {len(sel)} attempts, goals {pct(sum(r['result'] == 'goal' for r in sel), len(sel))}, high danger {sum(r['danger'] == 'high' for r in sel)}")

    if system == "snes":
        section("12. Glove saves and uncounted shots")
        for mv in ("glove", "stick", "pad stack", "sprawl", "butterfly", "none"):
            sel = [r for r in S if r["save"] == mv and r["result"] == "save"]
            if sel:
                print(f"{mv:10}: saves {len(sel)}, not counted {sum(not r['counted'] for r in sel)}")
