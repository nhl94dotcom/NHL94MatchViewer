"""NHL '95 (Genesis): NOSE4Web's organ resume after a pause, played (2026-11-16, b1d6bee). Pausemode's btst #sfpz at
$7E38C saves the playing song's sequencer slot (the slot whose SndSeqId is PlayingSong $FFCFD8, $32-$55: SndSeqPtr,
SndSeqPos, Wait, Tempo, Frac, State) at $FFF800 (22 bytes: the slot word, -1 none, then the id and the fields) when the
pause is a player's and sflags9 bit 5 is clear; the move.w Vcount,OldVcount at $7E4BC, after the driver reload and the
fade-in, puts it back (its own slot or the first free one) after sending the Z80 the slot's reset and the song's $Bx
(not $75), $Cx and $Ex events up to the kept position.

From a live state per ROM (gen95_assist_check's: STATE), the same presses on the original and the build:
  song cases: a home goal (its song, $47 on retail, starts about 220 frames later and plays into live play); S = the
    song playing with the clock running. resume (START, C on Resume Game), stats (STATS tab, Game Stats, B, back to
    OPTIONS, Resume), replay (Instant Replay, START out of it, Resume); and stoppage (the same pause 300 frames after
    the goal, the clock stopped). Each against S played on unpaused: the saved block, the slot after the restore,
    the song's position (SndSeqPos) changes after it against the reference's from the same position, the sound (the
    core's audio, 0.1 s spectra correlated, aligned on that position) and its loudness.
  untouched: bit5 (sflags9 bit 5 set before the pause), intermission (the clock run out, START / C through the
    intermission screens), timeout (no pad on either team, the pause left alone 2,100 frames: Pausemode's $708-frame
    no-pad exit), abort (Abort Game, then START into a new game and 1,500 frames of it): $FFF800's word, the song
    slots' ids and PlayingSong frame by frame, the original against the build.
  tour: every pause tab's items opened in turn (C, then B), Instant Replay too: every change in $FFF800-$FFF815.

python gen95_organ_resume_check.py OUT ORIGINAL BUILD STATE"""
import json
import sys
from pathlib import Path

import numpy as np

from emu import Emu
from gen_midi_song_check import capture
import lowload

PUCK = 0xAC62 + 14 * 0x80
HMGOALS, CLOCK, GSP, GMODE, SFLAGS, SFLAGS9 = 0xC294, 0xC022, 0xC020, 0xBEF0, 0xBEF2, 0xBF06
PLAYING, PTR, POS, SID, WAIT, TEMPO, FRAC, STATE = 0xCFD8, 0xFDFE, 0xFE1E, 0xFE3E, 0xFE4E, 0xFE5E, 0xFE6E, 0xFE7E
DRV, KEEP, CONT1, CONT2 = 0xFDFC, 0xF800, 0xBF4C, 0xBF4E


def l(e, a):
    return (e.w(a) << 16 | e.w(a + 2)) & 0xFFFFFFFF


def fields(e, k):
    return dict(ptr=l(e, PTR + 4 * k), pos=l(e, POS + 4 * k), id=e.w(SID + 2 * k), wait=e.w(WAIT + 2 * k),
                tempo=e.w(TEMPO + 2 * k), frac=e.w(FRAC + 2 * k), state=l(e, STATE + 4 * k))


def kept(e):
    return bytes(e.b(KEEP + i) for i in range(22))


def song_slot(e):
    s = e.w(PLAYING)
    if not 0x32 <= s <= 0x55:
        return None
    for k in range(8):
        if l(e, PTR + 4 * k) != 0xFFFFFFFF and e.w(SID + 2 * k) == s:
            return k
    return None


