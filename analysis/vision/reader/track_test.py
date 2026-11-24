"""Chunk 4 test: inverse.py's reader over a stretch of BOS-CHI game 1, no match file used in the reading (the teams'
palettes from the ROM by colour coverage, the transitions from games 2-4); then each frame scored against game 1's
match file: per recorded on-screen player, a read sprite of his team with one of his frames (within +-3 samples) within
6 pixels of his spot (recall); read sprites matching no player (extra)."""
import json
import os
TEST_GAME = int(os.environ.get('TEST_GAME', 0))   # the game read; everything learnt comes from the others
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parents[3]          # the repository
sys.path.insert(0, str(V / "analysis/vision"))
sys.path.insert(0, str(V / "tools"))
import inverse as INV
import camera_track as C
import rink_render
import replay_pack
import imageio_ffmpeg
from systems import genesis

HOME = Path.home() / "Documents/NHL94 Viewer"
# Any synced Genesis game (2026-11-20, for the learning plan): NHL94_INV_VIDEO, _ROM, _CAM (an every-frame camera
# track), _STATIC, _TIMELINE, _TRANS_GAMES (comma-separated match names the transition table is learnt from; default
# the timeline's other games). Unset: BOS-CHI as before.
VIDEO = Path(os.environ.get("NHL94_INV_VIDEO", HOME / "replay/nhl94_playoffs-261113-133619.mkv"))
ROMP = Path(os.environ.get("NHL94_INV_ROM", HOME / "roms/7a7a876f_a738ea1c.bin"))
ROM = ROMP.read_bytes()
cam = np.load(os.environ.get("NHL94_INV_CAM", Path.home() / "NHL94_scoring_map/runs/vision/report_boschi/camera.npz"))["rows"]
assert len(cam) < 2 or cam[1][0] - cam[0][0] == 1, "the reader needs a camera track with every frame"
static = np.load(os.environ.get("NHL94_INV_STATIC", Path.home() / "NHL94_scoring_map/runs/vision/static_boschi.npz"))["mask"]
tl = json.loads(Path(os.environ.get("NHL94_INV_TIMELINE", str(VIDEO) + ".timeline.json")).read_text())
FPS = tl["fps"]
FIRST_F, COUNT = int(sys.argv[1]) if len(sys.argv) > 1 else 6200, int(sys.argv[2]) if len(sys.argv) > 2 else 1800


def load(name):
    s = (HOME / "matches" / f"{name}.js").read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


