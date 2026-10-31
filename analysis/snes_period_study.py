"""The SNES second period in the recorded games (2026-10-30). The leagues' results show about 5% fewer SNES goals a
shot in period 2 for both teams (LEAGUE_RESULTS, "Game-wide patterns"); the period number itself does nothing to a
standing shot (snes_period_hand_run.py). Here every recorded SNES game (both game folders, each game once) is split
by period: minutes of play, attempts (shots and one-timers), shots on goal, goals, xG, goals against xG, attempts off
the rush, one-timers, completed passes, zone entries and turnovers, per 5 minutes of play, with Home and Away apart.
python analysis/snes_period_study.py"""
import json
from collections import defaultdict
from pathlib import Path

DIRS = [Path.home() / "Documents" / "NHL94 Viewer" / "matches", Path(__file__).resolve().parents[1] / "matches"]


def load(p):
    s = p.read_text(encoding="utf-8")
    return json.loads(s[s.index("=") + 1:].strip().rstrip(";"))


def games():
    seen = set()
    for d in DIRS:
        for f in sorted(d.glob("*.js")):
            if f.stem in seen or f.stem.startswith(("season", "shot_study")):
                continue
            try:
                m = load(f)
            except (ValueError, OSError):
                continue
            if m.get("system") == "snes" and "shotList" in m:      # older files have no event lists
                seen.add(f.stem)
                yield m


def main():
    T = defaultdict(lambda: defaultdict(float))
    n = 0
    for m in games():
        n += 1
        per, t = m["period"], m["t"]
        for i in range(1, len(t)):
            if per[i] == per[i - 1] and per[i] <= 2:
                T[per[i]]["secs"] += (t[i] - t[i - 1]) / 1000          # t in milliseconds
        for s in m["shotList"]:
            p = per[min(s["f"], len(per) - 1)]
            if p > 2:
                continue
            side = "home" if s["team"] == 0 else "away"
            for k in ("all", side):
                c = T[p]
                c[k + " attempts"] += 1
                c[k + " on goal"] += bool(s.get("counted"))
                c[k + " goals"] += s.get("result") == "goal"
                c[k + " xg"] += s.get("xg") or 0
                c[k + " rush"] += s.get("origin") == "rush"
                c[k + " one-timers"] += s.get("kind") == "one-timer"
        for key, name in (("passes", "passes completed"), ("zoneEntries", "zone entries"), ("turnovers", "turnovers")):
            for e in m.get(key, []):
                p = per[min(e["f"], len(per) - 1)]
                if p <= 2 and (key != "passes" or e.get("result") == "completed"):
                    T[p][name] += 1
    print(f"{n} recorded SNES games")
    rows = ["attempts", "on goal", "goals", "xg", "rush", "one-timers"]
    print("Per 5 minutes of play, periods 1 / 2 / 3 (minutes of play in each: "
          + " / ".join(f"{T[p]['secs'] / 60:.0f}" for p in range(3)) + ")")
    for side in ("all", "home", "away"):
        for r in rows:
            vals = [T[p][f"{side} {r}"] / T[p]["secs"] * 300 for p in range(3)]
            print(f"  {side:4} {r:10} " + " / ".join(f"{v:5.2f}" for v in vals))
        g = [T[p][f"{side} goals"] for p in range(3)]
        x = [T[p][f"{side} xg"] for p in range(3)]
        sog = [T[p][f"{side} on goal"] for p in range(3)]
        print(f"  {side:4} goals / xG " + " / ".join(f"{a:.0f}/{b:.1f} ({a / b:.2f})" for a, b in zip(g, x))
              + "; goals per shot on goal " + " / ".join(f"{100 * a / max(1, b):.0f}%" for a, b in zip(g, sog)))
    for r in ("passes completed", "zone entries", "turnovers"):
        print(f"  {r:16} " + " / ".join(f"{T[p][r] / T[p]['secs'] * 300:5.2f}" for p in range(3)))


if __name__ == "__main__":
    main()
