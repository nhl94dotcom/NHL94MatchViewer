# Where faceoffs are held (both systems, 2026-11-07)

Findings only, for a fix to be made in NOSE4Web: how the game picks a faceoff spot, where it lands off the nine dots,
and which dot the NHL rules give for each kind of stoppage.

Coordinates are the game's: x across the ice (+ right), y along it (+ the top end), blue lines at y +/-89. The nine
dots are centre (0, 0), the four neutral-zone dots (+/-70, +/-65) and the four end-zone dots (+/-70, +/-206).

## How the game decides

Both games do it the same way, in **Stop4Pen** (Genesis `src/penalty94.asm`; SNES
`src/routines/penalty/penalties/Stop4Pen.asm`). Every stoppage goes through it, a penalty or not: the stoppage is
entered in PenBuf with a code (the Penaltylist number), and Stop4Pen reads that code. The spot is only set when the
clock is not already stopped, so the first stoppage wins.

1. **A raw spot, by the code:**

   Codes 2-$E are the same on both systems. Above that they differ: offside is $10 on the Genesis and $12 on the
   SNES, and the penalties start at $12 (Genesis) and $14 (SNES).

   | Code | Stoppage | Raw spot |
   |---|---|---|
   | $E | Goal | Centre (0, 0) |
   | 6 (PenOOP) | Puck out of play (over the glass) | Where the **last player to touch the puck** stood (ltx / lty) |
   | $C (PenIcing) | Icing | Puck x, and y +/-600 toward the icing team's own end |
   | everything else | Goalie holding (8), whistle ($A), offside, penalties, period over (2) | Where the **puck** is |

2. **The clamp:** x is held to +/-70. If y is 166 or more (or -166 or less), the spot becomes that end's dot on the
   side of the raw x: (+/-70, +/-206). **Otherwise y is kept as it is.** So any spot short of 166 from centre stays where
   it was, in the neutral zone or in the end zone between the blue line and the hash marks.

3. **limitfo**, for every player in PenBuf (penalties): if the spot is past y 88 toward the end that player attacks
   (his attacking zone), it moves to the neutral dot outside that blue line, (+/-70, +/-65), keeping the side of x.
   Nothing moves a spot into his own end. The SNES limitfo is the same, except that it skips entries of type $34 (not
   named in the disassembly).

Elsewhere: the period starts and goals clear the spot to centre (Genesis `hockey94.asm`, `logic94.asm`), so a spot set
at the end of a period is never used.

**Goalie holding the puck:**
- **Genesis** (`logic94.asm`, checkanim): a hold timer (temp5) runs whenever the goalie has the puck, wherever he is,
  and its whistle (code 8) puts the faceoff at the puck: off the dot if he has skated out past the hash marks.
- **SNES** (`routines/logic/assignments/assgoalie.asm`): a goalie holding the puck at |y| under 187 (more than 77 out
  from his goal line at 264) is whistled at once, otherwise when the hold timer runs out. Code 8 there too, and the
  same spot rule.
- **The net knocked off (SNES):** `routines/collide/checkgoalp.asm` also whistles code 8, when a bursting player moves
  the net (1 time in 8, the puck within 128 of it), so that faceoff too is held at the puck.

## Where it goes wrong, in the recorded games

- **Genesis:** the game's own spot (fox / foy, work RAM $FFBF94 / $FFBF96) and the stoppage code (the newest PenBuf
  entry, $FFC3A4), from the recordings in Documents\NHL94 Viewer. Of 222 spots used for a faceoff, 27 (12%) were off
  the dots.

  | Stoppage | Off a dot | On a dot |
  |---|---|---|
  | Penalty called | 20 | 51 |
  | Goalie holding | 1 | 13 |
  | Out of play | 1 | 7 |
  | Other whistle (no new entry) | 5 | 65 |
  | Goal | 0 | 52 |
  | Icing | 0 | 7 |

  Examples:
  - **Penalties:** penalties called in the neutral zone or the offending team's own end are faced off where the puck
    was: (-15, -74), (11, 138), (-22, 102), (28, 139), (-49, -107), (34, 87). The last two of those are in an end
    zone, short of the hash marks.
  - **Goalie holding:** 2026-10-17_2227_BOS-DAL, the goalie holding the puck at (0, 164), 2 short of the 166 that
    would have taken it to a dot: faced off at (0, 164).
  - **Out of play:** 2026-10-18_2208_WPG-BOS, the puck over the glass behind the net at (-41, -292), last touched
    by a player at (-55, -84): faced off at (-55, -84), in the neutral zone. 2026-10-16_1314_BOS-PIT: the puck out at
    (-130, -109) from a player at (-87, 100): faced off at (-70, 100), in the other end, short of the hash marks.

