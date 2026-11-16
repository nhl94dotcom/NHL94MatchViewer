"""NOSE4Web's organ resume after a pause, played (Genesis, 2026-11-16, 74cb94b: Pausemode's jsr p_turnoff ($7D0C) and its
last move.w Vcount,OldVcount ($7DC6) hooked: the song's track slot (fm_track_slots $FFD3D4, 8 x 6 bytes: the stream
pointer, -1 free, and a delay) and its 8 voice rows (fm_voice_usage_table $FFD1A4, 8 bytes every $40) saved on the
stack through the pause and put back after).

From one moment per ROM with a song playing (S: Boston (1) at home, the clock run out, the next period's song 200
frames in), the same presses on the original and the build, each case against the same moment played on unpaused
(the reference):
  resume    START, 150 frames in the menu, out again
  stats     START, Game Stats (item 4), B, out
  replay    START, Instant Replay (item 1), 300 frames of it, START, out
  delayed   a home goal (its song chosen with songdelay $FFDECC = 120), START 40 frames after it, out
  nosong    an away goal (no song), START 60 frames into the stoppage, out
  many      from S, 40 pauses (Resume, Game Stats or Instant Replay in turn) 30-200 frames apart, then 1,800 frames
Per case: the song's slot and voice rows at the pause and just after it, the stream pointer's changes for 900 frames
after (against the reference's from the same game moment), the sound (the core's audio) as 0.1 s (real) spectra
correlated with the reference's, the sound during the pause, sound-effect starts (slot pointers below song $30's
stream) and the crowd ($FFB8A2) against the reference's, and for many the stack's depth (the lowest word changed in
$FFE800-$FFFFF6 over 300 frames of play, against the reference's) and the clock's pace.

python gen_organ_resume_check.py OUT ROM [ROM ...]"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

import gen_1on1_edit_lines as G
import gen_songs_check as SC
from gen_midi_song_check import capture
import lowload

SLOTS, VOICES, SONGDELAY, CROWD, ITEM, SCREEN, SFLAGS = 0xD3D4, 0xD1A4, 0xDECC, 0xB8A2, 0xCF20, 0xFFF7, 0xC2EC
TABLE = 0x2C648
SPF = 735 * 2                                    # int16 values a frame (44,100 Hz stereo, 60 frames a second)


def slots(e):
    return [((e.w(SLOTS + 6 * k) << 16 | e.w(SLOTS + 6 * k + 2)) & 0xFFFFFFFF, e.w(SLOTS + 6 * k + 4)) for k in range(8)]


def voices(e, idx):
    return [bytes(e.b(VOICES + idx * 8 + j * 0x40 + i) for i in range(8)).hex() for j in range(8)]


class Case:
    def __init__(self, rom, out):
        self.rom = rom
        data = Path(rom).read_bytes()
        self.song30 = struct.unpack_from(">I", data, TABLE + 4 * 0x30)[0]
        self.r = G.Run(rom, out)
        self.e = self.r.e
        self.buf = capture(self.e)

    def song_slot(self):
        for k, (p, _) in enumerate(slots(self.e)):
            if not p & 0x80000000 and self.song30 <= p < 0x400000:
                return k
        return None

    def frame(self, n=1, hold=()):
        trace = []
        for _ in range(n):
            self.e.run(1, hold=list(hold))
            trace.append(dict(sl=slots(self.e), crowd=self.e.w(CROWD), clock=self.e.w(SC.CLOCK),
                              screen=self.e.b(SCREEN), pz=self.e.w(SFLAGS) & 0x100, a=len(self.buf)))
        return trace

    def press(self, b, after):
        return self.frame(4, [b]) + self.frame(after)

    def paused(self):
        return bool(self.e.w(SFLAGS) & 0x100)                # sfpz (bit 0 of the byte at $C2EC): the pause

    def pause_menu(self, kind, wait=150):
        t = self.press("START", 60)
        if kind == "stats":
            for _ in range(20):
                if self.e.w(ITEM) == 4:
                    break
                t += self.press("DOWN", 20)
            t += self.press("C", 240) + self.press("B", 120)
        elif kind == "replay":
            for _ in range(20):
                if self.e.w(ITEM) == 1:
                    break
                t += self.press("DOWN", 20)
            t += self.press("C", 300) + self.press("START", 200)
        else:
            t += self.frame(wait)
        for _ in range(6):                       # out of the menu: Resume Game (item 0), C
            if self.e.w(ITEM) == 0:
                break
            t += self.press("UP", 20)
        t += self.press("C", 30)
        for _ in range(4):
            if not self.paused():
                break
            t += self.press("START", 60)
        return t


def to_song(c):
    """S: a song playing in live play. Boston at home, the clock run out, C through the intermission until the next
    period's clock runs; if its song is still on, S is 60 frames later; else a home goal's song 150 frames in (a
    stoppage)."""
    r, e = c.r, c.e
    r.to_play()
    r.step(120)
    e.setw(SC.HOMETEAM, 1)
    p0 = e.w(SC.PERIOD)
    e.setw(SC.CLOCK, 2)
    last = None
    for f in range(9000):
        e.setw(SC.HOMETEAM, 1)
        live = e.w(SC.PERIOD) > p0 and last is not None and 0 < e.w(SC.CLOCK) < last and not c.paused()
        if live:
            break
        last = e.w(SC.CLOCK)
        if f % 60 == 0:
            r.step(4, hold=["C"])
        else:
            r.step(1)
    else:
        return None, "no next period"
    c.frame(60)
    if c.song_slot() is not None:
        return e.serialize(), "live play, the next period's song"
    if not goal(c, True):
        return None, "no song"
    for f in range(400):
        c.frame(1)
        if c.song_slot() is not None:
            c.frame(150)
            return e.serialize(), "a home goal's song (a stoppage)"
    return None, "no song after the goal"


def goal(c, home):
    """The puck sent into the net Home (home=True) or Away attacks; True if that side scored."""
    e = c.e
    st = e.serialize()
    for y, vy in ((258, 6000), (-258, -6000)):
        e.unserialize(st)
        h0, a0 = e.w(SC.HSCORE), e.w(SC.ASCORE)
        e.setw(SC.PUCK, 3); e.setw(SC.PUCK + 0x14, y); e.setw(SC.PUCK + 0x18, 0); e.setw(SC.PUCK + 0x28, 0)
        e.setw(SC.PUCK + 0x2A, vy); e.setb(SC.PUCK + 0x60, 0xFF); e.setw(SC.PUCK + 0x5E, 0)
        tr = c.frame(40)
        if (e.w(SC.HSCORE) != h0) if home else (e.w(SC.ASCORE) != a0):
            return tr
    e.unserialize(st)
    return None


def spectra(c, a0, n):
    """0.1 s (real) log spectra from the audio buffer index a0, n windows."""
    x = np.asarray(c.buf[a0:a0 + n * 8820], dtype=np.float32)
    if len(x) < n * 8820:
        return None
    x = x.reshape(n, 4410, 2).mean(2)
    return np.log1p(np.abs(np.fft.rfft(x * np.hanning(4410), axis=1))[:, 20:1200])


def rms(c, a0, a1):
    x = np.asarray(c.buf[a0:a1], dtype=np.float32)
    return round(float(np.sqrt((x * x).mean())), 1) if len(x) else None


def is_song(c, p):
    return not p & 0x80000000 and c.song30 <= p < 0x400000


def song_ptrs(c, trace, k):
    """(frame, pointer) each time slot k's stream pointer changes while a song plays in it."""
    out, last = [], None
    for i, t in enumerate(trace):
        p = t["sl"][k][0]
        if is_song(c, p) and p != last:
            out.append((i, p))
        last = p
    return out


