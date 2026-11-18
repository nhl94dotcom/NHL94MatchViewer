"""A match file from the video reader (inverse.py's tracks and PuckTracker), for the converter's own event finders,
compared with the recorded match file event by event (2026-11-17, chunk 6 of the video reader).

The pseudo match keeps the recorded file's samples in the stretch (t, shots, stats and the goals) and replaces what
the reader sees (the clock, period and score from the score box where the reader's rows carry hud_read's reading):
- each track gets a record of its team: a goalie track (a frame goalies draw) record 5 / 11, skaters 0-4 / 6-10, a new
  track the free record whose last known spot is nearest; records with no live track keep their last spot;
- pos from the sprite point (X = sx - 128 + Hpos, Y = 112 - sy + Vpos), frame / mirror as read, anim and facing the
  most common for that frame in the other recorded games, roles fixed (5 3 4 2 1 0 as the recordings list them);
- the puck (X, Y, height) from PuckTracker, owner its carrier's record, puckV from its motion (speed x 4096 / 100);
- ctrl from the joypad stars (frames 390 / 391): each pad's skater the last track seen on its star, the pads empty;
- the owner steadied (gaps under SHORT samples filled) and the puck hidden (height -256, as the game) where the
  clock has stood still for STOPPED samples and the puck isn't seen.
Then export_match.analyse on both, the recorded slice's own event lists dropped first, and the events compared.

    build(match, vf, rows, maps) -> pseudo match;  compare(a, b) -> per event kind: matched / only recorded / only read
"""
import copy
import math

import numpy as np
from collections import Counter

ROLES = "534210"
SHORT = 8                   # samples (about 0.12 s): an owner gap shorter than this is filled
GOALIE_SHARE = 0.8          # a frame goalies draw this share of the time is a goalie's
MIN_SPELL = 2               # samples: a shorter possession with the puck loose either side is the puck passing a stick
FLICK = 24                  # samples (0.4 s real): the other team "having" the puck this briefly between two spells of
                            # one carrier is a misread scrum
BURST_GAIN = 0              # off: a burst seen in the skating (units a second gained over 6 samples); on the full period
                            # read it found 1 more check attempt and 6-9 false ones at 50-90 (sprite points too jumpy)
LUNGE, LUNGE_BACK = "0c5e", 4   # the burst's anim word (Genesis ACTIONS lunge) and how far a read one is moved back
Z_SCALE = (0.72, 0.8)       # game height from the read gap (rows): fitted on 264 airborne reads of BOS-CHI game 1
SHOT, SHOT_SPEED, SHOT_MOUTH = "092e", 99.0, 40  # off (99): over a full period it found no more shots, only false ones
SHOOTS, PASSES, PASS = {"07fc", "092e"}, {"0718", "078a"}, "0718"   # Genesis ACTIONS shoot / pass anims
FOLLOW = 24                  # samples after a release whose shot / pass frames are its follow-through
WIDE = 60                   # a release whose line crosses the goal line this far from the middle is a pass
RELEASE_LOOK = 90           # samples a release's outcome is looked for
V_WINDOW = 12               # video frames the puck velocity's slope is taken over
VMAX = 9.0                  # pixels a frame: about the fastest shot (a puck at 23,000 moves 5.6)
STOPPED = 90                # samples (about 1.4 s real) of an unchanged clock: a stoppage
MERGE = 150                 # samples (2.5 s real): stoppages this close, the clock unchanged between, are one
MIN_STOP = 60               # samples (1 s real): a shorter stoppage is a sliver of unseen puck, not a whistle
PER_SAMPLE = {"t": 1, "clock": 1, "period": 1, "score": 2, "shots": 2, "puck": 3, "puckV": 2, "pos": 24, "ctrl": 1,
              "owner": 1, "pad": 1, "pad2": 1, "facing": 12, "roster": 12, "role": 12, "frame": 36, "puckFrame": 3,
              "mirror": 12, "anim": 48, "lights": 1}