class R:
    def __init__(self, rom, state):
        self.e = Emu(rom)
        self.e.run(1500)                         # powered on first: states leave out save RAM
        self.base = Path(state).read_bytes()
        self.buf = capture(self.e)

    def frame(self, n=1, hold=()):
        e, out = self.e, []
        for _ in range(n):
            e.run(1, hold=list(hold))
            k = song_slot(e)
            out.append(dict(pz=bool(e.w(SFLAGS) & 0x100), song=e.w(PLAYING), k=k,
                            pos=l(e, POS + 4 * k) if k is not None else None,
                            ids=tuple(e.w(SID + 2 * j) for j in range(8) if l(e, PTR + 4 * j) != 0xFFFFFFFF),
                            keep=kept(e), clock=e.w(CLOCK), a=len(self.buf)))
        return out

    def press(self, b, w):
        return self.frame(6, [b]) + self.frame(w)

    def paused(self):
        return bool(self.e.w(SFLAGS) & 0x100)

    def goal(self):
        e = self.e
        e.unserialize(self.base)
        st = e.serialize()
        for y, vy in ((262, 6000), (-262, -6000)):
            e.unserialize(st)
            h = e.w(HMGOALS)
            e.setw(PUCK, 3); e.setw(PUCK + 0x14, y & 0xFFFF); e.setw(PUCK + 0x18, 0); e.setw(PUCK + 0x28, 0)
            e.setw(PUCK + 0x2A, vy & 0xFFFF); e.setb(PUCK + 0x60, 0xFF); e.setw(PUCK + 0x5E, 0)
            tr = self.frame(40)
            if e.w(HMGOALS) != h:
                return tr
        return None

    def resume(self):
        t = []
        for b in ("C", "START", "B", "C"):
            if not self.paused():
                break
            t += self.press(b, 90)
        return t

    def menu(self, kind):
        t = self.press("START", 120)
        if kind == "stats":
            t += self.press("LEFT", 90) + self.press("DOWN", 30) + self.press("C", 300) + self.press("START", 150)
            for _ in range(4):                          # START leaves Game Statistics for the STATS tab
                t += self.press("UP", 20)
        elif kind == "replay":
            t += self.press("DOWN", 30) + self.press("C", 400) + self.press("START", 150)
            for _ in range(8):
                t += self.press("UP", 20)
        else:
            t += self.frame(60)
        return t + self.resume()


def moments(r):
    """(S_play, S_stop): the goal's song playing with the clock running; and 300 frames after the goal."""
    e = r.e
    if r.goal() is None:
        return None, None
    stop = None
    for f in range(1500):
        r.frame(1)
        if f == 260:
            stop = e.serialize()
        if f > 260 and song_slot(e) is not None and not e.w(GMODE) & 0x100:
            r.frame(30)
            return (e.serialize() if song_slot(e) is not None else None), stop
    return None, stop


def moment_period(r):
    """The next period's opening song (on NHL_95 $51, on W18 $32: channel 0 and channel 7, programs 25 and 12) playing,
    the screen back to the game: the clock run out, C through the intermission."""
    e = r.e
    e.unserialize(r.base)
    e.setw(CLOCK, 2)
    for f in range(60 * 90):
        r.frame(1, ["C"] if f % 120 < 4 else [])
        if e.w(GSP) >= 1 and song_slot(e) is not None and not r.paused():
            r.frame(20)
            if song_slot(e) is not None:
                return e.serialize()
    return None


def spectra(r, a0, n):
    x = np.asarray(r.buf[a0:a0 + n * 8820], dtype=np.float32)
    if len(x) < n * 8820:
        return None
    x = x.reshape(n, 4410, 2).mean(2)
    return np.log1p(np.abs(np.fft.rfft(x * np.hanning(4410), axis=1))[:, 20:1200])


def corr(r, a0, b0, n=60):
    sa, sb = spectra(r, a0, n), spectra(r, b0, n)
    if sa is None or sb is None:
        return None
    cc = [float(np.corrcoef(sa[i], sb[i])[0, 1]) for i in range(n)]
    return [round(float(np.nanmean(cc[i:i + 20])), 3) for i in range(0, n, 20)]


def rms(r, a0, a1):
    x = np.asarray(r.buf[a0:a1], dtype=np.float32)
    return round(float(np.sqrt((x * x).mean())), 1) if len(x) else None


