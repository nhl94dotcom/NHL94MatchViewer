"""The scripted bot's one-timers and passes across the slot, against people's (2026-11-13, the user: after the BOS-CHI
series, where all seven of the user's one-timer goals came from a pass to a receiver open in the slot).

Groups, from match files already recorded (no new runs):
  bot       the bot's side (home) in runs/cmp_v68 (version 68, bot_compare's games against the computer)
  computer  the computer's side in those games
  people    each side with a person in the recorded Genesis games with a person on both sides (<home>/matches;
            games the helper recorded against the bot left out: tools/bot_games marks them)
Per 15 minutes of game clock (season.clock_ticks): goals; one-timers tried (shotList kind "one-timer"), their goals and
xG, and the game's failed one-timers (C pressed for one, no shot); passes across the slot as coach_report.py counts
them (a person's pass in the attacking zone crossing the middle, 40+ across, ending within 90 of the goal line):
tried, completed, and a shot by the team within 3 s of a completed one (its xG); and how often a completed one became a
one-timer (the next shot within 3 s a one-timer). For people and the computer the passes are every pass (the computer
has no person; for people only the person's own passes count in coach_report, here every pass of the team, the same
for all three groups so they compare).

python analysis/bot_onetimers.py [BOT_RUN_FOLDER]   (default runs/cmp_v68)"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
RUNS = Path.home() / "NHL94_scoring_map" / "runs"


def attacks_up(m, f, team):
    """Home attacks up in periods 1 and 3 (and overtime)."""
    up = m["period"][f] % 2 == 0
    return up if team == 0 else not up


def side_stats(m, team):
    c = defaultdict(float)
    ticks = sum(season.clock_ticks(m))
    c["minutes"] = ticks / 60
    t = m["t"]
    shots = sorted((s for s in m.get("shotList", []) if s["team"] == team), key=lambda s: s["f"])
    c["goals"] = sum(1 for g in m.get("goals", []) if g["team"] == team)
    for s in shots:
        if s.get("kind") == "one-timer":
            c["ot"] += 1
            c["ot_goals"] += s.get("result") == "goal"
            c["ot_xg"] += s.get("xg") or 0
            ny = 268 if attacks_up(m, s["f"], team) else -268
            c["ot_dist"] += math.hypot(s["x"], ny - s["y"]) / 3
    c["ot_failed"] = sum(1 for x in m.get("failedOneTimers", []) if x["team"] == team)
    for p in m.get("passes", []):
        if p["team"] != team or p.get("result") == "pass shot" or p.get("zone") != "att":
            continue
        ny = 268 if attacks_up(m, p["f"], team) else -268
        if not (p["x0"] * p["x1"] < 0 and abs(p["x1"] - p["x0"]) >= 40 and abs(ny - p["y1"]) < 90):
            continue
        ok = p["result"] in ("completed", "one-timer")
        c["across"] += 1
        c["across_ok"] += ok
        if ok:
            nxt = next((s for s in shots if 0 < t[s["f"]] - t[p["f"]] <= 3000), None)
            if nxt:
                c["across_shot"] += 1
                c["across_xg"] += nxt.get("xg") or 0
                c["across_ot"] += nxt.get("kind") == "one-timer"
                c["across_goal"] += nxt.get("result") == "goal"
    return c


def people_games():
    out = []
    for f in sorted((HOME / "matches").glob("*.js")):
        if f.name == "season.js":
            continue
        summ = f.with_name(f.name[:-3] + ".summary.json")
        meta = json.loads(summ.read_text(encoding="utf-8")) if summ.exists() else {}
        if meta.get("system", "genesis") != "genesis" or meta.get("bot"):
            continue
        try:
            m = season.load_match(f)
        except Exception:
            continue
        if m.get("system", "genesis") != "genesis":
            continue
        home = any(v & 0x3F for v in m["ctrl"][::30])
        away = any(v & 0xFC0 for v in m["ctrl"][::30])
        if home and away:
            out.append(m)
    return out


def total(rows):
    s = defaultdict(float)
    for c in rows:
        for k, v in c.items():
            s[k] += v
    return s


def main():
    run = Path(sys.argv[1]) if len(sys.argv) > 1 else RUNS / "cmp_v68"
    bot, cpu = [], []
    for f in sorted((run / "matches").glob("*.js")):
        m = season.load_match(f)
        bot.append(side_stats(m, 0))
        cpu.append(side_stats(m, 1))
    ppl = [side_stats(m, t) for m in people_games() for t in (0, 1)]
    label = "bot (" + run.name.replace("cmp_", "") + ")"
    groups = [(label, bot), ("computer", cpu), ("people", ppl)]
    print(f"Side-games: bot {len(bot)}, computer {len(cpu)}, people {len(ppl)}. Per 15 game minutes unless marked.\n")
    print("| | " + " | ".join(n for n, _ in groups) + " |\n|---|" + "---|" * len(groups))
    rows = [
        ("goals", lambda s: s["goals"]),
        ("one-timers tried", lambda s: s["ot"]),
        ("one-timer goals", lambda s: s["ot_goals"]),
        ("failed one-timers (C, no shot)", lambda s: s["ot_failed"]),
        ("passes across the slot", lambda s: s["across"]),
        ("... completed", lambda s: s["across_ok"]),
        ("... a shot within 3 s", lambda s: s["across_shot"]),
        ("... that shot a one-timer", lambda s: s["across_ot"]),
        ("... a goal", lambda s: s["across_goal"]),
    ]
    T = {n: total(g) for n, g in groups}
    for label, fn in rows:
        print(f"| {label} | " + " | ".join(f"{15 * fn(T[n]) / max(T[n]['minutes'], 1):.2f}" for n, _ in groups) + " |")
    shares = [
        ("one-timer goals, share of goals", lambda s: s["ot_goals"] / max(s["goals"], 1)),
        ("one-timers: goals per try", lambda s: s["ot_goals"] / max(s["ot"], 1)),
        ("one-timers: xG per try", lambda s: s["ot_xg"] / max(s["ot"], 1)),
        ("one-timers: distance (ft, mean)", lambda s: s["ot_dist"] / max(s["ot"], 1)),
        ("across the slot: completed share", lambda s: s["across_ok"] / max(s["across"], 1)),
        ("across, completed: shot within 3 s", lambda s: s["across_shot"] / max(s["across_ok"], 1)),
        ("across, the shot's xG (mean)", lambda s: s["across_xg"] / max(s["across_shot"], 1)),
    ]
    for label, fn in shares:
        fmt = (lambda v: f"{v:.2f}") if "xG" in label else (lambda v: f"{v:.1f}") if "ft" in label else (lambda v: f"{100 * v:.0f}%")
        print(f"| {label} | " + " | ".join(fmt(fn(T[n])) for n, _ in groups) + " |")
    print("\nMinutes of game clock: " + ", ".join(f"{n} {T[n]['minutes']:.0f}" for n, _ in groups))


if __name__ == "__main__":
    main()
