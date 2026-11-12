"""Computer-against-computer games recorded as the helper records people's games (2026-11-11, the user: how a team the
computer plays differs from one people play; for better simulations and the bot). Each game: power-on, Game Setup
with the league's settings (5-minute periods, penalties on except offsides (Genesis) / On, No Offside (SNES), line
changes off), a matchup of its own (game n: home team (7 n) mod 26, visitors (7 n + 11) mod 26, the two different), its
own random seed, the computer on both sides (pads taken off every second), START tapped through the screens that wait;
recorded from the first frame of play to the end of the game (the final horn, or 60 minutes (real) at most): every
frame a sample of the system's BLOCKS as the helper keeps them (an 8-byte millisecond stamp, then the blocks: the
Genesis words in the emulator's host order, as RetroArch shows them), a full RAM snapshot every 10 s, capture.json.
Then tools/export_match.py converts it, the same converter as the people's games. Gentle (lowload); one game a
process.

python cvc_record.py genesis|snes ROM OUT GAMES [FIRST]   -> OUT/captures/<name>, OUT/matches/<name>.js"""
import gzip
import json
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import lowload  # noqa: E402

FPS = 60


def teams_for(n):
    h = (7 * n) % 26
    a = (7 * n + 11) % 26
    return h, (a + 1) % 26 if a == h else a


def record_genesis(rom, n, folder, fast, full):
    import gen_ot_check as G
    from emu import Emu
    from systems import genesis
    e = Emu(rom)
    G.to_setup(e, folder)
    h, a = teams_for(n)
    # the matchup is HomeTeam / VisTeam ($C330 / $C332); Opt1team / Opt2team are the pads' sides
    for addr, v in ((0xC330, h), (0xC332, a), (0xD050, 0), (0xD056, 2), (0xD058, 1)):
        e.setw(addr, v)
    if not G.into_play(e):
        return None
    e.setl(0xD066, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    ram = memoryview(e.ram)
    count = 0
    frame, still, last = 0, 0, None
    while frame < 60 * 60 * FPS:
        if frame % 60 == 0:
            e.setw(0xC328, 0)
            e.setw(0xC32A, 0)
            for k in range(12):
                e.setb(0xB04A + 0x80 * k + 0x62, e.b(0xB04A + 0x80 * k + 0x62) & ~8)
            c = e.w(0xC468)
            still = still + 1 if c == last else 0
            last = c
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 1
        ms = frame * 1000 // FPS
        fast.write(struct.pack("<q", ms) + b"".join(bytes(ram[s:s + k]) for s, k in genesis.BLOCKS))
        count += 1
        if frame % (10 * FPS) == 0:
            full.write(struct.pack("<q", ms) + bytes(ram[:genesis.RAM_SIZE]))
            lowload.breathe()
        if e.w(0xC466) >= 4:                       # the game over: a few seconds more, then done
            for _ in range(5 * FPS):
                e.run(1)
                frame += 1
                fast.write(struct.pack("<q", frame * 1000 // FPS) + b"".join(bytes(ram[s:s + k]) for s, k in genesis.BLOCKS))
                count += 1
            break
    return genesis, count, (h, a)


def record_snes(rom, n, folder, fast, full):
    import menu_shots as M
    from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, OPTPEN, SEED, Mem, computer_only
    from systems import snes
    e = M.emulator(rom)
    m = Mem(e, rom)
    h, a = teams_for(n)
    # Game Setup: row 1 Home, row 2 Visitor (RIGHT until HomeTeam $1C98 / VisTeam $1C9A read the team, as
    # snes_logo_spill_check; writing Opt1team / Opt2team didn't take), then rows 3 and 4 as snes_60fps_cvc sets them
    # (from 1765 frames of intro on, the presses land before Game Setup: the waits of games 0-4 again)
    M.play(e, f"w{1500 + 53 * (n % 5)} START w240 START w240 DOWN w20", folder)
    for addr, team in ((0x1C98, h), (0x1C9A, a)):
        for _ in range(40):
            if m.w(addr) == team:
                break
            M.play(e, "RIGHT w20", folder)
        M.play(e, "DOWN w20", folder)
    if (m.w(0x1C98), m.w(0x1C9A)) != (h, a):
        return None
    M.play(e, "RIGHT*2 DOWN RIGHT*2 w30", folder)
    M.play(e, "START w240 START w200 w2400", folder)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    ram = memoryview(e.ram)
    count = 0
    frame, still, last = 0, 0, None
    while frame < 60 * 60 * FPS:
        if frame % 300 == 0:
            computer_only(m)
        c = m.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        e.run(1, hold=["START"] if still > 5 * FPS and frame % 60 < 4 else [])
        frame += 1
        ms = frame * 1000 // FPS
        fast.write(struct.pack("<q", ms) + b"".join(bytes(ram[s:s + k]) for s, k in snes.BLOCKS))
        count += 1
        if frame % (10 * FPS) == 0:
            full.write(struct.pack("<q", ms) + bytes(ram[:snes.RAM_SIZE]))
            lowload.breathe()
        if m.w(GSP) >= 4:
            e.run(120)
            break
    return snes, count, (h, a)


def one(system, rom, n, out):
    folder = out / "captures" / f"cvc_{system}_{n:02d}"
    folder.mkdir(parents=True, exist_ok=True)
    with gzip.open(folder / "fast.bin.gz", "wb", compresslevel=3) as fast,             gzip.open(folder / "full.bin.gz", "wb", compresslevel=3) as full:
        got = (record_genesis if system == "genesis" else record_snes)(rom, n, folder, fast, full)
    if not got:
        print(json.dumps({"game": n, "error": "never reached play"}))
        return
    mod, count, teams = got
    layout = {"blocks": [list(b) for b in mod.BLOCKS], "recorded_by": "cvc_record", "system": mod.NAME}
    (folder / "capture.json").write_text(json.dumps(layout))
    print(json.dumps({"game": n, "teams": teams, "samples": count, "folder": str(folder)}))


def main():
    system, rom, out, games = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
    first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    lowload.gentle()
    (out / "matches").mkdir(parents=True, exist_ok=True)
    for n in range(first, first + games):
        r = subprocess.run([sys.executable, __file__, "--one", system, rom, str(n), str(out)], capture_output=True, text=True)
        lines = [x for x in r.stdout.splitlines() if x.startswith("{")]
        info = json.loads(lines[-1]) if lines else {"game": n, "error": r.stderr[-400:]}
        print(json.dumps(info), flush=True)
        if "folder" in info:
            c = subprocess.run([sys.executable, str(ROOT / "tools" / "export_match.py"), info["folder"], "--rom", rom,
                                "--out", str(out / "matches")], capture_output=True, text=True)
            print("  converted:", (c.stdout.strip().splitlines() or [c.stderr[-300:]])[-1], flush=True)
        lowload.breathe()


if __name__ == "__main__":
    if sys.argv[1] == "--one":
        one(sys.argv[2], sys.argv[3], int(sys.argv[4]), Path(sys.argv[5]))
    else:
        main()
