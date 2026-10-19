"""B without the puck on the Genesis: poke check or switch? (2026-10-19, the user asked.)

doinput (input94.asm) acts when B is RELEASED within 17 frames of the press (bholdtimer $11; held longer, it can take the
goalie instead). It calls chgplayer (title94.asm): among the controller's team's skaters on the ice (not the goalie, not
unavailable, not animation-locked (pflags bit 5), not the other controller's skater; the current one included), take the
one nearest the point the puck will reach in 16 frames (puck position + velocity / 256). If that is the skater already
controlled, he sweep-checks (pokes); otherwise control moves to that skater.

For every B release by controller 1 with its skater not carrying the puck, this works out the game's choice from the
sample before and compares it with what happened (a poke animation $0B24 on the current skater, or the controlled
marker moving). python analysis/b_button_study.py <capture folders>"""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

BASE, SIZE, PUCK = 0xB04A, 0x80, 14
PAD1, CONT1TEAM = 0xBEEF, 0xC328


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def rec(k, off):
    return BASE + SIZE * k + off


def main():
    tally, examples = Counter(), []
    for folder in map(Path, sys.argv[1:]):
        try:
            cap = Capture(folder)
            cap.byte(0, PAD1)
            cap.word(0, CONT1TEAM)
        except Exception as e:  # noqa: BLE001
            print("skip", folder.name, e)
            continue
        prev_b, pressed_at = False, None
        for i in range(1, cap.count - 6):
            b = bool(cap.byte(i, PAD1) & 0x10)
            if b and not prev_b:
                pressed_at = cap.ms(i)
                # doinput_islocked: a B PRESS while his skater is locked in an animation switches at once
                team_ = cap.word(i, CONT1TEAM)
                ks_ = range(0, 6) if team_ == 1 else range(6, 12)
                c_ = [k for k in ks_ if cap.byte(i - 1, rec(k, 0x62)) & 0x08]
                if (team_ in (1, 2) and len(c_) == 1 and cap.byte(i - 1, rec(c_[0], 0x35)) not in (0, 0xFF)
                        and cap.byte(i - 1, rec(c_[0], 0x62)) & 0x20 and sw(cap.word(i - 1, rec(PUCK, 0x18))) >= 0
                        and not (cap.byte(i - 1, rec(PUCK, 0x60)) == 0 and cap.byte(i - 1, rec(PUCK, 0x61)) == c_[0])):
                    moved_ = any(not (cap.byte(j, rec(c_[0], 0x62)) & 0x08) for j in range(i, i + 6))
                    tally[("pressed while locked", "switch" if moved_ else "nothing")] += 1
            released = prev_b and not b
            prev_b = b
            if not released or pressed_at is None:
                continue
            if cap.ms(i) - pressed_at > 17 * 1000 / 60:
                tally[("(held over 17 frames)", "")] += 1
                continue
            if sw(cap.word(i - 1, rec(PUCK, 0x18))) < 0:
                continue                                   # the puck hidden: a stoppage
            team = cap.word(i, CONT1TEAM)
            if team not in (1, 2):
                continue
            ks = range(0, 6) if team == 1 else range(6, 12)
            ctrl = [k for k in ks if cap.byte(i - 1, rec(k, 0x62)) & 0x08]
            if len(ctrl) != 1:
                continue
            cur = ctrl[0]
            if cap.byte(i - 1, rec(cur, 0x35)) in (0, 0xFF):
                continue                                   # a goalie, or off the ice
            if cap.byte(i - 1, rec(cur, 0x62)) & 0x20:
                tally[("(his skater locked)", "")] += 1
                continue                                   # doinput_islocked: B does nothing
            if cap.byte(i - 1, rec(PUCK, 0x60)) == 0 and cap.byte(i - 1, rec(PUCK, 0x61)) in ks:
                continue                                   # his team has the puck: not defence
            px = sw(cap.word(i - 1, rec(PUCK, 0))) + (sw(cap.word(i - 1, rec(PUCK, 0x28))) >> 8)
            py = sw(cap.word(i - 1, rec(PUCK, 0x14))) + (sw(cap.word(i - 1, rec(PUCK, 0x2A))) >> 8)
            best, bestd = None, None
            for k in ks:
                pos = cap.byte(i - 1, rec(k, 0x35))
                if pos in (0, 0xFF) or cap.byte(i - 1, rec(k, 0x63)) & 0x04 or cap.byte(i - 1, rec(k, 0x62)) & 0x20:
                    continue
                d = (px - sw(cap.word(i - 1, rec(k, 0)))) ** 2 + (py - sw(cap.word(i - 1, rec(k, 0x14)))) ** 2
                if bestd is None or d <= bestd:
                    best, bestd = k, d
            predicted = "poke" if best == cur else "switch"
            # what happened in the next few samples
            poked = any(cap.word(j, rec(cur, 0x58)) == 0x0B24 for j in range(i, i + 6))
            moved = any(not (cap.byte(j, rec(cur, 0x62)) & 0x08) for j in range(i, i + 6))
            happened = "poke" if poked else "switch" if moved else "nothing"
            if cap.byte(i - 1, rec(cur, 0x64)) & 0x40:
                tally[("(release already used)", happened)] += 1
                continue
            tally[(predicted, happened)] += 1
            if predicted != happened and len(examples) < 12:
                examples.append((folder.name, round(cap.ms(i) / 1000, 1), predicted, happened))
    print("predicted -> happened:")
    for k, v in sorted(tally.items()):
        print(f"  {k[0]:7} -> {k[1]:8} {v}")
    for e in examples:
        print("  mismatch", e)


if __name__ == "__main__":
    main()
