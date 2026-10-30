"""Expected goals from the SNES game's own rules (2026-10-17; see docs/SNES_SHOOTING.md 4.7).

Every shot is played out N_SAMPLES times the way the SNES game would (doshot, updateplayers, checkgoal,
checkpuckcoll_ccx, assgoalie): sent exactly at its aim point with chance (Shot Accuracy + 1) / (Shot Accuracy + 16)
from within 200 of it (distances by the game's ApproxLength), else with the game's scatter; the puck flies two frames
a step (the game loop's usual pace) under gravity 96 a frame; a goal when its centre crosses the net's front (y 259)
within 17 of the middle under the crossbar (13), a post out to 22. The goalie stops it with his body (a box -11 .. 10
each way around his centre, any height) or with the stick / glove area of the sprite frame he shows (GetHot,
GetFrameHot: a circle around the frame's hot point, within a height band). He moves as the computer goalie does:
rethinking every half his Defensive Awareness value (aidef / 2 frames), heading for the puck's predicted spot on an
ellipse 26 across and 20 out, or for where it will cross his goal line once it will within 35 frames (the crossing
worked out every 5 frames, as pucknorm does); at a rethink with the crossing under 19 frames he starts a save move
(GoalieSaveList, chosen by the puck's direction against his facing and its height; his speed halved) and keeps skating
through it (a save move sets pfalock, not pf2aip). A person in net is moved the same way.

Checked against the five recorded SNES games: driven by the recorded puck, the emulated goalie lands a median 0.8
units from the recorded one when the puck arrives; over 175 unblocked shots the model gives 40.1 expected goals
against 32 scored (computer in net 25.7 / 21, people 14.4 / 11; posts and misses as recorded), log loss 0.27 against
0.48 for one rate for all shots. The one fitted number, GOALIE_SPREAD, stands for the emulated goalie's error.

Pass shots (2026-10-30) have no aim or scatter: the puck leaves as the recording shows it over the next 50 ms
(xg.launched, its direction jittered by the recording's rounding), with a fresh random lift each play-out (dopass with
no target: vertical speed 0 to $FFF, SNES_MECHANICS 6.1). Deflections and kind 'other' have no xG.
"""
import copy
import random
import struct

N_SAMPLES = 400
GOALIE_SPREAD = 2.0
STEP = 2   # frames a game step: the SNES game loop mostly runs every other frame
AIM = [(0, 12), (15, 12), (15, 6), (15, 0), (0, 0), (-15, 0), (-15, 6), (-15, 12), (0, 6)]  # shotsets (screen x, z)
SAVES = [0xE1E2, 0xE214, 0xE2AA, 0xE2FC, 0xE246, 0xE278, 0xE862, 0xE7D0, 0xE73E]       # GoalieSaveList
DIRSTEP = [(0, 6), (4, 4), (6, 0), (4, -4), (0, -6), (-4, -4), (-6, 0), (-4, 4)]        # playeracc .8
FRICTION = {1: 0xFD, 2: 0xFA, 3: 0xF7}                                                   # updateplayers .21
VTOA_TABLE = [1, 7, 3, 5, 0, 0, 4, 4, 2, 6, 2, 6, 1, 7, 3, 5]
TWO_THIRDS = [0, 1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 19,
              20, 21, 21, 22, 23, 23, 24, 25, 25, 26, 27, 27, 28, 29, 29, 30, 31, 31]
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def approx_length(a, b):
    """The game's ApproxLength: the longer side plus a quarter (or 3/8) of the shorter."""
    a, b = abs(int(a)), abs(int(b))
    big, small = max(a, b), min(a, b)
    return big + (small >> 2) if (big >> 1) >= small else big + ((small + (small >> 1)) >> 2)


