"""How a team's puck carriers end their carries, by zone (2026-11-11, chunk 3: targets for a bot that plays like
people). For people's games (Documents\\NHL94 Viewer, people on both sides), the bot's team (bot_record.py's matches)
and computer games (cvc_record.py's), Genesis or SNES: every carry (one skater holding the puck, `owner`, at least 6
samples), the zone it began in (tools/export_match.own_end and zone_of), its length in game seconds, and how it ended:
a pass (a `passes` event by him within 3 samples of the end), a shot (`shotList`), else lost / other. Per zone: carries,
the median length, the share ending in a pass / a shot, and passes and shots per 10 game s of carrying; the passes'
directions; shots by kind and distance band. A carry by a person's skater (ctrl) and by a computer teammate are kept
apart for people's games and the bot's team.

python analysis/carry_profile.py BOT_MATCHES CVC_MATCHES [genesis|snes]"""
import json
import math
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from export_match import own_end, zone_of  # noqa: E402

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"
GAME_S = 2.5          # game seconds a second (real)


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def carries(m, teams):
    """(team, person, zone, game seconds, end, pass dir) for each carry by a team in `teams`."""
    T, own, ctrl, N = m["t"], m["owner"], m["ctrl"], len(m["t"])
    passes = defaultdict(list)              # by (team, roster index): `idx` is the roster place, the samples'
    for p in m.get("passes", []):           # `roster` gives each record's (a base-36 character a record)
        passes[(p["team"], p["idx"])].append(p)
    shots = defaultdict(list)
    for s in m.get("shotList", []):
        shots[(s["team"], s["idx"])].append(s)
    ros = m["roster"]
    ends = {}
    out = []
    i = 0
    while i < N:
        o = own[i]
        if o is None or o < 0:
            i += 1
            continue
        j = i
        while j + 1 < N and own[j + 1] == o:
            j += 1
        team = 0 if o < 6 else 1
        if team in teams and j - i >= 6:
            e = ends.get((team, i // 600))
            if e is None:
                e = next((x for q in range(i, min(N, i + 600)) for x in [own_end(m, q, team)] if x is not None), None)
                ends[(team, i // 600)] = e
            if e is not None:
                P = m["puck"]
                zone = zone_of(P[3 * i + 1], -e)
                secs = (T[j] - T[i]) / 1000 * GAME_S
                end, d = "lost", None
                key = (team, int(ros[12 * j + o], 36))
                p = next((p for p in passes.get(key, []) if j - 3 <= p["f"] <= j + 3), None)
                s = next((s for s in shots.get(key, []) if j - 3 <= s["f"] <= j + 3), None)
                if s:
                    end = "shot:" + (s.get("type") or s.get("kind"))
                    d = math.hypot(s["x"], abs(s["y"]) - 264)
                elif p:
                    end, d = "pass", p.get("dir")
                out.append((team, bool(ctrl[i] >> o & 1), zone, secs, end, d))
        i = j + 1
    return out


def report(name, rows):
    print(f"\n### {name}: {len(rows)} carries")
    print("| Zone | Carries | Median length (game s) | Pass % | Shot % | Lost / other % | Passes a 10 game s | Shots a 10 game s |")
    print("|---|---|---|---|---|---|---|---|")
    for z in ("def", "neu", "att"):
        R = [r for r in rows if r[2] == z]
        if not R:
            continue
        secs = sum(r[3] for r in R)
        np_ = sum(r[4] == "pass" for r in R)
        ns = sum(r[4].startswith("shot") for r in R)
        print(f"| {z} | {len(R)} | {st.median(r[3] for r in R):.1f} | {100 * np_ / len(R):.0f} | {100 * ns / len(R):.0f} | "
              f"{100 * (len(R) - np_ - ns) / len(R):.0f} | {10 * np_ / secs:.2f} | {10 * ns / secs:.2f} |")
    dirs = Counter(r[5] for r in rows if r[4] == "pass")
    if dirs:
        print("Passes by direction: " + ", ".join(f"{k} {100 * v / sum(dirs.values()):.0f}%" for k, v in dirs.most_common()))
    kinds = Counter()
    for r in rows:
        if r[4].startswith("shot"):
            band = "close (<60)" if r[5] < 60 else "slot (60-110)" if r[5] < 110 else "point (110+)"
            kinds[(band, r[4][5:])] += 1
    if kinds:
        tot = sum(kinds.values())
        print("Shots by distance and kind: " + ", ".join(f"{b} {k} {100 * v / tot:.0f}%" for (b, k), v in sorted(kinds.items())))


def main():
    bots, cvc = Path(sys.argv[1]), Path(sys.argv[2])
    system = sys.argv[3] if len(sys.argv) > 3 else "genesis"
    groups = defaultdict(list)
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != system or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        js = f.with_name(f.name.replace(".summary.json", ".js"))
        if not js.exists():
            continue
        for r in carries(load(js), (0, 1)):
            groups["people: the person's skater" if r[1] else "people: computer teammates"].append(r)
    for f in sorted(bots.glob(f"bot_{system}_*.js")):
        for r in carries(load(f), (0,)):
            groups["bot: the bot's skater" if r[1] else "bot: computer teammates"].append(r)
    for f in sorted(cvc.glob(f"cvc_{system}_*.js")):
        groups["computer games"] += carries(load(f), (0, 1))
    for name in ("people: the person's skater", "people: computer teammates", "bot: the bot's skater",
                 "bot: computer teammates", "computer games"):
        if groups[name]:
            report(name, groups[name])


if __name__ == "__main__":
    main()
