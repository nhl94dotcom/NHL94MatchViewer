"""NHL '95 (Genesis): Vancecookcobxin's fighting patch as NOSE4Web builds it (2026-11-16, 540d453; the patch's notes:
FIGHTING_ROM_PATCH.md beside the ROMs). Modes:

  menu   power-on: the screen after boot (no red screen), the setting $FFCC63 (expected 1, On), Game Setup scrolled to
         its ninth row (Fighting) and stepped through its three choices with RIGHT (screenshots, $FFD28A each time)
  game   SETTING (0 Off, 1 On, 2 Arcade) chosen on that row, a Regular Game, the computer on both sides; with --push the
         check tension ChkCnt ($FFC028) is held at 40 or more (the patch's threshold (band - tension) / 4 + 10 is then
         10 at most: fights come early and often, the same code). Each fight (the puck's +$63
         bit 0, $FFB3C5) is logged: its fighters (the skaters showing fight frames $3CA-$3E7), the frames each showed
         (punches, hits, falls, flat out), the penalty list (PenBuf $FFBFCE) when play stops, the fighters' penalty
         time words (team struct +$68 by roster place) afterwards, screenshots every half second and of the penalty
         screen. Played until MAXFIGHTS fights or the end of period 3.
         --tie (all-hacks ROMs): after the first fight's penalties are set, the third period with 3 s left at 1-1 and
         the overtime cut to 3 s: a shootout after a fight; the fight engine's RAM ($FFE800-$FFE879) watched while
         the shootout runs and the shootout's ($FFF000-$FFF6CF) while it doesn't.

python gen95_fight_check.py ROM OUT menu
python gen95_fight_check.py ROM OUT game SETTING [--push] [--five] [--fgt=N] [--tie] [MAXFIGHTS]
  --perlen=V  the Per. Length row's value (0 5 min, 1 10 min, 2 20 min)
  --five   5-minute periods (the patch's bar for the opponent, 16 with 10-minute periods, is then 8, less twice his hits)
  --fgt=N  every skater's fighting byte (+$74, the roster's Chk/Hnd low nibble & $E, which the patch reads as
           "aggressiveness") set to N every second: W18's rosters have 0 for every player, so no fight can start there
           otherwise (the opponent must have 2 or more)."""
import sys
from pathlib import Path

import numpy as np

from emu import Emu
import gen95_assist_check as G
import gen95_shootout_check as S
import lowload

SETTING, ROW, CURSOR, FIGHTROW = 0xCC63, 0xD282, 0xD27C, 0xD28A
CHKCNT, PENBUF, PUCKFLAGS, GSP, CLOCK, PENCNT = 0xC028, 0xBFCE, 0xB3C5, 0xC020, 0xC022, 0xC010
FIGHT_RAM = (0xE800, 0x7A)


def frame_of(e, k):
    return e.w(G.rec(k) + 6) & 0x7FF


def to_setup(e, done=0):
    e.run(1500 - done)
    for _ in range(3):
        e.run(6, hold=["START"]); e.run(200)


def menu(e, out):
    e.run(700); e.screenshot(out / "boot.png")
    print(f"after boot (700 frames): setting $FFCC63 = {e.b(SETTING)} (screenshot boot.png: no red screen)")
    e.unserialize(e.serialize()) if False else None
    to_setup(e, 700)
    print(f"Game Setup: setting {e.b(SETTING)}, Fighting row value $FFD28A = {e.b(FIGHTROW)}")
    for i in range(8):
        e.run(6, hold=["DOWN"]); e.run(30)
    e.run(30)
    e.screenshot(out / "row_0.png")
    print(f"  cursor {e.w(CURSOR)}, value {e.b(FIGHTROW)}")
    for i in range(1, 4):
        e.run(6, hold=["RIGHT"]); e.run(40)
        e.screenshot(out / f"row_{i}.png")
        print(f"  RIGHT: value {e.b(FIGHTROW)}")
    for i in range(8):
        e.run(6, hold=["UP"]); e.run(30)
    e.screenshot(out / "top.png")