def vtoa(dx, dy, dead=0):
    """The SNES vtoa: 8 directions (0 = +Y, clockwise), diagonal whenever neither part is more than twice the other."""
    dx, dy = int(dx), int(dy)
    if (abs(dx) < dead and abs(dy) < dead) or (dx == 0 and dy == 0):
        return 8
    i = (1 if dx < 0 else 0) + (2 if dy < 0 else 0)
    if 2 * abs(dy) >= abs(dx):
        i |= 4
    if 2 * abs(dx) >= abs(dy):
        i |= 8
    return VTOA_TABLE[i]


class RomData:
    """What the model reads from the ROM: each sprite frame's hot point and area, and the save moves' frames."""

    def __init__(self, rom):
        from systems import snes as SN
        self.SN, self.rom = SN, SN.strip_header(rom)
        self._hot, self._anim = {}, {}

    def hot(self, frame):
        """(hot x, hot y (up), radius, top of the height band, bottom) for a goalie frame (never mirrored)."""
        if frame <= 0:
            return None
        if frame not in self._hot:
            SN, rom = self.SN, self.rom
            base = SN.file_offset(SN.SPRITE_FRAMES)
            off = struct.unpack_from("<I", rom, base + 4 * (frame - 1))[0]
            at = base + (off >> 16) * 0x8000 + (off & 0xFFFF)
            x1, y1, x2, y2 = struct.unpack_from("<bbbb", rom, at + 0x12)
            d2 = abs(x2 - x1)
            d3, d4 = TWO_THIRDS[min(47, abs(y1 - y2))], TWO_THIRDS[min(47, d2)]
            self._hot[frame] = (x1, -y1, d2, max(d3 + d4, 5), d3 - d4)
        return self._hot[frame]

    def anim(self, spa, facing):
        key = (spa, facing)
        if key not in self._anim:
            SN, rom = self.SN, self.rom
            ptr = struct.unpack_from("<H", rom, SN.file_offset(SN.ANIM_BANK | spa) + 2 * (facing & 7))[0]
            seq, at = [], SN.file_offset(SN.ANIM_BANK | ptr)
            while len(seq) < 40:
                fr, t = struct.unpack_from("<Hh", rom, at)
                seq.append((fr, t))
                at += 4
                if t < 0:
                    break
            self._anim[key] = seq
        return self._anim[key]


