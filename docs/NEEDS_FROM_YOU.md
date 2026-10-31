# Things I need from you

Questions the recordings and the code can't answer on their own. Do any of them whenever you can; each says what to
record or check and what it will settle. Newest at the bottom of each section.

## Recordings to make (with the helper running)

1. **Genesis passing test.** In a practice game against the computer, make a dozen **slow, low passes straight past
   an opponent standing still** (pass along the ice, short, so the puck slides by within a stick's length of him), and
   note the game's name. *Settles:* why about half the slow passes that pass within reach of a stick aren't taken,
   though the game's rule says they should be (GENESIS_MECHANICS.md 6.2).
2. ~~**A SNES flip.**~~ Done (2026-10-30): 18 flips were found in the recorded games, and 864 were played in the game
   (SNES_MECHANICS 6.3).
3. **Shots at an empty net** (either system). In a two-controller practice game, pull one team's goalie and take
   shots at the empty net from near (inside 60 feet) and far (beyond 70 feet), some holding Up, some Down, some
   nothing. *Settles:* the empty-net table in the mechanics docs (section 4.2), worked out from the code but not yet
   seen on real shots.

4. ~~**Pucks through the goalie's legs (Genesis).**~~ Done (2026-10-19): the user's 2v2 game confirmed it (three goals);
   one more recorded going down the screen would show the bottom net's band too.
   Was: **Pucks through the goalie's legs (Genesis).** In a two-controller practice game: with one controller, send fast
   flat pucks straight at the goalie's middle (a pass shot: B with nobody ahead, toward the net; or a slapshot aimed
   along the ice, Down held); with the other, have the goalie press C as it arrives (a butterfly) a few times, and not
   press it a few times. Note roughly when. *Settles:* the blind band through the middle of a butterfly (GENESIS_SHOOTING
   5.5): the puck should pass through untouched when it's at ice level and not rising, and bounce backward off him.

   The three shooting tests below (items 5, 6 and 7) are on one printable page with tally boxes: [PRACTICE_CARD](PRACTICE_CARD.md).

5. **Down slapshots at a set computer goalie (Genesis).** In a practice game against the computer, stand still with
   the puck in the middle, roughly between the tops of the faceoff circles and the blue line, let the goalie settle,
   and take a dozen full slapshots holding Down; then a dozen holding Left or Right. Do it at both ends. *Settles:*
   the scoring map (GENESIS_SHOOTING 4.10), which plays these shots in the game itself and says about 20% go in
   holding Down (more at the top net) and only a few percent with the other aims. Only real play shows whether a
   standing slapshot like that is something a person can set up. The map's goalie is Los Angeles's Kelly Hrudey, played
   cold, which makes him weaker than a typical starter; better goalies stop far more slapshots (SCORING_GENESIS, "The computer goalie's ratings"), so
   note which goalie you shot at.
6. **Slapshots from just left of centre at a set computer goalie (SNES).** In a practice game, stand still with the
   puck a stride to your own left of the middle (2-5 feet), 25-40 feet out, let the goalie settle, and take a dozen
   full slapshots aimed at that side (attacking up the screen: Left; attacking down: Right). Then a dozen from a stride
   to your right, aimed at your right. *Settles:* SNES_SHOOTING 4.8, which plays these in the game itself and says
   about half the first kind go in and almost none of the second. This matters more than it looked: the SNES lane's
   rate depends on the game's frame timing, which changes with who is on the ice (SNES_SHOOTING 4.8).
7. **One-timers from a pass across and from the same side (Genesis).** In a practice game, a dozen one-timers by a
   teammate within about 18 feet of the goal line from a pass across the net's centre line, then a dozen from a pass
   from his own side, the goalie settled first. *Settles:* the one-timer study (SCORING_GENESIS, "One-timers", Genesis),
   which plays them in the game itself: about 63% from across, 20-30% from the same side.
8. ~~**SNES dekes and moves (the 2v2 ROM).**~~ Done (2026-10-25): the user's 2v2 game (`2026-10-25_1951_MTL-LA`) is
   traced and its 26 tries replayed in the game at both nets and by both hands (SNES_SHOOTING 4.10, with GIFs). A
   short game trying the cut going down the screen, released inside about 13 feet, would confirm it in play.
