"""The user's games against the scripted bot (2026-11-12): every game the season summaries mark as played against it
(summary `bot`: tools/bot_games.py, from analysis/scoring_map/bot_live.py's session log), Genesis. Per game the score,
teams and version; then per side-game, side by side: the bot, the user in those games, and the coaches rated 80%+
against an average coach in the people's recordings (recorded_coaches.py; people on both sides):
- goals, shots, ordinary shots' xG a shot and share scored, slapshot share overall and by the shooter's roster Shot
  Power, one-timers tried and scored, shots by distance out from the goal line;
- passes (the game's counters: tried, completed), the converter's intercepted share;
- knockdowns by the controlled skater: thrown checks, plain contact, after a B press (a poke), on / off the carrier;
- penalties and minutes; attack-zone time; breakaways.

--test FOLDER: bot_record.py's games in FOLDER as if played against the bot (the bot Home, the computer as "you"), to
check the report before there are real games.

python analysis/bot_games_report.py [--version N] [--test FOLDER]"""
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis"))
from export_match import STAT_FIELDS  # noqa: E402
from recorded_coaches import ratings  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
SF = {k: STAT_FIELDS.index(k) for k in ("goals", "shots", "passTried", "passMade", "checks", "pim", "attackZone",
                                        "oneTimerTried", "oneTimerGoals", "breakTried") if k in STAT_FIELDS}


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def side(m, team):
    last = m["stats"]["home" if team == 0 else "away"][-1]
    r = {k: last[i] for k, i in SF.items()}
    pad = m.get("pad") if m.get("padTeam", -1) == team else m.get("pad2") if m.get("pad2Team", -1) == team else None
    t = m["t"]
    shots = [s for s in m.get("shotList", []) if s["team"] == team and s.get("kind") == "shot"]
    r["ordinary shots"] = len(shots)
    r["_xg"] = sum(s.get("xg") or 0 for s in shots)
    r["_scored"] = sum(s.get("result") == "goal" for s in shots)
    r["_slap"] = sum(s.get("type") == "slapshot" for s in shots)
    ros = m["rosters"][team]
    r["_byshp"] = Counter()
    r["_slapbyshp"] = Counter()
    for s in shots:
        if 0 <= s["idx"] < len(ros) and not ros[s["idx"]]["g"]:
            shp = ros[s["idx"]]["a"][5]
            r["_byshp"][shp] += 1
            r["_slapbyshp"][shp] += s.get("type") == "slapshot"
    for lo, hi in ((0, 40), (40, 80), (80, 130), (130, 400)):
        r[f"shots {lo}-{hi} out"] = sum(lo <= 264 - abs(s["y"]) < hi for s in shots)
    ot = [s for s in m.get("shotList", []) if s["team"] == team and s.get("kind") == "one-timer"]
    r["one-timers (shots)"] = len(ot)
    r["one-timer goals"] = sum(s.get("result") == "goal" for s in ot)
    ps = [p for p in m.get("passes", []) if p["team"] == team]
    r["_passes"] = len(ps)
    r["_intercepted"] = sum(p["result"] == "intercepted" for p in ps)
    me = [h for h in m.get("hits", []) if h["team"] == team and h.get("human") and h.get("outcome") == "knocked down"]
    r["knockdowns, controlled"] = len(me)
    r["  thrown checks"] = sum(h.get("how") != "check" for h in me)
    r["  plain contact"] = sum(h.get("how") == "check" for h in me)
    r["  on the carrier"] = sum(bool(h.get("onCarrier")) for h in me)
    pokes = 0
    if pad:
        for h in me:
            f = h["f"]
            win = [q for q in range(max(1, f - 120), f + 1) if t[f] - t[q] <= 1500]
            if not any(pad[q] & 32 and not pad[q - 1] & 32 for q in win) and any(pad[q] & 16 and not pad[q - 1] & 16 for q in win):
                pokes += 1
    r["  after a poke (B)"] = pokes
    r["knockdowns, teammates"] = sum(1 for h in m.get("hits", []) if h["team"] == team and not h.get("human")
                                     and h.get("outcome") == "knocked down")
    r["penalties"] = sum(1 for p in m.get("penalties", []) if p["team"] == team)
    return r


