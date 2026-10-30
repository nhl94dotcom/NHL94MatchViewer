"""Goals per minute by strength in the leagues' own results (2026-10-30; the user's question: does a power play work
mostly by the shorthanded team scoring less rather than the power-play team scoring more?). The user's databases
outside the repository (%USERPROFILE%\\NHL94_League_Data), simulated games left out, aggregates only.

Each game's regulation timeline (three 300-second periods; games with a goal at 300 s or later left out) is rebuilt
from its penalty list (period, seconds into it, team, ...) and goal list (period, seconds, team, ..., strength tag): a
team has a man less while a penalty runs; a minor ends early when the other team scores while it is a man up (the
earliest-ending one); at most two men off. The databases give every minor as 120 s, but many leagues play 1-minute
minors (their ROMs): each league's length is taken from its own power-play goals (95% of them within 75 s of the call:
60 s; else 120 s; leagues with under 40 power-play goals: 120 s). Then goals and minutes in each state, for each
team, overall and split into the first 20 seconds after a call and the rest. The goals' own strength tags (EV, PP,
SH, PP2, SH2) are counted beside the rebuilt state as a check.
python analysis/league_strength_study.py"""
import ast
import csv
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path.home() / "NHL94_League_Data"
REG, EARLY = 900, 20


def rows(name):
    csv.field_size_limit(10 ** 9)
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") != "1":
                yield r


def parse(r):
    """Penalty call times and goals for each side ({True: home ...}), or None."""
    try:
        pens = {home: [(int(p[0]) - 1) * 300 + int(p[1]) for p in (ast.literal_eval(r[col]) if r[col] else [])
                       if int(p[0]) <= 3]
                for col, home in (("HomePenalties", True), ("AwayPenalties", False))}
        goals = []
        for col, home in (("HomeGoals", True), ("AwayGoals", False)):
            for g in ast.literal_eval(r[col]) if r[col] else []:
                if int(g[0]) > 3:
                    continue
                if int(g[1]) >= 300:
                    return None
                goals.append(((int(g[0]) - 1) * 300 + int(g[1]), home, str(g[-1])))
    except (ValueError, SyntaxError, IndexError, TypeError):
        return None
    return pens, goals


def minor_lengths(name):
    """Each league's minor length from its power-play goals' time since the opponents' last call."""
    since = defaultdict(list)
    for r in rows(name):
        g = parse(r)
        if g is None:
            continue
        pens, goals = g
        for t, home, tag in goals:
            prior = [p for p in pens[not home] if p <= t]
            if tag in ("PP", "PP2") and prior:
                since[r["League"]].append(t - max(prior))
    out = {}
    for league, v in since.items():
        v.sort()
        out[league] = 60 if len(v) >= 40 and v[int(0.95 * len(v))] <= 75 else 120
    return out


def game(pens, goals, length, secs, scored, tags):
    events = sorted([(t, 0, home) for home in pens for t in pens[home]] + [(t, 1, home, tag) for t, home, tag in goals],
                    key=lambda e: (e[0], -e[1]))
    box, started, t = {True: [], False: []}, [], 0

    def men(side):
        return 5 - min(2, len(box[side]))

    def state(side):
        st = (men(side), men(not side))
        if st == (5, 5):
            return st
        return st + ("first 20 s" if any(s <= t < s + EARLY for s in started) else "after",)

    def advance(to):
        nonlocal t
        while t < to:
            nxt = min([to] + [e for side in box for e in box[side] if e > t] + [s + EARLY for s in started if s + EARLY > t])
            for side in (True, False):
                secs[state(side)] += nxt - t
            t = nxt
            for side in box:
                box[side] = [e for e in box[side] if e > t]

    for e in events:
        advance(min(e[0], REG))
        if e[1] == 0:
            box[e[2]].append(e[0] + length)
            started.append(e[0])
        else:
            home, tag = e[2], e[3]
            st = state(home)
            scored[st] += 1
            tags[st[:2]][tag] += 1
            if men(home) > men(not home) and box[not home]:      # a power-play goal frees the first minor
                box[not home] = sorted(box[not home])[1:]
    advance(REG)


def study(name, label):
    lengths = minor_lengths(name)
    secs, scored, tags = defaultdict(float), defaultdict(int), defaultdict(Counter)
    n = 0
    for r in rows(name):
        g = parse(r)
        if g is not None:
            n += 1
            game(*g, lengths.get(r["League"], 120), secs, scored, tags)
    print(f"\n==================== {label}: {n} games (regulation); "
          f"{sum(v == 60 for v in lengths.values())} of {len(lengths)} leagues with 1-minute minors")
    rate = lambda st: scored[st] / secs[st] * 60 if secs[st] else float("nan")
    whole = lambda a, b: (scored[(a, b, "first 20 s")] + scored[(a, b, "after")]) / \
                         (secs[(a, b, "first 20 s")] + secs[(a, b, "after")]) * 60
    base = rate((5, 5))
    print(f"  5-on-5: {base:.3f} goals a team-minute")
    for a, b in ((5, 4), (4, 5), (5, 3), (3, 5), (4, 3), (3, 4), (4, 4), (3, 3)):
        st = (a, b)
        tg = tags[st]
        mine = tg["PP"] + tg["PP2"] if a > b else tg["SH"] + tg["SH2"] if a < b else tg["EV"]
        print(f"  {a}-on-{b}: {whole(a, b) / base:.2f} of the 5-on-5 rate "
              f"(first 20 s after a call {rate((a, b, 'first 20 s')) / base:.2f}, after {rate((a, b, 'after')) / base:.2f}); "
              f"{(secs[(a, b, 'first 20 s')] + secs[(a, b, 'after')]) / 60:.0f} team-minutes; the goals' own tags agree "
              f"{100 * mine / max(1, sum(tg.values())):.0f}%")


def main():
    study("All_Games_GENS.csv", "GENESIS")
    study("All_Games_SNES.csv", "SNES")


if __name__ == "__main__":
    main()
