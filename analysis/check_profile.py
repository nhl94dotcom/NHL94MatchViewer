"""How a side checks, per game (2026-11-12, for the scripted bot's checking gap: about 19 checks a game against the expert
coaches' 31). From match files' `checkAttempts` (export_match.find_check_attempts: every check started, with its target,
whether he had the puck, the zone, the result) and `hits`, Genesis, for:
- people: the recorded games with people on both sides (Documents\\NHL94 Viewer), each side;
- the bot: bot_record.py's games (the bot is Home), and the computer it played (Away);
- the computer against itself (cvc_record.py's games), each side.
Per side and game: attempts, the share that landed (any result but a whiff), on the carrier or not, by zone, the
game's checks (stats) and the knockdowns (hits), and the result categories.

python analysis/check_profile.py BOT_MATCHES [CVC_MATCHES]"""
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis"))
from export_match import STAT_FIELDS  # noqa: E402

PEOPLE = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents" / "NHL94 Viewer")) / "matches"


def load(f):
    t = f.read_text(encoding="utf-8")
    return json.loads(t[t.index("{"):t.rindex("}") + 1])


def side_row(m, team):
    ca = [c for c in m.get("checkAttempts", []) if c["team"] == team]
    hits = [h for h in m.get("hits", []) if h["team"] == team]
    last = m["stats"]["home" if team == 0 else "away"][-1]
    r = {"attempts": len(ca), "landed": sum(c["result"] != "whiff" for c in ca),
         "on the carrier": sum(bool(c.get("carrier")) for c in ca),
         "landed on the carrier": sum(bool(c.get("carrier")) and c["result"] != "whiff" for c in ca),
         "game's checks": last[STAT_FIELDS.index("checks")], "knockdowns": sum(h.get("outcome") == "knocked down" for h in hits),
         "hits": len(hits)}
    for z in ("own", "neutral", "att"):
        zc = [c for c in ca if c.get("zone") == z]
        r[f"attempts {z}"] = len(zc)
        r[f"landed {z}"] = sum(c["result"] != "whiff" for c in zc)
    kd = [h for h in hits if h.get("outcome") == "knocked down"]
    me = [h for h in kd if h.get("human")]
    r["knockdowns, controlled"] = len(me)
    r["knockdowns, teammates"] = len(kd) - len(me)
    r["controlled: thrown (shoulder, hip, cross-check)"] = sum(h.get("how") != "check" for h in me)
    r["controlled: plain contact"] = sum(h.get("how") == "check" for h in me)
    r["controlled: on the carrier"] = sum(bool(h.get("onCarrier")) for h in me)
    r["controlled: off the puck"] = sum(not h.get("onCarrier") for h in me)
    r["attempts that hit"] = sum(c["result"] == "hit" for c in ca)
    r["results"] = Counter(c["result"] for c in ca)
    r["outcomes"] = Counter(h.get("outcome") for h in hits)
    return r


def summarize(name, rows):
    if not rows:
        return
    keys = [k for k in rows[0] if k not in ("results", "outcomes")]
    mean = {k: st.mean(r[k] for r in rows) for k in keys}
    print(f"\n{name}: {len(rows)} side-games")
    print(f"  attempts {mean['attempts']:.1f}, landed {mean['landed']:.1f} ({100 * mean['landed'] / max(mean['attempts'], 1e-9):.0f}%), "
          f"game's checks {mean["game's checks"]:.1f}, knockdowns {mean['knockdowns']:.1f}, hits {mean['hits']:.1f}")
    print(f"  on the carrier {mean['on the carrier']:.1f} ({100 * mean['on the carrier'] / max(mean['attempts'], 1e-9):.0f}% of attempts), "
          f"landed {100 * mean['landed on the carrier'] / max(mean['on the carrier'], 1e-9):.0f}%; "
          f"off the puck {mean['attempts'] - mean['on the carrier']:.1f}, landed "
          f"{100 * (mean['landed'] - mean['landed on the carrier']) / max(mean['attempts'] - mean['on the carrier'], 1e-9):.0f}%")
    print("  by zone (attempts, landed %): " + "; ".join(
        f"{z} {mean[f'attempts {z}']:.1f} ({100 * mean[f'landed {z}'] / max(mean[f'attempts {z}'], 1e-9):.0f}%)" for z in ("own", "neutral", "att")))
    print("  " + ", ".join(f"{k} {mean[k]:.1f}" for k in keys if k.startswith(("knockdowns,", "controlled:", "attempts that"))))
    res, out = Counter(), Counter()
    for r in rows:
        res.update(r["results"])
        out.update(r["outcomes"])
    n = len(rows)
    print("  results a game: " + ", ".join(f"{k} {v / n:.1f}" for k, v in res.most_common()))
    print("  hit outcomes a game: " + ", ".join(f"{k} {v / n:.1f}" for k, v in out.most_common()))


def main():
    from recorded_coaches import ratings
    rate = ratings("genesis")
    people, strong, rest = [], [], []
    for f in sorted(PEOPLE.glob("*.summary.json")):
        d = json.loads(f.read_text())
        if d.get("system") != "genesis" or (d.get("seconds") or 0) < 600 or not all(d.get("humans") or [False]):
            continue
        js = f.with_name(f.name.replace(".summary.json", ".js"))
        if js.exists():
            m = load(js)
            rs = rate.get(f.name.replace(".summary.json", ""), [None, None])
            for team in (0, 1):
                r = side_row(m, team)
                people.append(r)
                if rs[team] is not None:
                    (strong if rs[team] >= 80 else rest).append(r)
    summarize("People (Genesis, people on both sides)", people)
    summarize("  coaches rated 80%+ against an average coach", strong)
    summarize("  coaches rated under 80%", rest)
    if len(sys.argv) > 1:
        bot, cpu = [], []
        for f in sorted(Path(sys.argv[1]).glob("bot_*.js")):
            m = load(f)
            bot.append(side_row(m, 0))
            cpu.append(side_row(m, 1))
        summarize("The bot (Home)", bot)
        summarize("The computer against the bot (Away)", cpu)
    if len(sys.argv) > 2:
        cvc = []
        for f in sorted(Path(sys.argv[2]).glob("cvc_genesis_*.js")):
            m = load(f)
            if m.get("system", "genesis") == "genesis" or "genesis" in f.name:
                cvc += [side_row(m, 0), side_row(m, 1)]
        summarize("The computer against itself", cvc)


if __name__ == "__main__":
    main()
