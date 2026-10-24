"""One-timers in the real game (Genesis test ROM, SNES retail ROM). The passer (pad 1's skater, object / record 2)
holds the puck at P and the receiver (a teammate, 3) stands at R while the computer goalie sets himself; the passer
passes toward R (B with the d-pad pointed at him), the one-timer button (Genesis C, SNES A) is pressed at a chosen
moment of the pass, and the swing is played to the frame the game strikes the puck (doshot): on the SNES once per aim,
the d-pad held from the press (held only at the strike it changes nothing: the aim is read during the swing); the
Genesis aims one-timers itself. The strike frame is then replayed from fresh random seeds and each shot played out. Nobody else is on the ice but the two goalies; the passer and
the receiver stay where they are (the SNES result depends on who is on the ice: PROJECT_NOTES, "Frame timing")."""
import os
import math

from lowload import gentle

PASSER, RECEIVER = 2, 3
DIRS = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
        6: ["LEFT"], 7: ["UP", "LEFT"], 8: []}


def direction(dx, dy):
    """The 8-way d-pad direction (0 up the screen, clockwise) nearest to the vector (dx, dy) (y up the screen)."""
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


class Genesis:
    """Records $80 bytes from $B04A; X +0, Y +$14, Z +$18, speeds +$28 / +$2A / +$2C."""
    name, pass_button, ot_button = "genesis", "B", "C"
    GOALIE, PUCK, PUCKC, SCORE, SEED = 11, 14, 0xB7AA, 0xC6DA, 0xD066

    def __init__(self, shp=20, sha=15):
        from harness import Harness
        from paths import STATE_TOP, STATE_BOTTOM
        top = Harness(state=STATE_TOP, top=True)
        self.h = {"top": top, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top.e)}
        self.e = e = top.e
        for h in self.h.values():
            e.unserialize(h.base)
            e.setb(self.rec(RECEIVER) + 0x6C, shp)
            e.setb(self.rec(RECEIVER) + 0x6D, sha)
            h.base = e.serialize()

    def rec(self, k):
        return 0xB04A + 0x80 * k

    def put(self, k, x, y):
        e, r = self.e, self.rec(k)
        for off, v in ((0, x), (2, 0), (0x14, y), (0x16, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
            e.setw(r + off, v)

    def xy(self, k):
        return self.e.sw(self.rec(k)), self.e.sw(self.rec(k) + 0x14)

    def v(self, k):
        return self.e.sw(self.rec(k) + 0x28), self.e.sw(self.rec(k) + 0x2A)

    def set_moment(self, net, p, rnd):
        self.e.unserialize(self.h[net].base)
        self.e.setw(0xC468, 590 - (p * 3) % 8)        # the clock: 590 .. 583
        return 80 + (p * 7) % 15                       # frames to settle

    def carrier(self):
        c = self.e.w(self.PUCKC)
        return None if c & 0xFF00 else c

    def give_puck(self, k):
        self.e.setw(self.PUCKC, k)

    def strike_mark(self):
        return self.e.w(0xE010)                        # the test ROM's doshot count

    def reset_mark(self):
        pass

    def set_seed(self, seed):
        self.e.setl(self.SEED, seed)

    def state(self):
        """(puck x, y, z, vx, vy, goalie x, y, animation, goalie holds it) as goal_types."""
        e, p, g = self.e, self.rec(self.PUCK), self.rec(self.GOALIE)
        return (e.sw(p), e.sw(p + 0x14), e.sw(p + 0x18), e.sw(p + 0x28), e.sw(p + 0x2A), e.sw(g), e.sw(g + 0x14),
                e.w(g + 0x58), e.w(self.PUCKC) == self.GOALIE)

    def score(self):
        return self.e.w(self.SCORE)


class Snes:
    """Word arrays, object k at +2k."""
    name, pass_button, ot_button = "snes", "B", "A"
    GOALIE, PUCK = 11, 14

    def __init__(self, shp=13, sha=13):
        import snes_harness as H
        from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM
        self.H = H
        top = H.Harness(state=SNES_STATE_TOP, top=True)
        self.h = {"top": top, "bottom": H.Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)}
        self.e = e = top.e
        for h in self.h.values():
            e.unserialize(h.base)
            e.setw(H.SHOTSPD + 2 * RECEIVER, shp)
            e.setw(H.SHOTACC + 2 * RECEIVER, sha)
            h.base = e.serialize()

    def put(self, k, x, y):
        self.h["top"].put(k, x, y)

    def sw(self, a):
        v = self.e.w(a)
        return v - 0x10000 if v & 0x8000 else v

    def xy(self, k):
        return self.sw(self.H.XPOS + 2 * k), self.sw(self.H.YPOS + 2 * k)

    def v(self, k):
        return self.sw(self.H.XVEL + 2 * k), self.sw(self.H.YVEL + 2 * k)

    def set_moment(self, net, p, rnd):
        e, H = self.e, self.H
        e.unserialize(self.h[net].base)
        e.setw(H.CLOCK, 590 - p % 8)
        seed = rnd.getrandbits(32)                     # the SNES goalie's look-ahead uses the generator
        e.setw(H.SEED, seed >> 16 or 1)
        e.setw(H.SEED + 2, seed & 0xFFFF or 1)
        return 80 + (p * 7) % 15

    def carrier(self):
        c = self.e.w(self.H.PUCKC)
        return None if c & 0x8000 else c // 2

    def give_puck(self, k):
        self.e.setw(self.H.PUCKC, 2 * k)

    def strike_mark(self):
        return self.e.w(0x0D29)                        # shotplayer: the last object doshot ran for (x 2)

    def reset_mark(self):
        self.e.setw(0x0D29, 0xFFFF)

    def set_seed(self, seed):
        self.e.setw(self.H.SEED, seed >> 16 or 1)
        self.e.setw(self.H.SEED + 2, seed & 0xFFFF or 1)

    def state(self):
        H, P, g = self.H, 2 * self.PUCK, 2 * self.GOALIE
        return (self.sw(H.XPOS + P), self.sw(H.YPOS + P), self.sw(H.PUCKZ), self.sw(H.XVEL + P), self.sw(H.YVEL + P),
                self.sw(H.XPOS + g), self.sw(H.YPOS + g), self.e.w(H.SPA + g), self.e.w(H.PUCKC) == g)

    def score(self):
        return self.e.w(self.H.SCORE_HOME)


class OneTimer:
    def __init__(self, system):
        gentle()
        r = os.environ.get("NHL94_OT_RATINGS")            # "shp,sha": the receiver's working ratings (else the defaults)
        kw = dict(zip(("shp", "sha"), map(int, r.split(",")))) if r else {}
        self.s = Genesis(**kw) if system == "genesis" else Snes(**kw)
        self.e = self.s.e

    def park(self, keep):
        """Everyone but the goalies and `keep` well away at the far end."""
        for k in range(12):
            if k in keep or k in (5, self.s.GOALIE):
                continue
            self.s.put(k, -100 + 18 * k, self.park_y)

    def run(self, buttons=()):
        self.park((PASSER, RECEIVER))
        self.e.run(1, hold=list(buttons))

    def setup(self, net, P, R, p, rnd):
        """Passer at P with the puck, receiver at R (net coordinates: y from centre ice toward the net), the goalie
        settling for this moment's number of frames."""
        s = self.s
        self.sg = 1 if net == "top" else -1
        self.park_y = -230 * self.sg
        settle = s.set_moment(net, p, rnd)
        self.P = (P[0], self.sg * P[1])
        self.R = (R[0], self.sg * R[1])
        for _ in range(settle):
            s.put(PASSER, *self.P)
            s.put(RECEIVER, *self.R)
            s.give_puck(PASSER)
            self.run()

    def pass_to_press(self, timing, max_frames=90, by=2):
        """Pass toward the receiver and play up to the one-timer press: timing "early" (`by` frames after the puck
        leaves) or "late" (`by` frames before he would take the pass: found by playing the pass once with no press
        first; timing it by the puck's distance to his centre came too late on slower passes, after his blade, 10-13
        in front of him, had already taken it, and the press was then an ordinary shot). The game's swing has narrow
        timing holes (a long pass across whiffed at every moment pressed 6 frames before the catch, struck at 4 and
        8), so ot_run spreads `by` over the moments. Returns (the state just before the press frame, frames from the
        release to the press) or (None, why)."""
        s, e = self.s, self.e
        d = DIRS[direction(self.R[0] - self.P[0], self.R[1] - self.P[1])]
        start = e.serialize()

        def play(until):
            """Play the pass from the start; stop just before frame `until` (the press) or when he takes the puck."""
            e.unserialize(start)
            released = None
            for f in range(max_frames):
                if f == until:
                    return e.serialize(), released, f
                self.run([s.pass_button] + d if f < 4 else d)   # 4 frames: the SNES loop runs every other frame,
                if released is None and s.carrier() != PASSER:  # and a release before it reads the direction passes
                    released = f                                # the way he faces
                if released is None and f > 20:
                    return None, None, "no pass"
                if released is not None and s.carrier() == RECEIVER:
                    return None, released, f                    # he has it
            return None, released, "puck never near"

        _, released, caught = play(None)
        if released is None:
            return None, caught
        if timing == "early":
            press = released + by
        else:
            if not isinstance(caught, int):
                return None, "never taken (no late press)"
            press = max(released + 1, caught - by)
        state, released, f = play(press)
        if state is None:
            return None, "taken before the press"
        return state, press - released

    def swing(self, press, aim, max_frames=60):
        """From the press: the one-timer button for 2 frames and the aim's d-pad held (the SNES aims the strike by the
        direction held through the swing; the Genesis aims it itself, aim None) until the game strikes the puck.
        Returns (the state just before the strike frame, frames from the press) or (None, "whiff")."""
        s, e = self.s, self.e
        e.unserialize(press)
        s.reset_mark()
        mark0 = s.strike_mark()
        pad = DIRS[aim] if aim is not None else []
        for f in range(max_frames):
            pre = e.serialize()
            self.run(([s.ot_button] if f < 2 else []) + pad)
            if s.strike_mark() != mark0:
                return pre, f
        return None, "whiff"

    def strike(self, pre, aim, seed):
        """Replay the strike frame from `pre` with this seed (the aim still held)."""
        self.e.unserialize(pre)
        self.s.set_seed(seed)
        self.run(DIRS[aim] if aim is not None else [])

    def play_out(self, maxf=150):
        """GOAL, SAVED, POST or MISSED (animate.outcome's rules)."""
        from animate import outcome
        s = self.s
        s0, sign = s.score(), self.sg
        states = [s.state()]
        away = held = 0
        for f in range(maxf):
            self.run()
            st = s.state()
            if s.score() != s0:
                return outcome(states, len(states) - 1, True)
            states.append(st)
            held = held + 1 if st[8] else 0
            away = away + 1 if st[4] * sign < 0 else 0
            if held >= 20 or away >= 4 or st[1] * sign > 280:
                return outcome(states, len(states) - 1, False)
        return outcome(states, len(states) - 1, False)
