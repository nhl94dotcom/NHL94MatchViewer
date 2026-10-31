# NHL '94 match viewer: study notes

The working notes of the studies: the game mechanics read from the disassemblies, the scoring map's runs, and what the user's games showed. Moved out of [PROJECT_NOTES.md](PROJECT_NOTES.md) on 2026-10-26. The findings themselves, in order, are in [GENESIS_MECHANICS.md](GENESIS_MECHANICS.md), [SNES_MECHANICS.md](SNES_MECHANICS.md), their *_SHOOTING.md parts and the SCORING_*.md pages.

## Passing study (2026-10-18)

analysis/stick_spot.py, analysis/passing_study.py. GetHot (checks94.asm): HotList[frame] x, y bytes; x negated when the
attribute's X flip (bit 11, = our `mirror`), y negated unless Y-flipped; added to the position (ccx: hot + player -
puck). Confirmed: carried puck to blade median 3.6 (variants 7-21); at catch samples the puck sits on the 14 circle.
Passes against the rule (Genesis, nhl94.bin games): rising or above 5 untouched 85-98%; over the catch limit kept 1 of
65; opponents near a low pass took 66% under 9000, 29% over 14000; median pass speed by Passing 0-2 / 3-4 / 5-6: 13485 /
14997 / 16561. Open: about half of slow low pucks within (computed) reach not taken (no nopuck or skip found; the
pass's `to` is the actual catcher for completed passes, so receiver-vs-other comparisons are circular). In
GENESIS_MECHANICS 6.2.

Who takes a loose puck (2026-10-18, the user: sometimes a magnet, sometimes it goes through the stick;
analysis/pickup_study.py reads the raw BOS-DAL captures, which hold sflags2): .ccx skips a player whose no-touch timer
(+$5E) runs (shot / pass 16 frames, steal both 20 + Stk / 2, deflect / body bounce / net strip 8, puck into the goalie
20 (goalie 10), fall 120, faceoff 20, goalie dive 8); then height > 5, Zvel > $200, reach 14 (7 while the puck's own
+$5E runs), goalie 8, speed limit. Blade contacts: timer running 1,078, taken 27. The walk (checkpuckcoll .0 / .1): Ylist ($B84A,
the sort key: our Y; X only while sflags bit 7 sfhor is set, at stoppage screens), OOlistpos $B86A, OOlist $B88A
(object x 2); from the puck outward, stopping at the first object more than 22 ($16) up or down from the puck's Y: only
players whose BODY is within 22 in y are tested, so a stick held 20 out in front can sit on the puck untested (2219
sample 9170). Clean test (seven Genesis games: slow low puck within 11 of the blade, timer out, not shooting / passing /
faceoff, reached by the walk): 117 / 137 taken, 7 another stick first, 13 after a whistle (gmode bit 0, puck pfnc).
SNES (analysis/snes_pickup_study.py, 2026-10-19): nopuck $1203 (word per object; shot / untargeted pass 16, targeted
pass its lead time d6, one-timer swing 10, flip 30, steal both Stk + 20, deflect / body / net 8, into the goalie 20 (goalie
10), fall 120, faceoff 20, box / breakaway glide 60, goal celebration 1800); walk within 40 in y (never blocked);
puckz / puckvz are single words ($0DF9 / $0E01), not per-object arrays; puckc $0AD9 (2 x object). Contacts: catch 924 /
1023, timer 21 / 1208, too high 0 / 80, too fast 0 / 21. SNES_MECHANICS 6.2, SNES_GUIDE 8.1. Record fields: Xpos 0, Ypos $14, Zpos $18 are current; the
match file reads OldXpos / OldYpos / OldZpos ($1C / $20 / $24, the previous frame's). Ylist ($B84A) holds our X: the
game's internal axes are the NHLPA93 horizontal ones, swapped for display (sfhor). GENESIS_MECHANICS 6.2, GENESIS_GUIDE 8.
Uncounted saves explained in GENESIS_SHOOTING 4.7 (analysis/uncounted_study.py); by direction the recordings show
85% counted going up, 91% down (the opposite of the database's gap; samples small). The opponent's iPhone opens game
files from the S3 link; Genesis netplay picks Player 1 / 2 regardless of host, so hosting isn't part of the home edge.

Tapestries (2026-10-18, the user's word): a goal at the end of 2+ quick passes. export_match `add_tapestries` (after
add_own_goals): the last pass (completed or one-timer) to the scorer within TAPESTRY_GOAL_MS 3 s of the goal; each
earlier pass completed to the next passer, released within TAPESTRY_GAP_MS 2.5 s (real time) of the next; the other team
never had the puck; not penalty shots or own goals. A goalie's pass counts as one of the passes (the user, 2026-10-18). Goal `tapestry` {n, chain: roster indices first passer .. scorer}
and kind 'tapestry' (2), 'fine tapestry' (3), 'masterpiece' (4+), beside 'one-timer'. Recordings: about 1 goal in 5;
capture1 P1 3:18 is 8 passes (Montreal, 10 s, five players, a one-timer). Viewer: tag "fine tapestry · 3 passes"
(goalKindText), the chain in goalNotes (A -> B -> C), team stats Shooting "Tapestry goals" and "· 2 / 3 / 4+ passes",
STAT_HELP, Help. Season VERSION 22: team tap / tapA (Team stats TAP), skater tapG / tapIn (Skaters TAP: scored · passed in).
Missed tapestries (the user): the same chain ending in a shot attempt that did not score: the shot gets `tapestry`
{n, chain} (chain_to in add_tapestries). Viewer: shot tooltip "missed tapestry (3 passes: A -> B -> C)", team stats
"Missed tapestries", Help. Season VERSION 23: team tapMiss / tapMissA, skater tapMiss (TAP MISS columns). Documents
games: 29 tapestry goals, 78 missed (55 saved, 10 wide, 7 blocked, 6 posts): about 27% finished.

Super-fast passes and pucks past save moves (2026-10-19, the user, Genesis only). Passes: passtoa0 solves the meeting
time t in whole 1/8 s (truncating divs; 1-24) and sends v = distance x 65536 / (120 t) per axis (capped by divs
overflow: an overflow leaves the puck nearly still); a receiver skating toward the passer 50-70 away gives t 1.x -> 1:
27,000-32,000. analysis/fast_pass_study.py replays the word arithmetic from the sample before each targeted pass
(passplayer $BEE0 set, passspeed $BEDE; receiver +0 / +$14 / +$28 / +$2A, HotList): 750 / 816 within 10%; persons 24 /
718 over 25,000, goalies 5 / 98. SNES dopass sets speed by distance. Save moves: goaliesave picks the side save when the
puck will cross 16+ to his side; the body circle doesn't change (pad stack aside), the stick only plays low pucks not
rising (shots are lifted). analysis/slip_study.py: 12-16 from his centre standing 11 / 82 in, save move 28 / 74; stick
saves 27 / 47 from 12-20. Through the legs (the user's clarification: fast flat puck straight at the middle, butterfly):
butterfly / kick-save frames put the blade 10-13 to the side, so a low non-rising puck through his middle is in the 8-14
blind band (no stick or body test) until behind his centre, where the body hit bounces it backward (offset x 256, slow)
into the net; ready stance has the stick in front. Confirmed on the user's 2v2 game 2026-10-19_0818_ANA-ATL (ROM 784b3674,
Anaheim vs Atlanta): goals P1 2:48, P1 2:11, P3 2:24 (frame 480, puck 1-4 from his centre in the band, bounced back
from 8-13 behind at 2,200-3,500); 2 of 8 such flat pass shots in P1 went in; P3 4:00 was the top net's shoulder-save
bobble (stick knock-up, ghighl hold point 14 behind, net strips it). analysis/goal_trace.py <capture> <period> <m:ss>
traces any moment. Pass lift: targeted puckvz = 256 x min(t, 12) (move.b into puckvz's high byte; 675 / 691),
untargeted randomd0($1000) (quartiles 900 / 2,000 / 3,100); peak height ~ vz^2 / 786432. C freezes a person's goalie (pf2aip: doinput skips his input) ~0.57 s at speed / 4. SNES save
frames add 12-28 hit areas. GENESIS_SHOOTING 5.5 and GENESIS_MECHANICS 6.1, GENESIS_GUIDE 8 and 12.2.

Runaway speed (2026-10-19, the user, Genesis): pfdoff (pflags bit 0, friction >> 9 instead of >> 6) set by asspassrec and
FallDown's boards / bench fall; cleared by asspassrec .exit, puckstick, assnearest insertion, not by assexit (a person
taking over the receiver) or getting up. Bursts (+~6,300) then stack: 2158 BOS-WPG P3 ~1:24 (boards fall, 20,079), 2149
BOS-WPG P2 ~0:22 (taken over mid-pass, 19,413). Flag set 765 times (690 passes, 65 boards falls); a person with it on
> 0.5 s 44 times, runaway only with 2+ bursts. GENESIS_MECHANICS 3.4, GENESIS_GUIDE 5.

## B without the puck: poke or switch (2026-10-19)

The user asked how the game decides. Genesis (input94.asm doinput, title94.asm chgplayer, Sweepcheck): on B's RELEASE
within 17 frames of the press (bholdtimer $11), chgplayer takes the team's on-ice skater nearest the puck + velocity /
256 (about 16 frames ahead), skipping goalies, pf2unav, pfalock and the other controller's skater, the current skater
INCLUDED: the current one -> Sweepcheck (poke), else switch. Locked (pfalock): doinput_islocked switches on the PRESS
(the CB check) and marks the new skater's pflags3 bit 6 so its release does nothing; the same flag swallows the release
after B+C on one frame and after a goalie's pass. analysis/b_button_study.py: 1,510 of 1,536 releases as predicted
(576 pokes, 934 switches), 815 / 844 locked presses switched, 808 / 837 flagged releases did nothing. SNES (doinput,
findpc): on the PRESS; a carried puck with puckdist2 < 100 (about 20 units) and the skater unlocked -> poke; else the
lowest puckdist (no lead) + 32 x (direction steps beyond 1 from up-ice) while carried; current -> poke (unless
locked), else switch; not checked on recordings. GENESIS_MECHANICS 7.5, GENESIS_GUIDE 10, SNES_MECHANICS 7.3, SNES_GUIDE 9.

## One-timers struck at the stick's reach (2026-10-21)

The user asked why a cross-ice one-timer had no xG: Derek King's two doorstep goals in 2026-10-21_1137_NYI-BOS were
backhand one-timer swings ($092E) meeting the puck 26-31 from his body at the far post, past find_shots' body tests
(25 in the swing, 30 in scorer_touch), so they became kind 'other' (no xG). find_shots now also accepts a course change
within STICK_NEAR 14 of the swinging player's stick blade (Genesis: HotList at ROM $A44C8 per sprite frame, x negated when
mirrored, y negated; analyse() hands the table over as match['_hot'], removed after), at that sample or the one before.
12 / 14 / 18 tried on the 12 games that changed: the shot list's one-timers 120 / 130 / 140 against the game's own
one-timers-tried count 131 (old rule 123). King's goals: one-timers, xG 0.66 and 0.76. Shots on goal unchanged against
the game's counts (2219 BOS-DAL's 9 vs 8 was already so: Oates's penalty-shot goal). 2026-10-19_2115_LA-BUF's fast.bin.gz
is cut off (no end-of-stream marker) and fails to convert, before and after (2117 LA-BUF is the game).

## Scoring map: shots played in the real game (2026-10-22)

The user asked for an exact scoring map (the chance a shot scores by spot, aim, shot type). `analysis/scoring_map/`
(build.py's docstring is the how-to). First map done: set goalie (GENESIS_SHOOTING 4.10, docs/img/scoring_map.svg).

- **Run 1**: 23 x 16 spots (x -110..110, y 100..250 by 10) x wrist (C 3 frames, passspeed 18 -> 173) and slapshot
  (C 20+, 35 -> 337) x both nets x 9 aims, 800 launches per aim (perfect / scatter split by the perfect chance), 30
  processes, about 2 hours (each job 3-5 minutes with 30 running). 1,260 of 1,472 jobs valid (puck 24+ from the
  goalie's centre and in front of him; validity.py). The shooter's working Shot Power 20, Shot Accuracy 15; the goalie
  Los Angeles's (weight 48, Agility 13, Speed 13, Def. Awareness 10 working).
- **Mechanisms behind the high cells, each traced**: the Down slapshot straight at the middle goes through the
  butterfly's blind ring (gstick $021E frame 480; the puck at height 0 passes his centre, meets his body behind it and
  bounces in at about 2,550); the "middle" perfect slapshot from 150-170 out peaks at height 5 and does the same; the
  row 55-70 out is the wind-up rule's pad stack (he was stacking at 46-48% of the release moments for slapshots, 34%
  for wrist shots); the far-left high wrist shot at the top net is the shoulder-save bobble (11 of 24 moments, every
  goal after a high save $148E with the puck held).
- **Checked** against natural shots (validate.py) at four spots: 51.6 / 52.0%, 32.6 / 33.9%, 7.3 / 7.8%, 43.0 / 44.4%.
- **Not done yet**: the "as in games" goalie (map_run.py takes xg.goalie_states' JSON as its 7th argument: each launch
  first puts the goalie where a recorded computer goalie was, relative to his set spot, moving as he was; 315 states
  from 16 games), other shooters (its 5th / 6th arguments), one-timers (the harness only makes normal shots).

What's settled about the method:

- **Engine**: the real game, headless. The disassembly builds (SNASM68k via its `build:dev`) from a copy; patch_rom.py
  adds a doshot hook without moving anything outside $B502-$C3xx: the dead lead-time block in `doinput_cbut` `.press`
  (gameclock .. the six branchless cmpi, 164 bytes) becomes two subroutines (SMAPIN at doshot's start, SMAPEX before its
  sfx call) and padding, 8 bytes shorter, paying for the two bsr.w. Hook RAM $FFE000-$E031 (never touched in menus or
  play: the stack only reaches down to $FEC2). The hook records doshot's inputs (seed, passspeed, passdir, puck, the
  goalies' SPA) and, when $E000 is set, replaces puckvx / vy / vz at .ex. emu.py is a ctypes libretro frontend for a
  copy of RetroArch's genesis_plus_gx core (about 4,500 frames a second; one core per process: a second Emu instance
  takes over the DLL's callbacks). RetroArch savestates are RASTATE containers
  (chunk "MEM ").
- **doshot ported exactly** (shotport.py, 68000 integer rules incl. divs overflow leaving the register, the byte
  arithmetic in the scatter size, puckvzadj): the game's launch equals the port's on 129 of 129 shots, both nets, 7 with
  the top-shelf lift. The LCG: seed = seed x $BB40E62D + 1, randomd0(n) = ((seed >> 8) & $FFFF) x n >> 16.
- **What is random after the release**: the goalie's movement code (checkanim, findpc, goaliesave) never calls the
  generator, but what happens on contact does (hold or rebound, 5.2; the stick's deflection direction). Replays first
  kept the seed and were biased (5.6% against 7.8% natural at one spot); the seed is now randomised after the release.
  Checked: the estimate equals natural shots (the game's own draws from a random seed) at three spots within one
  standard error (51.6 / 52.0%, 32.6 / 33.9%, 7.3 / 7.8%).
- **The moment matters**: a perfect slapshot just inside the post at mid-height from 108 out scored at 13 of 16
  moments: the goalie committed to a stick save (gstick, $01EC) at once and stayed at x 0 (reach 13, the puck at 16),
  unless his rethink happened to fall before; findpc (every 5 frames) and his rethink cycle set it. The map uses 120
  moments: clock 590-583 x 15 settle lengths.
- **Fast stop**: decided when the goalie has held the puck 20 frames, or it has moved away from the goal 4 frames, or
  it is 12 past the goal line; agrees with a 240-frame play-out on 1,475 of 1,475. (Not as soon as he holds it:
  the top net's shoulder-save bobble, 5.3, lets six in at frames 48-79.)
- **Harness limit near the net**: the shooter is held on his spot while the goalie sets, and within about 30 units of
  the net's centre the goalie's set spot is the puck itself, so he skates onto it and the shot starts inside his reach
  (65-100% "goals" from 28-48 out in the middle). validity.py keeps spots where the puck starts 20+ from the goalie's
  centre and in front of him: 1,279 of 1,472.
- **Recorded shots replayed** (replay_recorded.py: 135 aimed shots at computer goalies, recorded puck spot to the unit,
  aim, speed, Shot Accuracy, the goalie's position, velocity and working ratings): totals agree (20.5 / 22.5 expected
  with a 2 / 4-unit goalie blur, 22 scored) but shot by shot the replay is too sure (113 shots at a standing goalie:
  log loss 0.253 with the 2-unit blur, xg.py 0.23, one rate 0.357): the recordings (60 Hz, not frame-locked, the
  previous frame's position, velocity over 100 ms, no AI state) don't pin the moment down finely enough, and xg.py's
  fitted spread suits that. Goalies recorded mid-save or diving are replayed standing (their animation isn't set):
  22 such shots, the replay's worst.

**SNES map (2026-10-23; SNES_SHOOTING 4.8, docs/img/snes_scoring_map.svg).** The user asked for the same study on the
SNES. `snes_emu.py` (the frontend over a copy of RetroArch's snes9x core, about 3,500 frames a second; SYSTEM_RAM is
banks $7E-$7F in natural little-endian order), `snes_make_states.py`, `snes_harness.py`, `snes_map_run.py`,
`snes_compare_xg.py`; render_map.py draws a SNES run too.

- **No test ROM**: the retail ROM (the disassembly's lst/nhl94snes.sfc) unmodified. The release frame is found by the
  puck coming loose (puckc $0AD9 negative) during the wind-up; that frame is replayed with a fresh seed ($0792 / $0794,
  RandomWord's two shift registers, both kept nonzero), so every draw is the game's own. Natural sampling instead of the
  Genesis's split by the perfect chance: 16 moments (a seed for the settle, the clock, 80-94 frames to settle) x 24
  release seeds per aim. The goalie's positioning calls the generator (his look-ahead), unlike the Genesis.
  **Too few moments** (found making the animations, 2026-10-23): the first 16 moments (p < 16) gave 47.7% at the top
  lane spot, p 16-63 gave 58.1%; over all 120 moments x 4 seeds 53.6%, with a moment-to-moment standard deviation of
  0.25-0.29, so a 16-moment square is good to about 7 points. Bottom lane spot 26.5% (map 30.2%), mirror 1.7% (0.8%).
  The Genesis map used all 120 and agrees (43.8% / 44.5% against 43.0%). A SNES rerun should use 120 moments.
  **Frame timing**: the SNES game loop doesn't move the puck every frame; with only the shooter left in place after the
  release (map: parked at -64, +/-230) the puck's stand-still frames shifted from frame 5 on and a lane shot that had
  skipped past the goalie's box edge (-234 to -245, goalie at y -238) was checked at -240 and saved. 480 shots each,
  parked / kept: top lane 53.6 / 53.8%, bottom lane 26.5 / 20.4%, mirror 1.7 / 0.8%. Genesis unchanged (51 / 52 of
  120). Any SNES study should keep the realistic set of skaters on the ice (or test the sensitivity).
  **SNES screen position**: the rink never scrolls sideways (the net's middle is column 128) and the screen follows the
  rink layer's scroll (07DC, a ring buffer; goal-line row = 422 - 07DC at the bottom net in one test), not Vpos (0D37),
  which ran up to 9 pixels off it; the first SNES animations jerked because their crop followed Vpos and the scroll-lock
  x (0D4B, 12 -> 26 during a shot). goal_frames.net_on_screen now reads the goal line's row off each frame.
  **Gentle mode** (lowload.py, 2026-10-23): 6 workers at below-normal priority still spun the user's fan up; now 2 workers
  at idle priority, each sleeping as long as it works (DUTY 0.5): the animations took 107 s instead of 28, the machine
  averaging 8% CPU (about 5% idle).
  **Genesis clock and score boxes** in the animations: rows 23-27 of plane A (map at VmMAP1 = E000, 64 columns), which
  doesn't scroll, so with the crop following the rink they slid into view; every other plane A tile is the transparent
  07FF. Video memory isn't exposed by the core, but its save state holds it (found after the state's 1 KB sprite-table
  copy, which reappears in video memory at DC00; work RAM at state offset 16): animate.py fills those rows with 07FF
  before each frame drawn (goal_frames.hide_genesis_hud). Display only: the four Genesis spots' 120-shot tallies were
  identical with and without it. That left a flash now and then (the game rewrites the clock's and score box's map
  entries at the start of a frame, before it is drawn), so the boxes' tile graphics are cleared too: the EA logo
  1C6-1D0, the borders 3FC-404 and the small font from smallfontchars (B012 = 405), 64 characters.
- **Controls**: A shoots (cbut $0080; ShotMode: a tap jumps the animation to its end, so the wrist shot leaves at frame
  3, passspeed 15 + frames; a slapshot at frame 26), B passes, Y flips. Boot: 12 x Start from power-on reaches the
  rink's "Start Game" menu, then Start again: Los Angeles (home, pad 1, the centre object 2 controlled) v Montreal, Los
  Angeles attacking the top net in period 1. Positions: Xpos / Ypos integer words with Xfrac / Yfrac beside them.
- **Run snes1**: x -110..110, y 90..250 by 10, both nets, wrist (A 3 frames) and slapshot (A 40), 9 aims; Shot Power /
  Accuracy 13 / 13 (the median of 297 recorded SNES shots); Montreal's goalie (weight 48, legstr 8, legspd 8, aidef 7
  working). 782 jobs on 30 processes, about 1 h 50; 2.07 million valid shots. Checked with the goalie moved away: the
  empty-net rates of 4.2.
- **Result**: averaged over the aims everything under about 1%; the hot cells are one lane (the shooter's left of
  centre by 6-16, aimed at that side, about the perfect-shot chance). Scanned at 2- and 3-unit steps (6 moments x 16
  seeds) to separate it from the 10-unit grid. Traced: the perfect shot passes 12-13 from the goalie's centre, outside
  his body box; his side save move on his right ($E862) holds a frame with its area at 25-28, on his left ($E7D0) at
  19-22. xg_snes.py's averages agree but it doesn't find the lane (its 2-unit goalie spread blurs it).
- **How the goals go in (2026-10-23)**: `goal_types.py SYSTEM RUN` plays a fresh natural sample over the maps' spots
  (Genesis 12 moments x 8 seeds: 1,088,208 shots, 12,810 goals; SNES 8 x 8: 761,400 shots, 2,725 goals) and sorts each
  goal from the puck and goalie state every frame (held; a speed jump near a post / the goalie, and for the Genesis
  whether it touched him behind his centre low = the blind ring; his animation at the closest pass). Genesis: blind
  ring 47%, pad stack 23%, clean (never within reach 13) 21%, held then in 7% (top net), off the goalie 2%. SNES: past a
  right-side save move 51%, off the goalie 24%, past a left-side move 21%, during a poke check ($E528) 2%. The lane's
  911 goals: 873 past right-side moves (glove 491, stick 293, sprawl 89). Goal-frame checks: the last frame of a goal's
  path is after the game has moved the puck (left out); the Genesis goal registers with the puck at y about 260.
  `goal_frames.py` replays a goal exactly (same moment and seeds) and saves four of the game's own frames cropped on
  the net (camera: Genesis BD18 / BD1C, offsets 118 / 126.5; SNES Vpos 0D37 and 0D4B, 114 / 124, read off frames);
  `goal_diagram.py` draws the crease from above and the puck's height. SNES save-move addresses checked against the
  frames94s.asm table sizes: E1E2 glove r, E214 glove l, E246 stick r, E278 stick l, E2AA stack r, E2FC stack l, E73E
  butterfly, E7D0 sprawl l, E862 sprawl r (xg_snes.SAVES is in GoalieSaveList order).

**Genesis xG: the goalie's stick and the rebound rule (2026-10-23; xg.play_out `stick`, `rebound`, both off).** The
stick as checkpuckcoll .ccx tests it (puck z <= 5, Zvel <= $200: the blade = his sprite frame's HotList hot point;
within 8 puckstick plays it, 8-14 nothing and no body test), his save move chosen as goaliesave does (frames from the
ROM's animation scripts; the same in every Genesis ROM here), and puckgoalie's hold-or-rebound (hold if both speed
parts are under (random((2 + Puck Control) << 9) + $C00) x 2, a quarter when standing with the puck within 44 across
and 210-270 out; else bounce at 256 x the offset from his centre, Zvel 0, no touch for 10 frames). Checked
(xg_stick_eval.py): against the map with no position blur (the map goalie is exact) the model now matches the game
(slapshots 88-168 out, mean of five aims, top 7.2% game / 7.2% model, bottom 4.9 / 5.1; 58-87 out 3.4 / 4.4 and
3.0 / 2.9; before: 0.5%), but overshoots the Down slapshot from the middle (20.7 / 34.1 top, 13.6 / 24.0 bottom). At
one spot (x 0, 118 out) 43% game, 44% model. GOALIE_SPREAD hides the blind ring: blur 4 -> 16% there, 2 -> 23%, 0 ->
44%. On the recorded games (661 shots) the new model doesn't help: log loss 0.3314 before and with it at blur 4,
0.378 / 0.428 / 0.479 at blur 2 / 1 / 0 (recordings don't pin the goalie down to a few units). Not adopted for
recorded shots. The Down overshoot traced: in the game the same butterfly (21E) at x -10 and +10, the puck
  leaving 6 units left of the shooter and 12 in front, the goalie at y 240; from those real starts the model matches the
  edges (x -20: 3% / 4%, +20: 18% / 19%) but not the middle (12% / 43%): the puck clips the body 12.4 from his centre
  in front of him the frame before it would enter the ring. Which happens turns on a unit of start or goalie position
  (5.6 units a frame), so the model matches averages, not spots. Viewer (2026-10-23): the xG map's set goalie uses the
  stick and rebound with no blur (XG_GEN_ROM from `xg.py --stick-tables <rom>`; checked against Python, the Down
  slapshot from the slot 0.345 JS / 0.363 Python, 3,000 shots each); as-in-games and recorded xG unchanged.

**One-timer study, pilot (2026-10-23).** `ot_harness.py` (pass, press, swing, strike, play-out on both systems),
`ot_run.py` (chunked and resumable: jobs appended to a JSONL as they finish, a chunk stops starting jobs after its time
budget, the next run skips finished jobs; the user approves each chunk), `ot_report.py`. Harness lessons: (1) a
receiver whose position is rewritten every frame can't touch the puck (not even catch a plain pass): he's held only
while the goalie settles; (2) SNES passes need B held with the direction for 4 frames (the loop runs every other frame;
a release before it reads the direction passes the way he faces, setpassmode); (3) the SNES one-timer's aim is read
during the swing, so the d-pad is held from the press, and the aims branch at the press, not at the strike; (4) the
Genesis strike is puckstick -> onetimershot when the puck reaches the blade (within 8) in the one-timer state.
Pilot (net top; receivers (0,200), (40,230), (-30,150); passers 60 and 120 away in 8 directions; 30 jobs a system;
early press = 2 frames after the release, late = about 6 frames before arrival; 32 moments; Genesis 8 seeds, SNES 9
aims x 4 seeds): Genesis early 896 strikes in 960, goal rate per job median 16.6% (max 81%), late 688 in 737, median
1.7%; SNES early 867 in 959, median 5.0% over the aims (best aim median 26%), late median 2.7%. Moment-to-moment sd of
a job's rate: Genesis early median 0.16 (max 0.33), so 32 moments give about +/-3 points; SNES (aims pooled) 0.05.
Times in gentle mode: Genesis 30 jobs in 3.2 min, SNES in 15.5 min; CPU averaged 5% (peak 19%).
**Timing the press (2026-10-23):** his blade is 10-13 in front of him, so on slower passes it takes the puck before
the puck reaches his centre; the pass is played once without a press to find the frame he'd take it, and
late = 2-10 frames before that; early = 2-5 frames after the release; both spread over the moments because the swing
has narrow timing holes (a long pass across whiffed at every moment pressed 6 frames before the catch, struck at 4 and
8). Genesis pilot (otpilot2): early median 16.6%, late 16.2%; the pass reached the late press 876 / 960. SNES pilot:
early median 4.9% over the aims (best aim 25.4%), late 4.3% (best 24.2%); the pass reached the late press 860 / 960,
a strike in 769 of those (early 866 / 959); 30 jobs in 15.2 min.
**Genesis full run (2026-10-23, run otfull, two chunks: top 412 jobs in 47.9 min, bottom 412 in 42.7 min, gentle
mode).** 42 receivers x 6-13 passers x 2 nets, early and late, 32 moments, 8 seeds a strike. The pass reached the
press 25,884 / 26,368 early, 21,819 / 26,368 late; strikes 21,560 and 19,962. Goal rate per job median 2.7% (both
timings; most jobs are far out), mean 14-16% both nets. Per receiver (pooled): doorstep middle 62%, 18 ft out 46-53%
within 10 ft of the middle, 27 ft 31-44%, 35 ft 2-14%, beyond 1-2%. Receiver inside 18 ft: pass across at the same
depth 63% (13 of 18 over 50%), across from farther out 43%, from his own side 20-30%. Top vs bottom by set-up:
correlation 0.82 early / 0.73 late, 56 / 70 set-ups more than 15 points apart; mirroring the bottom net in x gives 0.85
/ 0.73 (no mirror effect). Write-up: SCORING_GENESIS "One-timers", Genesis, GENESIS_SHOOTING 4.10. SNES chunk 1 (top)
started the same day.
**xG check (`ot_xg_check.py 14 8`, 2026-10-23, one process at duty 0.33 beside SNES chunk 2):** 59 set-ups (every 14th
job), 748 strikes; at each the strike state read from RAM, 8 seeds played out, and xg.play_out 400 times from it as
add_expected_goals would (auto_aim from his coming spot, reach 12, ShA 15). Game 20.7%, model 22.1% (blur 4), 19.1%
(blur 0), 19.2% (stick + rebound, blur 0); log loss 0.290 / 0.320 / 0.318 (one rate 0.510); correlation 0.83 / 0.81 /
0.81. Receiver inside 55: across game 0.69 model 0.67, same side 0.24 / 0.24. Goalie off the puck-to-net line at the
strike: across median 12.0 (speed 50 units/s), same side 3.7 (29); off 0-5: 25% scored, 5-10 46%, 10-20 86%, 20+ 96%.
The model is kept as it is. Practice card Test 3 / NEEDS_FROM_YOU item 7: the one-timer across vs the same side.

## Game mechanics from the disassemblies (2026-10-17)

Read from the commented Genesis disassembly (github.com/abdulahmad/NHL94Genesis: src/crowd94.asm, collide94.asm,
input94.asm, checks94.asm) and the SNES one (abdulahmad/NHL94SNES: src/routines/collide/setplayer.asm,
Create_HotCold_Table.asm), and checked against the recordings where marked. Nothing is built from them yet.
- Working ratings (Genesis): `setplayer` turns each rating nibble r into r x 5 + hot/cold, clamped 0-30, whenever a
  player comes on the ice, and keeps them in his record: +$67 Wgt (nibble x 8), $68 Agl, $69 Spd, $6A OfA and $6B DfA
  (transformed: (30 - (v + bonuses) / 2) / 2), $6C ShP, $6D ShA, $6E Pas, $70 PS bias, $71 Stk, $72 End, $73 Agr,
  $75 Chk. So every recording holds every player's working ratings (fast.bin covers $B000-$BFFF).
- Hot / cold (Genesis): team block +$1A2, 16 bytes per roster place, random -9..8, rolled at StartGame (and again
  by the scouting report), constant all game (checked). BUG, checked: AttributeCalc loads the rating number and then
  clears the register, so play uses only byte 0 of a player's 16 for all his ratings (int(byte0 / 3): -3..+2 on the
  0-30 scale). In 4,000+ samples across four games (one a 30-team ROM) where byte 0 and the rating's own byte give
  different results, Agl / Spd / ShP / End always match byte 0. The scouting report's hot / cold players and the
  matchup screen's flame / snowflake icons sum bytes 3-15, and the player cards add each rating's own byte, so
  what the game shows has nothing to do with what is played.
- Hot / cold (SNES): HotColdTable $1A12, 12 bytes per player ((roster place + 26 if Away) x 12 + rating number:
  0 Agl, 1 Spd, 2 OfA, 3 DfA, 4 ShP, 5 Chk, 6 Stk, 7 ShA, 8 End, 9 PS bias, 10 Pas, 11 goalie glove), random -12..12;
  working rating = (nibble & 7) x 5 / 2 + bonuses + byte >> 2, clamped 0-15 (arrays legstr $12E3, legspd $1303,
  shotspd $1363, shotacc $1383, endurance $1423 ..., a word per object). BUG, checked in all three SNES games
  (NHL94_Classic and SDL16): the shift is unsigned and the sign extension tests `bit #$00`, so a negative ("cold")
  byte becomes 60-63 and the rating goes to the maximum, 15. About 46% of every player's ratings are maxed each game.
  HotColdRaised $19CE: meant to raise four bytes of each entry by 2 at 110 dB, but the raise (ShowCrowdMeter .11) is
  never called; 0 in every recording (2026-10-21, analysis/crowd_study.py).
- Hidden bonuses (both systems; Genesis checked): power play / penalty kill (the team's ROM byte: PP to OfA, Stk, ShA,
  Pas; PK negative to OfA, Stk, ShA), home / away (a per-team ROM byte: home nibble added, away nibble subtracted, to
  OfA, DfA, Stk, ShA, Pas: Boston +2 at home, -1 away; Calgary 0 at home), and ThirdPBonus +2 to OfA and Chk (+4 PS
  bias) for a team tied or trailing. BUG, checked: the third-period test is the wrong way round, so the bonus is on
  while more than half the third period is left (5-minute periods: before 2:30) and off after; overtime always.
- Shots (Genesis doshot): aimed at (table x, Y +/-264). Within 200 units the shot is perfect (straight at the aim
  point) when randomd0(16 + ShA) > 14, i.e. (ShA + 1) / (ShA + 16); always with the shooter's goalie pulled or in a
  shootout; never beyond 200. Otherwise scatter: s = (speed / 16 - ShA / 2 + 16) x distance / 64, halved within 250,
  at most 136; X += random +/-s, the aiming Y += random +/-min(s, 60) (halved when shooting down the screen), height
  += random 0..s/2 (shots only scatter upward). Backhands lose a quarter of their power; one-timers start at power $1F;
  power is scaled by the shooter's energy. Checked: within 200, 82 of 123 shots left the stick within 2 units of the
  aim point, rising with ShA much as predicted; beyond 200 none.
- Auto-aim (shotdiradj): one-timers and computer shooters ignore the stick: middle height on the side away from where
  the goalie is heading (passdir 2 / 6), high in the middle (0) when he is far off centre, 8 with no goalie.
  High shots from in close (|Y| >= 216, stick up / up-left / up-right) at a goalie IN a pad stack or with none on the
  ice (pulled) get puckvzadj ("in-close top shelf"; chaos's forum post, topic 36095, checked against the code): it
  replaces puckvz (no upward scatter), reaching the goal line ~10-13 high from 30-48 out, over the bar inside ~25; never
  one-timers. Same post, checked against the code: the scatter is halved at 250 or LESS (his post says more), Y halved
  when the aim's dy < 0 (bottom net from in front; top net from behind; not dy = 0), the perfect chance is (ShA + 1) /
  (ShA + 16) (his 69.6% at 30 counts 14 as a success); his wind-up maxima (passspeed 31 for ShP < 20, 35 otherwise;
  one-timers 31) and speed formula agree with ours.
- Saves are geometry, not a roll (checkpuckcoll / puckgoalie / puckstick): a puck at height <= 15 within the goalie's
  reach of his centre hits him: reach 12-15 by agility (+2 agility from the "crowd meter broken" flag, which is always
  set), 15 whenever a person controls him, 18 in a pad stack, 12 against a one-timer, 2 less in a shootout. Before
  that, a puck at height <= 5 within 14 of his stick blade (HotList at ROM $A44C8: x, y bytes per frame, x negated when
  mirrored, y negated) is the stick's: within 8 he plays it (slower than 13000 he catches it, faster it deflects in a
  random direction), between 8 and 14 nothing happens that frame (the body test is skipped). After a body touch the
  puck is held if slow enough (random by his PkC), else bounces off. The glove / stick "save odds" the routine looks up
  are never used. Checked on 111 goals and saves: as the puck reached his line, saves passed a median 13 units from his
  centre (49 of 71 within 15), goals 24 (31 of 40 at 15 or more); 5 of the 9 goals that passed within 15 were
  one-timers. So expected goals can come from the game's own rules: the chance the scatter takes the shot past his reach.
- Shots on goal (ChkShotStat): counted when the puck touches the goalie's body (puckgoalie) or his stick catches it, while
  the "shot taken" flag set at the release still stands; any touch (a2touchpuck), the boards (wallcoll) or a stick
  deflection clears it without counting, and nothing counts while the clock is stopped (penalty shots: capture3's
  Oates). Pass shots never set the flag. The "saved, not counted" shots, one by one (2026-10-18,
  analysis/uncounted_study.py, by how each save ended): of 34, 17 knocked away slowly in a random direction (the
  goalie's stick: deflect's +/-$1000 each way, puck at height <= 5, 16-33 from his centre), 3 with the clock stopped (two
  arriving after 0:00 at a period's end, capture3's penalty shot), 6 wide off the end boards / behind the net first,
  about 4 off a skater's body in front (height 8-12); held or bounced radially (body) 165 counted of 173. About 15
  counted saves also look like stick deflections (sampling). GENESIS_SHOOTING 4.7.
- Checks (CCStart): only a burst ($0C5E) checks; impact = closing speed along the line between them (at least 5; a
  check needs 20), and hits taken add up (impact(a2)). Knockdown when (base - checker weight + target weight) / 2 -
  impact <= 0, or he is against the boards, else when randomd0(that) <= Chk / 2 (weight = Wgt rating x 8, record +$67);
  base 120, 240 for a checker a person controls at the moment of contact (pflags bit 3). Goalies cannot be knocked down
  this way. THE WEIGHT BUG (the community's name; confirmed): the sum is done in one byte (sub.b / add.b at ROM $13D72),
  so for a person's checker 240 - Wc + Wt wraps past 255 whenever the target is 2+ weight points heavier: threshold
  (8 x diff - 16) / 2, 0 (automatic) at exactly 2 heavier; against a target the same or lighter it stays 76-124, far
  worse than the computer's 60 + 4 x diff (16-92, no wrap: heavier checkers do better, as physics would have it). So a
  person checks best when light and badly when heavy. The "CB check" (C to burst, then B to switch control away before
  contact) makes the contact a computer one: the 120 formula, where his weight helps; but checkagr's penalty range is not
  doubled for the computer, so twice the charging / roughing chance. Recordings (8 Genesis games, lunges that met an
  opponent; target 2+ heavier / within 1 / 2+ lighter): person 48% / 15% / 7%; computer 15% / 27% / 34%; CB checks
  (controlled at the burst, not at contact) 10 of 18. The NOSE editor's hacks: weightFix at $13D72 and checkFix at
  $13D6C (6700 0004 -> 4E71 4E71: everyone uses 240, so CB gains nothing in knockdowns, still doubles the penalty
  risk, and computer checkers get the weight bug). The weight "fix" rests on a misreading (the editor's comment: the
  original "takes the checker's weight from the other player's, so that light players check well and heavy ones fall
  over"; in fact the original sum is physical and only the person's byte overflow is wrong). 'simple' swaps sub.b /
  add.b (base - target + checker: computer checkers better the lighter they are; a person's overflows when 2+ heavier);
  'on' hooks base - target + 3/4 checker + 2 x Chk - 14, still in a byte (the same reversal for the computer; a person's
  overflows once weight and Checking are high: equal 60s, Chk 23+). Worked through in GENESIS_MECHANICS.md 7.2. The user's
  rule (2026-10-17): where the editor and the disassembly disagree, trust the disassembly. The editor's other play
  settings, checked against the code: goalieWidth / goalieOut ($B632 / $B66A, doinput_chkanim) and goalieLine ($D3EA,
  assgoaliectrl) bind only a goalie a person controls; energyDrain 33 is taken about 1 frame in 128 (HV counter test)
  and Endurance / 2 is given back only above $C00 (capture5: steps -33 and -20..-26, -204 bursts, +9 a second on the
  bench); speedBurst replaces energy >> 7 (32 fresh); turnRate is stopna's 150 a frame (stopping, and reversing in
  noturn0).
  A ROM hacker's correction (via the user, 2026-10-17): checkFix should make everyone 120, not 240. NOPing the
  asl.w #1,d0 (E340 at $13D70) instead of the beq gives base 120 for all: 120 - Wc + Wt stays 0-240, so no overflow,
  fixing the weight bug and CB at once (a person's checks then as easy as the computer's: about 30% instead of 10% at
  equal weight). genesis_settings reads checkFix as False / True (everyone 240) / "120"; WJ2025 is True. Of the 65 Genesis ROMs in the ROM folder, all the
  NHL '94-based ones (CDL league ROMs, nhl94.bin) have the original code; only WJ2025_v01.bin has the CB fix; none the
  weight fix. SNES: 16-bit sums and no person doubling, so no weight bug and nothing gained by CB.
  Penalties (checkagr): randomd0(((40 - Agr) / 2) x 13), doubled for a person,
  halved within 40 of the puck; small = penalty; none while the other team has a delayed penalty.
  A knocked-down target with working Stk >= 24 only stumbles when the impact is under a random 16-31 (FallDown).
  Injuries (FallDown -> setInjuryType): on a knockdown, 1 in 4, then randomd0(160) <= impact (harder hits hurt more),
  clock running; roughing is called if penalties are on. Out for the game or the period by the CHECKER's H/F
  (fighting) value (getFgtbyte: H/F / 4 = 3, or chkFgtBit1), else for the period.
- Faceoffs, checked on 102 Genesis faceoffs: the roll above picks whose direction the puck goes, and the puck leaves at
  dirtab x 32 (6400 straight, 4512 per axis diagonal) plus 2048 toward the roll winner's own end; every drop decodes to
  exactly one team that way. A person who won the roll got his held direction 37 times in 49 (the code: 3 in 4, else
  random); with no direction held (the computer never holds one), random among the 5 directions from sideways to
  straight at the other end (30 forward, 18 sideways, 1 back). Home won 42 rolls where the timing model predicted 44.4.
  The swing animation cycles (wind-up 1 / 21, middle 258 / 266, sweep 257 / 265, back to the wind-up), so timing is
  being on the sweep frame at the drop. The faceoff-won stat (+$0E, puckglue) goes to whoever first takes possession
  after it: it agreed with the roll winner only 52 times in 102.
  The swing (updateanim; durations in frames): a NEW B press (doinput d1 = new buttons) starts SPAfaceoff unless one is in
  progress: 2 frames wind-up (0), 10 middle (8), 6 sweep (16), then it ends (not a looping animation) and the centre goes
  back to his stance (0) until the next press; holding B does nothing more. The drop comes randomd0(120) + 180 frames
  (3-5 s) after the faceoff box appears (at least 270 with some arena animations); the box's drop picture changes 17 and
  9 frames before it (updatefaceoff), too late to react to for the sweep. The person's faceoffs (110, six Genesis games):
  7-11 B presses in the last 1.5 s; state at the drop 16 / 8 / 0 = 23% / 47% / 26%, as mashing predicts (an 18-frame
  swing plus a few frames' gap). P(roll) = (17 + yours - theirs) / 33 is linear, so only the average state counts: the
  shorter the gaps between swings (faster mashing), the better: 9.8 with none, 7.9 with the recordings' 4 frames.
- Penalties (Genesis), all from the code; every penalty goes through AddPenalty (ignored while the clock is stopped,
  with penalties off, or when the player already has one pending: pflags2 bit 4). Penaltylist codes: $16 charging, $18
  slashing, $1A / $12 roughing, $1C cross-checking, $1E hooking, $20 tripping, $22 interference, $24 holding, $26 / $28
  fighting, $2A instigator, $2C delay (fighting, instigator and delay are never called: checkfight is an rts).
  The roll (checkagr): R = ((40 - Agr) / 2) x 13, x 2 for a checker a person controls, / 2 within 40 (x and y) of the
  puck; d0 = randomd0(R); a penalty when d0 <= the action's threshold. Agr is the working value AND 15 (setplayer masks
  it): rating 1 -> 2-7, 2 -> 8-12, 3 -> 12-15 (or 0), 4 -> 1-6, 5 -> 10 (checked, 1,111 samples), so rating 4 plays like
  rating 1. While one team has a penalty pending (DelayedPen bit 1 home, bit 2 away; cleared at the faceoff), checkagr
  returns $7F for the OTHER team's players, so they cannot be called for checks, holds, hooks or trips until the
  whistle; the team already penalised can take more (any player but one already called: pflags2 bit 4); goalie
  interference and an injury's roughing do not go through checkagr, so they can still put the other team in the box at
  that whistle. SNES: no DelayedPen test anywhere, so both teams can be called at one whistle (both multi-penalty
  whistles in the recordings are SNES: TOR-CHI, and snes_2026-10-15_1755's cross-check then interference). If the player fouled is on a
  breakaway, d0 = randomd0(8 / 7 / 4 / 3 by his distance from the goal line: > 117 / 59-117 / 45-58 / closer) whatever
  the ratings, and PenShotChk turns it into a penalty shot through PenShotPenalties, a table off by one: charging is
  awarded as "slashing", slashing "roughing", roughing "cross-checking", cross-checking "hooking", hooking "tripping",
  tripping "interference"; holding and interference give no penalty shot.
  By action: a burst check (C) that leaves him up: d0 <= 4, charging or slashing 50 / 50 (HV counter bit); one that
  knocks him down: d0 <= 3, roughing or cross-checking 50 / 50; one that injures him: roughing, no roll (AddPenalty2);
  a poke (B, sweepchk) whose body touches a skater within 45 degrees of where he faces: he always falls when penalties
  are on (with them off, a person's poke trips only when randomd0(32 + Chk - target Agl) >= 24), tripping on d0 <= 4;
  A: hook ($1122), or hold when he has just collided with the opponent ahead (Acheck): holding the man within 45
  degrees of where he faces, d0 <= 6: holding after a hold, hooking after a hook; goalie interference (checkint): a
  skater hitting a goalie who stands in his crease area (|x| <= 20, 239-266 from centre toward his net) with the
  goalie's impact over 30 falls and, if a CPU-team skater or the controlled skater of a person's team (never a
  computer teammate on a person's team), is called when randomd0(40 - Agr) <= 4 (12-20%, no doubling for people).
  Recordings: of the 4 Genesis penalties with a known foul moment, both slashing calls came from shoulder checks that
  left the man up, roughing from one that knocked him down; Neely's roughing came with Jagr's injury.
  Other whistles (AddPenalty2): goalie holding the puck (temp5: $8C frames after he takes it, 5 when he takes it in a
  dive), a person's goalie past |Y| 170, puck out of play, goals, period end.
- Penalties (SNES): checkagr R = (20 - Agr) x 16 (Agr = the working value in aggress $1443 for skaters: rating byte 7
  low nibble, hot / cold index 11), doubled for a person (playerpad not negative) and halved within $29 of the puck. The
  accumulator is 16-bit there (`lda.w #$0014` is a word immediate), so `asl.b d0` / `lsr.b d0` (".b" is the direct-page
  operand, not the width) shift the whole word, and randoma takes ranges of 256 and up through Mul16U: nothing wraps.
  A person's range is 640 at Agr 0 down to 160 at 15, half the computer's chance at every value (2026-10-30, read again
  from the code). SNES codes as in the SNES section. Recordings (first 14; 31 of 52 by 2026-10-30, penalty_aggression.py): 11 of 14 SNES
  penalties by players at working Agr 15, the value the hot / cold bug gives every "cold" rating.
  SNES goalie interference (checkint): no person / computer test (the user: both are called; recordings: Ruuttu and
  Gill as computer skaters of person-played teams): the skater falls on impact as on the Genesis, then with the goalie's
  impact >= 31 and the goalie in his crease (goalieflags $0B05 bit 2 clear: |x| < 40, 228-259 from centre, set by
  assgoalie) it is called when randoma8(20 - Agr) < 2: 2 / (20 - Agr), 15% at Agr 7, 40% at Agr 15; 4 of the 14 SNES
  penalties were interference. The Genesis rule (only the controlled skater of a person's team) is from the code; no
  Genesis interference call has been recorded.
- Skater-goalie collisions (checkint .ci, both systems; the user asked): every frame two opponents overlap while closing,
  both gain impact (closing speed, at least 5); impact fades 2 a frame. A goalie is never knocked down (CCStart and
  Bcheck skip goalies; checkint only fells the skater). The skater goes to FallDown when he is the puck carrier and his
  impact is over 2 (any touch), or without the puck over 25 (Genesis; SNES >= 26): a fast collision or ~8 frames of
  pushing. FallDown: a stumble (the "wobble", SPAstumble) instead of a fall when his working Stk >= 24 of 30 (Genesis;
  SNES >= 12 of 15, which the hot / cold bug gives every "cold" player), no stumble in the last 60 frames (nopuck+1 /
  nopuckb) and impact <= a random 16-31 (SNES 10-25); else a fall (nopuck 120 frames: the puck is gone). Genesis: the
  stumble also lets go of the puck (puckc cleared, no no-touch timer), so he usually takes it straight back; FallDown
  ignores a repeat of the same pair (PlayerChked / PlayerChking), so bumping the same goalie again does nothing until any
  other knockdown or stumble happens. SNES: the stumble keeps the puck outright; no same-pair rule, so a second touch
  within 60 frames of a stumble (the wobble is shorter) is a fall: the user's observation.
  Boards: Genesis FallDown checks the wall at the fallen player (wallcollduringcheck: within his size + 23) and, with the
  hitter on the inside (toward centre ice, or in front when behind the net) and the player outside |x| 104 between the goal
  lines, plays a boards / bench fall and gives the HITTER SPAcrosscheck with his speed cleared; nothing stops a goalie
  hitter getting it, which is the goalie-turns-into-a-cross-checking-skater picture (capture5 P2 2:20, Hawerchuk: the
  goalie's animation $1AC2 at the fall). SNES FallDown has no wall test: any fall in the outer lanes (|x| >= 104, |y| <
  240) with the hitter inside, behind the net (|y| >= 274, |x| < 80) or near a corner arc puts the player on the boards
  (x = +/-130 or y = +/-296) in a boards fall; it never gives the hitter the cross-check animation.
  Recordings (falls and stumbles with the goalie the nearest opponent within 20 and no check): Genesis carriers 22 falls
  (all below Stk 24 fell; two into the boards), 2 stumbles (Oates 25 kept it, Lemieux 29 lost it); SNES carriers 19
  falls / flips, 7 stumbles (all at Stk 13-15; every carrier under 12 fell), Roenick CHI-TOR P3 4:18 stumbled and fell
  0.9 s later. Without the puck: 28 Genesis and 16 SNES skaters went down skating into a goalie, mostly closing at
  85-206 units / s (BOS-PIT P1 0:36 Sweeney lunged into him; CGY-BOS P1 1:52 Roberts; capture6 P2 4:50 Shanahan).
- Repeated checks (FallDown's same-pair rule, Genesis; the user noticed it): FallDown returns at once when the player
  and the hitter are the pair it last handled (PlayerChked / PlayerChking, recorded on every fall and stumble), so after
  checker A knocks B down (or B wobbles from A's check), A cannot knock B down again until FallDown runs for any other
  pair anywhere (a different checker, any knockdown, a stumble, a goalie collision). A check that fails its roll without
  a stumble never reaches FallDown and blocks nothing. Checked (7 Genesis games): 11 lunges into contact when the last
  FallDown anywhere was the same pair, none knocked him down, against 74 of 333 otherwise. SNES FallDown has no such
  rule.
- Delayed-penalty sniping (Genesis doshot): a shot within 200 is always perfect when ReadGoaliePulled finds the
  shooter's team +$26 negative, the $FF flag the team carries while the other side has a delayed penalty pending (the
  game pulls the fouled team's goalie then). The two aimed shots in the recordings during a delayed penalty left the
  stick 0.7 and 0.3 off the aim point. SNES doshot has no such test (only highlight mode is always perfect).
- Rebounds (Genesis puckgoalie): a puck touching the goalie's body is held when both speed components are under a
  random threshold, (randomd0((2 + PkC) x 512) + $C00) x 2, quartered when the puck is in close (|x| <= 44, 210-270 from
  centre) and the goalie is not in a save animation; a diving goalie never holds it. Otherwise it bounces straight out
  from his centre through the point it touched (velocity = offset x 256). Checked on 135 saves: in close with the
  goalie standing 28 rebounds of 47 (60%), in close mid-save 19 of 72 (26%), farther out 2 of 8; rebounds left a
  median 6 degrees (3 in 4 within 19) off the line from his centre through the contact point.
- The flip (A with the puck; the disassembly calls it OneTimerPass, a name from the earlier game): a new A press arms it
  and its release (or 15 frames held, which also opens line changes) fires it (doinput_ispc: sflags5 bit 3 ->
  setpassmode -> dopass). No receiver is chosen (passplayer stays -1), so nobody one-times it, and the d-pad does not aim
  it: OneTimerTarget takes a fixed spot from the PASSER's place and facing (in his attacking direction): outside his
  attacking zone (< 88 from centre toward it) the faceoff circle at (+/-116, 194) on the side he faces (facing straight
  ahead: his right), lofted high (onetimerheight $3A: the puck reaches about 57); inside the zone the high slot (-5, 171),
  or the goal mouth (y 259) when he is at least 138 deep and within 55 of the middle, lofted low ($12: about 13-19); a
  goalie: about (+/-50, -9). Then 0-9 added at random to each, and the spot is moved to 60 units sideways from him when
  it is closer than that. The puck is thrown (OneTimerPass: puckvz = sqrt(12 x height x 65536), speed to reach the spot)
  and lands there. Checked: of 13 lofted flips in 7 Genesis games, 9 came down within 12 of the predicted spot (most
  1-6); CGY-BOS P1 2:41 Oates from behind the net came down at the goal mouth. The computer clears the zone with it
  (checks94 near CompShoot). Over the glass (the user: a neutral-zone flip sometimes goes over the near boards): the
  60-unit rule moves the spot to the passer's x + / - 60 when the circle on the side he faces is less than 60 to his
  side, so a passer outside the attacking zone on that side, about 75 to 116-125 from the middle (the random 0-9 decides
  the edge), facing that way, sends the high lob at a spot past the boards (+/-129), and it crosses them above height
  18 (wallcollb lets it out: whistle). Recordings: BOS-PIT P2 0:51 Oates from x -85 facing left, spot -145, crossed the
  boards at height 44; capture6 P1 1:44 Bourque from x 122 (the random put the circle just past him: spot ~182),
  height 42. Closer to the middle the spot lands at the boards; against the boards it is pulled 60 inside.
  SNES dopass has no such branch (and passes at 144 + 4 x Pas): how the SNES flip works is
  not read yet.
- Breakaways (Genesis BreakawayOffsidesFlagSet / breakaway): the flag (pflags3 pf3break) is set only at the moment the
  carrier crosses the attacking blue line (his offside bit clearing), when every other player on the ice, teammates
  included and goalies excepted, is behind him; it then holds (the ding, +$358) while he keeps the puck and keeps
  skating toward the net (his Y speed toward that end; stopping or turning back ends it), so a defender catching up
  does not end it, and fouls on him meanwhile use checkagr's breakaway roll and PenShotChk. doshot sets gmode2 bit 4 on
  a breakaway shot and clears it at every other shot; a goal while it is set counts as a breakaway goal (+$35A), so only
  a goal with no shot between (pass shot, deflection) after a missed breakaway shot would be miscounted. Recordings:
  every counted breakaway goal came 1.3-2.1 s after its breakaway.
- Computer line changes and clears (Genesis): chk4lc, from the computer carrier at his OfA ticks (asspuckc), with line
  changes On (not Auto: sflags7 bit 4): puck in the attacking half short of the blue line (0-88), a 1 in 4 roll, the
  line's average energy (AvgCline) at most $C00 (75%) -> CompLine, setpersonel, then CompShoot (dump it in to change).
  chk4shot: killing a penalty, or no threat on the carrier, at a 1 in 4 roll: in his own half CompShoot (shoot it down
  the ice), in the neutral zone the flip (sflags5 bit 3 -> dopass).
- Offsides (only with the option on: gmode bit 5; never in a penalty shot). Genesis ChkOffsides, each frame: the
  moment the puck crosses a blue line (y +/-84) into a zone, the team attacking that zone (by gmdir, whoever moved the
  puck: even a defender carrying it back into his own end) is flagged (tmflags bit 4) if any of its players is more
  than 10 past the line (y > 94); ClearOffsidesIfAllPlayers clears the flag once none is past it (tag-up). While
  flagged, the computer's attacking jobs go back to defence (assdefo, asswingo, asscentero test the flag) and a2offsides,
  run inside a2touchpuck, calls offside ($10, a faceoff) when one of that team touches the puck with it more than 104 in
  (so the first 20 units inside the line are free). a2touchpuck runs every frame for the carrier (pucknorm), for stick
  deflections and steals (puckstick), body bounces (puckbody) and the goalie (puckgoalie); the one-timer strike
  (puckstick -> onetimershot) never calls it, so an offside player can one-time a pass with no whistle and the goal
  counts (the user's Genesis quirk). The individual pf3oside bit only serves the breakaway test. A carrier whose body
  leads the puck in by more than 10 (skating backwards) would put himself offside (code reading). SNES (ChkOffsides,
  a2offsides): checks only when the puck's carrier, or its last toucher, is of the attacking team; same 10-unit margin
  ($5E); a2offsides calls it with the puck past blueline ($58 = 88, no free band); asspassrec's one-timer path calls
  a2touchpuck before doshot, so SNES one-timers can be offside. None of the recordings had offsides on.
- Penalty shots (Genesis): awarded (PenShotChk -> getBAplayerInfo) by setting BA_PS_flags ($C2F2) bit 3, "pending", and
  saving the shooter, team and goalie (BA_Sktr_SCnum $D406, BA_Goalie_SCnum $D408). The penalty-shot code has minutes
  $FF, so checkfornewpen treats it as a delayed call: play goes on until the guilty team has the puck, then Stop4Pen.
  When the stoppage is over, InProgress gives the puck puckshootout ($1E) instead of puckfaceoff whenever bit 3 is set;
  puckshootout clears bits 2, 4, 5, 6, counts the attempt (+$360), sets shootoutclock ($D454) to $19 (unless a
  delayed penalty is flagged: gmpendel jumps to Stop4Pen first and skips that), sets bit 2 (penalty shot on), checks the
  saved goalie, then puckpenshot puts the puck at centre, the nets home, the shooter (object 0 or 6) at the puck and
  everyone else off. It ends (UpdatePenaltyShotEnd, every frame in pucknorm; bit 4 -> whistle $A and
  EndPenaltyShotPlay, which clears bits 2-6) when: the goalie has the puck; after the shooter has shot or passed (bit 5,
  passmodetimer $64), anyone takes the puck once it has gone loose (gmode2 bit 5), or 100 frames pass; shootoutclock
  reaches 0; the goalie's hold timer runs out (bit 4); a goal (which also clears bit 3). Losing the puck without shooting
  ends nothing unless the goalie gets it. Bit 3 is cleared only by EndPenaltyShotPlay and a goal, so a penalty shot
  stopped by any other whistle (net knocked off, puck over the glass) leaves it set and the next stoppage gives another
  penalty shot from centre ice (code reading, not seen). The user's bug (shot ends at once after the transition) is not
  explained yet: the only path to a zero clock found is the gmpendel branch, which cannot be taken there (the clock is
  stopped, so no new delayed call). The flags are outside fast.bin ($C2EA-$C3E8, $D406-$D454); recording them would let
  a recorded occurrence be traced.
- Goals while play is stopped (Genesis checkgoal .goal): outside a penalty shot a puck reaching the goal with the clock
  stopped (gmode bit 0) is ignored; with BA_PS_flags bit 2 on, that test is skipped and the goal counts if the puck is in
  the net the shooter attacks (pucky sign), then EndPenaltyShotPlay. puckshootout turns bit 2 on as it starts setting
  up the shot, a frame or so before puckpenshot blanks the screen and moves the puck to centre, so a puck still moving
  in that net after the award whistle scores then, after the stoppage countdown (the user's "goal after a hesitation",
  penalty shot cancelled). Collisions are checked only for objects that moved, so a puck lying still does not.
- Ghost puck in a penalty shot (Genesis wallcollb): a puck over the boards gets pfnc (no collision: checkcoll returns at
  once, so boards, posts and nets are skipped), sfslock and attribute bit 15; the out-of-play whistle (AddPenalty2 6)
  comes only while the clock runs. pfnc is cleared on the puck only by Endfaceoff (the faceoff drop), which a penalty
  shot never goes through, so a puck flipped out of play after the award whistle stays in no-collision mode through
  the shot: it is carried and shot normally (checkpuckcoll, the player and goalie touches, does not test the puck's
  pfnc) but then passes through the net and the boards; with the penalty shot's clock stopped no out-of-play whistle
  comes, and the shot ends 100 frames after the release (passmodetimer) or on the shot clock. The user saw it pass
  through the goalie too: the code would let the goalie block it, so it presumably missed his reach (unconfirmed).
- Penalty shots (SNES): penshot $1E9B (pending / under way: StartPenaltyShot sets it, EndPenaltyShot clears it),
  penshotlive $1E9D, PenShotActive $163A. SetupPenaltyShot puts the puck at centre and gives it straight to the shooter
  where he stands (the puck then sits on his stick); pstimer 1000 frames. EndPenaltyShot is called when: anyone takes
  the puck who did not have it (puckglue: also the shooter gathering a puck he lost), the loose puck moves back away
  from the goal for 48 frames (pucknorm pspuckback), pstimer runs out (Gameloop), the loose puck hits the boards
  (wallcoll, with a whistle) or leaves the rink (wallcollb), a goal, the period's end. A net knocked off is not among them,
  so penshot stays set and the next faceoff (puckfaceoff2: penshot -> Endfaceoff then SetupPenaltyShot) starts another
  penalty shot with the shooter wherever he lined up: for a net knocked off by the attacker, the dot outside the zone.
  That is the user's SNES bug (a penalty shot, the net knocked off, a new penalty shot from a side dot).
- Offensive / Defensive Awareness (both systems): used only as AI reaction timers. setplayer turns the working value v
  (0-30, bonuses included: OfA gets the power-play, home / away and third-period bonuses, DfA home / away) into frames,
  aioff / aidef = ((v / 2) XOR 15 + 15) / 2 = 15 (worst) to 7 (best) (SNES skaters' aidef = 22 - v on 0-15: 7-22). Each
  computer-controlled player's assignment reloads temp1 (record +$40) with it and re-decides where to go when it runs
  out (1 frame less with the sflags7 bit 6 crowd boost): Offensive for the puck carrier (asspuckc), the player nearest a
  loose puck (assnearest) and a defenceman when his team has the puck (assdefo); Defensive for every defending
  assignment (assdefd, asswingd, asscenterd) and, apparently by mistake, for wingers and centres when their team has the
  puck (asswingo, asscentero; SNES the same). The controlled skater skips all of it. Goalies: the CPU goalie
  re-aims every DfA / 4 frames (checkanim / assgoaliectrl), skates to a loose puck on a DfA timer (assgoalietopuck);
  SNES dopass also adds DfA / 2 + 1 frames to the goalie's timer at every pass. Checked: the +$40 reloads in BOS-PIT
  and capture6 equal the player's working +$6A / +$6B within the frames already counted (98%; mostly 6-12).
  What each tick decides (Genesis; the current job is record +$38 + the word at +$36: 1 assdefo, 2 assdefd, 3 asswingd,
  4 asswingo, 5 asscenterd, 6 asscentero, $10 asspuckc, $11 assnearest): every job checks at its tick whether
  possession changed and switches to the other side's job then, so awareness is the reaction to turnovers. asswingo
  also re-picks its spot by the puck's zone (predicted by puckvy / 64: a box per zone, randomised, re-picked only on a
  zone change or 1 tick in 128). assdefd re-reads, at its tick, the deepest opposing attacker (Y + Yvel / 16) and sets
  its depth 50 behind him (no deeper than 190-220), and its side (65 toward its side, or the middle with the puck on the
  other side), skating to that stored spot between ticks: so DfA is the defencemen's gap control. asswingd / asscenterd /
  assdefo compute their spot every frame from the puck and use the tick only for the possession check (assdefo also
  for the puck leaving the zone: a low-OfA defenceman retreats late). asspuckc (computer carrier) considers shooting
  (chk4shot) and passing (chk4pass) at each OfA tick. assnearest (the chaser of a loose puck AND of the opposing carrier,
  forecheck and backcheck) re-predicts the target and hands the chase to whichever teammate is now nearest the puck at
  each OfA tick, the timer halved while the opposing carrier is in the slot. Timers are 1 frame shorter while the shooter's
  goalie is pulled (OfA jobs) and while the crowd meter is at or above the arena record (sflags7 bit 6, both teams; the
  +2 Agility / +2 Speed that the same tests give come from sflags8 bit 1, which SetSflags8Bit1 always sets, so they are
  always on for everyone). Frames by rating (Genesis, hot / cold -3..+2): 0: 15-14, 1: 14-13, 2: 13-12, 3: 12-11, 4: 11-9,
  5: 9-8, 6: 8-7 (OfA also takes the PP / PK, home / away and third-period bonuses, DfA home / away). SNES: Offensive
  15-7, skater Defensive 22-7 frames; the hot / cold bug gives every cold rating the best value, 7. Recordings (four
  Genesis games): after a turnover a defenceman on offence switched to defence a mean 96 / 132 / 147 / 223 ms later at
  OfA values 9 / 10 / 11 / 12. Split by what happened (606 turnovers): not locked and switching directly, defencemen
  131 ms, wingers 128, centres 125 (countdown left about 80 ms, plus a frame or two of reading); locked in an animation
  (pfalock: every job returns at once while it is set, so nothing switches) 620-1,022 ms; given the chase first (job
  $11) 814-1,372 ms. Forwards are locked or chasing far more often (they just lost the puck), which is why their average
  looked unrelated to awareness.
- The SNES flip (doinput: the Y button, our pad's A, with the puck -> assinsert $14 assdumpin): the game takes the
  carrier's flip over: DumpInTarget picks by his SIDE OF CENTRE (x sign), not his facing: outside the attacking zone
  (+/-80, 180 toward the goal he attacks) on his own side, inside it (0, 215), a goalie (0, 105) moved by his facing; a
  computer carrier inside the zone shoots instead (CompShoot). He turns first until he faces within 45 degrees of
  straight up the ice; the spot then gets random +/-(20-25 + 2 x (15 - Pas)) across and +/-(20-70) along (the deeper
  targets 70), so Passing sets flip accuracy on the SNES. Recorded flips found 2026-10-30 (export_match.split_flips:
  they leave through the pass animation, so find_passes had them as passes; the puck's SPApflip spin frames, sprite
  $18C + 2-10 but not + 1 / + 5, plus a climb of 5 in 0.13 s pick them out): 18 in the 17 SNES games, 15 after a
  person's Y press (10 by goalies), 2 by the computer, 1 a rimmed pass behind the net (a boards bounce spins it too).
- Puck physics (Genesis): updateplayers each frame on the ice takes velocity >> 9 off the puck (and off a player with
  pfdoff; others >> 6): the puck keeps 0.889 of its speed a second, skaters 0.39; in the air (Zpos > 0) no friction at
  all; gravity 6 x 17 off Zvel a frame; on landing Zvel = -Zvel / 2 (half-height bounces, the puck-on-ice sound). Checked:
  loose pucks sliding flat kept a median 0.893 a second (314 stretches), in the air 1.000 (306). Boards (wallcoll): the
  speed into the boards is quartered and reversed, the speed along them loses 1/64 + 1/128; a hard hit adds a small
  random hop and a boards sound; any board touch clears the shot flag (a shot off the boards is never a shot on goal).
  Net (checkgoal): crossbar at height 13 (higher passes over), a puck crossing the line inside the mouth less one unit
  is a goal, exactly at the post or at crossbar height a deflection (counted as a shot on goal: ChkShotStat; the post
  sound; random velocity up to $1000 each way, away from the net); back and sides bounce like the boards; a puck
  carried into the carrier's own net is stripped (pfgoal on the puck, collflag undoes that frame's move) but NOT bounced:
  wallcoll's "moving into the surface" test reads a puck moving into the mouth as moving away (2026-10-19, frame by frame
  on the ANA-ATL shoulder-save goal, frames 1671-1676), so it slides on in; only entries from behind bounce.
- What each rating does (Genesis; every read of the working ratings, by routine):
  Weight (record $67, rating x 8): acceleration (playeracc: (64 - weight / 4 + Agl + 2) / 2, i.e. each Weight point
  costs as much as 2 Agility points), the check knockdown sum (CCStart, with the person overflow), momentum in
  collisions (checkcx: mass = weight + $8C). Agility ($68): acceleration and so turning (playeracc; goalies add Agl
  + 16 again), goalie reach (.cbg), resisting a poke trip with penalties off (Bcheck). Speed ($69): top speed (MaxSpeed
  table), the chaser's +6 when the opposing carrier is in the slot (assnearest). Offensive / Defensive Awareness: AI
  timers (above). Shot Power ($6C): shot speed ((ShP / 2 x energy + 20) x wind-up, + 1/16 for odd values), and the
  wind-up: below 20 it is cut off at animation step 8 instead of running to 16 while C is held (ShotMode), so weak
  shooters cannot take a full slapshot (recordings: under 20, top speed 20,746 in 67 shots; 20 or more, up to 29,216 in
  83); goalies: PkC in this slot, the hold-the-puck threshold. Shot Accuracy ($6D): the perfect-shot roll and scatter.
  Passing ($6E): pass speed (160 + 2 x Pas). Stickhandling ($71): steals both ways and catching passes (puckstick),
  the stumble instead of a fall at 24+ (FallDown). Checking ($75): the knockdown roll (CCStart), the poke trip with
  penalties off (Bcheck), the upend / flip fall at 20+ (FallDown), and computer checking: check4check rolls randomd0(40
  - Chk), doubled with penalties ON (so computer skaters check half as often then), <= 6 with an opponent within 30
  exactly where he faces -> burst 3 in 4, else hook / hold (always hook / hold with the carrier in the slot); the chaser
  (assnearest) rolls randomd0((40 - Chk) << d1) <= 2 to go straight at the carrier for 240 frames instead of containing
  (halfway between him and the net), d1 2 normally, 0 on his team's power play, 4 on the penalty kill, no switch for a
  defenceman within 20 of the puck; in the slot his Chk counts double for check4check. Endurance ($72): energy loss
  (only with line changes on). Pass / shoot bias (spodds $70, the roster's "Rgh", byte 6 low nibble; gets the
  third-period bonus twice): the computer carrier's choice: chk4shot shoots when randomd0((32 - spodds / 2) x 16, / 16
  within 100 of the net, x 2 per defender in the shooting lane) <= 7 (odd values) or 8; chk4pass considers a pass when
  randomd0(16 + spodds) <= 12. Aggression ($73, 0-15 after the wrap): penalties (checkagr, checkint); goalies: the reach-out
  glove save at 11+ (this slot is GL for goalies). Fighting / H/F: injury length for the hitter's victims.
- What each rating does (SNES; working ratings 0-15, arrays a word per object; the arrays, as renamed 2026-10-21: checking $1483,
  aggress $1443 (Aggression; GGSleft is its goalie alias), fighting $1463; before, aggress held Checking and GGSleft Aggression): Weight: acceleration (playeracc: 32 - Wgt + 1.5 x Agl, so a Weight
  point costs 2/3 of an Agility point), checks, collisions. Agility: acceleration, stopping (dostop), the goalie's skating
  to loose pucks; goalies: a person's goalie without the puck gets 2 x Agl + 8 more, a computer goalie (or one with the
  puck) only + 8 and loses his Agl again while a pass is in flight (passReceiverPlayerNum set): sluggish across the
  crease on passes. Speed: top speed, scaled by energy (0.5 + energy / 2; full with OptLine 2); a person's goalie in his
  crease (goalieflags bit 2 clear) at 3/4. No half acceleration for a person's puck carrier was found, and no chaser
  slot speed boost. Shot Power: shot speed ((ShP x energy + 20) x wind-up); no weak-shooter wind-up cut-off (ShotMode
  does not read it): anyone winds up to step 16. Shot Accuracy: as the Genesis (perfect roll, scatter). Passing: pass
  speed (144 + 4 x Pas) and the flip's scatter (assdumpin). Stickhandling: steals, catches, the stumble at 12+.
  Checking (aggress): knockdowns, the flip fall, and computer checking: check4check rolls randoma(20 - Chk), doubled with
  penalties on, TWICE, either < 4 -> look for a target (Chk 15: about 96% a frame with penalties off, 64% on; the hot /
  cold bug puts many players at 15); the chaser's attack roll uses 20 - Chk the same way. Endurance: energy. Pass /
  shoot bias (spodds): chk4shot / chk4pass. Aggression (GGSleft): penalties (checkagr, checkint, with the person
  overflow). Goalie save ratings (glove / stick, in the passacc / endurance / spodds / GGSleft slots): looked up in
  puckgoalie, then overwritten before use, so unused as on the Genesis. Fighting (fighting, once fightagg): never read.
- One-timers (Genesis): triggered by a C press (doinput) while the person still controls the passer of a targeted pass
  in flight (lastplayer = him, passplayer set; the receiver not a goalie, not a person's, not already one-timing), or by
  the pass's receiver himself with the puck loose; only with the puck on the attacking half (PuckOnAttackHalf); for
  computer teams asspassrec starts them itself (in the attacking zone, or 1 in 8 outside). assonetimer gives control to
  the receiver and starts the shot animation (forehand or backhand by the angle to the net); while the puck comes it
  works out the frames until it arrives (distance / speed / 17) and starts the downswing itself when that is no more
  than the frames left in the swing, so the swing is timed by the game; at full wind-up it holds 48 more frames
  (SPAcnt += $30) waiting. It is cancelled when anyone gains the puck or the puck is 60+ away and moving away; it fails
  when the downswing ends without the puck within 10 of the blade (puckstick: within 18 the swing jumps to the strike,
  within 10 it strikes: onetimershot -> doshot with power from $1F, auto-aim, goalie reach 12, the last two passers
  credited). Recordings: successful one-timers struck 0-870 ms after the C press (median ~210; pressing as the puck
  arrives strikes at once), failed ones ended 300-960 ms after it: press C no more than ~0.9 s before the pass arrives.
- Hooks, holds and pokes (Genesis): A starts SPAhook (or SPAHold right after contact with the opponent ahead), a 30-frame
  reach; an opponent caught within 45 degrees of where he faces (holdcheck) gets both players' velocities averaged (the
  carrier slows to the hooker's pace) and is locked flailing (SPAflail) 40 frames, the hooker in SPAhook2 / SPAHold2 36-40
  frames, then the hooking / holding roll (checkagr <= 6). The poke (B without the puck, SPAsweepchk) lasts 16 frames;
  stealing is not special to it: any opposing stick within reach of a carried puck rolls the puckstick steal (randomd0(36
  + carrier Stk / 2 - stick Stk / 2) <= 2, <= 4 in the slot, both scaled by energy; a steal knocks the puck loose in a
  random direction); body contact facing him trips him (Bcheck). Recordings (7 Genesis games): 107 hooks / holds caught an
  opponent, 86 of them without the puck; on the carrier (22) he kept it 4 times, the hooker's team got it 6, his own team
  4, loose or whistle 8. Pokes by people: 136 of 210 from more than 30 away (no effect); within 30 (74): tripped him 21,
  knocked it loose 22, took it 9, loose then his team kept it 8, nothing 14. The computer hardly pokes (1).
- SNES goalies (assgoalie): besides the save list (GoalieSaveList, chosen like the Genesis: high / low, near / far, pad
  stack while the puck is carried), the code has a poke (SPAgpoke, puck within 35 in front of the goal line, randomWord
  < $A00, then goaliedivewait 240) and a dive at the carrier (puck within 45, an attacker within 60, randomWord < $800,
  wait 360); which goalies use them is not clear: in four SNES games no computer goalie dived (all 6 dives by people).
  Genesis computer goalies dived 7 times, all at a loose puck within 45, as the code says.
- Computer positioning (Genesis; y toward the goal the team attacks, x: right wing +, left wing -, flipped with the
  direction). Offence, by the puck's zone (a spot picked at random in the box, kept until the zone changes or a 1 in 128
  frame re-pick; boxes as centre +/- half-range): wingers (asswingo; zone from the puck's y + Yvel / 64): puck in own zone
  (80 +/- 20, -70 +/- 10), neutral (100 +/- 20, 58 +/- 5), attacking zone (60 +/- 50, 230 +/- 20), behind the goal line
  (80 +/- 30, 250 +/- 20); centre (asscentero): own zone (0 +/- 60, -70 +/- 10), neutral (0 +/- 60, 60 +/- 10), attacking
  zone (0 +/- 40, 170 +/- 30), behind the goal line (0 +/- 80, 170 +/- 20); defencemen (assdefo, every frame): y 98 (just
  inside the blue line), x +/- 80 on their side, or following the puck's x when it is on their side (half way toward it
  when not). Defence: defencemen (assdefd, at DfA ticks): depth 50 behind the deepest attacker (y + Yvel / 16), no deeper
  than 190-220, x +/- 65 on their side or 0 with the puck on the other side; wingers (asswingd, every frame): x +/- 100
  on their side or the puck's x when it is on their side, y the puck's y while it is beyond 78 toward the other end
  (out of the zone if need be), 158 with it in their zone, the goal line with it behind;
  centre (asscenterd, every frame): x half the puck's, y the own high slot (-128) with the puck in the zone, else half
  way between the puck and it; the chaser (assnearest): straight at the carrier (attack, 240 frames) or half way between
  the predicted puck and a point 20 out from his own goal line (contain). All but the defending centre and wingers steer
  around the carrier (EvadePC).
- Skating checked against the recorded velocities (record +$28 / +$2A): top speed: each skater's 90th-percentile speed
  outside bursts and checks sits just under (20 + Spd' / 2) x 275 (Spd' = working Spd + 2, at most 30; + 137 for odd
  values): 6,628 at Spd 7 (cap 6,737) up to 9,162 at 26 (9,350), 61 skaters in three games; about 23 to 32 mph. Acceleration:
  speed gained per frame (one-frame steps by the frame counter, skating animations, 300-3000, friction v / 64 added back)
  against (64 - 2 x Wgt + Agl + 2) / 2 x 200 / 32: medians within 1-5% of it from 167 (term 27) to 236 (39), ~19,500
  samples in two games. So Agility is acceleration and a Weight point costs 2 Agility points, as the code says.
  SNES top speed: MaxSpeed ((20 + n) x 261)^2 with n = working Spd x (0.5 + energy / 2) (Xvel $0EC3, Yvel $0EE3, Spd
  legspd $1303): 90th-percentile speeds 6,919 at Spd 7 (cap 7,047) to 8,901 at 15 (9,135) in three SNES games; 32 of the
  61 skaters were at working Spd 15 (the hot / cold bug), so most of the ice skates at full speed.
- Skating (Genesis playeracc): top speed from MaxSpeed ((20 + n) x 275)^2 with n = working Spd / 2 (+1 always: the
  "crowd meter broken" +2); a person's puck carrier accelerates at half rate (not the computer's); a goalie with the puck
  at half speed. Top speeds in the recordings follow Spd only loosely (bursts add to them).
- Goalie AI: the CPU goalie stands on the line from the puck to his net, 18 out; he rethinks every DfA / 4 frames.
  Save moves (goaliesave, from checkanim when findpc's puckcross predicts the puck crossing his goal line within 24 of
  the middle in under 12 frames, or 34 for the outer test): side from the crossing point against his facing (flipped
  for mirrored goalies). High puck (puckz > 8 or puckvz > $800): ghighr / ghighl (shoulder) when the crossing is within
  16 of him, else gglover / gglovel (blocker / glove; gglovel2, the reach-out glove, with the angle off straight and his
  glove rating, the aggress slot, 11+). Low puck: within 8 frames, gstickr / gstickl (kick / butterfly) when within 16 of
  him, else gstick2r / gstick2l (stick save); further off, a pad stack (gstackr / gstackl, sliding at $1000 and 6 units
  toward the side, by his x and handedness) when someone still carries the puck and he is not facing sideways, else the
  kick / butterfly. Dives (gdive) only at a slow loose puck (|vx| + |vy| <= $1000) within 20 across and 30 out, never at
  a shot; a puck taken in a dive is whistled after 5 frames (temp5). Recordings earlier (115 saves): stick 62, high 14,
  pad stack 12, dive 5, glove 2, none 20.
- Stick steals (puckstick): a stick touching the carrier's puck steals it when randomd0(36 + carrier Stk / 2 - stealer
  Stk / 2, both scaled by energy) <= 2 (<= 4, and from farther, with the carrier in the slot).
- Crowd: CwdExciteLvl $B8A2 (fast.bin): +10 a shot, +20 big hits, +30 goals (less for the visitors), -1 a tick; the meter
  is sqrt(level x 4) + 65 dB. SNES CwdExciteLvl $19BE.
- Genesis injuries (2026-10-21, a question about an RL bot that draws many penalties): the injury roll (collide94,
  after the knockdown) needs a2 = the puck carrier, SPAfallback, facedir & 3 = 0 (facing straight up or down; the
  docs' old "1 in 4 chance" was this facing test), the clock running, then randomd0(160) <= impact. All 5 recorded
  injuries: carriers facing 4. Carriers face 0 / 4 about 40% of the time. CCStart only rolls a check's penalty (and
  knockdown) when the impact d4 >= $14, so soft hits are never called. A straight-line carrier taking head-on hits
  gets hurt (automatic roughing) and draws the check-penalty rolls far more often.
- Disassembly bug hunt (2026-10-21): Genesis CPgoalie pulls only at exactly 2 behind (bne); icing always on, armed by
  a2touchpuck, cancelled by PuckIChk when |puckx| <= $2C at the goal line (iflags $BF80 = ifcgl 0, ifdir 1, ifok 2;
  icingPlayer $BF81; checked 5/5 and 67/68 in the recordings); wallcollb: Z 19-29 out of play except Y >= $118 (top end
  bounces; glass break at x 13-15, Yvel >= $FA0); PenGoalStuff clears PenBuf only when the scored-on team has 6 on the
  ice; setInjuryType game injury for H/F 3, 5, 6, 7; the person goalie's C press computes a target (lead 160 + 16 x
  (clock & 7)) and six branchless cmpi, all dead: goaliesave overwrites d0 / d1 and never reads d2. SNES: no icing window; chk4shot cmp #$2711 dead (square, not circle), shoots under 5 s
  left. The converter's icing finder can take an over-the-glass whistle for an icing (capture6 P1 1:44); iflags would
  settle it. nhl94.com's bug list (35 items) has none of these.
- Genesis game options (2026-10-21): addresses from ram94.asm's rs list summed from varstart $B000 (it reproduces
  SortCords $B04A, CwdExciteLvl $B8A2, BA_PS_flags $C2F2, CurCrowdMeter $C30E): Optperlen $D050, OptGoalie $D052,
  OptPen $D056 (0 off, 2 on), OptLine $D058. Outside fast.bin's blocks, so read from full.bin (Capture.word falls back).
  Penalties were off in 2026-10-21_1121 / 1133 / 1137 / 1147 / 1156 BOS-NYI and 2026-10-19_0818 ANA-ATL, on in every
  other Genesis recording. analysis/cpu_check_study.py: computer check tries at 12% of openings off, 9% on.
- SNES puck physics (2026-10-21, analysis/puck_glide_study.py, SNES_MECHANICS 7.8): updateplayers runs the puck
  through the skaters' friction (.20,x = .21[timestep - 1]; gliding pflags bit 0 -> .22-1,x = .22[timestep - 1]); the
  puck glides: $FF a step at timestep 2, kept 0.881 a second measured (262 stretches; the Genesis 0.895, 227), air 1.000;
  gravity gravstep (96 a step), landing -vz / 2; wallcoll as the Genesis (v1n / 4, v1t - v1t/64 - v1t/128, pop-up when
  v1n / 4 < -$400).
- SNES upend (2026-10-21, analysis/snes_upend_study.py): FallDown in open ice: back if the direction to the hitter is
  within 1 of facedir ($1163), else forward, else SPAflip ($F6C0) when facedir & 3 = 0 and the hitter's checking ($1483)
  >= 10. 714 of 788 recorded falls right (hitter = nearest opponent skater; direction 0 points to +y, clockwise).
- Crowd record flag (2026-10-21, analysis/crowd_study.py): Genesis BA_PS_flags $C2F2, sflags7 $C2FC (bit 6 is the word's
  high byte: & $4000), CurCrowdMeter $C30E, CrowdRecord $C310 (checked against sqrt(level x 4) + 65). CrowdRecord was
  $50 in all 17 recorded games (no saved record), and the flag was on 73% of live play. SNES: no crowd effect at all.
- SNES checks of the above (2026-10-17, same tests on the SNES recordings): home / away and PP bonuses confirmed (ShA:
  home +1 / +2, away -1; arrays as listed under Hot / cold (SNES), Chk = aggress $1483); the third-period bonus confirmed
  with the same backwards test. Both systems set ratings only when players are put on the ice (faceoffs, changes), so
  the bonus follows the clock at the last faceoff: CHI-TOR's third period had no stoppage and kept it all period. Shot
  roll (doshot: cmp #$C9, randoma8(16 + shotacc) >= 15; scatter (speed / 8 - ShA + 16) x distance / 64) confirmed: 60%
  of 112 shots within 200 left on the aim point, none of 15 beyond; 63 of the 112 were by shooters at ShA 15 (the
  hot / cold bug). SNES shotdiradj auto-aims computer shooters only (playerpad), not one-timers. SNES goalie
  (checkpuckcoll_ccx): a frame-dependent area from GetFrameHot with a height window, then a fixed body box |dx|, |dy| <= 10
  at any height; no agility, person, one-timer or pad-stack change; a diving goalie lets pucks at height >= 5 through;
  the save ratings looked up in puckgoalie seem unused. Recordings: no goal passed within 12.6 of the goalie's centre
  (26 goals); saves median 12.9. SNES checks (checkcheck): impact >= 32 ($20), base 120 for everyone, roll against
  Chk (aggress); recordings: 327 lunges into contact, heavier checker 50% knocked down, lighter 39%, people 50%, CPU 39%.
- Genesis person goalie, checked: the four non-one-timer goals that passed 12-15 from the goalie all had the computer in
  net (agility 3-4: reach 13-14); with a person in net no such goal passed within 20.
- Faceoffs (Endfaceoff, both systems): no ratings. Each centre's state is how far his faceoff swing has got at the drop
  (assfaceoffpl: SPAnum / 4 + 1, +3 right-handed; fofdata2 $BDA8 home, +4 away) worth 0 / 8 / 16; Home wins when a roll
  of 0-32 (SNES 1-32) is at least 16 - home + away: equal timing 17 / 33 (SNES 17 / 32) for Home. Genesis checked (see
  Faceoffs, checked, below); SNES not.
- Passing (dopass / passtoa0, Genesis): Pas sets the pass's speed (160 + 2 x Pas), not its accuracy; the target is the
  nearest teammate within 45 degrees of the direction held (45 off counts as 256 farther), none = the puck goes that
  way (pass shots); the puck is sent exactly where the receiver will be if he keeps skating, lifted by the time to get
  there (puckvz up to 12 x 256). Catching (puckstick): a skater's stick takes a puck at height <= 5 slower than 13000 +
  350 x Stk (13000 flat while the shot flag stands), faster deflects at random. Recordings: 300 of 302 catches were
  within the receiver's limit; 13 of 32 bobbles were over it, 4 more in the air; the other 15 are unexplained (skaters'
  stick positions from HotList did not come out right: catches a median 14 from it).
- Energy: with line changes Off nothing drains it (skating drain and burst cost both skip on OptLine; Genesis OptLine 0
  On, 1 Off, 2 Auto = On with every use reading full energy). Checked: every skater at 4096 all game in the line-changes-
  off games of both systems (BOS-PIT, CGY-BOS, capture6, the four SNES games); capture3 and capture5 (line changes on)
  went down to 1134-1516. So in the leagues' setting fatigue and the Endurance rating do nothing.

- The 0-99 numbers on the game's screens (CalcAttrib / AttribAdjust; Genesis high ROM $FAA30..., SNES
  routines/stats/CalcAttrib.asm): Genesis n = 18 x nibble + that rating's own hot / cold byte (byte 15 - bit; never byte
  0, which plays), floor 0, 100+ -> 99, under 50 -> n / 2 + 25; bands 25-29 / 29-38 / 38-47 / 47-62 / 63-80 / 81-98 /
  99 (the NOSE editor's table agrees). Show-as-played ROMs (CDL ...) NOP the adda.l #$10,a4 at $FAA38 and read 0(a4,d0)
  with d0 = 0, so every rating shows byte 0: position in the band (middle 54 / 72 / 90) = the played hot / cold. SNES:
  18 x nibble + sign x floor(3|b| / 4), capped 100, same squash, with the hot / cold index mapped exactly as in play
  (checked: Agl 0 ... Agr 11), so a number below its band's middle = that rating maxed in play. The Genesis pre-game
  Matchups screen (ScoutingReport) re-rolls hot / cold. Overall weights (OvrPlayerWgtList, w / 2): Spd, OfA, StH 3;
  Agl, DfA, Chk, ShA 2; ShP, End, Pas 1; goalies Agl, DfA, PkC 4.5, the four save ratings 1. All in
  docs/GENESIS_MECHANICS.md / SNES_MECHANICS.md 2.5 and the player's guides (2026-10-17, which the user asked for).

## Three of the user's observations explained (2026-10-17)

- SNES: the same player never bobbles twice running. dopass sets a targeted pass's speed by distance (64 x 256 up to
  ~96 units, 2/3 x distance between, 80 x 256 from 120) plus randomd0s(16 - passacc) x 256; puckstick catches a loose
  puck slower than 10000 + 700 x Stk + 3000 (the +3000 applies to every stick; see the SNES puck-meets-skater note). The pass back after a bobble is
  usually short, so slow. (The SNES docs' "pass speed 144 + 4 x Passing" is only an untargeted pass.)
- Genesis: the top net's shoulder-save bobble. pucknorm pulls a held puck 1/4 a frame toward the holder + GetHot
  (HotList at ROM $A44C8, y negated); ghighr / ghighl hold points facing down (top goalie) (-10, +15) / (+10, +14), i.e.
  behind him toward his goal line (ready stance -4 to -6); facing up (+9, +14) / (-9, +14), in front. Goalie at
  242-250 -> puck at the net's front (261) -> checkgoal takes a carried puck off its carrier (nopuck 8) and bounces it;
  loose next frame, it can go in. Not found in the recordings (7 losses after shoulder saves, none at the net).
- SNES get-up glitch (press hook while down): doinput tests Y ($4000 -> holdplayer) before pfalock, and holdplayer
  refuses only during SPAburst, so SPAhook replaces the fall; the Genesis tests pflags bit 5 first. Confirmed: falls cut
  to 0.5-1.2 s by a Y press (TOR-CHI P2 3:05, CHI-TOR P2 2:36, CHI-CGY P3 0:11), next animation SPAhook $F864 /
  SPAhook2 $F3D8. snes ACTIONS "hook" = {"f864"} now; SAVE_MOVES from the disassembly's names (e246 stick,
  e2aa pad stack, sprawls e862 / e7d0, butterfly e73e), with "sprawl" / "butterfly" in the viewer.

## The user's five BOS-DAL games (2026-10-17)

Five Genesis games (Documents/NHL94 Viewer, 2026-10-17_2219 ... 2257, nhl94.bin, all with xG). What stood out:
- The double assist (2257 P1 4:25, Courtnall from Broten and Broten; the game's own scoring summary says [4, 4]): the
  game's bug. Each team keeps its last three touchers at stat block +$18 / $1A / $1C (in fast.bin). a2touchpuck shifts
  them only for a new player and clears the oldest when it equals the new one; onetimershot shifts unconditionally,
  and the goal code checks each assist only against the scorer. Broten struck two one-timers 0.25 s apart (the save's
  rebound back onto his blade: one-timers tried 1 -> 2), giving (Broten, Broten, Courtnall); Courtnall's one-timer
  goal then made it (Courtnall, Broten, Broten).
- Converter fixes from that game (every other recording unchanged): shooter_at looks first at the stat snapshots
  either side of the shots-on-goal rise (the wide window held Broten's two shots and the goal, so the second strike
  had no shooter); `latest` skips a shot when an opposing skater took the puck and the shooting team won it back
  before the goal (Courtnall's P1 3:52 shorthanded goal had gone to his pass shot 3 s earlier, which a Boston skater
  picked up; now his one-timer from Gagner's pass); scorer_touch prefers his shooting swing over the latest touch.
- An own goal by a skater (2246 P2 1:58): Neely took Courtnall's shot and carried it into his own net; the net's
  front took it off his stick (checkgoal, as in the shoulder-save bobble) and it crossed the line loose. The game
  credited Courtnall, unassisted (Dallas's last toucher), which the shot list keeps (an opposing skater who keeps the
  puck does not stop the credit).
- The viewer notes both (the user's wish; credits kept as the game gives them): `add_own_goals` gives a goal
  `ownGoal` (roster index) when the last player to have the puck within OWN_GOAL_MS 1 s was an opposing skater;
  `goalNotes` adds "own goal: X put it in his own net" and "the game credits X with both assists (a bug in the game,
  not the viewer)" to the banner and the scoring summary, an "own goal" tag, two Help entries. Over all recordings:
  seven own goals (Juneau and Suter in CGY-BOS, Taglianeti in BOS-PIT, Steve Smith in CHI-CGY (SNES), Ciccarelli in
  capture2_away, Robitaille in capture3_bos_la, Neely); in each Genesis one the defender held the puck 0.3-1.1 s and
  the scoring team's last toucher (+$18) never changed after, so the game's own record agrees.
- Two injuries in 2246 (Neely by Modano P1, Sweeney by Tinordi P3), each with the injury's roughing call (code $12,
  no roll), out for the period; a penalty-shot goal (2219, Oates, not a shot on goal, as the code says).

## SNES ratings screen confirmed; the computer goalie's cover (2026-10-17)

The user recorded 2026-10-17_1719_CHI-CGY (in Documents/NHL94 Viewer; NHL94_Classic, the user Calgary, Away, against
the computer) and took 16 Edit Lines screenshots (RetroArch screenshots folder, NHL94_Classic-261017-1721xx.png; 256 x
224, read after a 4x nearest-neighbour enlargement) of Calgary's nine forwards, every column. All 99 rating numbers
equal 18 x nibble + sign x floor(3|b| / 4) (b = HotColdTable $1A12 + (place + 26) x 12 + rating index), squashed under
50, and the weights 140 + 8 x nibble. In play (working arrays $12E3 ... $1483 for on-ice objects, 3,450 samples per
rating): every value as predicted; below the band's middle maxed 46 / 46, above 0 / 31, at the middle 5 / 22.
The user saw the computer goalie "cover the puck" (never with a person in net): SPAgcover ($E66C), assgoalie: with the
puck held a while, on a RandomWord >= $C000, an opposing skater with puckdist < $14 makes him cover for 90 frames
(pf2aip $5A); < $23 waits; none within $23: chk4pass. In the recording: puck at P3 0:11, $E66C 0:09-0:05.

## Post, body, goal (2026-10-23)

Sweeney's 5-0 goal in 2026-10-23_1117_BOS-LA (P1 0:29) went post, his own body, in: the post sent the puck back out at
height 12, `puckbody` bounced it off him toward the net at 3 mph (the bounce is his offset from the puck, not a
reflection: GENESIS_MECHANICS 13.5) and it crept over the line. The converter had named that touch a one-timer
(`scorer_touch` took any touch in a shooting animation for one); it now needs a swing begun without the puck, so the
follow-through of his own shot is a deflection. All recordings re-converted.

## How league players score against people (the user, 2026-10-23)

The usual ways, in the user's words condensed. SNES: (1) straight at the goalie, fake one way and shoot the other at
close range; (2) the one-timer; (3) across the goal just in front of the crease, a soft wrist shot into the open far
side before the goalie (or the person taking him and sliding him across) gets there; (4) expecting the person to slide
the goalie across: hesitate or turn slightly back toward your own end, then a light shot at the near post (a goal, or a
post, if he did slide); (5) on a diagonal toward the net the goalie sometimes starts for the far post, leaving a small
gap at the near post; (6) now and then a slapshot. Genesis: 1, 2, 3, 4 and 6 are the common ones against people, and
slapshots to the far post (strong, accurate shooters) work more often than on the SNES; and (7) the EA Special (the
flipped wrist shot from the side that the goalie bobbles, then the follow-up into the open side: "Shot context" below,
tagged by the converter as `flip` / `afterFlip` and the goal kind "EA Special"). The scoring map and the
one-timer study cover (2) and (6) against a computer goalie at rest; (1), (3), (4), (5) and (7) are moving shooters or rebounds and, for
(3) and (4), a person moving the goalie: not studied in the game yet.

**Near and far post** (the user, 2026-10-24): by the shooter's hand. Right-handed: the goalie's left is the far post,
his right the near post; left-handed: the goalie's right is far, his left near (the far post is on the shooter's
forehand side). On the SNES slapshot goals are rarer and usually near post.

**Examples in the 2026-10-23 BOS-LA games** (the user named them; each checked against the recording):
- **Straight-on deke** (1107 LA-BOS, Neely 1-0, P1 3:30; right-handed): skating straight in with the puck on his right,
  it crossed to his left about half a second before the release and went in on that side (xG 0.70). Also 1126 LA-BOS
  Neely 1-0, a standard deke.
- **A computer teammate in the goalie's way** (1107, Neely's 7-1 slapshot, P3 4:09): Juneau stayed 16 from the LA
  goalie (bodies in contact) from the release to the goal, the goalie moved 2 across, and the puck went past his other
  side; Juneau never touched it. Not something to do on purpose; notable when it happens.
- **The floater** (1117 BOS-LA, Juneau 3-0 P1 2:29 and Sweeney 4-0 P1 2:18, both left-handed): skating up and across
  from his left to his right (or straight up a little wide of the post) to finish a little wide of the post, the
  puck turned from his right side to his left at the end, a soft wrist shot (12,700-15,500) into the opposite post.
  The user: other league players do this better than the user.
- **Slapshot from the middle, bumped** (1117, Neely 7-0, P2 2:20): Gretzky in contact (17) for the last third of a
  second of the wind-up; Neely pushed about 15 to his right, which moved the shot's line.
- **The near-post deke** (1117, Neely 9-0, P3 2:29): skating in, drifting a little toward the middle to be level with
  the near post as he reaches the goalie, then a quick turn moving the puck away from the middle and a quick wrist shot
  point-blank. xG gave it 0.01: the model misses this deke.
- **Far-post slapshots** (1126 LA-BOS, Neely 4-1 P2 2:54, 6-3 P3 4:49, 7-4 P3 0:39): each skating from his left to
  his right with the puck on his forehand, in at his right (the goalie's left: far). 7-4 from out wide (x 50 from the
  middle, 178 up the ice; usually it starts nearer the wing), the goalie 17 over toward the near post; the user was
  surprised 4-1 went in. LA's 4-3 (Sandstrom, left-handed): skating to his left, in at the far post (the goalie's
  right), a person in goal moved him the wrong way.

## RetroArch videos as a source (pilot, 2026-10-23)

The user keeps RetroArch .mkv captures of league games (51 GB, mostly Genesis; H.264 from x264, lossy; pauses and
intermissions included). Pilot on nhl94-261023-110709.mkv (the three BOS-LA games of 2026-10-23, also recorded by the
helper), game 1 (`analysis/video/`: video_lines.py, video_pilot.py; PyAV and numpy installed for it):
- **The picture:** the game draws 256 x 224 (H32) and the video stretches it to 320 x 224, 60 frames a second. A game
  position (x, y) is at pixel (1.25 (x - Hpos + 126.5), Vpos - y + 111), Hpos / Vpos the camera words BD1C / BD18
  (updatescroll: Hscroll = -64 - Hpos), at the skates (the sprite's bottom is about 6 pixels lower).
- **Line-up:** video frame = the game's frame counter (B03E) + an offset found stretch by stretch from where the blue
  lines (+-86) are drawn; the offset grows at each pause and intermission (the video keeps running, the counter stops)
  and the counter is reset to just below 0 at each period's start. 54 stretches of 600 samples, median match 0.81, the
  offset drifting about a frame a stretch.
- **The rink** rebuilt from the video (a median of 400 aligned frames with the camera moving) is clean.
- **Players:** every on-screen player shows in the foreground (pixels unlike every rink pixel within one pixel: the
  stretch draws edges differently at each scroll position), but only 53% of player-moments are on screen at all (the
  camera shows part of the rink); of those, 73% are a blob of their own once thin leftovers are trimmed, 27% merged
  with others; the blob bottom puts a player within 5 pixels of his spot only 38% of the time.
- **The puck** (a small dark blob) was found within 6 pixels in 15% of the frames it was on screen.
- **Not tested:** the camera from the video alone (an archive game has no recording): vertical from the lines,
  horizontal not yet. Conclusion so far: a video gives the players on screen, roughly, and little of the puck; the
  person-play measures need everyone and the puck, so Helper recordings stay the source; videos are for watching.
- **What a video can give for many games (the user: what goes with winning):** the HUD read by a learned font
  (`video_hud.py`; digits and letters kept apart, the game draws 0 and O alike): period, clock, score and both teams
  97% of frames right on all three games; the camera up and down the ice from the video alone (`video_camera.py`:
  the lines' rows, and a lone blue line told apart by the frame's row profile of red and blue against the rink's) 94-98%
  within 10 pixels of the recorded camera; the play's zone from the camera agrees with the puck's 83-87%.
  `video_game.py` puts them together: the games in a video (teams and final score right for all three), each team's
  attacking-zone time (video 132 / 212, 233 / 100, 165 / 190 s against the puck's 125 / 210, 221 / 107, 136 / 198), zone
  entries (with hysteresis; 22 / 26, 27 / 19, 22 / 23 against 29 / 33, 26 / 19, 23 / 25) and rush goals (all equal).
  Every third frame gives the same: 200 s for the 29-minute video in gentle mode. `video_archive.py` runs a folder in
  chunks (work files, the font and the rink picture in `%USERPROFILE%\NHL94_video`). The user's archive: 66 Genesis
  videos (30.5 h), 48 SNES (256 wide, 15.1 h, not read yet), one unreadable.
- **The archive read (2026-10-24, gentle, about 4 hours):** all 66 Genesis videos, 203 games found. The learned font
  only knew BOS and LA's letters; every letter is drawn identically, so the score box's cells thresholded fall into 26
  exact pictures, labelled by eye (`video_teams.py`, table in the work folder's letters.json): 20 teams named (BOS, LA,
  CGY, DET, MTL, WPG, DAL, PIT, PHI, BUF, CHI, NYI, VAN, HFD, QUE, NYR and league-ROM teams HEL, LVW, NIU, MNS).
- **What goes with winning** (`video_wins.py`, 182 whole games: 7-14 minutes of video, not tied): the team with more
  attacking-zone time won 79% (zone share 55 / 45; correlation with the goal difference +0.71), more entries 70%
  (+0.51); 38 winners had less zone time but finished better. 84% of the timed goals came within 6.5 s of the play
  entering the zone (the rule counts any re-entry as a rush, so this is an upper bound on rush goals). Scoring first
  won 73%, leading after 1 period 80%, after 2 periods 91%; down 1 after two, 13 of 54 came back; down 2 or more, 2 of
  107. Home won 55%. Goals by period 414 / 482 / 523. Zone time partly follows the score (a trailing team presses),
  so it is not all cause.

## SNES get-up glitch apart from hooks (2026-10-25)

The user's opponent in the 4-game TOR-NYI set (2026-10-25_2121 ... _2153) said most of the 40 "hooks" the viewer
showed were Y pressed to get up after being knocked down (the get-up glitch, SNES_MECHANICS 7.3). Checked: 30 of the
40 began the sample right after a fall. Over the 15 SNES games in Documents\NHL94 Viewer, 81 hooks by a controlled skater:
56 began exactly one sample after a fall or upend, 1 began 8+ samples after one, 24 had none in the 40 samples before,
so the rule is clean. `find_habits` (export_match.py) now counts a hook starting the sample after a fall or upend
(the system's HIT_OUTCOMES animations; a stumble is not a fall) as `getUps`, SNES only, and leaves it out of `hooks`;
hook takeaways unchanged. Viewer: a "Get-ups (hook glitch)" row under Controller (SNES), with help; season page: a
Get-ups/GP column when any game has one, HEAD_HELP for it and Hooks/GP (both systems); season.py VERSION
25. All SNES recordings with a match file re-converted in both game folders: only `habits` changed.

## A scripted bot (Genesis, 2026-10-31)

The user asked for an automated player that scores the ways they taught. `analysis/scoring_map/bot.py` reads the
game's memory each frame (the Helper's addresses: skaters, puck, carrier, controlled skater, the goalie's spot) and
returns the buttons to hold; `bot_run.py` plays whole games in the harness (the retail ROM, `bot_states.py`'s start:
Regular Season, the bot as Montreal at home on pad 1 against Los Angeles and the computer, 5-minute periods, penalties
and line changes off, manual goalies; about 30 s a game in gentle mode); `bot_report.py` sums a run, `bot_gif.py`
makes GIFs of any game's plays (a game replays exactly from its seed), `bot_deke_check.py` plays the standing deke
set-up with the bot's inputs. Run notes: the break between periods is a menu with play flagged live (FFF7 = 0) that
waits for START; a faceoff waits about 300 frames with the puck held up (z -256); with manual goalies the pad drives
our goalie when he has the puck (skated past the red line, a whistle), so the bot passes it out.

The plays: the deke (deke_run's best set-ups), a wrist shot in close at the half of the net away from the goalie, the
Down slapshot, and from version 2 the one-timer (a teammate open in the slot: B toward him, C while the puck
travels). Defence is simple (chase from the goal side, burst-check, poke within 26, B to switch), the goalie the
computer's. 20 games a version, the same seeds:

| Version | Record | Goals a game | Shots on goal | Deke | One-timer | Close wrist | Slapshot |
|---|---|---|---|---|---|---|---|
| 1: deke, wrist, slapshot | 18-2 | 3.60 - 1.10 | 26.2 - 10.8 | 42 / 258 (16%) | - | 23 / 295 (8%) | 7 / 521 (1%) |
| 2: + one-timer, deke only on a clear line | 17-3 | 3.00 - 0.90 | 25.4 - 10.9 | 9 / 60 (15%) | 14 / 97 (14%) | 28 / 306 (9%) | 9 / 621 (1%) |
| 3: + one-timer, every deke | 18-2 | 3.40 - 1.05 | 26.0 - 11.8 | 38 / 260 (15%) | 9 / 84 (11%) | 18 / 308 (6%) | 3 / 398 (1%) |
| 4: 3 with the deke's entry steered | 20-0 | 4.65 - 1.05 | 21.8 - 11.7 | 50 / 205 (24%) | 11 / 153 (7%) | 27 / 301 (9%) | 3 / 185 (2%) |
| 5: 4, C pressed as the pass arrives, receiver close in | 20-0 | 4.95 - 0.70 | 21.6 - 10.0 | 53 / 198 (27%) | 7 / 46 (15%) | 31 / 354 (9%) | 5 / 207 (2%) |
| 6: 5 with the deke re-timed (everyone on the ice) | **20-0** | **5.50** - 0.95 | 22.3 - 10.4 | 76 / 237 (**32%**) | 4 / 36 (11%) | 25 / 300 (8%) | 3 / 217 (1%) |

(Goals per shot: a goal within 120 frames of the play's shot, per shot the bot took. **The one-timer column of
versions 2-4 counts passes, not one-timers** (the user, from the GIF: the "one-timer goal" was a pass that went in).
From version 5 a one-timer is a teammate's shooting swing (animation $07FC / $092E) begun without the puck that
strikes it (within 25, moving 1.2+ a frame); in versions 2-4 no pass ever got one: C went in as the pass left, and the
receiver's swing was over before the puck came (the game times it only from about 0.9 s out, GENESIS_GUIDE 7).
Version 5 presses C when the puck is 14 frames from him: 46 swings struck in 20 games, from 6.9 passes a game; the
passes for one that went in themselves or off someone, 3 and 2 goals.)

- **Why the deke scored 16% in play against 82-96% standing: the skater's speed coming in, not the defenders.** At
  the swing, with an opponent within 40 it went in 6 of 29, with open ice 0 of 12 (3 games). `bot_deke_check.py`, the
  standing set-up with the bot's own inputs in the retail ROM, everyone else away: entering at 0.5 across / 2.1 up the
  ice (the runs' set-up) 27 of 32; 1.2 / 1.7 (diagonal, as the bot arrived) 11 of 32; 0.0 / 2.1 (straight up) 6 of 32.
  With the puck the skater turns slowly (0.5 across at the gate, 0.77 at the swing holding up and right), so the
  move needs that path. Version 4 lines up on a lane 55 to the left by the red line, builds the drift to it, starts
  the deke only when entering the gate at 0.2-0.9 across: the deke 24% a shot and the bot's goals up a third. Still
  far below standing: the timing is the standing runs', tuned to one speed, and defenders close in.
- **The deke runs' timings were found with every other skater off the ice, and that changes the right-hander's
  turn.** `bot_deke_check.py`, 48 tries a hand at the runs' entry: others taken off (and the shooter after his shot,
  as the runs did) left-handers 38, right-handers 48; everyone on the ice 40 and **4**. Frame by frame the two are the
  same until the swing; then with the others away his facing turns to up-left and the puck crosses, with them on the
  ice he keeps facing up, the puck stays in front and the goalie holds it. Taking only the shooter off after the shot
  doesn't restore it, so it's the other skaters' presence, not his follow-through (why isn't known: they were far
  from the play). Re-timed with everyone on (24 tries each, swing at 60): right-handers C 16 frames on 23 of 24 (13: 1,
  19: 9; swing at 72 or 85 worse), left-handers 13 frames 23 of 24 (10: 20, 16: 21, 19: 13). Version 6 uses these:
  the deke 32% a shot in games, the bot 5.5 goals a game. Caveat added to SCORING_GENESIS_DEKES, GENESIS_SHOOTING
  and the guide.
- Slapshots score 1-2% in play, as the maps say for a set goalie; real one-timers 11-15%, below the maps' (the bot
  waits for a teammate to be open close in, and passes from wherever it is).
- Still 32% for the deke against 96% re-timed in the check: pucks lost on the way in (drive 72, swing 40 in 20 games)
  and entries off the path. Next: the EA Special from the faceoff dot, one-timer set-ups (carry low on one side, pass
  across), then defence; then the RetroArch link (a virtual pad).
- **What separates the dekes that score (version 6, 17 games logged, 232 swings: 63 goals, 136 misses, 33 lost in
  the swing).** Space and speed at the swing: with an opponent within 25 of him 26 goals in 135 swings (21 lost), 25-40
  away 26 in 70, 40+ away 11 in 27. Swings that missed came in slower up the ice (1.48 a frame against the goals'
  1.71); across speed and spot barely differed (0.65 against 0.71 across; 0.6-0.8 across scored 50 of 160, below
  0.4 2 of 23). Pucks lost in the deke's drive (64) spread from the gate to the swing; but most of the bot's lost
  pucks (415) are in the plain carry, half of them in its own half. Not yet acted on (ideas: take the wrist shot or
  pass when a defender is within 25 at the swing).
- **The EA Special (versions 7-8, work in progress).** `bot.EA`: the EA runs' best set-ups (BEST17), a right-hander
  from his left, a left-hander mirrored: the top net released 23 ft out and 28 ft to the side skating in at 45
  degrees, the bottom net 17 ft out, 29 ft to the side, at the middle of the goal line; 1.7 a frame (coasting every
  other frame above 1.8), the first shot aimed across, then at the loose puck and at once a wrist shot at the near
  post. `bot_ea_check.py`, started on the top net's line 25 frames out at 1.7 (16 tries a hand, Shot Power 14 / 20):
  others off the ice 13 + 12 of 32 / 8 + 11; everyone on 7 + 8 / 3 + 8, every goal the follow-up. With everyone on,
  the follow-up claimed the puck 5-10 frames later; small changes swing the rates by 5 of 16 (one try at holding the
  speed tighter: free 11 + 8, parked 6 + 12), so 16 tries a hand is too few to tune on. In games the bot seldom got
  onto the line: version 7 pursued a point on it from wherever he was and came in from the middle, off the line
  (about 5 EA Specials a game, the close-in wrist shot instead); version 8 aims farther back along the line the
  farther off it he is, so he swings out to the wing, and reaches the release spot, but about 15 units (5 ft) inside
  the line and scored 0 of 12 from the neutral zone in the check. Next: bring him onto the line from farther out (the
  release spot matters most: SCORING_GENESIS_EA "A person's slop"), then games. The default stays version 6.
- **Version 9: the slowed left-hander's bail-out (the default since 2026-10-31).** In version 6's 20 logged games
  every swing under 1.3 a frame up the ice had a defender within 15-22 of him, who had slowed him from about 2.0; such
  left-handers scored 1 in 43 (right-handers 5 in 18). Version 9 has a left-hander slowed under 1.3 with an opponent
  within 25 at the swing pass to an open teammate close in, else take the wrist shot away from the goalie: 38 bail-outs,
  6 goals. 20 games: 20-0, **6.15 goals a game to 0.70** (version 6: 5.50 - 0.95), the deke **43% a shot** (32%).
  Version 6 run again with the log on gave the same games, so the logging changes nothing.
- **Version 8's EA Special, its approach redone, in games: no better than the deke.** A carrier gains speed at half
  rate, so from 2.0 straight up the turn onto a 45 degree line takes about 40 frames. A d-pad tapped every other frame
  (version 7's way of skating a little below full speed) doesn't turn him at all, and holding Down-Right to slow down
  brakes. Version 8 skates up the wing 110 to his side, and from 80 (left-handers) or 105 (right-handers) short of the
  release spot presses the direction that moves his velocity toward 1.7 along the line, never back down the ice
  (`bot.EA_TUNE`). `bot_ea_check.py` "wing", from the neutral zone up the wing (16 tries a hand, Shot Power 14): 29
  of 32 with the others off the ice, 23 of 32 with everyone on; from four starting spots, everyone on, 34 of 64. Getting him
  onto the line exactly (a stronger correction) didn't raise it at 8 tries a hand. In 20 games: 20-0, 5.50 goals a game to 0.90,
  9.1 EA Specials a game, 32 goals from 182 (18% a try: the first shot 3 goals, the follow-up claimed 56 times and 29 goals,
  52% when claimed), against version 9's deke at 43% a shot. Off the line the bot fell back on close-in wrist shots (30.7
  a game). The bottom net's right-hander seldom got there (7 of 181 tries): the turn was tuned at the top net only.
