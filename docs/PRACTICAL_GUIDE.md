# A Practical Guide to NHL '94 Mechanics

What the game's code means for you as a player: how to read the ratings screen, how to pick a lineup, and what actually
works on the ice. Everything here comes from [GAME_MECHANICS.md](GAME_MECHANICS.md), which has the details, the
formulas and how each finding was checked. Section numbers like (7.2) point there.

Unless a heading says SNES, this is about the **Genesis** game (`nhl94.bin` and the league ROMs built on it). The SNES
game differs in important ways; [section 15](#15-snes-whats-different) collects them.

Distances: the game measures the rink in units of about **a third of a foot** (blue line to goal line is 180 units, 60
feet).

## Contents

1. [Reading the ratings screen](#1-reading-the-ratings-screen)
2. [What each rating does for you](#2-what-each-rating-does-for-you)
3. [Choosing your lineup](#3-choosing-your-lineup)
4. [Faceoffs](#4-faceoffs)
5. [Skating and carrying the puck](#5-skating-and-carrying-the-puck)
6. [Shooting](#6-shooting)
7. [One-timers](#7-one-timers)
8. [Passing and the flip](#8-passing-and-the-flip)
9. [Checking](#9-checking)
10. [Taking the puck: pokes and hooks](#10-taking-the-puck-pokes-and-hooks)
11. [Penalties](#11-penalties)
12. [Goaltending](#12-goaltending)
13. [Breakaways and penalty shots](#13-breakaways-and-penalty-shots)
14. [Your computer teammates](#14-your-computer-teammates)
15. [SNES: what's different](#15-snes-whats-different)
16. [Myths: things that don't matter](#16-myths-things-that-dont-matter)
17. [Cheat sheet](#17-cheat-sheet)

---

## 1. Reading the ratings screen

### 1.1 The numbers come in seven steps

The 0-99 numbers on Edit Lines, Team Roster and the player cards look fine-grained, but each rating is really one of
**seven steps** (0 to 6). The game turns the step into a number and adds a random hot / cold value, so each step covers
a band of numbers:

| You see | Step | In play (Genesis, out of 30) | In play (SNES, out of 15) |
|---|---|---|---|
| **99** | 6 | 30 | 15 |
| **81-98** | 5 | 25 | 12 |
| **63-80** | 4 | 20 | 10 |
| **47-62** | 3 | 15 | 7 |
| **38-47** | 2 | 10 | 5 |
| **29-38** | 1 | 5 | 2 |
| **25-29** | 0 | 0 | 0 |

(29, 38 and 47 can be either of two steps.) Below 50 the game squashes the numbers, so the low bands are narrow. **The
jump from one band to the next is the real difference between players.** Weight is the exception: it's shown in pounds
(140 lb plus 8 lb a step; league ROMs may start elsewhere).

### 1.2 What the position inside a band means

It depends on your game and ROM:

- **Genesis, original ROM** (`nhl94.bin`, the GENS Classic leagues): **nothing at all.** An 81 and a 98 play exactly
  the same. The game shows each rating with its own random value, but because of a bug it plays every rating with one
  other value that it never shows (2.2). That hidden value is small: at most -3 to +2 on the 30-point scale, less than
  a step. **The scouting report's hot and cold players, and the flame and snowflake icons, are fake too.**
- **Genesis league ROMs that show hot / cold as played** (the CDL, IDL, DPWM, RGDL families and others; the viewer's
  Help, "This game's ROM", says which yours is): the position is real. All of a player's numbers sit the same distance
  from the **middle of their band (54, 72 or 90)**, and that distance is his hot / cold for this game: 3 or more above
  is +1 in play, 6 or more +2; 3 or more below is -1, 6 or more -2. Check any rating in the 50+ bands: a player whose
  Speed reads 96 (6 above 90) is hot; 84 (6 below) is cold. It's still less than a step, so it only matters at the
  thresholds in section 2.
- **SNES: low in the band is good.** A number **below the middle of its band (34, 43, 54, 72, 90)** means that rating
  plays at the **maximum, as if it were 99**, because of the SNES hot / cold bug (2.2). A Speed of 66 is a maximum
  Speed; a Speed of 75 is an ordinary step 4. At the middle exactly, it's maxed one time in three. About half of all
  SNES ratings are maxed every game. See [section 15](#15-snes-whats-different).

**Look at Edit Lines from the pause menu once the game has started.** On the Genesis the pre-game Matchups screen
re-rolls everyone's hot / cold, so anything seen before it isn't this game's.

### 1.3 Don't trust Overall

Overall is a weighted average that counts **Offensive Awareness three times**, though it does nothing for the player
you control, and Endurance, which does nothing with line changes off. It leaves out Weight and Aggressiveness entirely.
A goalie's Overall includes four glove and stick ratings the game never uses. Read the individual columns.

---

## 2. What each rating does for you

You control one skater at a time, usually the one with the puck or nearest it. The other four, and your goalie unless
you take him, are played by the computer. Some ratings only matter for the player you control, some only for the
computer's players.

### 2.1 Skaters (Genesis)

| Column | What it does | How much it matters |
|---|---|---|
| **Speed** | Top speed: about 20 mph at 25-29, 24 at 38-47, 29 at 63-80, 31 at 81-98, 33 at 99 | **A lot.** Each step is about 8% faster. Bursts go past it for a moment |
| **Agility** | Acceleration, and so turning and changing direction | **A lot**, but see Weight: heavy players accelerate slower |
| **Weight** (lb) | Costs acceleration (every 20 lb costs about one Agility step); decides checks through the weight bug (section 9) | **A lot**, both ways: light players accelerate and check better against people |
| **Shot Power** | How hard he shoots. **Below a working 20 the wind-up is cut short: no full slapshot** | 81+: full slapshots always. **63-80: in about 6 games of 10** (on show-as-played ROMs: 70 and up yes, 63-69 no). 62 and under: never |
| **Shot Accuracy** | The chance a shot goes **exactly** where you aimed (from inside the zone), and how far it strays if not | Exact-shot chance: 25-29: 9%, 29-38: 28%, 38-47: 42%, 47-62: 51%, 63-80: 58%, 81-98: 63%, 99: 67% |
| **Stick Handling** | Keeping the puck from stick checks, stealing it, catching hard passes, and **wobbling instead of falling when hit** | Wobble needs a working 24: **99 always, 81-98 about 4 games in 5, below 81 never.** A carrier who can't wobble falls on any contact with the goalie |
| **Checking** | Your knockdown chance on a check; **upending** players (63-80 in about 6 games of 10, 81+ always); how often your computer teammates hit and chase | Moderate for your own checks (weight matters more), real for your computer teammates |
| **Pass Accuracy** | **Pass speed only.** Every pass is aimed perfectly anyway | Small. Fast passes are harder to pick off but bounce off low Stick Handling receivers |
| **Off. Awareness** | How quickly **computer-controlled** teammates react on offence and to loose pucks | **Nothing for the player you control.** Matters for your teammates |
| **Def. Awareness** | How quickly computer teammates react on defence; **your defencemen's gap control**; also (a coding slip) your forwards' positioning on offence | Matters for the four skaters you're not controlling, especially defencemen |
| **Aggressiveness** | Penalty chance. It wraps around, so **63-80 is among the cleanest, 99 and 47-62 the dirtiest** (section 11) | Modest: the dirtiest are about 1.5 times as likely to be called as the cleanest |
| **Endurance** | How fast energy drains | **Nothing with line changes off** (the leagues' usual setting) |
| **Handed** | Which side his stick is on | Backhands lose a quarter of their power |

Not on the screen: **Fighting** (how long players he injures stay out) and a **pass / shoot bias** (whether a
*computer* puck carrier prefers to shoot or pass; the editors call it "Rgh").

### 2.2 Goalies (Genesis)

| Column | What it does |
|---|---|
| **Agility** | **His reach**, which decides saves (section 12): 99: 15 units; 81-98: 14 (15 when hot); 63-80: 14 (13 when very cold); below 63: 13; 25-29: 12-13. **When you control him yourself he always has 15** |
| **Puck Control** | Whether he holds a shot or gives a rebound |
| **Def. Awareness** | How often the computer goalie re-squares to the puck, and how fast he goes for loose pucks |
| **Speed**, **Weight** | Skating |
| **Stick Right / Left, Glove Right / Left** | **Nothing.** The save code looks them up and throws them away. (Glove Left only lets him use a reaching glove animation; the save itself is still decided by his reach) |
| **Glove Hand** | Which hand |

---

## 3. Choosing your lineup

For the Genesis, with line changes off (the usual online setting):

- **Forwards (the players you'll mostly control):** Speed, Agility and a moderate Weight first, then Stick Handling
  (81+ to wobble through contact), Shot Power (81+ for a full slapshot; 62 or under can't take one), Shot Accuracy.
  Offensive Awareness barely matters for them.
- **Defencemen:** you control them less, so **Defensive Awareness** (gap control, getting back) earns its keep here;
  Speed and Agility still matter for when you do take them.
- **Checkers:** light beats heavy against human opponents. Because of the weight bug, **a player you control knocks down
  anyone 16 lb or more heavier almost every time**, and has a poor chance against anyone his weight or lighter (9.1).
- **Penalties:** prefer Aggressiveness 63-80 or under 38; avoid 99 and 47-62 if you play with penalties on.
- **Goalie:** Agility and Puck Control. Ignore the glove and stick columns. If you play the goalie yourself, his
  Agility's reach doesn't matter (you always get the maximum), but it still makes him quicker.
- **Endurance doesn't matter** with line changes off: energy never drains, and speed bursts are free.
- **Ignore Overall.**
- Some teams get hidden bonuses at home or on the power play (2.3), set per team in the ROM.

---

## 4. Faceoffs

**Ratings play no part. It's timing, and you can't see the drop coming in time.**

1. **Mash B as fast as you can** from when the faceoff box appears until the drop (3-5 seconds, random). Each press
   swings the stick once; what counts is how far into the swing you are at the drop. Fast mashing keeps you in the
   swing; holding B does nothing.
2. **Hold the d-pad toward the teammate you want the puck to reach**, the whole time. If you win, the puck goes that
   way **3 times in 4**. **Never leave it neutral**: then it goes forward or sideways, toward the other team.
3. **Straight back to your defence is the most reliable target.** The puck always gets a push toward the winner's
   own end, so a sideways draw comes out angled slightly back: aim a little forward of a winger.
4. The game's "faceoffs won" stat counts whoever touches the puck first afterwards, not who won the draw.

The computer never holds a direction, so its wins go a random way.

---

## 5. Skating and carrying the puck

- **With the puck, you accelerate at half rate** (the computer's carriers don't). Build speed before you take a pass,
  and take passes in stride.
- **Speed bursts (C without the puck) give a big push** in the direction you face, and with line changes off they
  cost nothing.
- **Don't skate into the goalie with the puck.** Any contact with him knocks you down and loses the puck, unless your
  Stick Handling lets you wobble (81+ usually, 99 always).
- Players skate at about 20-33 mph; the puck in a hard slapshot goes 90-100 mph.

---

## 6. Shooting

- **You aim with the d-pad as you shoot**, at nine spots in the net. **In screen directions**: Up is high, Down is
  along the ice, Left and Right are the screen's sides. So when you're attacking down the screen, Left is the
  *shooter's* right.
- **From inside the attacking zone** (within about 67 feet of the net) a shot can go **exactly** where aimed: the
  chance is set by Shot Accuracy (2.1). **From outside the zone, never**: it always scatters.
- Scatter grows with shot speed, distance and poor accuracy, and **only ever pushes the puck up, never down**. A
  shot aimed along the ice can rise; a high shot can go over the crossbar.
- **Close in and high:** from within about 17 feet of the goal line, a high shot gets an extra-steep lift ("top
  shelf").
- **Slapshots:** hold C longer for more power. Weak shooters (section 2.1) can't wind up fully.
- **A shot that touches the boards, or any stick or body on the way, isn't a shot on goal**, even if the goalie stops
  it.
- **Delayed penalty = free snipe.** While the referee's arm is up for a penalty against the other team, the game
  pulls your goalie, and **every shot your team takes from inside the zone goes exactly where you aim it**. Shoot for
  a corner.
- **Rebounds go straight out from the goalie's centre through where the puck hit him.** A shot off his left pad comes
  off to his left. Point-blank shots at a goalie standing still rebound about 60% of the time; get a man to the side
  you're shooting at.
- **The EA Special** (community name): a wrist shot from the side that the goalie bobbles and is pushed back on, then
  a quick follow-up into the open side. It fits the rebound rule above.

---

## 7. One-timers

**The best way to score.** Against a one-timer the goalie's reach drops to its minimum, whoever he is.

- **How:** pass with B to a teammate, then **press C while the pass is on its way**. (Or, already controlling the
  receiver, press C as the puck comes to him.)
- **Only in your attacking half**; in your own half C is a speed burst.
- **The game times the swing for you.** Press C up to about 0.9 s before the puck arrives; earlier and the swing ends
  before the puck gets there. Pressing late is fine, even as the puck arrives.
- **You can't aim it**: the game aims one-timers itself, usually at the side away from where the goalie is moving.
- They fail when the pass is slow, the receiver drifts off its line, or someone else touches the puck.
- **Offsides on:** a one-timer by a player who is offside isn't whistled, and the goal counts.

---

## 8. Passing and the flip

- **B passes to the nearest teammate within 45 degrees of the direction you hold.** A teammate straight ahead is
  preferred over one at the edge of that cone.
- Passes are **always aimed perfectly** at where the receiver will be if he keeps skating. Pass Accuracy is only
  speed.
- **Pass shots:** with nobody in the cone, the puck just goes that way, hard. Aimed at the net, it's a shot the game
  doesn't count unless it scores.
- **Bobbles:** a pass faster than the receiver can handle (it depends on his Stick Handling) bounces off his stick.
- **The flip (A with the puck) isn't aimed by the d-pad.** It goes to a fixed spot from where you are and **which way
  your skater faces**:
  - outside the attacking zone: a high lob to the attacking-zone faceoff circle on the side you face;
  - inside the zone: low, to the high slot (or to the goal mouth from behind the net).
  Steer your skater's facing to choose the side.
- **Over the glass:** outside the attacking zone, out on one side (not right on the boards), facing those boards, the
  flip's spot is pushed past the boards and the puck goes out of play.

---

## 9. Checking

### 9.1 The weight bug (Genesis)

**Only a speed burst (C without the puck) can knock someone down.** Whether it does depends on how hard you hit and on
the two players' weights, and **for the player you control** the sum overflows:

| You check someone | Chance to knock him down |
|---|---|
| **16 lb or more heavier than you** | **almost certain** |
| About your weight or lighter | low (around 1 in 10 in recorded games) |

The computer's checkers work the sensible way: heavier checkers do better. Recorded games: a person checking a man
2+ steps heavier knocked him down 48% of the time, 7% against a man 2+ steps lighter; computer checkers the other way
round, 15% and 34%.

**What to do:** check bigger players with smaller ones. **Your heavy carriers are vulnerable** to a human opponent's
lighter checkers; against the computer's checkers, weight protects them.

### 9.2 The CB check

**C to burst, then B to switch to another player before contact.** At contact the checker is now the computer's, so
the computer's formula applies, where a heavy checker does well. The cost: **twice the penalty risk**, because the
game halves a person's penalty chance and the checker is no longer yours. Some league ROMs remove the trick (the
viewer's Help, "This game's ROM", says whether yours does).

### 9.3 More checking rules

- **Against the boards, a check that lands hard enough always knocks him down.** Check along the boards.
- **You can't knock the same man down twice in a row.** After you knock a player down, or make him wobble, your next
  checks on him do nothing until **some other** knockdown or wobble happens anywhere on the ice. Hit someone else.
- **Goalies can't be knocked down.** Skating into one fast knocks *you* down.
- Players with Stick Handling 81+ may wobble instead of falling (2.1).
- **Injuries:** a hard knockdown can injure; the injury always gives the hitter a roughing minor (with penalties on).

---

## 10. Taking the puck: pokes and hooks

- **Any stick touching the carrier's puck can steal it**, a roll each frame they touch; better Stick Handling on
  either side shifts the odds.
- **Poke check (B without the puck):** only from close. In recorded games two-thirds of pokes were from more than 10
  feet away and did nothing. Within 10 feet: tripped him 28%, knocked the puck loose 30%, took it 12%, nothing 19%.
  **Facing him, a poke that bumps his body trips him**, and with penalties on that's always a trip (and a chance of a
  tripping call).
- **Hook (A without the puck):** drags a fast carrier to your speed and freezes him for two-thirds of a second, but
  carries the highest penalty risk of any move, and on the carrier he kept the puck only 4 times in 22. Usually not
  worth it.

---

## 11. Penalties

With penalties on:

- **Your own player draws half as many penalties as a computer player** with the same rating.
- **Near the puck (within about 13 feet) the chance doubles.**
- **What gets called:** a check that leaves him standing is **charging or "slashing"** (in NHL '94, "slashing" is a
  body check that didn't knock him over); a check that knocks him down, **roughing or cross-checking**; a poke that
  trips him, **tripping**; A, **hooking or holding** (the likeliest).
- **Aggressiveness wraps around**, so a high number isn't always dirty:

  | Aggressiveness shown | Penalty chance |
  |---|---|
  | 25-29, 63-80 | lowest |
  | 29-38 | low |
  | 38-47, 81-98 | higher |
  | **47-62, 99** | **highest** (about 1.5 times the lowest) |

- **Delayed penalties:** once the other team has a penalty coming, **your team can't be called** for checks, hooks,
  holds or trips until the whistle (only goalie interference and injury roughing still count). Play physically, and
  shoot (section 6).
- **Goalie interference:** knocking into a goalie in his crease. On a team a person plays, only the skater you control
  can be called.
- Fighting, instigating and delay of game are never called.

---

## 12. Goaltending

### 12.1 How saves work

**There's no save roll.** A puck at stick or body height that comes within the goalie's **reach** of his centre is
stopped; anything farther away goes past him. Reach is 12-15 units (4-5 feet) by Agility (2.2), 18 in a pad stack.

- **Take the goalie yourself** (B with the puck loose or the other team's): **he always has the full reach, 15.** In
  recorded games, with a person in net, no goal except one-timers went in within 20 units of him.
- **One-timers cut his reach to 12** whoever controls him.
- To score: shoot **wide of his reach** (a corner, from inside the zone, where your shot can be exact), use one-timers,
  and follow up rebounds.

### 12.2 Playing goal yourself

- Stay in your area: **a goalie you control who skates more than about 33 feet out from his goal line** (past the
  tops of the faceoff circles) is whistled.
- He's whistled for holding the puck about 2.3 s after taking it; a puck taken in a dive is whistled at once.
- Dives (A while moving) stop him dead for over a second; the computer only dives at a slow loose puck right in front
  of him.

### 12.3 The computer goalie

- He stands in front of his net, about 6 feet out, facing where the puck is *about to be*, and re-squares several
  times a second.
- **When a shot is coming at the net**, he slides sideways to the spot where it will cross the goal line, starting
  about 0.6 s before it gets there.
- **0.2 s before it arrives he commits to a save move and stops sliding.**
- So what beats him is **time**: a quick, hard shot from close in, or a pass across that makes him slide again (a
  one-timer), leaves him short of the crossing point. A slow shot from far out gives him time to get there.
- Point-blank shots at him while he's standing still mostly rebound.

The viewer's **xG** (expected goals) plays every shot out this way, hundreds of times, and shows the chance it had of
going in: on each shot, the player cards and the team stats. It's a fair way to see who is getting good chances and
which goalie is stealing games (Genesis games).

---

## 13. Breakaways and penalty shots

- **A breakaway is decided at one instant:** as you cross the blue line, **every other skater, your teammates
  included, must be behind you.** A teammate already ahead of you costs you the breakaway.
- After the "ding" it lasts while you keep the puck and **keep skating toward the net**; a defender catching up
  doesn't end it.
- **A foul on a breakaway** is called by distance, not ratings: the closer to the net, the likelier. It becomes a
  **penalty shot**, though with the wrong name (a slashing call is announced as roughing, and so on). Holding and
  interference give no penalty shot.
- **Penalty shots:** the shot ends when the goalie gets the puck, after you shoot and someone touches the loose puck
  (or about 1.7 s after the shot), or when its clock runs out. **Losing the puck without shooting doesn't end it** unless
  the goalie gets it: go back and get it.

---

## 14. Your computer teammates

- **Awareness is reaction time** for computer players: 0.25 s at the bottom, 0.12 s at the top. It decides how fast
  they react to turnovers, loose pucks and rushes. **It never affects the player you control.**
- **Defensive Awareness** gives your defencemen their **gap control**: they set themselves 50 units (about 17 feet)
  behind the deepest attacker and update that only at their reaction ticks. Low-rated defencemen get beaten on rushes.
- Players busy in an animation (falling, shooting, checking) don't react at all until it ends: a forward who just lost
  the puck is out of the play for up to a second.
- **With penalties on, computer skaters try to check only half as often.**
- Computer forwards go to set spots by zone: on offence the centre heads for the slot, wingers wide. The middle
  between the blue line and the high slot is often open when the centre is the one chasing the puck.

---

## 15. SNES: what's different

### 15.1 Ratings

- **Read the screen backwards: low in the band is maxed.** A number below the middle of its band (34, 43, 54, 72, 90)
  plays at the maximum, 15, whatever the step. So a Speed of 66 beats a Speed of 80; a Shot Accuracy of 85 is a
  maximum shooter. More than half of SNES skaters skate at full speed in a typical game.
- **But maxed Aggressiveness is bad:** most SNES penalties are taken by players with maxed Aggressiveness, and they're
  called for goalie interference 40% of the time they crash a goalie. Aggressiveness below its band's middle is a
  penalty risk.
- **Maybe worse (from the code, not yet seen in a game):** a skater **you control** whose Aggressiveness reads
  **78-80 or 90-92** is at the one value where the game's arithmetic overflows, and could be called on every penalty
  roll.
- Weight costs less acceleration than on the Genesis.

### 15.2 On the ice

- **No weight bug and no CB trick:** heavier checkers simply do a bit better (50% against 39% in recorded games). No
  same-man rule either, but **a second hit within a second of a wobble always knocks him down**.
- **Computer players are hit-happy:** at high Checking (which the bug hands out) they go for a hit almost every time an
  opponent is in front of them.
- **One-timers go where your d-pad points** (no auto-aim), and the goalie's reach isn't cut. They're still strong:
  **a computer goalie loses his Agility while a pass is in the air**, so he slides across slowly, and every pass
  delays his next adjustment.
- **The SNES goalie** is a fixed-size box; controlling him yourself doesn't make him bigger, but a goalie you control
  moves much faster. Pad stacks and Agility don't change his size.
- **No shooter is limited to a short wind-up**: anyone can take a full slapshot.
- **The flip (Y) is a computer dump-in**: it goes deep on whichever side of centre you're on, and **Pass Accuracy
  decides how far it strays**.
- **Interference:** any skater can be called, yours or the computer's.
- **No delayed-penalty immunity and no delayed-penalty sniping:** both teams can be called at one whistle.
- Faceoffs use the same timing rule.

---

## 16. Myths: things that don't matter

- **The goalie's glove and stick ratings** (both systems).
- **Endurance**, and fatigue in general, with line changes off.
- **Offensive Awareness for the player you control.**
- **The scouting report's hot and cold players** (Genesis original ROM): fake.
- **Small differences within a rating band** on the Genesis original ROM: 81 and 98 are the same player.
- **Ratings on faceoffs.**
- **Pass Accuracy as accuracy**: it's speed.
- **"A loud crowd makes players faster"**: the crowd's speed bonus is on for everyone, always.
- **The comeback bonus** for a team behind in the third: small, and because of a bug it's on in the *first* half of
  the period and off in the second.

---

## 17. Cheat sheet

**Before the game (Genesis):** pick on bands, not exact numbers. Speed, Agility, light Weight, Stick Handling 81+,
Shot Power 81+ for the shooters you'll control; Defensive Awareness on defence; Aggressiveness 63-80; goalie Agility and
Puck Control. Ignore Overall, Endurance, and the goalie's glove and stick columns.

**On the ice (Genesis):**

1. Faceoffs: mash B, hold the d-pad toward your target, back to the defence is safest.
2. Shoot from inside the zone, aim for a corner away from the goalie; follow up rebounds to the side they come off.
3. One-timers: B to pass, C while it travels. The best way to score.
4. Take your goalie when a shot is coming: he gets the full reach.
5. Check heavier players with lighter ones, and along the boards; don't hit the same man twice running.
6. Pokes only from within 10 feet; hooks rarely.
7. Ref's arm up for the other team: you can't be called, and your shots go exactly where you aim.
8. On a breakaway keep skating at the net; make sure no teammate is ahead of you at the blue line.
9. Flip by facing, not the d-pad.

**SNES:** low in the band is maxed; maxed Aggressiveness means penalties; one-timers go where you point; no weight
bug.
