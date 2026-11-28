"""NOSE4Web's goal sounds by home team (2026-11-28; nhl94_goal_sounds.bin 76EE874B, nhl95_goal_sounds.bin AFB0F984):
checkgoal's `move.w #SFXsiren,-(sp)` + the call to sfx (NHL 94 $1484A, NHL '95 $8C3B0) becomes a jsr to new code
(NHL 94 $FFAC0, '95 $1A72C6) that finds the scorer as checkgoal does (Ypos(a3) not negative XOR gmdir in gmode: home)
and plays the home team's word from a table by HomeTeam, or the visitors' word, through sfx (negative: nothing).

The control is the build with the hook site's original bytes put back (the siren, as retail), so the two run the same
frames. Each ROM: power-on into play (period 1) and on into period 2 (the clock set to 0:02, the screens pressed
through), then for each period, each home team given (HomeTeam set every frame) and each net, a goal forced (the puck
sent into the net from just in front of it) and 900 frames watched:
  NHL 94: every sfx call (lastsfx $C016, set $7FFF after each read; sfx skips negatives before writing it), every
          ChooseSong pick (SongNum $D6C8), the songs in the driver's slots (fm_track_slots, stream pointers mapped to
          song numbers by the table at $2C648: $30 and up), the score that went up.
  NHL '95: lastsfx $BC1C (the driver's sfx skips $B / $C there, so also) the sequencer slots' ids SndSeqId $FE3E
          (free when SndSeqPtr $FDFE is -1): each id newly started, songs ($32-$55) playing, SongNum $D392.
The core's audio around each goal: a WAV, its loudness every 0.1 s (real) and the sound's length (the goal sound's
slots until free).

`ps` (NHL 94): penalty shots awarded as ps_fixes_test does (a breakaway foul, from the saved live states), the puck put
into the net the shooter attacks once he has it: the sound against the team credited.
`shootout` (NHL '95): Shootout mode (gen95_shootout_mode_check, every attempt forced in): each goal's sound against the
team credited.

python gen_goal_sounds_check.py OUT ROM94_BUILD ROM95_BUILD [TEAMS]        (TEAMS default 0,1,2,3)
python gen_goal_sounds_check.py ps OUT ROM94_BUILD [N]
python gen_goal_sounds_check.py shootout OUT ROM95_BUILD"""
import json
import random
import struct
import sys
import wave
from pathlib import Path

import numpy as np

import lowload
from emu import Emu
from gen_midi_song_check import capture


class G94:
    name = "94"
    HOOK, ORIG = 0x1484A, bytes.fromhex("3f3c00006100c8e2")
    HOME, GMODE, GSP, CLOCK, HSCORE, ASCORE = 0xC330, 0xC2EA, 0xC466, 0xC468, 0xC6DA, 0xCA3E
    PUCK = 0xB04A + 14 * 0x80
    LASTSFX, SONGNUM, SCREEN = 0xC016, 0xD6C8, 0xFFF7
    SLOTS, TABLE = 0xD3D4, 0x2C648

    def __init__(self, rom):
        d = Path(rom).read_bytes()
        self.st = sorted((struct.unpack_from(">I", d, self.TABLE + 4 * s)[0], s) for s in range(0x30, 0x7B))
        self.s30 = dict((s, p) for p, s in self.st)[0x30]
        self.all = sorted((struct.unpack_from(">I", d, self.TABLE + 4 * s)[0], s) for s in range(0, 0x7B))

    def boot(self, e):
        e.run(900)
        for _ in range(60):
            if e.b(self.SCREEN) == 0 and self.running(e):
                return True
            e.run(4, hold=["START"]); e.run(200)
        return False

    def running(self, e):
        c = e.w(self.CLOCK)
        e.run(30)
        return e.w(self.CLOCK) != c and e.b(self.SCREEN) == 0

    def songs(self, e):
        out = set()
        for k in range(8):
            p = (e.w(self.SLOTS + 6 * k) << 16 | e.w(self.SLOTS + 6 * k + 2)) & 0xFFFFFFFF
            if p & 0x80000000 or p < self.s30:
                continue
            out.add(max((q, s) for q, s in self.st if q <= p)[1])
        return out

    def sfx_slots(self, e):
        n = 0
        for k in range(8):
            p = (e.w(self.SLOTS + 6 * k) << 16 | e.w(self.SLOTS + 6 * k + 2)) & 0xFFFFFFFF
            n += not (p & 0x80000000) and p < self.s30
        return n

    def slots(self, e):
        """Each slot's sound: every sound (effects 0-$2F, songs $30-$7A) is one stream starting at its table entry, so a
        stream pointer is in the sound whose start is the highest at or below it."""
        out = {}
        for k in range(8):
            p = (e.w(self.SLOTS + 6 * k) << 16 | e.w(self.SLOTS + 6 * k + 2)) & 0xFFFFFFFF
            if not p & 0x80000000:
                out[k] = (max((q, s) for q, s in self.all if q <= p)[1], p)
        return out

    def new_ids(self, e, prev):
        now = self.slots(e)
        out = [i for k, (i, p) in now.items() if k not in prev or prev[k][0] != i or p < prev[k][1]]
        prev.clear()
        prev.update(now)
        return out


