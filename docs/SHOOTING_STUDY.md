# Shooting and goaltending: up and down the screen, home and away

A study of every shot and one-timer in the recorded games: **13 Genesis games (387 shots and one-timers) and 5 SNES
games (189)**, recorded 2026-10-14 to 2026-10-17. Most were played by one person, often as Boston, so the samples are
small and some splits are only a handful of shots. Treat differences of a few percentage points as noise. Rerun it as
more games come in: `python analysis/shot_table.py`, then `python analysis/shot_study.py` (from the project folder).

Terms: an **attempt** is any shot or one-timer (on goal, wide or blocked). **Uncounted stops** are shots that reached
the goalie and were stopped but not counted as shots on goal. **xG** is expected goals from the game's own rules
(GENESIS_MECHANICS.md 4.9, SNES_MECHANICS.md 4.7). **Up** means the shooting team was attacking up the screen.

## Up and down

| | Genesis up | Genesis down | SNES up | SNES down |
|---|---|---|---|---|
| Attempts | 185 | 202 | 95 | 94 |
| Goals (share of attempts) | 36 (19.5%) | 38 (18.8%) | 15 (15.8%) | 17 (18.1%) |
| Counted on goal | 122 | 139 | 58 | 66 |
| Uncounted stops | 15% | 9% | 16% | 14% |
| xG | 38.5 | 36.7 | 20.3 | 19.8 |
| Average shot speed | 51 mph | 53 mph | 54 mph | 61 mph |
| A person's aims high / middle / ice | 39 / 60 / 14 | 16 / 61 / 26 | 28 / 26 / 3 | 1 / 44 / 5 |
| A person's shots that went exactly where aimed | 48% | 49% | 43% | 58% |
| One-timers scored | 29% | 29% | 15% | 15% |

- **Goals don't depend on the direction** in these games, on either system, and goals match xG both ways.
- **Aim does**, strongly: people push the d-pad toward the net, so they aim high going up and low going down (on the
  SNES almost never high going down).
- **Counted shots on goal:** on the Genesis more were counted going down (139 against 122), the opposite of the
  community's 10% more going up; 13 games can't settle it either way. The mechanism found earlier (hard low shots off
  the goalie's stick aren't counted) is real, but in these games the uncounted stops were more common going up.

## Home and away

| | Genesis home | Genesis away | SNES home | SNES away |
|---|---|---|---|---|
| Attempts | 214 | 173 | 98 | 91 |
| Goals (share of attempts) | 44 (20.6%) | 30 (17.3%) | 16 (16.3%) | 16 (17.6%) |
| xG | 43.8 | 31.4 | 20.5 | 19.6 |

- **The difference comes from who was playing, not from home ice.** Taking only teams a person played, home and away
  shot the same: on the Genesis 38 goals from 189 attempts at home and 26 from 130 away, both 20%, with xG 21% a shot
  both ways; on the SNES 19% and 20%. The computer teams, few and mostly away, account for the gap above.
- The built-in reasons Home should win slightly more (the hidden home / away rating bonus, the home centre's faceoff
  edge, Home going up the screen in two regulation periods) are in GENESIS_MECHANICS.md 13.6. None is big enough to
  show in 13 games.

## Exact shots (a person's shots from within 200 units)

Within 200 units of the net a shot can go exactly where aimed (the chance set by Shot Accuracy); beyond 200 it never
does. Checked: beyond 200, 0 of 24 Genesis and 0 of 19 SNES shots went exactly where aimed; within 200, people's shots
went exact 60 times in 124 on the Genesis (the rule predicts 68) and 25 in 49 on the SNES (22).

| | Exact | Scattered |
|---|---|---|
| Genesis goals | 10 / 60 (17%) | 12 / 64 (19%) |
| SNES goals | 5 / 25 (20%) | 2 / 24 (8%) |

On the Genesis exactness didn't help: an exact shot at a goalie standing in the right spot is still saved, and the
scatter only pushes shots up, sometimes over his shoulder. Scattered shots went wide 13 times, exact ones once.

