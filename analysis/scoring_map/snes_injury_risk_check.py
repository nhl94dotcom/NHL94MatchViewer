"""The SNES injury risk option, ready for NOSE4Web's build (2026-11-09; gen_injury_risk_check.py is the Genesis one,
0f3e827 there: a count a player of the knockdowns he took, cleared at the start of a game, halved at each intermission,
and min(count x bonus, cap) added to the impact in FallDown's injury roll).

The SNES roll (FallDown .24, the NHL94SNES disassembly): only the puck carrier, only when he goes into SPAfallback
facing straight up or down the ice (facedir & 3 = 0), the hitter a skater, the clock running; then an injury when
randoma8(150) x 2 < impact (about impact / 300). setInjuryType then sets his tmpdst entry ($1852, the visitors +$34, by
pnum) to $FFFD (out for the period), or one time in 8 $FFFC (for the game).

In live play (snes_assist_stick_test.Game, the retail game states): the pad-1 skater A skates at an opponent O who has
the puck (it kept on him, puckc $0AD9 = O x 2, until he goes down), facing him straight down the ice (the case the
game can injure) or on a diagonal (which it never can); A presses A (the body check) at frame `at`. To get many
knockdowns: A heavy (working weight $12C3 = 120, checking $1483 = 15), O light (weight 0) with stickhandling 0
($1403: FallDown lets a carrier with stickhandling 12+ stumble instead of falling when the hit is weak). Injuries
counted by his tmpdst entry turning $FFFD / $FFFC (or SPAinjury1, $F90E retail, on him).

Parts:
- `injuries ROM OUT [--counts SPEC]`: the trials above, with his knockdown count preset to 0 and to 6 when SPEC is
  given (else 0 only): knockdowns, falls back facing straight, injuries. Run on the unchanged ROM and on a strong build
  (a big bonus and cap): with count 0 they should match the unchanged ROM's rate; with count 6 the straight-facing
  injuries go up; the diagonal ones stay 0 on both.
- `counts ROM OUT SPEC`: the count before and after each trial, by what happened (A body check, B poke, Y hook / hold):
  expected +1 for a knockdown of him, nothing for a hold, a stumble or a miss.
- `halving ROM OUT SPEC`: counts set (7, 10, 255 for players on both teams), the clock set to 1 s, play run into the
  next period: the counts there (expected 3, 5, 127).
- `start ROM OUT SPEC`: from power-on (snes_60fps_cvc's menus), junk ($5A) written over the counts at Game Setup:
  the counts at the first frame of play (expected all 0).
- `whistle ROM OUT SPEC|-`: hits after the whistle (the clock stopped, gmclock $15D6 = 1) and with it running: each
  trial's energy change, knockdowns, count change; run on the unchanged ROM (SPEC -) and the build, then compared.
SPEC is where the build keeps the counts: BASE[:TEAM_STRIDE[:SIZE]] in bank $7E (hex BASE, TEAM_STRIDE bytes between
the home and away tables, default $20; SIZE 1 for bytes, 2 for words; indexed by pnum), e.g. F034:40:2 (NOSE4Web efb691b: a word a player at $7E:F034, the away team +$40).

python snes_injury_risk_check.py injuries ROM OUT [--counts SPEC] | counts ROM OUT SPEC | halving ROM OUT SPEC
       | start ROM OUT SPEC | whistle ROM OUT SPEC|-"""
import json
import sys
from collections import Counter
from pathlib import Path

import lowload
from snes_assist_stick_test import Game, POSITION, PUCK, ZPOS, CLOCK

PUCKC, TMPDST, SPA, PNUM, FACE, PFTEAM = 0x0AD9, 0x1852, 0x11A3, 0x12A3, 0x1163, 0x1503
TMPDE, GMCLOCK, OPTLINE = 0x17EA, 0x15D6, 0x34C6
WEIGHT, STICKHAND, CHECKING, CHECKS, PERIOD = 0x12C3, 0x1403, 0x1483, 0x17B6, 0x1630
SEED = 0x0792
FALLBACK, INJURY1 = 0xF54E, 0xF90E
FALLS = (0xF49C, 0xF54E, 0xF6C0)          # SPAfallfwd, SPAfallback, SPAflip
FLAIL = 0xF46A
SA1_SHIFT = 0xEA06 - 0xF46A               # the SA-1 build's animation words, moved as one table


class Counts:
    def __init__(self, spec):
        parts = spec.split(":")
        self.base = int(parts[0], 16)
        self.stride = int(parts[1], 16) if len(parts) > 1 else 0x20
        self.size = int(parts[2]) if len(parts) > 2 else 1

    def addr(self, G, k):
        return self.base + (self.stride if G.w(PFTEAM + 2 * k) else 0) + self.size * (G.w(PNUM + 2 * k) & 0xFF)

    def get(self, G, k):
        a = self.addr(G, k)
        return G.w(a) if self.size == 2 else G.w(a) & 0xFF

    def set(self, G, k, v):
        a = self.addr(G, k)
        G.setw(a, v if self.size == 2 else (G.w(a) & 0xFF00) | (v & 0xFF))


