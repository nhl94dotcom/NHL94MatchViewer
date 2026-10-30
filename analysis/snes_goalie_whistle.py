"""The SNES instant whistle on a person's goalie catch (SNES_SHOOTING 5.4, 2026-10-30). puckglue starts the hold count
(temp5 $1083) at 140 frames, or 5 when the goalie's animation is SPAgdive ($E4B6); assgoalie counts it down for a
person's goalie only while he is within 77 of his goal line (|Ypos| >= 187) and zeroes it farther out, and the
whistle (AddPenalty2 PenGhold) comes when it runs out. For every catch by a person's goalie in the SNES recordings
(puckc $0AD9 turning to a goalie with a pad, playerpad $19D4 not negative): how long until the clock stopped (gmclock
$15D6), and for the quick ones the goalie's animation (SPA $11A3), hold count, y and the puck around the catch.
python analysis/snes_goalie_whistle.py   (every SNES recording with a match, both game folders)"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

PUCKC, POSITION, PLAYERPAD, SPA, TEMP5, YPOS, XPOS, GMCLOCK, PUCKZ, SFLAGS = (
    0x0AD9, 0x0F43, 0x19D4, 0x11A3, 0x1083, 0x0DB7, 0x0D55, 0x15D6, 0x0DF9, 0x15D8)
GDIVE = 0xE4B6
PENBUF = 0x15DE   # 32 (penalty number, object) words queued by AddPenalty2; numbers from ram94s.asm
PEN = {0x02: "end of period", 0x04: "end of game", 0x06: "puck out of play", 0x08: "goalie hold", 0x0A: "whistle",
       0x0C: "icing", 0x0E: "goal", 0x10: "no text", 0x12: "offside", 0x16: "injury", 0x24: "penalty shot"}
QUICK_MS = 150


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def folders():
    seen = set()
    for home in (Path("."), Path.home() / "Documents" / "NHL94 Viewer"):
        for cap in sorted((home / "captures").glob("*")):
            cj = cap / "capture.json"
            if cj.exists() and '"snes"' in cj.read_text() and (home / "matches" / f"{cap.name}.js").exists() \
                    and cap.name not in seen:
                seen.add(cap.name)
                yield cap


def main():
    catches, quick, pending = 0, [], []
    delays = Counter()
    for folder in folders():
        cap = Capture(folder)
        prev = -1
        for i in range(cap.count):
            pc = sw(cap.word(i, PUCKC))
            if pc >= 0 and pc != prev and pc % 2 == 0 and pc < 24:
                k = pc // 2
                if cap.word(i, POSITION + 2 * k) == 0 and sw(cap.word(i, PLAYERPAD + 2 * k)) >= 0 \
                        and cap.word(i, GMCLOCK) == 0 and not cap.word(i, SFLAGS) & 1:
                    catches += 1
                    t0 = cap.ms(i)
                    j = i
                    while j < cap.count - 1 and cap.word(j, GMCLOCK) == 0 and sw(cap.word(j, PUCKC)) == pc \
                            and cap.ms(j) - t0 < 4000:
                        j += 1
                    stopped = cap.word(j, GMCLOCK) != 0 and sw(cap.word(j, PUCKC)) == pc
                    d = cap.ms(j) - t0
                    delays["held to the whistle" if stopped else "passed or lost"] += 1
                    if stopped and d <= QUICK_MS:
                        rows = []
                        for q in range(max(0, i - 6), min(cap.count, j + 2)):
                            rows.append((cap.ms(q) - t0, f"{cap.word(q, SPA + 2 * k):04x}", sw(cap.word(q, TEMP5 + 2 * k)),
                                         sw(cap.word(q, YPOS + 2 * k)), sw(cap.word(q, PUCKC)), cap.word(q, GMCLOCK),
                                         cap.word(q, PUCKZ)))
                        why = []
                        for q in range(j, min(cap.count, j + 4)):
                            for n in range(32):
                                v = cap.word(q, PENBUF + 2 * n)
                                if v and (v & 0xFF) != 0x34 and (v & 0xFF, v >> 8) not in why:
                                    why.append((v & 0xFF, v >> 8))
                        before = [(v & 0xFF, v >> 8) for v in (cap.word(i - 1, PENBUF + 2 * n) for n in range(32))
                                  if v and (v & 0xFF) != 0x34]
                        why = why or before
                        own = [c for c, o in before if (o & 0x7F) < 12 and (o & 0x7F) // 6 == k // 6]
                        quick.append((folder.name, k, d, rows, why))
                        pending.append((folder.name, k, [PEN.get(c, hex(c)) for c, o in before], bool(own)))
            prev = pc
    print(f"catches by a person's goalie with the clock running: {catches}; {dict(delays)}")
    print(f"whistled within {QUICK_MS} ms: {len(quick)}")
    spa_at = Counter()
    reasons = Counter()
    for name, k, d, rows, why in quick:
        at = next(r for r in rows if r[0] >= 0)
        spa_at[at[1]] += 1
        names = [f"{PEN.get(c, hex(c))} (object {o})" for c, o in why]
        reasons[", ".join(PEN.get(c, hex(c)) for c, o in why) or "none queued"] += 1
        print(f"\n{name} goalie object {k}: clock stopped {d} ms after the catch; queued: {names}")
        print("   ms    SPA   temp5    y  puckc  gmclock  puckz")
        for r in rows:
            print(f"  {r[0]:5} {r[1]} {r[2]:6} {r[3]:5} {r[4]:5} {r[5]:7} {r[6]:6}")
    print("\nanimation at the catch in the quick whistles:", dict(spa_at), "(e4b6 = SPAgdive)")
    print("whistles queued (PenBuf):", dict(reasons))
    print("\npending in PenBuf the sample before the catch (penalty numbers), and whether one was on the goalie's team:")
    for name, k, names, own in pending:
        print(f"  {name} goalie {k}: {names} own team: {own}")
    print(f"a penalty against the goalie's own team was pending at {sum(p[3] for p in pending)} of {len(pending)}")


if __name__ == "__main__":
    main()
