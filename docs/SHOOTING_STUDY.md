# Shooting and goaltending: up and down the screen, home and away

A study of every shot and one-timer in the recorded games, and (first section) of the leagues' own results. The first section (home / away and up / down, rerun
2026-10-30) uses every recorded game: 29 Genesis and 22 SNES; the rest uses **13 Genesis games (387
shots and one-timers) and 5 SNES games (189)**, recorded 2026-10-14 to 2026-10-17. Most were played by one person, often as Boston, so the samples are
small and some splits are only a handful of shots. Treat differences of a few percentage points as noise. Rerun it as
more games come in: `python analysis/shot_table.py`, then `python analysis/shot_study.py` (from the project folder).

Terms: an **attempt** is any shot or one-timer (on goal, wide or blocked). **Uncounted stops** are shots that reached
the goalie and were stopped but not counted as shots on goal. **xG** is expected goals from the game's own rules
(GENESIS_SHOOTING.md 4.9, SNES_SHOOTING.md 4.7). **Up** means the shooting team was attacking up the screen.

## The leagues' own results (2026-10-30)

The user's league result databases (kept outside this repository; `analysis/league_home_study.py` reads them and
prints aggregates only): **86,735 Genesis and 36,180 SNES games** from 2013 to 2026, simulated games left out. Each
row has both sides' goals, shots on goal (the game's own count) and faceoff wins, by period. Ranges are 95%.

| | Genesis | SNES |
| --- | --- | --- |
| Home wins (of decided games) | **50.5%** (+/- 0.3) | **52.3%** (+/- 0.5) |
| Goals a game, home / away | 3.81 / 3.77 | 4.53 / 4.32 |
| Shots on goal a game, home / away | 12.17 / 11.55 (1.05) | 12.37 / 11.20 (1.11) |
| Faceoff wins, home / away | 0.98 | 1.07 |
| Home's share of shots on goal, periods 1 / 2 / 3 | 52.3% / **49.3%** / 52.4% | 52.8% / 52.1% / 52.6% |
| Home's share of goals, periods 1 / 2 / 3 | 49.6% / 51.2% / 49.9% | 51.6% / 50.4% / 51.6% |
| The same player at home minus away (players with 20+ games each way) | shots +0.67 a game, win rate +1.0% (+/- 0.8) | shots +1.20 a game, win rate **+4.5%** (+/- 1.3) |
| A team's home win rate minus its own away win rate: retail home bonus +2 / none / other teams | **+2.3 / +0.4** / +0.7 points | +4.9 / +3.9 / +5.0 points |

- **Genesis: the shot edge is the screen direction, not home.** Home's share of shots on goal is 52.3% in periods 1
  and 3, when it attacks up the screen, and 49.3% in period 2, when it attacks down: the team going up gets about 10%
  more shots counted, whoever it is (GENESIS_SHOOTING 4.7: low shots going down are knocked away by the goalie's
  stick uncounted). Goals lean the other way (the team going down scores a little more). The home edge in results
  is small (50.5%), and the same player wins only about 1 point more often at home.
