"""Expected goals from the Genesis game's own rules (2026-10-17; see docs/GENESIS_SHOOTING.md 4.9).

Every shot is played out N_SAMPLES times the way the game would: the shot code (doshot) sends it at the aim point
exactly, with chance (Shot Accuracy + 1) / (Shot Accuracy + 16) from within 200 of that point (always while the
shooter's team has a delayed penalty coming), or else with its random scatter; the puck flies (lift cancelling gravity)
to the net, a goal when its centre crosses within 20 of the middle under the crossbar (checkgoal, puck radius 5); the
goalie stops it when it passes within his reach of his centre at height 15 or less (checkpuckcoll: 12-15 by working
Agility, 15 when a person controls him, 12 against a one-timer, 18 in a pad stack). The goalie moves meanwhile as the
computer goalie does (checkanim, findpc, playeracc): every few frames (his Defensive Awareness) he aims for the
puck's predicted spot on an ellipse in front of his net, or for where it will cross his goal line once it will within
34 frames, and commits to a save move (his speed quartered) 12 frames before. A person in net is moved the same way.

The emulated goalie lands a median 1.1 units from where the recorded goalies were when the puck arrived (120 shots at
computer goalies), and the one fitted number, GOALIE_SPREAD, stands for that error: the goalie's position is jittered
by it. Over 191 unblocked Genesis shots in seven recordings this gives 39.4 expected goals against 34 scored (computer
in net 28.6 / 23, a person 10.8 / 11) and a log loss of 0.30 against 0.46 for one rate for all shots. What it leaves
out: skaters in the way, the in-close top-shelf lift.

Checked against the game itself (2026-10-29, analysis/scoring_map/xg_calib.py: 33,808 shots the studies play, from
the exact state at the release): right on dekes and EA first shots, a little high on shots with the goalie set, and
far too low when the goalie is already in a save move (the game 24%, the model 15%). The goalie's stick (play_out's
`stick`, the converter passes the ROM) helps both there and on the 886 recorded shots (log loss 0.2657 -> 0.2630), so
recorded shots have it since. A goalie locked in an animation at the release (a save move, a pad stack: pflags bit 5,
which match files keep as `locked`, with the frame it clears) is held in it for the frames the recording shows, his
speed taken from the next 100 ms (add_expected_goals' `lock`): with the stick, log loss 0.2612 on the recorded shots,
and on the game's own shots at a goalie in a save move 0.42 -> 0.30; on since (xg_stick_eval.py games compares them).
Older match files without `locked` fall back to the save move's length less the time it has run.

Pass shots (2026-10-30) have no aim or scatter: the puck leaves as the recording shows it over the next 50 ms
(`launch`; its direction jittered by the 0.1-unit rounding of the recorded positions), with a fresh random lift each
play-out (dopass with no target: vertical speed 0 to 4,095, GENESIS_MECHANICS 6.1). Deflections (played the same way
from their recorded start, five of the six recorded Genesis goals off one came out at 0) and shots of kind 'other' have
no xG.
"""
import bisect
import copy
import math
import random
import sys

N_SAMPLES = 400
GOALIE_SPREAD = 4.0   # units: the emulated goalie's position error, fitted (log loss) over the recordings
AIM = [(0, 12), (16, 12), (16, 6), (16, 0), (0, 0), (-16, 0), (-16, 6), (-16, 12), (0, 6)]  # doshot's shotsets (screen x, z)
REACH = [12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15]  # .cbg, by (Agility + 2) / 2
PAD_STACK = {"0250": -6, "02a2": 6}   # gstackr / gstackl: the body test moves 6 to one side
DIRTAB = [(0, 200), (141, 141), (200, 0), (141, -141), (0, -200), (-141, -141), (-200, 0), (-141, 141)]
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
HOT_LIST = 0xA44C8   # stick hot points: x, y bytes per sprite frame (x negated when the frame is drawn mirrored, y negated)
READY = 0x0002       # SPAgready
SAVE_ANIM = [0x146, 0x178, 0x250, 0x2A2, 0x1EC, 0x21E, 0x148E, 0x14C0, 0x14F2, 0x1544]   # goaliesave .saveanim
SAVE_LEN = dict(zip(SAVE_ANIM, (32, 32, 40, 40, 32, 32, 32, 32, 36, 36)))   # frames each runs (the ROM's scripts; any
                                                                             # facing): his lock lasts as long


