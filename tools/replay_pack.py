"""A replay pack: the stream overlay's numbers and events for a series played back from video (2026-11-13).

A streamer plays a video of games already played and recorded (RetroArch's own recording of the session) and wants the
live overlay (overlay.html, tools/live_overlay.py) to show what it would have shown, in step with the video. The
helper's recordings keep only live play (pauses, instant replays, intermissions and menus are left out) and no
clock-of-day times, so the video is matched to the recordings first (tools/video_sync.py: a timeline of video stretches,
each one game's frames) and then every second of the video gets the overlay's data as it stood at that moment of play:

  cut(m, f)    the match file as it stood at sample f: per-sample arrays cut there, events kept once their outcome is
               known (a shot when it is resolved, a pass when it is known, a goal at the goal), the game's own stat
               snapshots up to f. season.summarize and live_overlay.team_stats then give the numbers.
  reveal(e)    when an overlay event (live_overlay.events of the whole match) is known: a goal at the goal, a big save
               or miss when the shot is over, a costly giveaway at the goal it led to, the others at their own frame.

The pack (replay_data.js beside replay.html) holds, per video second, the game and both teams' numbers, and per game
the events with the video second each is known. replay.html follows the video's position (OBS's WebSocket; without
it, a clock started when the page loads) and shows the state for that second (less `delay` seconds, for the live
feel).

The pack's folder: replay.html (overlay.html with replay_settings.js loaded first: OBS's "Local file" Browser Source
takes no address choices), replay_settings.js (the choices, edited in Notepad), replay_data.js and "Replay guide.txt"
(docs/REPLAY_GUIDE.md).

python tools/replay_pack.py TIMELINE.json OUT_FOLDER [--step S]     (TIMELINE from tools/video_sync.py)"""
import bisect
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_overlay  # noqa: E402
import season  # noqa: E402

NOT_SAMPLES = {"name", "positions", "nets", "abbr", "rosters", "palettes", "team1", "team2", "rom", "system"}


def known_at(e):
    """The sample at which an event of the match file is known (its outcome included)."""
    return max(v for v in (e.get("f", 0), e.get("known"), e.get("resolved")) if isinstance(v, (int, float)))


def cut(m, f):
    """The match as it stood at sample f (inclusive)."""
    n = len(m["t"])
    out = {}
    for k, v in m.items():
        if k in NOT_SAMPLES or not isinstance(v, (list, str)):
            out[k] = v
            continue
        r = len(v) / n
        if v and r >= 1 and r == int(r) and r <= 64:
            out[k] = v[:int(r) * (f + 1)]
        elif v and isinstance(v[0], dict) and "f" in v[0]:
            out[k] = [e for e in v if known_at(e) <= f]
        elif v and isinstance(v[0], list) and v[0] and isinstance(v[0][0], int) and k in ("aim", "locked", "work", "fast"):
            out[k] = [e for e in v if e[0] <= f]
        elif k == "posts":
            out[k] = [p for p in v if p <= f]
        else:
            out[k] = v
    if f < n - 1:
        out.pop("shootout", None)   # a season shootout's result (the final score) only once the game is over
    st = m.get("stats")
    if isinstance(st, dict) and isinstance(st.get("f"), list):
        j = bisect.bisect_right(st["f"], f)
        out["stats"] = {**st, "f": st["f"][:j], "home": st["home"][:j], "away": st["away"][:j]}
    return out


def reveal(m, ev):
    """The sample at which an overlay event is known."""
    if ev["kind"] in ("big_save", "big_miss"):
        s = next((s for s in m.get("shotList", []) if s["f"] == ev["f"]), None)
        return known_at(s) if s else ev["f"]
    if ev["kind"] == "giveaway":
        goals = sorted(g["f"] for g in m.get("goals", []) if g["f"] >= ev["f"])
        return goals[0] if goals else ev["f"]
    return ev["f"]


