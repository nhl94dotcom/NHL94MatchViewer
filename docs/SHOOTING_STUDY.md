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
