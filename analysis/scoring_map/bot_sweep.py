"""An overnight tuning sweep of the Genesis bot against the expert coaches (2026-11-11, the user: a long run that isn't
a waste of time). Version 50 (bot.py) with settings drawn from a grid (env overrides): the one-timer's C timing
(NHL94_ARRIVE, frames before the pass arrives), how far out its receiver may stand (PEOPLE48 "out"), how often the
one-timer is offered and whether the goalie must be drawn (PEOPLE50), how often the burst becomes a CB check (DEF47),
how often the hold in the attacking zone ends in a shot (PEOPLE41 "shoot"). Each setting plays 8 games against the
computer (bot_record.py: the same 8 seeds for every setting, so they compare paired); after each batch the game's own
counts are read from the match files (expert_profile.bot_rows) and the batch's captures and match files are deleted
(only inside this sweep's folder: the disk is nearly full). Each setting gets an expert-likeness score: the mean of
((bot - expert) / scale)^2 over the 85-90% coaches' per-game numbers (expert_profile.py): shots 13.7 (3), one-timer
tries 5.0 (1.5), the share of one-timers scored 0.36 (0.10), checks 31 (5), penalty minutes 2.4 (1.5), passes tried 43.5
(6), the share completed 0.65 (0.06), attack-zone time 337 (30), breakaway tries 2.2 (0.8); lower is closer. Then the
best 3 settings play 16 more games each (seeds 8-23) to confirm. Two settings at a time (lowload), resumable
(results.jsonl), stops after HOURS.

python bot_sweep.py OUT [N_SETTINGS] [HOURS]   -> OUT/results.jsonl, OUT/report.md"""
import json
import os
import random
import shutil
import statistics as st
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "analysis"))
from expert_profile import bot_rows  # noqa: E402

GRID = {"arrive": [8, 11, 14, 17, 20], "out": [100, 120, 140], "offer": [0.1, 0.15, 0.2, 0.3], "drawn": [0, 4],
        "cb": [0.1, 0.2, 0.3], "shoot": [0.4, 0.6, 0.8]}
BASE = {"arrive": 14, "out": 140, "offer": 0.2, "drawn": 4, "cb": 0.2, "shoot": 0.6}
TARGET = {"shots": (13.7, 3), "one-timer tries": (5.0, 1.5), "one-timer share": (0.36, 0.10), "checks": (31.0, 5),
          "penalty minutes": (2.4, 1.5), "passes tried": (43.5, 6), "pass share": (0.65, 0.06),
          "attack zone time (s)": (337.0, 30), "breakaway tries": (2.2, 0.8)}


def env_for(c):
    e = dict(os.environ)
    e.update({"NHL94_BOT_VERSION": "50", "NHL94_ARRIVE": str(c["arrive"]),
              "NHL94_PEOPLE48": json.dumps({"out": [30, c["out"]]}),
              "NHL94_PEOPLE50": json.dumps({"offer": c["offer"], "drawn": c["drawn"]}),
              "NHL94_DEF47": json.dumps({"cb": c["cb"]}), "NHL94_PEOPLE41": json.dumps({"shoot": c["shoot"]})})
    return e


def name_of(c, first):
    return "_".join(f"{k}{v}" for k, v in c.items()).replace(".", "p") + f"_g{first}"


def measure(folder):
    rows = bot_rows(folder / "matches")
    out = []
    for r in rows:
        ot = r.get("one-timer tries") or 0
        pt = r.get("passes tried") or 0
        out.append({k: r.get(k) for k in ("goals", "goals against", "shots", "one-timer tries", "one-timer goals", "checks",
                                           "penalty minutes", "passes tried", "passes completed", "attack zone time (s)",
                                           "breakaway tries")})
    return out


def clean(folder, root):
    """Delete a finished batch's captures and match files: only inside the sweep's own folder."""
    folder, root = folder.resolve(), root.resolve()
    if root not in folder.parents or not folder.name.startswith("arrive"):
        raise RuntimeError(f"won't delete outside the sweep: {folder}")
    for sub in ("captures", "matches"):
        d = folder / sub
        if d.is_dir() and d.parent == folder:
            shutil.rmtree(d)


