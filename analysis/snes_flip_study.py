"""SNES flips (Y with the puck: a computer-run dump-in, SNES_MECHANICS 6.3) in the recorded games and in the harness
(2026-10-30). Recorded: every match file's `flips` (export_match.split_flips): who flipped (goalie or skater, person
or computer), from where, the target the code picks for that spot (DumpInTarget), where the puck first came down
after its peak, and who had it next (own team, the other team, or nobody within 3 s). Harness:
analysis/scoring_map/snes_flip_run.py's results (where flips from set spots came down, by Passing), if given.
python analysis/snes_flip_study.py [HARNESS_JSONL]"""
import glob
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
TX = [0, -80, 80, -80, 0, 80, 0, 80, -80, -80, 0, 80]          # assdumpin .8: target x
TY = [-105, -115, -115, -180, -215, -180, 105, 115, 115, 180, 215, 180]   # .ytab: target y


def target(x, y, attack_top):
    """DumpInTarget for a skater (screen coordinates): the target index into TX / TY."""
    if attack_top:
        return 10 if y >= 88 else 9 if x < 0 else 11
    return 4 if y < -88 else 3 if x < 0 else 5


def recorded():
    rows = []
    for f in sorted(glob.glob(str(HOME / "*.js"))):
        if f.endswith("season.js"):
            continue
        m = json.loads(load_js_object(Path(f)))
        if m.get("system") != "snes" or not m.get("flips"):
            continue
        t, P, own, N, K = m["t"], m["puck"], m["owner"], len(m["t"]), 12
        pos = m["pos"]
        for fl in m["flips"]:
            r, team = fl["f"], fl["team"]
            k = own[r - 1]
            goalie = k >= 0 and m["role"][(r - 1) * K + k] == "0"
            gk = next((j for j in range(team * 6, team * 6 + 6) if m["role"][r * K + j] == "0"), None)
            attack_top = gk is not None and pos[(r * K + gk) * 2 + 1] < 0
            zs = [(P[3 * q + 2], q) for q in range(r, N) if t[q] - t[r] <= 3000]
            peak = max(range(len(zs)), key=lambda i: zs[i][0])
            land = next((q for z, q in zs[peak:] if z <= 1), None)
            nxt = next((own[q] for q in range(r, N) if t[q] - t[r] <= 3000 and own[q] >= 0), None)
            who = "nobody" if nxt is None else "own team" if nxt // 6 == team else "other team"
            x0, y0 = fl["x0"], fl["y0"]
            tgt = None if goalie else target(x0, y0, attack_top)
            rows.append(dict(game=Path(f).stem, f=r, human=fl.get("human"), goalie=goalie, x0=x0, y0=y0,
                             top=attack_top, tgt=tgt, peak=round(zs[peak][0], 1),
                             land=(round(P[3 * land]), round(P[3 * land + 1]), round((t[land] - t[r]) / 1000, 2))
                             if land else None, next=who))
    return rows


def harness(path):
    rows = [json.loads(line) for line in open(path)]
    print(f"\nHarness ({len(rows)} flips): where they first came down (attacker's view: y from centre toward the net "
          "he attacks), by spot and Passing")
    groups = {}
    for r in rows:
        if r["land"]:
            groups.setdefault((r["x"], r["y"], r["pa"]), []).append(r)
    for (x, y, pa), g in sorted(groups.items()):
        xs, ys = [r["land"][1] for r in g], [r["land"][2] for r in g]
        ts = [r["land"][0] for r in g]
        tgt = (TX[target(x, y, True)], TY[target(x, y, True)])
        print(f"  from ({x:4},{y:5}) Passing {pa:2}: came down at x {statistics.median(xs):5.0f} "
              f"({min(xs)} to {max(xs)}), y {statistics.median(ys):5.0f} ({min(ys)} to {max(ys)}) after "
              f"{statistics.median(ts) / 60:.2f} s; peak {statistics.median(r['peak'] for r in g):.0f}; "
              f"target {tgt}; n {len(g)}")


def main():
    rows = recorded()
    print(f"Recorded SNES flips: {len(rows)} (people {sum(bool(r['human']) for r in rows)}, goalies "
          f"{sum(r['goalie'] for r in rows)})")
    print("  puck next to:", dict(Counter(r["next"] for r in rows)))
    for r in rows:
        tg = "goalie" if r["goalie"] else (TX[r["tgt"]], TY[r["tgt"]])
        print(f"  {r['game']} {r['f']:6} {'person' if r['human'] else 'computer'} {'G' if r['goalie'] else 'S'} "
              f"from ({r['x0']},{r['y0']}) attacking {'top' if r['top'] else 'bottom'}: target {tg}, peak {r['peak']}, "
              f"came down {r['land']}, next {r['next']}")
    if len(sys.argv) > 1:
        harness(sys.argv[1])


if __name__ == "__main__":
    main()
