"""How a team people play differs from a team the computer plays (2026-11-11, the user: for better simulations and a
bot that plays like people). People: every recorded game in Documents\\NHL94 Viewer (people on both sides; their
season summaries, matches/*.summary.json). Computer: computer-against-computer games recorded as people's are and
converted by the same converter (analysis/scoring_map/cvc_record.py), summarized here by the same tools/season.py
summarize. Per team-game, scaled to 15 minutes (900 game seconds) of play; each measure's mean for people and for the
computer, with standard errors, and the difference; per system. Names nobody.

With BOT_MATCHES_FOLDER (analysis/scoring_map/bot_record.py: the scripted bot on Home against the computer, Genesis):
three more columns, the bot's team, the bot against people, and the computer team it played.

python analysis/team_style_compare.py CVC_MATCHES_FOLDER [BOT_MATCHES_FOLDER]"""
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import season  # noqa: E402

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"


def rows_of(summary):
    """Per team of one game: the measures (None where a game lacks one)."""
    sec = summary.get("seconds") or 900
    k = 900 / sec
    out = []
    for i, t in enumerate(summary["teams"]):
        o = summary["teams"][1 - i]
        att = t.get("att") or 0
        orig = t.get("origin") or [0] * 8
        ent = t.get("entries") or [0] * 5
        shots = t.get("shotMap") or []
        kinds = defaultdict(int)
        dist = []
        for s in shots:
            kinds[s[4]] += 1
            dist.append(math.hypot(s[0], abs(s[1]) - 264))
        pz = t.get("possZones") or [0, 0, 0]
        xg = t.get("xg") or [None, None, None, None]
        r = {
            "goals": t["gf"] * k, "shots on goal": t["sog"] * k, "shot attempts": att * k,
            "xG": xg[0] * k if xg[0] is not None else None,
            "xG a shot attempt": (xg[0] / att) if xg[0] is not None and att else None,
            "shooting % (goals / on goal)": 100 * t["gf"] / t["sog"] if t["sog"] else None,
            "save % (own goalie)": 100 * (1 - o["gf"] / o["sog"]) if o["sog"] else None,
            "median shot distance": st.median(dist) if dist else None,
            "one-timer share of attempts %": 100 * kinds.get("one-timer", 0) / len(shots) if shots else None,
            "slapshot share %": 100 * kinds.get("slapshot", 0) / len(shots) if shots else None,
            "wrist shot share %": 100 * kinds.get("wrist shot", 0) / len(shots) if shots else None,
            "rush share of attempts %": 100 * orig[0] / sum(orig[:4]) if sum(orig[:4]) else None,
            "sustained-pressure share %": 100 * orig[1] / sum(orig[:4]) if sum(orig[:4]) else None,
            "high-danger attempts": t["hd"][0] * k if t.get("hd") else None,
            "rebound attempts": t["reb"][0] * k if t.get("reb") else None,
            "one-timer tries (game stat)": (t.get("oneTimerTried") or 0) * k,
            "breakaways (game stat)": (t.get("breakTried") or 0) * k,
            "odd-man rushes": t["oddMan"][0] * k if t.get("oddMan") else None,
            "possession (game s)": sum(pz) * k, "attacking-zone possession (game s)": pz[0] * k,
            "attack zone time (game stat, s)": (t.get("attackZone") or 0) * k,
            "zone entries": ent[0] * k,
            "carried entries %": 100 * ent[1] / ent[0] if ent[0] else None,
            "passed entries %": 100 * ent[2] / ent[0] if ent[0] else None,
            "dumped entries %": 100 * ent[3] / ent[0] if ent[0] else None,
            "entries leading to a shot %": 100 * ent[4] / ent[0] if ent[0] else None,
            "passes tried": (t.get("passTried") or 0) * k,
            "pass completion %": 100 * t["passMade"] / t["passTried"] if t.get("passTried") else None,
            "body checks (game stat)": t["checks"] * k, "big hits": (t.get("bigHits") or 0) * k,
            "giveaways": t.get("give", 0) * k, "takeaways": t.get("take", 0) * k,
            "faceoffs won %": 100 * t["fow"] / t["fo"] if t.get("fo") else None,
            "penalties": t.get("pen", 0) * k,
            "posts": t.get("posts", 0) * k,
        }
        out.append(r)
    return out


def people_rows(system):
    rows = []
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != system or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        rows += rows_of(d)
    return rows


def cvc_rows(folder, system, prefix="cvc", side=None):
    """side None: both teams; 0 / 1: only that team (the bot's games: 0 the bot, 1 the computer)."""
    rows = []
    for f in sorted(Path(folder).glob(f"{prefix}_{system}_*.js")):
        m = season.load_match(f)
        d = season.summarize(m, f.stem)
        if (d.get("seconds") or 0) < 600:
            continue
        r = rows_of(d)
        rows += r if side is None else [r[side]]
    return rows


def main():
    folder = sys.argv[1]
    bots = sys.argv[2] if len(sys.argv) > 2 else None
    for system in ("genesis", "snes"):
        P, C = people_rows(system), cvc_rows(folder, system)
        B = cvc_rows(bots, system, "bot", 0) if bots else []
        BC = cvc_rows(bots, system, "bot", 1) if bots else []
        if not P or not C:
            print(f"{system}: people {len(P)} team-games, computer {len(C)}: not enough")
            continue
        print(f"\n=== {system}: people {len(P)} team-games, computer {len(C)}" + (f", bot {len(B)}" if B else "")
              + " (a team, 15 minutes of play)")
        print("| Measure | People | Computer | People - computer |"
              + (" Bot | Bot - people | Computer against the bot |" if B else ""))
        print("|---|---|---|---|" + ("---|---|---|" if B else ""))
        vals = lambda R, key: [r[key] for r in R if r[key] is not None]

        def diff(a, b):
            ma, mb = st.mean(a), st.mean(b)
            se = math.hypot(st.stdev(a) / len(a) ** 0.5, st.stdev(b) / len(b) ** 0.5)
            return f"{ma - mb:+.2f} +- {se:.2f}" + (" **" if se and abs(ma - mb) > 2 * se else "")
        for key in P[0]:
            a, b = vals(P, key), vals(C, key)
            if len(a) < 3 or len(b) < 3:
                continue
            line = f"| {key} | {st.mean(a):.2f} | {st.mean(b):.2f} | {diff(a, b)} |"
            if B:
                c, d = vals(B, key), vals(BC, key)
                line += (f" {st.mean(c):.2f} | {diff(c, a)} | {st.mean(d):.2f} |" if len(c) >= 3 and len(d) >= 3
                         else " - | - | - |")
            print(line)


if __name__ == "__main__":
    main()
