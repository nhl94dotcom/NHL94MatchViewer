"""The lost-assist bug on the SNES, and NOSE4Web's regained-puck fix, played (2026-11-09; the Genesis:
gen_assist_repro.py). In live play (snes_assist_stick_test.Game: retail, Classic or a 2 MB build), the pad-1 skater A,
his teammates B and C, an away skater O; everyone else parked at the far end:
  0. the home touch history set as if C had passed to A (tmtouch1 A, tmtouch2 C; tmflags bit 2 clear), or for the
     control as if A had passed to C (tmtouch1 C, tmtouch2 A);
  1. the loose puck put on O's stick: the game's puckglue gives it to him (Home's assists wiped, bit 2 set);
  2. the loose puck put in front of A, who skates onto it (pad 1 held toward it): his retake. With tmtouch1 A this
     is the bug's case (same player: bit 2 stays set on retail);
  3. A passes to B straight ahead (B pressed with the direction held), until B's touch;
  4. the puck slid into the empty net: the goal's scorer and assists from the game's scoring summary ($313C).
Each step logs Home's tmtouch1-3 and tmflags bit 2.

python snes_regain_assist_test.py ROM [ROM ...]"""
import sys

from snes_assist_stick_test import (Game, PUCKC, CARRIER2, POSITION, PNUM, TOUCH1, TOUCH2, TOUCH3, TMFLAGS, CLOCK,
                                    SCORING_COUNT, SCORING_LIST, PUCK, ZPOS)


def play(G, base, control=False):
    log = []
    e = G.e
    e.unserialize(base)
    G.setw(CLOCK, 250)
    a, team, up = G.me()
    t = 2 * team
    mates = [k for k in range(team * 6, team * 6 + 6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF) and k != a]
    b, c = mates[0], mates[1]
    opp = next(k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    gk = next(k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if G.w(POSITION + 2 * k) == 0)
    pn = lambda k: G.w(PNUM + 2 * k)
    names = {pn(k) & 0xFF: n for k, n in ((a, "A"), (b, "B"), (c, "C"))}
    nm = lambda v: names.get(v & 0xFF, "-" if v >= 0x8000 or v == 0xFF else f"#{v}")
    state = lambda: ([nm(G.w(TOUCH1 + t)), nm(G.w(TOUCH2 + t)), nm(G.w(TOUCH3 + t))], int(bool(G.w(TMFLAGS + t) & 4)))
    first, second = (c, a) if control else (a, c)
    G.setw(TOUCH1 + t, pn(first))
    G.setw(TOUCH2 + t, pn(second))
    G.setw(TOUCH3 + t, 0xFFFF)
    G.setw(TMFLAGS + t, G.w(TMFLAGS + t) & ~4)
    log.append(("0. history", ("A passed to C" if control else "C passed to A")) + state())

    def hold_others(keep):
        for k in range(12):
            if k in keep or G.w(POSITION + 2 * k) in (0, 0xFFFF):
                continue
            G.put(k, -100 + 18 * (k % 6) + (10 if k >= 6 else 0), -230 * up)

    # 1. O picks up the loose puck (the computer chases a loose puck right in front of him)
    G.put(opp, 0, 40 * up)
    G.put(a, 90, 120 * up)
    G.put(b, 0, 200 * up)
    G.put(c, -90, 120 * up)
    G.put(PUCK, 0, 52 * up)
    G.setw(ZPOS, 0)
    G.setw(PUCKC, 0xFFFF)
    G.setw(CARRIER2, 0xFFFF)
    for f in range(120):
        hold_others({opp, a, b, c})
        G.put(a, 90, 120 * up)
        G.put(b, 0, 200 * up)
        G.put(c, -90, 120 * up)
        G.run()
        if G.w(PUCKC) == 2 * opp:
            break
    else:
        log.append(("1. O picks it up", "no pickup") + state())
        return log
    G.run(4)
    log.append(("1. O (away) picks it up", "after %d frames" % f) + state())
    # 2. A skates onto the loose puck (O moved away first)
    G.put(opp, 110, -100 * up)
    G.put(a, 0, 120 * up)
    G.put(PUCK, 0, 150 * up)
    G.setw(ZPOS, 0)
    G.setw(PUCKC, 0xFFFF)
    G.setw(CARRIER2, 0xFFFF)
    for f in range(120):
        hold_others({a, b, c})
        G.put(opp, 110, -100 * up)
        G.put(b, 0, 210 * up)
        G.put(c, -90, 120 * up)
        G.run(hold=["UP"] if up > 0 else ["DOWN"])
        if G.w(PUCKC) == 2 * a:
            break
    else:
        log.append(("2. A picks it back up", "no pickup") + state())
        return log
    G.run(4)
    log.append(("2. A picks it back up", "after %d frames" % f) + state())
    # 3. A passes to B straight ahead
    way = "UP" if up > 0 else "DOWN"
    ok = False
    for f in range(90):
        hold_others({a, b, c})
        G.put(opp, 110, -100 * up)
        G.put(c, -90, 120 * up)
        if f < 3:
            ax, ay = G.sw(0x0D55 + 2 * a), G.sw(0x0DB7 + 2 * a)
            G.put(b, ax, ay + 60 * up)
        G.run(hold=[way] + (["B"] if 3 <= f < 6 else []))
        if G.w(TOUCH1 + t) == pn(b):
            ok = True
            break
    log.append(("3. A passes to B", "B's touch after %d frames" % f if ok else "B never touched it") + state())
    if not ok:
        return log
    G.run(4)
    # 4. into the empty net
    n0 = G.w(SCORING_COUNT)
    G.setw(PUCKC, 0xFFFF)
    G.setw(CARRIER2, 0xFFFF)
    for f in range(60):
        hold_others(set())
        G.put(gk, 90, 240 * up)
        if f == 0:
            G.put(PUCK, 0, 240 * up, 0, 0x2000 * up)
        G.run()
        if G.w(SCORING_COUNT) != n0:
            break
    else:
        log.append(("4. into the empty net", "no goal") + state())
        return log
    entry = SCORING_LIST + G.w(SCORING_COUNT) - 6
    sc, a1, a2 = (G.g.at(entry + 3 + i)[0][G.g.at(entry + 3 + i)[1]] for i in range(3))
    log.append(("4. into the empty net", "goal: %s, assists %s, %s" % (nm(sc), nm(a1), nm(a2))))
    return log


def main():
    for rom in sys.argv[1:]:
        G = Game(rom)
        for control in (False, True):
            done = False
            for base in G.g.bases:
                log = play(G, base, control)
                if log and log[-1][0].startswith("4.") and "goal:" in log[-1][1]:
                    done = True
                    break
            print(f"== {rom.split('/')[-1]}: {'control (A passed to C first)' if control else 'A retakes his own puck'}")
            for row in log:
                print("  ", row, flush=True)


if __name__ == "__main__":
    main()
