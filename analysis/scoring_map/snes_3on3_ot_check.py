"""SNES 3-on-3 overtime (2026-11-12, for NOSE4Web e95d330: NHL94_3on3_ot.smc, every overtime; nhl94snes_SA1_3on3_ot.sfc,
regular season only; gen_3on3_ot_check.py is the Genesis one). In overtime (gsp >= 3, no shootout or penalty shot)
the fill order is G, C, LW, RD, LD, RW, extra attacker; each team's tmap is 4 plus the other team's penalties beyond its
own (at most 2), at most 6 minus all its boxed players, at least 3; the faceoff takes the full-strength row.

Each case: snes_60fps_cvc's boot (the menus, the computer on both sides, the game's seed from its number), then in
RAM penalties On, No Offside (OptPen $34C4 = 2), line changes (OptLine $34C6: 0 off, 1 on), the play mode
(OptPlayMode $34BC: 0 regular season, 2 playoffs); the third period's clock set to 2 s at 0-0 (or, `carry`, to 40 s
with the home skaters' Aggression ($1443) high until a home player is in the box, then to 2 s) and played into
overtime. In overtime the away skaters are held at Aggression AGR (default 18: checkagr's range (20 - Agr) x 16 = 32)
so penalties come. Every 4 frames: each team's skaters on the ice (objects by pfteam $1503, position $0F43 1-6), tmap
($17A6, away +2), its players in the box (tmpdst $1852, away +$34, values 1-$7FFF), kept as segments; at each faceoff
drop (the clock stopped flag $15D6 clearing): both teams' skaters and tmap, and a screenshot of the first few; a
screenshot the first time each count is seen (the power-play clock). Low RAM through snes_60fps_cvc.Mem (BW-RAM on
the SA-1 build). Until the overtime ends or 15,000 frames.

python snes_3on3_ot_check.py ROM CASE OUT [SEEDS]   CASE: off | on | carry | playoff | reg"""
import json
import sys
from pathlib import Path

import lowload
import menu_shots as M
import snes_60fps_cvc as cvc

GSP, CLOCK, STOPPED, SEED = 0x1630, 0x1632, 0x15D6, 0x0792
OPTPEN, OPTLINE, PLAYMODE = 0x34C4, 0x34C6, 0x34BC
TMAP, TMPDST, POSITION, PFTEAM, AGGRESS = 0x17A6, 0x1852, 0x0F43, 0x1503, 0x1443
GOALS_P = 0x177E
POS = {1: "LD", 2: "RD", 3: "LW", 4: "C", 5: "RW", 6: "EA"}
UNTIL_CROWDED = bool(__import__("os").environ.get("NHL94_AGR_UNTIL_CROWDED"))
AGR = int(__import__("os").environ.get("NHL94_AGR", "18"))   # (20 - Agr) x 16: 19 is the most that leaves a range


def team_of(m, k):
    return 0 if m.w(PFTEAM + 2 * k) == 0 else 1


def on_ice(m, t):
    return sorted(POS[m.w(POSITION + 2 * k) & 0xFF] for k in range(12)
                  if team_of(m, k) == t and 1 <= (m.w(POSITION + 2 * k) & 0xFF) <= 6 and m.w(POSITION + 2 * k) < 0x8000)


def boxed(m, t):
    return [i + 1 for i in range(26) if 0 < m.w(TMPDST + 0x34 * t + 2 * i) < 0x8000]


def boot(rom, n, out):
    e = M.emulator(rom)
    m = cvc.Mem(e, rom)
    tmp = out / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", tmp)
    else:
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(STOPPED) == 0:
            return e, m
        e.run(4, hold=["START"])
        e.run(60)
    return e, None


