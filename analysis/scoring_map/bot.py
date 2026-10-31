"""A scripted NHL '94 player (Genesis), 2026-10-31: the user's scoring moves played by rules read from the game's
memory each frame. It plays Home on pad 1 against the computer; bot_run.py plays whole games with it in the harness.
Reads only (any object with the emulator's b / w / sw readers), so the same bot can later drive RetroArch through a
virtual pad.

Offence (the bot's skater has the puck): the deke (SCORING_GENESIS_DEKES; deke_run.py plan "best", the set-ups that
scored 82-96% standing in): skate to the gate (45 to the attacker's left, 140 up the ice: 124 out from the goal line),
then up and right at the net drifting toward the middle; once within D of the goalie swing the d-pad up and left,
and `lag` frames later tap C with Left held (a wrist shot at that side). Left-handers D 60, lag 10; right-handers
D 60, lag 13. A carrier caught off the gate's line (too far up the ice or across) circles back out to it. Under
pressure (an opponent within PRESSURE, ahead of him) inside the attacking zone he takes the Down slapshot instead;
in his own half he keeps going. In close (200+ up the ice) off the deke's line, a wrist shot at the half of the net
away from the goalie. After a shot he chases the rebound. Our goalie with the puck (manual goalies) passes it out.
Versions (Bot(team, version)): 1 the above; 2 adds the one-timer (a teammate open in the slot with a clear lane: B
toward him, C while the puck travels) and skips the deke when a defender is near its line (slapshot instead); 3 the
one-timer with every deke; 4 3 with the deke's entry steered onto the standing set-up's path (on the
lane by the red line, 0.5 a frame across toward the middle at the gate, 0.77 at the swing: bot_deke_check.py found
the deke needs it) and no slapshot under pressure before the gate; 5 real one-timers (C as the pass arrives); 6 the
deke re-timed with everyone on the ice; 7-8 (work in progress, STUDY_NOTES "A scripted bot") the EA
Special (EA) in place of the deke: skate its line, release at the EA runs' best spot, follow up at the near post (8
swings out to the wing to come in on the line); 9 is 6 with a left-hander slowed by a defender at the swing (under
1.3 a frame up the ice, one within 25) passing or wrist-shooting instead; 10 is 9 taking the puck around his own net (not into its back) and veering
up and away from an opponent closing in ahead before the gate (fewer dekes: worse); 11 is 9 with only the
way around his own net; 12 is 11 with a right-hander who comes up the right
side deking there (mirrored, DEKE12R); 13 is 11 (not 12) with the one-timer as people play
it (the pass from 100 up the ice, to a receiver within 100 of the goal line and 70 of the middle, 39-110 across); 14 is 13 with people's
limits on the pass (the passer within 120 of the goal line, the pass under 130 long, no defender within 20 of
the receiver); 15 is 14 passing only to a receiver within 40 of the
middle with the goalie drawn 4+ toward the passer's side; 16 (the default) is 15 without the slapshot under pressure and
with the close-in wrist shot from 170 up the ice (WRIST16; a limit across, cutting in to the middle first, scored
less the narrower it was); 17 is 16 with, in close and off the middle, the slapshot wind-up that
drops the goalie, released at his own side (CLOSE17).
Without the puck: at a faceoff mash B with the d-pad toward his own net; otherwise skate at the carrier from his
goal side (or at a loose puck's spot a few frames ahead), burst-check (C) when close and closing, poke (B) from
POKE; B also switches when a teammate is much nearer the puck. The goalie is the computer's.

Positions in the attacker's view: ax = s x, ay = s y, s = +1 attacking the top net (y +268), -1 the bottom."""
import math

