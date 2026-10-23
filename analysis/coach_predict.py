"""Which of the coach report's measures go with winning (2026-10-23, the user: what does success look like?). For every
Genesis match file in both game folders where both teams had a person at the controls, each person's measures from
coach_report.measure, as rates; then, game by game, the difference between the two people against the goal difference
and the xG difference (less luck in it). A measure that is about decisions and still goes with the result is one worth
watching. Few games so far: the correlations are rough (with 30 games, about 0.36 is needed to be fairly sure).
python analysis/coach_predict.py   -> reports/coach_predict.md"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, "tools")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from coach_models import Models, matches  # noqa: E402
from share_game import load_js_object  # noqa: E402
import coach_report as CR  # noqa: E402


def r(a, b):
    return a / b if b else None


MEASURES = [  # (label, rate from a Counter) - each a decision or a habit, not the score
    ("picked the best option with the puck", lambda c: r(c["dec_best"], c["dec"])),
    ("value left on the table per decision", lambda c: r(c["dec_lost"], c["dec"])),
    ("xG per shot (his own shots)", lambda c: r(c["sh_xg"], c["sh"])),
    ("shots at a set goalie (share)", lambda c: r(c["sh_set"], c["sh"])),
    ("shots at a goalie 10+ off the line (share)", lambda c: r(c["sh_off10"], c["sh"])),
    ("passes across the slot", lambda c: c["pa_across"]),
    ("attacking-zone passes completed", lambda c: r(c["pa_ok_att"], c["pa_att"])),
    ("passes completed above the league table (per pass)", lambda c: r(c["pr_ok"] - c["pr_exp"], c["pr_n"])),
    ("risky passes in his own end", lambda c: c["pr_risky_def"]),
    ("check attempts landed", lambda c: r(c["b_check_landed"], c["b_check"])),
    ("right C / CB choice", lambda c: r(c["rw_cb_right"], c["rw_cb"])),
    ("recovery bursts that got him goal-side", lambda c: r(c["b_recover_ok"], c["b_recover"])),
    ("last-man check attempts", lambda c: c["b_lastman"]),
    ("steal pokes that won the puck", lambda c: r(c["k_steal_won"], c["k_steal"])),
    ("wasted pokes", lambda c: c["k_wasted"]),
    ("his skater in position (share of time defending)", lambda c: r(c["pos_n_in"], c["pos_n_in"] + c["pos_n_off"] + c["pos_n_up"])),
    ("his skater caught up ice (share of time defending)", lambda c: r(c["pos_n_up"], c["pos_n_in"] + c["pos_n_off"] + c["pos_n_up"])),
    ("switches that took him out of position (share)", lambda c: r(c["sw_bad"], c["sw"])),
    ("back in position within 2 s of a turnover", lambda c: r(c["tr_back_quick"], c["tr_back_n"])),
    ("shots by the best shooter on the ice (share)", lambda c: r(c["ws_top"], c["ws"])),
    ("goalie takeovers", lambda c: c["gt"]),
]


def main():
    M = Models()
    rows = []
    for p in matches():
        m = json.loads(load_js_object(p))
        if m.get("system", "genesis") != "genesis" or "abbr" not in m:
            continue
        people = [any(m["ctrl"][f] >> k & 1 for f in range(0, len(m["t"]), 30) for k in range(tm * 6, tm * 6 + 6)) for tm in (0, 1)]
        if not all(people):
            continue
        cs = [CR.measure(m, tm, M) for tm in (0, 1)]
        N = len(m["t"]) - 1
        gd = m["score"][2 * N] - m["score"][2 * N + 1]
        xg = [sum(s.get("xg") or 0 for s in m.get("shotList", []) if s["team"] == tm) for tm in (0, 1)]
        rows.append((p.stem, gd, xg[0] - xg[1], cs))
        print(p.stem, gd, flush=True)
    out = ["# Which person-level measures go with the result", "",
           f"{len(rows)} Genesis games with a person on each side (both game folders). For each measure: the difference "
           "between the two people in each game, correlated with that game's goal difference and xG difference. "
           "Positive: the person higher on the measure tended to win. With this many games a correlation under about "
           "0.36 could easily be chance.", "",
           "| Measure | with goal difference | with xG difference | games |", "|---|---|---|---|"]
    res = []
    for label, fn in MEASURES:
        d, gd, xd = [], [], []
        for name, g, x, cs in rows:
            a, b = fn(cs[0]), fn(cs[1])
            if a is None or b is None:
                continue
            d.append(a - b)
            gd.append(g)
            xd.append(x)
        if len(d) < 5 or statistics.pstdev(d) == 0:
            continue
        res.append((label, statistics.correlation(d, gd), statistics.correlation(d, xd), len(d)))
    for label, cg, cx, n in sorted(res, key=lambda r: -abs(r[1])):
        out.append(f"| {label} | {cg:+.2f} | {cx:+.2f} | {n} |")
    out += ["", "Games: " + ", ".join(name for name, *_ in rows)]
    path = Path("reports") / "coach_predict.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
