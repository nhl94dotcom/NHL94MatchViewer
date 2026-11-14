"""NOSE4Web's clutch time (e0dd96b, both systems), played (2026-11-14): in the last 2:00 of the third period with the
score within one goal, the working ratings rise (Genesis +3 of 30, SNES +1 of 15) for both teams: at the 2:00 tick
for the players on the ice, and in setplayer's rebuilds (every faceoff, line changes, out of the box) after it.
Aggression is left alone; aioff / aidef take it through setplayer's inversion (at the next rebuild only).

A computer game in play (power-on, START into play, the computer on both sides), a saved state, then each case from
it (the period, clock and score set):
  tick         period 3, 2:04 left, 2-2: the ratings a few seconds before 2:00 and a few after; then a whistle forced
               (the puck put high at the side boards: out of play) and on to the faceoff (the clock running again: the
               rebuild) and the ratings; then the score made 4-2 and
               on to the faceoff after that
  tick_margin2 the same at 3-1 (no change expected)
  tick_period2 period 2, 2:04 left, 2-2 (none)
  tick_ot      overtime, 2:04 left, 2-2 (none)
  rebuild, rebuild_margin2, rebuild_early, rebuild_ot: 1:55 left at 2-2 / 1:55 at 3-1 / 3:20 at 2-2 / overtime 1:55 at
               2-2, a whistle forced at once: the ratings before and after the faceoff's rebuild (the 2:00 tick never
               runs in these)
Each snapshot: per player record (12) his roster slot and every working rating byte. Written to OUT/clutch.json.
Run it on the original and the build, then `compare`: per case the change across the 2:00 tick on each ROM (by
rating), and the build against the original at each snapshot (by player: only the same roster slot compared).
  Genesis: the records at $B04A + $80 k, ratings +$67-$75 (weight, legstr, legspd, aioff, aidef, shotspd, shotacc,
  passacc, rostnum, spodds, stickhand, endurance, aggress, fighting, checking); gsp $C466, gameclock $C468, scores
  $C6DA (home) / $CA3E; gmode $C2EA bit 0 the clock stopped.
  SNES: 16-word arrays (object x 2): weight $12C3, legstr $12E3, legspd $1303, aioff $1323, aidef $1343, shotspd
  $1363, shotacc $1383, passacc $13A3, spodds $13E3, stickhand $1403, endurance $1423, aggress $1443, checking $1483;
  pnum $12A3; gsp $1630, gameclock $1632, tmscore $178E / $1790; the clock stopped $15D6 nonzero.

python clutch_check.py run ROM OUT
python clutch_check.py compare ORIGINAL_OUT BUILD_OUT"""
import json
import sys
from pathlib import Path

import lowload

GEN_NAMES = ["weight", "legstr", "legspd", "aioff", "aidef", "shotspd", "shotacc", "passacc", "rostnum", "spodds",
             "stickhand", "endurance", "aggress", "fighting", "checking"]
SNES_ARR = {"weight": 0x12C3, "legstr": 0x12E3, "legspd": 0x1303, "aioff": 0x1323, "aidef": 0x1343, "shotspd": 0x1363,
            "shotacc": 0x1383, "passacc": 0x13A3, "spodds": 0x13E3, "stickhand": 0x1403, "endurance": 0x1423,
            "aggress": 0x1443, "checking": 0x1483}
BOOSTED = ["legstr", "legspd", "shotspd", "shotacc", "passacc", "spodds", "stickhand", "endurance", "checking"]
CASES = {"tick": (2, 124, 2, 2), "tick_margin2": (2, 124, 3, 1), "tick_period2": (1, 124, 2, 2), "tick_ot": (3, 124, 2, 2),
         "rebuild": (2, 115, 2, 2), "rebuild_margin2": (2, 115, 3, 1), "rebuild_early": (2, 200, 2, 2),
         "rebuild_ot": (3, 115, 2, 2)}


class Gen:
    GSP, CLOCK, HOME, AWAY = 0xC466, 0xC468, 0xC6DA, 0xCA3E

    def __init__(self, rom, out):
        import gen_1on1_edit_lines as G
        self.r = G.Run(rom, out)
        self.e = self.r.e
        self.r.to_play()

    def step(self, n):
        self.r.step(n)

    def w(self, a):
        return self.e.w(a)

    def setw(self, a, v):
        self.e.setw(a, v)

    def stopped(self):
        return bool(self.e.b(0xC2EA) & 1)

    def puck_out(self):
        p = 0xB04A + 14 * 0x80
        for off, v in ((0x00, 118), (0x14, 0), (0x18, 0x30), (0x28, 4000), (0x2A, 0), (0x2C, 0)):
            self.e.setw(p + off, v)
        self.e.setb(p + 0x60, 0xFF)

    def snap(self):
        out = []
        for k in range(12):
            base = 0xB04A + 0x80 * k
            out.append({"slot": self.e.b(base + 0x66), **{n: self.e.b(base + 0x67 + i) for i, n in enumerate(GEN_NAMES)}})
        return out