def table(groups):
    names = list(groups)
    keys = [k for k in next(iter(groups.values()))[0] if not k.startswith("_")]
    head = "| Per game | " + " | ".join(f"{n} ({len(groups[n])})" for n in names) + " |"
    lines = [head, "|---|" + "---|" * len(names)]
    mean = lambda rows, k: st.mean(r[k] for r in rows) if rows else float("nan")
    for k in keys:
        lines.append(f"| {k} | " + " | ".join(f"{mean(groups[n], k):.1f}" for n in names) + " |")
    def pct(rows, a, b):
        sa, sb = sum(r[a] for r in rows), sum(r[b] for r in rows)
        return f"{100 * sa / sb:.0f}%" if sb else "-"
    lines.append("| passes completed (game's count) | " + " | ".join(pct(groups[n], "passMade", "passTried") for n in names) + " |")
    lines.append("| passes intercepted | " + " | ".join(pct(groups[n], "_intercepted", "_passes") for n in names) + " |")
    lines.append("| ordinary shots scored | " + " | ".join(pct(groups[n], "_scored", "ordinary shots") for n in names) + " |")
    lines.append("| xG an ordinary shot | " + " | ".join(
        f"{sum(r['_xg'] for r in groups[n]) / max(1, sum(r['ordinary shots'] for r in groups[n])):.3f}" for n in names) + " |")
    lines.append("| slapshots of ordinary shots | " + " | ".join(pct(groups[n], "_slap", "ordinary shots") for n in names) + " |")
    for shp in range(2, 7):
        cells = []
        for n in names:
            a = sum(r["_byshp"][shp] for r in groups[n])
            b = sum(r["_slapbyshp"][shp] for r in groups[n])
            cells.append(f"{100 * b / a:.0f}% of {a}" if a else "-")
        lines.append(f"| slapshots, Shot Power {shp} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    want = int(sys.argv[sys.argv.index("--version") + 1]) if "--version" in sys.argv else None
    bot, you, games = [], [], []
    if "--test" in sys.argv:
        for f in sorted(Path(sys.argv[sys.argv.index("--test") + 1]).glob("bot_*.js")):
            m = load(f)
            bot.append(side(m, 0))
            you.append(side(m, 1))
            games.append(f"{f.stem} (test: bot_record's game, the computer as 'you')")
    for f in ([] if "--test" in sys.argv else sorted(HOME.glob("*.summary.json"))):
        d = json.loads(f.read_text())
        b = d.get("bot")
        if not b or d.get("system") != "genesis" or (want is not None and b.get("version") != want):
            continue
        m = load(f.with_name(f.name.replace(".summary.json", ".js")))
        bs = b["side"]
        bot.append(side(m, bs))
        you.append(side(m, 1 - bs))
        games.append(f"{f.name[:15]}  v{b.get('version')}  {d['names'][0]} {d['score'][0]}-{d['score'][1]} {d['names'][1]}"
                     f"  (bot {'Home' if bs == 0 else 'Away'}{', ' + str(round(d.get('seconds') or 0)) + ' s' if d.get('seconds') else ''}"
                     f"{'' if d.get('finished') else ', unfinished'})")
    if not games:
        print("no games against the bot yet (bot_live.py play logs its sessions; the season summaries mark the games)")
        return
    rate = ratings("genesis")
    strong = []
    for f in sorted(HOME.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or d.get("bot") or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        stem = f.name.replace(".summary.json", "")
        rs = rate.get(stem, [None, None])
        m = None
        for team in (0, 1):
            if rs[team] is not None and rs[team] >= 80:
                m = m or load(f.with_name(stem + ".js"))
                strong.append(side(m, team))
    print("Games against the bot:")
    for g in games:
        print("  " + g)
    won = sum(1 for r, y in zip(bot, you) if r["goals"] > y["goals"])
    print(f"\nThe bot won {won} of {len(games)}; goals {sum(r['goals'] for r in bot)}-{sum(y['goals'] for y in you)}\n")
    print(table({"the bot": bot, "you": you, "strong coaches": strong}))


if __name__ == "__main__":
    main()
