"""Live stats and events for a stream overlay (2026-11-13, for a league member streaming a Genesis series from OBS).

The helper's local live mode (`--live-local`: live_broadcast's pipeline written into <NHL94_HOME>/live instead of S3)
calls `write` after each update with the whole match converted so far. It writes:
- live/stats.json   {status, game, updated, period, clock, teams: [{name, abbr, stats}, ...], events: [...]}
                    for overlay.html (an OBS Browser Source);
- live/obs/*.txt    one small text file per number and team (home_shots.txt, away_xg.txt ...), the team names, and the
                    latest events (event_last.txt, events_recent.txt), for OBS Text sources ("Read from file").

The team numbers come from season.py's per-game summary (the same as the season page), the events from the converter's
lists. Every event has its game time (period and clock), its kind and a line of text; the overlay or OBS picks which kinds
to show. Kinds: goal, big_save, post, big_hit, hit, injury, penalty, giveaway (a giveaway that led to a goal), fight, streak.
A big save is a saved shot of xG BIG_SAVE_XG or more.

python tools/live_overlay.py MATCH.js [OUT]   writes stats.json and obs/ for a finished match file (a test)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import season  # noqa: E402

BIG_SAVE_XG = 0.30
RECENT = 5           # lines in events_recent.txt
KEEP = 40            # events kept in stats.json (and the last 10 plain hits, which run to about 40 a game)
PERIODS = ("1st", "2nd", "3rd", "OT")


def clock_text(secs):
    return f"{secs // 60}:{secs % 60:02d}"


def when(m, f):
    f = max(0, min(f, len(m["t"]) - 1))
    p, c = m["period"][f], m["clock"][f]
    return PERIODS[min(p, 3)], c


def who(m, team, idx):
    try:
        p = m["rosters"][team][idx]
        return f"#{p['num']} {p['name']}"
    except (IndexError, KeyError, TypeError):
        return "?"


def abbr(m, team):
    a = m.get("abbr")
    if a and len(a) > team:
        return a[team]
    return (m.get("team1"), m.get("team2"))[team] or ("HOME", "AWAY")[team]


def team_stats(m, s, team):
    """The numbers for one team from season.summarize's team summary (and the other team's, for save %)."""
    t, o = s["teams"][team], s["teams"][1 - team]
    pct = lambda a, b: round(100 * a / b) if b else None
    xg = t.get("xg") or [0, 0, 0, 0]
    sa, ga = t.get("sa", 0), t.get("ga", 0)
    zone = t.get("attackZone", 0)
    return {
        "goals": t.get("gf", 0),
        "shots": t.get("sog", 0),
        "attempts": t.get("att", 0),
        "shooting_pct": pct(t.get("gf", 0), t.get("sog", 0)),
        "save_pct": round(100 * (sa - ga) / sa, 1) if sa else None,
        "xg": round(xg[0], 2),
        "hits": t.get("checks", 0),
        "knockdowns": sum(1 for h in m.get("hits", []) if h.get("team") == team and h.get("outcome") == "knocked down"),
        "faceoffs": f"{t.get('fow', 0)}/{t.get('fo', 0)}",
        "faceoff_pct": pct(t.get("fow", 0), t.get("fo", 0)),
        "passes": f"{t.get('passMade', 0)}/{t.get('passTried', 0)}",
        "pass_pct": pct(t.get("passMade", 0), t.get("passTried", 0)),
        "power_play": f"{t.get('ppg', 0)}/{t.get('ppTries', 0)}",
        "penalties": t.get("pen", 0),
        "pim": t.get("pim", 0),
        "attack_zone": clock_text(zone) if isinstance(zone, int) else zone,
        "one_timers": f"{t.get('oneTimerGoals', 0)}/{t.get('oneTimerTried', 0)}",
        "breakaways": f"{t.get('breakGoals', 0)}/{t.get('breakTried', 0)}",
        "posts": t.get("posts", 0),
        "takeaways": t.get("take", 0),
        "giveaways": t.get("give", 0),
    }


def events(m):
    """Every notable event so far, in order."""
    out = []

    def add(f, kind, team, text):
        per, c = when(m, f)
        out.append({"f": f, "kind": kind, "team": team, "period": per, "clock": clock_text(c),
                    "text": f"{per} {clock_text(c)} - {text}"})

    # Goals, with the game situation (tying, go-ahead) and unanswered streaks.
    score, run_team, run = [0, 0], None, 0
    for g in sorted(m.get("goals", []), key=lambda g: g["f"]):
        team = g["team"]
        before = score[:]
        score[team] += 1
        tags = [k for k in g.get("kinds", []) if k]
        if g.get("ownGoal") is not None:
            tags.append("own goal")
        sit = ""
        if score[team] == score[1 - team]:
            sit = "tying goal"
        elif before[team] == before[1 - team]:
            sit = "go-ahead goal"
        assists = ", ".join(who(m, team, a[0]).split(" ", 1)[-1] for a in g.get("assists", []))
        text = (f"GOAL {abbr(m, team)}: {who(m, team, g['scorer'])}" + (f" ({g['goals']})" if g.get("goals") else "")
                + (f", from {assists}" if assists else ", unassisted") + (f" [{', '.join(tags)}]" if tags else "")
                + (f" - {sit}" if sit else "") + f" - {abbr(m, 0)} {score[0]}-{score[1]} {abbr(m, 1)}")
        add(g["f"], "goal", team, text)
        run = run + 1 if run_team == team else 1
        run_team = team
        if run >= 3:
            add(g["f"], "streak", team, f"{abbr(m, team)}: {run} unanswered goals")

    # Big saves: saved shots of high expected-goal value.
    for s in m.get("shotList", []):
        if s.get("result") == "save" and (s.get("xg") or 0) >= BIG_SAVE_XG:
            team = s["team"]
            goalie = who(m, 1 - team, s["goalie"]) if s.get("goalie") is not None else "the goalie"
            add(s["f"], "big_save", 1 - team, f"BIG SAVE: {goalie} ({abbr(m, 1 - team)}) robs {who(m, team, s['idx'])}"
                + f" (xG {s['xg']:.2f})")

    # Posts: the shot just before each post.
    shots = sorted(m.get("shotList", []), key=lambda s: s["f"])
    for pf in m.get("posts", []) if isinstance(m.get("posts"), list) else []:
        s = next((s for s in reversed(shots) if s["f"] <= pf and m["t"][pf] - m["t"][s["f"]] <= 1500), None)
        if s:
            add(pf, "post", s["team"], f"OFF THE POST: {who(m, s['team'], s['idx'])} ({abbr(m, s['team'])})")

    # Hits: the rarer outcomes (upended, into the boards or the bench: about 7 a game) are big hits; plain knockdowns
    # (about 40 a game in the recorded Genesis games) their own kind, for an overlay that wants them all.
    big = {"upended": "upends", "into the boards": "puts {} into the boards", "into the bench": "sends {} into the bench"}
    for h in m.get("hits", []):
        t, o = h["team"], h.get("outcome")
        victim = who(m, 1 - t, h["on"])
        if o in big:
            verb = big[o]
            text = f"{who(m, t, h['by'])} ({abbr(m, t)}) " + (verb.format(victim) if "{}" in verb else f"{verb} {victim}")
            add(h["f"], "big_hit", t, "BIG HIT: " + text)
        elif o == "knocked down":
            add(h["f"], "hit", t, f"HIT: {who(m, t, h['by'])} ({abbr(m, t)}) knocks down {victim}")

    for i in m.get("injuries", []):
        if i.get("atStart"):
            continue
        t = i["team"]
        add(i["f"], "injury", t, f"INJURY: {who(m, t, i['idx'])} ({abbr(m, t)}) out for the {i.get('out', 'period')}")

    # A penalty's name and minutes from the match's rules (by its code); its `secs` is the clock when it was called.
    rules = m.get("rules") or {}
    for p in m.get("penalties", []):
        rule = rules.get(str(p.get("code"))) or rules.get(p.get("code")) or {}
        name = rule.get("name", "Penalty") if isinstance(rule, dict) else "Penalty"
        mins = rule.get("min") if isinstance(rule, dict) else None
        t = p["team"]
        add(p.get("called", p["f"]), "penalty", t, f"PENALTY {abbr(m, t)}: {who(m, t, p['idx'])}, {name}"
            + (f" ({mins} min)" if mins else ""))

    for x in m.get("turnovers", []):
        if x.get("kind") == "giveaway" and x.get("goalAfter"):
            t = x["from"]
            add(x["f"], "giveaway", t, f"COSTLY GIVEAWAY: {who(m, t, x['giver'])} ({abbr(m, t)}), {x.get('how', '')}, "
                "and it's in the net")

    for fgt in m.get("fights", []) or []:
        f = fgt.get("f", 0)
        add(f, "fight", None, "FIGHT!" + (f" {fgt['text']}" if fgt.get("text") else ""))

    # Ids that stay the same from update to update (an event found late, a save known once the shot is over, must not
    # move the others: the overlay highlights an id it hasn't seen).
    out.sort(key=lambda e: e["f"])
    for e in out:
        e["id"] = f"{e['kind']}-{e['f']}-{e['team']}"
    return out


def build(m, status="live"):
    s = season.summarize(m, m.get("name", "live"))
    last = len(m["t"]) - 1
    per, c = when(m, last)
    ev = events(m)
    return {"status": status, "game": m.get("name"), "system": m.get("system"),
            "period": per, "clock": clock_text(c),
            "teams": [{"name": (m.get("team1"), m.get("team2"))[t], "abbr": abbr(m, t), "stats": team_stats(m, s, t)}
                      for t in (0, 1)],
            "events": sorted([e for e in ev if e["kind"] != "hit"][-KEEP:] + [e for e in ev if e["kind"] == "hit"][-10:],
                             key=lambda e: e["f"])}


def write(folder, m, status="live"):
    """stats.json and the OBS text files, written whole each time (a reader never sees half a file)."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    data = build(m, status)
    put(folder / "stats.json", json.dumps(data, separators=(",", ":")))
    obs = folder / "obs"
    obs.mkdir(parents=True, exist_ok=True)
    for t, side in ((0, "home"), (1, "away")):
        team = data["teams"][t]
        put(obs / f"{side}_name.txt", team["name"] or "")
        put(obs / f"{side}_abbr.txt", team["abbr"] or "")
        for k, v in team["stats"].items():
            put(obs / f"{side}_{k}.txt", "" if v is None else str(v))
    h, a = data["teams"]
    put(obs / "score.txt", f"{h['abbr']} {h['stats']['goals']} - {a['stats']['goals']} {a['abbr']}")
    ev = data["events"]
    quiet =[e for e in ev if e["kind"] not in ("hit", "big_hit")]   # hits (about 7 big and 40 plain a game) would fill
    put(obs / "event_last.txt", quiet[-1]["text"] if quiet else "")    # these: only in last_big_hit.txt
    put(obs / "events_recent.txt", "\n".join(e["text"] for e in quiet[-RECENT:]))
    for kind in ("goal", "big_save", "big_hit", "penalty"):
        last = [e for e in ev if e["kind"] == kind]
        put(obs / f"last_{kind}.txt", last[-1]["text"] if last else "")
    return data


def put(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("live_test")
    d = write(out, season.load_match(src), "final")
    print(json.dumps({k: d[k] for k in ("period", "clock")}), [t["stats"] for t in d["teams"]])
    for e in d["events"][-12:]:
        print(e["kind"], "|", e["text"])