class GenesisRom:
    """What the stick model reads from the ROM: each sprite frame's stick hot point, and the animation scripts (8
    lists of (frame, frames shown) per animation, one per direction faced; found as tools/systems/genesis.py finds
    them, by the standing animation $050C)."""

    def __init__(self, rom):
        import struct
        self.rom = rom
        self.word = lambda a: struct.unpack_from(">H", rom, a)[0]
        self.sword = lambda a: struct.unpack_from(">h", rom, a)[0]
        self.base = next((b for b in range(0, len(rom) - 0x2000, 2)
                          if all(self.word(b + 0x50C + 2 * e) == 18 + 4 * e for e in range(8))
                          and self.word(b + 0x50C + 18) == 1), None)
        self._anim = {}

    def hot(self, frame, mirrored):
        """The blade relative to the player's centre, in rink units (y up the screen)."""
        hx, hy = self.rom[HOT_LIST + 2 * frame], self.rom[HOT_LIST + 2 * frame + 1]
        hx, hy = hx - 256 if hx > 127 else hx, hy - 256 if hy > 127 else hy
        return (-hx if mirrored else hx), -hy

    def anim(self, spa, facing):
        key = (spa, facing)
        if key not in self._anim:
            at = self.base + spa + self.word(self.base + spa + 2 * (facing & 7))
            seq = []
            while len(seq) < 40:
                frame, t = self.word(at), self.sword(at + 2)
                seq.append((frame, abs(t)))
                at += 4
                if t < 0:
                    break
            self._anim[key] = seq
        return self._anim[key]


