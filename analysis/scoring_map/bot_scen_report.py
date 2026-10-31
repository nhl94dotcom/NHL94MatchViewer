"""Compare bot versions over the same real situations (bot_scenario.py): python bot_scen_report.py RUN V1 V2 ...
Per version: goals, shots, held, lost, stoppages, time-outs, as counts and rates with their standard error. For each
pair against the first version: the situations only one of the two scored from (the difference that counts when both
played the same situations with the same seed), and the goal-rate difference with its standard error from those."""
import json
import math
import sys
from collections import Counter

from paths import RUNS


def load(run, v):
    return {r["i"]: r for r in map(json.loads, open(RUNS / run / f"scen_{v}.jsonl"))}


def main():
    run, vs = sys.argv[1], sys.argv[2:]
    data = {v: load(run, v) for v in vs}
    common = set.intersection(*(set(d) for d in data.values()))
    n = len(common)
    print(f"{n} situations played by every version")
    for v in vs:
        rows = [data[v][i] for i in common]
        c = Counter(r["res"] for r in rows)
        g = c["goal"] / n
        se = math.sqrt(g * (1 - g) / n)
        print(f"version {v:>3}: goals {c['goal']:4} ({100 * g:.1f}% +- {100 * se:.1f}), shots {sum(r['shots'] for r in rows)}, "
              f"held {c['held']}, lost {c['lost']}, stoppage {c['stoppage']}, time {c['time']}, against {c['against']}")
    a = vs[0]
    for b in vs[1:]:
        only_a = sum(data[a][i]["res"] == "goal" and data[b][i]["res"] != "goal" for i in common)
        only_b = sum(data[b][i]["res"] == "goal" and data[a][i]["res"] != "goal" for i in common)
        d = (only_b - only_a) / n
        se = math.sqrt(only_a + only_b) / n
        print(f"{b} against {a}: scored where {a} didn't {only_b}, the other way {only_a}: "
              f"{100 * d:+.1f} points +- {100 * se:.1f}")


if __name__ == "__main__":
    main()
