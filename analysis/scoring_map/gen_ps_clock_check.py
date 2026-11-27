"""The penalty-shot attempt clock, played (2026-11-27, NOSE4Web's answer: shootoutclock $FFD454 and its tick counter
shootoutjiffy $D456; the penalty-shot setup sets gmode2 bit 1 and the clock to 25; VBlank's .soclock takes $0AAA off
the jiffy a frame (the real-time option: $0444, the word at $15E32) and 1 off the clock at each borrow, not while
gmode2 bit 7 is set; .checktimer ends the attempt at 0 (BA_PS_flags bit 4); shootoutpath94.asm times the computer
shooter by it).

Penalty shots awarded as ps_fixes_test does (ps_table_test's breakaway foul, from the saved live states). Two kinds of
attempt, each frame of it logged (the clock, the jiffy, gmode2, BA_PS_flags, the puck's carrier):
  cpu    the computer shoots (both pads off): the clock's value when the puck leaves him, and how the attempt ends.
  stall  pad 1 given the shooter's team at the award and nothing pressed: does the attempt end when the clock reaches
         0, at which frame, with BA_PS_flags bit 4. Screenshots at clock 25, 20, 15, 10, 5, 1 and the end of the
         first stall attempt (the on-screen clock beside the RAM value).

python gen_ps_clock_check.py ROM OUT [N_CPU] [N_STALL]"""
import json
import random
import sys
from pathlib import Path

import ps_fixes_test as F
import ps_table_test as P
from bot import rec
from bot_scenario import live_state, LIVE_STATES, CONT_TEAMS
from emu import Emu
from lowload import breathe, gentle

SOCLOCK, SOJIFFY, GMODE2 = 0xD454, 0xD456, 0xC2FA
UNDERWAY, ENDED = 0x0400, 0x1000        # BA_PS_flags (the word: its high byte's bits 2 and 4)
GM2_PS, GM2_HOLD = 0x0200, 0x8000       # gmode2's high byte: bit 1 (a penalty-shot attempt), bit 7 (the clock held)
PUCKC = 0xB7AA
SHOTS_AT = (25, 20, 15, 10, 5, 1, 0)


def attempt(e, mode, out, tag, shots):
    """From an award to the attempt's end. Returns the frame log's summary."""
    if mode == "stall":
        e.setw(CONT_TEAMS[0], 1)              # pad 1 on Home (the fouled team: the computer's carrier was Home)
        e.setw(CONT_TEAMS[1], 0)
    else:
        e.setw(CONT_TEAMS[0], 0)
        e.setw(CONT_TEAMS[1], 0)
    f0 = F.run_until(e, lambda: e.w(P.BA_PS_FLAGS) & UNDERWAY and e.w(SOCLOCK) == 25, 3000)
    if f0 is None:
        return dict(res="no attempt")
    shooter = e.w(P.BA_SKTR)
    log = []
    ticks = []                                # frames at which the clock stepped down
    shot_at = end = None
    had = False
    seen = set()
    changes = []
    for f in range(3000):
        c = e.w(SOCLOCK)
        held = e.w(GMODE2) & GM2_HOLD
        if shots is not None and log and log[-1][3] & GM2_HOLD == 0 and len(log) > 1 and log[-2][3] & GM2_HOLD \
                and "live" not in seen:
            seen.add("live")                                     # the frame after the attempt went live
            e.screenshot(out / f"{tag}_live.png")
        elif shots is not None and not held and c in SHOTS_AT and c not in seen:
            seen.add(c)
            e.screenshot(out / f"{tag}_clock{c:02d}.png")      # runs the frame
        else:
            e.run(1)
        c2, flags, gm2, pc = e.w(SOCLOCK), e.w(P.BA_PS_FLAGS), e.w(GMODE2), e.w(PUCKC)
        log.append((f, c2, e.w(SOJIFFY), gm2, flags, pc))
        if c2 < c:
            ticks.append(f)
        if not log[1:] or (gm2, flags) != (log[-2][3], log[-2][4]):
            changes.append((f, c2, hex(gm2), hex(flags), pc))
        had = had or pc == shooter
        if had and shot_at is None and pc != shooter:
            shot_at = dict(frame=f, clock=c2, carrier=pc)
        if flags & ENDED and end is None:
            end = dict(frame=f, clock=c2, flags=hex(flags))
        if not flags & UNDERWAY:
            if shots is not None:
                for j in range(3):
                    e.screenshot(out / f"{tag}_end{j}.png")
            break
    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    live = next((r[0] for r in log if not r[3] & GM2_HOLD and r[0] > 0 and log[r[0] - 1][3] & GM2_HOLD), None)
    ticks_held = sum(1 for t in ticks if log[t][3] & GM2_HOLD)
    return dict(res="ok", mode=mode, shooter=shooter, frames=len(log), first_tick=ticks[0] if ticks else None,
                ticks=len(ticks), gaps=sorted(set(gaps)), mean_gap=round(sum(gaps) / len(gaps), 2) if gaps else None,
                last_clock=log[-1][1], shot=shot_at, ended_bit4=end, bit7_frames=sum(1 for r in log if r[3] & GM2_HOLD),
                ticks_while_bit7=ticks_held, gmode2_bit1_frames=sum(1 for r in log if r[3] & GM2_PS), live=live,
                live_to_first_tick=None if live is None or not ticks else ticks[0] - live,
                live_to_end=None if live is None else len(log) - 1 - live, changes=changes[:40])


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    n_cpu = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    n_stall = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    out.mkdir(parents=True, exist_ok=True)
    gentle()
    e = Emu(rom)
    print("word at $15E32:", Path(rom).read_bytes()[0x15E32:0x15E34].hex(), flush=True)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    tag = Path(rom).stem
    rows = []
    i = 0
    plan = ["stall"] * n_stall + ["cpu"] * n_cpu
    for k, mode in enumerate(plan):
        r = None
        while r is None or r["res"] != "ok":
            rnd = random.Random(5000 + i)
            i += 1
            if F.award(e, bases[i % LIVE_STATES], rnd) is None:
                r = dict(res="no award")
                continue
            r = attempt(e, mode, out, f"{tag}_{mode}{k}", {} if k == 0 else None)
            if i > 200:
                raise SystemExit("no attempts")
        r["trial"] = i
        print(json.dumps(r), flush=True)
        rows.append(r)
        breathe()
    (out / f"{tag}_attempts.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