def state(m, f, all_events, status="live"):
    """The overlay's stats.json at sample f: the numbers from the cut match, the events known by then."""
    c = cut(m, f)
    s = season.summarize(c, m.get("name", "replay"))
    per, clk = live_overlay.when(m, f)
    ev = [e for e in all_events if e["reveal"] <= f]
    keep = sorted([e for e in ev if e["kind"] != "hit"][-live_overlay.KEEP:] + [e for e in ev if e["kind"] == "hit"][-10:],
                  key=lambda e: e["f"])
    return {"status": status, "game": m.get("name"), "system": m.get("system"), "period": per,
            "clock": live_overlay.clock_text(clk),
            "teams": [{"name": (m.get("team1"), m.get("team2"))[t], "abbr": live_overlay.abbr(m, t),
                       "stats": live_overlay.team_stats(c, s, t)} for t in (0, 1)],
            "events": [{k: v for k, v in e.items() if k != "reveal"} for e in keep]}


def game_events(m):
    ev = live_overlay.events(m)
    for e in ev:
        e["reveal"] = reveal(m, e)
    return ev


def rate(seg):
    """A segment's drift: video frames per recording frame, less 1 (the two clocks differ by about 0.06%)."""
    return seg[4] if len(seg) > 4 else 0.0


def at_ms(seg, v):
    """The recording's time (ms) at video second v of a segment [v0, v1, game, ms0, drift]."""
    return seg[3] + (v - seg[0]) * 1000 / (1 + rate(seg))


def build_pack(timeline, matches_dir, step=1.0):
    """The replay data: per video second (step), the game and both teams' numbers; per game, the events with the
    video second each is known. timeline: {"duration": s, "games": [match names], "segments": [[v0, v1, game index,
    ms0], ...]}: video seconds v0-v1 show game `index` from its recording's live time ms0 on, at real speed."""
    games = [season.load_match(Path(matches_dir) / f"{g}.js") for g in timeline["games"]]
    segs = sorted(timeline["segments"])
    keys = None
    out_games = []
    for gi, m in enumerate(games):
        ev = game_events(m)
        mine = [s for s in segs if s[2] == gi]
        for e in ev:
            ms = m["t"][min(e["reveal"], len(m["t"]) - 1)]
            seg = next((s for s in mine if s[3] <= ms <= at_ms(s, s[1])), None)
            if seg is None:   # in a stretch the video doesn't show: at the next one that does
                seg = next((s for s in mine if s[3] >= ms), mine[-1] if mine else None)
                e["v"] = round(seg[0], 2) if seg and seg[3] >= ms else round(seg[1], 2) if seg else 0
            else:
                e["v"] = round(seg[0] + (ms - seg[3]) / 1000 * (1 + rate(seg)), 2)
        out_games.append({"game": m.get("name"), "abbr": [live_overlay.abbr(m, 0), live_overlay.abbr(m, 1)],
                          "events": [{k: v for k, v in e.items() if k not in ("reveal", "f")} for e in ev]})
    seconds, last, cache = [], None, {}
    n = int(timeline["duration"] / step) + 1
    for i in range(n):
        v = i * step
        seg = next((s for s in segs if s[0] <= v < s[1]), None)
        if seg:
            m = games[seg[2]]
            f = max(0, bisect.bisect_right(m["t"], at_ms(seg, v)) - 1)
            last = (seg[2], f)
        elif last is not None:   # a pause, a replay, an intermission, the menus: as it stood
            prev = max((s for s in segs if s[1] <= v), key=lambda s: s[1])
            m = games[prev[2]]
            last = (prev[2], max(0, bisect.bisect_right(m["t"], at_ms(prev, prev[1])) - 1))
        if last is None:
            seconds.append(None)
            continue
        if last not in cache:
            gi, f = last
            st = state(games[gi], f, [])
            if keys is None:
                keys = list(st["teams"][0]["stats"])
            cache[last] = [gi] + [[t["stats"].get(k) for k in keys] for t in st["teams"]]
        seconds.append(cache[last])
    return {"keys": keys or [], "step": step, "games": out_games, "seconds": seconds,
            "video": timeline.get("video"), "duration": timeline.get("duration")}   # the overlay checks OBS's length