def vtoa(dx, dy):
    """The game's 8-way direction of a vector (0 = +Y, clockwise); 8 when both parts are within 4."""
    if -4 <= dx <= 4 and -4 <= dy <= 4:
        return 8
    return int((math.degrees(math.atan2(dx, dy)) % 360 + 22.5) // 45) % 8


class Goalie:
    """The computer goalie's movement, frame by frame. Velocities in the game's words (units x 4096 a frame)."""

    def __init__(self, x, y, vx, vy, weight, agility, speed, aidef, rom=None, frame=None, facing=4, mirror=False,
                 puck_control=10, locked=0):
        """rom (GenesisRom), frame, facing, mirror: the stick model (play_out's `stick`): the frame he shows at the
        release, the way he faces and whether he's drawn mirrored; his save move then runs its own frames. locked: he
        is already in a save move at the release (one of SAVE_ANIM): for that many frames more he is locked in it,
        can't rethink or skate, only slide on (2026-10-29: xg_calib.py; a follow-up at a goalie still in his save was
        scored too low)."""
        self.rom, self.frame0, self.facing, self.mirror = rom, frame, facing, mirror
        self.seq, self.t = None, 0
        self.puck_control, self.nopuck = puck_control, 0
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.acc = (64 - weight // 4 + agility + 2 + agility + 16) // 2   # playeracc; goalies count Agility twice, + 16
        n = min(30, speed + 2)                                            # MaxSpeed, the odd half-step included
        self.vmax = (20 + n // 2) * 275 + (137 if n % 2 and n < 30 else 0)
        self.aidef = aidef
        self.d3, self.gl = (260, 264) if y > 0 else (-260, -264)
        self.timer, self.dir, self.locked, self.k = 0, 8, locked > 0, 216
        self.unlock = locked if locked > 0 else None   # frames left in a save move he was already in

    def randomise(self, rng):
        self.timer = rng.randrange((self.aidef >> 2) + 1) - 1   # where his rethink countdown stands
        self.k = 0xA0 + 16 * rng.randrange(8)                   # the look-ahead, from the game clock's low bits
        self.x += rng.gauss(0, GOALIE_SPREAD)
        self.y += rng.gauss(0, GOALIE_SPREAD)

    def frame(self):
        """The sprite frame he shows now: his save move's, frame by frame, else the one at the release."""
        if not self.seq:
            return self.frame0
        t = self.t
        for fr, n in self.seq:
            if t < n:
                return fr
            t -= n
        return self.seq[-1][0]

    def blade(self):
        hx, hy = self.rom.hot(self.frame(), self.mirror)
        return self.x + hx, self.y + hy

    def save_move(self, xc, frames, pz, pvz):
        """goaliesave: the move from the side the puck will cross on (against the way he faces, flipped for a mirrored
        goalie) and its height: high, a shoulder save within 16 of him else a glove save; low, the kick save or the
        butterfly, or the stick save when it arrives within 8 frames more than 16 to his side. (The pad stack needs a
        carried puck: never here.)"""
        side = ((vtoa(xc - self.x, self.gl - self.y) % 8 - self.facing) & 7) >> 2
        if self.mirror:
            side ^= 1
        if pz > 8 or pvz > 0x800:
            move = side + 6 if abs(self.x - xc) <= 16 else side
        else:
            move = side + 8 if frames <= 8 and not -16 < self.x - xc <= 16 else side + 4
        self.seq, self.t = self.rom.anim(SAVE_ANIM[move], self.facing), 0

    def think(self, px, py, pvx, pvy, pz=0, pvz=0):
        clamp = lambda v: max(-259, min(259, v))
        k = self.k - 64 if abs(py) > 219 else self.k
        rx, ry = px + k * pvx / 65536, clamp(py + k * pvy / 65536) - self.d3
        if rx * rx + ry * ry > 900:
            ln = math.isqrt(int(rx * rx + ry * ry)) + 1
            rx, ry = rx * 26 / ln, ry * 18 / ln
        gx, gy = rx, ry + self.d3
        if pvy and (self.gl - py) * pvy > 0:                    # findpc: when and where it crosses his goal line
            frames = (self.gl - py) * 4096 / pvy
            xc = px + (self.gl - py) * pvx / pvy
            if frames <= 34 and abs(xc) <= 24:
                if frames <= 12 and abs(py) <= 264:
                    self.locked = True                          # goaliesave: a save move, his speed quartered
                    self.vx, self.vy = int(self.vx / 4), int(self.vy / 4)
                    if self.rom and self.frame0 is not None:
                        self.save_move(xc, frames, pz, pvz)
                gx = xc if abs(py) <= 252 else (24 if px >= 0 else -24)
        self.dir = vtoa(gx - (self.x + int(self.vx / 256)), gy - (self.y + int(self.vy / 256)))

    def step(self, px, py, pvx, pvy, pz=0, pvz=0):
        if self.seq:
            self.t += 1
        if self.unlock is not None:
            self.unlock -= 1
            if self.unlock <= 0:
                self.locked, self.unlock = False, None
        self.vx -= int(self.vx / 64)
        self.vy -= int(self.vy / 64)
        if not self.locked:
            self.timer -= 1
            if self.timer < 0:
                self.timer = self.aidef >> 2
                self.think(px, py, pvx, pvy, pz, pvz)
            if self.dir == 8:                                   # stopna
                self.vx = 0 if abs(self.vx) <= 150 else self.vx - math.copysign(150, self.vx)
                self.vy = 0 if abs(self.vy) <= 150 else self.vy - math.copysign(150, self.vy)
            else:
                ax, ay = DIRTAB[self.dir]
                nvx, nvy = self.vx + (ax * self.acc >> 5), self.vy + (ay * self.acc >> 5)
                if nvx * nvx + nvy * nvy <= self.vmax ** 2:
                    self.vx, self.vy = nvx, nvy
        self.x += self.vx / 4096
        self.y += self.vy / 4096


def play_out(start, target, pp, sha, perfect, goalie, reach, shift, rng, stick=False, rebound=False, launch=None):
    """One shot as the game plays it: 'goal', 'save', 'post', 'over' or 'wide' ('stick' with `stick`).

    stick (2026-10-23, off until it is shown to predict the recordings better): the goalie's stick as checkpuckcoll
    .ccx tests it, before his body, for a puck at height 5 or less rising no faster than $200: the blade (his sprite
    frame's hot point) within 8 units plays it (puckstick: caught or deflected, no goal); 8-14 units, nothing that frame
    and the body test skipped (the blind ring the Down slapshot goes through: GENESIS_SHOOTING 4.10, 5.5). Needs the
    goalie made with rom and frame.

    rebound (2026-10-23, off until shown to help): a body touch isn't always a save (puckgoalie): he holds the puck only
    if both its speed components are under a random limit, (random((2 + Puck Control) x 512) + $C00) x 2, a quarter
    of that when he's standing (not in a save move) with the puck in close (within 44 across, 210-270 out); otherwise
    it bounces straight out from his centre through where it touched him at 256 x that offset a frame (slowly), its
    height speed cleared, and he can't touch it for 10 frames. A touch behind his centre so drifts into the net: the
    other half of the through-the-legs goal (5.5).

    launch: (vx, vy, vz) in velocity words, the puck's own start (a pass shot, a deflection): no aim, no scatter; the
    target then only says which net."""
    (px, py, pz), (tx, ty, tz) = start, target
    if launch:
        vx, vy, vz = launch
    else:
        dx, dy, z = tx - px, ty - py, tz
        d3 = max(1, int(math.hypot(dx, dy)))
        if not (d3 <= 200 and rng.random() < perfect):        # doshot's scatter
            s = ((int(pp) >> 4) - (sha >> 1) + 16) * d3 >> 6
            s = min(s >> 1 if d3 <= 250 else s, 0x88)
            if s > 0:
                dx += rng.randrange(2 * s) - s
                sy = min(s, 60)
                ry = sy >> 1 if dy < 0 else sy                # halved shooting down the screen
                if ry > 0:
                    dy += rng.randrange(2 * ry) - ry
                if sy >> 1 > 0:
                    z += rng.randrange(sy >> 1)               # height only ever up
        vx, vy = pp * 68 * dx / d3, pp * 68 * dy / d3
        vz = min(0x1800, pp * 68 * z / d3 + d3 * 0xB33 / pp) if z else 0.0
    G = None
    if goalie:
        G = copy.copy(goalie)
        G.randomise(rng)
    x, y, h = px, py, pz
    front = 261 if ty > 0 else -261                           # the net's front: goal line 268 less half its depth and the puck
    for _ in range(400):
        nx, ny, nh = x + vx / 4096, y + vy / 4096, h + vz / 4096
        vz -= 102
        if nh < 0:
            nh, vz = 0.0, -vz / 2 if vz < 0 else vz
        if (ny - front) * (y - front) <= 0 and ny != y:
            k = (front - y) / (ny - y)
            cx, cz = x + k * (nx - x), h + k * (nh - h)
            if cz > 13:
                return "over" if abs(cx) <= 21 else "wide"
            if abs(cx) <= 20 and cz < 13:
                return "goal"
            return "post" if abs(cx) <= 21 else "wide"
        x, y, h = nx, ny, nh
        if G:
            G.step(x, y, vx, vy, h, vz)
            if G.nopuck > 0:                                  # just bounced off him: no touch for 10 frames
                G.nopuck -= 1
                if abs(y) > 300 or abs(x) > 140:
                    return "wide"
                continue
            if stick and G.frame0 is not None and h <= 5 and vz <= 0x200:
                bx, by = G.blade()
                sdx, sdy = bx - x, by - y
                if abs(sdx) <= 14 and abs(sdy) <= 14:
                    d2 = sdx * sdx + sdy * sdy
                    if d2 <= 64:
                        return "stick"
                    if d2 <= 196:
                        continue                              # the blind ring: no body test this frame
            gdx, gdy = G.x + shift - x, G.y - y
            if h <= 15 and abs(gdx) <= reach and abs(gdy) <= reach and gdx * gdx + gdy * gdy <= reach * reach:
                if not rebound:
                    return "save"
                limit = min(0x7FFF, (rng.randrange((2 + G.puck_control) << 9) + 0xC00) * 2)
                if not G.locked and abs(x) <= 0x2C and 0xD2 <= abs(y) <= 0x10E:
                    limit >>= 2                               # standing, the puck in close: a quarter
                if abs(vx) <= limit and abs(vy) <= limit:
                    return "save"                             # held
                vx, vy, vz = 256 * (x - G.x), 256 * (y - G.y), 0.0
                G.nopuck = 10
        if abs(y) > 300 or abs(x) > 140:
            return "wide"
    return "wide"


def auto_aim(px, py, gx, gy, gl):
    """shotdiradj: where the game aims one-timers and computer shooters, from the goalie's coming position."""
    d0, d1 = gx - px, gy - py
    d2 = math.isqrt(int(d0 * d0 + d1 * d1) + 1) or 1
    total = sum(int((d0 * (gl - py) - d1 * (post - px)) / d2) for post in (18, -18))
    if not -44 <= total <= 44:
        return 0
    if gl > 0:
        total = -total
    return 2 if total >= 0 else 6


def _work(rows, f, k):
    best = None
    for r in rows.get(k, ()):
        if r[0] > f:
            break
        best = r
    return best[2:] if best else None


def _velocity(m, f, k, back_ms=100, ahead=False):
    """A player's movement in units a frame over the last back_ms (ahead: over the next back_ms)."""
    t, P = m['t'], m['pos']
    if ahead:
        j = f
        while j + 1 < len(t) and t[j + 1] - t[f] <= back_ms:
            j += 1
        if j == f or t[j] == t[f]:
            return 0.0, 0.0
        frames = (t[j] - t[f]) / (1000 / 60)
        return ((P[(j * 12 + k) * 2] - P[(f * 12 + k) * 2]) / frames,
                (P[(j * 12 + k) * 2 + 1] - P[(f * 12 + k) * 2 + 1]) / frames)
    j = f
    while j > 0 and t[f] - t[j - 1] <= back_ms:
        j -= 1
    if j == f or t[f] == t[j]:
        return 0.0, 0.0
    frames = (t[f] - t[j]) / (1000 / 60)
    return ((P[(f * 12 + k) * 2] - P[(j * 12 + k) * 2]) / frames, (P[(f * 12 + k) * 2 + 1] - P[(j * 12 + k) * 2 + 1]) / frames)


_CACHE = {}  # every input of a shot's play-out -> its xg (the live broadcast re-analyses the game every few seconds)


def launched(m, f, ms=50):
    """The puck's velocity (x, y, height; velocity words) leaving sample f, from where it is ms later, and how
    uncertain its direction is (radians: the match file's positions are rounded to 0.1), or None."""
    t, P = m['t'], m['puck']
    q = next((q for q in range(f + 1, len(t)) if t[q] - t[f] >= ms), None)
    if q is None or P[3 * q + 2] < -100 or P[3 * f + 2] < -100:
        return None
    frames = (t[q] - t[f]) / (1000 / 60)
    v = [(P[3 * q + i] - P[3 * f + i]) / frames * 4096 for i in range(3)]
    moved = math.hypot(P[3 * q] - P[3 * f], P[3 * q + 1] - P[3 * f + 1])
    return (*v, 0.1 / moved) if moved and math.hypot(v[0], v[1]) > 400 else None


def aimed(launch, rng, lift):
    """A play-out's start from launched(): its direction jittered by the recording's error, the lift given."""
    vx, vy, _vz, sd = launch
    a = rng.gauss(0, sd)
    return vx * math.cos(a) - vy * math.sin(a), vx * math.sin(a) + vy * math.cos(a), lift


def add_expected_goals(m, stick_rom=None, rebound=False, lock=False):
    """Each shot, one-timer and pass shot of a Genesis match gets `xg`, the chance it goes in by the game's rules (see
    above).
    stick_rom: the ROM's bytes to model the goalie's stick (play_out's `stick`); rebound: play_out's `rebound`; lock:
    a goalie in a save move at the release starts locked in it (Goalie's `locked`)."""
    rom = GenesisRom(stick_rom) if stick_rom else None
    if m.get('system', 'genesis') != 'genesis' or not m.get('work'):
        return
    rows = {}
    for r in m['work']:
        rows.setdefault(r[1], []).append(r)
    role, roster, P = m['role'], m['roster'], m['pos']
    for sh in m.get('shotList', []):
        if sh['kind'] not in ('shot', 'one-timer', 'pass shot') or sh['team'] not in (0, 1):
            continue
        f, team = sh['f'], sh['team']
        launch = launched(m, f) if sh['kind'] == 'pass shot' else None
        if sh['kind'] == 'pass shot' and launch is None:
            continue
        own = next((1 if P[(f * 12 + k) * 2 + 1] > 0 else -1 for k in range(team * 6, team * 6 + 6) if role[f * 12 + k] == '0'), None)
        if own is None:
            continue
        gl = 264 if own < 0 else -264
        px, py, pz = m['puck'][3 * f], m['puck'][3 * f + 1], max(0.0, m['puck'][3 * f + 2])
        shooter = next((k for k in range(team * 6, team * 6 + 6)
                        if role[f * 12 + k] != 'x' and DIGITS.index(roster[f * 12 + k]) == sh['idx']), None)
        w = _work(rows, f, shooter) if shooter is not None else None
        sha = w[5] if w else 15
        gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + k] == '0'), None)
        goalie, reach, shift, coming = None, 0, 0, None
        if gk is not None:
            gx, gy = P[(f * 12 + gk) * 2], P[(f * 12 + gk) * 2 + 1]
            gw = _work(rows, f, gk) or [64, 15, 15, 11, 15, 0]
            vgx, vgy = _velocity(m, f, gk)
            reach = REACH[min(19, (gw[1] + 2) >> 1)]
            if (m['ctrl'][f] >> gk) & 1:
                reach = 15
            if sh['kind'] == 'one-timer':
                reach = 12
            anim = m['anim'][(f * 12 + gk) * 4:(f * 12 + gk) * 4 + 4]
            saving = 0
            if lock and m.get('locked') is not None:            # the recording's own lock (pflags bit 5): locked
                rows_l = m['locked']                             # now, until the frame it clears
                at = bisect.bisect_right([r[0] for r in rows_l], f) - 1
                if at >= 0 and rows_l[at][1] >> gk & 1:
                    end = next((r[0] for r in rows_l[at + 1:] if not r[1] >> gk & 1), len(m['t']) - 1)
                    saving = max(1, round((m['t'][end] - m['t'][f]) / (1000 / 60)))
            elif lock and int(anim, 16) in SAVE_ANIM:            # older match files: frames left in the save move
                j = f
                while j > 0 and m['anim'][((j - 1) * 12 + gk) * 4:((j - 1) * 12 + gk) * 4 + 4] == anim:
                    j -= 1
                saving = max(0, SAVE_LEN[int(anim, 16)] - round((m['t'][f] - m['t'][j]) / (1000 / 60)))
                if saving:                                        # locked: his path can't answer the puck, so the
                    vgx, vgy = _velocity(m, f, gk, ahead=True)    # next 100 ms show his speed (a fresh stack slides)
            if anim in PAD_STACK:
                reach, shift = 18, PAD_STACK[anim]
            gfr = int(m['frame'][(f * 12 + gk) * 3:(f * 12 + gk) * 3 + 3], 16) if rom and 'frame' in m else None
            goalie = Goalie(gx, gy, vgx * 4096, vgy * 4096, *gw[:4], rom=rom, frame=gfr or None,
                            facing=int(m['facing'][f * 12 + gk]) if rom else 4,
                            mirror=bool(rom) and m.get('mirror', '')[f * 12 + gk:f * 12 + gk + 1] == '1',
                            puck_control=gw[4] if len(gw) > 4 else 10, locked=saving)
            coming = (gx + 8 * vgx, gy + 8 * vgy)   # shotdiradj looks half his velocity's high byte ahead
        if launch:
            d = 8
        elif sh['kind'] == 'one-timer' or not sh.get('human'):
            d = auto_aim(px, py, *coming, gl) if coming else 8
        else:
            d = sh.get('aim', {}).get('d')
            if d is None:
                continue
        tx, tz = AIM[d]
        perfect = (sha + 1) / (sha + 16)
        if any(dl['team'] == team and dl['f'] <= f <= dl.get('end', f) for dl in m.get('delayed', [])):
            perfect = 1.0                                         # ReadGoaliePulled: the delayed-penalty snipe
        pp = max(1.0, sh['speed'] / 68)
        key = (m.get('name', ''), f, team, sh['idx'], px, py, pz, tx, gl, tz, pp, sha, perfect, reach, shift,
               (gx, gy, vgx, vgy, *gw[:5], saving) if goalie else None, bool(rom), rebound, sh['kind'], launch)
        if key in _CACHE:
            sh['xg'] = _CACHE[key]
            continue
        rng = random.Random(f"{m.get('name', '')}:{f}:{team}:{sh['idx']}")

        def start():                                              # a pass shot's lift: random, 0-4,095 (dopass)
            return aimed(launch, rng, rng.randrange(4096)) if launch else None
        goals = sum(play_out((px, py, pz), (tx, gl, tz), pp, sha, perfect, goalie, reach, shift, rng,
                             stick=bool(rom), rebound=rebound, launch=start()) == 'goal' for _ in range(N_SAMPLES))
        sh['xg'] = _CACHE[key] = round(goals / N_SAMPLES, 3)