def song_starts(c, trace):
    """(frame, slot, pointer) where a song appears in a slot that had none."""
    out, prev = [], [False] * 8
    for i, t in enumerate(trace):
        now = [is_song(c, p) for p, _ in t["sl"]]
        out += [(i, k, hex(t["sl"][k][0])) for k in range(8) if now[k] and not prev[k]]
        prev = now
    return out


def sfx(c, trace):
    out, prev = [], [None] * 8
    for i, t in enumerate(trace):
        for k, (p, _) in enumerate(t["sl"]):
            if p != prev[k] and not p & 0x80000000 and not is_song(c, p) and (prev[k] is None or prev[k] & 0x80000000):
                out.append((i, hex(p)))
            prev[k] = p
    return out


def corr(c, a0, b0, n=100):
    """0.1 s spectra correlated, averaged by 2 s (real)."""
    sa, sb = spectra(c, a0, n), spectra(c, b0, n)
    if sa is None or sb is None:
        return None
    cc = [float(np.corrcoef(sa[i], sb[i])[0, 1]) for i in range(n)]
    return [round(float(np.nanmean(cc[i:i + 20])), 3) for i in range(0, n, 20)]


def song_case(c, S, kind):
    """S played on (the reference) and paused (kind), from the same moment."""
    e = c.e
    e.unserialize(S)
    ref = c.frame(1800)
    e.unserialize(S)
    k = c.song_slot()
    pv = voices(e, 7 - k) if k is not None else None
    tr = c.pause_menu(kind)
    ri = resume_index(tr)
    row = dict(kind=kind, slot_at_pause=k)
    if ri is None:
        row["res"] = "never back in play"
        return row
    p_at = tr[0]["sl"][k][0]
    back = None
    for f in range(240):                          # until a song is in a slot again (the restore, after the fade)
        tr += c.frame(1)
        kk = c.song_slot()
        if kk is not None:
            back = (len(tr) - 1, kk, slots(e)[kk], voices(e, 7 - kk))
            break
    tr += c.frame(1500)
    row.update(pointer_at_pause=hex(p_at), pause_frames=ri,
               song_back_frames_after_pause_flag=None if back is None else back[0] - ri)
    rp = song_ptrs(c, ref, k)
    row["sfx_ref"] = sfx(c, ref[:900])[:8]
    if back is None:
        row.update(res="no song after the pause", song_starts_after=song_starts(c, tr[ri:ri + 900])[:3],
                   sfx_after=sfx(c, tr[ri:ri + 900])[:8],
                   sound_corr=corr(c, ref[0]["a"], tr[ri]["a"]))
        return row
    bi, kk, (bp, bd), bv = back
    cp = [(i, q) for i, q in song_ptrs(c, tr, kk) if i >= bi]
    j = next((j for j, (_, q) in enumerate(rp) if q == cp[0][1]), None) if cp else None
    row.update(res="song back", slot_after=kk, pointer_after=hex(bp), delay_after=bd, voices_same=bv == pv)
    if j is not None:
        n = min(60, len(rp) - j, len(cp))
        same = sum(1 for t in range(n) if rp[j + t][1] == cp[t][1])
        timed = sum(1 for t in range(1, n) if rp[j + t][0] - rp[j + 1][0] == cp[t][0] - cp[1][0])
        row.update(resumed_at_ref_change_no=j, next_pointers_same=f"{same} of {n}",
                   timing_from_the_second_same=f"{timed} of {n - 1}")
        row["sound_corr"] = corr(c, ref[rp[j][0]]["a"], tr[cp[0][0]]["a"])
    row["rms_during_pause"] = rms(c, tr[10]["a"], tr[ri - 5]["a"])
    row["rms_ref"] = rms(c, ref[0]["a"], ref[600]["a"])
    row["rms_after"] = rms(c, tr[bi]["a"], tr[bi + 600]["a"])
    row["sfx_after"] = sfx(c, tr[bi:bi + 900])[:8]
    row["crowd_ref"] = [ref[i]["crowd"] for i in range(0, 900, 150)]
    row["crowd_after"] = [tr[bi + i]["crowd"] for i in range(0, 900, 150)]
    return row