class G95(G94):
    name = "95"
    HOOK, ORIG = 0x8C3B0, bytes.fromhex("3f3c00004eb9000677ac")
    HOME, GMODE, GSP, CLOCK = 0xBF54, 0xBEF0, 0xC020, 0xC022
    HSCORE, ASCORE = 0xC288 + 0xC, 0xC288 + 0x366 + 0xC
    PUCK = 0xAC62 + 14 * 0x80
    LASTSFX, SONGNUM = 0xBC1C, 0xD392
    PTR, SID = 0xFDFE, 0xFE3E

    def __init__(self, rom):
        pass

    def boot(self, e):
        e.run(1500)
        for _ in range(40):
            if self.running(e):
                return True
            e.run(6, hold=["START"]); e.run(300)
        return False

    def running(self, e):
        c = e.w(self.CLOCK)
        e.run(30)
        return e.w(self.CLOCK) != c and c != 0

    def slots(self, e):
        return {k: (e.w(self.SID + 2 * k), e.l(self.PTR + 4 * k)) for k in range(8) if e.l(self.PTR + 4 * k) != 0xFFFFFFFF}

    def songs(self, e):
        return {i for i, _ in self.slots(e).values() if 0x32 <= i <= 0x55}

    def sfx_slots(self, e):
        return sum(1 for i, _ in self.slots(e).values() if i < 0x32)

    def new_ids(self, e, prev):
        now = self.slots(e)
        out = [i for k, (i, p) in now.items() if k not in prev or prev[k][0] != i or p < prev[k][1] - 64]
        prev.clear()
        prev.update(now)
        return out


def control(rom, sysm, out):
    d = bytearray(Path(rom).read_bytes())
    d[sysm.HOOK:sysm.HOOK + len(sysm.ORIG)] = sysm.ORIG
    p = out / f"control_{Path(rom).name}"
    p.write_bytes(d)
    return p


def table(rom, sysm):
    """The build's sounds: (home word by team, visitors' word), read from the hook's code."""
    d = Path(rom).read_bytes()
    at = struct.unpack_from(">I", d, sysm.HOOK + 2)[0]
    code = d[at:at + 0x50]
    lea = code.index(bytes.fromhex("41fa"))
    tab = at + lea + 2 + struct.unpack_from(">h", code, lea + 2)[0]
    mv = code.index(bytes.fromhex("303a"))
    vis = at + mv + 2 + struct.unpack_from(">h", code, mv + 2)[0]
    sw = lambda v: v - 0x10000 if v >= 0x8000 else v  # noqa: E731
    return [sw(struct.unpack_from(">H", d, tab + 2 * t)[0]) for t in range(32)], sw(struct.unpack_from(">H", d, vis)[0])


