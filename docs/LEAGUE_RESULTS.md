# The leagues' own results

What the user's league result databases show about the game as people play it (2026-10-30 on). The databases are
kept outside this repository (`%USERPROFILE%\NHL94_League_Data`); the scripts in `analysis/league_*.py` read them and
print aggregates only, and only aggregates go here (no player names). Shooting by screen direction is in
SHOOTING_STUDY ("The leagues' own results"); confirmations of single mechanics are noted in the mechanics docs with a
pointer here.

The user's league result databases (kept outside this repository; `analysis/league_home_study.py` reads them and
prints aggregates only; `analysis/league_goalie_study.py` the goalies): **86,735 Genesis and 36,180 SNES games** from
2013 to 2026, simulated games left out. Each row has both sides' goals, shots on goal (the game's own count) and
faceoff wins, by period, and each player's and goalie's line. Ranges are 95%.

## Home and away, goalies and teams

| | Genesis | SNES |
| --- | --- | --- |
| Home wins (of decided games) | **50.5%** (+/- 0.3) | **52.3%** (+/- 0.5) |
| Goals a game, home / away | 3.81 / 3.77 | 4.53 / 4.32 |
| Shots on goal a game, home / away | 12.17 / 11.55 (1.05) | 12.37 / 11.20 (1.11) |
| Faceoff wins, home / away | 0.98 | 1.07 |
| Home's share of shots on goal, periods 1 / 2 / 3 | 52.3% / **49.3%** / 52.4% | 52.8% / 52.1% / 52.6% |
| Home's share of goals, periods 1 / 2 / 3 | 49.6% / 51.2% / 49.9% | 51.6% / 50.4% / 51.6% |
| The same player at home minus away (players with 20+ games each way) | shots +0.67 a game, win rate +1.0% (+/- 0.8) | shots +1.20 a game, win rate **+4.5%** (+/- 1.3) |
| Home and screen direction separated (Home's share is h x u / (h x u + 1) going up in periods 1 and 3, h / (h + u) going down in period 2): shots on goal, home h / up u | 1.034 / **1.062** | **1.101** / 1.012 |
| The same, goals | 1.019 / **0.970** | 1.040 / 1.024 |
| Classic leagues (the retail rosters and home bonuses): a team's home win rate minus its own away win rate, by the team's home bonus + away penalty 0 / 2 / 3 (its opponents' bonuses still in it) | +1.1 / +2.7 / +3.6 points | +2.7 / +4.9 / +7.1 points |
| Classic leagues, each pair of teams met both ways (strength cancels): home edge with no bonus at all / per point of home bonus or away penalty | -0.3 (+/- 1.6) / +0.5 (+/- 0.4) points | -1.2 (+/- 2.6) / **+0.9** (+/- 0.6) points |
| Classic games with no bonus either side, home / away: goals, shots, pass completions, checks, faceoffs | 0.98, 1.04, 1.00, 1.01, 0.99 | **1.00**, 1.07, 1.00, 1.10, 1.07 |

- **Genesis: the shot edge is the screen direction, and it's a counting effect** (going up the screen a team gets
  6.2% more shots on goal counted but scores 3.0% fewer goals; the SNES almost none): SHOOTING_STUDY, "The leagues'
  own results".
- **Home: the hidden home / away bonus, and nothing else, on both systems.** Adding up each pair of teams' home win
  rates both ways (their strengths cancel), home ice with no bonus is worth nothing (Genesis -0.3, SNES -1.2 points,
  both within chance), and each point of home bonus or away penalty is worth +0.5 points on the Genesis and +0.9 on
  the SNES, whose 0-15 rating scale makes the same bonus count about twice as much. A typical Classic game has about
  two points of it, which gives the 50.5% and 52.3% seen. In the 451 Classic SNES games with no bonus either side,
  Home scored no more (1.00) and passed no better. (Only the Classic leagues' bonuses are known, from the retail
  tables; SDL16, for one, gives nearly every team +1 / -1.) A small oddity left: in those games SNES Home still had
  about 7% more shots and 10% more checks, with no goals from them.
- **The 29 recorded Genesis games' home edge in attempts** (below: 1.22 times as many per minute) isn't in the
  leagues' results. It was the recorded games' players and sample, not the game.
- **Goalie ratings** (`analysis/league_goalie_study.py`; the Classic leagues, so each goalie's retail ratings; 559,049
  Genesis and 350,696 SNES shots against): **Genesis save % rises with the goalie's Agility**: 64.8% at roster 3,
  68.2% at 4, 69.7% at 5, 72.2% at 6 (+2.2 points a step, correlation +0.93 over 29 goalies; Roy 72.4%, Belfour
  72.0%), as Agility is a Genesis goalie's reach (GENESIS_SHOOTING 5.1). **SNES save % doesn't: 62.3-63.5% at every Agility**
  (correlation +0.24), as every SNES goalie is the same size (SNES_SHOOTING 5.1). The same goalies on the same teams
  show nothing on the SNES, so the Genesis gradient isn't just good teams in front of them. (Puck Control tracks
  Genesis save % too, +0.69, but the best goalies have both.)