def run_case(rom, case, n, out):
    e, m = boot(rom, n, out)
    if m is None:
        return {"case": case, "seed": n, "error": "never reached play"}
    m.setw(OPTPEN, 2)
    m.setw(OPTLINE, 1 if case == "on" else 0)
    m.setw(PLAYMODE, 2 if case == "playoff" else 0)
    cvc.computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    m.setw(GSP, 2)
    for p in range(4):
        m.setw(GOALS_P + 4 * p, 0)
        m.setw(GOALS_P + 4 * p + 2, 0)
    carried = None
    if case == "carry":
        m.setw(CLOCK, 40)
        for f in range(30000):
            if f % 300 == 0:
                cvc.computer_only(m)
            for k in range(12):
                if team_of(m, k) == 0:
                    m.setw(AGGRESS + 2 * k, AGR)
            e.run(1)
            if boxed(m, 0) and m.w(STOPPED) == 0:
                carried = {"clock": m.w(CLOCK), "tmap": [m.w(TMAP), m.w(TMAP + 2)], "boxed": boxed(m, 0)}
                break
            if m.w(CLOCK) <= 3 and m.w(STOPPED) == 0:
                m.setw(CLOCK, 40)
            for p in range(4):
                m.setw(GOALS_P + 4 * p, 0)
                m.setw(GOALS_P + 4 * p + 2, 0)
    m.setw(CLOCK, 2)
    still, last = 0, None
    for f in range(60000):                                  # into overtime: its own clock running
        e.run(1, hold=["START"] if still >= 300 and f % 60 < 4 else [])
        c = m.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        if f % 300 == 0:
            cvc.computer_only(m)
        if m.w(GSP) == 3 and c != 0:
            break
    else:
        return {"case": case, "seed": n, "error": "no overtime", "gsp": m.w(GSP)}
    segs, faceoffs, shot_tags, f, was_stopped = [], [], set(), 0, True
    pp = case in ("off", "on", "carry", "playoff")
    crowded = []
    burst = {"left": 0, "tag": ""}
    while f < 15000:
        if f % 300 == 0:
            cvc.computer_only(m)
        if pp and UNTIL_CROWDED and any(len(boxed(m, t)) >= 3 for t in (0, 1)):
            pp = False                                      # three in one box: let them come out (the return)
        if pp:
            for k in range(12):
                if team_of(m, k) == 1:
                    m.setw(AGGRESS + 2 * k, AGR)
        e.run(4, hold=["START"] if f % 600 == 0 and m.w(STOPPED) and still > 600 else [])
        f += 4
        c = m.w(CLOCK)
        still = still + 4 if c == last else 0
        last = c
        if m.w(GSP) != 3 or (c == 0 and m.w(STOPPED)):
            break
        h, a = on_ice(m, 0), on_ice(m, 1)
        tm = [m.w(TMAP), m.w(TMAP + 2)]
        bx = [boxed(m, 0), boxed(m, 1)]
        stopped = bool(m.w(STOPPED))
        key = (tuple(h), tuple(a), tuple(tm), tuple(len(b) for b in bx))
        if not segs or segs[-1]["key"] != key:
            segs.append({"key": key, "from": f, "to": f, "clock": c, "stopped": stopped})
            tag = f"{len(h)}v{len(a)}"
            if tag not in shot_tags and not stopped:
                shot_tags.add(tag)
                e.screenshot(out / f"{Path(rom).stem}_{case}_{n}_{tag}.png")
                if len(h) != len(a):
                    burst["left"], burst["tag"] = 8, tag      # a power play: 8 more, 90 frames apart (the scoreboard)
        if burst["left"] and f % 90 == 0 and not stopped:
            e.screenshot(out / f"{Path(rom).stem}_{case}_{n}_{burst['tag']}_b{8 - burst['left']}.png")
            burst["left"] -= 1
        else:
            segs[-1]["to"] = f
        if was_stopped and not stopped:
            faceoffs.append({"f": f, "clock": c, "home": h, "away": a, "tmap": tm, "boxed": [len(b) for b in bx]})
            for t in (0, 1):
                if len(bx[t]) >= 3:
                    crowded.append({"team": t, "clock": c, "tmap": tm[t], "on_ice": [h, a][t], "boxed": bx[t]})
            if len(faceoffs) <= 3:
                e.screenshot(out / f"{Path(rom).stem}_{case}_{n}_faceoff{len(faceoffs)}.png")
        was_stopped = stopped
    for s in segs:
        s["key"] = [list(s["key"][0]), list(s["key"][1]), list(s["key"][2]), list(s["key"][3])]
    return {"case": case, "seed": n, "carried": carried, "frames": f, "gsp_end": m.w(GSP), "segments": segs,
            "faceoffs": faceoffs, "crowded": crowded}


def main():
    rom, case, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    seeds = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    for n in range(seeds):
        r = run_case(rom, case, n, out)
        with open(out / f"{Path(rom).stem}_{case}.jsonl", "a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({k: r.get(k) for k in ("case", "seed", "carried", "frames", "gsp_end", "error")}), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
