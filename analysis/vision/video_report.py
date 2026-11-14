"""A game report from a Genesis video alone (2026-11-14; the video reader's product so far).

For each game in the video: the teams (the score box's abbreviations), the final, the goals (team, period, clock),
zone time (from the camera) and possession (from the puck-possession star), with possession in each team's attacking
zone. Every step is one process at a time in gentle mode, and keeps its result in OUT (rerunning skips what exists):
  camera.npz        camera_track (every STEP-th frame)
  events.json       game_events (games, teams, goals, whistles, the held readings)
  static.npz        sprites.learn_static (the nets, the logo, the benches)
  poss_<k>.json     possession per game, with that game's home and visitors
  report.json / report.md

python analysis/vision/video_report.py VIDEO OUT [--crop=X,Y,W,H] [--rom=ROM] [--step=N] [--check]
  --check: each game against its recording (tools/video_sync.py's timeline), side by side"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import camera_track as C  # noqa: E402

HERE = Path(__file__).resolve().parent


def opt(name, default=None):
    return next((a.split("=", 1)[1] for a in sys.argv if a.startswith(f"--{name}=")), default)


def check(video, report):
    """Each game against its recording (the games tools/video_sync.py placed, in order): live play, zone shares from
    the puck's own Y, possession by the last carrier's team (the puck's +$61: the star stays on him while it's loose)
    and attack-zone possession, over the recording's live samples (play screen, the clock running)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import os
    from export_match import Capture
    import zone_time as Z
    home_dir = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    P = 0xB04A + 0x80 * 14

    def s16(v):
        return v - 65536 if v & 0x8000 else v
    for name, r in zip(tl["games"], report):
        c = Capture(home_dir / "captures" / name)
        z, poss, att, n = {1: 0, 0: 0, -1: 0}, [0, 0], [0, 0], 0
        for i in range(c.count):
            if c.byte(i, 0xFFF7) != 0 or c.byte(i, 0xC2EA) & 1:
                continue
            n += 1
            zz = Z.zone(s16(c.word(i, P + 0x14)), c.word(i, 0xC466))
            z[zz] += 1
            t = 0 if c.byte(i, P + 0x61) < 6 else 1
            poss[t] += 1
            if (t == 0 and zz == 1) or (t == 1 and zz == -1):
                att[t] += 1
        secs = c.ms(c.count - 1) / 1000 * 2.5 * n / c.count
        per = secs / max(n, 1)
        h, v = r["home"], r["visitors"]
        r["recording"] = {"name": name, "live_game_seconds": round(secs),
                          "zone_share": {h + " attacking": round(100 * z[1] / n, 1), "neutral": round(100 * z[0] / n, 1),
                                         v + " attacking": round(100 * z[-1] / n, 1)},
                          "possession_share": {h: round(100 * poss[0] / n, 1), v: round(100 * poss[1] / n, 1)},
                          "attack_zone_possession_s": {h: round(att[0] * per), v: round(att[1] * per)}}