- **Team ratings can't be checked this way:** a team's roster strength doesn't predict its league results (Genesis
  -0.11, SNES -0.46 against the top 12 skaters' Overall), as people pick or are given teams to balance a league, and
  Overall is a poor measure anyway.

## Game-wide patterns (`analysis/league_patterns.py`)

| | Genesis | SNES |
| --- | --- | --- |
| Goals / shots on goal a game, shooting % | 7.58 / 23.7, 32.0% | 8.85 / 23.6, 37.6% |
| Power play: goals per power play; power plays a game | 30.4%; 2.54 | 40.6%; 2.22 |
| Shorthanded goals per 100 power plays | 20.4 | 27.5 |
| Breakaways: goals per breakaway; a game | 13.6%; 4.2 | 14.5%; 3.4 |
| One-timers: goals per one-timer tried; a game; share of all goals | 30.9%; 8.7; 35% | 24.9%; 10.3; 29% |
| Penalty shots scored | 33% (22,076) | 35% (11,118) |
| Passes completed | 62.1% | 56.3% |
| Goals by period, 1 / 2 / 3 / OT | 2.48 / 2.49 / 2.49 / 0.13 | 2.96 / **2.80** / 2.98 / 0.11 |
| Games to overtime; ties | 13.4%; 0.4% | 12.1%; 0.7% |

- **One-timers are a third of all Genesis goals** (35%; 29% on the SNES), at 31% per try, about the shooting
  percentage of a shot that reaches the net; a breakaway scores only 14%.