def changes(tr, start=0):
    out, last = [], None
    for i in range(start, len(tr)):
        p = tr[i]["pos"]
        if p is not None and p != last:
            out.append((i, p))
        last = p
    return out


def song_case(r, S, kind):
    e = r.e
    e.unserialize(S)
    k0 = song_slot(e)
    at = fields(e, k0)
    ref = r.frame(1500)
    e.unserialize(S)
    tr = r.menu(kind)
    pz = [i for i, t in enumerate(tr) if t["pz"]]
    if not pz:
        return dict(kind=kind, res="no pause")
    first, last = pz[0], pz[-1]
    before = tr[first - 1]                               # the last frame before the pause flag
    saved = tr[first + 30]["keep"]
    row = dict(kind=kind, slot=k0, saved_slot_word=saved[:2].hex(), saved_block=saved.hex(),
               pause_frames=last - first + 1, left_paused=r.paused())
    tr += r.frame(1500)
    back = next((i for i in range(last + 1, min(len(tr), last + 300)) if tr[i]["k"] is not None), None)
    rp = changes(ref)
    row["ref_pos_at_pause"] = hex(before["pos"]) if before["pos"] is not None else None
    if back is None:
        row.update(res="no song after the pause", songs_after=sorted(set(t["song"] for t in tr[last + 1:])),
                   sound_corr_no_song=corr(r, ref[0]["a"], tr[last + 1]["a"]))
        return row
    e2 = tr[back]
    row.update(res="song back", frames_after_pause_flag=back - last, slot_after=e2["k"], pos_after=hex(e2["pos"]),
               keep_word_after=e2["keep"][:2].hex())
    cp = changes(tr, back)
    j = next((j for j, (_, q) in enumerate(rp) if q == cp[0][1]), None) if cp else None
    if j is not None:
        n = min(40, len(rp) - j, len(cp))
        row["next_positions_same"] = f"{sum(rp[j + t][1] == cp[t][1] for t in range(n))} of {n}"
        row["timing_from_the_second_same"] = f"{sum(rp[j + t][0] - rp[j + 1][0] == cp[t][0] - cp[1][0] for t in range(1, n))} of {n - 1}"
        row["sound_corr"] = corr(r, ref[rp[j][0]]["a"], tr[cp[0][0]]["a"])
        row["rms_ref"] = rms(r, ref[rp[j][0]]["a"], ref[min(len(ref) - 1, rp[j][0] + 300)]["a"])
        row["rms_after"] = rms(r, tr[cp[0][0]]["a"], tr[min(len(tr) - 1, cp[0][0] + 300)]["a"])
    else:
        row["position_not_in_reference"] = hex(cp[0][1]) if cp else None
    row["at_S"] = {a: hex(b) for a, b in at.items()}
    return row


def trace_summary(tr):
    return dict(keep_words=sorted(set(t["keep"][:2].hex() for t in tr)), songs=sorted(set(t["song"] for t in tr)),
                song_starts=[(i, t["song"]) for i, t in enumerate(tr) if t["k"] is not None and (i == 0 or tr[i - 1]["k"] is None)][:6],
                ids_seq_hash=hash(tuple(t["ids"] for t in tr)), left_paused=tr[-1]["pz"])


def untouched(r, S, kind):
    e = r.e
    e.unserialize(S)
    if kind == "bit5":
        e.setw(SFLAGS9, e.w(SFLAGS9) | 0x2000)
        tr = r.menu("resume") + r.frame(900)
    elif kind == "intermission":
        e.setw(CLOCK, 2)
        tr = []
        for f in range(60):
            tr += r.frame(60)
            if f % 2 == 0:
                tr += r.press("C", 4)
            if e.w(GSP) >= 1 and not e.w(GMODE) & 0x100 and not r.paused():
                break
        tr += r.frame(600)
    elif kind == "timeout":
        e.setw(CONT1, 0); e.setw(CONT2, 0)
        for k in range(12):
            a = 0xAC62 + k * 0x80 + 0x62
            e.setb(a, e.b(a) & ~8)
        tr = r.press("START", 2100) + r.frame(900)
    elif kind == "abort":
        tr = r.press("START", 120)
        for _ in range(6):
            tr += r.press("DOWN", 30)
        tr += r.press("C", 200)
        for _ in range(3):
            if not r.paused():
                break
            tr += r.press("C", 200)                     # a confirmation, if any
        last = None
        for f in range(60 * 150):
            tr += r.frame(1, ["START"] if f % 240 == 0 else [])
            c = e.w(CLOCK)
            if e.w(GSP) == 0 and last is not None and 0 < c < last and not r.paused() and f > 600:
                break
            last = c
        tr += r.frame(1500)
    s = trace_summary(tr)
    s.update(kind=kind, frames=len(tr))
    return s, tr


