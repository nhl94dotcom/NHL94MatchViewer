"""A replay pack in one command (2026-11-13): a video of a session in, a zip for the streamer out.

  python tools/make_replay.py VIDEO [MATCH_NAME ...] [--out FOLDER] [--name "NHL94 Replay - BOS-CHI series"]

1. The games: the ones named, else the recorded games, Genesis or SNES (a match file in <home>/matches), whose recordings began
   while the video was running, read from the video's file name (RetroArch's recordings end in -YYMMDD-HHMMSS, the
   moment it started) and its length.
2. tools/video_sync.py places each game in the video (the scroll measure is cached beside the video, so a second run
   takes seconds) and writes <video>.timeline.json.
3. Checks, printed, any failure stops before the zip unless --force:
   - every game found, each stretch at one offset backed by at least MIN_CHECKS matched 10-second stretches;
   - every stretch the video adds (a pause, a replay, a period break, the menus) not looking like live play (the rink
     scrolling: video_sync.play_like), else the step may sit in the wrong place;
   - the goals in order through the video, each inside its game's stretches.
   Plus a sheet of stills a quarter-second before each goal (goals_check.png beside the pack): the on-screen clock should
   read one game second above each goal's time, with the score before the goal. Look at it before sending.
4. tools/replay_pack.py writes the pack (replay.html, replay_data.js, replay_settings.js, the guide, About this
   pack.txt) into FOLDER (default: a folder named after the zip beside the video) and the zip beside it. The zip always
   gets the blank replay_settings.js, never one edited for a test (it would carry an OBS password).

Gentle: one process, ffmpeg at below-normal priority."""
import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay_pack  # noqa: E402
import video_sync  # noqa: E402
from season import load_match  # noqa: E402

MIN_CHECKS = 5          # matched stretches behind a run at one offset
GAP_PLAY = 0.5          # the video's added frames shouldn't look like live play (video_sync.play_like) for more
GAP_MIN = 1.0           # than half of them; steps under a second (a gap in the helper's own sampling) aren't judged


def games_in(video, seconds):
    """The recorded games whose recordings began while the video ran (by the names' minute, a minute's slack)."""
    m = re.search(r"(\d{6})-(\d{6})", Path(video).stem)
    if not m:
        raise SystemExit("can't tell when the video started from its name: name the games")
    start = datetime.strptime(m.group(1) + m.group(2), "%y%m%d%H%M%S")
    end = start + timedelta(seconds=seconds)
    found = []
    for cap in sorted((video_sync.HOME / "captures").iterdir()):
        t = re.match(r"(\d{4}-\d{2}-\d{2}_\d{4})_", cap.name)
        if not t or not (video_sync.HOME / "matches" / f"{cap.name}.js").exists():
            continue
        began = datetime.strptime(t.group(1), "%Y-%m-%d_%H%M")
        info = json.loads((cap / "capture.json").read_text()) if (cap / "capture.json").exists() else {}
        if start - timedelta(minutes=1) <= began <= end:
            found.append(cap.name)
    return found


def skipped(name, ms0, span=6000):
    """Did the recording miss some live play near ms0: its game clock jumping 3+ game seconds from one sample to the next
    while its timer barely moved? Then the video has play the recording hasn't, and the step is right where it is.
    (2026-11-13: TOR-NYI game 2 on the SNES, P2 0:46 to 0:36 between two samples, about 4 s of play not recorded.)"""
    import bisect
    m = load_match(video_sync.HOME / "matches" / f"{name}.js")
    t, clock, period = m["t"], m["clock"], m["period"]
    i, j = max(1, bisect.bisect_left(t, ms0 - span)), bisect.bisect_right(t, ms0 + span)
    return any(period[k] == period[k - 1] and clock[k - 1] - clock[k] >= 3 and t[k] - t[k - 1] < 500
               for k in range(i, min(j, len(t))))


