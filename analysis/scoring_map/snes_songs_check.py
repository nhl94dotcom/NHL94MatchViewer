"""SNES organ songs by home team, played (2026-11-09, for NOSE4Web 5f3a2bc's song editing). In live play
(snes_assist_stick_test.Game) with HomeTeam ($1C98) set to a team, the events that start a team song are driven and
the song the game starts is read: PlayTeamSong stores the slot + 1 in cursong ($0CC3) and MusicStart the song's
address in SongPtr ($07ED) and its bank in EventPtr+2 (direct page $58); MusicOn ($07F3) is written 0 before each
event and watched.
- slot 3: a home goal (the puck slid into the net the home team attacks, the goalie aside);
- the faceoff after it, with MusicOn held 0 so its song can start: PBnum ($1624, home x 16 + visitors in the boxes)
  $01 (a home power play: slot 1), $10 (a home penalty kill: slot 4), or 0 with percue ($0CC1) set (a period's first
  faceoff: slot 0).

python snes_songs_check.py ROM TEAM [TEAM ...]"""
import sys

from snes_assist_stick_test import Game, PUCKC, CARRIER2, POSITION, PFGOAL, PUCK, ZPOS

HOMETEAM, CURSONG, SONGPTR, BANK, MUSICON, PBNUM, PERCUE, GOALS = 0x1C98, 0x0CC3, 0x07ED, 0x0058, 0x07F3, 0x1624, 0x0CC1, 0x178E


def song(G):
    return (G.w(BANK) & 0xFF) << 16 | G.w(SONGPTR)


def event(G, base, team, kind, pb=0, percue=0):
    e = G.e
    e.unserialize(base)
    G.setw(HOMETEAM, team)
    G.setw(0x1632, 250)
    hk = next(k for k in range(6) if G.w(POSITION + 2 * k) not in (0, 0xFFFF))
    up = 1 if G.w(PFGOAL + 2 * hk) else -1
    gk = next(k for k in range(6, 12) if G.w(POSITION + 2 * k) == 0)
    G.setw(MUSICON, 0)
    G.setw(CURSONG, 0)
    g0 = G.w(GOALS)
    G.setw(PUCKC, 0xFFFF)
    G.setw(CARRIER2, 0xFFFF)
    picks = []
    last = (0, 0)
    for f in range(1500):
        if f < 60:
            G.put(gk, 90, 240 * up)
            if f == 0:
                G.put(PUCK, 0, 240 * up, 0, 0x2000 * up)
                G.setw(ZPOS, 0)
        if G.w(GOALS) != g0 and kind == "faceoff":
            # after the goal song: hold the music off and set the boxes / the period cue for the faceoff
            if not any(p[0] == 4 for p in picks):
                pass
            else:
                G.setw(MUSICON, 0)
                G.setw(PBNUM, pb)
                if percue:
                    G.setw(PERCUE, 0xFFFF)
        G.run(hold=["B"] if f % 40 == 0 and f > 300 else [])
        cur = (G.w(CURSONG), song(G))
        if cur != last and cur[0]:
            picks.append((cur[0], cur[1]))
            last = cur
            if kind == "goal" and cur[0] == 4:
                break
            if kind == "faceoff" and cur[0] != 4:
                break
    return [("slot %d" % (c - 1), "$%06X" % s) for c, s in picks]


def main():
    rom, teams = sys.argv[1], [int(t) for t in sys.argv[2:]]
    G = Game(rom)
    base = G.g.bases[0]
    for team in teams:
        out = {"home goal": event(G, base, team, "goal"),
               "faceoff, home power play (PBnum $01)": event(G, base, team, "faceoff", pb=0x01),
               "faceoff, home penalty kill (PBnum $10)": event(G, base, team, "faceoff", pb=0x10),
               "faceoff, period start (percue)": event(G, base, team, "faceoff", percue=1)}
        print(f"== {rom.split('/')[-1]} team {team}")
        for k, v in out.items():
            print(f"   {k}: {v}", flush=True)


if __name__ == "__main__":
    main()
