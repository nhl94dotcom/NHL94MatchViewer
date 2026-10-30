# NHL '94 Game Mechanics: Super Nintendo (SNES)

What NHL '94 on the Super Nintendo actually does under the hood: how ratings work, how saves and checks are decided,
how penalties are called, what the computer players think, and the bugs that shape online play. It covers the
original `NHL94.smc`, NHL94_Classic and the league ROMs built on them (the SDL ROMs). Every finding comes from reading
the game's own code and is marked with what supports it:

- **Confirmed**: the code says so *and* recorded games show it, with the numbers given.
- **Code**: read from the code, not (yet) seen in a recording.
- **Not read yet**: parts of the SNES code nobody has gone through for this document. The Genesis game often has an
  answer ([GENESIS_MECHANICS.md](GENESIS_MECHANICS.md)), but the two games differ often enough that it isn't assumed
  here.

For what all this means when you play, without the code, see the [SNES player's guide](SNES_GUIDE.md).

Distances are game units, **about 3 to a foot** (divide by 3 for feet); the rink's landmarks, common distances and
speeds in feet and mph are in [Units](#units) in the appendix.

**Buttons** (from the game's input code, `doinput`):

| Button | With the puck | Without the puck |
|---|---|---|
| **B** | Pass | Poke check / switch player |
| **A** | Shoot (hold for a slapshot) | Speed burst / body check; one-timer while a pass is on its way to a teammate |
| **Y** | Flip (a dump-in) | Hook / hold |
| **X** | | Take the goalie |
| **L / R** | | Take the left / right defenceman |
| **Select** | Line change | Line change |

*Sections 4 (Shooting) and 5 (Goaltending) are in [SNES_SHOOTING.md](SNES_SHOOTING.md). The section numbers are shared, so a reference such as 5.3 is there.*

## In brief

One line per chapter: the main finding, then the section with the evidence.

1. **Ratings**: a negative ("cold") hot / cold byte maxes the rating (an unsigned-shift bug): about 46% of all ratings, every game; the hidden bonuses are the Genesis ones, the third-period one backwards here too. ([2](#2-ratings-what-the-game-really-uses))
2. **Skating**: Speed and energy set top speed; most skaters skate at full Speed because of the bug. ([3](#3-skating))
3. **Shooting**: the stick's screen direction picks the aim point (Up is always high); the same perfect-shot roll as the Genesis; long slapshots rarely score; one-timers follow the d-pad. Played in the real game, a set goalie stops nearly every shot from a standstill, except a slapshot from just left of centre (the shooter's left) aimed at that side: about half go in (4.8). ([4](SNES_SHOOTING.md#4-shooting))
4. **Goaltending**: a body box plus areas from each save frame; a person's held save button adds an area to one side; the computer goalie's hold rule; the net ignores a puck the goalie holds; posts are a 5-unit band. ([5](SNES_SHOOTING.md#5-goaltending))
5. **Passing**: speed comes from the distance (so no rocket pass); the receiver is the nearest teammate in a 90-degree cone; the flip is a computer dump-in; a stick can't play the puck while its no-touch timer runs. ([6](#6-passing-the-flip-and-stickhandling))
6. **Checking**: no weight bug and no CB trick (everyone uses the same formula); no same-pair rule, so a second hit after a wobble knocks him down. ([7](#7-checking-hooking-poking-and-collisions))
7. **Penalties**: a person's skater is called half as often as the computer's; cold (maxed) Aggression takes the penalties; no delayed-penalty immunity; anyone can be called for interference. ([8](#8-penalties))
8. **Faceoffs**: pure timing, as on the Genesis; confirmed on 70 draws. ([9](#9-faceoffs))
9. **Penalty shots**: a net knocked off during one gives a retake from the side dot; breakaways and injuries. ([10](#10-penalty-shots))
10. **Offsides**: off in the leagues; when on, one-timers can be offside. ([11](#11-offsides))
11. **The computer players**: they switch to defence the moment possession changes (no awareness delay) and roll to check twice a frame (hit-happy). ([12](#12-the-computer-players))
12. **Energy and the crowd**: with line changes off nothing drains energy. ([13](#13-energy-and-the-crowd))
13. **The ROMs**: what NHL94_Classic and the SDL ROMs change. ([14](#14-the-roms))

---

## Contents

1. [How this was found](#1-how-this-was-found)
2. [Ratings: what the game really uses](#2-ratings-what-the-game-really-uses)
3. [Skating](#3-skating)
4. [Shooting](SNES_SHOOTING.md#4-shooting)
5. [Goaltending](SNES_SHOOTING.md#5-goaltending)
6. [Passing, the flip and stickhandling](#6-passing-the-flip-and-stickhandling)
7. [Checking, hooking, poking and collisions](#7-checking-hooking-poking-and-collisions)
8. [Penalties](#8-penalties)
9. [Faceoffs](#9-faceoffs)
10. [Penalty shots](#10-penalty-shots)
11. [Offsides](#11-offsides)
12. [The computer players](#12-the-computer-players)
13. [Energy and the crowd](#13-energy-and-the-crowd)
14. [The ROMs](#14-the-roms)
15. [Quick reference: bugs and exploits](#15-quick-reference-bugs-and-exploits)
16. [Open questions and parts not read yet](#16-open-questions-and-parts-not-read-yet)
17. [Appendix: units, addresses and sources](#17-appendix-units-addresses-and-sources)

---

## 1. How this was found

The game has been disassembled by the community into source code that rebuilds `NHL94.smc` byte for byte:
[abdulahmad/NHL94SNES](https://github.com/abdulahmad/NHL94SNES).

The NHL '94 Viewer's helper records the game's memory about 60 times a second while you play in RetroArch (the Snes9x
core). That gives every player's position, speed, animation and *working* ratings, so the code's rules can be checked
against real games. The first checks used four recorded SNES games (online, NHL94_Classic and SDL16) and several hundred save states;
later ones more games, as each says. Numbers like "11 of 14" are counts from the games available at the time.

Routine and variable names in `code style` are the disassembly's names. The rating arrays are `checking` ($1483),
`aggress` ($1443, a skater's **Aggression**; `GGSleft` is its goalie name) and `fighting` ($1463). Copies of the
disassembly from before 21 October 2026 called the Checking array `aggress` and the Aggression array `GGSleft`.

---

## 2. Ratings: what the game really uses

### 2.1 Working ratings

The ratings stored in the ROM are steps from 0 to 6 (the game's screens show them as numbers from 25 to 100, see 2.5).
Each time a player comes on the ice (faceoffs, line changes), `setplayer` turns each one into a **working rating** from
0 to 15: **(step x 5) / 2 + hot / cold + bonuses**, at most 15. Without hot / cold or bonuses the steps play as 0, 2, 5,
7, 10, 12 and 15.

Because ratings are only worked out when a player is put on the ice, bonuses that depend on the clock or the score
follow **the situation at the last faceoff or change**. **Confirmed** (CHI-TOR: a third period with no stoppage kept the
comeback bonus (2.3) the whole period).

### 2.2 Hot and cold: "cold" means maxed

Before each game the game rolls random "hot / cold" values for every player (`Create_HotCold_Table`). **Confirmed**:

- Each player gets 12 random values from -12 to +12, one per rating, fixed for the game.
- A positive value adds a quarter of itself (0 to +3) to that rating.
- **Bug:** the value is shifted with an unsigned shift, and the step that should restore the minus sign tests the
  wrong bit (`bit #$00`), so it never fires. A negative ("cold") value turns into a big positive one, and **that rating
  goes to the maximum, 15.**
- About **46% of every player's ratings are maxed in every game**, whatever his real rating.
- Checked in all three SNES games where it was tested (NHL94_Classic and SDL16). Effects seen elsewhere in this
  document: more than half of all skaters skate at maximum speed; most penalties are taken by players at maximum
  Aggression; many shooters have maximum Shot Accuracy.
- A loud crowd does **not** change the hot / cold values. The code that would raise four of each player's values by 2
  at 110 dB (`ShowCrowdMeter` `.11`) is never called; only the undo (`LowerHotColdTable`, at under 105 dB) is, and it
  does nothing while `HotColdRaised` ($19CE) is 0. **Confirmed**: 0 all through 15 recorded games, meters up to 128 dB.

**Bottom line:** the bug flattens the ratings. A player's real ratings matter far less than on the Genesis, and which
of them are maxed changes every game.

The NHL '94 Viewer shows which of a player's ratings the bug maxed on his player card ("Hot / cold (as played)"), read
from the game's memory during the recorded game.

### 2.3 Hidden bonuses

Added to working ratings when a player comes on the ice.

| Bonus | Who | Ratings | Notes |
|---|---|---|---|
| Home / away | per team, set in the ROM | Offensive and Defensive Awareness, Stickhandling, Shot Accuracy, Passing | Home team adds its home value, away team subtracts its away value (Shot Accuracy +1 / +2 at home, -1 away in the games checked). **Confirmed** |
| Power play | team on the power play, per-team ROM value | Offensive Awareness, Stickhandling, Shot Accuracy, Passing | **Confirmed** |
| Penalty kill | team killing a penalty | minus to the same | **Code** |
| Comeback | team tied or trailing in the third period, both teams in overtime | +2 Offensive Awareness, +2 Checking, +4 pass/shoot bias | **Bugged**, see below |

The power play and penalty kill halves of the team byte are read swapped, as on the Genesis (GENESIS_MECHANICS 2.3):
the power play adds the half meant as the penalty-kill deficit, and the penalty kill takes off the half meant as the
power-play bonus. The NOSE4Web editor's fix swaps them back on the SNES too. **Code**

**The comeback bonus is backwards** (**Confirmed**). The test that should switch it on for the last half of the third
period is the wrong way round, so it is **on while more than half of the third period is left** (with 5-minute
periods, before 2:30) **and off for the last half**. In overtime both teams have it throughout.

### 2.4 What each rating does

Working values 0-15. Every place found where the code reads each rating:

| Rating | What it does |
|---|---|
| **Weight** | Acceleration (each Weight point costs 2/3 of an Agility point); checks; momentum in collisions. **No weight bug** |
| **Agility** | Acceleration and stopping; goalies: how fast they skate to loose pucks (see 3.2 for goalies) |
| **Speed** | Top speed (scaled down by fatigue, only with line changes on) |
| **Offensive Awareness** | Reaction time of computer players in some jobs (12.1) |
| **Defensive Awareness** | Reaction time of computer players in other jobs (a bigger effect than Offensive); delays a goalie's rethink after each pass |
| **Shot Power** | Shot speed: (Shot Power x energy + 20) x wind-up. **No wind-up cut-off**: anyone can take a full slapshot. Goalies: Puck Control |
| **Shot Accuracy** | The chance a shot goes exactly where aimed, and how far it scatters if not |
| **Passing** | How steady a pass's speed is (6.1) **and the flip's accuracy** (6.3) |
| **Stickhandling** | Steals, catching passes, and wobbling instead of falling when hit (12+) |
| **Checking** (array `checking`) | Knockdowns; the upend fall; **how often computer skaters go for a hit** (12.3) |
| **Endurance** | Energy, which only matters with line changes on |
| **Pass / shoot bias** | Whether a **computer** puck carrier shoots or passes (`chk4shot`, `chk4pass`) |
| **Aggression** (array `aggress`) | Penalty odds, with an overflow bug (8.1) |
| **Fighting** | **Never read** |
| **Goalie glove / stick save ratings** | **Nothing.** They are looked up and then overwritten before use |

### 2.5 The numbers on the ratings screens


![Which numbers on the SNES ratings screen mean a maxed rating in play](img/snes_hot_cold.svg)

The game's screens (Edit Lines and the rosters) show each rating as a number (`CalcAttrib`): n = 18 x the step (0-6) +
3/4 of that rating's hot / cold value (so -9 to +9), at least 0, at most 100; **under 50 it is squashed to n / 2 + 25**.
The hot / cold value shown is exactly the one that plays (the screen reads the same table, rating for rating).

| Step | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Numbers shown | 25-29 | 29-38 | 38-47 | 47-63 | 63-81 | 81-99 | 99-100 |
| Band's middle (no hot / cold) | 25 | 34 | 43 | 54 | 72 | 90 | |
| Working value at the middle | 0 | 2 | 5 | 7 | 10 | 12 | 15 |

**Because "cold" means maxed, read the screen backwards:**

- A number **below its band's middle** means that rating is **maxed in play (15)**, whatever the step: a Speed of 66
  plays like a Speed of 100.
- **At the middle**, maxed one time in three.
- **Above the middle**, the step's value plus 0 to 3.
- Numbers on the edge between two bands (29, 38, 47, 63, 81) can't be told apart from the screen.

**Confirmed** with screenshots of Edit Lines taken during a recorded game (Calgary's forwards, every column): all 99
rating numbers matched the formula exactly, and so did the weights. In play, every rating whose number was below its
band's middle was maxed (46 of 46), none above the middle was (31), and 5 of the 22 at the middle were (the code says
one in three). The seven ratings the recording holds in working form (Agility, Speed, Shot Power, Shot Accuracy,
Endurance, Aggression, Checking) played exactly at the predicted values in all 3,450 samples each.

---

## 3. Skating

### 3.1 Top speed

Cap = (20 + Speed) x 261 in the game's speed units, Speed on 0-15, scaled by energy (0.5 + energy / 2; full with line
changes off). **Confirmed**: each skater's normal cruising speed sat just under his cap, from 6,919 at Speed 7 (cap
7,047) to 8,901 at 15 (cap 9,135). **32 of 61 skaters were at the maximum working Speed of 15** (the hot / cold bug),
so speed ratings barely separate players: most of the ice skates at full speed.

### 3.2 Acceleration

- Speed grows by 32 - Weight + 1.5 x Agility (working values) each frame you push. **Code**
- No half-acceleration rule for a person's puck carrier was found (the Genesis has one).
- **Goalies:** a person's goalie without the puck gets 2 x Agility + 8 more; a computer goalie (or one with the puck)
  only + 8, and a computer goalie **loses 1 x Agility of his 1.5 while a pass is in the air**, so he slides across
  slowly on passes. A person's goalie inside his crease skates at three-quarters of his top speed. **Code**

### 3.3 No runaway speed

The Genesis can leave a skater's "deceleration off" switch on, so his speed bursts stack up to twice top speed
(GENESIS_MECHANICS 3.4). The SNES has the same switch: `updateplayers` slows each skater by a friction byte from table
.21 ($FD, $FA, $F7 ... by the frame step) normally and from .22 ($FF, $FF, $FE ...: about a sixth as much friction)
while pflags bit 0 is set, and above top speed `playeracc` adds nothing but takes nothing off either, so bursts could
stack the same way. But the switch is **turned off reliably**: only `asspassrec` sets it (on the receiver of a pass),
and it is cleared when his wait for the pass ends (`asspassrec` .6: anyone has the puck, or the wait runs out), when
**any stick touches the puck** (`puckstick`, which clears it for that player first thing), by `assnearest` and at
faceoffs (`resetplstuff`). `FallDown` never sets it, so the Genesis's boards-fall route doesn't exist. **Code**

**Confirmed** (analysis/snes_runaway_study.py; 15 SNES games as of 2026-10-21, eight at first): 1,683 stretches with
the switch on, a median 0.3 s, 90% under 0.6 s, the longest 2.9 s; the fastest skater with it on went 11,553, for 0.6 s
(a person's, 2026-10-19_2246_TOR-NYI; before that 10,156; top speed is about 9,000), against 19,400-20,100 in the
Genesis runaways.

---

## 6. Passing, the flip and stickhandling

### 6.1 Passing

- **A pass to a teammate gets its speed from the distance** to where he will be (`dopass`): 64 (x 256 = 16,384) up to
  about 96 units (32 feet), two-thirds of the distance in between, 80 (20,480) from 120 units (40 feet) on. **Passing
  only makes it steadier**: a random +/-(16 - Passing) x 256 is added, about +/-4,000 for a poor passer, almost nothing
  for a good one. (`dopass` first sets the speed to 144 + 4 x Passing, but a targeted pass replaces it and a pass with no
target never reads it.) **Code** Because the speed comes from the
  distance, the SNES has no "rocket pass": on the Genesis the speed comes from a meeting time rounded down to an eighth
  of a second, which can double it (GENESIS_MECHANICS 6.1).
- **The direction** (`setpassmode`, `passmode`): pressing B sets it to the way the passer faces. If the d-pad is held
  (or pressed while B is down) the pass goes **at once** in that direction; otherwise it goes when B is released, the
  way he faces. A goalie behind his net is the exception (no direction set).
- **The receiver** (`dopass`): of the passer's five teammates, **never the goalie** and nobody off the ice, only those
  in the pass direction or 45 degrees either side of it count. Each is scored by (distance squared) / 4, plus 4,096 for
  one 45 degrees off (like being 128 units farther, close in), and the lowest score gets the pass. The Genesis rule is
  the same idea (GENESIS_MECHANICS 6.1). **Confirmed** on 594 completed SNES passes: 96% of receivers were within one
  45-degree step of the pass direction, 83% exactly the rule's pick (the rest mostly a teammate other than the one aimed
  at taking it, or the samples' timing).
- **The aim:** the receiver's stick blade (the hot spot of his one-timer pose for the way he faces), where it will be
  if he keeps skating: 24 frames ahead (0.4 s), or distance / 4 frames for a short pass, distance / 5 for a long one.
  A small lift grows with the distance (vertical speed = distance x 8). **Confirmed:** in the recordings the median
  pass peaked at 0.2 units high within 50 units, 1.4 at 100-149, 3.3 at 200-249 (a stick plays a puck up to 5); 9-16% of
  passes went above 5 at most distances. The Genesis lifts targeted passes by their flight time and more (GENESIS_MECHANICS
  6.1), so long Genesis passes clear sticks far more often. The receiver gets the "receive a pass" job, a
  person's team switches control to him, the passer can't touch the puck for the lead time, and the opposing computer
  goalie's next rethink is delayed (6.1's goalie note, 5.3).
- **Pass shots** happen: a B pass with nobody in that cone flies off the way you pressed at 2 x 80 (x 256) along the
  8-way direction plus half the passer's own speed, **lifted at random up to about 21 units high**, so it can sail over
  the goalie or the net (one scored in the recordings).

### 6.2 Catching and bobbles

A skater's stick takes a loose puck when it is slower than **13,000 + 700 x his Stick Handling**; a faster one bounces
off his stick (`puckstick`): a bobble. So he catches anything under 13,000 at Stick Handling 0 and 23,500 at 15.
**Code** (the routine adds 3,000 when "the object's position" is the goalie's or it is the pass's receiver, but the
object it looks at is the puck, whose position reads 0, so every stick gets the 3,000.)

What that means: a **long pass** (up to 20,480, more with a poor passer's random extra) to a **low-Stick Handling**
receiver can bob off his stick; a **short pass** (16,384) almost never does. The game keeps no memory of a bobble: the
user noticed that the same player never seems to bobble twice running, and that's because the pass back to him usually
comes from a teammate who just picked up the loose puck close by, a short, slow pass. A long pass back would bobble
again. In one recorded game the user reviewed, ten passes bounced off the receiver's stick.

**Who can take a loose puck at all** (`checkpuckcoll`, `checkpuckcoll_ccx`; the Genesis rules are in GENESIS_MECHANICS
6.2). In order, a player's stick is skipped when:

1. **His no-touch timer runs** (`nopuck`, a word per object, counted down by the frames each update takes). It is set
   when he:

   | Event | Frames (60 a second) |
   |---|---|
   | shoots (`doshot`) or makes an untargeted pass (`dopass`) | 16 |
   | makes a targeted pass | the pass's lead time (up to about 24) |
   | swings a one-timer (`asspassrec`) | 10 |
   | flips it (`assdumpin`, the Y button) | 30 |
   | loses it to a steal, and the stealer too (`puckstick`) | 20 + Stick Handling (energy-scaled) |
   | knocks a too-fast puck off his stick, or it bounces off his body, or the net takes it off his stick | 8 |
   | carries it into the goalie (`puckgoalie`; the goalie gets 10) | 20 |
   | falls (`FallDown`) | 120 |
   | lines up for a faceoff (`assfaceoffpl`) | 20 |
   | heads to the penalty box, or glides back out of a breakaway play | 60 |
   | celebrates a goal (`assscore`) | 1,800 |

2. **The game doesn't reach him**: it tests only players whose body is within 40 of the puck up or down the screen
   (the Genesis: 22). A stick reaches about 20 in front, so on the SNES this never cut anyone off in the recordings.
3. **The puck is at height 5 or more, or still rising** (`puckvz` $100 or more): only bodies then.
4. **It's out of reach**: the blade more than 14 from it (7 while the puck's own timer runs, right after a deflection).
5. **It's too fast**: over 13,000 + 700 x Stick Handling (13,000 flat while the shot flag stands); it deflects.

**Confirmed** on every moment a skater's blade came within 14 of a loose puck in seven SNES games
(`analysis/snes_pickup_study.py`): with nothing in the way he took it 924 times in 1,023 (90%; the rest mostly at the
edge of reach between samples); with his timer running 21 in 1,208 (2%, the timer running out between samples), the
puck too high 0 in 80, too fast 0 in 21 (19 deflected), still rising 16 in 366. Most timer misses were the passer just
after his pass, then shooters, centres at a faceoff and fallen players.

### 6.3 The flip (Y with the puck): a computer-run dump-in

![Where the SNES flip goes](img/snes_flip.svg)

Pressing Y hands your skater to the computer's dump-in routine (`assdumpin`, `DumpInTarget`). **Code, confirmed in the
game and seen in the recordings** (below).

- **Outside the attacking zone:** the outside of the attacking faceoff circle, a little above the dot (80 from the
  middle, 180 toward the goal: 84 out from the goal line), **on whichever side of centre you're on**. Facing doesn't
  choose.
- **Inside the zone:** in front of the net.
- **A goalie:** about the middle of the ice, moved by his facing.
- He **first turns to face up the ice** (within 45 degrees), so it comes out late if he was facing sideways.
- **It scatters by up to +/-(20-25 + 2 x (15 - Passing)) across and +/-(20-70 + 2 x (15 - Passing)) along** (the
  slot target 20 and 20, the others 25 and 70: `assdumpin` `.6` / `.7`), so **Passing is flip accuracy**.
- A computer carrier inside the attacking zone shoots instead.
- **Played in the game** (2026-10-30, `analysis/scoring_map/snes_flip_run.py`: 864 flips from six spots, Passing 4, 10
  and 15, both nets, from a standing start facing up the ice): every flip leaves at once, peaks at about 27 units and
  first comes down 1.6 s later (the speed cap of `assdumpin`, $60, keeps long flips short). From the carrier's own zone
  (150 from centre) the median landing is 104-127 up the ice on his side (the target is 180), from centre 130-148;
  then it slides on deep. From inside the zone (150 up, 40 across) it lands 226-237 up, **about 30 across on the far
  side** (target 0, 215). Passing narrows the spread: across, 80 units of range at Passing 4, 40 at 15.
- **Recorded** (`analysis/snes_flip_study.py`; the converter keeps them as `flips`, apart from the passes they go out
  through): 18 flips in 17 SNES games, 16 by people (10 by goalies, whose flips came down near centre ice when they
  defended the top net, 1-1.8 s on) and 2 by the computer (one of the people's is a rimmed pass behind the net, which a
  boards bounce makes look the same). The flipping team had the puck next 9 times, the other team 9.

### 6.4 Steals

`puckstick`, when a defender's stick blade is within about 6 units of a carried puck (squared distance under 37).
**Code.**

- **The roll, every frame in reach:** he knocks the puck loose when randoma(36 + the carrier's Stick Handling - his Stick
  Handling) comes under 3, both adjusted for energy. So about 1 frame in 12 at equal ratings, 1 in 17 for a Stick
  Handling 15 carrier against a 0, 1 in 7 the other way round.
- **A defending goalie always steals**; nobody steals from a goalie carrying the puck.
- **A steal knocks the puck loose in a random direction** (it doesn't hand it over), and neither player can touch it
  for 20 frames plus his Stick Handling.
- **Unlike the Genesis there's no slot rule** (there, a carrier in the slot is easier to rob: a wider reach and a better
  roll).

---

## 7. Checking, hooking, poking and collisions

### 7.1 How a check lands (`checkcheck`)

- A speed burst (A without the puck) into an opponent can knock him down.
- **Impact** = how fast the two players are closing along the line between them; a check needs **impact 32+**.
- Base **120 for everyone** (a person and the computer alike), and the sum uses 16 bits: **no weight bug, and nothing
  to gain from switching away before contact** (the Genesis "CB check").
- A roll against the checker's working Checking decides.
- **Goalies can't be knocked down.**
- **Confirmed** (327 lunges into contact): heavier checkers knocked their man down 50% of the time, lighter ones 39%;
  people 50%, the computer 39%.

### 7.2 Wobbles and repeated hits

- **Wobble (stumble)** instead of a fall: needs working **Stickhandling 12+** (of 15), which the hot / cold bug gives
  every "cold" player, and an impact under a random 10-25. **The wobble keeps the puck.**
- **A second contact within a second of a wobble is always a fall**: no second wobble is allowed, and the wobble
  animation is shorter than the wait. **Confirmed** (CHI-TOR P3 4:18: Roenick wobbled, then fell 0.9 s later).
- There is **no "same checker, same target" rule**: you can knock the same man down again straight away (the Genesis
  ignores it).
- **Which way he falls** (`FallDown`, for a fall in open ice; near the boards it's a boards fall, 7.4): **backward**
  when the hitter is within one direction step (45 degrees) of where he faces, a hit from the front; otherwise
  **forward**, unless he is skating **straight up or down the ice** (facing exactly up or down the screen) and the
  hitter's working **Checking is 10 or more** (of 15): then he's **upended** (`SPAflip`, $F6C0). Nothing else matters:
  not the impact, not his weight. The Genesis needs Checking 20+ (of its larger scale, 7.4 there).
- **Confirmed** (analysis/snes_upend_study.py, 15 games, 788 falls with an opponent skater beside him, taken as the
  hitter): the rule gives the right fall for 714 (91%); 95 were upends (12%), 88 of them with the victim facing straight
  up or down and the hitter at Checking 10+. Most misses are where the nearest skater wasn't the hitter, or a facing
  that changed on the frame of the hit.

### 7.3 Hooks, holds and pokes

**B without the puck: poke or switch?** (`doinput`, and the choosing routine the disassembly files as `findpc`.)
Different from the Genesis:

- **When:** on the **press** of B, locked in an animation or not.
- **Always a poke** when the puck is carried, your skater isn't locked, and he's within about 20 units of the puck
  (`puckdist2`, (dx^2 + dy^2) / 4, under 100).
- **Otherwise the choice:** among your team's skaters on the ice (goalies and the other controller's skater left out;
  locked ones only while skating or in a check / burst animation), the lowest of **distance to the puck itself** (no
  look-ahead) plus, while the puck is carried, **32 for each 45 degrees** beyond the first that the direction to the
  puck turns away from straight up-ice (toward the goal he attacks): a skater with the puck in front of him, between it
  and his own net, is preferred. Your own skater is included: if he's chosen he pokes (if not locked; locked, nothing);
  otherwise control switches. Locked skaters (down, hooking, holding) are never chosen, his own current one included,
  so B while your skater is down always switches; skaters turning or in a check animation can be.
- **With a loose puck** there is no direction term and no "close" rule: the skater nearest the puck gets control, and if
  he's already yours he pokes, at nothing.
- **Checked** (analysis/snes_hook_poke_study.py, 15 games, 1,682 B presses without the puck and not within 0.5 s of
  another): the rule predicts 78% (switch 910 of 946 right; the preferred direction is the puck up-ice of him: 72% the
  other way round). Most misses are a predicted poke that didn't come, or the reverse, with the skater turning or
  gliding (animations $EBB0, $EBE2, $EAFE): the game's own distance figure (`puckdist`) and lock state aren't in the
  recordings.

- **Y without the puck** (`Holdplayer`, `Acheck`): picks the nearest opponent in front (distance + 16 for each 45
  degrees he is off your facing) and starts a **hook** (`SPAhook`, $F864), or a **hold** (`SPAHold`, $F374) when he faces
  you (roughly face to face). Not as a goalie, nor while locked in anything but a speed burst.
- **When it connects** (`holdcheck`, from the collision code; the target within 45 degrees of where you face and not
  locked): **both players' speeds are averaged** (the carrier slows to your pace), he flails (`SPAflail`, $F46A) and
  **keeps the puck** (a shot wind-up is cancelled), you go into `SPAhook2` / `SPAHold2`; then a hooking / holding roll,
  or a penalty shot if he was on a breakaway.
- **Recorded** (15 games): 594 hooks started (58 by people, 536 by the computer), 107 caught someone; 344 holds (37 /
  307), 136 caught someone: the hold, used face to face, connects far more often. On the carrier: hooks 27 (he kept the
  puck 1.5 s in 14, the hooking team got it in 12; his speed 56 -> 48 units/s), holds 46 (23 kept, 18 won; 73 -> 47).
- **The get-up glitch** (known in the community: a knocked-down player gets up at once if his person presses the hook
  button). The SNES input code checks the hook button **before** the animation lock that holds a falling player down,
  and `holdplayer` refuses only during a speed burst, so the hook animation replaces the fall and he is back up. The
  Genesis checks the lock first, so it can't happen there. **Confirmed**: three times in the recordings a person pressed
  Y while down and was up and hooking 0.5-1.2 s later, where falls otherwise last 2.3 s. In the recordings a get-up
  shows as a hook starting the very sample after a fall or upend (a real hook never follows one that closely); the
  converter counts these apart as `getUps` and leaves them out of `hooks` (2026-10-25). In the user's 4-game TOR-NYI
  set (2026-10-25) one person used it 30 times (their skater down 1.35 s a fall on average), the other never (2.2 s).
- **The poke** (`SPAsweepchk`, $F208) takes the puck only through the stick-steal roll (6.4). Its body touching a
  skater within 45 degrees in front (`Bcheck`): **with penalties on, or poked by a computer skater, he always goes down**
  (a fall or a wobble), with a tripping roll; **a person's poke with penalties off** trips him only when randoma8(16 +
  your Checking - his Agility) is 12 or more.
- **Recorded:** people poked 874 times, 403 from more than 30 away (out of reach); of the 471 in reach, 85 tripped someone
  and 141 won the puck. The computer poked 364 times, 340 out of reach.
- **X** takes your goalie when the team's manual goalie option is on; a goalie you control pokes with X (`SPAgpoke`).
  **L / R** take the defenceman on the left / right of the screen when defence control is on (`PadTakeLeftDefense`,
  `PadTakeRightDefense`). **Select** opens the line-change box.

### 7.4 Skaters and goalies colliding

- **A goalie is never knocked down.** Only the skater can go down.
- **Skater with the puck:** **any touch** sends him to the knockdown routine: he falls and loses the puck, unless he can
  wobble (7.2). **Confirmed:** all 7 wobbles were by carriers at Stickhandling 13-15, and every carrier under 12 fell
  (19 falls).
- **Skater without the puck:** he goes down once the built-up impact reaches 26. **Confirmed:** 16 skaters went down
  skating into a goalie at speed.
- **Boards:** there's no "near the boards" test. Any fall in the outer lanes (more than 104 from the middle), behind the
  net or near a corner, with the hitter on the inside, **puts the player on the boards** for a boards fall. So goalies
  and skaters ram players into the boards from much farther out than on the Genesis.

### 7.5 The puck meeting a skater

`checkpuckcoll`, `checkpuckcoll_ccx`, `puckstick`, `puckbody`; the same rules as the Genesis, a unit lower at the top.
**Code**; the height rules **Confirmed** (below).

- **16 or more off the ice: it goes over everyone.**
- **Low (under 5, rising slowly or not at all) and within 14 units of his stick blade** (its spot comes from his
  current sprite frame): **the stick plays it.** A shot slower than 13,000 **he takes**; a faster one **deflects off in a
  random direction** and he can't touch it again for 8 frames. Passes and loose pucks: he takes anything slower than
  13,000 + 700 x his Stick Handling (6.2). Right after a deflection the stick's reach is halved.
- **Otherwise his body, a circle 8 units around his centre:**
  - **Low pucks (under 8) almost always go straight through him**: only when the squared distance happens to be a
    multiple of 16, about one frame in 16, does a low puck hit his body. Only his stick stops a low shot.
  - **Pucks 8-15 off the ice always hit him** and bounce slowly straight out from his centre. A fast one (over about
    12,300) at 12 or higher **knocks him over**; a slower one makes him play the **glove-catch animation**, but the puck
    still bounces off him.
- Any touch clears the "shot taken" flag, so a blocked shot is never a shot on goal.
- **Confirmed** (5 SNES games, a loose puck at speed passing within 8 of a skater's centre): under 5 high, 291 times:
  passed through 81%, taken 13%, changed course 7%; 5-7, 6 times: passed through every time; 8-15, 5 times: hit him
  every time.

### 7.5b Bursts that shove, and players passing through

**The shove (the user's "fast-moving wall")**, **Code** (`checkcheck`, `checkplcoll`), **Confirmed**. A check is only
considered while the hitter's animation is the burst itself (`SPAburst`, $F342): **24 frames, 0.4 s**, drawn as an
ordinary skating frame. A burst lasts much longer as speed than as an animation, so a burster who reaches a man after
those 0.4 s is just a fast skater bumping into him: no check, no fall, no animation on either, and a carrier keeps
the puck. The bump (`checkplcoll`) shares their speeds by weight along the line between them, so the burster carries
him along in the direction he burst. **Recorded** (analysis/snes_burst_contact_study.py, 15 games): of bursts reaching an
opponent after the animation had ended, 204 of 260 did nothing but shove; inside the 0.4 s a check came 936 times in
1,180 (416 knockdowns). To check, burst from close: within about 0.4 s of skating of your man.

**A check that lands but knocks nothing over** looks much the same, except that the hitter shows his check
animation. The victim shows nothing: the game has no reaction for a failed knockdown, only the bump. The roll (7.1):
the single contact must be worth 32+, then a random number below (120 + victim's weight - hitter's weight) / 2 - the
impact must come out under the hitter's working Checking. A light, low-Checking hitter on a heavy man almost always
fails. Example (nhl94.com's clip of 2020-10-28, QUE-PHI, 2nd 2:43): Sundin (Checking 1, weight 56) checks Brind'Amour
(weight 72) head-on; the range is 68 - impact, so at impact 32-50 his chance is about 1 in 6 to 1 in 12 (unless the
hot / cold bug had maxed his Checking that game). The check animation plays, the bump pushes Brind'Amour back to the
boards, and the two stay overlapped there (7.6).

**Why a full-speed push is rare.** The bump runs after every check, landed or not (only pokes and hooks / holds skip
it), and moves the victim by about the hitter's weight share of the closing speed along the line between them (about
half), and the hitter on with him, so the two travel together. A soft check (most are from behind or the side) pushes
little; a hard one usually knocks him down, and the fall hides the push. So the push shows only when a hard hit fails
its knockdown roll. **Recorded** (bursts that reached a man during the burst, 15 games): closing under 120 units a second,
626 checks, 20-42% knockdowns, the rest pushed a median 16-32; closing 160+, 95 checks, 58-82% knockdowns, and the 31
who stayed up were pushed a median 73-92 (about two a game). A low-Checking hitter on a heavier man (the clip) makes it
far likelier.

**Passing through (ghosting)**, **Code**, partly explained. Two players touching (closer than 16) are always handled
the same way: a check if the hitter is in the burst animation, then a bounce, unless the game judges them to be moving
apart. Three ways a pair is skipped:

- **A player in a boards fall** (animations $FD3A-$FE60 and the like) is moved by the animation and never tested for
  collisions: anyone can skate through him. The three slow pass-throughs in the recordings were all this.
- **Two players at exactly the same speed** are skipped (7.6).
- **Overflow at extreme speed:** "moving apart" is worked out from their relative speed in 16 bits, which wraps past
  32,767 (about 480 units a second along one axis); then a head-on pair looks as if it's separating and is skipped
  entirely. One burst on top of top speed reaches about 270 units a second (the recorded maximum, 267), so it takes a
  second burst stacked on the first, head-on against a fast skater. Not seen in the recordings.

The user's GIF (PIT-WPG, 3rd 4:10: 55 bursting down into 13 carrying up) fits none of these: they closed at about 290
units a second (timed by the game clock in the GIF, 404 ms a clock second), and neither was in a boards fall. Its cause
is still open; a recorded case would show it frame by frame (the helper records the speeds, animations and flags
involved).

### 7.6 Players tangled together

**Code** (`checkplcoll`, `checkcheck`), **Confirmed** on two overtime winners. Two players can end up skating on top of
each other, and then neither can knock the other over.

- The collision code works only on two players within 16 units **who are closing on each other** (their relative speed
  points toward each other). Moving at the same speed, or drifting apart, they are skipped: no push apart, no impact, and
  **no check can land**, because `checkcheck` (7.1) is only reached from a collision.
- A collision never moves anyone; it only changes speeds. Each player gets **the other's speed plus a share of the push
  by weight**, so a soft contact (too slow for a knockdown) leaves the two moving almost as one.
- So a defender who bursts into the carrier without enough closing speed starts his shoulder-check animation, doesn't
  knock him down, and then glides along with him, overlapping, until one of them changes speed or direction. Against the
  boards both stop dead and stay overlapped. Further bursts don't help: there is no closing speed to make an impact.
- **Recorded:** 2026-10-19_2256_TOR-NYI OT: Turgeon (computer) burst into Gilmour (a person) skating down the left side
  and into the corner; the two spent 2.3 s 2-5 units apart behind the New York net; Gilmour came out with the puck and
  scored 1.8 s after they parted. 2026-10-19_2316_NYI-TOR OT: Ellett (computer) burst into King (a person) twice down
  the right wing, each time starting a shoulder check that didn't land, and skated stride for stride 11-14 apart into
  the corner; King passed out and Turgeon one-timed the winner 0.6 s later.
- **How often** (analysis/tangle_study.py, every recorded game, 2026-10-21): a carrier and a defender within 14 units for
  0.7 s or more 45 times in 137 minutes of SNES play (about 20 an hour), once in 191 minutes of Genesis play. The defender
  had tried a check in 16 of the 45; the carrier's team got a shot within 5 s in 15, a goal in 3. A carrier and a
  defender within 14 units: 3,076 samples on the SNES, 38% of them moving exactly alike; 147 on the Genesis, 2% alike.
- **Why the Genesis differs:** its collision (`checkcx`) drops a contact only when the two are moving apart, so players
  touching at matching speeds still add at least 5 impact a frame and run the check test; and its knockdown test uses the
  impact built up over the contact. The SNES drops contacts at exactly matching speeds, and `checkcheck` judges each
  collision's own strength (32 needed in one frame), so a soft, lasting contact never adds up to a knockdown.

### 7.7 Knocking the net off

**Code** (`checkgoalp`), **Confirmed** on the recordings. A skater running into a net knocks it off its spot when, on
a frame he's touching it:

- a **1-in-8** random test passes (`seed & $01C0` zero);
- he's in a **speed burst** (`SPAburst`: A without the puck);
- **the puck is within 128 units** of the net up or down the ice (most of that zone);
- he's moving faster than **8,192** across or along the ice.

The net takes 3/16 of his speed, he stops dead, and play is whistled (the faceoff goes to a dot just outside the zone
when an attacker did it, in the zone when a defender did). **The Genesis rule (GENESIS_MECHANICS 7.7) is four times
less likely per frame, needs the puck within 40, and no burst.** Recorded: 7 nets off in 137 minutes of SNES play (6 of
them in one game, 2026-10-16_2018_PHI-VAN, against the computer), each time a person's skater in a burst just before;
1 in 191 minutes of Genesis play.

**Stuck on the net** (the user: a skater who goes diagonally into the front or back of the net stays there, and every
burst can knock it off; not on the Genesis). The bounce off the net is the same code in both games (`wallcoll`: the
speed into the net cut to a quarter, at least 1,000 back out, the speed along it kept), and the recordings show skaters
pinned against the back or sides of a net for a second or more on both: 4.1 an hour barely moving on the Genesis, 1.3
on the SNES (analysis/net_stuck_study.py and the check in this section's history). What differs is the knock: on the
SNES every burst from there rolls the 1-in-8 chance on each frame while the puck is anywhere within 128 units, and a
burst (about 7,000 at full energy) on top of the push into the net reaches the 8,192 it needs; on the Genesis the puck
must be within 40, right at the net, and the chance is 1 in 32 a frame. Of the 7 SNES nets knocked off in the
recordings, 4 came after the skater had been against the net 0.6-1.2 s with one or two bursts already made; all 7 by
a person's skater.

### 7.8 The puck sliding, flying and off the boards

**Code** (`updateplayers`, `wallcoll`), **Confirmed** where measured. The same as the Genesis (GENESIS_MECHANICS 13.1,
13.2), by a different route:

- **On the ice the puck keeps about 88% of its speed a second.** It goes through the skaters' friction step, with its
  "gliding" bit set (table `.22`: $FF/256 a step at the usual two frames a step). Measured (analysis/puck_glide_study.py):
  a median 0.881 a second over 262 clean stretches (the Genesis 0.895 over 227).
- **In the air there's no friction** (measured 1.000, 245 stretches). Gravity 96 a step; **on landing it bounces back up
  at half its landing speed** (a bounce sound when that's big).
- **Boards** (`wallcoll`, the same code as the Genesis): the speed into the boards is quartered and reversed, the speed
  along them loses 1/64 + 1/128 (about 98% kept). Rim shots ride the boards; pucks fired straight in die. A hard hit
  (more than 4,096 into the boards) pops the puck up by a random amount, with a sound.

---

## 8. Penalties


![Penalty chance per check by working Aggression, Genesis and SNES](img/penalty_chances.svg)

### 8.1 The penalty roll (`checkagr`)

- Range = (20 - Aggression) x 16, using the working Aggression; a penalty when the roll comes in under the move's
  threshold.
- **Doubled for a person's player** (so people are called half as often as the computer, as on the Genesis) and
  **halved within 40 of the puck**. Both are 16-bit shifts and `randoma` takes ranges of 256 and more, so nothing
  wraps: a person's range runs from 640 at working Aggression 0 down to 160 at 15. **Code**
- **Cold players take the penalties.** Over the recordings (`analysis/penalty_aggression.py`, 2026-10-30: 52 penalties
  in 18 games, the fouling player's working Aggression read from the recording) 31 (60%) were by players at working
  Aggression 15, the value the hot / cold bug gives every "cold" rating, while skaters spent 41% of their time at 15:
  a maxed player is called about twice as often per minute on the ice, about what the roll says (1 in 5 at 15, 1 in
  13 at a typical 7). (The first 14 penalties had 11 at 15.)

Which move draws which penalty hasn't been mapped for the SNES. The penalties the game knows (its rule table): roughing,
charging, slashing, cross-checking, hooking, tripping, penalty shot, interference, holding, fighting, instigator.

### 8.2 Goalie interference (`checkint`)

- **Anyone can be called**, your computer-controlled teammates included. **Confirmed**: two of the first four interference
  calls in the recordings were on computer-controlled skaters of person-played teams; of all 18 now, 8 were on
  computer-controlled skaters.
- The goalie must be in his crease: within 40 of the middle, 228-259 from centre.
- With the goalie's impact 31 or more, it's called 2 times in (20 - Aggression): 15% at Aggression 7, **40% at 15** (a
  "cold" player).
- The skater falls whether or not a penalty is called.
- Interference is the commonest call in the recordings: 18 of 52 penalties.

### 8.3 Delayed penalties

- A foul can be called with play going on (a delayed penalty) until the whistle. **Confirmed**.
- **There's no immunity for the other team:** both teams can be called for anything at one whistle. **Confirmed**: both
  multi-penalty whistles in the recordings (a cross-check then interference by the other team at one whistle).
- A player who already has a penalty pending can't get a second one. **Code**
- **After a goal** (`PenGoalStuff`) the scored-on team's pending penalties are waived, the scoring team's still
  served (the Genesis keeps them all when the scored-on team is already shorthanded). In overtime the goal ends the game
  and the list is cleared. **Code**
- **Icing** (`PuckIChk`, `a2touchpuck`): touch-up icing as on the Genesis (armed by a touch in your own half when not
  shorthanded, called when the other team's skater touches it first, waved off by your own skater or a goalie), but
  **any crossing of the far goal line counts**: there's no Genesis-style 44-unit window in the middle. **Code**

### 8.4 Penalty lengths

From the ROM's rule table: the SDL league ROMs use **1-minute minors**.

### 8.5 Which moves draw which penalty

Every call is the roll of 8.1 (0 up to the range) against the move's threshold. **Code** (`checkcheck`, `Bcheck`,
`holdcheck`).

| Move | What happens | Penalty | Called on a roll of |
|---|---|---|---|
| A check (A, burst) that leaves him on his feet | | Charging or slashing, 50 / 50 | 0 |
| A check that knocks him down | he falls | Roughing or cross-checking, 50 / 50 | 0 |
| A poke (B) or a body touch, opponent within 45 degrees of where you face | with penalties on he always falls (tripped); with them off a person's poke trips only on randoma8(16 + his Checking - the target's Agility) of 12 or more | Tripping | under 5 |
| A hook or hold (Y), opponent within 45 degrees ahead | both slow to the average of their speeds; he flails, you're locked in the hook | Hooking, or holding when it began as a hold | 0 |
| Any of these on a skater on a breakaway | | Penalty shot | always |

- **A poke or trip is about five times as likely to be called as a check or a hook** (5 roll values against 1).
- At the same range a check is called 1 time in R: with the computer's range at working Aggression 7 (208, halved to 104
  near the puck) that's about 1 check in 100 near the puck; a person's is half as likely (8.1).
- **Recordings** (2026-10-30, 18 SNES games, 52 penalties, named from each ROM's rule table): interference 18,
  roughing 13, tripping 10, holding 4, cross-checking 4, slashing 1, hooking 1, charging 1; 34 by a person's skater,
  18 by the computer's.

---

## 9. Faceoffs

**Ratings play no part. It's timing** (`faceoffinput`, `Endfaceoff`; **Code**, **Confirmed** below):

- Each **new B press** starts one swing of the centre's stick; holding B doesn't start another. How far into the swing
  he is at the drop sets his value.
- At the drop, the home centre wins when a roll of 1-32 is at least 16 - home + away.
- **The held d-pad direction** is stored the whole time. If you win, the puck goes **that way 3 times in 4**, otherwise
  one of five directions at random; with no direction held, always at random. **The puck also gets a push back toward
  the winner's own end.**

So: **mash B, and hold the d-pad toward the teammate you want it to reach** (back to your defence is safest).

- **The swing's stage** at the drop is worth 0, 8 or 16 (wind-up, middle, sweep: which step of the swing animation the
  centre is on). Home's chance is (17 + home's stage - away's stage) / 32. The computer's centre swings at random
  moments once the drop is near.
- **Confirmed** (`analysis/snes_faceoffs.py`, 70 draws in 5 SNES games, the winner read from the push in the puck's
  speed after the drop): home won 36 where the model expects 38.7. Home ahead by a stage (8) won 74% (model 78%), level
  48% (53%), behind by a stage 20% (28%). People mashing caught the drop at stage 0 / 8 / 16 27% / 45% / 28% of the time
  (average 8.1; the computer 7.4): about the same as people on the Genesis.

---

## 10. Penalty shots


![A penalty shot step by step, with its bugs](img/penalty_shot.svg)

### 10.0 Breakaways

`CheckBreakaway`, `StartBreakaway`, `PenShotChk`, `doshot`. **Code.**

- **When it starts:** as the carrier crosses the attacking blue line, if no opposing skater (the goalie aside) is more
  than 4 units nearer the goal than he is. Teammates don't matter (on the Genesis every other player must be behind
  him). It's counted for the team (+1 breakaways), with the ding and a crowd boost.
- **It's tested again at the shot:** if a defender has caught up by then the breakaway ends, and a goal from that shot
  isn't a breakaway goal (the Genesis keeps it). A goal while it stands is a breakaway goal.
- **A foul on the carrier** (a check, a trip, a hook or hold) gives a penalty shot if the test still passes at that
  moment; otherwise the normal penalty.


### 10.1 How one ends

- **anyone takes the puck who didn't already have it**, including the shooter picking up a puck he lost;
- the loose puck moves back away from the net for 48 frames (0.8 s);
- the penalty-shot timer runs out (1,000 frames, about 17 s);
- **the loose puck hits the boards** (whistle) or leaves the rink;
- a goal, or the end of the period.

The setup puts the puck at centre and **gives it straight to the shooter where he stands** (`SetupPenaltyShot`).

### 10.2 The retake bug (explains an observed bug)

**A knocked-off net isn't one of the ways a penalty shot ends.** The whistle comes, the "penalty shot" flag stays, and
the next faceoff sets up **another** penalty shot instead of dropping the puck. The setup hands the puck to the shooter
where he stands, and he'd lined up for the faceoff: after a net knocked off by the attacker, that's the dot just outside
the zone. So the new shot starts from the side dot.

---

### 10.9 Injuries

`FallDown`, `setInjuryType`. **Code.** Much rarer than on the Genesis, which is why none has been recorded yet:

- **Only the puck carrier can be hurt**, and only when a check knocks him flat on his back while he faces straight up or
  down the ice, with the clock running and the hitter a skater.
- Then the chance grows with the hit's force: randoma8(150) x 2 under the impact, about impact / 300.
- **Out for the period**, or **for the game 1 time in 7** (on the Genesis the checker's fighting rating decides).
- With penalties on, **roughing** is called on the hitter and play stops; the hitter is knocked back.

## 11. Offsides

Only when offsides are turned on (most online leagues play with them off). **Code**: no recorded game had offsides on.

- **The moment the puck crosses a blue line into a zone**, the attacking team is flagged offside if any of its players
  is more than 10 units past the line; the flag clears once none is (tag-up). It's only checked when the puck's
  carrier, or its last toucher, is on the attacking team.
- While flagged, **a touch past 88 units from centre is called** (no free band inside the line).
- **One-timers can be offside**: the one-timer goes through the "touched the puck" routine before shooting.

---

## 12. The computer players

### 12.1 Offensive and Defensive Awareness: reaction times

**Awareness is how quickly a computer-controlled player reacts.** Each computer player has a countdown; when it runs
out he makes his decisions again. **It never affects the player you're controlling.**

- **Offensive Awareness:** 15 frames (0.25 s) at the bottom to 7 at the top.
- **Defensive Awareness** (skaters): **22 frames down to 7**: a bigger effect than on the Genesis.
- The hot / cold bug gives every "cold" rating the **best** value, 7.
- Which rating counts for which job follows the Genesis (a defenceman's gap control on Defensive, the chaser and the
  carrier on Offensive), including the same **coding slip**: wingers and centres use Defensive Awareness when their
  own team has the puck. **Code**
- **But on the SNES awareness doesn't delay the switch between attack and defence.** Every positioning job checks who
  has the puck at its start, every frame, before its countdown, and swaps to the other side's job as soon as the other
  team has it (a loose puck changes nothing). On the Genesis that check waits for the countdown, which is why there
  awareness is the reaction to turnovers. On the SNES the countdown only paces how often a player re-picks his spot.
  **Code**. Recordings, after a turnover: computer skaters of the team that lost the puck who were skating up the ice
  turned back a median 900 ms later (defencemen), 885 (wingers), 780 (centres), against 1,159 / 1,050 / 952 on the
  Genesis. That fits, though the two games' skating also differs.

### 12.2 How the computer checks

- Each frame a computer skater rolls in a range of 20 - Checking, **twice**, doubled with penalties on; either roll
  under 4 sends him looking for a hit. At Checking 15 that's **about 96% of frames with penalties off, 64% with them
  on**. Many players sit at 15 because of the hot / cold bug, so **SNES computer players are hit-happy**. **Code**
- The chaser's "go straight at the carrier" roll uses 20 - Checking the same way. **Code**

### 12.3 How the computer carrier decides

It uses the pass / shoot bias rating to choose between shooting and passing (`chk4shot`, `chk4pass`), as the Genesis
does. **Code** Differences found (2026-10-21):

- **The last 5 seconds:** with the clock running and under 5 seconds left in a period, a computer carrier shoots at
  once.
- **"Close to the net" is a square, not a circle:** the 16-times-likelier shot within 100 units of the goal-line
  centre uses a 200 x 200 square there; the distance-squared test that should trim it to a circle (`cmp #$2711`) is
  followed by no branch, so it does nothing. The square's corners in front of the goal line (100-141 units out, toward
  the boards) get the close-in odds. Not seen in the recordings (computer carriers spent only 5 s there).
- **No shot from behind the goal line or from his own half.**

### 12.4 Positioning and line changes

**Code** (`asswingo`, `asswingd`, `asscentero`, `asscenterd`, `assdefo`, `assdefd`, `assnearest`, `chk4lc`,
`CompLine`). Spots in the team's own direction: y toward the goal it attacks (its blue lines at -88 and +88, goal lines
-264 and +264), x toward each player's own side. Mostly the Genesis's numbers (GENESIS_MECHANICS 12.2); the differences
are in bold.

| Job | SNES | Genesis |
|---|---|---|
| Winger, his team has the puck | A random spot in a box picked by the puck's zone (where it'll be shortly): own zone (80 +/- 20, -70 +/- 10), neutral (100 +/- 20, 60 +/- 10), attacking (60 +/- 50, 230 +/- 20), behind the goal line (80 +/- 30, 250 +/- 20); re-picked on a zone change or 1 tick in 128 | The same (neutral y 58 +/- 5) |
| Centre, his team has the puck | Own (0 +/- 60, -70 +/- 10), neutral (0 +/- 60, 60 +/- 10), attacking (0 +/- 40, 170 +/- 30), behind (0 +/- 80, 170 +/- 20) | The same |
| Defenceman, his team has the puck | x 80 on his side (the puck's x when it's on his side, half way toward it when not); **y by the puck's zone: 98 (just inside the blue line) with the puck in the attacking zone, -78 (just outside his own blue line) with it in the neutral zone, -216 (deep in his own end) with it in his own zone; -98 while his team is offside** | Holds y 98 only while the puck is in the attacking zone; otherwise he plays his defensive job |
| Defenceman, the other team has it | x 65 on his side (0 with the puck on the other side); y **40** behind the deepest attacker (his y plus a little of his speed toward the net), jumping to -220 once that is past -190; checks for a hit every frame | 50 behind; similar depth limit |
| Winger, the other team has it | x 100 on his side, or the puck's x when it's on his side; y the puck's y while the puck is outside his zone; with the puck in his zone he stays at -158 (between the blue line and the circles), on the goal line once the puck is behind it; **-78 if their carrier is the goalie** or they're offside | The same (without the goalie case) |
| Centre, the other team has it | x half the puck's; y his high slot (-128) with the puck in his zone, else half way between the puck and it | The same |
| The chaser (nearest to the puck) | At each Offensive Awareness tick hands the chase to whoever is now nearest; charges the carrier for 240 frames on a roll by 20 - Checking, else contains half way between the puck and a point 20 out from his goal line; a loose puck: skates to it; **their goalie holding it: waits at the blue line** | The same, without the goalie case |

So SNES defencemen join the rush and drop back by zone rather than all-or-nothing. SNES and Genesis wingers both
hold at -158. What happens as the puck crosses a blue
line, and the "step out and come back in" move, are in GENESIS_MECHANICS 12.5; the SNES differs only in the numbers
above. Recordings: 3 such carries in the SNES games, too few to say more.

**Line changes** (only with line changes On: `OptLine` 1; not Off or Automatic), as on the Genesis:

- **When:** the computer carrier (`asspuckc`), with the puck in his attacking half short of the blue line (0-88), on a
  1-in-4 roll, his team not already changing, and the line's average energy at 75% or less. He then dumps the puck in
  (`CompShoot`).
- **Which line** (`CompLine`):
  - With a man advantage either way, the fresher of the two power-play or penalty-killing units.
  - At even strength, the next line from a rotation table. The third period has separate tables for leading and
    trailing.
  - If that line is at 75% energy or less, the first line in a fixed order at 95% or more.

In the leagues' usual setting (line changes off) none of this happens.

**Not checked against the recordings** except the turnover timing in 12.1: the recordings have no SNES job numbers
(the Genesis ones are in each record).

---

## 13. Energy and the crowd

- **With line changes Off, energy never drains**: skating and bursts cost nothing, **fatigue doesn't exist and
  Endurance does nothing**. **Confirmed**: every skater stayed at full energy all game in the four games first checked.
- With line changes On, energy scales top speed (down to half) and shot power.
- The crowd's excitement rises with shots, hits and goals (`CwdExciteLvl`); the meter is sqrt(excitement x 4) + 65 dB
  (`CurCrowdMeter` $19C2, at most 128). **The crowd has no effect on play**: the 110 dB flag (`CrowdLoud` $19C0) only
  triggers an undo of a hot / cold raise that is never made (2.2). **Code**, **Confirmed** (analysis/crowd_study.py:
  15 games, meter median 72-86 dB, peaks 86-128, `HotColdRaised` always 0).

---

## 14. The ROMs

- **`NHL94.smc`**: the original game.
- **NHL94_Classic**: a small hack that counts checks for each player.
- **SDL league ROMs** (SDL13-SDL16): league rosters on the same game. SDL16 is NHL94_Classic's code plus league rosters,
  **1-minute minors**, and the stats screen's "Penalties" column renamed "Checks"; everything else in its first
  megabyte is the original game's.

There's no known editor of SNES gameplay settings (the Genesis has many, see GENESIS_MECHANICS.md section 15), so
everything in this document applies to all of these ROMs.

---

## 15. Quick reference: bugs and exploits

| | |
|---|---|
| Hot / cold | Every "cold" rating is **maxed** (about 46% of all ratings, every game) |
| Ratings screen | Below the band's middle = maxed in play |
| Comeback bonus | On in the first half of the 3rd, off in the second |
| Checking | No weight bug, no CB trick; heavier checkers do a bit better |
| Repeated hits | No same-pair rule; a second hit within a second of a wobble always knocks him down |
| Aggression | Cold (maxed) players take most penalties; a person's skater is called half as often as the computer's |
| Interference | Anyone can be called; 40% for a maxed-Aggression player |
| Delayed penalties | No immunity: both teams can be called at one whistle |
| One-timers | Go where the d-pad points; goalie reach unchanged, but the computer goalie is slowed by passes; can be offside |
| Person in net | Moves much faster; taking him doesn't make him bigger, but holding A (a save move) adds a stick / glove / pad area on one side |
| Wind-up | No Genesis-style early pad stack; he stops once when a carrier winds up skating up or down the ice |
| Goalie pushed in | Impossible: the net ignores a puck the goalie holds |
| Flip | A computer dump-in by side of centre; scatters by Passing |
| Weak shooters | No limit: anyone can take a full slapshot |
| Set goalie's right | A slapshot from 6-16 units to the shooter's left of centre, 25-40 feet out, aimed at that side: about half go in (his side save leaves a gap, 4.8) |
| Computer skaters | Hit-happy (two check rolls a frame) |
| Turnovers | Computer skaters switch to defence at once (no awareness delay, unlike the Genesis) |
| Faceoffs | Pure timing; held direction 3 in 4 |
| Penalty shots | Retaken from the side dot after a net knocked off |
| Glove / stick save ratings, Fighting | Unused |
| Line changes off | No fatigue, Endurance unused |

---

## 16. Open questions and parts not read yet

Ordered by how much the answer would matter in league play (penalties off).

**Would change how people play or how games are judged:**

- **The SNES second period.** In the leagues' 36,180 games both teams score about 5% fewer goals in period 2 on the
  same shots (goals per shot 35.9% against 38.3-38.6%); the Genesis periods are equal. Not a net (each period has one
  team at each) and only partly the screen direction. Something about the period or its set-up (each side's goalie
  at the other end) is a guess; a recording or a harness test of the same shots in periods 1 and 2 would show it.
  (Settled 2026-10-30: the SNES home edge is the home / away bonus, 2.3, with nothing left over; SHOOTING_STUDY.)
- **Pressing or sitting back against a person.** Scripted rushes can't settle it (a script doesn't dodge or delay
  the way a person does); it needs many more recorded games.
- **The lane against a goalie who catches with the other hand** (SNES_SHOOTING 5.3, 4.8): the code mirrors his save
  moves, so the half-the-time slapshot lane should move to the shooter's right. One harness run would show it.
- **Instant whistles on a person goalie's catch** (5.4): mostly explained (2026-10-30): 12 of 16 were a delayed
  penalty against his own team, whistled when his catch gave his team the puck. 3 in 386 catches remain unexplained.
- **Ghosting through a skater at ordinary speeds** (7.5b): the GIF case; needs a recorded example (NEEDS_FROM_YOU).

**Expected goals:**

- **Close follow-ups** (SNES_SHOOTING 4.7): the goalie's 10-frame no-touch timer after the puck comes off him isn't
  modelled; rare in real games (13 of 745 recorded shots). Deflections have no xG.
- *Settled:* the total. Over the 741 unblocked shots and one-timers in the recorded games (both game folders,
  2026-10-30) the model gives 185.8 expected goals against 174 scored (log loss 0.40, against 0.54 for one rate for
  all): within chance.

*Settled 2026-10-30:* the flip (6.3), now played in the game and found in the recordings.

---

## 17. Appendix: units, addresses and sources

### Units


![The rink with its landmarks in game units and feet](img/rink_feet.svg)

- **Position:** game units, as on the Genesis: the rink runs about -130 to +130 across and -300 to +300 along; goal
  lines at +/-264 (the code's tests; the net object sits at +/-268), blue lines at +/-88. About 3 units per foot.
- **Speed:** the game's velocity words; skaters top out around 9,000.

Distances are in the game's own units: **about 3 units to a foot**, so divide by 3 for feet. Speeds are the game's
speed numbers; a puck moves its speed / 4,096 units a frame, 60 frames a second.

**The rink:**

| Landmark | Units | Feet |
|---|---|---|
| Rink length / width | about 600 / 260 | about 200 / 87 |
| Centre of the rink to each goal line | 264 (the net sits at 268) | about 88 |
| Centre to each blue line | 88 | about 29 |
| Blue line to goal line (the attacking zone) | 180 | 60 |
| Goal line to where the goalie stands | about 20-25 | 7-8 |
| End-zone faceoff dots: out from the goal line / across from the middle | 62 / 70 | 21 / 23 |
| Goal mouth (scoring part) | 17 either side of the middle (posts out to 22) | about 6 either side |

**Distances that come up a lot:**

| Distance | Units | Feet | Where it comes up |
|---|---|---|---|
| A goalie's body | a box about 10 either side of his centre, plus areas from his save poses | 3-4 | what a shot must miss to score |
| A stick's reach for a loose puck | 14 | about 5 | catching passes, the goalie's stick |
| A player's body to the puck, up or down, for his stick to be checked | 40 | about 13 | pucks going through a stick |
| High-danger shot (the slot) | within 60 of the net | within 20 | shot maps |
| Shots that can go exactly where aimed | within 200 of the aim point | within about 67 | roughly from the blue line in |

**Speeds:**

| Speed number | Units a frame | About | Example |
|---|---|---|---|
| 9,000 | 2.2 | 30 mph | a skater flat out |
| 15,000 | 3.7 | 50 mph | a typical pass |
| 23,000 | 5.6 | 78 mph | a hard pass shot or slapshot |
| 29,000 | 7.1 | 98 mph | the hardest slapshots |

- **Time:** frames at 60 a second.
- **Ratings:** steps 0-6; working values 0-15.

### Useful RAM addresses (bank $7E)

| Address | What |
|---|---|
| $0D55 / $0DB7 | X / Y positions (a word per object: 0-5 Home, 6-11 Away, 12-13 nets, 14 puck) |
| $0EC3 / $0EE3 | X / Y speed |
| $0DF9 | Puck height |
| $1A12 | Hot / cold table (12 bytes per player) |
| $12E3, $1303, $1363, $1383, $1423, $1443, $1483 | Working Agility, Speed, Shot Power, Shot Accuracy, Endurance, Aggression, Checking (a word per object) |
| $15DE | Penalties called, waiting to be listed |
| $1E9B, $163A | Penalty shot pending / under way |
| $19BE | Crowd excitement |

### Sources

- SNES disassembly: [github.com/abdulahmad/NHL94SNES](https://github.com/abdulahmad/NHL94SNES)
  (`src/routines/hockey`, `src/routines/logic`, `src/routines/stats`, `src/ram94s.asm`)
- Recordings and save states read with this project's helper; the project's `docs/PROJECT_NOTES.md` holds the detailed notes,
  addresses and test methods behind each finding.