def words(G):
    s = SA1_SHIFT if G.g.sa1 else 0
    return {"fallback": (FALLBACK + s) & 0xFFFF, "injury": (INJURY1 + s) & 0xFFFF, "flail": (FLAIL + s) & 0xFFFF,
            "falls": {(w + s) & 0xFFFF for w in FALLS}}


def tmpdst(G, k):
    return TMPDST + (0x34 if G.w(PFTEAM + 2 * k) else 0) + 2 * (G.w(PNUM + 2 * k) & 0xFF)


def trial(G, base, button, dy, at, seed, facing_kind="straight", preset=None, counts=None, heavy=True, stopped=False, optline=None):
    """One trial; returns what happened to O."""
    e = G.e
    e.unserialize(base)
    if optline is not None:
        G.setw(OPTLINE, optline)          # the hit energy option works only with line changes on
    W = words(G)
    a, team, up = G.me()
    o = next(k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    keep = {a, o}
    face_o = (4 if up > 0 else 0) if facing_kind == "straight" else (3 if up > 0 else 7)

    def park():
        for k in range(12):
            if k not in keep and G.w(POSITION + 2 * k) != 0xFFFF:
                G.put(k, -100 + 18 * (k % 6) + (10 if k >= 6 else 0), -230 * up)

    once = G.g.sa1                         # players put in place every frame stay frozen on the SA-1 build
    for f in range(30 if not once else 1):
        park()
        G.put(a, 0, 0)
        G.put(o, 0, dy * up)
        G.setw(FACE + 2 * a, 0 if up > 0 else 4)
        G.setw(FACE + 2 * o, face_o)
        G.put(PUCK, 0, dy * up + 6 * up)
        G.setw(ZPOS, 0)
        if stopped:
            G.setw(GMCLOCK, 1)
        G.run()
    G.setw(SEED, (0x9E37 * (seed + 1)) & 0xFFFF or 1)
    G.setw(SEED + 2, (0x7F4A * (seed + 3)) & 0xFFFF or 1)
    if heavy:
        G.setw(WEIGHT + 2 * a, 120)
        G.setw(CHECKING + 2 * a, 15)
        G.setw(WEIGHT + 2 * o, 0)
        G.setw(STICKHAND + 2 * o, 0)
    if counts and preset is not None:
        counts.set(G, o, preset)
    c_before = counts.get(G, o) if counts else None
    slot = tmpdst(G, o)
    for t in range(2):                     # everyone at 3/4 energy, so a cost shows
        for s in range(26):
            G.setw(TMPDE + 0x34 * t + 2 * s, 0xC00)
    en = TMPDE + (0x34 if G.w(PFTEAM + 2 * o) else 0) + 2 * (G.w(PNUM + 2 * o) & 0xFF)
    e0 = G.w(en)
    checks0 = G.w(CHECKS) + G.w(CHECKS + 2)
    res = dict(down=False, fellback_straight=False, injured=False, flail=False, injured_for_game=False)
    way = "UP" if up > 0 else "DOWN"
    for f in range(90):
        if not once:
            park()
        spa = G.w(SPA + 2 * o)
        if spa not in W["falls"] and spa != W["injury"] and not res["down"]:
            G.setw(PUCKC, 2 * o)           # he keeps the puck until he goes down (the roll is for the carrier)
            G.setw(FACE + 2 * o, face_o)
        if stopped:
            G.setw(GMCLOCK, 1)
        G.run(hold=[way] + ([button] if at <= f < at + 3 else []))
        spa = G.w(SPA + 2 * o)
        if spa in W["falls"]:
            res["down"] = True
        if spa == W["fallback"] and G.w(FACE + 2 * o) & 3 == 0:
            res["fellback_straight"] = True
        if spa == W["flail"]:
            res["flail"] = True
        v = G.w(slot)
        if v in (0xFFFD, 0xFFFC) or spa == W["injury"]:
            res["injured"] = True
            res["injured_for_game"] |= v == 0xFFFC
    res["knockdowns counted"] = G.w(CHECKS) + G.w(CHECKS + 2) - checks0
    res["de"] = G.w(en) - e0
    if counts:
        res["count change"] = counts.get(G, o) - c_before
    return res


def injuries_part(rom, out, spec=None):
    G = Game(rom)
    counts = Counts(spec) if spec else None
    tally = Counter()
    presets = (0, 5) if counts else (None,)   # the SNES option counts at most 5 knockdowns
    for facing in ("straight", "diagonal"):
        for preset in presets:
            for bi, base in enumerate(G.g.bases[:2]):
                for dy in (40, 60, 80):
                    for at in (5, 15, 25):
                        for sd in range(8):
                            r = trial(G, base, "A", dy, at, 0x9000 + 37 * sd + dy + at + 101 * bi, facing, preset, counts)
                            tally[(facing, preset, "down" if r["down"] else "-",
                                   "fell back facing straight" if r["fellback_straight"] else "-",
                                   "INJURED" if r["injured"] else "-")] += 1
                lowload.breathe()
    res = {str(k): v for k, v in sorted(tally.items(), key=str)}
    for facing in ("straight", "diagonal"):
        for preset in presets:
            n = sum(v for k, v in tally.items() if k[0] == facing and k[1] == preset)
            fb = sum(v for k, v in tally.items() if k[0] == facing and k[1] == preset and k[3] != "-")
            inj = sum(v for k, v in tally.items() if k[0] == facing and k[1] == preset and k[4] != "-")
            res[f"{facing}, count {preset}"] = f"{n} trials, {fb} fell back facing straight, {inj} injured"
    return res


def counts_part(rom, out, spec):
    G = Game(rom)
    counts = Counts(spec)
    tally = Counter()
    for button in ("A", "B", "Y"):
        for bi, base in enumerate(G.g.bases[:2]):
            for dy in (30, 50, 70):
                for at in (5, 15):
                    for sd in range(3):
                        r = trial(G, base, button, dy, at, 0x3000 + 131 * sd + dy + at + 7 * bi, "straight", None,
                                  counts, heavy=(button == "A"))
                        event = ("he was injured" if r["injured"] else "he went down" if r["down"] else
                                 "he flailed" if r["flail"] else "nothing")
                        tally[(button, event, r["count change"])] += 1
            lowload.breathe()
    return {str(k): v for k, v in sorted(tally.items(), key=str)}


def whistle_part(rom, out, spec):
    """Hits after the whistle (line changes On, OptLine $34C6 = 1): the same trials (A body check, Y hook / hold) with the clock stopped (gmclock $15D6 = 1
    every frame) and running, each trial kept (so the unchanged ROM's and the build's can be put side by side)."""
    G = Game(rom)
    counts = Counts(spec) if spec != "-" else None
    res = []
    for stopped in (False, True):
        for button in ("A", "Y"):
            for bi, base in enumerate(G.g.bases[:2]):
                for dy in (30, 50, 70):
                    for at in (5, 15):
                        for sd in range(3):
                            r = trial(G, base, button, dy, at, 0x5000 + 131 * sd + dy + at + 7 * bi, "straight", None,
                                      counts, heavy=(button == "A"), stopped=stopped, optline=1)
                            res.append(dict(stopped=stopped, what=button, base=bi, dy=dy, at=at, seed=sd, **r))
            lowload.breathe()
    return res


def halving_part(rom, out, spec):
    G = Game(rom)
    counts = Counts(spec)
    G.e.unserialize(G.g.bases[0])
    home = [k for k in range(6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF)]
    away = [k for k in range(6, 12) if G.w(POSITION + 2 * k) not in (0, 0xFFFF)]
    setv = {home[0]: 7, away[0]: 10, home[1]: 255}
    for k, v in setv.items():
        counts.set(G, k, v)
    p0 = G.w(PERIOD)
    G.setw(CLOCK, 1)
    last, still, run = None, 0, 0
    for f in range(60000):                 # START tapped only when the clock has stood still 5 s (real)
        G.run(1, hold=["START"] if still >= 300 and f % 60 < 4 else [])
        c = G.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        run = run + 1 if G.w(PERIOD) == p0 + 1 and still == 0 else run
        if run >= 3:                       # the next period's clock running
            break
    return {"period": [p0, G.w(PERIOD)], "set": list(setv.values()),
            "after the intermission (expected 3, 5, 127)": [counts.get(G, k) for k in setv]}


def start_part(rom, out, spec):
    """From power-on through snes_60fps_cvc's menus: junk over the counts at Game Setup, the counts when play starts."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import menu_shots as M
    import snes_60fps_cvc as cvc
    counts = Counts(spec)
    span = counts.stride + 32 * counts.size
    st = {}

    class Stop(Exception):
        pass

    orig_play, orig_mem, orig_co = M.play, cvc.Mem, cvc.computer_only

    def play(e, script, tmp):
        if script.startswith("START w240 START w200") and "m" in st:
            for a in range(counts.base, counts.base + span, 2):
                st["m"].setw(a, 0x5A5A)
        return orig_play(e, script, tmp)

    class Mem(orig_mem):
        def __init__(self, e, r):
            super().__init__(e, r)
            st["m"] = self

    def computer_only(m):
        st["first"] = sorted({m.w(a) & 0xFF for a in range(counts.base, counts.base + span)} |
                             {m.w(a) >> 8 for a in range(counts.base, counts.base + span, 2)})
        raise Stop
    M.play, cvc.Mem, cvc.computer_only = play, Mem, computer_only
    try:
        cvc.game(rom, 0, lambda e, m: {})
    except Stop:
        pass
    finally:
        M.play, cvc.Mem, cvc.computer_only = orig_play, orig_mem, orig_co
    return {"byte values over the counts at the first frame of play (junk $5A written at Game Setup)": st.get("first")}


def main():
    part, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    if part == "injuries":
        spec = sys.argv[sys.argv.index("--counts") + 1] if "--counts" in sys.argv else None
        res = injuries_part(rom, out, spec)
    else:
        res = {"counts": counts_part, "halving": halving_part, "start": start_part,
               "whistle": whistle_part}[part](rom, out, sys.argv[4])
    print(json.dumps(res, indent=1), flush=True)
    (out / f"{part}_{Path(rom).stem}.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
