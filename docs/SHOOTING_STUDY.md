# Shooting and goaltending: up and down the screen, home and away

A study of every shot and one-timer in the recorded games. The first section (home / away and up / down, reworked
2026-10-21) uses all 19 Genesis and 8 SNES games recorded through 2026-10-19; the rest uses **13 Genesis games (387
shots and one-timers) and 5 SNES games (189)**, recorded 2026-10-14 to 2026-10-17. Most were played by one person, often as Boston, so the samples are
small and some splits are only a handful of shots. Treat differences of a few percentage points as noise. Rerun it as
more games come in: `python analysis/shot_table.py`, then `python analysis/shot_study.py` (from the project folder).

Terms: an **attempt** is any shot or one-timer (on goal, wide or blocked). **Uncounted stops** are shots that reached
the goalie and were stopped but not counted as shots on goal. **xG** is expected goals from the game's own rules
(GENESIS_MECHANICS.md 4.9, SNES_MECHANICS.md 4.7). **Up** means the shooting team was attacking up the screen.

## Home / away and up / down, together (reworked 2026-10-21)

The user asked for the two split together: Home going up, Home going down, Away going up, Away going down. This
section uses **every game recorded through 2026-10-19: 19 Genesis games (570 shots and one-timers) and 8 SNES games
(340)**; the sections after it still use the 13 Genesis and 5 SNES games of the first study.

**Why game time matters here.** Home attacks up the screen in periods 1 and 3 and down in period 2 and overtime
(checked in every recorded game), so Home spends about twice as long going up as down, and Away the reverse. Raw totals
would mostly measure that. So each cell also gives its **game minutes** and its attempts, shots on goal and goals **per
5:00**; percentages (goals per attempt, per shot on goal) don't depend on time. A team counts as **a person's** when it
had the controlled-skater marker in most samples: the computer teams are few and weak, and mostly Away, which skews
"all teams". Terms as above: *uncounted stops* are shots that reached the goalie and were stopped without being counted
as shots on goal; *exact* means the shot left the stick exactly at its aim point (possible only within 200 units).

