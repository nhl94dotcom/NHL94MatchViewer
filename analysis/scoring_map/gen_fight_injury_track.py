"""What becomes of a fight injury's tmpdst word over the rest of a game (2026-11-13, for NOSE4Web's Genesis shootout
injury skip): chaos's fight patch, as in nhl94_fighting_blood.bin, puts the loser hurt in a fight through the game's
setInjuryType and then overwrites his tmpdst with $112C ($1000: not counted against tmap; $12C: 300 s).

Computer games (gen_ot_check's boot, the computer on both sides, the seed from the game's number), Fighting On ($FFF080
= 1), penalties On Except Off-sides, every player's fighting rating (+$74) at 14 so fights come, 5-minute periods.
Each second: every team's tmpdst words ($C6CE / $CA32 + $66, 26 words); a word that becomes $112C starts a track of
that player: each change of his word (game time, value), his team's tmap and penalty box list (tmboxlist, +$66 + 52,
roster offsets, $FF ends), and whether he is on the ice (an object with his roster index, +$66, at position 1-6).
Runs whole games (through overtime when tied) until TRACKS players have been followed or GAMES games played.

--force: every player's +$75 (Checking) held at $7F, so fight losers are hurt (the patch's roll at $200814-$20081E).

python gen_fight_injury_track.py ROM OUT.jsonl [GAMES] [TRACKS] [FIRST] [--force]"""
import json
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTPEN, PERLEN, SEED, FIGHTING = 0xD056, 0xD050, 0xD066, 0xF080
CONT1, CONT2, GSP, CLOCK, SCREEN = 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
TEAMS, TMPDST, TMAP = (0xC6CE, 0xCA32), 0x66, 0x24
BASE, SZ = 0xB04A, 0x80
FORCE = "--force" in sys.argv
if FORCE:
    sys.argv.remove("--force")


def game(rom, n, tmp, want):
    e = Emu(rom)
    G.to_setup(e, tmp)
    e.setw(OPTPEN, 2)
    e.setw(PERLEN, 0)
    e.setw(FIGHTING, 1)
    if not G.into_play(e):
        return {"game": n, "error": "never reached play"}
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    tracks, f, still, last = {}, 0, 0, None
    while f < 60 * 60 * 50:
        for k in range(12):
            e.setb(BASE + SZ * k + 0x74, 14)
            if FORCE:
                e.setb(BASE + SZ * k + 0x75, 0x7F)   # the patch hurts the loser when its roll <= the winner's +$75
        e.setw(FIGHTING, 1)
        e.setw(OPTPEN, 2)
        e.run(1, hold=["START"] if still >= 8 and f % 60 < 4 else [])
        f += 1
        if f % 60:
            continue
        e.setw(CONT1, 0)
        e.setw(CONT2, 0)
        for k in range(12):
            e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        if f % 3600 == 0:
            lowload.breathe()
        g = e.w(GSP)
        if g >= 4 or (g == 3 and e.w(TEAMS[0] + 0xC) != e.w(TEAMS[1] + 0xC) and c == 0):
            break
        for t in (0, 1):
            b = TEAMS[t]
            for i in range(26):
                v = e.w(b + TMPDST + 2 * i)
                key = f"{t}:{i}"
                if v == 0x112C and key not in tracks:
                    tracks[key] = {"team": t, "roster": i, "log": []}
                if key in tracks:
                    tr = tracks[key]
                    on = any(e.b(BASE + SZ * k + 0x66) == i and 1 <= e.b(BASE + SZ * k + 0x35) <= 6
                             for k in range(6 * t, 6 * t + 6))
                    box = []
                    for j in range(16):
                        x = e.b(b + TMPDST + 52 + j)
                        if x >= 0x80:
                            break
                        box.append(x // 2)
                    row = [f"{v:04X}", e.w(b + TMAP), on, box]
                    if not tr["log"] or tr["log"][-1][2:] != row:
                        tr["log"].append([g, c] + row)
    return {"game": n, "frames": f, "tracks": list(tracks.values())}


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    games = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    want = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    first = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    lowload.gentle()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.parent / "_boot"
    tmp.mkdir(parents=True, exist_ok=True)
    got = 0
    for n in range(first, first + games):
        r = game(rom, n, tmp, want)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        got += len(r.get("tracks", []))
        print(json.dumps({"game": n, "frames": r.get("frames"), "tracks": len(r.get("tracks", [])), "error": r.get("error")}),
              flush=True)
        lowload.breathe()
        if got >= want:
            break


if __name__ == "__main__":
    main()