def to_period2(sysm, e):
    """The clock set to 0:02; the screens pressed through (START, C) until period 2 starts, then C only (START would
    pause; C takes Resume Game if it did) until the clock counts down."""
    e.setw(sysm.CLOCK, 2)
    for f in range(400):
        if e.w(sysm.GSP) == 1:
            break
        e.run(4, hold=["C"] if f % 2 else ["START"])
        e.run(56)
    else:
        return False
    for f in range(200):
        c = e.w(sysm.CLOCK)
        e.run(60)
        c2 = e.w(sysm.CLOCK)
        if 0 < c2 < c:
            return True
        e.run(4, hold=["C"])
    return False


def watch(sysm, e, frames, team, buf):
    """Every frame for `frames`: sfx calls, song picks, new sequencer ids, the songs playing, sfx slots in use."""
    e.setw(sysm.LASTSFX, 0x7FFF)
    e.setw(sysm.SONGNUM, 0x7FFF)
    prev = {}
    sysm.new_ids(e, prev)
    rows = []
    for f in range(frames):
        if team is not None:
            e.setw(sysm.HOME, team)
        e.run(1)
        s, n = e.w(sysm.LASTSFX), e.w(sysm.SONGNUM)
        e.setw(sysm.LASTSFX, 0x7FFF)
        e.setw(sysm.SONGNUM, 0x7FFF)
        rows.append(dict(f=f, sfx=None if s == 0x7FFF else s, pick=None if n == 0x7FFF else n, ids=sysm.new_ids(e, prev),
                         songs=sorted(sysm.songs(e)), nsfx=sysm.sfx_slots(e), score=[e.w(sysm.HSCORE), e.w(sysm.ASCORE)],
                         a=len(buf)))
    return rows


def force_goal(sysm, e, y):
    """The puck sent into the net at `y` from just in front of it, both goalies (position 0) moved aside first."""
    base = sysm.PUCK - 14 * 0x80
    for k in range(12):
        r = base + k * 0x80
        if e.b(r + 0x35) == 0:
            e.setw(r, 120)
            e.setw(r + 0x14, (-200 if y > 0 else 200) & 0xFFFF)
    p = sysm.PUCK
    e.setw(p, 3)
    e.setw(p + 0x14, y & 0xFFFF)
    e.setw(p + 0x18, 0)
    e.setw(p + 0x28, 0)
    e.setw(p + 0x2A, (6000 if y > 0 else -6000) & 0xFFFF)
    e.setb(p + 0x60, 0xFF)
    e.setw(p + 0x5E, 0)


def save_wav(path, pcm):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes(struct.pack(f"<{len(pcm)}h", *pcm))


def loud(pcm):
    a = np.asarray(pcm, dtype=np.float64)
    step = 2 * 4410
    return [round(float(np.sqrt(np.mean(a[i:i + step] ** 2)))) for i in range(0, len(a) - step + 1, step)]


