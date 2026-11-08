# "Game variables": what's known, and what we could study

A plan from the forum thread [NHL'94 Game Variables](https://forum.nhl94.com/index.php?/topic/20372-nhl94-game-variables/)
(2020-2025). The opening post lists the things people blame when a game goes their way or not, the "game variables
... overlayed on top of everything": shots missing open nets, goalies making extra saves or letting in easy goals,
solid checks failing, passes and one-timers not connecting, the puck being tipped away, penalties away from the play,
momentum and hot / cold. Replies add that most goals at the top level come from mental errors, that elite players
win by knowing where the computer's skaters are and moving them, and (2025) that getting the crowd loud makes a
team play better. A 2021 post proposes tracking possessions, chances, loose pucks, penalties, goalie-control saves
and an "AI factor" (+1 / -1 for the game helping or hurting a team), noting that the AI factor has no defined
"normal" to measure against.

Our tools can measure most of this: the recorded games (positions, every shot with its expected goals, passes,
checks, the hidden ratings as played), the league's result databases (about 120,000 games since 2013, box scores
with goals and penalties by time), and the game itself run headless with its code read from the disassemblies.

## Already answered

- **Momentum: there isn't any in the game.** A team that shoots well early doesn't keep shooting well: over the
  league's box scores (87,000 Genesis and 36,000 SNES games), a team shooting 50% or better in the first period
  shot 34.6% afterwards against 34.2% if the order of its shots meant nothing (Genesis), and a little worse than that
  on the SNES. The recorded games, shot by shot, agree: the shots right after a goal go in no more often than chance
  says. ([LEAGUE_RESULTS.md, "Momentum"](LEAGUE_RESULTS.md), [STUDY_NOTES.md, "Momentum in the recorded
  games"](STUDY_NOTES.md))
- **Hot and cold are real, and hidden.** Each player gets a random hot / cold value at the start of every game.
  - Genesis: one value for all of his ratings, worth about -0.6 to +0.4 of a rating step (a 4 plays somewhere from
    3.4 to 4.4). The hot / cold players and flame icons the game shows are not this value: they're fake.
    ([GENESIS_GUIDE.md, 1.2](GENESIS_GUIDE.md))
  - SNES: a value per rating, and a sign bug **maxes every "cold" rating** instead of lowering it, so a "cold"
    player is often better. ([SNES_MECHANICS.md, 2.2](SNES_MECHANICS.md))
  - The Match Viewer's player card shows each player's hot / cold as played.
- **The crowd.**
  - Genesis: while the crowd meter is at or above the home arena's record (80 dB if there isn't one), the computer's
    skaters on **both** teams react one frame faster. In the recorded games that was 73% of play, so it's the normal
    state, and it favours neither team. It does nothing to faceoffs (pure timing), passes or shots, and the
    "+2 Agility, +2 Speed" crowd bonus in the code is on for everyone all the time.
    ([GENESIS_MECHANICS.md, 14.3](GENESIS_MECHANICS.md))
  - Genesis has two crowd levels. The meter (the excitement) rises only with shots, big hits, goals and
    breakaways. The **noise** rises with more: a goalie diving under a person's control (C with a direction) adds to
    it every time, so hammering C with the goalie at a stoppage really does make the building louder and the crowd
    animate faster. But the noise only sets the crowd's sound and animation; play never reads it.
  - SNES: the crowd has no effect on play at all. ([SNES_MECHANICS.md, 13](SNES_MECHANICS.md))
- **Home ice** is a hidden ratings bonus for the home team and a penalty for the visitors, and on both systems
  that bonus is the whole home edge in the league's results. ([LEAGUE_RESULTS.md](LEAGUE_RESULTS.md))
- **Third-period "comeback" bonus:** the game gives a bonus to a team tied or behind in the third period, but its
  test is backwards (on in the first half of the period, off in the second), on both systems, and it's too small to
  show in the league's results. ([GENESIS_MECHANICS.md, 2.3](GENESIS_MECHANICS.md), [SNES_MECHANICS.md,
  2.3](SNES_MECHANICS.md))
