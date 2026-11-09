"""What NOSE4Web's injury risk option would do in the recorded league games (Genesis, 2026-11-09): the option adds
min(knockdowns taken x bonus, cap) to a hit's impact in FallDown's injury roll (an injury when randomd0(160) <=
impact: chance (impact + 1) / 160), the count halved at each intermission.

For each knockdown in the match files (hits that knocked the player down: knocked down, upended, into the boards or
bench; poke trips included), from the raw recording (captures/<name>/fast.bin.gz, the helper's blocks): whether it
could injure (the victim had the puck ($B7AA = his record) in the samples before, went into SPAfallback $0DD8 within
6 samples, facing straight up or down then (+$55 & 3 = 0), the clock running), and its impact (+$32, the highest in
those samples). Then per game: the expected injuries without the option (the sum of (impact + 1) / 160) against the
real ones, and with each bonus / cap; and the same for the hits on skaters who had 5+ knockdowns that game.

python injury_risk_estimate.py [NAME ...]   (default: every Genesis game in Documents\\NHL94 Viewer)"""
import gzip
import json
import os
import struct
import sys
from collections import defaultdict
from pathlib import Path

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
DOWN = ("knocked down", "upended", "into the boards", "into the bench")
OPTIONS = ((2, 10), (3, 15), (4, 20))
REC, SZ, PUCKC, CLOCK, PERIOD = 0xB04A, 0x80, 0xB7AA, 0xC468, 0xC466
FALLBACK = 0x0DD8


class Capture:
    def __init__(self, path):
        cj = json.loads((path / "capture.json").read_text())
        self.blocks = [tuple(b) for b in cj["blocks"]]
        self.size = 8 + sum(n for _, n in self.blocks)
        self.data = gzip.open(path / "fast.bin.gz").read()
        self.n = len(self.data) // self.size
        self.ms = [struct.unpack_from("<q", self.data, i * self.size)[0] for i in range(self.n)]

    def off(self, i, a):
        a &= 0xFFFF
        pos = 8
        for start, n in self.blocks:
            if start <= a < start + n:
                return i * self.size + pos + a - start
            pos += n
        raise KeyError(hex(a))

    def w(self, i, a):
        o = self.off(i, a)
        return self.data[o] | self.data[o + 1] << 8

    def b(self, i, a):
        return self.data[self.off(i, a ^ 1)]


def study(name):
    t = (HOME / "matches" / f"{name}.js").read_text(encoding="utf-8")
    m = json.loads(t[t.index("{"):t.rindex("}") + 1])
    if m.get("system", "genesis") != "genesis":
        return None
    cap = Capture(HOME / "captures" / name)
    import bisect
    at = lambda f: min(cap.n - 1, bisect.bisect_left(cap.ms, m["t"][f]))
    hits = sorted((h for h in m.get("hits", []) if h.get("outcome") in DOWN), key=lambda h: h["f"])
    taken = defaultdict(float)                # knockdowns taken, halved each intermission (the option's count)
    period = None
    out = []
    for h in hits:
        i = at(h["f"])
        p = cap.w(i, PERIOD)
        if period is not None and p != period:
            for k in taken:
                taken[k] = int(taken[k]) // 2
        period = p
        key = (1 - h["team"], h["on"])        # the victim: the other team's roster place h["on"]
        rec = next((k for k in (range(6, 12) if key[0] else range(6))
                    if cap.b(i, REC + SZ * k + 0x66) == h["on"]), None)
        eligible, impact = False, 0
        if rec is not None:
            had = any(cap.w(j, PUCKC) == rec for j in range(max(0, i - 4), i + 1))
            running = cap.w(max(0, i - 8), CLOCK) != cap.w(min(cap.n - 1, i + 8), CLOCK)
            for j in range(i, min(cap.n, i + 7)):
                impact = max(impact, cap.w(j, REC + SZ * rec + 0x32))
                if cap.w(j, REC + SZ * rec + 0x58) == FALLBACK and cap.b(j, REC + SZ * rec + 0x55) & 3 == 0:
                    eligible = had and running
        out.append({"f": h["f"], "victim": key, "count": int(taken[key]), "eligible": eligible, "impact": impact})
        taken[key] += 1
    totals = defaultdict(int)
    for h in hits:
        totals[(1 - h["team"], h["on"])] += 1
    injuries = sum(1 for e in m.get("injuries", []) if not e.get("atStart"))
    return {"hits": out, "totals": dict((f"{k[0]},{k[1]}", v) for k, v in totals.items()), "injuries": injuries}


def chance(impact, extra=0):
    return min(160, impact + 1 + extra) / 160


def main():
    names = sys.argv[1:] or sorted(p.stem for p in (HOME / "matches").glob("*.js") if p.name != "season.js"
                                   and (HOME / "captures" / p.stem / "fast.bin.gz").exists())
    games = []
    for n in names:
        try:
            r = study(n)
        except (KeyError, FileNotFoundError, ValueError) as err:
            print("skip", n, err)
            continue
        if r:
            games.append(r)
    g = len(games)
    elig = [(h, game) for game in games for h in game["hits"] if h["eligible"]]
    base = sum(chance(h["impact"]) for h, _ in elig)
    real = sum(game["injuries"] for game in games)
    print(f"{g} Genesis games; {sum(len(x['hits']) for x in games)} knockdowns, {len(elig)} that could injure "
          f"({len(elig) / g:.2f} a game); impact of those: median {sorted(h['impact'] for h, _ in elig)[len(elig) // 2] if elig else '-'}, "
          f"usual chance {base / max(1, len(elig)):.3f}")
    print(f"injuries: real {real} ({real / g:.2f} a game); expected from the roll {base:.1f} ({base / g:.2f} a game)")
    counts = sorted(h["count"] for h, _ in elig)
    print("knockdowns already taken (halved at intermissions) before those hits:",
          {c: counts.count(c) for c in sorted(set(counts))})
    heavy = lambda h, game: game["totals"].get(f"{h['victim'][0]},{h['victim'][1]}", 0) >= 5
    hb = sum(chance(h["impact"]) for h, game in elig if heavy(h, game))
    for bonus, cap in OPTIONS:
        exp = sum(chance(h["impact"], min(h["count"] * bonus, cap)) for h, _ in elig)
        exph = sum(chance(h["impact"], min(h["count"] * bonus, cap)) for h, game in elig if heavy(h, game))
        print(f"+{bonus} / cap {cap}: {exp / g:.3f} a game ({100 * (exp / base - 1):+.0f}%); skaters with 5+ knockdowns "
              f"in the game: {hb / g:.3f} -> {exph / g:.3f} a game (x{exph / hb if hb else float('nan'):.2f})")


if __name__ == "__main__":
    main()
