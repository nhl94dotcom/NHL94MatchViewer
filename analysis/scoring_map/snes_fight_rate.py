"""How often fights happen on McMarkis's Fighting build with Fighting On and After Whistle (2026-11-09, for the help's
Fighting line). snes_60fps_cvc's games (the computer on both sides, Montreal at home against Los Angeles, 5-minute
periods, penalties On, No Offside, each game its own random seed, regulation only) with OptFights ($E708, in BW-RAM
on the SA-1 build: snes.SA1_MOVED) set to the setting at the start and every 5 s. Fights are counted from the
penalties called (snes_60fps_cvc's buffer watch: $2A / $2C fighting majors, $2E instigator; a fight gives both
fighters a major) and, as a check, from the fighters' pflags $0400 (pffight) every 10 frames: each run of frames
with a fighter is one fight.

python snes_fight_rate.py ROM on|whistle|none GAMES OUT.jsonl"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lowload  # noqa: E402
import snes_60fps_cvc as cvc  # noqa: E402
from systems import snes  # noqa: E402

OPTFIGHTS, PFLAGS, FIGHTER = 0xE708, 0x1283, 0x0400
SETTING = {"on": 0, "whistle": 2, "none": None}   # none: a build with no Fighting option (its fights always on):
                                                  # nothing poked ($E708 is ordinary work RAM there)


def at(m, a):
    if m.sa1:
        for lo, hi, to in snes.SA1_MOVED:
            if lo <= a < hi:
                return m.bw, to + a - lo
    return m.at(a)


def setw(m, a, v):
    buf, o = at(m, a)
    buf[o], buf[o + 1] = v & 0xFF, (v >> 8) & 0xFF


def main():
    rom, which, games, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), Path(sys.argv[4])
    value = SETTING[which]
    lowload.gentle()
    orig = cvc.computer_only
    episodes = {"n": 0, "on": False}

    def computer_only(m):
        orig(m)
        if value is not None:
            setw(m, OPTFIGHTS, value)

    cvc.computer_only = computer_only
    orig_run = None

    def extra(e, m):
        return {"fights_seen": episodes["n"], "setting": which}

    # every frame batch: the pffight watch (the cvc loop runs e.run(10) three times per step)
    import menu_shots as M
    orig_emulator = M.emulator

    def emulator(r):
        e = orig_emulator(r)
        run = e.run
        holder = {}

        def run10(n=1, **kw):
            run(n, **kw)
            m = holder.get("m")
            if m is not None:
                f = any(m.w(PFLAGS + 2 * k) & FIGHTER for k in range(12))
                if f and not episodes["on"]:
                    episodes["n"] += 1
                episodes["on"] = f
        e.run = run10
        e._holder = holder
        return e

    M.emulator = emulator
    orig_mem = cvc.Mem

    class Mem(orig_mem):
        def __init__(self, e, r):
            super().__init__(e, r)
            if hasattr(e, "_holder"):
                e._holder["m"] = self

    cvc.Mem = Mem
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        episodes.update(n=0, on=False)
        r = cvc.game(rom, n, extra)
        r["fighting_majors"] = sum(1 for _, c in r["calls"] if c in (0x2A, 0x2C))
        r["instigators"] = sum(1 for _, c in r["calls"] if c == 0x2E)
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps({k: r[k] for k in ("game", "setting", "goals", "checks", "penalties", "fighting_majors",
                                             "instigators", "fights_seen", "reached_p4", "person_seen")}), flush=True)


if __name__ == "__main__":
    main()