- **Several "variables" are rules with dice in them,** each explained in the mechanics documents: where a shot goes
  (exact within a short range, otherwise scattered upward only), how a goalie saves (geometry: his body and pads
  against the puck's path), whether a check knocks a man down (ratings and weights, with the Genesis weight bug),
  whether a pass is picked off. "Goalie letting in an easy goal" has some named causes on the Genesis, counted in
  the Match Viewer's Quirky Events: pucks through the legs (a blind spot by the stick), the top net's shoulder-save
  bobble.
- **Already in the Match Viewer** from the 2021 tracking proposal: possession (and by zone), chances (expected goals
  and high-danger attempts), penalties by person and computer, and saves with a person or the computer in net.

## Results so far

- **Study 1, luck against skill** (the recorded games): the chances a team makes decide most games. The goal
  difference follows the expected-goals difference closely (correlation 0.90 on both systems); luck is about a fifth
  of it. A team's goals against the expected goals of its own shots (the "AI factor", measured) usually land within
  about a goal and a half of zero (the spread is 1.5 goals a game on the Genesis, 1.3 on the SNES), more than 2 goals
  off in about one game in six. The team with clearly better chances lost 2 of 25 Genesis games and 6 of 28 SNES
  games. ([STUDY_NOTES.md, "Game variables: phase 1"](STUDY_NOTES.md))
- **Study 2, what hot / cold is worth:** at the shot, little. Played again with everyone's hot / cold taken out, a
  team's expected goals changed by 0.05 a game on the Genesis (at most 0.38, a cold goalie) and never changed which
  team had the better chances; on the SNES, where the bug maxes "cold" ratings, by 0.18 a game (at most 0.62), and it
  changed which team had the better chances in 1 game of 29. (Its effect on skating, checking and passing isn't
  counted.)
- **Study 3, penalties and the score:** the score doesn't change who gets called. Over about 120,000 league games,
  leading and trailing teams are called equally often (at every moment one team leads and the other trails: 89,244
  penalties to the leaders, 89,191 to the trailers on the Genesis), and the game's penalty roll has no score in it.
  One real effect: tied games in the last minute of the third draw about 15% more calls, most likely people pressing.
  **Penalties away from the play are mostly the computer's skaters** (a computer skater's foul is called twice as
  often as a person's; in the recorded Genesis games the computer's penalized skaters were a median 117 units from
  the puck, people's 42). ([LEAGUE_RESULTS.md, "Penalties and the score"](LEAGUE_RESULTS.md))

- **Study 4, are the dice streaky?** No, for shots, goalies and passes: in the recorded games one result doesn't make
  the same result likelier next time (each player's sequences against shuffles of themselves). A shooter's next shot
  after 1, 2 or 3 misses in a row scored as its expected goals said (Genesis). Checks do cluster (hits follow hits),
  but that's the target: the same man checked again and again, whose weight and ratings decide; split by checker and
  target it goes on the Genesis (a little remains on the SNES).
- **Study 5, missing a great chance:** of the chances worth 0.5 expected goals or more that didn't score, the goalie
  got to most (32 of 71 on the Genesis, 44 of 75 on the SNES), then blocks and posts; the puck going wide or over the
  bar is one miss in five on the Genesis, one in eight on the SNES.
- **Study 6, easy goals:** 17% of Genesis goals and 11% of SNES goals came from chances under 0.1 expected goals (on
  the Genesis about half of them deflections and scrambles). The game's named quirks are a small part (3 through the
  legs, 2 shoulder-save bobbles). A person in net is over-represented: a person had the goalie for a third of the
  easy goals on the Genesis (16% of shots) and half on the SNES (28% of shots).
- **Study 7, loose pucks:** on the Genesis the computer's skaters win about half the loose pucks, and which team's
  computer wins more follows the teams' awareness ratings (the home team's, with its bonus, 54%). No catch-up: the
  leading team's computer wins more, not less. On the SNES a person's own skater gets to most loose pucks.

