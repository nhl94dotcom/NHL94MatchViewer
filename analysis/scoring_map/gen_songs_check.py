"""Organ songs by home team, played (2026-11-09, for NOSE4Web b21423e: TeamSongs moved so 30-team ROMs read their own
rows). From one play state of each ROM, HomeTeam ($C330) is set to a team and the events that pick a song are driven:
a home goal (slot 3: the puck sent into the net the home team attacks), the faceoff after it (LeadSong, with one team's
players-on-ice count tmap set lower first, so the home team ahead (slot 4) or the away team ahead (slot 1)), the end of
the period and the next one's start (slot 0, then the faceoff slot 2) and the late-game tune in the 3rd (slot 5). Every
ChooseSong is caught by SongNum ($D6C8), written $7FFF before each event, with SongIndex ($D6CC) and HmTeam ($D6CA).

python gen_songs_check.py ROM OUT TEAM [TEAM ...]"""
import json
import sys
from pathlib import Path

import lowload
import gen_1on1_edit_lines as G

SONGNUM, HMTEAM, SONGIDX, HOMETEAM = 0xD6C8, 0xD6CA, 0xD6CC, 0xC330
PERIOD, CLOCK, HSCORE, ASCORE = 0xC466, 0xC468, 0xC6DA, 0xCA3E
TMAP_H, TMAP_A = 0xC6CE + 0x24, 0xCA32 + 0x24
PUCK = 0xB04A + 14 * 0x80
SCREEN = 0xFFF7


def watch(r, frames, out, label, poke=None, press=False, team=None):
    e = r.e
    e.setw(SONGNUM, 0x7FFF)
    last = 0x7FFF
    for f in range(frames):
        if poke:
            poke()
        if team is not None:
            e.setw(HOMETEAM, team)      # the intermission puts the real home team back
        if press and f % 60 == 0:
            r.step(4, hold=["C"])           # the intermission screens wait for a button (and leave $FFF7 at 0)
        else:
            r.step(1)
        s = e.w(SONGNUM)
        if s != last:
            out.append(dict(event=label, frame=f, slot=e.w(SONGIDX), hmteam=e.w(HMTEAM), song=s,
                            period=e.w(PERIOD), clock=e.w(CLOCK)))
            last = s
            e.setw(SONGNUM, 0x7FFF)
            last = 0x7FFF
        if f % 120 == 0:
            lowload.breathe()


def goal(r, out, label):
    """Send the puck into the net the home team attacks, from just inside the goalie (both ends tried; the one that
    scores for Home is kept). Returns the state just before, with the puck on its way, or None."""
    e = r.e
    st = e.serialize()
    for y, vy in ((258, 6000), (-258, -6000)):
        e.unserialize(st)
        h0 = e.w(HSCORE)
        e.setw(PUCK, 3)
        e.setw(PUCK + 0x14, y)
        e.setw(PUCK + 0x18, 0)
        e.setw(PUCK + 0x28, 0)
        e.setw(PUCK + 0x2A, vy)
        e.setb(PUCK + 0x60, 0xFF)
        e.setw(PUCK + 0x5E, 0)
        before = e.serialize()
        r.step(40)
        if e.w(HSCORE) != h0:
            e.unserialize(before)
            return True
    e.unserialize(st)
    return None


def main():
    rom, outdir, teams = sys.argv[1], Path(sys.argv[2]), [int(t) for t in sys.argv[3:]]
    r = G.Run(rom, outdir)
    r.to_play()
    r.step(120)
    base = r.e.serialize()
    res = {}
    for team in teams:
        out = []
        e = r.e
        # a home goal, then the faceoff with the home team a man up (slot 4)
        e.unserialize(base)
        e.setw(HOMETEAM, team)
        e.setw(CLOCK, 120)                  # the faceoff tune: the first faceoff past half a period 1 or 2
        side = goal(r, out, "goal")
        if side:
            watch(r, 2400, out, "goal at 2:00, then the faceoff")
        # LeadSong at the faceoff after a goal, one team a man up (tmap); the power-play display's sf2pwrplay
        # (sflags2 byte $C2EE bit 5) cleared each frame, since it also blocks LeadSong (see the notes)
        for lab, hm, aw in (("home ahead", 6, 5), ("away ahead", 5, 6)):
            e.unserialize(base)
            e.setw(HOMETEAM, team)
            if goal(r, out, "goal"):
                watch(r, 2400, out, "goal, then faceoff, " + lab,
                      poke=lambda hm=hm, aw=aw: (e.setw(TMAP_H, hm), e.setw(TMAP_A, aw), e.setb(0xC2EE, e.b(0xC2EE) & 0xDF)),
                      team=team)
        # the end of the period and the next one's start
        e.unserialize(base)
        e.setw(HOMETEAM, team)
        e.setw(CLOCK, 2)
        watch(r, 2400, out, "period end, next period", press=True, team=team)
        # the late-game tune: the 3rd period with little time left
        e.unserialize(base)
        e.setw(HOMETEAM, team)
        e.setw(PERIOD, 2)
        e.setw(CLOCK, 40)
        watch(r, 900, out, "3rd period, 40 s left", team=team)
        res[team] = out
        print(team, [(x["event"][:12], x["slot"], hex(x["song"])) for x in out], flush=True)
    (outdir / "songs.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
