"""Converts a RAM capture (from nhl94_record.ps1 or nhl94_record_full.ps1) into a match file that viewer.html can play."""
import argparse
import bisect
import gzip
import json
import os
import math
import re
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

FULL = 8 + 0x10000  # one full.bin snapshot
OLD_BLOCKS = [[0xB000, 0x900], [0xC400, 0x800]]  # fast.bin layout before capture.json existed
BASE, SIZE = 0xB04A, 0x80  # record 0 start, record size
PLAYERS, PUCK = 12, 14
FRAME, X, Y, Z, ROLE, FACING, ANIM, FLAGS, ROSTER, HAND = 0x06, 0x1C, 0x20, 0x24, 0x35, 0x55, 0x58, 0x62, 0x66, 0x76
OWNED, OWNER = 0x60, 0x61  # puck record: $00 while a player has it, and that player's record number
HOME_TEAM, AWAY_TEAM = 0xC6F6, 0xCA5A
# Each team's stat block ($364 bytes, cleared before a game). Team words, then byte arrays by roster index.
STAT_BLOCKS = (0xC6CE, 0xCA32)  # Home, Away
# shots, goals, faceoffs won, checks, passes tried, passes made, attack-zone seconds,
# breakaways tried, breakaway goals, one-timers tried, one-timer goals, penalty shots tried, penalty-shot goals,
# power-play goals, power plays, penalties, penalty minutes, shorthanded goals. The power-play, penalty and
# shorthanded offsets come from the user's old save-state parser (stats_parse_code.txt), which also confirms the rest.
TEAM_STATS = (0x00, 0x0C, 0x0E, 0x10, 0x12, 0x14, 0x0A, 0x358, 0x35A, 0x35C, 0x35E, 0x360, 0x362, 0x02, 0x04, 0x06, 0x08, 0x356)
GOALS, ASSISTS, SHOTS, CHECKS_OR_PIM, HITS_TAKEN = 0xB4, 0xCE, 0xE8, 0x102, 0x11C  # one byte per roster index
ICE_TIME, ENERGY = 0x136, 0x32  # one word per roster index: game seconds played; energy 0-16 in the high byte
PENALTY = 0x66  # one word per roster index: $FFxx = not penalized; else high byte $20 = called, play still on
                # (delayed), $00 = serving; low byte = seconds left to serve
DELAYED = 0x26  # stat-block byte: $FF while this team has a delayed penalty coming (the other side has fouled)
PENALTY_LIST, RULES = 0xC5DC, 0x18E0C  # work RAM penalty summary; ROM table of rule messages (penalty names)
PIM_CODE = 0x12302  # the game adds penalty minutes here; smozROM's checks hack replaces it with two NOPs
PAD1 = 0xBEEF  # controller 1, held buttons: $80 Start, $40 A, $20 C, $10 B, $08 Right, $04 Left, $02 Down, $01 Up
TEAM_TABLE = 0x30E
RINK_LOGO_TABLE_POINTER = 0xFEA5A  # holds the address of a table of one logo address per team
# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent
DEFAULT_ROM = Path(r"C:\Users\tdemorest\RetroArch-1.17-Win64\ROMs\Genesis\nhl94.bin")
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


