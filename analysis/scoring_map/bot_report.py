"""Sum up bot_run.py's games: python bot_report.py RUN
The record against the computer, goals and shots on goal a game, and per play: how often the bot started it, how
often it got the shot away, goals from it (a goal within 120 frames of the play's shot) and the rate per shot; the
pucks lost on the way, by the phase the bot was in."""
import json
import sys
from collections import Counter

from paths import RUNS


def main():
    rows = [json.loads(l) for l in open(RUNS / sys.argv[1] / "bot_games.jsonl")]
    n = len(rows)
    w = sum(r["score"][0] > r["score"][1] for r in rows)
    l = sum(r["score"][0] < r["score"][1] for r in rows)
    ot = sum(any(g["period"] >= 3 for g in r["goals"]) for r in rows)
    gf, ga = sum(r["score"][0] for r in rows), sum(r["score"][1] for r in rows)
    sf, sa = sum(r["shots"][0] for r in rows), sum(r["shots"][1] for r in rows)
    print(f"{n} games: won {w}, lost {l}, tied {n - w - l} ({ot} went to overtime)")
    print(f"goals a game {gf / n:.2f} - {ga / n:.2f}; shots on goal {sf / n:.1f} - {sa / n:.1f}; "
          f"goals per shot on goal {100 * gf / max(1, sf):.0f}% - {100 * ga / max(1, sa):.0f}%")
    ev, shots, goals, lost = Counter(), Counter(), Counter(), Counter()
    for r in rows:
        ev.update(r["events"])
        shots.update(r.get("shot_kinds", {}))
        goals.update(g["play"] for g in r["goals"] if g["team"] == 0)
        lost.update(r["lost"])
    print(f"plays started a game: deke {ev['deke start'] / n:.1f} (swung {ev['swing'] / n:.1f}), EA Special {ev['ea start'] / n:.1f}, "
          f"slapshot {ev['slap start'] / n:.1f}, close-in wrist shot {ev['wrist start'] / n:.1f}")
    print(f"  passes for a one-timer {ev['pass start'] / n:.1f} a game (kept by the receiver {ev['pass kept'] / n:.1f})")
    for k in ("deke", "ea", "ea follow", "one-timer", "pass", "wrist", "slap"):
        print(f"  {k:9} shots {shots[k]:4}  goals {goals[k]:3}  ({100 * goals[k] / max(1, shots[k]):.0f}% a shot)")
    print(f"  other goals {goals['other']}  (one-timer: swings that struck the puck, from bot5; pass: the pass for one,"
          f" goals = the pass going in or a deflection; before bot5 one-timer meant the pass)")
    print("pucks lost, by phase: " + ", ".join(f"{k} {v}" for k, v in lost.most_common()))


if __name__ == "__main__":
    main()