- **SNES:** the match files' faceoff position (the puck where it was dropped; the SNES game drops it at the spot), the
  stoppage told from the match file (a goal or penalty near the whistle, the goalie with the puck, the puck leaving the
  ice), so less exact than the Genesis count. 16 of 368 faceoffs were off the dots:

  | Stoppage | Off a dot |
  |---|---|
  | Penalty called | 7 |
  | Other whistle | 6 |
  | Goalie holding | 1 |
  | Out of play | 1 |

  Each one sat where the puck was at the whistle, x held to +/-70. For example (34, -33), (-21, -27), (-21, 139) and
  (-70, -149) after penalties, and (6, 158) and (21, 86) after other whistles.

## What the rules say (NHL Official Rules 2021-22)

- **Rule 76.2, the nine spots:** "All face-offs must be conducted on one of the nine (9) face-off spots located on the
  rink." And "No face-off shall be made within fifteen feet (15') of the goal or side boards nor anywhere other than
  at a face-off spot."
- **Neutral zone, no one to blame (76.2):** "the ensuing face-off shall be conducted at the nearest face-off spot
  outside the blue line whenever possible": one of the four neutral-zone dots. A tie goes to the home team's
  advantage.
- **End zone (76.2):** "When stoppage occurs between the end face-off spots and near end of the rink, the puck shall be
  faced-off at the end face-off spot on the side where the stoppage occurs." Otherwise, "the puck must be faced-off at
  a face-off spot in the zone nearest to where it was last played."
- **Penalties (76.2):** "the ensuing face-off shall be conducted at one of the two face-off spots in the offending
  team's end zone". There are three exceptions: centre ice after a goal or at the end or start of a period, and the
  neutral zone if the attacking players have entered the zone during a scrum. "The team awarded the power-play will
  have the choice of which end zone dot the face-off will take place at."
- **Puck out of play (85.1):** "it shall be faced-off at the nearest face-off spot in the zone from where it was shot or
  deflected out of play." From the neutral or defending zone, "the nearest face-off spot closest to the origin of the
  shot or deflection that gives the offending team the least amount of territorial advantage."
- **Icing (Rule 81.2):** "Following an icing, the attacking team will have the choice of which end zone dot the
  face-off will take place." That's the icing team's end. The game uses that end, on the side of the puck.
- **Goal:** centre. The game already does this.
- **Goalkeeper holding the puck (67.3):** holding it "longer than three seconds" is a delay-of-game minor. The
  rulebook has no faceoff of its own for a goalkeeper holding the puck out of his zone; it falls under the rules
  above.

So the agreed targets, by stoppage:

| Stoppage | NHL target | The game |
|---|---|---|
| Goal, start of a period | Centre | Right |
| Icing | The icing team's end-zone dot (the other team's choice of side) | Right end; side by the puck |
| Penalty | The offending team's end-zone dot (the power-play team's choice of side) | Where the puck was, or a neutral dot (limitfo): off the dot in 20 of 71 (Genesis) |
| Puck out of play | The nearest dot in the zone the shot came from; from the neutral or defending zone, the one least to the shooting team's advantage | Where the shooter stood, short of the hash marks: off the dot |
| Goalie holding, other whistles in the end zone | That end's dot on the side of the puck | Right past the hash marks; between the blue line and the hash marks off the dot |
| Goalie holding, other whistles in the neutral zone | The nearest neutral-zone dot | Where the puck was: off the dot |

## Decisions for the fix (the user, 2026-11-07)

The two questions the rulebook left open:

1. **After a penalty**, the offending team's end-zone dot on the side of the rink where the puck was when play stopped.
2. **A goalie whistled for holding the puck in the neutral zone:** the nearest neutral-zone dot to where he held it.

How NOSE4Web is building it (the user can overrule any of these):

