"""Each coach's Rating as it stood on past dates, using only the games played by then (2026-11-04, the user). Two uses: a monthly history for tracking and charts, and every league's coaches as of the day
before its first game, for league_ratings.py. Names real people, so everything goes to %USERPROFILE%\\NHL94_League_Data\\coach_history, never the repository. Resumable: finished dates are kept.

A date's fit is the published fit (coach_rating.py) with only earlier games, and recent games counting more from that date: all leagues, except the outliers, and separately Classic only. "Average" is the mean
of coaches with 100+ games by then, or, early on, the 20 with the most games. Values stay on the published scale (the conversion factor from the final fit).
python analysis/coach_history.py test           time a sample of dates, write nothing
python analysis/coach_history.py [hours]        run (default 1 hour), then stop; run again to go on"""
import json
import re
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

OUT = C.DATA / "coach_history"
SYSTEMS = (("All_Games_GENS.csv", "GENESIS", 0), ("All_Games_SNES.csv", "SNES", 1))
REF_GAMES, REF_FEW = 100, 20


def settings():
    """(half-life, ridge, conversion factor) by system: all leagues, then Classic."""
    def pick(name):
        text = (C.DATA / name).read_text(encoding="utf-8")
        return [(float(a), float(b)) for a, b in re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)], [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]
    return {"all": pick("coach_rating_test.md"), "classic": pick("coach_rating_groups.md")}


class Fit:
    """One system and scope, ready to be fitted as of any day."""

    def __init__(self, name, scope, at, sets):
        C.PREFIX = "classic" if scope == "classic" else None
        self.games, _ = C.prepare(name)
        self.D = C.Design(self.games)
        self.y = C.values(self.games)["coast"]
        self.days = np.array([g["day"] for g in self.games])
        (self.hl, self.ridge), self.scale = sets[scope][0][at], sets[scope][1][at]
        self.names = list(self.D.people)
        self.ids = np.array([self.D.people[p] for p in self.names])
        col = {p: i for i, p in enumerate(self.names)}
        self.home_i = np.array([col[g["hp"]] for g in self.games])
        self.away_i = np.array([col[g["ap"]] for g in self.games])

    def as_of(self, day):
        """{coach: (log odds against the average coach, games by then)} from games before that day, for coaches who've played or not."""
        m = self.days < day
        if not m.any():
            return {}
        w = 0.5 ** ((day - self.days) / (365.25 * self.hl))
        beta = self.D.fit(m, w, self.y, self.ridge)[0]
        count = np.bincount(self.home_i[m], minlength=len(self.names)) + np.bincount(self.away_i[m], minlength=len(self.names))
        ref = np.nonzero(count >= REF_GAMES)[0]
        if len(ref) < REF_FEW:
            ref = np.argsort(-count)[:REF_FEW]
        vals = (beta[self.ids] - beta[self.ids[ref]].mean()) * self.scale
        return {p: (round(float(vals[i]), 4), int(count[i])) for i, p in enumerate(self.names)}


def targets(fit):
    """The dates wanted: the first of each month, and the day of each league's first game."""
    first = {}
    for g in fit.games:
        first[g["league"]] = min(first.get(g["league"], g["day"]), g["day"])
    lo, hi = date.fromordinal(int(fit.days.min())), date.fromordinal(int(fit.days.max()))
    months = [date(y, m, 1).toordinal() for y in range(lo.year, hi.year + 1) for m in range(1, 13) if lo < date(y, m, 1) <= hi] + [int(fit.days.max()) + 1]
    return sorted(set(months) | set(first.values())), first


def main():
    gentle()
    sets = settings()
    test = sys.argv[1:] == ["test"]
    hours = float(sys.argv[1]) if sys.argv[1:] and not test else 1.0
    OUT.mkdir(exist_ok=True)
    stop = time.time() + hours * 3600
    for name, label, at in SYSTEMS:
        for scope in ("all", "classic"):
            t0 = time.time()
            fit = Fit(name, scope, at, sets)
            days, first = targets(fit)
            print(f"{label} {scope}: {len(fit.games)} games, {len(fit.names)} coaches, {len(first)} leagues, {len(days)} dates; loaded in {time.time() - t0:.0f} s", flush=True)
            path = OUT / f"{label}_{scope}.json"
            done = json.loads(path.read_text(encoding="utf-8")) if path.exists() and not test else {}
            todo = [d for d in days if str(d) not in done]
            if test:
                sample = todo[-3:] + todo[len(todo) // 2 - 1: len(todo) // 2 + 1]
                t1 = time.time()
                for d in sample:
                    fit.as_of(d)
                each = (time.time() - t1) / len(sample)
                print(f"  about {each:.2f} s a date while working, so about {each * len(todo) / 60:.0f} min of work, {2 * each * len(todo) / 60:.0f} min with rests", flush=True)
                continue
            for k, d in enumerate(todo):
                if time.time() > stop:
                    path.write_text(json.dumps(done), encoding="utf-8")
                    print(f"  stopped on time: {len(todo) - k} dates left here; run again to go on", flush=True)
                    return
                done[str(d)] = fit.as_of(d)
                breathe()
                if k % 25 == 24:
                    path.write_text(json.dumps(done), encoding="utf-8")
            path.write_text(json.dumps(done), encoding="utf-8")
            (OUT / f"{label}_{scope}_leagues.json").write_text(json.dumps(first), encoding="utf-8")
            print(f"  {label} {scope} finished, {len(done)} dates", flush=True)


if __name__ == "__main__":
    main()
