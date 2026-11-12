"""The SNES per-player check counts in the recorded games (2026-11-12, for NOSE4Web 5c9609b, which copies the Vault's
PlayerStat_BodyChecks byte for byte: FallDown's `lda tmchecks,y` becomes a jsr that adds 1 to the checker's byte (a3)
at $168E and the hit player's (a2) at $16C2, 26 a team, the roster place read from pnum $12A3 as a word). On every
SNES recording in the game folder:
- whether its ROM counts (the per-player sums equal the team checks at the last sample);
- where it does, at the last sample: each player's $168E against the converter's knockdowns he gave (match `hits`,
  outcome "knocked down", by `by`), and $16C2 against the knockdowns he took (`on`, the other team's hits): the players
  that differ;
- pnum's high byte, every sample, for objects 0-11 (the skaters and goalies): any not 0;
- the penalty log's length PenSumLength $163C, its largest (the counts share PenSum's room from entry 20, $168E).
Aggregates only (no names).

python analysis/snes_bodycheck_recorded.py"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "analysis"))
from export_match import Capture  # noqa: E402
from injury_risk_estimate import HOME  # noqa: E402

GIVEN, TAKEN, PNUM, PENLEN, CHECKS = 0x168E, 0x16C2, 0x12A3, 0x163C, 0x17B6


def main():
    tot = Counter()
    pen_max, high = 0, Counter()
    for summ in sorted((HOME / "matches").glob("*.summary.json")):
        d = json.loads(summ.read_text())
        if d.get("system") != "snes":
            continue
        name = summ.name.replace(".summary.json", "")
        folder = HOME / "captures" / name
        js = HOME / "matches" / f"{name}.js"
        if not folder.exists() or not js.exists():
            continue
        cap = Capture(folder)
        last = cap.count - 1
        tot["games"] += 1
        for i in range(0, cap.count, 6):
            for k in range(12):
                hb = cap.byte(i, PNUM + 2 * k + 1)
                if hb:
                    high[k] += 1
            pen_max = max(pen_max, cap.word(i, PENLEN))
        given = [cap.byte(last, GIVEN + j) for j in range(52)]
        taken = [cap.byte(last, TAKEN + j) for j in range(52)]
        team = [cap.word(last, CHECKS + 2 * s) for s in (0, 1)]
        if [sum(given[:26]), sum(given[26:])] != team or not any(team):
            tot["games without the counts"] += 1
            continue
        tot["games with the counts"] += 1
        t = js.read_text(encoding="utf-8")
        m = json.loads(t[t.index("{"):t.rindex("}") + 1])
        conv_g, conv_t = Counter(), Counter()
        for h in m.get("hits", []):
            if h.get("outcome") != "knocked down":
                continue
            conv_g[26 * h["team"] + h["by"]] += 1
            conv_t[26 * (1 - h["team"]) + h["on"]] += 1
        tot["team checks"] += sum(team)
        tot["taken sums = other team's checks"] += [sum(taken[26:]), sum(taken[:26])] == team
        for j in range(52):
            if given[j] or conv_g[j]:
                tot["players with checks given"] += 1
                tot["given = converter"] += given[j] == conv_g[j]
            if taken[j] or conv_t[j]:
                tot["players with checks taken"] += 1
                tot["taken = converter"] += taken[j] == conv_t[j]
        tot["converter knockdowns"] += sum(conv_g.values())
    print(json.dumps(dict(tot), indent=1))
    print("pnum high byte not 0 (object: samples):", dict(high) or "never")
    print("largest PenSumLength:", pen_max)


if __name__ == "__main__":
    main()