- **Penalties** (Genesis codes $12-$2A, SNES $14-$2E): the offending team's own end-zone dot, the end read from the
  penalized player's pfgoal flag (as icing does). Codes above those (the delayed-penalty signal, and on the Genesis
  the penalty-shot versions) follow the zone rule.
- **Every other stoppage** (whistle, goalie holding, offside, icing, the SNES net knocked off): past a blue line
  (|y| 89 or more), that end's dot on the puck's side of x; in the neutral zone, the nearest neutral-zone dot.
  Icing's +/-600 still lands in the icing team's end.
- **Puck out of play:** the same zone rule, at the spot of the last player to touch it. In the neutral zone that gives
  the nearest dot, not the rulebook's "least advantage to the offending team".
- **Goal:** centre, as now.
- **Ties:** x = 0 counts as the right-hand side (as the game has it); y = 0 in the neutral zone as the top half.
- **limitfo** still runs afterwards, unchanged, so coincidental penalties to both teams still move to a neutral dot.
- **Where:** Stop4Pen's clamp, between the raw spot and limitfo, is replaced by a call to the new code.

Two codes inside those penalty ranges, both fine:
- **Genesis $14** is PenNoText ("no text"); nothing in the game's code uses it.
- **SNES $24** is PenShot, the penalty shot (a foul from behind on a breakaway: Bcheck, checkcheck, holdcheck). Rule
  24.5 puts a missed penalty shot's faceoff "at either of the end face-off spots in the zone in which the penalty shot
  has been tried", the offending team's end, and a goal's at centre: what the fix gives.

## NOSE4Web's fix, tested in the game (2026-11-07)

`analysis/scoring_map/faceoff_fix_test.py`: from moments of live play, a player is given the puck at a chosen spot, a
PenBuf entry is written with a chosen stoppage code and that player, the game's own penalty check calls Stop4Pen (and
limitfo), and the spot it sets is read. 48 spots (x +/-40, +/-100; y from -250 to 250), skaters of both teams (both
attacking directions), 11 stoppage codes (out of play, goalie holding, whistle, icing, goal, offside, three to four
penalties, the "no text" and penalty-shot codes), on several moments. Each ROM against its own rule, limitfo included:

| ROM | Rule | Agree | Differ |
|---|---|---|---|
| nhl94.bin (Genesis retail) | Original | 8,364 | 8 |
| nhl94_faceoff_fix.bin | Fixed | 8,372 | 0 (and 8,372 / 0 rebuilt, reading the newest PenBuf entry) |
| NHL94.smc (SNES retail) | Original | 4,152 | 72 |
| NHL94_faceoff_fix.smc | Fixed | 4,212 | 12 (the same rebuilt) |
| nhl94_2026.sfc (SNES 2 MB, SA-1) | Original | 2,112 | 0 |
| nhl94_2026_faceoff_fix.sfc | Fixed | 2,112 | 0 (the same rebuilt) |

