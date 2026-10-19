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

## In brief

One line per chapter: the main finding, then the section with the evidence.

1. **Ratings**: a negative ("cold") hot / cold byte maxes the rating (an unsigned-shift bug): about 46% of all ratings, every game; the hidden bonuses are the Genesis ones, the third-period one backwards here too. ([2](#2-ratings-what-the-game-really-uses))
2. **Skating**: Speed and energy set top speed; most skaters skate at full Speed because of the bug. ([3](#3-skating))
3. **Shooting**: the stick's screen direction picks the aim point (Up is always high); the same perfect-shot roll as the Genesis; long slapshots rarely score; one-timers follow the d-pad. ([4](#4-shooting))
4. **Goaltending**: a body box plus areas from each save frame; a person's held save button adds an area to one side; the computer goalie's hold rule; the net ignores a puck the goalie holds; posts are a 5-unit band. ([5](#5-goaltending))
5. **Passing**: speed comes from the distance (so no rocket pass); the receiver is the nearest teammate in a 90-degree cone; the flip is a computer dump-in; a stick can't play the puck while its no-touch timer runs. ([6](#6-passing-the-flip-and-stickhandling))
6. **Checking**: no weight bug and no CB trick (everyone uses the same formula); no same-pair rule, so a second hit after a wobble knocks him down. ([7](#7-checking-hooking-poking-and-collisions))
7. **Penalties**: a person's penalty range overflows a byte (Aggression 12: every roll a penalty); no delayed-penalty immunity; anyone can be called for interference. ([8](#8-penalties))
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
4. [Shooting](#4-shooting)
5. [Goaltending](#5-goaltending)
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
[Mhopkinsinc/NHL94SNES](https://github.com/Mhopkinsinc/NHL94SNES).

The NHL '94 Viewer's helper records the game's memory about 60 times a second while you play in RetroArch (the Snes9x
core). That gives every player's position, speed, animation and *working* ratings, so the code's rules can be checked
against real games. The checks here used four recorded SNES games (online, NHL94_Classic and SDL16) and several hundred
save states. Numbers like "11 of 14" are counts from those.

Routine and variable names in `code style` are the disassembly's names. Two of its rating arrays are misnamed: the one
called `aggress` holds **Checking**, and `GGSleft` holds a skater's **Aggression**.

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
- A loud crowd (110 dB or more) raises four of each player's values by 2 until it drops under 105 (**Code**), which can
  turn a slightly "cold" (maxed) rating back into an ordinary one.

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
| **Passing** | How steady a pass's speed is (6.1), the speed of a pass with no target (144 + 4 x Passing), **and the flip's accuracy** (6.3) |
| **Stickhandling** | Steals, catching passes, and wobbling instead of falling when hit (12+) |
| **Checking** (array `aggress`) | Knockdowns; the upend fall; **how often computer skaters go for a hit** (12.3) |
| **Endurance** | Energy, which only matters with line changes on |
| **Pass / shoot bias** | Whether a **computer** puck carrier shoots or passes (`chk4shot`, `chk4pass`) |
| **Aggression** (array `GGSleft`) | Penalty odds, with an overflow bug (8.1) |
| **Fighting** | **Never read** |
| **Goalie glove / stick save ratings** | **Nothing.** They are looked up and then overwritten before use |

### 2.5 The numbers on the ratings screens

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
  only + 8, and a computer goalie **loses his Agility again while a pass is in the air**, so he slides across slowly on
  passes. A person's goalie inside his crease skates at three-quarters of his top speed. **Code**

### 3.3 No runaway speed

The Genesis can leave a skater's "deceleration off" switch on, so his speed bursts stack up to twice top speed
(GENESIS_MECHANICS 3.4). The SNES has the same switch: `updateplayers` slows each skater by a friction byte from table
.21 ($FD, $FA, $F7 ... by the frame step) normally and from .22 ($FF, $FF, $FE ...: about a sixth as much friction)
while pflags bit 0 is set, and above top speed `playeracc` adds nothing but takes nothing off either, so bursts could
stack the same way. But the switch is **turned off reliably**: only `asspassrec` sets it (on the receiver of a pass),
and it is cleared when his wait for the pass ends (`asspassrec` .6: anyone has the puck, or the wait runs out), when
**any stick touches the puck** (`puckstick`, which clears it for that player first thing), by `assnearest` and at
faceoffs (`resetplstuff`). `FallDown` never sets it, so the Genesis's boards-fall route doesn't exist. **Code**

**Confirmed** (analysis/snes_runaway_study.py, eight SNES games): 791 stretches with the switch on, a median 0.3 s,
90% under 0.6 s, the longest 2.7 s; the fastest skater with it on went 10,156 (top speed is about 9,000), against
19,400-20,100 in the Genesis runaways.

---

## 4. Shooting

### 4.1 The nine aim points


![The nine aim points in the SNES net, attacking up and down the screen](img/aim_points_snes.svg)

Every shot is aimed at one of nine points in the net (`doshot`, `shotsets`), picked by **the direction the d-pad is
held as the shot is taken**, in **screen** directions:

| Held | Aim |
|---|---|
| Up-left / Up / Up-right | High: the screen's left / middle / right |
| Left / nothing / Right | Middle height: left / middle / right |
| Down-left / Down / Down-right | Along the ice: left / middle / right |

The points are 15 units either side of the middle and at heights 12, 6 and 0. Because it is screen direction, when you
attack down the screen the d-pad's left is the shooter's right, and **up is always high**: people pushing toward the top
net put their shots high. **Confirmed**: at every person's shot in two games the recorded direction was the d-pad's, and
goals crossed the line where they were aimed.

### 4.2 Perfect shot or scatter

- **Within 200 units of the aim point** (about 65 feet), a roll decides whether the shot goes **exactly** where aimed:
  chance (Shot Accuracy + 1) / (Shot Accuracy + 16). That's at most **52%** (Shot Accuracy 15), 35% at 7.
- **Beyond 200, never perfect.**
- Otherwise random scatter is added: (shot speed / 8 - Shot Accuracy + 16) x distance / 64, bigger for harder,
  longer and less accurate shots.
- **Confirmed**: 60% of 112 close shots left the stick on the aim point, none of 15 from farther out; 63 of the 112
  were by shooters at the maximum Shot Accuracy (the hot / cold bug).
- There is **no delayed-penalty "snipe"** (the Genesis makes every shot perfect while the other team has a penalty
  coming; the SNES doesn't).


**Shooting at an open net** (the goalie pulled, or far out of his crease). Nothing in the game makes shots at an open
net less accurate (the "goalie pulled" test in the shot code only ever looks at the *shooting* team's own goalie; and
unlike the Genesis, SNES one-timers follow the stick, so they don't get the Genesis's high open-net aim), but
three things from the rules above make them miss: such shots are often taken from far out, where a shot is never
exact and the scatter is wide; the scatter only ever pushes the puck *up*, so a high aim has no room under the
crossbar; and the d-pad direction is the aim, so attacking *up* the screen, pushing toward the net aims high. Worked out
from the game's own scatter rule for an average shooter (working Shot Accuracy 10, a 15,000 shot) at an empty net, the chance it goes in by aim and distance:

| Aim (d-pad at the release) | 60 units | 120 | 180 | 220 | 300 |
|---|---|---|---|---|---|
| Nothing held (middle) | 100% | 87% | 62% | 22% | 3% |
| Left or right | 79% | 68% | 58% | 22% | 3% |
| Up (high) | 54% | 49% | 45% | 3% | 0% |
| Up-left / up-right | 50% | 47% | 45% | 3% | 0% |
| Down (along the ice) | 100% | 100% | 78% | 41% | 5% |
| Down-left / down-right | 79% | 75% | 72% | 41% | 5% |

![The chance an aimed shot goes into an empty net, by aim and distance](img/empty_net.svg)

**At an open net: get within about 180 units (60 feet) if you can, and hold Down or nothing as you shoot, never Up.**
Not yet checked on recorded shots (only five recorded shots had the goalie far out or pulled; they hint at more going
wide: 24% wide with him 35-70 units out, 16% in his crease).

### 4.3 Shot power

Shot speed is (Shot Power x energy + 20) x the wind-up. **Anyone can wind up fully**: the wind-up code doesn't read
Shot Power, so weak shooters can take full slapshots. **Code**

### 4.4 Auto-aim

Only **computer** shooters are auto-aimed (`shotdiradj` is skipped for a person's player). **Your one-timers go where
your d-pad points.** **Code**

### 4.5 One-timers


![One-timer timing and what made them score](img/one_timers.svg)

- **Triggering:** while your pass is on its way to a teammate, press **A**: control moves to the receiver and he swings
  at it (`onetimerreq`). **Code**
- The swings are their own animations (two of them, never with the puck), seen in the recordings at every "led to a
  one-timer" moment reviewed.
- **The goalie's reach is not cut** against one-timers (the Genesis cuts it), but the **computer goalie loses his
  Agility while the pass is in the air and his next rethink is delayed by each pass** (5.3), so a quick pass across and
  a one-timer still catches him moving slowly.
- One-timers **can be offside** (11).
- **The swing and the strike** (`asspassrec`): the swing (forehand or backhand by the angle to the net) starts the
  moment the request is made, and **the game doesn't time it to the puck** (the Genesis starts the downswing itself
  and holds the wind-up up to 0.8 s). While the swing runs, the receiver's stick won't catch the puck (his `nopuck`
  is held at 10); the puck has to come **within 8 units of his blade** before the swing ends (the Genesis: within 10,
  pulled in from 18). Then it's struck at a fixed power, **aimed by the d-pad held at the strike** (computer
  one-timers: no direction, then the computer's auto-aim), and counted as a one-timer; a B press while waiting cancels.
  The game counts every swing too (`tmOneTimerSwings`). **Code.**
- **Computer teams** one-time on their own only in the attacking zone (past their blue line), and quickly: a coin flip
  each frame while the pass comes.
- **Confirmed timing** (5 SNES games, a person's A press): one-timers that connected struck 0-0.59 s after the press
  (median 0.20 s); swings that missed ended a median 0.47 s after it. **Press A no more than about 0.6 s before the pass
  arrives**; the Genesis allows about 0.9 s. In one recorded game: 7 one-timers plus 6 swings that missed, against the
  game's own count of 11 tried.

### 4.6 What counts as a shot on goal

As on the Genesis (`ChkShotStat`): the shot counts when the puck touches the goalie's body box (`puckgoalie`) or he
catches it with his stick or glove (`puckglue`), while the "shot taken" flag set at the release still stands; any
other touch on the way (`a2touchpuck`) clears the flag, and nothing counts while the clock is stopped (penalty shots).
A hard shot that **deflects off his stick or glove area** (faster than 13,000; 7.5) clears it too, so it is never
counted, even though his body box gets the puck a moment later. **Code**

**Which shots that is differs from the Genesis.** The SNES goalie's stick / glove area (5.1) comes with a height
window from his sprite frame: none in his ready stance, low (0-6) in the stick saves, but **7-15 off the ice in the
glove saves**. So hard high shots that meet his glove deflect uncounted as well as hard low ones off his stick.
**Confirmed** (5 SNES games, shots that reached the goalie): not counted aimed high 6 of 29, middle 15 of 104, along the
ice 2 of 14: no height stands out, unlike the Genesis (ice 41%, high 3%).

**Direction:** people aim even more by direction than on the Genesis (attacking up the screen 49% of their shots high,
attacking down 2%), but with no height uncounted more than another, that makes little difference: 17% of the shots
that reached the goalie went uncounted going up, 14% going down. One of the stick saves is lopsided (facing down,
the top net's goalie, its area reaches 8 off the ice with a radius of 8; facing up, 2-5 with a radius of 2), which
would make shots at the top net a little more likely to go uncounted. A goal can also come with no shot counted (a
penalty-shot goal, and a Roenick goal in CHI-TOR).

### 4.7 Expected goals from the game's own rules

As on the Genesis, the chance a shot goes in can be worked out by playing it out the SNES game's way, many times; the
NHL '94 Viewer does it for every SNES shot and one-timer (`tools/xg_snes.py`, 400 times each):

1. **The aim**: the recorded d-pad direction (one-timers too; computer shooters' aim as the game set it).
2. **The shot** (`doshot`): exact with the perfect-shot chance (4.2), else the game's scatter (distances by its
   approximate length), at the recorded speed and the shooter's working Shot Accuracy.
3. **The flight** (`updateplayers`): two frames a game step, gravity 96 a frame, the lift worked out to cancel it.
4. **The goalie** moves as the computer goalie does (5.3), with his save move and its frames (5.2); a person in net is
   moved the same way. He stops the puck with his body box or his frame's stick / glove area (5.1).
5. **The net**: a goal within 17 of the middle under 13 at y 259, a post to 22 (5.1).

The one number fitted to the recordings is a 2-unit random spread for the emulated goalie's position. **Checked** on
175 unblocked shots in five recorded SNES games: 40.1 expected goals against 32 scored (computer in net 25.7 / 21,
people 14.4 / 11), the predicted posts and misses matching, and a log loss of 0.27 against 0.48 for giving every shot
the same chance. Getting there showed what matters on the SNES: with the goalie frozen where he was at the release the
model said 62 goals, carrying on at his speed 50; it's his reaction during the shot, and above all that **he keeps
sliding through his save move**, that makes the saves.

The viewer shows SNES xG on shots, cards, team stats, the season page and the xG map (one-timers there face goalies as
they were at recorded one-timers, usually still moving across after the pass).

---

## 5. Goaltending

### 5.1 Saves are geometry

The goalie stops a puck only if it physically reaches him (`checkpuckcoll_ccx`), but the shape differs from the
Genesis:

- **His body is a fixed box**: the puck within 11 units on one side and 10 on the other, across and along, at any
  height.
- **His stick / glove area**, which depends on the sprite frame he shows (`GetHot`, `GetFrameHot`): a circle around the
  frame's hot point, within a band of heights, both read from the frame's record (frame number - 1, as the drawing code
  reads it). A save move's frames change it.
- **The net:** a goal when the puck's centre crosses the net's front (9 units out from the net, y 259) within 17 of the
  middle below the crossbar (13); 18-22 out is a post (`checkgoal`). **Posts are why SNES shots ring off the iron so
  often:** the post is a 5-unit band on each side of a 35-wide mouth, against a 1-unit band beside a 41-wide mouth on the
  Genesis:

| | Goal if it crosses within | Post band, each side | Crossbar | Goal mouth |
|---|---|---|---|---|
| Genesis | 20 of the middle | **1 unit** (20-21) | a 1-unit band at height 13 | 41 wide |
| SNES | 17 of the middle | **5 units** (18-22) | none (anything at 13 or higher passes over) | 35 wide |

  The aim points are 15 from the middle, so a shot aimed at a side has only 2 units of goal outside it, then 5 of post.
  A post deflects the puck away at a random speed and angle, counts as a shot on goal, and ends any breakaway or
  one-timer credit. **The crossbar can't be hit:** the code tests for height 13 only after it has already let anything at
  13 or more pass over (dead code). **Confirmed** in the recordings: 19 of the 234 SNES shots that reached the net hit a
  post (8.1%), against 7 of 316 on the Genesis (2.2%).
- The expected-goals model (4.7), which uses these widths, predicted 16.6-17.6 posts where the first five SNES games
  had 18.
- **No changes for Agility, for a person controlling him, for pad stacks or for one-timers.** (On the Genesis all four
  change his reach.)
- **A diving goalie lets pucks at height 5 or more through.**
- The glove and stick save ratings are looked up and then overwritten: unused.
- **Confirmed:** no goal passed within 12.6 units of the goalie's centre (26 goals); saves a median 12.9.


**No "through the legs" or shoulder-save bobble here** (the Genesis ones are in GENESIS_MECHANICS 5.3 and 5.5): the SNES
goalie's save frames add hit areas 12-28 units out to the side on top of his body box, rather than moving a blind ring
over his middle, and checkgoal returns at once when the puck's carrier is a goalie, so a held puck can't be stripped at
his net.

### 5.2 Save moves

At a rethink with the puck going to cross within 24 of the middle in under 19 frames, he picks a move
(`GoalieSaveList`) by the puck's direction against the way he faces (the game's 8-way directions are coarse: anything
between 1:2 and 2:1 counts as diagonal) and its height: well to one side, a **sprawl**; to one side and low, a **stick
save**; high, a **glove / blocker save**; a pad stack while the puck is still carried; a **butterfly** for a slow puck
straight at him. Most moves hold a single frame; his speed is halved as he starts, **and he keeps skating through the
move** (it sets the animation lock `pfalock`, not `pf2aip`, which is what stops his routine), so he slides on toward
the crossing point. **Confirmed** (the model's goalie in 4.7 lands where the recorded goalies did).

### 5.3 The computer goalie

- **Passes slow him down:** every pass delays his next rethink by half his Defensive Awareness value plus one frame,
  and he loses his Agility while a pass is in flight. **Code**
- **Attacking moves:** a **poke check** at a carrier within 35 units in front of the goal line, on a random roll (about
  1 in 26 per frame), then 4 seconds before he can poke again; and a **dive at the puck carrier** when the puck is within
  45 and an attacker within 60 (about 1 in 32 per frame), then 6 seconds before he can dive again. **Code**. In four
  games no computer goalie dived at all (all 6 dives were by people), so which goalies use these is unclear.
- **Covering the puck** (`assgoalie`): once a computer goalie has held the puck a moment, now and then (a 1-in-4 roll)
  he checks the opposing skaters. **If one is within 20 units of the puck he drops onto it and covers it** (`SPAgcover`)
  for 90 frames; within 35, he waits; with nobody within 35 he looks to pass it out (`chk4pass`). A goalie a person
  controls never does this: it's part of the computer goalie's routine. **Confirmed** once (CHI-CGY, the last seconds:
  Chicago's computer goalie took the puck at 0:11 and covered it from 0:09 to 0:05).
- **Positioning** (`assgoalie`). He rethinks every half his Defensive Awareness reaction value (`aidef / 2`: about 3
  to 11 frames, slower than the Genesis goalie's 1-3), each time picking a spot: where the puck is heading (12-24
  frames of its motion ahead, a little at random) on an **ellipse 26 across and 20 out** in front of his net, or the
  puck itself once it is near his goal line. **Once the puck will cross his goal line within 24 of the middle in under
  35 frames** (worked out every 5 frames), he heads for that crossing point, and under 19 frames starts a save move
  (5.2). He skates like a player (acceleration from Weight and Agility, + 8 for a goalie, his Agility taken away while a
  pass is in the air; top speed from Speed), and a computer goalie with nowhere to go halves his speed each step.
  **He stops dead when an opposing carrier winds up a shot** while skating mostly up or down the ice.
- **Confirmed:** emulating all this and driving it with the recorded puck, the goalie lands a median 0.8 units from the
  recorded goalie when the puck arrives (100 shots at computer goalies; 78 within 3 units).

### 5.4 Holding the puck and rebounds

`puckgoalie`, when the puck touches his body box (5.1). **Code**; the hold rule **Confirmed** (below).

- **The shot is counted** (`ChkShotStat`) and the touch clears the "shot taken" flag, unless he's in a dive and the
  puck is 5 or more off the ice: then it goes through him untouched.
- **He holds it** when both the puck's sideways and its up-and-down speed are under a random threshold between 8,192
  and 8,192 + (2 + his Puck Control) x 512: at most about 17,000 for the best puck handler. Otherwise **it bounces off**,
  straight out from his centre through where it touched him, slowly (the speed comes from how far off-centre it hit,
  not from the shot), its up-the-ice direction set against the way he's moving.
- **Differences from the Genesis:** no rule making him hold less in close, and a diving goalie can still hold a low
  puck; on the Genesis the threshold is about twice as high, so a Genesis goalie holds harder shots.
- **His glove and stick save ratings are looked up and never used** (as on the Genesis).
- A puck carried into him is knocked loose (the carrier can't touch it for 20 frames).
- **Confirmed** (102 SNES saves, the faster speed component just before the save): 17,000 or more, held at once 4 of 41
  (10%); 8,192-17,000, 28 of 45 (62%), the random range at work; under 8,192, 10 of 16 (the rule says all; the sampled
  speeds and the "held at once" test are rough).
- **Not read yet:** the hold and out-of-range whistles.

### 5.5 The save button for a person in net (A, held)

**Code** (`assgoalie`): while a person's goalie **holds A** without the puck, every rethink starts a save move. No shot
is needed. The move is chosen as for the computer goalie (5.2): by the puck's direction against the way he faces, and a
pad stack while the puck is still carried. His speed is halved, and **he can't steer until the move ends**: the
animation lock stops `doinput`. (Holding A while carrying the puck does nothing for a goalie; on the Genesis the save
button is C, a single press.)

**Unlike the Genesis, the move makes him bigger, on one side.** Standing, he stops only what reaches the box around his
body (about 10 units each way, 5.1). A save frame adds an area off to one side (the frame's hot point and radius, within
a height band):

| Move | Extra area | Reaches about |
|---|---|---|
| Glove / blocker | 6-12 to the side, radius 5-6, heights 7-15 | 18 |
| Stick save | 12 to the side, radius 5, low | 17 |
| Pad stack | 15 to the side, radius 6-8, low | 22 |
| Sprawl | 19-28 to the side, radius 2-3, low | 30 |
| Butterfly | 13-18 to the side, radius 1-3, low | 20 |

No effect on rebounds: the SNES hold rule (5.4) doesn't look at his animation.

**Recordings:** people pressed A on 25 of the 39 shots at a goalie they controlled, 22 times before the release, which
gave mostly pad stacks (16). With A, 8 goals in 25 (xG 0.41 a shot); without, 4 in 14 (0.32). Too few to say more.

### 5.6 Early save moves and cross-crease goals

- **No wind-up save rule.** The Genesis computer goalie drops into a pad stack the moment a shot is wound up close in
  (GENESIS_MECHANICS 5.6); the SNES one doesn't. Instead, **when an opposing carrier starts a shot or one-timer swing
  while skating mostly up or down the ice** (sideways speed under twice his up-and-down speed), the goalie's speed is
  set to zero once (`goaliestopped`). He picks up again at his next rethink. A carrier moving across doesn't trigger it.
- **During a wind-up his positioning spot widens:** 34 across and 28 out, instead of 26 by 20. **Code**
- **Save moves don't freeze him:** his speed is halved and he keeps sliding and rethinking through the move (5.2).
- **Recordings:** a save move started before the release on 9 of 121 SNES shots at computer goalies, a median 0 ms
  before (Genesis: 35 of 213, a median 92 ms before).
- **Cross-crease goals still happen,** for other reasons:
  - he rethinks only every 3-11 frames (Genesis: 1-3);
  - his standing body is only about 10 units each way (Genesis reach 12-15);
  - he aims for the puck itself with a look-ahead (the Genesis goalie aims halfway between puck and carrier).

  Recordings: 8 carries that crossed the middle within 90 of the goal line, 5 shots, 3 goals (Genesis 12, 9, 3).

### 5.7 A goalie holding the puck can't be pushed in

`checkgoal` returns at once when the puck's carrier is a goalie, so the net never touches a puck the goalie holds. Pushing
him back into the net with it does nothing. On the Genesis the net strips the puck from him at the goal line, and a
nudge then scores (GENESIS_MECHANICS 5.9). **Code**

### 5.8 Long slapshots

Worked out with the expected-goals model's rules (4.7), the computer goalie started where recorded SNES computer
goalies stood at shots from 90+ units, working Shot Accuracy 15, aimed just inside a post or at the middle at
mid-height. Percent that go in (`analysis/goalie_study.py longsnes`):

| Spot | 16,000 | 20,000 | 24,000 | 28,000 |
|---|---|---|---|---|
| 120 out, 25 to the side: far / near / middle | 2.0 / 2.5 / 2.5 | 1.7 / 2.5 / 2.4 | 2.2 / 4.3 / 2.3 | 3.7 / **7.1** / 2.8 |
| 120 out, 60 to the side | 2.6 / 2.6 / 2.6 | 2.3 / 4.5 / 2.7 | 2.0 / 4.4 / 2.1 | 4.4 / **9.1** / 2.3 |
| 160 out, 25 to the side | 1.8 / 1.7 / 2.4 | 2.3 / 2.2 / 2.1 | 1.7 / 2.0 / 2.0 | 2.0 / 2.5 / 2.1 |
| 200 out, 25 to the side | 0.5 / 0.7 / 0.9 | 0.7 / 0.8 / 0.9 | 0.6 / 0.6 / 0.4 | 0.4 / 1.0 / 0.6 |

- **Long slapshots hardly ever score on the SNES**: a few percent at best, against 15-23% for the hardest Genesis
  shots from 40 feet (GENESIS_MECHANICS 5.8). The SNES goalie keeps sliding through his save moves, which also stretch
  his reach to one side, and the goal mouth is narrower (35 against 41) with wide posts.
- **Power helps less, and only at the near post**: with the hardest shots the near post is about twice as good as the
  far one. Shot Accuracy changes little (a 26,000 shot 120 out at the near post: 2.9% at working 5, 4.5% at 15).
- **Confirmed** on the recordings: 1 goal in 17 SNES slapshots from 100-200 units out (the model's xG for them: 0.7),
  against 5 in 39 on the Genesis (xG 4.5).

---

## 6. Passing, the flip and stickhandling

### 6.1 Passing

- **A pass to a teammate gets its speed from the distance** to where he will be (`dopass`): 64 (x 256 = 16,384) up to
  about 96 units (32 feet), two-thirds of the distance in between, 80 (20,480) from 120 units (40 feet) on. **Passing
  only makes it steadier**: a random +/-(16 - Passing) x 256 is added, about +/-4,000 for a poor passer, almost nothing
  for a good one. A pass with no target leaves at 144 + 4 x Passing. **Code** Because the speed comes from the
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

Pressing Y hands your skater to the computer's dump-in routine (`assdumpin`, `DumpInTarget`). **Code**; no SNES flip in
the recordings yet.

- **Outside the attacking zone:** deep in the zone between the circle and the corner (80 from the middle, 180 toward the
  goal), **on whichever side of centre you're on**. Facing doesn't choose.
- **Inside the zone:** in front of the net.
- **A goalie:** about the middle of the ice, moved by his facing.
- He **first turns to face up the ice** (within 45 degrees), so it comes out late if he was facing sideways.
- **It scatters by up to +/-(20-25 + 2 x (15 - Passing)) across and +/-(20-70) along** (the deeper targets 70), so
  **Passing is flip accuracy**.
- A computer carrier inside the attacking zone shoots instead.

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
- The upend (flip fall) depends on Checking (threshold not read).

### 7.3 Hooks, holds and pokes

- **Y without the puck** starts a hook or hold (`holdplayer`; the hook is animation `SPAhook`, then `SPAhook2`); what it
  does to the victim hasn't been read for the SNES.
- **The get-up glitch** (known in the community: a knocked-down player gets up at once if his person presses the hook
  button). The SNES input code checks the hook button **before** the animation lock that holds a falling player down,
  and `holdplayer` refuses only during a speed burst, so the hook animation replaces the fall and he is back up. The
  Genesis checks the lock first, so it can't happen there. **Confirmed**: three times in the recordings a person pressed
  Y while down and was up and hooking 0.5-1.2 s later, where falls otherwise last 2.3 s.
- **B without the puck** near the carrier is a poke check (its animation confirmed from the recordings); its effects
  haven't been read.

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

---

## 8. Penalties


![Penalty chance per check by working Aggression, Genesis and SNES](img/penalty_chances.svg)

### 8.1 The penalty roll, and its overflow (`checkagr`)

- Range = (20 - Aggression) x 16, using the working Aggression; a penalty when the roll comes in under the move's
  threshold.
- Doubled for a person's player and halved near the puck, **but the doubling and halving act on one byte only and
  wrap**. A person's ranges by working Aggression 0-15: 384, 352, 320, 288, 256, 224, 192, 160, 128, 96, 64, 32, **0**,
  224, 192, 160.
- **At working Aggression exactly 12, a person's skater has a range of 0: a penalty on every qualifying contact.** At
  9-11, people are called more often than the computer would be. **Code** (people were at 12 only briefly in the
  recordings).
- **11 of 14 penalties in the recordings were by players at working Aggression 15**, the value the hot / cold bug gives
  every "cold" rating. **Cold players take the penalties.**

Which move draws which penalty hasn't been mapped for the SNES. The penalties the game knows (its rule table): roughing,
charging, slashing, cross-checking, hooking, tripping, penalty shot, interference, holding, fighting, instigator.

### 8.2 Goalie interference (`checkint`)

- **Anyone can be called**, your computer-controlled teammates included. **Confirmed**: two of the four interference
  calls in the recordings were on computer-controlled skaters of person-played teams.
- The goalie must be in his crease: within 40 of the middle, 228-259 from centre.
- With the goalie's impact 31 or more, it's called 2 times in (20 - Aggression): 15% at Aggression 7, **40% at 15** (a
  "cold" player).
- The skater falls whether or not a penalty is called.
- 4 of the 14 penalties in the recordings were interference.

### 8.3 Delayed penalties

- A foul can be called with play going on (a delayed penalty) until the whistle. **Confirmed**.
- **There's no immunity for the other team:** both teams can be called for anything at one whistle. **Confirmed**: both
  multi-penalty whistles in the recordings (a cross-check then interference by the other team at one whistle).
- A player who already has a penalty pending can't get a second one. **Code**

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
  near the puck) that's about 1 check in 100 near the puck; a person's wrapped range can be far smaller (8.1).
- **Recordings** (5 SNES games, 15 penalties): interference 4, roughing 3, cross-checking 2, holding 2, tripping 2,
  slashing 1, one with code $30 (not read); 9 by a person's skater, 6 by the computer's. Too few to check the rates.

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
does; the exact odds haven't been compared. **Code**

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

So SNES defencemen join the rush and drop back by zone rather than all-or-nothing. (Until 2026-10-18 this said SNES
wingers hold up where Genesis ones follow the puck down; both hold at -158.) What happens as the puck crosses a blue
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
  Endurance does nothing**. **Confirmed**: every skater stayed at full energy all game in all four recorded games.
- With line changes On, energy scales top speed (down to half) and shot power.
- The crowd's excitement rises with shots, hits and goals (`CwdExciteLvl`). At 110 dB it raises four hot / cold values
  of every player by 2 until it falls under 105 (2.2). **Code**

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
| Aggression | A person's skater at working 12: a penalty on every qualifying contact (**Code**); cold (maxed) players take most penalties |
| Interference | Anyone can be called; 40% for a maxed-Aggression player |
| Delayed penalties | No immunity: both teams can be called at one whistle |
| One-timers | Go where the d-pad points; goalie reach unchanged, but the computer goalie is slowed by passes; can be offside |
| Person in net | Moves much faster; taking him doesn't make him bigger, but holding A (a save move) adds a stick / glove / pad area on one side |
| Wind-up | No Genesis-style early pad stack; he stops once when a carrier winds up skating up or down the ice |
| Goalie pushed in | Impossible: the net ignores a puck the goalie holds |
| Flip | A computer dump-in by side of centre; scatters by Passing |
| Weak shooters | No limit: anyone can take a full slapshot |
| Computer skaters | Hit-happy (two check rolls a frame) |
| Turnovers | Computer skaters switch to defence at once (no awareness delay, unlike the Genesis) |
| Faceoffs | Pure timing; held direction 3 in 4 |
| Penalty shots | Retaken from the side dot after a net knocked off |
| Glove / stick save ratings, Fighting | Unused |
| Line changes off | No fatigue, Endurance unused |

---

## 16. Open questions and parts not read yet

- **Aggression 12** (8.1): a person's skater penalised on every qualifying contact, from the code only.
- **Computer goalies' poke and dive**: which goalies use them.
- **The expected-goals model** (4.7) predicts 40.1 goals where 32 were scored: within chance for 32 goals, but worth
  checking as more games are recorded.

---

## 17. Appendix: units, addresses and sources

### Units


![The rink with its landmarks in game units and feet](img/rink_feet.svg)

- **Position:** game units, as on the Genesis: the rink runs about -130 to +130 across and -300 to +300 along; goal
  lines at +/-268, blue lines at +/-88. About 3 units per foot.
- **Speed:** the game's velocity words; skaters top out around 9,000.

Distances are in the game's own units: **about 3 units to a foot**, so divide by 3 for feet. Speeds are the game's
speed numbers; a puck moves its speed / 4,096 units a frame, 60 frames a second.

**The rink:**

| Landmark | Units | Feet |
|---|---|---|
| Rink length / width | about 600 / 260 | about 200 / 87 |
| Centre of the rink to each goal line | 268 | about 89 |
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

- SNES disassembly: [github.com/Mhopkinsinc/NHL94SNES](https://github.com/Mhopkinsinc/NHL94SNES)
  (`src/routines/hockey`, `src/routines/logic`, `src/routines/stats`, `src/ram94snes.asm`)
- Recordings and save states read with this project's helper; the project's `CLAUDE.md` holds the detailed notes,
  addresses and test methods behind each finding.