EVENT_LISTS = ("shotList", "turnovers", "failedOneTimers", "passes", "flips", "faceoffs", "icings", "zoneEntries", "hits",
               "injuries", "bumps", "bobbles", "netsOff", "checkAttempts", "cpuCheckAttempts", "checkPasses", "habits",
               "runaways", "steals", "fast", "posts", "delayed", "shotFlag", "foSpot")


def learn_maps(matches):
    """frame -> the most common anim word and facing, and the frames goalies draw, from recorded games."""
    anim, face, goalie = {}, {}, Counter()
    for m in matches:
        N = len(m["t"])
        for q in range(0, N, 2):
            for k in range(12):
                fr = int(m["frame"][(q * 12 + k) * 3:(q * 12 + k) * 3 + 3], 16)
                anim.setdefault(fr, Counter())[m["anim"][(q * 12 + k) * 4:(q * 12 + k) * 4 + 4]] += 1
                # facing by frame and mirror (key frame x 2 + mirror): the game draws left- and right-facing poses as
                # one frame, mirrored, so the frame alone had read a mirrored pose 90 degrees off (3 for 5): no checks
                face.setdefault(fr * 2 + int(m["mirror"][q * 12 + k] == "1"), Counter())[m["facing"][q * 12 + k]] += 1
                if m["role"][q * 12 + k] == "0":
                    goalie[fr] += 1
    # a goalie frame is one goalies draw (5+ times) and mostly they (80% of its uses): a goalie skating out of his crease
    # draws skaters' frames, which had made a carrier's skating frames "goalie" ones (game 2: a carrier in record 5)
    return dict(anim={f: c.most_common(1)[0][0] for f, c in anim.items()},
                facing={f: c.most_common(1)[0][0] for f, c in face.items()},
                goalie={f for f, c in goalie.items() if c >= 5 and c >= GOALIE_SHARE * sum(anim[f].values())})


def slice_match(m, q0, q1):
    """The samples q0..q1 of a match (per-sample arrays cut by their stride; the stats snapshots and the goals in it
    re-indexed; the event lists dropped)."""
    out = {k: v for k, v in m.items() if k not in PER_SAMPLE and k not in EVENT_LISTS and k not in ("stats", "goals")}
    N = len(m["t"])
    for k, w in PER_SAMPLE.items():
        if k in m and len(m[k]) == N * w:
            out[k] = m[k][q0 * w:q1 * w]
    st = m.get("stats")
    if isinstance(st, dict) and "f" in st:
        keep = [i for i, f in enumerate(st["f"]) if q0 <= f < q1]
        out["stats"] = {k: ([v[i] for i in keep] if isinstance(v, list) and len(v) == len(st["f"]) else v) for k, v in st.items()}
        out["stats"]["f"] = [st["f"][i] - q0 for i in keep]
    out["goals"] = [dict(g, f=g["f"] - q0) for g in m.get("goals", []) if q0 <= g["f"] < q1]
    for k, v in list(out.items()):                     # other lists of moments (penalties ...): those in the stretch
        if isinstance(v, list) and v and isinstance(v[0], dict) and "f" in v[0]:
            out[k] = [dict(e, f=e["f"] - q0) for e in v if q0 <= e["f"] < q1]
    return out


