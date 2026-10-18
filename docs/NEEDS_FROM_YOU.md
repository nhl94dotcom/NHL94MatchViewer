# Things I need from you

Questions the recordings and the code can't answer on their own. Do any of them whenever you can; each says what to
record or check and what it will settle. Newest at the bottom of each section.

## Recordings to make (with the helper running)

1. **Genesis passing test.** In a practice game against the computer, make a dozen **slow, low passes straight past
   an opponent standing still** (pass along the ice, short, so the puck slides by within a stick's length of him), and
   note the game's name. *Settles:* why about half the slow passes that pass within reach of a stick aren't taken,
   though the game's rule says they should be (GENESIS_MECHANICS.md 6.2).
2. **A SNES flip** (Y with the puck, a few of them, in the neutral zone and in the attacking zone). *Settles:* where
   the SNES flip lands; none has been recorded yet.
3. **Shots at an empty net** (either system). In a two-controller practice game, pull one team's goalie and take
   shots at the empty net from near (inside 60 feet) and far (beyond 70 feet), some holding Up, some Down, some
   nothing. *Settles:* the empty-net table in the mechanics docs (section 4.2), worked out from the code but not yet
   seen on real shots.

## Things to note when they happen

1. **A Genesis penalty shot that ends the moment it starts.** Note the game and roughly when. The helper now records
   the penalty-shot flags, so a recorded one can be traced.
2. **A SNES injury.** None recorded yet; it would confirm the SNES injury rules.
3. **Helper processes still running with its window closed.** Note how you last started the helper (double-click, a
   shortcut, at startup).

## Questions only you or your league can answer

1. **Does the opponent's iPhone open the game files from the S3 link?** If not, what the page shows.
2. **In online league games, is Home always the netplay host?** If so, the host's connection could be part of the
   home edge.

## Checks you could run on your box-score database

1. **Home record by home bonus.** Teams with no home bonus in the ROM (CGY, DAL, DET, HFD, NYI, QUE, TB) against teams
   with +2 (BOS, BUF, CHI, MTL, PHI, PIT, STL): if the bonus is behind the 51%, the first group should be at 50% at home
   and the second a little higher.
2. **Shots on goal by period.** Each side's shots on goal in periods 1 and 3 against period 2 (Home goes up in 1 and 3,
   Away in 2): separates up / down from home / away.

## Things to review in the replays (each a quick look)

1. **Goalie giveaway goals** (a goalie's pass picked off, a goal within 6 s): Moog twice, Joseph, Belfour in the older
   recordings. Are they right?
2. **Own goals** found in the older games: Juneau and Suter (CGY-BOS), Ciccarelli (capture2), Robitaille (capture3),
   Steve Smith (CHI-CGY, SNES). Did each defender really put it in his own net?
3. **Unconfirmed posts:** capture5 P3 4:47 and capture3 P2 2:32.
