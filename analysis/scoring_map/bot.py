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
middle with the goalie drawn 4+ toward the passer's side; 16 is 15 without the slapshot under pressure and
with the close-in wrist shot from 170 up the ice (WRIST16; a limit across, cutting in to the middle first, scored
less the narrower it was); 17 is 16 with, in close and off the middle, the slapshot wind-up that
drops the goalie, released at his own side (CLOSE17); 18 is 16 (not 17) with a carry that begins in the middle of the zone
going straight up the ice to the wrist shot; 19 is 18 chasing its own rebounds; 20 is 16 (not 17-19) with the faceoff B-mash only just
after a faceoff drop; 21 is 20 with the CB check; 22 is 21 with the defence's
numbers from DEF22 (env NHL94_DEF); 23 is 22 covering the
slot in our end (SLOT23); 24-26 are 22 (16's offence) with
one offence change each: 24 the right-hander's deke on the right (12's), 25 no one-timer passes, 26 (the default) a looser
deke entry; 27 is 26 looser still, 28 is 26 with 24's right-side deke; 29 is 26 with people's
one-timer set-up (low on one side, across: LOW29), checked before the wrist shot; 30 is 26 with a relief pass to an open
teammate when a defender closes in ahead (RELIEF30). 39 is 32 passing out of a check (2026-11-07, CHECK39): when an
opponent skater is bursting at him and due to reach him in 6-16 frames, a pass to an open teammate (relief_mate) at
once, as check_pass_timing.py found best (B as the burst begins, the pass away 0.10-0.25 s real before contact).
40 (2026-11-11, the user: a bot that plays like people, for simulations) is 32 carrying the puck as people do
(people_carry, PEOPLE40; analysis/carry_profile.py): a hold time drawn from people's by zone, then a pass to an open
teammate (the one-timer pass in the attacking zone), the slapshot from the slot or the point, the dump-in at their line;
and it bursts in to check again. 41 is 40 shooting less (in the attacking zone only after the hold, and then only
now and then: PEOPLE41), the one-timer pass more often and less narrowly, and the burst check from farther out (DEF41).
42 is 41 hitting off the puck when a teammate is on the carrier, the long burst only near the boards, and no poke
from point-blank (DEF42; for its penalties and people's big hits). 43 is 42 checking a man on the boards from his
inside, outward, as the game's board check needs (DEF43, board_hit). 44 is 43 without pokes, shooting once two
holds in the attacking zone have run out, and dumping in more often (PEOPLE44). 45 is 44 with fewer, safer passes
(PEOPLE45) and more body checks (DEF45), toward the expert coaches' numbers. 46 is 45 without 32's slot passes (the
one-timer pass only from people_carry) and with the CB check on purpose (DEF46). 47 is 46 offering the one-timer
whenever a teammate is open across the slot (a safer open_mate) and with fewer CB checks (PEOPLE47, DEF47). 48 is
47 with 32's slot pass back and open_mate on people's one-timer spots and coverage (PEOPLE48). 49 is 48 without 32's
slot pass (48: 9.1 one-timer tries a game, 1.2 goals; experts 5.0 / 1.8): the one-timer only from people_carry's offer.
50 is 49 offering it less often and only with the goalie drawn toward the passer's side (PEOPLE50).
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
ARRIVE = int(__import__("os").environ.get("NHL94_ARRIVE") or 14)   # version 5: the one-timer's C this many frames before the pass arrives
PRESSURE = 24          # units (3 to a foot)
POKE = 26
DEKE = {"L": dict(D=60, lag=10), "R": dict(D=60, lag=13)}
# version 6: re-timed with every skater on the ice (the runs' timings were found with the others taken off, and then a
# right-hander turns faster): 24 tries each, left-handers 23 (lag 10: 20), right-handers 23 (lag 13: 1)
DEKE6 = {"L": dict(D=60, lag=13), "R": dict(D=60, lag=16)}
if __import__("os").environ.get("NHL94_DEKE_SHIFT"):           # test: "dD,dlag" added to DEKE6 (both hands)
    _dd, _dl = map(int, __import__("os").environ["NHL94_DEKE_SHIFT"].split(","))
    DEKE6 = {h: dict(D=v["D"] + _dd, lag=v["lag"] + _dl) for h, v in DEKE6.items()}
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
WRIST_AIM = __import__("os").environ.get("NHL94_WRIST_AIM") or "mid"   # the wrist shot's aim: mid (the far side, middle height:
# best), low, high, near (the goalie's side), none (nothing held)
# version 22: the defence's numbers (21's by default): poke within poke, burst within burst every `every` frames, the
# goal-side spot gap in front of the carrier toward our net, switch (B) when a teammate is `switch` nearer; env
# NHL94_DEF="poke,burst,every,gap,switch" (the long test plan's block 2)
DEF22 = dict(poke=26, burst=45, every=30, gap=14, switch=50)
# version 33 (2026-11-01, penalties: tripping is the bot's most-called foul after roughing; a poke trips the carrier
# whenever the poker's body touches him while facing him): 32 with no poke closer than `lo` (B only between lo and the
# poke range, so the stick reaches without the body); env NHL94_POKE33="lo"
POKE33 = float(__import__("os").environ.get("NHL94_POKE33") or 16)
# version 34 (2026-11-01, special teams: power plays score 61%): 32 that clears the puck when shorthanded, in our own
# half with an opponent within `press` (999: always), a shot up the ice with C held `hold` frames; env NHL94_PK34=
# "press,hold"
PK34 = dict(zip(("press", "hold"), map(float, (__import__("os").environ.get("NHL94_PK34") or "40,3").split(","))))
# version 35 (2026-11-01): 32 that pokes only when the carrier isn't closing on him faster than `close` a frame (a
# poke trips whenever the bodies touch, and 33's later poke still tripped); env NHL94_POKE35="close"
POKE35 = float(__import__("os").environ.get("NHL94_POKE35") or 0.4)
# version 36 (2026-11-01): 32 on the penalty kill: shorthanded, with the carrier within `zone` of our goal line, he
# holds the slot `hold` out from our net on the line to the carrier (23's cover, at even strength no gain) instead of
# chasing; env NHL94_PK36="zone,hold"
PK36 = dict(zip(("zone", "hold"), map(float, (__import__("os").environ.get("NHL94_PK36") or "150,40").split(","))))
if __import__("os").environ.get("NHL94_DEF"):
    DEF22 = dict(zip(("poke", "burst", "every", "gap", "switch"),
                     map(float, __import__("os").environ["NHL94_DEF"].split(","))))
# version 23: covering the slot in our end (the carrier within `zone` of our goal line: stand `hold` out from our net
# on the line to him); env NHL94_SLOT="zone,hold"
SLOT23 = dict(zone=140, hold=55)
if __import__("os").environ.get("NHL94_SLOT"):
    SLOT23 = dict(zip(("zone", "hold"), map(float, __import__("os").environ["NHL94_SLOT"].split(","))))
# version 26's looser deke entry (half-width of the gate, across speed from / to, up-ice speed above); 27 looser still
# version 37: cover an open man in our slot when a teammate is nearer the carrier by `margin` and the carrier is
# within `zone` of our goal line; stand `off` from him toward the carrier; env NHL94_COVER37="zone,margin,off"
COVER37 = dict(zip(("zone", "margin", "off"), map(float, (__import__("os").environ.get("NHL94_COVER37") or "175,10,10").split(","))))
# version 38: B to the goal-side teammate when we are `behind` farther from our net than the carrier and a teammate
# is nearer our net within `line` of the carrier's line to it; env NHL94_GOAL38="behind,line"
GOAL38 = dict(zip(("behind", "line"), map(float, (__import__("os").environ.get("NHL94_GOAL38") or "20,40").split(","))))
LOOSE = {False: (26, 0.0, 1.1, 1.2), True: (36, -0.2, 1.3, 1.0)}
# version 29: the low one-timer set-up (the carrier within out of the goal line and side off the middle; the
# receiver rmin-rmax out); env NHL94_LOW29="out,side,rmin,rmax"
LOW29 = dict(out=90, side=28, rmin=25, rmax=110)
if __import__("os").environ.get("NHL94_LOW29"):
    LOW29 = dict(zip(("out", "side", "rmin", "rmax"), map(float, __import__("os").environ["NHL94_LOW29"].split(","))))
# version 30: the relief pass (an opponent within press ahead, the carrier past `from` up the ice; the receiver with no
# opponent within open, the pass under len); env NHL94_RELIEF30="press,from,open,len"
RELIEF30 = dict(press=24, **{"from": -300}, open=30, len=150)
# version 39: passing out of a check: an opponent skater within `dist`, closing on the carrier at `closing`+ a frame,
# due in `tmin`-`tmax` frames; not in close (up the ice under `ay`, where the bot shoots); env NHL94_CHECK39
CHECK39 = dict(dist=70, closing=1.2, tmin=6, tmax=16, ay=170)
if __import__("os").environ.get("NHL94_CHECK39"):
    CHECK39 = dict(zip(("dist", "closing", "tmin", "tmax", "ay"),
                       map(float, __import__("os").environ["NHL94_CHECK39"].split(","))))
# version 40: people's carry (people_carry): hold medians in frames by zone, pass chances by zone, the one-timer,
# slapshot and dump-in chances, people_mate's limits; env NHL94_PEOPLE40 as JSON to override any of them
# (first try, 1 game: pass 0.85 / 0.7 / 0.55, dump 0.5, open 30: own-zone carries 48% passes (people 74%), neutral
# 27% (57%) with 50% ending in a shot or dump (19%): passes made likelier, a teammate open from 25, fewer dumps)
PEOPLE40 = {"hold": {"def": 74, "neu": 94, "att": 53}, "pass": {"def": 0.95, "neu": 0.9, "att": 0.6}, "ot": 0.5,
            "slap": 0.35, "dump": 0.25, "open": 25, "len": 220, "back": 40}
# version 41 (40's step 2): in the attacking zone no shot before the hold runs out, then the shot only with "shoot"
# (while holding he skates as 32, only no shot starts; a prime chance in close is always taken); the one-timer pass more often ("ot") and on 13-14's limits (not
# 15's narrow ones); the burst check from farther out (DEF41: within "burst", every "every" frames, closing at "rate"+
# a frame); env NHL94_PEOPLE41 / NHL94_DEF41 as JSON
# (first try, 1 game: holding at the top of the circle, shoot 0.45: 9 attempts a team-game, xG 0.03 a shot, 22
# giveaways: he shot from far out and lost it there; now he skates as 32 does while holding, only the shot is held
# back, and a prime chance (past "prime" up the ice, within it across) is always taken)
# version 42 (41's step 3, penalties and big hits): off_puck_hit (a teammate nearer the carrier by "margin": the
# nearest opponent without the puck within "reach" of me and "zone" of our goal line; C within "burst"); the long
# burst only at a carrier past "wallx" across or "wally" along (near the boards), else "open_burst"; no poke closer
# than POKE33 (the trip); env NHL94_DEF42 as JSON
DEF42 = {"margin": 25, "reach": 90, "zone": 300, "burst": 55, "every": 15, "wallx": 95, "wally": 250, "open_burst": 45}
if __import__("os").environ.get("NHL94_DEF42"):
    DEF42.update(__import__("json").loads(__import__("os").environ["NHL94_DEF42"]))
# version 43 (42's step 2, big hits): board_hit at a target past "wall" across within "reach": from "inside" nearer the
# middle, C within "burst" once nearer the middle than him by "side"+; env NHL94_DEF43 as JSON
DEF43 = {"wall": 95, "reach": 120, "inside": 30, "side": 6, "burst": 50, "every": 10}
if __import__("os").environ.get("NHL94_DEF43"):
    DEF43.update(__import__("json").loads(__import__("os").environ["NHL94_DEF43"]))
# version 44 (43's step 2: penalties and possession): no pokes; in the attacking zone the shot once "draws" holds
# have run out with nothing on; the dump-in more often ("dump"); env NHL94_PEOPLE44 as JSON
PEOPLE44 = {"draws": 2, "dump": 0.5}
if __import__("os").environ.get("NHL94_PEOPLE44"):
    PEOPLE44.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE44"]))
# version 45 (44's step 2: experts' passing and checking; expert_profile.py: 85-90% coaches 43.5 passes a game, 65%
# completed, 31 checks; 44: 55.6, 49%, 18): people_mate's teammate open by "open", the pass under "len", within "lane"
# of the lane, the pass chances "pass"; the burst from "open_burst" every "every" frames closing at "rate"+ (no pokes)
PEOPLE45 = {"pass": {"def": 0.8, "neu": 0.7, "att": 0.55}, "open": 40, "len": 170, "back": 30, "lane": 22}
DEF45 = {"every": 10, "open_burst": 60, "rate": 0.8}
if __import__("os").environ.get("NHL94_PEOPLE45"):
    PEOPLE45.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE45"]))
# version 46 (the diagnosis: 32's slot passes reached the meant mate 14%, people-style 63%; people's CB checks land
# 43%): no 32-style slot pass or left-hander's bail-out pass (one-timer passes only from people_carry's offer), and
# the CB check, B a few frames into the burst, "cb" of the bursts
DEF46 = {"cb": 0.35}
# version 47 (46's step 2): the one-timer offer every "every" frames in the attacking zone with chance "offer", to a
# receiver open by "open" with the lane clear by "lane" (open_mate's other limits as 41's); CB on "cb" of the bursts
PEOPLE47 = {"every": 6, "offer": 0.35, "open": 35, "lane": 20}
DEF47 = {"cb": 0.2}
if __import__("os").environ.get("NHL94_DEF47"):
    DEF47.update(__import__("json").loads(__import__("os").environ["NHL94_DEF47"]))
# version 48: 47 with 32's slot pass back (it made the one-timers: 41 4.8 tries a game) and open_mate on people's
# one-timer spots: the receiver "out" from the goal line and within "mid" of the middle, the pass "across" and under
# "len", the receiver open by "open", the lane clear by "lane"
# version 50: 49 with the goalie drawn "drawn"+ toward the passer's side before the pass across, offered "offer"
PEOPLE50 = {"drawn": 4, "offer": 0.2}
if __import__("os").environ.get("NHL94_PEOPLE50"):
    PEOPLE50.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE50"]))
PEOPLE48 = {"out": (30, 140), "mid": 60, "across": (30, 130), "len": 170, "open": 15, "lane": 5}
if __import__("os").environ.get("NHL94_PEOPLE48"):
    PEOPLE48.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE48"]))
if __import__("os").environ.get("NHL94_PEOPLE47"):
    PEOPLE47.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE47"]))
if __import__("os").environ.get("NHL94_DEF46"):
    DEF46.update(__import__("json").loads(__import__("os").environ["NHL94_DEF46"]))
PEOPLE41 = {"shoot": 0.6, "ot": 0.8, "prime": (200, 40)}
DEF41 = {"burst": 70, "every": 15, "rate": 1.0}
if __import__("os").environ.get("NHL94_PEOPLE41"):
    PEOPLE41.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE41"]))
if __import__("os").environ.get("NHL94_DEF41"):
    DEF41.update(__import__("json").loads(__import__("os").environ["NHL94_DEF41"]))
if __import__("os").environ.get("NHL94_PEOPLE40"):
    PEOPLE40.update(__import__("json").loads(__import__("os").environ["NHL94_PEOPLE40"]))
if __import__("os").environ.get("NHL94_RELIEF30"):
    RELIEF30 = dict(zip(("press", "from", "open", "len"),
                        map(float, __import__("os").environ["NHL94_RELIEF30"].split(","))))
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
    def __init__(self, team=0, version=32):
        self.rng = __import__("random").Random(7919 * team + version)   # version 40's draws
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
            r = P[me] if me != self.passer else P[self.mate]
            if getattr(self, "relief", False):         # version 30's relief pass: no one-timer, he skates to it
                return pad(dir_to(pk["x"] + 4 * pk["vx"] - r["x"], pk["y"] + 4 * pk["vy"] - r["y"]))
            # C once the puck is about ARRIVE frames from the receiver (control passes to him as it leaves)
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
            if self.version == 19 and self.phase == "shot" and owner is None and pk["z"] >= 0:
                # version 19: after our shot, at the loose puck (the rebound) a few frames ahead; B switches to a
                # teammate much nearer it (16 fell back on the defence's faceoff rule: B mashed toward our net)
                tx, ty = pk["x"] + 4 * pk["vx"], pk["y"] + 4 * pk["vy"]
                dist = {k: math.hypot(P[k]["x"] - tx, P[k]["y"] - ty) for k in self.mine if P[k]["pos"] != 0}
                near_k = min(dist, key=dist.get)
                out = pad(dir_to(tx - P[me]["x"], ty - P[me]["y"]))
                if near_k != me and dist[near_k] + 30 < dist.get(me, 999) and self.frame % 10 == 0:
                    out = ["B"] + out
                return out
            out = self.defence(P, me, owner, s)
        return out

    def shorthanded(self, P):
        """Fewer of our skaters on the ice than theirs (a player serving a penalty is off: position $FF)."""
        n = lambda ks: sum(1 for k in ks if P[k]["pos"] not in (0, 0xFF))
        return n(self.mine) < n(self.theirs)

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
        if self.version in (12, 24, 28) and (ay < LANE[0] or self.phase in ("free", "shot")):
            self.side = -1 if ax > 10 and hand == "R" else 1
        mx = getattr(self, "side", 1) if self.version in (12, 24, 28) else 1
        ax = mx * ax
        deke = self.deke if mx > 0 else DEKE12R
        vxa = mx * s * m["vx"]                      # across speed toward the middle (left side's view)
        aview = lambda d: (d if mx > 0 else (8 - d) % 8) if s > 0 else ((d if mx > 0 else (8 - d) % 8) + 4) % 8
        if self.phase in ("free", "shot"):
            self.phase, self.t = "carry", 0
            self.last, self.stuck = (m["x"], m["y"]), 0
            self.straight = self.version in (18, 19) and 60 < ay < 170 and abs(ax) < 25
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
            if self.version == 34 and ay < 0 and near[0] < PK34["press"] and self.shorthanded(P):
                self.phase, self.t = "clear", 0     # version 34: shorthanded in our half: clear it up the ice
                self.note("clear start", ax=ax, ay=ay)
                return ["C"] + pad(aview(0))
            if self.version in (40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50):
                act = self.people_carry(P, me, s, g, ax, ay, near, ahead)
                if act is not None:
                    return act
            low_mate = self.low_mate(P, me, s, g, ax, ay) if self.version == 29 else None
            relief = self.relief_mate(P, me, s, g) if self.version == 30 and near[0] < RELIEF30["press"] and ahead                 and ay > RELIEF30["from"] else None
            if self.version == 39 and ay < CHECK39["ay"] and self.checker_due(P, me, g):
                relief = self.relief_mate(P, me, s, g)
            self.relief = False
            if relief is not None:
                # version 30: a defender closing in ahead: pass to an open teammate (no one-timer; he carries on)
                self.mate, self.relief = relief, True
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay, relief=True, check=self.version == 39)
            elif low_mate is not None:
                # version 29: people's one-timer set-up, checked before the wrist shot (which otherwise always came
                # first in close, so 16's passes only left from farther out): low on one side, a quick pass across
                self.mate = low_mate
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay, low=True)
            elif self.version == 17 and CLOSE17["ay"] < ay < NET_Y - 10 and abs(ax) > CLOSE17["side"]:
                # version 17: in close and off the middle, the slapshot wind-up that drops the computer goalie into
                # a pad stack sliding to the middle (GENESIS_GUIDE 6: 37% when he dropped), released at his own side
                self.phase, self.t = "close", 0
                self.note("close start", ax=ax, ay=ay)
            elif ((WRIST16["ay"] < ay < NET_Y - 10 and abs(ax) < WRIST16["mid"]) if self.version >= 16 else 200 < ay < NET_Y)                     and getattr(self, "shoot_ok", True):
                self.phase, self.t = "wrist", 0     # in close off the deke's line: a wrist shot away from the goalie
                self.note("wrist start", ax=ax, ay=ay)
            elif near[0] < PRESSURE and ahead and ay > (GATE[1] + 35 if self.version >= 4 else 90)                     and self.version < 16:          # version 16: no slapshot under pressure (about none went in)
                self.phase, self.t = "slap", 0
                self.note("slap start", ax=ax, ay=ay)
            elif self.version >= 2 and self.version not in (46, 47, 49, 50) and ay > (144 if self.version >= 14 else 100 if self.version >= 13 else 150 if self.version >= 5 else 90) \
                    and self.open_mate(P, me, s, g) is not None:
                self.mate = self.open_mate(P, me, s, g)
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay)
            elif GATE[1] - 15 < ay < GATE[1] + 35 and abs(ax - GATE[0]) < 22 and s * m["vy"] > 1.2 \
                    and self.version == 2 and self.blocked(P, me, s, g):
                self.phase, self.t = "slap", 0     # a defender on the deke's line: the slapshot from the gate
                self.note("slap start", ax=ax, ay=ay, blocked=True)
            elif self.version >= 4 and getattr(self, "shoot_ok", True) and GATE[1] - 15 < ay < GATE[1] + 35 and (
                    abs(ax - GATE[0]) < 16 and 0.2 < vxa < 0.9 and s * m["vy"] > 1.5 or
                    self.version >= 26 and abs(ax - GATE[0]) < LOOSE[self.version == 27][0]
                    and LOOSE[self.version == 27][1] < vxa < LOOSE[self.version == 27][2]
                    and s * m["vy"] > LOOSE[self.version == 27][3]):
                # (version 26: a looser entry, so the bot dekes more often)
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
                elif getattr(self, "straight", False) and ay < WRIST16["ay"] + 5:
                    # version 18: a carry that began in the middle of the zone goes straight up the ice to the
                    # wrist shot (16 swung him out to the deke's lane, across the defenders: 7 goals from 84 middle
                    # entries, people 15)
                    return pad(aview(0))
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
            if dg <= deke[hand]["D"] and self.version >= 9 and self.version not in (46, 47, 49, 50) and hand == "L" and s * m["vy"] < 1.3                     and near[0] < 25:
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
            aim = aview(side)                       # screen: the aim's height is screen Up (high) / Down (low)
            if WRIST_AIM == "low":
                aim = 3 if aim == 2 else 5
            elif WRIST_AIM == "high":
                aim = 1 if aim == 2 else 7
            elif WRIST_AIM == "near":
                aim = 6 if aim == 2 else 2
            if WRIST_AIM == "none":
                return ["C"] if self.t < 4 else self.note("shot", kind="wrist") or []
            if self.t < 4:
                return ["C"] + pad(aim)
            self.note("shot", kind="wrist")
            return pad(aim)
        if self.phase == "close":
            near_side = aview(2 if ax > 0 else 6)   # his own side of the net
            if self.t < CLOSE17["hold"]:
                return ["C"] + pad(near_side)
            self.note("shot", kind="close")
            return pad(near_side)
        if self.phase == "dump":                    # version 40: the dump-in, C 3 frames at the corner
            corner = aview(1 if ax < 0 else 7)
            if self.t < 4:
                return ["C"] + pad(corner)
            self.note("shot", kind="dump")
            return pad(corner)
        if self.phase == "clear":
            if self.t < PK34["hold"]:
                return ["C"] + pad(aview(0))
            self.note("shot", kind="clear")
            return pad(aview(0))
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

    def checker_due(self, P, me, g):
        """Version 39: an opponent skater bursting at the carrier, due to reach him in CHECK39's window."""
        m = P[me]
        for o in self.theirs:
            if o == g or P[o]["pos"] in (0, 0xFF):
                continue
            dx, dy = m["x"] - P[o]["x"], m["y"] - P[o]["y"]
            d = math.hypot(dx, dy) or 1
            if d > CHECK39["dist"]:
                continue
            closing = ((P[o]["vx"] - m["vx"]) * dx + (P[o]["vy"] - m["vy"]) * dy) / d
            if closing >= CHECK39["closing"] and CHECK39["tmin"] <= (d - 18) / closing <= CHECK39["tmax"]:
                return True
        return False

    def people_carry(self, P, me, s, g, ax, ay, near, ahead):
        """Version 40 (2026-11-11, chunk 3: a bot that plays like people; carry_profile.py): people's carriers hold the
        puck a median 74 / 94 / 53 frames in their own / the neutral / the attacking zone and then most often pass
        (74% / 57% / 44% of carries end in a pass; the bot's 32 almost never did). Each carry draws a hold time
        (exponential, the zone's median); when it runs out: in the attacking zone the one-timer pass (open_mate) with
        probability PEOPLE40 "ot", else a pass to an open teammate (people_mate) with the zone's "pass", else from the
        slot or the point (90-175 up the ice) the slapshot ("slap"; people: a quarter of their shots); in the neutral
        zone near their line (30+ up the ice) with an opponent within 40 ahead, the dump-in ("dump"); else carry on
        (32's deke and wrist shot) and draw again. The buttons this frame, or None for 32's way."""
        zone = "def" if ay < -89 else "att" if ay > 89 else "neu"
        draw = lambda: max(8, int(PEOPLE40["hold"][zone] * -math.log(1 - self.rng.random()) / math.log(2)))
        av = lambda d: d if s > 0 else (d + 4) % 8
        v41 = self.version in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50)
        if self.version in (47, 48, 49, 50) and zone == "att" and self.frame % PEOPLE47["every"] == 0                 and self.rng.random() < (PEOPLE50["offer"] if self.version == 50 else PEOPLE47["offer"]):
            # version 47: the one-timer offered whenever a teammate is open across the slot, not only when the hold
            # runs out (46: 0.9 one-timer tries a game; experts 5.0)
            mate = self.open_mate(P, me, s, g)
            if mate is not None:
                self.mate, self.relief = mate, False
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay, people=True, onetimer=True)
                return ["B"] + pad(dir_to(P[mate]["x"] - P[me]["x"], P[mate]["y"] - P[me]["y"]))
        if self.t <= 1:
            self.hold = draw()
            self.shoot_ok = not v41
            self.draws = 0
        if v41 and not self.shoot_ok and ay > PEOPLE41["prime"][0] and abs(ax) < PEOPLE41["prime"][1]:
            self.shoot_ok = True                    # a prime chance in close: people take it at once
        if self.t < self.hold:
            return None
        self.hold = self.t + draw()
        if zone == "att":
            mate = self.open_mate(P, me, s, g)
            if mate is not None and self.rng.random() < (PEOPLE41["ot"] if v41 else PEOPLE40["ot"]):
                self.mate, self.relief = mate, False
                self.phase, self.t, self.passer = "pass", 0, me
                self.note("pass start", ax=ax, ay=ay, people=True, onetimer=True)
                return ["B"] + pad(dir_to(P[mate]["x"] - P[me]["x"], P[mate]["y"] - P[me]["y"]))
        mate = self.people_mate(P, me, s, g)
        if mate is not None and self.rng.random() < (PEOPLE45["pass"] if self.version in (45, 46, 47, 48, 49, 50) else PEOPLE40["pass"])[zone]:
            self.mate, self.relief = mate, True
            self.phase, self.t, self.passer = "pass", 0, me
            self.note("pass start", ax=ax, ay=ay, people=True, relief=True)
            return ["B"] + pad(dir_to(P[mate]["x"] - P[me]["x"], P[mate]["y"] - P[me]["y"]))
        if zone == "att" and 90 < ay < 175 and self.rng.random() < PEOPLE40["slap"]:
            self.phase, self.t = "slap", 0
            self.note("slap start", ax=ax, ay=ay, people=True)
            return ["C"] + pad(av(4))
        dump = PEOPLE44["dump"] if self.version in (44, 45, 46, 47, 48, 49, 50) else PEOPLE40["dump"]
        if zone == "neu" and ay > 30 and near[0] < 40 and ahead and self.rng.random() < dump:
            self.phase, self.t = "dump", 0
            self.note("dump start", ax=ax, ay=ay)
            return ["C"] + pad(av(1 if ax < 0 else 7))
        if v41 and zone == "att" and not self.shoot_ok:
            # version 41: the shot (32's deke or wrist shot) only now and then; else hold on and draw again
            self.shoot_ok = self.rng.random() < PEOPLE41["shoot"]
            if self.version in (44, 45, 46, 47, 48, 49, 50):
                # version 44: no holding on and on: the second hold out with nothing on, shoot
                self.draws += 1
                self.shoot_ok = self.shoot_ok or self.draws >= PEOPLE44["draws"]
        return None

    def off_puck_hit(self, P, me, owner, dist_to_puck, dc, own_net_y):
        """Version 42 (people hit off the puck: 36% of their hits, the bot's 41 17%; the game's penalty roll halves its
        chance away from the puck): a teammate is nearer the carrier by DEF42 "margin": the nearest opponent skater
        without the puck within "reach" of me and within "zone" of our goal line: skate at him, C (the burst) when
        within "burst" and closing, every "every" frames. The buttons, or None."""
        if min(dist_to_puck.values()) + DEF42["margin"] >= dc:
            return None
        m, best = P[me], None
        for o in self.theirs:
            a = P[o]
            if o == owner or a["pos"] in (0, 0xFF):
                continue
            if abs(own_net_y - a["y"]) > DEF42["zone"]:
                continue
            d = math.hypot(a["x"] - m["x"], a["y"] - m["y"])
            if d < DEF42["reach"] and (best is None or d < best[0]):
                best = (d, o)
        if best is None:
            return None
        d, o = best
        a = P[o]
        if self.version in (43, 44, 45, 46, 47, 48, 49, 50):
            hit = self.board_hit(P, me, o, d)
            if hit is not None:
                return hit
        tx, ty = a["x"] + 6 * a["vx"], a["y"] + 6 * a["vy"]
        out = pad(dir_to(tx - m["x"], ty - m["y"]))
        rate = ((a["x"] - m["x"]) * (m["vx"] - a["vx"]) + (a["y"] - m["y"]) * (m["vy"] - a["vy"])) / max(1, d)
        if d < DEF42["burst"] and rate > 0.5 and self.frame % int(DEF42["every"]) == 0:
            out = ["C"] + out
            self.note("off-puck hit", on=o, d=round(d))
        return out

    def board_hit(self, P, me, o, d):
        """Version 43 (people's big hits: 97 of 163 a cross-check into the boards; FallDown makes a board check only
        when the man hit is against the boards (wallcollduringcheck), wide of the crease (|x| > $68) or past a goal
        line, and the checker comes from the middle side, driving him outward): a target `o` past DEF43 "wall" across
        (within the goal lines): skate to a spot "inside" nearer the middle than him, level with him; once on his
        inside (nearer the middle by "side"+) and within "burst", C at him (outward). The buttons, or None."""
        m, a = P[me], P[o]
        if abs(a["x"]) < DEF43["wall"] or abs(a["y"]) > 260:
            return None
        sx = 1 if a["x"] > 0 else -1
        ax_, ay_ = a["x"] + 6 * a["vx"], a["y"] + 6 * a["vy"]
        inside = sx * (a["x"] - m["x"]) >= DEF43["side"]
        if inside and d < DEF43["burst"] and self.frame % int(DEF43["every"]) == 0:
            self.note("board hit", on=o, d=round(d))
            return ["C"] + pad(dir_to(ax_ - m["x"], ay_ - m["y"]))
        if inside:
            return pad(dir_to(ax_ - m["x"], ay_ - m["y"]))
        tx, ty = ax_ - sx * DEF43["inside"], ay_
        return pad(dir_to(tx - m["x"], ty - m["y"]))

    def people_mate(self, P, me, s, g):
        """Version 40: an open teammate as people pass to (sideways 32%, forward 30%, diagonal forward 25%, back
        13%): no opponent within PEOPLE40 "open" of him, none within 15 of the lane, the pass under "len", him no more
        than "back" behind; the one farthest up the ice."""
        m, best = P[me], None
        for k in self.mine:
            if k == me or P[k]["pos"] in (0, 0xFF):
                continue
            t = P[k]
            L = math.hypot(t["x"] - m["x"], t["y"] - m["y"]) or 1
            Q = PEOPLE45 if self.version in (45, 46, 47, 48, 49, 50) else PEOPLE40
            if L >= Q["len"] or s * (t["y"] - m["y"]) < -Q["back"]:
                continue
            if any(math.hypot(P[o]["x"] - t["x"], P[o]["y"] - t["y"]) < Q["open"] for o in self.theirs if o != g):
                continue
            if any(0 < ((P[o]["x"] - m["x"]) * (t["x"] - m["x"]) + (P[o]["y"] - m["y"]) * (t["y"] - m["y"])) / L < L
                   and abs((P[o]["x"] - m["x"]) * (t["y"] - m["y"]) - (P[o]["y"] - m["y"]) * (t["x"] - m["x"])) / L < (Q.get("lane", 15))
                   for o in self.theirs):
                continue
            if best is None or s * t["y"] > s * P[best]["y"]:
                best = k
        return best

    def relief_mate(self, P, me, s, g):
        """Version 30: an open teammate for a relief pass: no opponent within RELIEF30["open"] of him, none within 15
        of the lane, the pass under RELIEF30["len"], him no more than 30 back down the ice; the one farthest up."""
        m, best = P[me], None
        for k in self.mine:
            if k == me or P[k]["pos"] == 0:
                continue
            t = P[k]
            L = math.hypot(t["x"] - m["x"], t["y"] - m["y"]) or 1
            if L >= RELIEF30["len"] or s * (t["y"] - m["y"]) < -30:
                continue
            if any(math.hypot(P[o]["x"] - t["x"], P[o]["y"] - t["y"]) < RELIEF30["open"] for o in self.theirs if o != g):
                continue
            if any(0 < ((P[o]["x"] - m["x"]) * (t["x"] - m["x"]) + (P[o]["y"] - m["y"]) * (t["y"] - m["y"])) / L < L
                   and abs((P[o]["x"] - m["x"]) * (t["y"] - m["y"]) - (P[o]["y"] - m["y"]) * (t["x"] - m["x"])) / L < 15
                   for o in self.theirs):
                continue
            if best is None or s * t["y"] > s * P[best]["y"]:
                best = k
        return best

    def low_mate(self, P, me, s, g, ax, ay):
        """Version 29: the carrier low (within LOW29["out"] of the goal line) and off the middle (LOW29["side"]+): a
        teammate across the middle (or near it), LOW29 "rmin"-"rmax" out, no opponent within 20 of him, none within 15
        of the passing lane, the pass under 130 long; else None."""
        out = NET_Y - ay
        if not (out < LOW29["out"] and abs(ax) > LOW29["side"]):
            return None
        m = P[me]
        for k in self.mine:
            if k == me or P[k]["pos"] == 0:
                continue
            t = P[k]
            tax, tay = s * t["x"], s * t["y"]
            if not (LOW29["rmin"] < NET_Y - tay < LOW29["rmax"] and (tax * ax < 0 or abs(tax) < 12) and abs(tax) < 60):
                continue
            if math.hypot(t["x"] - m["x"], t["y"] - m["y"]) >= 130:
                continue
            if any(math.hypot(P[o]["x"] - t["x"], P[o]["y"] - t["y"]) < 20 for o in self.theirs if o != g):
                continue
            L = math.hypot(t["x"] - m["x"], t["y"] - m["y"]) or 1
            if any(0 < ((P[o]["x"] - m["x"]) * (t["x"] - m["x"]) + (P[o]["y"] - m["y"]) * (t["y"] - m["y"])) / L < L
                   and abs((P[o]["x"] - m["x"]) * (t["y"] - m["y"]) - (P[o]["y"] - m["y"]) * (t["x"] - m["x"])) / L < 15
                   for o in self.theirs):
                continue
            return k
        return None

    def open_mate(self, P, me, s, g):
        """A teammate in the slot (170-245 up the ice, within 60 of the middle) with no opponent within 30 of him
        and none within 15 of the passing lane; else None."""
        if self.version == 25:
            return None                             # version 25: no one-timer passes (what are they worth?)
        m = P[me]
        for k in self.mine:
            if k == me or P[k]["pos"] == 0:
                continue
            t = P[k]
            if self.version in (48, 49, 50):
                # version 48 (one_timer_setups.py: people's 243 one-timer passes; the receiver 63-120 out, the pass
                # 75-141 long and 51-119 across; how covered he was made no difference to the goal rate): the
                # receiver within PEOPLE48's spot, open by "open", the lane clear by "lane"
                tax, tay = s * t["x"], s * t["y"]
                lo, hi = PEOPLE48["out"]
                if not (NET_Y - hi < tay < NET_Y - lo and abs(tax) < PEOPLE48["mid"]
                        and PEOPLE48["across"][0] < abs(tax - s * m["x"]) < PEOPLE48["across"][1]
                        and math.hypot(t["x"] - m["x"], t["y"] - m["y"]) < PEOPLE48["len"]):
                    continue
                if self.version == 50 and not (P[g]["x"] * m["x"] > 0 and abs(P[g]["x"]) >= PEOPLE50["drawn"]):
                    continue                    # version 50: the goalie drawn toward the passer's side (15's test)
            elif self.version >= 13:
                # version 13: the recorded games' one-timers (GENESIS_GUIDE 7: a pass moving the puck 13-30 ft across
                # scored nearly half; struck from inside about 33 ft): the receiver 15-100 out from the goal line
                # within 70 of the middle, the pass 39-110 across
                tax, tay = s * t["x"], s * t["y"]
                if not (NET_Y - 100 < tay < NET_Y - 15 and abs(tax) < 70 and 39 < abs(tax - s * m["x"]) < 110):
                    continue
                if self.version >= 14 and math.hypot(t["x"] - m["x"], t["y"] - m["y"]) >= 130:
                    continue                    # version 14: people's one-timer passes 130+ long scored 7 of 36
                if self.version >= 15 and self.version not in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50) and (abs(tax) >= 40 or not (P[g]["x"] * m["x"] > 0 and abs(P[g]["x"]) >= 4)):
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
            if any(math.hypot(P[o]["x"] - t["x"], P[o]["y"] - t["y"]) < (PEOPLE48["open"] if self.version in (48, 49, 50) else PEOPLE47["open"] if self.version == 47 else 20 if self.version >= 14 else 30)
                   for o in self.theirs if o != g):
                continue
            L = math.hypot(t["x"] - m["x"], t["y"] - m["y"]) or 1
            lane = False
            for o in self.theirs:
                ox, oy = P[o]["x"] - m["x"], P[o]["y"] - m["y"]
                along = (ox * (t["x"] - m["x"]) + oy * (t["y"] - m["y"])) / L
                if 0 < along < L and abs(ox * (t["y"] - m["y"]) - oy * (t["x"] - m["x"])) / L < (PEOPLE48["lane"] if self.version in (48, 49, 50) else PEOPLE47["lane"] if self.version == 47 else 15):
                    lane = True
            if not lane:
                return k
        return None

    def open_in_slot(self, P, owner, own_net_y):
        """An attacker without the puck in our slot (within 35 of the middle, 100 of our goal line) with none of
        our skaters within 20 (slot_defence.py's open man): the nearest our net, or None."""
        best = None
        for k in self.theirs:
            a = P[k]
            if k == owner or a["pos"] in (0, 0xFF):
                continue
            out = abs(own_net_y) - 4 - (1 if own_net_y > 0 else -1) * a["y"]
            if abs(a["x"]) > 35 or not 0 <= out <= 100:
                continue
            if any(math.hypot(P[j]["x"] - a["x"], P[j]["y"] - a["y"]) <= 20 for j in self.mine if P[j]["pos"] not in (0, 0xFF)):
                continue
            if best is None or out < best[0]:
                best = (out, k)
        return best and best[1]

    def defence(self, P, me, owner, s):
        m, pk = P[me], P[PUCK]
        own_net_y = -s * 268
        out = []
        loose = owner is None
        still = abs(pk["vx"]) + abs(pk["vy"]) < 0.05
        if loose and pk["z"] < 0:                   # the puck held up for a faceoff (dropped about 300 frames on)
            self.faceoff_f = self.frame
            return []
        faceoff = self.version < 20 or self.frame - getattr(self, "faceoff_f", -999) < 60
        if loose and still and faceoff and math.hypot(pk["x"] - m["x"], pk["y"] - m["y"]) < 30:
            # version 20: only just after a faceoff drop (16 did it at any still puck near him, pressing back toward
            # our net)
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
            dp = DEF22 if self.version >= 22 else dict(poke=POKE, burst=45, every=30, gap=14)
            if self.version in (31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50):
                # 2026-11-01, penalties (BOT_PLAN): the bot's own skater takes 80% of its team's calls, a power play
                # scores 61%; version 31 never pokes (B touching a carrier he faces always trips with penalties on:
                # tripping 44 of its 148), 32 never bursts in to check (C and the CB check: roughing, slashing,
                # charging, cross-checking)
                # 33-38: as 32; 40 (people's way) bursts in to check again: people hit (26 checks, 3.9 big hits a
                # team-game; 32: 22 and 1.4)
                dp = dict(dp, poke=0) if self.version == 31 else dp if self.version in (40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50) else dict(dp, burst=0)
                if self.version in (44, 45, 46, 47, 48, 49, 50):
                    dp = dict(dp, poke=0)       # version 44: no pokes (the trips)
                if self.version in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50):
                    dp = dict(dp, **DEF41)
                if self.version in (42, 43, 44, 45, 46, 47, 48, 49, 50):
                    # version 42: the long burst only at a carrier near the boards (people's big hits: into the
                    # boards); elsewhere 40's 45
                    near_wall = abs(c["x"]) > DEF42["wallx"] or abs(c["y"]) > DEF42["wally"]
                    dp = dict(dp, burst=dp["burst"] if near_wall else DEF42["open_burst"])
                if self.version in (45, 46, 47, 48, 49, 50):
                    # version 45: more checks (experts 31 a game; 44: 18): from farther in open ice, more often
                    dp = dict(dp, every=DEF45["every"], burst=max(dp["burst"], DEF45["open_burst"]), rate=DEF45["rate"])
            tx, ty = c["x"] + dp["gap"] * dx / L + 6 * c["vx"], c["y"] + dp["gap"] * dy / L + 6 * c["vy"]
            out_c = abs(own_net_y) - 4 - (-s) * c["y"]  # the carrier's distance out from our goal line
            if self.version == 36 and out_c < PK36["zone"] and L > PK36["hold"] + 15 and self.shorthanded(P):
                tx, ty = -dx / L * PK36["hold"], own_net_y - dy / L * PK36["hold"]   # version 36: the slot
            if self.version == 23 and out_c < SLOT23["zone"] and L > SLOT23["hold"] + 15:
                # version 23: in our end, stand in his shooting lane in the slot, `hold` out from our net on the
                # line to him (the attacking bot scores nearly all with quick mid-height wrist shots, and a
                # mid-height shot always hits a body: GENESIS_GUIDE 6), instead of chasing him
                tx, ty = -dx / L * SLOT23["hold"], own_net_y - dy / L * SLOT23["hold"]
            dist_to_puck = {k: math.hypot(P[k]["x"] - c["x"], P[k]["y"] - c["y"]) for k in self.mine if P[k]["pos"] != 0}
            dc = dist_to_puck.get(me, 999)
            if self.version == 37 and out_c < COVER37["zone"] and min(dist_to_puck.values()) + COVER37["margin"] < dc:
                # version 37 (2026-11-01, slot_defence.py: 94% of one-timers went to a man open in the slot): a
                # teammate is on the carrier and an attacker without the puck stands open in our slot: cover him, on
                # his side of the pass line, instead of chasing (no poke, no switch)
                o = self.open_in_slot(P, owner, own_net_y)
                if o is not None:
                    a = P[o]
                    ex, ey = c["x"] - a["x"], c["y"] - a["y"]
                    el = math.hypot(ex, ey) or 1
                    tx, ty = a["x"] + COVER37["off"] * ex / el, a["y"] + COVER37["off"] * ey / el
                    self.covering = self.frame
                    return pad(dir_to(tx - m["x"], ty - m["y"]))
            if self.version in (42, 43, 44, 45, 46, 47, 48, 49, 50):
                hit = self.off_puck_hit(P, me, owner, dist_to_puck, dc, own_net_y)
                if hit is not None:
                    return hit
            if self.version in (43, 44, 45, 46, 47, 48, 49, 50) and dc < DEF43["reach"]:
                hit = self.board_hit(P, me, owner, dc)
                if hit is not None:
                    return hit
            closing = (c["x"] - m["x"]) * (m["vx"] - c["vx"]) + (c["y"] - m["y"]) * (m["vy"] - c["vy"]) > 0
            rate = ((c["x"] - m["x"]) * (m["vx"] - c["vx"]) + (c["y"] - m["y"]) * (m["vy"] - c["vy"])) / max(1, math.hypot(c["x"] - m["x"], c["y"] - m["y"]))
            if self.version == 35 and dc < dp["poke"] and rate > POKE35:
                pass                                # version 35: closing on him fast: the bodies would meet
            elif self.version in (33, 42, 43) and dc < POKE33:
                pass                                # version 33: too close, the body would touch: no poke
            elif dc < dp["poke"]:
                self.b_down = not self.b_down
                if self.b_down:
                    out.append("B")
            elif dc < dp["burst"] and closing and self.frame % int(dp["every"]) == 0                     and (self.version not in (41, 42, 43, 44, 45, 46, 47, 48, 49, 50) or rate > dp["rate"]):
                out.append("C")                     # burst into him
                self.cb_at = self.frame + 4
                # version 46: the CB check on purpose (people throw a quarter of their checks as CB, landing 43%
                # against C's 33%): B a few frames into the burst, DEF46 "cb" of the time
                self.cb_pick = self.version in (46, 47, 48, 49, 50) and self.rng.random() < (DEF47["cb"] if self.version in (47, 48, 49, 50) else DEF46["cb"])
            if (self.version >= 21 and self.version not in (32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50)
                    or self.version in (46, 47, 48, 49, 50) and getattr(self, "cb_pick", False)) and getattr(self, "cb_at", -1) == self.frame:
                return ["B"]                        # version 21: the CB check (B mid-burst: the computer's checking
                                                    # formula decides the hit, not the person's weight bug)
        d = dir_to(tx - m["x"], ty - m["y"])
        nearest = min(dist_to_puck, key=dist_to_puck.get)
        margin = DEF22["switch"] if self.version >= 22 else 50
        if self.version == 38 and not loose and self.frame % 10 == 0 and "B" not in out:
            # version 38 (2026-11-01, slot_defence.py: an empty slot with nobody home was the commonest danger): the
            # carrier past us toward our net (we are farther from our net than he is) and a teammate goal-side of
            # him (nearer our net, within GOAL38 of the line from him to it): B, so control goes to that teammate
            # rather than chasing from behind
            c = P[owner]
            to_net = lambda q: math.hypot(q["x"], own_net_y - q["y"])
            if to_net(m) > to_net(c) + GOAL38["behind"]:
                for k in self.mine:
                    q = P[k]
                    if k == me or q["pos"] == 0 or to_net(q) >= to_net(c):
                        continue
                    dx, dy = -c["x"], own_net_y - c["y"]
                    L = math.hypot(dx, dy) or 1
                    side = abs((q["x"] - c["x"]) * dy - (q["y"] - c["y"]) * dx) / L
                    if side < GOAL38["line"]:
                        return ["B"] + pad(d)
        if nearest != me and dist_to_puck[nearest] + margin < dist_to_puck.get(me, 999) and "B" not in out \
                and self.frame % 20 == 0:
            out.append("B")                         # tap: control switches to whoever the game picks
        return out + pad(d)
