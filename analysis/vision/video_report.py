"""A game report from a Genesis video alone (2026-11-14; the video reader's product so far).

For each game in the video: the teams (the score box's abbreviations), the final, the goals (team, period, clock),
zone time (from the camera), possession (from the puck-possession star), with possession in each team's attacking
zone, and faceoffs (count, winner, zone: see FO_RUN). Every step is one process at a time in gentle mode, and keeps
its result in OUT (rerunning skips what exists):
  camera.npz        camera_track (every STEP-th frame)
  events.json       game_events (games, teams, goals, whistles, the held readings)
  static.npz        sprites.learn_static (the nets, the logo, the benches)
  poss_<k>.json     possession per game, with that game's home and visitors
  report.json / report.md

python analysis/vision/video_report.py VIDEO OUT [--crop=X,Y,W,H] [--rom=ROM] [--step=N] [--soft] [--check]
  --soft: a soft copy (YouTube): possession's star and teams as possession.py --soft reads them
  --check: each game against its recording (tools/video_sync.py's timeline), side by side"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import camera_track as C  # noqa: E402

HERE = Path(__file__).resolve().parent
WIN_SWITCH = 8.0                                     # possession's SWITCH for counting the puck won (see below)


# Faceoffs (2026-11-15; BOS-CHI's soft copy and recording against the recordings' 53 faceoffs): a faceoff is the start
# of a live run (the clock's ticks) of FO_RUN s (real) or more, after a stop of FO_STOP s or more, with the camera lost
# (the game's close-up faceoff box covers the picture) between FO_BOX s before it; the other starts are breaks in the
# ticks (most under 1.5 s long) and restarts after a pause. The winner: the possession star's team seen most 0.2-1.0 s
# after the start, or 0.2-2.5 s if the star isn't seen in that (the recording's copy often finds no star for the first
# second). Before 0.2 s the star is still on the last carrier from before the whistle; the first touch after the drop,
# 0.2-0.5 s real, is the game's faceoff winner in all 53. The zone: the camera's place at the start, against cut-offs
# of its own (FO_END): faceoffs are only at the nine dots, and at the drop the camera sat at -116 to -183 for the bottom
# end zone's dots, 16 to 142 for the centre and neutral dots (one 200), 226 to 256 for the top end zone's; the zone
# edges for play (zone_time, about +-78) put the neutral dots' 142 in an end zone.
FO_RUN, FO_STOP, FO_BOX, FO_READ = 2.0, 2.5, (1.5, 6.0), (0.2, 1.0, 2.5)
FO_END = (-60, 180)


def faceoffs(live, cams, pd, fps, first, last, cam_blue):
    """[(frame, period, zone from the home team's view (1 attacking, 0 neutral, -1 defending), winner 0 / 1 / None)]."""
    import bisect
    from collections import Counter
    import zone_time as Z
    lf = [n for n in sorted(live) if first <= n <= last]
    cf = sorted(n for n in cams if first - 10 * fps <= n <= last)
    runs = []
    for n in lf:
        if runs and n - runs[-1][1] <= fps:
            runs[-1][1] = n
        else:
            runs.append([n, n, runs[-1][1] if runs else None])
    pf, obs = pd["frames"], pd["obs"]
    out = []
    for a, b, before in runs:
        if (b - a) / fps < FO_RUN or (before is not None and (a - before) / fps < FO_STOP):
            continue
        i0, i1 = bisect.bisect_left(cf, a - FO_BOX[1] * fps), bisect.bisect_right(cf, a - FO_BOX[0] * fps)
        if not any(not cams[n][4] for n in cf[i0:i1]):
            continue
        j = bisect.bisect_left(pf, a)
        seen = Counter()
        for end in FO_READ[1:]:                    # the first window, then a longer one if the star wasn't seen in it
            seen = Counter(o for f, o in zip(pf[j:j + 400], obs[j:j + 400])
                           if a + FO_READ[0] * fps <= f <= a + end * fps and o is not None)
            if seen:
                break
        k = bisect.bisect_left(cf, a)
        at = next((cams[n] for n in cf[k:k + 20] if cams[n][4]), None)
        v = at[2] if at is not None else 0
        zone = 0 if FO_END[0] <= v <= FO_END[1] else Z.zone_cam(-1000 if v < FO_END[0] else 1000, live[a], cam_blue)
        out.append((a, live[a], zone, seen.most_common(1)[0][0] if seen else None))
    return out


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
        wins = {t: {"attacking": 0, "neutral": 0, "defending": 0} for t in (0, 1)}
        prev_t = None
        for i in range(c.count):
            if c.byte(i, 0xFFF7) != 0 or c.byte(i, 0xC2EA) & 1:
                continue
            n += 1
            zz = Z.zone(s16(c.word(i, P + 0x14)), c.word(i, 0xC466))
            z[zz] += 1
            t = 0 if c.byte(i, P + 0x61) < 6 else 1
            if prev_t is not None and t != prev_t:
                wins[t][{1: "attacking", 0: "neutral", -1: "defending"}[zz * (1 if t == 0 else -1)]] += 1
            prev_t = t
            poss[t] += 1
            if (t == 0 and zz == 1) or (t == 1 and zz == -1):
                att[t] += 1
        fo_won, fo_zone, n_fo = {0: 0, 1: 0}, {z: {0: 0, 1: 0} for z in ("att", "neu", "def")}, 0
        mp = home_dir / "matches" / f"{name}.js"
        if mp.exists():
            ms = mp.read_text(encoding="utf-8")
            for fo in json.loads(ms[ms.index("{"):ms.rindex("}") + 1]).get("faceoffs", []):
                n_fo += 1
                if fo["won"] in (0, 1):
                    fo_won[fo["won"]] += 1
                    fo_zone[fo["zone"]][fo["won"]] += 1
        secs = c.ms(c.count - 1) / 1000 * 2.5 * n / c.count
        per = secs / max(n, 1)
        h, v = r["home"], r["visitors"]
        r["recording"] = {"name": name, "live_game_seconds": round(secs),
                          "zone_share": {h + " attacking": round(100 * z[1] / n, 1), "neutral": round(100 * z[0] / n, 1),
                                         v + " attacking": round(100 * z[-1] / n, 1)},
                          "possession_share": {h: round(100 * poss[0] / n, 1), v: round(100 * poss[1] / n, 1)},
                          "possession_won": {h: wins[0], v: wins[1]},
                          "attack_zone_possession_s": {h: round(att[0] * per), v: round(att[1] * per)},
                          "faceoffs": n_fo, "faceoffs_won": {h: fo_won[0], v: fo_won[1]},
                          "faceoffs_by_zone": {zn: {h: fo_zone[z][0], v: fo_zone[z][1]} for zn, z in
                                               ((h + " attacking", "att"), ("neutral", "neu"), (v + " attacking", "def"))}}


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
        def rink_at(n):                          # the camera found the rink at or next to this frame
            k = n - n % cstep
            return any(m in cams and cams[m][4] for m in (k - cstep, k, k + cstep))
        rows = G.held(G.read_video(video, templates, max(1, round(fps / 10)), rink_at))
        games = G.events(rows, fps)
        from collections import Counter
        for g in games:
            pairs = Counter((v, h) for n, v, h in G.TEAM_READS if g["start_frame"] <= n <= g["end_frame"])
            if pairs:
                (g["visitors"], g["home"]), _ = pairs.most_common(1)[0]
        ev_path.write_text(json.dumps({"video": str(video), "fps": fps, "crop": C.CROP, "games": games,
                                       "readings": rows, "team_reads": G.TEAM_READS, "ticks": G.CLOCK_TICKS},
                                      indent=1))
    ev = json.loads(ev_path.read_text())

    st_path = out / "static.npz"
    if not st_path.exists():
        print("static sprites ...", flush=True)
        import sprites as S
        S.learn_static(video, cam_path, rom, st_path, step=max(step, round(fps / 3)))
    static = np.load(st_path)["mask"]

    import possession as PO
    import zone_time as Z
    # live play: the clock as read, or its seconds cells ticking (zone_time.live_ticks); on a soft copy the ticks
    # alone (its blurred digits hold one value for seconds while the clock runs; with them, twice the stoppage
    # frames). An older events.json without ticks: the clock as read.
    cam_blue = Z.CAM_BLUE if "--soft" in sys.argv else Z.CAM_BLUE_SHARP
    live = Z.live_frames(ev["readings"], fps)
    if ev.get("ticks"):
        ticks = Z.live_ticks(ev["ticks"], ev["readings"], fps)
        live = ticks if "--soft" in sys.argv else {**live, **ticks}
    team_reads = ev.get("team_reads") or []       # (frame, visitors, home) every few seconds (older events.json: none)
    report = []
    for k, g in enumerate(ev["games"]):
        if g["end_frame"] - g["start_frame"] < 60 * fps or not g.get("home"):
            continue                                 # a fragment, or teams never read
        pp = out / f"poss_{k}.json"
        if not pp.exists():
            print(f"possession, game {k + 1} ({g['visitors']} at {g['home']}) ...", flush=True)
            seq, obs = PO.run(video, cams, static, g["home"], g["visitors"], g["start_frame"],
                              g["end_frame"] - g["start_frame"] + 1, step, rom,
                              soft=PO.SOFT_BLUR if "--soft" in sys.argv else None)
            pp.write_text(json.dumps({"frames": [s[0] for s in seq], "obs": obs}))
        pd = json.loads(pp.read_text())
        team = dict(zip(pd["frames"], PO.team_path(pd["obs"])))
        # another game on screen (an intermission highlight shows its own teams in the score box): the stretches
        # around a team read that isn't this game's pair are left out, to the next read of the right pair
        others = [n for n, v, h in team_reads if g["start_frame"] <= n <= g["end_frame"] and (v, h) != (g["visitors"], g["home"])]
        ours = sorted(n for n, v, h in team_reads if (v, h) == (g["visitors"], g["home"]))
        import bisect
        cut = []
        for n in others:
            i = bisect.bisect_left(ours, n)
            a = ours[i - 1] if i > 0 else g["start_frame"]
            b = ours[i] if i < len(ours) else g["end_frame"]
            cut.append((a, b))
        if cut:
            print(f"  game {k + 1}: {len(others)} reads of other teams; {len(cut)} stretches left out", flush=True)

        def other_game(n):
            return any(a < n < b for a, b in cut)
        z = {"home att": 0, "neutral": 0, "home def": 0}
        poss = {0: 0, 1: 0}
        att_poss = {0: 0, 1: 0}
        n_live = 0
        for n, r in cams.items():
            if not (g["start_frame"] <= n <= g["end_frame"]) or n not in live or not r[4] or other_game(n):
                continue
            zz = Z.zone_cam(r[2], live[n], cam_blue)
            z[{1: "home att", 0: "neutral", -1: "home def"}[zz]] += 1
            n_live += 1
            t = team.get(n)
            if t is not None:
                poss[t] += 1
                if (t == 0 and zz == 1) or (t == 1 and zz == -1):
                    att_poss[t] += 1
        # possession won, by the zone it was won in (the winner's attacking / neutral / defending zone): each change of
        # the possession path in live play, the zone from the camera there
        wins = {t: {"attacking": 0, "neutral": 0, "defending": 0} for t in (0, 1)}
        prev_t = None
        sw = PO.SWITCH                               # a stickier path for counting changes (BOS-CHI: total error 74 ->
        PO.SWITCH = WIN_SWITCH                       # 54 of 315 recorded wins); the shares keep possession's own
        team_w = dict(zip(pd["frames"], PO.team_path(pd["obs"])))
        PO.SWITCH = sw
        for n in sorted(team_w):
            if not (g["start_frame"] <= n <= g["end_frame"]) or n not in live or other_game(n) or n not in cams \
                    or not cams[n][4]:
                continue
            t = team_w[n]
            if prev_t is not None and t != prev_t:
                zz = Z.zone_cam(cams[n][2], live[n], cam_blue) * (1 if t == 0 else -1)
                wins[t][{1: "attacking", 0: "neutral", -1: "defending"}[zz]] += 1
            prev_t = t
        fos = [f for f in faceoffs(live, cams, pd, fps, g["start_frame"], g["end_frame"], cam_blue) if not other_game(f[0])]
        fo_won = {0: 0, 1: 0}
        fo_zone = {z: {0: 0, 1: 0} for z in (1, 0, -1)}
        for _, _, zz, w in fos:
            if w is not None:
                fo_won[w] += 1
                fo_zone[zz][w] += 1
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
            "possession_won": {g["home"]: wins[0], g["visitors"]: wins[1]},
            "attack_zone_possession_s": {g["home"]: round(att_poss[0] * pstep / fps * 2.5),
                                         g["visitors"]: round(att_poss[1] * pstep / fps * 2.5)},
            "faceoffs": len(fos), "faceoffs_won": {g["home"]: fo_won[0], g["visitors"]: fo_won[1]},
            "faceoffs_by_zone": {name: {g["home"]: fo_zone[zz][0], g["visitors"]: fo_zone[zz][1]}
                                 for name, zz in ((g["home"] + " attacking", 1), ("neutral", 0),
                                                  (g["visitors"] + " attacking", -1))}})
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
        for zname in ("attacking", "neutral", "defending"):
            a = r["possession_won"]
            line = f"| puck won in its {zname} zone | {a[r['home']][zname]} | {a[r['visitors']][zname]} |"
            if rc:
                b = rc["possession_won"]
                line += f" {b[r['home']][zname]} | {b[r['visitors']][zname]} |"
            lines.append(line)
        if "faceoffs_won" in r:
            a = r["faceoffs_won"]
            line = f"| faceoffs won (of {r['faceoffs']}) | {a[r['home']]} | {a[r['visitors']]} |"
            if rc and "faceoffs_won" in rc:
                line += f" {rc['faceoffs_won'][r['home']]} (of {rc['faceoffs']}) | {rc['faceoffs_won'][r['visitors']]} |"
            lines.append(line)
            for zname, a in r["faceoffs_by_zone"].items():
                where = "in the neutral zone" if zname == "neutral" else f"in the {zname} zone"
                line = f"| faceoffs won {where} | {a[r['home']]} | {a[r['visitors']]} |"
                if rc and "faceoffs_by_zone" in rc:
                    b = rc["faceoffs_by_zone"][zname]
                    line += f" {b[r['home']]} | {b[r['visitors']]} |"
                lines.append(line)
        lines.append(f"\nLive play {r['live_game_seconds']} game seconds"
                     + (f" (recording {rc['live_game_seconds']})" if rc else "")
                     + f"; neutral zone {r['zone_share']['neutral']}%"
                     + (f" (recording {rc['zone_share']['neutral']}%)" if rc else "") + ".\n")
    (out / "report.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
