"""NOSE4Web's SNES second-assist and stick-deflection fixes, played in the game (2026-11-08, the user approved running the
patched ROMs; STUDY_NOTES "The Genesis-only fixes: does the SNES have the bug?").

- assist: in live play, the pad-1 team's touch history set as if C, then A, then B had touched the puck (tmtouch3 C,
  tmtouch2 A, tmtouch1 B; tmflags bit 2 clear), the loose puck put in front of A, who skates onto it, so the game's own
  puckglue / a2touchpuck runs as he takes it, then the puck put in the other net: the goal's scorer and assists from the game's
  scoring summary ($313C). The original drops C (A was the third touch); the fix keeps him. And a control: C, B, D
  before A (nobody twice), the same on both.
- shots: the pad-1 skater at a spot in the attacking zone with the puck (everyone else parked at the far end), a shot
  (A held 3-12 frames) with one of nine aims, 150 frames on: the team's shots on goal (the game's count by period) and
  goals, and every skater's and the puck's position each frame. The same shots on both ROMs.

python snes_assist_stick_test.py ORIGINAL FIXED [shots]   (an SA-1 or 2 MB build by its header, as faceoff_fix_test.Snes)"""
import random
import sys
from collections import Counter

from faceoff_fix_test import Snes

PUCKC, CARRIER2, PLAYERPAD, POSITION, PNUM, PFGOAL = 0x0AD9, 0x0AE7, 0x19D4, 0x0F43, 0x12A3, 0x14C3
XPOS, YPOS, XFRAC, YFRAC, XVEL, YVEL, ZPOS, ZVEL = 0x0D55, 0x0DB7, 0x0D77, 0x0DD9, 0x0EC3, 0x0EE3, 0x0DF9, 0x0E01
TOUCH1, TOUCH2, TOUCH3, TMFLAGS = 0x179A, 0x179E, 0x17A2, 0x17DE
SHOTS = (0x176A, 0x176E, 0x1772, 0x1776)
GOALS, SCORING_COUNT, SCORING_LIST, CLOCK = 0x178E, 0x313A, 0x313C, 0x1632
PUCK = 14
DIRS = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
        6: ["LEFT"], 7: ["UP", "LEFT"], None: []}


