"""Stickhandling's other two jobs in the recorded league games (2026-11-11, for NOSE4Web and the commissioner): wobbles
(stumbles) instead of falls, and passes caught instead of bobbled. Both systems; the games in Documents\\NHL94 Viewer.

The code (GENESIS_MECHANICS 6.2 / 7.4, SNES_MECHANICS 7.2; the disassemblies' puckstick and FallDown):
- Catch limit (the puck's speed when it reaches the stick): Genesis 13,000 + 350 x working Stk (0-30), shots
  13,000 flat; SNES 10,000 + 700 x working Stk (0-15), +3,000 for the pass's intended receiver and goalies, shots no
  Stk. Match files keep speeds / 100, so 130 + 3.5 x Stk and 100 + 7 x Stk (+30).
- Wobble: Genesis working Stk 24+ and impact under 16 + (HVcount & 15), never after a wobble in the last 60 frames;
  SNES working Stk 12+ and impact at most 10 + (seed & 15), never with the clock stopped. Impact isn't recorded.

Printed:
- Wobbles: every start of the stumble animation (Genesis $11E6, SNES $F7B2) against every start of a fall (Genesis
  $0D26 / $0DD8 / $145C, SNES $F49C / $F54E / $F6C0), skaters only, by the player's roster Stickhandling (and on the
  Genesis his hot / cold), with the puck (owner the sample before) or not. (The converter's hits can't be used: they
  come from the game's checks count, which a stumble never raises.)
- Catches: every pass that reached a skater (completed or intercepted: the first sample the receiver owns the puck)
  and every bobble (find_bobbles): the puck's speed in the last sample before (match units), its spread, and the share
  of those arrivals that fall between each Stickhandling step's limit and the next; and the share bobbled by the
  receiver's roster Stickhandling; on the SNES also by his Stickhandling as played (the per-game hot / cold, `hcs`:
  a cold roll maxes it to 15), and what followed a bobble.

python stickhandling_study.py"""
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

MATCHES = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
STK = 8                                     # Stickhandling's place in a roster player's ratings ('a')
STUMBLE = {"genesis": "11e6", "snes": "f7b2"}
FALLS = {"genesis": {"0d26", "0dd8", "145c"}, "snes": {"f49c", "f54e", "f6c0"}}


def load():
    for f in sorted(MATCHES.glob("*.js")):
        if f.name == "season.js":
            continue
        t = f.read_text(encoding="utf-8")
        try:
            yield f.stem, json.loads(t[t.index("{"):t.rindex("}") + 1])
        except ValueError:
            continue


def speed(m, i):
    return math.hypot(m["puckV"][2 * i], m["puckV"][2 * i + 1])