**GENESIS, all teams** (19 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 173 min | 110 min | 110 min | 173 min | 283 min | 283 min | 283 min | 283 min |
| Attempts | 184 (5.3 per 5:00) | 116 (5.3 per 5:00) | 92 (4.2 per 5:00) | 178 (5.1 per 5:00) | 300 (5.3 per 5:00) | 270 (4.8 per 5:00) | 276 (4.9 per 5:00) | 294 (5.2 per 5:00) |
| Shots on goal | 121 (3.5 per 5:00) | 78 (3.5 per 5:00) | 64 (2.9 per 5:00) | 129 (3.7 per 5:00) | 199 (3.5 per 5:00) | 193 (3.4 per 5:00) | 185 (3.3 per 5:00) | 207 (3.7 per 5:00) |
| Goals | 35 (1.0 per 5:00) | 27 (1.2 per 5:00) | 18 (0.8 per 5:00) | 36 (1.0 per 5:00) | 62 (1.1 per 5:00) | 54 (1.0 per 5:00) | 53 (0.9 per 5:00) | 63 (1.1 per 5:00) |
| Goals per attempt | 19.0% | 23.3% | 19.6% | 20.2% | 20.7% | 20.0% | 19.2% | 21.4% |
| Goals per shot on goal | 28.9% | 34.6% | 28.1% | 27.9% | 31.2% | 28.0% | 28.6% | 30.4% |
| xG per unblocked attempt | 0.23 | 0.22 | 0.21 | 0.22 | 0.23 | 0.22 | 0.22 | 0.22 |
| Goals minus xG | -4.3 | +1.7 | -0.2 | +2.7 | -2.5 | +2.5 | -4.5 | +4.5 |
| Uncounted stops | 17% | 7% | 10% | 8% | 13% | 9% | 15% | 8% |
| A person's aims high / middle / ice | 39 / 51 / 10% | 8 / 66 / 26% | 35 / 51 / 14% | 20 / 58 / 22% | 26 / 57 / 17% | 26 / 55 / 19% | 38 / 51 / 11% | 13 / 62 / 24% |
| A person's shots exact (within 200) | 51% of 70 | 42% of 52 | 56% of 25 | 61% of 33 | 48% of 122 | 59% of 58 | 53% of 95 | 49% of 85 |

**GENESIS, teams a person played** (19 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 155 min | 95 min | 80 min | 128 min | 250 min | 208 min | 235 min | 223 min |
| Attempts | 170 (5.5 per 5:00) | 105 (5.5 per 5:00) | 67 (4.2 per 5:00) | 130 (5.1 per 5:00) | 275 (5.5 per 5:00) | 197 (4.7 per 5:00) | 237 (5.0 per 5:00) | 235 (5.3 per 5:00) |
| Shots on goal | 112 (3.6 per 5:00) | 70 (3.7 per 5:00) | 45 (2.8 per 5:00) | 94 (3.7 per 5:00) | 182 (3.6 per 5:00) | 139 (3.3 per 5:00) | 157 (3.3 per 5:00) | 164 (3.7 per 5:00) |
| Goals | 33 (1.1 per 5:00) | 23 (1.2 per 5:00) | 14 (0.9 per 5:00) | 33 (1.3 per 5:00) | 56 (1.1 per 5:00) | 47 (1.1 per 5:00) | 47 (1.0 per 5:00) | 56 (1.3 per 5:00) |
| Goals per attempt | 19.4% | 21.9% | 20.9% | 25.4% | 20.4% | 23.9% | 19.8% | 23.8% |
| Goals per shot on goal | 29.5% | 32.9% | 31.1% | 35.1% | 30.8% | 33.8% | 29.9% | 34.1% |
| xG per unblocked attempt | 0.24 | 0.20 | 0.23 | 0.23 | 0.22 | 0.23 | 0.23 | 0.22 |
| Goals minus xG | -4.3 | +1.9 | -0.3 | +7.3 | -2.4 | +6.9 | -4.6 | +9.1 |
| Uncounted stops | 17% | 8% | 12% | 10% | 14% | 10% | 16% | 9% |
| A person's aims high / middle / ice | 39 / 51 / 10% | 8 / 66 / 26% | 35 / 51 / 14% | 20 / 58 / 22% | 26 / 57 / 17% | 26 / 55 / 19% | 38 / 51 / 11% | 13 / 62 / 24% |
| A person's shots exact (within 200) | 51% of 70 | 42% of 52 | 56% of 25 | 61% of 33 | 48% of 122 | 59% of 58 | 53% of 95 | 49% of 85 |

**SNES, all teams** (8 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 80 min | 40 min | 40 min | 80 min | 120 min | 120 min | 120 min | 120 min |
| Attempts | 115 (7.2 per 5:00) | 57 (7.1 per 5:00) | 56 (7.0 per 5:00) | 112 (7.0 per 5:00) | 172 (7.2 per 5:00) | 168 (7.0 per 5:00) | 171 (7.1 per 5:00) | 169 (7.0 per 5:00) |
| Shots on goal | 75 (4.7 per 5:00) | 39 (4.9 per 5:00) | 35 (4.4 per 5:00) | 73 (4.6 per 5:00) | 114 (4.8 per 5:00) | 108 (4.5 per 5:00) | 110 (4.6 per 5:00) | 112 (4.7 per 5:00) |
| Goals | 26 (1.6 per 5:00) | 15 (1.9 per 5:00) | 6 (0.8 per 5:00) | 21 (1.3 per 5:00) | 41 (1.7 per 5:00) | 27 (1.1 per 5:00) | 32 (1.3 per 5:00) | 36 (1.5 per 5:00) |
| Goals per attempt | 22.6% | 26.3% | 10.7% | 18.8% | 23.8% | 16.1% | 18.7% | 21.3% |
| Goals per shot on goal | 34.7% | 38.5% | 17.1% | 28.8% | 36.0% | 25.0% | 29.1% | 32.1% |
| xG per unblocked attempt | 0.27 | 0.20 | 0.15 | 0.22 | 0.25 | 0.20 | 0.23 | 0.21 |
| Goals minus xG | -3.1 | +4.3 | -1.5 | -1.0 | +1.2 | -2.5 | -4.6 | +3.4 |
| Uncounted stops | 18% | 11% | 17% | 17% | 16% | 17% | 17% | 15% |
| A person's aims high / middle / ice | 69 / 27 / 3% | 8 / 88 / 4% | 44 / 48 / 8% | 2 / 84 / 14% | 51 / 45 / 4% | 17 / 71 / 12% | 62 / 33 / 5% | 4 / 86 / 10% |
| A person's shots exact (within 200) | 41% of 29 | 47% of 15 | 58% of 12 | 56% of 25 | 43% of 44 | 57% of 37 | 46% of 41 | 52% of 40 |

**SNES, teams a person played** (8 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 60 min | 30 min | 25 min | 50 min | 90 min | 75 min | 85 min | 80 min |
| Attempts | 90 (7.5 per 5:00) | 42 (7.0 per 5:00) | 33 (6.6 per 5:00) | 71 (7.1 per 5:00) | 132 (7.3 per 5:00) | 104 (6.9 per 5:00) | 123 (7.2 per 5:00) | 113 (7.1 per 5:00) |
| Shots on goal | 63 (5.2 per 5:00) | 29 (4.8 per 5:00) | 21 (4.2 per 5:00) | 53 (5.3 per 5:00) | 92 (5.1 per 5:00) | 74 (4.9 per 5:00) | 84 (4.9 per 5:00) | 82 (5.1 per 5:00) |
| Goals | 23 (1.9 per 5:00) | 14 (2.3 per 5:00) | 6 (1.2 per 5:00) | 16 (1.6 per 5:00) | 37 (2.1 per 5:00) | 22 (1.5 per 5:00) | 29 (1.7 per 5:00) | 30 (1.9 per 5:00) |
| Goals per attempt | 25.6% | 33.3% | 18.2% | 22.5% | 28.0% | 21.2% | 23.6% | 26.5% |
| Goals per shot on goal | 36.5% | 48.3% | 28.6% | 30.2% | 40.2% | 29.7% | 34.5% | 36.6% |
| xG per unblocked attempt | 0.31 | 0.25 | 0.22 | 0.25 | 0.29 | 0.24 | 0.28 | 0.25 |
| Goals minus xG | -3.5 | +3.9 | -1.1 | -0.2 | +0.4 | -1.4 | -4.7 | +3.7 |
| Uncounted stops | 16% | 15% | 16% | 12% | 16% | 13% | 16% | 13% |
| A person's aims high / middle / ice | 69 / 27 / 3% | 8 / 88 / 4% | 44 / 48 / 8% | 2 / 84 / 14% | 51 / 45 / 4% | 17 / 71 / 12% | 62 / 33 / 5% | 4 / 86 / 10% |
| A person's shots exact (within 200) | 41% of 29 | 47% of 15 | 58% of 12 | 56% of 25 | 43% of 44 | 57% of 37 | 46% of 41 | 52% of 40 |

**Is any difference real?** The ratio of the two rates per game minute, with the range a difference this size could
come from chance alone (95%). A ratio above 1 favours the first of the pair; a range that includes 1.00 means these
games can't tell the two apart.

| Teams | Comparison | Attempts | Shots on goal | Goals |
|---|---|---|---|---|
| Genesis, all teams | Home / Away | 1.11 (0.94-1.31) | 1.03 (0.85-1.26) | 1.15 (0.80-1.65) |
| Genesis, all teams | Up / Down | 0.94 (0.80-1.11) | 0.89 (0.73-1.09) | 0.84 (0.58-1.21) |
| Genesis, all teams | Home: Up / Down | 1.01 (0.80-1.27) | 0.99 (0.74-1.31) | 0.82 (0.50-1.36) |
| Genesis, all teams | Away: Up / Down | 0.81 (0.63-1.05) | 0.78 (0.58-1.05) | 0.79 (0.45-1.39) |
| Genesis, teams a person played | Home / Away | 1.16 (0.97-1.39) | 1.09 (0.87-1.36) | 0.99 (0.67-1.46) |
| Genesis, teams a person played | Up / Down | 0.96 (0.80-1.15) | 0.91 (0.73-1.13) | 0.80 (0.54-1.17) |
| Genesis, teams a person played | Home: Up / Down | 0.99 (0.78-1.27) | 0.98 (0.73-1.32) | 0.88 (0.52-1.50) |
| Genesis, teams a person played | Away: Up / Down | 0.82 (0.61-1.11) | 0.77 (0.54-1.09) | 0.68 (0.36-1.27) |
| SNES, all teams | Home / Away | 1.02 (0.83-1.27) | 1.06 (0.81-1.37) | 1.52 (0.93-2.47) |
| SNES, all teams | Up / Down | 1.01 (0.82-1.25) | 0.98 (0.75-1.28) | 0.89 (0.55-1.43) |
| SNES, all teams | Home: Up / Down | 1.01 (0.73-1.39) | 0.96 (0.65-1.42) | 0.87 (0.46-1.64) |
| SNES, all teams | Away: Up / Down | 1.00 (0.73-1.38) | 0.96 (0.64-1.43) | 0.57 (0.23-1.42) |
| SNES, teams a person played | Home / Away | 1.06 (0.82-1.37) | 1.04 (0.76-1.41) | 1.40 (0.83-2.38) |
| SNES, teams a person played | Up / Down | 1.02 (0.79-1.32) | 0.96 (0.71-1.31) | 0.91 (0.55-1.52) |
| SNES, teams a person played | Home: Up / Down | 1.07 (0.74-1.55) | 1.09 (0.70-1.69) | 0.82 (0.42-1.60) |
| SNES, teams a person played | Away: Up / Down | 0.93 (0.62-1.40) | 0.79 (0.48-1.31) | 0.75 (0.29-1.92) |

What the games show so far:

- **No clear effect of either Home / Away or Up / Down** on attempts, shots on goal or goals, on either system: every
  range above includes 1.00. Differences of 10-20% are well inside what chance gives with 20-35 goals a cell.
- **The direction changes how people aim, not how often they score.** Going up, people push the d-pad toward the net,
  which aims high (Genesis 38% of a person's shots aimed high going up against 13% going down; SNES 62% against 4%).
  Going down they aim along the ice or the middle. Goals per attempt end up about the same either way.
- **More uncounted stops going up on the Genesis** (15% of shots that reached the goalie, against 8% going down), the
  opposite of what the league's box scores suggest (about 10% more shots on goal going up). These games give 0.89
  times the shots on goal per minute going up, but the range (0.73-1.09) includes the league's 1.10 too: about 100
  whole games would be needed to see a 10% difference.
- **Away going up was the weakest cell on both systems** (Genesis 2.9 shots on goal per 5:00 against 3.5-3.7 in the
  other three cells; SNES 0.8 goals per 5:00). That cell is almost all period 2, the one period Away goes up, so it
  mixes direction with whatever is special about the middle period (no third-period bonus, no score pressure). It's
  the thing to watch as more games come in.
- **Home on the SNES scored 1.52 times as often per minute** (range 0.93-2.47), the biggest gap here, but 41 goals
  against 27 in 8 games is still within chance; its attempts and shots on goal were equal (1.02, 1.06).
- **Played in the game itself, single shots do differ by net** ([SCORING_MAP](SCORING_MAP.md)): the Down slapshot
  from the middle scores about 21% at the top net against 14% at the bottom, the shoulder-save bobble happens only at
  the top net, and a deke swung to the shooter's right does much better going down. Other shots favour neither net or
  the other one, so over the mix of shots in a game they can cancel out, as here.
- The built-in reasons Home should win slightly more (the hidden home / away rating bonus, the home centre's faceoff
  edge, Home going up in two regulation periods) are in GENESIS_MECHANICS.md 13.6.

Rerun: `python analysis/shot_table.py`, then `python analysis/home_direction_study.py`.

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
