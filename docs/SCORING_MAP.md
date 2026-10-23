# NHL '94 Scoring Maps: How the Simulation Was Built

Every shot in these maps was played in the real game, not a model: the Genesis and SNES ROMs ran headless thousands of
times faster than real time, and each shot was played out until it was a goal or a save. (2026-10-23. The findings are
also in [GENESIS_MECHANICS](GENESIS_MECHANICS.md) 4.10 and [SNES_MECHANICS](SNES_MECHANICS.md) 4.8; the run notes in
[PROJECT_NOTES](PROJECT_NOTES.md), "Scoring map"; the tools in [`analysis/scoring_map/`](../analysis/scoring_map/).)

## Contents

1. [At a glance](#at-a-glance)
2. [Building the Genesis simulator](#building-the-genesis-simulator)
3. [Making every Genesis shot count exactly](#making-every-genesis-shot-count-exactly)
4. [What went wrong and how it was fixed](#what-went-wrong-and-how-it-was-fixed)
5. [Building the SNES simulator](#building-the-snes-simulator)
6. [The goals that went in](#the-goals-that-went-in)
7. [Makes and misses, animated](#makes-and-misses-animated)
8. [How often each kind of goal happens](#how-often-each-kind-of-goal-happens)
9. [The maps](#the-maps)
10. [Limits and what comes next](#limits-and-what-comes-next)
11. [Rebuilding it yourself](#rebuilding-it-yourself)

## At a glance

A computer goalie who has set himself stops almost every shot from a standing shooter on both systems; the goals come
from a few gaps in the game's own rules.

| | Genesis | SNES |
| --- | --- | --- |
| Shots played | about 10.6 million launches for the map (800 per aim at each spot) + 1.09 million for the goal sample | 2.07 million for the map + 761,400 for the goal sample |
| Goals, averaged over every spot and aim | 1.18% | 0.36% |
| The biggest gap | A slapshot holding Down, straight at him from the middle: 21% (top net), 14% (bottom), up to 47%, through the butterfly's blind ring | A slapshot from 2-5 feet to the shooter's left of centre, 25-40 feet out, aimed at that side: about 50%, past his right-side save |
| Other gaps | Early pad stack (30-50% close in); the top net's shoulder-save bobble (31% at one spot) | Deflections off the edge of his body box |
| Emulator | Genesis Plus GX, a test ROM with a hook | Snes9x, the retail ROM unmodified |

![How the simulator fits together: the Genesis and SNES paths into one harness](img/scoring_map/simulator.svg)

The two systems took different roads to the same harness. The Genesis map rebuilt the ROM from the disassembly with a
hook in the shot routine so its dice could be covered exactly; the SNES map ran the untouched ROM and let the game roll
its own dice millions of times.

## Building the Genesis simulator

The Genesis map runs a test ROM built from the community disassembly, with one small hook added to the shot routine,
inside a minimal emulator front end written for the job.

**1. The ROM.** The [NHL94Genesis](https://github.com/abdulahmad/NHL94Genesis) disassembly rebuilds the retail ROM byte
for byte. A copy of it is built with its own tools (SNASM68k), never in the clone itself. The build's listing gives the
address of every routine and variable.

**2. The hook.** The shot routine, `doshot`, is where the game turns the shooter's power, aim and accuracy into the
puck's speed. Two calls were added:

- one at the start of `doshot`, which records what goes in: the random seed, the shot power, the aim, the puck's spot
  and the goalie's animation;
- one just before its sound effect, which records the launch the game chose and, when a flag is set, replaces it with a
  launch the harness supplies.

Inserting bytes would have moved every routine after it and broken branches, so the hook had to fit in place. It does:
a 164-byte block in the button-handling code (`doinput_cbut`) is dead (nothing ever reaches it), and the two hook
routines plus padding fit in it with 8 bytes to spare, which pays for the two new calls. The hook writes to a RAM area
(`FFE000-FFE031`) the game never touches.

**3. The emulator.** A copy of RetroArch's Genesis Plus GX core is driven directly from Python through its libretro
interface (`emu.py`): load the ROM, load a saved state, hold buttons, run frames, read and write work RAM, take
screenshots. With no video or sound to show it runs about 4,500 frames a second per process. One core per process: a
second emulator in the same process takes over the first one's callbacks (this silently broke the first attempt).

**4. The game states.** `make_states.py` boots the test ROM through the menus (Montreal v Los Angeles, the defaults)
and saves two live moments: period 1, where the shooter attacks the top net, and period 2, the bottom net.

**5. A shot.** `harness.py` holds the shooter on a spot with the puck and every other skater parked out of the way
while the computer goalie sets himself (80-94 frames). It then presses the shoot button (C) for 3 frames (a wrist
shot) or 20+ (a full slapshot) with the d-pad held for the aim, and stops on the frame `doshot` runs.

## Making every Genesis shot count exactly

A shot's outcome depends on two random things: the dice `doshot` rolls at the release, and the moment the shot is
taken. The Genesis map covers the first exactly and the second with 120 moments per spot.

**The shot's dice, ported exactly.** `doshot` makes four random draws: a perfect-shot roll (the puck goes exactly to
the aim point) and, when that fails, three scatter draws (across, along and up). `shotport.py` is a line-by-line Python
copy of the routine, down to the 68000's integer rules (a division that overflows leaves its register unchanged; a
byte that wraps in the scatter size; the top-shelf lift for a few pad-stack cases). Checked against the hook's record
of the game's own launch: **129 of 129 shots identical**, both nets.

**Splitting the shots by the dice.** With the port, each aim's outcome is the perfect shot's chance times its result,
plus the scatter's chance times the average over scatter draws. The harness asks the hook to fire the launches it wants
(800 per aim at each spot), so no shots are wasted re-rolling the perfect case.

**What happens after the release is random too.** The goalie's movement never calls the random generator, but contact
does: whether he holds the puck or it bounces, and which way a deflection goes. The first version kept the seed after
the release and came out low (5.6% where natural shots gave 7.8%), so the seed is now randomised right after the
launch.

**The moment.** The same shot from the same spot can score at one moment and not the next: the goalie rethinks on a
5-frame cycle and has a countdown no player can see. A perfect slapshot just inside the post scored at 13 of 16
moments in one test. Each spot is played at 120 moments: the game clock at 590 down to 583, times 15 settle lengths
(80 to 94 frames).

**When a shot is decided.** Playing every shot 240 frames would waste time, so a shot stops when the goalie has held
the puck 20 frames, the puck has moved away from the goal 4 frames running, or it is 12 units past the goal line. This
agreed with full 240-frame play-outs on 1,475 of 1,475 shots. (A first version stopped the moment the goalie caught it
and missed six goals the top net's shoulder-save bobble lets in 48-79 frames later.)

**Which spots count.** Within about 30 units of the net, the goalie's set spot is the puck itself: he skates onto it,
and the shot would start inside him, which no game allows. A spot counts when, at the release, the puck is at least 24
units from his centre and in front of him, and the shooter at least 16 away (`validity.py`).

**The run.** 23 x 16 spots (x -110 to 110, 100 to 250 from centre ice, every 10 units), both nets, wrist shot and
slapshot, all nine aims; shooter working Shot Power 20, Shot Accuracy 15; Los Angeles's goalie (weight 48, Agility
13, Speed 13, Defensive Awareness 10). 30 processes, about 2 hours.

## What went wrong and how it was fixed

Every problem below was caught by a check before the results were used; the final Genesis map matches natural shots
(the game rolling its own dice from a random seed) within about one standard error at every spot tested.

| Problem found | How it showed | Fix |
| --- | --- | --- |
| Two emulators in one process | No shots happened at all: the second emulator took over the first's input | One emulator per process, shared by both nets |
| The hook moved code | Branches out of range when bytes were inserted | Made the hook size-neutral, inside a dead 164-byte block |
| Shots stopped too early | Six top-net goals missed: the shoulder-save bobble scores 48-79 frames after the catch | Stop only after the goalie holds the puck 20 frames |
| The seed kept after the release | 5.6% at one spot where natural shots scored 7.8% | Randomise the seed right after the launch |
| Too few moments | Results swung with the shot's timing | 16 moments, then 120 |
| Spots too close to the net | The goalie skated onto the puck; 65-100% "goals" from 28-48 units out | `validity.py`: the puck 24+ from his centre and in front of him |
| Replayed recorded shots started in the wrong spot | Up to about 195 units off | Settle 80 frames, then correct the start twice from `doshot`'s own record |
| Replays of recorded shots too sure of themselves | Worse shot-by-shot predictions than the xG model | Added the goalie's ratings, animation and a 2-4 unit position blur; the xG model still predicts recorded shots better |

**The checks that passed:**

| Check | Result |
| --- | --- |
| Ported shot code against the game's own launch | 129 of 129 identical |
| Map against natural shots, four spots (map / natural) | 51.6 / 52.0%, 32.6 / 33.9%, 7.3 / 7.8%, 43.0 / 44.4% |
| Fast stop against full 240-frame play-outs | 1,475 of 1,475 agree |
| 135 recorded shots at computer goalies, replayed in the game | 20.5-22.5 expected goals against 22 scored |
| SNES harness with the goalie moved away | Close to the mechanics doc's empty-net rates (80% / 95% / 60% / 78% on 40 shots each, against 87% / 100% / 49% / 68%) |

## Building the SNES simulator

The SNES map needed no test ROM: the unmodified retail ROM runs in a copy of RetroArch's Snes9x core, and the game
rolls its own dice for every shot.

**1. The emulator.** The same Python front end, pointed at Snes9x (`snes_emu.py`), about 3,500 frames a second per
process. SNES work RAM is read in its natural byte order (the Genesis core stores it in swapped pairs).

**2. Reading the code.** From the [NHL94SNES](https://github.com/abdulahmad/NHL94SNES) disassembly: the shot is
`doshot`, started by the A button (`SetShotMode`, then `ShotMode` each frame); tapping A jumps the shot animation to
its end (a wrist shot leaves on frame 3), holding it winds up a slapshot (released on frame 26). The random generator,
`RandomWord`, is two 16-bit shift registers at `7E0792` and `7E0794`. The puck carrier is `puckc` (`7E0AD9`),
negative when the puck is loose.

**3. The game states.** `snes_make_states.py` presses Start 12 times from power-on to reach the rink, then once more:
Los Angeles (home, pad 1, the centre controlled) against Montreal, with Los Angeles attacking the top net in period 1
and the bottom net in period 2, both against Montreal's goalie.

**4. Finding the release.** During the wind-up the harness saves the state before every frame; the frame on which the
puck comes loose is the one where `doshot` ran.

**5. Natural sampling.** That frame is replayed from a fresh random seed each time, so every draw comes from the game
itself: the perfect-shot roll, the scatter, the goalie's look-ahead (the SNES goalie's positioning does use the random
generator), rebounds and post deflections. No ported code is involved, so there is nothing to verify against.

**6. The run.** 23 x 17 spots (x -110 to 110, 90 to 250 from centre ice, every 10 units), both nets, wrist shot (A
held 3 frames) and slapshot (A held 40), all nine aims; 16 moments (a seed for the settle, the clock, 80-94 frames to
settle) x 24 release seeds = 384 shots per aim at every spot. The shooter is the typical recorded SNES shooter:
working Shot Power 13 and Shot Accuracy 13, the median of 297 recorded shots. 782 jobs on 30 processes, about 1 hour
50 minutes, 2.07 million valid shots.

**Too few moments, found later (2026-10-23):** the map sampled 16 of the 120 moments (clock x settle) a spot, and the
goal rate swings by about 0.27 (standard deviation) from moment to moment, so a single square is only good to about 7
points either way. Over all 120 moments (480 shots each): the top-net lane spot (10 left of centre, 88 out, Left held)
53.6% (map 47.7%), the bottom-net one (10 right, 118 out, Right held) 26.5% (map 30.2%), the mirror spot 1.7% (map
0.8%). The findings stand; the squares' exact values would need a rerun at 120 moments.

**7. Narrowing the lane.** The 10-unit grid showed hot squares next to near-zero ones. A second pass at 2- and 3-unit
steps across the middle (96 shots per aim per spot) showed one lane about 10 units wide, and tracing single shots frame
by frame showed why (below).

## The goals that went in

Almost every goal against a set goalie comes through one of a few gaps in the game's rules, and each one below is a
real goal replayed in the game (`goal_frames.py`). The frames are the emulator's own output, zoomed 3x on the net. The
diagram under each (`goal_diagram.py`) is drawn from the game's numbers frame by frame: the crease from above (one dot
per frame for the puck, coloured by height; grey dots for where the goalie moved; his reach or body box and save area
as they were when the puck passed closest) and the puck's height on the way in.

### Genesis 1: through the butterfly's blind ring (47% of Genesis goals)

A slapshot with Down held, from straight in front of him 118 units out, at the top net. A flat puck arriving at his
middle makes him drop into the butterfly. The ring around his stick doesn't touch a puck on the ice, so it passes his
centre (3 units off it, frame 12), hits his body behind his centre and bounces in. 5,629 of the 6,051 such goals were
slapshots; 4,514 were at the top net.

![Genesis through-the-legs goal: four game frames](img/scoring_map/g1_ring_frames.png)

![Genesis through-the-legs goal: the puck's path and height](img/scoring_map/g1_ring_path.svg)

### Genesis 2: past his early pad stack (23%)

A wrist shot aimed down-left from 68 units out, 60 to the side, at the bottom net. He started sliding into a pad stack
as the shot was wound up (his reach grows to 18), but he slid the wrong way: the puck crossed the line 21 units from
his centre.

![Genesis pad-stack goal: four game frames](img/scoring_map/g2_stack_frames.png)

![Genesis pad-stack goal: the puck's path and height](img/scoring_map/g2_stack_path.svg)

### Genesis 3: clean, never within his reach (21%)

A slapshot aimed high (Up) from 118 units out at the top net. It rises on the way in and passes 14 units from his
centre at height 9, just beyond his reach of 13, and goes in under the crossbar.

![Genesis clean goal: four game frames](img/scoring_map/g3_clean_frames.png)

![Genesis clean goal: the puck's path and height](img/scoring_map/g3_clean_path.svg)

### Genesis 4: held, then carried into the net (7%, top net only)

A high wrist shot from the far left boards, 78 units out. He catches it in a high shoulder save and, still holding it,
drifts back into his own net: 882 of the 905 such goals were at the top net (the shoulder-save bobble).

![Genesis shoulder-save bobble: four game frames](img/scoring_map/g4_held_frames.png)

![Genesis shoulder-save bobble: the puck's path and height](img/scoring_map/g4_held_path.svg)

### SNES 1: past his right glove save (the lane)

A slapshot aimed Left from 10 units left of centre, 88 out, at the top net. The puck passes 12 units from his centre,
just outside his body box (11). He's in his right glove save, whose save area (green) covers heights 7-15 and sits
close to his body; the puck goes by at height 4.

![SNES lane goal past the right glove save: four game frames](img/scoring_map/s1_glove_frames.png)

![SNES lane goal past the right glove save: the puck's path and height](img/scoring_map/s1_glove_path.svg)

### SNES 2: past his right stick save

The same lane at the bottom net: a slapshot aimed down-right from 10 right of centre (the shooter's left), 118 out.
The puck stays on the ice and passes 13 units from his centre; his stick save's area is a small circle at the corner of
his body box, 2-5 off the ice, so the puck slides under it.

![SNES lane goal past the right stick save: four game frames](img/scoring_map/s2_stick_frames.png)

![SNES lane goal past the right stick save: the puck's path and height](img/scoring_map/s2_stick_path.svg)

### SNES 3: past his right sprawl

A slapshot aimed down-left from 14 left of centre, 88 out, at the top net. The puck passes 12 units from his centre on
the ice; the sprawl's save area at that moment covers heights 4-8, so it goes under.

![SNES lane goal past the right sprawl: four game frames](img/scoring_map/s3_sprawl_frames.png)

![SNES lane goal past the right sprawl: the puck's path and height](img/scoring_map/s3_sprawl_path.svg)

### SNES 4: off the goalie (24% of SNES goals)

A puck that clips the edge of his body box and deflects in. Here a slapshot from 10 left of centre catches his edge 11
units from his centre and glances into the net. Most of these were wrist shots (423 of 645).

![SNES deflection goal: four game frames](img/scoring_map/s4_off_frames.png)

![SNES deflection goal: the puck's path and height](img/scoring_map/s4_off_path.svg)

## Makes and misses, animated

At each worthwhile spot, 120 shots were played (one at each of the 120 moments, a fresh random seed each,
`animate.py`) and kept frame by frame. For each spot there are two animations, both at half speed:

- **Nine real clips** side by side: the game's own frames zoomed on the net, with goals and saves in the spot's real
  proportion, each labelled when it's decided.
- **All 120 shots from above at once:** each puck's trail (orange went in, grey saved) and the goalie as a dark dot.
  Shots that went exactly where aimed share one path, so many goals can look like a single orange line.

The Genesis rates are the map's (all 120 moments). The SNES rates come from 480 shots over all 120 moments, because the
SNES map's 16 moments a spot turned out to be too few (see the SNES run above).

### Genesis: slapshot holding Down, straight in (top net 43%, bottom 10%)

![Genesis top net, Down slapshot from 118 out: nine real clips](img/scoring_map/genesis_down_slapshot_top_clips.gif)

![Genesis top net, Down slapshot from 118 out: all 120 shots from above](img/scoring_map/genesis_down_slapshot_top_fan.gif)

The same shot at the bottom net goes in far less often:

![Genesis bottom net, Down slapshot from 118 out: nine real clips](img/scoring_map/genesis_down_slapshot_bottom_clips.gif)

![Genesis bottom net, Down slapshot from 118 out: all 120 shots from above](img/scoring_map/genesis_down_slapshot_bottom_fan.gif)

### Genesis: the early pad stack (34%)

![Genesis bottom net, wrist shot down-left from 68 out: nine real clips](img/scoring_map/genesis_pad_stack_clips.gif)

![Genesis bottom net, wrist shot down-left from 68 out: all 120 shots from above](img/scoring_map/genesis_pad_stack_fan.gif)

### Genesis: the shoulder-save bobble (31%)

![Genesis top net, high wrist shot from the far left: nine real clips](img/scoring_map/genesis_shoulder_bobble_clips.gif)

![Genesis top net, high wrist shot from the far left: all 120 shots from above](img/scoring_map/genesis_shoulder_bobble_fan.gif)

### SNES: the lane (top net 54%, bottom 27%)

![SNES top net, slapshot holding Left from 10 left of centre, 88 out: nine real clips](img/scoring_map/snes_lane_top_clips.gif)

![SNES top net lane: all 120 shots from above](img/scoring_map/snes_lane_top_fan.gif)

![SNES bottom net, slapshot holding Right from 10 right of centre, 118 out: nine real clips](img/scoring_map/snes_lane_bottom_clips.gif)

![SNES bottom net lane: all 120 shots from above](img/scoring_map/snes_lane_bottom_fan.gif)

### SNES: the mirror shot (2%)

The same slapshot from 10 right of centre, aimed right, at the top net: his left-side saves cover it.

![SNES top net mirror shot: nine real clips](img/scoring_map/snes_mirror_top_clips.gif)

![SNES top net mirror shot: all 120 shots from above](img/scoring_map/snes_mirror_top_fan.gif)

## How often each kind of goal happens

On the Genesis nearly half the goals go through the butterfly's blind ring; on the SNES half go past a save move on
the goalie's right, against a fifth past one on his left.

![Share of goals by how they went in, Genesis and SNES](img/scoring_map/goal_shares.svg)

The sample (`goal_types.py`) is fresh: the same spots as the maps, both nets, wrist shots and slapshots, all nine aims,
each equally weighted, with the game rolling its own dice. Every goal was sorted by what the puck and the goalie did
each frame between the stick and the net:

- **Held, then in:** the goalie had the puck and it still crossed the line.
- **Off the post / off the goalie:** the puck's speed jumped near a post or near the goalie before it went in.
- **Genesis, through the blind ring:** the puck passed his centre low and untouched, or touched him only behind his
  centre (his body, after slipping past the stick).
- **Genesis, pad stack:** he was in a pad stack as it passed. **Clean:** it never came within his reach.
- **SNES, past a save move:** he was in a save move as it passed and nothing touched it, named by the move
  (`GoalieSaveList`). Of the 911 goals from the lane, 873 passed a right-side move (glove 491, stick 293, sprawl 89),
  35 were deflections and 3 passed a left-side move.

The two systems' rates differ partly by design: the Genesis map's shooter is stronger (Shot Accuracy 15 against 13).

## The maps

A set computer goalie stops nearly every shot from a standing shooter on both systems; each map's hot spots are the
few places a rule of the game leaves a gap. Each square is one spot, coloured by the chance with the best of the nine
aims; the arrow is the d-pad direction to hold (Up is always high, Down along the ice). Grey squares are spots too
close to the goalie for a real shot.

**Genesis** (Shot Power 20, Shot Accuracy 15; Los Angeles's goalie):

![Genesis scoring map: chance a shot scores against a set computer goalie, best aim, by spot](img/scoring_map.svg)

- Wrist shots: under 1% averaged over the aims; the best aim reaches 4-5% in patches.
- A slapshot holding Down, straight at him from the middle, 30-55 feet out: 20.7% at the top net, 13.6% at the bottom,
  up to 47% at the best spots (through the butterfly's blind ring).
- Close in (within about 20 feet): the early pad stack, 30-50% with a down-diagonal aim to the side he slides away
  from.
- The top net's far-left high wrist shot: 31%, every goal the shoulder-save bobble.

**SNES** (Shot Power 13, Shot Accuracy 13; Montreal's goalie):

![SNES scoring map: chance a shot scores against a set computer goalie, best aim, by spot](img/snes_scoring_map.svg)

- Averaged over the aims everything is under about 1%; nothing within 20 feet.
- One lane: a slapshot from 2-5 feet to the shooter's own left of centre, 25-40 feet out, aimed at that side, scores
  about half the time. The mirror shot on the right scores 0-3%.
- The rays of blue squares pointing at the net are the same gap reached from farther out at an angle.

## Limits and what comes next

The maps are exact for one situation (a standing shooter, a set computer goalie, nobody else near) and say nothing
yet about shots off the rush, one-timers or a person in net.

- **Not yet seen in real play.** Two practice tests are on the request list ([NEEDS_FROM_YOU](NEEDS_FROM_YOU.md)
  items 5 and 6): a dozen Down slapshots from the middle on the Genesis, and a dozen slapshots from the SNES left lane
  against its mirror.
- **One shooter, one goalie per system.** Other ratings change the perfect-shot chance (the SNES lane scores about that
  chance: 35% at Shot Accuracy 7, 52% at 15). The goalie's ratings barely matter on the SNES (the same body box and save
  frames for all); on the Genesis Agility sets his reach (12-15).
- **Recorded games still use the xG models.** Replaying 135 recorded Genesis shots in the game gave the right total but
  worse shot-by-shot predictions than the xG model: a recording can't pin down the exact frame and the goalie's internal
  state.
- **Next, if wanted:** a moving-goalie map using goalie states from recorded games (about 2 hours a system); other
  shooters; one-timers; and testing whether adding the Genesis goalie's stick (the blind ring) improves the xG model on
  recorded games.

## Rebuilding it yourself

You need your own ROMs (none are in this repository), RetroArch 1.17's Genesis Plus GX and Snes9x cores, and clones of
the two disassemblies in `%USERPROFILE%\NHL94_disasm`. Work files go to `%USERPROFILE%\NHL94_scoring_map` (or
`NHL94_SMAP_WORK`). From `analysis/scoring_map/`:

| Step | Genesis | SNES |
| --- | --- | --- |
| Build and states | `build.py` (its docstring is the how-to) | copy the Snes9x core to the work folder's `core/`, put the ROM at the disassembly's `lst/nhl94snes.sfc`, then `snes_make_states.py` |
| The map | `map_run.py WORKER WORKERS RUN` (one per process; its docstring), `validity.py RUN` | `snes_map_run.py RUN` |
| The picture | `render_map.py RUN OUT.svg` | `render_map.py RUN OUT.svg` |
| Goal types | `goal_types.py genesis RUN` | `goal_types.py snes RUN` |
| One goal, pictured | `goal_frames.py genesis RUN TYPE N OUT.png`, then `goal_diagram.py genesis OUT.json OUT.svg "Title"` | the same with `snes` |
| The share chart | `goal_chart.py RUN OUT.svg` | (both systems in one chart) |
| The animations | `animate.py OUT_DIR` (all seven spots, both systems; gentle mode) | |

The game frames in this page are screenshots of the games as the emulator drew them, shown to explain how the goals
happen.
