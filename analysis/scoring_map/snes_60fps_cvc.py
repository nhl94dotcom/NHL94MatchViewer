"""How much McMarkis's 60 frames a second changes play (2026-11-08, for NOSE4Web): the original engine (game logic at 30
frames a second, d7 = 2) against the SA-1 build (60, d7 = 1). The physics scale with d7 and the computer's decision
timers count down by it (real time on both); collisions, input and steering run every step, twice as often at 60.

Each game, the computer on both sides: Montreal at home against Los Angeles (the ROMs' defaults; on the original the
menu presses set 5-minute periods and penalties), the clock held to 5:00 at most and the Penalties option set to On,
No Offside ($34C4 = 2) when play starts (on the original engine a press lost to the seed's timing left penalties Off in
15 of 20 games before this was added; `optpen_found` records what the menus left), each game's random seed ($0792 /
$0794) set from its number (the SA-1 build's random state doesn't depend on the menu frames), every pad taken off the
teams (as snes_period_cvc.computer_only, again every 5 s), the three regulation periods (breaks passed with START). At
the end of regulation, from the game's own team stats (low RAM; in BW-RAM on the SA-1 build,
faceoff_fix_test.Snes.MOVED): goals and shots by period, saves, body checks, penalties, passes completed and tried.
Every 10 frames: each penalty called (team, number) from the buffer at $15DE (numbers as snes.read_penalties: $14 /
$1C Roughing, $2A / $2C Fighting ...), and each shot's strength (even, power play, short-handed) from the players in
the boxes ($1624) when the shot count rises. Gentle (lowload).

`--make-30 ROM OUT.sfc` writes the SA-1 build at 30 frames a second, to separate the frame rate from the rest of the
build: its Gameloop waits for 2 frames instead of 1 (at $F8517 `lda vcount / sec / sbc oldvcount / beq` becomes
`... / lsr / beq`, taking the 3 bytes of `inc gameframes`, which only feeds the gamefps readout), so every step has
d7 = 2 as on the original engine (checked: timestep $0ADB is 2 at every frame, the clock runs as before).

python snes_60fps_cvc.py ROM GAMES OUT.jsonl
python snes_60fps_cvc.py --make-30 SA1ROM OUT.sfc"""
import json
import sys
from pathlib import Path

import lowload
import menu_shots as M
from faceoff_fix_test import Snes

CONT1TEAM, PADSIDE, PLAYERPAD, C1PLAYER, TEAMPADS, PFLAGS = 0x1C84, 0x19F6, 0x19D4, 0x19EC, 0x19D0, 0x1283
GSP, CLOCK, CLOCKSTOP, SEED = 0x1630, 0x1632, 0x15D6, 0x0792   # seed: RandomWord's two words
OPTPEN = 0x34C4                              # the Penalties option: 0 Off, 2 On, No Offside
GOALS_P, SHOTS_P = 0x177E, 0x176A          # per period (+4 a period), home / away words
CHECKS, PENS, PASSES_C, PASSES_T = 0x17B6, 0x174A, 0x17BA, 0x17BE
PEN_BUFFER, IN_BOX = 0x15DE, 0x1624         # (penalty number, object) byte pairs at the foul; players in the boxes (Home x 16 + Away)


class Mem:
    """Word reads and writes, with the SA-1 build's low RAM in BW-RAM."""
    def __init__(self, e, rom):
        import ctypes as C
        self.e = e
        data = Path(rom).read_bytes()
        self.sa1 = len(data) > 0x7FD6 and data[0x7FD5] == 0x23
        self.bw = (C.c_ubyte * e.lib.retro_get_memory_size(0)).from_address(e.lib.retro_get_memory_data(0)) if self.sa1 else None

    def at(self, a):
        if self.sa1:
            for lo, hi, to in Snes.MOVED:
                if lo <= a < hi:
                    return self.bw, to + a - lo
        return self.e.ram, a

    def w(self, a):
        buf, o = self.at(a)
        return buf[o] | buf[o + 1] << 8

    def setw(self, a, v):
        buf, o = self.at(a)
        buf[o], buf[o + 1] = v & 0xFF, (v >> 8) & 0xFF


