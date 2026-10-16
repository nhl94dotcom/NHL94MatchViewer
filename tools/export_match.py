"""Converts a RAM capture (from the helper, nhl94_record.ps1 or nhl94_record_full.ps1) into a match file that
viewer.html can play. Which system the game ran on (capture.json's "system", Genesis if absent) decides how the
recording is read (tools/systems/); the analysis here (shots, passes, turnovers, goals ...) is the same for all."""
import argparse
import bisect
import gzip
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import systems  # noqa: E402
from systems.common import ROOT, STAT_FIELDS  # noqa: E402


class Capture:
    """Samples of work RAM: an 8-byte millisecond stamp, then one or more blocks of RAM in host byte order."""

    def __init__(self, folder, system=None):
        self.system = system or systems.of_capture(folder)
        full_size = 8 + self.system.RAM_SIZE  # one full.bin snapshot
        self.swap = self.system.BYTE_SWAP
        if (folder / "ram.bin").exists():
            self.data, self.blocks = (folder / "ram.bin").read_bytes(), [[0, self.system.RAM_SIZE]]
        else:
            # The helper writes the same samples gzipped (fast.bin.gz, full.bin.gz).
            fast = folder / "fast.bin"
            self.data = fast.read_bytes() if fast.exists() else gzip.decompress((folder / "fast.bin.gz").read_bytes())
            layout = folder / "capture.json"
            self.blocks = json.loads(layout.read_text())["blocks"] if layout.exists() else self.system.OLD_BLOCKS
        self.sample = 8 + sum(length for _, length in self.blocks)
        self.count = len(self.data) // self.sample
        # The recorder also keeps all of RAM now and then (full.bin), for addresses fast.bin does not hold.
        full, packed = folder / "full.bin", folder / "full.bin.gz"
        if (folder / "ram.bin").exists():
            self.full = b""
        else:
            self.full = full.read_bytes() if full.exists() else gzip.decompress(packed.read_bytes()) if packed.exists() else b""
        self.full_size = full_size
        self.full_ms = [struct.unpack_from("<q", self.full, j * full_size)[0] for j in range(len(self.full) // full_size)]

    def offset(self, addr):
        """Position of an address within a sample, or None when the capture does not cover it."""
        pos = 8
        for start, length in self.blocks:
            if start <= addr < start + length:
                return pos + addr - start
            pos += length
        return None

    def ms(self, i):
        return struct.unpack_from("<q", self.data, i * self.sample)[0]

    def _full_at(self, i):
        """Start of the latest full snapshot taken at or before sample i (the first one if none)."""
        j = max(0, bisect.bisect_right(self.full_ms, self.ms(i)) - 1)
        return j * self.full_size + 8

    def byte(self, i, addr):  # the Genesis core keeps the two bytes of each word swapped (system.BYTE_SWAP)
        off = self.offset(addr ^ self.swap)
        return self.data[i * self.sample + off] if off is not None else self.full[self._full_at(i) + (addr ^ self.swap)]

    def word(self, i, addr):
        off = self.offset(addr)
        if off is None:
            return struct.unpack_from("<H", self.full, self._full_at(i) + addr)[0]
        return struct.unpack_from("<H", self.data, i * self.sample + off)[0]

    def fixed(self, i, addr):  # a position, in the system's format
        return self.system.fixed(self.data, i * self.sample + self.offset(addr))

    def raw(self, i, addr, length):
        start = i * self.sample + self.offset(addr)
        return self.data[start:start + length]


def actions(m):
    """The animation words of each action (shoot, pass, ...) for the system this match was played on."""
    return systems.of_match(m).ACTIONS


FLICKER_MS = 250  # a stat value that changes and changes back within this was not a real change


def steady_stats(m):
    """Smooth out flickers in the stat snapshots: a value that changes and is back where it was at the next snapshot,
    less than FLICKER_MS later. The SNES shots-on-goal word did 2 -> 3 -> 2 -> 3 in 80 ms twice in 2026-10-16_1528_TOR-CHI (the
    game updating it in steps, or a read in the middle), which counted one shot twice."""
    st, t = m["stats"], m["t"]
    f, n, per = st["f"], st["n"], st.get("p", 0)
    # Only counts: the team's (not its attack-zone time) and each player's goals, assists, shots and the two check
    # bytes. Ice time, energy and the penalty word (bench / ice / out, seconds left) really do change back and forth.
    counts = [i for i in range(n) if STAT_FIELDS[i] != "attackZone"]
    for side in ("home", "away"):
        rows = st[side]
        if not rows:
            continue
        fields = counts + [n + per * k + i for k in range((len(rows[0]) - n) // per if per else 0) for i in range(5)]
        for j in range(1, len(rows) - 1):
            if t[f[j + 1]] - t[f[j]] > FLICKER_MS:  # how long the new value lasted
                continue
            a, b, c = rows[j - 1], rows[j], rows[j + 1]
            for i in fields:
                if a[i] == c[i] != b[i]:
                    b[i] = a[i]
    # The same for the per-sample score and shots-on-goal words (the shot finder counts their rises).
    for key in ("score", "shots"):
        v = m.get(key)
        if not v:
            continue
        for team in (0, 1):
            i = 1
            while i < len(t):
                if v[2 * i + team] == v[2 * i - 2 + team]:
                    i += 1; continue
                j = i + 1
                while j < len(t) and v[2 * j + team] == v[2 * i + team]:
                    j += 1
                if j < len(t) and v[2 * j + team] == v[2 * i - 2 + team] and t[j] - t[i] < FLICKER_MS:
                    for q in range(i, j):
                        v[2 * q + team] = v[2 * i - 2 + team]
                i = j


def find_shots(m, goals=None):
    """Every shot, with where it was taken from and how it ended, for the viewer's shot map. The game keeps only
    totals, so shots are found from the animations:
    - shots ($07FC, $092E): the release is the moment the shooter loses the puck, or for a one-timer (he never has
      it) the moment a loose puck beside him changes course hard;
    - pass shots: a pass ($0718, $078A, the B button) used as a shot. With no obvious target the puck goes off
      quickly the way the player pressed, and community players use it to shoot. Counted when it is released at least
      20 units in front of the goal line, its line crosses that goal line within PASS_MOUTH of the middle of the net
      the other team defends, and it reaches the goal mouth or that goalie before a teammate takes or one-times it.
    Then what the game counted is credited in time order, each to the latest shot not yet used: a goal (which always
    also raises shots on goal), a shot on goal ('save'), a post (also counted as a shot on goal by the game). Each
    counted shot goes to the player the game credited (the scorer it named, or whose shots-on-goal count it raised):
    his shot, else a deflection or one-timer beside him, else kind 'other' where the puck last changed course.
    `counted` says whether the game counted the shot on goal: in all captures the counted shots equal the game's
    shots on goal and the goals equal the score, for both teams. The game does not count a pass shot unless it
    scores, and not every other stopped shot either: a shot the goalie stopped that the game did not count reads
    'save' with counted false. The rest are 'blocked' (an opposing
    skater got the puck, or it changed course beside one, before the goal line) or 'wide'.
    Returns [{f, team, idx (roster index, -1 unknown), x, y, speed, kind, result, counted}], kind being shot,
    one-timer, pass shot, deflection or other."""
    t, P, V, own, A = m['t'], m['puck'], m['puckV'], m['owner'], m['anim']
    N, K = len(t), 12
    act = actions(m)
    SHOOT, PASS = act['shoot'], act['pass']  # the shooting animations, the passing ones
    # Game units either side of the middle of the net (the posts are at about 20). Pass shots are aimed by direction
    # only, so near misses count: the user's wide attempts in capture6_netplay_bos_stl crossed at 30.2 and 35.
    PASS_MOUTH = 40
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    pos = lambda i, k: (m['pos'][(i * K + k) * 2], m['pos'][(i * K + k) * 2 + 1])
    vel = lambda i: (V[2 * i] * 100, V[2 * i + 1] * 100)
    kick = lambda i: math.hypot(vel(i)[0] - vel(i - 1)[0], vel(i)[1] - vel(i - 1)[1])
    near = lambda i, k, d: math.hypot(P[3 * i] - pos(i, k)[0], P[3 * i + 1] - pos(i, k)[1]) < d
    roster_idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    role = lambda i, k: m['role'][i * K + k] if 'role' in m else 'x'
    shots, posts = [], m.get('posts', [])
    reached = {}  # release frame of a pass -> the frame it was found to be a pass shot (it got to the net or the goalie)

    def shot(i, k, team, kind, held=0):
        # held: how long the shooting animation ran before the release, ms (a slapshot is wound up for 800 or more)
        sh = {'f': i, 'k': k, 'team': team, 'idx': roster_idx(i, k) if k >= 0 else -1, 'x': P[3 * i - 3], 'y': P[3 * i - 2],
              'speed': round(max(math.hypot(*vel(q)) for q in range(i, min(N, i + 10)))), 'kind': kind, 'result': 'miss'}
        sh['type'] = ('slapshot' if held >= 800 else 'wrist shot') if kind == 'shot' else kind
        return sh

    def at_their_net(i, team):
        # Is the loose puck at frame i heading for the net the other team defends, and does it get there untouched by
        # a teammate? Returns the goal-line Y it is heading for, or None.
        vx, vy = vel(min(N - 1, i + 1))
        if not vy:
            return None
        goal = 268 if vy > 0 else -268
        x, y = P[3 * i], P[3 * i + 1]
        if (goal - y) / vy <= 0 or abs(goal - y) < 20 or abs(x + vx * (goal - y) / vy) > PASS_MOUTH:
            return None  # going away from that net, released on its goal line, or not aimed at it
        others = range(6, 12) if team == 0 else range(6)
        keeper = next((k for k in others if role(i, k) == '0'), None)
        if keeper is not None and (pos(i, keeper)[1] > 0) != (goal > 0):
            return None  # that is his own team's net
        # And it has to get there: to the goal mouth (within PASS_MOUTH at the goal line) or into the goalie's
        # hands, with no teammate taking it or one-timing it first.
        mates = [k for k in (range(6) if team == 0 else range(6, 12))]
        q = i + 1
        while q < N and t[q] - t[i] < 2000:
            if abs(P[3 * q + 1]) >= 250 and abs(P[3 * q]) <= PASS_MOUTH:
                # At the goal mouth. Wide of the posts (about 20 from the middle) and then taken by a teammate within
                # 1 s, before the goalie or the other team: a pass round the net, not a shot (Andreychuk to Gill in
                # snes_2026-10-15_1755, P2, which the user knew as a pass: 36 wide, Gill had it behind the net).
                if abs(P[3 * q]) > 22:
                    r = q
                    while r < N and t[r] - t[q] < 1000 and own[r] < 0 and P[3 * r + 2] > -100:
                        r += 1
                    if r < N and t[r] - t[q] < 1000 and own[r] in mates:
                        return None
                reached[i] = q
                return goal
            if own[q] >= 0:
                reached[i] = q
                return goal if own[q] in others and role(q, own[q]) == '0' else None  # the goalie's, or a pass
            if kick(q) > 5000 and any(near(q, k, 25) for k in mates):
                return None  # a teammate one-timed or redirected it: his shot, not this one
            q += 1
        return None

    for k in range(K):
        team = 0 if k < 6 else 1
        i = 0
        while i < N:
            a = anim(i, k)
            if a not in SHOOT and a not in PASS:
                i += 1; continue
            s0, kind = i, 'shot' if a in SHOOT else 'pass'
            while i < N and anim(i, k) in (SHOOT if kind == 'shot' else PASS):
                i += 1
            e = i
            rel, j = None, max(1, s0)
            while j < N and t[j] <= t[e - 1] + 300:
                if own[j] < 0 and own[j - 1] == k:
                    rel = j; break
                if kind == 'shot' and own[j] < 0 and own[j - 1] < 0 and not any(abs(j - p) <= 2 for p in posts):  # not a bounce off a post
                    if near(j, k, 25) and kick(j) > 5000:
                        rel = j; break
                j += 1
            if rel is None:
                continue
            if kind == 'pass':
                if own[rel - 1] == k and at_their_net(rel, team) is not None:
                    shots.append(shot(rel, k, team, 'pass shot'))
                    shots[-1]['known'] = reached[rel]  # until then it was just a pass
            else:
                shots.append(shot(rel, k, team, 'one-timer' if own[j - 1] != k else 'shot', t[min(N - 1, e)] - t[s0]))
    # A shooting animation can run in two pieces that find the same release (Oates in capture6_netplay_bos_stl, P1
    # 1:17): one shot per player and release.
    seen = set()
    shots = [sh for sh in shots if (sh['f'], sh['k']) not in seen and not seen.add((sh['f'], sh['k']))]
    shots.sort(key=lambda d: d['f'])
    score = lambda i, team: m['score'][2 * i + team]
    sog = lambda i, team: m['shots'][2 * i + team]

    def latest(team, g, window, free, idx=None):
        best = None
        for sh in shots:
            if (sh['team'] == team and sh['f'] <= g and t[g] - t[sh['f']] <= window and (not free or sh['result'] == 'miss')
                    and (idx is None or sh['idx'] == idx)):
                best = sh
        return best

    def add(sh):
        shots.append(sh); shots.sort(key=lambda d: d['f'])
        return sh

    def shooter_at(team, g):
        # Whose shots-on-goal count the game raised around frame g (its per-player shots, stat block +$E8).
        st = m.get('stats')
        if not st or not st.get('f') or st.get('p', 0) < 3:
            return None
        side, n, per = st['home' if team == 0 else 'away'], st['n'], st['p']
        before = max([i for i, f in enumerate(st['f']) if t[f] < t[g] - 300] or [0])
        after = max([i for i, f in enumerate(st['f']) if t[f] <= t[g] + 2000] or [0])
        rose = [idx for idx in range((len(side[0]) - n) // per) if side[after][n + per * idx + 2] > side[before][n + per * idx + 2]]
        return rose[0] if len(rose) == 1 else None

    def credited_before(team, g, idx=None):
        # The frame of the team's (or the player's) last shot already credited with a result before g: a goal the
        # game counts later is never the same shot again (a rebound scored 2 s after a saved one-timer, in
        # capture3_bos_la P2, was credited to the saved one-timer a second time).
        return max((sh['f'] for sh in shots if sh['team'] == team and sh['result'] != 'miss' and sh['f'] < g
                    and (idx is None or sh['idx'] == idx)), default=-1)

    def scorer_touch(team, g, idx):
        # A shot by a player with no shot of his found: the last moment the puck changed course beside him, after
        # his last shot that was already credited.
        floor = credited_before(team, g, idx)
        for i in range(g, 0, -1):
            if t[g] - t[i] > 2000 or i <= floor + 2:
                break
            for k in (range(6) if team == 0 else range(6, 12)):
                if roster_idx(i, k) == idx and near(i, k, 30) and (kick(i) > 3000 or own[i - 1] == k):
                    found = shot(i, k, team, 'one-timer' if anim(i, k) in SHOOT else 'deflection')
                    found['known'] = g  # found only when the game counted it
                    return add(found)
        return None

    def origin(team, g, idx=-1):
        # a counted shot with no shot found (a scramble): where the puck last changed course (after the team's last
        # credited shot)
        i, floor = g, credited_before(team, g)
        while i > max(1, floor + 3) and t[g] - t[i] < 1500:
            if kick(i) > 5000 or own[i - 1] >= 0:
                break
            i -= 1
        sh = shot(i, own[i - 1] if own[i - 1] >= 0 else -1, team, 'other')
        sh['known'] = g  # found only when the game counted it
        if idx >= 0:
            sh['idx'] = idx
        return add(sh)

    def scorer_at(team, g):
        best = None
        for gl in goals or []:
            if gl['team'] == team and abs(t[gl['f']] - t[g]) <= 2500 and gl['scorer'] is not None:
                if best is None or abs(t[gl['f']] - t[g]) < abs(t[best['f']] - t[g]):
                    best = gl
        return best['scorer'] if best else None

    # Credit what the game counted, in time order, each to the latest shot not used yet. A goal also raises the
    # shots-on-goal count (within a moment either side); that rise belongs to the goal.
    events, uncounted = [], set()
    for team in (0, 1):
        sogs = [g for g in range(1, N) if sog(g, team) > sog(g - 1, team)]
        goal_frames = [g for g in range(1, N) if score(g, team) > score(g - 1, team)]
        for g in goal_frames:
            close = [s for s in sogs if abs(t[s] - t[g]) <= 1500]
            if close:
                sogs.remove(min(close, key=lambda s: abs(t[s] - t[g])))
            else:
                uncounted.add(g)  # a goal the game did not count as a shot on goal (the SNES penalty-shot goal)
            events.append((g, 'goal', team))
        events += [(s, 'save', team) for s in sogs]
    for g, result, team in sorted(events):
        # Whose it was: the scorer the game named, or whose shots-on-goal count it raised.
        idx = scorer_at(team, g) if result == 'goal' else None
        if idx is None:
            idx = shooter_at(team, g)
        window = 4000 if result == 'goal' else 3500
        if idx is not None:
            sh = latest(team, g, window, True, idx) or scorer_touch(team, g, idx) or origin(team, g, idx)
        else:
            sh = latest(team, g, window, True) or origin(team, g)
        sh['result'], sh['counted'], sh['resolved'] = result, g not in uncounted, g
    for p in posts:
        for team in (0, 1):
            sh = latest(team, min(N - 1, p + 3), 2000, False)  # point-blank: the post can register a sample before the release
            # the game counts a shot off the post as a shot on goal, so it may already read 'save'
            if sh and sh['result'] in ('miss', 'save') and (P[3 * p + 1] > 0) == (sh['y'] > 0):  # shot from that end
                sh['result'], sh['resolved'] = 'post', max(p, sh.get('resolved', p))
    # A shot the game did not count is judged from the play: saved if the other goalie got the puck, or it changed
    # course beside him, before anyone else touched it. The game does not count every stopped shot: pass shots never
    # unless they score (Fedorov's in capture2_away and Roenick's in capture5_league30 were stopped and left the count
    # alone), and in capture6_netplay_bos_stl five ordinary shots aimed inside the posts and caught by the goalie,
    # Neely's 23000 one from the right circle among them, were not counted either. Those read 'save', counted false.
    for sh in shots:
        if sh.get('counted') or sh['result'] != 'miss':
            continue
        others = range(6, 12) if sh['team'] == 0 else range(6)
        q = sh['f'] + 1
        while q < N and t[q] - t[sh['f']] < 2500:
            keeper = [k for k in others if role(q, k) == '0']
            if own[q] >= 0:
                if own[q] in keeper:
                    sh['result'], sh['resolved'] = 'save', q
                break
            if kick(q) > 3000 and any(near(q, k, 25) for k in keeper):
                sh['result'], sh['resolved'] = 'save', q
                break
            q += 1
    # The misses, split: 'blocked' when an opposing skater (not the goalie) gets the puck, or it changes course beside
    # one, before it reaches the goal line; otherwise 'wide'.
    for sh in shots:
        if sh['result'] != 'miss':
            continue
        others = range(6, 12) if sh['team'] == 0 else range(6)
        skaters = lambda q: [k for k in others if role(q, k) not in ('0', 'x')]
        sh['result'] = 'wide'
        q = sh['f'] + 1
        while q < N and t[q] - t[sh['f']] < 2000 and abs(P[3 * q + 1]) < 268:
            if own[q] >= 0:
                if own[q] in skaters(q):
                    sh['result'] = 'blocked'
                break
            if kick(q) > 3000 and any(near(q, k, 20) for k in skaters(q)):
                sh['result'] = 'blocked'
                break
            q += 1
        sh['resolved'] = min(q, N - 1)
    # For the goalie report: which goalie faced it (roster index), what happened after a save (the goalie held it or
    # play stopped; a rebound the shooters got first; cleared by his team's skaters; still loose after 3 s), and
    # whether it was itself a rebound (the same team's previous shot was saved and they got the puck back within 3 s).
    previous = {}
    for sh in shots:
        team, f = sh['team'], sh['f']
        others = range(6, 12) if team == 0 else range(6)
        keeper = next((k for k in others if role(f, k) == '0'), None)
        sh['goalie'] = roster_idx(f, keeper) if keeper is not None else -1
        # Who was working that goalie at the release: 'human' if he carried the controlled-player marker (+$62 bit $08),
        # else 'cpu'. Taking the goalie is a B press (with the puck loose or the other team's); control also moves to a
        # goalie by itself when he gets the puck, so a CPU save often ends with the human holding him, which is why
        # the release is the moment that decides. In the seven recordings about five shots were grabbed in flight.
        sh['gctl'] = 'human' if keeper is not None and (m['ctrl'][f] >> keeper) & 1 else 'cpu'
        # The goalie's save move: his first save animation from the release until a quarter second after the result
        # was settled (glove, stick, pad stack, high, dive, slam), or 'none' when he made none (stood his ground).
        # In the seven recordings, of 115 saves: stick 62, high 14, pad stack 12, dive 5, glove 2, none 20.
        moves = getattr(systems.of_match(m), 'SAVE_MOVES', {})
        if moves and keeper is not None and sh['result'] in ('save', 'goal', 'post'):
            sh['save'], q, until = 'none', f, t[min(N - 1, sh.get('resolved', f))] + 250
            while q < N and t[q] <= until:
                a = m['anim'][(q * K + keeper) * 4:(q * K + keeper) * 4 + 4]
                if a in moves:
                    sh['save'] = moves[a]
                    break
                q += 1
        if sh['result'] == 'save':
            after, q = 'loose', f + 1
            while q < N and t[q] - t[f] < 3000:
                if P[3 * q + 2] < -100:
                    after = 'held'; break
                if own[q] >= 0:
                    after = 'held' if own[q] == keeper else 'cleared' if own[q] in others else 'rebound'
                    break
                q += 1
            sh['after'] = after
        last = previous.get(team)
        sh['rebound'] = bool(last and last.get('after') == 'rebound' and t[f] - t[last['f']] <= 3000)
        previous[team] = sh
    # For a live view: `known`, the frame the attempt could first be known (the release; for a pass shot the moment
    # it reached the net or the goalie; for one found from a counted event, that event), and `resolved`, the frame
    # its result could first be known (the game's count, the post, the goalie's stop, the block, the goal line).
    keys = ('f', 'team', 'idx', 'x', 'y', 'speed', 'kind', 'type', 'result', 'goalie', 'gctl', 'rebound')
    return [{**{key: sh[key] for key in keys}, 'counted': bool(sh.get('counted')),
             'known': sh.get('known', sh['f']), 'resolved': max(sh.get('resolved', sh['f']), sh.get('known', sh['f'])),
             **({'after': sh['after']} if 'after' in sh else {}), **({'save': sh['save']} if 'save' in sh else {})} for sh in shots]


def find_failed_one_timers(m):
    """One-timers that never connected: a player went into a shooting animation ($07FC/$092E) without the puck, just
    after a teammate's pass (within 1.5 s; C pressed while the pass was on its way), and no shot of his came of it
    (no release in the shot list within the animation and 0.3 s after) because the puck never got close enough.
    The game's own one-timers-tried count (+$35C) only includes ones that connected: 6 and 7 in
    capture6_netplay_bos_stl, against 6 and 8 connected here and 11 and 1 that failed.
    Returns [{f (start of the swing), team, idx (roster index), passer (roster index), x, y (where he was)}]."""
    t, own, A = m['t'], m['owner'], m['anim']
    N, K = len(t), 12
    act = actions(m)
    SHOOT, PASS = act['shoot'], act['pass'] | act['goalie_pass']
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    shots = m.get('shotList', [])
    out = []
    for k in range(K):
        team, i = (0 if k < 6 else 1), 0
        while i < N:
            if anim(i, k) not in SHOOT:
                i += 1; continue
            s0 = i
            while i < N and anim(i, k) in SHOOT:
                i += 1
            end = t[i - 1] + 300
            if own[s0] == k or own[max(0, s0 - 1)] == k:
                continue  # he had the puck: an ordinary shot
            me = idx(s0, k)
            if any(sh['team'] == team and sh['idx'] == me and t[s0] - 100 <= t[sh['f']] <= end for sh in shots):
                continue  # it connected
            passer = None
            for q in range(s0, -1, -1):
                if t[s0] - t[q] > 1500:
                    break
                mate = next((kk for kk in range(team * 6, team * 6 + 6) if kk != k and anim(q, kk) in PASS), None)
                if mate is not None:
                    passer = idx(q, mate); break
            if passer is None:
                continue
            x, y = m['pos'][(s0 * K + k) * 2], m['pos'][(s0 * K + k) * 2 + 1]
            known = next((q for q in range(i - 1, N) if t[q] >= end), N - 1)  # the swing over, nothing hit
            out.append({'f': s0, 'team': team, 'idx': me, 'passer': passer, 'x': x, 'y': y, 'known': known})
    return sorted(out, key=lambda e: e['f'])


def whistles(m):
    """Stretches when the game hides the puck (a whistle until the next faceoff): [(first hidden frame, faceoff frame)]."""
    P, N = m['puck'], len(m['t'])
    out, i = [], 1
    while i < N:
        if P[3 * i + 2] < -100 and P[3 * i - 1] > -100:
            j = i
            while j < N and P[3 * j + 2] < -100:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def own_end(m, i, team):
    """+1 if the team's goalie is at the +Y end at frame i, -1 if at -Y, None if no goalie is on."""
    for k in range(team * 6, team * 6 + 6):
        if m['role'][i * 12 + k] == '0':
            return 1 if m['pos'][(i * 12 + k) * 2 + 1] > 0 else -1
    return None


def find_faceoffs(m):
    """Every faceoff: where the puck was dropped, who won it (the team whose faceoff count, team stat +$0E, went up
    within 3 s) and in which zone, for Home (Away's is the mirror: Home's attacking zone is Away's defensive one).
    Zones by the dot: |Y| under 100 is neutral (centre and the four neutral dots); otherwise the end the team
    defends (its goalie's end) is its defensive zone.
    Returns [{f (the drop), x, y, won (0 Home, 1 Away, -1 unknown), zone (Home's view: att, neu, def)}]."""
    t, P, N = m['t'], m['puck'], len(m['t'])
    stats = m.get('stats') or {}
    at = STAT_FIELDS.index('faceoffs')  # faceoffs won, in each stat snapshot
    out = []
    starts = [(a, b) for a, b in whistles(m) if b < N]
    if N and P[2] < -100:  # the recording starts with the puck hidden: the opening faceoff
        first = next((i for i in range(N) if P[3 * i + 2] > -100), None)
        if first is not None and first not in [b for a, b in starts]:
            starts.insert(0, (0, first))
    for a, b in starts:
        x, y = P[3 * b], P[3 * b + 1]
        home_end = own_end(m, b, 0)
        if abs(y) < 100:
            zone = 'neu'
        elif home_end is None:
            zone = None
        else:
            zone = 'def' if (y > 0) == (home_end > 0) else 'att'
        won = -1
        if stats.get('f'):
            before = max([i for i, f in enumerate(stats['f']) if f <= a] or [0])  # from the whistle: the win can count at the drop
            after = max([i for i, f in enumerate(stats['f']) if t[f] <= t[b] + 6000] or [0])
            for team, side in ((0, 'home'), (1, 'away')):
                if stats[side][after][at] > stats[side][before][at]:
                    won = team
        out.append({'f': b, 'x': round(x), 'y': round(y), 'won': won, 'zone': zone})
    return out


def find_icings(m):
    """Icings. NHL '94 calls touch-up icing: a team releases the puck on its own side of the red line, it crosses the
    other team's goal line untouched, and the whistle goes when a defending player touches it (or, if nobody does,
    when play is stopped); the faceoff then comes back to the icing team's defensive zone. The game keeps no trace of
    which whistle message it showed (the ROM has an "Icing" message, rule 6 in the table at $18E0C), so it is worked
    out from the play. Confirmed on the user's two in 2026-10-14_1540_CGY-BOS (Juneau at 1:43 and Sweeney at 1:18 of
    the 2nd; Calgary touched both behind its goal line, whistles at 1:38 and 1:09).
    Returns [{f (the whistle), team (who iced it), idx (roster index of the player), x, y (where it was released)}]."""
    t, P, own, N = m['t'], m['puck'], m['owner'], len(m['t'])
    out = []
    for a, b in whistles(m):
        if b >= N or m['score'][2 * min(N - 1, b + 60):2 * min(N - 1, b + 60) + 2] != m['score'][2 * (a - 1):2 * a]:
            continue  # a goal
        # Work back from the whistle: the last possession, and if it was a defender's touch behind his goal line,
        # the release before it.
        q = a - 1
        while q > 0 and own[q] < 0:
            q -= 1
        if own[q] < 0:
            continue
        last = 0 if own[q] < 6 else 1
        start = q
        while start > 0 and own[start - 1] == own[q]:
            start -= 1
        r = start - 1
        while r > 0 and own[r] < 0:
            r -= 1
        candidates = [(q, a)]  # the last team iced it and nobody touched it
        if r > 0 and own[r] >= 0 and (0 if own[r] < 6 else 1) != last:
            candidates.append((r, start))  # the other team iced it and the last team touched it up
        for rel, until in candidates:
            team = 0 if own[rel] < 6 else 1
            end = own_end(m, rel, team)
            if end is None:
                continue
            x, y = P[3 * (rel + 1)], P[3 * (rel + 1) + 1]
            crossed = any(P[3 * i + 1] * -end >= 268 for i in range(rel + 1, until + 1))
            back = P[3 * b + 1] * end > 150
            if y * end > 0 and crossed and back:
                out.append({'f': a, 'team': team, 'idx': int(m['roster'][rel * 12 + own[rel]], 36), 'x': round(x), 'y': round(y)})
                break
    return out


def find_passes(m):
    """Every pass, for each player: the pass animations ($0718, $078A; a goalie's $0366) whose player loses the puck,
    and what came of it, from where it was released to where it ended:
    - 'completed': a teammate got it (receiver given);
    - 'one-timer': a teammate one-timed it (a one-timer in the shot list), also completed;
    - 'intercepted': the other team got it (its skater or its goalie);
    - 'failed': nobody did before a whistle or 3 s, or the passer got it back himself;
    - 'pass shot': it was a pass shot (see find_shots).
    The game's own counts are team totals of passes tried and completed (+$12, +$14) and do not count a one-timer as
    completed. `known` is when the outcome could first be known (for live knowledge).
    Returns [{f, known, team, idx, to, x0, y0, x1, y1, result}] (idx / to: roster indices, -1 unknown)."""
    t, P, own, A = m['t'], m['puck'], m['owner'], m['anim']
    N, K = len(t), 12
    act = actions(m)
    PASS = act['pass'] | act['goalie_pass']
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    shots = m.get('shotList', [])
    out = []
    for k in range(K):
        team, i = (0 if k < 6 else 1), 0
        mates = range(team * 6, team * 6 + 6)
        while i < N:
            if anim(i, k) not in PASS:
                i += 1; continue
            s0 = i
            while i < N and anim(i, k) in PASS:
                i += 1
            rel, j = None, max(1, s0)
            while j < N and t[j] <= t[i - 1] + 300:  # the puck leaves his stick during the animation or just after
                if own[j] < 0 and own[j - 1] == k:
                    rel = j; break
                j += 1
            if rel is None:
                continue
            me = idx(rel, k)
            p = {'f': rel, 'team': team, 'idx': me, 'to': -1, 'x0': round(P[3 * rel - 3]), 'y0': round(P[3 * rel - 2])}
            shot = next((sh for sh in shots if sh['team'] == team and sh['kind'] == 'pass shot' and sh['idx'] == me and abs(sh['f'] - rel) <= 2), None)
            q, result = rel, 'failed'
            while q < N and t[q] - t[rel] < 3000:
                if P[3 * q + 2] < -100:
                    break  # a whistle
                one = next((sh for sh in shots if sh['team'] == team and sh['kind'] == 'one-timer' and sh['f'] == q and sh['idx'] != me), None)
                if one:
                    result, p['to'] = 'one-timer', one['idx']; break
                if own[q] >= 0:
                    if own[q] == k:
                        result = 'failed'
                    elif own[q] in mates:
                        result, p['to'] = 'completed', idx(q, own[q])
                    else:
                        result = 'intercepted'
                    break
                q += 1
            q = min(q, N - 1)
            if shot:
                result, q = 'pass shot', shot.get('resolved', shot['f'])
            p.update({'x1': round(P[3 * q]), 'y1': round(P[3 * q + 1]), 'result': result, 'known': q})
            out.append(p)
    # A passing animation in two pieces finds the same release twice (2026-10-16_1540_CHI-TOR P1 0:42): one pass per
    # player and release.
    seen = set()
    out = [p for p in out if (p['f'], p['team'], p['idx']) not in seen and not seen.add((p['f'], p['team'], p['idx']))]
    # Did the game count it (its passes-tried count, team stat +$12, going up within 1.5 s)? It counts only passes
    # aimed at a receiver: in 2026-10-14_1540_CGY-BOS 20 of the user's 62 passes were B presses with no target (the
    # puck went the way he pushed, as with a pass shot), and goalie passes ($0366) are never counted.
    stats = m.get('stats') or {}
    tried = STAT_FIELDS.index('passTried')
    for team, side in ((0, 'home'), (1, 'away')):
        if not stats.get('f'):
            break
        rises = [t[stats['f'][i]] for i in range(1, len(stats['f'])) if stats[side][i][tried] > stats[side][i - 1][tried]]
        for p in out:
            if p['team'] == team:
                hit = next((r for r in rises if -300 <= r - t[p['f']] <= 1500), None)
                p['counted'] = hit is not None
                if hit is not None:
                    rises.remove(hit)
    return sorted(out, key=lambda e: e['f'])



def find_hits(m):
    """Every body check that landed: who threw it and who took it. The game counts checks per player, but where
    depends on the ROM: in the original game the byte at +$11C counts the checks a player THREW (its team sums equal
    the team's checks, +$10, and the player is mid-check, $0C5E/$0B96, when it rises) and +$102 his penalty minutes;
    ROMs with smozROM's bodycheck hack count checks thrown at +$102 and hits taken at +$11C. The thrower comes from
    whichever byte counts checks thrown; whom he hit is the nearest opponent going down ($0DD8/$0D26) within 0.8 s,
    else the nearest opponent on the ice. On capture5_league30 (hack ROM, which records both) that gives every one of
    the 23 hits to the player the game says took it.
    Returns [{f (when the game counted it), team (the thrower's), by, on (roster indices), x, y (where)}]."""
    st = m.get('stats') or {}
    if not st.get('f'):
        return []
    t, pos, role, roster, A, N = m['t'], m['pos'], m['role'], m['roster'], m['anim'], len(m['t'])
    F, n, per = st['f'], st['n'], st['p']
    slot = 3 if st.get('x') == 'Checks' else 4
    act = actions(m)
    system = systems.of_match(m)
    check_moves, hit_outcomes = getattr(system, 'CHECK_MOVES', {}), getattr(system, 'HIT_OUTCOMES', {})
    anim = lambda i, k: A[(i * 12 + k) * 4:(i * 12 + k) * 4 + 4]
    at = lambda i, k: (pos[(i * 12 + k) * 2], pos[(i * 12 + k) * 2 + 1])
    dist = lambda i, a, b: math.hypot(at(i, a)[0] - at(i, b)[0], at(i, a)[1] - at(i, b)[1])
    on_ice = lambda i, k: role[i * 12 + k] != 'x' and roster[i * 12 + k] != 'z'
    out = []

    def window(f, ms):
        j0 = f
        while j0 > 0 and t[f] - t[j0 - 1] <= ms:
            j0 -= 1
        j1 = f
        while j1 + 1 < N and t[j1 + 1] - t[f] <= ms:
            j1 += 1
        return range(j0, j1 + 1)

    def record(f, team, k, rise):
        """The hit thrown by record k at frame f: whom it hit, how, and what it did to him."""
        opp = [v for v in range((1 - team) * 6, (1 - team) * 6 + 6) if on_ice(f, v)]
        if not opp:
            return
        # the nearest opponent going down within 0.8 s, else the nearest on the ice
        down = [(dist(j, k, v), v, j) for j in window(f, 800) for v in opp
                if on_ice(j, v) and anim(j, v) in act['down'] and dist(j, k, v) < 40]
        victim = min(down)[1] if down else min((dist(f, k, v), v) for v in opp)[1]
        x, y = at(f, victim)
        # How it was thrown (the thrower's check animation: shoulder, hip, cross-check) and what it did to the
        # player hit (knocked down, upended, into the boards, into the bench), within 0.7 s either side.
        # In the Genesis recordings: shoulder 111, cross-check 14, hip 2, not seen 48.
        how = outcome = None
        for j in window(f, 700):
            how = how or check_moves.get(anim(j, k))
            if outcome in (None, 'knocked down'):
                outcome = hit_outcomes.get(anim(j, victim), outcome)
        for _ in range(rise):
            out.append({'f': f, 'team': team, 'by': int(roster[f * 12 + k], 36), 'on': int(roster[f * 12 + victim], 36),
                        'x': round(x), 'y': round(y), 'how': how or 'check', 'outcome': outcome or 'stayed up'})

    team_checks = STAT_FIELDS.index('checks')
    for s in range(1, len(F)):
        f = F[s]
        for team, side in ((0, 'home'), (1, 'away')):
            a, b = st[side][s - 1], st[side][s]
            mine = [k for k in range(team * 6, team * 6 + 6) if on_ice(f, k)]
            if len(b) <= n or not any(b[n + per * j + slot] for j in range((len(b) - n) // per)) and b[team_checks]:
                # No per-player counts (the SNES so far): the team's checks rose; the thrower is the skater of
                # that team checking (a check or burst animation) nearest an opponent going down, else the one
                # nearest any opponent.
                rise = b[team_checks] - a[team_checks]
                if not 0 < rise <= 3 or not mine:
                    continue
                moves = set(check_moves) | act['lunge']
                opp = [v for v in range((1 - team) * 6, (1 - team) * 6 + 6) if on_ice(f, v)]
                if not opp:
                    continue
                checking = [k for k in mine if role[f * 12 + k] != '0' and any(anim(j, k) in moves for j in window(f, 800))]
                pool = checking or [k for k in mine if role[f * 12 + k] != '0']
                if not pool:
                    continue
                k = min(pool, key=lambda k: min(dist(f, k, v) for v in opp))
                record(f, team, k, rise)
                continue
            for idx in range((len(b) - n) // per):
                rise = b[n + per * idx + slot] - a[n + per * idx + slot]
                if not 0 < rise <= 3:
                    continue
                k = next((k for k in mine if int(roster[f * 12 + k], 36) == idx), None)
                if k is not None:
                    record(f, team, k, rise)
    return sorted(out, key=lambda e: e['f'])


ZONE_LINE = 89  # the blue lines, Y = +/-89: with it the puck's time in each end matches the game's attack-zone time


def find_zone_entries(m):
    """Zone entries: the puck crossing a blue line from the neutral zone into the zone a team attacks, with that team
    the last to touch it (the other team clearing it back into its own zone is not an entry). Each is
      - 'carried': a player of that team has the puck as it crosses;
      - 'passed': it was a targeted pass (find_passes, counted by the game) across the line;
      - 'dumped': anything else: dumped or shot in, chipped past a defender, an untargeted pass.
    A puck that goes on to an icing is left out. The zone (for whether a shot attempt came of it) lasts until the puck
    is back in the neutral zone, a whistle, or the period ends. Crossings need the puck back in the neutral zone
    (|Y| under 83) before the next one, so a puck sitting on the line is not counted again and again.
    Returns [{f (crossing), known, end, team, idx (carrier, passer or dumper), to (receiver, passes), kind, x,
    recovered (dumped: the same team got the puck in the zone before the other did)}]."""
    t, P, own, N = m['t'], m['puck'], m['owner'], len(m['t'])
    roster = m['roster']
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(roster[i * 12 + k], 36))
    hidden = lambda i: P[3 * i + 2] < -100
    passes = m.get('passes', [])
    icings = m.get('icings', [])
    out = []
    state, last, last_f, end = None, -1, -1, None
    for i in range(N):
        e = own_end(m, i, 0)
        end = e if e is not None else end
        if hidden(i) or (i and m['period'][i] != m['period'][i - 1]) or end is None:
            state = None
            if hidden(i):
                last = -1
            continue
        if own[i] >= 0:
            last, last_f = own[i], i
        y = P[3 * i + 1] * -end  # in Home's view: > 0 towards the end Home attacks
        if abs(y) < ZONE_LINE - 6:
            state = 'neu'
            continue
        if abs(y) < ZONE_LINE or state != 'neu':
            if abs(y) >= ZONE_LINE:
                state = 'zone'
            continue
        state = 'zone'
        team = 0 if y > 0 else 1  # the team attacking that end
        if last < 0 or (last < 6) != (team == 0):
            continue
        entry = {'f': i, 'team': team, 'idx': idx(last_f, last), 'to': -1, 'x': round(P[3 * i])}
        # where the zone ends: back in the neutral zone, a whistle, or the period's end
        q = i
        while q + 1 < N and not hidden(q + 1) and m['period'][q + 1] == m['period'][i] and abs(P[3 * (q + 1) + 1]) >= ZONE_LINE - 6:
            q += 1
        entry['end'] = q
        mates = range(team * 6, team * 6 + 6)
        if own[i] >= 0 or (i + 1 < N and own[i + 1] == last and own[i - 1] == last):
            entry.update(kind='carried', known=i)
        else:
            nxt = next((j for j in range(i, q + 1) if own[j] >= 0), None)
            if any(ic['team'] == team and last_f < ic['f'] and (nxt is None or nxt >= ic['f']) for ic in icings):
                continue  # an icing, not an entry
            p = next((p for p in passes if p['team'] == team and p['f'] <= i and p['f'] >= last_f - 2 and p.get('counted')), None)
            entry['known'] = nxt if nxt is not None else q
            if p:
                entry.update(kind='passed', to=p['to'] if p['result'] in ('completed', 'one-timer') else -1)
                entry['known'] = max(i, p.get('known', i))
            else:
                entry['kind'] = 'dumped'
                entry['recovered'] = nxt is not None and own[nxt] in mates
        out.append(entry)
    return out


def find_turnovers(m):
    """Changes of possession from one team to the other with no whistle between, and why. Possession is the
    game's own (puck +$60/+$61: who has the puck). A shot losing the puck is not a turnover (blocked, saved or
    wide). Otherwise, if the other team poke-checked ($0B24), hooked ($1122) or body-checked ($0C5E, or the carrier
    went down, $0DD8/$0D26) within half a second of the loss, it is a takeaway for that player; a carrier relieved of
    the puck at once by an opponent on top of him is a takeaway too ('stolen'). Otherwise it is a giveaway by the
    player who lost it: a pass the other team picked off, or the puck simply lost. A pass the goalie collects is a
    dump-in, counted as neither (as the NHL counts them).
    Returns [{f (frame the other team has it), lost (frame it was lost), from (team that lost it), giver, taker, by
    (roster indices; by = who forced it, takeaways only), kind (giveaway, takeaway, dump-in), how, x, y}]."""
    act = actions(m)
    causes = {**{w: 'poke check' for w in act['poke']}, **{w: 'hook' for w in act['hook']}, **{w: 'hit' for w in act['lunge']}}
    t, P, own, A = m['t'], m['puck'], m['owner'], m['anim']
    N, K = len(t), 12
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    pos = lambda i, k: (m['pos'][(i * K + k) * 2], m['pos'][(i * K + k) * 2 + 1])
    dist = lambda i, k: math.hypot(P[3 * i] - pos(i, k)[0], P[3 * i + 1] - pos(i, k)[1])
    team = lambda k: 0 if k < 6 else 1
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    goalie = lambda i, k: m['role'][i * K + k] == '0'
    shots = m.get('shotList', [])
    runs, i = [], 0
    while i < N:
        if own[i] < 0:
            i += 1; continue
        k, s0 = own[i], i
        while i < N and own[i] == k:
            i += 1
        runs.append((k, s0, i - 1))
    out = []
    for (k1, a1, e1), (k2, a2, e2) in zip(runs, runs[1:]):
        if team(k1) == team(k2):
            continue
        lost = e1 + 1
        if m['period'][e1] != m['period'][a2] or any(P[3 * q + 2] < -100 for q in range(e1, a2 + 1)):
            continue  # a whistle between: the faceoff decides it
        if any(sh['team'] == team(k1) and abs(sh['f'] - lost) <= 3 for sh in shots):
            continue  # he shot it
        ev = {'f': a2, 'lost': lost, 'from': team(k1), 'giver': idx(lost, k1), 'taker': idx(a2, k2),
              'x': P[3 * lost], 'y': P[3 * lost + 1]}
        window = [q for q in range(max(0, lost - 40), min(N, lost + 20)) if abs(t[q] - t[lost]) <= 500]
        rivals = range(team(k2) * 6, team(k2) * 6 + 6)
        cause = None
        for q in window:
            for k in rivals:
                a = anim(q, k)
                if a in causes and dist(q, k) < 35:
                    cause = (causes[a], k); break
            if cause:
                break
        if not cause and any(anim(q, k1) in act['down'] for q in window):
            # He went down: the nearest opposing skater (a goalie only if no skater is there) hit him.
            near = sorted((k for k in rivals if m['role'][lost * K + k] != 'x'),
                          key=lambda k: (goalie(lost, k), math.hypot(pos(lost, k)[0] - pos(lost, k1)[0], pos(lost, k)[1] - pos(lost, k1)[1])))
            if near:
                cause = ('hit', near[0])
        passed = any(anim(q, k1) in act['pass'] | act['goalie_pass'] for q in window if q <= lost + 2)
        if cause:
            ev.update(kind='takeaway', how=cause[0], by=idx(lost, cause[1]))
        elif passed and goalie(a2, k2):
            ev.update(kind='dump-in', how='to the goalie')
        elif passed:
            ev.update(kind='giveaway', how='pass picked off')
        elif t[a2] - t[lost] < 150 and dist(a2, k2) < 20:
            ev.update(kind='takeaway', how='stolen', by=idx(a2, k2))
        else:
            ev.update(kind='giveaway', how='lost the puck')
        out.append(ev)
    return out


BOBBLE_KICK = 50    # puck speed change (hundreds) of a pass bouncing off its receiver; a catch slows it the same way,
                    # but he has it a sample later
BOBBLE_NEAR = 22    # ... within this of the receiver


def find_bobbles(m):
    """Bobbled passes: a pass reaches a teammate, close enough to take (the puck within BOBBLE_NEAR of him), and bounces
    off him (its speed changes by BOBBLE_KICK or more) without his having it; the user's community calls it a
    bobble. Not when the receiver played it (a shooting or passing move within 0.4 s: one-timers, which bounce the
    puck the same way), an opponent was as close or got the puck at once (an interception), or the puck was at the
    boards (a pass that missed and came off them). He may get it back afterwards: still a bobble (the user).
    Checked against the user's review of 2026-10-16_1540_CHI-TOR (SNES): the 10 he called bobbles and none of the 11
    others. After find_passes and find_shots.
    The pass itself gets `bobble`: {f, idx, x, y} (the passes map draws it to that spot, then on to its outcome).
    Returns [{f (the bounce), pass (the pass's frame), team, by (passer), idx (receiver; roster indices), x, y,
    next: 'himself' | 'teammate' | 'opponent' | 'none', got (frame someone had it, or None)}]."""
    act = actions(m)
    played = act['shoot'] | act['pass'] | act['goalie_pass']
    t, P, V, own, A = m['t'], m['puck'], m['puckV'], m['owner'], m['anim']
    N, K = len(t), 12
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    pos = lambda i, k: (m['pos'][(i * K + k) * 2], m['pos'][(i * K + k) * 2 + 1])
    to_puck = lambda i, k: math.hypot(P[3 * i] - pos(i, k)[0], P[3 * i + 1] - pos(i, k)[1])
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    hidden = lambda q: P[3 * q + 2] < -100

    def at_boards(q):
        x, y = abs(P[3 * q]), abs(P[3 * q + 1])
        cx, cy = 132 - 46, 303 - 46  # the corners' centres (ice edge X 132, Y 303, corner radius 46)
        return x >= 126 or y >= 297 or (x > cx and y > cy and math.hypot(x - cx, y - cy) >= 40)

    out = []
    for p in m.get('passes', []):
        rel, team = p['f'], p['team']
        # skaters only: a goalie takes a pass his own way (Cullen's back to Potvin in 2026-10-16_1540_CHI-TOR)
        mates = [k for k in range(team * 6, team * 6 + 6) if m['role'][rel * K + k] not in '0x' and idx(rel, k) != p['idx']]
        rivals = [k for k in range(6 * (1 - team), 6 * (1 - team) + 6) if m['role'][rel * K + k] != 'x']
        q, hit = rel + 1, None
        while q < N - 1 and t[q] - t[rel] < 2000 and own[q] < 0 and not hidden(q):
            if math.hypot(V[2 * q + 2] - V[2 * q], V[2 * q + 3] - V[2 * q + 1]) >= BOBBLE_KICK:
                mate = min(((to_puck(q, k), k) for k in mates), default=(999, -1))
                rival = min((to_puck(q, k) for k in rivals), default=999)
                if mate[0] <= BOBBLE_NEAR and rival > mate[0] + 8:
                    hit = (q, mate[1])
                break  # the first thing the pass hit decides it
            q += 1
        if not hit or at_boards(hit[0]):
            continue
        q, k = hit
        if any(anim(z, k) in played for z in range(max(0, q - 40), min(N, q + 40)) if abs(t[z] - t[q]) <= 400):
            continue  # he played it: a one-timer, or passed it on
        r = q + 1
        while r < N and own[r] < 0 and not hidden(r) and t[r] - t[q] < 3000:
            r += 1
        got = r if r < N and own[r] >= 0 else None
        if got is not None and own[got] == k and t[got] - t[q] < 100:
            continue  # caught
        if got is not None and own[got] not in mates and own[got] // 6 != team and t[got] - t[q] < 60:
            continue  # picked off
        nxt = 'none' if got is None else 'himself' if own[got] == k else 'opponent' if own[got] // 6 != team else 'teammate'
        out.append({'f': q, 'pass': rel, 'team': team, 'by': p['idx'], 'idx': idx(q, k), 'x': P[3 * q], 'y': P[3 * q + 1],
                    'next': nxt, 'got': got})
        p['bobble'] = {'f': q, 'idx': idx(q, k), 'x': round(P[3 * q]), 'y': round(P[3 * q + 1])}
    return out


CONTACT = 17.5   # skaters' bodies stop about 16 units apart (opponents spend thousands of samples at 16-17, a handful closer)
BUMP_BEFORE = 500  # ms before the loss in which the bump may come
GOALIE_PUCK = 15   # a puck lost on a goalie comes this close to him (the user's two in 2026-10-16_1314_BOS-PIT: 10 and 12) ...
GOALIE_BODY = 33   # ... with the carrier near him: 17 and 23 then, and 32 for Lemieux in P3 0:12 (the puck out on his stick touched
                   # the goalie; the user judged it the goalie, with Juneau close too)
BUMP_HELD = 150    # ms the carrier must have had it (shorter touches are scrambles)
BUMP_FAST = 70     # puck speed (hundreds) after the loss above which he shot or flipped it (carried pucks go up to about 55;
                   # Taglianeti's flip down the ice in 2026-10-16_1314_BOS-PIT P1 3:54 left at 121)


def find_bumps(m):
    """Pucks knocked loose by body contact, two kinds:
    - 'goalie': a carrier who skates into a goalie, his own or the other team's, loses the puck (the game knocks it
      loose; the user: a known way to lose it): the puck within GOALIE_PUCK of a goalie from 0.15 s before the loss
      to 0.2 s after, the carrier within GOALIE_BODY of him;
    - 'skater': otherwise, an opposing skater up against him (within CONTACT, in the BUMP_BEFORE ms up to the loss)
      with no check landed on him (the hit list); a defender who lunged without the check landing still counts.
    Either way: no poke check or hook by an opponent near the puck, he did not go down, did not shoot or pass (a pass
    animation counts even when the pass list has no pass), the puck did not leave faster than BUMP_FAST (shot or
    flipped), he had it at least BUMP_HELD ms and did not have it back within 0.3 s. After find_shots, find_passes
    and find_hits. The user reviewed 2026-10-16_1314_BOS-PIT's first list: the flip and an intercepted pass were not
    bumps, two were the carrier skating into a goalie (Samuelsson into his own, P3 3:31; Lemieux into Moog, P2 1:45).
    Returns [{f (the loss), kind, team (carrier's), idx (carrier, roster index), by (the opponent he ran into, or the
    goalie), own (goalie kind: his own goalie), x, y, next: 'opponent' | 'teammate' | 'himself' | 'none' (whistle or
    period end first), got (frame the next player had it, or None), human (skater kind: the opponent was a person's
    skater)}]."""
    act = actions(m)
    sticks = act['poke'] | act['hook']
    passing = act['pass'] | act['goalie_pass']
    t, P, own, A = m['t'], m['puck'], m['owner'], m['anim']
    V = m.get('puckV')
    N, K = len(t), 12
    ctrl = m.get('ctrl') or []
    anim = lambda i, k: A[(i * K + k) * 4:(i * K + k) * 4 + 4]
    pos = lambda i, k: (m['pos'][(i * K + k) * 2], m['pos'][(i * K + k) * 2 + 1])
    gap = lambda i, a, b: math.hypot(pos(i, a)[0] - pos(i, b)[0], pos(i, a)[1] - pos(i, b)[1])
    to_puck = lambda i, k: math.hypot(P[3 * i] - pos(i, k)[0], P[3 * i + 1] - pos(i, k)[1])
    team = lambda k: 0 if k < 6 else 1
    idx = lambda i, k: (lambda v: v if v < 35 else -1)(int(m['roster'][i * K + k], 36))
    skater = lambda i, k: m['role'][i * K + k] not in '0x'
    goalie = lambda i, k: m['role'][i * K + k] == '0'
    hidden = lambda q: P[3 * q + 2] < -100
    shots, passes, hits = m.get('shotList', []), m.get('passes', []), m.get('hits', [])
    runs, i = [], 0
    while i < N:
        if own[i] < 0:
            i += 1; continue
        k, s0 = own[i], i
        while i < N and own[i] == k:
            i += 1
        runs.append((k, s0, i - 1))
    out = []
    for j, (k1, a1, e1) in enumerate(runs):
        lost = e1 + 1
        if lost >= N or m['role'][e1 * K + k1] in '0x' or hidden(lost) or m['period'][lost] != m['period'][e1]:
            continue
        if t[lost] - t[a1] < BUMP_HELD:
            continue  # a touch in a scramble
        me, them = team(k1), 1 - team(k1)
        if any(sh['team'] == me and abs(sh['f'] - lost) <= 3 for sh in shots) or \
                any(p['team'] == me and abs(p['f'] - lost) <= 3 for p in passes):
            continue  # he shot or passed it
        if V and max(math.hypot(V[2 * q], V[2 * q + 1]) for q in range(lost, min(N, lost + 4))) > BUMP_FAST:
            continue  # sent away hard: shot or flipped
        window = [q for q in range(max(0, lost - 40), min(N, lost + 20)) if abs(t[q] - t[lost]) <= 500]
        if any(anim(q, k1) in passing for q in window if q <= lost + 2):
            continue  # a pass (picked off at once, say)
        if any(anim(q, k1) in act['down'] for q in window):
            continue  # knocked over: a check (or a fall)
        if any(anim(q, k) in sticks and to_puck(q, k) < 35 for q in window for k in range(them * 6, them * 6 + 6)):
            continue  # a poke check or hook took it
        mine = idx(lost, k1)
        if mine < 0:
            continue
        near = [q for q in window if -150 <= t[q] - t[lost] <= 200]
        on_goalie = [(to_puck(q, g), g) for q in near for g in range(K) if goalie(q, g) and gap(q, k1, g) <= GOALIE_BODY]
        if on_goalie and min(on_goalie)[0] <= GOALIE_PUCK:
            entry = {'kind': 'goalie', 'by': idx(lost, min(on_goalie)[1]), 'own': team(min(on_goalie)[1]) == me}
        else:
            if any(h['team'] == them and h['on'] == mine and abs(t[h['f']] - t[lost]) <= 700 for h in hits):
                continue  # a check landed on him (he stayed up)
            before = [q for q in range(max(0, lost - 40), min(N, lost + 3)) if t[lost] - t[q] <= BUMP_BEFORE]
            touching = [(gap(q, k1, k), k) for q in before for k in range(them * 6, them * 6 + 6) if skater(q, k)]
            if not touching or min(touching)[0] > CONTACT:
                continue
            k2 = min(touching)[1]
            q2 = max(q for q in before if q <= lost)
            entry = {'kind': 'skater', 'by': idx(lost, k2),
                     'human': bool(ctrl) and any(ctrl[q] >> k2 & 1 for q in range(max(0, q2 - 20), min(N, lost + 3)) if abs(t[q] - t[lost]) <= 300)}
        nxt = runs[j + 1] if j + 1 < len(runs) else None
        if nxt and (m['period'][nxt[1]] != m['period'][lost] or any(hidden(q) for q in range(lost, nxt[1] + 1))):
            nxt = None  # a whistle first
        if nxt and nxt[0] == k1 and t[nxt[1]] - t[lost] < 300:
            continue  # only a moment off his stick: he kept it
        out.append({'f': lost, 'team': me, 'idx': mine, **entry, 'x': P[3 * lost], 'y': P[3 * lost + 1],
                    'next': 'none' if not nxt else 'himself' if nxt[0] == k1 else 'teammate' if team(nxt[0]) == me else 'opponent',
                    'got': nxt[1] if nxt else None})
    return out


NET_Y = 268
HIGH_DANGER = (60, 50)     # within 60 units of the net (about 20 ft) and no wider than 50 from the middle: the slot
MEDIUM_DANGER = (100, 70)  # within 100 units and inside the faceoff dots
EA_GOALIE_LINE = 12        # an EA Special attempt is shot at a goalie standing within this of the puck's line to the net
EA_MAX_DISTANCE = 130      # ... from no farther out than this
EA_OUTWARD = 15            # ... not moving out toward the side faster than this (units/s)
EA_CARRIED = 600           # ... having carried the puck at least this long (ms)
EA_BACKWARD = 50           # ... by a shooter not skating toward his own end faster than this (units/s; standing or drifting is
                           # fine: Sweeney's real one in 2026-10-16_1314_BOS-PIT drifted back at 30, Juneau's non-one at P3 4:09 skated back at 80)
# In the recordings (226 attempts) a third of the attempts from that slot scored (20 of 60) and 14% of the rest; a
# tighter slot (50 x 40) scores 38% but holds only one attempt in seven. Goals by distance from the net: under 50
# units 35%, 50-75 24%, 75-100 18%, farther about 8%.


def shot_distance(sh):
    return math.hypot(sh['x'], (NET_Y if sh['y'] >= 0 else -NET_Y) - sh['y'])


def add_shot_context(m):
    """Tags that need the shots, passes and turnovers together (run after them):
    - every shot's `danger`: 'high' (the slot, HIGH_DANGER), 'medium' (MEDIUM_DANGER) or 'low', by where it was taken;
    - `assist`: the teammate whose completed pass reached the shooter in the 4 s before it (a shot assist, as the
      NHL's trackers count them), with the other team never having the puck in between;
    - `flip` on an EA Special attempt, and `afterFlip` on the same team's shot that followed it within 2 s from
      within 65 units (the rebound): the attempt is a wrist shot from close in and off to the side (within 70 units,
      at least 20 from the middle) at a goalie in position, which he saved; an attempt that leads to a goal is an
      EA Special (the goal gets that kind). The user's Genesis community
      calls the deliberate play an "EA Special", after the player known as EA who invented it (not Electronic
      Arts): skate down the side, usually a winger, flip a wrist shot on goal, the goalie bobbles it and is pushed
      back, and the shooter or an onrushing teammate scores into the open part of the net. Confirmed by the user:
      Ciccarelli's goal in capture2_away (P1 14:28);
    - each turnover's `shotAfter` (frame of the gaining team's first shot attempt within 5 s, no whistle between)
      and `goalAfter` (that attempt, or another by them in the 5 s, went in)."""
    t, own, P = m['t'], m['owner'], m['puck']
    shots, passes = m.get('shotList', []), m.get('passes', [])
    team_of = lambda f: -1 if own[f] < 0 else (0 if own[f] < 6 else 1)
    for sh in shots:
        d = shot_distance(sh)
        sh['danger'] = 'high' if d < HIGH_DANGER[0] and abs(sh['x']) <= HIGH_DANGER[1] else \
            'medium' if d < MEDIUM_DANGER[0] and abs(sh['x']) <= MEDIUM_DANGER[1] else 'low'
        for p in reversed(passes):
            if p['f'] >= sh['f'] or t[sh['f']] - t[p['f']] > 4000:
                continue
            if p['team'] == sh['team'] and p.get('to') == sh['idx'] and p['result'] in ('completed', 'one-timer') and p['idx'] != sh['idx'] \
                    and all(team_of(q) in (-1, sh['team']) for q in range(p['f'], sh['f'] + 1)):
                sh['assist'] = p['idx']
            break  # only the last pass before the shot
    K = 12
    # EA Specials are a Genesis play: the SNES goalie saves differently and is not pushed back by a wrist shot (the
    # user). On the Genesis the goalie often dives after the save, as if to cover the loose puck he is nowhere near,
    # and is out of the play for a couple of seconds: `eaDive` (a detail of the attempt, not a condition).
    genesis = m.get('system', 'genesis') == 'genesis'
    dive, shoot, forehand = (actions(m).get(a, set()) for a in ('dive', 'shoot', 'forehand'))
    anim = lambda q, k: m['anim'][(q * K + k) * 4:(q * K + k) * 4 + 4]
    for i, sh in enumerate(shots):
        if not genesis:
            break
        # An EA Special attempt: a wrist shot (never a slapshot: goalies hold those far more often) from the side,
        # flipped at a goalie in position (within EA_GOALIE_LINE of the puck's line to the net at the release; on the
        # saves in the recordings he stood 2-15 off it, on wrist shots that went straight in 15-51), which he stopped:
        # not a try to score directly. "From the side" is an angle: at least 20 units off the middle and 0.4 of the
        # distance, up to 130 out. The user's deliberate ones (2026-10-16_1314_BOS-PIT) came from 94 and 120 units,
        # by the faceoff dot and the half-boards (66 and 71 off the middle); a first limit of 70 units missed both.
        d = shot_distance(sh)
        # Whatever came of it (saved, blocked, wide: the user's review of 2026-10-16_1314_BOS-PIT counted a flip judged
        # blocked and one judged wide), except a goal straight from the shot, which is a goal, not an attempt.
        if sh['type'] != 'wrist shot' or sh['result'] == 'goal' or d >= EA_MAX_DISTANCE or abs(sh['x']) < max(20, 0.4 * d):
            continue
        net_y = NET_Y if sh['y'] >= 0 else -NET_Y
        keeper = next(((m['pos'][(sh['f'] * K + k) * 2], m['pos'][(sh['f'] * K + k) * 2 + 1])
                       for k in range((1 - sh['team']) * 6, (1 - sh['team']) * 6 + 6) if m['role'][sh['f'] * K + k] == '0'), None)
        if not keeper:
            continue
        vx, vy = -sh['x'], net_y - sh['y']
        off_line = abs((keeper[0] - sh['x']) * vy - (keeper[1] - sh['y']) * vx) / math.hypot(vx, vy)
        if off_line > EA_GOALIE_LINE:
            continue
        # Only a person tries one (the computer never does): the shooter carried the controlled-skater marker as he
        # released it (within a few samples; the rebound may be anyone's).
        ctrl = m.get('ctrl') or []
        shooter = [k for k in range(sh['team'] * 6, sh['team'] * 6 + 6) if int(m['roster'][sh['f'] * K + k], 36) == sh['idx']]
        if not shooter or not any(q < len(ctrl) and ctrl[q] >> shooter[0] & 1 for q in range(max(0, sh['f'] - 6), sh['f'] + 1)):
            continue
        # Always a forehand (the user): his last shooting animation before the release is the forehand one ...
        k = shooter[0]
        last = next((anim(q, k) for q in range(sh['f'], max(0, sh['f'] - 90), -1) if anim(q, k) in shoot), None)
        if last not in forehand:
            continue
        # ... so from his forehand side, as the attacker sees it: right-handed (drawn mirrored) from the left,
        # left-handed from the right.
        from_left = sh['x'] * (1 if net_y > 0 else -1) < 0
        if (m['mirror'][sh['f'] * K + k] == '1') != from_left:
            continue
        # Never skating away from the goal (the user: standing still is fine; away = moving toward his own end), over
        # the half second before the release.
        q0 = next((q for q in range(sh['f'], -1, -1) if t[sh['f']] - t[q] >= 500), 0)
        dt = (t[sh['f']] - t[q0]) / 1000 or 1
        toward = (m['pos'][(sh['f'] * K + k) * 2 + 1] - m['pos'][(q0 * K + k) * 2 + 1]) * (1 if net_y > 0 else -1) / dt
        if toward < -EA_BACKWARD:
            continue
        # Coming in from the side, not drifting out to it: the user ruled out a shooter moving from in front of the
        # net toward the side (CGY-BOS OT 9:02, 59 units/s outward); in all of the user's real ones he was moving in
        # toward the middle (9-81 units/s).
        outward = (abs(m['pos'][(sh['f'] * K + k) * 2]) - abs(m['pos'][(q0 * K + k) * 2])) / dt
        if outward > EA_OUTWARD:
            continue
        # A set play, not a scramble: he carried the puck at least EA_CARRIED before the shot (the user ruled out a
        # wrist shot 0.3 s after winning a loose puck in a scrum, capture6 P2 0:08; the real ones carried 0.9 s or more).
        q = sh['f'] - 1
        while q > 0 and own[q] == k:
            q -= 1
        if t[sh['f'] - 1] - t[q] < EA_CARRIED:
            continue
        # And not a follow-up: no attempt by his team in the 3 s before (the user's review of the first nine found
        # rebound put-backs among them).
        if any(s['team'] == sh['team'] and s['f'] < sh['f'] and t[sh['f']] - t[s['f']] < 3000 for s in shots):
            continue
        sh['flip'] = True
        settled = sh.get('resolved', sh['f'])
        if any(anim(q, k) in dive for q in range(settled, len(t)) if t[q] - t[settled] <= 2000
               for k in range((1 - sh['team']) * 6, (1 - sh['team']) * 6 + 6) if m['role'][q * K + k] == '0'):
            sh['eaDive'] = True
        # The rebound: the same team's next attempt within 2 s from close in, by the shooter or an onrushing
        # teammate; when it goes in, that is an EA Special. Not when a defending skater had the puck in between: in
        # 2026-10-16_1314_BOS-PIT (P2 4:23) Pittsburgh's Taglianeti collected Oates's flip and put it into his own net,
        # which the game credits to Oates; the user counts that as an attempt only.
        follow = next((s for s in shots[i + 1:] if s['team'] == sh['team'] and s['f'] > sh['f'] and t[s['f']] - t[sh['f']] <= 2000 and shot_distance(s) < 65), None)
        defenders = range((1 - sh['team']) * 6, (1 - sh['team']) * 6 + 6)
        if follow and not any(own[q] in defenders and m['role'][q * K + own[q]] != '0' for q in range(sh['f'] + 1, follow['f'] + 1)):
            follow['afterFlip'] = True
    for e in m.get('turnovers', []):
        gainer = 1 - e['from']
        horizon = t[e['f']] + 5000
        stop = next((q for q in range(e['f'], len(t)) if t[q] > horizon or P[3 * q + 2] < -100), len(t))
        after = [s for s in shots if s['team'] == gainer and e['f'] <= s['f'] < stop]
        if after:
            e['shotAfter'] = after[0]['f']
            e['goalAfter'] = any(s['result'] == 'goal' for s in after)


RUSH_MS = 5000  # a shot attempt within this of the team's zone entry is off the rush
PAD_A, PAD_B, PAD_C = 64, 16, 32  # controller bits as kept in the match file (Genesis layout; SNES mapped to it)


def add_play_context(m):
    """Tags about how play was made, after add_shot_context:
    - `human` on hits, penalties, shots and passes: the player (thrower, fouler, shooter, passer) was the skater a
      person controlled (the controlled-skater marker on his record within 0.3 s; for a penalty, at the foul, or in
      the 3 s before it was listed when the moment of the foul is not known). The person always has the puck
      carrier, so shots and passes are a person's almost always.
    - each shot's `origin`: 'rush' (within RUSH_MS of the team's zone entry, the puck still in the zone), 'zone'
      (later in that stay: sustained pressure), 'faceoff' (no entry: from a faceoff in that zone), else 'other';
    - each zone entry's `odd`: [attackers, defenders] as the puck crossed the blue line: the entering team's skaters
      level with the puck or ahead of it (or up to 60 behind it) against the defending team's skaters back
      between the puck and their net; on a carried or passed entry, more attackers than defenders (at least two) is
      an odd-man rush (2-on-1, 3-on-2 ...), and 1-on-0 a breakaway (a dump-in leaves the attackers behind it);
    - `wrap` on a shot taken from beside the post (within 45 of the middle, close to the goal line) just after the
      shooter carried the puck behind that goal line: a wraparound;
    - m['habits']: for each team a person played, what that person did with the controller: button presses
      (A, B, C) and minutes of live play, and the controlled skater's actions (speed bursts / check lunges and the
      checks landed, poke checks and hooks and the takeaways they made, the goalie's dives and the time a person had
      the goalie; one-timers and passes come from the shot and pass lists' `human`). Hooks are not known on the SNES."""
    t, P, own = m['t'], m['puck'], m['owner']
    N, K = len(t), 12
    ctrl = m.get('ctrl') or []
    act = actions(m)
    anim = lambda q, k: m['anim'][(q * K + k) * 4:(q * K + k) * 4 + 4]
    record = lambda f, team, idx: next((k for k in range(team * 6, team * 6 + 6) if int(m['roster'][f * K + k], 36) == idx), None)

    def controlled(f, team, idx, before=300, after=300):
        if not ctrl or idx is None or idx < 0:
            return False
        lo = next((q for q in range(f, -1, -1) if t[f] - t[q] > before), -1) + 1
        hi = next((q for q in range(f, N) if t[q] - t[f] > after), N)
        for q in range(lo, hi):
            k = record(q, team, idx)
            if k is not None and ctrl[q] >> k & 1:
                return True
        return False

    for h in m.get('hits', []):
        h['human'] = controlled(h['f'], h['team'], h['by'])
    for p in m.get('penalties', []):
        p['human'] = controlled(p['called'], p['team'], p['idx']) if 'called' in p else controlled(p['f'], p['team'], p['idx'], 3000, 0)
    for sh in m.get('shotList', []):
        sh['human'] = controlled(sh['f'], sh['team'], sh['idx'], 300, 0)
    for p in m.get('passes', []):
        p['human'] = controlled(p['f'], p['team'], p['idx'], 300, 0)

    # Odd-man rushes, at the moment the puck crossed the blue line
    for e in m.get('zoneEntries', []):
        f, team = e['f'], e['team']
        sign = 1 if P[3 * f + 1] >= 0 else -1  # the end they entered
        py = sign * P[3 * f + 1]
        skaters = lambda side: [k for k in range(side * 6, side * 6 + 6) if m['role'][f * K + k] not in ('x', '0')]
        ya = lambda k: sign * m['pos'][(f * K + k) * 2 + 1]
        attackers = sum(1 for k in skaters(team) if ya(k) >= py - 60)
        defenders = sum(1 for k in skaters(1 - team) if ya(k) >= py - 10)
        e['odd'] = [attackers, defenders]

    # Where each shot attempt came from: the rush, sustained pressure, or a faceoff in that zone
    entries = m.get('zoneEntries', [])
    faceoffs = m.get('faceoffs', [])
    for sh in m.get('shotList', []):
        stay = next((e for e in reversed(entries) if e['team'] == sh['team'] and e['f'] <= sh['f'] <= e.get('end', e['f'])), None)
        if stay:
            sh['origin'] = 'rush' if t[sh['f']] - t[stay['f']] <= RUSH_MS else 'zone'
            continue
        fo = next((e for e in reversed(faceoffs) if e['f'] <= sh['f']), None)
        attacking_end = 1 if sh['y'] >= 0 else -1
        if fo and fo.get('zone') != 'neu' and (fo['y'] >= 0) == (attacking_end > 0) and \
                not any(P[3 * q + 2] < -100 for q in range(fo['f'], sh['f'])):
            sh['origin'] = 'faceoff'
        else:
            sh['origin'] = 'other'

    # Wraparounds: the shooter had the puck behind that goal line in the 1.5 s before releasing it beside the post
    for sh in m.get('shotList', []):
        if abs(sh['x']) > 45 or abs(sh['y']) < 235 or sh['kind'] not in ('shot', 'one-timer'):
            continue
        k = record(sh['f'], sh['team'], sh['idx'])
        end = 1 if sh['y'] > 0 else -1
        lo = next((q for q in range(sh['f'], -1, -1) if t[sh['f']] - t[q] > 1500), -1) + 1
        if k is not None and any(own[q] == k and end * P[3 * q + 1] > 270 for q in range(lo, sh['f'])):
            sh['wrap'] = True

    # Controller habits, for each team a person played
    pads = [(m.get('pad'), m.get('padTeam', -1)), (m.get('pad2'), m.get('pad2Team', -1))]
    live = [q for q in range(N - 1) if P[3 * q + 2] >= -100]
    minutes = sum(min(100, t[q + 1] - t[q]) for q in live) / 60000
    habits = [None, None]
    for pad, team in pads:
        if not pad or team not in (0, 1):
            continue
        presses = {name: sum(1 for q in range(1, len(pad)) if pad[q] & bit and not pad[q - 1] & bit)
                   for name, bit in (('A', PAD_A), ('B', PAD_B), ('C', PAD_C))}
        mine = range(team * 6, team * 6 + 6)
        starts = lambda words, goalie=False: [(q, k) for q in range(1, N) for k in mine
                                              if ctrl and ctrl[q] >> k & 1 and anim(q, k) in words and anim(q - 1, k) not in words
                                              and (m['role'][q * K + k] == '0') == goalie]
        lunges = starts(act.get('lunge', set()))
        pokes = starts(act.get('poke', set()))
        hooks = starts(act.get('hook', set()))
        dives = starts(act.get('dive', set()), goalie=True)
        goalie_ms = sum(min(100, t[q + 1] - t[q]) for q in live if any(ctrl[q] >> k & 1 and m['role'][q * K + k] == '0' for k in mine))
        takes = [e for e in m.get('turnovers', []) if e['kind'] == 'takeaway' and e['from'] != team]
        habits[team] = {
            'minutes': round(minutes, 2), 'presses': presses,
            # C without the puck is the speed burst and the check lunge in one ($0C5E): 'bursts' counts both, 'checks'
            # the checks the controlled skater landed.
            'bursts': len(lunges), 'checks': sum(1 for h in m.get('hits', []) if h['team'] == team and h.get('human')),
            'pokes': len(pokes), 'pokeTakeaways': sum(1 for e in takes if e.get('how') == 'poke check' and controlled(e['lost'], team, e.get('by'))),
            'hooks': len(hooks), 'hookTakeaways': sum(1 for e in takes if e.get('how') == 'hook' and controlled(e['lost'], team, e.get('by'))),
            'dives': len(dives), 'goalieSeconds': round(goalie_ms / 1000, 1),
        }
    if any(habits):
        m['habits'] = habits


def find_injuries(m):
    """Injuries, from each player's availability code: when he is not serving a penalty, the low byte of his penalty
    word (Genesis team block +$66 + 2i; the SNES box state $1852 the same) is $FE on the bench, $FF on the ice and $FD
    out. The game puts an injured player out for the rest of the period or of the game: out for the period clears
    at the period's end (Jagr in 2026-10-16_1314_BOS-PIT: $FD from his injury at P3 4:01 until the horn, then $FE
    with everyone; the computer simply had not sent him back), out for the game never does. Whether the player comes
    back on the ice says nothing (the computer may keep him on the bench). The moment and the cause come from the
    injury animation (genesis ACTIONS "injury": $1AF4 injury1, $145C injuryfall) in the 3 s before the code turned
    $FD, and the opponent whose hit he took in the 1.5 s before that.
    Returns [{f, team, idx, by, out: 'period' | 'game', until (frame the code cleared, or None), atStart (already
    out when the recording began)}]."""
    st = m.get('stats') or {}
    if not st.get('f') or st.get('p', 0) < 8:
        return []
    t, K, N = m['t'], 12, len(m['t'])
    n, per, frames = st['n'], st['p'], st['f']
    words = actions(m).get('injury', set())
    anim = lambda q, k: m['anim'][(q * K + k) * 4:(q * K + k) * 4 + 4]
    code = lambda side, s_, idx: (lambda v: v[n + per * idx + 7] if len(v) >= n + per * (idx + 1) else 0xFFFE)(st[side][s_])
    out = []
    for team, side in enumerate(('home', 'away')):
        places = (len(st[side][0]) - n) // per if st[side] else 0
        for idx in range(places):
            was = None
            for s_, fr in enumerate(frames):
                c = code(side, s_, idx)
                down = c == 0xFFFD
                if down and was is None:
                    # Already out when the recording began (capture1: Desjardins, out through period 1): no moment or
                    # cause to show, but his line says so.
                    until = next((frames[j] for j in range(s_ + 1, len(frames)) if code(side, j, idx) != 0xFFFD), None)
                    out.append({'f': fr, 'team': team, 'idx': idx, 'by': None, 'atStart': True,
                                'out': 'period' if until is not None else 'game', 'until': until})
                elif down and was is False:
                    # When and why: the injury animation in the 3 s before, and the hit he took just before that
                    f = fr
                    for q in range(fr, -1, -1):
                        if t[fr] - t[q] > 3000:
                            break
                        if any(anim(q, k) in words and int(m['roster'][q * K + k], 36) == idx for k in range(team * 6, team * 6 + 6)):
                            f = q
                            while f > 0 and any(anim(f - 1, k) in words and int(m['roster'][(f - 1) * K + k], 36) == idx for k in range(team * 6, team * 6 + 6)):
                                f -= 1
                            break
                    hit = next((h for h in reversed(m.get('hits', [])) if h['f'] <= f and t[f] - t[h['f']] <= 1500 and h['team'] != team and h['on'] == idx), None)
                    until = next((fr2 for c2, fr2 in ((code(side, j, idx), frames[j]) for j in range(s_ + 1, len(frames))) if c2 != 0xFFFD), None)
                    out.append({'f': f, 'team': team, 'idx': idx, 'by': hit['by'] if hit else None,
                                'out': 'period' if until is not None else 'game', 'until': until})
                was = down
    return sorted(out, key=lambda e: e['f'])


def find_goals(match, rosters):
    """Goals from the stat snapshots: when a team's goal count goes up, whose goals and assists went up with it
    (looking two seconds on, as the game can credit them a moment apart), and what kind of goal it was."""
    stats, n, per = match["stats"], match["stats"]["n"], match["stats"]["p"]
    kinds = {STAT_FIELDS.index(field): name for field, name in (("ppGoals", "PPG"), ("shGoals", "SHG"), ("breakGoals", "breakaway"),
                                                                ("oneTimerGoals", "one-timer"), ("psGoals", "penalty shot"))}
    goals = []
    for team, side in enumerate(("home", "away")):
        snaps = stats[side]
        for i in range(1, len(snaps)):
            if snaps[i][1] <= snaps[i - 1][1]:
                continue
            f = stats["f"][i]
            j = i
            while j + 1 < len(snaps) and match["t"][stats["f"][j + 1]] <= match["t"][f] + 2000:
                j += 1
            before, after = snaps[i - 1], snaps[j]
            roster = rosters[team]
            gained = lambda idx, field: after[n + per * idx + field] - before[n + per * idx + field]
            scorer = next((idx for idx in range(len(roster)) if not roster[idx]["g"] and gained(idx, 0) > 0), None)
            assists = [idx for idx in range(len(roster)) if gained(idx, 1) > 0]
            goals.append({
                "f": f, "team": team, "period": match["period"][f], "clock": match["clock"][f],
                "scorer": scorer, "goals": after[n + per * scorer] if scorer is not None else None,
                "assists": [[idx, after[n + per * idx + 1]] for idx in assists],
                "kinds": [name for at, name in kinds.items() if after[at] > before[at]],
            })
    return sorted(goals, key=lambda g: g["f"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path, help="folder containing fast.bin or ram.bin")
    ap.add_argument("--name", help="match name (default: the capture folder's name)")
    ap.add_argument("--rom", type=Path, help="the ROM that was being played (default: found from the recording, else nhl94.bin)")
    ap.add_argument("--home", help="home team name (default: read from the ROM)")
    ap.add_argument("--away", help="away team name (default: read from the ROM)")
    ap.add_argument("--out", type=Path, default=ROOT / "matches")
    args = ap.parse_args(argv)

    system = systems.of_capture(args.capture)
    cap = Capture(args.capture, system)
    rom_path, rom_note = (args.rom, "given") if args.rom else system.find_rom(args.capture)
    name = args.name or args.capture.resolve().name
    match = system.read_match(cap, rom_path, name, args.home, args.away)
    match["system"] = system.NAME
    if "stats" in match:
        steady_stats(match)
    if "stats" in match and "rosters" in match and "goals" not in match:
        match["goals"] = find_goals(match, match["rosters"])
        # The game's own scoring summary, where the system has one: it names the scorer and assists outright and the
        # strength (even, power play, two men up, shorthanded). Matched to the goals found from the stats in order.
        summary = system.scoring_summary(cap) if hasattr(system, "scoring_summary") else []
        goals = match["goals"]
        if len(summary) > len(goals):
            summary = summary[len(summary) - len(goals):]  # the recording began after the first goals
        if summary and len(summary) == len(goals) and all(e["team"] == g["team"] for e, g in zip(summary, goals)):
            for e, g in zip(summary, goals):
                g["strength"] = e["strength"]
                if e["strength"] in ("PP2", "SH2"):
                    g["kinds"].append("5 on 3" if e["strength"] == "PP2" else "3 on 5")
                if e["scorer"] != g["scorer"] or sorted(e["assists"]) != sorted(a[0] for a in g["assists"]):
                    print(f"scoring summary differs at goal {goals.index(g) + 1}: summary {e}, stats {g}; the summary is used")
                    g["scorer"], g["assists"] = e["scorer"], [[a, None] for a in e["assists"]]
        elif summary:
            print(f"scoring summary: {len(summary)} goals, the stats show {len(goals)}; not used")

    # The recorded controller ($BEEF) is the local player's. With two people playing, whose is it? The team whose
    # controlled skater starts an action (pass, shot, check, poke, hook, dive...) within 350 ms of a press, clearly
    # more often than the other team's. In capture6_netplay_bos_stl (the user Boston, online): 222 against 102 of 617.
    if "pad" in match:
        act = system.ACTIONS
        pressed = set().union(*(act.get(a, set()) for a in ("pass", "shoot", "lunge", "poke", "hook", "dive", "goalie_pass", "goalie_save")))
        t, A, ctrl = match["t"], match["anim"], match["ctrl"]

        def answers(pad):
            out = [0, 0]
            for i in range(1, len(t)):
                if not pad[i] & 0x70 & ~pad[i - 1]:
                    continue
                for team in (0, 1):
                    ks = [k for k in range(team * 6, team * 6 + 6) if (ctrl[i] >> k) & 1]
                    j = i
                    while j < len(t) and t[j] - t[i] <= 350:
                        if any(A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] in pressed
                               and A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] != A[((j - 1) * 12 + k) * 4:((j - 1) * 12 + k) * 4 + 4] for k in ks):
                            out[team] += 1
                            break
                        j += 1
            return 0 if out[0] > 1.5 * out[1] else 1 if out[1] > 1.5 * out[0] else -1

        match["padTeam"] = answers(match["pad"])
        if "pad2" in match and not hasattr(system, "controller_teams"):
            second = answers(match["pad2"])  # the SNES does not say: whose skater answers controller 2
            match["pad2Team"] = second if second >= 0 and second != match["padTeam"] else -1
        # Better: the game says which team each controller plays for (cont1team / cont2team). Controller 2 is the
        # other player's in netplay (pad2; in capture6_netplay_bos_stl St. Louis's presses answer it 308 to 91).
        if hasattr(system, "controller_teams"):
            first, second = system.controller_teams(cap)
            if first >= 0:
                match["padTeam"] = first
            match["pad2Team"] = second if second >= 0 and second != match["padTeam"] else -1
    # The analysis needs the system's animation words (shoot, pass ...) and who has the puck; a system that does not
    # have them yet (the SNES) gets the replay without it.
    if all(system.ACTIONS.get(a) for a in ("shoot", "pass")) and any(o >= 0 for o in match["owner"]):
        # Shots for the shot map, credited where the game counted them (and to the scorer it named, when known).
        match["shotList"] = find_shots(match, match.get("goals"))
        match["turnovers"] = find_turnovers(match)
        match["failedOneTimers"] = find_failed_one_timers(match)
        match["passes"] = find_passes(match)
        match["faceoffs"] = find_faceoffs(match)
        match["icings"] = find_icings(match)
        match["zoneEntries"] = find_zone_entries(match)
        match["hits"] = find_hits(match)
        add_shot_context(match)
        add_play_context(match)
        match["injuries"] = find_injuries(match)
        match["bumps"] = find_bumps(match)
        match["bobbles"] = find_bobbles(match)
    for goal in match.get("goals", []):  # a goal scored with a pass shot says so, beside the game's own kinds
        if any(sh["kind"] == "pass shot" and sh["result"] == "goal" and sh["team"] == goal["team"]
               and abs(match["t"][sh["f"]] - match["t"][goal["f"]]) <= 5000 for sh in match.get("shotList", [])):
            goal["kinds"].append("pass shot")
        # A goal off an EA Special (see add_shot_context): the shot that went in followed the bobbled wrist shot.
        if any(sh.get("afterFlip") and sh["result"] == "goal" and sh["team"] == goal["team"]
               and abs(match["t"][sh["f"]] - match["t"][goal["f"]]) <= 2000 for sh in match.get("shotList", [])):
            goal["kinds"].append("EA Special")

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / f"{name}.js"
    target.write_text("window.NHL94_MATCH = " + json.dumps(match, separators=(",", ":")) + ";\n", encoding="utf-8")
    frames = len(match["t"])
    held = sum(1 for o in match["owner"] if o >= 0) / frames
    print(f"ROM: {rom_path.name} ({rom_note})")
    print(f"{target}: {match['team1']} (home) vs {match['team2']} (away), {frames} frames, {match['t'][-1] / 1000:.0f} s, "
          f"puck held {held:.0%} of frames, buttons {'yes' if 'pad' in match else 'no'}, {target.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