def build(truth, vf, rows, maps, q0, q1):
    """The pseudo match over samples q0..q1: each sample takes the read frame nearest its video frame."""
    by_fi = {r["fi"]: r for r in rows}
    m = slice_match(truth, q0, q1)
    n = q1 - q0
    pos = list(m["pos"])
    frame, mirror, anim, facing = list(m["frame"]), list(m["mirror"]), list(m["anim"]), list(m["facing"])
    role = ROLES * 2 * n
    puck, puckV, owner, ctrl = list(m["puck"]), [0] * (2 * n), [-1] * n, [0] * n
    slot_of, last, votes = {}, {k: (pos[2 * k], pos[2 * k + 1]) for k in range(12)}, {}
    pad_track = {}
    prev_p, hist = None, []
    for i in range(n):
        q = q0 + i
        r = by_fi.get(int(round(vf[q]))) if vf[q] == vf[q] else None
        if r is None or r.get("cam") is None:
            if i:
                for arr, w in ((pos, 24), (frame, 36), (mirror, 12), (anim, 48), (facing, 12), (puck, 3)):
                    arr[i * w:(i + 1) * w] = arr[(i - 1) * w:i * w]
                owner[i] = owner[i - 1]
            continue
        hpos, vpos = r["cam"]
        live = {}
        for tid, team, fr, mir, sy, sx in r["tracks"]:
            X, Y = sx - 128 + hpos, 112 - sy + vpos
            if tid not in slot_of:
                base = 6 * team
                taken = set(slot_of[t] for t in live) | {slot_of[t] for t in slot_of if t in {x[0] for x in r["tracks"]}}
                if fr in maps["goalie"]:
                    cands = [base + 5]
                else:
                    cands = [base + k for k in range(5)]
                free = [k for k in cands if k not in taken] or cands
                slot_of[tid] = min(free, key=lambda k: abs(last[k][0] - X) + abs(last[k][1] - Y))
            # a track's record follows what it draws: one first seen in a goalie-like frame that skates (or a goalie
            # first seen in a skater's frame) moves once 10 of its frames say so, swapping with the record's holder
            # (the full period's carrier had sat in the away goalie's record, so no check on him was an attempt)
            v = votes.setdefault(tid, [0, 0])
            v[0] += fr in maps["goalie"]
            v[1] += 1
            k = slot_of[tid]
            if v[1] >= 10 and ((k % 6 == 5 and v[0] < 0.3 * v[1]) or (k % 6 != 5 and v[0] > 0.7 * v[1])):
                base = 6 * team
                want = [base + 5] if k % 6 != 5 else sorted(range(base, base + 5), key=lambda j: abs(last[j][0] - X) + abs(last[j][1] - Y))
                holders = {slot_of[t]: t for t in slot_of if t != tid}
                to = next((j for j in want if j not in holders or votes.get(holders[j], [0, 0])[1] < 10
                           or (j % 6 == 5) != (votes[holders[j]][0] > 0.5 * votes[holders[j]][1])), None)
                if to is not None:
                    if to in holders:
                        slot_of[holders[to]] = k
                    slot_of[tid] = k = to
            if k in live.values():
                continue
            live[tid] = k
            last[k] = (X, Y)
            frame[(i * 12 + k) * 3:(i * 12 + k) * 3 + 3] = f"{fr:03x}"
            mirror[i * 12 + k] = str(mir)
            anim[(i * 12 + k) * 4:(i * 12 + k) * 4 + 4] = maps["anim"].get(fr, "0000")
            facing[i * 12 + k] = maps["facing"].get(fr * 2 + int(mir), maps["facing"].get(fr * 2 + 1 - int(mir), "0"))
        for k in range(12):
            pos[(i * 12 + k) * 2:(i * 12 + k) * 2 + 2] = [float(last[k][0]), float(last[k][1])]
        if r["puck"] is not None:
            sy, sx, z, how = r["puck"]
            zz = Z_SCALE[0] * z + Z_SCALE[1] if z > 0 else 0.0   # the shadow gap in screen rows, as game height
            P = [float(sx - 128 + hpos), float(112 - sy + vpos), round(zz, 1)]
            puck[3 * i:3 * i + 3] = P
            if not hist or hist[-1][0] != r["fi"]:      # one point a video frame (samples can share one)
                hist.append((r["fi"], P[0], P[1]))
            hist[:] = [h for h in hist if r["fi"] - h[0] <= V_WINDOW]
            if len(hist) >= 2:                          # the slope over the last few read frames, capped at VMAX
                fr_ = np.array([h[0] for h in hist], float)
                vx = float(np.polyfit(fr_, [h[1] for h in hist], 1)[0])
                vy = float(np.polyfit(fr_, [h[2] for h in hist], 1)[0])
                sp = (vx * vx + vy * vy) ** 0.5
                if sp > VMAX:
                    vx, vy = vx * VMAX / sp, vy * VMAX / sp
                puckV[2 * i:2 * i + 2] = [round(vx * 4096 / 100), round(vy * 4096 / 100)]
            prev_p = (P, r["fi"])
        elif i:
            puck[3 * i:3 * i + 3] = puck[3 * (i - 1):3 * i]
        if r.get("carrier") is not None and r["carrier"] in slot_of and (r["carrier"] in live or r["puck"] and r["puck"][3] == "out of view"):
            owner[i] = slot_of[r["carrier"]]
        for tid_s, fr_s in r.get("stars", {}).items():          # each pad's skater: the last one seen on its star
            for star in (390, 391):
                if star in fr_s and int(tid_s) in slot_of:
                    pad_track[star] = int(tid_s)
        ctrl[i] = sum(1 << slot_of[tid] for tid in pad_track.values() if tid in slot_of)
    # the clock, period and score from the score box where the reader read it (hud_read), carried forward over frames
    # it couldn't read; the recorded values stay only where no read frame has come yet
    clock, period, score = list(m["clock"]), list(m["period"]), list(m["score"])
    got = None
    for i in range(n):
        r = by_fi.get(int(round(vf[q0 + i]))) if vf[q0 + i] == vf[q0 + i] else None
        h = (r or {}).get("hud")
        if h:
            got = dict(clock=h["clock"] if h["clock"] is not None else (got or {}).get("clock"),
                       period=h["period"] if h["period"] is not None else (got or {}).get("period"),
                       home=h["home"] if h["home"] is not None else (got or {}).get("home"),
                       vis=h["vis"] if h["vis"] is not None else (got or {}).get("vis"))
        if got:
            if got["clock"] is not None:
                clock[i] = got["clock"]
            if got["period"] is not None:
                period[i] = got["period"]
            if got["home"] is not None and got["vis"] is not None:
                score[2 * i:2 * i + 2] = [got["home"], got["vis"]]
    m.update(clock=clock, period=period, score=score)
    # a burst backdated: its own frames (41, 46 ... 76) show a few samples into it, by when the pad has often switched
    # to another skater, so a read burst starts LUNGE_BACK samples earlier
    aw = lambda i, k: "".join(anim[(i * 12 + k) * 4:(i * 12 + k) * 4 + 4])          # noqa: E731
    starts = [(i, k) for k in range(12) for i in range(1, n) if aw(i, k) == LUNGE and aw(i - 1, k) != LUNGE]
    for i, k in starts:
        for j in range(max(0, i - LUNGE_BACK), i):
            anim[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] = LUNGE
    # the owner steadied (the reader's carrier drops out for a frame or two behind a sprite)
    i = 1
    while i < n:                                     # any interruption (other owners, gaps, mixed) under SHORT samples
        if owner[i] != owner[i - 1] and owner[i - 1] >= 0:   # that ends with the same owner is his
            back = next((j for j in range(i, min(n, i + SHORT)) if owner[j] == owner[i - 1]), None)
            if back is not None:
                owner[i:back] = [owner[i - 1]] * (back - i)
                i = back
        i += 1
    # a puck passing a stick: a spell of possession under MIN_SPELL samples with the puck loose before and after is
    # loose (game 2's passes in flight had read an opponent "having" it for one sample: a pick-off and a takeaway)
    i = 1
    while i < n:
        if owner[i] >= 0 and owner[i - 1] < 0:
            j = i
            while j < n and owner[j] == owner[i]:
                j += 1
            if j - i < MIN_SPELL and j < n and owner[j] < 0:
                owner[i:j] = [-1] * (j - i)
            i = j
        else:
            i += 1
    # a scrum read as the puck changing hands back and forth: a spell of another team's player under FLICK samples
    # between two of the same carrier is his (the full period's turnovers had come in threes a few samples apart)
    # (loose samples on either side of the other team's spell allowed, up to FLICK each)
    changed = True
    while changed and FLICK:
        changed = False
        spells, i = [], 0                                     # [start, end, owner] of each owned stretch
        while i < n:
            if owner[i] >= 0:
                j = i
                while j < n and owner[j] == owner[i]:
                    j += 1
                spells.append([i, j, owner[i]])
                i = j
            else:
                i += 1
        for (a0, a1, pa), (b0, b1, pb), (c0, c1, pc) in zip(spells, spells[1:], spells[2:]):
            if (pa == pc and (pb < 6) != (pa < 6) and b1 - b0 < FLICK and b0 - a1 <= FLICK and c0 - b1 <= FLICK):
                owner[a1:c0] = [pa] * (c0 - a1)
                changed = True
                break
    # bursts seen only in the skating: a burst's first frames are skating frames (its own frames come later or not at
    # all), so where a person's skater, the other team carrying within 70 of him, gains BURST_GAIN units a second of
    # speed over the next 6 samples against the 6 before, with no read burst within 8 samples, a burst starts there
    # (on the recorded positions of games 3-4, at 70: 71% of the person's burst starts found, 81% of those flagged real;
    # on the video's read positions it added 1 attempt for 6-9 false ones, so it is off)
    if BURST_GAIN:
        t_ = m["t"]
        P_ = lambda i, k: (pos[(i * 12 + k) * 2], pos[(i * 12 + k) * 2 + 1])          # noqa: E731
        last_flag = {}
        for i in range(6, n - 6):
            o = owner[i]
            if o < 0 or puck[3 * i + 2] < -100:
                continue
            team = 1 - o // 6
            k = next((j for j in range(team * 6, team * 6 + 6) if ctrl[i] >> j & 1 and role[i * 12 + j] in "12345"), None)
            if k is None or math.dist(P_(i, k), P_(i, o)) > 70:
                continue
            dt, dt0 = (t_[i + 6] - t_[i]) / 1000, (t_[i] - t_[i - 6]) / 1000
            if not (0 < dt < 0.2 and 0 < dt0 < 0.2):
                continue
            gain = math.dist(P_(i + 6, k), P_(i, k)) / dt - math.dist(P_(i, k), P_(i - 6, k)) / dt0
            if gain < BURST_GAIN or i - last_flag.get(k, -99) <= 12:
                continue
            last_flag[k] = i
            if any(aw(j, k) == LUNGE for j in range(max(0, i - 8), min(n, i + 9))):
                continue
            for j in range(i, min(n, i + 6)):
                anim[(j * 12 + k) * 4:(j * 12 + k) * 4 + 4] = LUNGE
    # shots: a frame doesn't tell a wind-up from its release, nor a shot from a pass (they share frames), so where the
    # read carrier loses the puck and it leaves fast (SHOT_SPEED pixels a frame within 6 samples) toward the net his
    # team attacks (home up in periods 1 and 3), from his attacking half, its line through the goal mouth, his last
    # samples are given the shot's anim
    period_ = m["period"]
    for i in range(2, n):
        k = owner[i - 1]
        if k < 0 or owner[i] == k:
            continue
        up = (k < 6) == (period_[i] % 2 == 0)
        for j in range(i, min(n, i + 6)):
            vx, vy = puckV[2 * j] * 100 / 4096, puckV[2 * j + 1] * 100 / 4096
            px, py = puck[3 * j], puck[3 * j + 1]
            gy = 264 if up else -264
            aimed = vy != 0 and (gy - py) / vy > 0 and abs(px + vx * (gy - py) / vy) <= SHOT_MOUTH
            if (vx * vx + vy * vy) ** 0.5 >= SHOT_SPEED and aimed and (py > 0) == up:
                for jj in range(max(0, i - 3), i + 1):
                    anim[(jj * 12 + k) * 4:(jj * 12 + k) * 4 + 4] = SHOT
                break
    # releases judged by where the puck went (a frame doesn't say pass or shot: they share frames): the next skater to
    # have it a teammate -> a pass (a shot anim at the release made the pass anim); the puck at the goal mouth the
    # team attacks, or the other goalie's, first -> a shot (a pass anim made the shot anim)
    for i in range(1, n):
        k = owner[i - 1]
        if k < 0 or owner[i] == k:
            continue
        up = (k < 6) == (period_[i] % 2 == 0)
        gy = 264 if up else -264
        verdict = None
        for j in range(i, min(n, i + RELEASE_LOOK)):
            o = owner[j]
            if o >= 0 and o != k:
                verdict = "pass" if (o < 6) == (k < 6) else ("shot" if o % 6 == 5 else None)
                break
            # a one-timer: the loose puck turns hard beside a teammate (he never has it), so the release was his pass
            if j >= i + 4 and j + 4 < n:
                ax, ay = puck[3 * j] - puck[3 * (j - 4)], puck[3 * j + 1] - puck[3 * (j - 4) + 1]
                bx, by_ = puck[3 * (j + 4)] - puck[3 * j], puck[3 * (j + 4) + 1] - puck[3 * j + 1]
                na, nb = math.hypot(ax, ay), math.hypot(bx, by_)
                if na > 4 and nb > 4 and (ax * bx + ay * by_) / (na * nb) < 0.5 and any(
                        math.dist((pos[(j * 12 + t) * 2], pos[(j * 12 + t) * 2 + 1]), (puck[3 * j], puck[3 * j + 1])) <= 25
                        for t in range(6 * (k // 6), 6 * (k // 6) + 6) if t != k):
                    verdict = "pass"
                    break
            if abs(puck[3 * j]) <= 30 and abs(puck[3 * j + 1] - gy) <= 14:
                verdict = "shot"
                break
        if verdict is None:                          # nobody had it and it never reached the mouth: its line decides
            j2 = min(n - 1, i + 10)
            dx, dy = puck[3 * j2] - puck[3 * i], puck[3 * j2 + 1] - puck[3 * i + 1]
            if dy != 0 and (gy - puck[3 * i + 1]) / dy > 0:
                cross = puck[3 * i] + dx * (gy - puck[3 * i + 1]) / dy
                verdict = "pass" if abs(cross) > WIDE else None
            elif abs(dx) + abs(dy) > 8:
                verdict = "pass"                       # away from the net he attacks
        if verdict is None:
            continue
        # the release and its follow-through (its frames, shared by shots and passes, read as a pass by default: a
        # shot's follow-through had made a second release, a "pass", on game 2's goals)
        for jj in range(max(0, i - 4), min(n, i + FOLLOW)):
            a = "".join(anim[(jj * 12 + k) * 4:(jj * 12 + k) * 4 + 4])
            if jj > i and a not in SHOOTS and a not in PASSES:
                break
            if verdict == "pass" and a in SHOOTS:
                anim[(jj * 12 + k) * 4:(jj * 12 + k) * 4 + 4] = PASS
            elif verdict == "shot" and a in PASSES:
                anim[(jj * 12 + k) * 4:(jj * 12 + k) * 4 + 4] = SHOT
    # the puck hidden at a stoppage, as the game hides it: the clock (the score box's) unchanged for STOPPED samples and
    # the puck not seen
    clock = list(m["clock"])
    # a misread of the score box's clock for a sample or two (89, 71, 89) is dropped: the real clock steps down by one
    # a game second (about 24 samples) and never comes back to a value it has left within 12 samples
    for i in range(1, n):
        if clock[i] != clock[i - 1] and any(clock[j] == clock[i - 1] for j in range(i + 1, min(n, i + 13))):
            clock[i] = clock[i - 1]
    m["clock"] = clock
    still = 0
    for i in range(n):
        still = still + 1 if i and clock[i] == clock[i - 1] else 0
        r = by_fi.get(int(round(vf[q0 + i]))) if vf[q0 + i] == vf[q0 + i] else None
        seen = r is not None and r.get("puck") is not None and r["puck"][3] in ("seen", "seen at a stick")
        if still >= STOPPED and not seen:
            puck[3 * i + 2] = -256.0
            owner[i] = -1
    # One whistle, one stoppage (each becomes a faceoff in the converter): stoppages a short sighting apart with the
    # clock unchanged are one (the game hides the puck a few seconds after the clock stops, and a stray read in
    # between had split it); one shorter than MIN_STOP samples is a sliver, not a whistle; none at 0:00 (the period
    # is over: the recording has no faceoff there). Full first period of BOS-CHI game 1: 6 read for 3 recorded.
    runs, i = [], 0
    while i < n:
        if puck[3 * i + 2] < -100:
            j = i
            while j < n and puck[3 * j + 2] < -100:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] <= MERGE and all(clock[x] == clock[a] for x in range(merged[-1][1] - 1, a + 1)):
            merged[-1][1] = b
        else:
            merged.append([a, b])
    for a, b in runs:
        for x in range(a, b):
            puck[3 * x + 2] = max(puck[3 * x + 2], 0.0) if puck[3 * x + 2] < -100 else puck[3 * x + 2]
    for a, b in merged:
        if b - a < MIN_STOP or clock[a] == 0:
            continue
        for x in range(a, b):
            puck[3 * x + 2] = -256.0
            owner[x] = -1
    m.update(pos=pos, frame="".join(frame), mirror="".join(mirror), anim="".join(anim), facing="".join(facing),
             role=role, puck=puck, puckV=puckV, owner=owner, ctrl=ctrl)
    if "pad" in m:
        m["pad"] = [0] * n
    if "pad2" in m:
        m["pad2"] = [0] * n
    return m


def analyse(m, rom_path):
    import types
    import export_match
    from systems import genesis
    m = copy.deepcopy(m)
    m.pop("pad", None)
    m.pop("pad2", None)
    export_match.analyse(m, genesis, types.SimpleNamespace(folder="."), rom_path)
    return m


def compare(a, b, kinds=("shotList", "passes", "turnovers", "hits", "faceoffs", "zoneEntries", "checkAttempts", "bobbles"),
            ms=600):
    """Events of a (recorded) against b (read): matched when the same kind and team within `ms` milliseconds."""
    out = {}
    for kind in kinds:
        A, B = a.get(kind) or [], b.get(kind) or []
        used, hit = set(), 0
        for ev in A:
            ta = a["t"][ev["f"]]
            best = None
            for j, ev2 in enumerate(B):
                if j in used or ev2.get("team") != ev.get("team"):
                    continue
                d = abs(b["t"][ev2["f"]] - ta)
                if d <= ms and (best is None or d < best[0]):
                    best = (d, j)
            if best:
                used.add(best[1])
                hit += 1
        out[kind] = dict(recorded=len(A), read=len(B), matched=hit)
    oa = [o >= 0 for o in a["owner"]]
    ob = [o >= 0 for o in b["owner"]]
    ta = [(o // 6) if o >= 0 else -1 for o in a["owner"]]
    tb = [(o // 6) if o >= 0 else -1 for o in b["owner"]]
    both = [i for i in range(len(oa)) if oa[i]]
    out["possession"] = dict(samples_carried=len(both), carried_read_as_carried=sum(ob[i] for i in both),
                             team_right=sum(ta[i] == tb[i] for i in both))
    return out
