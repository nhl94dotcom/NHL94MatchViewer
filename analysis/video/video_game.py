"""One pass over a RetroArch video of Genesis games (2026-10-23): the camera's position up and down the ice every frame
(the rink's cross lines and the rink's row profile: video_lines.py, video_camera.py) and the HUD (video_hud.py: period,
clock, both teams' letters and scores) every HUD_EVERY frames, written as a timeline; then the games in it and, per
game, what the video can say about each team: time with the play in its attacking zone, zone entries, and the goals
(from the score) with how long the play had been in that zone. The score box shows the away team on top; the home team
attacks up the screen in periods 1 and 3 (CLAUDE.md), so the zone is the team's by the period.
Gentle mode.
python analysis/video/video_game.py extract <video.mkv> <font.npz> <rink.png> <timeline.tsv>
python analysis/video/video_game.py games <timeline.tsv> <games.json>"""
import json
import sys
from pathlib import Path

import av
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
import video_camera as VC  # noqa: E402
import video_hud as VH  # noqa: E402
import video_lines as VL  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

HUD_EVERY, OUT_EVERY = 6, 3        # frames (every frame is decoded; the camera is worked out every OUT_EVERY)
MID = 16            # the screen's middle row shows rink y = Vpos + MID
BLUE = 86
HYST = 8            # a zone is entered 8 past the blue line and left 8 short of it (the camera wobbles on the line)
MIN_OUT, MIN_IN = 1.0, 1.0   # s: an entry needs this long outside before and inside after
RUSH_S = 5.0        # a goal this soon after the play entered that zone is off the rush


def extract(video, font, rink_png, out):
    R = VH.Reader(font)
    rink = VC.profile(np.array(Image.open(rink_png))[:, 60:380])
    c = av.open(video)
    v = c.streams.video[0]
    prev, hud = None, None
    with open(out, "w") as f:
        for j, fr in enumerate(c.decode(v)):
            if j % OUT_EVERY:
                continue
            a = fr.to_ndarray(format="rgb24")
            bl, rd = VL.lines(a)
            cands = [r + y - VC.CY for r in bl for y in VC.BLUE] + [r + y - VC.CY for r in rd for y in VC.RED]
            cands = sorted({round(x) for x in cands if VC.VPOS[0] - 5 <= x <= VC.VPOS[1] + 5})
            if cands:
                if len(cands) > 1 or prev is None or abs(cands[0] - prev) > VC.STEP:
                    p = VC.profile(a[:VC.ROWS])

                    def cost(x):
                        top = int(VC.Y_TOP - (x + VC.CY))
                        if top < 0 or top + VC.ROWS > len(rink):
                            return 1e9
                        return np.abs(p - rink[top:top + VC.ROWS]).sum() + (0.01 * abs(x - prev) if prev is not None else 0)
                    prev = min(cands, key=cost)
                else:
                    prev = cands[0]
            if j % HUD_EVERY == 0:
                hud = R.read(a)
            if j % OUT_EVERY == 0:
                h = hud or {}
                f.write("\t".join(str(x) for x in (j, round(fr.time, 3), prev if prev is not None else "",
                                                    h.get("period", ""), h.get("clock", ""), h.get("top", ""),
                                                    h.get("bottom", ""), h.get("top_score", ""), h.get("bottom_score", ""))) + "\n")
            breathe()


def read_timeline(path):
    rows = []
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        num = lambda s: int(float(s)) if s not in ("", "None") else None
        rows.append({"j": int(p[0]), "t": float(p[1]), "cam": num(p[2]), "period": num(p[3]), "clock": num(p[4]),
                     "top": p[5] or None, "bottom": p[6] or None, "ts": num(p[7]), "bs": num(p[8])})
    return rows


def steady(rows, key, n=5):
    """The value of `key` held for n readings in a row (a single misread doesn't count)."""
    out, run, last = [], 0, None
    for r in rows:
        v = r[key]
        run = run + 1 if v == last else 1
        last = v
        out.append(v if run >= n else None)
    return out


def plausible(r):
    """A HUD reading that can be real: period 1-4 (4 is overtime), the clock 0-10 minutes, both scores read. Screens
    without the HUD (intermissions, menus) can read as steady nonsense such as period 7 at 7-7."""
    return r["period"] in (1, 2, 3, 4) and r["clock"] is not None and 0 <= r["clock"] <= 600 \
        and r["ts"] is not None and r["bs"] is not None


