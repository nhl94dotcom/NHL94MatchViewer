"""NOSE4Web's postsFix (2026-11-20, e224658): McMarkis's 2 MB builds' Posts stat (tmposts $7E:E7F0, a team word pair,
raised by PostCount from checkgoal's post branch) credited the team of the object at lastplayer as an offset, but
lastplayer ($0CF3, SA-1 $6CF3) holds an object number: the fix doubles it. Computer games (shootout_savestate_check's
Snes set-up), every frame: each time the post branch runs (crowdlevel $35E0 up by exactly $12C, the branch's mark) and
each time a team's count goes up: the team credited, the shooter's team (shotplayer $0D29, an offset), the last toucher's
(lastplayer x 2), whether a shot was in flight (sflags $15D8 bit $1000, the frame before), gmclock.
python snes_posts_check.py ROM OUT.jsonl GAMES [FIRST]"""
import json
import sys
from pathlib import Path

import lowload
import shootout_savestate_check as SC

CROWD, POSTS, LAST, SHOT, SFLAGS, GMCLOCK, PFTEAM = 0x35E0, 0xE7F0, 0x0CF3, 0x0D29, 0x15D8, 0x15D6, 0x1503


def team_of(m, off):
    return None if off >= 0x18 else (0 if m.w(PFTEAM + off) == 0 else 1)


def game(S, n):
    e, m = S.e, S.m
    S.new_game(n)
    rows, f, last, still = [], 0, None, 0
    prev = dict(crowd=m.w(CROWD), posts=(m.w(POSTS), m.w(POSTS + 2)), flag=bool(m.w(SFLAGS) & 0x1000),
                shot=m.w(SHOT), last=m.w(LAST))
    while f < 60 * 60 * 40 and S.gsp() < 4:
        if f % 300 == 0:
            S.computer()
        if f % 3600 == 0:
            lowload.breathe()
        c = S.clock(); still = still + 1 if c == last else 0; last = c
        e.run(4 if still >= 900 and still % 900 == 0 else 1, hold=["START"] if still >= 900 and still % 900 == 0 else [])
        f += 1
        cur = dict(crowd=m.w(CROWD), posts=(m.w(POSTS), m.w(POSTS + 2)), flag=bool(m.w(SFLAGS) & 0x1000),
                   shot=m.w(SHOT), last=m.w(LAST))
        branch = (cur["crowd"] - prev["crowd"]) & 0xFFFF == 0x12C
        up = [t for t in (0, 1) if cur["posts"][t] > prev["posts"][t]]
        if branch or up:
            rows.append(dict(game=n, f=f, period=S.gsp(), clock=c, branch=branch, credited=up,
                             shooter_team=team_of(m, prev["shot"]), last_team=team_of(m, 2 * prev["last"]),
                             shot_in_flight=prev["flag"], gmclock=m.w(GMCLOCK), posts=list(cur["posts"])))
            print(json.dumps(rows[-1]), flush=True)
        prev = cur
    return rows, (m.w(POSTS), m.w(POSTS + 2)), f


def main():
    rom, out, games = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    S = SC.Snes(rom, first)
    for n in range(first, first + games):
        rows, final, frames = game(S, n)
        with out.open("a") as fh:
            fh.write(json.dumps(dict(game=n, rom=Path(rom).name, final_posts=final, frames=frames, events=rows)) + "\n")
        print("game", n, "posts", final, "events", len(rows), flush=True)


if __name__ == "__main__":
    main()