- **A power play works mostly by stopping the shorthanded team** (the user's own study found the same;
  `analysis/league_strength_study.py` rebuilds each regulation timeline from the penalty and goal lists, 86,098
  Genesis and 36,108 SNES games; the goals' own strength tags agree with it 97-99%). Goals a team-minute against
  5-on-5:

  | | Whole man advantage | First 20 s after the call | After that |
  | --- | --- | --- | --- |
  | Genesis, power play (5-on-4) / shorthanded (4-on-5) | **+7% / -24%** | -15% / -52% | +15% / -14% |
  | SNES, power play / shorthanded | **+10% / -23%** | -8% / -48% | +15% / -15% |
  | Genesis, 5-on-3 / 3-on-5 | **+20% / -55%** | -4% / -73% | +35% / -43% |
  | SNES, 5-on-3 / 3-on-5 | **+23% / -51%** | 0% / -72% | +35% / -40% |
  | Genesis, 4-on-3 / 3-on-4 (2,861 team-minutes) | -6% / -47% | -30% / -71% | +17% / -23% |
  | SNES, 4-on-3 / 3-on-4 (1,166 team-minutes) | -16% / -36% | -47% / -63% | +10% / -13% |
  | 4-on-4, Genesis / SNES | -18% / -15% | | |

  4-on-3 is best set against 4-on-4: the man up scores about 15% more than at 4-on-4 on the Genesis and no more on
  the SNES, the man down 35% and 25% less (few goals: about 700 and 300).

  Over a whole power play the shorthanded team's scoring falls about three times as much as the power play's rises.
  Most of that is the first 20 seconds after the call: the restart faceoff is in the penalized team's end and it
  hardly scores, while the power play is held down by the restart too (4-on-4 is just as low then). After that the
  two are about equal and opposite. That fits how goals come in this game (the user's reading): in the recorded games
  81% of Genesis and 79% of SNES goals came off the rush (within 5 s of the zone entry), only 3-5% from a faceoff
  play, and scoring in the 20 game-seconds after any faceoff was 16% (Genesis) and 26% (SNES) below the rest of play.
  A penalty means a faceoff, usually in the penalized team's end: no rush for either side, and the shorthanded team
  must get the puck out and back up the ice before it can rush. (The databases list every minor as 120 s; 132 of 333 Genesis leagues and 9 of
  181 SNES leagues play 1-minute minors, which the script finds from each league's own power-play goals.)
- **No sign of the backwards comeback bonus** (+2 Offensive Awareness and Checking, +4 pass / shoot bias for a tied or
  trailing team, on in the first half of the third period by a bug: GENESIS_MECHANICS 2.3): the trailing team's share
  of goals is 44-46% in each half of the second and third periods alike (first half minus second half, third period
  against second: -0.4 points on both systems, 182,000 and 93,000 goals). Offensive Awareness does nothing for the
  skater a person controls, so a bonus this size was never going to show.
- **The SNES second period has about 5% fewer goals** (2.80 against 2.96-2.98) on the same shots (7.80 against
  7.72-7.73): goals per shot 35.9% against 38.3-38.6%, for both teams (Home 8% fewer than in periods 1 and 3, Away
  3%). Each period has one team attacking each net, so it isn't a net, and the screen direction (+2.4% goals going
  up) accounts for only part of Home's drop. The Genesis periods are equal. Cause unknown (SNES_MECHANICS 16). **Not
  the period number** (2026-10-30): in periods 1-2 the code reads it only for the records, and the harness
  (`analysis/scoring_map/snes_period_hand_run.py`) played the same 52,000 standing shots against the set computer
  goalie with only the period number changed, period 1 as 2 at the top net and period 2 as 1 at the bottom: the same
  result shot for shot (110 and 186 goals, none different). So the harness's bottom-net runs (period 2) aren't
  affected by it either. What period 2 changes is the direction of play: each team attacks the other net. Something
  that goes with a team and a direction together (code that uses the team where it should use the direction, or the
  people), or something in play a standing shot doesn't reach, is left.
- **The Genesis game has tightened over the years:** 8.1-8.7 goals a game and 34-36% shooting in 2013-2017, 7.3-7.6
  and 31-32% since 2020, on the same 23-24 shots; the SNES stayed at 8.5-9.3 and 35-40%.

## Ratings, game flow, skill and luck (`analysis/league_player_study.py`, `analysis/league_flow_study.py`)

**Penalties by roster Aggression** (Classic leagues, the retail ratings; players with 150+ games): the Genesis wrap
shows. Penalties per 100 games at roster 0-5: 22, 27, 33, **35, 29**, 41 (per 100 checks 4.4, 5.8, 6.7, **6.8,
5.6**, 6.6): rising to 3, then down at 4, which plays like a 1 (GENESIS_MECHANICS 8.2; few players at 0 and 5). The
SNES has no wrap: 19, 22, 26, 26, 28, 28, 33 at 0-6, rising throughout, flattened by the "cold" maxing.

**Which ratings make scorers** (within each team and position, all ratings fitted at once, so the team, its opponents
and the people playing it cancel; about 95 Genesis and 90 SNES forwards; per roster step):

| Forwards | Goals a game | Shots a game | Shooting % |
| --- | --- | --- | --- |
| Genesis | **Shot Power +0.29**, Speed +0.22, Shot Accuracy +0.15, Stick Handling +0.11, Agility +0.10, Weight -0.06 | Shot Power +0.69, Speed +0.51, Shot Accuracy +0.39, Stick Handling +0.32, Agility +0.27, Weight -0.19 | Shot Power +1.8 points, Speed +1.0, Shot Accuracy +0.7 |
| SNES | Speed +0.18, Shot Power +0.16, Shot Accuracy +0.14, Agility +0.14, Stick Handling +0.14, Weight +0.08 | Speed +0.39, Agility +0.34, Stick Handling +0.33, Shot Power +0.29, Shot Accuracy +0.28, Weight +0.20 | Shot Power +1.8, Shot Accuracy +1.0 |

Offensive Awareness, Checking and Pass Accuracy do next to nothing for a forward's scoring on either system (Offensive
Awareness never touches the skater a person controls). Shot Power is the Genesis scorer's rating (its slapshot
threshold, GENESIS_SHOOTING 4.3); on the SNES the ratings share it more evenly, and Weight helps a little instead of
costing (it costs less acceleration there). These are what the ratings do as people use the players: a fast, strong
shooter also gets the puck more.

