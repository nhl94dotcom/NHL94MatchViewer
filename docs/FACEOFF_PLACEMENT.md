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

   | Code | Stoppage | Raw spot |
   |---|---|---|
   | $E | Goal | Centre (0, 0) |
   | 6 (PenOOP) | Puck out of play (over the glass) | Where the **last player to touch the puck** stood (ltx / lty) |
   | $C (PenIcing) | Icing | Puck x, and y +/-600 toward the icing team's own end |
   | everything else | Goalie holding (8), whistle ($A), offside ($10), penalties ($12 and up), period over (2) | Where the **puck** is |

2. **The clamp:** x is held to +/-70. If y is 166 or more (or -166 or less), the spot becomes that end's dot on the
   side of the raw x: (+/-70, +/-206). **Otherwise y is kept as it is.** So any spot short of 166 from centre stays where
   it was, in the neutral zone or in the end zone between the blue line and the hash marks.

3. **limitfo**, for every player in PenBuf (penalties): if the spot is past y 88 toward the end that player attacks
   (his attacking zone), it moves to the neutral dot outside that blue line, (+/-70, +/-65), keeping the side of x.
   Nothing moves a spot into his own end.

Elsewhere: the period starts and goals clear the spot to centre (Genesis `hockey94.asm`, `logic94.asm`), so a spot set
at the end of a period is never used.

**Goalie holding the puck:**
- **Genesis** (`logic94.asm`, checkanim): a hold timer (temp5) runs whenever the goalie has the puck, wherever he is,
  and its whistle (code 8) puts the faceoff at the puck: off the dot if he has skated out past the hash marks.
- **SNES** (`routines/logic/assignments/assgoalie.asm`): a goalie holding the puck more than 187 from his goal line
  (|y| under 187) is whistled at once, otherwise when the hold timer runs out. Code 8 there too, and the same spot rule.
  `routines/collide/checkgoalp.asm` also whistles code 8, for the puck pinned against the net.

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

- **SNES:** the match files' faceoff position (the puck where it was dropped; the SNES game drops it at the spot).
  16 of 368 faceoffs were off the dots:

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

Two choices are open, since the rulebook doesn't settle them:
- **Which end-zone dot a power play gets.** The NHL lets the power-play team choose, and the game has no way to ask.
- **A goalie whistled for holding the puck out in the neutral zone.** The neutral rule gives the nearest neutral dot.
  The out-of-play rule's "least advantage to the offending team" would give the dot on his own side of centre.

Source: [NHL Official Rules 2021-22](https://media.nhl.com/site/asset/public/ext/2021-22/2021-22Rules.pdf) (Rules
67.3, 76.2, 81.2, 85.1).