class Capture:
    """Samples of work RAM: an 8-byte millisecond stamp, then one or more blocks of RAM in host byte order."""

    def __init__(self, folder):
        if (folder / "ram.bin").exists():
            self.data, self.blocks = (folder / "ram.bin").read_bytes(), [[0, 0x10000]]
        else:
            # The helper writes the same samples gzipped (fast.bin.gz, full.bin.gz).
            fast = folder / "fast.bin"
            self.data = fast.read_bytes() if fast.exists() else gzip.decompress((folder / "fast.bin.gz").read_bytes())
            layout = folder / "capture.json"
            self.blocks = json.loads(layout.read_text())["blocks"] if layout.exists() else OLD_BLOCKS
        self.sample = 8 + sum(length for _, length in self.blocks)
        self.count = len(self.data) // self.sample
        # The recorder also keeps all of RAM once a second (full.bin), for addresses fast.bin does not hold.
        full, packed = folder / "full.bin", folder / "full.bin.gz"
        if (folder / "ram.bin").exists():
            self.full = b""
        else:
            self.full = full.read_bytes() if full.exists() else gzip.decompress(packed.read_bytes()) if packed.exists() else b""
        self.full_ms = [struct.unpack_from("<q", self.full, j * FULL) [0] for j in range(len(self.full) // FULL)]

    def offset(self, addr):
        """Position of a Genesis address within a sample, or None when the capture does not cover it."""
        pos = 8
        for start, length in self.blocks:
            if start <= addr < start + length:
                return pos + addr - start
            pos += length
        return None

    def ms(self, i):
        return struct.unpack_from("<q", self.data, i * self.sample)[0]

    def _full_at(self, i):
        """Start of the latest once-a-second snapshot taken at or before sample i (the first one if none)."""
        j = max(0, bisect.bisect_right(self.full_ms, self.ms(i)) - 1)
        return j * FULL + 8

    def byte(self, i, addr):  # host memory swaps the two bytes of each word
        off = self.offset(addr ^ 1)
        return self.data[i * self.sample + off] if off is not None else self.full[self._full_at(i) + (addr ^ 1)]

    def word(self, i, addr):
        off = self.offset(addr)
        if off is None:
            return struct.unpack_from("<H", self.full, self._full_at(i) + addr)[0]
        return struct.unpack_from("<H", self.data, i * self.sample + off)[0]

    def fixed(self, i, addr):  # 16.16 position, rounded to a tenth
        whole, frac = struct.unpack_from("<hH", self.data, i * self.sample + self.offset(addr))
        return round(whole + frac / 65536, 1)

    def raw(self, i, addr, length):
        start = i * self.sample + self.offset(addr)
        return self.data[start:start + length]


def colour(word):
    """Genesis colour word (0000BBB0GGG0RRR0) -> #rrggbb."""
    r, g, b = (((word >> shift) & 0xE) * 255 // 14 for shift in (0, 4, 8))
    return f"#{r:02x}{g:02x}{b:02x}"


def find_rom(capture):
    """The ROM a capture was played on, by the fingerprint the recorder stored, looked for beside the default ROM."""
    layout = capture / "capture.json"
    stored = json.loads(layout.read_text()).get("rom_crc32") if layout.exists() else None
    if not stored:
        return DEFAULT_ROM, "assumed; this capture does not say which ROM was played"
    first, second = (int(part, 16) for part in stored)
    # The helper copies the ROM out of the emulator into roms/ (named by its fingerprint); then RetroArch's ROM folder.
    candidates = sorted((ROOT / "roms").glob("*.bin")) + (sorted(DEFAULT_ROM.parent.glob("*.bin")) if DEFAULT_ROM.parent.exists() else [])
    for path in candidates:
        data = path.read_bytes()
        # The recorder fingerprints the first megabyte and the second; a one-megabyte ROM has no second.
        if zlib.crc32(data[:0x100000]) == first and (len(data) <= 0x100000 or zlib.crc32(data[0x100000:0x200000]) == second):
            return path, "matched to the recording"
    return DEFAULT_ROM, f"assumed; no ROM in {DEFAULT_ROM.parent} matches the one that was recorded"


def team_count(rom):
    """28 for the original game, 30 for the 30-team hack, 64 for NHL 94: EVO (as the NOSE editor tells them apart)."""
    if rom[0x120:0x12B] == b"NHL 94: EVO":
        return 64
    code = re.match(r"GM T-50656( -|-F)([03])", rom[0x180:0x18E].decode("latin-1"))
    return 30 if code and code.group(2) == "3" else 28


def overall(attrs, goalie):
    """The overall rating the game shows on its roster screens (formula from the NOSE editor)."""
    weights = [2.25, 0, 0, 2.25, 2.25, 0, 0, 0, 0, 0.5, 0.5, 0.5, 0.5] if goalie else [1, 1.5, 1.5, 1, 0.5, 1, 0, 1.5, 1, 0.5, 0, 0.5, 0]
    rating = 0
    for weight, value in zip(weights, attrs[1:]):
        rating += value * weight
        if goalie and weight == 2.25 and value % 2:  # the game rounds these down to the nearest half
            rating -= 0.25
    return int(rating + max(0, rating - 25) + 25)


def rink_logo(rom, team):
    """A team's centre-ice logo: 6 x 4 tiles of colour indices into its home palette, as one hex digit per pixel."""
    block = struct.unpack_from(">I", rom, struct.unpack_from(">I", rom, RINK_LOGO_TABLE_POINTER)[0] + 4 * team)[0]
    tiles = block + 10
    if not 0 < block and tiles + 24 * 32 <= len(rom):
        return None
    rows = [[0] * 48 for _ in range(32)]
    for t in range(24):
        for y in range(8):
            for x in range(4):
                v = rom[tiles + 32 * t + y * 4 + x]
                rows[(t // 6) * 8 + y][(t % 6) * 8 + 2 * x] = v >> 4
                rows[(t // 6) * 8 + y][(t % 6) * 8 + 2 * x + 1] = v & 15
    return {"w": 48, "h": 32, "p": "".join(f"{v:x}" for row in rows for v in row)}


def read_teams(rom_path):
    """Team names, rosters, palettes and logos from the ROM. Roster order matches the index in each player record."""
    rom = rom_path.read_bytes()
    teams = []
    for k in range(team_count(rom)):
        team = struct.unpack_from(">I", rom, TEAM_TABLE + 4 * k)[0]
        players_off, _, names_off = struct.unpack_from(">3H", rom, team)
        # The first players on a roster are its goalies, up to the last of four goalie values that is not zero.
        nibbles = [n for byte in rom[team + 0x50:team + 0x52] for n in (byte >> 4, byte & 15)]
        goalies = max((i + 1 for i, n in enumerate(nibbles) if n), default=0)
        players, off = [], team + players_off
        while True:
            length = struct.unpack_from(">H", rom, off)[0]
            if not 2 < length <= 40:
                break
            name = rom[off + 2:off + length].decode("latin-1").rstrip("\x00")
            # After the name: the jersey number as decimal digits, then fourteen ratings of 0-15, two to a byte.
            attrs = [n for byte in rom[off + length + 1:off + length + 8] for n in (byte >> 4, byte & 15)]
            goalie = len(players) < goalies
            players.append({"name": name, "num": int(f"{rom[off + length]:02x}"), "a": attrs, "g": goalie, "ovr": overall(attrs, goalie)})
            off += length + 8
        length = struct.unpack_from(">H", rom, team + names_off)[0]
        # Two 16-colour palettes per team, as the game loads them: +$0C when playing at home, +$2C when away.
        palettes = [[colour(struct.unpack_from(">H", rom, team + start + 2 * i)[0]) for i in range(16)] for start in (0x0C, 0x2C)]
        try:
            logo = rink_logo(rom, k)
        except (struct.error, IndexError):
            logo = None  # a ROM that keeps its logos somewhere this does not know
        teams.append({"name": rom[team + names_off + 2:team + names_off + length].decode("latin-1").rstrip("\x00"), "players": players,
                      "palettes": palettes, "logo": logo, "abbr": team_abbr(rom, team + names_off + length)})
    return teams


def team_abbr(rom, at):
    """The team's abbreviation (BOS, STL): the second of its length-prefixed name strings (city, abbreviation,
    nickname, arena), starting at `at`. Empty if it does not look like one."""
    length = struct.unpack_from(">H", rom, at)[0]
    return rom[at + 2:at + length].decode("latin-1").rstrip("\x00") if 2 < length < 12 else ""


def animation_table(rom):
    """The game's animation scripts, which the player record's animation word (+$58) is an offset into. Each starts
    with 8 word offsets (from the script's start), one per direction faced, to a list of (frame, duration) word pairs
    ended by a negative duration. The table is found by the standing animation ($050C): frames 1, 6, 11 ... 36, one
    pair per direction, so its offsets read 18, 22 ... 46. Returns {word as 4 hex digits: 8 lists of frames}, used by
    the viewer to redraw a player facing another way when the view is turned; {} if the table is not there."""
    word = lambda a: struct.unpack_from(">H", rom, a)[0]
    base = next((b for b in range(0, len(rom) - 0x2000, 2)
                 if all(word(b + 0x50C + 2 * e) == 18 + 4 * e for e in range(8)) and word(b + 0x50C + 18) == 1), None)
    if base is None:
        return {}

    def script(v):
        offsets = [word(base + v + 2 * e) for e in range(8)]
        if min(offsets) != 18 or max(offsets) > 0x600 or any(o % 2 for o in offsets):
            return None
        dirs = []
        for o in offsets:
            at, frames = base + v + o, []
            while True:
                frame, duration = word(at), struct.unpack_from(">h", rom, at + 2)[0]
                if not 0 < frame < 900 or len(frames) >= 64:
                    return None
                frames.append(frame)
                at += 4
                if duration < 0:
                    break
            dirs.append(frames)
        return dirs

    return {f"{v:04x}": dirs for v in range(2, 0x2000, 2) if (dirs := script(v))}


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
    SHOOT, PASS = {'07fc', '092e'}, {'0718', '078a'}  # the two shooting animations, the two passing ones
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
    keys = ('f', 'team', 'idx', 'x', 'y', 'speed', 'kind', 'type', 'result', 'goalie', 'rebound')
    return [{**{key: sh[key] for key in keys}, 'counted': bool(sh.get('counted')),
             'known': sh.get('known', sh['f']), 'resolved': max(sh.get('resolved', sh['f']), sh.get('known', sh['f'])),
             **({'after': sh['after']} if 'after' in sh else {})} for sh in shots]


def find_failed_one_timers(m):
    """One-timers that never connected: a player went into a shooting animation ($07FC/$092E) without the puck, just
    after a teammate's pass (within 1.5 s; C pressed while the pass was on its way), and no shot of his came of it
    (no release in the shot list within the animation and 0.3 s after) because the puck never got close enough.
    The game's own one-timers-tried count (+$35C) only includes ones that connected: 6 and 7 in
    capture6_netplay_bos_stl, against 6 and 8 connected here and 11 and 1 that failed.
    Returns [{f (start of the swing), team, idx (roster index), passer (roster index), x, y (where he was)}]."""
    t, own, A = m['t'], m['owner'], m['anim']
    N, K = len(t), 12
    SHOOT, PASS = {'07fc', '092e'}, {'0718', '078a', '0366'}
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
    at = TEAM_STATS.index(0x0E)  # faceoffs won, in each stat snapshot
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
    PASS = {'0718', '078a', '0366'}
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
    tried = TEAM_STATS.index(0x12)
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
                if a in ('0b24', '1122', '0c5e') and dist(q, k) < 35:
                    cause = ({'0b24': 'poke check', '1122': 'hook', '0c5e': 'hit'}[a], k); break
            if cause:
                break
        if not cause and any(anim(q, k1) in ('0dd8', '0d26') for q in window):
            # He went down: the nearest opposing skater (a goalie only if no skater is there) hit him.
            near = sorted((k for k in rivals if m['role'][lost * K + k] != 'x'),
                          key=lambda k: (goalie(lost, k), math.hypot(pos(lost, k)[0] - pos(lost, k1)[0], pos(lost, k)[1] - pos(lost, k1)[1])))
            if near:
                cause = ('hit', near[0])
        passed = any(anim(q, k1) in ('0718', '078a', '0366') for q in window if q <= lost + 2)
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
    kinds = {13: "PPG", 17: "SHG", 8: "breakaway", 10: "one-timer", 12: "penalty shot"}  # team-stat positions
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

    cap = Capture(args.capture)
    rom_path, rom_note = (args.rom, "given") if args.rom else find_rom(args.capture)
    name = args.name or args.capture.resolve().name
    has_pad = cap.offset(PAD1) is not None

    match = {"version": 21, "name": name, "positions": ["G", "LD", "RD", "LW", "C", "RW"],
             "t": [], "clock": [], "period": [], "score": [], "shots": [], "puck": [], "puckV": [], "lights": [], "pos": [], "ctrl": [], "owner": []}
    if has_pad:
        match["pad"] = []
    facing, roster, anim, role, frame, mirror, puck_frame = [], [], [], [], [], [], []
    match["posts"] = []  # frames where the puck came off a goal post
    # Stat snapshots: whenever a counted stat changes, and once a second for ice time and energy.
    stats = {"f": [], "home": [], "away": []}
    last_counts, last_stat_ms = None, -10_000
    penalties = []
    delayed, open_delayed = [], [None, None]
    last_post = -10_000
    team_ids = Counter()
    previous = None
    for i in range(cap.count):
        # Identical consecutive samples (a paused game, or two reads of one frame) are stored once.
        key = (cap.raw(i, BASE, SIZE * 16), cap.raw(i, 0xC466, 4), cap.byte(i, PAD1) if has_pad else 0)
        if key == previous:
            continue
        previous = key
        team_ids[(cap.word(i, HOME_TEAM) & 0xFF, cap.word(i, AWAY_TEAM) & 0xFF)] += 1
        match["t"].append(cap.ms(i))
        match["period"].append(cap.word(i, 0xC466))
        match["clock"].append(cap.word(i, 0xC468))
        match["score"] += [cap.word(i, 0xC6DA), cap.word(i, 0xCA3E)]
        match["shots"] += [cap.word(i, 0xC6CE), cap.word(i, 0xCA32)]
        puck = BASE + SIZE * PUCK
        match["puck"] += [cap.fixed(i, puck + X), cap.fixed(i, puck + Y), cap.fixed(i, puck + Z)]
        # The puck's picture (frames 395-404 of the sprite table; 395 and 399 on the ice, the rest tumbling in the air).
        # Its height reads -256 while the game hides it, at stoppages before the faceoff.
        puck_frame.append(f"{cap.word(i, puck + FRAME) & 0xFFF:03x}")
        # Its speed words (+$28 X, +$2A Y, signed, same directions as the position), in hundreds: wrist shots peak at
        # about 11400-13700, slapshots 15000-23600.
        speed_x, speed_y = struct.unpack("<hh", cap.raw(i, puck + 0x28, 4))
        match["puckV"] += [round(speed_x / 100), round(speed_y / 100)]
        # Record 15, the puck's shadow, becomes the goal light after a goal: frames 563-576 (a red lamp, its flash and
        # then its beam turning), for 7-9 seconds, at the end boards behind the net or in the net.
        light = BASE + SIZE * 15
        light_frame = cap.word(i, light + FRAME) & 0xFFF
        if 563 <= light_frame <= 576:
            match["lights"] += [len(match["t"]) - 1, cap.fixed(i, light + X), cap.fixed(i, light + Y),
                                cap.fixed(i, light + Z), light_frame]
        owner = cap.byte(i, puck + OWNER)
        match["owner"].append(owner if cap.byte(i, puck + OWNED) == 0 and owner < PLAYERS else -1)
        # A post: the loose puck turns back out of the end zone right beside a post (about 20 units either side of
        # the middle, on the goal line). Found from a post shot the user saw in capture5_league30 at 2:57 of period 1;
        # across all captures the rule fires only three times.
        if i and cap.byte(i, puck + OWNED) != 0 and cap.ms(i) - last_post > 1000:
            px, py, vx, vy = struct.unpack("<hxxhxxxxxxhh", cap.raw(i, puck + X, 16))
            before = struct.unpack("<hh", cap.raw(i - 1, puck + 0x28, 4))
            fresh = (vx, vy) != before or cap.byte(i - 1, puck + OWNED) == 0
            if fresh and 14 <= abs(px) <= 28 and 252 <= abs(py) <= 272 and vy * py < 0 and abs(vx) + abs(vy) >= 1500:
                match["posts"].append(len(match["t"]) - 1)
                last_post = cap.ms(i)
        if has_pad:
            match["pad"].append(cap.byte(i, PAD1))
        mask = 0
        for k in range(PLAYERS):
            rec = BASE + SIZE * k
            match["pos"] += [cap.fixed(i, rec + X), cap.fixed(i, rec + Y)]
            facing.append(str(cap.byte(i, rec + FACING) & 7))
            roster.append(DIGITS[min(cap.byte(i, rec + ROSTER), 35)])
            anim.append(f"{cap.word(i, rec + ANIM):04x}")
            frame.append(f"{cap.word(i, rec + FRAME) & 0xFFF:03x}")
            mirror.append("0" if cap.byte(i, rec + HAND) & 1 else "1")
            code = cap.byte(i, rec + ROLE)
            role.append(str(code) if code < 6 else "x")
            if cap.byte(i, rec + FLAGS) & 0x08:
                mask |= 1 << k
        match["ctrl"].append(mask)
        vectors, counts = [], []
        for block in STAT_BLOCKS:
            vector = [cap.word(i, block + o) for o in TEAM_STATS]
            for idx in range(26):
                vector += [cap.byte(i, block + GOALS + idx), cap.byte(i, block + ASSISTS + idx), cap.byte(i, block + SHOTS + idx),
                           cap.byte(i, block + CHECKS_OR_PIM + idx), cap.byte(i, block + HITS_TAKEN + idx),
                           cap.word(i, block + ICE_TIME + 2 * idx), cap.byte(i, block + ENERGY + 2 * idx),
                           cap.word(i, block + PENALTY + 2 * idx)]
            vectors.append(vector)
            n = len(TEAM_STATS)
            counts.append([v for j, v in enumerate(vector) if j < n or (j - n) % 8 not in (5, 6)])
        # The penalty summary: a byte count, then 4 bytes per penalty in the order called:
        # (period << 14 | seconds into the period), team ($80 = Away) | rule code, roster index.
        # Delayed penalties: the benefiting team's flag goes up at the moment of the foul, and down when play
        # resumes. The offender is only written to the summary after the whistle; it is matched up below.
        for team, block in enumerate(STAT_BLOCKS):
            up = cap.byte(i, block + DELAYED) == 0xFF
            if up and open_delayed[team] is None:
                open_delayed[team] = {"f": len(match["t"]) - 1, "team": team}
            elif not up and open_delayed[team] is not None:
                open_delayed[team]["end"] = len(match["t"]) - 1
                delayed.append(open_delayed[team])
                open_delayed[team] = None
        listed = cap.word(i, PENALTY_LIST)
        if listed < 4 * len(penalties) or listed > 240:
            penalties.clear()  # a new game started, or the list is not set up yet
        while listed >= 4 * (len(penalties) + 1):
            at = PENALTY_LIST + 2 + 4 * len(penalties)
            when = (cap.byte(i, at) << 8) | cap.byte(i, at + 1)
            code = cap.byte(i, at + 2)
            # f = -1 marks penalties already listed when the recording began
            penalties.append({"f": len(match["t"]) - 1 if len(match["t"]) > 1 else -1, "period": when >> 14, "secs": when & 0x3FFF,
                              "team": code >> 7, "code": code & 0x7F, "idx": cap.byte(i, at + 3)})
        if counts != last_counts or cap.ms(i) - last_stat_ms >= 1000:
            stats["f"].append(len(match["t"]) - 1)
            stats["home"].append(vectors[0])
            stats["away"].append(vectors[1])
            last_counts, last_stat_ms = counts, cap.ms(i)
    match["facing"] = "".join(facing)
    match["roster"] = "".join(roster)  # one base-36 digit per player per frame: index into that team's roster
    match["role"] = "".join(role)  # one character per player per frame: index into "positions", or x when off the ice
    for team in (0, 1):
        if open_delayed[team] is not None:
            delayed.append({**open_delayed[team], "end": len(match["t"]) - 1})
    # A penalty listed while the other team's delayed flag was up was called when that flag went up.
    for p in penalties:
        for d in delayed:
            if d["team"] == 1 - p["team"] and d["f"] <= p["f"] <= d["end"] and not d.get("matched"):
                p["called"], d["matched"] = d["f"], True
                break
    match["delayed"] = delayed
    match["penalties"] = penalties
    match["frame"] = "".join(frame)  # three hex digits per player per frame: the animation frame, for the sprite library
    match["puckFrame"] = "".join(puck_frame)  # three hex digits per frame: the puck's picture
    match["mirror"] = "".join(mirror)  # 1 where the game draws that frame mirrored left-to-right
    match["anim"] = "".join(anim)  # four hex digits per player per frame: the animation word at record +$58

    home_id, away_id = team_ids.most_common(1)[0][0]
    match["team1"], match["team2"] = args.home or "Home", args.away or "Away"
    if rom_path.exists():
        teams = read_teams(rom_path)
        if home_id < len(teams) and away_id < len(teams):
            match["team1"], match["team2"] = args.home or teams[home_id]["name"], args.away or teams[away_id]["name"]
            match["abbr"] = [teams[home_id]["abbr"], teams[away_id]["abbr"]]
            match["rosters"] = [teams[home_id]["players"], teams[away_id]["players"]]
            match["palettes"] = [teams[home_id]["palettes"][0], teams[away_id]["palettes"][1]]
            # Stats per snapshot: the team values, then 8 per player (goals, assists, shots, checks or PIM, hits taken,
            # ice time, energy, penalty word) for each roster place.
            sizes = (len(TEAM_STATS) + 8 * len(teams[home_id]["players"]), len(TEAM_STATS) + 8 * len(teams[away_id]["players"]))
            stats["n"], stats["p"] = len(TEAM_STATS), 8
            rom_bytes = rom_path.read_bytes()
            # Penalty names and lengths: the rule-message table (the NOSE editor's rulesOffset). A code is twice the
            # rule number; each rule starts with two bytes, the second being the minutes, then its name.
            rules = {}
            for number in range(1, 31):
                at = RULES + struct.unpack_from(">H", rom_bytes, RULES + 2 * number)[0]
                length = struct.unpack_from(">H", rom_bytes, at + 2)[0]
                if 2 < length < 30:
                    minutes = rom_bytes[at + 1]
                    rules[2 * number] = {"name": rom_bytes[at + 4:at + 2 + length].decode("latin-1").rstrip("\x00"),
                                         "min": minutes if minutes <= 10 else 0}
            match["rules"] = rules
            stats["home"] = [v[:sizes[0]] for v in stats["home"]]
            stats["away"] = [v[:sizes[1]] for v in stats["away"]]
            rom_bytes = rom_path.read_bytes()
            stats["x"] = "Checks" if rom_bytes[PIM_CODE:PIM_CODE + 4] == bytes.fromhex("4e714e71") else "PIM"
            match["stats"] = stats
            match["goals"] = find_goals(match, match["rosters"])
            if teams[home_id]["logo"]:
                match["logo"] = teams[home_id]["logo"]  # drawn at centre ice in the home palette
        # Players are drawn from this ROM's own sprites; build its library the first time it is seen.
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import extract_sprites
        rom = rom_path.read_bytes()
        match["rom"] = f"{zlib.crc32(rom):08x}"
        match["anims"] = animation_table(rom)
        if not extract_sprites.library_path(rom).exists():
            try:
                extract_sprites.build(rom)
            except ValueError as problem:
                print(f"no game sprites for {rom_path.name}: {problem}")
    else:
        print(f"ROM not found at {rom_path}; exporting without player names")

    # The recorded controller ($BEEF) is the local player's. With two people playing, whose is it? The team whose
    # controlled skater starts an action (pass, shot, check, poke, hook, dive...) within 350 ms of a press, clearly
    # more often than the other team's. In capture6_netplay_bos_stl (the user Boston, online): 222 against 102 of 617.
    if "pad" in match:
        answers = [0, 0]
        actions = {"0718", "078a", "07fc", "092e", "0c5e", "0b24", "1122", "02f4", "0366", "148e"}
        t, A, pad, ctrl = match["t"], match["anim"], match["pad"], match["ctrl"]
        for i in range(1, len(t)):
            if not pad[i] & 0x70 & ~pad[i - 1]:
                continue
            for team in (0, 1):
                ks = [k for k in range(team * 6, team * 6 + 6) if (ctrl[i] >> k) & 1]
                j = i
                while j < len(t) and t[j] - t[i] <= 350:
                    if any(A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] in actions
                           and A[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] != A[((j - 1) * 12 + k) * 4:((j - 1) * 12 + k) * 4 + 4] for k in ks):
                        answers[team] += 1
                        break
                    j += 1
        match["padTeam"] = 0 if answers[0] > 1.5 * answers[1] else 1 if answers[1] > 1.5 * answers[0] else -1
    # Shots for the shot map, credited where the game counted them (and to the scorer it named, when known).
    match["shotList"] = find_shots(match, match.get("goals"))
    match["turnovers"] = find_turnovers(match)
    match["failedOneTimers"] = find_failed_one_timers(match)
    match["passes"] = find_passes(match)
    match["faceoffs"] = find_faceoffs(match)
    match["icings"] = find_icings(match)
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
          f"puck held {held:.0%} of frames, buttons {'yes' if has_pad else 'no'}, {target.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
