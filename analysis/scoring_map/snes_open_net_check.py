"""NOSE4Web's SNES open net shot fix in computer games (2026-11-19): shotdiradj ($9E:DFF7 retail) aims every computer
shot; when a goalie is found but his sightline misses the net (an open net) it leaves aim 0 (high middle, just under
the 13-unit bar), the fix 8 (the middle, mid-height). Covered nets get 1-4 or 5-8 (the side roll), so in the fix an
open-net shot can't be told by its aim: the test is paired.

collect: games as snes_60fps_cvc.game sets them up (the computer on both sides, 5-minute periods, penalties on, each
game its own seed) on the original ROM, every frame; a shot is sf2shot ($1000 in sflags $15D8) turning on, with its
aim passdir ($0D03), the shooter (lastplayer $0CF3) and whether the defending team has a goalie on (position 0 among
its objects: shotdiradj's own test). Every shot is logged with its result; each open-net one (aim 0, a goalie on) also
keeps the emulator state from the frame before (STATES/g<game>_<frame>.state).
replay: each kept state loaded into a ROM (the original again, to check the replay repeats; the fix), the shot fired
the same frame, its aim and result. Results: the puck followed until it reaches the net's front (|y| 259) or sf2shot
clears (touched first): over (height 13 or more within 22 of the middle: over the bar), goal (the shooting team's
goals rise within 90 frames after), post (17-22 out, under 13), in (within 17, under 13, no goal), wide, touched
(a stick, a body or the goalie first), other.

python snes_open_net_check.py collect ROM GAMES OUT.jsonl STATES [FIRST]   (games FIRST to GAMES - 1; resumable)
python snes_open_net_check.py replay ROM STATES OUT.jsonl
python snes_open_net_check.py report COLLECT.jsonl REPLAY.jsonl ..."""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, GOALS_P, OPTPEN, SEED, Mem, computer_only

SFLAGS, SF2SHOT, PASSDIR, LASTPLAYER = 0x15D8, 0x1000, 0x0D03, 0x0CF3
XPOS, YPOS, POSITION, PFGOAL, PFTEAM = 0x0D55, 0x0DB7, 0x0F43, 0x14C3, 0x1503
PUCK = 0x1C
PUCKZ = 0x0DF9


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def goals(m, t):
    return sum(m.w(GOALS_P + 4 * q + 2 * t) for q in range(4))


def shot_start(m):
    sh = m.w(LASTPLAYER)
    team = 1 if m.w(PFTEAM + 2 * sh) else 0
    dfd = range(6, 12) if team == 0 else range(6)
    return dict(team=team, top=m.w(PFGOAL + 2 * sh) != 0, aim=m.w(PASSDIR),
                goalie=any(m.w(POSITION + 2 * k) == 0 for k in dfd), x=s16(m.w(XPOS + PUCK)),
                y=s16(m.w(YPOS + PUCK)), clock=m.w(CLOCK), period=m.w(GSP), g0=goals(m, team), age=0)


def step_shot(e, m, cur, on):
    """One frame of a shot in flight: its result, or None while it flies (runs up to 90 more frames at the front)."""
    cur["age"] += 1
    x, y, z = s16(m.w(XPOS + PUCK)), s16(m.w(YPOS + PUCK)), s16(m.w(PUCKZ))
    front = (y >= 259) if cur["top"] else (y <= -259)
    res = None
    if goals(m, cur["team"]) > cur["g0"]:
        res = "goal"
    elif front:
        res = "over" if z >= 13 and abs(x) <= 22 else "post" if 17 < abs(x) <= 22 else "in" if abs(x) <= 17 else "wide"
        cur.update(cx=x, cz=z)
        for _ in range(90):
            e.run(1)
            if goals(m, cur["team"]) > cur["g0"]:
                res = "goal"
                break
    elif not on and cur["age"] > 1:
        res = "touched"
    elif cur["age"] > 150:
        res = "other"
    if res:
        cur["result"] = res
        del cur["g0"]
    return res


