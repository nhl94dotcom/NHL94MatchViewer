"""NOSE4Web's SNES ports of fight momentum and blocked shots (2026-11-20, 87d2c57: NHL94_momentum_blocks.smc,
NHL94_momentum_blocks_allpages.smc, nhl94snes_2026_momentum_blocks.sfc, nhl94snes_SA1_momentum_blocks.sfc).

The builds' RAM (sneshacks.ts): momentum, the winner's team word (0 home, 1 visitors) and the timer word at $7E:FDF8 /
$FDFA (SA-1 $40:55E8 / $55EA); blocks, a byte per roster place at $7E:FE40 (the visitors from +$1A), the team totals
words at +$34 / +$36 (SA-1 $40:5600). The lift: +1 Agility and +1 Speed (at most 15) for the stored team's skaters
while the timer runs and the clock runs.

games: computer games (snes_60fps_cvc's boot and controls, 5-minute periods, penalties on; McMarkis's builds' OptFights
$E708 set On every second; NOSE4Web's fights on the retail builds are always on). Before the game starts (at the
pre-game menus, so before StartGame) the momentum words and every count are set to non-zero values: the game's start
must clear them. Every frame:
- fights (a skater's pflags $0400): the fighters; the knockout (the timer rising): the team word, each fighter's
  frames for 150 frames, screenshots of the first knockouts (the loser is the one that falls);
- the timer: each drop with the clock (two in one clock second, clock seconds skipped), while the clock is stopped
  ($15D6) none;
- blocks: shots (sflags $1000 rising, shotplayer $0D29), puckbody's signature (the puck's speed high bytes the offset
  from the skater, nopuck 8, puckvz 0), every count change matched to a body hit; goalies, teammates' shots, pucks
  without a shot in flight;
- the two RAM areas: every change that isn't one of those (the RAM watch); in period 2 the pause menu's Instant Replay
  (back and forward) and Game Stats, the areas compared before and after;
- the end: the counts against the totals.
boost: from one moment of play, the timer 0, then 90 for home, then for the visitors: each object's speed against the
timer-0 run (the frame it first differs).
screens: a game paused in period 2 with the counts set to known values: Player Stats (item 5, B) every page RIGHT,
Y (the other team), LEFT back; Game Stats (item 2, A) top and bottom, with penalties on and off.

python snes_momentum_blocks_check.py games ROM OUT GAMES [FIRST]  |  boost ROM OUT  |  screens ROM OUT"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

import lowload
import menu_shots as M
import snes_60fps_cvc as cvc

XPOS, YPOS, XVEL, YVEL, FRAME = 0x0D55, 0x0DB7, 0x0EC3, 0x0EE3, 0x0D97
POSITION, PFLAGS, PNUM, NOPUCK = 0x0F43, 0x1283, 0x12A3, 0x1203
PUCK, PUCKZ, PUCKVZ, PUCKC = 14, 0x0DF9, 0x0E01, 0x0AD9
SFLAGS, SHOTPLAYER, GMODE, SHOOTOUT = 0x15D8, 0x0D29, 0x15D4, 0x1D81
GSP, CLOCK, CLOCKSTOP, PSITEM, OPTPEN, OPTFIGHTS = 0x1630, 0x1632, 0x15D6, 0x0D15, 0x34C4, 0xE708
FIGHTER, FIGHTING = 0x0400, 0x1463
BODY = 9


class Ram:
    """The builds' own words: bank $7E (retail, 2 MB) or BW-RAM (SA-1)."""
    def __init__(self, e, m):
        self.buf = m.bw if m.sa1 else e.ram
        self.fm, self.blk = (0x55E8, 0x5600) if m.sa1 else (0xFDF8, 0xFE40)

    def w(self, a):
        return self.buf[a] | self.buf[a + 1] << 8

    def setw(self, a, v):
        self.buf[a], self.buf[a + 1] = v & 0xFF, (v >> 8) & 0xFF

    def team(self):
        return self.w(self.fm)

    def timer(self):
        return self.w(self.fm + 2)

    def counts(self):
        return bytes(self.buf[self.blk + i] for i in range(0x34))

    def totals(self):
        return [self.w(self.blk + 0x34), self.w(self.blk + 0x36)]

    def area(self):
        return bytes(self.buf[self.fm + i] for i in range(4)) + bytes(self.buf[self.blk + i] for i in range(0x38))


def sw(v):
    return v - 0x10000 if v & 0x8000 else v


def s8(v):
    return v - 256 if v > 127 else v


def o(k):
    return 2 * k


