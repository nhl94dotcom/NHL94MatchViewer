"""The press-or-sit-back runs (posture_run.py, snes_posture_run.py) as tables: for each attack and defender posture,
over both nets, both hands and the lanes, per rush: goals (each shot's goal rate over its release seeds, summed),
shots, the puck lost before a shot (taken, or knocked loose and not recovered), where the shot came from (median
distance out), and the defender's distance from the shooter at the release. 90% ranges from resampling the rushes.
python posture_report.py RUN   (reads paths.RUNS / RUN / posture_full.jsonl and snes_posture_full.jsonl)"""
import json
import random
import statistics
import sys

from paths import RUNS
from posture_run import POSTURES

ATTACKS = ("solo", "slot", "deke", "2on1")


def rows(path):
    out = {}
    if not path.exists():
        return out
    for line in open(path):
        d = json.loads(line)
        out.setdefault(d["attack"], {}).setdefault(d["posture"], []).extend(d["moments"])
    return out


def rng90(values, rnd, n=1000):
    if not values:
        return None, None
    means = sorted(sum(rnd.choice(values) for _ in values) / len(values) for _ in range(n))
    return means[int(0.05 * n)], means[int(0.95 * n)]


def table(name, data):
    rnd = random.Random(1)
    print(f"\n{name}")
    print(f"{'attack':6} {'posture':10} {'rushes':>6} {'goals/rush':>10} {'90% range':>13} {'shot':>5} {'lost':>5} "
          f"{'out':>5} {'def':>5}")
    for attack in ATTACKS:
        for posture in POSTURES:
            ms = data.get(attack, {}).get(posture)
            if not ms:
                continue
            g = [m[1] if m[0] == "shot" else 0.0 for m in ms]
            lo, hi = rng90(g, rnd)
            shots = [m for m in ms if m[0] == "shot"]
            lost = sum(m[0] in ("lost", "loose") for m in ms)
            out = statistics.median(m[3] for m in shots) if shots else float("nan")
            dd = [m[5] for m in shots if m[5] is not None]
            print(f"{attack:6} {posture:10} {len(ms):6} {sum(g) / len(ms):10.3f} {lo:6.3f}-{hi:.3f} "
                  f"{len(shots) / len(ms):5.0%} {lost / len(ms):5.0%} {out:5.0f} "
                  f"{statistics.median(dd) if dd else float('nan'):5.0f}")


def main():
    run = RUNS / sys.argv[1]
    table("Genesis", rows(run / "posture_full.jsonl"))
    table("SNES", rows(run / "snes_posture_full.jsonl"))


if __name__ == "__main__":
    main()
