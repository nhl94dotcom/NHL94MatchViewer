"""Shootouts for tied regular-season games (2026-11-11, for NOSE4Web 2776621: nhl94_shootout.bin,
CDL_Season_12_shootout.bin). From a game in play (power-on, START into play, the computer on both sides: cont1team /
cont2team cleared and the person flag taken off every second), one case at a time:

  tie       regular season (OptPlayMode $D048 = 0), overtime (gsp $C466 = 3) with 3 s left at 1-1
  playoff   the same in the playoffs (2): overtime until a goal, no shootout expected
  reg       regular season, the third period with 3 s left at 2-1: the game over as usual
  ot        regular season, overtime with 3 s left at 2-1 (a game won in overtime)
  tie3      regular season, the third period with 3 s left at 1-1 (NOSE4Web 6c951fc: the shootout after period 3)
  playoff3  the same in the playoffs: overtime expected
  mode4     Shootout from Game Setup (Play Mode 4), as on retail: expected to end at the title

Played (START every 2.5 s while the clock stands, as gen_ot_goal_check, but in a shootout only until its clock, shootoutclock $D454, first runs: later presses open the pause menu) until the game is over and the menus come back,
or 40 minutes of frames. Logged whenever it changes: gsp, the screen ($FFF7), gmode2 ($C2FA, bit 0 in its first byte), $FFF082 (the build's
shootout flag), shootoutround ($D578), homeshootgoals / awayshootgoals ($D574 / $D576), the score, the shots and the
clock; a screenshot at every change of screen, every 2 s while gmode2 bit 0 is on and every second from gsp 4. At the shootout's start and end
both team stat blocks ($C6CE / $CA32, $364 bytes; the hot / cold table +$1A2-$341 left out) and the player stats (tmstruct+$20...) are kept and the changed
offsets printed. With --cdl, also the fighting setting ($FFF080), OptPen / OptLine and the plus-minus log ($FFDEF4,
first 64 bytes) before and after.

--gmdir clears gmode bit 1 (gmdir, $C2EA's first byte) once when $FFF082 is first set: the build plays its shootout
with the overtime period's ends (gmdir set), so each shooter attacks the net where Goal's shootout test (home: puck y >= 0,
away: y < 0) throws the goal out; with gmdir clear the ends are Shootout mode's.

--end, when $FFF082 clears (the build's end code has run): gmode2's first byte's bits 0, 1 and 3 cleared (the build clears
the low byte's) and the score put back to the shootout's start plus 1 for the winner (shootout goals go through Goal's
ordinary path too). At that moment the stat blocks and scoring summary ($C472) are compared with the shootout's start.

--records: User Records on (OptUserRec $D054 = 0) at Game Setup, and the save memory's changed bytes printed after the
game (UpdateTeamRecord counts a win, loss or tie by the two teams' tmscore).

--force: the first home shot of the shootout put into the net it was going at (shootoutteam $D594 = 0, the puck loose
past y 150): for ROMs whose computer shooters never score (CDL Season 12, its own Shootout mode too).

--preset=R:T:H:A (2026-11-14, the three-round shootout's edge cases): when round R's attempt by team T (0 home, 1
visitors; home shoots first) first comes up, the shootout's goals are set to H (home) and A; every attempt is logged
(round, team, the counts, the shooter: the shooting team's one skater on the ice). --results=GM...: each attempt's result in turn (G goal, M miss, anything else as
played): once the shot is on its way (the shooter has had the puck, and it is loose 150-250 from the middle), the puck is put into the net or
wide of it. (--seed=N sets $D066 in Shootout mode; it made no difference.)

python gen_shootout_check.py ROM OUT CASE [--cdl] [--gmdir] [--end] [--records] [--force] [--preset=R:T:H:A]"""
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

PLAYMODE, OPTUSER, OPTPEN, OPTLINE, GSP, CLOCK, SCREEN = 0xD048, 0xD054, 0xD056, 0xD058, 0xC466, 0xC468, 0xFFF7
CONT1, CONT2, BASE, SZ = 0xC328, 0xC32A, 0xB04A, 0x80
GMODE, GMODE2, SOFLAG, SOROUND, HSO, ASO, SOCLOCK = 0xC2EA, 0xC2FA, 0xFFF082, 0xD578, 0xD574, 0xD576, 0xD454
HM, AW, HSHOTS, ASHOTS, TEAMB, TMSIZE = 0xC6DA, 0xCA3E, 0xC6CE, 0xCA32, (0xC6CE, 0xCA32), 0x364
FIGHT, PLUSMINUS, SUMMARY = 0xFFF080, 0xFFDEF4, 0xC472
SOTEAM, PUCK, PUCKC = 0xD594, 0xB04A + 14 * 0x80, 0xB7AA


def blocks(e):
    return [bytes(e.b(t + i) for i in range(TMSIZE)) for t in TEAMB]


def diff(a, b):
    out = []
    for t in range(2):
        ch = [i for i in range(TMSIZE) if a[t][i] != b[t][i] and not 0x1A2 <= i < 0x342]   # not tmHotCold
        out.append(" ".join(f"+${i:03X}:{a[t][i]}->{b[t][i]}" for i in ch[:40]) + (" ..." if len(ch) > 40 else ""))
    return out