BASE, SZ = 0xB04A, 0x80
PUCK = 14
PUCKC = 0xB7AA
NET_Y = 264
DIRS = ["UP", ["UP", "RIGHT"], "RIGHT", ["DOWN", "RIGHT"], "DOWN", ["DOWN", "LEFT"], "LEFT", ["UP", "LEFT"]]
ARRIVE = 14            # version 5: the one-timer's C this many frames before the pass arrives
PRESSURE = 24          # units (3 to a foot)
POKE = 26
DEKE = {"L": dict(D=60, lag=10), "R": dict(D=60, lag=13)}
# version 6: re-timed with every skater on the ice (the runs' timings were found with the others taken off, and then a
# right-hander turns faster): 24 tries each, left-handers 23 (lag 10: 20), right-handers 23 (lag 13: 1)
DEKE6 = {"L": dict(D=60, lag=13), "R": dict(D=60, lag=16)}
# version 12: the right-hander's deke on the right side, mirrored (swing up and right, C with Right): the deke runs'
# swing at 85, C 13 frames on; with everyone on the ice 12 of 12 (bot_deke_check.py, NHL94_DEKE_SIDE=right)
DEKE12R = {"R": dict(D=85, lag=13), "L": dict(D=85, lag=13)}
GATE = (-45, 140)
SHOOT_ANIMS = (0x07FC, 0x092E)       # the shooting swing (genesis.py "shoot")
LANE = (40, -55)        # version 4: on the lane (55 to the left) by 40 up the ice
# version 7: the EA Special (SCORING_GENESIS_EA, ea_run.py BEST17): the release spot (a right-hander from his left;
# mirrored for a left-hander) and the line he skates in on, per net (s: +1 the top net). Top: 23 ft out, 28 ft to the
# side, in at 45 degrees; bottom: 17 ft out, 29 ft to the side, at the middle of the goal line. 1.7 a frame; the first
# shot aimed across (Right for him), the follow-up at the near post
EA = {1: dict(R=(-84, 196), u=(0.7071, 0.7071)), -1: dict(R=(-88, 212), u=(0.8608, 0.5087))}
EA_SPEED = 1.7
# version 17: the close-in wind-up (in close past ay up the ice, more than side off the middle, C held hold frames);
# env NHL94_CLOSE17="ay,side,hold"
CLOSE17 = dict(ay=200, side=20, hold=12)
# version 16: the close-in wrist shot's zone (within mid of the middle, past ay up the ice); env NHL94_WRIST16="mid,ay"
WRIST16 = dict(mid=140, ay=170)                     # 140: no limit across (best: below)
EA_TUNE = dict(wing=-110, turnL=80, turnR=105, look=20)   # version 8's approach (bot_ea_check.py "wing"; env
import os as _os                                           # NHL94_EA_TUNE="wing,turnL,turnR,look")
if _os.environ.get("NHL94_CLOSE17"):
    CLOSE17 = dict(zip(("ay", "side", "hold"), map(float, _os.environ["NHL94_CLOSE17"].split(","))))
if _os.environ.get("NHL94_WRIST16"):
    WRIST16 = dict(zip(("mid", "ay"), map(float, _os.environ["NHL94_WRIST16"].split(","))))
if _os.environ.get("NHL94_EA_TUNE"):
    EA_TUNE = dict(zip(("wing", "turnL", "turnR", "look"), map(float, _os.environ["NHL94_EA_TUNE"].split(","))))


def rec(k):
    return BASE + k * SZ


def pad(d):
    """Screen direction 0-7 (0 up, clockwise) to buttons."""
    v = DIRS[d % 8]
    return list(v) if isinstance(v, list) else [v]


def dir_to(dx, dy):
    """The nearest of the 8 screen directions toward (dx, dy) (y up the screen)."""
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