- **Genesis: the home bonus works as coded.** Teams the retail ROM gives +2 at home win 2.3 points more often at
  home than away; teams with no bonus 0.4. (League ROMs can edit the bonus, so this is the retail table's teams.)
- **The 29 recorded Genesis games' home edge in attempts** (below: 1.22 times as many per minute) isn't in the
  leagues' results: there Home's shots in period 2, going down, are below half. It was the recorded games' players and
  sample, not the game.
- **SNES: a real home edge, and not from the bonus or the direction.** Home wins 52.3%, the same player wins 4.5
  points more often at home, and 147 of 156 players shoot more at home; Home's shot share is the same in every period,
  and teams gain 4-5 points at home whatever their bonus. Part of it may be faceoffs (the home centre wins ties: 17 of
  32 at equal timing, SNES_MECHANICS 9; Home won 7% more of them here). The rest is open.

## Home / away and up / down, together (rerun 2026-10-30)

The user asked for the two split together: Home going up, Home going down, Away going up, Away going down. This
section uses **every game recorded through 2026-10-30: 29 Genesis games (972 shots and one-timers) and 22 SNES games
(805)**; the sections after it still use the 13 Genesis and 5 SNES games of the first study.

**Why game time matters here.** Home attacks up the screen in periods 1 and 3 and down in period 2 and overtime
(checked in every recorded game), so Home spends about twice as long going up as down, and Away the reverse. Raw totals
would mostly measure that. So each cell also gives its **game minutes** and its attempts, shots on goal and goals **per
5:00**; percentages (goals per attempt, per shot on goal) don't depend on time. A team counts as **a person's** when it
had the controlled-skater marker in most samples: the computer teams are few and weak, and mostly Away, which skews
"all teams". Terms as above: *uncounted stops* are shots that reached the goalie and were stopped without being counted
as shots on goal; *exact* means the shot left the stick exactly at its aim point (possible only within 200 units).

**GENESIS, all teams** (29 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 278 min | 160 min | 160 min | 278 min | 438 min | 438 min | 438 min | 438 min |
| Attempts | 347 (6.2 per 5:00) | 187 (5.8 per 5:00) | 143 (4.5 per 5:00) | 295 (5.3 per 5:00) | 534 (6.1 per 5:00) | 438 (5.0 per 5:00) | 490 (5.6 per 5:00) | 482 (5.5 per 5:00) |
| Shots on goal | 242 (4.4 per 5:00) | 131 (4.1 per 5:00) | 97 (3.0 per 5:00) | 207 (3.7 per 5:00) | 373 (4.3 per 5:00) | 304 (3.5 per 5:00) | 339 (3.9 per 5:00) | 338 (3.9 per 5:00) |
| Goals | 72 (1.3 per 5:00) | 43 (1.3 per 5:00) | 30 (0.9 per 5:00) | 57 (1.0 per 5:00) | 115 (1.3 per 5:00) | 87 (1.0 per 5:00) | 102 (1.2 per 5:00) | 100 (1.1 per 5:00) |
| Goals per attempt | 20.7% | 23.0% | 21.0% | 19.3% | 21.5% | 19.9% | 20.8% | 20.7% |
| Goals per shot on goal | 29.8% | 32.8% | 30.9% | 27.5% | 30.8% | 28.6% | 30.1% | 29.6% |
| xG per unblocked attempt | 0.23 | 0.23 | 0.23 | 0.22 | 0.23 | 0.22 | 0.23 | 0.22 |
| Goals minus xG | -2.4 | +1.8 | -1.1 | +1.3 | -0.6 | +0.2 | -3.5 | +3.1 |
| Uncounted stops | 13% | 6% | 9% | 8% | 11% | 8% | 12% | 7% |
| A person's aims high / middle / ice | 26 / 64 / 10% | 8 / 70 / 21% | 37 / 54 / 9% | 13 / 68 / 19% | 19 / 66 / 14% | 21 / 63 / 15% | 29 / 61 / 10% | 11 / 69 / 20% |
| A person's shots exact (within 200) | 54% of 138 | 44% of 84 | 54% of 50 | 55% of 86 | 50% of 222 | 54% of 136 | 54% of 188 | 49% of 170 |

**GENESIS, teams a person played** (29 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 250 min | 140 min | 125 min | 228 min | 390 min | 353 min | 375 min | 368 min |
| Attempts | 310 (6.2 per 5:00) | 170 (6.1 per 5:00) | 115 (4.6 per 5:00) | 239 (5.2 per 5:00) | 480 (6.2 per 5:00) | 354 (5.0 per 5:00) | 425 (5.7 per 5:00) | 409 (5.6 per 5:00) |
| Shots on goal | 214 (4.3 per 5:00) | 117 (4.2 per 5:00) | 76 (3.0 per 5:00) | 166 (3.6 per 5:00) | 331 (4.2 per 5:00) | 242 (3.4 per 5:00) | 290 (3.9 per 5:00) | 283 (3.8 per 5:00) |
| Goals | 69 (1.4 per 5:00) | 39 (1.4 per 5:00) | 26 (1.0 per 5:00) | 53 (1.2 per 5:00) | 108 (1.4 per 5:00) | 79 (1.1 per 5:00) | 95 (1.3 per 5:00) | 92 (1.2 per 5:00) |
| Goals per attempt | 22.3% | 22.9% | 22.6% | 22.2% | 22.5% | 22.3% | 22.4% | 22.5% |
| Goals per shot on goal | 32.2% | 33.3% | 34.2% | 31.9% | 32.6% | 32.6% | 32.8% | 32.5% |
| xG per unblocked attempt | 0.24 | 0.23 | 0.25 | 0.23 | 0.24 | 0.24 | 0.25 | 0.23 |
| Goals minus xG | -1.3 | +2.4 | -0.9 | +4.9 | +1.1 | +3.9 | -2.3 | +7.3 |
| Uncounted stops | 13% | 6% | 11% | 10% | 11% | 10% | 13% | 8% |
| A person's aims high / middle / ice | 26 / 64 / 10% | 8 / 70 / 21% | 37 / 54 / 9% | 13 / 68 / 19% | 19 / 66 / 14% | 21 / 63 / 15% | 29 / 61 / 10% | 11 / 69 / 20% |
| A person's shots exact (within 200) | 54% of 138 | 44% of 84 | 54% of 50 | 55% of 86 | 50% of 222 | 54% of 136 | 54% of 188 | 49% of 170 |

**SNES, all teams** (22 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 219 min | 114 min | 114 min | 219 min | 334 min | 334 min | 334 min | 334 min |
| Attempts | 267 (6.1 per 5:00) | 139 (6.1 per 5:00) | 138 (6.0 per 5:00) | 261 (5.9 per 5:00) | 406 (6.1 per 5:00) | 399 (6.0 per 5:00) | 405 (6.1 per 5:00) | 400 (6.0 per 5:00) |
| Shots on goal | 176 (4.0 per 5:00) | 91 (4.0 per 5:00) | 93 (4.1 per 5:00) | 166 (3.8 per 5:00) | 267 (4.0 per 5:00) | 259 (3.9 per 5:00) | 269 (4.0 per 5:00) | 257 (3.9 per 5:00) |
| Goals | 65 (1.5 per 5:00) | 30 (1.3 per 5:00) | 19 (0.8 per 5:00) | 60 (1.4 per 5:00) | 95 (1.4 per 5:00) | 79 (1.2 per 5:00) | 84 (1.3 per 5:00) | 90 (1.3 per 5:00) |
| Goals per attempt | 24.3% | 21.6% | 13.8% | 23.0% | 23.4% | 19.8% | 20.7% | 22.5% |
| Goals per shot on goal | 36.9% | 33.0% | 20.4% | 36.1% | 35.6% | 30.5% | 31.2% | 35.0% |
| xG per unblocked attempt | 0.29 | 0.24 | 0.17 | 0.26 | 0.27 | 0.23 | 0.25 | 0.25 |
| Goals minus xG | -6.3 | -0.3 | -2.9 | -2.3 | -6.6 | -5.2 | -9.2 | -2.7 |
| Uncounted stops | 16% | 12% | 14% | 18% | 15% | 17% | 15% | 16% |
| A person's aims high / middle / ice | 57 / 38 / 5% | 12 / 77 / 11% | 47 / 49 / 5% | 9 / 76 / 15% | 44 / 50 / 7% | 24 / 65 / 11% | 54 / 41 / 5% | 11 / 76 / 13% |
| A person's shots exact (within 200) | 47% of 64 | 56% of 32 | 41% of 37 | 50% of 54 | 50% of 96 | 46% of 91 | 45% of 101 | 52% of 86 |

**SNES, teams a person played** (22 games)

| | Home, up | Home, down | Away, up | Away, down | All home | All away | All up | All down |
|---|---|---|---|---|---|---|---|---|
| Game time | 199 min | 104 min | 99 min | 189 min | 304 min | 289 min | 299 min | 294 min |
| Attempts | 242 (6.1 per 5:00) | 124 (6.0 per 5:00) | 114 (5.7 per 5:00) | 219 (5.8 per 5:00) | 366 (6.0 per 5:00) | 333 (5.8 per 5:00) | 356 (6.0 per 5:00) | 343 (5.8 per 5:00) |
| Shots on goal | 164 (4.1 per 5:00) | 81 (3.9 per 5:00) | 76 (3.8 per 5:00) | 139 (3.7 per 5:00) | 245 (4.0 per 5:00) | 215 (3.7 per 5:00) | 240 (4.0 per 5:00) | 220 (3.7 per 5:00) |
| Goals | 62 (1.6 per 5:00) | 29 (1.4 per 5:00) | 19 (1.0 per 5:00) | 52 (1.4 per 5:00) | 91 (1.5 per 5:00) | 71 (1.2 per 5:00) | 81 (1.4 per 5:00) | 81 (1.4 per 5:00) |
| Goals per attempt | 25.6% | 23.4% | 16.7% | 23.7% | 24.9% | 21.3% | 22.8% | 23.6% |
| Goals per shot on goal | 37.8% | 35.8% | 25.0% | 37.4% | 37.1% | 33.0% | 33.8% | 36.8% |
| xG per unblocked attempt | 0.31 | 0.26 | 0.20 | 0.27 | 0.29 | 0.25 | 0.27 | 0.27 |
| Goals minus xG | -6.7 | -0.7 | -2.2 | -3.5 | -7.5 | -5.7 | -8.9 | -4.3 |
| Uncounted stops | 15% | 14% | 15% | 18% | 15% | 17% | 15% | 16% |
| A person's aims high / middle / ice | 57 / 38 / 5% | 12 / 77 / 11% | 47 / 49 / 5% | 9 / 76 / 15% | 44 / 50 / 7% | 24 / 65 / 11% | 54 / 41 / 5% | 11 / 76 / 13% |
| A person's shots exact (within 200) | 47% of 64 | 56% of 32 | 41% of 37 | 50% of 54 | 50% of 96 | 46% of 91 | 45% of 101 | 52% of 86 |

**Is any difference real?** The ratio of the two rates per game minute, with the range a difference this size could
come from chance alone (95%). A ratio above 1 favours the first of the pair; a range that includes 1.00 means these
games can't tell the two apart.

| Teams | Comparison | Attempts | Shots on goal | Goals |
|---|---|---|---|---|
| Genesis, all teams | Home / Away | 1.22 (1.07-1.38) | 1.23 (1.05-1.43) | 1.32 (1.00-1.75) |
| Genesis, all teams | Up / Down | 1.02 (0.90-1.15) | 1.00 (0.86-1.17) | 1.02 (0.77-1.34) |
| Genesis, all teams | Home: Up / Down | 1.07 (0.89-1.28) | 1.06 (0.86-1.31) | 0.96 (0.66-1.41) |
| Genesis, all teams | Away: Up / Down | 0.84 (0.69-1.03) | 0.81 (0.64-1.04) | 0.91 (0.59-1.42) |
| Genesis, teams a person played | Home / Away | 1.23 (1.07-1.41) | 1.24 (1.05-1.46) | 1.24 (0.93-1.65) |
| Genesis, teams a person played | Up / Down | 1.02 (0.89-1.17) | 1.01 (0.85-1.18) | 1.01 (0.76-1.35) |
| Genesis, teams a person played | Home: Up / Down | 1.02 (0.85-1.23) | 1.02 (0.82-1.28) | 0.99 (0.67-1.47) |
| Genesis, teams a person played | Away: Up / Down | 0.88 (0.70-1.10) | 0.84 (0.64-1.10) | 0.89 (0.56-1.43) |
| SNES, all teams | Home / Away | 1.02 (0.89-1.17) | 1.03 (0.87-1.22) | 1.20 (0.89-1.62) |
| SNES, all teams | Up / Down | 1.01 (0.88-1.16) | 1.05 (0.88-1.24) | 0.93 (0.69-1.26) |
| SNES, all teams | Home: Up / Down | 1.00 (0.81-1.23) | 1.01 (0.78-1.30) | 1.13 (0.73-1.74) |
| SNES, all teams | Away: Up / Down | 1.02 (0.83-1.25) | 1.08 (0.84-1.39) | 0.61 (0.36-1.02) |
| SNES, teams a person played | Home / Away | 1.04 (0.90-1.21) | 1.08 (0.90-1.30) | 1.22 (0.89-1.66) |
| SNES, teams a person played | Up / Down | 1.02 (0.88-1.18) | 1.07 (0.89-1.29) | 0.98 (0.72-1.34) |
| SNES, teams a person played | Home: Up / Down | 1.02 (0.82-1.27) | 1.06 (0.81-1.38) | 1.12 (0.72-1.74) |
| SNES, teams a person played | Away: Up / Down | 0.99 (0.79-1.25) | 1.04 (0.79-1.38) | 0.70 (0.41-1.18) |

What the games show so far:

- **Up / Down: no effect on either system** (every ratio 0.93-1.07, every range holding 1.00).
- **Home / Away on the Genesis: Home took more shots in these games** (not in the leagues' 86,735 games: above).
  1.22 times the attempts per game minute (1.07-1.38) and
  1.23 times the shots on goal (1.05-1.43); goals 1.32 (1.00-1.75), on the edge. With 19 games it was within chance.
  It holds in the 20 games with a person on each side (attempts 1.27, 1.04-1.58 resampling games; goals 1.23,
  0.83-1.88), so it isn't the computer teams. But most of those games are the same few players, so which person was
  Home can't be told apart from the home edge itself; Home's goals per attempt are no better (21.5% against 19.9%).
  The built-in reasons (below) are small. More games with other players would settle it.
- **No Home / Away difference on the SNES** in attempts or shots on goal (1.02, 1.03); goals 1.20 (0.89-1.62), within
  chance (the first 8 games gave 1.52).
- **The direction changes how people aim, not how often they score.** Going up, people push the d-pad toward the net,
  which aims high (Genesis 29% of a person's shots aimed high going up against 11% going down; SNES 54% against
  11%). Goals per attempt end up about the same either way.
- **More uncounted stops going up on the Genesis** (12% of shots that reached the goalie, against 7% going down), the
  opposite of what the league's box scores suggest (about 10% more shots on goal going up). These games give 1.00
  times the shots on goal per minute going up (0.86-1.17), which holds the league's 1.10 too.
- **Away going up is still the weakest cell** (Genesis 3.0 shots on goal per 5:00 against 3.7-4.4 in the others; SNES
  0.8 goals per 5:00 against 1.3-1.5, Away's Up / Down goals 0.61, 0.36-1.02). That cell is almost all period 2, the
  one period Away goes up, so it mixes direction with whatever is special about the middle period. Still the thing to
  watch.
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
(SNES_SHOOTING.md 5), which may blunt the pass effects seen on the Genesis; more games needed.