def resume_index(tr):
    for i in range(8, len(tr)):
        if not tr[i]["pz"] and tr[i - 1]["pz"]:
            return i
    return None


def depth(c, frames=300):
    e = c.e
    lo, hi = 0xE800, 0xFFF6
    before = [e.w(a) for a in range(lo, hi, 2)]
    tr = c.frame(frames)
    after = [e.w(a) for a in range(lo, hi, 2)]
    ch = [lo + 2 * i for i, (x, y) in enumerate(zip(before, after)) if x != y]
    return (hex(0xFF0000 + min(ch)) if ch else None), tr


def stoppage_case(c, S, home, wait):
    """A goal (home: its song after songdelay; away: none), START `wait` frames later; song starts against the
    reference's."""
    e = c.e
    e.unserialize(S)
    for _ in range(900):
        if c.song_slot() is None:
            break
        c.frame(1)
    g = None
    for _ in range(6):
        g = goal(c, home)
        if g:
            break
        c.frame(120)
    if not g:
        return dict(res="no goal")
    c.frame(wait)
    G0 = e.serialize()
    info = dict(songdelay=e.w(SONGDELAY), song_slot=c.song_slot(), clock_stopped=bool(e.w(0xC2EA) & 0x0100))
    ref = c.frame(1800)
    e.unserialize(G0)
    tr = c.pause_menu("resume")
    ri = resume_index(tr)
    tr += c.frame(1800)
    if ri is None:
        return dict(res="never back in play", at_pause=info)
    return dict(res="ok", at_pause=info, pause_frames=ri,
                song_starts_ref=song_starts(c, ref[:1500])[:3],
                song_starts_after_pause_flag=song_starts(c, tr[ri:ri + 1500])[:3],
                sfx_ref=sfx(c, ref[:900])[:6], sfx_after=sfx(c, tr[ri:ri + 900])[:6],
                sound_corr=corr(c, ref[0]["a"], tr[ri]["a"]))