def main():
    wob = {s: defaultdict(Counter) for s in ("genesis", "snes")}
    arrive = {s: {"catch": [], "bobble": []} for s in ("genesis", "snes")}
    recv = {s: defaultdict(Counter) for s in ("genesis", "snes")}
    keep = {s: defaultdict(Counter) for s in ("genesis", "snes")}
    nxt = {s: Counter() for s in ("genesis", "snes")}
    snes_hc, snes_after = defaultdict(Counter), Counter()
    games = Counter()
    for name, m in load():
        s = m.get("system", "genesis")
        if s not in wob:
            continue
        games[s] += 1
        R, A, RO, own, N = m["rosters"], m["anim"], m["roster"], m["owner"], len(m["t"])
        stumble, falls = STUMBLE[s], FALLS[s]

        def player(i, k):
            c = RO[i * 12 + k]
            if c == "z":
                return None
            team = 0 if k < 6 else 1
            r = int(c, 36)
            return R[team][r] if r < len(R[team]) else None
        for k in range(12):
            prev = None
            for i in range(N):
                a = A[(i * 12 + k) * 4:(i * 12 + k) * 4 + 4]
                if a != prev and (a == stumble or a in falls):
                    p = player(i, k)
                    if p and not p.get("g"):
                        key = (p["a"][STK], p.get("hc", 0) if s == "genesis" else 0,
                               "carrier" if i and own[i - 1] == k else "other")
                        wob[s][key]["wobble" if a == stumble else "fall"] += 1
                        if key[2] == "carrier":            # who has the puck next: his team or the other
                            who = next((own[j] for j in range(i, min(N, i + 180)) if own[j] >= 0), None)
                            keep[s]["wobble" if a == stumble else "fall"][
                                "none" if who is None else "kept" if (who < 6) == (k < 6) else "lost"] += 1
                prev = a
        for p in m.get("passes", []):
            if p.get("result") not in ("completed", "intercepted") or "bobble" in p:
                continue
            for i in range(p["f"] + 1, min(N, p["f"] + 240)):
                if own[i] >= 0 and own[i] != p["idx"]:
                    arrive[s]["catch"].append(speed(m, i - 1))
                    rp = player(i, own[i])
                    if rp and not rp.get("g"):
                        recv[s][rp["a"][STK]]["catch"] += 1
                        if s == "snes":
                            snes_hc[snes_working(rp)]["catch"] += 1
                    break
        for b in m.get("bobbles", []):
            arrive[s]["bobble"].append(max(speed(m, b["f"] - 1), speed(m, b["f"] - 2)))
            nxt[s][b.get("next")] += 1
            rp = player(b["f"], b["idx"])
            if rp and not rp.get("g"):
                recv[s][rp["a"][STK]]["bobble"] += 1
                if s == "snes":
                    snes_hc[snes_working(rp)]["bobble"] += 1
                    shots = [x for x in m.get("shotList", []) if x["team"] != (0 if b["idx"] < 6 else 1)
                             and b["f"] <= x["f"] <= b["f"] + 300]
                    snes_after["bobbles"] += 1
                    snes_after["a shot against within 12.5 game s"] += bool(shots)
                    snes_after["a goal against within 12.5 game s"] += any(x["result"] == "goal" for x in shots)
    print("Games:", dict(games))
    for s in ("genesis", "snes"):
        print(f"\n== {s}: wobbles (hits on skaters) by the hit player's roster Stickhandling"
              + (" and hot / cold" if s == "genesis" else ""))
        rows = defaultdict(Counter)
        for (stk, hc, who), c in wob[s].items():
            rows[(stk, who)] += c
        for (stk, who) in sorted(rows):
            c = rows[(stk, who)]
            n = c["wobble"] + c["fall"]
            print(f"  Stk {stk} {who:7s}: {c['wobble']:3d} wobbles of {n:4d} ({100 * c['wobble'] / n if n else 0:4.1f}%)")
        if s == "genesis":
            print("  Stk 5-6 by hot / cold (wobbles / hits):",
                  {f"{stk}/{hc:+d}": f"{c['wobble']}/{c['wobble'] + c['fall']}" for (stk, hc, who), c in
                   sorted(wob[s].items()) if stk >= 5 and c['wobble'] + c['fall']})
        a = arrive[s]
        allv = sorted(a["catch"] + a["bobble"])
        if not allv:
            continue
        q = lambda p: allv[min(len(allv) - 1, int(p * len(allv)))]
        print(f"== {s}: passes reaching a skater: {len(a['catch'])} taken, {len(a['bobble'])} bobbled; arrival speed "
              f"(match units, x100 for the game's) median {q(.5):.0f}, 90% {q(.9):.0f}, 99% {q(.99):.0f}")
        base, step, top, extra = (130, 3.5, 30, 0) if s == "genesis" else (100, 7, 15, 30)
        for lo in range(0, top + 1, 5 if s == "genesis" else 3):
            hi = lo + (5 if s == "genesis" else 3)
            L0, L1 = base + step * lo + extra, base + step * hi + extra
            band = sum(L0 < v <= L1 for v in allv)
            over = sum(v > L0 for v in allv)
            print(f"  working Stk {lo:2d}: limit {L0:5.1f}; arrivals over it {over:4d} ({100 * over / len(allv):4.1f}%);"
                  f" between it and Stk {hi}'s {band:3d} ({100 * band / len(allv):4.1f}%)")
    receivers(recv)
    print("== snes: bobbled by the receiver's Stickhandling as played (cold = maxed to 15 by the bug; otherwise roster x 5 / 2"
          " plus his hot value, the hidden bonuses left out)")
    for k in sorted(snes_hc, key=lambda k: -1 if k == "cold" else k):
        c = snes_hc[k]
        n = c["catch"] + c["bobble"]
        print(f"  {'cold (maxed)' if k == 'cold' else 'working ' + str(k):13s}: {c['bobble']:3d} bobbled of {n:4d} ({100 * c['bobble'] / n:4.1f}%)")
    print("  after a bobble:", dict(snes_after))
    for s in ("genesis", "snes"):
        print(f"== {s}: after a carrier's wobble / fall, the next to have the puck (3 s (real)):",
              {w: dict(c) for w, c in keep[s].items()}, "| after a bobble:", dict(nxt[s]))


def snes_working(p):
    hc = p.get("hcs", [0] * 14)[STK]
    return "cold" if hc == "max" else min(15, p["a"][STK] * 5 // 2 + (hc or 0))


def receivers(recv):
    for s in ("genesis", "snes"):
        print(f"== {s}: passes reaching a skater, bobbled by the receiver's roster Stickhandling")
        for stk in sorted(recv[s]):
            c = recv[s][stk]
            n = c["catch"] + c["bobble"]
            print(f"  Stk {stk}: {c['bobble']:3d} bobbled of {n:4d} ({100 * c['bobble'] / n if n else 0:4.1f}%)")


if __name__ == "__main__":
    main()
