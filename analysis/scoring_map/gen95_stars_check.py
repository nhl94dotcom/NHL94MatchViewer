"""NHL '95 three stars in computer games (2026-11-26, for NOSE4Web's NHL '95 three stars at 900 / 1,170 a shot faced:
CalcTeamStarScores at $95C8A, the weights' words in the ROM from $95CAC; one ROM for line changes off, one for on).

Each game as gen95_ref_cvc.py's (power-on to Game Setup, penalties On Except Off-sides, the seed from the game's
number, the computer on both sides), 10-minute periods, line changes off or on, played on through overtime until the
stars box (gmode's high byte bit 7): the 52 longs at ThreeStars ($FFCAF8) half a second later against the formula on the
team structs with the ROM's weights (goalie slots and the ice-time rule tried a few ways, the best kept), the three
cleared against the formula's top three, the same game's top three at the weight given as OLD (4,000 / 4,500), the
scorer of the last goal, each goalie's shots faced and ice time.

python gen95_stars_check.py ROM GAMES OUT.jsonl [FIRST] [on]   |   report OUT.jsonl ..."""
import json
import sys
from pathlib import Path

import gen95_fight_check as F
import lowload
from emu import Emu
from gen95_stats_check import ASSISTS, CHECKS, CLOCK, GMODE, GOALS, GSP, HOME, SHOTS, STARS, TMSIZE, TOI, arr, s32, words

SEED, BASE, SZ = 0xCC6A, 0xAC62, 0x80
OLD = {900: 4000, 1170: 4500}


def weights(rom):
    b = Path(rom).read_bytes()
    w = lambda a: int.from_bytes(b[a:a + 2], "big")  # noqa: E731
    return dict(assist=w(0x95CAC), shot=w(0x95CBE), goal=w(0x95CCA), check=w(0x95CD6), shutout=w(0x95D00),
                ga=w(0x95D04) - 65536, sa=w(0x95D12))


def formula(st, v, goalies, need):
    out = []
    for t in (0, 1):
        s, d3 = st[t], st[t]["score"] - st[1 - t]["score"]
        for i in range(26):
            val = d3
            if i >= goalies[t]:
                val += s["a"][i] * v["assist"] + s["s"][i] * v["shot"] + s["g"][i] * v["goal"] + s["c"][i] * v["check"]
            elif s["toi"][i] >= need and s["s"][i]:
                val += (s["a"][i] * v["assist"]) >> 1
                val += v["shutout"] if s["g"][i] == 0 else 0
                val += s["g"][i] * v["ga"] + ((s["s"][i] - 1) if d3 < 0 else s["s"][i]) * v["sa"]
            out.append(val)
    return out


def stats(e):
    return [dict(score=e.w(HOME + t * TMSIZE + 0xC), g=arr(e, t, GOALS), a=arr(e, t, ASSISTS), s=arr(e, t, SHOTS),
                 c=arr(e, t, CHECKS), toi=words(e, t, TOI)) for t in (0, 1)]


