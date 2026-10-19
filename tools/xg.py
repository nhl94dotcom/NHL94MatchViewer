"""Expected goals from the Genesis game's own rules (2026-10-17; see docs/GENESIS_MECHANICS.md 4.9).

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
out: the goalie's stick (a puck at height 5 or less near the blade), skaters in the way, the in-close top-shelf lift.

Shots with a shooting animation only (shots and one-timers); pass shots and deflections have no xG.
"""
import copy
import math
import random

N_SAMPLES = 400
GOALIE_SPREAD = 4.0   # units: the emulated goalie's position error, fitted (log loss) over the recordings
AIM = [(0, 12), (16, 12), (16, 6), (16, 0), (0, 0), (-16, 0), (-16, 6), (-16, 12), (0, 6)]  # doshot's shotsets (screen x, z)
REACH = [12, 12, 13, 13, 13, 13, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15, 15, 15]  # .cbg, by (Agility + 2) / 2
PAD_STACK = {"0250": -6, "02a2": 6}   # gstackr / gstackl: the body test moves 6 to one side
DIRTAB = [(0, 200), (141, 141), (200, 0), (141, -141), (0, -200), (-141, -141), (-200, 0), (-141, 141)]
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def vtoa(dx, dy):
    """The game's 8-way direction of a vector (0 = +Y, clockwise); 8 when both parts are within 4."""
    if -4 <= dx <= 4 and -4 <= dy <= 4:
        return 8
    return int((math.degrees(math.atan2(dx, dy)) % 360 + 22.5) // 45) % 8


class Goalie:
    """The computer goalie's movement, frame by frame. Velocities in the game's words (units x 4096 a frame)."""

    def __init__(self, x, y, vx, vy, weight, agility, speed, aidef):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.acc = (64 - weight // 4 + agility + 2 + agility + 16) // 2   # playeracc; goalies count Agility twice, + 16
        n = min(30, speed + 2)                                            # MaxSpeed, the odd half-step included
        self.vmax = (20 + n // 2) * 275 + (137 if n % 2 and n < 30 else 0)
        self.aidef = aidef
        self.d3, self.gl = (260, 264) if y > 0 else (-260, -264)
        self.timer, self.dir, self.locked, self.k = 0, 8, False, 216

    def randomise(self, rng):
        self.timer = rng.randrange((self.aidef >> 2) + 1) - 1   # where his rethink countdown stands
        self.k = 0xA0 + 16 * rng.randrange(8)                   # the look-ahead, from the game clock's low bits
        self.x += rng.gauss(0, GOALIE_SPREAD)
        self.y += rng.gauss(0, GOALIE_SPREAD)

    def think(self, px, py, pvx, pvy):
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
                gx = xc if abs(py) <= 252 else (24 if px >= 0 else -24)
        self.dir = vtoa(gx - (self.x + int(self.vx / 256)), gy - (self.y + int(self.vy / 256)))

    def step(self, px, py, pvx, pvy):
        self.vx -= int(self.vx / 64)
        self.vy -= int(self.vy / 64)
        if not self.locked:
            self.timer -= 1
            if self.timer < 0:
                self.timer = self.aidef >> 2
                self.think(px, py, pvx, pvy)
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


def play_out(start, target, pp, sha, perfect, goalie, reach, shift, rng):
    """One shot as the game plays it: 'goal', 'save', 'post', 'over' or 'wide'."""
    (px, py, pz), (tx, ty, tz) = start, target
    dx, dy, z = tx - px, ty - py, tz
    d3 = max(1, int(math.hypot(dx, dy)))
    if not (d3 <= 200 and rng.random() < perfect):            # doshot's scatter
        s = ((int(pp) >> 4) - (sha >> 1) + 16) * d3 >> 6
        s = min(s >> 1 if d3 <= 250 else s, 0x88)
        if s > 0:
            dx += rng.randrange(2 * s) - s
            sy = min(s, 60)
            ry = sy >> 1 if dy < 0 else sy                    # halved shooting down the screen
            if ry > 0:
                dy += rng.randrange(2 * ry) - ry
            if sy >> 1 > 0:
                z += rng.randrange(sy >> 1)                   # height only ever up
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
            G.step(x, y, vx, vy)
            gdx, gdy = G.x + shift - x, G.y - y
            if h <= 15 and abs(gdx) <= reach and abs(gdy) <= reach and gdx * gdx + gdy * gdy <= reach * reach:
                return "save"
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


def _velocity(m, f, k, back_ms=100):
    """A player's movement in units a frame over the last back_ms."""
    t, P = m['t'], m['pos']
    j = f
    while j > 0 and t[f] - t[j - 1] <= back_ms:
        j -= 1
    if j == f or t[f] == t[j]:
        return 0.0, 0.0
    frames = (t[f] - t[j]) / (1000 / 60)
    return ((P[(f * 12 + k) * 2] - P[(j * 12 + k) * 2]) / frames, (P[(f * 12 + k) * 2 + 1] - P[(j * 12 + k) * 2 + 1]) / frames)


_CACHE = {}  # every input of a shot's play-out -> its xg (the live broadcast re-analyses the game every few seconds)


def add_expected_goals(m):
    """Each shot and one-timer of a Genesis match gets `xg`, the chance it goes in by the game's rules (see above)."""
    if m.get('system', 'genesis') != 'genesis' or not m.get('work'):
        return
    rows = {}
    for r in m['work']:
        rows.setdefault(r[1], []).append(r)
    role, roster, P = m['role'], m['roster'], m['pos']
    for sh in m.get('shotList', []):
        if sh['kind'] not in ('shot', 'one-timer') or sh['team'] not in (0, 1):
            continue
        f, team = sh['f'], sh['team']
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
            if anim in PAD_STACK:
                reach, shift = 18, PAD_STACK[anim]
            goalie = Goalie(gx, gy, vgx * 4096, vgy * 4096, *gw[:4])
            coming = (gx + 8 * vgx, gy + 8 * vgy)   # shotdiradj looks half his velocity's high byte ahead
        if sh['kind'] == 'one-timer' or not sh.get('human'):
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
               (gx, gy, vgx, vgy, *gw[:4]) if goalie else None)
        if key in _CACHE:
            sh['xg'] = _CACHE[key]
            continue
        rng = random.Random(f"{m.get('name', '')}:{f}:{team}:{sh['idx']}")
        goals = sum(play_out((px, py, pz), (tx, gl, tz), pp, sha, perfect, goalie, reach, shift, rng) == 'goal'
                    for _ in range(N_SAMPLES))
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


if __name__ == "__main__":
    # python tools/xg.py matches/a.js matches/b.js ...: the goalie states for the viewer's XG_GOALIE_STATES
    import json
    import sys
    games = []
    for path in sys.argv[1:]:
        text = open(path, encoding="utf-8").read()
        games.append(json.loads(text[text.index("{"):text.rindex("}") + 1]))
    print(json.dumps(goalie_states(games), separators=(",", ":")))