SETTINGS = """// Settings for the replay overlay (replay.html). Change the text between the quotes and save; then in OBS
// select the Browser Source and click "Refresh" (under the preview). The choices are the same as the live overlay's:
// see "Replay guide.txt".
window.NHL94_SETTINGS = {
  replay: "1",
  // The numbers, in order, separated by commas (the list is in the guide).
  stats: "shots,xg,hits,faceoffs,power_play,save_pct",
  // The events shown (goal, big_save, big_miss, post, injury, penalty, giveaway, streak, big_hit, hit).
  events: "goal,big_save,big_miss,post,injury,penalty,giveaway,streak",
  layout: "panel",      // panel, bar or ticker
  recent: "4",          // how many event lines
  side: "right",        // right or left
  scale: "1",           // bigger: 1.3, smaller: 0.8
  score: "1",           // 0 hides the score
  // Following the video through OBS's WebSocket (recommended): the name of the Media Source playing the video,
  // exactly as in OBS's Sources list, and the WebSocket password (OBS: Tools > WebSocket Server Settings >
  // Show Connect Info). With obs: "" the overlay's clock starts when the page loads instead.
  obs: "NHL94 video",
  obspw: "",
  delay: "0",           // seconds behind the video: 0 shows things as they happen, 3 feels like the live overlay
  offset: "0"           // seconds: + if the overlay is late, - if it is early
};
"""


def write_pack(timeline, out, step=1.0, matches=None, video_path=None):
    """The folder the streamer gets: replay.html (overlay.html loading replay_settings.js first), replay_settings.js,
    replay_data.js and the guide."""
    home = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
    root = Path(__file__).resolve().parents[1]
    out.mkdir(parents=True, exist_ok=True)
    pack = build_pack(timeline, matches or home / "matches", step)
    (out / "replay_data.js").write_text("window.NHL94_REPLAY = " + json.dumps(pack, separators=(",", ":")) + ";\n",
                                        encoding="utf-8")
    page = (root / "overlay.html").read_text(encoding="utf-8")
    tag = '<script src="replay_settings.js"></script>\n'
    at = page.index("<script>\n// The address's choices")
    page = page[:at] + tag + page[at:]
    (out / "replay.html").write_text(page, encoding="utf-8")
    if not (out / "replay_settings.js").exists():   # an existing one holds someone's choices and password
        (out / "replay_settings.js").write_text(SETTINGS, encoding="utf-8")
    mmss = lambda v: f"{int(v // 60)}:{int(v % 60):02d}"
    vfile = video_path if video_path and Path(video_path).exists() else None
    size = f", {Path(vfile).stat().st_size:,} bytes" if vfile else ""
    lines = [f"This pack is for the video: {timeline.get('video', '?')} ({mmss(timeline['duration'])} long{size}).",
             "Use that file as it is: the overlay warns if the video playing in OBS is a different length.", "",
             "The games in it (video time: first faceoff - final horn), home team first:"]
    for gi, g in enumerate(pack["games"]):
        segs = [s for s in timeline["segments"] if s[2] == gi]
        last = next((r for r in reversed(pack["seconds"]) if r and r[0] == gi), None)
        score = f"{last[1][pack['keys'].index('goals')]}-{last[2][pack['keys'].index('goals')]}" if last else "?"
        lines.append(f"  Game {gi + 1}: {g['abbr'][0]} {score} {g['abbr'][1]}   {mmss(segs[0][0])} - {mmss(segs[-1][1])}")
    lines += ["", "Made by tools/replay_pack.py from the helper's recordings, matched to the video by tools/video_sync.py."]
    (out / "About this pack.txt").write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    guide = root / "docs" / "REPLAY_GUIDE.md"
    if guide.exists():   # Notepad-friendly line ends
        (out / "Replay guide.txt").write_bytes(guide.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    return pack


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    step = float(sys.argv[sys.argv.index("--step") + 1]) if "--step" in sys.argv else 1.0
    if "--step" in sys.argv:
        args.remove(sys.argv[sys.argv.index("--step") + 1])
    timeline = json.loads(Path(args[0]).read_text())
    out = Path(args[1])
    pack = write_pack(timeline, out, step)
    print(f"{out}: {len(pack['seconds'])} seconds, {sum(len(g['events']) for g in pack['games'])} events")


if __name__ == "__main__":
    main()
