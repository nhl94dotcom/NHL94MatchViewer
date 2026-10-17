# NHL '94 Game Mechanics (Sega Genesis and SNES)

What NHL '94 actually does under the hood: how ratings work, how saves and checks are decided, how penalties are
called, what the computer players think, and the bugs that shape online play. Every finding comes from reading the
games' own code and is marked with what supports it:

- **Confirmed**: the code says so *and* recorded games show it, with the numbers given.
- **Code**: read from the code, not (yet) seen in a recording, usually because the situation hasn't come up.

Each finding says which system it applies to. **Genesis** means NHL '94 on the Sega Genesis / Mega Drive (the original
`nhl94.bin` and the league ROMs built on it). **SNES** means NHL '94 on the Super Nintendo (`NHL94.smc`,
NHL94_Classic and the league ROMs built on it). Where the two differ, both are described.

For what this means in play, without the code, see the [Practical Guide](PRACTICAL_GUIDE.md).

## Contents

1. [How this was found](#1-how-this-was-found)
2. [Ratings: what the game really uses](#2-ratings-what-the-game-really-uses)
3. [Skating](#3-skating)
4. [Shooting](#4-shooting)
5. [Goaltending](#5-goaltending)
6. [Passing, the flip and stickhandling](#6-passing-the-flip-and-stickhandling)
7. [Checking, hooking, poking and collisions](#7-checking-hooking-poking-and-collisions)
8. [Penalties](#8-penalties)
9. [Faceoffs](#9-faceoffs)
10. [Breakaways and penalty shots](#10-breakaways-and-penalty-shots)
11. [Offsides](#11-offsides)
12. [The computer players](#12-the-computer-players)
13. [Puck physics](#13-puck-physics)
14. [Line changes, energy and the crowd](#14-line-changes-energy-and-the-crowd)
15. [League ROMs: settings that change the game (Genesis)](#15-league-roms-settings-that-change-the-game-genesis)
16. [Quick reference: bugs and exploits](#16-quick-reference-bugs-and-exploits)
17. [Open questions](#17-open-questions)
18. [Appendix: units, addresses and sources](#18-appendix-units-addresses-and-sources)

---

## 1. How this was found

Both games have been disassembled by the community into source code that rebuilds the original cartridges byte for
byte:

- Genesis: [abdulahmad/NHL94Genesis](https://github.com/abdulahmad/NHL94Genesis), with comments explaining most
  routines.
- SNES: [Mhopkinsinc/NHL94SNES](https://github.com/Mhopkinsinc/NHL94SNES).

The NHL '94 Viewer's helper records the game's memory about 60 times a second while you play in RetroArch (Genesis Plus
GX and Snes9x cores). That gives every player's position, speed, animation and *working* ratings, frame by frame, so
the code's rules can be checked against real games. The checks here used about a dozen recorded games (online and
single-player, both systems, the original ROMs and league ROMs). Numbers like "48 of 102" are counts from those games.

Routine names in `code style` are the disassemblies' names, for anyone who wants to read the code.

---

## 2. Ratings: what the game really uses

### 2.1 Working ratings

The ratings you see in the editor (0 to 6 on most ROMs; the game's own screens show them as numbers from 25 to 99,
see 2.5) are not what the game plays with. Each time a player comes on the ice (faceoffs, line changes), `setplayer`
turns each rating into a **working rating**:

| | Genesis | SNES |
|---|---|---|
| Scale | 0 to 30 | 0 to 15 |
| Formula | rating x 5 + hot/cold + bonuses | (rating x 5) / 2 + hot/cold + bonuses |
| When | when the player is put on the ice | the same |

Because ratings are only worked out when a player is put on the ice, bonuses that depend on the clock or the score
(below) follow **the situation at the last faceoff or change**, not the live situation. **Confirmed** (SNES CHI-TOR:
a third period with no stoppage kept the bonus the whole period).

### 2.2 Hot and cold: buggy on both systems

Before each game the game rolls random "hot / cold" values for every player. Both systems have a bug in how they are
used.

**Genesis** (**Confirmed**)

- Each player gets 16 random values from -9 to +8, fixed for the whole game.
- **Bug:** the routine that applies them (`AttributeCalc`) loads the number of the rating it is working on, then
  immediately clears it. So **every rating a player has gets the same single value** (his first one), divided by 3:
  from -3 to +2 on the 0-30 scale (about -0.6 to +0.4 of an editor rating point).
- **On the original ROM, the hot and cold players the game shows you are fake.** The scouting report's hot / cold
  players and the matchup screen's flame and snowflake icons are worked out from values 4 to 16, and the player cards
  add each rating's own value. None of those are what plays. Many league ROMs change this (section 15): most show the
  bonus as it plays in Edit Lines, some fix the bug so each rating has its own value, and some turn hot / cold off.
- Checked over 4,000+ moments in four games (including a 30-team league ROM) where the two readings differ: the
  working ratings matched the single value every time.

**SNES** (**Confirmed**)

- Each player gets 12 random values from -12 to +12, one per rating, fixed for the game.
- **Bug:** the value is shifted with an unsigned shift, and the step that should restore the minus sign tests the
  wrong bit (`bit #$00`), so it never fires. A negative ("cold") value turns into a big positive one, and **that rating
  goes to the maximum, 15.**
- About **46% of every player's ratings are maxed in every game**, whatever his real rating.
- Checked in all three SNES games (NHL94_Classic and SDL16). Effects seen elsewhere in this document: more than half
  of all SNES skaters skate at maximum speed; most SNES penalties are taken by players at maximum Aggression; many SNES
  shooters have maximum Shot Accuracy.
- A loud crowd (110 dB or more) raises four of each player's values by 2 until it drops under 105 (**Code**).

**Bottom line:** on the Genesis hot / cold is small and invisible; on the SNES it flattens the ratings, which is a big
part of why ratings matter less on the SNES.

The NHL '94 Viewer shows each player's hot / cold **as played** on his player card ("Hot / cold (as played)"), read
from the game's memory during the recorded game: the single Genesis value, the per-rating values on ROMs that fixed the
bug, or on the SNES which ratings the bug maxed.

### 2.3 Hidden bonuses

Added to working ratings when a player comes on the ice.

| Bonus | Who | Ratings | Notes |
|---|---|---|---|
| Home / away | per team, set in the ROM | Offensive and Defensive Awareness, Stickhandling, Shot Accuracy, Passing | Home team adds its home value, away team subtracts its away value. Boston: +2 at home, -1 away; Calgary 0 at home. **Confirmed** (both systems) |
| Power play | team on the power play, per-team ROM value | Offensive Awareness, Stickhandling, Shot Accuracy, Passing | **Confirmed** (Genesis) |
| Penalty kill | team killing a penalty, per-team ROM value | minus to Offensive Awareness, Stickhandling, Shot Accuracy | **Confirmed** (Genesis) |
| Comeback | team tied or trailing in the third period, both teams in overtime | +2 Offensive Awareness, +2 Checking, +4 pass/shoot bias | **Bugged**, see below |

**The comeback bonus is backwards** (**Confirmed**, both systems). The test that should switch it on for the last half
of the third period is the wrong way round, so it is **on while more than half of the third period is left** (with
5-minute periods, before 2:30) **and off for the last half**. In overtime both teams have it throughout.

### 2.4 What each rating does

**Genesis** (working values 0-30). Every place the code reads each rating:

| Rating | What it does |
|---|---|
| **Weight** | Acceleration (each Weight point costs as much acceleration as 2 Agility points); check knockdowns (with the weight bug, section 7.2); momentum in collisions |
| **Agility** | Acceleration, and so how quickly a player changes direction; a goalie's reach; resisting a poke trip when penalties are off |
| **Speed** | Top speed; the computer chaser's +6 when the opposing carrier is in the slot |
| **Offensive Awareness** | Reaction time of computer players in some jobs (section 12.1) |
| **Defensive Awareness** | Reaction time of computer players in other jobs; the computer goalie's re-aiming |
| **Shot Power** | Shot speed; **below a working 20 (rating 3 or less, and a "cold" 4) the wind-up is cut short, so weak shooters can't take a full slapshot**. Goalies: this slot holds Puck Control (how often they hold shots) |
| **Shot Accuracy** | The chance a shot goes exactly where aimed, and how far it scatters if not |
| **Passing** | **Pass speed only**: passes are always aimed perfectly |
| **Stickhandling** | Stealing and protecting the puck; catching hard passes; wobbling instead of falling when hit |
| **Checking** | Knockdown odds; upending players (20+); **how often computer skaters try to check, and how aggressively the computer chaser attacks the carrier** |
| **Endurance** | How fast energy drains, which only matters with line changes on |
| **"Rgh" (pass/shoot bias)** | Whether a **computer** puck carrier shoots or passes. The disassembly calls it the pass/shoot bias |
| **Aggression** | Penalty odds (with a wrap-around bug, section 8.2). Goalies: this slot is glove skill, and 11+ allows the reaching glove save |
| **H/F (Fighting)** | How long players *you* injure are out (period or game) |
| **Goalie glove / stick save ratings** | **Nothing.** They are looked up and never used |

**SNES** (working values 0-15). Same roles, with these differences:

| Rating | SNES difference |
|---|---|
| Weight | Costs less acceleration: a Weight point equals 2/3 of an Agility point. No weight bug |
| Agility | Also drives stopping. Goalies: a person's goalie accelerates much harder than a computer goalie, and a computer goalie loses his Agility while a pass is in flight |
| Speed | Top speed is also reduced by fatigue (down to half), only relevant with line changes on. No chaser slot boost |
| Shot Power | **No wind-up cut-off**: weak shooters can take full slapshots |
| Passing | Pass speed, **and the flip's accuracy** |
| Stickhandling | The wobble needs 12+ (of 15), which many players get from the hot / cold bug |
| Checking | Computer players check far more often (two rolls a frame) |
| Aggression | Penalty odds, with a different overflow bug (section 8.3) |
| Goalie save ratings | Also unused |
| Fighting | Never read |

### 2.5 The 0-99 numbers on the ratings screens

The game's own screens (Edit Lines, Team Roster, player cards) show each rating as a number from 25 to 99. It is made
from the stored rating r (0-6) and a hot / cold value (`CalcAttrib`, `AttribAdjust`):

- **Genesis:** n = 18 x r + that rating's own hot / cold value (-9 to +8), at least 0; 100 or more shows as 99;
  **under 50 it is squashed to n / 2 + 25**.
- **SNES:** n = 18 x r + 3/4 of that rating's hot / cold value (-12 to +12, so -9 to +9), the same squash; the top shows
  as 100.

So each stored rating is a **band** of numbers, and where a number sits inside its band is hot / cold:

| Stored rating | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Numbers shown | 25-29 | 29-38 | 38-47 | 47-62 | 63-80 | 81-98 | 99 (SNES 99-100) |
| Band's middle (no hot / cold) | 25 | 34 | 43 | 54 | 72 | 90 | |
| Working value, Genesis (x 5) | 0 | 5 | 10 | 15 | 20 | 25 | 30 |
| Working value, SNES | 0 | 2 | 5 | 7 | 10 | 12 | 15 |

What the position inside a band means differs (**Code**; the bands agree with the NOSE editor's table):

- **Genesis, original code** (`nhl94.bin`, and ROMs whose Edit Lines shows each rating's own value): **nothing**. Each
  number uses that rating's own hot / cold value, but play uses one value for all of a player's ratings (2.2), and that
  one is never shown. Only the band counts.
- **Genesis league ROMs that show hot / cold as played** (CDL, IDL, DPWM, RGDL ...; section 15): the routine is changed
  to add the player's played value to every rating (`adda.l #$10,a4` and the per-rating read replaced), so **all of a
  player's numbers sit the same distance from their band's middle**, and that distance is his real hot / cold: 3 or more
  above is +1 working point, 6 or more +2; 3 or more below is -1, 6 or more -2, 9 below -3.
- **Genesis ROMs with the per-rating fix** (WJ2025): each number is that rating's real value, as shown.
- **SNES:** a number **below its band's middle means that rating is maxed in play** (15, the hot / cold bug, 2.2), even
  for a rating-1 player; at the middle, maxed one time in three; above it, the rating plus 0-3. The pairs of
  neighbouring bands that share a number (29, 38, 47, 63, 81) can't be told apart from the screen.

The Genesis scouting report (the pre-game Matchups screen) rolls new hot / cold values, so only screens seen after it
(Edit Lines from the pause menu) show the game's values.

**Overall** (Genesis `CalcAttrib` with `OvrPlayerWgtList`): skaters count Speed, Offensive Awareness and Stickhandling
three times, Agility, Defensive Awareness, Checking and Shot Accuracy twice, Shot Power, Endurance and Passing once,
and leave out Weight, Aggression, Fighting and the pass / shoot bias. Goalies: Agility, Defensive Awareness and Puck
Control 4.5 each, the four glove / stick ratings 1 each. So Overall leans on ratings that don't touch the skater you
control (Offensive Awareness) or do nothing with line changes off (Endurance), and goalies' on four unused ratings.

---

## 3. Skating

### 3.1 Top speed

Each skater has a speed cap set by his working Speed. Pushing the d-pad adds speed only below the cap; speed bursts
can take him past it and friction brings him back.

- **Genesis:** cap = (20 + (Speed + 2) / 2) x 275 in the game's speed units, Speed + 2 capped at 30. **Confirmed**:
  each skater's normal cruising speed sat just under his cap, from 6,628 at working Speed 7 (cap 6,737) to 9,162 at
  26 (cap 9,350), 61 skaters in three games. That is roughly **23 mph for the slowest to 32 mph for the fastest**.
- **SNES:** cap = (20 + Speed) x 261, Speed on 0-15, scaled by energy. **Confirmed**: 6,919 at Speed 7 (cap 7,047) to
  8,901 at 15 (cap 9,135). **32 of 61 SNES skaters were at the maximum working Speed of 15** (the hot / cold bug), so
  speed ratings barely separate SNES players.
- The "+2 Speed" in the Genesis formula comes from a crowd feature that is hard-wired on (its switch-off line is
  skipped), so it applies to everyone, always.

### 3.2 Acceleration

- **Genesis:** each frame you push, speed grows by (64 - 2 x Weight rating + working Agility + 2) / 2, scaled by the
  direction (full straight, about 70% diagonally). **Confirmed**: measured frame by frame over about 19,500 samples,
  within 1-5% of the formula at every level. The quickest accelerators gain speed about 40% faster than the slowest.
  - **A person's puck carrier accelerates at half rate** (the computer's carriers don't). **Code**
  - Goalies add their Agility again, plus 16. A goalie carrying the puck has half his top speed. **Code**
- **SNES:** speed grows by 32 - Weight + 1.5 x Agility (SNES scale). A person's goalie without the puck gets
  2 x Agility + 8 more; a computer goalie gets only + 8, and **loses his Agility again while a pass is in the air**, so
  he slides across slowly on passes. A person's goalie inside his crease skates at three-quarters of his top speed.
  No half-acceleration rule for puck carriers was found. **Code**

### 3.3 Friction

- On the ice a gliding skater loses 1/64 of his speed per frame (about 61% a second); the puck far less (section 13).
- Speed bursts (C without the puck) add speed in the direction faced; with line changes on they cost energy.

---

## 4. Shooting

### 4.1 The nine aim points

Every shot is aimed at one of nine points in the net, picked by **the direction the stick (d-pad) is held as the shot
is taken**, in **screen** directions:

| Held | Aim |
|---|---|
| Up-left / Up / Up-right | High: the screen's left / middle / right |
| Left / nothing / Right | Middle height: left / middle / right |
| Down-left / Down / Down-right | Along the ice: left / middle / right |

Because it is screen direction, when you attack down the screen the stick's left is the shooter's right. Posts are at
about +/-16 (Genesis) or +/-15 (SNES) from the middle; heights are 12 (high), 6 and 0. **Confirmed** on both systems:
goals' aim points and where they crossed the line agree closely.

### 4.2 Perfect shot or scatter (both systems)

- **Within 200 units of the aim point** (about 65 feet), a roll decides whether the shot goes **exactly** where aimed.
  Chance = (Shot Accuracy + 1) / (Shot Accuracy + 16) on the working scale: about 55-67% for typical Genesis shooters
  (0-30 scale), at most about 52% on the SNES (0-15 scale).
- **Beyond 200, never perfect.**
- Otherwise random scatter is added: bigger for harder shots, longer distance and poorer accuracy (Genesis: (shot
  speed / 16 - Shot Accuracy / 2 + 16) x distance / 64, halved within 250, capped). Across: either way. Height:
  **only ever upward**.
- **Confirmed.** Genesis: within 200, 82 of 123 shots left the stick within 2 units of the aim point, more often for
  better shooters, roughly as the formula predicts; none of those from beyond 200. SNES: 60% of 112 close shots on the
  aim point, none of 15 from farther out; 63 of the 112 were by shooters at the maximum Shot Accuracy (hot / cold bug).

### 4.3 Shot power and the wind-up

- **Genesis:** shot speed grows with working Shot Power and with how long the wind-up runs; backhands lose a quarter
  of their power; fatigue scales it (only with line changes on). **Shooters with working Shot Power below 20 have the
  wind-up cut short (step 8 instead of 16), so they can't take a full slapshot.** **Confirmed**: those shooters topped
  out at 20,746 (median 13,706, 67 shots); stronger ones reached 29,216 (83 shots). In mph, the hardest slapshots are
  around 95-100 mph.
- **SNES:** no wind-up cut-off; anyone can wind up fully. **Code**

### 4.4 Auto-aim: one-timers and computer shooters

- **Genesis:** **one-timers ignore the stick.** The game aims them itself: middle height, on the side away from where
  the goalie is heading, or high in the middle when he is well off to one side. Computer shooters are aimed the same
  way. **Code**
- **SNES:** only computer shooters are auto-aimed; your one-timers go where your stick points. **Code**

### 4.5 "In-close top shelf" (Genesis)

A high shot (stick up, up-left or up-right) from close in (within about 50 units of the goal line), at a goalie who is
not in a pad stack, gets a steeper lift. **Code**

### 4.6 Delayed-penalty sniping (Genesis only)

While the other team has a delayed penalty pending (referee's arm up, play continuing), the game pulls your goalie for
an extra attacker, and **every shot your team takes from within 200 units goes exactly where it's aimed**: the shot
code treats "goalie pulled" as "always perfect". **Confirmed** on the two aimed shots in the recordings taken during a
delayed penalty (0.7 and 0.3 units off the aim point). The SNES doesn't do this.

### 4.7 What counts as a shot on goal (Genesis)

- A shot counts when the puck touches the goalie's body, or he catches it with his stick, while the "shot taken" flag
  set at the release still stands. Posts and the crossbar also count (section 13.3).
- **Any touch on the way** (a stick, a body), **the boards**, or a hard puck deflecting off the goalie's stick clears the
  flag without counting. Pass shots (a B pass used as a shot) never set it, so they only count if they score.
- **Nothing counts while the clock is stopped**, which is why penalty shots are never shots on goal.
- **Code**, partly confirmed (the penalty shot). Some saved shots in the recordings weren't counted and the
  stick-deflection rule doesn't fully explain them.

### 4.8 One-timers (Genesis)

**Triggering:**

- Pass (B) to a teammate, then **press C while the pass is on its way**. You still control the passer then, and C
  hands control to the receiver for the shot.
- Or, controlling the receiver, press C while the puck is loose and coming to him.
- **Only in your attacking half.** In your own half, C is a normal speed burst. The receiver can't be a goalie.

**The game times the swing for you.** The receiver starts his wind-up; the game keeps working out how many frames
until the puck reaches him and **starts the downswing itself** so the blade meets the puck (forehand or backhand by the
angle to the net). If the puck is slow he holds the top of the wind-up for up to 0.8 s more. The strike happens when
the puck comes within 10 units of the blade, and gets a strong minimum shot speed, auto-aim (4.4), and **the goalie's
reach cut to its minimum** (5.1).

**It fails** when the puck doesn't reach the blade before the swing ends (a slow pass, a receiver drifting off the
pass's line, a deflection), when anyone else touches the puck first, or when the puck goes away from him.

**Confirmed timing:** successful one-timers struck 0-0.87 s after the C press (median about 0.2 s); failed ones ended
0.3-1 s after it. **Press C no more than about 0.9 s before the pass arrives.** Pressing late is fine, even as the puck
reaches him: the swing snaps forward when the puck is already at the blade.

The computer one-times on its own in the attacking zone (and now and then outside it), but only for teams no person
controls.

---

## 5. Goaltending

### 5.1 Saves are geometry, not a dice roll (Genesis)

The goalie stops a puck only if it physically reaches him:

- **Body:** a puck at height 15 or lower within his **reach** of his centre is stopped.

  | Situation | Reach (game units) |
  |---|---|
  | Computer goalie, by Agility | 12 to 15 |
  | **A person controls him** | **always 15** |
  | In a pad stack | 18 |
  | **Against a one-timer** | **12, whatever his Agility** |
  | Shootout | 2 less |

- **Stick:** a puck at height 5 or lower near his stick blade. Within 8 units he plays it: slower than 13,000 he
  catches it, faster it deflects off in a random direction. **Between 8 and 14 units nothing happens that frame and the
  body test is skipped**: a small gap beside the stick.
- After a body touch the puck is held or rebounds (5.3).
- **The glove and stick save ratings are never used.**

**Confirmed:**

- As the puck reached the goalie's line, saves passed a median 13 units from his centre (49 of 71 within 15); goals a
  median 24 (31 of 40 at 15 or more). 111 goals and saves.
- 5 of the 9 goals that went in close to the goalie were one-timers (reach cut to 12).
- The other 4 all had the computer in net, with Agility rated 3-4 (reach 13-14). **With a person in net, no goal other
  than a one-timer passed within 20 units.** Taking the goalie yourself really does make him bigger.

This means a true "expected goals" model can be built from the game's own rules: the chance the aim scatter carries a
shot outside the goalie's reach.

### 5.2 SNES saves

Also geometry, but different (**Code**, partly confirmed):

- His body is a fixed box (within 10 units across and along), apparently with no height limit.
- A second area that depends on his animation frame, with its own height range, covers the stick and pads.
- **No changes for Agility, for a person controlling him, for pad stacks or for one-timers.**
- A diving goalie lets pucks at height 5 or more through.
- The glove and stick save ratings are looked up and then overwritten: unused here too.
- **Confirmed:** no SNES goal passed within 12.6 units of the goalie's centre (26 goals); saves a median 12.9.

### 5.3 Rebounds (Genesis)

- After the puck touches his body, he **holds it** if both of its speed components are under a random threshold set
  by his Puck Control; otherwise it **rebounds**.
- **In close with the goalie standing still** (puck within 44 of the middle, 210-270 from centre ice, goalie not in a
  save move) the threshold is quartered, so point-blank shots mostly rebound. A **diving** goalie never holds it.
- **The rebound goes straight out from the goalie's centre through the spot the puck touched**, at a speed set by how
  far from his centre that was. A shot clipping his left pad comes off to his left.
- **Confirmed** on 135 saves: in close with the goalie standing, 28 rebounds in 47 (60%); in close mid-save, 19 of 72
  (26%); farther out, 2 of 8. Rebounds left a median 6 degrees off the centre-to-contact line (3 in 4 within 19).

### 5.4 The computer goalie (Genesis)

**Positioning:** he plays the angle: on the line from the puck to the middle of his net, 18 units out. He re-aims every
1-3 frames depending on his Defensive Awareness (12.1). **Code**

**Save moves** (`goaliesave`). He starts one only when he predicts the puck will cross his goal line **within 24 units
of the middle in under 0.2 seconds**. Which move:

| Puck | Where it will cross | Move |
|---|---|---|
| High (above 8, or rising fast) | near him (within 16) | shoulder save |
| High | farther out | glove or blocker (reaching glove save with glove rating 11+) |
| Low, arriving within 8 frames | near him | kick / butterfly |
| Low, arriving within 8 frames | farther out | stick save |
| Low, further off, **someone still carrying it** | | **pad stack** (slides across toward that side) |

**Dives:** the computer goalie **only dives to smother a slow loose puck right in front of him** (within 20 across and
30 out), never at a shot. **Confirmed**: all 7 computer dives in the Genesis recordings were at loose pucks within 45
units. A puck taken in a dive is whistled dead almost at once (5 frames); otherwise the hold whistle comes about 2.3 s
after he takes it.

The save-move mix in the recordings (115 saves) fits: stick 62, high 14, pad stack 12, dive 5, glove 2, none 20.

### 5.5 SNES goalie extras

The SNES save-move choice follows the same pattern. Its code also has two attacking moves (**Code**):

- a **poke check** at a carrier within 35 units in front of the goal line, on a random roll (about 1 in 26 per frame),
  then 4 seconds before he can poke again;
- a **dive at the puck carrier** when the puck is within 45 and an attacker within 60 (about 1 in 32 per frame), then
  6 seconds before he can dive again.

In four SNES games no computer goalie dived at all (all 6 dives were by people), so which goalies use these is unclear.

**SNES goalies and passes:** every pass delays the goalie's next rethink by half his Defensive Awareness value, and a
computer goalie loses his Agility while a pass is in flight. Both make **one-timers especially effective against SNES
computer goalies**. **Code**

### 5.6 Goalie whistles

- Holding the puck: about 2.3 s after he takes it (5 frames if he took it in a dive).
- A person-controlled Genesis goalie who skates past the top of the faceoff circles (about 170 from centre) gets a
  whistle.

---

## 6. Passing, the flip and stickhandling

### 6.1 Passing (Genesis)

- **The Passing rating sets pass speed** (160 + 2 x working Passing), **not accuracy.**
- **Every targeted pass is aimed perfectly** at where the receiver will be if he keeps skating the same way, and lifted
  slightly according to how long it will travel.
- **Who it goes to:** the nearest teammate within 45 degrees of the direction held. A teammate straight ahead gets no
  penalty; one 45 degrees off counts as if he were 256 units farther away. With nobody in that cone, the puck just goes
  that way: that's how **pass shots** happen.
- **SNES** pass speed: 144 + 4 x working Passing. **Code**

### 6.2 Catching and bobbles (Genesis)

- A skater can take a pass only if it's at stick height (5 or lower) and **slower than 13,000 + 350 x his working
  Stickhandling**. A faster puck deflects off his stick in a random direction: a **bobble**.
- **Confirmed** in part: 300 of 302 catches were within the receiver's limit; of 32 reviewed bobbles, 13 were over it
  and 4 arrived in the air. The other 15 are not explained yet.

### 6.3 The flip (A with the puck)

**Genesis: a lob to a fixed spot, not aimed by the d-pad.** **Confirmed.** The spot comes from where your skater is and
which way he's facing:

| From | Lands at | Loft |
|---|---|---|
| Outside the attacking zone | **the attacking-zone faceoff circle on the side he's facing** (facing straight ahead: his right) | high (up to height 57) |
| Inside the attacking zone | the high slot | low |
| Deep and near the middle (behind or beside the net) | the goal mouth | low |
| A goalie | about the middle of the ice, to his facing side | |

- A random 0-9 units is added. **If the spot is less than 60 units to his side, it's moved to 60 units out from him.**
- To place a flip, **steer your skater's facing**, not the d-pad at the press.
- Nobody one-times a flip, despite the disassembly calling it a "one-timer pass" (a name left over from the earlier
  game).
- **Checked:** 9 of 13 high flips came down within 12 units of the predicted spot, most within 1-6; a flip from behind
  the net dropped at the goal mouth.

**Flipping it over the glass on purpose (Genesis).** The 60-unit rule can push the target past the boards:

1. Be outside the attacking zone (high lob).
2. Be on one side, about 75-115 units from the middle (the outer half of that side, not hugging the boards).
3. Face toward those boards.
4. Press A: the target is pushed 60 units past you, beyond the boards, and the lob is still high there. Out of play,
   whistle.

Too close to the middle and it lands at the boards; right on the boards and the target is pulled back inside. The
random 0-9 decides the edge cases, which is why it doesn't always work. **Confirmed** on the two flips in the
recordings that went over the glass (heights 44 and 42 at the boards).

**SNES: a computer-run dump-in.** Pressing the flip button (Y) hands your skater to the computer's dump-in routine
(**Code**; no SNES flip in the recordings yet):

- Outside the attacking zone: deep in the zone between the circle and the corner, **on whichever side of centre
  you're on** (facing doesn't choose).
- Inside the zone: in front of the net.
- He first turns to face up the ice, so it comes out late if he was facing sideways.
- **It scatters by up to +/-(20-25 + 2 x (15 - Passing)) across and up to +/-70 along**, so Passing is flip accuracy on
  the SNES.

### 6.4 Steals (both systems)

- **Any opposing stick touching a carried puck gets a steal roll**: about 3 in (36 + carrier Stickhandling / 2 -
  stealer Stickhandling / 2) per frame of contact, better with the carrier in the slot, both scaled by energy. A steal
  knocks the puck loose in a random direction.
- The poke check (7.5) is just the quickest way to get a stick there.

---

## 7. Checking, hooking, poking and collisions

### 7.1 How a check lands (both systems)

- Only a **speed burst** (C without the puck) can knock someone down.
- **Impact** = how fast the two players are closing along the line between them. Each frame of contact adds at least
  5, and it fades by 2 a frame, so repeated contacts build up.
- **Genesis:** a check needs impact 20+. The knockdown value is (base - checker weight + target weight) / 2 - impact
  (weight = Weight rating x 8). At 0 or below, or with the target against the boards, **he goes down**. Otherwise a
  roll against half the checker's working Checking decides.
- **SNES:** a check needs impact 32+; base 120 for everyone; the roll is against the checker's Checking.
- **Goalies can't be knocked down** on either system.

### 7.2 The weight bug and the CB check (Genesis)

The community knows the **weight bug**: a person-controlled skater checks better when light, a computer one better
when heavy. The cause:

- A person's checker uses base **240** (the computer's: 120), and the sum is done in **a single byte**.
- When the target is **2 or more Weight points heavier** than the checker, 240 - checker + target passes 255 and
  **wraps around to nearly 0**. At exactly 2 points heavier the knockdown is automatic.
- Against a target the same weight or lighter there's no wrap, and the value is 76-124: far harder than the computer's
  16-92.
- So a light skater controlled by a person gets the wrap against almost everyone; a heavy one almost never does.

**The CB check** (C to burst, then B to switch control away before contact) works because **what counts is who
controls the checker at the moment of contact**. Handing him to the computer puts him on the 120 formula, where his
weight helps. The price: computer checkers draw **twice the penalties** of person checkers (8.1).

**Confirmed** in eight Genesis games (lunges that made contact, share knocking the man down):

| Checker at contact | Target 2+ heavier | Within 1 point | Target 2+ lighter |
|---|---|---|---|
| A person | **48%** | 15% | **7%** |
| The computer | 15% | 27% | 34% |
| CB checks | 10 of 18 overall | | |

**ROMs:** the editors' hacks (smozROM, carried on by NOSE4Web) offer changes to both, but **their weight "fix" rests
on a misreading** of this code. The editor's note says the original game takes the checker's weight from the target's,
"so that light players check well and heavy ones fall over". In fact the original formula is the physical one
(checker's weight subtracted, so a heavier checker does better, as the computer's numbers above show); the only bug is
the byte overflow for a person's checker. The two versions found in ROMs:

- **"Simple"** (`sub.b` and `add.b` swapped: base - target + checker): computer checkers now do *better the lighter
  they are*, and a person's checker overflows when he is 2 or more points *heavier* than the target, an automatic
  knockdown.
- **The full fix** (base - target + 3/4 x checker + 2 x Checking - 14, still in one byte): computer checkers again do
  better the lighter they are, and for a person's checker the sum overflows once his weight and Checking are high
  enough (at equal weights of 60, working Checking 23 or more), turning a hard check into an automatic one.

Worked through for a check at impact 30 by a skater with working Checking 16 (light 40, heavy 80):

| Version | Person: light into heavy | Person: equal | Person: heavy into light | Computer: light into heavy | Computer: heavy into light |
|---|---|---|---|---|---|
| Original | 100% | 10% | 13% | 18% | 90% |
| Simple | 13% | 10% | 100% | 90% | 18% |
| Full fix | 12% | 10% | 100% | 64% | 18% |
| Everyone 120 (below) | 18% | 30% | 90% | 18% | 90% |

**The C-then-B fix makes it worse.** The code at $13D6C is:

```
moveq  #$78,d0           ; base 120
btst   #3,pflags(a3)     ; checker controlled by a person?
beq.w  +4                ; no: skip the next line
asl.w  #1,d0             ; yes: double it to 240
sub.b  weight(a3),d0     ; - checker's weight   (one byte)
add.b  weight(a2),d0     ; + target's weight
```

The editor's `checkFix` replaces the `beq.w` with two NOPs, so **every checker uses 240**. CB then gains nothing, but
every checker now has the weight bug, computer ones included: an automatic knockdown against anyone 2+ points heavier,
a poor chance against lighter players. In a CB check a computer checker still doubles the penalty risk (8.1).

**The right fix is the other way round: 120 for everyone** (a ROM hacker's correction; replace the `asl.w #1,d0`,
`E340` at $13D70, with a NOP, `4E71`). Weights run 0-120, so 120 - checker + target stays within 0-240 and never
overflows. That one change fixes **both** the weight bug and the CB check: everyone checks with the computer's
formula, where the heavier checker does better, so switching away before contact gains nothing. One balance change
comes with it: the designers' doubling made a person's checks harder (about 10% at equal weight in the example), and
with 120 a person checks as well as the computer (about 30%). The viewer's settings reader recognises this version.

In a survey of 65 Genesis ROMs, all the NHL '94-based league ROMs and `nhl94.bin` have the original code; only one ROM
(WJ2025_v01) has `checkFix` (everyone 240), and none has either weight change or the 120 fix.

**SNES:** no weight bug (the sum uses 16 bits and people get the same base), so nothing to gain from a CB check.
**Confirmed:** heavier checkers knocked their man down 50% of the time, lighter 39%.

### 7.3 Repeated checks are ignored (Genesis)

`FallDown` (the knockdown routine) ignores a call for **the same checker and the same target as the last time it ran
anywhere on the ice**.

- It records the pair on every **knockdown and every wobble**. After you knock a player down, or make him wobble, **your
  later checks on him do nothing** until a knockdown or wobble happens for any other pair anywhere: usually a
  different defender hitting him.
- A check that simply fails its roll (no wobble) never reaches `FallDown` and blocks nothing.
- **Confirmed:** 11 lunges made contact while their pair was blocked, and **none** knocked the man down, against 22%
  (74 of 333) otherwise.
- **SNES:** no such rule.

### 7.4 Wobbles, upends and injuries

- **Wobble (stumble):** instead of falling, a hit player only wobbles if his working **Stickhandling is 24+** (Genesis;
  SNES 12+ of 15), the impact is under a random 16-31 (SNES 10-25), and he hasn't wobbled in the last second.
  - **Genesis:** the wobble lets go of the puck for an instant; he usually picks it straight back up.
  - **SNES:** the wobble keeps the puck. **A second contact within a second of a wobble is always a fall** (no second
    wobble allowed, and the wobble animation is shorter than the wait).
- **Upend (flip fall):** a checker with working Checking 20+ can upend a player facing a certain way. **Code**
- **Injuries (Genesis):** on a knockdown, a 1-in-4 chance of an injury roll, which succeeds more often the harder the
  hit (impact out of 160). **An injury always gives the hitter a roughing minor** (with penalties on). **Whether the
  injured player is out for the period or the game depends on the checker's H/F (fighting) rating.** **Code**, with one
  confirmed case (an injury that came with a roughing call).

### 7.5 Hooks, holds and pokes (Genesis)

**Hook / hold (A without the puck):**

- The reach lasts 0.5 s. A hold instead of a hook happens right after contact with the opponent ahead of you.
- If it catches an opponent in front of the hooker: **both are set to their average speed** (a fast carrier is dragged
  to the hooker's pace), **the victim is frozen for two-thirds of a second** (no pass, shot or check), then the
  hooking / holding penalty roll, the likeliest of any foul.
- **Confirmed:** 86 of 107 successful hooks/holds caught a player **without** the puck (mostly the computer hooking
  whoever is in front of it): penalty risk with no reward. On the **carrier** (22 times) he **kept the puck only 4
  times**; the hooker's team took it 6 times, his own team 4, and it stayed loose (or the whistle went) 8 times.

**Poke check (B without the puck):**

- Lasts 0.27 s. It puts a stick on the puck for a steal roll (6.4), and **trips the carrier if your body touches him
  while you're facing him** (with penalties on, always; with penalties off, a rating roll).
- **Confirmed:** two-thirds of pokes in the recordings were from more than 30 units away and did nothing. Within 30
  units (74 pokes): tripped him 28%, knocked the puck loose 30%, took it 12%, loose then his team got it back 11%,
  nothing 19%.
- **The computer almost never pokes**; it body-checks and hooks.

### 7.6 Skaters and goalies colliding (both systems)

- **A goalie is never knocked down.** Only the skater can go down.
- **Skater with the puck:** **any touch** sends him to the knockdown routine: he falls and loses the puck, unless he can
  wobble (7.4). **Confirmed:** every Genesis carrier with working Stickhandling under 24 fell (22 falls); on the SNES all
  7 wobbles were by players at 13-15 and every carrier under 12 fell. SNES CHI-TOR P3 4:18: wobble, then a fall 0.9 s
  later.
- **Skater without the puck:** he goes down once the built-up impact passes 25: skating into the goalie fast, or
  pushing into him for about 8 frames. **Confirmed:** 28 Genesis and 16 SNES skaters went down skating into a goalie at
  speed.
- **Genesis:** the same-pair rule (7.3) means bumping the same goalie again usually does nothing.
- **Boards:**
  - **Genesis:** when a hit knocks a player into the boards (he must be near them, with the hitter on the inside), the
    **hitter is given the skater's cross-check animation and stops dead**. Nothing excludes goalies, so **a goalie who
    rams a skater into the boards briefly turns into a cross-checking skater sprite**. **Confirmed** once in the
    recordings.
  - **SNES:** no "near the boards" test: any fall in the outer lanes (more than 104 from the middle), behind the net or
    near a corner, with the hitter on the inside, **teleports the player to the boards** for a boards fall. So SNES
    goalies ram skaters into the boards from much farther out. No sprite swap.

---

## 8. Penalties

### 8.1 How a penalty is decided (Genesis)

Most penalties come from one roll (`checkagr`):

- Range = ((40 - Aggression) / 2) x 13, using the working Aggression (0-15, see 8.2).
- **Doubled when a person controls the fouling player** (half as many penalties for people).
- **Halved within about 40 units of the puck** (twice as many near the play).
- A penalty when the roll is at or below the move's threshold.

| What you did | Penalty | Threshold |
|---|---|---|
| **C check, opponent stays up** | **charging or slashing, 50/50** | 4 |
| **C check, opponent knocked down** | **roughing or cross-checking, 50/50** | 3 |
| C check that injures him | roughing, automatically | (no roll) |
| B poke that bumps into him | he falls, then **tripping** | 4 |
| A after bumping into a man ahead | **holding** | 6 |
| A otherwise | **hooking** | 6 |
| Crashing a goalie in his crease | interference (8.4) | (own roll) |

**Confirmed** (the Genesis penalties whose foul moment was recorded): both slashing calls came from body checks that
left the man standing; roughing came after a knockdown; one roughing came with an injury. **In NHL '94, "slashing"
really means a body check that didn't knock him over.**

**Fighting, instigating and delay of game are never called on the Genesis** (the fighting routine is empty).

### 8.2 Aggression wraps around (Genesis)

The working Aggression is cut to 0-15 after the 0-30 calculation, so high values wrap around. **Confirmed** (1,111
samples):

| Editor Aggression (shown as) | Working value | Penalty chance vs Aggression 0 |
|---|---|---|
| 0 (25-29) | 0-2 | x 1.0 |
| 1 (29-38) | 2-7 | x 1.2 |
| 2 (38-47) | 7-12 | x 1.35 |
| **3 (47-62)** | **12-15** (or 0-1) | **x 1.4** |
| **4 (63-80)** | **1-6** | **x 1.1** |
| 5 (81-98) | 6-11 | x 1.3 |
| **6 (99)** | **11-14** | **x 1.5** |

The ranges come from the hot / cold value (-3 to +2); 1-5 were checked against the recordings (rating 5 read 10
there), 0 and 6 follow from the same formula. The last column is the average penalty chance against a working 0, for
any fouling move. **A rating-4 player plays like a rating-1. Ratings 6 and 3 are the most penalty-prone**, though the
whole spread is only about 1.5 to 1.

### 8.3 SNES penalty roll

- Range = (20 - Aggression) x 16, doubled for a person and halved near the puck, **but the doubling and halving act on
  one byte only and wrap**. Person ranges by working Aggression 0-15: 384, 352, 320, 288, 256, 224, 192, 160, 128, 96,
  64, 32, **0**, 224, 192, 160.
- **At working Aggression exactly 12, a person's skater has a range of 0: a penalty on every qualifying contact.** At
  9-11, people are called more often than the computer. **Code** (the recordings had people at 12 only briefly).
- **11 of 14 SNES penalties in the recordings were by players at working Aggression 15**, the value the hot / cold
  bug gives every "cold" rating. On the SNES, cold players take the penalties.

### 8.4 Goalie interference

| | Genesis | SNES |
|---|---|---|
| Who can be called | On a team a person plays, **only the skater he controls**; on a computer team, anyone | **Anyone** |
| Goalie must be in his crease | Yes: within 20 of the middle, 239-266 from centre | Yes, wider: within 40, 228-259 |
| Chance once the hit is hard enough | 5 in (40 - Aggression): about 12-20% | 2 in (20 - Aggression): 15% at Aggression 7, **40% at 15** |

The skater who hits the goalie falls whether or not a penalty is called. **Code** (Genesis; no Genesis interference
call recorded), **Confirmed** for the SNES rule that computer skaters can be called (two of four SNES interference calls
were on computer-controlled skaters of person-played teams). On the SNES, 4 of 14 penalties were interference.

### 8.5 Delayed penalties

- **Genesis:** once one team has a penalty pending (referee's arm up), **the other team can't be called** for checks,
  holds, hooks or trips until the whistle. The team that already fouled can keep taking penalties (any player except
  one already called). **Goalie interference and the roughing on an injury skip this rule**, so they can still put the
  other team in the box at that whistle. **Code**
- **SNES:** no such rule; both teams can be called for anything at one whistle. Both multi-penalty whistles in the
  recordings were SNES games.
- A player who already has a penalty pending can't get a second one (both systems).

### 8.6 Fouls on a breakaway (Genesis)

- If the fouled player is on a breakaway (10.1), the ratings are ignored: the closer he is to the net, the likelier the
  call, up to certain close in. **Code**
- It becomes a **penalty shot**, through a table that is **off by one**: charging is awarded as "slashing", slashing as
  "roughing", roughing as "cross-checking", cross-checking as "hooking", hooking as "tripping", tripping as
  "interference". **Holding and interference give no penalty shot** (just a minor). **Code**

### 8.7 Other whistles

Forced stoppages that aren't penalties: a goalie holding the puck, a person's goalie skating too far out, the puck out
of play, goals, the end of a period.

---

## 9. Faceoffs

### 9.1 What decides the draw (both systems)

**Ratings play no part. It's timing.**

- Each B press starts one swing of the centre's stick: **2 frames wind-up (worth 0), 10 frames mid-swing (worth 8),
  6 frames full sweep (worth 16)**, then he drops back into his stance (worth 0) until you press again. Holding B does
  nothing after the first press.
- At the drop, the home centre wins when a roll of 0-32 (SNES 1-32) is at least 16 - home + away. Equal timing gives
  the home centre 17 in 33 (52%); a full sweep against a centre in his wind-up wins every time.
- **The drop comes at a random moment 3-5 seconds** after the faceoff box appears. The referee's drop animation changes
  only 17 frames (0.28 s) before the drop, too late to react to for a full sweep.

**Confirmed** (Genesis): home won 42 rolls where the timing model predicted 44.4; people mash B 7-11 times in the last
1.5 s and were on the full sweep 23% of the time, mid-swing 47%, standing 26%, as the swing and mashing gaps predict.

### 9.2 Where the puck goes (Genesis)

- **The roll winner's held direction, 3 times in 4.** Otherwise one of the five directions from sideways to straight
  at the other end, at random. The computer never holds a direction, so its wins always go the random way.
- **Plus a push back toward the winner's own end.** Sideways directions come out angled slightly back.
- **Confirmed:** the puck's launch velocity matched exactly one team's "direction plus push" in all 102 faceoffs; a
  person who won the roll got his held direction 37 times in 49 (76%).

### 9.3 The faceoff "win" stat

The game's faceoff-won count (and the stats screen) credits **whichever team first takes possession after the drop**,
not the draw winner. **Confirmed:** it agreed with the roll winner only 52 times in 102.

### 9.4 How to win faceoffs (Genesis)

1. **Mash B as fast as you can** from the moment the faceoff box appears until the drop. Fast mashing keeps you
   swinging with almost no gaps standing still, which is all you can control.
2. **Hold the d-pad toward the teammate you want the puck to reach** (screen direction, 8 ways), the whole time.
   **Never leave it neutral**, or the puck goes forward or sideways toward the other team.
3. Straight back toward your defence is the strongest and most reliable target (the push adds to it). For a winger,
   aim a little forward of him: the push bends a sideways draw slightly back.

---

## 10. Breakaways and penalty shots

### 10.1 What counts as a breakaway (Genesis)

- Decided **at one instant**: as the carrier crosses the attacking blue line, **every other skater on the ice,
  teammates included, must be behind him**. Goalies don't count. A teammate already ahead of you costs you the
  breakaway.
- After the "ding", **it lasts as long as he keeps the puck and keeps skating toward the net**. Stopping, turning back,
  passing or losing the puck ends it; **a defender catching up does not**. So fouls on him use the breakaway rules
  (8.6) all the way in.
- **Confirmed:** every counted breakaway goal came 1.3-2.1 s after its breakaway.

### 10.2 How a penalty shot ends

**Genesis:**

- the goalie gets the puck;
- **once the shooter has shot or passed:** anyone touching the loose puck ends it; otherwise it ends about 1.7 s after
  the shot;
- the penalty-shot clock runs out;
- the goalie's hold timer runs out;
- a goal.

**Losing the puck without shooting ends nothing**, unless the goalie gets it.

**SNES:**

- **anyone takes the puck who didn't already have it**, including the shooter picking up a puck he lost;
- the loose puck moves back away from the net for 48 frames (0.8 s);
- the penalty-shot timer runs out (1,000 frames, about 17 s);
- **the loose puck hits the boards** (whistle) or leaves the rink;
- a goal, or the end of the period.

### 10.3 Penalty-shot bugs

**A penalty shot stopped by an "outside" whistle is retaken** (both systems). The "penalty shot pending" flag is only
cleared when the shot ends through its own routine or by a goal.

- **SNES (explains an observed bug):** a knocked-off net isn't one of the SNES's ending conditions. The whistle comes,
  the flag stays, and the next faceoff sets up **another** penalty shot instead of dropping the puck. The setup hands
  the puck to the shooter where he stands, and he'd lined up for the faceoff: after a net knocked off by the attacker,
  that's the dot just outside the zone. So the new shot starts from the side dot.
- **Genesis (Code):** a net knocked off or the puck over the glass during a penalty shot would likewise lead to another
  penalty shot, but from centre ice, because the Genesis setup moves everyone there.

**Goal after the award whistle (Genesis, explains an observed bug).** Normally a puck reaching the net while the clock
is stopped is ignored. During a penalty shot that test is skipped (the penalty-shot clock replaces the game clock), and
the game switches to "penalty shot mode" **as it starts setting up the shot, a moment before** it blanks the screen and
moves the puck to centre. If the puck is still moving in the net the shooter will attack at that instant, it's a goal,
which cancels the penalty shot. It's rare because the puck has to be still moving inside that particular net at that
moment (the game only checks collisions for objects that moved).

**Ghost puck (Genesis, explains an observed bug).** When the puck goes over the boards it's put in "no collision" mode;
normally the out-of-play whistle and a faceoff follow, and **only the faceoff puck-drop turns that mode off**. If the
puck is flipped out after the award whistle, the clock is already stopped (no out-of-play call), and **a penalty shot
never goes through a puck drop**, so the puck enters the shot still in no-collision mode. Picking it up and shooting
work normally (a separate player-and-puck check), but **the net and boards are skipped**: the shot floats out of the
rink, and the shot ends about 1.7 s later. The goalie's own check doesn't look at that mode, so he could still block
it if it reached him.

**Penalty shot that ends at once (Genesis).** Not explained yet: every "end" flag is cleared when the shot is set up,
and the one path found that could start the shot with its clock at zero can't be taken while the clock is stopped.

---

## 11. Offsides

Only when offsides are turned on (most online leagues play with them off). **Code** throughout: no recorded game had
offsides on.

### 11.1 The rule (Genesis)

- **The moment the puck crosses a blue line into a zone**, if any player of the team attacking that zone is **more
  than 10 units past the line**, the team is flagged offside.
- **Delayed offside with tag-up:** the flag clears once none of them is past the line. Meanwhile the computer's
  attackers retreat on their own.
- While flagged, **one of that team touching the puck more than 20 units inside the zone** is whistled offside.

### 11.2 Genesis quirks

- **One-timers dodge offside.** The offside call lives in the game's "player touched the puck" routine, which runs for
  carrying, receiving, stick deflections, body bounces and the goalie, but **not for the one-timer strike**. An offside
  player can one-time a pass from outside the zone with no whistle, **and the goal counts**.
- **A free band:** in the first 20 units inside the line, an offside team can play the puck without a whistle.
- **Defenders can put attackers offside:** the attacking team is checked whenever the puck enters their zone, even if a
  defender carried it back into his own end. Attackers standing in the zone then become offside, and their next touch
  there is whistled.
- **Backwards entries:** a carrier whose body leads the puck in by more than 10 units (skating backwards) could put
  himself offside.

### 11.3 SNES differences

- Only checked when the puck's carrier, or its last toucher, is on the attacking team.
- No free band: a touch past 88 units from centre is called.
- **The SNES one-timer goes through the touch routine before shooting**, so SNES one-timers can be offside.

---

## 12. The computer players

### 12.1 Offensive and Defensive Awareness: reaction times

**Awareness is how quickly a computer-controlled player reacts.** Each computer player has a countdown; when it runs
out he makes his decisions again, and in between he keeps doing what he last decided. **It never affects the player
you're controlling.**

**Frames between decisions (Genesis):**

| Rating | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| Frames | 15-14 | 14-13 | 13-12 | 12-11 | 11-9 | 9-8 | 8-7 |

About 0.25 s at the bottom and 0.12 s at the top; the range within a rating is hot / cold. **SNES:** Offensive 15-7
frames, a skater's Defensive 22-7 frames (a bigger effect), and the hot / cold bug gives every "cold" rating the
*best* value.

**Which rating counts when:**

| Job | Rating | What the decision covers |
|---|---|---|
| Defenceman, opponents have the puck | Defensive | **Gap control:** re-reads the deepest attacker and sets himself 50 units behind him (never deeper than about the top of the crease area), and picks his side |
| Defenceman, his team has the puck | Offensive | Notices the puck leaving the zone or a turnover (late = caught pinching) |
| Winger or centre, opponents have it | Defensive | Notices a turnover (they follow the puck every frame anyway) |
| **Winger or centre, his team has it** | **Defensive** (a coding slip, both systems) | Picks his spot by the puck's zone; notices a turnover |
| **The chaser** (loose puck, or pressuring the opposing carrier) | Offensive | Re-predicts the target, **hands the chase to whichever teammate is now closest**; twice as fast when the carrier is in the slot |
| Computer puck carrier | Offensive | Considers shooting or passing |
| Computer goalie | Defensive | Re-aims his position every 1-3 frames; goes after loose pucks |

**Every job uses its tick to check whether possession has changed**, so awareness is above all the computer's
**reaction to turnovers**.

**Confirmed:**

- Each player's countdown reloaded with his awareness value 98% of the time (two games).
- After 606 turnovers, computer players who weren't busy switched to defence in **about 125-130 ms** on average, at
  every position, in line with their countdown. Defencemen on offence with Offensive Awareness values 9 / 10 / 11 / 12
  switched after 96 / 132 / 147 / 223 ms on average.
- **Slow reactions came from being busy:** a player locked in an animation (falling, checking, shooting, passing)
  makes no decisions until it ends (620-1,022 ms), and the player sent to chase the puck first only drops back later
  (814-1,372 ms). Forwards are in those situations far more often, usually because they just lost the puck.

**Easy summary:**

- **Higher Defensive Awareness:** defencemen keep better gaps on rushes; everyone switches to defence faster; wingers
  and the centre position themselves faster on offence too; goalies re-aim and chase loose pucks quicker, and (SNES)
  recover faster after passes.
- **Higher Offensive Awareness:** faster to loose pucks; sharper forechecking and backchecking on the carrier; quicker
  hand-offs of the chase; defencemen on offence get back sooner; a computer carrier shoots or passes sooner.
- **Low values** mean the opposite: defencemen beaten on rushes, late retreats, odd-man rushes against.
- Bonuses (2.3) and a loud crowd (14.3) speed reactions up slightly.

### 12.2 Where computer skaters position themselves (Genesis)

Coordinates: x across (right wing +, left wing -), y toward the net the team attacks; boxes are centre +/- range.

**Their team has the puck:**

| Player | Puck in own zone | Neutral zone | Attacking zone | Behind the goal line |
|---|---|---|---|---|
| Wingers | (80 +/- 20, -70 +/- 10) | (100 +/- 20, 58 +/- 5) | (60 +/- 50, 230 +/- 20) | (80 +/- 30, 250 +/- 20) |
| Centre | (0 +/- 60, -70 +/- 10) | (0 +/- 60, 60 +/- 10) | **(0 +/- 40, 170 +/- 30): the slot** | (0 +/- 80, 170 +/- 20) |

Forwards pick a random spot in the box for the puck's zone and keep it until the puck changes zone (or a small random
re-pick). Defencemen hold just inside the blue line (98 from centre), 80 to their side, sliding toward the puck when
it's on their side.

**The other team has the puck:**

- **Defencemen:** 50 units behind the deepest attacker (allowing for his speed), no deeper than about 190-220 from
  centre; 65 to their side, or the middle when the puck is on the other side. Updated only at their awareness ticks.
- **Wingers:** wide on their side (100), at the puck's depth between their own blue line and goal line; they follow
  the puck across when it's on their side.
- **Centre:** the high slot when the puck is in his zone, otherwise halfway between it and the puck.
- **The chaser:** "attack" (straight at the carrier, for 4 seconds) or "contain" (halfway between the carrier and a spot
  just in front of his own net), see 12.3.

The middle of the ice between the blue line and the high slot is often left open when the computer centre is the one
chasing.

### 12.3 How the computer checks and chases

**Decision to check (both systems):**

- **Genesis:** each frame a computer skater rolls in a range of 40 - Checking; **with penalties turned on, the range
  doubles, so computer skaters check half as often.** On a hit, if an opponent is within 30 units exactly in the
  direction he faces, he goes for **a body check (3 in 4) or a hook/hold**, always a hook/hold when the carrier is in
  the slot. **Code**
- **SNES:** range 20 - Checking (also doubled with penalties on), **rolled twice**: at high Checking a computer skater
  goes for a hit almost every time an opponent is in front of him (about 96% a frame at Checking 15 with penalties off,
  64% with them on). Many SNES players sit at 15 because of the hot / cold bug, so **SNES computer players are
  hit-happy.** **Code**

**The chaser's mode** (Genesis): a roll on (40 - Checking) switches him into **attack** for 4 seconds; high-Checking
players attack the carrier far more often. More often on his team's power play, much less on the penalty kill, never
for a defenceman already within 20 of the puck. With the opposing carrier in the slot he gets **+6 Speed** and his
Checking counts double for the check decision. **Code**

### 12.4 How the computer carrier decides (both systems)

Using the "Rgh" pass/shoot bias rating (2.4):

- **Shoot:** a roll in a range of (32 - bias / 2) x 16, **cut to 1/16 within 100 units of the net and doubled for each
  defender in the shooting lane**. Higher bias = more shooting.
- **Pass:** considered on a roll of 12 or less in a range of 16 + bias. Higher bias = fewer passes.
- The bias gets a **double comeback bonus**, so computer teams shoot more when trailing (with the comeback timing bug,
  2.3).
- **Clears:** on the penalty kill, or when nobody pressures its carrier, the computer shoots the puck down the ice from
  its own half and **flips** it from the neutral zone.
- The computer's own one-timers are described in 4.8.

---

## 13. Puck physics

**Genesis**, all **Confirmed** where numbers are given.

### 13.1 Sliding and flying

- **On the ice the puck keeps 89% of its speed per second** (it loses 1/512 a frame). Measured: 89.3% (314 clean
  stretches).
- **In the air there's no friction at all.** Measured: 100.0% (306 stretches). Flips and lifted clears carry until they
  land.
- Gravity pulls it down a fixed amount each frame; **on landing it bounces back up at half its landing speed**.

### 13.2 Boards

- The puck keeps about **98% of its speed along the boards** but only **a quarter of its speed off them**. Rim shots
  ride the boards; pucks fired straight in die. A hard hit adds a little random hop.
- **A shot that touches the boards can never count as a shot on goal.**

### 13.3 The net

- **The crossbar is at height 13.** Anything higher goes over.
- A puck crossing the goal line inside the mouth is a goal.
- **Exactly at the post, or exactly at crossbar height:** a deflection away from the net in a random direction, slowly,
  and **it counts as a shot on goal** (with the "oooh").
- The back and sides of the net bounce the puck like the boards.
- **A puck carried into your own net bounces off.** Only a loose puck can become an own goal. **Code**

### 13.4 A puck still moving after a whistle

Collisions are only checked for objects that moved, and goals are ignored while the clock is stopped (except during a
penalty shot, 10.3).

---

## 14. Line changes, energy and the crowd

### 14.1 Energy and fatigue

- **With line changes Off, energy never drains** (both systems): skating and speed bursts cost nothing. **Fatigue
  doesn't exist and Endurance does nothing.** **Confirmed:** every skater stayed at full energy all game in every
  line-changes-off game recorded (three Genesis, four SNES); with line changes on, energy fell to about a third.
- With line changes On, energy drains while skating and with each burst, recovers on the bench, and lowers shot power,
  stickhandling and (SNES) top speed.
- Genesis amounts (energy runs 0-4096): on the ice a skater loses 33 at a time, every 2-3 seconds (the code tests the
  video chip's beam position, about 1 frame in 128); **while he is above 3/4 his Endurance gives back half its working
  value** (up to 15), so Endurance only slows the first quarter of the drain. Each speed burst costs 204. On the bench
  he gains 9 a second. **Confirmed** in capture5 (line changes on): steps of -33 and -20 to -26 on the ice, -204 at
  bursts, +9 on the bench.
- Genesis "Auto" line changes: energy drains, but every use of it reads full energy.

### 14.2 How the computer changes lines (Genesis, line changes On)

Only while **its puck carrier is in the attacking half before the blue line**, on a 1-in-4 roll at his decision ticks,
**once the line's average energy is down to 75%**. It then sends the new line and **dumps the puck in** to make the
change. **Code**

### 14.3 The crowd

- Shots (+10), big hits (+20) and goals (+30, less for the visitors) raise the crowd's excitement; it fades a little
  every tick. The meter in decibels is the square root of (excitement x 4) + 65.
- **While the meter is at or above the home arena's record** (or 80 dB without one), every computer player on both
  teams reacts a frame faster.
- The "+2 Agility, +2 Speed" crowd bonus in the skating code is hard-wired on for everyone, always; a loud building
  does **not** add speed.
- SNES: a crowd of 110 dB raises hot / cold values (2.2).

---

## 15. League ROMs: settings that change the game (Genesis)

League ROMs are edited with tools such as the NOSE4Web editor
([nhl94dotcom/NOSE4Web](https://github.com/nhl94dotcom/NOSE4Web)), which carries smozoma's smozROM hacks and other
changes found by the NHL94 community (wboy, Tony H, clockwise, smozoma, Brodeur30, kingraph, AverageRangersFan).
Several of them change how the game plays, so **some findings in this document depend on the ROM**. The editor
recognises each change by the code it leaves in the ROM; the NHL '94 Viewer reads the same places
(`tools/systems/genesis_settings.py`) and lists a game's ROM settings in its Help ("This game's ROM").

| Setting | Original game | What league ROMs can do |
|---|---|---|
| Rating scale | 0-6 (x5 on the ice) | 0-15 (x2), with their own overall formulas |
| Hot / cold in play | one value per player (the bug, 2.2) | **one value per rating** (the bug fixed), or **off** |
| Hot / cold in Edit Lines | each rating's own value (not what plays) | **as played**, or not shown |
| Weight bug (7.2) | present | "fixed" (two versions, both of which reverse the computer's checking; see 7.2) |
| C-then-B check (7.2) | works | removed: the editor's version gives everyone 240 (weight bug for all); 120 for everyone fixes it and the weight bug |
| Goalie hold whistle | 140 frames (2.33 s) | longer, shorter, or never |
| A person's goalie, without the puck | kept within 36 to each side and 231 from centre | wider |
| A person's goalie whistle line | 170 from centre (reachable only with the puck) | moved |
| Energy (line changes on) | on the ice -33 every 2-3 s (Endurance gives back up to 15 while above 3/4), -204 a burst; +9 a second on the bench | other amounts, or unlimited stamina |
| Speed burst | 32 when fresh, less when tired | one fixed push for everyone |
| Stopping and reversing | sheds 150 speed a frame | faster or slower |
| Clock | 2.5x real time | real time |
| Base weight | 140 lb + 8 per Weight point | 102-152 lb |
| Checks per player | not kept (penalty minutes there) | kept |
| Second assist | missed when two players pass back and forth | fixed |
| Plus-minus | not kept | kept |
| Three stars | the original choice | fuller formulas |

**What the ROMs in one large collection of league ROMs use** (65 Genesis ROMs, 51 of them NHL '94-based):

| ROMs | Hot / cold | Other changes |
|---|---|---|
| `nhl94.bin` and its playoff / 1-on-1 versions | original (bug) | none |
| CDL, IDL, DPWM, RGDL league ROMs (40+) | original in play, **shown as played** in Edit Lines | goalie range 40 / 224 (wider), checks per player, second assist, plus-minus, fuller three stars |
| WJ2025 | **fixed: one value per rating** | **everyone checks with base 240** (no C-then-B check; weight bug for all), goalie range 40 / 224 |
| Plablegs04, 2on2 | **off** | 2on2: goalie hold 3 s, fixed speed burst 24 |
| QDL Season 1 | original | second assist, plus-minus |

**None of them fixes the weight bug, all use the 0-6 rating scale, and all use the original clock.** So the weight
bug and the C-then-B check work on all of these ROMs, except that on WJ2025 everyone checks with base 240: no
C-then-B check, and the weight bug for computer checkers too.

The SNES game has no such settings known.

---

## 16. Quick reference: bugs and exploits

| | Genesis | SNES |
|---|---|---|
| Hot / cold | One value for all ratings; the shown hot / cold players are fake (league ROMs: often shown as played, fixed or off) | Every "cold" rating maxed (about 46% of all ratings) |
| Comeback bonus | On in the first half of the 3rd, off in the second | Same |
| Weight bug | Person checkers do best when lighter than the target | None |
| CB check | Works (computer formula at contact); twice the penalty risk | Nothing to gain |
| Repeated checks | Same checker on same target ignored until another knockdown | None |
| Aggression | Wraps: rating 4 plays like 1, ratings 6 and 3 most penalised | Person overflow: Aggression 12 = penalty on every contact |
| Penalty-shot table | Off by one; holding and interference give no penalty shot | |
| Delayed penalties | Other team immune (except interference, injury roughing) | No immunity |
| Delayed-penalty sniping | Every shot within 200 perfect | No |
| One-timers | Auto-aimed; goalie reach 12; dodge offside | Stick-aimed; goalie reach unchanged; can be offside |
| Person in net | Full reach (15) always | Faster acceleration |
| Flip | Fixed spot by facing; can be flipped over the glass | Computer dump-in by side, scatters by Passing |
| Weak shooters | No full slapshot (Shot Power < 20) | No limit |
| Awareness slip | Offensive wingers / centre use Defensive Awareness | Same |
| Faceoffs | Pure timing; held direction 3 in 4; stat counts first possession | Same draw rule |
| Penalty shots | Goal after the award whistle; ghost puck after a flip out; retake after outside whistles | Retake after a net knocked off, from the side dot |
| Glove / stick save ratings | Unused | Unused |
| Line changes off | No fatigue, Endurance unused | Same |

---

## 17. Open questions

- **Saved shots the game didn't count** (Genesis): the stick-deflection rule doesn't fully explain them.
- **15 bobbles** with no explanation yet (Genesis): maybe the puck reaching the body before the stick.
- **The penalty shot that ends immediately after the transition** (Genesis): unexplained. Recording the penalty-shot
  flags ($C2EA-$C3E8, $D406-$D454) during a game where it happens would settle it.
- **SNES goalie poke and dive-at-carrier**: which goalies use them.
- **Code-only items worth confirming** when the situations come up: the SNES flip; offsides; penalty odds by situation;
  computer checking frequency with penalties off; Aggression-12 penalties on the SNES; own goals off a carried puck;
  Genesis penalty-shot retakes.

---

## 18. Appendix: units, addresses and sources

### Units

- **Position:** game units. The rink runs about -130 to +130 across and -300 to +300 along; goal lines at +/-268,
  blue lines at about +/-88. About 3 units per foot.
- **Speed:** the game's velocity words. A puck speed of 23,000 is about 78 mph; skaters top out around 9,000.
- **Time:** frames at 60 a second. The game clock runs at 2.5x real time (24 frames per game second).
- **Ratings:** editor values 0-6 (0-15 on some ROMs); working values 0-30 (Genesis) or 0-15 (SNES).

### Useful Genesis RAM addresses (work RAM, $FFxxxx)

| Address | What |
|---|---|
| $B04A + $80 x n | Player records 0-11 (Home 0-5, Away 6-11); +$28/+$2A speed, +$36/+$38 current job, +$40 decision countdown, +$58 animation, +$67-$75 working ratings |
| $C6CE / $CA32 | Team blocks (Home / Away); +$1A2 hot / cold table (16 bytes per roster place) |
| $C2EA, $C2FA | Game mode flags (bit 0: clock stopped; bit 5: offsides on) |
| $C2F2 | Penalty-shot flags (bit 2: under way, bit 3: pending) |
| $B8A2 | Crowd excitement |
| $BDA8 | Faceoff swing states |

### Useful SNES RAM addresses (bank $7E)

| Address | What |
|---|---|
| $1A12 | Hot / cold table (12 bytes per player) |
| $12E3, $1303, $1363, $1383, $1423, $1443, $1483 | Working Agility, Speed, Shot Power, Shot Accuracy, Endurance, Aggression, Checking (a word per object) |
| $0EC3 / $0EE3 | X / Y speed |
| $1E9B, $163A | Penalty shot pending / under way |
| $19BE | Crowd excitement |

### Sources

- Genesis disassembly: [github.com/abdulahmad/NHL94Genesis](https://github.com/abdulahmad/NHL94Genesis)
  (`src/collide94.asm`, `checks94.asm`, `input94.asm`, `crowd94.asm`, `assign94.asm`, `penalty94.asm`,
  `onetimer94.asm`, `replay94.asm`)
- SNES disassembly: [github.com/Mhopkinsinc/NHL94SNES](https://github.com/Mhopkinsinc/NHL94SNES)
  (`src/routines/hockey`, `src/routines/logic`, `src/ram94snes.asm`)
- League ROM settings: the NOSE4Web editor, [github.com/nhl94dotcom/NOSE4Web](https://github.com/nhl94dotcom/NOSE4Web)
  (`src/core/hacks.ts`), after smozoma's smozROM and the NHL94 forums.
- Recordings made with this project's helper; the project's `CLAUDE.md` holds the detailed notes, addresses and test
  methods behind each finding.
