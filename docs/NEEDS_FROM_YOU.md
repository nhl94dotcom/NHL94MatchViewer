# Things I need from you

Questions the recordings and the code can't answer on their own. Do any of them whenever you can; each says what to
record or check and what it will settle. Newest at the bottom of each section.

## Recordings to make (with the helper running)

1. **Genesis passing test.** In a practice game against the computer, make a dozen **slow, low passes straight past
   an opponent standing still** (pass along the ice, short, so the puck slides by within a stick's length of him), and
   note the game's name. *Settles:* why about half the slow passes that pass within reach of a stick aren't taken,
   though the game's rule says they should be (GENESIS_MECHANICS.md 6.2).
2. **Shots at an empty net** (either system). In a two-controller practice game, pull one team's goalie and take
   shots at the empty net from near (inside 60 feet) and far (beyond 70 feet), some holding Up, some Down, some
   nothing. *Settles:* the empty-net table in the mechanics docs (section 4.2), worked out from the code but not yet
   seen on real shots.

   The three shooting tests below (items 3, 4 and 5) are on one printable page with tally boxes: [PRACTICE_CARD](PRACTICE_CARD.md).

3. **Down slapshots at a set computer goalie (Genesis).** In a practice game against the computer, stand still with
   the puck in the middle, roughly between the tops of the faceoff circles and the blue line, let the goalie settle,
   and take a dozen full slapshots holding Down; then a dozen holding Left or Right. Do it at both ends. *Settles:*
   the scoring map (GENESIS_SHOOTING 4.10), which plays these shots in the game itself and says about 20% go in
   holding Down (more at the top net) and only a few percent with the other aims. Only real play shows whether a
   standing slapshot like that is something a person can set up. The map's goalie is Los Angeles's Kelly Hrudey, played
   cold, which makes him weaker than a typical starter; better goalies stop far more slapshots (SCORING_GENESIS, "The computer goalie's ratings"), so
   note which goalie you shot at.
4. **Slapshots from just left of centre at a set computer goalie (SNES).** In a practice game, stand still with the
   puck a stride to your own left of the middle (2-5 feet), 25-40 feet out, let the goalie settle, and take a dozen
   full slapshots aimed at that side (attacking up the screen: Left; attacking down: Right). Then a dozen from a stride
   to your right, aimed at your right. *Settles:* SNES_SHOOTING 4.8, which plays these in the game itself and says
   a little under half of the first kind go in at the top net (about 20% at the bottom) and almost none of the second, with real line-ups on the ice (SNES_SHOOTING 4.8).
5. **One-timers from a pass across and from the same side (Genesis).** In a practice game, a dozen one-timers by a
   teammate within about 18 feet of the goal line from a pass across the net's centre line, then a dozen from a pass
   from his own side, the goalie settled first. *Settles:* the one-timer study (SCORING_GENESIS, "One-timers", Genesis),
   which plays them in the game itself: about 63% from across, 20-30% from the same side.
6. **Optional:** a short SNES game trying the deke cut going down the screen, released inside about 13 feet (would
   confirm SNES_SHOOTING 4.10 in play); a recording of you trying SNES EA Specials (checks SCORING_SNES's EA section).
7. **The EA Special defender test (Genesis, plan E)** needs four design answers from you: where the defender starts,
   whether a person controls him (checking, poking or both), his ratings, and one net or both (SCORING_GENESIS_EA).
8. **An SNES game on a 2026 SA-1 build** (2 MB, 60 frames a second), with the helper running, if the league plays
   them. *Settles:* that recording works in a real RetroArch session (so far only a headless test, the 32-team
   build), and gives the SA-1 xG work (STUDY_NOTES, "SNES xG for SA-1 games") real shots to check against.

## Things to note when they happen

1. **A Genesis penalty shot that ends the moment it starts.** Note the game and roughly when. The helper now records
   the penalty-shot flags, so a recorded one can be traced.
2. **A SNES injury.** None recorded yet; it would confirm the SNES injury rules.
3. **A SNES ghost** (a skater passing straight through an opponent, as in the PIT-WPG GIF). Note the game and the time
   with the helper recording: the recording holds the speeds, animations and flags needed to see why. The known causes
   (a player in a boards fall, identical speeds, or a stacked burst head-on at extreme speed) don't fit the GIF.
4. **Helper processes still running with its window closed.** Note how you last started the helper (double-click, a
   shortcut, at startup).

## Questions only you or your league can answer

1. **Team bonuses in the strength fit:** should strengths use each team's real home and away bonuses? Otherwise they
   stay inside each team's value.
2. **Tests with a person in net** (Genesis): how a person's goalie reacts to the deke and the floater is to be
   designed with you before anything is run.

## Things to review in the replays (each a quick look)

1. **Goalie giveaway goals** (a goalie's pass picked off, a goal within 15 game s): Moog twice, Joseph, Belfour in the older
   recordings. Are they right?
2. **Own goals** found in the older games: Juneau and Suter (CGY-BOS), Ciccarelli (capture2), Robitaille (capture3).
   Did each defender really put it in his own net? (Steve Smith's in CHI-CGY was not one: it was an unrecorded SNES
   penalty-shot goal, fixed 2026-10-18.)
3. **Unconfirmed posts:** capture5 P3 4:47 and capture3 P2 2:32.
4. **A Genesis goalie pushed into his net with the puck.** Note the game and time when it happens; none recorded yet
   (GENESIS_SHOOTING 5.9 explains it from the code).
5. **Cross-crease goals you remember**, either system, to check against the wind-up rule (5.6 / 5.7).

## To pass on to the disassembly maintainers (if you like)

Found in the 2026-10-21 review and studies (the first seven still in the code 2026-11-08, paths current; the eighth found 2026-11-09): comments that say something different from the code they sit on (the code
and our recordings agree with each other; the comments are the slips).
1. **NHL94Genesis, collide94.asm, the breakaway roll in checkagr:** the comment says "d0 = 3..5"; the code loads 8, 7,
   4 or 3 by the fouled player's distance from the goal line (over 117, 59-117, 45-58, closer).
2. **NHL94SNES, routines/collide/puckgoalie.asm, the hold test:** the comment says the catch limit is
   random((2 + shotspd) x 512) + $C00; the code adds $2000 (`adc.w #$2000`).
3. **NHL94SNES, routines/collide/setplayer.asm, the third-period bonus:** the comment says no bonus in the first half
   of the period; the code skips the bonus when (period length / 2 - seconds left) is positive, i.e. in the second
   half, so the bonus is on while more than half the third period is left (the game's clock counts down). Our
   recordings show the same.
4. **NHL94SNES, routines/logic/assignments/assgoalie.asm, the computer goalie's poke roll:** the comment says "1 in 6"; the code
   takes a RandomWord under $0A00, 1 in 25.6. In the same routine, the person's goalie test `bit.w #$4000` on JoyPad is
   commented "B held?"; $4000 is Y (B is $8000), and the pad test above it, $0040, is X.
5. **NHL94Genesis, logic94.asm, CPgoalie:** "exit if behind by more than 2" sits on `cmp #2` / `bne`, which exits for
   anything but exactly 2: a code bug (the SNES port tests one or two behind), not only a comment slip.
6. **NHL94Genesis, logic94.asm, PuckIChk `.set`:** "puck within the crease width: icing goes on to the goal line
   check"; it's reached when the puck is *outside* ±$2C, and within it icing is cancelled.
7. **NHL94SNES, routines/logic/puck/chk4shot.asm:** `cmp.w #$2711` ("distance^2 > 100*100?") has no branch after it, so the
   test does nothing (the Genesis branches with `bhi`).
8. **NHL94Genesis, crowd94.asm, Create_HotCold_Table:** the comments say -9 .. 8 ("random -9 ... 8", "sets RNG limit
   (-9 - +8)"); randomd0s with 9 gives -8 .. 8 (-(range-1) .. range-1, as its own comment says).

## Done (where the answers are)

- A SNES flip (2026-10-30): 18 in the recorded games, 864 played in the game (SNES_MECHANICS 6.3).
- Pucks through the goalie's legs (2026-10-19): the user's 2v2 game, three goals (GENESIS_SHOOTING 5.5); one going
  down the screen would still show the bottom net's band.
- SNES dekes and moves (2026-10-25): `2026-10-25_1951_MTL-LA`'s 26 tries replayed in the game (SNES_SHOOTING 4.10).
- The EA Special at the bottom net (2026-10-27): 70 forehand attempts in two 2v2 games, 15 of 40 scored at the top
  net, 4 of 30 at the bottom (SCORING_GENESIS_EA "The best set-ups at 1.7 a frame").
- Long far-post slapshot goals (2026-10-24): skating shots across toward the stick side, 50-62% for a strong shooter
  (SCORING_GENESIS "Moving shooters"); more examples welcome.
- The opponent's iPhone opens game files from the S3 link (2026-10-18).
- Home isn't always the netplay host (2026-10-18): sides are picked in RetroArch (Genesis) or the game (SNES).
- The EA Special's side (2026-10-25): a left-hander from the right, a right-hander from the left, facing across or
  diagonally toward the goalie, never straight up the ice (SCORING_GENESIS_EA "EA Specials").
- The CDL goalie edit (2026-10-25): the studies use what `CDL_Season_12.bin` holds.
- Which ROM the SNES Classic leagues play (2026-10-30): one strength per person over all seasons (LEAGUE_RESULTS
  "Teams with the people taken out").
- Home record by home bonus and shots on goal by period (2026-10-30): LEAGUE_RESULTS.
