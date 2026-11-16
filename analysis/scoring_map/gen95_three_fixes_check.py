"""NHL '95 (Genesis): NOSE4Web's aggression, comeback bonus and open-net one-timer fixes played (2026-11-16, b9fa5f3).
setplayer stores Aggression as AttributeCalc's result masked to 4 bits ($83C7C: a 16-30 rating wraps to 0-14); the fix
clamps it to 0-30 and halves it. setplayer's third-period bonus ($83A2C) is on in the first half (bgt), the fix in the
second (blt); overtime takes the bonus throughout either way. shotdiradj's aim when the sightline through the goalie
misses the net ($84ED2): passdir 0 (high middle), the fix 8 (middle, mid-height).

Modes (one ROM per process; STATE: gen95_assist_check's live state):
  agg ROM OUT       a Regular Game for each of several team pairs (Team 1 t, Team 2 t + 13), every player's working
                    Aggression (+$73) at the faceoff, with position and roster place
  comeback ROM STATE OUT
                    a goal scored from live play; during its celebration the period, clock and score set (period 3
                    or overtime; the clock in the first half (90% left) or the second (20%); Home one down or one
                    up); after the faceoff (setplayer) Home's skaters' working Checking (+$75): trailing minus leading
  opennet ROM STATE OUT
                    gen95_assist_check's one-timer play from shooter spots across the slot, the away goalie left in
                    position or held wide of the far post on the goal line until the strike; passdir ($FFBADA) at the
                    strike and the goal"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen95_assist_check as G  # noqa: E402
from emu import Emu  # noqa: E402

GSP, CLOCK, GMODE, PASSDIR, OTPLAYER = 0xC020, 0xC022, 0xBEF0, 0xBADA, 0xBB72
AGGRESS, CHECKING, POSITION = 0x73, 0x75, 0x34


def agg(rom, out):
    sys.path.insert(0, str(Path.home() / "NHL94_scoring_map" / "runs" / "nhl95" / "logos"))
    from nav import Nav, TEAM1, TEAM2
    rows = []
    for t in range(0, 13, 2):
        n = Nav(rom, str(out / f"agg_{t}"))
        n.team(1, t, TEAM1)
        n.team(2, t + 13, TEAM2)
        n.press("START", 300); n.press("START", 60); n.e.run(1800); n.press("START", 400); n.press("START", 10)
        n.e.run(200)
        for k in range(12):
            r = G.rec(k)
            rows.append(dict(teams=(t, t + 13), rec=k, pos=n.e.b(r + POSITION + 1), place=n.e.b(r + 0x66),
                             aggress=n.e.b(r + AGGRESS)))
        del n
    (out / "agg.json").write_text(json.dumps(rows))
    print(len(rows), "players")


def comeback(rom, state, out):
    e = Emu(rom)
    base = Path(state).read_bytes()
    res = []
    for gsp in (2, 3):
        for part, frac in (("first half", 0.9), ("second half", 0.2)):
            row = {}
            for lead, (hs, as_) in (("trailing", (1, 2)), ("leading", (2, 1))):
                log = []
                p = G.Play(e, base, {G.A: (0, 150), G.D: (110, -220)}, log)
                p.into_net("goal")
                length = 600
                e.setw(GSP, gsp)
                e.setw(CLOCK, int(length * frac))
                e.setw(G.TEAM + 0x0C, hs)
                e.setw(G.TEAM + G.TMSIZE + 0x0C, as_)
                ran = False
                for f in range(4000):
                    e.run(1)
                    if f > 60 and not e.b(GMODE) & 1 and e.w(CLOCK) < int(length * frac):
                        ran = True
                        break
                row[lead] = [e.b(G.rec(k) + CHECKING) for k in range(6) if e.b(G.rec(k) + POSITION + 1) != 0]
                row[lead + " ran"] = ran
            row["bonus (trailing - leading)"] = [a - b for a, b in zip(row["trailing"], row["leading"])]
            res.append(dict(period="third" if gsp == 2 else "overtime", part=part, **row))
            print(res[-1], flush=True)
    # overtime: regulation run out tied 2-2 (a goal in overtime ends the game); at the overtime faceoff both teams'
    # skaters' working Checking against the third period's no-bonus values (the leading ones above)
    e.unserialize(base)
    e.setw(GSP, 2)
    e.setw(CLOCK, 2)
    e.setw(G.TEAM + 0x0C, 2)
    e.setw(G.TEAM + G.TMSIZE + 0x0C, 2)
    ok = False
    for f in range(20000):
        e.run(1, hold=["START"] if f % 180 < 3 and e.b(GMODE) & 1 else [])
        if e.w(GSP) == 3 and not e.b(GMODE) & 1 and e.w(CLOCK) < 600:
            ok = True
            break
    ot = dict(period="overtime", reached=ok, gsp=e.w(GSP), clock=e.w(CLOCK),
              home=[e.b(G.rec(k) + CHECKING) for k in range(6) if e.b(G.rec(k) + POSITION + 1) != 0],
              away=[e.b(G.rec(k) + CHECKING) for k in range(6, 12) if e.b(G.rec(k) + POSITION + 1) != 0])
    res.append(ot)
    print(ot, flush=True)
    (out / "comeback.json").write_text(json.dumps(res))


def opennet(rom, state, out):
    e = Emu(rom)
    base = Path(state).read_bytes()
    res = []
    for bx in (-40, -20, 0, 20, 40):
        for by in (170, 200, 225):
            for goalie in ("in position", "out wide"):
                log = []
                p = G.Play(e, base, {G.A: (0, 110), G.C: (bx // 2, 150), G.B: (bx, by), G.D: (110, -220)}, log)
                if not p.pick_up(G.A, "A") or not p.pass_to(G.A, G.C, "A to C"):
                    res.append(dict(bx=bx, by=by, goalie=goalie, result="setup failed"))
                    continue
                for _ in range(10):
                    p.frame()
                st = e.serialize()
                s0 = G.struct_bytes(e)
                got = None
                for press in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16):
                    e.unserialize(st)
                    struck, aim, scored = False, None, False
                    for f in range(150):
                        held = ["UP"] + (["B"] if 2 <= f < 5 else []) + (["C"] if press <= f < press + 3 else [])
                        if goalie == "out wide" and not struck:
                            far = -1 if bx > 0 else 1
                            e.setw(G.rec(G.AWAYG), far * 60)
                            e.setw(G.rec(G.AWAYG) + 0x14, 258)
                            for off in (0x28, 0x2A, 0x2C):
                                e.setw(G.rec(G.AWAYG) + off, 0)
                        p.frame(held, hold=[k for k in p.keep if k not in (G.C, G.B)] + ([G.B] if f < 2 else []))
                        if e.w(OTPLAYER) == G.B and not struck:
                            struck = True
                        if struck:
                            aim = e.w(PASSDIR)             # written at the strike (shotdiradj), held after it: the
                                                           # one-timer is armed (onetimerplayer) before the pass arrives
                        if G.goal_seen(e, s0):
                            scored = True
                            break
                    if struck:
                        got = dict(bx=bx, by=by, goalie=goalie, press=press, aim=aim, goal=scored, result="ok")
                        break
                res.append(got or dict(bx=bx, by=by, goalie=goalie, result="no one-timer"))
                print(res[-1], flush=True)
    (out / "opennet.json").write_text(json.dumps(res))


def main():
    mode = sys.argv[1]
    if mode == "agg":
        out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
        agg(sys.argv[2], out)
    else:
        out = Path(sys.argv[4]); out.mkdir(parents=True, exist_ok=True)
        {"comeback": comeback, "opennet": opennet}[mode](sys.argv[2], sys.argv[3], out)


if __name__ == "__main__":
    main()
