"""Goals from mistakes: what started each goal (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 8: "most goals at the top
level come from a mental error").

The recorded games with a person on each side (both systems). Each goal, matched to its shot, gets every cause the
recording shows (a goal can have several), and one primary cause, the first of:
1. a giveaway by the scored-on team (turnovers: kind giveaway: a pass picked off, the puck lost on its own) within
   12.5 game s (5 s real) before the goal, in its own zone or elsewhere;
2. the puck taken from them (a takeaway: a check, a poke, a hook ...) within the same window: forced, not their error;
3. an odd-man rush (a carried or passed entry with more attackers than defenders back) that the goal came out of;
4. the shooter left open: no defending skater within 30 (about 10 ft) of him at the release;
5. the goalie 5+ ft (15) off the shot line at the release;
6. a rebound;
7. a power play;
8. off a faceoff (the shot list's origin);
9. none of these: a set play, beating a man, a good shot.

python analysis/goal_causes.py"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end  # noqa: E402
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
ORDER = ["own-zone giveaway", "giveaway elsewhere", "takeaway (forced)", "odd-man rush", "shooter left open",
         "goalie off the line", "rebound", "power play", "off a faceoff", "none of these"]


def main():
    primary = defaultdict(Counter)
    every = defaultdict(Counter)
    n = Counter()
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        if not (m.get("pad") and m.get("pad2") and {m.get("padTeam"), m.get("pad2Team")} == {0, 1}):
            continue
        sysn = m.get("system", "genesis")
        t, pos, role = m["t"], m["pos"], m["role"]
        shots = [s for s in m.get("shotList", []) if s.get("team") in (0, 1)]
        for g in m.get("goals", []):
            team, opp = g["team"], 1 - g["team"]
            sh = min((s for s in shots if s["team"] == team and s["result"] == "goal" and 0 <= t[g["f"]] - t[s["f"]] <= 2000),
                     key=lambda s: t[g["f"]] - t[s["f"]], default=None)
            causes = set()
            for tv in m.get("turnovers", []):
                if tv["from"] != opp or not 0 <= t[g["f"]] - t[tv["f"]] <= 5000:
                    continue
                if tv["kind"] == "giveaway":
                    e = own_end(m, tv["f"], opp)
                    causes.add("own-zone giveaway" if tv["y"] * e >= 89 else "giveaway elsewhere")
                elif tv["kind"] == "takeaway":
                    causes.add("takeaway (forced)")
            for en in m.get("zoneEntries", []):
                if en["team"] == team and en["kind"] in ("carried", "passed") and en.get("odd") and en["odd"][0] >= 2 \
                        and en["odd"][0] > en["odd"][1] and en["f"] <= g["f"] <= en.get("end", en["f"]) + 60:
                    causes.add("odd-man rush")
            if sh:
                f = sh["f"]
                k = next((k for k in range(team * 6, team * 6 + 6) if role[f * 12 + k] in "12345"
                          and m["roster"][f * 12 + k] == "0123456789abcdefghijklmnopqrstuvwxyz"[sh["idx"]]), None)
                if k is not None:
                    x, y = pos[(f * 12 + k) * 2], pos[(f * 12 + k) * 2 + 1]
                    near = min((math.hypot(pos[(f * 12 + d) * 2] - x, pos[(f * 12 + d) * 2 + 1] - y)
                                for d in range(opp * 6, opp * 6 + 6) if role[f * 12 + d] in "12345"), default=999)
                    if near > 30:
                        causes.add("shooter left open")
                if sh.get("gOff") is not None and sh["gOff"] >= 15:
                    causes.add("goalie off the line")
                if sh.get("rebound"):
                    causes.add("rebound")
                if sh.get("origin") == "faceoff":
                    causes.add("off a faceoff")
            if "PPG" in g.get("kinds", []) or g.get("strength") in ("PPG", "PP2"):
                causes.add("power play")
            n[sysn] += 1
            first = next((c for c in ORDER if c in causes), "none of these")
            primary[sysn][first] += 1
            for c in causes or {"none of these"}:
                every[sysn][c] += 1
    for sysn in sorted(n):
        print(f"{sysn.upper()}: {n[sysn]} goals (games with a person on each side)")
        print("   cause            primary   any")
        for c in ORDER:
            print(f"   {c:22s} {primary[sysn][c]:4d} ({primary[sysn][c] / n[sysn]:3.0%})  {every[sysn][c]:4d}")


if __name__ == "__main__":
    main()
