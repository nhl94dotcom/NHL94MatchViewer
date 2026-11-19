"""Goalies holding and passing the puck at each net, two ROMs (Genesis, 2026-11-19; NOSE4Web's blade-mirror build: the
facing-up goalie frames' HotList hot spots, which also place a held puck, set to the y-mirror of the facing-down ones).

Each ROM plays the same GAMES computer-against-computer games: power-on to Game Setup (gen_ot_check.to_setup), line
changes off, the shortest periods, penalties on, START into play, the seed $D066 from the game's number, the computer on
both sides, three periods. Every frame: the puck carrier (puckc $B7AA); while it is a goalie (position 0): a hold, at the
top net or the bottom by his y. Per hold: the puck's offset from him each frame (net coordinates, the bottom net turned
half a circle so both read as the top: "out" toward centre ice, "side" to his right looking out), frames with the puck
behind the goal line (also by the goalie's sprite frame, +$06) (|y| > 264) or behind him, and how it ends: who next has the puck within 120 frames (his team,
the other team, nobody), and a goal for either side within 180 frames of the release. Also every goal by net.

python gen_goalie_hold_check.py ROM [ROM ...] GAMES OUT.jsonl   (or report OUT.jsonl)   (resumes: (rom, game) pairs already in OUT are skipped)"""
import json
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

TEAM1, TEAM2, PERLEN, OPTPEN, OPTLINE = 0xD04C, 0xD04E, 0xD050, 0xD056, 0xD058
SEED, CONT1, CONT2, GSP, CLOCK, SCREEN, PUCKC = 0xD066, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7, 0xB7AA
BASE, SZ, POS = 0xB04A, 0x80, 0x35
GOALS = (0xC6DA, 0xCA3E)


def xy(e, k):
    return e.sw(BASE + SZ * k), e.sw(BASE + SZ * k + 0x14)


def game(rom, n):
    e = Emu(rom)
    G.to_setup(e, Path(rom).parent)
    e.setw(PERLEN, 0)
    e.setw(OPTPEN, 2)
    e.setw(OPTLINE, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    holds, goals = [], []
    cur = None                   # the hold in progress
    pending = []                 # ended holds waiting for their next carrier / a goal
    frame, still, last = 0, 0, None
    score = [e.w(a) for a in GOALS]
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
        if e.b(SCREEN) != 0:
            continue
        sc = [e.w(a) for a in GOALS]
        if sc != score:
            px, py = xy(e, 14)
            side = 0 if sc[0] != score[0] else 1
            goals.append({"frame": frame, "team": side, "net": "top" if py > 0 else "bottom"})
            for h in pending:
                if frame - h["end"] <= 180 and "goal_after" not in h:
                    h["goal_after"] = "own team" if side == h["team"] else "other team"
            score = sc
        pc = e.w(PUCKC)
        carrier = None if pc & 0xFF00 else pc
        for h in pending:
            if "next" not in h and carrier is not None and carrier != h["k"]:
                h["next"] = "own team" if (carrier < 6) == (h["k"] < 6) else "other team"
        pending = [h for h in pending if frame - h["end"] <= 180]
        is_goalie = carrier is not None and e.b(BASE + SZ * carrier + POS) == 0
        if cur and (not is_goalie or carrier != cur["k"]):
            cur["end"] = frame
            holds.append(cur)
            pending.append(cur)
            cur = None
        if is_goalie:
            gx, gy = xy(e, carrier)
            px, py = xy(e, 14)
            sg = 1 if gy > 0 else -1
            if cur is None:
                cur = {"k": carrier, "team": 0 if carrier < 6 else 1, "net": "top" if sg > 0 else "bottom",
                       "start": frame, "out": [], "side": [], "in_net": 0, "behind": 0, "fr": Counter(), "fr_net": Counter(),
                       "fr_out": defaultdict(list)}
            cur["out"].append(-sg * (py - gy))
            cur["side"].append(sg * (px - gx))
            cur["in_net"] += abs(py) > 264
            fr = e.w(BASE + SZ * carrier + 6)
            cur["fr"][fr] += 1
            cur["fr_net"][fr] += abs(py) > 264
            cur["fr_out"][fr].append(-sg * (py - gy))
            cur["behind"] += -sg * (py - gy) < -2
    for h in holds + pending:
        h.setdefault("next", "nobody")
        h.setdefault("goal_after", None)
    rows = [{"net": h["net"], "frames": len(h["out"]), "out": round(st.median(h["out"]), 1),
             "side": round(st.median(h["side"]), 1), "in_net": h["in_net"], "behind": h["behind"],
             "next": h["next"], "goal_after": h["goal_after"], "fr": dict(h["fr"]), "fr_net": dict(h["fr_net"]),
             "fr_out": {k: round(st.median(v), 1) for k, v in h["fr_out"].items()}} for h in holds]
    return {"game": n, "holds": rows, "goals": goals, "score": score, "periods": e.w(GSP)}


def report(out):
    by = defaultdict(list)
    goals = defaultdict(Counter)
    for line in open(out):
        r = json.loads(line)
        for h in r.get("holds", []):
            by[(r["rom"], h["net"])].append(h)
        for g in r.get("goals", []):
            goals[r["rom"]][g["net"]] += 1
    for (rom, net), hs in sorted(by.items()):
        print(f"{rom} {net:6s} holds {len(hs):4d}  out median {st.median(h['out'] for h in hs):+5.1f}  side median "
              f"{st.median(h['side'] for h in hs):+5.1f}  frames in the net {sum(h['in_net'] for h in hs)}  behind him "
              f"{sum(h['behind'] > 0 for h in hs)}  next {dict(Counter(h['next'] for h in hs))}  goal within 3 s "
              f"{dict(Counter(h['goal_after'] for h in hs if h['goal_after']))}")
    for rom, c in goals.items():
        print(rom, "goals by net", dict(c))
    print("frames held in each goalie frame (bottom net: facing up 407-412 / 428-430; top: 413-424), puck behind the goal line")
    for (rom, net), hs in sorted(by.items()):
        tot, net_ = Counter(), Counter()
        for h in hs:
            for k, v in h.get("fr", {}).items():
                tot[int(k)] += v
            for k, v in h.get("fr_net", {}).items():
                net_[int(k)] += v
        print(f"  {rom} {net}: " + ", ".join(f"{k}: {tot[k]} ({net_[k]} behind)" for k in sorted(tot) if tot[k] >= 5))


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2])
        return
    roms, games, out = sys.argv[1:-2], int(sys.argv[-2]), Path(sys.argv[-1])
    lowload.gentle()
    done = set()
    if out.exists():
        done = {(r["rom"], r["game"]) for r in map(json.loads, open(out))}
    for n in range(games):
        for rom in roms:
            name = Path(rom).name
            if (name, n) in done:
                continue
            r = game(rom, n)
            r["rom"] = name
            with open(out, "a") as f:
                f.write(json.dumps(r) + "\n")
            print(name, n, r.get("score"), len(r.get("holds", [])), "holds", flush=True)
    report(out)


if __name__ == "__main__":
    main()