def game(rom, n, lines_on):
    e = Emu(rom)
    F.to_setup(e)
    e.setb(F.ROW + 3, 1)                       # 10-minute periods
    e.setb(F.ROW + 6, 2)                       # penalties: On, Except Off-sides
    e.setb(F.ROW + 7, 0 if lines_on else 1)    # line changes
    e.run(6, hold=["START"]); e.run(300); e.run(6, hold=["START"]); e.run(60); e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    v = weights(rom)
    frame, still, last, lastgoal, pg = 0, 0, None, None, None
    while frame < 60 * 60 * 90:
        if frame % 60 == 0:
            e.setw(0xBF4C, 0)
            e.setw(0xBF4E, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        if frame % 10 == 0:
            st = stats(e)
            g = [st[0]["g"][2:], st[1]["g"][2:]]           # skaters' goals (the first slots are goalies: goals against)
            if pg is not None and g != pg:
                for t in (0, 1):
                    for i, (a, b) in enumerate(zip(pg[t], g[t])):
                        if b > a:
                            lastgoal = dict(slot=26 * t + i + 2, gsp=e.w(GSP), clock=e.w(CLOCK))
            pg = g
        if e.w(GMODE) & 0x8000:
            break
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
    else:
        return {"game": n, "rom": Path(rom).name, "frames": frame, "stars": False}
    gsp = e.w(GSP)
    e.run(30)
    st = stats(e)
    got = [s32(e.l(STARS + 4 * i)) for i in range(52)]
    e.run(30)
    got2 = [s32(e.l(STARS + 4 * i)) for i in range(52)]
    best = None
    for goalies in ((2, 2), (3, 3), (2, 3), (3, 2), (1, 1), (1, 2), (2, 1)):
        for need in (0, 1, 60, 300, 100000):
            want = formula(st, v, goalies, need)
            bad = [i for i in range(52) if got[i] != want[i] and got[i] != 0]
            if best is None or len(bad) < len(best[0]):
                best = (bad, want, goalies, need)
    bad, want, goalies, need = best
    old = formula(st, dict(v, sa=OLD.get(v["sa"], 4000)), goalies, need)
    top = lambda sc: sorted(range(52), key=lambda i: (-sc[i], i))[:3]  # noqa: E731
    isg = lambda i: i % 26 < goalies[i // 26]  # noqa: E731
    taken = [i for i in range(52) if got[i] == 0 and want[i] != 0]
    return {"game": n, "rom": Path(rom).name, "frames": frame, "stars": True, "lines_on": lines_on, "gsp": gsp,
            "score": [st[0]["score"], st[1]["score"]], "weights": v, "bad": [(i, got[i], want[i]) for i in bad],
            "stable": got == got2, "goalie_slots": goalies, "need": need, "taken": taken, "top3": top(want),
            "top3_scores": [want[i] for i in top(want)], "top3_old": top(old), "goalie_top3": [isg(i) for i in top(want)],
            "goalie_top3_old": [isg(i) for i in top(old)], "last_goal": lastgoal,
            "goalies": [dict(slot=26 * t + i, shots=st[t]["s"][i], against=st[t]["g"][i], toi=st[t]["toi"][i], assists=st[t]["a"][i],
                             got=got[26 * t + i], want=want[26 * t + i]) for t in (0, 1) for i in range(goalies[t])],
            "checks": [sum(st[t]["c"]) for t in (0, 1)], "shots": [sum(st[t]["s"][goalies[t]:]) for t in (0, 1)],
            "fourth": sorted(want, reverse=True)[3]}


def report(paths):
    for p in paths:
        G = [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
        S = [g for g in G if g["stars"]]
        n = len(S)
        print(f"{Path(p).stem}: {len(G)} games, the stars box in {n}; weights {S[0]['weights'] if S else None}; "
              f"line changes on {S[0]['lines_on'] if S else None}")
        print("  scores off the formula:", sum(len(g["bad"]) for g in S), "; the read stable in", sum(g["stable"] for g in S),
              "; goalie slots", sorted({tuple(g["goalie_slots"]) for g in S}), "ice-time rule", sorted({g["need"] for g in S}))
        print("  cleared = the formula's top three in", sum(sorted(g["taken"]) == sorted(g["top3"]) for g in S))
        for g in S:
            if sorted(g["taken"]) != sorted(g["top3"]):
                print("    game", g["game"], "score", g["score"], "gsp", g["gsp"], "cleared", g["taken"], "top three", g["top3"],
                      g["top3_scores"], "fourth", g["fourth"], "last goal", g["last_goal"])
        for key, name in (("goalie_top3", "the ROM's weights"), ("goalie_top3_old", "4,000 / 4,500")):
            print(f"  {name}: a goalie first star {sum(g[key][0] for g in S)}, among the three {sum(any(g[key]) for g in S)}, "
                  f"both {sum(sum(g[key]) == 2 for g in S)}, goalie places {sum(sum(g[key]) for g in S)} of {3 * n}")
        ot = [g for g in S if g["gsp"] >= 3]
        print("  overtime games", len(ot), "; tied at the end", sum(g["score"][0] == g["score"][1] for g in S),
              "; overtime winner's scorer among the cleared", sum(bool(g["last_goal"]) and g["last_goal"]["gsp"] >= 3 and g["last_goal"]["slot"] in g["taken"] for g in ot),
              "of", sum(bool(g["last_goal"]) and g["last_goal"]["gsp"] >= 3 for g in ot), "decided in overtime")
        gl = [x for g in S for x in g["goalies"]]
        print("  goalies: shutouts", sum(x["against"] == 0 and x["shots"] > 0 for x in gl), "; with no shots faced", sum(x["shots"] == 0 for x in gl),
              "(their scores other than the goal difference:", sum(1 for g in S for x in g["goalies"] if x["shots"] == 0 and x["got"] not in (0, g["score"][x["slot"] // 26] - g["score"][1 - x["slot"] // 26])), ")",
              "; with shots faced", sum(x["shots"] > 0 for x in gl), "; shots faced, mean", round(sum(x["shots"] for x in gl) / max(1, sum(x["shots"] > 0 for x in gl)), 1))
        for g in S:
            for x in g["goalies"]:
                if x["against"] == 0 and x["shots"] > 0:
                    print("    shutout: game", g["game"], "score", g["score"], x)
        print("  a game: skaters' shots", round(sum(sum(g["shots"]) for g in S) / n, 1), "checks", round(sum(sum(g["checks"]) for g in S) / n, 1),
              "goals", round(sum(sum(g["score"]) for g in S) / n, 2))


def main():
    if sys.argv[1] == "report":
        report(sys.argv[2:])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lines_on = len(sys.argv) > 5 and sys.argv[5] == "on"
    lowload.gentle()
    for n in range(first, first + games):
        r = game(rom, n, lines_on)
        with open(out, "a") as fo:
            fo.write(json.dumps(r) + "\n")
        print(n, r.get("score"), r.get("gsp"), len(r.get("bad", [])), r["frames"], flush=True)


if __name__ == "__main__":
    main()