def boot(rom, n, before_start=None):
    e = M.emulator(rom)
    m = cvc.Mem(e, rom)
    tmp = Path("x_tmp_mb")
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", tmp)
    else:
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", tmp)
    m.setw(0x34BC, 0)                                   # regular season
    if before_start:
        before_start(e, m)
    M.play(e, "START w240 START w200 w2400", tmp)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    cvc.computer_only(m)
    m.setw(cvc.SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(cvc.SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    return e, m


def fights_on(m, mc):
    if mc:
        m.setw(OPTFIGHTS, 0)


def press(e, b, after=40):
    e.run(4, hold=[b])
    e.run(after)


def pause_item(e, m, item, out, tag):
    press(e, "START", 90)
    for _ in range(40):
        if m.w(PSITEM) == item:
            break
        press(e, "DOWN")
    press(e, "A", 300)
    if item == 1:
        for b in ("LEFT", "RIGHT"):
            e.run(240, hold=[b])
    e.screenshot(out / f"{tag}.png")
    for k in range(10):
        press(e, "START" if k % 2 == 0 else "A", 240)
        if m.w(SFLAGS) & 1 and not m.w(SFLAGS) & 0x0800:
            break
    for _ in range(40):
        if m.w(PSITEM) == 0:
            break
        press(e, "UP")
    press(e, "START", 240)


def game(rom, out, n, mc, hot=False):
    def before(e, m):
        r = Ram(e, m)
        r.setw(r.fm, 1)
        r.setw(r.fm + 2, 77)
        for i in range(0x34):
            r.buf[r.blk + i] = 5
        r.setw(r.blk + 0x34, 99)
        r.setw(r.blk + 0x36, 99)
        fights_on(m, mc)

    e, m = boot(rom, n, before)
    r = Ram(e, m)
    log = open(out / f"game{n}.jsonl", "w")

    def note(**k):
        log.write(json.dumps(k) + "\n")
        log.flush()
        print(k, flush=True)

    c = Counter()
    note(what="start of play", game=n, team=r.team(), timer=r.timer(), counts=sum(r.counts()), totals=r.totals(),
         clock=m.w(CLOCK))
    fight, ko, kos, prev_t, prev_gsp, drop_clk = None, None, 0, r.timer(), m.w(GSP), None
    prev_counts, prev_tot, prev_area = r.counts(), r.totals(), r.area()
    prev_shot, shooter, hits = False, None, []
    frames, still, last, paused_done = 0, 0, None, False
    p = o(PUCK)
    while m.w(GSP) < 3 and frames < 60 * 60 * 50:
        if frames % 60 == 0:
            cvc.computer_only(m)
            fights_on(m, mc)
            if hot:
                for k in range(12):
                    if m.w(POSITION + o(k)) != 0:
                        m.setw(FIGHTING + o(k), 14)
            if m.w(CLOCK) > 300:
                m.setw(CLOCK, 300)
            sig = m.w(CLOCK)
            still = still + 1 if sig == last else 0
            last = sig
            if frames % 3600 == 0:
                lowload.breathe()
        before = [(sw(m.w(XPOS + o(k))), sw(m.w(YPOS + o(k)))) for k in range(12)]
        pb = (sw(m.w(XPOS + p)), sw(m.w(YPOS + p)))
        e.run(1, hold=["START"] if still >= 15 and frames % 60 < 4 else [])
        frames += 1
        t, clk, gsp, stopped = r.timer(), m.w(CLOCK), m.w(GSP), m.w(CLOCKSTOP)
        explained = set()
        # ---- fights and momentum
        on = [k for k in range(12) if m.w(PFLAGS + o(k)) & FIGHTER]
        if on and fight is None:
            fight = dict(start=frames, who=set(on))
            c["fights"] += 1
        if fight is not None:
            fight["who"] |= set(on)
            if not on and frames - fight["start"] > 60:
                note(what="fight over", game=n, fighters=sorted(fight["who"]), frames=frames - fight["start"],
                     timer=r.timer(), team=r.team(), gsp=gsp, clock=clk)
                fight = None
        if t != prev_t:
            explained.add("timer")
            if t > prev_t:
                explained.add("team")
                kos += 1
                ko = dict(frame=frames, team=r.team(), was=prev_t, who=sorted(fight["who"]) if fight else [], frames={})
                drop_clk = None
                note(what="timer set", game=n, gsp=gsp, clock=clk, timer=t, was=prev_t, team=r.team(), fighters=ko["who"])
            elif prev_t - t == 1:
                c["timer drops"] += 1
                if stopped:
                    c["timer: drops with the clock stopped"] += 1
                if drop_clk is not None and gsp == prev_gsp:
                    if clk == drop_clk:
                        c["timer: two drops in one clock second"] += 1
                    elif abs(drop_clk - clk) > 1:
                        c["timer: clock seconds without a drop"] += 1
                drop_clk = clk
            else:
                c["timer jumps"] += 1
                note(what="timer jump", game=n, gsp=gsp, clock=clk, timer=t, was=prev_t)
        if ko is not None:
            for k in ko["who"]:
                ko["frames"].setdefault(k, []).append(m.w(FRAME + o(k)))
            d = frames - ko["frame"]
            if kos <= 3 and d in (0, 30, 60, 90, 120):
                e.screenshot(out / f"g{n}_ko{kos}_{d:03d}.png")
            if d >= 150:
                note(what="knockout", game=n, team=ko["team"], was=ko["was"], fighters=ko["who"],
                     frames={k: sorted(set(v)) for k, v in ko["frames"].items()},
                     last={k: v[-1] for k, v in ko["frames"].items()})
                ko = None
        if gsp != prev_gsp:
            note(what="period change", game=n, gsp_from=prev_gsp, gsp_to=gsp, timer=t, team=r.team())
        prev_t, prev_gsp = t, gsp
        # ---- blocks
        sf = m.w(SFLAGS)
        shot = bool(sf & 0x1000)
        if shot and not prev_shot:
            sp = m.w(SHOTPLAYER)
            shooter = sp // 2 if sp < 24 else None
            c["shots"] += 1
        vx, vy, vz = sw(m.w(XVEL + p)), sw(m.w(YVEL + p)), sw(m.w(PUCKVZ))
        hit = None
        if sw(m.w(PUCKC)) < 0:
            for k in range(12):
                if m.w(NOPUCK + o(k)) != 8:
                    continue
                ok = False
                for (ax, ay), (bx, by) in ((pb, before[k]), ((sw(m.w(XPOS + p)), sw(m.w(YPOS + p))),
                                                             (sw(m.w(XPOS + o(k))), sw(m.w(YPOS + o(k)))))):
                    dx, dy = ax - bx, ay - by
                    if math.hypot(dx, dy) > BODY or (dx == 0 and dy == 0):
                        continue
                    if abs(s8((vx >> 8) & 0xFF) - s8(dx & 0xFF)) <= 3 and abs(s8((vy >> 8) & 0xFF) - s8(dy & 0xFF)) <= 3:
                        ok = True
                if ok and vz == 0:
                    hit = k
                    break
        if hit is not None and not (m.w(GMODE) & 0x10):
            goalie = m.w(POSITION + o(hit)) == 0
            team = 1 if hit >= 6 else 0
            kind = ("no shot in flight" if not prev_shot else "shot, shooter unknown" if shooter is None
                    else "teammate's shot" if (shooter >= 6) == (team == 1) else "the other team's shot")
            if not hits or hits[-1][0] < frames - 8 or hits[-1][1] != hit:
                hits.append([frames, hit, team, kind + (" (goalie)" if goalie else ""), False])
        counts, tot = r.counts(), r.totals()
        if counts != prev_counts:
            for i in range(0x34):
                d = counts[i] - prev_counts[i]
                if d:
                    tm, slot = (0, i) if i < 0x1A else (1, i - 0x1A)
                    who = None
                    for h in hits:
                        if frames - h[0] <= 2 and h[2] == tm and m.w(PNUM + o(h[1])) == slot:
                            h[4] = True
                            who = h
                    c["counts: " + (("matched to a body hit: " + who[3]) if who else "NO body hit matched")] += 1
                    if d != 1:
                        c["count changes other than +1"] += 1
                    if not who:
                        note(what="count without a body hit", game=n, team=tm, slot=slot, d=d, clock=clk, gsp=gsp,
                             shot=prev_shot, shooter=shooter, puckz=sw(m.w(PUCKZ)), gmode=m.w(GMODE))
            explained.add("counts")
        if tot != prev_tot:
            explained.add("totals")
            if sum(tot) - sum(prev_tot) != sum(counts) - sum(prev_counts):
                c["totals not in step with the counts"] += 1
        area = r.area()
        if area != prev_area:
            fm_changed = area[:4] != prev_area[:4]
            if fm_changed and "timer" not in explained:
                c["RAM watch: momentum words changed unexplained"] += 1
                note(what="momentum RAM change", game=n, before=prev_area[:4].hex(), after=area[:4].hex(), gsp=gsp, clock=clk)
            if area[4:] != prev_area[4:] and not ({"counts", "totals"} & explained):
                c["RAM watch: block area changed unexplained"] += 1
                note(what="blocks RAM change", game=n, gsp=gsp, clock=clk)
        prev_counts, prev_tot, prev_shot, prev_area = counts, tot, shot, area
        # ---- the pause menu once, in period 2
        if not paused_done and gsp == 1 and clk < 200 and not stopped and not (m.w(SFLAGS) & 0x0801):
            paused_done = True
            a0 = r.area()
            pause_item(e, m, 1, out, f"g{n}_replay")
            a1 = r.area()
            pause_item(e, m, 2, out, f"g{n}_gamestats")
            a2 = r.area()
            note(what="pause menu", game=n, replay_unchanged=a0 == a1, game_stats_unchanged=a1 == a2)
            prev_area, prev_counts, prev_tot, prev_t = r.area(), r.counts(), r.totals(), r.timer()
    for h in hits:
        c[f"body hits: {h[3]}: {'counted' if h[4] else 'not counted'}"] += 1
    counts = r.counts()
    note(what="end", game=n, frames=frames, players=[sum(counts[:0x1A]), sum(counts[0x1A:])], totals=r.totals(),
         timer=r.timer(), **dict(c))


def boost(rom, out, mc):
    e, m = boot(rom, 0, lambda e, m: fights_on(m, mc))
    r = Ram(e, m)
    for _ in range(60 * 60):
        cvc.computer_only(m)
        e.run(1)
        if m.w(GSP) == 0 and m.w(CLOCK) < 270 and m.w(CLOCKSTOP) == 0:
            c0 = m.w(CLOCK)
            e.run(60)
            if m.w(CLOCK) != c0:
                break
    base = e.serialize()
    res = {}
    for tag, team, timer in (("off", 0, 0), ("home", 0, 90), ("away", 1, 90)):
        e.unserialize(base)
        r.setw(r.fm, team)
        r.setw(r.fm + 2, timer)
        rows = []
        for _ in range(40):
            e.run(1)
            rows.append([(m.w(XVEL + o(k)), m.w(YVEL + o(k))) for k in range(12)])
        res[tag] = rows
    lines = []
    for tag in ("home", "away"):
        for k in range(12):
            first = next((f for f in range(40) if res[tag][f][k] != res["off"][f][k]), None)
            lines.append(dict(run=tag, object=k, team="home" if k < 6 else "away", goalie=m.w(POSITION + o(k)) == 0,
                              first_differs=first))
            print(lines[-1], flush=True)
    json.dump(lines, open(out / "boost.json", "w"))


def screens(rom, out, mc):
    for pen in (2, 0):
        e, m = boot(rom, 0, lambda e, m: fights_on(m, mc))
        r = Ram(e, m)
        m.setw(OPTPEN, pen)
        for _ in range(60 * 60 * 3):
            cvc.computer_only(m)
            e.run(1)
            if m.w(GSP) == 0 and m.w(CLOCK) < 270 and m.w(CLOCKSTOP) == 0:
                break
        for i in range(0x1A):                     # home 1-6 at places 0-5, visitors 6-1 at places 0-5, the rest 0
            r.buf[r.blk + i] = i + 1 if i < 6 else 0
            r.buf[r.blk + 0x1A + i] = 6 - i if i < 6 else 0
        r.setw(r.blk + 0x34, 21)
        r.setw(r.blk + 0x36, 21)
        sub = out / f"pen{pen}"
        sub.mkdir(parents=True, exist_ok=True)
        base = e.serialize()
        if pen == 2:
            press(e, "START", 90)
            for _ in range(40):
                if m.w(PSITEM) == 5:
                    break
                press(e, "DOWN")
            press(e, "B", 300)
            e.screenshot(sub / "player_00.png")
            for k in range(1, 12):
                press(e, "RIGHT", 120)
                e.screenshot(sub / f"player_{k:02d}.png")
            press(e, "Y", 200)
            for k in range(12, 24):
                e.screenshot(sub / f"player_{k:02d}_other.png")
                press(e, "LEFT", 120)
            e.unserialize(base)
        press(e, "START", 90)
        for _ in range(40):
            if m.w(PSITEM) == 2:
                break
            press(e, "DOWN")
        press(e, "A", 300)
        e.screenshot(sub / "game_top.png")
        e.run(400, hold=["DOWN"])
        e.run(60)
        e.screenshot(sub / "game_bottom.png")
        print("screens done, penalties", pen, flush=True)


if __name__ == "__main__":
    mode, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    mc = "nhl94snes_" in Path(rom).name                  # McMarkis's 2 MB and SA-1 builds: their Fighting option
    if mode == "games":
        first = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5].isdigit() else 0
        for n in range(first, first + int(sys.argv[4])):
            game(rom, out, n, mc, "--hot" in sys.argv)
    elif mode == "boost":
        boost(rom, out, mc)
    else:
        screens(rom, out, mc)