rinkC = C.Rink(ROMP)
rink = rink_render.render(ROM).astype(np.int16)
ice = rinkC.ice()
# the ice the reader reads: with NHL94_INV_BEHIND, grown BEHIND_ROWS pixels down the screen (a carrier behind the bottom
# net is drawn over the boards and glass below the ice's edge; at the top net his feet stay on the ice)
BEHIND_ROWS = int(os.environ.get("NHL94_INV_BEHIND", "0"))
BEHIND_HALF = int(os.environ.get("NHL94_INV_BEHIND_HALF", "48"))   # columns either side of the nets' centre line
ICE_READ = ice.copy()
if BEHIND_ROWS:
    grown = ice.copy()
    for k in range(1, BEHIND_ROWS + 1):
        grown[k:] |= ice[:-k]
    cx = ice.shape[1] // 2                      # the nets' centre line in the padded render
    lower = np.zeros_like(ice)
    lower[ice.shape[0] // 2:, cx - BEHIND_HALF:cx + BEHIND_HALF] = True     # the bottom end only
    ICE_READ = ice | (grown & lower)
# NHL94_INV_GROW=N (2026-11-24): the read area grown N pixels past the ice's edge all round (a skater knocked down at
# the boards or behind a net is drawn over them: of ten missed falls in BOS-WPG game 1, nine lay a quarter or more
# outside the ice)
GROW = int(os.environ.get("NHL94_INV_GROW", "0"))
if GROW:
    _g = ICE_READ.copy()
    for _k in range(1, GROW + 1):
        _g[_k:] |= ICE_READ[:-_k]
        _g[:-_k] |= ICE_READ[_k:]
        _g[:, _k:] |= ICE_READ[:, :-_k]
        _g[:, :-_k] |= ICE_READ[:, _k:]
    ICE_READ = _g
# NHL94_INV_LEARNT=learnt_bottom.npz (learn_bg.py): read the strip behind the bottom net only where the video shows one
# clear colour there (60%+ of the frames of the other games); the flickering net mesh and posts stay unread
LEARNT = os.environ.get("NHL94_INV_LEARNT")
if LEARNT:
    _d = np.load(Path(__file__).with_name(LEARNT))
    _ok = (_d["seen"] >= 30) & (_d["share"] >= float(os.environ.get("NHL94_INV_LEARNT_SHARE", "0.6")))
    ICE_READ = ICE_READ.copy()
    ICE_READ[_d["ys"][_ok], _d["xs"][_ok]] = True
st = np.pad(static, 1)
st = st[:-2, :-2] | st[1:-1, 1:-1] | st[2:, 2:] | st[:-2, 2:] | st[2:, :-2]


# A stream (2026-11-23, a Twitch video with no recording): NHL94_INV_CROP=X,Y,W,H (stream_locate.py) cuts the game's
# picture out and resizes it to 256 x 224, as camera_track does; a timeline with no games ({"fps": 30, "games": [],
# "segments": []}) reads with nothing to score against (transitions from NHL94_INV_TRANS_GAMES).
CROP = [int(v) for v in os.environ["NHL94_INV_CROP"].split(",")] if os.environ.get("NHL94_INV_CROP") else None
if CROP:
    C.CROP = CROP
_VF = ["-vf", ("crop={2}:{3}:{0}:{1},scale=256:224:flags=" + os.environ.get("NHL94_INV_SCALE", "area")).format(*CROP)] if CROP else []
VW = 320                                            # the video's width (2026-11-21: a 256-wide recording was read as 320)
try:
    if CROP:
        VW = 256
        raise KeyError
    import re as _re
    _p = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-i", str(VIDEO)], capture_output=True)
    VW = int(_re.search(rb"Video:.*?, (\d{3,4})x224", _p.stderr).group(1))
except Exception:
    pass


def frames(first, count):
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "fatal", "-threads", "1", "-i", str(VIDEO),
           "-an", "-fps_mode", "passthrough", *_VF, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = 0
    try:
        while n < first + count:
            b = p.stdout.read(VW * 224 * 3)
            if len(b) < VW * 224 * 3:
                break
            if n >= first:
                yield n, np.frombuffer(b, np.uint8).reshape(224, VW, 3).astype(np.int16)
            n += 1
    finally:
        p.kill()


def measure_dx(n=30, near=3):
    """The rink's column for screen column 0 is hpos + RINK_DX. It depends on how the video was made (2026-11-21: 64
    on BOS-CHI's 320-wide stretch, columns picked back by INV.native; 63 on BOS-TOR's native 256-wide video, where
    64 had put every frame one pixel off and the reader found two thirds of the players). Measured here at the start:
    n placed frames spread over the stretch read, each frame's coded colours against the drawn rink's at each shift
    (the best of the camera frames within +-near, against a seek landing a frame or two off); the shift with the
    highest mean share wins. A best share under 0.85 is warned about: the camera or the video is wrong, not the
    reader's business to guess."""
    want = [fi for fi in range(FIRST_F, min(FIRST_F + COUNT, len(cam))) if cam[fi][4] and cam[fi][3] >= 0.8]
    if not want:
        return 64 if VW == 320 else 63, {}
    picks = sorted({want[int(k * (len(want) - 1) / max(n - 1, 1))] for k in range(n)})
    rc = INV.code(rink)
    shares = {dx: [] for dx in range(61, 67)}
    for fi in picks:
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "fatal", "-threads", "1", "-ss",
               f"{fi / FPS:.4f}", "-i", str(VIDEO), "-an", "-frames:v", "1", *_VF, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        b = subprocess.run(cmd, capture_output=True).stdout
        if len(b) < VW * 224 * 3:
            continue
        fc = INV.code(INV.native(np.frombuffer(b[:VW * 224 * 3], np.uint8).reshape(224, VW, 3).astype(np.int16))[:186])
        for dx in shares:
            best = 0.0
            for g in range(fi - near, fi + near + 1):
                if 0 <= g < len(cam) and cam[g][4]:
                    hpos, vpos = int(cam[g][1]), int(cam[g][2])
                    bg = rc[256 - vpos:256 - vpos + 186, hpos + dx:hpos + dx + 256]
                    if bg.shape == fc.shape:
                        best = max(best, float((bg == fc).mean()))
            shares[dx].append(best)
    mean = {dx: float(np.mean(v)) for dx, v in shares.items() if v}
    if not mean:
        return 64 if VW == 320 else 63, {}
    return max(mean, key=mean.get), mean


if os.environ.get("NHL94_INV_DX"):
    RINK_DX, _dx_shares = int(os.environ["NHL94_INV_DX"]), {}
    print("rink line-up: RINK_DX", RINK_DX, "(NHL94_INV_DX)", flush=True)
else:
    RINK_DX, _dx_shares = measure_dx()
    print("rink line-up: RINK_DX", RINK_DX, "shares", {k: round(v, 3) for k, v in _dx_shares.items()}, flush=True)
    _rest = sorted((v for k, v in _dx_shares.items() if k != RINK_DX), reverse=True)
    if _dx_shares and (_dx_shares[RINK_DX] < 0.85 or (_rest and _dx_shares[RINK_DX] - _rest[0] < 0.03)):
        print(f"WARNING: the best rink line-up matches {_dx_shares[RINK_DX]:.1%} of pixels"
              f"{f', the next {_rest[0]:.1%}' if _rest else ''}: check the camera track and the video before trusting "
              "this read (2026-11-21: BOS-TOR 0.937 against 0.852, BOS-CHI 0.891 against 0.800)", flush=True)


def view(fi):
    hpos, vpos = int(cam[fi][1]), int(cam[fi][2])
    bg = INV.code(rink[256 - vpos:256 - vpos + INV.H_PLAY, hpos + RINK_DX:hpos + RINK_DX + 256])
    u, v = hpos + RINK_DX + C.PAD, 256 - vpos + C.PAD
    ign = st[v:v + INV.H_PLAY, u:u + 256] | ~ICE_READ[v:v + INV.H_PLAY, u:u + 256]
    ign = ign | INV.box_mask(ign.shape)
    return hpos, vpos, bg, ign


# the teams from colour coverage (the first frame with blobs)
teams = genesis.read_teams(ROMP)
_pool = [g for g in os.environ.get("NHL94_INV_TRANS_GAMES", "").split(",") if g]
trans = INV.transitions([load(n) for n in _pool] if _pool else [load(n) for i, n in enumerate(tl["games"]) if i != TEST_GAME])
print("transitions from", len(trans), "frames", flush=True)

# the truth: video frame per sample of game 1
m = load(tl["games"][TEST_GAME]) if tl["games"] else None      # None: a video with no recording
N = len(m["t"]) if m else 0
vf = np.full(N, np.nan)
for sg in tl["segments"]:
    if sg[2] != TEST_GAME:
        continue
    for q in range(N):
        v = sg[0] + (m["t"][q] - sg[3]) * (1 + replay_pack.rate(sg)) / 1000
        if sg[0] <= v <= sg[1]:
            vf[q] = v * FPS


def truth_near(fi, R=3):
    qs = np.nonzero(np.abs(vf - fi) < 1.0)[0]
    if not len(qs):
        return None
    q = int(qs[0])
    out = {}
    for k in range(12):
        if m["role"][q * 12 + k] not in "012345":
            continue
        frs = {int(m["frame"][((q + d) * 12 + k) * 3:((q + d) * 12 + k) * 3 + 3], 16) for d in range(-R, R + 1) if 0 <= q + d < N}
        x, y = m["pos"][(q * 12 + k) * 2], m["pos"][(q * 12 + k) * 2 + 1]
        out[k] = (frs, x, y)
    return out


def truth_puck(fi):
    qs = np.nonzero(np.abs(vf - fi) < 1.0)[0]
    if not len(qs):
        return None
    q = int(qs[0])
    return [tuple(m["puck"][3 * (q + d):3 * (q + d) + 3]) for d in range(-3, 4) if 0 <= q + d < N]


def choose_palettes(img, bg, ign):
    bl = INV.blobs((img != bg) & ~ign, 60)
    codes = np.concatenate([img[b[:, 0], b[:, 1]] for b in bl]) if bl else np.zeros(0, int)
    best = {}
    for side in (0, 1):
        sc = []
        for t, team in enumerate(teams):
            pal = {int(INV.hexcode(c)) for c in team["palettes"][side][8:]}     # the team's own colours
            sc.append((np.isin(codes, list(pal)).mean() if len(codes) else 0, t))
        sc.sort(reverse=True)
        best[side] = sc[:3]
    return best


if __name__ == '__main__':
    LOG = []
    PRED = [None]
    PS = dict(on=0, read=0, pos_ok=0, z_ok=0, air=0, air_ok=0)
    PLOG = []
    reader = None
    stats = dict(frames=0, players=0, found=0, frame_right=0, extra=0)
    t0 = time.time()
    for fi, fr in frames(FIRST_F, COUNT):
        if cam[fi][3] < 0.8:
            continue
        hpos, vpos, bg, ign = view(fi)
        img = INV.code(INV.native(fr)[:INV.H_PLAY])
        if reader is None:
            import hud_read
            import game_events as GE
            hud = hud_read.Reader(Path.home() / "NHL94_scoring_map/runs/vision/hud_native.npz")
            hud.fit(GE.sample_frames(VIDEO))                     # the templates' geometry against this video
            for _, sq in C.frames(VIDEO, fi, 1):
                vis_ab, home_ab = hud.read_teams(sq)
            by_abbr = {t["abbr"][:3].upper().ljust(3): i for i, t in enumerate(teams)}
            print("score box:", vis_ab, "(visitors),", home_ab, "(home)", flush=True)
            home, away = by_abbr[home_ab], by_abbr[vis_ab]
            print("teams:", teams[home]["name"], "(home),", teams[away]["name"], "(away); match file:", m.get("team1"), m.get("team2"), flush=True)
            if "--truth-palettes" in sys.argv:
                print("palettes from the match file (testing the tracking alone)", flush=True)
                S = INV.Sprites(ROM, m["palettes"][0], m["palettes"][1])
            else:
                S = INV.Sprites(ROM, teams[home]["palettes"][0], teams[away]["palettes"][1])
            reader = INV.Reader(S, trans)
            reader.max_new = 40
            first_read = True
        img_m = np.where(ign, -1, img)
        read = reader.step(img_m, bg, cam=(hpos, vpos))
        if '--tracker' in sys.argv:
            if not hasattr(reader, 'pt'):
                reader.pt = INV.PuckTracker(reader)
            pk = reader.pt.step(img_m, bg, (hpos, vpos))
        else:
            pk = INV.read_puck_all(reader, img_m, bg, read, pred=PRED[0])
        PRED[0] = (pk[0] - pk[3], pk[1]) if pk else None
        tp = truth_puck(fi)
        if tp:
            x, y, z = tp[3] if len(tp) > 3 else tp[0]
            sx, sy = 128 + x - hpos, 112 - y + vpos
            if 8 < sx < 248 and 24 < sy < 176:
                PS["on"] += 1
                qs = np.nonzero(np.abs(vf - fi) < 1.0)[0]
                tmode = 'truth carried' if m['owner'][int(qs[0])] >= 0 else 'truth loose'
                PS[tmode] = PS.get(tmode, 0) + 1
                if pk:
                    PS["read"] += 1
                    errs = [(abs(pk[1] - (128 + a - hpos)) + abs(pk[0] - (112 - b + vpos)), abs(pk[3] - c)) for a, b, c in tp]
                    e_pos, e_z = min(errs)
                    PS["pos_ok"] += e_pos <= 4
                    PS["z_ok"] += e_pos <= 4 and e_z <= 2
                    PS["air"] += z > 3
                    PS["air_ok"] += z > 3 and e_pos <= 4 and e_z <= 2
                    PS[pk[5]] = PS.get(pk[5], 0) + 1
                    PS[pk[5] + " ok"] = PS.get(pk[5] + " ok", 0) + (e_pos <= 4)
                    PS[tmode + ' ok'] = PS.get(tmode + ' ok', 0) + (e_pos <= 4)
                    q0 = int(qs[0])
                    PLOG.append(dict(fi=fi, how=pk[5], read=(int(pk[0]), int(pk[1])), truth=(round(112 - b + vpos) if False else None),
                                     tp=[(round(128 + a - hpos), round(112 - b + vpos), c) for a, b, c in tp], owner=m['owner'][q0],
                                     ok=bool(e_pos <= 4), err=int(e_pos)))
        reader.max_new = 6
        tr = truth_near(fi)
        if tr is None:
            continue
        LOG.append(dict(fi=fi, hpos=hpos, vpos=vpos, read=[[int(v) if not isinstance(v, float) else round(v, 2) for v in r] for r in read],
                        truth={k: [sorted(f), round(128 + x - hpos), round(120 - y + vpos)] for k, (f, x, y) in tr.items()}))
        stats["frames"] += 1
        used = set()
        for k, (frs, x, y) in tr.items():
            sx, sy = 128 + x - hpos, 112 - y + vpos          # measured: the sprite's point is 8 rows above 120 - Y + Vpos
            if not (8 < sx < 248 and 24 < sy < 176):
                continue
            stats["players"] += 1
            team = 0 if k < 6 else 1
            near = [(abs(r[4] - sx) + abs(r[3] - sy), i, r) for i, r in enumerate(read) if r[0] == team and i not in used
                    and abs(r[4] - sx) <= 4 and abs(r[3] - sy) <= 4]
            if near:
                near.sort()
                _, i, r = near[0]
                used.add(i)
                stats["found"] += 1
                stats["frame_right"] += r[1] in frs
        stats["extra"] += sum(1 for i, r in enumerate(read) if i not in used and 8 < r[4] < 248 and 24 < r[3] < 176)
        if stats["frames"] % 25 == 0:
            el = time.time() - t0
            print(f"frame {fi}: {stats}, {stats['frames'] / el:.2f} frames a second", flush=True)
    Path("track_log.json").write_text(json.dumps(LOG))
    Path(f"puck_log_{FIRST_F}.json").write_text(json.dumps(PLOG))
    el = time.time() - t0
    print("final", stats, f"{stats['frames'] / el:.2f} frames a second")
    print("puck:", PS, f"read {PS['read'] / max(1, PS['on']):.1%} of frames with it on screen, within 4 px {PS['pos_ok'] / max(1, PS['on']):.1%}, height within 2 too {PS['z_ok'] / max(1, PS['on']):.1%}")
    print(f"players found {stats['found'] / max(1, stats['players']):.1%}, their frame right {stats['frame_right'] / max(1, stats['found']):.1%}, "
          f"extra read sprites per frame {stats['extra'] / max(1, stats['frames']):.2f}")