class Goalie:
    """The SNES computer goalie, a game step at a time. Velocities in the game's words (units x 4096 a frame)."""

    def __init__(self, data, x, y, vx, vy, facing, frame, weight, agility, speed, aidef, puck_control=10):
        self.data = data
        self.puck_control, self.nopuck = puck_control, 0
        self.x, self.y, self.vx, self.vy, self.facing, self.frame = x, y, vx, vy, facing, frame
        self.acc = 32 - (weight >> 3) + agility + (agility >> 1) + 8
        self.vmax = (20 + speed) * 261
        self.aidef = aidef
        self.d3, self.gl = (260, 264) if y > 0 else (-260, -264)
        self.timer, self.cross_timer, self.dir = 0, 0, 8
        self.cross, self.save, self.save_t = None, None, 0

    def randomise(self, rng):
        self.timer = rng.randrange((self.aidef >> 1) + 1)
        self.cross_timer = rng.randrange(5)
        self.x += rng.gauss(0, GOALIE_SPREAD)
        self.y += rng.gauss(0, GOALIE_SPREAD)

    def update_cross(self, px, py, pvx, pvy):
        if pvy == 0 or (self.gl - py) * pvy <= 0:
            self.cross = None
            return
        frames = (self.gl - py) * 4096 / pvy
        self.cross = [max(-136, min(136, px + frames * pvx / 4096)), frames]

    def save_move(self, px, py, pvx, pvy, pz, pvz):
        tx, ty = px + int(pvx / 1024), py + int(pvy / 1024)
        d = vtoa(tx - self.x, ty - self.y)
        d3 = 0 if d == 8 else (d - self.facing) & 7
        if d3 == 0:
            if self.facing in (0, 4):
                d3 = 1 if (tx - self.x >= 0) == (self.facing == 0) else 7
            else:
                d3 = 1 if abs(tx - self.x) >= abs(ty - self.y) else 7
        if d3 == 4:
            if -0x800 < pvy < 0x800:
                return 8
            d3 = 1
        d0 = d3 >> 2
        if d3 >= 4:
            d3 = 8 - d3
        if d3 >= 2:
            return d0 + 6
        if pz < 8 and pvz < 0x800:
            d0 += 4
        return d0

    def think(self, px, py, pvx, pvy, pz, pvz, rng):
        d0, d1 = px, max(-259, min(259, py)) - self.d3
        if not -46 < d1 < 46:
            ty = py + 1.5 * int(pvy / 512)
            if abs(ty) >= 224:
                tx = px + int(pvx / 512)
            else:
                tx = px + (1.5 * int(pvx / 256) if rng.random() < 1 / 8 else int(pvx / 256))
            d0, d1 = tx, max(-259, min(259, ty)) - self.d3
        ln = approx_length(d0, d1)
        if ln >= 30:
            d0, d1 = d0 * 26 / (ln + 1), d1 * 20 / (ln + 1)
        gx, gy = d0, d1 + self.d3
        want = vtoa(px - self.x, py - self.y)
        if want != 8 and want != self.facing:
            self.facing = (self.facing + (1 if (want - self.facing) % 8 < 4 else -1)) % 8
        if self.cross and self.cross[1] < 35:
            cx, frames = self.cross
            if -25 < cx < 25:
                if frames < 19 and abs(py) < 265 and self.save is None:
                    self.vx, self.vy = self.vx / 2, self.vy / 2
                    self.save = self.data.anim(SAVES[self.save_move(px, py, pvx, pvy, pz, pvz)], self.facing)
                    self.save_t = 0
                gx = cx if abs(py) < 252 else (24 if px >= 0 else -24)
        self.dir = vtoa(gx - (self.x + int(self.vx / 256)), gy - (self.y + int(self.vy / 256)), 5)

    def step(self, px, py, pvx, pvy, pz, pvz, rng, frames=STEP):
        f = FRICTION.get(frames, 0xFA)
        self.vx, self.vy = int(self.vx * f / 256), int(self.vy * f / 256)
        self.cross_timer -= frames
        if self.cross_timer < 0:
            self.cross_timer += 5
            self.update_cross(px, py, pvx, pvy)
        elif self.cross:
            self.cross[1] -= frames
        if self.save is not None:
            self.save_t += frames
            t, self.frame = 0, self.save[-1][0]
            for fr, dur in self.save:
                if dur < 0 or self.save_t < t + dur:
                    self.frame = fr
                    break
                t += dur
        self.timer -= frames
        if self.timer < 0:
            self.timer = max(0, self.timer + (self.aidef >> 1))
            self.think(px, py, pvx, pvy, pz, pvz, rng)
        if self.dir == 8:
            self.vx, self.vy = int(self.vx / 2), int(self.vy / 2)   # StopNA: a computer goalie halves his speed
        else:
            sx, sy = DIRSTEP[self.dir]
            nvx, nvy = self.vx + sx * self.acc * frames, self.vy + sy * self.acc * frames
            if nvx * nvx + nvy * nvy <= self.vmax ** 2:
                self.vx, self.vy = nvx, nvy
        self.x += frames * self.vx / 4096
        self.y += frames * self.vy / 4096