class Snes:
    GSP, CLOCK, HOME, AWAY = 0x1630, 0x1632, 0x178E, 0x1790

    def __init__(self, rom, out):
        from snes_ot_goal_check import start
        from snes_60fps_cvc import computer_only
        out.mkdir(parents=True, exist_ok=True)
        self.e, self.m = start(rom, 0, out)
        self.cpu = computer_only
        self.cpu(self.m)
        self.f = 0

    def step(self, n):
        for _ in range(n):
            self.e.run(1)
            self.f += 1
            if self.f % 300 == 0:
                self.cpu(self.m)
            if self.f % 600 == 0:
                lowload.breathe()

    def w(self, a):
        return self.m.w(a)

    def setw(self, a, v):
        self.m.setw(a, v)

    def stopped(self):
        return self.m.w(0x15D6) != 0

    def puck_out(self):
        for a, v in ((0x0D71, 110), (0x0DD3, 0), (0x0DF9, 0x30), (0x0E01, 0), (0x0EDF, 2000), (0x0EFF, 0), (0x0AD9, 0xFFFF)):
            self.m.setw(a, v & 0xFFFF)

    def snap(self):
        return [{"slot": self.m.w(0x12A3 + 2 * k) & 0xFF, **{n: self.m.w(a + 2 * k) & 0xFF for n, a in SNES_ARR.items()}}
                for k in range(12)]


def until(g, test, limit):
    for _ in range(limit):
        if test():
            return True
        g.step(1)
    return False


def next_faceoff(g, limit=60 * 240):
    """A whistle forced (the puck sent out of play over the side boards: wallcollb's whistle), then on to the play
    after it: the rebuild has run once the clock runs again."""
    for _ in range(5):
        g.puck_out()
        if until(g, g.stopped, 120):
            break
    ok = g.stopped() and until(g, lambda: not g.stopped(), limit)
    g.step(10)
    return ok


def state(g):
    return {"gsp": g.w(g.GSP), "clock": g.w(g.CLOCK), "score": [g.w(g.HOME), g.w(g.AWAY)]}


def run(rom, out):
    out.mkdir(parents=True, exist_ok=True)
    g = Gen(rom, out) if rom.lower().endswith((".bin", ".md", ".gen")) else Snes(rom, out)
    st = g.e.serialize()
    res = {}
    for name, (gsp, clock, home, away) in CASES.items():
        g.e.unserialize(st)
        g.setw(g.GSP, gsp)
        g.setw(g.CLOCK, clock)
        g.setw(g.HOME, home)
        g.setw(g.AWAY, away)
        snaps = {}
        if name.startswith("rebuild"):                           # under 2:00 already: only setplayer's rebuild
            g.step(30)
            snaps["before"] = {**state(g), "players": g.snap()}
            ok = next_faceoff(g)
            snaps["after"] = {**state(g), "found": ok, "players": g.snap()}
            res[name] = snaps
            print(name, {k: {kk: v[kk] for kk in ("gsp", "clock", "score")} for k, v in snaps.items()}, flush=True)
            continue
        until(g, lambda: g.w(g.CLOCK) <= 122, 60 * 60)
        snaps["before"] = {**state(g), "players": g.snap()}
        until(g, lambda: g.w(g.CLOCK) <= 118, 60 * 60)
        snaps["after"] = {**state(g), "players": g.snap()}
        if name == "tick":
            ok = next_faceoff(g)
            snaps["faceoff"] = {**state(g), "found": ok, "players": g.snap()}
            sc = state(g)["score"]
            g.setw(g.HOME, min(sc) + 2)                          # a two-goal margin
            ok = next_faceoff(g)
            snaps["faceoff_margin2"] = {**state(g), "found": ok, "players": g.snap()}
        res[name] = snaps
        print(name, {k: {kk: v[kk] for kk in ("gsp", "clock", "score")} for k, v in snaps.items()}, flush=True)
    (out / "clutch.json").write_text(json.dumps(res))


def compare(a_dir, b_dir):
    A = json.loads((Path(a_dir) / "clutch.json").read_text())
    B = json.loads((Path(b_dir) / "clutch.json").read_text())
    names = [n for n in A["tick"]["before"]["players"][0] if n not in ("slot", "rostnum", "fighting")]
    top = max(max(p[n] for p in s["players"] for n in BOOSTED) for d in (A, B) for c in d.values() for s in c.values())
    print(f"highest boosted rating seen anywhere: {top}")
    for case in A:
        print(f"\n== {case}")
        for label, D in (("original", A), ("build", B)):
            b, a = D[case]["before"]["players"], D[case]["after"]["players"]
            ch = {n: sorted({pa[n] - pb[n] for pb, pa in zip(b, a) if pa["slot"] == pb["slot"]}) for n in names}
            what = "the faceoff's rebuild" if case.startswith("rebuild") else "the 2:00 tick"
            print(f"  {label} across {what} (clock {D[case]['before']['clock']} -> {D[case]['after']['clock']}): "
                  + (", ".join(f"{n} {v}" for n, v in ch.items() if v != [0]) or "no change"))
        for snap in B[case]:
            pa, pb = A[case][snap]["players"], B[case][snap]["players"]
            diffs = {n: sorted({q[n] - p[n] for p, q in zip(pa, pb) if p["slot"] == q["slot"]}) for n in names}
            same = sum(p["slot"] == q["slot"] for p, q in zip(pa, pb))
            extra = "" if "found" not in B[case][snap] else f" (faceoff found: original {A[case][snap]['found']}, build {B[case][snap]['found']}; scores {A[case][snap]['score']} / {B[case][snap]['score']}, clock {A[case][snap]['clock']} / {B[case][snap]['clock']})"
            print(f"  {snap}: build - original, {same} players matched{extra}: "
                  + (", ".join(f"{n} {v}" for n, v in diffs.items() if v != [0]) or "all the same"))


if __name__ == "__main__":
    lowload.gentle()
    if sys.argv[1] == "run":
        run(sys.argv[2], Path(sys.argv[3]))
    else:
        compare(sys.argv[2], sys.argv[3])
