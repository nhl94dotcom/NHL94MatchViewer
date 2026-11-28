"""No fans in the stands, NHL '94 Genesis (2026-11-27, for NOSE4Web's rink themes: the moving crowd sprites drawn over
a themed rink's stands): the crowd frames skipped, played against the unpatched ROM.

showcrowd (video94.asm, called from setvideo every frame) draws, from CrowdSprites at crowdvrcset ($FFB01A), first
the penalty-box players (PBnum's two nibbles: frames 26+ and 29+, up to 3 each) and then the crowd: the two frames
Crowdframe ($FFB89A) and Crowdframe+1 that updatecrowdf picks by Crowdlevel ($FFB8A2). The patch puts an rts on the
crowd part, at retail $16216 (`10 38 B8 9A`, move.b (Crowdframe).w,d0 -> `4E 75`): the penalty-box players, the
crowd level, updatecrowdf, the crowd noise (Crowd_Noise, updatesound), the replay's saved Crowdframe and every other
sprite are left alone. In the side-on (horizontal) view the same frames + 31 are the scoreboard's crowd: they go too.

`patch ROM OUT.bin`: the patch (and the checksum call at $300 NOPed, as NOSE4Web's builds do, if it isn't yet).
`play ROM OUT TAG`: from one game moment (Game Setup's defaults, the computer on both sides), each frame's sprite
table (VDP register 5) sorted into crowd-tile sprites (tiles crowdvrcset to crowdvrcset + the CrowdSprites count) and
the rest, Crowdframe, Crowdlevel, the side-on flag, the frame counter and puck, and the sound (the core's
audio); cases: a home goal at 2:00 and 900 frames of its celebration; 1,800 frames of play; a penalty called (a
PenBuf entry, as gen_hor_board_check does) through its side-on view and 1,200 frames of the power play (the boxed
player's sprite); the pause menu's instant replay and back; the period's end and the intermission into period 2.
`compare OUT BASE_TAG BUILD_TAG`: crowd sprites per case (the build: only penalty-box frames), the other sprites,
Crowdlevel and the sound's loudness per 0.1 s (real). The patch saves CPU time each frame and the game takes its
randomness from the beam position (HVcount), so the two games drift apart within a few hundred frames even where the
frame counter and puck agree: the other sprites are compared by count and by the screenshots, not frame for frame.

python gen_crowd_off_check.py patch ROM OUT.bin
python gen_crowd_off_check.py play ROM OUT TAG
python gen_crowd_off_check.py compare OUT BASE_TAG BUILD_TAG"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

import gen_1on1_edit_lines as G
import gen_songs_check as SC
from gen_midi_song_check import capture
from gen_score_logo_check import VRAM_AT

PATCH_AT, OLD, NEW = 0x16216, bytes.fromhex("1038B89A"), bytes.fromhex("4E75")
CROWDVRC, CROWDFRAME, CROWDLEVEL, FRAMECTR, SFLAGS, CLOCK, GSP, SCREEN = 0xB01A, 0xB89A, 0xB8A2, 0xB03E, 0xC2EC, 0xC468, 0xC466, 0xFFF7
PUCKC, PENBUF, GMODE = 0xB7AA, 0xC3A4, 0xC2EA


def crowd_count(rom):
    """CrowdSprites' tile count: the long at showcrowd's `movea.l #CrowdSprites,a1` points at its jim (+8 count)."""
    j = rom.rfind(bytes.fromhex("227C"), PATCH_AT - 0x60, PATCH_AT)   # showcrowd's movea.l #CrowdSprites,a1
    jim = struct.unpack(">I", rom[j + 2:j + 6])[0]
    return struct.unpack(">H", rom[jim + 8:jim + 10])[0] & 0x7FFF


def patch(rom, out):
    d = bytearray(Path(rom).read_bytes())
    assert d[PATCH_AT:PATCH_AT + 4] == OLD, f"not retail's showcrowd at ${PATCH_AT:X}: {d[PATCH_AT:PATCH_AT + 4].hex()}"
    d[PATCH_AT:PATCH_AT + 2] = NEW
    if d[0x300:0x306] != bytes.fromhex("4E714E714E71"):
        d[0x300:0x306] = bytes.fromhex("4E714E714E71")         # the checksum call (jsr ValidationRoutine) NOPed
    Path(out).write_bytes(d)
    print(out, "patched")


def sprites(e):
    st = bytes(e.serialize())
    vr = st[VRAM_AT:VRAM_AT + 0x10000]
    reg = st[VRAM_AT + 0x10100:VRAM_AT + 0x10120]
    sat = (reg[5] & 0x7F) << 9
    out, link = [], 0
    for _ in range(80):
        o = sat + 8 * link
        w = [vr[o + 2 * k] | vr[o + 2 * k + 1] << 8 for k in range(4)]
        out.append((w[0] & 0x3FF, w[1] >> 8 & 15, w[2], w[3] & 0x1FF))
        link = w[1] & 0x7F
        if link == 0:
            break
    return out


def play(rom, out, tag):
    out.mkdir(parents=True, exist_ok=True)
    data = Path(rom).read_bytes()
    r = G.Run(rom, out / f"_{tag}")
    e = r.e
    buf = capture(e)
    r.to_play()
    r.step(120)
    base = e.serialize()
    cvr, ccount = e.w(CROWDVRC), crowd_count(data)
    res = dict(rom=Path(rom).name, crowdvrcset=cvr, crowd_tiles=ccount, cases={})

    def watch(case, n, each=None):
        rows = []
        a0 = len(buf)
        for f in range(n):
            if each:
                each(f)
            e.run(1)
            sp = sprites(e)
            crowd = [s for s in sp if cvr <= (s[2] & 0x7FF) < cvr + ccount]
            other = sorted((s[0], s[2], s[3]) for s in sp if not cvr <= (s[2] & 0x7FF) < cvr + ccount)
            rows.append(dict(f=f, crowd=len(crowd), other=other, cf=e.w(CROWDFRAME), cl=e.w(CROWDLEVEL),
                             fc=e.w(FRAMECTR), puck=[e.w(0xB04A + 14 * 0x80), e.w(0xB04A + 14 * 0x80 + 0x14)],
                             hor=e.b(SFLAGS) >> 7 & 1, screen=e.b(SCREEN), a=len(buf) - a0))
            if f in (60, n // 2, n - 1):
                e.screenshot(out / f"{tag}_{case}_{f:05d}.png")
        res["cases"][case] = dict(rows=rows, a0=a0)
        print(tag, case, "crowd sprites (frames with any):", sum(1 for x in rows if x["crowd"]), "max", max(x["crowd"] for x in rows), flush=True)

    # a home goal and its celebration
    e.unserialize(base)
    e.setw(CLOCK, 120)
    SC.goal(r, [], "goal")
    watch("goal", 900)
    # play
    e.unserialize(base)
    watch("play", 1800)
    # a penalty called on the puck carrier, its side-on view and the power play (the boxed player)
    e.unserialize(base)
    for _ in range(40):
        e.run(30)
        k = e.w(PUCKC)
        if 0 <= k < 12 and not e.b(SFLAGS) & 0x80:
            e.setw(PENBUF, 0x1E << 8 | k)
            e.setw(PENBUF + 2, 0)
            e.setw(GMODE, e.w(GMODE) & ~0x0D00)
            break
    watch("penalty", 3000)
    # the instant replay from the pause menu, and back
    e.unserialize(base)
    r.step(600)

    def presses(f):
        for at, b in ((0, "START"), (90, "DOWN"), (130, "C"), (900, "START"), (1000, "START"), (1200, "START")):
            if f == at:
                e.run(4, hold=[b])
    watch("replay", 1600, presses)
    # the period's end, the intermission (C through its screens) and period 2
    e.unserialize(base)
    e.setw(CLOCK, 2)
    watch("intermission", 4000, lambda f: e.run(4, hold=["C"]) if f % 60 == 0 and e.w(GSP) == 0 else None)
    np.save(out / f"audio_{tag}.npy", np.asarray(buf, dtype=np.int16))
    (out / f"crowd_{tag}.json").write_text(json.dumps(res))


def compare(out, ta, tb):
    A = json.loads((out / f"crowd_{ta}.json").read_text())
    B = json.loads((out / f"crowd_{tb}.json").read_text())
    aa, ab = np.load(out / f"audio_{ta}.npy").astype(float), np.load(out / f"audio_{tb}.npy").astype(float)
    lines = []
    for case in A["cases"]:
        ra, rb = A["cases"][case]["rows"], B["cases"][case]["rows"]
        step = next((i for i, (x, y) in enumerate(zip(ra, rb)) if (x["fc"], x["puck"]) != (y["fc"], y["puck"])), len(ra))
        other_diff = sum(1 for x, y in list(zip(ra, rb))[:step] if x["other"] != y["other"])
        # crowd sprites in the build only where the base, with no crowd frame on, draws penalty-box players
        b_crowd = [x["crowd"] for x in rb]
        pb_only = [x["crowd"] for x in ra[:step] if x["cf"] == 0]
        loud = []                       # the sound's loudness per 0.1 s (real): means and their correlation
        pa = aa[A["cases"][case]["a0"]:A["cases"][case]["a0"] + ra[-1]["a"]]
        pb = ab[B["cases"][case]["a0"]:B["cases"][case]["a0"] + rb[-1]["a"]]
        m = min(len(pa), len(pb)) // 8820 * 8820
        if m:
            ra_ = np.sqrt((pa[:m].reshape(-1, 8820) ** 2).mean(1))
            rb_ = np.sqrt((pb[:m].reshape(-1, 8820) ** 2).mean(1))
            loud = [round(float(ra_.mean())), round(float(rb_.mean())), round(float(np.corrcoef(ra_, rb_)[0, 1]), 3) if ra_.std() and rb_.std() else None]
        lines.append(dict(case=case, frames=len(rb), in_step=step,
                          base_crowd_sprites=[sum(1 for x in ra if x["crowd"]), max(x["crowd"] for x in ra)],
                          build_crowd_sprites=[sum(1 for x in b_crowd if x), max(b_crowd)],
                          build_crowd_frames_with_cf_on=sum(1 for x in rb if x["crowd"] and x["cf"]),
                          base_penalty_box_only_max=max(pb_only) if pb_only else 0,
                          other_sprites_differ_in_step=other_diff,
                          crowdlevel_same_in_step=all(x["cl"] == y["cl"] for x, y in list(zip(ra, rb))[:step]),
                          crowdlevel_max=[max(x["cl"] for x in ra), max(x["cl"] for x in rb)],
                          loudness_base_build_corr=loud, side_on_frames=[sum(x["hor"] for x in ra), sum(x["hor"] for x in rb)]))
    (out / "crowd_off_compare.json").write_text(json.dumps(lines, indent=1))
    for x in lines:
        print(json.dumps(x))


if __name__ == "__main__":
    if sys.argv[1] == "patch":
        patch(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "play":
        play(sys.argv[2], Path(sys.argv[3]), sys.argv[4])
    else:
        compare(Path(sys.argv[2]), sys.argv[3], sys.argv[4])