- **Study 8, what started each goal** (games with a person on each side): almost every goal has something the
  defence did or allowed just before it. On the Genesis the first such thing was the shooter left open (no defender
  within about 10 feet) for 30% of goals, an odd-man rush 24%, the puck taken by force 19%, a giveaway 20% (12% in the
  team's own zone), and nothing of these only 3%; the SNES is much the same (giveaways 10%, nothing 11%). Whether each
  is a mental error or the attacker's skill (a fine pass, a good breakout) the recording can't say.

- **Study 9, a first measure** ("elite players move the computer's skaters"): a person's carrier pulling two
  defenders onto himself while a teammate is open happens in about 40% of attacking-zone possessions. It pays only
  when the pass comes at once (possessions under a second: about half as much again in expected goals); in longer ones
  there's no difference, and the person who did it more often didn't make the better chances. Inconclusive so far:
  it needs games from more players and a look at where the pass goes.

## How each study was done

**The data.** Two sources:
- **The recorded games:** league and practice games recorded with the Match Viewer's helper, about 50 whole games
  on each system, most of them played by one person. Each recording keeps every player's and the puck's position
  about 60 times a second, the controllers, the game's own counts, and the ratings each player actually played with
  (hot / cold included). The converter turns that into events: every shot with how it ended, passes, turnovers, check
  attempts, zone entries, penalties.
- **The league's result databases:** the box scores of about 120,000 league games since 2013 (87,000 Genesis,
  36,000 SNES), with every goal and penalty and the period and second it came in. They have no positions, so they
  answer questions about scores and penalties only. Simulated games are left out; only aggregates are published.

**Expected goals (xG)**, used in several studies: each shot is played out hundreds of times by the game's own shot and
save rules, taken from the game's code (where it was aimed, the shooter's Shot Accuracy and the random scatter, the
puck's flight, the goalie's reach and how he moves), starting from the positions and speeds the recording shows at the
release. The share that goes in is the shot's xG. Deflections and scrambles have none.
([XG_MODELS.md](XG_MODELS.md))

**Shuffle tests**, used where a question is about order (momentum, streaks): a sequence of results is compared with
the same results in a random order, 2,000 times. If the real sequence doesn't stand out from the shuffles, its order
carries no information. Shuffling each player's or team's own results keeps their overall quality fixed, so a good
shooter's many goals can't pass for a streak.

1. **Luck against skill.** Recorded games from the opening faceoff only. For each team: its xG (the chances it made)
   and its goals from the same shots. "Finishing luck" (the "AI factor") is goals less xG; the result's luck is the
   goal difference less the xG difference. Across games, the goal difference's variance is split into what the xG
   difference explains and the rest. "Clearly better chances" means 0.25 xG or more ahead. The Deserve to Win figures
   play each game's shots out exactly. Limit: xG itself is a model (studies 5 and 6 found where it is off).
   (`analysis/luck_vs_skill.py`)
2. **What hot / cold is worth.** Every recorded game's shots played out again with the hot / cold taken out of the
   ratings the shot and save use (the shooter's Shot Accuracy; the goalie's Agility, Speed, awareness and puck
   control): first the shooters only, then the goalies only, then both. The change in each team's xG is what hot /
   cold did. On the SNES, a rating the bug maxed goes back to its normal value plus the team's bonus. Before any
   change, the rerun with the real ratings was checked to reproduce the stored xG exactly. Limit: only the shot and
   the save; hot / cold's effect on skating, checking and passing, which make the chances, isn't counted. On the SNES
   the goalie's reaction time was left as played. (`analysis/hot_cold_worth.py`)
3. **Penalties and the score.** League databases, games with 5-minute periods, regulation only. The score at each
   penalty is rebuilt from the goals before it (a goal in the same second counts as after). Rates are penalties per
   5 minutes of the time each team spent leading, tied or trailing, overall, by margin, by period and in the third
   period's last minute. The cleanest test is the even split: at any moment one team leads and the other trails, so
   with no score effect the leaders and trailers take the same number. A same-team-same-game comparison was also
   made, but penalties cause power-play goals, which end leads, so that one leans by itself. The game's penalty roll
   was read in both games' code. For "away from the play": in the recorded games, the penalized player's distance from
   the puck at the call, person against computer. (`analysis/league_penalties.py`)
4. **Are the dice streaky?** For each kind of roll, each player's results in a game, in order: shots (goal less xG),
   the shots a goalie faced, check attempts that reached a man (hit or not), passes (picked off or not). The test
   statistic adds up how much each result and the next lie on the same side of the player's own average; a positive
   excess over the shuffles means like follows like. Checks were also split by checker and target, to see whether a
   streak was really the same man being checked again. (`analysis/streaks.py`)
5. **Missing a great chance.** Every recorded attempt worth 0.5 xG or more that didn't score, sorted by how it ended
   (the goalie, a skater blocking, a post, or a miss). For a miss, where the puck crossed the front of the net, from
   its recorded path: over the crossbar, wide of a post, or not reaching the net. Also counted: the kind of shot,
   who shot, how far off his line the goalie was, the range. (`analysis/open_net_misses.py`)
