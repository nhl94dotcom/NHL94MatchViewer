"""NOSE4Web's SNES penalty-shot fix (bug 27), played in the game (2026-11-08, the user approved running the patched
ROMs). Two whistles during an attempt don't end it (no EndPenaltyShotPlay), so penshot stays 1 and the next faceoff
sets up the penalty shot again from where the shooter stands: checkgoalp's knocked-off net (PenGhold) and pucknorm's
still puck (PenOOP, a loose puck at exactly the same spot for 120 frames). The fix calls EndPenaltyShotPlay first in
both.

The penalty shot is awarded as the game does after PenShotChk (BA_Sktr_SCnum, pspad, a PenBuf entry PenShot $24 on
the fouler); the shooter is pad 1's skater and nobody presses anything, so he stands with the puck. Once the attempt
is live (penshotlive 1, the clock running):
- net: he is put 20-60 units beside the net he attacks, level with it, in the burst animation (SPA $F342, as A
  without the puck starts it; the 2 MB builds' own word through snes_layout), skating into its side at $2400-$3400, both every frame until he meets it. checkgoalp
  knocks it off when seed & $01C0 is 0 (one meeting in eight); trials where it stays on are reported apart. At the
  whistle the puck is stopped where it is (he loses it at the net, and a loose puck sliding on into the boards ends
  the attempt through wallcoll even after the whistle: what happens when he keeps it, or it stops short).
- still: the puck is put loose 60 units in front of him, still, with puckvy $40 forward every frame
  (the sign pucknorm counts as forward: the other if pspuckback counts; too little to move it a unit)
  (pucknorm's other rule, pspuckback, ends an attempt after 48 frames of a loose puck not going forward, so a puck
  that is truly still ends it that way first: this case needs a puck held in place while "going forward", as one
  pinned against something might be), until the whistle.
After the whistle, when play resumes (gmclock 0): another attempt (penshotlive 1) is a retake, else a faceoff.

python snes_ps_fixes_test.py RUN ROM [N]   -> paths.RUNS / RUN / trials.jsonl (an SA-1 ROM is told by its header)
python snes_ps_fixes_test.py report RUN [RUN]"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

from faceoff_fix_test import Snes
from lowload import breathe, gentle
from paths import RUNS

PENBUF, BA_SKTR, PSPAD, PENSHOT, PSACTIVE, PSLIVE, GMCLOCK, GMODE = 0x15DE, 0x1E8D, 0x1E93, 0x1E9B, 0x163A, 0x1E9D, 0x15D6, 0x15D4
PUCKC, PLAYERPAD, SEED, PFGOAL = 0x0AD9, 0x19D4, 0x0792, 0x14C3
XPOS, YPOS, XFRAC, YFRAC, XVEL, YVEL, SPA, POSITION = 0x0D55, 0x0DB7, 0x0D77, 0x0DD9, 0x0EC3, 0x0EE3, 0x11A3, 0x0F43
PUCK, NETS = 14, (12, 13)
PSPUCKBACK = 0x3450                     # pucknorm's count of frames a loose puck is not going forward
SPABURST = 0xF342


class Game:
    def __init__(self, rom):
        self.g = Snes(rom)
        self.e = self.g.e
        self.w, self.setw = self.g.w, self.g.setw
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "systems"))
        from snes_layout import layout
        self.burst = layout(Path(rom).read_bytes()).rom_spa(SPABURST)   # the 2 MB builds moved the animations

    def sw(self, a):
        v = self.w(a)
        return v - 0x10000 if v >= 0x8000 else v

    def run(self, n=1):
        for _ in range(n):
            self.e.lib.retro_run()

    def until(self, test, frames):
        for f in range(frames):
            self.run()
            if test():
                return f
        return None

    def award(self, base, seed):
        """Returns (shooter, the y direction he attacks) once the attempt is live, or None."""
        self.e.unserialize(base)
        self.setw(SEED, seed & 0xFFFF)
        self.setw(SEED + 2, seed >> 16)
        shooter = next((k for k in range(12) if self.w(PLAYERPAD + 2 * k) < 0x8000 and self.w(POSITION + 2 * k)), 2)
        fouler = next(k for k in (range(6, 12) if shooter < 6 else range(6)) if self.w(POSITION + 2 * k))
        self.setw(BA_SKTR, 2 * shooter)
        self.setw(PSPAD, self.w(PLAYERPAD + 2 * shooter) if self.w(PLAYERPAD + 2 * shooter) < 0x8000 else 0)
        self.setw(PENBUF, fouler << 8 | 0x24)
        self.setw(PENBUF + 2, 0)
        self.setw(GMCLOCK, 0)
        self.setw(GMODE, self.w(GMODE) & ~0x000C)
        if self.until(lambda: self.w(PSLIVE) and not self.w(GMCLOCK), 3000) is None:
            return None
        self.run(20)
        if not self.w(PSLIVE) or self.w(PUCKC) >= 0x8000:
            return None
        shooter = self.w(PUCKC) // 2                       # the shooter has the puck (the SA-1 build sets the attempt
        return shooter, (1 if self.w(PFGOAL + 2 * shooter) else -1)   # up with him in another object)

    def target_net(self, up):
        return max(NETS, key=lambda n: up * self.sw(YPOS + 2 * n))

    def outcome(self, extra, tag_boards=True):
        """After a whistle (gmclock set): play on until it runs again. Whether the attempt was ended on the way by
        the loose puck meeting the boards (wallcoll's EndPenaltyShotPlay: penshot to 0 with a $0A entry on the
        puck, object 14), which ends it whatever the whistle. Not for the still puck: there the fix's own
        EndPenaltyShotPlay (X the puck) writes that same entry."""
        boards = False
        for _ in range(4000):
            self.run()
            boards = boards or (self.w(PENSHOT) == 0 and any(self.w(PENBUF + 2 * j) & 0x7FFF == 0x0E0A for j in range(4)))
            if not self.w(GMCLOCK):
                break
        else:
            return dict(res="play never resumed", **extra)
        self.run(5)
        res = "retake" if self.w(PSLIVE) else "faceoff (the puck met the boards)" if boards and tag_boards else "faceoff"
        return dict(res=res, penshot=self.w(PENSHOT), **extra)

    def net(self, base, rnd):
        a = self.award(base, rnd.getrandbits(32))
        if a is None:
            return dict(res="no attempt")
        k, up = a
        n = self.target_net(up)
        nx, ny = self.sw(XPOS + 2 * n), self.sw(YPOS + 2 * n)
        side = rnd.choice((-1, 1))
        self.setw(XPOS + 2 * k, (nx + side * rnd.randint(20, 60)) & 0xFFFF)
        self.setw(YPOS + 2 * k, ny & 0xFFFF)
        speed = rnd.randint(0x2400, 0x3400)
        net_off, entry = False, None
        moved = lambda: (self.sw(XPOS + 2 * n), self.sw(YPOS + 2 * n)) != (nx, ny)
        for f in range(90):
            self.setw(SPA + 2 * k, self.burst)
            self.setw(XVEL + 2 * k, (-side * speed) & 0xFFFF)
            self.setw(YVEL + 2 * k, 0)
            self.run()
            if self.w(GMCLOCK) or moved():
                entry = hex(self.w(PENBUF))
                for _ in range(5):                         # the knocked net starts moving a frame or two later; the
                    self.setw(XVEL + 2 * PUCK, 0)          # puck stopped where it is (a loose puck sliding on into the
                    self.setw(YVEL + 2 * PUCK, 0)          # boards ends the attempt there, wallcoll, even after it)
                    self.run()
                net_off = moved()
                break
            if abs(self.sw(XPOS + 2 * k) - nx) < 6:
                break
        if not net_off:                                    # (another whistle first: the attempt's own end, $0A)
            return dict(res="net stayed on" if not self.w(GMCLOCK) else "other whistle", net=n, entry=entry)
        return self.outcome(dict(net=n, entry=entry, frames=f))

    def still(self, base, rnd):
        a = self.award(base, rnd.getrandbits(32))
        if a is None:
            return dict(res="no attempt")
        k, up = a
        px, py = self.sw(XPOS + 2 * k) + rnd.randint(-30, 30), self.sw(YPOS + 2 * k) + up * 60
        self.setw(PUCKC, 0xFFFF)
        vy = -up * 0x40
        for f in range(200):
            if f == 3 and self.w(PSPUCKBACK) >= 2:         # counting: the other sign is "forward" here
                vy = -vy
            self.setw(XPOS + 2 * PUCK, px & 0xFFFF)
            self.setw(YPOS + 2 * PUCK, py & 0xFFFF)
            self.setw(XFRAC + 2 * PUCK, 0x8000)              # mid-unit: the creep (either sign) stays in it
            self.setw(YFRAC + 2 * PUCK, 0x8000)
            self.setw(XVEL + 2 * PUCK, 0)
            self.setw(YVEL + 2 * PUCK, vy & 0xFFFF)
            self.setw(XPOS + 2 * k, (px + 50) & 0xFFFF)     # the shooter kept away from it
            self.setw(YPOS + 2 * k, (py - up * 40) & 0xFFFF)
            self.run()
            if self.w(GMCLOCK):
                return self.outcome(dict(entry=hex(self.w(PENBUF)), frames=f, live_at_whistle=self.w(PSLIVE),
                                         penshot_at_whistle=self.w(PENSHOT)), tag_boards=False)
            if not self.w(PENSHOT) and f < 100:
                return dict(res="attempt ended first", frames=f)
        return dict(res="no whistle", pspuckback=self.w(PSPUCKBACK), penshot=self.w(PENSHOT), live=self.w(PSLIVE),
                    puck=(self.sw(XPOS + 2 * PUCK), self.sw(YPOS + 2 * PUCK)), puckc=hex(self.w(PUCKC)))


def main():
    run, rom = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    out = RUNS / run
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    gm = Game(rom)
    with open(out / "trials.jsonl", "w") as fh:
        for i in range(n):
            for case in ("net", "still"):
                r = getattr(gm, case)(gm.g.bases[i % len(gm.g.bases)], random.Random(7000 + 13 * i))
                r.update(i=i, case=case)
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                breathe()
    print("done", flush=True)


def report(runs):
    for run in runs:
        rows = [json.loads(l) for l in open(RUNS / run / "trials.jsonl")]
        print(f"{run}:")
        for case in ("net", "still"):
            print(f"  {case}: {dict(Counter(r['res'] for r in rows if r['case'] == case))}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        main()