def play(rom, out, tag, teams):
    sysm = (G95 if Path(rom).stat().st_size > 0x100000 else G94)(rom)
    e = Emu(str(rom))
    buf = capture(e)
    assert sysm.boot(e), "not into play"
    e.run(120)
    states = {1: e.serialize()}
    assert to_period2(sysm, e), "period 2 not reached"
    e.run(120)
    states[2] = e.serialize()
    res = []
    for per, st in states.items():
        for team in teams:
            for y in (258, -258):
                e.unserialize(st)
                del buf[:]
                e.setw(sysm.HOME, team)
                e.run(2)
                gm = e.b(sysm.GMODE) >> 1 & 1
                pre = watch(sysm, e, 30, team, buf)
                sc0 = [e.w(sysm.HSCORE), e.w(sysm.ASCORE)]
                force_goal(sysm, e, y)
                rows = watch(sysm, e, 900, team, buf)
                g = next((r for r in rows if r["score"] != sc0), None)
                if g is None:
                    res.append(dict(period=per, team=team, net=y, goal=False))
                    continue
                who = "home" if g["score"][0] > sc0[0] else "away"
                gf = g["f"]
                near = [r for r in rows if gf - 2 <= r["f"] <= gf + 8]
                sfx = [r["sfx"] for r in near if r["sfx"] is not None]
                ids = [i for r in near for i in r["ids"]]
                after = rows[gf:]
                dur = next((r["f"] - gf for r in after[5:] if r["nsfx"] == 0), None)
                double = [r["f"] - gf for r in after if len(r["songs"]) > 1]
                pcm = list(buf[g["a"] - 2 * 735 * 30:])
                save_wav(out / f"{tag}_p{per}_team{team:02d}_{who}.wav", pcm)
                res.append(dict(period=per, team=team, net=y, gmdir=gm, goal=True, scorer=who, frame=gf, sfx=sfx, ids=ids,
                                songs_before=pre[-1]["songs"], songs_at_goal=g["songs"],
                                songs_after=[(r["f"] - gf, r["songs"]) for i, r in enumerate(after) if i == 0 or r["songs"] != after[i - 1]["songs"]][:8],
                                picks=[(r["f"] - gf, r["pick"]) for r in after if r["pick"] is not None],
                                sfx_after=[(r["f"] - gf, r["sfx"]) for r in after if r["sfx"] is not None][:12],
                                sound_frames=dur, two_songs_frames=len(double),
                                loud=loud(buf[g["a"]:g["a"] + 2 * 44100 * 6])))
                print(json.dumps({k: v for k, v in res[-1].items() if k != "loud"}), flush=True)
                lowload.breathe()
    (out / f"{tag}.json").write_text(json.dumps(res, indent=1))


GOALSOUNDS = {0: "siren", 4: "horn", 0xB: "cheer"}
DRIVER95 = {0: 0x26, 4: 0x16, 0xB: 0x10}           # NHL '95's SfxTable: the driver sound each effect plays


def goal_sounds(sysm, ids):
    """The siren, horn and cheer started among `ids` (a Counter by effect number)."""
    from collections import Counter
    m = (lambda s: s) if sysm is G94 else DRIVER95.get
    return Counter({s: n for s in GOALSOUNDS if (n := sum(1 for i in ids if i == m(s)))})


def judge(sysm, want, ids, control_ids):
    """The build's goal sounds against the control's with its siren swapped for the one wanted (-1: nothing): the game
    starts a crowd cheer of its own at a goal (Crowdlevel), so that cheer is in both."""
    got, ctl = goal_sounds(sysm, ids), goal_sounds(sysm, control_ids)
    exp = ctl.copy()
    exp[0] -= 1
    if want >= 0:
        exp[want] += 1
    exp = +exp
    name = lambda c: "+".join(GOALSOUNDS[s] + (f" x{n}" if n > 1 else "") for s, n in sorted(c.items())) or "none"  # noqa: E731
    return got == exp, name(got), name(ctl)