def play_out(px, py, tx, ty, tz, pp, sha, perfect, goalie, rng, rebound=False, launch=None):
    """One shot as the SNES game plays it: 'goal', 'save', 'post', 'over' or 'wide'.

    rebound (2026-10-29, xg_calib.py: close follow-ups scored half again as often in the game as in the model): a touch
    of his body box isn't always a save (puckgoalie, SNES_SHOOTING 5.4): he holds the puck only if both its speed
    components are under random((2 + Puck Control) x 512) + $2000; otherwise it bounces off, its velocity 256 x its
    offset from his centre (the up-and-down part against the way he is moving), its height speed cleared, and he can't
    touch it for 10 frames: it can go in off him.

    launch: (vx, vy, vz), the puck's own start (a pass shot, a deflection): no aim, no scatter; ty then only says which
    net."""
    if launch:
        vx, vy, vz = launch
    else:
        dx, dy, z = tx - px, ty - py, tz
        d3 = max(1, approx_length(dx, dy))
        if not (d3 < 201 and rng.random() < perfect):
            s = (((int(pp) >> 3) - sha + 16) * d3) >> 6
            s = min(s >> 1 if d3 < 251 else s, 0x88)
            if s > 0:
                dx += rng.randrange(2 * s) - s
            sy = min(s, 60)
            ry = sy >> 1 if dy < 0 else sy
            if ry > 0:
                dy += rng.randrange(2 * ry) - ry
            if sy >> 1 > 0:
                z += rng.randrange(sy >> 1)
        vx, vy = 2 * pp * 68 * dx / d3, 2 * pp * 68 * dy / d3
        vz = min(0x1800, 2 * pp * 68 * z / d3 + (0xB33 * d3 / pp) / 2) if z else 0.0
    G = None
    if goalie:
        G = copy.copy(goalie)
        G.randomise(rng)
    x, y, h = px, py, 0.0
    front = 259 if ty > 0 else -259
    for _ in range(0, 300, STEP):
        nx, ny = x + STEP * vx / 4096, y + STEP * vy / 4096
        vz -= 96 * STEP
        nh = h + STEP * vz / 4096
        if nh < 0:
            nh, vz = 0.0, -vz / 2 if vz < 0 else vz
        if (ny - front) * (y - front) <= 0 and ny != y:
            q = (front - y) / (ny - y)
            cx, cz = x + q * (nx - x), h + q * (nh - h)
            if cz >= 13:
                return "over" if abs(cx) <= 22 else "wide"
            if abs(cx) <= 17:
                return "goal"
            return "post" if abs(cx) <= 22 else "wide"
        x, y, h = nx, ny, nh
        if G:
            G.step(x, y, vx, vy, h, vz, rng)
            if G.nopuck > 0:                                  # just bounced off him: no touch for 10 frames
                G.nopuck -= STEP
                if abs(y) > 300 or abs(x) > 140:
                    return "wide"
                continue
            hot = G.data.hot(G.frame)
            if hot:
                hx, hy, d2, top, bottom = hot
                ex, ey = G.x + hx - x, G.y + hy - y
                if abs(ex) < d2 and abs(ey) < d2 and h <= top and (bottom < 0 or bottom < h) and ex * ex + ey * ey <= d2 * d2:
                    return "save"
            bx, by = G.x - x, G.y - y
            if -11 <= bx <= 10 and -11 <= by <= 10:
                if not rebound:
                    return "save"
                limit = rng.randrange((2 + G.puck_control) << 9) + 0x2000
                if abs(vx) < limit and abs(vy) < limit:
                    return "save"                             # held
                ox, oy = int(x - G.x), int(y - G.y)
                if oy:
                    oy += 1
                if (G.vy >= 0) == (oy >= 0):
                    oy = -oy                                  # up or down the ice against the way he is moving
                vx, vy, vz = 256 * ox, 256 * oy, 0.0
                G.nopuck = 10
        if abs(y) > 300 or abs(x) > 140:
            return "wide"
    return "wide"


_CACHE = {}  # every input of a shot's play-out -> its xg (the live broadcast re-analyses the game every few seconds)


