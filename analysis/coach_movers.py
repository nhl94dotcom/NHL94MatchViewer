"""Which coaches' Ratings have risen and fallen most (2026-11-04, the user), from the history coach_history.py keeps. Names real people, so the tables go to %USERPROFILE%\\NHL94_League_Data\\coach_history only.
A coach counts over a period only with MIN_GAMES games in it and MIN_START games before it, so a move is play, not a new coach's first estimate or a retired coach drifting as the average moves.
Ratings are win chances against an average coach. The chance a move is only noise isn't measured here: a move of a few points on a few dozen games can be luck.
python analysis/coach_movers.py"""
import json
import math
from datetime import date

import coach_rating as C

OUT = C.DATA / "coach_history"
PERIODS = ((1, "the last year"), (3, "the last three years"))
SCOPES = (("all", "all leagues"), ("classic", "Classic"))
MIN_GAMES, MIN_START, SHOWN = 30, 50, 15


def chance(v):
    return 100 / (1 + math.exp(-v))


def moves(history, years):
    days = sorted(int(d) for d in history)
    end = days[-1]
    start = max((d for d in days if d <= end - round(365.25 * years)), default=None)
    if start is None:
        return None, None, []
    now, then = history[str(end)], history[str(start)]
    rows = []
    for coach, (value, games) in now.items():
        was, before = then.get(coach, (0.0, 0))
        if before >= MIN_START and games - before >= MIN_GAMES:
            rows.append(dict(coach=coach, was=chance(was), now=chance(value), games=games - before))
    return start, end, sorted(rows, key=lambda r: r["was"] - r["now"])


def table(rows):
    out = ["| Coach | Then | Now | Change | Games in the period |", "| --- | --- | --- | --- | --- |"]
    out += [f"| {r['coach']} | {r['was']:.1f} | {r['now']:.1f} | {r['now'] - r['was']:+.1f} | {r['games']} |" for r in rows]
    return out + [""]


def main():
    for label in ("GENESIS", "SNES"):
        out = [f"# {label}: Ratings rising and falling", "", f"Private: names real coaches. A coach needs {MIN_START}+ games before the period and {MIN_GAMES}+ in it. Ratings are win chances against an average coach, on the Rating as it stood on each date.", ""]
        for scope, name in SCOPES:
            history = json.loads((OUT / f"{label}_{scope}.json").read_text(encoding="utf-8"))
            for years, period in PERIODS:
                start, end, rows = moves(history, years)
                if not rows:
                    continue
                changes = sorted(r["now"] - r["was"] for r in rows)
                middle = changes[len(changes) // 2]
                rose = sum(c > 0 for c in changes)
                print(f"{label} {name}, {period}: {len(rows)} coaches, {rose} rose, median change {middle:+.1f}, largest {changes[-1]:+.1f} and {changes[0]:+.1f}")
                out += [f"## {name}: {period} ({date.fromordinal(start)} to {date.fromordinal(end)})", "", f"{len(rows)} coaches qualify; {rose} rose; the middle change is {middle:+.1f}. Most coaches who keep playing rise against an average that includes those who've stopped, so read a move against that middle change, not against zero.", "","**Rising most**", ""]
                out += table(rows[:SHOWN])
                out += ["**Falling most**", ""]
                out += table(rows[::-1][:SHOWN])
        path = OUT / f"MOVERS_{label}.md"
        path.write_text("\n".join(out), encoding="utf-8")
        print(path.name)


if __name__ == "__main__":
    main()