9. ~~**The EA Special at the bottom net (Genesis)**~~ Answered (2026-10-27) by the user's two 2v2 games: 70 forehand
   attempts, 19 scored by the shooter's own follow-up (15 of 40 at the top net, 4 of 30 at the bottom; most of the
   bottom net's failures came after the shot: a defender claimed the rebound, or no shot followed). The simulation:
   SCORING_GENESIS_EA, "The best set-ups at 1.7 a frame" onward. Still open from it: the defender test (plan E), which needs four design answers:
   where the defender starts, whether a person controls him (checking, poking or both), his ratings, and one net or
   both. **Optional for the SNES:** a recording of you trying EA Specials would check SCORING_SNES's EA section against
   real play.

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
3. ~~**Which side is the EA Special taken from?**~~ Answered (2026-10-25): a left-hander from the right side (down the
   right wing, turning a little toward the middle, a wrist shot at the goalie), a right-hander from the left; now and
   then a backhand flip from the other side. **The shooter always faces straight across the rink or diagonally toward
   the goalie as he shoots, never straight up the ice**, so he is placed to claim the rebound. The studies' side was
   right; the standing and straight-up-the-ice runs aren't the real play, and plan "angle" plays it across and at an
   angle (SCORING_GENESIS_EA "EA Specials").
4. ~~**The CDL goalie edit**~~ Settled (2026-10-25): the studies use what `CDL_Season_12.bin` holds: every goalie but
   Roy, Belfour and Fuhr has +1 Agility, +1 Defensive Awareness and +1 Puck Control over the retail ROM (capped at 6),
   Fuhr +1 Agility only, Roy and Belfour nothing; the stick and glove ratings are unchanged.
5. **Tests with a person in net** (Genesis): how a person's goalie reacts to the deke and the floater is to be
   designed with you before anything is run.
6. **Which ROM the SNES Classic leagues play.** With the people taken out, the SNES Classic teams' strengths run
   nearly against NHL94_Classic's ratings (New Jersey and Edmonton on top, Detroit and Montreal at the bottom;
   LEAGUE_RESULTS, "Teams with the people taken out"), where the Genesis order follows its ratings. Do those leagues
   play NHL94_Classic's rosters unchanged, or an edited ROM (balanced teams, a handicap)? And are teams handed out in
   some way that would tilt it (the best people given the weakest teams)?

## Checks you could run on your box-score database

1. ~~**Home record by home bonus.**~~ Done (2026-10-30, the user's databases): on both systems the home edge is the
   home bonus plus away penalty and nothing else (each pair of teams compared both ways); each point is worth about
   twice as much on the SNES (LEAGUE_RESULTS).
2. ~~**Shots on goal by period.**~~ Done: on the Genesis the team going up gets about 10% more shots counted; on the
   SNES no period difference.

## Things to review in the replays (each a quick look)

1. **Goalie giveaway goals** (a goalie's pass picked off, a goal within 6 s): Moog twice, Joseph, Belfour in the older
   recordings. Are they right?
2. **Own goals** found in the older games: Juneau and Suter (CGY-BOS), Ciccarelli (capture2), Robitaille (capture3).
   Did each defender really put it in his own net? (Steve Smith's in CHI-CGY was not one: it was an unrecorded SNES
   penalty-shot goal, fixed 2026-10-18.)
3. **Unconfirmed posts:** capture5 P3 4:47 and capture3 P2 2:32.
4. ~~**Long far-post slapshot goals (Genesis).**~~ Mostly answered (2026-10-24): Neely's in the 2026-10-23 BOS-LA games
   were skating shots, and played in the game the far-post slapshot is a skating shot across toward the stick side,
   50-62% for a strong shooter (SCORING_GENESIS, "Moving shooters"). More examples are still welcome.
5. **A Genesis goalie pushed into his net with the puck.** Note the game and time when it happens; none recorded yet
   (GENESIS_SHOOTING 5.9 explains it from the code).
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
