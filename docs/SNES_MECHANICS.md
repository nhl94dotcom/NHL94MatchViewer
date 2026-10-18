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

**Buttons** (from the game's input code, `doinput`):

| Button | With the puck | Without the puck |
|---|---|---|
| **B** | Pass | Poke check / switch player |
| **A** | Shoot (hold for a slapshot) | Speed burst / body check; one-timer while a pass is on its way to a teammate |
| **Y** | Flip (a dump-in) | Hook / hold |
| **X** | | Take the goalie |
| **L / R** | | Take the left / right defenceman |
| **Select** | Line change | Line change |

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
| **Passing** | Pass speed (144 + 4 x Passing), **and the flip's accuracy** (6.3) |
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

---

## 4. Shooting

### 4.1 The nine aim points

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

### 4.3 Shot power

Shot speed is (Shot Power x energy + 20) x the wind-up. **Anyone can wind up fully**: the wind-up code doesn't read
Shot Power, so weak shooters can take full slapshots. **Code**

### 4.4 Auto-aim

Only **computer** shooters are auto-aimed (`shotdiradj` is skipped for a person's player). **Your one-timers go where
your d-pad points.** **Code**

### 4.5 One-timers

- **Triggering:** while your pass is on its way to a teammate, press **A**: control moves to the receiver and he swings
  at it (`onetimerreq`). **Code**
- The swings are their own animations (two of them, never with the puck), seen in the recordings at every "led to a
  one-timer" moment reviewed.
- **The goalie's reach is not cut** against one-timers (the Genesis cuts it), but the **computer goalie loses his
  Agility while the pass is in the air and his next rethink is delayed by each pass** (5.3), so a quick pass across and
  a one-timer still catches him moving slowly.
- One-timers **can be offside** (11).
- How the game times the swing, and what makes one fail, hasn't been read for the SNES. In one recorded game: 7
  one-timers plus 6 swings that missed, against the game's own count of 11 tried.

### 4.6 What counts as a shot on goal

**Not read yet.** Seen in the recordings: a goal can come with no shot on goal counted (a penalty-shot goal, and a
Roenick goal in CHI-TOR).

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
  middle below the crossbar (13); 18-22 out is a post (`checkgoal`). **Confirmed** with the model in 4.7: it predicts
  16.6-17.6 posts where the recordings had 18.
- **No changes for Agility, for a person controlling him, for pad stacks or for one-timers.** (On the Genesis all four
  change his reach.)
- **A diving goalie lets pucks at height 5 or more through.**
- The glove and stick save ratings are looked up and then overwritten: unused.
- **Confirmed:** no goal passed within 12.6 units of the goalie's centre (26 goals); saves a median 12.9.

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

### 5.4 Rebounds and whistles

**Not read yet:** how often he holds the puck, where rebounds go, and the hold and out-of-range whistles.

---

## 6. Passing, the flip and stickhandling

### 6.1 Passing

- **Pass speed** is 144 + 4 x working Passing. **Code**
- How the receiver is chosen and how passes are aimed: **not read yet**.
- **Pass shots** happen: a B pass with nobody to take it flies off the way you pressed (one scored in the recordings).

### 6.2 Bobbles

How a receiver catches the puck hasn't been read for the SNES. Bobbles happen: in one game the user reviewed, ten passes
bounced off the receiver's stick.

### 6.3 The flip (Y with the puck): a computer-run dump-in

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

Stickhandling decides steals (both the carrier's and the stealer's). The exact roll hasn't been read for the SNES.

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

- **Y without the puck** starts a hook or hold (`holdplayer`); what it does to the victim hasn't been read for the SNES.
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

---

## 8. Penalties

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

---

## 9. Faceoffs

**Ratings play no part. It's timing** (`faceoffinput`, `Endfaceoff`; **Code**, not yet checked against recordings):

- Each **new B press** starts one swing of the centre's stick; holding B doesn't start another. How far into the swing
  he is at the drop sets his value.
- At the drop, the home centre wins when a roll of 1-32 is at least 16 - home + away.
- **The held d-pad direction** is stored the whole time. If you win, the puck goes **that way 3 times in 4**, otherwise
  one of five directions at random; with no direction held, always at random. **The puck also gets a push back toward
  the winner's own end.**

So: **mash B, and hold the d-pad toward the teammate you want it to reach** (back to your defence is safest).

---

## 10. Penalty shots

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

### 12.2 How the computer checks

- Each frame a computer skater rolls in a range of 20 - Checking, **twice**, doubled with penalties on; either roll
  under 4 sends him looking for a hit. At Checking 15 that's **about 96% of frames with penalties off, 64% with them
  on**. Many players sit at 15 because of the hot / cold bug, so **SNES computer players are hit-happy**. **Code**
- The chaser's "go straight at the carrier" roll uses 20 - Checking the same way. **Code**

### 12.3 How the computer carrier decides

It uses the pass / shoot bias rating to choose between shooting and passing (`chk4shot`, `chk4pass`), as the Genesis
does; the exact odds haven't been compared. **Code**

### 12.4 Positioning and line changes

**Not read yet** for the SNES.

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
| Person in net | Moves much faster; doesn't make him bigger |
| Flip | A computer dump-in by side of centre; scatters by Passing |
| Weak shooters | No limit: anyone can take a full slapshot |
| Computer skaters | Hit-happy (two check rolls a frame) |
| Faceoffs | Pure timing; held direction 3 in 4 |
| Penalty shots | Retaken from the side dot after a net knocked off |
| Glove / stick save ratings, Fighting | Unused |
| Line changes off | No fatigue, Endurance unused |

---

## 16. Open questions and parts not read yet

- **Aggression 12** (8.1): a person's skater penalised on every qualifying contact, from the code only.
- **Computer goalies' poke and dive**: which goalies use them.
- **Not read yet for the SNES:** what counts as a shot on goal; rebounds and the goalie's hold; pass targeting and
  catching; steals; hooks and pokes; which move draws which penalty; injuries; breakaways; computer skaters'
  positioning and line changes; one-timer timing.
- **The expected-goals model** (4.7) predicts 40.1 goals where 32 were scored: within chance for 32 goals, but worth
  checking as more games are recorded.

---

## 17. Appendix: units, addresses and sources

### Units

- **Position:** game units, as on the Genesis: the rink runs about -130 to +130 across and -300 to +300 along; goal
  lines at +/-268, blue lines at +/-88. About 3 units per foot.
- **Speed:** the game's velocity words; skaters top out around 9,000.
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