def main():
    rom, out, case = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    cdl = "--cdl" in sys.argv
    gmdir_fix = "--gmdir" in sys.argv
    end_fix = "--end" in sys.argv
    force = "--force" in sys.argv
    forced = False
    saved, flag_was, summ0 = None, 0, None
    gmdir_done = False
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e = Emu(rom)
    G.to_setup(e, out)
    userrec = "--records" in sys.argv
    if userrec:
        from gen_records_check import sram
        e.setw(OPTUSER, 0)
        s0 = sram(e)
    seed = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--seed=")), None)
    if case == "mode4":
        e.setw(PLAYMODE, 4)
        if seed is not None:
            e.setl(0xD066, (0x2545F491 * (seed + 1)) & 0xFFFFFFFF or 1)      # the game's random seed
        for _ in range(4):
            e.run(4, hold=["START"])
            e.run(300)
    elif not G.into_play(e):
        print("never reached play")
        return
    if case != "mode4":
        G.OURS.append(tuple(e.b(a) for a in G.TEAMS))
        mode, gsp, hm, aw = {"tie": (0, 3, 1, 1), "playoff": (2, 3, 1, 1), "reg": (0, 2, 2, 1),
                             "ot": (0, 3, 2, 1),
                             "tie3": (0, 2, 1, 1), "playoff3": (2, 2, 1, 1)}[case]
        e.setw(PLAYMODE, mode)
        e.setw(GSP, gsp)
        e.setw(CLOCK, 3)
        e.setw(HM, hm)
        e.setw(AW, aw)
    if cdl:
        print(f"before: fighting ${e.w(FIGHT):04X}, OptPen {e.w(OPTPEN)}, OptLine {e.w(OPTLINE)}, plus-minus "
              + bytes(e.b(PLUSMINUS + i) for i in range(64)).hex())
    preset = next(([int(v) for v in a.split("=")[1].split(":")] for a in sys.argv if a.startswith("--preset=")), None)
    preset_done, attempt, shooter_seen = False, None, False
    results = next((a.split("=")[1] for a in sys.argv if a.startswith("--results=")), "")
    n_attempt, attempt_f, decided, carried = -1, 0, False, False
    prev, last, still, shots_n = None, None, 0, 0
    so_start, started = None, False
    for f in range(60 * 60 * 40):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        so = e.b(GMODE2) & 1
        fl = e.b(SOFLAG)
        if fl and not flag_was:
            saved = (e.w(HM), e.w(AW))
            summ0 = bytes(e.b(SUMMARY + i) for i in range(0x168))
        if flag_was and not fl and saved:
            d = diff(so_start, blocks(e)) if so_start else ["?", "?"]
            print(f"f{f}: shootout over (the build's end code): score {e.w(HM)}-{e.w(AW)} (at the start {saved[0]}-"
                  f"{saved[1]}), gmode2 ${e.w(GMODE2):04X}; stat blocks changed since the start: home {d[0] or 'none'};"
                  f" away {d[1] or 'none'}; scoring summary changed: "
                  f"{summ0 != bytes(e.b(SUMMARY + i) for i in range(0x168))}", flush=True)
            if end_fix:
                e.setb(GMODE2, e.b(GMODE2) & 0xF4)
                win = e.w(HSO) > e.w(ASO)
                e.setw(HM, saved[0] + win)
                e.setw(AW, saved[1] + (not win))
                print(f"f{f}: end corrected in RAM: gmode2 ${e.w(GMODE2):04X}, score {e.w(HM)}-{e.w(AW)}", flush=True)
        flag_was = fl
        if gmdir_fix and not gmdir_done and e.b(SOFLAG):
            e.setb(GMODE, e.b(GMODE) & ~2)          # the suggested fix, in RAM: Shootout mode's ends (gmdir clear)
            gmdir_done = True
            print(f"f{f}: gmdir cleared", flush=True)
        if so and e.w(SOCLOCK):
            started = True                  # the first attempt is on: no more presses until the shootout ends
        if not so:
            started = False
        e.run(1, hold=["START"] if still >= 150 and f % 150 == 0 and not (so and started) else [])
        pk = PUCK
        py = e.w(pk + 0x14) - (0x10000 if e.w(pk + 0x14) > 0x7FFF else 0)
        if force and not forced and so and started and e.w(SOTEAM) == 0 and e.w(PUCKC) >= 0xFF00 and 150 < abs(py) < 250:
            end = 1 if py > 0 else -1               # the first home shot put into the net it was going at
            for off, v in ((0x00, 0), (0x1C, 0), (0x14, end * 262), (0x20, end * 256), (0x18, 0), (0x24, 0), (0x28, 0),
                           (0x2A, end * 12000), (0x2C, 0)):
                e.setw(pk + off, v & 0xFFFF)
            forced = True
            print(f"f{f}: the home shot put into the {'top' if end > 0 else 'bottom'} net", flush=True)
        if e.b(GMODE2) & 1:                          # each attempt: who shoots, and the counts when it starts
            at = (e.w(SOROUND), e.w(SOTEAM) & 1)
            if at != attempt:
                attempt, shooter_seen = at, False
                n_attempt, attempt_f, decided, carried = n_attempt + 1, f, False, False
                if preset and not preset_done and at == (preset[0], preset[1]):
                    e.setw(HSO, preset[2])
                    e.setw(ASO, preset[3])
                    preset_done = True
                    print(f"f{f}: preset: round {at[0]}, {'visitors' if at[1] else 'home'} to shoot, shootout set to "
                          f"{preset[2]}-{preset[3]}", flush=True)
                print(f"f{f}: attempt: round {at[0]}, {'visitors' if at[1] else 'home'} shooting, shootout "
                      f"{e.w(HSO)}-{e.w(ASO)} (home-visitors)", flush=True)
            if e.w(SOCLOCK) and e.w(PUCKC) < 0xFF00 and not carried:
                carried = True                        # the shooter has the puck: name him (the skater nearest it)

                def s16(v):
                    return v - 0x10000 if v > 0x7FFF else v
                px, py = s16(e.w(PUCK)), s16(e.w(PUCK + 0x14))
                k = min(range(12), key=lambda k: abs(s16(e.w(BASE + SZ * k)) - px) + abs(s16(e.w(BASE + SZ * k + 0x14)) - py))
                rec = BASE + SZ * k
                print(f"f{f}:   shooter: record {k}, roster slot {e.b(rec + 0x66)}, number {e.b(rec + 0x6F):X}", flush=True)
        want = results[n_attempt] if 0 <= n_attempt < len(results) else None
        if want in ("G", "M") and carried and not decided and e.b(GMODE2) & 1 and e.w(SOCLOCK) and e.w(PUCKC) >= 0xFF00:
            py = e.w(PUCK + 0x14) - (0x10000 if e.w(PUCK + 0x14) > 0x7FFF else 0)
            if 150 < abs(py) < 250:                   # the shot on its way: into the net, or wide of it
                end = 1 if py > 0 else -1
                x, vx = (0, 0) if want == "G" else (110, 9000)
                for off, v in ((0x00, x), (0x1C, x), (0x14, end * 262), (0x20, end * 256), (0x18, 0), (0x24, 0),
                               (0x28, vx), (0x2A, end * 12000 if want == "G" else 0), (0x2C, 0)):
                    e.setw(PUCK + off, v & 0xFFFF)
                decided = True
                print(f"f{f}:   result forced: {'goal' if want == 'G' else 'miss'}", flush=True)
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        g2 = e.b(GMODE2)
        if case != "mode4" and not G.ours(e):
            continue
        st = (e.w(GSP), e.b(SCREEN), g2, e.b(SOFLAG), e.w(SOROUND), e.w(HSO), e.w(ASO), e.w(HM), e.w(AW),
              e.w(HSHOTS), e.w(ASHOTS))
        if st != prev:
            print(f"f{f}: gsp {st[0]} screen {st[1]} gmode2 ${st[2]:02X} flag ${st[3]:02X} round {st[4]} "
                  f"shootout {st[5]}-{st[6]} score {st[7]}-{st[8]} shots {st[9]}-{st[10]} clock {c}", flush=True)
            if prev is None or st[1] != prev[1] or st[0] != prev[0]:
                e.screenshot(out / f"{case}_{shots_n:03d}_f{f}.png")
                shots_n += 1
            if g2 & 1 and so_start is None and case != "mode4":
                so_start = blocks(e)
                print("shootout on: stat blocks kept", flush=True)
            if so_start is not None and not g2 & 1 and prev is not None and prev[2] & 1:
                d = diff(so_start, blocks(e))
                print(f"stat blocks changed during the shootout: home {d[0] or 'none'}; away {d[1] or 'none'}",
                      flush=True)
            prev = st
        if (g2 & 1 and f % 120 == 0 or e.w(GSP) >= 4 and f % 60 == 0) and shots_n < 400:
            e.screenshot(out / f"{case}_{shots_n:03d}_f{f}.png")
            shots_n += 1
        if f > 600 and e.w(GSP) == 0 and e.b(SCREEN) not in (0, 0x80, 100):
            print(f"f{f}: back to the menus (screen {e.b(SCREEN)})")
            break
    e.screenshot(out / f"{case}_end.png")
    if userrec:
        e.run(300)
        s1 = sram(e)
        ch = [i for i in range(len(s0)) if s0[i] != s1[i]]
        print(f"save memory changed at {len(ch)} bytes: " + " ".join(f"{i:04X}:{s0[i]:02X}->{s1[i]:02X}" for i in ch[:60]))
    if cdl:
        print(f"after: fighting ${e.w(FIGHT):04X}, OptPen {e.w(OPTPEN)}, OptLine {e.w(OPTLINE)}, plus-minus "
              + bytes(e.b(PLUSMINUS + i) for i in range(64)).hex())


if __name__ == "__main__":
    main()