def computer_only(m):
    for i in range(5):
        m.setw(CONT1TEAM + 2 * i, 0)
        m.setw(PADSIDE + 2 * i, 0xFFFE)
        m.setw(C1PLAYER + 2 * i, 0xFFFF)
    m.setw(TEAMPADS, 0)
    m.setw(TEAMPADS + 2, 0)
    for k in range(12):
        m.setw(PLAYERPAD + 2 * k, 0xFFFF)
        m.setw(PFLAGS + 2 * k, m.w(PFLAGS + 2 * k) & ~8)


def game(rom, n, extra=None):
    e = M.emulator(rom)
    m = Mem(e, rom)
    tmp = Path("x_tmp_60fps")
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", tmp)                          # its defaults: 5 min, On, No Offside
    else:
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    M.play(e, "START w240 START w200 w2400", tmp)                           # player select, the matchups
    for _ in range(12):                                                    # the pre-game menu: START until the clock runs
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    optpen_found = m.w(OPTPEN)                # a lost menu press can leave penalties Off (15 of 20 seeds did)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)                        # each game its own random state (the
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)                    # menu frames don't vary the SA-1 build's)
    still, frames, person = 0, 0, 0
    calls, seen = [], set()                  # each penalty called: (team, number), from the buffer at the foul
    strength = {}                            # shots by (team, "even" / "pp" / "sh")
    shots_now = [sum(m.w(SHOTS_P + 4 * q + 2 * t) for q in range(3)) for t in (0, 1)]
    while m.w(GSP) < 3 and frames < 200000:
        c = m.w(CLOCK)
        for _ in range(3):
            e.run(10)
            now = set()
            for slot in range(0, 64, 2):
                buf, o = m.at(PEN_BUFFER + slot)
                code, obj = buf[o], buf[o + 1] & 0x7F
                if code and obj < 12:
                    now.add((slot, code, obj))
                    if (slot, code, obj) not in seen:
                        calls.append((0 if obj < 6 else 1, code))
            seen = now
            box = m.w(IN_BOX)
            boxed = [(box >> 4) & 0xF, box & 0xF]
            for t in (0, 1):
                now_shots = sum(m.w(SHOTS_P + 4 * q + 2 * t) for q in range(3))
                if now_shots > shots_now[t]:
                    kind = "pp" if boxed[1 - t] > boxed[t] else "sh" if boxed[t] > boxed[1 - t] else "even"
                    strength[f"{t}{kind}"] = strength.get(f"{t}{kind}", 0) + now_shots - shots_now[t]
                shots_now[t] = now_shots
        frames += 30
        if m.w(CLOCK) > 300:                                               # 5-minute periods whatever the menu set
            m.setw(CLOCK, 300)
        if frames % 300 == 0:
            if any(m.w(PFLAGS + 2 * k) & 8 for k in range(12)):
                person += 1
            computer_only(m)
            lowload.breathe()
        still = still + 30 if m.w(CLOCK) == c else 0
        if still >= 900:                                                    # a break or a menu waiting: START
            e.run(4, hold=["START"])
            still = 0
    per = lambda base, t: sum(m.w(base + 4 * p + 2 * t) for p in range(3))
    goals = [per(GOALS_P, t) for t in (0, 1)]
    shots = [per(SHOTS_P, t) for t in (0, 1)]
    return dict(game=n, rom=Path(rom).name, frames=frames, person_seen=person, goals=goals, shots=shots,
                saves=[shots[1] - goals[1], shots[0] - goals[0]],                # saves by each team's goalie
                checks=[m.w(CHECKS), m.w(CHECKS + 2)], penalties=[m.w(PENS), m.w(PENS + 2)],
                passes=[[m.w(PASSES_C), m.w(PASSES_T)], [m.w(PASSES_C + 2), m.w(PASSES_T + 2)]],
                reached_p4=m.w(GSP) >= 3, optpen_found=optpen_found, calls=calls, shot_strength=strength,
                **(extra(e, m) if extra else {}))


def make_30(rom, out):
    data = bytearray(Path(rom).read_bytes())
    assert data[0xF8517:0xF8522].hex() == "a58338ed016df0f8ee6d7d", "not the SA-1 build's Gameloop"
    data[0xF8517:0xF8522] = bytes.fromhex("a58338ed016d4af0f7eaea")
    Path(out).write_bytes(data)


def main():
    if sys.argv[1] == "--make-30":
        make_30(sys.argv[2], sys.argv[3])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        r = game(rom, n)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
