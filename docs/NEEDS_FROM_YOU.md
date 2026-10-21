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

4. ~~**Pucks through the goalie's legs (Genesis).**~~ Done (2026-10-19): the user's 2v2 game confirmed it (three goals);
   one more recorded going down the screen would show the bottom net's band too.
   Was: **Pucks through the goalie's legs (Genesis).** In a two-controller practice game: with one controller, send fast
   flat pucks straight at the goalie's middle (a pass shot: B with nobody ahead, toward the net; or a slapshot aimed
   along the ice, Down held); with the other, have the goalie press C as it arrives (a butterfly) a few times, and not
   press it a few times. Note roughly when. *Settles:* the blind band through the middle of a butterfly (GENESIS_MECHANICS
   5.5): the puck should pass through untouched when it's at ice level and not rising, and bounce backward off him.

## Things to note when they happen

1. **A Genesis penalty shot that ends the moment it starts.** Note the game and roughly when. The helper now records
   the penalty-shot flags, so a recorded one can be traced.
2. **A SNES injury.** None recorded yet; it would confirm the SNES injury rules.
2b. **A SNES ghost** (a skater passing straight through an opponent, as in the PIT-WPG GIF). Note the game and the time
   with the helper recording: the recording holds the speeds, animations and flags needed to see why. The known causes
   (a player in a boards fall, identical speeds, or a stacked burst head-on at extreme speed) don't fit the GIF.
3. **Helper processes still running with its window closed.** Note how you last started the helper (double-click, a
   shortcut, at startup).

## Questions only you or your league can answer

1. ~~**Does the opponent's iPhone open the game files from the S3 link?**~~ Yes (2026-10-18).
2. ~~**In online league games, is Home always the netplay host?**~~ No (2026-10-18): Genesis players pick Player 1 or 2
   in RetroArch whoever hosts, and SNES players pick their side in the game, so hosting isn't part of the home edge.

## Checks you could run on your box-score database

1. **Home record by home bonus.** Teams with no home bonus in the ROM (CGY, DAL, DET, HFD, NYI, QUE, TB) against teams
   with +2 (BOS, BUF, CHI, MTL, PHI, PIT, STL): if the bonus is behind the 51%, the first group should be at 50% at home
   and the second a little higher.
2. **Shots on goal by period.** Each side's shots on goal in periods 1 and 3 against period 2 (Home goes up in 1 and 3,
   Away in 2): separates up / down from home / away.

## Things to review in the replays (each a quick look)

1. **Goalie giveaway goals** (a goalie's pass picked off, a goal within 6 s): Moog twice, Joseph, Belfour in the older
   recordings. Are they right?
2. **Own goals** found in the older games: Juneau and Suter (CGY-BOS), Ciccarelli (capture2), Robitaille (capture3).
   Did each defender really put it in his own net? (Steve Smith's in CHI-CGY was not one: it was an unrecorded SNES
   penalty-shot goal, fixed 2026-10-18.)
3. **Unconfirmed posts:** capture5 P3 4:47 and capture3 P2 2:32.
4. **Long far-post slapshot goals (Genesis).** The game, the time and the shooter of a few. The xG model doesn't show
   the far post beating the near post except with the hardest shots (GENESIS_MECHANICS 5.8). The examples would show
   what's different.
5. **A Genesis goalie pushed into his net with the puck.** Note the game and time when it happens; none recorded yet
   (GENESIS_MECHANICS 5.9 explains it from the code).
6. **Cross-crease goals you remember**, either system, to check against the wind-up rule (5.6 / 5.7).

## To pass on to the disassembly maintainers (if you like)

Found in the 2026-10-21 review and studies: comments that say something different from the code they sit on (the code
and our recordings agree with each other; the comments are the slips).
1. **NHL94Genesis, collide94.asm, the breakaway roll in checkagr:** the comment says "d0 = 3..5"; the code loads 8, 7,
   4 or 3 by the fouled player's distance from the goal line (over 117, 59-117, 45-58, closer).
2. **NHL94SNES, routines/collide/puckgoalie.asm, the hold test:** the comment says the catch limit is
   random((2 + shotspd) x 512) + $C00; the code adds $2000 (`adc.w #$2000`).
3. **NHL94SNES, routines/collide/setplayer.asm, the third-period bonus:** the comment says no bonus in the first half
   of the period; the code skips the bonus when (period length / 2 - seconds left) is positive, i.e. in the second
   half, so the bonus is on while more than half the third period is left (the game's clock counts down). Our
   recordings show the same.
4. **NHL94SNES, routines/logic/assgoalie.asm, the computer goalie's poke roll:** the comment says "1 in 6"; the code
   takes a RandomWord under $0A00, 1 in 25.6. In the same routine, the person's goalie test `bit.w #$4000` on JoyPad is
   commented "B held?"; $4000 is Y (B is $8000), and the pad test above it, $0040, is X.
5. **NHL94Genesis, checks94.asm, CPgoalie:** "exit if behind by more than 2" sits on `cmp #2` / `bne`, which exits for
   anything but exactly 2: a code bug (the SNES port tests one or two behind), not only a comment slip.
6. **NHL94Genesis, checks94.asm, PuckIChk `.set`:** "puck within the crease width: icing goes on to the goal line
   check"; it's reached when the puck is *outside* ±$2C, and within it icing is cancelled.
7. **NHL94SNES, routines/checks/chk4shot.asm:** `cmp.w #$2711` ("distance^2 > 100*100?") has no branch after it, so the
   test does nothing (the Genesis branches with `bhi`).