def score(games):
    m = lambda k: st.mean(g[k] for g in games if g.get(k) is not None)
    vals = {k: m(k) for k in ("shots", "one-timer tries", "checks", "penalty minutes", "passes tried", "attack zone time (s)",
                              "breakaway tries")}
    vals["one-timer share"] = sum(g["one-timer goals"] for g in games) / max(1, sum(g["one-timer tries"] for g in games))
    vals["pass share"] = sum(g["passes completed"] for g in games) / max(1, sum(g["passes tried"] for g in games))
    s = st.mean(((vals[k] - t) / sc) ** 2 for k, (t, sc) in TARGET.items())
    vals["goals for"], vals["goals against"] = m("goals"), m("goals against")
    vals["won"] = sum(g["goals"] > g["goals against"] for g in games)
    return s, vals


def main():
    out = Path(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    hours = float(sys.argv[3]) if len(sys.argv) > 3 else 8
    out.mkdir(parents=True, exist_ok=True)
    res_path = out / "results.jsonl"
    done = {json.loads(l)["name"] for l in open(res_path)} if res_path.exists() else set()
    rng = random.Random(94)
    settings = [dict(BASE)]
    while len(settings) < n:
        c = {k: rng.choice(v) for k, v in GRID.items()}
        if c not in settings:
            settings.append(c)
    t0 = time.time()

    def run_all(jobs):
        """jobs: (setting, first game, games); two at a time."""
        queue = [j for j in jobs if name_of(j[0], j[1]) not in done]
        running = []
        while queue or running:
            while queue and len(running) < 2 and time.time() - t0 < hours * 3600:
                c, first, games = queue.pop(0)
                folder = out / name_of(c, first)
                folder.mkdir(exist_ok=True)
                log = open(folder / "batch.log", "w")
                p = subprocess.Popen([sys.executable, str(HERE / "bot_record.py"), str(folder), str(games), str(first)],
                                     cwd=str(HERE), env=env_for(c), stdout=log, stderr=subprocess.STDOUT)
                running.append((p, c, first, folder, log))
            for item in list(running):
                p, c, first, folder, log = item
                if p.poll() is None:
                    continue
                log.close()
                running.remove(item)
                games = measure(folder)
                rec = {"name": name_of(c, first), "setting": c, "first": first, "games": games}
                if games:
                    rec["score"], rec["values"] = score(games)
                with open(res_path, "a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                done.add(rec["name"])
                clean(folder, out)
                print(json.dumps({"done": rec["name"], "score": rec.get("score"), "elapsed_h": round((time.time() - t0) / 3600, 2)}), flush=True)
            if not queue and not running:
                break
            if time.time() - t0 > hours * 3600 and not running:
                break
            time.sleep(20)

    run_all([(c, 0, 8) for c in settings])
    recs = [json.loads(l) for l in open(res_path)]
    first8 = sorted((r for r in recs if r["first"] == 0 and r.get("score") is not None), key=lambda r: r["score"])
    top = [r["setting"] for r in first8[:3]]
    run_all([(c, 8, 16) for c in top])
    report(out)


def report(out):
    recs = [json.loads(l) for l in open(out / "results.jsonl")]
    by = {}
    for r in recs:
        key = json.dumps(r["setting"], sort_keys=True)
        by.setdefault(key, []).extend(r["games"])
    rows = []
    for key, games in by.items():
        if games:
            s, v = score(games)
            rows.append((s, json.loads(key), v, len(games)))
    rows.sort(key=lambda x: x[0])
    lines = ["# Bot sweep: version 50's settings against the 85-90% coaches", "",
             "Score: the mean of ((bot - expert) / scale)^2 over the expert numbers (lower is closer). Experts per game: "
             + ", ".join(f"{k} {t}" for k, (t, _) in TARGET.items()) + ".", "",
             "| Score | Games | C timing | Receiver out | Offer | Goalie drawn | CB | Shoot | Shots | OT tries | OT scored | Checks | PIM | Passes | Pass share | AZT | Breakaways | GF-GA | Won |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, c, v, n in rows:
        lines.append(f"| {s:.2f} | {n} | {c['arrive']} | {c['out']} | {c['offer']} | {c['drawn']} | {c['cb']} | {c['shoot']} | "
                     f"{v['shots']:.1f} | {v['one-timer tries']:.1f} | {100 * v['one-timer share']:.0f}% | {v['checks']:.1f} | "
                     f"{v['penalty minutes']:.1f} | {v['passes tried']:.1f} | {100 * v['pass share']:.0f}% | {v['attack zone time (s)']:.0f} | "
                     f"{v['breakaway tries']:.1f} | {v['goals for']:.1f}-{v['goals against']:.1f} | {v['won']} of {n} |")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    if sys.argv[1] == "--report":
        report(Path(sys.argv[2]))
    else:
        main()