def checks(tl, video):
    """The timeline's checks: (problems, goals [(game, match goal, video second)])."""
    problems = []
    segs = tl["segments"]
    for gi, name in enumerate(tl["games"]):
        mine = [(s, c) for s, c in zip(segs, tl["checks"]) if s[2] == gi]
        if not mine:
            problems.append(f"{name}: not found in the video")
        for s, c in mine:
            if c[0] < MIN_CHECKS:
                problems.append(f"{name}: video {s[0]:.1f}-{s[1]:.1f} s rests on only {c[0]} matched stretches")
    dy, dx, ice = video_sync.measure(video)
    play = video_sync.play_like(dy, dx, ice)
    for a, b in zip(segs, segs[1:]):
        lo, hi = int(a[1] * video_sync.FPS), int(b[0] * video_sync.FPS) + 1
        if hi - lo >= GAP_MIN * video_sync.FPS and float(np.mean(play[lo:hi])) > GAP_PLAY:
            if a[2] == b[2] and skipped(tl["games"][b[2]], b[3]):
                print(f"note: video {a[1]:.1f}-{b[0]:.1f} s is live play the recording missed (its game clock jumps "
                      f"there): the panel holds for those seconds, then catches up")
                continue
            problems.append(f"video {a[1]:.1f}-{b[0]:.1f} s (left out of game {a[2] + 1}'s recording) looks like live "
                            f"play: a replay, or a misplaced step (look at it)")
    goals, last = [], -1.0
    for gi, name in enumerate(tl["games"]):
        m = load_match(video_sync.HOME / "matches" / f"{name}.js")
        mine = [s for s in segs if s[2] == gi]
        for g in sorted(m["goals"], key=lambda g: g["f"]):
            ms = m["t"][g["f"]]
            seg = next((s for s in mine if s[3] <= ms <= replay_pack.at_ms(s, s[1])), None)
            if seg is None:
                problems.append(f"{name}: goal at P{g['period'] + 1} {g['clock'] // 60}:{g['clock'] % 60:02d} "
                                "falls outside the stretches found")
                continue
            v = seg[0] + (ms - seg[3]) / 1000 * (1 + replay_pack.rate(seg))
            if v < last:
                problems.append(f"{name}: goals out of order in the video at {v:.1f} s")
            last = v
            goals.append((gi, m, g, v))
    return problems, goals


def goal_sheet(video, goals, out):
    """Stills a quarter-second before each goal, labelled, six across."""
    import imageio_ffmpeg
    from PIL import Image, ImageDraw
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    vw, vh = video_sync.video_size(video)
    tiles = []
    for gi, m, g, v in goals:
        p = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-threads", "1", "-ss", f"{max(0, v - 0.25):.3f}",
                            "-i", str(video), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0))
        if len(p.stdout) < vw * vh * 3:
            continue
        im = Image.frombytes("RGB", (vw, vh), p.stdout[:vw * vh * 3])
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, vw, 12], fill=(0, 0, 0))
        d.text((2, 1), f"G{gi + 1} P{g['period'] + 1} {g['clock'] // 60}:{g['clock'] % 60:02d} {m['abbr'][g['team']]} "
                       f"goal, video {v:.1f}s", fill=(255, 255, 0))
        tiles.append(im)
    if not tiles:
        return None
    cols = 6
    sheet = Image.new("RGB", (cols * vw, -(-len(tiles) // cols) * vh))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * vw, (i // cols) * vh))
    sheet.save(out)
    return out


def main():
    args = sys.argv[1:]
    opt = lambda k: args[args.index(k) + 1] if k in args else None
    force = "--force" in args
    out_dir, name = opt("--out"), opt("--name")
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i - 1] not in ("--out", "--name"))]
    video = Path(pos[0]).resolve()
    dy, _, _ = video_sync.measure(video)                       # the scroll measure, cached beside the video
    seconds = len(dy) / video_sync.FPS
    names = pos[1:] or games_in(video, seconds)
    if not names:
        raise SystemExit("no recorded games began while the video ran: name them")
    print("games:", ", ".join(names))
    tl = video_sync.timeline(video, names)
    tl_path = video.with_suffix(video.suffix + ".timeline.json")
    tl_path.write_text(json.dumps(tl, indent=1))
    problems, goals = checks(tl, video)
    abbr = []
    for n in names:
        a = re.match(r".*_([A-Z0-9]+)-([A-Z0-9]+)$", n)
        abbr.append("-".join(sorted(a.groups())) if a else n)
    title = name or ("NHL94 Replay - " + (abbr[0] + " series" if len(set(abbr)) == 1 else f"{len(names)} games")
                     + f" {re.sub('_.*', '', names[0])}")
    pack = Path(out_dir) if out_dir else video.parent / title
    pack.mkdir(parents=True, exist_ok=True)
    sheet = goal_sheet(video, goals, pack.parent / f"{title} - goals_check.png")
    print(f"\n{len(goals)} goals placed; stills: {sheet}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  -", p)
        if not force:
            raise SystemExit("not packed (look at the problems; --force packs anyway)")
    else:
        print("checks: all games found, no left-out stretch looks like live play, goals in order")
    replay_pack.write_pack(tl, pack)
    zpath = pack.parent / f"{title}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(pack.iterdir()):
            if f.name == "replay_settings.js":
                z.writestr("NHL94 Replay/replay_settings.js", replay_pack.SETTINGS.replace("\n", "\r\n"))
            else:
                z.write(f, "NHL94 Replay/" + f.name)
    print(f"\npack: {pack}\nzip:  {zpath} ({zpath.stat().st_size // 1024} KB)\nsend the zip and the video ({video.name}, "
          f"{video.stat().st_size // 2**20} MB, uncut). Look at the goal stills first.")


if __name__ == "__main__":
    main()