def main():
    import lowload
    lowload.gentle()
    video, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rom = Path(opt("rom", Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"))
    crop = opt("crop")
    if crop:
        C.CROP = tuple(int(v) for v in crop.split(","))
        C.OFF_X = 64
    fps = C.video_fps(video)
    step = int(opt("step", max(1, round(fps / 15))))
    templates = Path.home() / "NHL94_scoring_map" / "runs" / "vision" / "hud_native.npz"

    cam_path = out / "camera.npz"
    if not cam_path.exists():
        print("camera ...", flush=True)
        rows = C.track(video, rom, 0, None, step)
        np.savez_compressed(cam_path, rows=rows, step=np.array(step))
    cams = {int(r[0]): r for r in np.load(cam_path)["rows"]}
    fr = sorted(cams)
    cstep = int(np.median(np.diff(fr[:5000]))) if len(fr) > 1 else step   # each camera row stands for cstep frames
    # (a track made elsewhere, as BOS-CHI's every-frame one, needn't have STEP's spacing: 2026-11-14 fix)

    ev_path = out / "events.json"
    if not ev_path.exists():
        print("score boxes ...", flush=True)
        import game_events as G
        rows = G.held(G.read_video(video, templates, max(1, round(fps / 10))))
        games = G.events(rows, fps)
        from collections import Counter
        for g in games:
            pairs = Counter((v, h) for n, v, h in G.TEAM_READS if g["start_frame"] <= n <= g["end_frame"])
            if pairs:
                (g["visitors"], g["home"]), _ = pairs.most_common(1)[0]
        ev_path.write_text(json.dumps({"video": str(video), "fps": fps, "crop": C.CROP, "games": games,
                                       "readings": rows}, indent=1))
    ev = json.loads(ev_path.read_text())

    st_path = out / "static.npz"
    if not st_path.exists():
        print("static sprites ...", flush=True)
        import sprites as S
        S.learn_static(video, cam_path, rom, st_path, step=max(step, round(fps / 3)))
    static = np.load(st_path)["mask"]

    import possession as PO
    import zone_time as Z
    live = Z.live_frames(ev["readings"], fps)
    report = []
    for k, g in enumerate(ev["games"]):
        if g["end_frame"] - g["start_frame"] < 60 * fps or not g.get("home"):
            continue                                 # a fragment, or teams never read
        pp = out / f"poss_{k}.json"
        if not pp.exists():
            print(f"possession, game {k + 1} ({g['visitors']} at {g['home']}) ...", flush=True)
            seq, obs = PO.run(video, cams, static, g["home"], g["visitors"], g["start_frame"],
                              g["end_frame"] - g["start_frame"] + 1, step, rom)
            pp.write_text(json.dumps({"frames": [s[0] for s in seq], "obs": obs}))
        pd = json.loads(pp.read_text())
        team = dict(zip(pd["frames"], PO.team_path(pd["obs"])))
        z = {"home att": 0, "neutral": 0, "home def": 0}
        poss = {0: 0, 1: 0}
        att_poss = {0: 0, 1: 0}
        n_live = 0
        for n, r in cams.items():
            if not (g["start_frame"] <= n <= g["end_frame"]) or n not in live or not r[4]:
                continue
            zz = Z.zone(r[2] + Z.OFFSET, live[n])
            z[{1: "home att", 0: "neutral", -1: "home def"}[zz]] += 1
            n_live += 1
            t = team.get(n)
            if t is not None:
                poss[t] += 1
                if (t == 0 and zz == 1) or (t == 1 and zz == -1):
                    att_poss[t] += 1
        secs = n_live * cstep / fps * 2.5
        share = lambda x: round(100 * x / max(n_live, 1), 1)  # noqa: E731
        n_poss = poss[0] + poss[1]                   # frames with a possession reading (every STEP-th frame)
        pshare = lambda x: round(100 * x / max(n_poss, 1), 1)  # noqa: E731
        pstep = n_live * cstep / max(n_poss, 1)      # the frames each possession reading stands for
        report.append({
            "game": len(report) + 1, "visitors": g["visitors"], "home": g["home"], "final": g["final"],
            "overtime": any(p["period"] == 3 for p in g["periods"]),
            "goals": [{"team": g["home"] if x["team"] == "home" else g["visitors"], "period": x["period"] + 1,
                       "clock": f"{x['clock'] // 60}:{x['clock'] % 60:02d}"} for x in g["goals"]],
            "live_game_seconds": round(secs),
            "zone_share": {g["home"] + " attacking": share(z["home att"]), "neutral": share(z["neutral"]),
                           g["visitors"] + " attacking": share(z["home def"])},
            "possession_share": {g["home"]: pshare(poss[0]), g["visitors"]: pshare(poss[1])},
            "attack_zone_possession_s": {g["home"]: round(att_poss[0] * pstep / fps * 2.5),
                                         g["visitors"]: round(att_poss[1] * pstep / fps * 2.5)}})
    if "--check" in sys.argv:
        check(video, report)
    (out / "report.json").write_text(json.dumps(report, indent=1))
    lines = [f"# {video.name}: games read from the video", ""]
    for r in report:
        lines.append(f"## Game {r['game']}: {r['visitors']} {r['final'][0]}, {r['home']} {r['final'][1]}"
                     + (" (OT)" if r["overtime"] else ""))
        lines.append("")
        lines.append("Goals: " + ", ".join(f"{x['team']} P{x['period']} {x['clock']}" for x in r["goals"]))
        lines.append("")
        rc = r.get("recording")
        if rc:
            lines.append(f"| | {r['home']} (video) | {r['visitors']} (video) | {r['home']} (recording) | "
                         f"{r['visitors']} (recording) |")
            lines.append("|---|---|---|---|---|")
        else:
            lines.append("| | " + r["home"] + " | " + r["visitors"] + " |")
            lines.append("|---|---|---|")

        def row(label, key, suffix=""):
            a, b = r[key], rc[key] if rc else None
            hk = r["home"] + (" attacking" if key == "zone_share" else "")
            vk = r["visitors"] + (" attacking" if key == "zone_share" else "")
            out = f"| {label} | {a[hk]}{suffix} | {a[vk]}{suffix} |"
            if b:
                out += f" {b[hk]}{suffix} | {b[vk]}{suffix} |"
            lines.append(out)
        row("possession", "possession_share", "%")
        row("in its attacking zone (share of live play)", "zone_share", "%")
        row("attack-zone possession (game seconds)", "attack_zone_possession_s")
        lines.append(f"\nLive play {r['live_game_seconds']} game seconds"
                     + (f" (recording {rc['live_game_seconds']})" if rc else "")
                     + f"; neutral zone {r['zone_share']['neutral']}%"
                     + (f" (recording {rc['zone_share']['neutral']}%)" if rc else "") + ".\n")
    (out / "report.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