**Genesis checks a game** (the player's own checks thrown): forwards -0.57 a Weight step (lighter forwards check more),
+0.61 an Agility step, +0.66 a Checking step; defencemen +1.03 a Checking step, Weight +0.09. So a light, quick
forward lands more checks, as acceleration gets a skater to the man: the user expected heavier players to log more
(repeated tries), but the counter counts contacts, and a heavy forward reaches fewer.

**Win probability** (every game whose goal list adds up to its score, overtime included; a tie counts half):

| Lead after | 60 s | 300 s (1st period) | 600 s (2nd) | 750 s | 840 s | 870 s |
| --- | --- | --- | --- | --- | --- | --- |
| Genesis, 1 / 2 / 3 goals | 68 / 82 / 92% | 70 / 85 / 93% | 75 / 91 / 98% | 82 / 96 / 99% | 90 / 99 / 100% | 94 / 100 / 100% |
| SNES, 1 / 2 / 3 goals | 67 / 80 / 93% | 69 / 84 / 92% | 74 / 89 / 97% | 80 / 95 / 99% | 89 / 99 / 100% | 94 / 100 / 100% |

- **A plain model fits it:** both teams keep scoring at the league's rate, overtime a coin flip: within 1-4 points
  everywhere (the real curves a little higher early, as the leader tends to be the better player). Goals in this game
  behave like independent events.
- **The 90% line** (the user's "coasting"): a 2-goal lead stays at 90% or more from 570 s on (Genesis) or 640 s (SNES),
  a 3-goal lead from 70-90 s (4 and 5 goals from 130-210 s only because few games have them earlier).
- **The players matter as much as the lead:** a 1-goal lead after two periods holds 75% of the time between players
  rated within 100 of each other, 85% when the leader is rated 100+ higher, 57-59% when the leader is rated 100+ lower.

**No momentum:** the team that just scored got the next goal 52.5% (Genesis) and 52.6% (SNES) of the time, against
53.0% and 52.9% if each game's goals came in random order (571,000 and 284,000 goal pairs): if anything the team just
scored on answers a shade more often.

**No score effects:** the team leading after two periods gets 50.8 / 51.6 / 54.9% of the third-period shots with a
1 / 2 / 3+ goal lead (Genesis; SNES 50.7 / 51.5 / 55.0%), just what a side with the same rating edge gets when the game
is tied (51.1 / 52.0 / 53.9%; SNES 50.9 / 51.6 / 53.3%). Leaders don't sit back and trailers don't swarm; the high shot
shares of periods 1-2 (54-65%) were partly why they led.

**Skill and luck:** each player's odd and even games in a league season (3,622 Genesis and 1,565 SNES player-seasons
with 10+ games each way) correlate 0.77-0.78 in win %, 0.84-0.86 in goal difference, 0.84-0.87 in shots and 0.78-0.80
in shooting %: results in this game are mostly the player (and the team they play). Save % is the most luck (0.67 /
0.53), as the computer is in net.

**Player ratings** (an Elo rating per person in date order, tuned on the next games: K 16 Genesis, 24 SNES): it
predicts the next game with log loss 0.598 / 0.591 against 0.693 for a coin flip; regulars spread 185 / 210 points, so
a one-standard-deviation edge wins 74% / 77%.

**A coasting bonus** (`analysis/league_elo_coasting.py`; the user's own ratings give one): the winner's update is
K x (1 + bonus), the bonus being the final unbroken stretch at a 90%+ chance of winning (a 1-goal lead never counts)
as a share of the third period: 100% for all of the third, 200% for all of the second and third, scaled in between,
and at least 10% for any 2-goal win. The 90% line from the table above (by lead and time), or from a model with the
two players' ratings in it. Each version's K tuned; log loss on the next games:

| | Plain Elo | Coasting bonus | Capped at 100% | Ratings in the 90% line | A goal-margin bonus instead |
| --- | --- | --- | --- | --- | --- |
| Genesis | 0.5982 (K 16) | 0.5990 (K 8) | 0.5982 (K 10) | 0.6024 (K 7) | 0.5978 (K 10) |
| SNES | 0.5907 (K 20) | 0.5898 (K 10) | 0.5893 (K 12) | 0.5932 (K 10) | 0.5891 (K 14) |

The winner coasts in 63% (Genesis) and 66% (SNES) of games, for a mean bonus of 1.1 when they do. The bonus does
nothing for the Genesis ratings and helps the SNES ones a little (0.001), no more than a plain bonus for the margin
of victory (25% for each goal past the first, up to 100%): coasting time is mostly the margin by another
name. Putting the ratings in the 90% line makes it worse on both: the favourite reaches the line sooner, so the
bonus goes mostly to expected wins, which the ratings had already counted.

**By year:** the Genesis shooting % fell from 33-36% (2013-2019) to 31-32% (2020 on) on the same shots, penalty
minutes from about 6 a game to 3-5; one-timers, breakaways and checks stayed level. SNES pass completion jumped from
52-57% to 63-65% in 2025-26 (new leagues or ROMs counting differently, most likely); the rest level.

**Goals by second of the period:** the first 10 seconds give a third of the usual rate (the faceoff), the last 10
seconds about 8% more than usual; the rest is flat.

