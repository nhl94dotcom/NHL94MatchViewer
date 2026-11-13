"""tools/replay_pack.cut against the game's own counters (2026-11-13).

For each match: the replay state at points through the game (every 1500 samples and the last) must show the goals and
shots on goal the game itself counted at that sample (the match file's per-sample score and shots; a season shootout's
winning goal only in the final), and the last state
must equal the live overlay's build of the whole match (numbers and event ids).

python tests/replay_pack_check.py [MATCH_NAME ...]   (default: every match in <home>/matches; NHL94_HOME or
Documents/NHL94 Viewer). Gentle: one process, a short rest between matches."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import live_overlay  # noqa: E402
import replay_pack  # noqa: E402
from season import load_match  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")


def check(path):
    m = load_match(path)
    n = len(m["t"])
    ev = replay_pack.game_events(m)
    bad = []
    for f in list(range(500, n, 1500)) + [n - 1]:
        st = replay_pack.state(m, f, ev)
        h, a = (t["stats"] for t in st["teams"])
        got = (h["goals"], a["goals"], h["shots"], a["shots"])
        game = (m["score"][2 * f], m["score"][2 * f + 1], m["shots"][2 * f], m["shots"][2 * f + 1])
        if f == n - 1 and m.get("shootout"):
            got, game = got[2:], game[2:]   # the final carries the shootout's winning goal; the counter doesn't
        if got != game:
            bad.append(f"sample {f} ({st['period']} {st['clock']}): goals/shots {got}, the game's {game}")
    full, last = live_overlay.build(m), replay_pack.state(m, n - 1, ev)
    if full["teams"] != last["teams"]:
        bad.append("last state's numbers differ from the live build")
    if [e["id"] for e in full["events"]] != [e["id"] for e in last["events"]]:
        bad.append("last state's events differ from the live build")
    return bad


def main():
    names = sys.argv[1:] or sorted(p.name[:-3] for p in (HOME / "matches").glob("*.js") if p.name != "season.js")
    failed = 0
    for name in names:
        bad = check(HOME / "matches" / f"{name}.js")
        failed += bool(bad)
        print(f"{name}: {'OK' if not bad else 'FAILED'}")
        for b in bad:
            print("   ", b)
        time.sleep(0.2)
    print(f"{len(names) - failed} of {len(names)} matches OK")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