def goalie_states(matches):
    """The goalies' states at the release of the shots in these match files (not blocked): [dx, dy, vx, vy] from his set
    spot for that puck position (units; units a frame), as if the shot were at the top net, split into computer goalies
    and people in net. The viewer's xG map draws its "as in games" goalies from them (XG_GOALIE_STATES in viewer.html):
    in the seven recordings, a goalie within 3 units of his spot let in 1 shot of 31; 10 or more out of it, 22 of 59."""
    out = {"cpu": [], "person": []}
    for m in matches:
        P = m["pos"]
        for sh in m.get("shotList", []):
            if sh["kind"] not in ("shot", "one-timer") or sh["result"] == "blocked" or sh["team"] not in (0, 1):
                continue
            f, team = sh["f"], sh["team"]
            gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][f * 12 + k] == "0"), None)
            if gk is None:
                continue
            gx, gy = P[(f * 12 + gk) * 2], P[(f * 12 + gk) * 2 + 1]
            px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
            d3 = 260 if gy > 0 else -260
            rx, ry = px, max(-259, min(259, py)) - d3
            if rx * rx + ry * ry > 900:
                ln = math.isqrt(int(rx * rx + ry * ry)) + 1
                rx, ry = rx * 26 / ln, ry * 18 / ln
            vx, vy = _velocity(m, f, gk)
            o = [gx - rx, gy - (ry + d3), vx, vy]
            if gy < 0:
                o = [-v for v in o]
            out["person" if (m["ctrl"][f] >> gk) & 1 else "cpu"].append([round(v, 1) if i < 2 else round(v, 2) for i, v in enumerate(o)])
    return out