def start_game(rom, n):
    e = M.emulator(rom)
    m = Mem(e, rom)
    tmp = Path.home() / "NHL94_scoring_map" / "x_tmp_opennet"
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", tmp)
    else:
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    return e, m


def collect_game(rom, n, states):
    e, m = start_game(rom, n)
    shots, frames, still, cur = [], 0, 0, None
    prev = m.w(SFLAGS) & SF2SHOT
    while m.w(GSP) < 3 and frames < 220000:
        c = m.w(CLOCK)
        for _ in range(30):
            before = e.serialize() if cur is None else None
            e.run(1)
            frames += 1
            on = m.w(SFLAGS) & SF2SHOT
            if on and not prev and cur is None:
                cur = shot_start(m)
                cur["frame"] = frames
                if cur["aim"] == 0 and cur["goalie"]:
                    p = Path(states) / f"g{n:03d}_{frames:06d}.state"
                    p.write_bytes(before)
                    cur["state"] = p.name
            elif cur is not None and step_shot(e, m, cur, on):
                shots.append(cur)
                cur = None
            prev = m.w(SFLAGS) & SF2SHOT
        if m.w(CLOCK) > 300:
            m.setw(CLOCK, 300)
        if frames % 300 < 30:
            computer_only(m)
            lowload.breathe()
        still = still + 30 if m.w(CLOCK) == c else 0
        if still >= 900:
            e.run(4, hold=["START"])
            still = 0
    return dict(game=n, rom=Path(rom).name, frames=frames, goals=[goals(m, 0), goals(m, 1)], shots=shots)


def replay(rom, states, out):
    e = M.emulator(rom)
    m = Mem(e, rom)
    done = {json.loads(line)["state"] for line in out.read_text().splitlines()} if out.exists() else set()
    for p in sorted(Path(states).glob("*.state")):
        if p.name in done:
            continue
        e.unserialize(p.read_bytes())
        prev = m.w(SFLAGS) & SF2SHOT
        e.run(1)
        on = m.w(SFLAGS) & SF2SHOT
        if not on or prev:
            r = dict(state=p.name, result="no shot")
        else:
            cur = shot_start(m)
            while True:
                e.run(1)
                if step_shot(e, m, cur, m.w(SFLAGS) & SF2SHOT):
                    break
            r = dict(state=p.name, rom=Path(rom).name, **cur)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        lowload.breathe()


def report(paths):
    for p in paths:
        R = [json.loads(line) for line in Path(p).read_text().splitlines()]
        if R and "shots" in R[0]:
            S = [s for g in R for s in g["shots"]]
            print(f"\n{Path(p).name}: {len(R)} games, {len(S)} computer shots, goals {sum(sum(g['goals']) for g in R)}")
            for label, f in (("open net (aim 0, goalie on)", lambda s: s["aim"] == 0 and s["goalie"]),
                             ("pulled goalie (none on)", lambda s: not s["goalie"]),
                             ("every other shot", lambda s: s["aim"] != 0 and s["goalie"])):
                sub = [s for s in S if f(s)]
                c = Counter(s["result"] for s in sub)
                print(f"  {label:30s} {len(sub):4d}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))
        else:
            c = Counter(r["result"] for r in R)
            aims = Counter(r.get("aim") for r in R)
            print(f"\n{Path(p).name}: {len(R)} replays; aims {dict(aims)}: " + ", ".join(f"{k} {v}" for k, v in c.most_common()))


def main():
    mode = sys.argv[1]
    if mode == "report":
        report(sys.argv[2:])
        return
    lowload.gentle()
    if mode == "replay":
        replay(sys.argv[2], sys.argv[3], Path(sys.argv[4]))
        return
    rom, games, out, states = sys.argv[2], int(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5])
    states.mkdir(parents=True, exist_ok=True)
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    first = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    for n in range(first, games):
        if n in done:
            continue
        r = collect_game(rom, n, states)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(n, len(r["shots"]), sum(s["aim"] == 0 and s["goalie"] for s in r["shots"]), r["goals"], flush=True)


if __name__ == "__main__":
    main()