def tour(r, S):
    e = r.e
    e.unserialize(S)
    tr = r.press("START", 120)
    for tab, moves in (("INFO", ["LEFT", "LEFT"]), ("STATS", ["LEFT"]), ("OPTIONS", [])):
        for item in range(1, 6 if tab == "OPTIONS" else 7):
            for m in moves:
                tr += r.press(m, 60)
            for _ in range(item):
                tr += r.press("DOWN", 20)
            tr += r.press("C", 300)
            if tab == "OPTIONS" and item == 1:          # Instant Replay: out with START
                tr += r.press("START", 150)
            tr += r.press("START", 150)                 # out of the screen (B doesn't leave them)
            if not r.paused():
                tr += r.press("START", 120)
            for _ in range(2):
                tr += r.press("RIGHT", 40)
            for _ in range(8):
                tr += r.press("UP", 15)
            if not r.paused():
                tr += r.press("START", 120)
    tr += r.resume() + r.frame(120)
    ch = [(i, tr[i - 1]["keep"].hex(), tr[i]["keep"].hex(), tr[i]["pz"]) for i in range(1, len(tr)) if tr[i]["keep"] != tr[i - 1]["keep"]]
    return dict(kind="tour", frames=len(tr), keep_changes=ch[:10], n_changes=len(ch))


Z80 = 16 + 0x10000                                   # Z80 RAM in Genesis Plus GX's state, after work RAM


def z80(e):
    return np.frombuffer(e.serialize()[Z80:Z80 + 0x2000], np.uint8).copy()


def to_pos(r, target, limit=1500):
    for f in range(limit):
        r.frame(1)
        k = song_slot(r.e)
        if k is not None and l(r.e, POS + 4 * k) == target:
            return True
    return False


def voice(out, orig, build, state, which="goal"):
    """The Z80's RAM at the same song positions (10, 20 and 30 position changes after the pause's position) in the
    unpaused game, after a pause on the build, and on the original with the slot written back by hand after the
    pause (no events sent: the reload's lost program changes); the bytes that differ from the unpaused game's."""
    res = []
    for name, rom in (("orig", orig), ("build", build)):
        r = R(rom, state)
        S = moments(r)[0] if which == "goal" else moment_period(r)
        e = r.e
        if S is None:
            res.append(dict(rom=name, res="no song moment"))
            continue
        e.unserialize(S)
        ref = r.frame(1500)
        rp = changes(ref)
        e.unserialize(S)
        k = song_slot(e)
        t = r.press("START", 0)
        last_f = fields(e, k)
        for _ in range(120):                      # the slot as the pause took it (until SoundOff frees it)
            t += r.frame(1)
            if l(e, PTR + 4 * k) == 0xFFFFFFFF:
                break
            last_f = fields(e, k)
        t += r.frame(120) + r.resume()
        t += r.frame(26)
        if name == "orig":                        # the control: the slot back by hand, nothing sent to the Z80
            f = last_f
            e.setl(PTR + 4 * k, f["ptr"]); e.setl(POS + 4 * k, f["pos"]); e.setw(SID + 2 * k, f["id"])
            e.setw(WAIT + 2 * k, f["wait"]); e.setw(TEMPO + 2 * k, f["tempo"]); e.setw(FRAC + 2 * k, f["frac"])
            e.setl(STATE + 4 * k, f["state"]); e.setw(PLAYING, f["id"])
        k2 = song_slot(e)
        if k2 is None:
            res.append(dict(rom=name, res="no song after the pause"))
            continue
        p0 = l(e, POS + 4 * k2)
        j = next((j for j, (_, q) in enumerate(rp) if q >= p0), None)
        st_case = e.serialize()
        for step in (4, 8, 12, 20, 30):
            if j is None or j + step >= len(rp):
                break
            target = rp[j + step][1]
            e.unserialize(S)
            ok1 = to_pos(r, target)
            zr = z80(e)
            e.unserialize(st_case)
            ok2 = to_pos(r, target)
            zc = z80(e)
            d = np.nonzero(zr != zc)[0]
            row = dict(rom=name + (" (slot by hand)" if name == "orig" else ""), moment=which, song=hex(e.w(PLAYING)),
                       step=step, pos=hex(target), reached=(ok1, ok2), z80_bytes_differing=len(d),
                       outside_500_5ff=int(((d < 0x500) | (d > 0x5FF)).sum()), where=[hex(a) for a in d[:24]])
            res.append(row)
            print(json.dumps(row), flush=True)
        lowload.breathe()
        del r
    (out / f"voice95_{which}_{Path(build).stem}.json").write_text(json.dumps(res, indent=1))