class Game:
    def __init__(self, rom):
        self.g = Snes(rom)
        self.e = self.g.e
        self.w, self.setw = self.g.w, self.g.setw
        data = open(rom, "rb").read()
        if len(data) > 0x100000:                           # the 2 MB builds: the retail states don't fit them; the
            if not self.g.sa1:                             # boot can stop on a whistle (the referee box up): play on
                self.g.bases = [self.g.boot()]             # (no buttons) until the clock runs again
            self.g.bases = [self.live(self.g.bases[0])]
            for _ in range(3):                             # more moments, each 15 s (real) of play after the last
                self.e.unserialize(self.g.bases[-1])
                self.run(900)
                self.g.bases.append(self.live(self.e.serialize()))

    def live(self, base):
        self.e.unserialize(base)
        running = 0
        for f in range(6000):
            c = self.w(CLOCK)
            self.run()
            running = running + 1 if self.w(0x15D6) == 0 and self.w(CLOCK) <= c else 0
            if running > 240 and self.w(PUCKC) < 0x8000:
                break
        return self.e.serialize()

    def sw(self, a):
        v = self.w(a)
        return v - 0x10000 if v >= 0x8000 else v

    def put(self, k, x, y, vx=0, vy=0):
        for a, v in ((XPOS, x), (YPOS, y), (XFRAC, 0), (YFRAC, 0), (XVEL, vx), (YVEL, vy)):
            self.setw(a + 2 * k, v & 0xFFFF)

    def run(self, n=1, hold=()):
        self.e.held = {self.e.PAD[b] for b in hold}
        for _ in range(n):
            self.e.lib.retro_run()
        self.e.held = set()

    def me(self):
        """The pad-1 skater, his team (0 home, 1 away) and which way he attacks (+1 the top net)."""
        k = next((k for k in range(12) if self.w(PLAYERPAD + 2 * k) == 0 and self.w(POSITION + 2 * k) not in (0, 0xFFFF)), None)
        if k is None:                                      # nobody on pad 1: give it the home centre
            k = next(k for k in range(6) if self.w(POSITION + 2 * k) == 4)
            self.setw(PLAYERPAD + 2 * k, 0)
            self.setw(0x1283 + 2 * k, self.w(0x1283 + 2 * k) | 0x0008)   # pflags: a person's
            self.setw(0x19EC, 2 * k)                                     # c1playernum
            self.setw(0x19D0, 1)                                         # teampads: one pad on Home
            self.setw(0x19F6, 0)                                         # padside: pad 1 Home
            self.setw(0x1C84, 1)                                         # cont1team: Home
        return k, k // 6, (1 if self.w(PFGOAL + 2 * k) else -1)

    def park(self, keep, up):
        for k in range(12):
            if k == keep or self.w(POSITION + 2 * k) in (0, 0xFFFF):
                continue
            self.put(k, -100 + 18 * (k % 6) + (10 if k >= 6 else 0), -230 * up)

    # --- the assist
    def assist(self, base, chain):
        e = self.e
        e.unserialize(base)
        self.setw(CLOCK, 250)
        me, team, up = self.me()
        mates = [k for k in range(team * 6, team * 6 + 6) if self.w(POSITION + 2 * k) not in (0, 0xFFFF) and k != me]
        a = me
        c, b, d = mates[0], mates[1], mates[2]
        pn = lambda k: self.w(PNUM + 2 * k)
        t = 2 * team
        hist = [pn(c), pn(a), pn(b)] if chain == "C A B, then A" else [pn(c), pn(b), pn(d)]   # oldest first
        self.setw(TOUCH3 + t, hist[0])
        self.setw(TOUCH2 + t, hist[1])
        self.setw(TOUCH1 + t, hist[2])
        self.setw(TMFLAGS + t, self.w(TMFLAGS + t) & ~4)
        self.park(a, up)
        self.put(a, 0, 120 * up)
        self.put(PUCK, 0, 150 * up)
        self.setw(PUCKC, 0xFFFF)
        self.setw(CARRIER2, 0xFFFF)
        for _ in range(120):                               # he skates onto it (pad 1 held toward it)
            self.park(a, up)
            self.run(hold=["UP"] if up > 0 else ["DOWN"])
            if self.w(PUCKC) == 2 * a:
                break
        else:
            return dict(res="no pickup")
        self.run(4)                                        # pucknorm records the carrier's touch (a2touchpuck)
        after = [self.w(TOUCH1 + t), self.w(TOUCH2 + t), self.w(TOUCH3 + t)]
        n0 = self.w(SCORING_COUNT)
        gk = next(k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if self.w(POSITION + 2 * k) == 0)
        self.setw(PUCKC, 0xFFFF)
        self.setw(CARRIER2, 0xFFFF)
        for _ in range(60):                                # the puck slid into the empty net (the goalie moved aside)
            self.put(a, 60, 150 * up)
            self.put(gk, 90, 240 * up)
            if _ == 0:
                self.put(PUCK, 0, 240 * up, 0, 0x2000 * up)
            self.run()
            if self.w(SCORING_COUNT) != n0:
                break
        else:
            return dict(res="no goal", touches=after)
        entry = SCORING_LIST + self.w(SCORING_COUNT) - 6
        scorer, a1, a2 = (self.g.at(entry + 3 + i)[0][self.g.at(entry + 3 + i)[1]] for i in range(3))
        names = {pn(k) & 0xFF: n for k, n in ((a, "A"), (b, "B"), (c, "C"), (d, "D"))}
        nm = lambda v: names.get(v, "none" if v == 0xFF else f"#{v}")
        return dict(res="goal", scorer=nm(scorer), assists=[nm(a1), nm(a2)],
                    touches=[names.get(v & 0xFF, v) for v in after])

    # --- the shots
    def shot(self, base, rnd):
        e = self.e
        e.unserialize(base)
        self.setw(CLOCK, 250)
        me, team, up = self.me()
        x, y = rnd.choice((-50, -25, 0, 25, 50)), up * rnd.choice((120, 150, 180, 205))
        aim, hold = rnd.choice(list(DIRS)), rnd.choice((3, 6, 9, 12))
        for _ in range(60):
            self.put(me, x, y)
            self.park(me, up)
            self.setw(PUCKC, 2 * me)
            self.setw(CARRIER2, 2 * me)
            self.run()
        shots = lambda: sum(self.w(a + 2 * team) for a in SHOTS)
        s0, g0 = shots(), self.w(GOALS + 2 * team)
        for f in range(60):
            self.park(me, up)
            self.run(hold=(["A"] if f < hold else []) + DIRS[aim])
            if self.w(PUCKC) >= 0x8000:
                break
        else:
            return None
        path = []
        for f in range(150):
            self.park(me, up)
            self.run()
            path.append(tuple(self.w(a + 2 * k) for k in (*range(12), PUCK) for a in (XPOS, YPOS)))
        return dict(shots=shots() - s0, goals=self.w(GOALS + 2 * team) - g0, path=path)


def main():
    orig, fixed = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    out = {}
    for name, rom in (("original", orig), ("fixed", fixed)):
        gm = Game(rom)
        base = gm.g.bases[0]
        print(name, rom.split("/")[-1])
        for chain in ("C A B, then A", "C B D, then A"):
            print("  ", chain, gm.assist(base, chain))
        out[name] = [gm.shot(gm.g.bases[i % len(gm.g.bases)], random.Random(i)) for i in range(n)]
    pairs = [(a, b) for a, b in zip(out["original"], out["fixed"]) if a and b]
    c = Counter()
    for a, b in pairs:
        same = next((f for f in range(150) if a["path"][f] != b["path"][f]), None)
        c[(b["shots"] - a["shots"], a["goals"], b["goals"], "same play" if same is None else "drifted")] += 1
    print(f"shots: {len(pairs)}; on goal original {sum(a['shots'] for a, _ in pairs)}, fixed {sum(b['shots'] for _, b in pairs)}; "
          f"goals {sum(a['goals'] for a, _ in pairs)} / {sum(b['goals'] for _, b in pairs)}")
    for k, v in sorted(c.items(), key=lambda t: -t[1]):
        print(f"   {v:4}  shots +{k[0]}, goals {k[1]} / {k[2]}, {k[3]}")


if __name__ == "__main__":
    main()
