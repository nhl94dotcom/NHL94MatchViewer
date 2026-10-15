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

    def scorer_touch(team, g, idx):
        # A shot by a player with no shot of his found: the last moment the puck changed course beside him.
        for i in range(g, 0, -1):
            if t[g] - t[i] > 2000:
                break
            for k in (range(6) if team == 0 else range(6, 12)):
                if roster_idx(i, k) == idx and near(i, k, 30) and (kick(i) > 3000 or own[i - 1] == k):
                    found = shot(i, k, team, 'one-timer' if anim(i, k) in SHOOT else 'deflection')
                    found['known'] = g  # found only when the game counted it
                    return add(found)
        return None

    def origin(team, g, idx=-1):
        # a counted shot with no shot found (a scramble): where the puck last changed course
        i = g
        while i > 1 and t[g] - t[i] < 1500:
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
    events = []
    for team in (0, 1):
        sogs = [g for g in range(1, N) if sog(g, team) > sog(g - 1, team)]
        goal_frames = [g for g in range(1, N) if score(g, team) > score(g - 1, team)]
        for g in goal_frames:
            close = [s for s in sogs if abs(t[s] - t[g]) <= 1500]
            if close:
                sogs.remove(min(close, key=lambda s: abs(t[s] - t[g])))
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
        sh['result'], sh['counted'], sh['resolved'] = result, True, g
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
    for s in range(1, len(F)):
        f = F[s]
        for team, side in ((0, 'home'), (1, 'away')):
            a, b = st[side][s - 1], st[side][s]
            for idx in range((len(b) - n) // per):
                rise = b[n + per * idx + slot] - a[n + per * idx + slot]
                if not 0 < rise <= 3:
                    continue
                k = next((k for k in range(team * 6, team * 6 + 6) if on_ice(f, k) and int(roster[f * 12 + k], 36) == idx), None)
                if k is None:
                    continue
                opp = [v for v in range((1 - team) * 6, (1 - team) * 6 + 6) if on_ice(f, v)]
                if not opp:
                    continue
                down = []  # (distance, victim record, frame) for opponents going down within 0.8 s
                j0 = f
                while j0 > 0 and t[f] - t[j0 - 1] <= 800:
                    j0 -= 1
                j = j0
                while j < N and t[j] - t[f] <= 800:
                    for v in opp:
                        if on_ice(j, v) and anim(j, v) in act['down'] and dist(j, k, v) < 40:
                            down.append((dist(j, k, v), v, j))
                    j += 1
                victim = min(down)[1] if down else min((dist(f, k, v), v) for v in opp)[1]
                x, y = at(f, victim)
                # How it was thrown (the thrower's check animation: shoulder, hip, cross-check) and what it did to the
                # player hit (knocked down, upended, into the boards, into the bench), within 0.7 s either side.
                # In the recordings: shoulder 111, cross-check 14, hip 2, not seen 48.
                how = outcome = None
                for j in range(j0, N):
                    if t[j] - t[f] > 700:
                        break
                    if t[f] - t[j] > 700:
                        continue
                    how = how or check_moves.get(anim(j, k))
                    if outcome in (None, 'knocked down'):
                        outcome = hit_outcomes.get(anim(j, victim), outcome)
                for _ in range(rise):
                    out.append({'f': f, 'team': team, 'by': idx, 'on': int(roster[f * 12 + victim], 36), 'x': round(x), 'y': round(y),
                                'how': how or 'check', 'outcome': outcome or 'stayed up'})
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
        answers = [0, 0]
        act = system.ACTIONS
        pressed = set().union(*(act[a] for a in ("pass", "shoot", "lunge", "poke", "hook", "dive", "goalie_pass", "goalie_save")))
        t, A, pad, ctrl = match["t"], match["anim"], match["pad"], match["ctrl"]
        for i in range(1, len(t)):
            if not pad[i] & 0x70 & ~pad[i - 1]:
                continue
            for team in (0, 1):
                ks = [k for k in range(team * 6, team * 6 + 6) if (ctrl[i] >> k) & 1]
                j = i
                while j < len(t) and t[j] - t[i] <= 350:
                    if any(A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] in pressed
                           and A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] != A[((j - 1) * 12 + k) * 4:((j - 1) * 12 + k) * 4 + 4] for k in ks):
                        answers[team] += 1
                        break
                    j += 1
        match["padTeam"] = 0 if answers[0] > 1.5 * answers[1] else 1 if answers[1] > 1.5 * answers[0] else -1
        # Better: the game says which team each controller plays for (cont1team / cont2team). Controller 2 is the
        # other player's in netplay (pad2; in capture6_netplay_bos_stl St. Louis's presses answer it 308 to 91).
        if hasattr(system, "controller_teams"):
            first, second = system.controller_teams(cap)
            if first >= 0:
                match["padTeam"] = first
            match["pad2Team"] = second if second >= 0 and second != match["padTeam"] else -1
    # Shots for the shot map, credited where the game counted them (and to the scorer it named, when known).
    match["shotList"] = find_shots(match, match.get("goals"))
    match["turnovers"] = find_turnovers(match)
    match["failedOneTimers"] = find_failed_one_timers(match)
    match["passes"] = find_passes(match)
    match["faceoffs"] = find_faceoffs(match)
    match["icings"] = find_icings(match)
    match["zoneEntries"] = find_zone_entries(match)
    match["hits"] = find_hits(match)
    for goal in match.get("goals", []):  # a goal scored with a pass shot says so, beside the game's own kinds
        if any(sh["kind"] == "pass shot" and sh["result"] == "goal" and sh["team"] == goal["team"]
               and abs(match["t"][sh["f"]] - match["t"][goal["f"]]) <= 5000 for sh in match["shotList"]):
            goal["kinds"].append("pass shot")

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