def game(e, out, setting, push, tie, maxfights, five=False, fgt=None, perlen=None):
    to_setup(e)
    for i in range(8):
        e.run(6, hold=["DOWN"]); e.run(30)
    for _ in range(6):
        if e.b(FIGHTROW) == setting:
            break
        e.run(6, hold=["RIGHT"]); e.run(40)
    if five:
        e.setb(ROW + 3, 0)                      # Per. Length: 5 minutes
    if perlen is not None:
        e.setb(ROW + 3, perlen)                 # Per. Length row value (0 5 min, 1 10, 2 20)
    print(f"Fighting row value {e.b(FIGHTROW)}, period length row {e.b(ROW + 3)}")
    e.run(6, hold=["START"]); e.run(300)
    e.run(6, hold=["START"]); e.run(60)
    e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    print(f"setting $FFCC63 in the game: {e.b(SETTING)}")
    fights, f, still, last, cur, after = 0, 0, 0, None, None, None
    shots = 0
    tie_done, ot_cut, armed, cprev, so_on = False, False, False, None, False
    fram = None
    so_ref = S.block(e, S.MARK, 0x6D0)
    fram_touched = so_touched = 0
    while f < 60 * 60 * 60:
        if f % 60 == 0:
            S.computer(e)
            if push and not tie_done:
                e.setw(CHKCNT, max(e.w(CHKCNT), 40))
            if fgt is not None:
                for k in range(12):
                    if k not in (5, 11):
                        e.setb(G.rec(k) + 0x74, fgt)
        on = bool(e.b(PUCKFLAGS) & 1)
        if not on and cur is None and f % 4 == 0 and any(0x3CB <= frame_of(e, k) <= 0x3E7 for k in range(12)):
            print(f"  fight frames on a skater at frame {f} without the fight flag")
        if on and cur is None:
            fights += 1
            cur = dict(start=f, frames={}, pen=None, gsp=e.w(GSP), clock=e.w(CLOCK))
            print(f"fight {fights}: period {e.w(GSP) + 1}, clock {e.w(CLOCK)} s left")
        if cur is not None:
            for k in range(12):
                fr = frame_of(e, k)
                if 0x3CA <= fr <= 0x3E7:
                    cur["frames"].setdefault(k, set()).add(fr)
            if (f - cur["start"]) % 30 == 0 and f - cur["start"] <= 900:
                e.screenshot(out / f"fight{fights}_{(f - cur['start']) // 30:02d}.png")
            if cur["pen"] is None and e.b(PENBUF):
                cur["pen"] = [e.b(PENBUF + i) for i in range(12)]
            if not on:
                for k, frs in sorted(cur["frames"].items()):
                    team = "home" if k < 6 else "away"
                    kinds = []
                    if frs & {0x3CB, 0x3CC, 0x3D8, 0x3D9}: kinds.append("stick down")
                    if frs & {0x3CE, 0x3CF, 0x3DB, 0x3DC, 0x3DA, 0x3E5}: kinds.append("punches")
                    if frs & {0x3D0, 0x3DD}: kinds.append("hit")
                    if frs & {0x3D1, 0x3D2, 0x3DE, 0x3DF, 0x3E6}: kinds.append("fell")
                    if frs & {0x3E7, 0x3E6}: kinds.append("flat out")
                    print(f"  record {k} ({team}, roster {e.b(G.rec(k) + 0x66)}): {', '.join(kinds)}; frames"
                          f" {' '.join(f'{x:X}' for x in sorted(frs))}")
                print(f"  lasted {f - cur['start']} frames; PenBuf when play stopped: {cur['pen']}; at the end: PenBuf"
                      f" {[e.b(PENBUF + i) for i in range(8)]}, the penalty screen's copy $FFDC82 {[e.b(0xDC82 + i) for i in range(8)]}"
                      f" ($26 Fighting, $28 Fighting * for the winner)")
                after = (f, cur)
                cur = None
        if after is not None and (f - after[0]) % 30 == 0 and f - after[0] <= 1200:
            e.screenshot(out / f"after{fights}_{(f - after[0]) // 30:02d}.png")
            if f - after[0] == 1200:
                pens = []
                for t in range(2):
                    for r in range(26):
                        v = e.w(S.TM + t * S.TMSIZE + 0x68 + 2 * r)
                        if 0 < v < 0x8000:
                            pens.append(f"{'home' if t == 0 else 'away'} roster {r}: ${v:04X} ({v & 0xFFF} s)")
                print(f"  penalty times 20 s after: {pens}")
                if tie and not tie_done:
                    tie_done = True
                    e.setw(GSP, 2); e.setw(CLOCK, 3); e.setw(S.HM, 1); e.setw(S.AW, 1)
                    print("  tie: third period, 3 s left, 1-1")
        if fights >= maxfights and cur is None and (after is None or f - after[0] > 1300) and not tie:
            break
        if tie_done:
            c = e.w(CLOCK)
            sob = bool(e.b(S.GMODE2) & 1)
            if not sob and e.w(GSP) == 3 and cprev is not None and c > cprev + 50:
                armed = True
            if armed and not sob and e.w(GSP) == 3 and c < cprev and not ot_cut:
                armed = False; ot_cut = True; e.setw(CLOCK, 3); print("  overtime cut to 3 s")
            cprev = e.w(CLOCK)
            if sob and not so_on:
                fram = S.block(e, *FIGHT_RAM)
                print(f"  shootout starts; fight RAM nonzero bytes {int((fram != 0).sum())}")
            if sob:
                if (S.block(e, *FIGHT_RAM) != fram).any():
                    fram_touched += 1
            if so_on and not sob:
                print(f"  shootout over: goals {S.block(e, S.HG, 0)} {e.w(S.HG)}-{e.w(S.AG)}, score {e.w(S.HM)}-{e.w(S.AW)}")
                so_ref = S.block(e, S.MARK, 0x6D0)
            if not sob and (S.block(e, S.MARK, 0x6D0) != so_ref).any():
                so_touched += 1; so_ref = S.block(e, S.MARK, 0x6D0)
            so_on = sob
            if e.w(GSP) >= 4:
                print(f"  game over {e.w(S.HM)}-{e.w(S.AW)}; fight RAM changed while the shootout ran: {fram_touched} looks;"
                      f" shootout RAM changed outside it: {so_touched}")
                e.run(300); e.screenshot(out / "end.png")
                break
        else:
            if (S.block(e, S.MARK, 0x6D0) != so_ref).any():
                so_touched += 1; so_ref = S.block(e, S.MARK, 0x6D0)
        sig = (e.w(CLOCK), e.w(G.PUCK), e.w(G.PUCK + 0x14))
        still = still + 1 if sig == last else 0
        last = sig
        quiet = after is not None and f - after[0] <= 1200      # the penalty screens after a fight, untouched
        e.run(1, hold=["START"] if still >= 300 and still % 300 == 0 and cur is None and not quiet else [])
        f += 1
        if e.w(GSP) >= 3 and not tie:
            break
        if f % 3600 == 0:
            lowload.breathe()
    print(f"{fights} fights in {f} frames (to period {e.w(GSP) + 1}, clock {e.w(CLOCK)}); the shootout block changed with no"
          f" shootout running: {so_touched}")


def main():
    rom, out, mode = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    lowload.gentle()
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    print(Path(rom).name)
    if mode == "menu":
        menu(e, out)
    else:
        nums = [a for a in sys.argv[5:] if not a.startswith("--")]
        fgt = [int(a.split("=")[1]) for a in sys.argv if a.startswith("--fgt=")]
        game(e, out, int(sys.argv[4]), "--push" in sys.argv, "--tie" in sys.argv, int(nums[0]) if nums else 3,
             "--five" in sys.argv, fgt[0] if fgt else None,
             ([int(a.split("=")[1]) for a in sys.argv if a.startswith("--perlen=")] or [None])[0])


if __name__ == "__main__":
    main()