def games(timeline, out):
    rows = read_timeline(timeline)
    for r in rows:
        if not plausible(r):
            r["period"] = r["clock"] = r["ts"] = r["bs"] = None
    teams = steady(rows, "top", 10)
    bots = steady(rows, "bottom", 10)
    periods = steady(rows, "period")
    ts, bs = steady(rows, "ts"), steady(rows, "bs")
    found, cur = [], None
    for k, r in enumerate(rows):
        key = (teams[k], bots[k]) if teams[k] and bots[k] else None
        down = cur is not None and ts[k] is not None and bs[k] is not None and \
            (ts[k] < cur["away"] or bs[k] < cur["home"])          # the score went back: a new game
        if key and (cur is None or key != cur["key"]) or down:
            cur = {"key": key or cur["key"], "away_team": (key or cur["key"])[0], "home_team": (key or cur["key"])[1],
                   "away": 0, "home": 0, "rows": [], "last_period": 1, "goals": []}
            found.append(cur)
        if cur is None:
            continue
        cur["rows"].append(k)
        if periods[k]:
            cur["last_period"] = periods[k]
        for side, vals in (("away", ts), ("home", bs)):
            if vals[k] is not None and vals[k] == cur[side] + 1:
                cur["goals"].append({"team": side, "k": k, "period": cur["last_period"], "clock": rows[k]["clock"]})
                cur[side] += 1
            elif vals[k] is not None and cur[side] < vals[k] <= cur[side] + 3:
                for _ in range(vals[k] - cur[side]):  # a jump (the score unread for a while): a goal each, timed here
                    cur["goals"].append({"team": side, "k": k, "period": cur["last_period"], "clock": rows[k]["clock"],
                                         "late": True})
                cur[side] = vals[k]
    result = []
    for g in found:
        if g["away"] + g["home"] == 0 and len(g["rows"]) < 2000:
            continue                                 # a menu or a few seconds of a game
        result.append(summarise(rows, g, periods))
    Path(out).write_text(json.dumps(result, indent=1))
    for g in result:
        print(g["away_team"], g["away"], "at", g["home_team"], g["home"], {k: g[k] for k in ("zone_s", "entries", "goals_rush", "goals_zone")})


def summarise(rows, g, periods):
    """Zone time and entries per team (the play's zone from the camera; only while the clock runs), and the goals."""
    zone_s, entries, in_zone_since = {"home": 0.0, "away": 0.0}, {"home": 0, "away": 0}, {"home": None, "away": None}
    last_clock, last_t, state, out_since, pending = None, None, None, -1e9, None
    rush = {"home": 0, "away": 0}
    zone = {"home": 0, "away": 0}
    goal_ks = {}
    for gl in g["goals"]:
        goal_ks.setdefault(gl["k"], []).append(gl)
    unknown = {"home": 0, "away": 0}
    for k in g["rows"]:
        r = rows[k]
        p = periods[k]
        if r["cam"] is None or p is None:
            continue
        running = r["clock"] is not None and last_clock is not None and r["clock"] < last_clock + 0.5 and \
            (r["clock"] != last_clock or (last_t is not None and r["t"] - last_t < 0.45))
        y = r["cam"] + MID
        home_up = p in (1, 3)
        up, down = ("home", "away") if home_up else ("away", "home")    # who attacks up, who attacks down
        z = state
        if y > BLUE + HYST or (state == up and y > BLUE - HYST):
            z = up
        elif y < -BLUE - HYST or (state == down and y < -BLUE + HYST):
            z = down
        else:
            z = None
        if running and last_t is not None and z:
            zone_s[z] += r["t"] - last_t
        if z != state:
            if z:
                in_zone_since[z] = r["t"]
                if running and r["t"] - out_since >= MIN_OUT:
                    pending = (z, r["t"])            # counted once it has lasted MIN_IN
            else:
                out_since = r["t"]
            state = z
        if pending and state == pending[0] and r["t"] - pending[1] >= MIN_IN:
            entries[pending[0]] += 1
            pending = None
        elif pending and state != pending[0]:
            pending = None
        for gl in goal_ks.get(k, ()):
            since = in_zone_since[gl["team"]]
            if gl.get("late"):
                unknown[gl["team"]] += 1             # found from a jump in the score: when it went in isn't known
            elif state == gl["team"] and since is not None and r["t"] - since <= RUSH_S + 1.5:
                rush[gl["team"]] += 1
            else:
                zone[gl["team"]] += 1
        if r["clock"] is not None:
            last_clock = r["clock"]
        last_t = r["t"]
    return {"away_team": g["away_team"], "home_team": g["home_team"], "away": g["away"], "home": g["home"],
            "start_t": rows[g["rows"][0]]["t"], "end_t": rows[g["rows"][-1]]["t"],
            "zone_s": {k: round(v) for k, v in zone_s.items()}, "entries": entries,
            "goals": [{"team": gl["team"], "period": gl["period"], "clock": gl["clock"], "t": rows[gl["k"]]["t"]} for gl in g["goals"]],
            "goals_rush": rush, "goals_zone": zone, "goals_unknown": unknown}


if __name__ == "__main__":
    gentle()
    if sys.argv[1] == "extract":
        extract(*sys.argv[2:6])
    else:
        games(*sys.argv[2:4])