def compare(out, build_rom, tag_c, tag_b, teams):
    sysm = G95 if Path(build_rom).stat().st_size > 0x100000 else G94
    tab, vis = table(build_rom, sysm)
    C = json.loads((out / f"{tag_c}.json").read_text())
    B = json.loads((out / f"{tag_b}.json").read_text())
    lines = []
    names = {0: "siren", 4: "horn", 0xB: "cheer", -1: "nothing"}
    for c, b in zip(C, B):
        if not (c["goal"] and b["goal"]):
            lines.append(f"FAIL  period {b['period']} team {b['team']} net {b['net']}: no goal ({c['goal']}, {b['goal']})")
            continue
        want = tab[b["team"]] if b["scorer"] == "home" else vis
        ok, got_s, ctl_s = judge(sysm, want, b["ids"], c["ids"])
        ok = ok and c["scorer"] == b["scorer"]
        same_picks = [p for _, p in c["picks"]] == [p for _, p in b["picks"]]
        lines.append(f"{'PASS' if ok else 'FAIL'}  NHL {sysm.name} period {b['period']} (gmdir {b['gmdir']}) home team {b['team']:2d} "
                     f"{b['scorer']:4s} goal: wants {names.get(want, hex(want))}, got {got_s} "
                     f"(control {ctl_s}); "
                     f"song picks {'as control' if same_picks else 'DIFFER'} {[p for _, p in b['picks']]}; "
                     f"two songs at once {b['two_songs_frames']} frames (control {c['two_songs_frames']}); "
                     f"songs after: {b['songs_after'][:4]} (control {c['songs_after'][:4]}); sound frames {b['sound_frames']} "
                     f"(control {c['sound_frames']}); loudness first 2 s {b['loud'][:20:4]} (control {c['loud'][:20:4]})")
    (out / f"compare_{sysm.name}.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def ps_pair(out, rom, n):
    """The penalty shots on the build and on the control, each in its own process (one core a process), the same seed,
    paired by trial."""
    import subprocess
    sysm = G94(rom)
    tab, vis = table(rom, sysm)
    ctl = control(rom, sysm, out)
    procs = [subprocess.Popen([sys.executable, __file__, "--ps", str(p), str(out), t, str(n)])
             for p, t in ((ctl, "control"), (rom, "build"))]
    for p in procs:
        p.wait()
    C = {r["i"]: r for r in json.loads((out / "ps94_control.json").read_text())}
    rows = []
    for b in json.loads((out / "ps94_build.json").read_text()):
        c = C.get(b["i"], {})
        if b.get("res") != "goal" or c.get("res") != "goal":
            rows.append(dict(i=b["i"], res=b.get("res"), control=c.get("res")))
        else:
            want = tab[b["team"]] if b["scorer"] == "home" else vis
            ok, got, cs = judge(G94, want, b["ids"], c["ids"])
            rows.append(dict(i=b["i"], team=b["team"], scorer=b["scorer"], control_scorer=c["scorer"], net=b["net"],
                             penalty_shot_goal=b["ps_at_goal"], gmdir=b["gmdir"], want=want, got=got, control=cs,
                             ok=ok and c["scorer"] == b["scorer"] and c["net"] == b["net"]))
        print(json.dumps(rows[-1]), flush=True)
    (out / "ps94.json").write_text(json.dumps(rows, indent=1))


def ps(out, rom, n, tag):
    import ps_fixes_test as F
    import ps_table_test as P
    from bot_scenario import live_state, LIVE_STATES
    sysm = G94(rom)
    rnd = random.Random(94)
    e = Emu(str(rom))
    rows = []
    SFLAGS4 = 0xC2F4

    def shot(em, st, y, team):
        em.unserialize(st)
        em.setw(sysm.HOME, team)
        sc0 = [em.w(sysm.HSCORE), em.w(sysm.ASCORE)]
        force_goal(sysm, em, y)
        ps_on = []
        w = []
        e0 = {}
        sysm.new_ids(em, e0)
        for f in range(200):
            em.setw(sysm.HOME, team)
            em.run(1)
            w.append(dict(f=f, ids=sysm.new_ids(em, e0), score=[em.w(sysm.HSCORE), em.w(sysm.ASCORE)]))
            ps_on.append(em.b(SFLAGS4) >> 5 & 1)
        g = next((x for x in w if x["score"] != sc0), None)
        if not g:
            return None
        ids = [i for x in w if g["f"] - 2 <= x["f"] <= g["f"] + 8 for i in x["ids"]]
        return dict(scorer="home" if g["score"][0] > sc0[0] else "away", ids=ids, ps_at_goal=ps_on[g["f"]],
                    gmdir=em.b(sysm.GMODE) >> 1 & 1)

    for i in range(n):
        base = live_state(e, i % LIVE_STATES)
        team = (0, 3)[i % 2]
        r = F.award(e, base, rnd)
        if r is None:
            rows.append(dict(i=i, res="no award")); continue
        if F.run_until(e, lambda: e.w(P.BA_PS_FLAGS) & F.UNDERWAY, 3000) is None:
            rows.append(dict(i=i, res="no attempt")); continue
        shooter = e.w(P.BA_SKTR)
        if F.run_until(e, lambda: e.w(P.PUCKC) == shooter, 1500) is None:
            rows.append(dict(i=i, res="no carry")); continue
        e.run(20)
        st = e.serialize()
        done = None
        for y in (258, -258):
            b = shot(e, st, y, team)
            if b is None:
                continue
            done = dict(i=i, res="goal", shooter=shooter, team=team, net=y, **b)
            break
        rows.append(done or dict(i=i, res="no goal either net"))
        print(tag, json.dumps(rows[-1]), flush=True)
        lowload.breathe()
    (out / f"ps94_{tag}.json").write_text(json.dumps(rows, indent=1))


def shootout(out, rom):
    import gen95_shootout_mode_check as S
    sysm = G95(rom)
    tab, vis = table(rom, sysm)
    log = []

    class LogEmu(Emu):
        def run(self, n=1, hold=(), **k):
            for _ in range(n):
                sc0 = (self.w(S.HG), self.w(S.AG))
                prev = getattr(self, "_prev", {})
                super().run(1, hold=hold, **k)
                ids = sysm.new_ids(self, prev)
                self._prev = prev
                sc = (self.w(S.HG), self.w(S.AG))
                if ids or sc != sc0:
                    log.append(dict(ids=ids, hg=sc[0], ag=sc[1], home=self.w(sysm.HOME), gm=self.b(sysm.GMODE) >> 1 & 1,
                                    gmode2=self.b(S.GMODE2)))
    S.Emu = LogEmu
    att = S.run(rom, out / "shootout", "G" * 12, 12)
    goals = []
    for i, x in enumerate(log):
        if i and (x["hg"], x["ag"]) != (log[i - 1]["hg"], log[i - 1]["ag"]):
            who = "home" if x["hg"] > log[i - 1]["hg"] else "away"
            near = [i2 for y in log[max(0, i - 3):i + 4] for i2 in y["ids"]]
            want = tab[x["home"]] if who == "home" else vis
            got = goal_sounds(G95, near)               # no control run here: the wanted sound started, no siren unless wanted
            ok = (want < 0 or got[want] > 0) and (want == 0 or not got[0])
            goals.append(dict(scorer=who, home=x["home"], gmdir=x["gm"], ids=[hex(v) for v in near], want=want,
                              got="+".join(GOALSOUNDS[s] for s in sorted(got)) or "none", ok=ok))
            print(json.dumps(goals[-1]), flush=True)
    (out / "shootout95.json").write_text(json.dumps(dict(attempts=att, goals=goals), indent=1))


def main():
    lowload.gentle()
    if sys.argv[1] == "--play":
        play(sys.argv[2], Path(sys.argv[3]), sys.argv[4], [int(t) for t in sys.argv[5].split(",")])
        return
    if sys.argv[1] == "--ps":
        ps(Path(sys.argv[3]), sys.argv[2], int(sys.argv[5]), sys.argv[4])
        return
    if sys.argv[1] == "ps":
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        ps_pair(out, sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 8)
        return
    if sys.argv[1] == "shootout":
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        shootout(out, sys.argv[3])
        return
    import subprocess
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    teams = sys.argv[4] if len(sys.argv) > 4 else "0,1,2,3"
    for rom in sys.argv[2:4]:
        sysm = G95 if Path(rom).stat().st_size > 0x100000 else G94
        ctl = control(rom, sysm, out)
        procs = [subprocess.Popen([sys.executable, __file__, "--play", str(p), str(out), t, teams])
                 for p, t in ((ctl, f"control{sysm.name}"), (rom, f"build{sysm.name}"))]
        for p in procs:
            p.wait()
        compare(out, rom, f"control{sysm.name}", f"build{sysm.name}", teams)


if __name__ == "__main__":
    main()