def run(rom, out, res):
    c = Case(rom, out)
    e = c.e
    S, how = to_song(c)
    name = Path(rom).stem
    print(name, "the song moment:", how, flush=True)
    if S is None:
        return
    for kind in ("resume", "stats", "replay"):
        row = song_case(c, S, kind)
        row["rom"] = name
        res.append(row)
        print(json.dumps(row), flush=True)
        lowload.breathe()
    for kind, home, wait in (("delayed", True, 40), ("nosong", False, 60)):
        row = stoppage_case(c, S, home, wait)
        row.update(rom=name, kind=kind)
        res.append(row)
        print(json.dumps(row), flush=True)
        lowload.breathe()
    e.unserialize(S)
    d_ref, _ = depth(c)
    e.unserialize(S)
    rng = np.random.default_rng(3)
    kinds = ("resume", "stats", "replay")
    stuck = 0
    for i in range(40):
        c.frame(int(rng.integers(30, 200)))
        if e.w(SC.CLOCK) < 30:                       # clear of the period's end (its menus)
            e.setw(SC.CLOCK, 500)
        c.pause_menu(kinds[i % 3], wait=int(rng.integers(20, 120)))
        stuck += c.paused()
        if i % 5 == 4:
            lowload.breathe()
    d_many, _ = depth(c)
    tail = c.frame(1800)
    ticks = sum(1 for a, b in zip(tail, tail[1:]) if a["clock"] != b["clock"])
    row = dict(rom=name, kind="many", depth_ref=d_ref, depth_after_40=d_many, left_paused=stuck,
               clock_ticks_in_1800=ticks, song_starts_in_tail=song_starts(c, tail)[:4],
               slots_in_use=[k for k, (p, _) in enumerate(slots(e)) if not p & 0x80000000])
    res.append(row)
    print(json.dumps(row), flush=True)


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    res = []
    for rom in sys.argv[2:]:
        run(rom, out, res)
    (out / "organ_resume.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
