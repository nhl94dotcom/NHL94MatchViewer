"""Games recorded while the scripted bot played (2026-11-12). analysis/scoring_map/bot_live.py plays controller 2 of the
user's RetroArch and logs each play session (start, stop, the bot's version) to
%USERPROFILE%\\NHL94_scoring_map\\bot_live_sessions.jsonl. The helper records those games as it records people's, so
season.py asks here: a game whose recording started during a session (its name's date and time, YYYY-MM-DD_HHMM,
from 10 minutes before the session's start to its stop: a game set up before bot_live.py was started) was played against the bot, on controller 2's side.

bot_session(name) -> the bot's version, or None"""
import datetime
import json
from pathlib import Path

SESSIONS = Path.home() / "NHL94_scoring_map" / "bot_live_sessions.jsonl"
_cache = {"mtime": None, "spans": []}


def spans():
    """[(start, stop, version)] from the session log (a session without its stop runs 6 hours)."""
    try:
        mtime = SESSIONS.stat().st_mtime
    except OSError:
        return []
    if _cache["mtime"] == mtime:
        return _cache["spans"]
    out, open_ = [], None
    for line in SESSIONS.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
            t = datetime.datetime.fromisoformat(e["time"])
        except (ValueError, KeyError):
            continue
        if e.get("event") == "start":
            if open_:
                out.append((open_[0], open_[0] + datetime.timedelta(hours=6), open_[1]))
            open_ = (t, e.get("version"))
        elif e.get("event") == "stop" and open_:
            out.append((open_[0], t, open_[1]))
            open_ = None
    if open_:
        out.append((open_[0], open_[0] + datetime.timedelta(hours=6), open_[1]))
    _cache.update(mtime=mtime, spans=out)
    return out


def bot_session(name):
    """The bot's version if the game `name` (a capture name starting YYYY-MM-DD_HHMM) was recorded during a session."""
    try:
        t = datetime.datetime.strptime(name[:15], "%Y-%m-%d_%H%M")
    except ValueError:
        return None
    for start, stop, version in spans():
        if start - datetime.timedelta(minutes=10) <= t <= stop:
            return version
    return None


if __name__ == "__main__":
    for s in spans():
        print(s)