6. **Easy goals.** Every recorded goal, matched to its shot; those under 0.1 xG or not priced (deflections,
   scrambles) sorted by the goal's own tags (through the legs, the shoulder bobble, an own goal ...), a rebound, the
   goalie 5 feet or more off his line, a person in net, the kind of shot and the range. To judge "a person in net",
   the same share was counted over all shots on net. Also goals against xG by band, for the models' calibration.
   (`analysis/easy_goals.py`)
7. **Loose pucks.** Games with a person on each side. A loose spell: nobody has the puck for between 0.1 and 3
   seconds with the clock running, ended by someone taking it. Who took it: a person's skater, a computer skater or a
   goalie. Because the game hands the person control of a skater the moment his team gets the puck, "who had him" is
   read just before he reached it. Then each team's computer share against its skaters' awareness ratings, and by
   the score. (`analysis/loose_pucks.py`)
8. **What started each goal.** Games with a person on each side. Each goal gets every cause the recording shows, and
   a primary one in this order: a giveaway by the scored-on team in the 12.5 game seconds before (in its own zone or
   elsewhere), the puck taken from them by force, an odd-man rush, the shooter left open (no defender within about 10
   feet at the release), the goalie 5 feet or more off his line, a rebound, a power play, off a faceoff, or none.
   Limit: the recording shows what happened, not whose fault it was. (`analysis/goal_causes.py`)
9. **Drawing two defenders.** Games with a person on each side. Each possession by a person's carrier in the
   attacking zone. It "drew two" if at some moment two or more defenders were within about 17 feet of him while a
   teammate in the zone had none that close. Compared: the team's xG in the possession and the 2 seconds after,
   overall and at equal possession lengths (so longer possessions don't count twice), and, per game, how often each
   person did it against which team made the better chances. (`analysis/draw_two.py`)

Every script is in the project's repository and documents itself at the top; they can be run again as more games
are recorded.

## Studies (in order)

Each says what it settles and where the data comes from. All use material we already have.

1. **Luck against skill, game by game (the "AI factor", measured).** For each team in each recorded game: goals
   against expected goals (finishing), saves against expected goals (the goalie), posts, check attempts won against
   their odds, passes picked off and pucks lost on contact against what's expected. Then, over the recorded games,
   how much of the results luck explains. *Settles:* a defined "normal" for the AI factor, and how often a game is
   decided by it. Could become a "luck" group in the Match Viewer's team stats.
2. **What hot / cold is worth.** Each recorded game's shots played again through the expected-goals model with
   every player's hot / cold set to neutral; the difference is what hot / cold did, for shooters and goalies.
   *Settles:* "he's cold" in goals per game.
3. **Penalties and the score.** Over the league's box scores (penalties carry their period and time): is the
   leading or the trailing team called more, by period? With the penalty code of both systems read for what rolls a
   call and whether the score enters it. *Settles:* whether the game "makes a narrative" through penalties, and
   penalties away from the play.
4. **Are the game's dice streaky?** For each kind of roll (shot scatter, goalie saves, checks, pass interceptions),
   in the recorded games: does one result make the same result likelier next time, for the same player? The same
   shuffle test as the momentum study. *Settles:* "Modano missed 4-5 in a row."
5. **"Missing an open net from 2 feet."** Every recorded close-range shot with the goalie well out of position that
   didn't score, and why: the scatter, a rising puck, the one-timer's automatic aim, the puck not on the stick.
   The telling ones played again in the game, with animations.
6. **Easy goals.** Every recorded goal with a low expected-goals value and how it went in (through the legs, the
   bobble, a rebound, a goalie caught moving), and how often each happens.
7. **Loose pucks.** Which team the computer's skaters win loose pucks for, by their awareness ratings, a person
   against the computer, and the score.
8. **Goals from mistakes.** Every recorded goal sorted by what started it: a turnover in the team's own zone, an
   odd-man rush, the slot left open, the goalie off his line, a power play, or none of these. *Settles:* how many
   goals come from a mistake someone could see.
9. **Moving the computer's skaters.** How the computer's defenders respond to a person's carrier (for example, how
   often he draws two of them and frees a teammate), compared between players of different strength. The hardest and
   least certain, so last.

All nine have a first answer (above); study 9 needs more players' games to settle. Results go into the project's documents as
each is done, and this list is kept up to date.
