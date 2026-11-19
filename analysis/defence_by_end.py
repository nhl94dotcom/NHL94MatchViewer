"""People's defence by end in the recorded Genesis games (2026-11-19; the league's Genesis penalty lean: the bottom
net's defenders are called 5.4% more, tripping 1.09, the checking calls about 1.05; checkagr, the penalty roll for
checks, holds and B-checks, is symmetric between the ends, so more calls means more contact).

Each regulation period, the team defending each net (the bottom net: home in periods 1 and 3). With the clock
running and the other team carrying:
- opportunities: samples a person-controlled defender (the ctrl bitmask) is within 40 of the carrier, and within 20;
- C checks: the converter's check attempts (people's bursts at an opposing skater: find_check_attempts), by result
  (hit, failed, whiff) and outcome; the carrier the target or not;
- B pokes: a person-controlled defender starting the poke animation ($0B24), and those followed within 4 samples by
  an opponent within 32 falling (a poke trip);
- penalties on the defending team by type (the game's codes) and whether a person was steering the offender.
Down / Up = the bottom net's defenders over the top net's.

python analysis/defence_by_end.py"""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import season  # noqa: E402

HOME = Path.home() / "Documents" / "NHL94 Viewer" / "matches"
K = 12
POKE = "0b24"
FALL = {"0d26", "0dd8", "136a", "1776", "17e8", "185a", "18cc", "193e", "1a00", "145c"}
PEN = {0x12: "roughing", 0x16: "charging", 0x18: "slashing", 0x1A: "roughing", 0x1C: "cross-check", 0x1E: "hooking",
       0x20: "tripping", 0x22: "interference", 0x24: "holding"}


def main():
    c = Counter()
    games = 0
    for p in sorted(HOME.glob("*.js")):
        if p.name == "season.js":
            continue
        try:
            m = season.load_match(p)
        except Exception:
            continue
        if (m.get("system") or "genesis") != "genesis" or "bot" in str(m.get("name", "")):
            continue
        games += 1
        per, clk, own, ctrl, pos = m["period"], m["clock"], m["owner"], m["ctrl"], m["pos"]
        N = len(m["t"])
        P = lambda f, k: (pos[(f * K + k) * 2], pos[(f * K + k) * 2 + 1])  # noqa: E731
        an = lambda f, k: m["anim"][(f * K + k) * 4:(f * K + k) * 4 + 4]  # noqa: E731
        end_def = lambda team, f: "Down" if (team == 0) == (per[f] % 2 == 0) else "Up"  # noqa: E731 the net it defends
        for i in range(24, N):
            if per[i] > 2 or clk[i] == clk[i - 24] or own[i] is None or own[i] < 0:
                continue
            carrier = own[i]
            dteam = 1 if carrier < 6 else 0
            e = end_def(dteam, i)
            cx, cy = P(i, carrier)
            near40 = near20 = False
            for k in range(6 * dteam, 6 * dteam + 6):
                if m["role"][i * K + k] not in "12345" or not ctrl[i] >> k & 1:
                    continue
                d = math.hypot(P(i, k)[0] - cx, P(i, k)[1] - cy)
                near40 |= d <= 40
                near20 |= d <= 20
            c[(e, "opportunity samples, within 40")] += near40
            c[(e, "opportunity samples, within 20")] += near20
            c[(e, "carried samples")] += 1
        for a in m.get("checkAttempts", []):
            f = a["f"]
            if per[f] > 2:
                continue
            e = end_def(a["team"], f)
            c[(e, "C checks")] += 1
            c[(e, f"C checks: {a['result']}")] += 1
            if a["result"] == "hit":
                c[(e, f"C hits: {a.get('outcome')}")] += 1
            c[(e, f"C checks: target the carrier {bool(a.get('carrier'))}")] += 1
        for k in range(12):
            if m["role"][0 * K + k] == "0":
                pass
            was = False
            for i in range(N):
                now = an(i, k) == POKE
                if now and not was and per[i] <= 2 and ctrl[i] >> k & 1:
                    dteam = 0 if k < 6 else 1
                    e = end_def(dteam, i)
                    c[(e, "B pokes")] += 1
                    tripped = False
                    for j in range(i, min(N, i + 5)):
                        for v in (range(6, 12) if dteam == 0 else range(6)):
                            if an(j, v) in FALL and (j == 0 or an(j - 1, v) not in FALL) and \
                                    math.hypot(P(j, v)[0] - P(j, k)[0], P(j, v)[1] - P(j, k)[1]) < 32:
                                tripped = True
                    c[(e, "B pokes: tripped someone")] += tripped
                was = now
        for pen in m.get("penalties", []):
            f = pen["f"]
            if per[f] > 2:
                continue
            e = end_def(pen["team"], f)
            typ = PEN.get(pen.get("code"), f"code {pen.get('code')}")
            c[(e, "penalties")] += 1
            c[(e, f"penalties: {typ}")] += 1
            c[(e, f"penalties by a {'person' if pen.get('human') else 'computer'}")] += 1
    print(f"{games} Genesis games; the team defending each net (Down = the bottom net)")
    keys = sorted({k for _, k in c}, key=lambda s: (s.split(":")[0], s))
    for k in keys:
        u, d = c[("Up", k)], c[("Down", k)]
        z = (d - u) / math.sqrt(d + u) if d + u else 0
        print(f"  {k:46s} Up {u:7d}  Down {d:7d}  Down/Up {d / u if u else float('nan'):6.3f}  (z {z:+.1f})")
    for e in ("Up", "Down"):
        o = c[(e, "opportunity samples, within 40")]
        print(f"  {e}: per 1,000 opportunity samples (within 40): C checks {1000 * c[(e, 'C checks')] / o:.2f}, "
              f"B pokes {1000 * c[(e, 'B pokes')] / o:.2f}; hit rate {c[(e, 'C checks: hit')] / max(c[(e, 'C checks')], 1):.1%}, "
              f"poke trips {c[(e, 'B pokes: tripped someone')] / max(c[(e, 'B pokes')], 1):.1%}")


if __name__ == "__main__":
    main()