def main():
    if sys.argv[1] == "voice":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        lowload.gentle()
        voice(out, *sys.argv[3:6], *(["period"] if "--period" in sys.argv else []))
        return
    if sys.argv[1] == "period":                     # the song cases on the next period's opening song
        out, orig, build, state = Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
        out.mkdir(parents=True, exist_ok=True)
        lowload.gentle()
        for name, rom in (("orig", orig), ("build", build)):
            r = R(rom, state)
            S = moment_period(r)
            if S is None:
                print(name, "no period song")
                continue
            for kind in ("resume", "stats", "replay"):
                row = song_case(r, S, kind)
                row["song"] = hex(r.e.w(PLAYING))
                print(name, json.dumps(row), flush=True)
            del r
        return
    out, orig, build, state = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    res = {}
    traces = {}
    for name, rom in (("orig", orig), ("build", build)):
        r = R(rom, state)
        S, Sstop = moments(r)
        rows = []
        if S is None:
            print(name, "no song moment")
        for kind in ("resume", "stats", "replay"):
            if S is not None:
                row = song_case(r, S, kind)
                rows.append(row)
                print(name, json.dumps(row), flush=True)
                lowload.breathe()
        if Sstop is not None:
            r.e.unserialize(Sstop)
            r.frame(1)
            if song_slot(r.e) is not None:
                row = song_case(r, r.e.serialize(), "stoppage")
                rows.append(row)
                print(name, json.dumps(row), flush=True)
        for kind in ("bit5", "intermission", "timeout", "abort"):
            s, tr = untouched(r, S or Sstop, kind)
            traces[(name, kind)] = tr
            rows.append(s)
            print(name, json.dumps(s), flush=True)
            lowload.breathe()
        row = tour(r, S or Sstop)
        rows.append(row)
        print(name, json.dumps(row), flush=True)
        res[name] = rows
        del r
    for kind in ("bit5", "intermission", "timeout", "abort"):
        a, b = traces[("orig", kind)], traces[("build", kind)]
        n = min(len(a), len(b))
        key = lambda t: (t["song"], t["k"] is not None, t["pos"], t["pz"], t["clock"])  # noqa: E731
        diff = [i for i in range(n) if key(a[i]) != key(b[i])]
        sfx = sum(1 for i in range(n) if a[i]["ids"] != b[i]["ids"])
        line = (f"{kind}: frames {len(a)} / {len(b)}; the song (PlayingSong, its slot, its position), the pause flag and"
                f" the clock differ in {len(diff)} frames" + (f", first at {diff[0]}" if diff else "")
                + f"; the slots' ids (sound effects too) in {sfx}")
        res.setdefault("compare", []).append(line)
        print(line, flush=True)
    (out / f"organ95_{Path(build).stem}.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