def touch_timer(m, f, gk, frames=10):
    """The goalie's no-touch timer at frame f, as near as a recording shows it: puckgoalie sets it to 10 when the puck
    comes off his body (5.4), and checkpuckcoll_ccx then skips him, stick and body, until it runs out. The puck loose
    inside his body box (within 11 each way) in the last `frames` frames: 10 less the frames since; else 0."""
    T, P, own = m["t"], m["pos"], m["owner"]
    j = f
    while j > 0 and T[f] - T[j - 1] <= frames * 1000 / 60:
        j -= 1
        if own[j] == gk:
            return 0                                       # he had it: a pass or a clear, not a bounce
        dx = m["puck"][3 * j] - P[(j * 12 + gk) * 2]
        dy = m["puck"][3 * j + 1] - P[(j * 12 + gk) * 2 + 1]
        if own[j] < 0 and -11 <= dx <= 11 and -11 <= dy <= 11:
            return max(0, frames - round((T[f] - T[j]) / (1000 / 60)))
    return 0


def add_expected_goals(m, rom, notouch=False):
    """Each shot, one-timer and pass shot of an SNES match gets `xg` (rom: the ROM's bytes, for the goalie's
    frames). notouch: the goalie's no-touch timer from the recording (touch_timer)."""
    from xg import aimed, launched
    if m.get("system") != "snes" or not m.get("work"):
        return
    data = RomData(rom)
    rows = {}
    for r in m["work"]:
        rows.setdefault(r[1], []).append(r)

    def work(f, k):
        best = None
        for r in rows.get(k, ()):
            if r[0] > f:
                break
            best = r
        return best[2:] if best else None

    T, P, role, roster = m["t"], m["pos"], m["role"], m["roster"]
    for sh in m.get("shotList", []):
        loose = sh["kind"] == "pass shot"
        if sh["kind"] not in ("shot", "one-timer", "pass shot") or sh["team"] not in (0, 1)                 or "aim" not in sh and not loose:
            continue
        f, team = sh["f"], sh["team"]
        launch = launched(m, f) if loose else None
        if loose and launch is None:
            continue
        own = next((k for k in range(team * 6, team * 6 + 6) if role[f * 12 + k] == "0"), None)
        if own is None:
            continue
        ty = 264 if P[(f * 12 + own) * 2 + 1] < 0 else -264   # doshot aims at y +/-$108
        px, py = m["puck"][3 * f], m["puck"][3 * f + 1]
        shooter = next((k for k in range(team * 6, team * 6 + 6)
                        if role[f * 12 + k] != "x" and DIGITS.index(roster[f * 12 + k]) == sh["idx"]), None)
        w = work(f, shooter) if shooter is not None else None
        sha = w[5] if w else 10
        gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + k] == "0"), None)
        goalie = None
        if gk is not None:
            gw = work(f, gk) or [48, 10, 10, 11, 10, 0]
            j0 = f
            while j0 > 0 and T[f] - T[j0 - 1] <= 100:
                j0 -= 1
            fr0 = max(1, (T[f] - T[j0]) / (1000 / 60))
            gx, gy = P[(f * 12 + gk) * 2], P[(f * 12 + gk) * 2 + 1]
            gvx = (gx - P[(j0 * 12 + gk) * 2]) / fr0 * 4096
            gvy = (gy - P[(j0 * 12 + gk) * 2 + 1]) / fr0 * 4096
            frame = int(m["frame"][(f * 12 + gk) * 3:(f * 12 + gk) * 3 + 3], 16)
            goalie = Goalie(data, gx, gy, gvx, gvy, int(m["facing"][f * 12 + gk]), frame, *gw[:4],
                            puck_control=gw[4] if len(gw) > 4 else 10)
            if notouch:
                goalie.nopuck = touch_timer(m, f, gk)
        tx, tz = AIM[sh["aim"]["d"]] if not loose else AIM[8]
        pp = max(1.0, sh["speed"] / 136)
        perfect = (sha + 1) / (sha + 16)
        key = (m.get('name', ''), f, team, sh['idx'], px, py, tx, ty, tz, pp, sha,
               (gx, gy, gvx, gvy, int(m["facing"][f * 12 + gk]), frame, *gw[:4], goalie.nopuck) if goalie else None,
               sh["kind"], launch)
        if key in _CACHE:
            sh["xg"] = _CACHE[key]
            continue
        rng = random.Random(f"{m.get('name', '')}:{f}:{team}:{sh['idx']}")

        def start():                                              # a pass shot's lift: random, 0-$FFF (dopass)
            return aimed(launch, rng, rng.randrange(0x1000)) if launch else None
        goals = sum(play_out(px, py, tx, ty, tz, pp, sha, perfect, goalie, rng, launch=start()) == "goal"
                    for _ in range(N_SAMPLES))
        sh["xg"] = _CACHE[key] = round(goals / N_SAMPLES, 3)


