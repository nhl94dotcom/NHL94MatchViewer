"""Injuries, knockdowns and holds a game, the computer against itself with line changes on (SNES, 2026-11-09;
gen_injury_baseline.py is the Genesis one): the "option off" half of the check on NOSE4Web's hit option.
snes_60fps_cvc's games (Montreal at home against Los Angeles, 5-minute periods, penalties on, each game its own seed,
regulation), with Line Changes set On in RAM at Game Setup (OptLine $34C6 = 1, before the game starts). Every 10
frames: a player newly out injured (tmpdst $1852, the visitors +$34: $FFFD out, $FFFC out for the game), a player
newly flailing (held or hooked: SPA $11A3 = $F46A). At the end: knockdowns (the game's team checks $17B6, which FallDown
counts) and the lowest energy any skater on the ice reached (tmpde $17EA).

python snes_injury_baseline.py ROM GAMES OUT.jsonl"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import lowload  # noqa: E402
import menu_shots as M  # noqa: E402
import snes_60fps_cvc as cvc  # noqa: E402

OPTLINE, TMPDST, TMPDE, SPA, FLAIL = 0x34C6, 0x1852, 0x17EA, 0x11A3, 0xF46A


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    st = {}
    orig_play, orig_emulator, orig_mem = M.play, M.emulator, cvc.Mem

    def play(e, script, tmp):
        if script.startswith("START w240 START w200") and "m" in st:
            st["m"].setw(OPTLINE, 1)          # still at Game Setup: line changes on before the game starts
        return orig_play(e, script, tmp)

    def emulator(r):
        e = orig_emulator(r)
        run = e.run

        def watched(n=1, **kw):
            run(n, **kw)
            m = st.get("m")
            if m is None or not st.get("live"):
                return
            for t in range(2):
                for s in range(26):
                    v = m.w(TMPDST + 0x34 * t + 2 * s)
                    if v in (0xFFFD, 0xFFFC) and (t, s) not in st["out"]:
                        st["out"].add((t, s))
                        st["injuries"].append({"team": t, "slot": s, "game": v == 0xFFFC})
                    elif v == 0xFFFF:
                        st["out"].discard((t, s))
                        st["low"] = min(st["low"], m.w(TMPDE + 0x34 * t + 2 * s))
            for k in range(12):
                f = m.w(SPA + 2 * k) == FLAIL
                if f and not st["flail"][k]:
                    st["holds"] += 1
                st["flail"][k] = f
        e.run = watched
        return e

    class Mem(orig_mem):
        def __init__(self, e, r):
            super().__init__(e, r)
            st["m"] = self

    M.play, M.emulator, cvc.Mem = play, emulator, Mem
    orig_co = cvc.computer_only

    def computer_only(m):
        orig_co(m)
        st["live"] = True                    # play has started (computer_only is first called then)
    cvc.computer_only = computer_only
    done = {json.loads(line)["game"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        st.clear()
        st.update(out=set(), injuries=[], holds=0, flail=[False] * 12, low=0x1000, live=False)
        r = cvc.game(rom, n, lambda e, m: {"optline": m.w(OPTLINE)})
        res = {"game": n, "injuries": st["injuries"], "holds": st["holds"], "knockdowns": r["checks"],
               "lowest_energy": st["low"], "goals": r["goals"], "optline": r["optline"], "reached_p4": r["reached_p4"]}
        with out.open("a") as fh:
            fh.write(json.dumps(res) + "\n")
        print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