def stick_tables(rom):
    """What the viewer's xG map needs for the stick model (XG_GEN_ROM): the ready frame for each facing, the ten save
    moves' (frame, frames shown) lists for each facing (goaliesave's .saveanim order), and each of those frames' blade
    offset unmirrored (x, y up the screen)."""
    g = GenesisRom(rom)
    ready = [g.anim(READY, f)[0][0] for f in range(8)]
    saves = [[g.anim(spa, f) for f in range(8)] for spa in SAVE_ANIM]
    frames = set(ready) | {fr for move in saves for seq in move for fr, _ in seq}
    return {"ready": ready, "saves": saves, "hot": {str(fr): list(g.hot(fr, False)) for fr in sorted(frames)}}


if __name__ == "__main__" and len(sys.argv) > 2 and sys.argv[1] == "--stick-tables":
    # python tools/xg.py --stick-tables <rom>: the viewer's XG_GEN_ROM
    import json
    print(json.dumps(stick_tables(open(sys.argv[2], "rb").read()), separators=(",", ":")))
elif __name__ == "__main__":
    # python tools/xg.py matches/a.js matches/b.js ...: the goalie states for the viewer's XG_GOALIE_STATES
    import json
    import sys
    games = []
    for path in sys.argv[1:]:
        text = open(path, encoding="utf-8").read()
        games.append(json.loads(text[text.index("{"):text.rindex("}") + 1]))
    print(json.dumps(goalie_states(games), separators=(",", ":")))
