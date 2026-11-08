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

Phase 1: studies 1-3 (each an hour or two). Phase 2: 4-7. Phase 3: 8-9. Results go into the project's documents as
each is done, and this list is kept up to date.