- The originals agreeing shows the test reads the game right; their differences are a carrier skating on (the
  original's off-dot spot follows him, up to 8 units; 6 are allowed).
- The fixed ROMs put every faceoff on the dot the decisions give. The SNES fix's 12 differences are moments where the
  puck was still sliding across centre when the call came: the original ROM's spot there reads y -1, so the puck was
  just below centre, and the fix's neutral dot on that side (-65) is right; the test's reading of the puck a frame
  earlier was not.
- The third build (Genesis $14 and SNES $16, the injury stoppage, on the zone rule): Genesis 8,372 / 0, SNES 2026
  SA-1 2,112 / 0, SNES retail 4,208 / 16; the 16 are the same two puck-across-centre placements, now also with $16.
- Not tested: the FallDown and puckfaceoff entries into Stop4Pen (below), and a faceoff after a penalty shot.

## NOSE4Web's four questions, from the code

1. **Codes $14 (Genesis), $16 and $24 (SNES).**
   - **Genesis $14 and SNES $16 are the injury stoppage without a penalty** (an earlier answer here said they were
     never used: FallDown writes them as numbers, #$14 and #$0016, not by name). A hit that injures (Genesis: the
     carrier knocked into a fall back, facing straight up or down the ice, the impact over a random 0-159; the SNES
     much the same) stops play with $14 / $16 when penalties are off or the hitter is a goalie; with penalties on and a
     skater hitting, it is roughing instead ($12 Genesis, $14 SNES), called straight away (FallDown -> AddPenalty2 ->
     Stop4Pen). In the Genesis recordings: 9 roughing calls from hits, 4 injury stoppages with $14. So $14 (Genesis)
     and $16 (SNES) are not penalties: Rule 76.2 puts an injury stoppage at the nearest spot in the zone of the puck,
     the ordinary zone rule. As built, the fix sends 3 of the 4 recorded $14 stoppages to the hitter's own end instead
     (for example the puck at (64, -76): built (70, -206), the zone rule (70, -65)).
   - **SNES $24 (PenShot)** is entered by Bcheck, checkcheck and holdcheck through AddPenalty, on the hitter (the
     offender), like any penalty, and AddPenalty lets it through even with penalties off. A penalty; its end is right by
     Rule 24.5.
   - **Roughing from a hit, with the fix as rebuilt** (the newest PenBuf entry, not a0): all 9 recorded Genesis cases
     go to the hitter's own end on the puck's side, as a penalty should (the original game left 5 of them off the
     dots). Not played in the game: no injury came of 450 hits played from the recorded check moments.
2. **Stop4Pen with a0 not at the entry: yes, on both systems.**
   - FallDown (Genesis collide94.asm, SNES FallDown.asm) calls AddPenalty2 (roughing, $12 Genesis / $14 SNES) and then
     goes straight into Stop4Pen. AddPenalty2 writes the entry through a1 and keeps a0, so Stop4Pen's -2(a0) and -1(a0)
     are not that entry. On the SNES, a0 there is the hitter's team offset (0 or 2), a direct-page value.
   - The Genesis also enters Stop4Pen from puckfaceoff (logic94.asm, twice) when a delayed penalty is pending
     (gmpendel), and the SNES from puckfaceoff (puckfaceoff.asm), with whatever a0 held.
   - The original game is just as exposed (its raw spot depends on the code it reads), but the fix reads the
     offender's pfgoal from -1(a0) as well, so on these paths it can pick an end from the wrong player.
   - **puckfaceoff with a delayed penalty pending (gmpendel):** it runs after the stoppage, with the clock already
     stopped, and Stop4Pen keeps the spot when the clock is stopped (bset / tsb gmclock, then .skipfo / .6), so a0 is
     not read for the spot there: the penalty is called (gmpen, the whistle, the referee) and the faceoff stays where
     the other stoppage put it. In the Genesis recordings, spots changed with the clock already stopped 68 times: 60
     clears to centre at a period's start, 2 netplay rollback reads, the period's end, and one not explained.
3. **SNES type $34.** Nothing in the code writes $34 into PenBuf that could be found. Every loop over PenBuf skips it
   (checkfornewpen, chkprogress, AddPenalty2's search for a free slot, limitfo), so it works as a reserved entry, and
   checkfornewpen never hands one to Stop4Pen. Treating it as a non-penalty is fine.
4. **The faceoff after a penalty shot.** SNES: StartPenaltyShot saves fox / foy (psfoxsave, psfoysave) and zeroes
   them; EndPenaltyShotPlay puts them back. So the faceoff after a missed penalty shot is held at the spot Stop4Pen set
   when the penalty-shot foul ($24) was called: the offending team's end with the fix, as Rule 24.5 wants. Genesis:
   no such save; fox / foy are cleared to centre only when sflags8 bit 0 is set (logic94.asm), so the faceoff after a
   penalty shot appears to keep the foul's spot too. The penalty-shot versions of the Genesis penalties ($2E-$3C) are
   above the fix's range and follow the zone rule; the foul usually comes near the offending team's net, so that
   mostly gives their end-zone dot as well. Not tested in the game.
5. **Other stoppages while a delayed penalty is pending.** In the Genesis recordings (the delayed flag and the
   stoppage code from each whistle): 32 stoppages came with a penalty pending; 29 were the penalty being called, 2 were
   goals (centre either way), 1 was another whistle. So the case where the NHL would still put the faceoff in the
   offending team's end and the fix uses the zone rule came up once. No exact SNES count: the SNES match files' delayed
   flag also marks penalty shots.

Source: [NHL Official Rules 2021-22](https://media.nhl.com/site/asset/public/ext/2021-22/2021-22Rules.pdf) (Rules
24.5, 67.3, 76.2, 81.2, 85.1).