## Forehand and backhand (Genesis, shots)

| | Shots | Goals | xG a shot | Speed | Distance |
|---|---|---|---|---|---|
| Forehand | 210 | 29 (14%) | 16% | 52 mph | 108 |
| Backhand | 78 | 16 (21%) | 22% | 39 mph | 114 |

**Backhands score more, from slightly farther out**, and the game's own rules (xG) agree. Backhands lose a quarter of
their power, and the random scatter grows with shot speed, so a slower shot strays less.

## Speed and height (a person's shots, Genesis)

| Aimed | Under 50 mph | 50-65 | 65-80 | 80+ |
|---|---|---|---|---|
| High | 9 / 34 | 0 / 12 | 1 / 5 | 0 / 4 |
| Middle | 13 / 75 | 2 / 21 | 5 / 15 | 2 / 10 |
| Along the ice | 2 / 19 | 1 / 6 | 0 / 12 | 0 / 3 |

High shots score when they're soft (quick wrist shots, close in, little scatter); hard shots along the ice almost never
score. The SNES shows the same pattern with fewer shots.

## After a save (Genesis; SNES in brackets)

| | Saves | Held | Rebound | Cleared |
|---|---|---|---|---|
| From under 60 units | 64 (38) | 36 (23) | 14 (8) | 13 (7) |
| 60-120 | 123 (47) | 55 (28) | 28 (10) | 38 (8) |
| Farther | 32 (12) | 20 (8) | 5 (1) | 6 (3) |