def set_spot(px, py, top):
    """Where a set computer goalie stands with the puck still at (px, py) (assgoalie's spot, no puck speed)."""
    d3 = 260 if top else -260
    d0, d1 = px, max(-259, min(259, py)) - d3
    ln = approx_length(d0, d1)
    if ln >= 30:
        d0, d1 = d0 * 26 / (ln + 1), d1 * 20 / (ln + 1)
    return d0, d1 + d3


def goalie_states(matches):
    """The goalies' states at the release of these SNES matches' shots (not blocked), from his set spot, as if the shot
    were at the top net: [dx, dy, vx, vy] (units; units a frame), for computer goalies, people in net and one-timers
    (any goalie). For the viewer's xG map (XG_SNES_GOALIE_STATES)."""
    out = {"cpu": [], "person": [], "onetimer": []}
    for m in matches:
        T, P = m["t"], m["pos"]
        for sh in m.get("shotList", []):
            if sh["kind"] not in ("shot", "one-timer") or sh["result"] == "blocked" or sh["team"] not in (0, 1):
                continue
            f, team = sh["f"], sh["team"]
            gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][f * 12 + k] == "0"), None)
            if gk is None:
                continue
            gx, gy = P[(f * 12 + gk) * 2], P[(f * 12 + gk) * 2 + 1]
            sx, sy = set_spot(m["puck"][3 * f], m["puck"][3 * f + 1], gy > 0)
            j0 = f
            while j0 > 0 and T[f] - T[j0 - 1] <= 100:
                j0 -= 1
            fr0 = max(1, (T[f] - T[j0]) / (1000 / 60))
            o = [gx - sx, gy - sy, (gx - P[(j0 * 12 + gk) * 2]) / fr0, (gy - P[(j0 * 12 + gk) * 2 + 1]) / fr0]
            if gy < 0:
                o = [-v for v in o]
            o = [round(v, 1) if i < 2 else round(v, 2) for i, v in enumerate(o)]
            out["onetimer" if sh["kind"] == "one-timer" else "person" if (m["ctrl"][f] >> gk) & 1 else "cpu"].append(o)
    return out


def map_tables(rom):
    """What the viewer's SNES xG map needs from the ROM: the goalie's ready and save frames for each facing, with each
    frame's hot point and area (XG_SNES_ROM)."""
    data = RomData(rom)
    anims = {"ready": [data.anim(0xE0FE, d)[0][0] for d in range(8)],
             "saves": [[data.anim(spa, d) for d in range(8)] for spa in SAVES]}
    frames = set(anims["ready"]) | {fr for move in anims["saves"] for seq in move for fr, _ in seq}
    return {"anims": anims, "hot": {str(fr): list(data.hot(fr)) for fr in sorted(frames)}}


if __name__ == "__main__":
    # python tools/xg_snes.py <rom> matches/a.js ...: the viewer's XG_SNES_ROM and XG_SNES_GOALIE_STATES
    import json
    import sys
    games = []
    for path in sys.argv[2:]:
        text = open(path, encoding="utf-8").read()
        games.append(json.loads(text[text.index("{"):text.rindex("}") + 1]))
    print(json.dumps({"rom": map_tables(open(sys.argv[1], "rb").read()), "states": goalie_states(games)}, separators=(",", ":")))