class Bot:
    def __init__(self, team=0, version=16):
        self.version = version                      # 1: the deke, slapshot and close-in shot only (bot1);
        self.struck = -999
        self.deke = DEKE6 if version >= 6 else DEKE
        self.swing_had = {}
        self.mate = None                            # 2: the deke only on a clear path, and the one-timer (bot2);
                                                    # 3: every deke, and the one-timer (bot3);
                                                    # 4: 3 with the deke's entry steered to the standing set-up's
                                                    # path (bot4); 5: 4 with the one-timer only to a receiver
                                                    # close in, the pass across (bot5); 6: 5 with the deke
                                                    # re-timed with everyone on the ice (bot6);
                                                    # 7-8 the EA Special; 9 6 with the slowed
                                                    # left-hander's bail-out (bot9); 10-11 his own
                                                    # net (bot10, bot11)
        self.team = team                            # 0 Home (records 0-5), 1 Away (6-11)
        self.mine = range(6) if team == 0 else range(6, 12)
        self.theirs = range(6, 12) if team == 0 else range(6)
        self.phase = "free"
        self.t = 0                                  # frames in this phase
        self.frame = 0
        self.log = []                               # (frame, event, details)
        self.b_down = False
        self.stuck, self.last = 0, (0, 0)            # set on each carry (a received pass can start one first)

    # --- reading
    def read(self, e):
        P = {}
        for k in list(range(12)) + [PUCK]:
            r = rec(k)
            P[k] = dict(x=e.sw(r), y=e.sw(r + 0x14), z=e.sw(r + 0x18), vx=e.sw(r + 0x28) / 4096, vy=e.sw(r + 0x2A) / 4096,
                        pos=e.b(r + 0x35), flags=e.b(r + 0x62), face=e.b(r + 0x55) & 7, left=e.b(r + 0x76) & 1,
                        anim=e.w(r + 0x58))
        own = e.w(PUCKC)
        return P, (own if own < 12 else None)

    # --- deciding
    def step(self, e):
        """The buttons to hold this frame."""
        self.frame += 1
        P, owner = self.read(e)
        me = next((k for k in self.mine if P[k]["flags"] & 8), None)
        if me is None:
            return []
        # a one-timer struck: a teammate in a shooting swing he began without the puck, the puck hit away from him
        pk = P[PUCK]
        for k in self.mine:
            swing = P[k]["anim"] in SHOOT_ANIMS
            if swing and k not in self.swing_had:
                self.swing_had[k] = owner == k              # the swing began: with the puck or without
            elif not swing:
                self.swing_had.pop(k, None)
            if swing and not self.swing_had[k] and owner != k and self.frame - self.struck > 30 \
                    and math.hypot(pk["x"] - P[k]["x"], pk["y"] - P[k]["y"]) < 25 \
                    and math.hypot(pk["vx"], pk["vy"]) > 1.2:
                self.struck = self.frame
                g = next((j for j in self.theirs if P[j]["pos"] == 0), self.theirs[-1])
                sg = 1 if P[g]["y"] > 0 else -1
                self.log.append(dict(f=self.frame, ev="strike", by=k, x=sg * P[k]["x"], y=sg * P[k]["y"],
                                     gx=sg * P[g]["x"], gy=sg * P[g]["y"], v=round(math.hypot(pk["vx"], pk["vy"]), 2)))
        their_goalie = next((k for k in self.theirs if P[k]["pos"] == 0), self.theirs[-1])
        s = 1 if P[their_goalie]["y"] > 0 else -1           # the net we attack
        if owner == me and P[me]["pos"] == 0:
            # our goalie has it (manual goalies: the pad drives him): pass to the nearest teammate after a moment
            self.t = self.t + 1 if self.phase == "goalie" else 0
            self.phase = "goalie"
            mate = min((math.hypot(P[k]["x"] - P[me]["x"], P[k]["y"] - P[me]["y"]), k) for k in self.mine if k != me)[1]
            d = dir_to(P[mate]["x"] - P[me]["x"], P[mate]["y"] - P[me]["y"])
            return (["B"] if 20 <= self.t < 23 else []) + pad(d)
        if self.phase == "goalie":
            self.phase, self.t = "free", 0
        if self.phase == "shot" and getattr(self, "c_left", 0) > 0:
            self.c_left -= 1                                # the one-timer's C, held 3 frames
            self.t += 1
            return ["C"] + pad(dir_to(0, s))
        if self.phase in ("ea", "ea2") and owner is None and self.t > 1:
            kind = "ea" if self.phase == "ea" else "ea follow"
            self.note("shot", kind=kind)                    # the first shot (or the follow-up) has left
            if kind == "ea":
                self.phase = "eaf"
        if self.phase == "eaf":                             # after the first shot: at the puck, the follow-up
            self.t += 1
            if owner == me:
                self.phase, self.t = "ea2", 0
            elif owner is not None or self.t > 70:
                self.log.append(dict(f=self.frame, ev="ea end", owner=owner, t=self.t,
                                     goalie=owner is not None and P[owner]["pos"] == 0))
                self.phase, self.t = "shot", 91
            else:
                return pad(dir_to(pk["x"] + 4 * pk["vx"] - P[me]["x"], pk["y"] + 4 * pk["vy"] - P[me]["y"]))
        if owner == me and self.phase == "shot" and self.t < 15:
            self.t += 1                                     # the shot hasn't left the stick yet
            return []
        if owner == me:
            out = self.offence(P, me, s, their_goalie)
        elif self.phase == "pass" and self.t < 70 and owner is None:
            self.t += 1                                     # the pass is on its way
            d = dir_to(0, s)                                # the d-pad toward the net while it travels
            if self.version < 5:                            # C at once (versions 2-4: the swing was over before
                if self.t == 8:                             # the puck came: no one-timer ever struck)
                    self.note("shot", kind="pass")
                return (["C"] if self.t < 12 else []) + pad(d)
            # C once the puck is about ARRIVE frames from the receiver (control passes to him as it leaves)
            r = P[me] if me != self.passer else P[self.mate]
            dx, dy = r["x"] - pk["x"], r["y"] - pk["y"]
            dist = math.hypot(dx, dy) or 1
            closing = ((pk["vx"] - r["vx"]) * dx + (pk["vy"] - r["vy"]) * dy) / dist
            if dist < 24 or closing > 0.3 and dist / closing < ARRIVE:
                self.note("shot", kind="pass")             # the pass for a one-timer (a "strike" if he swings)
                self.c_left = 3
            return pad(d)
        else:
            if self.phase not in ("free", "shot"):
                self.note("lost", phase=self.phase, carrier=owner, t=self.t, ax=round(s * P[me]["x"]), ay=round(s * P[me]["y"]))
            elif self.phase == "shot" and self.t > 90:
                self.phase = "free"
            self.t += 1
            out = self.defence(P, me, owner, s)
        return out

    def note(self, what, **kw):
        self.log.append(dict(f=self.frame, ev=what, **kw))
        if what in ("lost", "shot"):
            self.phase, self.t = ("shot" if what == "shot" else "free"), 0

    def offence(self, P, me, s, g):
        m = P[me]
        ax, ay = s * m["x"], s * m["y"]
        gx, gy = P[g]["x"], P[g]["y"]
        hand = "L" if m["left"] else "R"
        # version 12: a right-hander who comes up the right side dekes there, the set-up mirrored (his forehand
        # deke, DEKE12R: the deke runs' 57-66%, the game favouring swings to the shooter's own left); 11 always
        # crossed to the left and was checked on the way. A left-hander's swing to his right doesn't get the puck
        # across, so left-handers still cross
        if self.version == 12 and (ay < LANE[0] or self.phase in ("free", "shot")):
            self.side = -1 if ax > 10 and hand == "R" else 1
        mx = getattr(self, "side", 1) if self.version == 12 else 1
        ax = mx * ax
        deke = self.deke if mx > 0 else DEKE12R
        vxa = mx * s * m["vx"]                      # across speed toward the middle (left side's view)
        aview = lambda d: (d if mx > 0 else (8 - d) % 8) if s > 0 else ((d if mx > 0 else (8 - d) % 8) + 4) % 8
        if self.phase in ("free", "shot"):
            self.phase, self.t = "carry", 0
            self.last, self.stuck = (m["x"], m["y"]), 0
            self.note("carry", ay=ay)
        self.t += 1
        # pressure: the nearest opponent skater ahead of him (toward the net)
        near = min((math.hypot(P[k]["x"] - m["x"], P[k]["y"] - m["y"]), k) for k in self.theirs if k != g)
        ahead = s * (P[near[1]]["y"] - m["y"]) > -5
        if self.phase in ("ea", "ea2") and self.t > 15:
            self.phase, self.t = "carry", 0         # it never left the stick
        if self.phase == "ea2":                     # claimed the loose puck: at once at the near post
            near = 2 if m["x"] > 0 else 6           # (screen: the side of the net he is on)
            return (["C"] if self.t <= 3 else []) + pad(near)
        if self.phase == "ea":                      # the first shot: C 3 frames, aimed across, held until it leaves
            return (["C"] if self.t <= 3 else []) + pad(aview(self.ea_dir(2, hand)))
        if self.phase == "carry":
            moved = math.hypot(m["x"] - self.last[0], m["y"] - self.last[1]) if self.t % 30 == 0 else None
            if moved is not None:
                self.stuck = self.stuck + 1 if moved < 4 else 0
                self.last = (m["x"], m["y"])
            if self.stuck >= 2:                     # pinned (against the goalie or the boards): go sideways
                self.stuck = 0 if self.t % 30 == 29 else self.stuck
                return pad(aview(2 if ax < 0 else 6))
            if self.version in (7, 8):
                ea = self.ea_carry(m, s, ax, ay, hand, near, ahead)
                if ea is not None:
                    return ea
            if self.version >= 16 and WRIST16["ay"] < ay < NET_Y and abs(ax) >= WRIST16["mid"]:
                # version 16: in close but off to the side (the bot's wrist shots from there: 7%): cut in toward the
                # middle of the slot first (people's wrist-shot goals came from within 30 of the middle)
                return pad(aview(dir_to(-ax, max(0, 215 - ay) + 5)))
            if self.version >= 17 and CLOSE17["ay"] < ay < NET_Y - 10 and abs(ax) > CLOSE17["side"]:
                # version 17: in close and off the middle, the slapshot wind-up that drops the computer goalie into
                # a pad stack sliding to the middle (GENESIS_GUIDE 6: 37% when he dropped), released at his own side
                self.phase, self.t = "close", 0
                self.note("close start", ax=ax, ay=ay)
            elif (WRIST16["ay"] < ay < NET_Y - 10 and abs(ax) < WRIST16["mid"]) if self.version >= 16 else 200 < ay < NET_Y:
                self.phase, self.t = "wrist", 0     # in close off the deke's line: a wrist shot away from the goalie
                self.note("wrist start", ax=ax, ay=ay)
            elif near[0] < PRESSURE and ahead and ay > (GATE[1] + 35 if self.version >= 4 else 90)                     and self.version < 16:          # version 16: no slapshot under pressure (about none went in)
                self.phase, self.t = "slap", 0
                self.note("slap start", ax=ax, ay=ay)
            elif self.version >= 2 and ay > (144 if self.version >= 14 else 100 if self.version >= 13 else 150 if self.version >= 5 else 90) \
                    and self.open_mate(P, me, s, g) is not None:
                self.mate = self.open_mate(P, me, s, g)
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay)
            elif GATE[1] - 15 < ay < GATE[1] + 35 and abs(ax - GATE[0]) < 22 and s * m["vy"] > 1.2 \
                    and self.version == 2 and self.blocked(P, me, s, g):
                self.phase, self.t = "slap", 0     # a defender on the deke's line: the slapshot from the gate
                self.note("slap start", ax=ax, ay=ay, blocked=True)
            elif self.version >= 4 and GATE[1] - 15 < ay < GATE[1] + 35 and abs(ax - GATE[0]) < 16                     and 0.2 < vxa < 0.9 and s * m["vy"] > 1.5:
                self.phase, self.t = "drive", 0     # entering the gate as the standing set-up did
                self.note("deke start", ax=ax, ay=ay, v=round(math.hypot(m["vx"], m["vy"]), 2), hand=hand)
            elif self.version < 4 and GATE[1] - 15 < ay < GATE[1] + 35 and abs(ax - GATE[0]) < 22                     and s * m["vy"] > 1.2:
                self.phase, self.t = "drive", 0
                self.note("deke start", ax=ax, ay=ay, v=round(math.hypot(m["vx"], m["vy"]), 2), hand=hand)
            else:
                tx, ty = GATE
                if ay > GATE[1] - 15:               # past the gate's line or off it: swing back out to it
                    tx, ty = GATE[0] - 20, GATE[1] - 70
                elif self.version == 10 and near[0] < 30 and ahead and ay < GATE[1] - 15 and not ay < -250:
                    # version 10: an opponent closing in ahead before the gate: up the ice and away from him
                    # (9 carried in a straight line up its lane and was checked there), off the boards
                    oxa = s * (m["x"] - P[near[1]]["x"])
                    side = 1 if (oxa > 0 or ax < -95) and ax < 95 else 7
                    return pad(aview(side))
                elif self.version >= 10 and ay < -250 and abs(ax) < 55:
                    tx, ty = (-80 if ax <= 0 else 80), ay + 10   # version 10: behind (or at) his own net: around
                                                    # it first (9 skated into its back and lost the puck there)
                elif self.version >= 4 and ay < LANE[0]:
                    tx, ty = LANE[1], ay + 80       # far away: onto the lane, wide of the gate
                elif self.version >= 4:
                    # up the lane to the gate, building the drift toward the middle (0.5 a frame at the gate)
                    k = min(1.0, max(0.0, (ay - LANE[0]) / (GATE[1] - 15 - LANE[0])))
                    want = 0.5 * k + 0.03 * (LANE[1] + (GATE[0] - LANE[1]) * k - ax)
                    return pad(aview(1 if vxa < want - 0.12 else 7 if vxa > want + 0.12 else 0))
                elif ay < GATE[1] - 60:             # far away: head up the ice toward the gate's lane
                    ty = ay + 80
                d = dir_to(tx - ax, ty - ay)
                return pad(aview(d))
        if self.phase == "drive":
            dg = math.hypot(m["x"] - gx, m["y"] - gy)
            if dg <= deke[hand]["D"] and self.version >= 9 and hand == "L" and s * m["vy"] < 1.3                     and near[0] < 25:
                # version 9: a left-hander slowed by a defender on him (version 6: 1 goal in 43 such swings): pass to
                # an open teammate close in, else the wrist shot away from the goalie
                mate = self.open_mate(P, me, s, g)
                if mate is not None:
                    self.mate, self.phase, self.t, self.passer = mate, "pass", 0, me
                    self.note("pass start", ax=ax, ay=ay, bail=True)
                else:
                    self.phase, self.t = "wrist", 0
                    self.note("wrist start", ax=ax, ay=ay, bail=True)
                return pad(aview(0))
            if dg <= deke[hand]["D"]:
                self.phase, self.t = "swing", 0
                self.note("swing", dg=round(dg), ax=round(ax), ay=round(ay), vx=round(vxa, 2), vy=round(s * m["vy"], 2),
                          near=round(near[0]))
            elif self.version >= 4:                 # the standing set-up's path: 0.5 across at the gate, 0.77 at
                want = 0.5 + (ay - GATE[1]) * 0.0054  # the swing (holding up-right; slower to turn with the puck)
                return pad(aview(1 if vxa < want else 0))
            else:
                return pad(aview(1))                # up and right at the net
        if self.phase == "swing":
            lag = deke[hand]["lag"]
            if self.t < lag:
                return pad(aview(7))                # up and left
            if self.t < lag + 4:
                return ["C"] + pad(aview(6))        # wrist shot with Left held
            self.note("shot", kind="deke")
            return pad(aview(6))
        if self.phase == "pass" and (me == self.mate or self.t > 4):
            self.phase, self.t = "carry", 0         # he took it without a one-timer (or the pass never left)
            self.note("pass kept")
            return pad(aview(0))
        if self.phase == "pass":                    # B toward him, then C while the puck travels: the one-timer
            mt = P[self.mate]
            d = dir_to(mt["x"] - m["x"], mt["y"] - m["y"])
            return (["B"] if self.t < 3 else []) + pad(d)
        if self.phase == "wrist":
            side = 2 if mx * s * P[g]["x"] < 0 else 6   # the half of the net away from the goalie (attacker's view)
            if self.t < 4:
                return ["C"] + pad(aview(side))
            self.note("shot", kind="wrist")
            return pad(aview(side))
        if self.phase == "close":
            near_side = aview(2 if ax > 0 else 6)   # his own side of the net
            if self.t < CLOSE17["hold"]:
                return ["C"] + pad(near_side)
            self.note("shot", kind="close")
            return pad(near_side)
        if self.phase == "slap":
            if self.t < 20:
                return ["C"] + pad(aview(4))        # wind up, Down held
            self.note("shot", kind="slap")
            return pad(aview(4))
        return []

    def ea_dir(self, d, hand):
        """A direction in the right-hander's EA view (attacker's view, from his left) for this skater's hand."""
        return d if hand == "R" else (8 - d) % 8

    def ea_carry(self, m, s, ax, ay, hand, near, ahead):
        """Version 7: skate the EA Special's line and release on it; None to fall back on the other plays (past the
        release spot, or pressured in the zone)."""
        R, u = EA[s]["R"], EA[s]["u"]
        mx = 1 if hand == "R" else -1               # his EA view: the right-hander's (x mirrored for a left-hander)
        bx, by = mx * ax, ay
        vx, vy = mx * s * m["vx"], s * m["vy"]
        a = (bx - R[0]) * u[0] + (by - R[1]) * u[1]          # along the line (negative: before the release)
        off = (by - R[1]) * u[0] - (bx - R[0]) * u[1]        # across it (positive: toward the middle and up)
        dR = math.hypot(bx - R[0], by - R[1])
        if a > 12 and by > R[1] - 20 or near[0] < PRESSURE and ahead and ay > 150:
            return None
        sp = math.hypot(vx, vy)
        if a > -4 * sp - 2 and abs(off) < 16:
            self.phase, self.t = "ea", 0            # C now: the puck leaves about 4 frames on, at the spot
            self.note("ea start", ax=round(ax), ay=round(ay), off=round(off), v=round(sp, 2), hand=hand, s=s)
            return ["C"] + pad(self.aview_s(s, self.ea_dir(2, hand)))
        if a > -12 and abs(off) >= 16 and dR < 40:
            return None                             # arrived off the line: the other plays
        # pure pursuit: a point on the line 30 ahead of his projection on it (kept 14 inside the boards)
        ta = a + 30
        tx, ty = R[0] + ta * u[0], R[1] + ta * u[1]
        tx = max(tx, -118)
        if by < R[1] - 150:                         # far away: up the ice toward the line's start
            tx, ty = max(R[0] - 60 * u[0], -118), by + 80
        if self.version >= 8:
            # up the wing (EA_TUNE wing across) to EA_TUNE turn short of the release spot (up the ice), then the d-pad
            # that pushes his velocity toward EA_SPEED along the line (a carrier gains speed at half rate, so the turn
            # onto a 45 degree line takes about 40 frames), corrected toward the line
            wing, turn = EA_TUNE["wing"], EA_TUNE["turn" + hand]
            if by < R[1] - turn:
                if bx > wing + 50 and by > R[1] - turn - 60:
                    return None                     # too far inside to get out to the wing: the other plays
                wx = max(-0.8, min(0.8, 0.03 * (wing - bx))) - vx     # onto the wing's line, damped
                wy = EA_SPEED + 0.2 - vy
            else:
                k = EA_TUNE["look"] / 1000          # the correction toward the line, a frame per unit off it
                wx = EA_SPEED * u[0] + k * off * u[1] - vx
                wy = EA_SPEED * u[1] - k * off * u[0] - vy
            if math.hypot(wx, wy) < 0.12:
                return []
            d = dir_to(wx, wy)                      # never back down the ice (a brake): glide to lose speed
            d = {3: 2, 5: 6}.get(d, d)
            if d == 4:
                return []
            return pad(self.aview_s(s, self.ea_dir(d, hand)))
        d = dir_to(tx - bx, ty - by)
        if a > -60 and sp > EA_SPEED + 0.1 and self.t % 2 and (self.version < 8 or d == dir_to(vx, vy)):
            return []                               # a little below full speed: coast every other frame (8: only
                                                    # when going his way: a tapped d-pad doesn't turn him)
        return pad(self.aview_s(s, self.ea_dir(d, "R") if hand == "R" else (8 - d) % 8))

    @staticmethod
    def aview_s(s, d):
        return d if s > 0 else (d + 4) % 8

    def blocked(self, P, me, s, g, width=30):
        """An opponent skater within `width` of the line from him to the middle of the goal line, ahead of him."""
        m = P[me]
        nx, ny = 0, s * NET_Y
        L = math.hypot(nx - m["x"], ny - m["y"]) or 1
        for k in self.theirs:
            if k == g:
                continue
            ox, oy = P[k]["x"] - m["x"], P[k]["y"] - m["y"]
            along = (ox * (nx - m["x"]) + oy * (ny - m["y"])) / L
            if 0 < along < L and abs(ox * (ny - m["y"]) - oy * (nx - m["x"])) / L < width:
                return True
        return False

    def open_mate(self, P, me, s, g):
        """A teammate in the slot (170-245 up the ice, within 60 of the middle) with no opponent within 30 of him
        and none within 15 of the passing lane; else None."""
        m = P[me]
        for k in self.mine:
            if k == me or P[k]["pos"] == 0:
                continue
            t = P[k]
            if self.version >= 13:
                # version 13: the recorded games' one-timers (GENESIS_GUIDE 7: a pass moving the puck 13-30 ft across
                # scored nearly half; struck from inside about 33 ft): the receiver 15-100 out from the goal line
                # within 70 of the middle, the pass 39-110 across
                tax, tay = s * t["x"], s * t["y"]
                if not (NET_Y - 100 < tay < NET_Y - 15 and abs(tax) < 70 and 39 < abs(tax - s * m["x"]) < 110):
                    continue
                if self.version >= 14 and math.hypot(t["x"] - m["x"], t["y"] - m["y"]) >= 130:
                    continue                    # version 14: people's one-timer passes 130+ long scored 7 of 36
                if self.version >= 15 and (abs(tax) >= 40 or not (P[g]["x"] * m["x"] > 0 and abs(P[g]["x"]) >= 4)):
                    continue                    # version 15: the receiver near the middle, the goalie drawn over
                                                # to the passer's side (people's one-timers that scored)
            elif self.version >= 5:
                # the study's good one-timers: the receiver close in (within 95 of the goal mouth's middle, in front
                # of the line) and the pass across (from the other side, or 50+ across)
                tax, tay = s * t["x"], s * t["y"]
                if not (math.hypot(tax, NET_Y - tay) < 95 and tay < NET_Y - 4):
                    continue
                if not (tax * s * m["x"] < 0 or abs(tax - s * m["x"]) > 50):
                    continue
            elif not (170 < s * t["y"] < 245 and abs(t["x"]) < 60):
                continue
            if any(math.hypot(P[o]["x"] - t["x"], P[o]["y"] - t["y"]) < (20 if self.version >= 14 else 30)
                   for o in self.theirs if o != g):
                continue
            L = math.hypot(t["x"] - m["x"], t["y"] - m["y"]) or 1
            lane = False
            for o in self.theirs:
                ox, oy = P[o]["x"] - m["x"], P[o]["y"] - m["y"]
                along = (ox * (t["x"] - m["x"]) + oy * (t["y"] - m["y"])) / L
                if 0 < along < L and abs(ox * (t["y"] - m["y"]) - oy * (t["x"] - m["x"])) / L < 15:
                    lane = True
            if not lane:
                return k
        return None

    def defence(self, P, me, owner, s):
        m, pk = P[me], P[PUCK]
        own_net_y = -s * 268
        out = []
        loose = owner is None
        still = abs(pk["vx"]) + abs(pk["vy"]) < 0.05
        if loose and pk["z"] < 0:                   # the puck held up for a faceoff (dropped about 300 frames on)
            return []
        if loose and still and math.hypot(pk["x"] - m["x"], pk["y"] - m["y"]) < 30:
            # a faceoff (or a dead puck at his feet): mash B, the d-pad back toward our net
            self.b_down = not self.b_down
            return (["B"] if self.b_down else []) + pad(dir_to(0, -s))
        if loose:
            tx, ty = pk["x"] + 8 * pk["vx"], pk["y"] + 8 * pk["vy"]
            dist_to_puck = {k: math.hypot(P[k]["x"] - tx, P[k]["y"] - ty) for k in self.mine if P[k]["pos"] != 0}
        else:
            c = P[owner]
            if owner in self.mine:                  # a teammate the computer runs has it: get open ahead
                return pad(dir_to(0, s))
            # his goal side: a spot between the carrier and our net, a little toward the net
            dx, dy = 0 - c["x"], own_net_y - c["y"]
            L = math.hypot(dx, dy) or 1
            tx, ty = c["x"] + 14 * dx / L + 6 * c["vx"], c["y"] + 14 * dy / L + 6 * c["vy"]
            dist_to_puck = {k: math.hypot(P[k]["x"] - c["x"], P[k]["y"] - c["y"]) for k in self.mine if P[k]["pos"] != 0}
            dc = dist_to_puck.get(me, 999)
            closing = (c["x"] - m["x"]) * (m["vx"] - c["vx"]) + (c["y"] - m["y"]) * (m["vy"] - c["vy"]) > 0
            if dc < POKE:
                self.b_down = not self.b_down
                if self.b_down:
                    out.append("B")
            elif dc < 45 and closing and self.frame % 30 == 0:
                out.append("C")                     # burst into him
        d = dir_to(tx - m["x"], ty - m["y"])
        nearest = min(dist_to_puck, key=dist_to_puck.get)
        if nearest != me and dist_to_puck[nearest] + 50 < dist_to_puck.get(me, 999) and "B" not in out \
                and self.frame % 20 == 0:
            out.append("B")                         # tap: control switches to whoever the game picks
        return out + pad(d)