**Rebound shots** (the same team's next shot after a save it got back): Genesis 8 goals in 17 (47%), against 18% for
all other shots; SNES 0 in 5.

## The goalie's move

Genesis, shots that reached him (goals / shots):

| Move | Computer in net | Person in net |
|---|---|---|
| Stick | 24 / 110 | 7 / 16 |
| None (stood his ground) | 4 / 40 | 10 / 25 |
| Pad stack | 10 / 32 | 1 / 5 |
| High (shoulder) | 3 / 30 | 0 / 3 |
| Glove | 10 / 18 | 1 / 4 |
| Dive | 1 / 6 | 3 / 7 |

- **A person in net faced harder shots**: xG 32% a shot on the Genesis against 23% for the computer (people take the
  goalie in dangerous moments), and let in 37%: a little worse than the odds. On the SNES a person in net faced xG 38%
  a shot and let in 31%: better than the odds.
- The computer's **glove** saves were beaten most (10 of 18 on the Genesis); **high** shoulder saves least.
- **"None"** with a person in net (10 of 25 in) is a goalie a person didn't move in time.
- SNES: a person's **pad stacks** were beaten 8 times in 15; the computer's **stick** saves 5 in 35.
- **Uncounted stops by move** (SNES): glove 4 of 27 saves, stick 4 of 31, no move 9 of 22. Many of the uncounted ones
  came with no save move at all, on both systems (Genesis computer goalies: 10 of 40).

## Strong side and off-wing (shots from more than 20 units off the middle)

| | Genesis | SNES |
|---|---|---|
| Strong side (left shot on the left side, right shot on the right) | 16 / 115 (14%) | 6 / 56 (11%) |
| Off-wing | 26 / 156 (17%) | 8 / 59 (14%) |

Off-wing shooters scored a little more on both systems; on the Genesis they also used their backhand more (58 against 35).

## Third period: first half and second half

The game's tied-or-trailing bonus (+2 Offensive Awareness and Checking) is on only while more than half the third
period is left (a bug; GENESIS_MECHANICS.md 2.3).

| Genesis | Attempts | Goals |
|---|---|---|
| Tied or trailing, first half | 29 | 9 (31%) |
| Tied or trailing, second half | 21 | 4 (19%) |
| Leading, first half | 24 | 6 (25%) |
| Leading, second half | 22 | 6 (27%) |

Tied or trailing teams did score more often while the bonus was on, as the bug would predict, but 50 shots can't
separate that from chance. The SNES sample is smaller still (tied or trailing, first half 2 in 16; second half 0 in 8).

## Hot or cold goalies (Genesis, as played: -3 to +2)

Goals against: cold 33 of 127 (26%), even 24 of 107 (22%), hot 17 of 63 (27%). No sign of an effect: a goalie's
hot / cold changes his Agility, which only changes his reach by about a unit.

## Score effects

| | Genesis attempts | Goals | SNES attempts | Goals |
|---|---|---|---|---|
| Trailing | 125 | 25 (20%) | 60 | 8 (13%) |
| Tied | 113 | 22 (19%) | 48 | 9 (19%) |
| Leading | 149 | 27 (18%) | 81 | 15 (19%) |

No clear effect: leading teams shot more (they're the better team on the day), at about the same rate.

---

# Part 2: the rest of the game, and the reasons tested

`python analysis/direction_study.py` (after `analysis/shot_table.py`). Same games as part 1.

## Count per period, not in total

Home attacks up in periods 1 and 3 and Away only in period 2, and in most of these games a person played Home. So totals
"going up" hold more of the person's team, and raw up / down counts mix the direction with who was playing. The fair
comparison is each team's rate per period going up against its own rate going down:

| Per period | Shots on goal | Goals | Checks | Passes made | Giveaways | Zone entries |
|---|---|---|---|---|---|---|
| Genesis, both teams up (34 team-periods) | 3.8 | 1.2 | 6.9 | 10.9 | 4.0 | 8.2 |
| Genesis, both teams down (34) | 4.3 | 1.3 | 6.4 | 11.3 | 4.1 | 8.3 |
| Genesis home up / down | 3.9 / 5.5 | 1.3 / 1.9 | 7.7 / 7.8 | 11.9 / 12.2 | 4.2 / 4.4 | 8.4 / 9.7 |
| Genesis away up / down | 3.5 / 3.8 | 1.1 / 1.0 | 5.2 / 5.7 | 8.7 / 10.9 | 3.5 / 4.0 | 7.9 / 7.6 |
| SNES, both teams up (15) | 3.9 | 1.0 | 9.8 | 13.5 | 3.3 | 9.0 |
| SNES, both teams down (15) | 4.5 | 1.2 | 8.7 | 14.0 | 3.1 | 8.9 |

**No direction stands out.** Going down was a little ahead on shots on goal on both systems, going up a little ahead on
checks, but these games are far too few to separate a 10% difference from chance: shots on goal come about 4 a period,
so telling 10% apart takes a couple of hundred team-periods each way, about 100 whole games. A large box-score database
can see it; these recordings can't yet. (Home teams going down are period 2, which may say more about period 2 than
about the direction.)

## Passing, turnovers, entries (totals)

| | Passes | Completed | Intercepted | Bobbled | Zone entries carried / all |
|---|---|---|---|---|---|
| Genesis up | 557 | 328 (59%) | 135 (24%) | 28 | 200 / 280 |
| Genesis down | 551 | 340 (62%) | 125 (23%) | 34 | 207 / 281 |
| SNES up | 273 | 177 (65%) | 55 (20%) | 14 | 103 / 135 |
| SNES down | 269 | 180 (67%) | 49 (18%) | 10 | 99 / 133 |

The camera shows 2-3 feet more ice ahead going up (GENESIS_MECHANICS.md 13.6), but passing went no better going up;
if anything slightly worse.

## The reasons tested

- **The home / away rating bonus is real and shows in play.** On the Genesis, a skater's working Shot Accuracy sat a
  mean 0.87 above his rating (5 per rating point) at home and 0.78 below it away (533 and 461 rating loads), as the
  ROM's per-team bonus says. Small: under a fifth of a rating point each way.
- **Faceoffs:** the home centre's 17-in-33 edge didn't show: Genesis away teams won 88 draws to 77, SNES 39 to 35. The
  faceoff count goes to whoever first gets the puck after the drop, and a person mashing the button decides far more
  than the built-in edge.
- **Home record in these games:** Genesis 6 home wins in 8 whole games, SNES 3 in 5, but most of these are the same
  person playing Home against the computer or a friend, so they say nothing about home ice.
- **Shot scatter** (Genesis): only one of its three parts is halved shooting down. A scattered shot's target point is
  moved at random sideways (up to 136 units), in depth along the ice (up to 60) and up (never down); the depth part is
  halved when the shot goes down the screen. The puck's velocity comes from that moved target, so depth scatter
  changes the shot's angle and speed: little for a shot from in front of the net, more from the side, where a target
  pushed deeper or nearer swings where the puck crosses the goal line. Worth, by the xG model played both ways on the
  recorded shots: +1.4% expected goals for shots going down (36.7 against 36.1 if never halved; 174 shots), +3.7% for
  shots from the side (more than 40 off the middle); nothing going up. About one goal in 300 shots going down: far too
  small to see in a dozen games (people's scattered shots went wide 32% going up, 36% going down, 41 and 42 shots).
- **The goalies' sticks**: stick saves were 41% of the shots that reached the top net's goalie and 44% at the bottom
  net (Genesis); SNES 23% and 30%. No clear difference.

---

# Part 3: one-timers

`python analysis/one_timer_study.py`. Each one-timer with the pass that set it up (the team's last pass in the 2.5 s
before), the goalie's position when the pass left and at the strike, and the result. 91 Genesis and 55 SNES one-timers.

| Genesis | One-timers | Scored | xG a shot |
|---|---|---|---|
| Pass stayed on one side | 63 | 22 (35%) | 35% |
| Pass crossed the middle | 28 | 5 (18%) | 19% |
| Pass moved the puck 0-40 units across | 32 | 6 (19%) | 24% |
| 40-90 across | 34 | 16 (47%) | 45% |
| 90+ across | 25 | 5 (20%) | 16% |
| Pass in the air under 0.5 s | 66 | 22 (33%) | 37% |
| 0.5-0.9 s | 20 | 5 (25%) | 12% |
| Goalie slid under 15 across during the pass | 63 | 22 (35%) | 35% |
| Goalie slid 15-40 | 25 | 5 (20%) | 21% |
| Goalie 0-4 off the puck's line at the strike | 28 | 3 (11%) | 11% |
| 4-10 off | 38 | 7 (18%) | 24% |
| 10+ off | 25 | 17 (68%) | 60% |
| Struck within 60 of the net | 18 | 8 (44%) | 52% |
| 60-100 | 34 | 15 (44%) | 41% |
| Beyond 100 | 39 | 4 (10%) | 10% |
| A person in net | 12 | 7 (58%) | 48% |
| The computer in net | 79 | 20 (25%) | 27% |

- **What decides a one-timer is whether the goalie is caught off his line** (the line from the puck to his net) when
  it's struck: 68% scored with him 10 or more off it, 11% with him on it.
- **Long cross-ice passes did worse, not better**, unlike real hockey: the computer goalie re-aims every few frames
  (Defensive Awareness sets how often), so a pass that takes long to get across gives him time to slide over and set.
  The best one-timers came off quick passes (under half a second) that moved the puck a moderate 40-90 units across.
- **Distance:** inside 100 units almost half went in; beyond, 1 in 10.
- A person in net let in 7 of 12 (the xG model says 48%): too few to say more than that people controlling the goalie
  have trouble sliding across in time.
- The xG model (which plays each one-timer out against the goalie as he was) agrees with all of these, so they're the
  game's rules at work, not luck.

**SNES** (55 one-timers, 8 goals, 15%): no clear pattern by pass. Within 60-100 units 8 of 25 scored, none of 30 from
elsewhere; goalie 10+ off his line 3 of 16 (xG 42%). The SNES goalie gets sluggish while a pass is in the air
(SNES_MECHANICS.md 5), which may blunt the pass effects seen on the Genesis; more games needed.
