# NHL '94 match viewer: study notes

The working notes of the studies: the game mechanics read from the disassemblies, the scoring map's runs, and what the user's games showed. Moved out of [PROJECT_NOTES.md](PROJECT_NOTES.md) on 2026-10-26. The findings themselves, in order, are in [GENESIS_MECHANICS.md](GENESIS_MECHANICS.md), [SNES_MECHANICS.md](SNES_MECHANICS.md), their *_SHOOTING.md parts and the SCORING_*.md pages.

Durations: game seconds (1 game second = 24 frames = 0.4 s of real time) for anything a second or longer, from
2026-11-06; shorter timings, frames, milliseconds and constants named _MS are real time. Entries before that date may
still give real seconds where not converted.

## Contents

In the order written (newest last).

**Studies, models and the recordings:** [Passing study (2026-10-18)](#passing-study-2026-10-18); [B without the puck: poke or switch (2026-10-19)](#b-without-the-puck-poke-or-switch-2026-10-19); [One-timers struck at the stick's reach (2026-10-21)](#one-timers-struck-at-the-sticks-reach-2026-10-21); [Scoring map: shots played in the real game (2026-10-22)](#scoring-map-shots-played-in-the-real-game-2026-10-22); [Game mechanics from the disassemblies (2026-10-17)](#game-mechanics-from-the-disassemblies-2026-10-17); [Three of the user's observations explained (2026-10-17)](#three-of-the-users-observations-explained-2026-10-17); [The user's five BOS-DAL games (2026-10-17)](#the-users-five-bos-dal-games-2026-10-17); [SNES ratings screen confirmed; the computer goalie's cover (2026-10-17)](#snes-ratings-screen-confirmed-the-computer-goalies-cover-2026-10-17); [Post, body, goal (2026-10-23)](#post-body-goal-2026-10-23); [How league players score against people (the user, 2026-10-23)](#how-league-players-score-against-people-the-user-2026-10-23); [RetroArch videos as a source (pilot, 2026-10-23)](#retroarch-videos-as-a-source-pilot-2026-10-23); [SNES get-up glitch apart from hooks (2026-10-25)](#snes-get-up-glitch-apart-from-hooks-2026-10-25); [A scripted bot (Genesis, 2026-10-31)](#a-scripted-bot-genesis-2026-10-31); [What check attempts lead to (both systems, 2026-11-03)](#what-check-attempts-lead-to-both-systems-2026-11-03); [Keeping the other team out of the slot (Genesis, 2026-11-01)](#keeping-the-other-team-out-of-the-slot-genesis-2026-11-01); [Passing out of a check (Genesis, 2026-11-06 / 07)](#passing-out-of-a-check-genesis-2026-11-06--07); [The SNES second period in full play (2026-11-07)](#the-snes-second-period-in-full-play-2026-11-07); [The scoring maps against a goalie as in games (both systems, 2026-11-07)](#the-scoring-maps-against-a-goalie-as-in-games-both-systems-2026-11-07); [A "count stick deflections" option, tested (Genesis, 2026-11-08)](#a-count-stick-deflections-option-tested-genesis-2026-11-08); [How often the fixed bugs happen in the recorded games (2026-11-08)](#how-often-the-fixed-bugs-happen-in-the-recorded-games-2026-11-08); [Momentum in the recorded games (2026-11-08, a community member's question)](#momentum-in-the-recorded-games-2026-11-08-a-community-members-question); [Game variables: phase 1 (2026-11-08; docs/GAME_VARIABLES_PLAN.md)](#game-variables-phase-1-2026-11-08-docsgame_variables_planmd); [The xG models' goalie spread refitted (2026-11-08)](#the-xg-models-goalie-spread-refitted-2026-11-08); [The SNES lines as loaded (LoadTeamLines; 2026-11-09)](#the-snes-lines-as-loaded-loadteamlines-2026-11-09); [SNES xG for SA-1 games: chunk 1, what it takes (2026-11-09)](#snes-xg-for-sa-1-games-chunk-1-what-it-takes-2026-11-09).

**Checks of ROM edits (NOSE4Web, McMarkis and forum hacks):** [NOSE4Web's rocket pass fix, played in the game (Genesis, 2026-11-07)](#nose4webs-rocket-pass-fix-played-in-the-game-genesis-2026-11-07); [NOSE4Web's runaway-speed fix, played in the game (Genesis, 2026-11-08)](#nose4webs-runaway-speed-fix-played-in-the-game-genesis-2026-11-08); [NOSE4Web's penalty-shot, goalie-pull, Y-button, extra-attacker and blind-ring fixes, played in the game (2026-11-08)](#nose4webs-penalty-shot-goalie-pull-y-button-extra-attacker-and-blind-ring-fixes-played-in-the-game-2026-11-08); [Code readings for NOSE4Web's next fixes (2026-11-08)](#code-readings-for-nose4webs-next-fixes-2026-11-08); [NOSE4Web's sniping, comeback, awareness and crowd fixes, played in the game (2026-11-08)](#nose4webs-sniping-comeback-awareness-and-crowd-fixes-played-in-the-game-2026-11-08); [One check for NOSE4Web's builds (2026-11-08)](#one-check-for-nose4webs-builds-2026-11-08); [The Genesis-only fixes: does the SNES have the bug? (2026-11-08, for NOSE4Web)](#the-genesis-only-fixes-does-the-snes-have-the-bug-2026-11-08-for-nose4web); [NOSE4Web's player photo and score logo editing, seen in the game (2026-11-08)](#nose4webs-player-photo-and-score-logo-editing-seen-in-the-game-2026-11-08); [McMarkis's score-box logos on the original SNES game: what retail leaves free (2026-11-08, for NOSE4Web)](#mcmarkiss-score-box-logos-on-the-original-snes-game-what-retail-leaves-free-2026-11-08-for-nose4web); [NOSE4Web's retail score-box logos, checked in the game (2026-11-08)](#nose4webs-retail-score-box-logos-checked-in-the-game-2026-11-08); [$A130F1 in Genesis Plus GX (2026-11-08, for NOSE4Web)](#a130f1-in-genesis-plus-gx-2026-11-08-for-nose4web); [The SNES big logos' overlapping pieces: which is in front (2026-11-08, for NOSE4Web)](#the-snes-big-logos-overlapping-pieces-which-is-in-front-2026-11-08-for-nose4web); [NOSE4Web's Classic import into the 32-team SA-1 build (2026-11-08)](#nose4webs-classic-import-into-the-32-team-sa-1-build-2026-11-08); [Genesis score-box logos: what the original game leaves free (2026-11-08, for NOSE4Web)](#genesis-score-box-logos-what-the-original-game-leaves-free-2026-11-08-for-nose4web); [NOSE4Web's Genesis score-box logos, checked in the game (2026-11-08)](#nose4webs-genesis-score-box-logos-checked-in-the-game-2026-11-08); [Injuries and NHLPA '93's blood (2026-11-08, for NOSE4Web)](#injuries-and-nhlpa-93s-blood-2026-11-08-for-nose4web); [NOSE4Web's head blood builds, checked (2026-11-08)](#nose4webs-head-blood-builds-checked-2026-11-08); [McMarkis's 60 frames a second: the computer against itself (2026-11-08, for NOSE4Web)](#mcmarkiss-60-frames-a-second-the-computer-against-itself-2026-11-08-for-nose4web); [NOSE4Web's SNES team-block colours, checked (2026-11-08)](#nose4webs-snes-team-block-colours-checked-2026-11-08); [NOSE4Web's SNES photo import freeing replaced photos, checked (2026-11-08)](#nose4webs-snes-photo-import-freeing-replaced-photos-checked-2026-11-08); [Six Genesis bugs looked for on the SNES (2026-11-08, for NOSE4Web)](#six-genesis-bugs-looked-for-on-the-snes-2026-11-08-for-nose4web); [NOSE4Web's SNES Import team with logos, checked (2026-11-08)](#nose4webs-snes-import-team-with-logos-checked-2026-11-08); [SNES "No interference penalties" in every period (2026-11-09, for NOSE4Web)](#snes-no-interference-penalties-in-every-period-2026-11-09-for-nose4web); [The same skater twice on one line (2026-11-09, for NOSE4Web)](#the-same-skater-twice-on-one-line-2026-11-09-for-nose4web); [NOSE4Web's NHL94SNESVault hacks (2026-11-09, NOSE4Web 0100df7)](#nose4webs-nhl94snesvault-hacks-2026-11-09-nose4web-0100df7); [The Genesis one-timer assist bug (2026-11-09, for NOSE4Web)](#the-genesis-one-timer-assist-bug-2026-11-09-for-nose4web); [The Genesis line editor's cursor (2026-11-09, for NOSE4Web)](#the-genesis-line-editors-cursor-2026-11-09-for-nose4web); [Edit Lines on the 1-on-1 ROM (2026-11-09, for NOSE4Web's "Edit Lines for fewer skaters")](#edit-lines-on-the-1-on-1-rom-2026-11-09-for-nose4webs-edit-lines-for-fewer-skaters); [NOSE4Web 6075749 and aaf3864: Edit Lines for fewer skaters rebuilt, and the "looks" build (2026-11-09)](#nose4web-6075749-and-aaf3864-edit-lines-for-fewer-skaters-rebuilt-and-the-looks-build-2026-11-09); [Organ songs moved, played; SNES credits and songs; the song format (2026-11-09, for NOSE4Web 5d1ec5e)](#organ-songs-moved-played-snes-credits-and-songs-the-song-format-2026-11-09-for-nose4web-5d1ec5e); [Assists that disappear (2026-11-09, the user: SNES goals left unassisted after passes, perhaps one-timers)](#assists-that-disappear-2026-11-09-the-user-snes-goals-left-unassisted-after-passes-perhaps-one-timers); [NOSE4Web's splash screen picture, played (2026-11-09, NOSE4Web fdacede)](#nose4webs-splash-screen-picture-played-2026-11-09-nose4web-fdacede); [Genesis forum hacks, from the code (2026-11-09, for NOSE4Web; not played)](#genesis-forum-hacks-from-the-code-2026-11-09-for-nose4web-not-played).

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
capture1 P1 3:18 is 8 passes (Montreal, 25 game s, five players, a one-timer). Viewer: tag "fine tapestry · 3 passes"
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
is cut off (no end-of-stream marker) and fails to convert, before and after (2117 LA-BUF is the game). Checked
2026-11-08: its 417 samples (6.75 s real) are period 1 from 5:00 to 4:52 at 0-0, LA and BUF, with an empty full.bin.gz;
the game restarted from 5:00 two minutes later, and 2117 has it from the opening faceoff to the final (6-3). Nothing is lost. The fragment was deleted (the user, 2026-11-08).

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
  120). Any SNES study should keep the realistic set of skaters on the ice (or test the sensitivity). Tested 2026-11-04 (`snes_lane_timing.py`, run lane_timing2, about 18 minutes in gentle mode; run lane_timing cleared skaters from the wrong path): SNES_SHOOTING 4.8.
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
  (3-5 s of real time; the clock is stopped) after the faceoff box appears (at least 270 with some arena animations); the box's drop picture changes 17 and
  9 frames before it (updatefaceoff), too late to react to for the sweep. The person's faceoffs (110, six Genesis games):
  7-11 B presses in the last 1.5 s (real); state at the drop 16 / 8 / 0 = 23% / 47% / 26%, as mashing predicts (an 18-frame
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
  every counted breakaway goal came 3-5 game s (1.3-2.1 s real) after its breakaway.
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
  (104 = $68: so the first 16 units inside the line are free). a2touchpuck runs every frame for the carrier (pucknorm), for stick
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
  before the goal (Courtnall's P1 3:52 shorthanded goal had gone to his pass shot 7.5 game s earlier, which a Boston skater
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
  attacking-zone time (video 132 / 212, 233 / 100, 165 / 190 s of real time against the puck's 125 / 210, 221 / 107, 136 / 198), zone
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
  (+0.51); 38 winners had less zone time but finished better. 84% of the timed goals came within 16 game s (6.5 s real) of the play
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
  a game). The bottom net's right-hander seldom got there (7 of 181 tries): the turn was tuned at the top net only. Why the
  follow-up was claimed so seldom (version 8 replayed for 5 games, the end of each follow-up logged, "ea end"):
  after 39 first shots an opponent skater reached the loose puck first 22 times, the goalie held it 4 times, nothing
  came within 70 frames 5 times, the bot claimed it 7 times. The standing test has no defenders by the net; in games
  they are there. Idea not yet tried: the EA Special only when no defender is near the net, the deke otherwise.
- **Pucks lost carrying (versions 10-11).** In version 9's games 481 pucks were lost in the plain carry: 145 in its
  own end, 161 in the middle, 175 in the attacking zone. One replayed: in his own end the carrier steered straight up
  the ice from behind his own net, skated into its back and bobbled the puck there over and over. In the middle he
  carried in a straight line up his lane and was checked. Version 10 takes him around his own net first (out to 80
  to the side) and veers up and away from an opponent within 30 ahead before the gate: carry losses 417, but he left
  the deke's lane, dekes fell from 18 to 11 a game, goals 4.90 a game (0.40 against). Version 11 keeps only the way
  around the net: own-end losses 111 (145), carry losses 420, **20-0, 6.20 goals a game to 0.65** (version 9 6.15 -
  0.70: the same within the games' spread), the deke 43% a shot. Version 11 is the default.
- **Version 12: the deke on the right side too (no gain; 11 stays the default).** Version 11's attacking-zone
  carry losses (167) sit on the lane by the gate, 100-175 up the ice. One replayed: a carrier who came up the right
  passed the gate's line, swung back across to the left lane (200 frames) and was checked. In the standing check
  (`bot_deke_check.py`, NHL94_DEKE_SIDE=right, everyone on the ice), the set-up mirrored: with the left side's timings
  left-handers 3 of 24, right-handers 11 of 24; with each hand's own timing 11 and 11. The deke runs had found the game
  favours swings to the shooter's own left and that a left-hander's swing to his right doesn't get the puck across.
  The right-hander's forehand deke (their swing at 85, C 13 frames on) was 12 of 12; 78 / 13 11, 92 / 16 10; swung at
  60-70, 0-7 of 12. Version 12 has right-handers coming up the right deke there (DEKE12R); left-handers still cross.
  20 games: 20-0, 6.00 goals a game to 0.65 (version 11: 6.20). Right-handers started 169 dekes for 37 goals (version 11:
  126 for 36), so the 43 extra on the right scored about 1; attacking-zone carry losses 152 (167), all carry losses
  434 (420).
- **Real situations from the recorded games (docs/BOT_PLAN.md phase 1).** 472 carried zone entries from 16 recorded
  Genesis games placed in the harness, the bot playing on 15 game s: 10% scored (versions 6-12 all within a point), against
  15.5% for the people in those games from the same entries. Details in BOT_PLAN "Status". Version 13 (the one-timer
  widened to people's) struck more often but scored no more; its strikes met a set goalie (BOT_PLAN "Status").
- **Version 16, the default (BOT_PLAN "Status"):** no slapshot under pressure and the close-in wrist shot from 170 up
  the ice: from the entries 16.9% (version 11 10.0%, people 15.5%); whole games 8.50 goals a game to 1.05 (6.20).

## What check attempts lead to (both systems, 2026-11-03)

The user: what does a failed or whiffed check cost, whoever else is back? `analysis/check_outcomes.py --all` (every recorded
game): a person's burst while the other team has the puck with an opponent in reach ahead, as hit (the game counted a check),
failed (reached a man, or the SNES check animation, nothing counted) or whiff (within 30 of a man, touched nobody); a burst that never gets
within 30 (about 10 feet) is repositioning and isn't counted (the user; 98 Genesis and 59 SNES bursts, about 30% of the whiffs). Then the other
team's shots and goals in 15 game s while his team hasn't had the puck and no faceoff has come. Goal within 15 game s: Genesis 869 attempts, hit 6.4%, failed
12.9%, whiff 10.6%, no attempt 10.3% of moments; SNES 828, hit 3.5%, failed 12.2%, whiff 14.6%, no attempt 10.3%. In his own end:
Genesis 4.1 / 18.1 / 16.0 / 15.6%, SNES 5.0 / 18.9 / 23.9 / 14.7%. The puck won: hits 57-65%, misses 24-31%. A miss by who else was goal-side:
last man 21.4 / 23.0%, one teammate 9.6 / 18.2%, two or more 10.0 / 7.7% (Genesis / SNES), so on the SNES one teammate adds little.
A miss from goal-side loses goal-side within 2.5 game s 75 / 71% of the time; goal 13.1 / 12.6% when it does, 5.1 / 3.6% when it doesn't. The
fair comparison for the decision, in his own end from goal-side with the carrier in reach: tried 12.3 / 12.4% goal, won the puck 51 / 58%;
held off 13.2 / 12.9%. So a check tried there about breaks even on goals against: a hit saves about what a miss costs, and the attempt also wins
the puck half the time or more. Neighbouring moments aren't independent, people choose when to try, and dodged and badly aimed misses aren't told apart.
41 Genesis and 44 SNES goals came within 15 game s of a miss (bursts under 2.5 game s before the shot not counted), about a fifth to a quarter of the goals. In the match report: section 16.

## Keeping the other team out of the slot (Genesis, 2026-11-01)

The user's hypothesis after the BOS-TOR games: the key on defence is keeping the other team, and above all the puck,
out of your slot, more than standing in it yourself. `analysis/slot_defence.py --all` (23 recorded Genesis games):
every quarter second with a team carrying the puck in the other's end (past the blue line; loose pucks not counted,
about 2.5 game minutes a team a game), the state of the defending team's slot (within 35 of the middle and 100 of the goal
line) and the attackers' shots in the next 7.5 game s. The carrier in the slot: 0.21 xG, a goal 23% of the time (9% of the
time); an attacker without the puck there, open 0.12 / 12% (15%), covered 0.12 / 13% (4%); nobody attacking in it and
no defender 0.15 / 15% (36%, the most common dangerous state), one defender 0.10 / 10% (28%), two or more 0.10 / 9% (8%).
One-timers: 80 from the slot to a receiver open at the pass (no defender skater within 20; 40 goals), 5 to a covered
one; 96 / 7 from outside the slot. 94% of one-timers went to open receivers. So the hypothesis holds: the carrier in the
slot is the worst, an open man there is what the one-timers come from, and one defender in an empty slot cuts the
danger by a third while a second adds nothing. The match report has it as section 14 (`SD.measure`); the guide's game
plan as GENESIS_GUIDE 17, with `docs/img/slot_defence.svg` (make_diagrams.py).

## Passing out of a check (Genesis, 2026-11-06 / 07)

The user's play: draw a check, then pass just before it lands. The data comes from two scripts.

**What counts as a pass out of a check:** a pass that left before contact, or one that left after the bodies met while the puck was still his. The game's own pass count confirms these after-contact passes are real passes, not pucks knocked loose: it counted 94% of them on the Genesis and 98% on the SNES, as many as before contact. So once B starts the pass with the puck on his stick, it gets away. "B a moment too late" is a press that came just after the puck was already gone (under 0.2 s real).

**In the recordings** (`analysis/check_pass.py --all`, 38 Genesis games, 1,186 bursts at a person's carrier):
- The carrier passed before contact 300 times, and 209 reached a teammate.
- By how long (real time) the pass left before contact:
  - under 0.10 s: 60% reached a teammate, 11% were picked off by the checker;
  - 0.10-0.25 s: 78% reached a teammate;
  - 0.25-0.50 s: 13 of 13 did.
- Passes that left just after contact, still his: 56, of which 68% reached a teammate.
- The recordings can't separate the timing from the situation.

**SNES recordings** (33 games, 1,487 bursts at a person's carrier; the SNES's B starts the pass 3-4 samples after the press, and the puck leaves about 30 ms later):
- 344 passes out of a check, 280 reached a teammate (81%).
- By lead before contact, the share reaching a teammate barely changes: under 0.10 s 80% (the checker picked off 7%), 0.10-0.25 s 80% (20 passes), after contact 83% (127).
- B a moment too late: 46 (3%).

**In the game** (`analysis/scoring_map/check_pass_timing.py`, run cpt1, 2 chunks in gentle mode, 12,548 trials):
- **Set-up:** the 641 usable moments from those recordings were placed in the retail ROM 15 frames before the recorded burst. The checker was on pad 2, steering at the carrier and bursting at the recorded moment. The carrier was on pad 1, skating on and pressing B toward the receiver at offsets from -6 to +24 frames from the burst, or not at all. The receiver was the person's real target, or else the most open teammate. Two seeds were used.
- **Reached a teammate, by offset, same situation and seed (1,253 pairs):**

  | B, frames from the burst | -6 | 0 | 3 | 6 | 9 | 12 | 15 | 18 | 24 |
  |---|---|---|---|---|---|---|---|---|---|
  | Reached a teammate | 64% | 61% | 59% | 57% | 55% | 53% | 53% | 51% | 50% |

  Each 6 frames (0.1 s real) of delay costs about 2-3 points.
- **By lead before the landed check (the game counting it):**

  | Lead (real) | Teammate | Picked off by the checker | Passes |
  |---|---|---|---|
  | under 0.10 s | 54% | 16% | 532 |
  | 0.10-0.25 s | 65% | 5% | 378 |
  | 0.25-0.50 s | 58% | 1% | 117 |
  | 0.50 s or more | 24% | 4% (46% reached nobody) | 80 |

- **No pass:** the carrier was caught 22% of the time. The scripted checker landed his check in only about a quarter of the trials, fewer than a person's checks land, so not passing looks safer here than it is against a person.
- **Caveats:** the checker steers simply, and the carrier skates straight on.
- **Conclusion:** the timing itself matters. The last-instant pass is the one the checker picks off. Pressing B as he starts his burst, about 0.1-0.25 s (real) before the hit, is best.

**The ratings** (`analysis/scoring_map/check_pass_ratings.py`, run cpr1, gentle mode, 22,633 trials):
- **Set-up:** the same moments and checker as cpt1. B at -6, +3, +12 and +18 frames from the burst, one seed. One rating changed at a time, written into the skater's record after placing: the carrier's Passing ($6E) 8 / 28, the receiver's Stick Handling ($71) 8 / 28, the checker's Speed ($69) 12 / 24, and the checker's Weight ($67, stored as the rating x 8) 32 / 112. Every rating was still set at the end of every trial.
- **Reached a teammate, 624 situations with every variant played:**

  | Variant | B -6 fr | +3 | +12 | +18 | All |
  |---|---|---|---|---|---|
  | Base | 65% | 59% | 53% | 52% | 57% |
  | Passing 8 | 65% | 59% | 53% | 53% | 57% |
  | Passing 28 | 65% | 59% | 52% | 50% | 56% |
  | Receiver's Stick Handling 8 | 58% | 54% | 48% | 46% | 51% |
  | Receiver's Stick Handling 28 | 66% | 60% | 53% | 52% | 58% |
  | Checker's Speed 12 | 66% | 60% | 54% | 53% | 58% |
  | Checker's Speed 24 | 66% | 59% | 52% | 50% | 57% |
  | Checker's Weight 32 | 65% | 55% | 41% | 39% | 50% |
  | Checker's Weight 112 | 65% | 62% | 57% | 58% | 60% |

  The checker picked off 5-13% in every variant (base: 8%, 11%, 6%, 6%).
- **Paired against base, same situation and offset (better / worse):** Passing 8: 163 / 158; Passing 28: 58 / 75; Stick Handling 8: 0 / 146; Stick Handling 28: 14 / 0; Speed 12: 61 / 36; Speed 24: 26 / 36; Weight 32: 62 / 235; Weight 112: 174 / 94.
- **Why weight matters:** the checker is a person here (pad 2), so the weight bug applies: the lighter he is, the more often his check knocks the carrier down. With weight 32 the carrier was caught before passing in 19% of trials (10% at base, 6% at 112), and passes that left after contact reached a teammate 6% of the time (12% at base). Against a computer checker the weight works the normal way round (GENESIS_MECHANICS 7.2), which this run doesn't test.
- **Conclusion:** Passing and the checker's Speed don't change it. A receiver with poor hands loses about 6 points. A light person checker punishes a late B: from 0.2 s (real) after the burst, about 12 points fewer passes reach a teammate. An early B is as good against any checker.

**In the SNES game** (`analysis/scoring_map/snes_check_pass_timing.py`, run scpt2, gentle mode, 9,383 trials):
- **Set-up:**
  - The SNES harness can't give pad 2 a skater, so the checker is the computer's own defender.
  - The 818 recorded SNES check moments were placed 15 frames before the burst, two seeds each, every skater at his recorded place, speed and facing.
  - A scout run with no B found the frame an away skater burst at the carrier. That happened in 853 of 1,636 placements.
  - The same placement was then replayed with B at offsets from that frame. The game is deterministic, so everything before the press repeats.
- **Placing a skater for pad 1 needs three things:** `c1playernum`, `playerpad` ($19D4: the pad each object answers; negative means the computer) and the person flag. A skater's leftover animation (`pf2aip`, `pfalock`) must also be cleared, or the pad's presses are ignored.
- **Speeds:** a SNES velocity word of about 4,300 moves an object one unit a frame (held steady, 2,048 and 4,096 moved 0.47 and 0.95 a frame; positions change every other frame).
- **Reached a teammate, by offset, same placement:**

  | B, frames from the burst | -12 | -6 | 0 | 3 | 6 | 9 | 12 | 15 | 18 | 24 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | Reached a teammate | 32% | 36% | 38% | 42% | 34% | 36% | 32% | 33% | 31% | 29% |

  The share is lower than on the Genesis because a computer checker often takes the puck before a late press.
- **By lead before contact (passes that left):**

  | Lead (real) | Teammate | Picked off by the checker | Passes |
  |---|---|---|---|
  | after contact | 49% | 17% | 2,912 |
  | under 0.10 s | 53% | 15% | 615 |
  | 0.10-0.25 s | 55% | 15% | 354 |
  | 0.25-0.50 s | 51% | 12% | 246 |
  | 0.50 s or more | 28% | 11% | 186 |

- **No pass:** the carrier was caught 33% of the time.
- **Conclusion:** the same shape as the Genesis by when B is pressed, weaker: B as the burst begins is best, and later presses do worse. Unlike the Genesis, a pass leaving in the last 0.1 s before contact does about as well as one 0.1-0.25 s before.

**The SNES ratings** (`analysis/scoring_map/snes_check_pass_ratings.py`, run scpr1, gentle mode, 18,600 trials):
- **Set-up:** the scpt2 moments, one seed, B at -6, +3, +12 and +24 frames from the burst. One rating changed at a time, written after placing and before the scout: the carrier's Pass Accuracy ($13A3) 4 / 15, the receiver's Stick Handling ($1403) 4 / 15, and every opposing skater's Speed ($1303) 8 / 15, Weight ($12C3) 32 / 112 or Checking ($1483) 4 / 15. The checker is the computer's, so his ratings went on all the defenders. A changed defence changes whether and when the burst comes (from 384 to 476 of 818 situations against base's 419), so each variant is compared with base over the situations with a burst in both.
- **Against base, same situations (reached a teammate / picked off by the checker / caught before passing):**

  | Variant | Situations | Base | Variant | Better / worse for a teammate |
  |---|---|---|---|---|
  | Pass Accuracy 4 | 419 | 36% / 9% / 25% | 36% / 9% / 25% | 44 / 38 |
  | Pass Accuracy 15 | 419 | 36% / 9% / 25% | 36% / 9% / 25% | 4 / 3 |
  | Receiver's Stick Handling 4 | 419 | 36% / 9% / 25% | 31% / 10% / 25% | 0 / 84 |
  | Receiver's Stick Handling 15 | 419 | 36% / 9% / 25% | 36% / 9% / 25% | 0 / 0 |
  | Defenders' Speed 8 | 339 | 37% / 8% / 24% | 39% / 10% / 20% | 131 / 104 |
  | Defenders' Speed 15 | 367 | 37% / 9% / 24% | 37% / 10% / 23% | 77 / 73 |
  | Defenders' Weight 32 | 353 | 36% / 9% / 23% | 39% / 10% / 17% | 149 / 109 |
  | Defenders' Weight 112 | 343 | 37% / 9% / 23% | 33% / 10% / 28% | 120 / 171 |
  | Defenders' Checking 4 | 275 | 37% / 8% / 24% | 40% / 10% / 18% | 179 / 142 |
  | Defenders' Checking 15 | 331 | 36% / 9% / 24% | 37% / 9% / 24% | 196 / 181 |

  Most of the base skaters already have Stick Handling and Checking at 15 (the SNES maxes "cold" ratings), so the high settings change little.
- **Conclusion:** as on the Genesis, the passer's rating doesn't matter and a receiver with poor hands costs about 5 points. The defenders' Weight and Checking decide how often the carrier is caught before he passes, the normal way round (heavier and better checkers catch more): the checker here is the computer, with no weight bug.

## The SNES second period in full play (2026-11-07)

- **Question:** the leagues' SNES games have about 5% fewer goals a shot in period 2 (LEAGUE_RESULTS). Standing shots with only the period number changed came out the same shot for shot, which left moving play and the people.
- **Method** (`analysis/scoring_map/snes_period_cvc.py`, run spc1, 3 chunks, gentle mode): the computer plays itself from the harness's states, every pad taken off the teams as StartGame does for an empty pad (cont1team $1C84 0, padside $19F6 $FFFE, teampads $19D0 0, playerpad and c1playernum cleared, the person flag off). FaceoffPads gives no pad back: no person-flagged object in any segment. Each segment is 9,000 frames (2.5 minutes real) from a fresh seed; goals and shots are the game's own counters (tmscore $178E, tmshots $177A).
- **Results:**

  | Condition | Segments | Shots | Goals | Goals per shot |
  |---|---|---|---|---|
  | Period 1 (snes_top.state) | 641 | 7,200 | 512 | 0.071 ± 0.003 |
  | Period 2 (snes_bottom.state) | 641 | 7,274 | 513 | 0.071 ± 0.003 |
  | Period 3 (period-1 state, gsp 2) | 134 | 1,501 | 116 | 0.077 ± 0.007 |
  | Period 2 as period 1 (gsp 0) | 134 | 1,562 | 119 | 0.076 ± 0.007 |

- **The period number shifts the random draws, not the play.** Paired segments with only gsp changed split apart, but through the random generator. In periods 1-2 the number goes into the records (tmPerShots $176A, the goal log at $313A), and the frames after a goal then take different work. In period 3, Gameloop draws a random number every frame with the music off (a team song, 1 in $1000) and the computer's goalie-pulling and line tables read it. No code in periods 1-2 uses it for play.
- **Conclusion:** the computer's own play has no second-period dip. The leagues' dip (0.004 at this rate, inside the margin) most likely comes from the people.

## The scoring maps against a goalie as in games (both systems, 2026-11-07)

- **Runs:** Genesis mvg1 (as in games) and mvs1 (set): `map_run.py 0 1 RUN 200 20 15 [goalies_genesis.json]` with NHL94_SMAP_SUBSET=coarse (352 jobs, about 70 s each in gentle mode). SNES smvg1 and smvs1: `snes_map_run.py RUN 24 4 13 13` with NHL94_SMAP_SUBSET=coarse and NHL94_SNES_GOALIES for the first (176 jobs, about 2 minutes each). Goalie states from `xg.goalie_states` / `xg_snes.goalie_states` over every recorded game (Genesis 742 computer goalies, SNES 423), in the work folder.
- **SNES velocity:** placing the goalie's speed uses 4,096 a unit a frame; measured with the speed held, 4,096 moves an object 0.95 a frame.
- **Model comparison:** `compare_xg.py RUN [GOALIES.json]`, `snes_compare_xg.py RUN [GOALIES.json [glide]]`. Genesis: set 0.014 against the game's 0.023 (the set goalie's quirks aren't in the model); as in games 0.074 against 0.084. SNES: set 0.004 against 0.003; as in games old movement 0.050, glide 0.066, against 0.052.
- Results and pictures: SCORING_MAP "The goalie as in games".


## NOSE4Web's rocket pass fix, played in the game (Genesis, 2026-11-07)

- **The fix** (NOSE4Web's Genesis Hacks page): passtoa0's meeting time in 64ths of a second from the division's
  remainder, not eighths rounded toward zero (the rocket pass), and the other root tried when the first is just below
  zero (dbpl took a quotient of 0 as positive: a pass to a teammate skating away close by was made in an eighth). The
  code reads right against the disassembly: the remainder's sign against the divisor's tells a time just below zero;
  the four edits after it (the receiver's wait, where he will be x t / 16, the speed / 15 t) agree with the time in
  64ths; lift and the limits (an eighth, 3 s) are unchanged. One change besides: with no root ahead (both below zero,
  the second just so), the original made an eighth of it, the fix the 3 s limit.
- **Method** (`analysis/scoring_map/rocket_pass_test.py`, runs rpt_orig and rpt_fix, gentle mode): NOSE4Web's cases
  (every targeted pass of the recorded games; it counts the capture's raw samples, mapped here to the match file's
  moment), placed in live play as bot_scenario places a situation, the passer pressing B toward the recorded receiver,
  on the retail ROM and the patched one. 451 passes in both (194 moments can't be placed: fewer than six a side).
- **The ROM does what the arithmetic says:** from the game's inputs read at the release, the original ROM's puck
  matched the original arithmetic exactly on 297 of 433 passes, the patched ROM's the fix's on 295 of 432 (the rest
  differ by when in the frame the receiver moved, alike for both).
- **Results:**

  | Cases | Passes | Speed / intended (median) | Over 1.3x | To the receiver | To an opponent |
  |---|---|---|---|---|---|
  | Over 1.3x in the recordings, original | 235 | 1.25 | 99 | 50% | 32% |
  | the same, fixed | 235 | 1.03 | 1 | 53% | 31% |
  | Wrong root, original | 8 | 1.70 | 5 | 0% | 100% |
  | the same, fixed | 8 | 1.03 | 0 | 38% | 50% |
  | The rest, original | 208 | 1.07 | 23 | 58% | 26% |
  | the same, fixed | 208 | 1.01 | 3 | 62% | 22% |

  The fixed passes over 1.3x are the game's own limits: two at its 3 s limit (as fast in the original), two to a
  receiver right beside the passer at its eighth of a second minimum. No more interceptions with the slower, correct
  passes: fewer, if anything; the wrong-root passes, all picked off in the original's replays, reach their man in 3 of 8.

## NOSE4Web's runaway-speed fix, played in the game (Genesis, 2026-11-08)

- **The fix** clears the "deceleration off" flag (pfdoff; GENESIS_MECHANICS 3.4) where it leaked: asspassrec's exit when
  a person takes over the receiver, the end of a fall (the boards), and EndOneTimer (every one-timer, hit or missed;
  the third leak, found from the 2026-10-18_2219_WPG-BOS runaway: a missed one-timer never reaches puckstick).
- **Method** (`analysis/scoring_map/runaway_fix_test.py`, runs rft2_* and rft3_*, gentle mode): the recorded check
  moments in live play, the retail ROM against the patched one, with the same inputs; each case ends in three bursts
  (C, 30 frames apart) skating away from the puck. A runaway: still over 10,000 0.6 s (real) after the last burst
  (normal skating never passes about 9,500; a burst fades in about half a second; the peak alone also counts an
  ordinary burst's spike).
- **Results:**

  | Case | Original: still fast after the bursts | Fixed |
  |---|---|---|
  | Taken over with a pass coming | 21 of 99 | 0 of 96 |
  | Up from a fall into the boards | 7 of 15 | 0 of 16 |
  | A missed one-timer | 7 of 258 | 1 of 259 (the flag off: one late spike, a hit) |
  | Taken over, then a missed one-timer | 15 of 236 | 0 of 237 |

- **One-timers that connect:** after a pass, shot speed median 4,778 against 4,702 and 18% over 15,000 in both; taken
  over first, 5,494 against 5,204 and 10% against 9% (30 and 27 of 300). The same shot frame for frame in 216 and 164 of
  300: the patch runs at every animation's end, so its few cycles shift the game's timing-based randomness (the
  video counter), and play drifts apart from there; the flag reads the same in both until then.

## NOSE4Web's penalty-shot, goalie-pull, Y-button, extra-attacker and blind-ring fixes, played in the game (2026-11-08)

Each patched ROM against its original, from the same moments with the same random seeds (gentle mode). Scripts in
`analysis/scoring_map/`, each documented at its top.

- **Genesis penalty-shot table** (`ps_table_test.py`, bug 11): breakaways made in live play (the computer's carrier
  crossing the blue line with every other skater behind him, a defender close behind fouling him: the computer's, or
  pad 2 pressing C, B or holding B), 2,000 per ROM, 98 penalty shots each. The foul's own code comes from the same
  frame played again with BA_PS_flags bit 3 ("pending", the word's $0800) set, so PenShotChk leaves it alone (the
  game sets the penalty shot up one frame and writes PenBuf the next). The original gave every one the wrong penalty
  shot: charging slashing's (17), slashing roughing's (14), roughing cross-checking's (3), cross-checking hooking's
  (5), hooking tripping's (12), tripping interference's (42). The fix gave each its own, all 98, the fouled carrier the
  shooter. No holding came up.
- **Genesis penalty-shot fixes** (`ps_fixes_test.py`, bugs 15 and 17), 44 attempts per ROM. An out-of-play whistle
  (a PenBuf entry) while the shooter carries the puck: the original put the puck back at centre and ran the attempt
  again 44 of 44 (InProgress finds bit 3 still set); the fix went to a faceoff 44 of 44. The puck given pfnc at the
  award whistle (as a puck flipped out of the rink has it): still set as the original's attempt went live 44 of 44,
  the puck leaving the rink in 18; cleared every time on the fix, none left the rink. (The clock is stopped all through
  a Genesis attempt; the whistle shows as gmpen.)
- **Genesis goalie pull** (`goalie_pull_test.py`): third period, 50 s left, the computer (Away) with the puck in its
  attacking half, 40 trials at each score. The original pulled only 2 down (38 of 40); the fix 1 down (38) and 2 down
  (38); neither tied or 3 down. (CPgoalie's `st` sets tmgoalie's first byte: the word reads $FF00.)
- **SNES penalty-shot fixes** (`snes_ps_fixes_test.py`, bug 27): the penalty shot awarded as the game does after
  PenShotChk (BA_Sktr_SCnum, pspad, a PenBuf PenShot entry); the clock runs during a SNES attempt. The still-puck
  whistle (a loose puck held at one spot while creeping forward): a retake 40 of 40 on the original, retail and SA-1,
  a faceoff 40 of 40 on both fixes. A truly still puck ends the attempt first through pspuckback (48 frames of a loose
  puck not going forward), so this retake needs a puck that is still yet "going forward" and is probably rare. The
  knocked-off net (the shooter put beside it in the burst at $2400-$3400; one meeting in eight knocks it off): the
  original retook the shot 11 times; its other knocks ended properly only because the puck carried on into the end
  boards after the whistle (wallcoll ends the attempt for any loose-puck contact, even then); the fix never retook it.
  The SA-1 knocked net was checked in the code only (that build sets the attempt up in other objects; the stubs call
  its own EndPenaltyShotPlay $9E:C7F9 and AddPenalty2 $9E:B8EA).
  With the faceoff fix in the same ROM (NHL94_faceoff_and_penalty_shot_fixes.smc and the SA-1 one; the two blocks
  adjacent at the end of bank $9E, the penalty-shot jumps re-pointed to $9E:FF5F / FF6B, every other byte as in the
  single-fix ROMs): exactly the single fix's results, retail (19 knocked nets, all faceoffs; the still puck 40 of 40
  faceoffs; the original 11 and 40 retakes) and SA-1 (the still puck 40 of 40); the faceoff spots as the faceoff fix
  alone (FACEOFF_PLACEMENT).
- **SNES Y button** (`snes_y_button_test.py`): the recorded SNES check moments, no pass; each frame the pad-1 skater
  is locked (not bursting), without the puck, an opponent within 40, played with and without Y. The original: his own
  animation changed (a hook or hold) in 1,071 of 1,387 such frames (knockdowns, lock 1, and locks holding an animation:
  boards, bench, held). The fix: 0. Y still did something in 28 locked frames on the fix, all through another skater
  (21 with a teammate carrying: Y works for the carrier, a pass). Unlocked frames: the same on both (239 of 266).
- **SNES extra attacker** (`snes_extra_attacker_test.py`, bug 28): Edit Lines from the pause menu, every list pick at
  RD, LW, C and RW. The original, choosing the extra attacker (roster 4) at C: C 04 and the extra attacker 04, the old
  centre (03) off the line. The fix swaps them (C 04, extra attacker 03). Every other pick was the same on both (the
  game's own neighbour checks already swap within the line; the lists offer only that position's players).
- **Genesis blind ring** (`blind_ring_test.py`, the option): shots from 15 slot spots with 6 aims (the home centre,
  everyone else parked, the computer's goalie set). Ordinary shots (3,960 a ROM, the run stopped there): 52 goals on
  both, 3 through his middle on both; 5 shots ended differently. Flat pucks (NHL94_BRT_FLAT: the frame after the
  release, sent along the ice at his middle, +/- 6, at 9,000-22,000; 1,800 a ROM): the original let in 80, 77 through
  his middle; the fix none (36 of those went past him, 44 he held). Held 995 against 1,049 overall: the body test
  bounces more of them off him.

## Code readings for NOSE4Web's next fixes (2026-11-08)

Addresses are file offsets in the original ROMs (Genesis nhl94.bin; SNES NHL94.smc and the two 2 MB 2026 builds).

- **Bug 13, delayed-penalty sniping (Genesis only).** doshot (logic94 ~1984): `cmp.w #$C8,d3` at $C414, `bhi .notperf`,
  `jsr ReadGoaliePulled` ($FEFCC) at $C41C, `bmi.w .perf` at $C422 (`6B00 0084`). ReadGoaliePulled tests the
  *shooting* team's tmgoalie (negative: pulled, CPgoalie's `st` makes it $FF00), so every shot within 200 of its aim
  point is exact while the shooter's own goalie is off: a delayed penalty against the other team, or the computer's
  late pull (with the goalie-pull fix, at 1 or 2 down as well). An empty net at the other end changes nothing (the
  normal roll). The other three callers ($CD40 assdefo, $E016 asspuckc, $E7D2 assnearest) only shorten the computer's
  re-decision timer by a frame with its own goalie off, and don't touch shots. Without the `bmi` the shot takes the
  normal roll, (ShA + 1) / (ShA + 16) exact within 200 for working Shot Accuracy (about 52% at 15, 67% at 30). The SNES
  doshot has no such test (highlight and distance only). Recordings (`analysis/pulled_goalie_shots.py`, 26 Genesis
  games): 11 shots with the shooter's goalie off, all people's, the other goalie in; 8 through doshot (7 shots, a
  one-timer), 10 within 200, 3 goals from the 8. Too few to measure the effect.
- **Bug 25, the comeback bonus (SNES).** setplayer (routines/collide/setplayer.asm): half the period minus the clock,
  `beq .2`, then `bpl .6` skips the bonus in the second half (the Genesis's bgt at $15B70). `10 22` (bpl) at file
  $FCFFB ($9F:CFFB) in NHL94.smc, $FD10B in nhl94_2026.sfc (SA-1), $FD039 in nhl94snes_2026.sfc; `30` (bmi) turns it
  round (the exact half still gets it, as on the Genesis).
- **Bug 16, a goal after the award whistle (Genesis).** puckshootout's first call clears puckvx / puckvy and sets
  BA_PS_flags bit 2, after which Goal skips its gmclock test; the puck is moved to centre about 33 frames later. But
  the puck doesn't move in that window: six pucks sent at the net 3 frames after bit 2 came on stayed where they were,
  and a puck put at rest in the net didn't count. Before bit 2 the clock is stopped and Goal refuses. What does count:
  a foul on a breakaway carrier whose team keeps the puck is a delayed call (gmpendel), play goes on, and a goal then
  counts and clears "pending" (Goal, collide94 ~1366), so the penalty shot is cancelled: the NHL's rule too. Probably
  what was seen.
- **Bug 18, a penalty shot that ends at once (Genesis).** Not reproduced: none of the 88 attempts in the fix tests did
  (the shortest 269 frames). UpdatePenaltyShotEnd ends an attempt at once if the goalie has the puck (puckc =
  BA_Goalie_SCnum), or if shootoutclock is 0; puckshootout sets shootoutclock to $19 only at .setstopped on its first
  call, and a delayed penalty pending then (gmpendel) sends it to Stop4Pen before that, so a later call would start
  the attempt with the clock at 0. Not seen; needs a recording or how it happened.
- **Bug 20, the awareness slip.** Genesis: the computer's re-decision timer reloads from `move.b $6B(a3),$40(a3)`
  (aidef) in asswingo at $D0DE and asscentero at $D2D6, where the other offence jobs use $6A (aioff: assdefo $CD3A,
  asspuckc $E010, assnearest $E7CC); the byte to change is $D0E1 / $D2D9 ($6B to $6A). SNES (the same slip):
  `18 7D 43 13` (clc; adc aidef,x) in asscentero at $F049E and asswingo at $F0ACC, retail and nhl94snes_2026
  ($F04A0 / $F0ACE: $43 to $23, aioff $1323); SA-1 the same offsets ($7343 to $7323). Size (the 619 retail skaters,
  ratings x 5, no hot / cold): the timer is 7-15 frames; Defensive for Offensive changes it by 0 frames for 196, at
  most 1 for 456, at most 4, -0.3 on average. Small.
- **Bug 21, the crowd bonus (Genesis).** SetSflags8Bit1 at $FEF66 starts `60 00 00 0C` (bra.w .set, skipping its own
  bclr), so sflags8 bit 1 is always set; every crowd-bonus test reads it before the real flag (sflags7 bit 6, the
  meter past its record): +2 Agility and +2 Speed in skating (logic94 ~7513, ~7557), the chaser's slot boost (~4932),
  the goalie's body reach (collide94 ~1854), and a person's poke trip with penalties off (collide94 ~605). Two nops
  there would let the bonus follow the meter, which the recordings show on 73% of live play (GENESIS_MECHANICS 14),
  both teams alike: the +2 (of a working 30; about a tenth of top speed for a typical skater) gone the other 27%.

## NOSE4Web's sniping, comeback, awareness and crowd fixes, played in the game (2026-11-08)

Each patched ROM against its original (every one changes only the bytes in the readings above). Scripts in
`analysis/scoring_map/`.

- **Sniping (bug 13, Genesis; `sniping_test.py`):** a wrist shot from 9 spots 94-174 from the aim point, 30 seeds
  each, the shooter's own tmgoalie as it was or $FF00. Exact (the puck leaving with the spot's most common speeds):
  goalie in, 151 of 270 on both ROMs; pulled, 270 of 270 on the original and 155 of 270 on the fix.
- **Crowd bonus (bug 21, Genesis; `crowd_test.py`):** a skater from standstill skating 90 frames, the meter held loud
  or quiet. Top speed 8,111 loud on both; quiet 8,111 on the original, 7,670 on the fix (5% less). sflags8 bit 1 on in
  every frame on the original, never on the fix.
- **Awareness (bug 20; `awareness_test.py`):** live play with the computer on every skater; each time a winger's or
  centre's timer reloaded while his team had the puck, whether it was his aioff or aidef (where they differ).
  Genesis: aidef 533, aioff 386 on the original (the other offence jobs, the carrier and the nearest man, already use
  aioff); aidef 47, aioff 1,631 on the fix. SNES retail: 402 / 240 against 61 / 475 (the SNES adds the reload to a
  slightly negative timer, so some don't match either); SA-1: 375 / 24 against 0 / 327.
- **Comeback bonus (bug 25, SNES; `snes_comeback_test.py`):** the third period, Home one down or one up, a whistle
  and its faceoff (setplayer runs there), then Home's working Checking, trailing minus leading. Original: +2 in the
  first half, nothing in the second; fix: nothing in the first half, +2 in the second; retail and SA-1. Only the
  skaters below the cap of 15 show it (2 of 5 retail, 1 of 5 SA-1; the hot / cold bug maxes many).

## A "count stick deflections" option, tested (Genesis, 2026-11-08)

For NOSE4Web: a low shot off the goalie's stick isn't counted (puckstick `.stdef` at $151CE: `move.w #SFXstdef` /
`bsr sfx` / `bsr a2touchpuck` ($1013E, which clears sf2shot) / `bra deflect` ($15704); never ChkShotStat, $12F30).
- **ChkShotStat is not stats only:** with sf2shot set it goes through `.Cwdupdate` ($12FBC), which adds 100 to
  Crowdlevel and 10 to CwdExciteLvl before the counts (`.addShot`, $12FD0: team, power play, period, shooter, the
  other goalie's shots against). The crowd meter feeds play (the computer's quicker re-decisions, sflags7 bit 6; and
  with the crowd option, the +2). Calling `.addShot` directly with ChkShotStat's own frame skips it.
- **No room in `.stdef`:** the 8 bytes of `bsr a2touchpuck / bra deflect` at $151D6 become `jsr hook / nop`; the hook
  ends with a2touchpuck, drops its return and jumps to deflect (`count_deflections_rom.py`, a test copy only).
- **Once only:** the hook clears sf2shot, as a2touchpuck would anyway, so a later catch or body touch doesn't count
  it again. A deflection that then goes in gets Goal's own extra count (ChkShotStat's sflags4 path counts the scorer's
  shot on its second call when the shot flag is already clear), as a body touch that trickles in already does on the
  original; none of the 1,195 test shots did that.
- **In the game** (`count_deflections_test.py`, the same 600 shots per end on both ROMs, nine aims, wrist shots to
  full slapshots): top net, shots on goal 521 on the original and 574 with the hook, goals 11 and 11; bottom net 525
  and 581, goals 16 and 16. Every difference was +1 on one shot (53 top, 56 bottom), never more. 1,185 of the 1,195
  pairs played identically frame by frame for 150 frames; 10 drifted apart from frame 20-148, a few of them where
  the hook ran without counting: its extra cycles shift the game's video-counter randomness, as other hooks do.

## How often the fixed bugs happen in the recorded games (2026-11-08)

`python analysis/bug_frequency.py`: the recorded league games (26 Genesis, 25 SNES, people's games on the original
ROMs), per game.

| Bug (fix) | Recorded | A game |
|---|---|---|
| Genesis rocket passes (64 of them people's) | 69 | 2.7 |
| Genesis saves not counted as shots on goal (stick deflections and other touches) | 108 of 567 saves | 4.2 |
| Genesis faceoffs held off the game's dots (the faceoff fix) | 41 of 287 | 1.6 |
| Genesis shots exact with the shooter's own goalie off (sniping) | 7, 3 goals | 0.27 |
| Genesis runaway skaters | 3 | 0.12 |
| Genesis goals through the legs (blind ring) / shoulder-bobble goals | 3 / 2 of 218 goals | 0.12 / 0.08 |
| Genesis penalty shots awarded (table, retake, ghost puck) | 0 | 0 |
| SNES hooks and holds straight from a fall by a person (Y button) | 106 | 4.2 |
| SNES knocked-off nets / penalty shots (bug 27 needs both at once) | 12 / 2 | 0.48 / 0.08 |

- **The SNES Y button is the one that happens most.** A person's skater went from a fall straight into the hook or
  hold (animations $F864 / $F374, what Y starts while down: snes_y_button_test) 106 times. These are mid-fall, not a
  hook as he got up: falls that ended on their own lasted a median 106-153 frames, the ones cut short by the hook a
  median 29-38 frames (22 at the least).
- **Uncounted saves:** 62 of 307 going up the screen, 46 of 260 going down. These games don't show the leagues'
  direction effect (SHOOTING_STUDY: the leagues' 86,735 games do). Not all are the stick: `analysis/uncounted_study.py`
  over the same games puts 42 of 98 as knocked away by the stick, 16 held and 15 bounced off his body uncounted (most
  of those probably off the stick first), 16 off the boards or behind the net first and 9 after the clock stopped. So
  the count-stick-deflections option adds about 2 shots on goal a game (1.6 the clear ones, at most about 2.8), not
  the 4 of all uncounted saves (corrected 2026-11-08; NOSE4Web was told 4 first).
- The comeback bonus (wrong in every third period with a team tied or behind), the awareness slip and the crowd bonus
  (always on) aren't events, so not counted.

## One check for NOSE4Web's builds (2026-11-08)

`python analysis/scoring_map/fix_check.py ROM [--orig ORIGINAL] [--full] [--only ID,...] [--list]`: finds which of
the tested fixes a ROM has from their bytes (call sites and changed instructions, so combined builds are found too),
lists any changed bytes outside them, and runs each fix's study script above on the ROM and the original of its layout
(nhl94.bin, NHL94.smc, nhl94_2026.sfc, nhl94snes_2026.sfc, from the ROM's folder), smaller than the write-ups unless
`--full`, with a pass when the ROM shows the fix and the original the bug. SNES files with a copier header are read
without it. First run, every NOSE4Web build so far (quick sizes): all 22 tests on 20 ROMs passed, nothing else changed
in any of them; the detection alone was right on all 25 ROMs in the folder (the originals: none found).

## The Genesis-only fixes: does the SNES have the bug? (2026-11-08, for NOSE4Web)

Offsets in NHL94.smc (retail), nhl94_2026.sfc (SA-1), nhl94snes_2026.sfc (2 MB).

| Genesis fix | SNES | Where / why not |
|---|---|---|
| Pulled-goalie sniping | No | doshot tests only the highlight flag and the distance before the accuracy roll |
| Computer forwards' awareness | Yes | Already built and tested (the SNES awareness fix) |
| Crowd bonus | No | The crowd has no effect on play (SNES_MECHANICS 13) |
| Count stick deflections | **Yes**, wider | See below |
| Second assist | **Yes** | See below |
| Aggression wrap | No | checkagr is 16-bit; nothing wraps (8.1) |
| Rocket pass | No | Pass speed comes from the distance |
| Runaway skater | No | Confirmed in the recordings (3.3) |
| Penalty-shot table | No | No table: a breakaway foul becomes the one PenShot entry ($24) |
| Weight bug / C-then-B | No | Base 120 for everyone, 16-bit sum (7.1) |

- **Second assist.** a2touchpuck (routines/logic/puck/a2touchpuck.asm `.t1`) shifts the touches with no check
  (`lda tmtouch2,y / sta tmtouch3,y / lda tmtouch1,y / sta tmtouch2,y`), then drops the second assist when the new
  toucher is also the third: C, A, B, A and A scores gives B one assist and C none, as on the Genesis. The shift is
  `B9 9E 17 99 A2 17 B9 9A 17 99 9E 17` at $F4549 ($9E:C549) retail, $F45B1 SA-1 (`77` for `17`), $F4591 2 MB; d0 ($A5)
  holds the new toucher's pnum. The Genesis fix's rule: when the new toucher is tmtouch2 already, keep tmtouch3. There
  is only the one place on the SNES (the Genesis also shifts in the one-timer code).
- **Stick (and glove) deflections.** puckstick `.t1x` ("too fast: nopuck 8, deflect", also the goalie's path when the
  puck is faster than he can catch) goes to `.3`: PuckSfx, a2touchpuck (clears sf2shot), deflect, never ChkShotStat.
  `.t1x` = `A4 91 A9 08 00 99 03 12 4C <.3>` at $F7714 ($9E:F714) retail, $F7797 SA-1, $F7766 2 MB; `.3` at $F768B /
  $F770E / $F76DD. ChkShotStat is $9E:F213 / $9E:F296 / $9E:F265 (it checks sf2shot and the clock itself and clears
  sf2shot, so once only; its crowd boost is harmless on the SNES). A hook: at `.t1x`'s `jmp .3`, jump to new code that
  does `lda position,y / bne` (not a goalie: on to `.3`) and otherwise `jsl ChkShotStat` before `.3`. It catches the
  glove too: the SNES goalie's stick / glove area deflects hard high shots as well (SNES_SHOOTING 4.6).
- **Played in the game** (2026-11-08, `analysis/scoring_map/snes_assist_stick_test.py`; NOSE4Web's
  *_second_assist_and_stick_shots builds, and for the shots copies with only the stick hook, since the assist hook runs
  on every touch and shifts the game's timing-based randomness): **second assist**, the touch history set to C, A, B
  and A taking the puck, then a goal into an empty net: the original's scoring summary has B and no second assist, the
  fix's B and C, in all three builds; a control (C, B, D, then A) gives D and B on both. **Stick deflections**, the
  same shots on both ROMs (the pad-1 skater with the puck at 20 spots, 9 aims, A held 3-12 frames): retail 267 to 297
  shots on goal of 300 (goals 2 and 2); SA-1 389 to 393 of 400; 2 MB 366 to 372 of 400. In pairs that played the same
  every difference was one more shot; in the 2 MB build 76 pairs drifted apart (the hook also runs for a skater's stick
  meeting a puck too fast to catch, adding a few cycles), where outcomes can differ either way. The recordings: 131 of
  532 saves in 29 SNES games weren't counted, 4.5 a game, the most the option can add (nearly all stick and glove
  deflections; the rest off the boards or as the clock stopped).

## Momentum in the recorded games (2026-11-08, a community member's question)

`analysis/momentum_study.py`: each team's shots in a recorded game, in order, split into a first and a second half
(the middle shot of an odd count left out; team-games with 6+ shots), against the same shots shuffled within each
team-game 2,000 times (order meaning nothing). The league's box scores, by period, are in LEAGUE_RESULTS "Momentum".

| | Genesis (26 games) | SNES (29 games) |
|---|---|---|
| Shots on goal: first / second half | 27.3% / 36.7% (shuffled: a gap this big 1% of the time) | 30.8% / 31.8% (83%) |
| All attempts: first / second half | 19.4% / 22.6% (22%) | 22.1% / 22.1% |
| First-half % with second-half %, correlation (shuffled) | +0.33 (+0.26, 95% +0.06 to +0.46) | +0.06 (+0.15) |
| Next 3 shots on goal after a goal / other shots (shuffled gap) | 35.9% / 27.0%: +8.9 (+6.4, 95% +0.8 to +11.9) | 33.8% / 29.4%: +4.4 (+4.0) |

- The shots after a goal do go in more often, but nearly all of that is the shuffled baseline too: a team that scores
  a lot in a game has more shots after its goals. Every gap is inside the shuffled range.
- The Genesis second halves went in more often (36.7% against 27.3% on shots on goal), and shuffling rarely gives a
  gap that size. But it is 26 games, mostly one person's, and all attempts (22% of shuffles) and the league's 87,000
  Genesis box scores (no momentum by period) don't back it, so it reads as these games, not the ROM.

## NOSE4Web's player photo and score logo editing, seen in the game (2026-11-08)

`analysis/scoring_map/menu_shots.py` boots a ROM in a copy of the core and follows a script of button presses, waits and
screenshots (a `u:` step presses until a RAM word, a menu's cursor, has a value: presses can be lost, and the SNES pause
menu ignores the first one at some moments). The same script on the original and the edited ROM gives screens to
compare frame for frame.

- **Genesis (nhl94_photos.bin, ANH vs BOS):** the setup screen's cards (Boston's six and Anaheim's six alternating,
  Kasatonov the second card, after Boston's Sweeney) and the seven matchups differ from the original only in Moog's and
  Kasatonov's pictures, now the test pattern, and in the hot / cold streaks and Ron Barr's lines (random each run). A
  card opens at most 2 frames (real) later on the edited ROM. Houlder, Anaheim's 7th featured picture, is never on the
  setup screen (cards94: it wraps after the sixth) or in the matchups (each position's first-line player, from the
  team's line sets); with him put on Anaheim's first line in a scratch copy, his test pattern shows on the left
  defence matchup (DrawPlayerPicture searches the whole list). The ROM's checksum check (checksum94, called at $300) is
  skipped and its space reused; the header checksum is updated.
- **SNES retail (NHL94_photos.smc, BOS vs LA):** the matchups and every pause-menu Player Card of both teams match the
  original except Moog's card and goalie matchup and John Blue's card (had the generic goalie), both the test pattern.
- **SNES SA-1 (nhl94_2026_photos.sfc, BOS vs VGK):** the setup screen's cards, the matchups and both teams' Player Cards
  match except Swayman (card, setup screen, goalie matchup) and DiPietro (card).
- **Score logos (nhl94_2026_score_logos.sfc):** Buffalo shows Boston's logo and Carolina Chicago's, in the score box
  and in the clock box on a power play (set by making tmap differ, $17A6: only the display was tested); Calgary its
  letters in both, laid out as the retail game prints a name ("LA PwrPlay" in retail). Boston and Vegas look the same
  on both ROMs, and the only changed bytes are those three teams' table entries and data (and the checksum).

## McMarkis's score-box logos on the original SNES game: what retail leaves free (2026-11-08, for NOSE4Web)

`analysis/scoring_map/snes_score_logo_check.py` plays a whole retail game (penalties on, line changes on and off,
every period cut short) with the 12 tiles from ExtraChars marked in VRAM and palbuffer rows 4 and 7 watched every
frame, a pause into every pause-menu screen, an instant replay, a power play and the breaks between periods, and scans
both background maps every 10 frames of play (vertical and horizontal rink).

- **ExtraChars** is $472 in play on NHL94.smc, NHL94_Classic.smc and SDL16.smc: VRAM words $5720-$57DF, below the
  sprite tiles at $6000 (room up to ExtraChars $4F4). No map entry ever points at them (BG1, the text layer, tiles from
  $2000, printed numbers 256 below the global ones: tiles $372-$37D; BG2, the rink, can't reach them). Only two pause
  screens write over them: Edit Lines and Crowd Level; both go back to the rink through ExitStatsScreen (McMarkis's
  ReloadRink). Game Stats, Team Roster, Player Stats, the summaries, Period Stats, Player Cards, Other Scores, the
  replay, the power play, the horizontal scoreboard and the breaks between periods leave them alone.
- **Palettes in play:** vertical rink BG1 uses palettes 0 and 1, and 4 for the line-change box (line changes on), whose
  tiles use colours 1 and 4 only (colour 4 black); BG2 uses 0, 1, 2, 3, 5, 6. Palette 7 is unused on the vertical rink.
  The horizontal scoreboard's team banners use palettes 6 (visitors) and 7 (home), colours 2-15: DrawHorTeams sends
  colourbuf's palettes 6-7 straight to CGRAM while it is up, and ClrHor sends palbuffer's palettes 0-7 back (its X is a
  colour count: $80 = 128 colours) whenever the vertical rink returns.
- **palbuffer rows 4 and 7** are never written during a game (only setupice's RinkPalette copy at the start: row 4
  colours 0-3, row 7 colour 0). DMAToCGRAM counts colours, not bytes; with the screen on it only queues one upload for
  the NMI. FadeIn / BrightnessHook change brightness only.
- **Horizontal mode:** printscores1's .sbscreen prints the period and the big scores; the team names are DrawHorTeams'
  banners (TeamBlocksTiles), not three letters.

## NOSE4Web's retail score-box logos, checked in the game (2026-11-08)

`analysis/scoring_map/snes_score_logo_build_check.py ORIGINAL EDITED OUT HOME:VISITOR ...` (retail layout; penalties
and line changes on): per matchup, on both ROMs, the score box, the power-play box for each side (tmap made to
differ while the clock ticks), play after Edit Lines and Crowd Level, the horizontal pause scoreboard, play after the
break into period 2 and the line-change box, as a sheet original beside edited, and the ROMs' changed byte ranges.
NHL94_score_logos.smc against NHL94.smc, Buffalo v Calgary, Hartford v Boston, Toronto v Chicago: the logos in the
score box and in the power-play box for either side, back after Edit Lines, Crowd Level and the break; Hartford keeps
its letters in both boxes; the scoreboard's banners pixel-identical; the line-change box unchanged. The changed bytes
are the five hooks NOSE4Web listed, three blocks of new code and logo data, and the checksum. Boston's made logo shows
its "B" in grey and olive rather than black and gold (Calgary, Buffalo, Chicago and Toronto look right in both
palettes, so it is that logo's colours). The 16:49 rebuild (made logos only): Boston black and gold; Philadelphia and
Los Angeles match the game's own big logos (black with a white "P" and a red dot; silver and black); Montreal,
Buffalo, Calgary and Hartford's letters as before; Detroit's wheel comes out pink, $51FF (255,121,164) and $457F (255,89,139). Both
are the big logo's own shades between its red and white (82 and 11 of its pixels, against 285 white, 208 red $001F and
111 dark red), and the game draws them as they are (palbuffer row 4, colours 6 and 7, exactly the screen's): no blend
and no colour maths; the red-and-white stripes' mix is nearest the pink, so "nearest the mix" picks it. (Corrected
2026-11-08: first reported as colours the big logo doesn't have.) The 17:03 rebuild leaves a big logo's in-between shades
out: Detroit's wheel red and white; Boston, Philadelphia, Montreal and Los Angeles as before.

## $A130F1 in Genesis Plus GX (2026-11-08, for NOSE4Web)

`analysis/scoring_map/a130f1_test.py` builds a test ROM (save memory declared at $200001-$20FFFF as EVO's, $5A in
the ROM there) and runs it in our copy of RetroArch 1.17's core (Genesis Plus GX v1.7.4 ed5c591). 3 MB: at power-on
$200001 reads the ROM; writing 1 to $A130F1 switches the save memory in (a written $C3 reads back), 0 switches the
ROM back, repeatedly. 2 MB: the save memory past the end of the ROM, writing 0 hides it as well (reads $FF); power-on
reads $FF (blank save memory or nothing: not told apart). Other emulators not tried.

## The SNES big logos' overlapping pieces: which is in front (2026-11-08, for NOSE4Web)

The big team logos (matchups, Game Setup and stats screens, player cards) are sprites: DrawSprite writes a logo's
pieces into the sprite table in list order (sprcount + 4 a piece) and the game never rotates sprite priority (OAMADDH
only ever cleared), so the first piece has the lowest sprite number and is in front. `analysis/scoring_map/
snes_logo_overlap.py` rebuilds a logo from the game's own sprite table (OAMShowBuf), VRAM tiles and colourbuf on the
matchups' first page, in both orders: on NHL94.smc the rebuild matches the screen in every pixel for all 28 teams.
Only Hartford's pieces overlap (180 pixels where two pieces have colour; NOSE4Web counts 192), and in every one the
two pieces have the same colour, so front-first and back-first give the same picture: a later-over-earlier render
matches the game for every retail logo. A logo made or edited with overlapping pieces of different colours would show
the earlier piece in the game.

## Game variables: phase 1 (2026-11-08; docs/GAME_VARIABLES_PLAN.md)

- **Study 3, penalties and the score:** LEAGUE_RESULTS "Penalties and the score". In the recorded games
  (penalties' fouling player at the call, distance to the puck): Genesis, the computer's penalized skaters a median
  117 from the puck (4 of 34 within 40), people's 42 (14 of 28 within 40); SNES 41 and 21. **Penalties away from the
  play are mostly the computer's skaters**, as the roll says: a person's range is doubled (half the calls), so most
  of a computer team's and a person's teammates' calls come off the puck.
- **Study 1, luck against skill** (`analysis/luck_vs_skill.py`, the recorded whole games, mostly one person's): the
  goal difference correlates 0.90 with the expected-goals difference on both systems (26 Genesis games, 28 SNES); the
  rest (luck) is about a fifth of its variance (Genesis 4.8 of 24.3, SNES 2.4 of 13.7). A team's goals less the xG of
  the same attempts (finishing luck, the forum's "AI factor" measured) has a spread (sd) of 1.5 goals a game on the
  Genesis and 1.3 on the SNES: within a goal of the chances in about half the team-games, more than 2 goals off in one
  in six. The team with clearly better chances (0.25 xG or more) lost 2 of 25 Genesis games and 6 of 28 SNES games;
  the winners' Deserve to Win was a median 95% / 93%.
- **Study 2, what hot / cold is worth** (`analysis/hot_cold_worth.py`): each recorded game's shots played out again
  with the hot / cold taken out of the working ratings the expected-goals model reads (the shooter's Shot Accuracy;
  the goalie's Agility, Speed, awareness and puck control), for the shooters, the goalies and both; the rerun with the
  real ratings matched the stored xG in every game. Genesis (23 games; one value from -3 to +2 on the 0-30 scale):
  hot / cold changed a team's expected goals by **0.05 a game** on average (largest 0.38, a cold goalie), the gap
  between the teams by 0.08 (the average gap 2.89), and never which team had the better chances. SNES (29 games; the
  sign bug's maxed ratings put back to their step plus the team's bonus, the goalie's reaction time left as played):
  **0.18 a game** (largest 0.62), the gap by 0.28 (average gap 2.62), and once (1 of 29) which team had the better
  chances. Only what hot / cold does at the shot is counted: its effect on skating, checking and passing, which make
  the chances, isn't.
- **Study 4, are the dice streaky?** (`analysis/streaks.py`; each player's results in a game in order, the summed
  products of consecutive results' distances from the sequence's own mean, against 2,000 shuffles of the same
  sequences). **Shots, goalies and passes: no streaks** on either system (Genesis: shots 52% of shuffles at or above
  the real statistic, goalies 57%, passes 66%; SNES 16%, 63%, 50%). After 1, 2 and 3+ misses in a row a shooter's
  next shot scored as its expected goals said on the Genesis (126 goals against 127.6, 72 / 74.4, 43 / 40.4); on the
  SNES below (107 / 122.2, 59 / 67.4, 33 / 41.2), which is selection (shooters who miss a lot are the ones the SNES
  model overrates; its xG runs about 0.19 goals a team-game high), not a streak: the shuffle test, which compares
  each shooter with himself, finds nothing. **Checks cluster**: hits follow hits (SNES 0% of shuffles, Genesis 7%).
  Split by checker and target, the Genesis clustering goes (22%): the same man checked again and again (weights and
  ratings decide). The SNES keeps some (2%, 169 checker-target sequences): something lasting through a spell
  (perhaps the approach's speed and angle), not the dice.
- **Study 5, missing a great chance** (`analysis/open_net_misses.py [--list]`; attempts worth 0.5+ xG that didn't
  score, a miss placed by where the recording shows the puck crossing the net's front). Genesis: 205 such chances, 134
  scored (155.3 expected); of the 71 that didn't, **the goalie got to it 32**, a skater blocked 10, wide of the post 9,
  over the crossbar 7, never reached the net 5, a post 4, a crossing inside the frame (deflected) 4; 22 of the 71 had
  the goalie 5+ ft off the shot line. SNES: 218, 143 scored (168.9 expected); of 75, **the goalie 44**, a post 14,
  wide 5, over 4, blocked 4, never reached 3. So "missing an open net" is rarely a miss: the goalie getting across
  (or the post, or a stick) is most of it; wide or over is one miss in five on the Genesis, one in eight on the SNES.
  **The xG models run about 14% high on these chances on both systems** (the recorded goalies get across more often
  than the modelled one): a point for the models' next calibration.
- **Study 6, easy goals** (`analysis/easy_goals.py`; each goal matched to its shot, the ones under 0.1 xG or not
  priced). Genesis: 36 of 218 goals (17%): 19 deflections and scrambles the models don't price, 17 priced shots;
  among them 13 one-timers, 9 with the goalie 5+ ft off the line, 7 off a check, 6 off rebounds; the game's quirks
  only 3 through the legs, 2 shoulder-save bobbles and 2 goalie giveaways. SNES: 23 of 217 (11%), 19 priced shots, 6
  with the goalie off the line. **A person in net is over-represented**: a person had the goalie for 16% of the shots
  on net on the Genesis (25% of all goals) but 12 of the 36 easy goals (33%); SNES 28% of shots (34% of goals) but 11
  of the 23 (48%): taking the goalie lets in more of the low chances (few goals; a lead, not a finding). By band, the
  models are too sure at both ends: shots under 0.1 xG scored about twice what they said (Genesis 17 goals against
  7.6 on 537 attempts, SNES 19 against 9.1), 0.1-0.6 about right, 0.6 and up about 14% short (112 / 128.1, 127 /
  148.0).
- **Study 7, loose pucks** (`analysis/loose_pucks.py`; games with a person on each side; a loose spell of 0.1-3 s
  with the clock running, ended by a player taking the puck; who had him just before he reached it, since control
  moves to the carrier at the pickup). Genesis: of 2,873, a person's skater took 1,132, **a computer skater 1,462**, a
  goalie 279. Per game the two computers' shares follow their teams' Offensive + Defensive Awareness steps
  (correlation +0.62 over 22 games; the home team's computer won 54% on average, as its awareness bonus says). **No
  catch-up**: the leading team's computer won more (605) than the trailing team's (513). SNES: the person's own skater
  reaches most (2,641 of 3,118; computer skaters 80, too few to split).
- **Study 8, what started each goal** (`analysis/goal_causes.py`; games with a person on each side; each goal's
  causes, and a primary one in this order: a giveaway by the scored-on team within 12.5 game s, in its own zone or
  elsewhere; a takeaway (forced) in the same window; an odd-man rush; the shooter left open (no defender within 30,
  about 10 ft, at the release); the goalie 5+ ft off the line; a rebound; a power play; off a faceoff; none).
  Genesis (176 goals): own-zone giveaway 12%, giveaway elsewhere 8%, takeaway 19%, odd-man rush 24%, shooter left
  open 30%, goalie off the line 2% (57 goals had it among their causes), the rest 1-3% each, none 3%. SNES (158): 6%,
  4%, 18%, 25%, 26%, 7% (66 had it), power play 3%, none 11% (the SNES shot list marks no rebounds). Something the
  defence did, or let happen, is behind almost every goal; how much of it is a mistake rather than the attacker's
  skill (a fine pass, a good breakout) the recording can't say.
- **Study 9, a first measure: drawing two** (`analysis/draw_two.py`; games with a person on each side; a person's
  carrier in his attacking zone "drew two" when two or more defenders were within 50, about 17 ft, of him while a
  teammate in the zone had none that close; the team's xG from the possession's start to 2 s after it). It happens
  in 38% of such possessions on the Genesis (1,640) and 46% on the SNES (1,760). Overall they bring more xG (Genesis
  0.144 against 0.116, SNES 0.130 against 0.104), but at equal lengths only the quick ones do (under 1 s real:
  0.124 against 0.085, SNES 0.115 against 0.061: draw and pass); at 1-4 s no difference. Per game, the person who
  drew two more often didn't make the better chances (correlation with the xG difference +0.10 Genesis, -0.61 SNES).
  **Inconclusive**: drawing defenders pays when the pass comes at once; doing it more isn't a mark of the stronger
  player in these games (mostly one person's). A proper test needs more people's games and whether the pass goes to
  the open man.

## NOSE4Web's Classic import into the 32-team SA-1 build (2026-11-08)

nhl94_2026_classic.sfc (McMarkis's 32-team SA-1 build with NHL94_Classic.smc's 28 teams imported) against
NHL94_Classic.smc (`analysis/scoring_map/menu_shots.py`): Montreal v Los Angeles, Boston v Chicago, a playoff start.
Right: the big logos (setup, matchups, player cards), the players' photos, names and positions, the team page's
nickname and arena, the score-box logos, the playoff start. Wrong: the team-name banners everywhere (setup, player
select, matchups, the pre-game menu, the horizontal scoreboard, the card's team page, the playoff bracket) and centre
ice, both by a team's Classic index read in the 32-team alphabetical list (Anaheim-Calgary right; Chicago shows
CAROLINA, Los Angeles EDMONTON, Montreal FLORIDA and Florida's centre ice). The playoff draw mixes the conferences
(Classic's is Wales and Campbell); the team and player Overall ratings shown differ from Classic's (Montreal 73 -> 66
on the matchups, Boston's card 76 -> 74): reported to NOSE4Web. The 18:00 rebuild: the banners right everywhere (TeamPlaceNames
and TeamBlockPalettes imported), the overalls and team ratings as Classic's, the playoff draw Classic's own Wales and
Campbell bracket, centre ice Classic's logos (shape, size, centred); **the centre-ice colours still wrong** (Montreal's
red C grey: (148,80,82) -> (131,121,123); the Kings' silver bluish: (156,157,156) -> (131,141,172), (74,72,74) ->
(74,72,115); Chicago's tan face and gold and green feathers pink and red). The 18:28 rebuild (each team's own 15 centre-ice colours set from Classic's rink rows): at the opening faceoff Los Angeles, Boston and Detroit pixel-identical to Classic, Montreal and Chicago differing only where skaters stand; no logo colour differs.

## Genesis score-box logos: what the original game leaves free (2026-11-08, for NOSE4Web)

NOSE4Web's plan: printscores1's 8x5 score box at x $17, y $17 becomes 8x7 at y $15 (a 24x16 logo and the score per
team, visitors above, home below), each logo in its team's uniform palette line. Checked on nhl94.bin with
`analysis/scoring_map/gen_score_logo_check.py` (a whole game: every 30 frames of vertical play the text map, every plane
map and the sprite table read from video memory, which Genesis Plus GX keeps in its saved state at VRAM_AT = 74789;
pause screens Edit Lines, Game Stats, Player Cards, Other Scores, Crowd Meter, a replay, both breaks) and
`gen_lc_box_check.py` (the line-change box, palettes, sprite priority). RAM names from the disassembly's build listing.
- **The corner** (columns $17-$1E, rows $15-$16 of the text map, plane A at $E000, 64x32): blank ($07FF) at every
  look in vertical play. The one thing that reaches it is the **lower line-change box** (line changes On, A held by
  a person's carrier; sflags3 bit 0): setlccords puts it at x $16, y $16, 9 wide, 6 rows (5 without a third line):
  rows $16-$1B, over the score box, which printscores1 skips while it is up. So a box from row $15 would leave its top
  row showing above the line-change box. lcfound_close blanks the box's area and calls printscores1, and ClrHor (back
  from the horizontal rink) blanks the whole 32x28 text area and calls printscores1: both redraw a taller box whole.
  The ticker (26x5 at x 3, y $17) only shows on the horizontal scoreboard; messages sit at x 0, y $A; the penalty-shot
  and other boxes at the top.
- **Video memory**: tiles no map or sprite used in play and nothing wrote all game, all zeros, clear of the planes
  ($C000, $E000, window $F000), the sprite table ($DC00) and the scroll table ($FC00): **$294-$29F** (exactly 12, VRAM
  $5280-$53FF) and **$3EC-$3FB** (16, $7D80-$7F7F, just before the box frame's tiles $3FC-$404). ExtraChars holds the
  horizontal referee tiles here, so it isn't free as on the SNES. ClrHor and ReloadRinkGraphics reload the rink tiles
  and the home team's graphics, but not these.
- **Palettes**: in play line 2 holds the home team's home palette and line 3 the visitors' away palette (copied by
  the routine setupice, StartHL2, the highlight setup and ReloadRinkGraphics call: after pause screens and replays);
  SetHor draws with no palette lines, so the vertical box always has them. The box's fill tile ($400, line 1) is all
  colour 7 = $0000 black; logo tiles replace their cells, so their see-through pixels would show the ice, not the box:
  a logo's background must be painted in black from its own line. Colour 2 is $0000 in all 56 retail uniform
  palettes (home and away, 28 teams).
- **Priority**: none of the 31 sprites in the table has the priority bit (the players are low-priority sprites); the
  box's letters, frame and fill all have it ($84xx, $A3FC-$A404), so the logo tiles need it too, or players would skate
  over the logos.

## NOSE4Web's Genesis score-box logos, checked in the game (2026-11-08)

nhl94_score_logos.bin (NOSE4Web, 19:12) against nhl94.bin with `analysis/scoring_map/gen_score_logo_build_check.py`:
the same presses on both ROMs; at each moment a screenshot, the text map's cells (columns $16-$1E, rows $15-$1C) and the
logo tiles. Full run: Montreal (home) v Los Angeles, penalties and line changes On, pad 1 home; in play, the lower
line-change box opened (A held by pad 1's carrier) and closed (B), back from Edit Lines and Game Stats, an instant
replay (its own menu, then the pause menu on the side view, Resume), the break, period 2 in play, a skater under the
box. Short runs (in play only, palettes): Hartford v Boston, Boston v Montreal, Montreal v Boston.
- **The bytes**: only the listed hooks, the checksum test NOP'd at $300, the header, new code at $FFAC0 and data at
  $100000-$102691.
- **In play**: the box is 7 rows, $15-$1B; visitors' logo tiles $29A-$29F on rows $16-$17 (map words $E29A..., the
  priority bit, line 3), home $294-$299 on rows $19-$1A ($C294..., priority, line 2); each score at columns $1C-$1D on
  the logo's lower row. Hartford shows its letters (HFD) in the logo's place, as planned. Palette lines 2 and 3 are
  the same as the original's in every matchup (the build changes no colours): Boston's logo at home is drawn from its
  home line and on the road from its away line (a few pixels differ, the grey shades), Montreal's likewise (the H's
  white $EEE at home, $CCC away). Each logo's edge has a few pixels in the colours every uniform line shares (slot 6,
  the skin tone, pink; slot 15, light blue); they show against the black box. They are probably the converter's
  nearest colours for anti-aliased edges, and are cosmetic.
- **The line-change box**: opened, row $15 is blanked ($87FF) and the box covers $16-$1B; closed, the whole 7-row box
  with both logos is back.
- **After pause screens, the replay, the side view and the break**: the box and logos are intact after Edit Lines,
  Game Stats and the replay. The pause menu's side view and the break's scoreboard look the same as the original's.
  Period 2 in play has both logos (visitors still above). In replays neither ROM shows the score box.
- **A skater under the box**: drawn behind it, as on the original (the logo tiles have the priority bit).
- **The rebuild (19:34)**, logos without the colours every uniform line shares: in Boston v Montreal and Montreal v
  Boston, Montreal's logo has no stray pixels and Boston's has one light-blue and one pink pixel (the first build: 21
  and 19).

## Injuries and NHLPA '93's blood (2026-11-08, for NOSE4Web)

NOSE4Web plans to bring '93's head blood into '94 (Genesis). Read from both ROMs and the '94 disassembly; seen in play
with `analysis/scoring_map/gen_injury_check.py` (a scratch copy of nhl94.bin patched so every fall of a puck carrier is
an injury, `game` or `period` forced; pad 1 idle) and in the 10 injuries of the recorded league games.
- **'93's frames**: frame table $6FAC2 (650 frames), tile bank $3A382, animation tables from SPAlist $4D8E. The blood
  is small pieces in palette lines 0 and 1 (dark red) in two sets of frames:
  - **633-644**, the "injured on the ice" frames (in '94 the same drawings are 641-652, SPFinjury1, after the 8 flip
    frames '94 added at 633, redrawn without the blood). '93's check injury ($102E2) always plays this animation
    (SPA $1616, frames 273-275 / 289-291 then 633-638 or 639-644, the last held -900), and its injury routine
    ($10332) always sets the player's status to $FFFD (out for the period): '93 has no game injuries, so every
    check injury bleeds.
  - **371-376**, the end of the fight loser's fall (SPA $10CE: 368-370, then 371-376, the last held -400). '93's fight
    code ($A7F2) draws a random number below $3C against a rating byte (+$75) of one fighter: under it, this bloody
    fall, the injury routine and then status $112C; over it, the plain fall (SPA $10AC: 368-370, held 200). The
    fight frames 354-370 and their tables ($5D1C-$5E5C) are fights' alone.
  - How long: the animation times count 2 a frame, as '94's. A check injury's blood shows from 21 frames after the hit
    and its animation lasts 509 more frames (21 game seconds), longer than the play stays on screen (in '94 the
    penalty scoreboard comes about 480 frames after the hit). A fight's blood lasts 267 frames (11 game seconds).
- **'94 in play**: every injury starts SPAinjuryfall ($145C: 273-275 or 289-291, the last held 1024). setInjuryType
  sets sflags7 bit 5 (the byte at $C2FC) for a game injury and clears it for a period injury; only a period injury
  goes on to SPAinjury1 ($1AF4: from 641 or 647, writhing 644-646 or 650-652). Seen: a game injury lies still on 275
  from 20 frames after the hit until he is taken off 530 frames after it; a period injury writhes 641-646 from 50
  frames. Both: the referee box, then "Injury to ... Out for game / period", then the penalty scoreboard (roughing,
  or $14 when the hitter is a goalie or penalties are off), then the faceoff. The recordings: 10 injuries, all period
  ones, all SPAinjury1.
- **'94's frames 353-376** (gloves, fight, fight injury) all point to one placeholder piece (tile 3749, one pixel). No
  animation table in '94 uses 353-376, and no code sets them (the two immediates 360 and 368 in the code are a timer
  and a screen window). Their HotList entries (stick points) are still there (369 (-22, -1), 370 (-32, -4), 371-376
  (-24, -4)) but are read only for a frame a player is showing. Filling 369-376 can't change play until a table uses
  them. To bleed like '93: the period injury could get blood on 641-652 (SPAinjury1 is used only by injuries); the
  game injury's frames 273-275 / 289-291 are every fall back's, so it would need its own frames (369-376 are free)
  and an SPAinjuryfall table pointing at them.

## The xG models' goalie spread refitted (2026-11-08)

Studies 5 and 6 of docs/GAME_VARIABLES_PLAN.md found the models too sure at both ends. `analysis/xg_spread_fit.py`
replays every recorded unblocked attempt with a model price under candidate spreads (the jitter on the emulated
goalie's position, GOALIE_SPREAD, fitted before on seven Genesis games):

| Genesis (928 shots, 199 goals) | log loss | expected | 0-0.1 | 0.1-0.3 | 0.3-0.6 | 0.6+ |
|---|---|---|---|---|---|---|
| 4 (was) | 0.3498 | 204.8 | 17 / 7.6 | 27 / 25.2 | 43 / 43.9 | 112 / 128.1 |
| 6 (now) | 0.3399 | 214.7 | 13 / 8.0 | 27 / 34.6 | 57 / 59.1 | 102 / 113.0 |
| 7 | 0.3388 | 220.0 | 12 / 8.5 | 21 / 36.4 | 73 / 70.5 | 93 / 104.6 |

| SNES (913 shots, 213 goals) | log loss | expected | 0-0.1 | 0.1-0.3 | 0.3-0.6 | 0.6+ |
|---|---|---|---|---|---|---|
| 2 (was) | 0.3762 | 223.6 | 19 / 9.1 | 37 / 24.8 | 30 / 41.8 | 127 / 148.0 |
| 3.5 (now) | 0.3666 | 229.9 | 19 / 9.8 | 36 / 34.9 | 37 / 51.6 | 121 / 133.6 |
| 4 | 0.3677 | 232.2 | 17 / 10.0 | 38 / 37.8 | 40 / 56.6 | 118 / 127.9 |

Genesis 6 takes nearly all of the log-loss gain with less total bias than 7; SNES 3.5 is the minimum. Changed in
tools/xg.py, tools/xg_snes.py and the viewer's ports; season VERSION 31; the library re-converted (from the cached
reads, 5 minutes). tests/xg_parity.py: the SNES 0.65 of its allowance, the Genesis 1.03 at one grid point (Python 0.005,
the viewer 0.013): the 3-sigma normal allowance is too tight where the chance is near 0 (a handful of goals each), and
every other point is inside. Still open: shots under 0.1 score more than the models say on both systems (Genesis 13
against 8.0, SNES 19 against 9.8), and the models' total runs 8% high: something the models leave out (screens,
goalies caught on long shots), not one number. After the refit, studies 1, 5 and 6: the goal difference against the
xG difference 0.88 / 0.90 (Genesis / SNES), finishing luck's spread 1.6 / 1.3 goals a game, the clearly better chances
lost 2 of 25 / 5 of 27; the 0.6+ chances 129 goals / 140.9 expected and 138 / 156.4 (was 14% short, now 8-9%). Study 2
(hot / cold) ran with the old spread; its effects are differences between two runs and change little.

## NOSE4Web's head blood builds, checked (2026-11-08)

nhl94_blood.bin and CDL_Season_12_blood.bin (a league ROM; its blood tiles past $15DE64, tile numbers $8000 and up).
The change: SPAinjuryfall's lists 273, 274, 369 (30), 370 (held) and 289, 290, 371 (30), 372; frames 369-372 are 275
/ 291 with one blood piece in front (palette line 1, colours 12 and 13); the frame table copied to the ROM's end (the
long at Sprites+4, Sprites = $5DE7A: $FFC04 and $1ED184); HotList 369-372 from 275 / 291; addframe2's `ext.l d2 /
asl.l #5,d2` (the tile number signed) now `mulu.w #32,d2`. Checked with `analysis/scoring_map/gen_blood_check.py`
(injuries forced in a scratch copy, as gen_injury_check) and by reading the ROMs.
- **The bytes**: only the listed changes (and on nhl94_blood the boot's ROM check NOP'd, the ROM 2 MB).
- **Frames**: in both ROMs every frame but 369-372 draws exactly as the original's (pieces and tile bytes); 369-372 are
  275 / 291's pieces with the blood piece first; the HotList entries equal 275's (2, 31) and 291's (1, -25). Only
  CDL's blood tiles are numbered $8000 or more, and addframe2 is the only reader of the frame table and tiles
  (Sprites, Spritetiles), so the unsigned read changes nothing else.
- **Game injuries in play** (4 on nhl94_blood, both lying directions twice; 1 on CDL): 273, 274 (or 289, 290), the
  small blood frame 369 / 371 for 30, then 370 / 372 with the larger blood until he is taken off (570-600 frames
  after the hit): the blood at the head, growing, in front of him. No player showed 369-372 in any other animation.
  On CDL the blood piece's tiles are in video memory byte for byte from ROM $1ED124 (tile $C795), as on nhl94_blood
  from $FFBA4 (the Genesis Plus GX state keeps video memory as little-endian words). When the horizontal scoreboard
  comes up the facing turns, and a player lying on 370 was drawn on 372 in one injury (the original's 275 / 291 weren't
  watched there), and the blood comes with the frame; but the side view never showed the lying player (in no
  injury, nor with him moved about the rink), so it wasn't seen there.
- **Period injuries and other falls**: period injuries frame for frame as on nhl94.bin (273, 274, 275 for 30, then
  641-646 or 647-652); every other animation's list is unchanged.
- **Palette line 1, colours 12 and 13**: $004A / $0006 in palfadenew and in the colour memory all through play on
  both ROMs (the colour memory in its 9-bit form 21 / 3), changed only during the game's own fades, the same on
  nhl94.bin.

## McMarkis's 60 frames a second: the computer against itself (2026-11-08, for NOSE4Web)

The original engine runs the game logic at 30 frames a second (d7 = 2 each step); McMarkis's SA-1 build at 60 (d7 =
1). `analysis/scoring_map/snes_60fps_cvc.py`: Montreal at home against Los Angeles, 5-minute periods (the clock held to
5:00), penalties On, No Offside (the option set to 2 when play starts), the computer on both sides, each game's random
seed ($0792 / $0794) set from its number, 20 games per ROM, regulation only, the game's own team stats, each penalty's
number from the buffer at $15DE when it is called and each shot's strength from the players in the boxes ($1624).
Five ROMs: NHL94_Classic.smc and nhl94_2026_classic.sfc (the 32-team SA-1 build with Classic's teams imported) at 60
and at 30 (`--make-30`: a scratch copy whose Gameloop waits for 2 frames, so every step has d7 = 2 as on the original
engine; checked: timestep $0ADB is 2 at every frame, the clock runs as before); retail NHL94.smc and
nhl94_SA1_Original.sfc (the SA-1 build with the original teams, also 60: its gamefps readout $0A98 reads 60).

| Per game, both teams | Classic (30) | SA-1 Classic at 30 | SA-1 Classic (60) | Retail (30) | SA-1 Original (60) |
|---|---|---|---|---|---|
| Goals | 2.95 | 2.00 | 2.40 | 2.25 | 2.30 |
| Shots | 35.5 | 38.1 | 37.1 | 34.2 | 37.5 |
| Saves | 32.6 | 36.1 | 34.7 | 32.0 | 35.2 |
| Body checks | 41.6 | 47.1 | 60.9 | 44.0 | 64.2 |
| Penalties | 2.20 | 1.75 | 2.90 | 2.55 | 3.00 |
| Passes completed / tried | 65 / 117 | 66 / 115 | 63 / 116 | 65 / 116 | 60 / 106 |
| Roughing or Cross Check / injury Roughing ($14) / other penalties | 0.45 / 0.20 / 1.60 | 0.75 / 0.30 / 0.90 | | 0.75 / 0.35 / 1.45 | |
| Even / power-play / short-handed shots | 29.1 / 4.4 / 2.1 | 32.1 / 3.8 / 2.3 | | 26.8 / 4.1 / 3.3 | |

- **The frame rate** (the SA-1 build at 30 against 60): body checks up 30% (47 to 61, z 6.6), penalties up (1.75 to
  2.90, z 2.8); shots, saves, goals and passing the same.
- **The rest of the build** (Classic against the SA-1 build at 30): about 2.6 more shots (z 2.5) and 3.5 more saves
  (z 3.1), 5 more checks (z 2.6), fewer goals (2.95 against 2.00, z -2.3); no more penalties (2.20 against 1.75). Not
  explained here.
- **The whole build against the original** (both team sets): checks up 45-50% (42 to 61; 44 to 64, z 10), penalties
  a little up (2.2 to 2.9; 2.55 to 3.0, z 1.0), 2-3 more shots and saves, goals no different with the original rosters
  (2.25 against 2.30). Passes tried fell with the original rosters (116 to 106, z -3.7), not with Classic's: not
  settled. No fighting penalty in any game.
- **The code**: the computer's decision timers (temp1, the awareness delay; the assignments; asspuckc's chk4shot /
  chk4pass gate) count down by d7, so they run in real time on both builds: the computer doesn't decide more often.
  temp3 and temp4 count down by 1 a step, so they run twice as fast on the SA-1 build. Collisions (checks, the penalty
  rolls with them), the controller reads and steering run every step, twice as often.
- **The penalty rolls** (`analysis/scoring_map/snes_penalty_rolls.py`: each roll's `jsl` sent through a counting stub
  in a scratch copy; on the SA-1 build the stubbed games are identical to the plain ones, on Classic the stubs' extra
  cycles change the games slightly). Classic against the SA-1 build at 30, 20 games each: reached per game / came up a
  penalty / called:

  | Roll | Classic | SA-1 at 30 |
  |---|---|---|
  | Roughing (checkcheck .t2x, a knock-down check) | 41.4 / 12 of 827 (1.45%) / 12 | 46.2 / 15 of 924 (1.62%) / 15 |
  | Interference (checkint, skater and goalie) | 1.9 / 9 of 38 (24%) / 8 | 3.0 / 13 of 59 (22%) / 12 |
  | Charging (checkcheck, no knock-down) | 18.1 / 4 / 4 | 17.5 / 1 / 1 |
  | Hooking / Holding (holdcheck) | 19.6 / 9 / 9 | 20.1 / 2 / 2 |
  | Tripping (Bcheck, under 5) | 1.9 / 0 / 0 | 1.8 / 3 / 3 |

  The rolls come up alike: the code from checkagr / checkint to AddPenalty is the same bytes with the RAM moved, and
  the SA-1 build's multiply (on the SA-1, its own arithmetic unit) masks both factors to 8 bits as the original does
  (read, not measured). The SA-1 build reaches the Roughing roll a little more often (z 2.5), with its extra checks.
- **A mistake made on the way** (corrected above): the original engine's Penalties option is set by menu presses whose
  timing moves with the seed, and 15 of the 20 seeds lost them, leaving penalties Off; the SA-1 build starts on On, No
  Offside. The first comparisons (penalties "five times" higher on the SA-1 build, its extra shots "power-play
  shots") came from those games. The script now sets the option and records what it found (`optpen_found`).
- Limits: the computer against itself, one matchup per team set, regulation only; nothing on how the game feels to a
  person (input and steering twice as often).

## NOSE4Web's SNES team-block colours, checked (2026-11-08)

NHL94_banner_test.smc (Boston's TeamBlockPalettes entry: colours 2-7 greens, 8-14 magentas) against NHL94.smc, with
`analysis/scoring_map/snes_banner_check.py`: the same presses on both and on a scratch copy of the test ROM with
Boston's colours 1 and 15 also changed (red, cyan), for Boston at home (palette 7), Boston visiting (palette 6) and
Boston against Boston: Game Setup, the controller screen, the matchups, the horizontal pause scoreboard, each pause
item's first screen, the player card's team page, and the playoff bracket (New Playoffs, Best of 7).
- The colours are at $D6F5C (0) to $D6F7A (15); colours 2-14 at $D6F60-$D6F79. Retail sets bit 15 on several
  ($94A5 ...); SetColours / SendColours only copy it, and nothing found reads it.
- Only Boston's blocks change (706 pixels a block) on every screen, and the player card's diagonal stripes:
  SetCardTeamColours copies block colours 7 and 8 (palette 7 at home, 6 visiting) to colours $4E / $4F.
- The block's tiles (from video memory, tile base word $2000, map at text-map rows 10-11) use colours 2-15: 2-14
  the fill, 15 the frame (172 pixels a block); never 1. Palette 6's colour 1 is also the menu text on Game Setup,
  the controller screen, the matchups and Edit Lines while the visitors' block palette is loaded, so it must stay
  $6F7B (every retail team has it). The bracket uses neither 1 nor 15.
- Boston against Boston: DrawTeamBlocks writes both palettes and draws both blocks with the palette-6 attribute.
- NOSE4Web's editor now offers colours 2-15 only (their commit 5088278).

## NOSE4Web's SNES photo import freeing replaced photos, checked (2026-11-08)

nhl94_2026_photo_import.sfc (nhl94_2026.sfc with Classic Boston imported into team 1, then Classic Chicago over it,
with photos), by `analysis/scoring_map/menu_shots.py`: every pause-menu Player Card of team 1 against Vegas, and of
Carolina against Vegas (the defaults), on the import ROM and nhl94_2026.sfc; Chicago's cards on NHL94_Classic.smc.
Team 1 is Chicago with 24 players; the six with photos of their own (Belfour, Roenick, Goulet, Larmer, Steve Smith,
Chelios) and the 18 stand-ins are pixel-identical to Classic's (the picture area of each card); no Boston photo, nothing
scrambled. Vegas (both games) and Carolina, both with photos of their own: every card identical to nhl94_2026.sfc.
Seen on the way: team 1's banner still reads BOSTON and its logo is the Bruins' (setup, matchups, scoreboard, team
page), with the Blackhawks' nickname, arena and rating.

## Six Genesis bugs looked for on the SNES (2026-11-08, for NOSE4Web)

From the NHL94SNES disassembly (retail), then the same routines compared instruction by instruction in nhl94_2026.sfc
(McMarkis's SA-1 build), allowing only its moved low RAM (+$6000) and moved code (long calls, jumps, its own table
addresses). None of the six is on the SNES, retail or SA-1:
1. **Rocket pass**: dopass sets a targeted pass's speed from the distance to the lead spot (2/3 of it, held at 64-80);
   the divisions that round (d / 4, d / 5) only set the lead, not the speed. Same in the SA-1 build.
2. **Penalty-shot table**: there is none. PenShotChk returns -1 when the man hit is the carrier on a breakaway, and
   the caller calls PenShot itself. Same in the SA-1 build.
3. **Ghost puck**: wallcollb gives a puck out of the rink pfnc, as on the Genesis, and SetupPenaltyShot doesn't clear
   it; but puckfaceoff2 calls Endfaceoff before SetupPenaltyShot, and every path through Endfaceoff ends at .12,
   `stz pfnc,x` on the puck. Same in the SA-1 build.
4. **Computer goalie pull**: CPgoalie pulls when 1 or 2 goals behind (bmi ahead, beq tied, 3 or more left in), third
   period, 60 or fewer seconds, puck in the attacking half. Same in the SA-1 build.
5. **Blind ring**: checkpuckcoll_ccx's goalie part tests the stick / glove circle of the save frame, and every way out
   of it (in reach or not, over or under its heights) goes on to the 11-unit body box; a skater's missed stick test
   goes on to his body. No distance band gets neither test. Same in the SA-1 build (all 256 instructions).
6. **Crowd bonus**: no sflags8 or anything like it. The SNES raise at 110 dB (CrowdMeterScreen .11, +2 to four hot /
   cold values) is never reached, only the undo; Bcheck has no crowd term. Same in the SA-1 build.
- **The name letters' colours** (NHL94.smc, measured on each screen): PrintTeamSprites draws them with attribute
  $3800 (sprite palette 4), or in the horizontal blocks $3E00 (home, palette 7) / $3C00 (visitors, palette 6). They use
  only colours 15 (the letter, $FFFF) and 1 (the edge). Palette 4 is UnusedSetupSpritePalette ($D715C: colour 1
  $1D47, 15 $FFFF), but on Game Setup setoptions then writes colourbuf+$182 (palette 4's colour 1) = $14A5, so the edge
  is dark grey there; everywhere else (the controller screen, matchups, pause stats pages, the card's team page, the
  playoff bracket, the horizontal pause scoreboard) it is $1D47. On the pause scoreboard, palettes 6 and 7 have colour 1
  $1D47 and colour 15 $FFFF, and PulsePauseSide pulses colour 15 of the pausing side's palette (colourbuf+$1DE / +$1FE).

## NOSE4Web's SNES Import team with logos, checked (2026-11-08)

nhl94_2026_chicago_import.sfc (nhl94_2026.sfc, Classic Boston then Classic Chicago imported into team 1, with logos and
photos) against NHL94_Classic.smc (Chicago at home) and nhl94_2026.sfc, by menu_shots (setup, matchups, the opening
faceoff, every Player Card) and the title screen with its logo list (titleteams $7E:F000) held at team 1 (Classic:
Chicago, 4). Right: the team logo on setup, the card team page and every player card (pixel-identical to Classic);
centre ice at the opening faceoff (Classic's logo; only the visitors' uniforms differ); the score box keeps the build's
Boston logo; the block palette (palette 7) equal to Classic's; all 24 photos and names pixel-identical to Classic's;
Carolina and Vegas (setup, matchups, Carolina's centre ice, all cards) and the default title identical to
nhl94_2026.sfc. Wrong: the banners' name reads BOSTON (setup, matchups, scoreboard, card team page; Classic CHICAGO;
the setup row says Chicago); the title screen's flying puck shows Chicago's logo shape in Boston-like colours (white,
grey, gold), so the title's logo colours come from somewhere the import doesn't write. (The cards' strengths and
overall ratings differ by the game's random hot / cold, not the import.)
- **The rebuilds (4f37d16, 1792846).** The banner reads CHICAGO on setup, the matchups, the scoreboard and the card
  team page; every other team's setup banner is pixel-identical to nhl94_2026.sfc (all 32 cycled). Centre ice at the
  opening faceoff still looks as in Classic. The title: every puck takes its colours from TitlePalette ($9A:CCA9, ROM
  $D4CA9, the same data in retail, Classic and both 2026 ROMs; unpacked to $7F:0000 and sent to CGRAM once in
  TitleScreen .7); LoadTitleLogo ORs each logo pixel with LogoPalBits ($0BED): $60, or $70 when an attribute byte of the
  logo's map has bits $1C set. Classic's Chicago uses $60, team 1 in the build $70, so its colours are CGRAM $70-$7F
  (6B5A 7FFF 4A52 2529 5EF7 025B 0F3F 0000 4CA4 3400 0165 6DA9 009A 0012 05FF 1DD9). After 1792846 the logo's pixels
  (counted in video memory) still leave Chicago's black outline at number 1 (white on the title) and put the tan face
  and dark brown at 7 (black): a white outline round a black face. The Snes9x saved state keeps CGRAM in its PPU
  block at offset 64, big-endian words.
- **Why the title doesn't show the file's numbers (9105301 rebuild, 2026-11-09).** The 2 MB build's LoadTitleLogo
  calls TitleIceColours (NHL94SNES-SA1 `routines/hockey/CenterIcePalette.asm`) after Decompress: when the team's
  IceTitleColours row (16 bytes a team: byte 0 the palette bits $60 / $70, 0 = retail colours; bytes 1-15 the title
  number for each of the logo's own colours) is non-zero, it renumbers every pixel in place through that row and sets
  LogoPalBits from byte 0. CenterIcePalette reads the same byte 0 to pick the rink's own colours (IcePalettes) over
  RinkPalette. In this build the table is at $A0:9CFC (file $101CFC; found from TitleIceColours's `lda.l`, bytes
  48 8A 0A AA BF + address), and the import leaves team 1's row as built: 70 01 01 01 01 04 06 06 05 02 03 03 07 07 07
  07. So the outline (own 7) and own 6 show as 6 (0F3F, gold, 532 pixels) and own 12-15, the face among them, as 7
  (black, 384): a gold outline round a black face. The same row turned the previous build's 3 and 15 into 1 and 7.
  Fix: write the team's row with the title number wanted for each own colour (byte 0 non-zero). Centre ice at the
  opening faceoff is still as in Classic (the same colours in the circle).
- **d02b823 rebuild (09:19).** Team 1's row is 60 01 02 ... 0F; with titleteams held at team 1 the title's logo is
  pixel-for-pixel Classic's in video memory: LogoPalBits $60, $61 (0000) x465, $6A (1DD9) x230, $6D x89 ... every
  number and count equal. Centre ice at the opening faceoff still as in Classic.

## SNES "No interference penalties" in every period (2026-11-09, for NOSE4Web)

NOSE4Web's hack (McMarkis's) turns checkint's last `bmi .rtl` before the roll (a2's impact under 31) into `bra` at
$9E:BAA8 (retail NHL94.smc has no copier header: file $F3AA8; NOSE4Web finds the place by bytes). checkint
then always returns before its roll, whatever the period; PenInterference ($26) is set nowhere else (checkcheck gives
$18 / $1A / $1C / $1E, holdcheck hooking / holding, Bcheck tripping / penalty shot). In play: scratch copies of
NHL94.smc with the roll always passing (`cmp #2 / bcs` at the roll's `bcs` NOP'd), without and with the hack, 4 full
games each by snes_60fps_cvc (penalties On, No Offside): without the hack 8 interference calls (periods 1 / 2 / 3: 1 /
4 / 3); with it none (54 other calls, every period). The forum report (first period only) doesn't hold in retail.

## The same skater twice on one line (2026-11-09, for NOSE4Web)

nhl94_line_dup.bin / NHL94_line_dup.smc: Boston's NLC and Sc1 lines with Adam Oates (roster place 2) at LW and C,
against nhl94.bin / NHL94.smc, by `analysis/scoring_map/gen_line_dup_check.py` and `snes_line_dup_check.py`: line
changes Off and On, Boston by pad 1 (random presses) and by the computer, four game minutes each, every 10 frames of
play Boston's skaters (position, roster place, sprite).
- **On the ice**: both builds dress the line as read, Oates in two objects (LW and C), both drawn, both playing (each
  carries the puck). Then, when the game rebuilds who should be on the ice (SetPlList from the current line), the
  second Oates object finds no position of its own (newpos -1) and leaves: position $FF (SNES $FFFF), no sprite, and
  Boston plays four skaters, without a penalty, until a line change brings a whole line back. Samples with four
  skaters (Genesis / SNES): lines Off, pad 294 of 729 / 303 of 799; lines Off, computer 349 of 664 / 818 of 844 (on
  the SNES from the first faceoff); lines On, pad 0 / 106; lines On, computer 478 of 681 / 0. The originals: never
  under five, never a player twice. No crash or freeze (the clock pauses match the originals'), faceoffs go on.
- **Stats**: by roster place, so Oates's goals, assists and shots count once; team checks equal the players' sum
  (Genesis). Genesis ice time counts each object, so Oates gets double time while both are on (334 and 366 game
  seconds in about 240 played); the LW has no time of his own. The SNES keeps no per-player ice time, and its
  per-player checks ($168E) only work on Classic. Assists (from the code): a touch by the player who is already the
  last touch changes nothing (Genesis logic94, SNES a2touchpuck), so Oates never assists himself; but a Genesis
  one-timer from one Oates to the other shifts the touch list without that check, and the goal code then skips both
  assists (assist 1 equals the scorer), so the player who passed to the first Oates loses his assist.
- **Edit Lines**: shows the line as read (Genesis "Sc1 Line", SNES "Best Line": LW Oates, C Oates), the player list
  has Oates once ("Ice"); picking another player for C works on both.

## NOSE4Web's NHL94SNESVault hacks (2026-11-09, NOSE4Web 0100df7)

NHL94_vault_hacks.smc (retail NHL94.smc, which has no copier header, with the extra attacker fix, ForwardsAndDefenseHack,
ShowMaxBoost, ManualPullGoalie and the computer's pull changed) against NHL94.smc, by
`analysis/scoring_map/snes_vault_hacks_test.py` from the saved state (Montreal on pad 1 at home). The bytes changed are
only the listed ones ($9B:8C96 / $9B:CE78 the extra attacker fix; $9B:8E1A / $9B:CEBA; $9E:D0BF / $9E:FB6E; $9E:D148,
$9E:D150; $9F:9A31 / $9F:FB43; the checksum).
- **ForwardsAndDefenseHack** (SelectLinePlayer: the forward / defence test replaced): every row's list is all the
  team's skaters (listcount 22, from the first after the goalies; retail 8 defencemen or 14 forwards). Every pick on
  every row of line 1 (the Best Line, Line Changes Off) and line 6 (Pen. Kill 1, 4 rows; Line Changes set On in RAM:
  with them Off the editor shows only line 1, so a first run's "line 6" never left line 1). Line 1, 110 picks: no
  player twice, nobody dropped (a pick already on the line swaps, the extra attacker included, through the extra
  attacker fix; retail: the extra attacker picked at LW, C or RW is in the line twice and the replaced player is off
  it). **Line 6: the extra attacker fix misses the extra attacker** on retail and the hack alike: picking the line's
  extra attacker at any of the 4 rows leaves him twice and drops the replaced player. The fix ($9B:CE78) searches
  from the line's first slot + lineslots down, lineslots + 1 slots: offsets 5 (extra attacker) to 0 on a 5-row line,
  4 (the unused RW slot) to 0 on the penalty-kill lines (lineslots 4, lines 6 and 7). A fixed count would cover all:
  `adc #5` for `adc lineslots`, `ldx #6 / nop` for `ldx lineslots / inx`. In play, LD given the line's extra attacker
  (a forward; the old LD became the extra attacker) and C a defenceman off the line: both skate at those positions;
  with the goalie pulled the old LD comes on as the extra attacker (position 6). The editor never edits the extra
  attacker's slot itself.
- **ShowMaxBoost** (CalcAttrib's single-rating path: 100 when the signed hot / cold value r3 is negative): in Edit Lines
  every cell that changed reads 100, and in 11 rating columns the cells match the cold values; unchanged cells read
  as on retail; the team roster the same (GetNameandAttrib). Not shown: a value of -1 (r3 = -1 x 3/4 rounds to 0;
  in play the 8-bit unsigned shift maxes it all the same): 2 of the 22 skaters' cells here (an Agility, a Checking),
  about 1 rating in 28. Overall, Energy, Weight and Handed are untouched (hot / cold value 9, spodds, has no column).
- **ManualPullGoalie** (ChkGoalies .1): L+R (the pad's low byte exactly $30: not with A or X) toggles tmgoalie 0 /
  $FFFF; nothing between whistles (ChkGoalies runs only with the clock going), with tmgoalie $FF00 (pulled by the
  game on a delayed penalty) or with the backup in net (1: only 0 and $FFFF toggle). The pads checked are 1 then 2:
  with both on one team only pad 1 has it (pad 2 alone on a team has it). A sound starts the frame after the toggle
  (louder audio for about 9 frames, none on retail). It is read once a game second (ChkGoalies, every 24 frames), from
  the buttons held then: held 2 / 4 / 8 / 12 / 16 frames it pulled in 1 / 2 / 4 / 6 / 8 of 12 tries; 24 frames 12 of
  12; held longer it toggles again at the next pass (30 frames: 3 of 12 back in; 48: all 12 back in). The pull lasts
  through faceoffs (ReturnGoalies keeps $FFFF).
- **The computer's pull** (CPgoalie: 3 -> 4 goals, $3D -> $79 s): home by the computer, third period, clock held, 60
  game seconds each: retail pulled behind by 1 or 2 at 55 s (not at 65 / 115 / 125, not behind by 3 or 4); the hack
  behind by 1, 2 or 3 at 115, 65 and 55 s (not at 125, not behind by 4). Both still need the puck carried by the team in
  its attacking half.
- **bfbd6a5 rebuild (10:23): L+R on a fresh press, Max Boost on the stored byte.** GetNewPresses' last store
  ($9B:84D8) calls $9B:CEDB: per pad 1 / 2, a new L or R with exactly $30 held sets $1EF0,X = 24, else it counts down
  (once per ReadPads: every game loop, every other frame in play); ManualPullGoalie acts on and clears its pad's
  count. Held 4 to 120 frames: pulled once, 12 of 12 each; 2 frames: 11 of 12 (missed when a game loop took 3
  frames, so no ReadPads during the tap). Backup in net, $FF00, a stoppage: nothing; both pads on home: pad 1 only;
  the sound as before. Ghost presses: none from a whistle (play 677 frames later) or from a pause resumed 120 frames
  after the press; **a press in a pause resumed 30 frames later pulled the goalie 84 frames after the press**: the
  count stops for about 37 frames while play resumes (no ReadPads), so a press in the last part of its count before
  START fires once play runs. In the pause the only extra RAM the press changes is $1EF0 (the stack bytes differ as
  the code differs); a whole-game comparison with retail diverges from the extra cycles alone (as the penalty-roll
  stubs did). Max Boost: Agility 11 and Checking 9 cells at 100 (the two -1s included), no cold value missed, the
  rest as retail. The extra attacker fix is still the old one (penalty-kill lines not fixed).
- **10:34 rebuilds (7163f00, 2dd8ea6).** L+R: the counts are zeroed while paused (sflags bit 0); a press in a pause
  resumed 30 or 120 frames later, or during a whistle: nothing; taps and holds as before (2 frames 11 of 12, 4-120
  frames once, 12 of 12), the rest unchanged. Extra attacker fix (`adc #5`, `ldx #6 / nop`), on NHL94_vault_hacks.smc
  and NHL94_extra_attacker.smc (retail + the fix only): every pick on every row of the Best Line, Scoring 1 (the same
  RAM line, Line Changes Off / On), Pen. Kill 1 and Pen. Kill 2: no player twice, nobody dropped (retail: the line's
  extra attacker picked at LW or C of either penalty-kill line, or LW / C / RW of line 1, is in it twice).
- **A short-handed pull doesn't bring on the extra attacker.** SetPlList fills the team's places from priolist (G, LD,
  RD, C, LW, RW, extra attacker), skipping G when the goalie is out; a team of 5 (short-handed) gets LD, RD, C, LW and
  RW, so the 5th skater is the penalty-kill line's RW slot, which Edit Lines doesn't show (4 rows). In play (the Vault
  ROM, Line Changes and Penalties On, Montreal short-handed on Pen. Kill 2: LD 22, RD 19, LW 3, C 13, RW slot 7,
  extra attacker 6), L+R: the goalie off and roster place 7 on at RW (position 5); place 6 stayed off. The extra
  attacker slot plays only with 6 places to fill (full strength, a penalty-kill line still on after the penalty).
- **Can a defenceman be a line's extra attacker on retail? (code)** Only if the ROM's own line data puts one there.
  The RAM lines are written by LoadTeamLines (from the team data: at the start, setoptions, Restore default lines) and
  by the editor (SetLineSlot / SwapLineSlots), which writes slot offsets 0-4 only (lineslots 5 or 4) and swaps only
  among LD / RD or the forward slots, never the extra attacker's. On the ice the extra attacker's stand-in
  (SetPlList's sublist .center) comes from the C, LW and RW slots of the lines, which the retail editor fills from the
  forward list. No PP or PK path.

## The SNES lines as loaded (LoadTeamLines; 2026-11-09)

A SNES team record's word at +6 points to lines 2-8 (Scoring 1 ... Pen. Kill 2, 7 x 8 bytes: goalie, LD, RD, LW, C,
RW, extra attacker, 0; values roster place + 1); line 1 (no line changes) sits 8 bytes before. LoadTeamLines copies
the 7 lines to RAM and, with Line Changes Off, copies line 1 over Scoring 1; Edit Lines then shows it as Best Line.
Retail Toronto, checked in the game: Best Line LD Gill, RD Ellett; Ken Baumgartner (place 16, the last of the 14
forwards, so in the forward lists) at RD on Scoring 1, Pwr. Play 1 and Pen. Kill 2.

## The Genesis one-timer assist bug (2026-11-09, for NOSE4Web)

onetimershot (onetimer94.asm) pushes the shooter onto his team's touch list (tmtouch1 / 2 / 3, team struct +$18 /
+$1A / +$1C: the scorer and the two assists) with three moves at $F6CE4, without a2touchpuck's checks (already the
last touch: no change; tmflast, set by puckglue when the other team takes the puck: overwrite, no shift; a second
assist equal to the new last touch: cleared). puckstick's one-timer branch doesn't call a2touchpuck, so an ordinary
one-timer counts once; but when the receiver's stick has touched the pass first (a touch, not a catch: a2touchpuck
makes him the last touch) and the one-timer then fires, the list reads shooter, shooter, passer, and the goal code
(assist 1 = scorer: stop) credits no assist. In the recorded Genesis games, 3 of 71 one-timer goals have no assist
although a teammate's pass made them; the recordings' touch words show that sequence in all three (DAL-BOS P3 2:16:
6 11 2 -> 11 6 -> 11 11 6; HFD-EDM P3 1:30: 20 5 0 -> 5 20 0 -> 5 5 20; BOS-VAN P1 3:40: 18 0 -> 11 18 0 -> 11 11 18).
The fix (`analysis/scoring_map/gen_onetimer_assist_test.py`): at $F6CE4 a jsr to 42 bytes of a2touchpuck's list
update (code at $FFB14), NOPs after. In play (the one-timer harness, 24 struck one-timers a ROM, 18 goals): as played
the original and the fix give the same lists and assists; with the receiver made the last touch before the strike the
original gives receiver, receiver, passer and the 18 goals no assist, the fix keeps receiver, passer, the one before,
and credits both. A retail copy with the fix boots and plays once the boot's ROM sum ($300) is off, as in NOSE4Web's
builds.
- **NOSE4Web's builds (5f06405, 11:15), checked** (`gen_onetimer_assist_test.py builds`: each build's changes laid
  over the test ROM; 12 one-timers a ROM, 9 goals): nhl94_one_timer.bin (the 42 bytes at $FFAC6, over the unused ROM
  sum) and nhl94_one_timer_second_assist.bin (a2touchpuck's first shift at $10188 skipped when the player is the
  first assist; the one-timer routine, 48 bytes at $FFADA, with the same test). As played: the same lists and assists
  as the test ROM on both. Receiver touched first: test ROM receiver, receiver, passer and no assists; both builds
  receiver, passer, the one before, both credited. A give-and-go (C, receiver, passer before the pass back): test
  ROM and the one-timer fix alone end receiver, passer, no second assist (the one-timer routine clears a second
  assist equal to the scorer, $FF10 from `st`), the passer credited; with both fixes receiver, passer, C, both
  credited; caught instead of one-timed, the same (test ROM and fix alone lose C, both fixes keep him).
- **Deflection goals with no assist (7 of 9), checked: the game's rule, not a bug.** In six the other team had the
  puck in the last 5 s before the goal (a skater, or the goalie holding it after the first shot: puckgoalie goes
  through puckglue, which clears the other team's assists and sets tmflast); the seventh (BOS-WPG P3 0:38) was a
  solo rush after taking the puck from the other team. The scorer's own rebound keeps the list only when nobody on
  the other team took the puck in between.

## The Genesis line editor's cursor (2026-11-09, for NOSE4Web)

`analysis/scoring_map/gen_line_editor_cursor.py` (retail nhl94.bin, Edit Lines from the pause menu, every slot the
cursor reaches from the first by up / down / left / right; TestList $D5B8, OptLine $D058): with OptLine 0 (line
changes on) LD to RW on lines 0-4 (Sc1 ... PP2) and LD, RD, LW, C on lines 5 and 6 (PK1, PK2); with OptLine 1 LD to
RW of line 0 only. The extra attacker's slot is never reached (LineCursorTable sends a move onto it to the next group
of lines), and the editor has no row for it; the penalty-kill lines' RW slot can't be edited, as on the SNES.

## Edit Lines on the 1-on-1 ROM (2026-11-09, for NOSE4Web's "Edit Lines for fewer skaters")

`analysis/scoring_map/gen_1on1_edit_lines.py` (power-on to play, OptLine $D058 set: 0 on, 1 off, 2 auto; the pause
menu's Edit Lines, item 3, every line with its roster list, and Team Roster, item 8, every rating page and all seven
lines). NHL941on1.bin (C only), NOSE4Web's NHL941on1_edit_lines.bin, and nhl94.bin as the control:

- **NHL941on1.bin:** both screens crash on opening, line changes off or on ("ADDRESS ERROR 00018BD4 0000BF4B:
  EDITOR", and "... ROSTER"). The editor's row loop (stats94 .line, $8646-$8686) looks up every row's roster place
  (the line byte - 1); an empty slot gives -1, and GetPlayerNamePointer (setup94, $18BC8) then walks 65,535 player
  records off the team data into RAM and reads a word at an odd address. Stack at the crash: $8660 (the row loop's
  `jsr $18B6E`), $859C, $8322 ...
- **NHL941on1_edit_lines.bin, line changes off:** Edit Lines shows the one line with C only (Muller), the roster list
  opens and scrolls; Team Roster shows C only on all seven lines (Scoring 1, 2, Checking, PP 1, 2, PK 1 Carbonneau,
  PK 2 Keane) and every rating page; both close back to the pause menu. No crash, no hang.
- **The same build, line changes on:** Team Roster works; **Edit Lines still crashes** as above. The rows per line
  come from LineIconPosTable (x, y, rows - 1 per line, $879E + 6 x line; OptLine set uses the entry before, whose
  count is $879C). The build sets $879C to 0, but the seven line-changes-on counts ($87A2, $87A8, $87AE, $87B4, $87BA:
  4; $87C0, $87C6: 3) still draw 5 or 4 rows from C, into the empty slots. A scratch copy with those seven words 0
  (header checksum redone): Edit Lines works with line changes on, all three pages (Sc1 / Sc2 / Chk, PP1 / PP2,
  PK1 / PK2) C only, the cursor on C of each line (TestList $04, $0C ... $34), every roster list opens.
- B in the select list leaves it up in retail too (not a change).
- **TeamSongs:** only ChooseSong reads it (`movea.l #TeamSongs,a0` at $FE574), in the source and in all 35 Genesis
  ROMs in NOSE4Web's folder (the absolute long searched, and PC-relative leas); RandomSongs has its own `movea.l` at
  $FE57A ($FE658, right after the table), so moving TeamSongs leaves it in place. The EVO ROMs already moved TeamSongs
  (to $181C30) the same way.

## NOSE4Web 6075749 and aaf3864: Edit Lines for fewer skaters rebuilt, and the "looks" build (2026-11-09)

- **2on2_update.bin** (before the rebuild; `gen_1on1_edit_lines.py`): line changes off, Edit Lines (LW and C) works;
  Team Rosters' two penalty-kill lines show LW only (the PK `subq` at $8C82 still there). Line changes on, Edit Lines
  crashes as the 1-on-1 ROM did (its LineIconPosTable counts still 4 / 3). A scratch copy with the seven counts 1 and
  $8C82 4E71 worked both ways.
- **The rebuilds** (NHL941on1_edit_lines.bin, counts 0; 2on2_update_edit_lines.bin, counts 1; both $8C82 4E71),
  line changes off and on: Edit Lines shows C only / LW and C on every line and page (Sc1 / Sc2 / Chk, PP1 / PP2,
  PK1 / PK2), the cursor on those rows only, every roster list opens; Team Rosters shows them on all seven lines,
  penalty kills included, every rating page; both screens close back to the pause menu. The 2-on-2 build also
  reorders the three routines NOSE4Web keeps in the second megabyte ($1E2AF6: the second-assist test, the stats
  routine, the per-player checks count), the same bytes, with all four calls ($1018C, $14134, $1494C, $F6CE8)
  repointed and no other pointer into that area.
- **nhl94_looks.bin** (`gen_looks_check.py`; changes from retail: $17AAD and $FEE2D $50 -> $14, $AC1D 9 -> 8, ten
  puck sprite attribute bytes $A1670-$A16B8 +$40, two IceRinkHor map words $BDEAE / $BDEEE, the boot checksum call at
  $300 NOPed and its routine at $FFAC0 cleared; nothing else calls $FFAC0):
  - Intro: from power-on, no input, each of the EA Sports and High Score screens about 96 frames (1.6 s real) from
    its fade-in to the next screen, against about 294 (4.9 s) in retail; held still 56-66 frames against 256-264.
  - Puck friction: the loose puck put on open ice at 6,000 (12 clean 30-frame runs each): retail keeps 0.99811 a
    frame (1/530), 0.893 a second; the build 0.99618 (1/262), 0.795 (1/256 gives 0.791). The same shift also serves
    a skater with pfdoff set (a pass's receiver, the runaway-speed state), so those skaters glide less too.
  - Puck colours: one retail play state drawn by both ROMs: only the puck's 14 pixels differ (black with a light-blue
    highlight -> dark navy with a light-grey one, the home team's palette line); the shadow unchanged.
  - The fan: the same state's pause screen: one spectator in the left stand of the horizontal arena (the IceRinkHor
    map SetHor draws behind the pause menu and the intermission screens) is green instead of grey; nothing else
    differs.

## Organ songs moved, played; SNES credits and songs; the song format (2026-11-09, for NOSE4Web 5d1ec5e)

- **CDL_Season_12_songs.bin** (TeamSongs copied to $1ED032, 30 rows; only the `movea.l` at $FE574 repointed; rows 0-27
  byte for byte the old ones; RandomSongs and its pointer untouched; the header checksum the only other change).
  `analysis/scoring_map/gen_songs_check.py ROM OUT TEAM ...` sets HomeTeam ($C330, which every ChooseSong caller copies
  to HmTeam) and drives each pick, watching SongNum ($D6C8) and SongIndex ($D6CC): a home goal (slot 3), with the
  clock at 2:00 the faceoff after it (slot 2: the tune plays only in periods 1 and 2, at the first faceoff past half
  the period with a minute or more left, sf3fosong), the next period's start (slot 0; the intermission screens wait
  for a button with $FFF7 still 0, and put the real home team back), the 3rd period at 0:40 (slot 5), and LeadSong at
  a faceoff with tmap set uneven. Tampa Bay (28) picked $34 in every slot; Nashville (29) $40 in slots 0, 2, 3, 5 and
  $60 in 1 and 4. On CDL_Season_12.bin the same runs read RandomSongs' bytes for 28 ($49, $42, $40, $58, $34, $5C)
  and code bytes for 29 ($E7, $48, $66, $C0, $65, $80). Teams 0, 13 and 27 picked the same songs on both ROMs, random
  picks included (team 0's slot 3 and team 27's slots 3 and 5 are 0).
- **LeadSong's slots: the disassembly's names are backwards, the code is right** (logos94): with the home team ahead
  on players the `exg` leaves a3 = the home struct and the `cmpa` picks slot 1 (named SngPPAway); with the away team
  ahead, slot 4 (named SngPP), which holds "Defense" ($5A) for most teams. So slot 1 is the home power play and slot
  4 the home penalty kill, as the SNES disassembly names its own slots. Seen in play both ways (tmap set), and after
  real penalties (below).
- **The power-play songs do play after a real penalty** (`analysis/scoring_map/gen_leadsong_check.py`: a scratch copy
  of the test ROM with checkagr's roll forced to 0, $13E70 -> `moveq #0,d0` / `nop`, penalties on; the home skater
  pokes the away carrier, the trip is called and play runs on). In all three runs the home team went a man short
  (tmap 5 / 6) and the next faceoff picked slot 4 ($5A) with sflags2 bit 5 still clear: the power-play display sets
  that bit only on the frame after. Later calls that left the same team a man up (5 / 6 to 4 / 6, 4 / 5) picked
  nothing: one song per change of which team is ahead, as LeadSong intends. (A first reading, from a test that set
  tmap by hand so the display ran before the faceoff, wrongly suggested the bit blocks them.)
- **SNES credits** (`RollCredits`, `PrintCopyright`, `PrintStringSprites`): CopyrightLines (two zero-ended strings;
  the second found as CopyrightLines+23, an immediate operand, so the first must stay 22 characters or that operand
  change), CreditTitles (17 word pointers, $0000, then the strings) and CreditNames (word pointers in lists ended by
  $0000, one list per title, then the strings), all in bank $80, read by `lda.l CreditTitles,x` / `lda.l
  CreditNames,x` with the bank from `#CreditTitles>>16`, so the strings must share the tables' bank. One block of 993
  bytes, followed at once by TitleSampleList: retail and every 1 MB edit file $62E0-$66C0 ($80:E2E0), nhl94_2026*.sfc
  $6501-$68E1, nhl94snes_2026*.sfc $635B-$673B, nhl94_SA1_Original $64A1-$6881. Letters: A-Z (lower case folded to
  upper by `and #$DF`), 0-9, space, "." and "@" (the copyright sign); anything else indexes LetterWidths wrongly.
  Each string is centred at x 128 as sprites.
- **SNES TeamSongs** (`PlayTeamSong`): six long pointers (4 bytes) per team straight to the song data, by HomeTeam and
  slot ((HomeTeam x 6 + slot) x 4); a pointer whose bank word is negative ($FFFFFFFF) plays one of the 8 DefaultSongs
  (long pointers) at random. Slots (the disassembly): 0 the first faceoff of a period, 1 a faceoff on a home power
  play, 2 other faceoffs, 3 a home goal, 4 a faceoff on a home penalty kill, 5 random in the third period. TeamSongs is
  followed by DefaultSongs, so its room: retail, Classic and SDL16 $80:DA56, 28 teams; nhl94_2026*.sfc $80:DC17 and
  nhl94snes_2026*.sfc $80:DA71, 32; nhl94_SA1_Original $80:DC17, 28.
- **NOSE4Web's SNES song editing, played (01bd4bf, NHL94_songs.smc):** only Boston's row changed (slot 1 $9A:AF99
  Charge [E-flat] -> $96:B6CD, retail's San Jose slot 1, the Jaws Theme; slot 3 $FFFFFFFF -> $99:BB80, retail's
  DefaultSongs entry 2 and Hartford's slots 0 / 5, Brass Bonanza) and the header checksum. `snes_songs_check.py`
  (HomeTeam $1C98 set, the song MusicStart is given read from SongPtr $07ED and EventPtr+2 at $58, cursong $0CC3):
  Boston's home goal plays $99:BB80 (retail: a DefaultSongs pick, $96:8646), the faceoff with a home power play
  (PBnum $01) $96:B6CD (retail $9A:AF99), the penalty-kill faceoff (PBnum $10) and the period's first faceoff
  (percue) $9A:B2DF and $99:9A9C on both; Hartford and San Jose the same on both ROMs. puckfaceoff2 picks slot 1 / 4
  from PBnum ($1624, players in the boxes: home x 16 + visitors), visitors more (a home power play) slot 1, home more
  slot 4; its inline comments call PBnum "score digits" and the slots "behind" / "ahead", which the code doesn't bear
  out (the TeamSongs table's own comment has it right).
- **The Genesis song format** (sound94): a song is an event stream of 4-byte events (the wait in frames before the
  event, 0-255, corrected 2026-11-10: the driver loads the next event's byte 0 after each one, the first at the start; a status byte, command in bits 6-4 and MIDI channel in 3-0; two data bytes), in up to 8 track slots
  of 8 MIDI channels each. Commands: $0x key off, $1x key on (note, velocity 0-127; velocity 0 = off), $3x controller
  (only 7, volume), $4x program change, $6x pitch bend (scaled by the patch's byte $1E); $2x, $5x, $7x ignored; status
  0 ends the stream, or loops to a long pointer. Voices: 5 FM channels, given out per note (a free one or the
  oldest), plus the DAC for PCM patches $60-$6E (13 samples, the game's sound effects). 32 FM patches of 32 bytes,
  read by the Z80 through one bank window. Notes 0-95 (the octave goes in the 3-bit block field). Sounds $00-$7A,
  songs $30-$7A, SoundLast caps the number.

## Assists that disappear (2026-11-09, the user: SNES goals left unassisted after passes, perhaps one-timers)

- **How assists are kept** (both systems, the same design): each team's last three different touchers (SNES tmtouch1-3
  $179A / $179E / $17A2, home / away words; Genesis team struct +$18 / +$1A / +$1C): the scorer and the two assists.
  `a2touchpuck` shifts the list down on a new toucher, unless the team's "next touch overwrites" flag is set (SNES
  tmflags $17DE bit 2, Genesis tmflast: byte +$30 bit 3), when the new toucher replaces tmtouch1 and the flag is
  cleared. An opponent picking the puck up (`puckglue`, the goalie's catch included) wipes the team's two assists and
  sets its flag; faceoffs, goals and a penalty ending set it too.
- **The bug** (code, and the recordings): `a2touchpuck` returns at once when the toucher is already tmtouch1 (SNES
  `cmp.w tmtouch1,y` / `beq .4`; Genesis `cmp.w tmtouch1(a0),d0` / `beq.w .same`), before the flag is looked at. So
  when the last toucher before an opponent's pickup wins the puck back himself, the flag stays set; the teammate he
  then passes to overwrites him instead of pushing him to the assist, and a goal from there is unassisted (or loses
  an assist). Traced frame by frame in all six SNES goals the converter flagged (a completed pass to the scorer
  within 4 s, no assist): each time the passer had been tmtouch1 before the wipe, carried the puck with the flag still
  set, and the receiver's touch replaced him (two were one-timers).
- **How often** (`analysis/assist_loss_study.py`, every recording with a match): SNES 9 of 259 goals (57 unassisted),
  Genesis 8 of 274 (61 unassisted): about one goal in 30, one unassisted goal in seven. (A first count, which
  reset only on the first wipe and not on a second opponent possession, said 10 and 9: one false case each, a goal
  scored alone by a player who got the puck after a second turnover.) Each Genesis case traced too: the re-taker
  (two of them goalies) carried with tmflast still set and the next teammate replaced him. The Genesis clears an
  assist with `st` (a byte), so a cleared slot reads $FFxx (-254, -246 ...), still no assist. The other unassisted goals after
  passes were real changes of possession: the goalie holding it 0.5 s or more (12 SNES goals), a skater holding it
  0.5 s or more (9), or a defender's stick picking it up for 0.1-0.3 s (5), which also clears them.
- **Reproduced on purpose (Genesis, `analysis/scoring_map/gen_assist_repro.py`, the scoring-map test ROM's code and
  state; only the loose puck placed by hand, every pickup, the pass and the goal the game's own):** home A picks the
  puck up (list [A, 11]); away D picks it up (puckglue: [A, -, -], tmflast set); A picks it back up: tmflast stays
  set; A passes to B (B pressed, UP held), B's touch replaces him: [B, -, -], and the puck sent on into the empty net
  is a goal by B, unassisted. The control (another home skater, C, wins it back and passes): [B, C], C's assist. The
  same plays on a scratch copy with the fix (the 8 bytes at $10176 -> `jsr $FFF00` / `nop`; at $FFF00 `cmp.w
  $18(a0),d0` / `bne.s +12` / `bclr #3,$30(a0)` / `move.l #$101A4,(sp)` / `rts`): A's retake clears tmflast, B's
  touch shifts him to [B, A], the goal is assisted by A; the control unchanged (C's assist).
- **NOSE4Web's fixes, played (2140fd9 Genesis, 7fabafa SNES):**
  - Genesis nhl94_regain_assist.bin and nhl94_assist_fixes.bin (the routine byte for byte at $FFAC6 / $FFB0E):
    the regain play credits A (retail: none), the control credits C as on retail (`gen_assist_repro.py`). On
    nhl94_assist_fixes.bin also `gen_onetimer_assist_test.py builds`: one-timers as played 2 assists (as retail),
    "receiver touched first" 2 (retail none), the one-timer give-and-go 2 (retail 1), a caught give-and-go keeps
    the third (retail clears it); 9 goals a case. nhl94_regain_assist.bin alone leaves those as retail.
  - SNES (`snes_regain_assist_test.py`, live play, the scoring summary read at the goal): retail NHL94.smc and the
    2 MB nhl94_2026.sfc: A's retake leaves bit 2 set, B's touch replaces him, B's goal unassisted; the control
    (C the last toucher before the steal) credits A. NHL94_regain_assist.smc and nhl94_2026_regain_assist.sfc: A's
    retake clears bit 2, the goal is B's assisted by A; the control the same as retail. The routine (`CMP
    tmtouch1,Y` / `BEQ +1` / `RTS` / `PLA` / `LDA tmflags,Y` / `AND #$FFFB` / `STA tmflags,Y` / `LDA $A5` / `JMP .4`,
    $9E:FFEB-$FFFF) is right; the `LDA $A5` (d0, the toucher) is harmless but unneeded: .4 begins `LDA #$1000`.
- **Where to fix it:** SNES retail and Classic $9E:C523 (file $F4523; SDL16 $9E:C723, nhl94snes_2026 $9E:C56B; not
  matched in nhl94_2026.sfc or the SA-1 original), Genesis retail and CDL $1017A (the `beq.w .same`, to $101A4). A fix
  clears the flag on the same-player path too and changes nothing else: same player and flag set, clear the flag and
  keep the list; same player and flag clear, as now.

## NOSE4Web's splash screen picture, played (2026-11-09, NOSE4Web fdacede)

nhl94_splash.bin (retail grown to 2 MB; changes: the first High Score picture $F4378 cut to 1 tile at 0,0, the second
at 0,0 and its `movea.l` at $FEE02 pointing to a 40 x 28 picture at $FFAC0: header (palette offset $124A, map offset
$12CA, 146 tiles), the tiles, 64 colours, the size and map, palette rows in map bits 13-14; the boot checksum call
NOPed). From power-on, a screenshot at every change, against retail:
- The picture shows in place of High Score / Mark Lesser, the right way up, for as long (256 frames held), and the
  rest of the start-up (the hockey picture, the title) matches retail, about 70 frames earlier (no checksum loop).
- **Its colours are wrong:** a brown field, a dark ring, a black and light-blue disc. The screen draws its two
  pictures with the routine at $1169A, whose d5 is a bitmask of the 16-colour palette rows to copy from the picture
  (one bit a row): the first call passes $F, the second `moveq #0,d5` ($FEE18) loads none. Retail's High Score
  screen takes its colours from its first picture; here the first picture is still retail's (one tile), so its four
  palette rows are what the new picture is drawn with, and the new 64 colours are never loaded.
- A scratch copy with $FEE18 `moveq #$F,d5` (7A0F): the screen matches the picture decoded from the ROM exactly (the
  same 46 colours, pixel for pixel), the top-left tile and the dark blue field clean.
- Rebuilt (NOSE4Web 7fabafa, $FEE18 7A0F): the same exact match.

## SNES xG for SA-1 games: chunk 1, what it takes (2026-11-09)

- **No SA-1 games recorded yet.** The 31 SNES captures in the game folder are on three 1 MB ROMs (29 on cd85e387); the
  two SA-1 ROM copies there (06edd6c6, 308bd713, Oct 19) have no captures. Every recorded SNES shot has xG.
- **What changes at 60 frames a second** (NHL94SNES-SA1 docs/SA1.md; retail code): the physics scale with the frame
  step d7 (timestep, velstep, gravstep): playeracc multiplies the acceleration by d7, updateplayers' friction comes
  from tables indexed by timestep (.21 / .22), the decision timers count down by d7. What runs per game step, twice as
  often in real time: the AI (assignments: the goalie's rethinks land on finer frame boundaries), input, and the
  collisions (the puck against the goalie's body box and stick / glove areas tested every frame, not every other).
- **The model** (tools/xg_snes.py, the viewer's XG_SNES port) steps puck and goalie STEP = 2 frames, with gravity,
  speeds, friction and timers per frame times STEP, so an SA-1 version is mostly STEP = 1, once each per-step rule is
  checked in the SA-1 code (the goalie's rethink every aidef / 2, pucknorm's crossing countdown every 5 frames, the
  save start under 19 frames, the no-touch timer). xg_calib.py (the game's own shots against the model) can't run on
  the SA-1 build as it is: its SNES states are retail's, and the build keeps low RAM in BW-RAM (snes_60fps_cvc.Mem
  maps it), so a check needs SA-1 states and a shot runner.

## SNES xG for SA-1 games: chunk 2, checked and on (2026-11-10)

- **The code** (NHL94SNES-SA1 against NHL94SNES): assgoalie, doshot, puckgoalie, checkgoal, checkpuckcoll_ccx,
  playeracc, updateplayers, GetHot and GetFrameHot differ only in labels and constants (and PlayerIceTime, PostCount, the
  `d7` energy roll). Every timer the model uses counts by the step: pucknorm's crossing countdown and the goalie's
  rethink (temp1) by `d7`, nopuck and the animation counters (SPAcnt) by `timestep`; updateplayers' friction table .21
  is indexed by it ($FD at 1, $FA at 2). The goalie's hot points (144 frames) and save moves on nhl94_SA1_Original are
  the retail bytes. So the SA-1 game is the retail rules a frame at a time: `xg_snes.play_out(step=1)`.
- **Tools:** `NHL94_SNES_SA1=<ROM>` (paths.py) runs every SNES tool on an SA-1 build: snes_emu routes the moved RAM
  (snes.SA1_MOVED) to BW-RAM, snes_make_states makes its states (period 1 top, period 2 bottom, timestep 1),
  xg_calib's watcher asks the model at step 1. `xg_calib_rescore.py RUN STEP` scores a run again with today's model.
- **The run** (xg_calib.py snes sa1_calib, an hour, nhl94_SA1_Original): 11,787 shots, 716 goals. Re-scored, the
  goalie's spot blurred as for recordings:

  | Shots | Model | Goals | xG | Log loss: model / one rate |
  |---|---|---|---|---|
  | SA-1 (all) | step 1 | 716 | 627 | 0.089 / 0.229 |
  | SA-1 (all) | step 2 | 716 | 640 | 0.089 / 0.229 |
  | Retail: standing, EA, walk-in (xgsnes_all) | step 2 | 169 | 121 | 0.034 / 0.096 |
  | Retail: the user's dekes replayed (xgdeke3) | step 2 | 826 | 678 | 0.413 / 0.637 |

  By kind on SA-1 at step 1: replayed dekes 631 / 558, walk-ins 54 / 29, EA follow-ups 15 / 14, standing 10 / 7,
  dekes 6 / 19. The model is about as right on SA-1 shots as on retail ones (low by an eighth against a fifth); the
  step itself changes little, and step 1 is what the code does. Walk-ins are low on both builds.
- **The game is harder to score on at 60** (the same jobs on both builds): replayed dekes 33.3% retail, 25.9% SA-1
  (22 jobs scored only on retail, 5 only on SA-1), walk-ins 3.9% / 1.7%, EA follow-ups 0.8% / 0.4%, standing 0.2% /
  0.4%. The model sees much of it already in the goalie's state at the release (the dekes: 27% retail, 23% SA-1).
- **On:** add_expected_goals plays SA-1 games at step 1 and marks the match `sa1`; the viewer's XG_SNES takes
  `opts.step` (its map key separates SA-1); tests/xg_parity.py compares both steps.

## NOSE4Web's moved team numbers (2026-11-10, NOSE4Web 603c7fc Genesis, c45dad7 SNES)

Four test ROMs with the first N teams reversed (team k = the original's N - 1 - k): nhl94_teams_moved.bin (26),
CDL_Season_12_teams_moved.bin (24), NHL94_teams_moved.smc (26), nhl94_2026_teams_moved.sfc (32).
- **The ROM data:** every moved team is its original twin (name, abbreviation, roster and ratings, palettes, logo;
  systems' read_teams), the unmoved ones unchanged; the Genesis TeamSongs rows moved; the playoff trees (32 rows of 16
  team numbers, both systems) renumbered right and every team in some tree, so NewPO finds every team (no freeze).
- **On screen** (`analysis/scoring_map/team_move_check.py ORIGINAL MOVED N OUT HOME:VISITOR`: the same presses with
  the teams picked by number, the moved ROM's mirrored): Game Setup (and the Genesis setup cards), the controller and
  matchup screens (the Genesis team ratings), and on the SNES every pause screen at the opening faceoff (player cards,
  stats, Edit Lines, the team card): identical, pixel for pixel, the 12 players' roster numbers the same; differences
  only from timing (the play screen a second apart, the faceoff inset), the random hot / cold draws and the random
  other scores. Organ songs: the same per team (SNES all slots; Genesis the team slots, the random ones random).
  New Playoffs with the first and last teams on both SNES ROMs: the bracket, real conferences, no freeze.
- **Found:** the SNES GetTeamLongName hard-codes teams $0D and $0E as NY Islanders and NY Rangers (their TeamList city
  is "New York"); the moved ROMs still compare 13 / 14 (2026 build: 17 / 18, at $DC5AB / $DC531 in the files), so
  moved team 14 (Montreal) is called "NY Rangers" and 13 (New Jersey) "NY Islanders" on Game Setup, the matchup
  commentary, the timeout menu, the scouting text, other scores, game info and the shootout winner, and the real New
  York teams (12, 11) lose their long names. The All-Stars still clamp to team 25 in NewPO (now Anaheim's place).

## Ron Barr's picture on the matchup screen, measured (2026-11-10, for NOSE4Web's own-picture feature)

`analysis/scoring_map/gen_ronbarr_check.py` / `snes_ronbarr_check.py ROM OUT` (retail ROMs, the matchup screen after
Game Setup; video and colour memory from the cores).
- **Genesis.** ScoutingReport (scout94.asm) draws RonBarrMap ($B389C in nhl94.bin; its `movea.l` at $FCDEE) with
  dobitmap at text cell (1,1), d5 = $C (palette lines 2 and 3 copied). The block: palette at +$4C4, map at +$544, the
  tiles packed (DecompressGraphicsPlain) from +8: 1,212 bytes, 61 tiles (1,952 unpacked); the map 8 x 9 cells (148
  bytes, every word on line 3). Its palette data holds only line 3 (lines 0-2 are $80E filler): line 2 is copied in
  too, then reloaded by the matchup pictures. On screen: tiles 467-527, line 3 only, all 15 colours; nothing else
  shows its tiles. Line 3 is shared: the text frames and boxes (plane A, colours 1, 4, 5, 7) and the SPORTS background
  (plane B, colours 1, 2, 4, 5). Lines 1 and 2 are the home and visitors' pictures and logos, line 0 the font and
  background. The hot / cold icons are loaded right after Ron Barr's tiles (hoticonchars, coldiconchars from d4), and
  the first table above them is the sprite table at tile 1,440: room is not the limit.
- **SNES.** LoadScoutingScreen: BG2 tiles at $1000 words (room for 256), BG1's at $2000. RonBarrTiles (Huffman, 2,944
  bytes packed, $1280 = 4,736 unpacked: 148 tiles) follow MenuBackTiles (backchars 104): tiles 104-251, 4 free before
  BG1's. RonBarrMap (Huffman, 295 packed, $0706 = 1,798: a 6-byte header and 32 x 28 words): 162 non-empty words,
  the announcer at his desk in the bottom right (rows 13-27, columns 6-31 at the widest, row 27); the empty words are
  the screen's frame and text area (BG1 text, BG2 MenuBack frame). RonBarrPalette (LZ, 44 packed, $0100 = 256
  unpacked; only the first 16 colours loaded) to colour row 2, used by nothing else. Row 0: the BG1 font; row 3:
  MenuBackPalette, the BG2 frame and background; rows 4-7: BG1, the team logos and player photos. Only
  LoadScoutingScreen reads the three pieces.

### NOSE4Web's Genesis announcer picture, checked, and the SNES picture's room (2026-11-10, 2e0aedb)

- **Genesis, nhl94_announcer.bin** (`gen_announcer_check.py ORIGINAL NEW OUT`: both ROMs to the matchup screen the same
  way, every matchup page; plane cells, tile data, sprites, colour memory, screenshots). ScoutingReport's movea at
  $FCDEE points at the new block $FFAC0 (palette +$42A, map +$4AA, the word after the header $0021: bit 15 clear,
  unpacked); the map 8 x 9 at cell (1,1), 33 tiles (467-499), line 3. The test picture shows the right way round:
  red top-left, green top-right, blue bottom-left, yellow bottom-right, the white circle in the middle (the grey frame
  is inside the picture's own cells and identical, 590 pixels). Every other cell on both planes has the same map word
  and the same tile data (2,168 cells), and the screenshot outside the picture is the same pixel for pixel. Colour
  lines 0-2 the same; line 3 differs only in colours 8-15 (1-7 kept). The hot / cold icons follow the picture's tiles,
  so they now start at 500 (528 in the original): the 96 tiles from there are the same data in both, and the HOT and
  COLD icons draw correctly on the matchup pages (who gets them differs from run to run: the hot / cold rolls are
  random, and differed between the two ROMs' runs, 85 / 82 for Robitaille).
- **SNES, where a new picture could go** (`snes_announcer_area.py ROM OUT`: the scouting screen sampled every 30
  frames for 60 s (real) from 180 frames in, the text typing and the matchups paging by themselves). BG1 draws only the
  text box there: rows 13-23, columns 1-22 (the box's edges, and the text in rows 14-21, columns 2-20; column 21 and
  row 22 inside it stay empty). Nothing else (no BG2 frame, no sprite) is ever in the bottom right. Free of BG1 at all
  times: columns 23-31 from row 12 down (9 x 16 cells) and rows 24-27 right across. So the largest rectangle a picture
  can fill completely is columns 23-31, rows 12-27 (72 x 128 pixels); Ron Barr himself (162 cells, rows 13-27) also
  runs under the box's right side (columns 19-22 in rows 15-23) and along the bottom (the desk, rows 24-27 from column
  6). BG1 covers him only where it draws (the box's edge in column 22, the letters): in column 21 and between the
  letters his suit shows through the box. (The first 180 frames are the fade-in, and the video memory still holds
  some of the last screen then.)
- **SNES, NOSE4Web's builds (8f5a975: NHL94_announcer.smc against NHL94.smc, nhl94_2026_announcer.sfc against
  nhl94_2026.sfc; `snes_announcer_check.py ORIGINAL NEW OUT`, the scouting screen every 30 frames for 30 s (real) from
  180 frames in).** The same on both: the test picture (red, green, blue, yellow quarters, the white circle) fills
  every cell of columns 23-31, rows 12-27 (144 BG2 cells, palette 2, no flips, unchanged over the samples) and no
  other cell; its tiles 105-126 (22, 129 tiles of BG2's room left; backchars 104 as before). Ron Barr's 66 cells
  outside the rectangle now show the menu background, every other BG2 cell is as in the original, and the menu
  background's tiles are unchanged. BG1 (the box and the text) is the same, and draws nothing inside the rectangle.
  Colour row 2 changes (colours 1-5 the picture's, 7-15 zero, 0 and 6 as before) and is drawn by the picture alone;
  rows 0-1 and 3-7 unchanged. The screenshots outside the rectangle differ only on Ron Barr's old cells (3,171 pixels),
  but for three letters typed a frame apart on the 1 MB build's first sample.
- **SNES, the whole of Ron Barr's area (2026-11-11, for the commissioner via NOSE4Web;** `snes_announcer_area.py` now
  prints his cells row by row; retail and nhl94_2026.sfc the same, but for the 2026 text reaching column 21 in more
  rows). **Nothing shares his tiles, cells or colours:** his 162 BG2 cells use 147 distinct tiles (104-250, his
  alone: no other BG2 cell is on a tile past the menu background's 104) and colour row 2 (his alone). The menu
  background (MenuBack, BG2) fills every other cell and is laid first; his map writes only his own cells, so cells a
  new picture leaves out show the plain background (as on NOSE4Web's builds). **What overlaps him is the text box, on
  the other layer (BG1, the font's tiles, drawn by the scouting text):** it covers rows 13-23, columns 1-22, and of his
  cells it ever draws over 14 (its right edge in column 22 and letters, rows 15-23: his rows 15-23 reach left to
  columns 19-22); 148 are never covered. His rows: 13: 24-25; 14: 23-26; 15-16: 22-26; 17: 23-26; 18: 21-28; 19-21:
  20-29; 22: 20-30; 23: 19-30; **the desk** 24: 15-30; 25: 15-31; 26: 10-31; 27: 6-31 (81 cells, rows BG1 never
  draws in). **Room for a new picture:** any BG2 cells outside the box: columns 23-31 rows 12-23 (108) and rows 24-27
  right across (128), 236 cells; cells under the box show only through its gaps. Limits: **152 tiles** (104-255,
  BG1's tiles start after) and **15 colours** (row 2; 0 transparent). A one-for-one replacement of his 162 cells fits
  (147 tiles now). Moving the box would mean changing where the scouting text is drawn (code), not moving a copy.
- **SNES, NOSE4Web's whole-place builds (e2ba1b1: NHL94_announcer_whole.smc against NHL94.smc,
  nhl94snes_SA1_announcer_whole.sfc against nhl94snes_SA1.sfc; `snes_announcer_check.py`), the same on both:** the
  test picture (a cut-out figure) on 142 BG2 cells, columns 15-31, rows 14-27, fitted in the bottom right of his
  place; 59 tiles (105-163: 92 to spare of the 152), colour row 2 its own (no other cell uses it). Of Ron Barr's 162
  cells none keeps his tiles: those the picture leaves out show the menu background (21 outside the old strip). 3
  cells that were background in the original now carry the picture (inside his 208 x 128 place). The box and its text
  (BG1) unchanged, the menu background's tiles unchanged, the other colour rows the same; the picture stays put over
  all 59 samples (30 s real) as the pages go by. Like Ron, a picture there sits behind the box's right part: the text,
  on BG1, is drawn over it, so a picture's detail in columns 15-22, rows 14-23 would be behind the ends of longer
  lines (on the test picture the head's left edge, about column 16, comes up to the ends of the longest lines; the letters
  stay readable, drawn over it).

## chaos's fighting patch as NOSE4Web puts it in, checked (2026-11-11, d864683: nhl94_fighting.bin, CDL_Season_12_fighting.bin)

Both 3 MB, the menu starting at On. Against their originals (nhl94.bin, CDL_Season_12.bin):

- **The menu** (`gen_menu_compare.py ORIGINAL EDITED OUT [--fourway]`: each Game Setup line's choices cycled with RIGHT,
  the cursor's row compared): every line's caption and choices the same as the original's (retail: Play Mode 4, Players
  5, both team lines 28, Period Length 3, Goalies 3, Line Changes 3; CDL: both team lines 24, Period Length 4; with the
  4-Way Play adaptor Players has 7 on both), the starting Away team aside (picked at random at power-on), and Line Changes
  carrying the "more below" arrow; then Fighting: On, On - Arcade Mode, Off. Penalties cycles Off / On / On, Except
  Off-sides (screenshots). (The first build, before d864683, showed "Home" / "Away" and "Goalie Ctrl" for "Team 1" / "Team
  2" and "Goalies": chaos's own menu.)
- **The title and credits**: the credit roll rebuilt from the row where text enters, frame by frame, the same on both
  (422 rows); the title the same picture.
- **Fights** (`gen_fight_check.py ROM OUT --hot`: the computer against itself, Penalties On Except Off-sides, 5-minute
  periods, every player's fighting rating, +$74, set to 14 in RAM; screenshots while a player has pf2fight, +$63 bit 0):
  retail build six fights in a game (both players a fighting major each, $26 / $28; two instigating minors), the game
  played to its end; CDL build two in the time it ran (into overtime at 3-3). The fight banner ("20 Luc Robitaille LA vs
  26 Gary Leeman MTL"), the referee inset and the gathering play; the scoreboard shows 5:00 Fighting for both. About 23 s
  (real) from the fight flag to the majors.
- **Saved records** (`gen_records_check.py ROM OUT [--names]`: User Records on, a whole game, the save memory read
  after it and after `retro_reset` and a boot to Game Setup; CDL starts at "Two - Head to Head", so Players set to One -
  Home and a name entered): retail original and build both wrote 46 bytes of records, CDL original 30 and CDL build 24
  (different games), and every one was the same byte for byte after the reset (the checksum held, nothing formatted).
- **Rosters**: a Fighting page after Checking on the Team Roster, 0-100 (14 a point: 0, 14, 28, 42 ...); Edit Lines'
  player list pages the same way.
- **Shootout** (Play Mode 4) starts and plays on all four ROMs; **the reverse-angle replay** (pause, Instant Replay,
  START for the banner, C) turns the rink round on all four, and play carries on after.
- **CDL's own changes**: every CDL change against retail is still there, except one routine CDL kept at $1E2B5A (called
  by `jsr`s at $1018C, $1494E and $F6CE8), which NOSE4Web moved unchanged to $1ED032 (free, all $FF before) and
  repointed the three calls to; chaos's save-memory code at $1F9A00 went into free space in CDL too.

## Free work RAM, the fighting setting at $FFF080, blood with fights, overtime until a goal (2026-11-11, for NOSE4Web)

- **Work RAM from $FFE000** (`gen_ram_use_check.py ROM`: a whole computer game with the pause menu and replays, every
  byte from $FFC000 compared with Game Setup's every 4 frames; `gen_ram_tour_check.py ROM [--fights]`: the playoff
  tree, a shootout, the pause menu's screens, fights on the fighting builds): on nhl94, CDL Season 12, DPWM3, GDL Season
  4, IDL5 and RGDL, nothing from $FFE000 to $FFFEBF ever changed; only the stack, from $FFFEC0 up (its deepest).
  So **$FFF080-$FFF081 is free on all of them**, and there's room beside it. (The scoring-map test ROM's hook also uses
  $FFE000-$FFE028, our tool only.)
- **The setting at $FFF080 on CDL** (`gen_fight_setting_check.py ROM CHOICE OUT [--hot]`: chosen on the menu, two
  computer games in a row, every 2 frames): Off, On and Arcade each held through both games; no fights with Off (8
  goals), 4 fights with On, 6 a game with Arcade (with every fighting rating at 14 the fights took the games over: no
  goals). **The plus-minus log** ($FFDEF4): the Off build and the original CDL, same presses and seed, played the same
  games at first and their logs were byte for byte the same at those goals (then the games drifted apart).
- **Fights and head blood** (nhl94_fighting_blood.bin, CDL_Season_12_fighting_blood.bin, injuries forced in a scratch
  copy, fighting ratings at 14): retail 2 fights (3 fighting majors) and 5 injuries, CDL 3 fights (6 majors) and 2
  injuries in the same games; the blood frames (369-372) shown on the injured players (4,898 and 2,576 samples), the
  injury box and the fight banners and dropped gloves as they should be, play going on.
  **The rebuilds (2026-11-12 14:33, after be39649):** blood the same (nhl94 4 injuries, CDL 2, frames 369-372 only in
  SPAinjuryfall); fights with Fighting On and ratings at 14 (`gen_fight_setting_check.py ROM 1 OUT --hot`): nhl94 2 and
  3, CDL 3 and 4 in two games each. Both start at Fighting On. In `gen_fight_blood_check.py` (injuries forced) no fight
  came on either rebuild, even with `--on` (the setting and penalties held on: CDL's extra menu line had left the
  harness's presses setting Penalties Off) and with the injury roll kept (NHL94_INJ_KEEP_ROLL=1): not yet explained.
- **Overtime until a goal** (`gen_ot_goal_check.py ROM`; nhl94_overtime_until_goal.bin, e86d31a: PeriodOver's `move.w
  #4,(gsp).w` at $1725C made NOPs): **not enough on its own.** At the end of a period hockey94's `.eop` ends the game
  itself: `cmpi.w #3,(gsp).w` / `bne` / `tst.w (OptPlayMode).w` / **`beq.s .eog` at $7C4C** (67 C8): in the regular
  season the end of overtime sets gmeog, stops the clock and calls PenEOG ("Stars of the Game"). With only $1725C
  changed, PeriodOver then goes into another overtime with the game marked over, and the intermission's Resume Game never
  resumes (40 presses, 100 s). A scratch copy with $7C4C made `4E71` as well plays on: another overtime (10:00:
  ResetClock's regular-season overtime length, $7818, left as it is), still 1-1; in the playoffs a goal in the extra
  overtime ended the game, as before. **The remade build (51739b3: $1725C and $7C4C both `4E71`, nothing else in the
  game's code changed) works:** a regular-season game tied 1-1 at the end of overtime played three more 10:00 overtimes
  (computer against computer) and ended on a goal, 1-2 with 5:04 left in the third (gsp 4, the game over as usual); the
  playoffs were as on retail (retail: extra 10:00 overtimes until a goal, 1-2 in the third; the build: 1-2 in the
  first). (A score of 3-4 that an earlier check printed was an intermission highlight of another game, not ours.)
- **The SNES builds** (`snes_ot_goal_check.py ROM OUT`; NOSE4Web abba8ad: NHL94_overtime_until_goal.smc and
  nhl94snes_SA1_overtime_until_goal.sfc; clockcont_0's regular-season game-over `beq` made `EA EA`, PeriodOver's
  play-mode `bne` made `bra`, nothing else but the checksum): a game set to overtime with 3 s left at 1-1, computer
  against computer. Retail NHL94.smc: the regular season over at 1-1 (period 4), the playoffs on in 5:00 overtimes until
  a goal. The retail build: three more 5:00 overtimes, then 2-1 and the game over; the playoffs until a goal (2-1). The
  SA-1 build: five more overtimes, then 2-1 and the game over; the playoffs the same.

## A shootout to settle a tied regular-season game (Genesis, 2026-11-11, for NOSE4Web; from the code, not built)

- **How a game ends now** (`PeriodOver`, setup94): after period 3 a tie goes to overtime (gsp 3); after overtime a
  regular-season game (OptPlayMode 0) is over (gsp 4) whatever the score; in the playoffs overtime goes on until a
  goal. `PeriodOver_sp` then: the ticker scores, `Intermission` (the period / game stats screens, and `UpdateRecords`,
  which writes the saved records from the final score), then `GameOver` (EncodePW, the playoff screens) and the title.
- **Shootout mode** (Play Mode 4, gmode2 bit 0; shootout94, shootoutpath94, period94 `EndShootout`): a mode of its own,
  started from Game Setup (forced: line changes, penalties and user records off). `ClearShootout` clears every player
  record (SortCords) and the shootout state; `InitShooters` takes each team's six starters as its shooter list (the
  "Shootout Setup" menu lets people choose five). Each attempt is the penalty-shot machinery (BA_* variables,
  `StartShootoutPath` picks one of seven skate-in paths for a computer shooter, `EndPenaltyShotPlay`). Teams alternate,
  home first; the shooters cycle after five. `CountShootoutGoals`: from round 5 on, after each away attempt, it ends as
  soon as the goals differ (sudden death after five rounds) and `EndShootout` (the winners' celebration); "SHOOTOUT WON
  BY" (`ShootoutWonBy`), then `NextShooter` jumps to `ExitToOpening`: no Intermission, no GameOver, no records.
- **A shootout goal is scored as an ordinary goal** (`Goal`, collide94: the penalty-shot end test, homeshootgoals /
  awayshootgoals + 1, `EndPenaltyShotPlay`, then `.8`): the team's goals (tmscore), the scorer's goals and points, the
  scoring summary and the goal shown; only the penalty-shot-goal count is skipped. Shootout mode gets away with it
  because it starts from cleared stats and never reports a game.
- **Starting one from a tied overtime in the same game** needs: a branch in `PeriodOver` where it now sets gsp 4 for a
  regular-season tie, into a set-up like Shootout mode's (gmode2 bit 0, the shooter lists, the first attempt's
  positions: what `StartGame` / `StartPer` do with gmode2 bit 0 set, without `clearTeamStats` and without clearing
  the scoring summary); the goal code told to count a shootout goal only in homeshootgoals / awayshootgoals (no score,
  no player stats, no summary entry); `NextShooter`'s exit, instead of the title, to: the winner's team score + 1
  (tmscore only), gmode2 bit 0 off, gsp 4, `PeriodOver_sp` (so Intermission, UpdateRecords and GameOver run as for any
  game). Things that could go wrong: shots, saves and shooters' stats from the attempts (the shot and save counters run
  in the attempt code too: to be checked); the stats screen and records showing a plain 3-2 with no goal behind the
  extra one; the pause menu (shootout mode has its own); penalties and line changes (off in Shootout mode; a game's
  settings would still be on); the clock and period display; the playoffs (unaffected: overtime goes on there).
- **The record:** a win for the winner with the score + 1 (3-2), as the NHL does, is what the code can hold: the team
  score is one number; nothing marks the extra goal as a shootout goal, so the saved records and the league's results
  would see a 3-2 win. (Match Viewer would see the score change at the end with no goal in play and could mark it.)
- **Size:** a moderate patch (some 150-300 bytes of new code and five or six hooks), and a careful one to test. **Most
  of the way for almost nothing:** regular-season overtime that goes on until a goal, as in the playoffs (in
  `PeriodOver`, skip `move.w #4,(gsp).w` after `tst.w (OptPlayMode).w`): no ties, one changed instruction, but no
  shootout and an overtime that can run long.

### The first build, played (2026-11-11, NOSE4Web 2776621: nhl94_shootout.bin)

`gen_shootout_check.py ROM OUT tie|playoff|reg|ot|mode4 [--gmdir] [--end] [--cdl]` (the computer on both sides; RAM:
gmode $C2EA, gmode2 $C2FA, shootoutclock $D454, homeshootgoals / awayshootgoals $D574 / $D576, shootoutround $D578,
shootoutteam $D594). The build: $7C4C `4E71`; $1725C `jsr $FFAC6` (tied: gmode2 bit 0, $FFF082 = $FF, ClearShootout,
Create_HotCold_Table for both teams); NextShooter's `jmp ExitToOpening` at $FC4CA `jsr $FFB0A` (with $FFF082 set: +1 to
the team with more shootout goals, `andi.w #$FFF4,($C2FA).w`, gsp 4, forceblack, `jmp PeriodOver_sp`).

- **Into the shootout: works.** A tie at the end of overtime gets the intermission with Start Shootout, then the Shootout
  Mode box, rounds and attempts; the game clock stands at 10:00 and gsp stays 3 throughout (no period can end); the
  shootout clock runs each attempt.
- **No goal can count.** The shootout keeps the overtime period's ends (gmode bit 1, gmdir, set: home attacks down in
  periods 2 and 4), so each shooter attacks the other net from Shootout mode's: home the bottom one, away the top.
  `Goal`'s shootout test takes a home shooter's goal only at y >= 0 and an away shooter's only at y < 0, so every goal is
  thrown out: 0-0 after 120 rounds (240 attempts; retail Shootout mode, computer against computer, scores about one in
  ten), and a puck put into the attacked net during attempts never counted (12 of 12; on retail 5 of 5 did). **Fix:
  clear gmdir when the shootout starts** (`bclr #1,(gmode).w`); cleared in RAM at that moment, the computer scored in
  the first round and the shootout ended in round 5 with Shootout Won By.
- **The end, with gmdir cleared:** two faults. (1) `andi.w #$FFF4,($C2FA).w` clears bits 0, 1 and 3 of gmode2's low byte;
  the game's bits are in the first byte (`btst` / `bset` on memory work on bytes), so gmode2 stays $2B: the intermission
  after the shootout shows the shootout menu again (Start Shootout ...) and START goes to the title (no game-over menu).
  Should be `andi.b #$F4,($C2FA).w`. (2) A shootout goal also goes through `Goal`'s ordinary path (as in Shootout mode):
  the score, the scorer's goals (tmgoals), the goalie's goals against, the overtime goals by period (tmPerGoals +$348)
  and a scoring summary entry ($C472); with the end's +1 a 1-1 game won 1-0 in the shootout finished 3-1. Shots don't
  change (and no saves are kept in the team blocks). Both corrected in RAM (the first byte cleared, the score put back to
  the shootout's start + 1): a final 1-2 and the usual game-over menu (Exit Game, Game Stats, Player Stats, Scoring
  Summary).
- **Unchanged, as asked:** a regulation win (2-1 at the end of the third) and a game leading at the end of overtime
  reach the menus at the same frame as on retail and on the overtime build; in the playoffs no shootout ($FFF082 never
  set) and overtime until a goal; Shootout mode from the menu ends at the title as on retail. (Also: Create_HotCold_Table
  re-rolls both teams' hot / cold tables at the end of overtime; harmless, the game is over.)

### The second build (2026-11-11, NOSE4Web cbff027: nhl94_shootout.bin, CDL_Season_12_shootout.bin)

The start code now also clears gmdir (`bclr #1,($C2EA).w`) and copies both team structs ($C6CE-$CF95) and the scoring
summary's length ($C472) to $FFF084-$FFF74D; the end code (only with $FFF082 set and gsp 3) puts them back, adds the
winners' goal and clears gmode2 with `andi.b #$F4,($C2FA).w`.

- **Retail build: everything as asked.** A tied game went into the shootout, the computer scored (1-0 after round 5;
  in another run after 35 rounds), Shootout Won By, a final 2-1 with only the score changed in the team blocks, gmode2
  clear, the game-over menu, the menus. **The saved records** (User Records on, `--records`): after the shootout win
  the save memory was byte for byte the same as after a 2-1 regulation win (the win counted); a retail 1-1 tie writes
  the ties instead. Regulation and overtime-end wins reach the menus at the same frame as retail; the playoffs play
  overtime until a goal ($FFF082 never set); Shootout mode from the menu runs as before.
- **CDL Season 12:** CDL's computer shooters never score (its own Shootout mode from the menu, on the original ROM, was
  0-0 after 167 rounds: the shooter shoots from centre ice at once, wide; the shootout clock stands at 0:10), so the
  first home shot was put into the net (`--force`): the goal counted (the gmdir fix works there too), the shootout
  ended after round 5, a final 2-1 with only the score changed, then the menus; the fighting setting ($FFF080), OptPen
  and OptLine unchanged. **One gap: the plus-minus log.** After the shootout game the log at $FFDEF4 holds an entry
  (length $000E: the shootout goal logged as a goal), after a regulation win from the same start it is empty: the
  shootout goal counts in plus-minus. Its length word needs saving and putting back too (on plus-minus ROMs).

### The shootout after period 3 (2026-11-11, NOSE4Web 6c951fc: nhl94_shootout_after_period_3.bin, CDL_Season_12_...)

PeriodOver's tie test at $17262 becomes a jsr that runs the shootout's start code (regular season, the end of the
third) and then repeats the test; $1725C and $7C4C original; the end code as before. `gen_shootout_check.py` cases
`tie3` / `playoff3` (the third period with 3 s left at 1-1).
- **Retail build:** a game tied after period 3 went straight to the shootout (no overtime period: the flag set at the
  end of the third), ended 1-0 in the shootout after 58 rounds of computer attempts, a final 2-1 with only the score
  changed, then the menus; **the save memory byte for byte as after a 2-1 regulation win** (User Records on). A 2-1 game
  ended at the same frame as retail; the playoffs went to overtime and a goal (2-1) ended it.
- **CDL build** (one home shot put in, `--force`): the same, a final 2-1, the settings unchanged; **the plus-minus log
  again kept the shootout goal** (length $000E), as on the after-overtime build.

### SNES: free RAM and calling PlayShootout mid-game (2026-11-11, for NOSE4Web's SNES shootouts)

`snes_ram_use_check.py ROM OUT game|shootout` (from the first frame of play: every byte not zero then, or changed
since, through a whole computer game with every pause-menu screen (Instant Replay too), the intermissions and the
screens after it; and a Shootout-mode game from power-on; **correction 2026-11-12:** that run pressed only START, and
with the computer on both sides the shootout's menu waits for a pad's B, so on the 1 MB and SA-1 ROMs it never left
round 0 (only the LoROM 32-team build's went on, and crashed): the Shootout-mode part covered the menu, not a
shootout): never written, runs of $800+:
- **Retail NHL94.smc and NHL94_Classic.smc:** $7E:E68C-$EFFF ($974), **$7E:F033-$FFFF ($FCD)**, $7F:F3F6-$FFFF.
- **SA-1 builds** (nhl94snes_SA1.sfc, nhl94_2026.sfc; the game runs on the SA-1, which sees only I-RAM and BW-RAM):
  BW-RAM free on both: **$40:46F4-$40:5FFF** ($190C; $40:46F4-$47F3 is the end of the moved $37F4-$47F3 block, so
  $40:4800-$40:5FFF, $1800, is the safe part), $40:BFFE-$40:E67B ($267E) and $40:E856 up (bank $41 holds LineSave,
  written when lines are saved: not seen in the tour, keep out). Work RAM $7E:F03F-$FFFF is free there too, but the SA-1
  can't reach it.
- **Calling PlayShootout from PeriodOver** (the disassembly): it is a whole game of its own: StartGame_go (zeroes
  $0AD7-$1A10 and $7E:30F4-$3478, the scoring summary `ScoreSum` $313C included, clears the team stats, reloads both
  teams' lines, re-rolls the other games' scores (InitScores), resets goalie modes, timeouts, `lastperiod` $1EAD,
  `newperiod`, the replay pointer, counts `gamesstarted` $7E:347A), StartPer (its setupice loads the game sound driver
  itself), the pause menu as the shootout's set-up screen, then turns until the two tmscores differ after five rounds:
  the shootout goals are counted in tmscore, so the winner must be read before the saved block goes back. Each turn
  sets gmode itself (gmdir for the away team: no ends problem on the SNES), and gmode ($15D4) is inside the saved
  block. Opening2's path to it sets only the stack, the data bank, the menu music, `jmlvector` and CheckPAL, all already
  in place in a game. PeriodOver can't be re-entered from inside the shootout in practice: every whistle there goes
  through SetPA, which sets `shootoutstop`, and puckfaceoff then ends the turn before its clock-out jump.

### Both choices remade (2026-11-11, NOSE4Web cb1ba29: the plus-minus log's length word kept too)

The start code adds `move.w ($DEF4).w,($F74E).w` after the scoring summary's length ($F74C); the end code puts it back
after the summary, before the winners' goal. All four ROMs:
- **The shootout after overtime (retail):** the checks as for the after-period-3 one, all passed: 1-0 in the shootout
  after 35 rounds, a 2-1 final with only the score changed, the save memory byte for byte as after a 2-1 regulation
  win; regulation and overtime-end wins at retail's frame; the playoffs until a goal; Shootout mode as before.
- **CDL, both choices** (one home shot put in): the plus-minus log's length word back to $0000 after the shootout, as
  after the same game won in regulation (the shootout goal's entry bytes stay past the length, unread); the settings
  unchanged. The after-period-3 retail build again went straight to the shootout (0-1 after 77 rounds, a 1-2 final).
- **$FFDEF4 in the original game** is `PALflag`, its last variable: cleared at power-on and bit 0 set on a PAL console
  (hockey94's start), read nowhere else; zero in all 1,498 recorded snapshots (NTSC). Saving and restoring it is harmless
  on any ROM; on a PAL system the plus-minus log's length word starts at 1.

## NOSE4Web's repeated-checks fix, played (2026-11-11, b03835c: nhl94_repeat_check_fix.bin)

The fix (GENESIS_MECHANICS 7.3): FallDown's pair test at $140A8 becomes `jsr $FFAC6`, NOPs, and the original `rts` at
$140B8 a NOP. At $FFAC6: `cmpa.l (PlayerChked $DEDC).w,a2 / bne`, `cmpa.l (PlayerChking $DEE0).w,a3 / bne`, `tst.w
$5E(a2) / beq` (nopuck and nopuckb both counted out), and only if all three hold `addq.l #4,sp / rts` (leaves FallDown
as the old rts did); otherwise back to FallDown, which records the pair as before. Nothing else changed (the header
checksum, the boot's ROM-sum jsr, the room at $FFAC0 as in NOSE4Web's other builds).

`gen_repeat_check_fix_test.py RETAIL BUILD [N]` (the test ROM and the build laid over it, one process each): the pad-1
skater bursts into an away skater standing still. Moving a player by writing his position leaves the game's y-sorted
object list out of order, and collisions are tested only between neighbours in it (`checkcoll`), so after each move
both are held still 8 frames before the burst.

- **The first check** (the target 2 Weight points heavier: a person's check wraps, always down): the team's checks +1;
  the fall animation ($0DD8) ends 135 frames after the hit, his nopuck (120 at the hit) about 15 frames before that.
- **The same checker again** (still 2 heavier), contact about 30-170 frames after the first hit: the original never
  knocks him down; the build does from the first frame he is out of the fall animation (blocked before that by
  FallDown's own animation tests, nopuck or not), each time +1 check.
- **Equal weights, paired by seed** (the pair recorded by a first heavy check): the build's repeated check knocked him
  down exactly as a fresh pair (PlayerChked cleared) did, 40 of 40 at both approach speeds tried, the original 0 of 40.
  The approach builds enough impact for a sure knockdown, so this shows the repeated pair is now a fresh one, not the
  roll's rate. The check count never rose by more than one in a collision.
- **How long the falls last** (the recorded league games, frames from the hit): knocked down ($0DD8 / $0D26) median 134
  (up to 164-213), upended ($136A) 148: both in FallDown's exclusion list (SPAfallfwd / SPAfallback / SPAflip).
  Into the boards (four animations) about 102, not excluded but inside the 120. **Into the bench ($193E, $1A00, the
  SPAbenchcheck falls near centre ice) 154-157, not excluded**: for the last 35 frames or so the same checker can
  flatten him again. Any other checker already could in the original.
- **Other nopuck settings** (each keeps only the last pair's checker off that man, and only that long): his own pass
  (dopass) or shot (doshot) 16 frames, a faceoff 20, losing the puck to a steal 20 + about half the stealer's
  Stickhandling, a bobble, a puck off his body, a bounce-off or a d-pad turn with the puck 8-10, the goalie 8.
- **One-timers:** FallDown records the pair before its one-timer exits, sets no nopuck there and counts nothing, so a
  one-timer contact can now call FallDown again on later frames; each call exits the same way.
- **The second version (774efea: the bench falls, $193E / $1A00, blocked too)**: everything above unchanged on the
  remade build. But no checker can reach a man in a bench fall in the first place: the check carries him over the boards
  into the bench within 10 frames (x 123 -> 136 at the right boards), and the checker stops at the boards (x 119), 17
  units away, past the 16-unit collision reach, for the whole fall (150 frames). So the extra test never comes into play;
  it does no harm. (The gap suggested from the animation's length alone, before checking where he is during it.)
- **The SNES has no pair block** (its FallDown, `src/routines/collide/FallDown.asm`, goes from the animation tests
  straight to the stumble roll).

## NOSE4Web's open-net one-timer fix, played (2026-11-10, e3de67f: nhl94_open_net_fix.bin)

The fix (from GENESIS_SHOOTING 4.4): shotdiradj's `clr.w d0` at $C5FC -> `moveq #8,d0`, so a one-timer whose
sightline through the goalie misses the net is aimed at the middle, mid-height (the pulled-goalie aim) instead of high
middle. The build's other changes against retail are NOSE4Web's usual ones (the header checksum, the boot's ROM-sum
jsr at $300 NOPed, the sum routine's room at $FFAC0 cleared). `gen_open_net_fix_test.py RETAIL BUILD [N]`: the one-timer
harness (test ROM, and the build laid over it), cross-slot passes at 44, 64, 94 and 124 from the goal line (7 setups:
one at 44 never gave a one-timer), the goalie left where he settled or, just before the strike, put still out of the
sightline (wide of the far post on the goal line, or out in front to the shooter's side); 20 seeds each.

| Goalie at the strike | Aim, retail -> fix | Goals, retail | Goals, fix |
|---|---|---|---|
| In position | 2 / 6 -> 2 / 6 (all 140) | 39 / 140 | 39 / 140 (shot for shot the same) |
| Out wide | 0 -> 8 (all 140) | 78 / 140 (56%) | 120 / 140 (86%) |
| Out front | 0 -> 8 (all 140) | 78 / 140 (56%) | 120 / 140 (86%) |

By depth at the open net (retail -> fix): 44: 15 / 20 -> 20 / 20; 64: 22 / 40 -> 39 / 40; 94: 21 / 40 -> 34 / 40; 124:
20 / 40 -> 27 / 40 (the worked-out table in 4.4: 61 / 58 / 57 / 55% high middle, 100 / 100 / 86 / 73% middle). Computer
shooters weren't played: they reach the same `.setpassdir` with the same d0 (shotdiradj runs for them on every shot,
for a person only on one-timers), so at an open net they now aim at the middle too, and the build changes nothing else
in shooting. In the league's recorded games the high-middle aim came up 14 times on one-timers (8 goals); tonight's
four (2026-11-10) had 1 goal, 1 save, Simpson's over the bar at 18 (VAN-EDM P3 0:17) and Recchi's high and wide.

## Genesis forum hacks, from the code (2026-11-09, for NOSE4Web; not played)

- **Injuries (topic 33962).** FallDown (collide94.asm, the hit code before .22 and setInjuryType):
  - $14440 `bne.w .22` after `btst #gmclock,(gmode)` (the last test before the injury) -> `bra`: never an injury;
    the fall and the knocked-loose puck stay, the crowd sound follows (.22). Safe alone.
  - $14450 `bsr setInjuryType` -> NOPs: the injury animations, the penalty ($12 roughing, or $14 when the hitter is
    a goalie or penalties are off) and Stop4Pen stay, and InjCntDown = 4 still brings ShowInjuryBox 4 game seconds
    later: 'Injury to:' TempPlOffset (left from the last injury or set by the penalty log to a penalized player),
    'Out for period / game' from a stale sflags7 bit 5; the player is not marked out (pf2unav, tmpdst), so he plays
    on. The box needs its countdown removed too (the `move.w #4,(InjCntDown)` after .9).
  - setInjuryType: d0 = the checker's Fgt / 4 (0-3). $14508 `bne.w .not0` (d0 = 0: period); .not0 $14520
    `beq.w .injurygame` (d0 = 3: game); else period, $14536 `beq.w .exit` after chkFgtBit1 (else game). $14536 ->
    `bra` alone: d0 1-2 always period, but d0 = 3 (Fgt 12+) still the game. Every injury the period: $14508 `bne.w`
    -> two NOPs. $14508 -> `bra` with $14520 -> `bra`: every injury the game (right).
- **Hot / cold range (topic 21637).** $F70AD is the low byte of Create_HotCold_Table's `move.w #9,d0` before
  randomd0s, which doubles the range, draws 0 .. 2n-1 and takes n away: **-n .. n-1** (-9 .. 8 in retail, as the
  code's comment says; a first reading here had -(n-1) .. n-1, corrected in play), into all 16 bytes a player. Play
  (AttributeCalc): rating x 5 + the player's first byte / 3 (signed, toward zero), so -2 .. 2 does nothing: **n <= 2
  removes the effect in play** (n = 3 can give -3, a step down). The cards / Edit Lines (cards94 rating code) add each
  rating's own byte, unscaled, so n = 2 still shows 1-2 point changes there; n = 0 or 1 makes every byte 0.
- **No icing (topic 15002).** $1023E `bset #ifok,(iflags)` at the end of a2touchpuck (a player sending the puck from
  his own half arms the icing check) and $102A0 `bset #ifcgl,(iflags)` in PuckIChk (the puck crossed the goal line
  outside the crease width); each -> `bra.s` over its own operand. The call needs both bits. $1023E alone: no icing
  state at all, so no call, and the computer goalie goes out to a loose puck as always (logic94 3740: it stays home
  while ifok is set). $102A0 alone: no call, but ifok still set from the shoot-in to the next touch, so the computer
  goalie still holds back from the puck as for an icing. Either stops the call; $1023E alone is the clean one.
- **B-checks with penalties off (topic 17875).** Bcheck (collide94.asm; CCStart's branch for a hitter in SPAsweepchk,
  the B sweep): with OptPen 0 and a person's checker (pfjoycon) the trip needs randomd0($20 + his Chk - the target's
  Agl, 2 less with sflags8 bit 1 or sflags7 bit 6) >= $18; otherwise straight to the direction test (.checkdir).
  $13FDC `bne.w .checkdir` (penalties on) -> `beq`, $13FE6 `beq.w .checkdir` (not a person) -> `bne`: the roll then
  applies with penalties on to the computer's checker only, and with penalties off to nobody. So with penalties on it
  changes play: the computer's B trips get the roll (about 1 in 4 succeed at Chk = Agl) where retail had none; a
  person's are unchanged. For "penalties off plays as on" alone: $13FDC `bne.w` -> `bra.w` (66 -> 60). No overlap
  with NOSE4Web's weight bug and C-then-B fix ($13D72, CCStart's speed-burst check: the CB check is a body check).
- **Goalie control delay (topic 13512).** bholdtimer ($FFBF06 pads 1 / 2) and bholdtimer34 ($FFBF08 pads 3 / 4, a
  byte each) are set in eight places, NOSE4Web's list: logic94 242-243 (both words $1111 when holdreset runs out:
  $AD04, $AD0A) and six `move.b #$11` (537 / 540 at the B change: $B12F / $B139; .bpress 699 / 702: $B36D / $B377;
  .brel 712 / 725: $B39B / $B3C3); the rest only test and count down (660-692) or swap (273-322). Pads 3 and 4 run
  through doinput with their word swapped into bholdtimer (pad index 0 for pad 3, 2 for pad 4) and each set picks
  its byte by the index, so they keep and reset their own; 2-on-2 is right (they do read pads 1 / 2's goaliemode1 /
  goaliemode2, which aren't swapped). The countdown is `subq.b #1` with `bpl`, so a start of $81 or more clamps to 0
  on the first count (the goalie at once): keep it 1 .. $80; the two words take the value in both bytes.
- **$17012 / $17014 (topics 20230 forum: the puck to the boards).** defaultsprites_0 (setup94, at $16E80; also from
  setoptions) sets the 16 objects from its .list ($16EEE, 20 bytes each: X, Y, Z, frame, attribute, a VRchar step,
  radiusx, radiusy, asslist byte, pflags byte); the puck is object 14 ($17006), and $17012 / $17014 are its radiusx /
  radiusy (5 / 5), set nowhere else. checkcoll copies them to wcradiusx / wcradiusy for checkwallcoll: the side boards
  at 136 - rx, the end boards at 298 - ry, the corner circles shifted the same, and checkgoal's box around each net,
  16 + rx across and 2 + ry deep, inside which the puck meets the posts, the net or goes in. So yes: they move the
  posts and the back of the net with the boards.
- **$F8908 (featured player cards).** The immediate of cards94's `cmpi.w #6,(featuredplayer)`: Game Setup's card
  steps through the first 6 entries of the team's FeaturedPictures list (picture.l, roster index.w; ended by a 0
  long) with no end check. Retail lists hold 6-8 (All-Stars 25); CDL_Season_12's and 2on2_update's hold 26 and CDL
  cycles 11. A count over a team's entries reads the end marker (picture pointer 0) and the data after it. The
  matchups and the player cards (DrawPlayerPicture) don't use the count: they look the player up in the list up to
  its end marker. $FD4B8 is MatchupLineSlots, `dc.b 0,4,3,5,1,2,0,0`: matchup 0 the teams, 1-6 the first line's C,
  LW, RW, LD, RD, G (the forum's $FD4B9 6 bytes); the names are a separate list (MatchupPosNames).
- **2-on-2 Edit Lines fix (2on2_update.bin).** With line changes off (OptLine set) the editor shows line 1 from the
  entry before LineIconPosTable: $82F2 the cursor's first slot (`move.w #1,(TestList)`, 1 LD -> 3 LW); $8375 / $837B
  the cursor's limits (`cmp.w #1` / `#5` -> 3 / 4); $8636 DrawLineIcon's first slot (`addq.w #1,d4` -> #3); $879D that
  entry's slot count - 1 (4 -> 1); $8C6E / $8C76 the Team Roster's line view (`lea 1(a3,d0)` -> 3, the first slot;
  `moveq #4,d1` -> 1, rows - 1; penalty-kill lines one fewer); $86DC-$86F4 the editor's header (LD RD LW C RW) and
  $191D2 PlayerPositionText (the roster rows' names). For any ROM whose used slots are consecutive in LD RD LW C RW
  order (first s, n of them): s at $82F2, $8375 and the lea's byte; s + n - 1 at $837B; `addq.w #s,d4` ($5044 |
  s << 9); n - 1 at $879D and in the moveq; the names of the used slots first. With n = 1 the roster's penalty-kill
  rows would be -1 (a dbf of 65,536 rows): that `subq.w #1,d1` needs skipping too. With line changes On the editor
  still uses LineCursorTable and the 5-row entries (the empty slots selectable).
- **Puck and net sprite pieces ($A1660-$A16F8).** Pieces are 8 bytes: x, y, tile, attribute word (palette, flips,
  size in bits 0-3), in the frame table's order ($9E724), so the forum's 8-byte groups from $A1660 are 2 bytes off
  (each is one piece's attribute and the next piece's x, y, tile). Frames: 393 SPFreplay (the replay marker, 6
  pieces to $A1661), 394 SPFpuck (the puck shadow, object 15; it turns into the siren on a goal), 395 the puck
  (object 14) and 396-404 its flip animation (SPApflip), one piece each ($A1662-$A16B9: $A16B8 is frame 404's
  attribute, part of the puck), 405 the bottom net (object 12, 4 pieces) and 406 the top net (object 13, 2 pieces)
  ($A16BA-$A16E9), 407 SPFGoalie (the goalie's first frame, palette 2 as players: $A16F0 is its first piece's
  attribute). The replay draws the same frames (replay94: the frame words it recorded).
- **The five forum options played** (NOSE4Web 92a30a9; `analysis/scoring_map/gen_forum_options_test.py`, scratch
  copies built as NOSE4Web describes):
  - Injuries (every carrier's fall made an injury): retail 4 injuries in 12,885 frames, by its own type rules; never
    ($14440): none in 43,200 frames; period ($14508 NOPs, getFgtbyte forced to 3, a checker with Fighting 12+): 4 of 4
    period ($FFFD, game bit clear); game ($14508 + $14520): 4 of 4 game ($FFFC). Penalty without the injury
    ($14450 and the countdown's `move.w #4,(InjCntDown)` at $1446A NOP'd): the penalty called (the team's penalties
    +1), the player kept (tmpdst stays $FFFF), no injury box, play on; he lies in the injury pose about 10 s, then
    skates again.
  - Hot / cold range: at the opening faceoff against range 0 (the same game, every byte 0): range 9 / 4 / 3 change 88
    / 49 / 19 working ratings, range 2 none; Edit Lines' player list differs on 5 of its 8 rating pages at every
    range, 2 included (Overall 54 / 55, 51 / 52): no effect in play at 2, still shown.
  - No icing: four long shots from the home half wide of the net. Retail arms the icing every time (iflags 7: crossed,
    the direction, ifok); 6004 and 6002 never (0 or 2), so no call can follow; the two the same in every shot (6002's
    `eor.l d7,d0` changed nothing seen). The goalie played the loose puck on retail and both builds alike, so the
    'goalie stays home' difference didn't show in these shots.
  - B-checks with penalties off ($13FDC `bra.w`): the pad-1 skater skating into the away carrier and poking (B, the
    sweep $0B24), 72 tries each: retail trips 66 with penalties on, 10 off; the option 66 on, 66 off.
  - Goalie control delay at 12 (all eight places): B held without the puck, 32 tries: pad 1 takes the goalie after
    17 frames on retail, 12 on the build (one count a frame). **Pads 3 and 4, played (2026-11-09,
    `gen_pad34_goalie.py`):** the frontend with EA's 4-Way Play adaptor (emu.Emu(fourway=True), the core's device
    $401 on both ports), booted with it so Detect4WayPlay sets FourWayPlay ($D046) and port 2's lines; pads 3 / 4 put
    on the home / away side (cont3team $C32C, cont4team $C32E) with a skater each (c3playernum $C324, c4playernum
    $C326, and the skater's pflags bit 3, without which doinput never runs for that pad); each pad holds B alone, its
    team without the puck, 32 tries: retail pads 1 / 3 18-19 frames, pads 2 / 4 17; the 12 build 13-14 and 12. So
    pads 3 and 4 keep their own timers (bholdtimer34) and the option reaches them as it does pads 1 and 2.
- **Organ songs (topic 11307).** ChooseSong (arena94): SongNum = TeamSongs[HmTeam x 6 + SongIndex] (TeamSongs $FE5B0,
  6 bytes a team in TeamList order, All-Stars included: 168 bytes), and a 0 there = one of the 8 RandomSongs ($FE658)
  at random; nothing in the highlight reel. SongIndex: 0 period start, 1 the away team ahead on players, 2 the
  faceoff (once a period; also the shootout), 3 a home goal, 4 the home team ahead on players, 5 the late-game tune
  (once in the 3rd period). A sound number d0 (0-$7A) plays from SoundStreamTable ($2C648, a long each); $30 and up
  are songs, so $2C708 is entry $30 (music_001, "Go Team Go", Boston's) and the 75 song pointers are $30-$7A ($78 the
  title, $79 the end of a period, $7A the scouting report). Retail ANH 119, 117, 118, 0, 90, 0; BOS 49, 50, 48, 0, 90,
  49 (90 = $5A, music_043, in most teams' slot 4).
- **Intro screens (topic 22589).** $17AAC is EASportsScreen's and $FEE2C HiScoreScreen's (the High Score
  Productions / Mark Lesser picture) `move.w #$50,(seed)`: a count of 4-frame waits (waitx 4, until it goes
  negative), so (n + 1) x 4 frames: 324 frames (5.4 s real) in retail, any button ending it. The count lives in the
  random seed's first word and always ends at $FFFF, so a smaller n changes only the time.
- **Puck friction (topic 22589).** updateplayers (logic94 ~160): on the ice (Z 0) each speed loses itself >> d2 a
  frame: `moveq #6,d2` ($AC10, the 6 at $AC11: 1/64, a skater) or with pfdoff (pflags bit 0) `moveq #9,d2` ($AC1C, the
  9 at $AC1D: 1/512). The puck's pflags start at 1 (defaultsprites_0's list), so it always takes the 9; so does a
  skater with pfdoff (a pass's receiver; the runaway-speed bug, 3.4 of GENESIS_MECHANICS). Nothing else reads them; in
  the air there's no friction.
- **Overall rating (topic 22589).** $19420 PAttribOverallMask ($1FBA000A) and $19582 GAttribOverallMask ($130F000A):
  the high word's bits are the ratings counted; $FAB1C OvrPlayerWgtList and $FAB2C OvrGoalWgtList (16 weights).
  CalcAttrib (cards94): each counted rating adds rating x w / 2 (w - 1 extra adds, then a halving: per rating,
  truncated), Weight (bit 13) and Fighting (bit 6) unweighted if a mask has them (retail's don't), plus the hot /
  cold average; the overall masks are also the key: CalcAttrib compares d4 with each to pick the weight list, so they
  must stay different from each other and from single-rating masks. An editor's Ovr has to mirror those three.
- **Follow-ups (NOSE4Web 93c077e).**
  - DPWM3RegularSeason (11 cards): its FeaturedPictures lists run through the roster (picture.l, roster index) with
    picture 0 for players without a card (entry 6 in every team checked). Game Setup, played: featuredplayer steps
    0-10 and wraps, no crash; an entry with picture 0 draws a garbage picture (the ROM's start unpacked as a picture)
    with that entry's player named; later entries with pictures draw normally. DrawPlayerPicture (player cards,
    matchups) stops at the first picture 0, so the players listed after it get no picture there.
  - TeamSongs in other ROMs: ChooseSong's `movea.l #TeamSongs,a0 / movea.l #RandomSongs,a1 / move.w (HmTeam).w,d0 /
    mulu.w #6,d0` (207C aaaaaaaa 227C bbbbbbbb 3038 xxxx C0FC 0006) finds it: $FE572 in retail and in every 30-team ROM
    here (CDL, IDL, DPWM, RGDL, GDL, 2on2 ...), the table still 28 teams at $FE5B0; EVO (64 teams) has it at $181C30.
    In a 30-team ROM teams 28 and 29 read past it: team 28 the first 6 RandomSongs, team 29 the last two and then code
    bytes ($48, $E7, $C0, $80: the last three above $7A, so no song).
  - AdamCatalyst's overall formula: skater mask $3FBF (bits 0-5, 7-13), goalie $1B0F (0-3, 8, 9, 11, 12); every
    counted bit has a weight of 2 or more (weight index = bit number; his skater 6 (0) is Fighting, not counted).
    Bit 13 (Weight) is in the skater mask, as in NOSE4Web's $3FBA, so Weight adds its raw value (his weight 4 there is
    not used). The masks differ from each other and from single-rating masks. A weight under 2 on a counted bit would
    loop ~65,536 times (dbf from -1 or -2). Scale: PrintOverallRating shows total x 100 / 100 and CalcAttrib clips a
    total of 100+ to 99; his counted skater weights sum to 66 (goalie 62), so on the 0-6 scale a player averaging
    above 3 shows 99 (retail's 40: above 5).


## McMarkis's Classic + 60 fps + Fighting release, from the code and played (2026-11-09, for NOSE4Web)

nhl94snes_SA1.sfc (release 26.11.09.14; source Mhopkinsinc/NHL94SNES-SA1 `src/routines/fights/`, NHLPA 93's fights
ported). The release thread's manual (the author's) agrees with the code below.

- The fight rating (`setplayer`): fightagg = 2 x Fighting + Aggression, capped at 14. Fighting is bits 1-3 of its
  byte (0-7); bit 0 of the same nibble is the handedness bit, so an editor showing the nibble shows 15 / 14 for the
  same Fighting 7 (found by diffing the release with nhl94_SA1_Original). Of the 49 raised players: 10 at 7, 14 at 6,
  25 at 5; every 7 is at the cap whatever his Aggression, a 6 with Aggression 2+, a 5 with 4+.
- Fights On (`checkfight`, `SetInst`): no dice. A hard collision (both impacts 10+, in play, neither locked) fights when
  one player's fightagg >= 8 + max(0, 24 - ChkCnt) / 4 (rounded down: 14 at 0 knockdowns, 13 at 1-4 ... 8 at 21+;
  the manual's table, 0-3 = 14, is one off) and the other's is 2+ and >= 14 - 2 x his own knockdowns since the last
  fight; both ways round. ChkCnt counts knockdowns since the last fight, +3 for one by a player of fightagg 0
  (`FightCountCheck`); a fight clears it and every player's count; a new game starts from 0 (`FightGameStart`).
- After Whistle: the n-th check of a stoppage fights when random((40 - both fightaggs) x 128) < n x 512.
- Who wins (`assfight`, `chkhit`, `FightFall`): each takes energy x fightagg / $1000 punches (at least 5), one per
  landed punch. The computer punches at random within 25 px (high 3/8, low 4/8, grab 1/8); a person with A, B, Y.
  The loser is hurt for the game when random(60) <= the winner's working Aggression. Instigator (penalties on): a
  shoulder check's fighter, else 1 in 4 the more willing one; served by the first teammate on the ice unpenalised.
- NOSE4Web's regained-puck assist fix on this release: site $9E:C58B, `.4` at $C5CD, $9E:FFEB free; played with
  `snes_regain_assist_test.py` on a scratch copy: the release loses the retaker's assist (B's goal unassisted), the
  fixed copy gives it (assist A); the control (a different teammate wins it back) is the same on both.
- The converter reads the fights and the extra stats (PROJECT_NOTES "Fights and the extra stats"); first checked on
  a headless fight from `snes_fight_capture.py` (MTL 19 v LA 11, both majors, called at the fight's start). How often
  fights happen under On and After Whistle is not measured yet (computer games; asked of the user).

## NOSE4Web's title credits editors, played (2026-11-09, Genesis 292693b, SNES 14d040d)

- **Genesis nhl94_credits.bin** against nhl94.bin: Credits / CreditsPages rewritten in place in the original's 934
  bytes ($5776-$5B1B; the rest zero; the copyright page byte for byte), plus only the usual checksum-check removal
  ($301 nops, $FFAC0- freed) and the header checksum. Pages: the copyright page; "NOSE4Web Test League / Season 12,
  2026 / (an empty String) / The Commissioner"; "Tested by / Match Viewer"; "Design adapted by / Michael Brook";
  "Programmed by / Mark Lesser". Played from power-on (menu_shots, a shot every 10 frames): each page scrolls in
  and holds centred (CreditsPrintRow: column $11 - length word / 2, as the original's), the blank line shows as a
  gap, lower case and the comma right; the first two lines of every page sit close in both ROMs (the title's line
  scroll). After page 5 the title ends into Game Setup, as the original does after its last page (TitleScreen
  returns into Opening2); the title, and so the roll, comes back only at power-on / reset.
- **SNES NHL94_credits.smc / nhl94snes_SA1_credits.sfc** against NHL94.smc / nhl94snes_SA1.sfc: only the 949 bytes
  after CopyrightLines (CreditTitles kept at its address, CreditNames moved to just after it: two of the four lda.l
  loads change value), the last terminator on the original's last byte ($66C0 retail, $6881 SA-1), and the header
  checksum. `snes_credits_check.py`: the five titles and their names rest in order and centred (TESTED BY / THE
  COMMISSIONER is the shared string), "@" is the copyright sign, digits and "." right, ADDITIONAL PROGRAMMING (22
  letters, as the original) fits. The roll ends (CreditStep 3) after title 5 at frame ~2990 from power-on; the
  title then sits without credits until its fixed $1284 frames (~3450 frames, 58 s real) end and it fades into the
  menus at ~6500, as the original (whose 17 titles end at ~6250, ~190 frames before). Every frame before the credits
  start (sampled every 3 frames to 1500) is pixel for pixel the original's, the copyright lines (shown only briefly
  in the title's zoom) included. The SNES title, too, plays once per power-on.

## The fourth period length with its own overtime, played (Genesis, 2026-11-09, NOSE4Web 438dec8)

nhl94_fourth_period_ot.bin against nhl94.bin: ResetClock's `tst.w OptPlayMode / bne.w` at $7822 -> `jsr $FFAC6 /
nop` (playoffs: return past the 10:00 load; regular season with Optperlen 3: d0 = 5940 and past it; else back to
it), GetPeriodTime's fourth entry 30 -> 300, both OptionLimits period counts 3 -> 4, the fourth name "5 Minutes, 99
Min OT", the usual checksum-check removal. `gen_ot_check.py`:
- Menu, one pad and 4-Way Play: RIGHT on Per. Length goes 10, 20, "5 Minutes, 99 Min OT" (fits the box), 5, 10.
- Overtime clock in real overtime play: regular season 600 on 5 Minutes, 5940 (99:00) on the fourth; playoffs 300
  on both. A test pitfall: intermission highlights put another game's (or this game's) period, clock and score in
  the same RAM, and the overtime's faceoff resets the clock once more; "in overtime" needs gsp 3, our team ids,
  0-0 and a clock that has run 3 s.
- The clock on the rink and on the pause scoreboard reads right at 98:59, 83:19, 59:59, 19:58, 9:59, 8:19 (after
  83:19), 0:58. A goal at 1:40 left is ScoreSum $D6D0 (OT, 97:20 in: gsp << 14 | seconds, 14 bits).
- A tied 99:00 overtime in the regular season ends the game at 0:00 (Stars of the Game, then Game Setup), as the
  original's 10:00 one (PeriodOver: gsp 4 after overtime unless OptPlayMode).
- From the code: CheckLateGameSong runs in the third period only (overtime length plays no part); puckfaceoff's
  faceoff song needs the clock under half the period (PerTimeTotal / 2), so a 99:00 overtime has none in its first
  49:30 (the original's 10:00: 5:00). PushTime (summaries, team stats) prints minutes 0-99. StartGame's pad-1 $E0
  at game start (Optperlen 3, retail's 30-second periods) now gives the fourth length.

## The Genesis Game Setup screen's video memory (2026-11-09, for NOSE4Web's custom setup background)

`gen_setup_screen.py` on retail, with the logos and with the first player card up:
- Tiles from d4 (LoadSetupTiles starts at 2): team banners $002-$31D (two copies), frame $31E, small font $327,
  setup font $385, GameSetUpMap $3E3-$4D2 (240), visitors' picture $4D3 (36), top strip $4F7, menu box $514, home
  picture $51D (36), logo boxes $541 / $547; the last $54C. Nothing on the screen uses a tile above $54C, and there
  are no sprites. Tiles $600-$76E hold leftovers of earlier screens.
- VDP: plane A $E000 (everything but the background), plane B $C000 (the background, 40 x 28), 64 x 32 planes, the
  window table $B800 but the window off (registers 17 / 18 = 0), sprite table $B400 (tile $5A0), full-screen
  horizontal scroll at $0000 (register 11 = 0: 4 bytes in tile 0), backdrop line 0 colour 0.
- Room: the d4 tiles must end below the sprite table: 83 more ($54D-$59F), so a background of up to 323 tiles
  with the code as it is. Unused but not in d4's run: $5B4-$5FF (after an 80-entry sprite table, and the unused
  window table), $680-$6FF (between plane B's end $D000 and plane A), $780-$7FE (after plane A; $7FF is the blank
  tile).
- Colours, line 0: the background 1-14; setup font 1, 4, 6; frame 4-7; top strip 3-7; menu box 3-6; logo boxes 1,
  3-7 (and line 1 1-6). Only the background uses 2 and 8-15 (the small font's remap, 12 / 15, draws nothing on
  this screen).
- Lines 1-3: GameSetUpMap's palette data holds line 0 and filler for 2 and 3 (d5 = $D loads 0, 2, 3; line 1 not).
  Line 1: the team banners (1-6) and the home logo or the player photo (5-12); line 2: the visitors' logo (overwrites
  it after dobitmap); line 3: GameSetUpMap's filler, drawn with by nothing.
- How much shows: the background's tiles decide 50.0% of the screen's pixels with the logos up, 44.4% with a card:
  besides the open areas, the menu box and the card box are see-through (their tiles' colour-0 pixels), so the
  background shows through them too.

## How often fights happen: Fighting On against After Whistle (2026-11-09, nhl94snes_SA1.sfc)

`snes_fight_rate.py`: 6 games a setting, the computer on both sides (Montreal at home against Los Angeles, the
ROM's defaults; 5-minute periods, penalties On, regulation only; snes_60fps_cvc's seeded games), fights counted from
the fighters' pffight flag:
- **On:** 10 fights in 6 games (1, 3, 1, 2, 1, 2: 1.7 a game), 2 instigator penalties; 54-67 body checks a game.
  Each fight put 3 fighting-major entries in the penalty buffer.
- **After Whistle:** 0 fights in 6 games (62-82 checks a game): the computer doesn't check after the whistle, so
  with After Whistle fights come only from people checking late.
Two teams, the computer only and short periods: a guide, not a league rate.

## Net colours, played (Genesis, 2026-11-09, NOSE4Web 629e033)

nhl94_nets_crowd.bin / nhl94_nets_home.bin against nhl94.bin: only the six net pieces' attribute high bytes
($A16C0-$A16E8 every 8: $00 / $08 -> $20 / $28 crowd line, $40 / $48 home line; the flip bit kept) and the usual
checksum-check removal. `gen_net_colour_check.py`: the test ROMs boot a few frames sooner (no checksum check), which
moves the random seed, so every ROM starts from retail's saved play state: 2400 frames of play and 20 s of instant
replay, each frame compared with retail's. Only a net-sized box differs, in play and in the replay; the puck and its
shadow are pixel for pixel retail's. With the puck put at each end, both nets differ (top and bottom). Crowd line:
an olive-grey net; home line (Montreal at home): a dark navy net with a red frame, heavy against the ice.

## The SNES fourth period length with a 99:00 overtime, played (2026-11-09, NOSE4Web 5560584)

NHL94_fourth_period_ot.smc / nhl94snes_SA1_fourth_period_ot.sfc against NHL94.smc / nhl94snes_SA1.sfc: ResetClock's
`lda.l OptPlayMode / bne .1` -> `jmp $FFE6` + 3 nops (bank $9F), 26 bytes there (`lda.l OptPlayMode / bne -> jmp .1;
lda.l Optperlen / cmp #3 / bne -> jmp lda #300; lda #5940 / sta d0 / jmp .1`; on SA-1 the options at $40:34BC /
$40:34C2), the period count 3 -> 4, GetPeriodTime's fourth entry 30 -> 300, the name "5 Min, 99 OT", the header
checksum. `snes_ot_check.py` (live play, options set in RAM; overtime = period 3, the teams, 0-0, the clock run 3 s):
both builds: regular season 300 on 5 Minutes and 5940 on the fourth length; playoffs 300 on both. The clock second
takes 24 frames on both (the SA-1 build at 60 frames a second: exactly 24 each; retail 22-25 at 60 Hz). A tied
99:00 overtime runs out at 0:00 and the game ends (period 4, then a new game's setup). Menu (screenshots): Period
goes 5 Minutes, 10, 20, "5 Min, 99 OT" and round again on both. Testing note: at 60 frames a second menu presses 4
frames apart can be lost (a wait between presses).

## Knockdowns, holds, injuries and shift energy: a baseline for a "hits cost energy" option (2026-11-09, NOSE4Web)

From the code (both systems): every knockdown goes through `FallDown` (Genesis collide94 :638, a2 down / a3 hitter;
SNES collide/FallDown, a2 down / X hitter), from body checks, the poke trip (`Bcheck`), checkint and a fast high puck
(`puckbody`); a real fall (not a stumble) is Genesis `.cont2`, SNES `.t2`, where the team's checks stat goes up.
Holds and hooks catch in `holdcheck` (once: the held player is then locked). The injury roll: Genesis `randomd0(160)
<= impact`, SNES `randoma8(150) x 2 < impact`, only the carrier falling back facing straight up or down with the clock
running. `PeriodOver` runs once at each period's end on both. Free RAM: Genesis after `PALflag` ($FFDEF4, zero in all
1,498 full snapshots up to the stack at about $FFFE60; cleared at power-on only); SNES retail $7E:F034-$7E:FFFF (zero
in all 31 games); the SA-1 CPU sees only ROM, I-RAM and BW-RAM.

`analysis/knockdown_study.py` (the recorded league games, people against people, line changes off): per game

| | knockdowns (the game's checks) | poke trips | body checks (the rest) | holds caught | hooks caught | injuries |
|---|---|---|---|---|---|---|
| Genesis, 26 games | 50.1 | 8.3 | 41.8 | 1.5 | 10.1 | 0.38 |
| SNES, 29 games | 51.8 | 6.8 | 45.1 | 9.7 | 8.0 | 0 |

(The converter's hits include the poke trips: a hit is any knockdown with a hitter.)

Energy with line changes on, the computer on both sides (`gen_energy_shifts.py`, one 10-minute period;
`snes_energy_shifts.py`, two 5-minute periods; full energy 4096):

| | shift (game s, median) | energy lost a shift | at the shift's end | lost a game second on the ice |
|---|---|---|---|---|
| Genesis | 108 | 971 (24%) | 76% | 8.0 |
| SNES | 60 | 411 (10%) | 89% | 5.4 |

A burst costs 204 on both; the bench gives back 9 a second (Genesis) / 10 a call (SNES).

## NOSE4Web's Genesis hit energy option, played (2026-11-09, 3180527, nhl94_hit_energy.bin: 100 a knockdown, 50 a hold)

The code: `.cont2` ($14116) -> `jsr $FFAC6` (OptLine 0 and sflags7 bit 4 clear, a2 not a goalie, a3 a player
(SCnum <= 11): getpde on a2, -100, setpde, registers saved; then .cont2's own test, a goalie hitter returning to
.chkpos), holdcheck's `move #SPAflail,d1 / bsr SetSPA` ($13F5C) -> `jsr $FFB0E` (-50 on a3, the held player, same
test; then the move and `jmp SetSPA` $1073A, the bsr's own target).
`gen_hit_energy_check.py`: NOSE4Web's 142 changed bytes laid over the scoring-map test ROM (the test ROM's only other
byte there: the replaced checksum routine's own sum), every trial on both copies with the same seed. With OptLine 0
(On): body checks that knocked him down 5, all -100; poke trips 1, -100; holds / hooks that caught 12 (first run 15),
-50 each (one -83: the drain on the ice fires on the video beam position, which the patch's extra cycles can move by
one tick of 33); a fast high puck knocking him down 4, no cost; checks that didn't knock down, no cost. With OptLine 1
(Off) and 2 (Auto): 124 trials each, nothing taken. The team checks stat and the checker's per-player count the same
on both copies in every trial. Not seen in play: a goalie knocked down (CCStart returns for a goalie a2 before any
fall: body checks never knock goalies down) and a stumble (16 soft bumps on a Stickhandling-30 carrier, none; in the
code a stumble branches to `.hitter`, never reaching `.cont2`).

Computer against itself, line changes on (5-minute periods, regulation, 12 games each; `gen_injury_baseline.py`,
`snes_injury_baseline.py`): Genesis no injuries, 22 knockdowns, 25 held / hooked a game, lowest energy median 38%;
SNES 5 injuries (0.42 a game, 2 for the game), 29 knockdowns, 14 held / hooked, lowest energy median 41%.
- Retail against nhl94_hit_energy.bin, the computer against itself (`gen_injury_baseline.py` with the mean energy on
  the ice each second and shift ends added; the same 12 seeds; 5-minute periods, line changes on): mean energy on the
  ice 3656 / 3660 of 4096 (89%), shift ends 88.7 / 87.3 a game, lowest energy median 1574 / 1614, knockdowns 22.4 /
  22.7, held / hooked 24.6 / 20.5, injuries 0 / 2 (the build changes no injury roll: chance; the games go their own
  ways). No measurable change: the option takes about 22 x 100 + 20 x 50 = 3,200 a game against about 85,000 drained
  on the ice (88 shifts of about 970), under 4%.

## NOSE4Web's SNES hit energy option, played (2026-11-09, 41def89: NHL94_hit_energy.smc, nhl94snes_SA1_hit_energy.sfc)

The code (both builds; the SA-1 one with its own addresses: OptLine $40:34C6, position $6F43, getpde $9F:DDC6 /
setpde $9F:DDE7, which start with the SA-1's own `lda $72A3,x` / table, flail $EA06): FallDown `.t2`'s `lda.w
position,x` -> `jsr` (X, Y, a2, d0, d1 saved; OptLine 0 skips; X (the hitter) $18 or more skips (the puck); the faller
a2 a goalie skips; getpde / -100 / setpde on him; `lda position,x / rts`, its flags for the untouched `beq .2`);
holdcheck's `lda #SPAflail` -> `jsr` (-50 on X, the held player, then `lda #SPAflail / rts`).
`snes_hit_energy_check.py`, retail, each trial on both ROMs from the same saved live state: the opponent himself
down from a body check (A) -100 (6 with OptLine 1, 9 with 2) and from a poke (B) -100 (2); held / hooked (Y) -50 (3
and 2); his going into the boards (not in the fall list) also -100; OptLine 0 nothing; the puck and the goalie trials
cost nothing (no knockdown of him seen); the checks stats the same on both in every trial; one -33 (the drain's
timing). The SA-1 build: the placed-player trials froze there (players put in place every frame stay frozen; put
once, no hit came), so `--natural` instead (the computer on both sides, 7,200 frames, each skater going down or
flailing, his energy over 4 frames): original down 0 (6), flail 0 (4); the option build with OptLine 1 down -100 (8),
flail -50 (3); OptLine 2 the same (one -304: a burst of 204 just before); OptLine 0 nothing (14). So the SA-1 code
reaches the moved energy table. Unlike the Genesis, the SNES drains energy with Auto too (the drain and the burst cost
test OptLine for zero), and the option follows it.
- Rebuilt at 204 / 102 (NOSE4Web 6794239's recommended values, up to 1024): retail trials the opponent down 204 (17:
  body checks 15, pokes 2; with OptLine 1 and 2), held / hooked 102 (5), OptLine 0 nothing, counts the same; the SA-1
  build in the computer's own play (OptLine 1) down -204 (13), flail -102 (9), OptLine 0 nothing (14).
- At 204 / 102, the computer against itself (12 games each, the same seeds, 5-minute periods, line changes on;
  Genesis: a scratch copy of nhl94_hit_energy.bin with the two amounts set to 204 / 102, against the retail games
  above; SNES: NHL94_hit_energy.smc against NHL94.smc): shift ends a game Genesis 88.7 -> 101.7 (+15%, 2.3 standard
  errors), SNES 114.5 -> 123.7 (+8%, 1.1); mean energy on the ice 89.3% -> 88.7% and 91.1% -> 90.5% (within the
  spread); the lowest energy anyone reached 1568 -> 1139 and 1573 -> 1207 (means; 1.7 standard errors each);
  knockdowns 22.4 -> 24.1 and 29.2 -> 31.0, held / hooked 24.6 -> 24.2 and 14.2 -> 18.3; injuries 0 -> 2 and 5 -> 2
  (no injury change in these builds: chance). So at a burst's cost the computer changes lines a little more often
  (clearly on the Genesis) and the most-hit skaters get noticeably more tired; the average skater barely changes.

## NOSE4Web's Genesis injury risk option, played and estimated (2026-11-09, 0f3e827)

Builds: nhl94_injury_risk.bin (+2, cap 10, with hit energy 204 / 102), nhl94_injury_risk_strong.bin (+10, cap 60, no
energy). Counts a byte a player at $FFF000 (32 a team, away +32, by pnum), +1 in FallDown's `.cont2` hook (any line
changes), cleared at StartGame (via its `jsr clearTeamStats` at $778C), halved at PeriodOver ($17236); the roll at
$14432 adds min(count x bonus, cap) to impact before `cmp.w impact(a2),d0`. RAM: $FFF000-$FFF03F is zero in all
1,498 full snapshots of 28 recorded games; the plus-minus hack's log runs up from $FFDEF4 (a length word and about 16
bytes a goal), thousands of bytes below.
`gen_injury_risk_check.py` (the builds laid over the scoring-map test ROM, as gen_hit_energy_check.py):
- Counts: each knockdown of the carrier +1, with line changes On and Off (6); holds / hooks (18) and no knockdown
  (66) nothing.
- From power-on: $5A written to $FFF000-$FFF03F at Game Setup read 0 at the first frame of play; 7, 10, 255 set in
  play read 3, 5, 127 in the next period.
- Injuries (the strong build against the unchanged ROM; heavy checker, light carrier, the puck kept on him; 120
  trials a case): the carrier facing straight down (facing 4, the case the game can injure), count 0: injured 7 times
  (unchanged 6); count 6 (+60): 13 times (unchanged 6). On a diagonal (facing 3): never, 45 knockdowns a case, with
  or without the bonus. Testing note: a period injury replaces SPAinjuryfall with SPAinjury1 in the same frame.
- `injury_risk_estimate.py`, the 26 recorded Genesis league games: 1,289 knockdowns, 28 that could injure (1.08 a
  game; impact median 38: about a 27% chance each); the roll's expected 0.29 injuries a game against 0.38 real. Before
  those hits the skater had taken (halved at intermissions) 0 knockdowns 11 times, 1: 6, 2: 5, 3: 4, 4: 1, 7: 1.
  Skaters with 5+ knockdowns in the game take 68% of the injury chance. Bonus / cap -> injuries a game (all), and
  for the 5+ skaters: +2/10 +6%, x1.09; +3/15 +9%, x1.13; +4/20 +12%, x1.17; +5/25 +16%, x1.22; +6/30 +19%, x1.26;
  +8/40 +25%, x1.34; +10/40 +30%, x1.42; +12/60 +37%, x1.52; +15/60 +45%, x1.63; +20/80 +61%, x1.84. (28 hits: rough.)
- SNES (`injury_risk_estimate.py snes`, the 29 recorded league games; the roll randoma8(150) x 2 < impact, the bonus
  assumed added to the impact): 1,350 knockdowns, 47 judged able to injure, expected 0.28 injuries a game, but none
  happened (the computer's own games: 0.42 a game). So the recordings don't pick the SNES's injurable hits out right
  (likely the impact read after the hit, which later collisions add to, or the puck already knocked loose before
  FallDown runs); the relative effects it gives (+2/10 +5%, x1.08; +3/15 +8%, x1.12; +4/20 +11%, x1.16 for the 5+
  skaters) are only indicative. The SNES computer does get injured, so there a computer-vs-computer comparison can
  measure the option directly.
- SNES test, ready for the build (`snes_injury_risk_check.py`; the counts' place an argument, BASE:STRIDE:SIZE): on
  retail, the same trials as the Genesis (heavy checker, light carrier with stickhandling 0 so a weak hit can't make
  him only stumble, the puck kept on him; 144 a case): facing straight down the ice, 94 fell back facing straight and
  27 were injured (the code: FallDown .24, SPAinjury1 $F90E retail replaces the fall in the same frame); on a
  diagonal, 80 knockdowns, none falling back facing straight, no injuries. Its other parts (counts by A / B / Y,
  halving at the intermission, clearing from power-on) run on retail with a stand-in address and wait for the build.

## NOSE4Web's Genesis "any skater at any position", played (2026-11-09, b2606c6, nhl94_any_position.bin)

`gen_any_position_check.py` (the build itself from power-on; Edit Lines from the pause menu, the exit menu's Save /
Load Team Line; save RAM byte X at 2X + 1 of the core's save RAM):
- The list for C and for LW: every skater, roster places 2-24 (23 rows, scrolling); the last (a defenceman) picked
  for C; then picked for LW: the LW's old player went to C (SetLineSlot's swap).
- Save Team Line changed save RAM $1EC0-$1EE1 (the new block: team + 1, then a byte a slot), the old block's team
  byte ($1EF6) and the checksum ($1FFE-$1FFF), nothing else; a pattern planted in the old block's playoff bytes
  (block bytes 18-27, passbits, loaded at boot) was kept. In that save line 0 had a defenceman at C, so the old block's
  line nibbles were left as they were (zeros on a fresh save); the `compat` run below shows they are written when the
  lines fit the old format.
- The other way round (`compat`): line 0's LW and RW swapped (both forwards) and saved on the option ROM, that save
  RAM given to the original nhl94.bin: Load Team Line gives the lines exactly (the old nibbles were written). Then a
  defenceman put at C and saved again: the old block's bytes 0-17 stayed exactly as after the first save, and the
  original loads that earlier, fitting line-up. The one leftover: the old team byte is written even when the nibbles
  aren't, so a team whose first save doesn't fit loads as empty (zero) lines on the original.
- **6a41e01 (the old nibbles written per slot: as the original for a player who fits, 0, the first forward or
  defenceman, for one who doesn't):** played the same way. Saves that fit load exactly on nhl94.bin. A defenceman at
  C loads there as the first forward at C (player 3; the rest as saved). A defenceman at LW with the first forward
  already at RW: the LW nibble is 0 as designed, and the original's load, which places by swapping, brings LW back
  as the player who was at RW before the load (7): no skater twice on the line. On the option ROM every save loads
  exactly (the defenceman at C after a reset; the defenceman at LW too). Save Team Line changes only $1EC0-$1EE1,
  the old block's bytes 0-17 ($1EF6-$1F07) and the checksum; the planted playoff bytes are kept; with line changes
  off the defenceman at C takes the next faceoff.
- With line changes off, back in play: the defenceman (roster place 24) is the record playing C (position 4) and
  lines up for the next faceoff.
- After a console reset and back to play, Load Team Line gives line 0 exactly as saved.
- Lines saved on the original nhl94.bin (LW and RW of line 0 swapped), its save RAM put into the option ROM's before
  power-on: Load Team Line gives them exactly (the new block's team byte doesn't match: the original code runs).

## NOSE4Web's hit option builds: SNES injury risk at +19 and hits after the whistle (2026-11-09, efb691b / 917b991)

NHL94_hit_option.smc (SNES: counts a word a player at $7E:F034, the away team +$40) and nhl94_hit_option.bin
(Genesis), against retail.
- SNES (`snes_injury_risk_check.py`, SPEC F034:40:2): each knockdown of him +1 (A body checks 32 of 32, poke trips 5,
  injuries too), holds / hooks and misses nothing; 7, 10, 255 set in play read 3, 5, 127 in the next period; junk at
  Game Setup reads 0 at the first frame of play. Injuries (heavy checker, light carrier, the puck kept on him, 144
  trials a case): facing straight down the ice, count 0: 27 injured (retail, same seeds: 23); count 5 (the cap): 57.
  On a diagonal: never, with or without the bonus.
- After the whistle (the clock stopped every frame: Genesis gmode $C2EA | $0100, SNES gmclock $15D6 = 1; line changes
  On), trial by trial against the unchanged game (`gen_after_whistle_check.py`, `snes_injury_risk_check.py whistle`):
  clock running, a knockdown costs 204 and counts +1, a hold / hook 102 (Genesis one 69), nothing; clock stopped,
  late hits still knock him down (Genesis 12 of 12, SNES 6) and holds still catch, with no energy cost and no count, on
  both systems.
- **The knockdown counts itself:** on both systems the count goes up where the fall is counted (Genesis .cont2, SNES
  .2), before FallDown's injury roll, so even a player's first knockdown gets one bonus (the SNES count-0 trials: 27
  injured against retail's 23). `injury_risk_estimate.py --self` redoes the estimate with that (the recorded games;
  SNES only indicative): Genesis +10 / cap 50: +54% injuries a game and the most-hit skaters x1.66 (as first
  estimated, counting only earlier knockdowns: +31%, x1.43); +5 / 25: +27%, x1.33. SNES +19 (cap 5 knockdowns):
  +87%, x2.11 (first estimate +52%, x1.77); +10 / 50: +46%, x1.58.
- The commissioner kept the order and lowered the values (NOSE4Web abfd401: Genesis +5 / cap 25, SNES +6, cap 5
  knockdowns; the rebuilt NHL94_hit_option.smc holds 6 / 30). SNES with --self: +4 +18%, x1.23; +5 +23%, x1.29; +6
  +27%, x1.35; +7 +32%, x1.41; +8 +37%, x1.47: +6 matches the Genesis's +5 / 25 (+27%, x1.33).

## One-timers that don't happen: "B pass, C shoot, he just takes the pass" (Genesis, 2026-11-09, a community member)

From the code (logic94 `passmode`, `doinput`; onetimer94 `assonetimer`): B starts pass mode and the puck leaves when B
is released; C starts a one-timer only when newly pressed in a frame with the pass in flight (the passer's pad:
lastplayer him, passReceiverPlayerNum set, onetimerplayer -1, the receiver a skater not on a pad, the puck on the
attacking half; the receiver's pad: the pass not a goalie's, the puck loose and past centre). A C pressed while B is
held, or in B's release frame, is already held once the pass exists. `analysis/one_timer_misses.py` over 26 recorded
games (onetimerplayer $FFBF6C, passReceiverPlayerNum $BEE0, lastplayer $BEDA, c1 / c2playernum $C320 / $C322, pads
$BEEF / $BEF1): the one-timer flag never stayed set past a one-timer's end (471, so nothing "clogs" it); passes by a
pad on the attacking half: C pressed in the sample the pass left 5 of 6 without a one-timer, after it 395 of 411 with
one (16 unexplained), no C 594 without (2 the computer's own). No C held from before the release in these games.
Write-up: GENESIS_SHOOTING 4.8.

## NOSE4Web's Game Setup backgrounds, checked (Genesis, 2026-11-09: nhl94_menu_picture.bin, nhl94_menu_colours.bin)

The picture's address is now read from $F823C (retail $4B7A0; also in CDL's ROM). `gen_setup_screen.py` on retail, both
test ROMs and CDL_Season_12.bin, then `gen_setup_compare.py`:
- Both test ROMs, logos up and a card up: every pixel the background doesn't decide is exactly retail's (cards,
  logos, banners, menu, lettering: 0 differences), and the background shows in exactly the same pixels. Plane B's
  words are the map's words + $3E3 with no palette, priority or flip bits changed. menu_picture: 323 tiles, the d4 run
  ending $59F, the highest tile drawn $59F; it looks like CDL's picture (the ice, red line, NHLPA skater and NHL
  shield), a little simpler. CDL's own: 1,120 tiles from $113 (over the team banners' tiles; drawn tiles up to $7FE).
- menu_colours: 25 bars, each one (line, colour): line 0 colours 0 (the backdrop), 2, 8-15 and line 3 colours 1-15,
  each in exactly its ROM palette word's colour, in both states: the map's line-3 words draw in line 3 as they are.
- Cells (40 x 28) whose background never shows in either state: 132. 64 under the top strip, 44 under the team
  banners (no banner tile of any team has a colour-0 pixel), 6 under the logo box frame: never for any team; 18 at
  columns 8-10, rows 6-11, under the visitors' logo (logos up) and the player photo (card up): never with Los Angeles
  at Montreal and Rob Blake's card, but another logo or photo with colour-0 pixels would show them.

## SNES saves the game doesn't count as shots (2026-11-10, community members: "a shot doesn't count when the goalie catches it"; "SNES clappers right at the goalie, no shot")

**From the code** (collide/checkpuckcoll_ccx, puckstick, puckgoalie, puckglue, puckbody, wallcoll; logic/puck/doshot,
a2touchpuck; penalty/shotstats/ChkShotStat): a shot counts in ChkShotStat only while sf2shot (sflags $15D8 bit
$1000) is set and the clock runs (gmclock $15D6 = 0). doshot sets the flag only when the shooter has the puck.
ChkShotStat runs from puckgoalie's save (before its a2touchpuck), from puckglue when a goalie takes the puck, from
Goal and checkgoal. The flag is cleared without a count by:
- **the goalie's stick, on a fast shot**: checkpuckcoll_ccx checks a goalie's stick first (`.9`, puckstick) and his
  body after it in the same frame (`.3xx: jmp .7`, puckgoalie). puckstick catches a loose puck (puckglue: counted)
  only when its speed is under 10,000 + 3,000 for a goalie (the stickhandling bonus is off while the shot flag is
  set); faster, a goalie always deflects it (`.t1x` -> `.3`: a2touchpuck, then deflect), the flag goes, and the body
  save that follows, or the goalie covering it later, can't count. 85% of recorded SNES slapshots (75 of 88), nearly
  all one-timers (275 of 281) and 43% of wrist shots (256 of 595) are over 13,000;
- any other player's stick (puckstick's deflection) or body (puckbody, within 8) on the way: a2touchpuck;
- a wall, post or the net's frame (wallcoll; the posts through checkgoalp);
- the whistle: after it nothing counts (gmclock).
Also from the code: a goal whose flag was cleared (a deflection) adds a goal and no shot; a shot that touches nothing
keeps its flag, so a goalie covering it much later (or a dump-in he takes cleanly) still counts.

**In the recordings** (`analysis/snes_shot_count_study.py`, the 29 recorded SNES games; the toucher from ltplayer
$30F6, which a2touchpuck writes on every touch): of 512 saves of shots and one-timers, 390 counted. Of the 122 the game
didn't count: **the goalie's stick at over 13,000: 56** (one-timers 27, slapshots 9, wrist shots 20; every goalie-stick
case was over 13,000), a wall, post or the net 31, a defender's stick or body 14, a teammate's 4, the clock stopped
2; and 13 slow "shots" (2,400-8,400) with no doshot behind them (shotplayer stale or empty): passes or pushes the
converter took for shots. Slapshot saves: 18 of 50 uncounted, 9 of them off the goalie's stick.
This is what NOSE4Web's SNES option "Count stick deflections as shots" already fixes (puckstick's `.t1x` calls
ChkShotStat for a goalie; on its recommended list; tested 2026-11-08, "NOSE4Web's sniping, comeback, awareness and
crowd fixes": the same 300 shots on retail 267 -> 297 counted). A ROM without it shows these uncounted saves.
What it looks like (the user, 4 of the listed cases in the viewer): the puck spins right after the goalie gets it,
and it doesn't always look near his stick. deflect gives the puck a random speed (x and y each up to +-4,096, height
speed up to 4,095) and starts puckflip, the puck's spin; a body save's rebound spins too (puckgoalie's .4x), so the
spin means "knocked away, not caught", not always "stick". The stick test (checkpuckcoll_ccx .9) is a box around the
current frame's stick spot as wide each way as the spot is from his centre (often 10-14 units), the puck below about
two thirds of the spot's height, checked before his body: a puck reaching his pads on the stick side can take it.

## Energy, speed and the drain on the Genesis; the SNES sites (2026-11-10, for NOSE4Web's "energy from hits only")

From the code (logic94 playeracc, burst, collide94 makepde; SNES skating/playeracc, burst):
- Genesis speed: level n = floor(floor(legspd / 2) x energy / 4096) (an odd legspd half a step more under level 15),
  the top speed (n + 20) x 275; `andi #$3F` on 4n wraps level 16 to 0. Energy also scales shot power (the shot speed
  factor ShP / 2 x energy / 4096 + 20: for ShP 30 35 at full, 20 at none), stickhandling in steal rolls and the
  no-touch times after a steal (Stk / 2 x energy / 4096), and the burst (energy / 128 added along the facing: none at
  0 energy, so checks hit softer). Pass speed and pass aim don't use energy. Auto line changes (OptLine 2) become On
  with sflags7 bit 4 set, which makes all of these read full energy whatever it is.
- Genesis sites (retail): `.sube` $10D26 (drain: subi #$21 at $10D40, the 33 at $10D42; the endurance / 2 give-back
  while energy >= $C00 follows, with no cap); burst's cost subi #$CC at $BB70 (the $CC at $BB72).
- SNES sites (retail): the drain in playeracc `.5` (only with OptLine nonzero: on or auto): $F2861 ($9E:A861) lda
  seed / and #$003F / bne (1 call in 64), $F286F ($9E:A86F) sec / sbc #$0021 (the 33 at $F2871), then the full
  endurance byte added while energy >= $C00 (so a lower drain can also climb past $1000; there the speed index has no
  mask and runs past MaxSpeed's end); burst's cost $F020B ($9E:820B) sec / sbc #$00CC (the $CC at $F020D), Auto's
  burst speed from a fixed $1000. SNES speed index = legspd x (energy / 2 + $800) / $1000: no energy is half the speed
  index, not none.
- `gen_energy_speed_check.py speed` (test ROM, line changes On, energy held): top speed from a standstill, the code's
  figure in brackets: the median skater (Speed 20, +2 from the home crowd boost in this state: 22) 8,524 (8,525) at
  full, 7,425 at 2/3, 6,325 at 1/3, 5,499 at none; Speed 30: 9,624, 8,239, 6,600, 5,499. At no energy everyone
  skates at 5,500.
- NOSE4Web's drain option with the drain under 8 (`drain` on a copy with the 33 made 0, Speed 30, endurance 30,
  skating up and down for 2 minutes, real): energy $1000 -> $12BE (on the unchanged game $1000 -> $7BA). Straight
  runs: $1111 tops at 9,624, $1112 at 5,499 (the wrap), $12BE 5,760, $1400 6,050. A skater already moving faster than
  his new cap keeps his speed but can't speed up or steer harder (playeracc keeps the old velocity when the new one
  is over the cap) until friction or the boards slow him.

## NOSE4Web's "energy from hits only", played (2026-11-10, 20b3a17: nhl94_hits_only.bin, NHL94_hits_only.smc)

Skating costs no energy (Genesis: the bne at $10D2A made bra; SNES: the bne at $F2867), bursts cost 0 (Genesis the
$CC at $BB72; SNES $F020D), knockdowns 1365, holds 683; bench recovery unchanged.
- Costs, trial by trial against the unchanged game, line changes On (`gen_hit_energy_check.py`, which now finds a
  changed byte by its retail surroundings where our test ROM's code sits elsewhere: its burst is 8 bytes earlier;
  `snes_hit_energy_check.py`): Genesis knockdowns by C or B 1365 every time, holds 683; a burst with no contact 0 (the
  game 204), the 33s of drain gone; nothing with line changes Off; a puck knocking a player down costs nothing (as
  in the earlier hit builds). SNES, where the two games stay in step: knockdowns 1365, holds 683 (650 once: the
  game's own 33 in the same trial), bursts and the drain free.
- A whole shift, never hit, skating and bursting: Genesis (`gen_energy_speed_check.py shift`, 2,700 frames, 68 C
  presses) $1000 at the end on the build, 0 on the game. SNES (live play is less steady over a shift: whistles,
  control moving between two skaters): his lowest energy over 1,500 frames 2,731 on the build, one knockdown when he
  ran into a parked player, against 1,120 on the game.
- The bench: the same on both, Genesis $800 -> $BF0 over the shift (+9 every 24 frames), SNES $800 -> $A6C.
- SNES top speed by knockdowns (`snes_energy_speed_check.py speed`, leg speed 15, most skaters in the state; the
  speed index legspd x (energy / 2 + $800) / $1000): none 9,214 (index 15), 1 knockdown 8,443 (12), 2: 7,927 (10),
  3: 7,167 (7). The SNES never slows a skater below half his speed index from energy.

## NOSE4Web's SNES "Energy takes all of a skater's speed", played (2026-11-10, 450306d)

playeracc's lsr / clc / adc #$0800 before the tax (retail $F2805, 5 bytes) made NOPs: the speed index legspd x energy
/ $1000 (retail: legspd x (energy / 2 + $800) / $1000); part of the SNES hits-only preset. `snes_energy_speed_check.py
speed`, leg speed 15, line changes On: NHL94_hits_only.smc 9,214 / 7,927 / 6,645 / 5,369 after 0 / 1 / 2 / 3
knockdowns (index 15 / 10 / 5 / 0); nhl94snes_SA1_hits_only.sfc 9,215 / 7,866 / 6,655 / 5,375. Line changes Auto:
9,214 (SA-1 9,215) at every energy. Goalies: holdcheck exits for a goalie and the knockdown cost skips position 0, so
in the preset nothing lowers a goalie's energy (a minute of computer play, line changes On: both stay 4,096). On
retail the drain runs for goalies too (3,996 and 4,060 after the same minute; they never go to the bench), so the
speed option used with the drain on would slow goalies, more than retail does.

## SNES goalie poke, and NOSE4Web's "Goalie poke check reaches the ice" (2026-11-10, c545a2e)

The goalie's stick test (checkpuckcoll_ccx `.9`) puts a box on the frame's stick spot (GetHot) whose size comes from
GetFrameHot: the frame record's bytes $14-$15 less the spot at $12-$13 (corrected the same day: an earlier note took
the spot itself for the size). For every SPAgpoke frame that vector is about (2, 2) (full sideways right (3, 2)); the
ready stance's (0, 0). So in retail a poke touches a puck only within about 2 units of its tip (11-12 ahead facing up
or down the ice, 20-35 to the side), and an ice-level puck only in the full sideways-right frame. The option (only in
SPAgpoke: reach max(|x|, |y|), the window from the ice to the same top, which can't go higher than retail's by
construction; outside the poke the original path byte for byte) lets every poke frame reach an ice-level puck within
those 2 units. `snes_goalie_poke_check.py trials` (goalie and carrier pinned, the computer goalie's own pokes, the
same state and seed on both ROMs; the cause from the goalie's lockout: stick 20+, body 10): diagonals, the option's
stick knocked the puck loose 8 times where retail's never did; sideways, no stick contact on either; straight on,
loose on both but by his body (the carried puck sits within his +-11 body box before it can reach a tip 11 out).
`cvc` (8 computer games each): 19 pokes at a carried puck on retail, 7 on the option build; too few, the games
diverge, and "came loose" there also counts a carrier shooting or passing during the poke: no measurable change.

### The rebuilt poke (c2a3549: reach max(d2, 6) in SPAgpoke) and a retail bug in the up-ice poke

Code as described (retail-size $F7FDF; the SA-1 build the same with SPA $71A3 and its SPAgpoke $DAC4). Trials
(`snes_goalie_poke_check.py trials`, the same states and seeds as retail, the goalie and carrier pinned): facing down
the ice (direction 4) the option's stick knocked a carried puck loose 7 times with it 12-14 units in front (retail: his
body only); sideways and diagonal it reached pucks 15-23 units to the side 24 times where retail never touched them;
nothing else differed. The raised-shot top is unchanged by construction (max(5, d3 + d4) as before), and outside
SPAgpoke the code takes the original path. **Facing up the ice (direction 0) no poke ever reaches full stretch, on
retail too:** assgoalie `.22` does `sta facedir,x / sta pfalock,x` with A the poke direction, so direction 0 leaves
pfalock 0 and the next think puts him back in SPAgready ($E528 -> $E0FE after one frame, seen in the trials). A
goalie at the bottom net can't poke straight up the ice; a pad goalie goes through the same `.22`. pfalock ($14E3) is
only ever tested zero / non-zero (every read is bne / beq or ORed into one) and cleared with stz when the animation
ends; the facing is facedir. So any non-zero lock is safe (the dive stores 150 there).
NOSE4Web 038dc3c hooks `.22`'s sta pfalock,x (retail-size $F5596, SA-1 $F5619: $74E3) to store $80, nothing else
changed (the dive and the other sta pfalock sites as before). Played: at the bottom net, facing up the ice, retail's
poke lasts 2 frames in SPAgpoke and never draws its full stretch (frame 679); the build's stays in SPAgpoke through the
25 frames watched and draws 679. Facing down: the same on both. (The SA-1 build's saved states are all at the top net,
so only facing down was played there; the same hook is in it.)

## NOSE4Web's SNES logo spill, checked (2026-11-10, 85a17a2: nhl94_2026_classic.sfc and _relaid.sfc)

From the code (video/FindCachedFrame: LoadFrameTiles): NOSE4Web's reading is right. A block frame (negative piece
count) gets ceil(word +2 / 4) units of 16x16 (2 tile columns by 2 tile rows); up to 8 units one run in a group of 8,
its room 2 x units columns of tile rows 0-1 from column 2 x (run & 7); more, a chain of whole groups of 8 and the
rest. The first DMA goes linearly from the room's start (sprox, frame +$0C bytes), the second one tile row down ($100
words; past 8 units at start + (sprox / 2 & $FF00) + $100). So a frame whose first DMA is longer than its room's row
writes over whatever else is cached there, and its own pieces past the room draw that instead.
`snes_logo_spill_check.py` (the 13 spilling teams in 7 home / visitor pairs, chosen by HomeTeam $1C98 / VisTeam $1C9A:
the setup menu wraps at 28; the same presses on both ROMs): Game Setup, the controller screen, the five matchup
moments and the pause scoreboard identical on both ROMs (both teams' big logos on screen, so the relaid logos draw
pixel for pixel as before); the pause items' screens (stats, rosters, player cards ...) differ in 5 of the 7 pairs by
77-191 pixels at the logos: stray blocks and stripes beside or under Anaheim's, Boston's, Dallas's, Florida's, the
Islanders' and Washington's logos on the old ROM, none on the relaid one. Pittsburgh-Quebec and San Jose-St. Louis
showed no difference on any screen.

## NOSE4Web's MIDI-made Genesis organ songs, played (2026-11-10, nhl94_songs_midi.bin)

Changed: SoundStreamTable ($2C648) entries $31 -> $FFAC0 and $32 -> $1002C0 (a 2 MB ROM; $31's stream runs over the 1 MB
line to $100298), the checksum check ($301); nothing else, so every other sound is retail's. The streams follow the
format (a 20-frame wait first, program 11 on channel 0, $90 / $80 notes, status 0 with $FFFF to end; NOSE4Web's tag
after).
- `gen_song_streams.py` (the streams decoded as notes; byte 0 the wait before its event, as the driver reads it,
  `move.b EventSize+ev_delay(a0),sl_delaybyte(a5)`: a first version read it as the wait after, which made the notes
  look swapped where two overlap and the fanfare's notes 0 frames long; NOSE4Web caught it): $31 against the original
  Brass Bonanza (song $40, found by matching notes) on the rebuilt nhl94_songs_midi.bin (velocity 35 as the original):
  250 of the original's 255 notes the same in start, pitch and length, the 5 others the ones over 4 at once; both
  1,480 frames, program 11. $32 ("Charge"): six notes of 9, 9, 9, 29, 14 and 59 frames, as written.
- `gen_midi_song_check.py` (the driver's track slots $D3D4 every frame; a slot is free when its pointer's top word is
  negative: a stream's end sets the top byte, st (a5)): Boston at home, the next period's first faceoff starts $31
  from $FFAC0 (retail $2D29E) on the same frame; it plays 1,481 frames and frees its slot (retail's $31 884); a home
  goal 300 frames in frees it 2 frames later, as on retail; sound effects play alongside as on retail (4 and 7 in the
  two runs on both). `wav` writes the songs out: $32's loudness holds through its 2.6 s (real) and drops to the
  background at its end: the organ patch's release lets each 0-frame note ring, as the original's own short notes do.

## NOSE4Web's MIDI-made SNES organ songs, played (2026-11-10: NHL94_songs_midi.smc, nhl94snes_SA1_songs_midi.sfc)

From the code (sound/MusicStart, SequencerTick, StepTrack, ReadTrackEvent, ReadVarLen): TempoTick = $2760 / the
header's tempo byte ($1FE0 on PAL); SequencerTick, from SoundUpdate in the NMI every frame, adds $40 and runs a tick
each time TempoAcc passes TempoTick, so tempo 157 is one tick a frame. A track is [delta][event] ... (deltas
variable-length ticks; the first one dropped, so every track starts at tick 0); a note is its code (below $D9), a
velocity byte and a variable-length length; **$D9 / $DA on any track stops the whole song** (MusicStop), and
SequencerTick steps the tracks from the highest down and quits as soon as the music stops. Panning comes with the
instrument: $DE reads its stereo bytes (+$12 / +$13).
`snes_song_streams.py` (the songs decoded): San Jose's new Brass Bonanza ($80:FCF7, tempo 157, 2 tracks, $DC 11 /
$DC 12, $D9 at tick 737 on both) against the game's own SNES Brass Bonanza ($99:BB80: tempo 120, a tick every 1.31
frames, $D9 at 561 / 562, so 738 frames): the same notes (codes, velocity 110) at the same moments (ticks 1, 20, 39 ...
there are frames 1.3, 26, 51; here 0, 25, 50), the same length; but the notes are shared out between the two tracks
(instruments 11 and 12) differently, 49 / 65 against 67 / 47. Boston's Charge fanfare ($80:FCAC): one track,
instrument 11, 6 notes, $D9 at 134.
`snes_midi_song_check.py` (live play, the home power-play faceoff, WAVs): San Jose's new song starts and plays 737
frames; Boston's 135; run into the period's end it is replaced by PeriodOver's song at once; left / right loudness
1.81 for the fanfare (all instrument 11) against 1.03-1.12 for the game's own songs. TempoAcc on the 1 MB build: +$40
a frame, one SequencerTick a frame.
- Rebuilt (e279997: a note alone plays on both organs, instrument 11 on track 0 and 12 on track 1; in a chord the top
  note on 11, the rest on 12), both builds (on the SA-1 build the goal slide set once: players put every frame stay
  frozen there): the fanfare's left / right loudness 1.01 (1 MB) and 1.02 (SA-1), Brass Bonanza's 1.05 / 1.06; the
  fanfare 135 frames on both (TempoAcc +$40 and -64 every frame: one tick a frame on the SA-1 build too); effect
  voices (VoiceState $08F2 in use, VoiceTrack $08FA $10 or more) sounding on every frame of the songs on both (the
  crowd's own voices included, so a single short effect isn't told apart).


## Penalty time and injury options (2026-11-11, for NOSE4Web)

### Penalty time, N seconds a penalty minute (bcd4dfb; test ROMs at N = 30)

`gen_penalty_time_check.py ROM GAMES OUT` / `snes_penalty_time_check.py ROM GAMES OUT`: computer games, penalties on
except offsides, every skater's Aggression at 15 (more penalties; goalies left alone), each penalised player's tmpdst
word (Genesis team block +$66, SNES $1852 / +$34: the seconds left; $2000 "just called", cleared as the penalty starts)
from the call until he is out, with the game-clock seconds that took and whether the other team scored then; the team
stats at the end. Majors from scratch copies with Cross Check and Roughing made 5 minutes (Genesis $19041 / $18FBD, the
retail copy's boot ROM check skipped as in NOSE4Web's builds; SNES by the entries' bytes).
- **Genesis nhl94_penalty_time_30.bin** (`mulu.w #$1E,d2` at $1230C): minors start at 60 s and are served in 59-63 s
  (retail 120 / 119-125), majors 150 s, served 150-152 (retail 300); penalty minutes 2 and 5 as before; power-play
  time matches the time served (a power-play goal after 12 s: 12 + 60 = 72 s) and power-play goals end the time.
- **SNES NHL94_penalty_time_30.smc**: minors 60 s, served 59; majors 150 s; minutes 2 and 5; a power-play goal released
  a minor after 24 s with 24 s of power-play time.
- **On both systems a power-play goal releases a major too** (retail as well: Genesis retail, a major out after 126 of
  300 s at a goal): PenGoalStuff releases the first player in the box whose penalty is not coincidental, majors
  included. Original behaviour, not the build's.
- No coincidental majors came up in play; the code compares the two box times, so they pair at any N. A third player
  waits for one of the two serving to come out (retail too).
- Nothing else found that assumes 60 seconds.

### Injuries on the SNES, mapped (for the Genesis-style Injuries choice)

FallDown `.24` (NHL94SNES routines/collide/FallDown.asm). Retail NHL94.smc addresses; the SA-1 and nhl94_2026 builds
have the same code $1B later ($68 later for setInjuryType); found by byte pattern.
- **The roll** ($9E:9DC3: `lda #$0096 / jsl randoma8 / asl / ldy a2 / sec / sbc impact,y / bpl .23 / lda gmclock /
  bne .23 / lda position,y / bmi .25 / beq .25`): only the puck carrier, falling back (SPAfallback), facing straight up
  or down the ice, not a goalie hitter, not in a highlight or Shootout mode, not already penalised; injured when
  randoma8(150) x 2 < impact, with the clock running. **Never:** `bne .23` after `lda gmclock` at **$9E:9DD6** -> `bra`
  (`D0` -> `80`): the fall and the loose puck stay (the Genesis $14440 equivalent).
- **setInjuryType** ($9E:C343 `lda #$0007 / jsl randoma8 / cmp #0 / bne .rtl / lda #TMPDINJGAME`): marks him
  unavailable (pf2unav), the crowd and groan, the camera lock, tmpdst TMPDOUT ($FFFD, out for the period), and
  **one time in 7** (randoma8(7) is 0-6: not 8) TMPDINJGAME ($FFFC, the game). **Every injury the period:** `bne .rtl` at
  **$9E:C34D** -> `bra`; **every injury the game:** the same two bytes -> `EA EA`.
- **The penalty without the injury** ($9E:9E21 `jsl setInjuryType / lda #4 / sta InjCntDown / lda #$16 / sta d0`, then
  the penalty at $9E:9E3C): `jsl setInjuryType` ($9E:9E21-24) -> NOPs and `sta InjCntDown` ($9E:9E28-2A) -> NOPs (else
  ShowInjuryBox comes 4 game seconds later with a stale name). The injury animation (SPAinjury1, set before) and the
  call stay: Roughing (PenRoughing2, $14) and Stop4Pen with penalties on; the $16 injury stoppage with them off or a
  goalie hitter. He is not marked out, so he plays on after the faceoff.

### "A long fall instead of an injury", both systems

- **What separates the fall from the injury:** the injury animation is set first (Genesis `move.w #SPAinjuryfall,d1 /
  bsr SetSPA`, then SPAinjury1 for a period injury after setInjuryType; SNES `lda #SPAinjury1 / jsl SetSPAFromA`); all
  of the injury itself comes after, in one run: setInjuryType (out of play, tmpdst, the crowd, the camera lock),
  InjCntDown = 4 (the injury box), the penalty and Stop4Pen. So skipping from the call to setInjuryType to the
  no-injury path leaves just the animation: **Genesis `bsr.w setInjuryType` at $14450 -> `bra.w .22`** (the crowd
  sound, as after any fall); **SNES `jsl setInjuryType` at $9E:9E21 -> `jmp .25`** (4C + the address of .25 and a NOP:
  the no-injury path).
- **How long the falls last:** an ordinary back fall plays fall 6 + 6 ticks, lies 100, gets up 8 + 8 (SPFduck); about
  one tick a frame on both systems: measured in the recorded games, **2.24 s (real) a back fall** (Genesis 2,220-2,265
  ms, SNES 2,265-2,325; 590 and 554 falls), so the lying part is about 1.7 s. The injury animations never get up:
  Genesis SPAinjuryfall falls 6 + 6, lies 30 then holds (-1024); SNES SPAinjury1 falls 20 + 20 (slower), lies 1,000
  ticks (about 17 s) then holds; the injured player lies until he is taken off at the stoppage (Genesis, seen: about
  530 frames after the hit).
- **So a long fall needs an animation that gets up.** The clean way is to rewrite the injury animation's lists in place
  for that option (in it no one is injured, so nothing else needs them; FallDown's early exits on SPAinjuryfall /
  SPAinjury1 then also keep a lying player from being knocked down again). Each list has 4 frame / time pairs, and a
  fall that gets up needs 5 (fall, fall, lie, get up, duck), so drop the first fall frame: **Genesis SPAinjuryfall**
  (two lists: directions 0-2 and 7, 3-6) `SPFfallback+1,6, SPFfallback+2,L, SPFfallback+3,8, SPFduck,-8` (and +17,
  +18, +19, SPFduck+4 for the second); **SNES SPAinjury1** (lists .d0, .d3) the same with the SNES frames
  (SPFfallback+1 / +2 / +3, SPFduck; +17 / +18 / +19, SPFduck+4 for .d3). L is the lying time in ticks (about frames):
  100 is the ordinary fall, 300 about 5 s (real), 600 about 10 s. The Genesis period injury's SPAinjury1 is never
  reached then.
- **The SA-1 build** (nhl94snes_SA1_penalty_time_30.sfc): minors 60 s, served 59-60, 2 minutes each, in three games;
  no major came up there (the same multiply as the 1 MB build's, whose majors served 150 s).

### The long fall as NOSE4Web built it, played (5de49b8; `gen_long_fall_check.py`, `snes_long_fall_check.py`)

Each build in a scratch copy with every knockdown of a puck carrier sent down the injury path (the fall-back, facing
and random tests NOP'd; the clock test kept), the computer playing (Genesis: pad 1 home, standing still), 8-10
minutes (real) of play.

- **Genesis (nhl94_long_fall.bin, CDL_Season_12_long_fall.bin): the game hangs at the first long fall.** The branch at
  $14450 is `60 00 00 46`, which lands at $14498, 4 bytes past .22 ($14494, `move.w #SFXcrowdcheer,-(sp)`): the sound's
  word is never pushed, `move.w #SFXcrowdboo,(sp)` writes over the return address and `song` takes it off the stack,
  so FallDown's `rts` goes astray. Seen: the clock stood at 537 and every skater kept the same animation for a minute
  (real). **The right bytes are `60 00 00 42`** ($14494 - $14452). Both builds have the same bytes (CDL's FallDown is
  at the same address).
- **With `60 00 00 42` (scratch copies of both): as meant.** 14 long falls: 325-351 frames from the fall to skating
  again (326 typical: 5.4 s real, 13.6 game s; one that turned mid-fall, 351), the sprite frames falling, lying,
  getting up (SPFduck), then skating; play on (screen 0), the clock running, no penalty during the fall, InjCntDown
  never set, the game-injury bit never set, tmpdst $FFFF (on the ice); never knocked down again while lying. Ordinary
  knockdowns 134 frames, as always (the build changes only the injury lists, the branch, the boot check and the
  checksum; CDL's long-fall build also moves two of CDL's own routines, $1E2B5A and $1E2B6E, byte for byte to $1ED032
  / $1ED046, with all three calls repointed and no old address left).
- **SNES (NHL94_injuries_long_fall.smc, nhl94snes_SA1_injuries_long_fall.sfc): as meant.** The jmp (at $9E:9E21 /
  SA-1 $9E:9E3C) lands on .25 (`ldy a2 / lda SPA,y / cmp #SPAstumble`). 9 long falls on the 1 MB build, 15 on the
  SA-1: 326-332 frames, lying and getting up (SPFduck, SPFduck+4), then skating; the clock running, no penalty,
  InjCntDown never set, tmpdst $FFFF, never knocked down again. Back falls 134-139 frames, as always. The builds change
  only the two lists, the call and the checksum.
- **The crowd at the fall's end is the right team's** (the code): Genesis .22 pushes the cheer and turns it into the
  boo when the faller is the home team's (pfteam clear): the home crowd boos its own player going down and cheers a
  visitor going down, as after any knockdown. SNES .25: a home faller, sound 3 (the groan); a visitor, the crowd level
  +$258 (the roar). The SNES injury path's StartBenchCheer (the faller's bench, before the jmp) stays. What the long
  fall leaves out: setInjuryType's "oooh" and the camera lock (Genesis), and the extra crowd excitement of an injury.
- **A lying player doesn't move:** the movement step skips a player in SPAinjuryfall (Genesis logic94.asm) /
  SPAinjury1 (SNES updateplayers), so he stops where he was hit instead of sliding as an ordinary fall does. A look only, as the
  injured player always did.

### NOSE4Web's SNES Injuries choice, played (aa0ac43; `snes_long_fall_check.py` on each build: SPAinjury1 stretches)

The same forced game (every carrier's knockdown down the injury path, 5 minutes real) on the 1 MB and SA-1 builds of
each choice; the same results on both:
- **Never:** no injury path at all (0 SPAinjury1); back falls 134-139 frames, as always.
- **The penalty but no injury:** 7 injury-path falls: the penalty called each time, InjCntDown never set (no injury
  box), tmpdst never $FFFD / $FFFC; the player lies in SPAinjury1 until the stoppage (566-749 frames) and plays on
  from the faceoff (three were on the bench, $FFFE, for the faceoff: the lines put back after the penalty).
- **Every injury for the period:** 4: tmpdst $FFFD each time, InjCntDown set (the box), the penalty called.
- **Every injury for the game:** 6: tmpdst $FFFC each time, the box, the penalty.

## McMarkis's SNES fighting as NOSE4Web puts it in, played (2026-11-11, b3f1510)

NHL94_fighting.smc (bank $A0), NHL94_Classic_fighting.smc ($A0), SDL16_fighting.smc ($A3); the bonus word at the block's
+$446C and +$47D (a 512-byte copier header on the Classic and SDL16 files moves every offset $200); bonus 0 and 8 tried
in scratch copies. `snes_fight_rate.py ROM none GAMES OUT` (none: no Fighting option to set; $E708 is ordinary work
RAM on these builds), `snes_fight_shots.py ROM OUT [minutes] [startonly]` (a computer game until a player's pflags
$0400, pictures every 20 frames, the calls, then the pause menu and an instant replay; startonly: START through a league
ROM's own setup defaults, as SDL16's setup screen differs from retail's), `snes_fight_capture.py ... --no-option`.
- **Fights**: on all three builds the names box ("14 K. Haller vs. 7 T. Sandstrom"), gloves and sticks on the ice, the
  punching, one fighter down, the fade, then the penalty scoreboard: both fighters a 5:00 major ($2A "Fighting", and
  $2C "Fighting *", its asterisk drawn as a tick), the pause menu with both in the box (4:53), the instant replay with
  its controls, then a faceoff. On SDL16 the fight ended with "Injury to: 10 E. Tikkanen, Out for the game" (the
  NHLPA 93 fight injury). No instigator minor came: only a fight that starts from a shoulder check gives one (93S
  SetInst), and none of the three did.
- **The bonus**: three computer games each (the computer on both sides, penalties on): bonus 0 and the default 2 no
  fights (the same games: the bonus only matters at the fight check), bonus 8 fights in two of three (one each, the
  majors called).
- **SDL16 otherwise**: plays as before (goals, checks, the clock; the original SDL16 behaves the same in the harness).
- **The injury risk on the same hook** ($9E:9BD2, FallDown .2 where a knockdown is counted: `ldy a2 / lda #$0078`):
  McMarkis's F_countcheck is straight-line (counts the check, does the two replaced instructions, `jml $9E:9BD7`), and
  the injury risk's count is the same shape, so they chain: the hook to the injury risk's code, ending in `jml
  F_countcheck` instead of its own tail; X (the hitter) and 16-bit A / X kept. No RAM clash (the fights use the game's
  arrays around $1463 and the direct page, the injury risk $7E:F034 up).

## How people play, and how their skaters differ from the computer's (2026-11-11, `analysis/human_vs_cpu.py`)

The recorded games (32 Genesis, 29 SNES; people on both sides), the person's skater against his five computer
teammates in the same games (`ctrl`, the events' `human` and `gctl`); the button habits from the match summaries.

| | Genesis | SNES |
|---|---|---|
| Puck carried by a person's skater | 94% of possession | 92% |
| Shot attempts by people / goals | 90% (1,165 of 1,299) / 243 of 261 | 89% (883 of 993) / 203 of 217 |
| xG a shot: person / computer teammate | 0.234 / 0.208 | 0.255 / 0.108 |
| Median shot distance: person / computer | 77 / 78 | 63 / 84 |
| People's shots: wrist / one-timer / slapshot | 56% / 19% / 17% | 60% / 29% / 8% |
| Shots from rushes (all) | 71% | 72% |
| Passes by people (completed) / computer (completed) | 3,006 (60%) / 108 (75%) | 2,659 (69%) / 226 (74%) |
| Hits by people (the game's knockdowns) | 70% (1,093 of 1,572) | 66% (985 of 1,503) |
| Skating: median speed person / computer; at a sprint; standing | 80 / 65; 46% / 39%; 29% / 42% | 78 / 69; 42% / 38%; 31% / 39% |
| Defending: the person's skater nearest the carrier | 52% of the time (median 62 from him; the nearest computer teammate 63) | 48% (65 / 62) |
| Goalie: a person in net for the shot / goals against xG | 19% of shots; 77 on 82.1 (computer 184 on 207.9) | 25%; 74 on 77.6 (computer 143 on 156.3) |
| Presses a minute: B / C (Genesis) or A (SNES); bursts; pokes (8.5% win the puck) | B 64, C 18; 10; 5 | B 54, A 21; 10; 5 |
| The goalie taken, game seconds a game (median) | 46 | 46 |

- **People play through the puck:** control follows the puck, so their skater has it about 93% of the time and takes
  nine shots in ten; computer teammates rarely carry, shoot or pass (when they do pass they complete more: short,
  safe passes). Per skater, a person's hits are about nine times a computer skater's (two thirds of all knockdowns
  from one skater in five).
- **People skate faster and stand less**, and **on defence are the nearest to the carrier only half the time**: the
  computer's chaser is usually as close, so people often shadow rather than lead the pressure (or switch late).
- **People's goalies** do a little worse than the computer's against the same xG (goals / xG 0.94 against 0.89 on the
  Genesis, 0.95 against 0.91 on the SNES), the same as the off-the-line finding (the match reports, section 6).
- **On the SNES the person's shots are far better than the computer teammates' (0.255 xG a shot against 0.108)** and
  closer (63 against 84); on the Genesis they are about the same. SNES people use one-timers more (29%) and slapshots
  less (8%) than Genesis people (19% / 17%).

## How a people's team plays against a computer's team (2026-11-11, `analysis/team_style_compare.py`; chunk 1)

The user: not the person's skater against his computer teammates (above), but a team people play against a team the
computer plays, for better simulations and a bot that plays like people. Computer games recorded as the helper records
people's (`analysis/scoring_map/cvc_record.py`: the retail ROMs, the league's settings, the computer on both sides, a
matchup and a seed of its own each game, every frame sampled, converted by tools/export_match.py): 8 Genesis and 8
SNES games, 16 team-games each; all pass tests/check_matches.py but for one faceoff win in four SNES games (the SNES
recording starts once the clock runs, after the opening faceoff). People: every recorded league game with people on
both sides (56 Genesis, 48 SNES team-games). Each team-game scaled to 15 minutes of play; ** marks a difference over
2 standard errors. Per team, people against the computer:

- **Finishing and goaltending dominate the scores:** goals 3.8 / 1.3 (Genesis), 3.3 / 0.7 (SNES); on goal the
  shooting % 35 / 9 and 33 / 4. Both halves are in it: people shoot from better places (xG a shot attempt 0.22 / 0.14,
  0.24 / 0.05), and the computer's goalie (on both sides of a computer game) saves far more than a goalie in people's
  games (people's league goalies are manual on the Genesis; both people's goalies are against people's shooters).
- **Genesis: people hit, the computer passes.** Body checks 26 / 13 and big hits 3.9 / 0.7 a team; passes 46 / 58;
  giveaways 12.7 / 18.6, takeaways 11.7 / 7.6. People dump in more (11% / 5% of entries), carry in less (73% / 81%),
  enter more often (27 / 24) and keep the puck longer in the attacking zone (149 / 126 s); more odd-man rushes
  (9.8 / 8.2); fewer shots on goal (11.0 / 14.1) from a little closer; one-timers, breakaways, penalties alike.
- **SNES: the computer shoots from far, people work the puck in close.** Shot attempts 15 / 29, median distance 63 / 91,
  slapshots 7% / 16%, rebounds 0.3 / 1.9 (its long shots saved and given back); people's shots more often one-timers
  (29% / 23%) and from sustained pressure (17% / 9%). People carry in (76% / 65%), the computer dumps in (6% / 19%);
  people keep the puck (404 / 372 s, in the attacking zone 162 / 98 s); 71% of the computer's entries lead to a shot
  against 47% of people's (it shoots at once). Checks 27 / 21 (big hits alike), giveaways 8 / 11, takeaways 13 / 10.
- **For the simulations and the bot:** computer-against-computer runs (the ratings chunks, the period and 60 fps
  studies) are games with fewer hits (Genesis), more passes, and (SNES) far more long shots and dump-ins than league
  games, and goalies that stop nearly everything; effects that work through hits, close shots or holding the zone are
  understated there. A bot that plays like people carries the puck in and holds it in the zone, shoots from close,
  takes one-timers, and (Genesis) checks hard.

### The scripted bot's team against people's and the computer's (chunk 3; `analysis/scoring_map/bot_record.py`)

8 games of bot.py's default version (Montreal, Home, pad 1) against the computer (Los Angeles), recorded and converted
as people's games are (all pass check_matches), compared by `team_style_compare.py CVC BOT` (Genesis; per team, 15
minutes of play). **The bot beats the computer 8.4 goals to 1.5 a game** (every game won: 11-1, 10-2, 9-2, 9-1, 8-0,
8-0, 6-3, 6-3), and it plays nothing like people:
- **It skates the puck in and shoots, alone:** 6 passes a team-game (people 46, the computer 58), no passed entries,
  97% carried; 42 shot attempts (people 18), 97% wrist shots (its dekes and close shots), almost no one-timers (1%,
  people 25%) or slapshots (1%, people 17%); median distance 60 (people 77), 18 high-danger attempts (people 5), 6
  rebounds (people 1); xG a shot 0.23, as people's.
- **It holds the puck:** possession 436 game s (people 385), giveaways 9 (people 13), takeaways 19 (people 12; its
  defence chases the carrier), more odd-man rushes (14 / 10).
- **It hits less hard:** body checks 22 (people 26) but big hits 1.4 (people 3.9), and more penalties (2.8 / 1.5).
- **Its opponent, the computer, against it:** 15.5 attempts, 81.6 game s in the bot's zone with the puck, xG 1.2: the
  computer hardly gets set up.

So the bot is strong in a way of its own (one skater, the deke and close wrist shot), not a stand-in for a person. A
bot that plays like people would add passing (and the one-timer that follows), slapshots from the point, dump-ins when
the line is closed, and checking to knock down (the big hit) rather than to touch.

### Version 40: the bot carrying the puck as people do (chunk 3, step 1; `analysis/carry_profile.py`)

**People's carriers** (the person's skater, 4,374 carries in the recorded Genesis games): own zone a median 3.1
game s, then 74% pass, 8% shoot or clear, 18% lost; neutral zone 3.9 s, 57% / 19% / 23%; attacking zone 2.2 s,
44% / 30% / 26%. Passes sideways 32%, forward 30%, diagonal forward 25%, back 13%. Shots: wrist 67%, slapshots 26%
(from the slot 15%, the point 9%). **Version 32's skater:** own zone 10.4 s (circling his net), 13% pass; neutral 1%
pass; attacking 5% pass, 59% shoot; no slapshots. The computer's carriers are much like people's (70% / 51% / 38%
pass).

**Version 40** (bot.py people_carry, PEOPLE40): a hold time drawn from people's by zone, then a pass to an open
teammate (pass chances 0.95 / 0.9 / 0.6 by zone; in the attacking zone the one-timer pass first, half the time), the
slapshot from the slot or the point (35% when no pass), the dump-in when pressed at their line (25%); it bursts in to
check again (32 never did, for its penalties). 7 games against the computer (the first with the first try's chances:
0.85 / 0.7 / 0.55, dump 0.5), recorded and converted as people's (all pass check_matches); per team, 15 minutes:

- **Now like people:** passes 43 (people 46; 32: 6), own-zone carries 2.8 s ending 57% in a pass; giveaways 12.7
  (12.7); body checks 28 (26); possession 405 game s (385); median shot distance 78 (77); attacking-zone possession
  136 (149); penalties 2.1 (1.5; 32: 2.8).
- **Still not:** shot attempts 41 (people 18): 32's close-in wrist shot and deke still fire whenever he gets there, and
  its rebounds (5.3, people 0.9); one-timers almost none (0.4 tries, people 4.6: the one-timer pass rarely finds an
  open receiver in the slot); slapshots 9% (17%); big hits 1.3 (3.9: the burst at 45 every 30 frames touches rather
  than flattens); pass completion 69% (55%: it only passes to open teammates); takeaways 20 (12).
- **Still strong:** it won all 7, 6.3 goals to 1.6 (32: 8.4 to 1.5).

Next steps for people's play: fewer, later shots (people shoot about once in three attacking-zone carries), the
one-timer set-up as people make it (the receiver moving into the slot, the pass across), and the big hit (a burst
from farther out at full speed).

### Version 41: fewer, later shots, people's one-timers, checks from farther out (chunk 3, step 2)

Version 41 is 40 with: in the attacking zone no shot starts before the carry's hold time runs out, and then only 60%
of the time (else hold on and draw again), while he skates as 32 does; a prime chance (past 200 up the ice, within 40
of the middle) always taken; the one-timer pass 80% of the time it is there, on 13-14's limits (not 15's narrow
ones); the burst check from within 70, every 15 frames, closing at 1.0+ a frame (bot.py PEOPLE41, DEF41). (A first
try held the puck at the top of the circle instead: 9 attempts a team-game at 0.03 xG and 22 giveaways in its one
game.) 6 games against the computer, all pass check_matches; per team, 15 minutes, people's in brackets:

- **Now like people (no significant difference):** goals 3.3 (3.8), shot attempts 21.5 (18.2), shots on goal 14.2
  (11.0), xG 3.4 (4.2), median distance 81 (77), **one-timer tries 4.8 (4.6)** and 20% of attempts (25%; 40: 1%),
  slapshots 21% (17%), wrist shots 50% (50%), high-danger attempts 5.7 (5.2), odd-man rushes 9.7 (9.8), passed entries
  16% (16%), entries leading to a shot 45% (46%), pass completion 53% (55%), body checks 26.7 (26.3).
- **Still off:** penalties 3.5 (1.5: the longer bursts), big hits 1.5 (3.9), giveaways 19 (13), takeaways 20 (12),
  possession 441 game s (385), passes 55 (46), rebounds 1.7 (0.9).
- It won all 6, 3.3 goals to 0.7 (40: 6.3 to 1.6; 32: 8.4 to 1.5): about a person's scoring against the computer's
  goalie.

### Versions 42 and 43: penalties and big hits (chunk 3, step 3)

**Where 41's penalties came from** (6 games, 21 calls, the bot's team): tripping 7, roughing 6, cross-checking 3,
charging 2, slashing 2, hooking 1: the checks about half, the pokes (a poke that bumps him trips) most of the rest.
The game rolls for a penalty on every check and doubles the chance within about 40 of the puck
(GENESIS_MECHANICS 8.1); **people hit off the puck a third of the time** (36% of their skater's hits, 41's 17%).
**People's big hits are cross-checks into the boards** (97 of their 163; 26 upended by a shoulder, 25 cross-checks
into the bench): FallDown makes a board check only when the man hit touches the boards (wide of the crease, |x| >
$68, or past a goal line) and the checker comes from the middle side, driving him outward; the bot chased from
behind.

- **42** (41 with off_puck_hit: a teammate nearer the carrier by 25, the nearest opponent without the puck in our
  half within 90 of the bot's skater hit; the long burst only at a carrier near the boards; no poke from point-blank;
  DEF42), 6 games: penalties 2.6 (41: 3.5; people 1.5: tripping 5, cross-check 3, charging 3, hooking 2, roughing 2,
  slashing 1), off-puck hits 27% of its hits (people 36%), but big hits 0.3 (41: 1.5) and possession up to 482 game s
  (people 385). Won all 6, 3.7 to 0.8.
- **43** (42 with board_hit: a man past 95 across within the goal lines, skate to his inside, 30 nearer the middle,
  then C at him outward once 6+ nearer the middle than him; DEF43), 6 games: **big hits 1.8** (42: 0.3; people 3.9;
  its skater's: 5 into the bench, 4 into the boards), but penalties 4.0 (tripping 11, roughing 7, hooking 4,
  slashing 2, cross-check 1), body checks 19.9 (people 26.3), giveaways 17.5 (12.7), possession 469 (385). Won all 6,
  3.1 to 0.9. Six games a version give a penalty rate to about +-0.7 a game, so 42 and 43's penalties differ less
  than they look; the tripping is the poke, still.

So far 41 is the closest to people overall (shots, one-timers, shot kinds, chances, passing, checks); 43 the closest
in big hits. Open: the bot's pokes (tripping: the most-called foul in every version), its long possession (it keeps
the puck about 80-100 game s a game more than people), and its giveaways.

### Version 44, and an expert benchmark (chunk 3, step 4; `analysis/expert_profile.py`, `analysis/recorded_coaches.py`)

**The user's goal (2026-11-11): a bot that plays as an expert human does: not perfect at everything, great at what
people do most.** (A community bot that is near-perfect in goal by manual goalie control and weak in attack is the
opposite.) The recorded games already lean expert: of the 18 Genesis games that match the league database
(`recorded_coaches.py`: date, teams, score), 28 of 36 sides are coaches at 80%+ against an average coach. The wider
benchmark is the league database's own counts for every game, by the coach's strength (`expert_profile.py`; Genesis, a
side's game):

| | 85-90% (14,593) | 80-85% (11,076) | 70-80% (32,088) | under 60% (78,986) |
|---|---|---|---|---|
| goals for / against | 5.1 / 3.3 | 4.4 / 3.6 | 4.1 / 3.6 | 3.3 / 4.0 |
| shots | 13.7 | 12.0 | 12.4 | 11.3 |
| one-timer tries (goals) | 5.0 (1.8) | 4.8 (1.7) | 4.3 (1.3) | 4.1 (1.2) |
| checks | 31.0 | 26.1 | 26.0 | 24.1 |
| penalty minutes | 2.4 | 2.2 | 2.1 | 2.2 |
| passes tried / completed | 43.5 / 28.3 | 47.0 / 30.5 | 42.7 / 27.1 | 39.8 / 24.1 |
| attack-zone time (s) | 337 | 328 | 321 | 315 |

Experts shoot more, try and score more one-timers, check more, complete more passes (65% against 61%) without more
penalties. On the SNES the bands differ less (experts score 5.5 to 4.0, the rest about alike).

**Version 44** (43 without pokes, shooting once two holds in the attacking zone have run out, dumping in half the time
when pressed at their line; 8 games): penalties 2.2 a team-game (43: 4.0; people 1.5; penalty minutes 4.2, experts
2.4), possession 422 game s (people 385), one-timer tries 4.4 (experts 5.0), shots 14.8 (experts 13.7); but body
checks 18 (the pokes' knockdowns gone; experts 31), giveaways 20 (people 13), pass completion 49% (experts 65%), and
it lost 2 of 8 (3.0 goals to 1.6). Next: fewer, safer passes, and checks back up without the trips.

## NOSE4Web's SNES fighting and injury risk together, played (2026-11-11, 87067a6: NHL94_fighting_injury_risk.smc, NHL94_Classic_fighting_injury_risk.smc)

- **The chain, by its bytes (both builds):** $9E:9BD2 `jml $9E:FFF7`, the stub `ldy a2` / `jsr $FF4A` (the injury
  risk's count) / `jml $A0:C2A8` (F_countcheck, the same target and the same code as NHL94_fighting.smc's). The count
  code begins `phx` and ends `plx` / `lda #$78` / `rts`, so F_countcheck gets X as before (it indexes the per-player
  fight meter $1464,x with it).
- **The injury risk's counts** (`snes_injury_risk_check.py counts ... F034:40:2`): +1 for each knockdown of him (12:
  10 falls, 2 by B, 5 of them injuries), nothing for the rest (55 misses, 16 hook flails): as on the injury-risk build.
- **The fights' code runs on every counted check:** in 5 minutes (real) of a computer game, the fight meter ($147F and
  $1464,x) changed 17 times on the chained build (25 on NHL94_fighting.smc: the games part ways), the injury-risk
  counts reaching 2. No fight came up in 45 minutes (retail) or 60 (Classic) of computer games; fights in computer
  games were as rare on the fighting-only build (2 of 3 games with none).

## NOSE4Web's SNES shootout for tied regular-season games, played (2026-11-11, 76802d1; `snes_shootout_check.py`)

NHL94_shootout.smc (after one overtime), NHL94_shootout_after_period_3.smc and the Classic copies; a computer game,
each case from the same state (period 3, 3 s left), the computer on both sides; the same results on all four:
- **Tied after period 3 (the after-period-3 builds):** the shootout at once (shootoutmode $1D81 on, the scores reset
  for its tally); 5 rounds, home 2-1; then gsp 2 for a moment, the score 3-2 (2-2 and the winners' goal), the game
  over (gsp 4) and the final screen "FINAL Los Angeles 2, Montreal 3" with the usual Exit Game menu.
- **Tied after one overtime (the after-overtime builds; overtime's clock set to 3 s once it ran):** overtime to 0:00,
  then the shootout: 6 rounds (into sudden death), the visitors 2-1; the score 2-3, the game over.
- **Untied (3-2):** the game ends at the horn, no shootout. **Playoffs, tied:** overtime until a goal (2-3 on the
  retail build, 3-2 on Classic), no shootout.
- **The stats put back:** from period 3's last second to the game's end, nothing changed in $1636-$1793 (shots,
  penalties, power plays and their times and shots, goals and shots by period) beyond what an untied game's last
  seconds change (a faceoff won, the puck touches, the nearest-player words, energies); the teams the same. The
  winners' goal is in the score only: not in goals by period, a player's goals or the scoring summary.
- **The shootout's menus, and the game lost in a test (NOSE4Web's follow-up):** the shootout has two pause menus
  (Pausemode_menu; PauseMenuItems / PauseMenuHandlers): before it (pmenulist 3, when a pad has a team: pregamepause)
  "Start Shootout, Shootout Setup, Team Roster, Goalie, Player Cards, Exit Shootout", and between shooters (list 4)
  "Resume Shootout, Instant Replay, Team Roster, Goalie, Player Cards, Exit Shootout". B or A runs the highlighted
  line, Up / Down move, START resumes. **Exit Shootout is PauseExitGame:** the "Exit Game?" prompt (AskExitGame),
  which starts on No; only Down then B (Yes) goes to Opening2 (Game Setup). **The test game that went back to Game
  Setup was something else:** the harness's game had no pad on a team (the computer on both sides), which the game
  treats as its attract demo: demoread, called every frame of play by Gameloop, sends any button but START to Opening2
  when cont1team-cont5team are all 0. The B press that did it came on round 1's shooter banner ("SHOOTOUT R. Blake vs.
  P. Roy"); any game, not only a shootout, ends so with no pad on a team. **With pad 1 on the home team** (as in a
  person's game), B pressed every second all through the shootout: the opening menu (list 3) took B as Start Shootout,
  5 rounds were played, the visitors won it, the score 2-3, the game over as any other. The original game's own
  Shootout mode runs the same PlayShootout, menus and demoread (not played here).

### Version 45: fewer, safer passes, more checks tried (chunk 3, step 5)

45 is 44 passing only to a teammate with no opponent within 40 (was 25), on a lane clear by 22 (was 15), under 170
long (was 220), less often (0.8 / 0.7 / 0.55 by zone, was 0.95 / 0.9 / 0.6), and bursting from 60 in open ice (was
45) every 10 frames (bot.py PEOPLE45, DEF45). 8 games (the game's own counts, against the 85-90% coaches'):
- **Better:** penalty minutes 2.8 (experts 2.4; 44: 4.2), 1.4 penalties a team-game (people 1.5); passes tried 41.5
  (experts 43.5; 44: 55.6); one-timer tries 4.8 (5.0); attack-zone time 326 (337).
- **Worse or no better:** passes completed 17.9 of 41.5 (43%; experts 65%, 44: 49%): the safer choice of receiver did
  not help, so the misses are not about how open he is; checks 16.4 (experts 31; 44: 17.8): the farther, more frequent
  burst does not land more; goals 2.4 to 2.0 (5 of 8 won).
- **Next:** find why its passes fail (intercepted, missed, bobbled; the 8-way d-pad picks the receiver, not the bot)
  and why its bursts miss, from the recorded games, before changing more.

### Why the bot's passes and checks fall short (chunk 3, diagnosis; `analysis/pass_diagnosis.py`, `bot_pass_probe.py`)

**Passes.** By the converter (the team keeps the puck), the bot's skater completes 71% of its passes, as people's
skaters do (71%; the computer 75%; 1,792 bot passes from versions 41-45, 2,819 people's): the same aim (median 13-14
degrees off the nearest teammate's line), lane gaps (35 / 31) and pressure. **The game counts a pass completed only
when the player who takes the puck is passReceiverPlayerNum** ($FFBEE0, the receiver the game chose when the pass
left: collide94 puckglue), so its count is lower for everyone (people 54% against the converter's 69%; the bot 43%
against 66%; one-timers are never "completed"). In the harness (`bot_pass_probe.py`, 2 games of 45, every pass the bot
began): the game's target was the mate the bot meant in 53 of 64 (the 8-way d-pad is not the problem); **its
people-style passes (40's people_carry) reached the meant mate 27 of 43 (63%; experts 65%), but 32's old passes from
the slot (open_mate past 144 up the ice, on 41's looser limits) 4 of 28 (14%), 17 going to opponents (3 to the
goalie).** 41 loosened open_mate for one-timers; those passes into covered lanes are what pull the count down.

**Checks.** The converter's check attempts (by the team, per team-game): people 22.5, 29% landing; bot 41 26.8, 30%;
bot 45 30.6, 24%. **People throw a quarter of their checks as CB (B pressed during the C burst: the game's computer
checking formula decides the hit), and CB lands 43% against C's 33%.** 41's CB checks were its pokes pressed during
a burst (81 of 161, 37% landing); 44 took the pokes out for the trips and with them every CB (45: 1 of 245), and its
C checks land 28%.

Next (version 46): no 32-style slot passes (one-timers only from people_carry's offer), and the CB check thrown on
purpose (B a few frames into the burst, as version 21 did) about as often as people throw it.

### Version 46: no slot passes, the CB check on purpose (chunk 3, step 6)

46 is 45 without 32's slot passes and the left-hander's bail-out pass (one-timer passes only from people_carry's
offer) and with the CB check thrown on purpose, B 4 frames into the burst on 35% of bursts (DEF46). 8 games (the
game's own counts; experts the 85-90% coaches): **passes 32.6, completed 19.9 (61%; experts 65%; 45: 43%)**; goals
against 0.2 a game (7 of 8 won, 2.1 goals for); check attempts land as people's do (C 33%, CB 39% of 36; people 33%
/ 43%). But **one-timer tries 0.9 (experts 5.0; 45: 4.8)**: the slot passes were where its one-timers came from;
penalty minutes 5.0 (cross-checking 7 and roughing 6 of 20 calls: the knockdown's roll), checks 17.5 (experts 31),
attack-zone time 411 s (experts 337). Next: one-timers set up as people make them (an offer whenever a teammate is
open across the slot, not only when the carry's hold runs out), and fewer roughing / cross-checking calls.

### Version 47: the one-timer offered more often, fewer CB checks (chunk 3, step 7)

47 is 46 offering the one-timer pass every 6 frames in the attacking zone (35% of the time) whenever open_mate finds a
receiver, open_mate's receiver open by 35 and the lane clear by 20 (safer than 41-46's 20 / 15), and the CB check on
20% of bursts (PEOPLE47, DEF47). 8 games (7 won, 2.4 goals to 1.0): one-timer tries 1.4 (46: 0.9; experts 5.0), checks
23.6 (46: 17.5; experts 31), penalty minutes 4.2 (46: 5.0; experts 2.4), passes completed 21.8 of 36.2 (60%; experts
65%), attack-zone time 423 s (experts 337). The safe receiver open across the slot rarely comes up with the
computer's teammates; people's one-timer set-ups need measuring from the recordings (where the passer and the
receiver are, how covered, how the receiver is moving) before the offer is shaped again.

### People's one-timer set-ups, and a correction (chunk 3; `analysis/one_timer_setups.py`)

**243 one-timer passes by people's skaters** (the recorded Genesis games; 80 goals, 33%), in the attacking team's
view: the passer a median 206 up the ice (the goal line 264; quartiles 167-229), the receiver 97 out from the goal line
(63-120) and near the middle (-32 to 28 across), the pass 105 long (75-141) and 82 across (51-119); the receiver's
nearest opponent 51 (36-67), the lane gap 27 (15-42). **How covered the receiver was made no difference to the goal
rate** (32-34% from 15-25 to 50+), nor did a tight lane (39% with an opponent within 10 of the line). The user: "we
humans are more willing to accept suboptimal circumstances when deciding whether to attempt a one-timer". The bot's
open_mate allows 11% of these (47's 35 / 20), 17% (41-46's 20 / 15), 26% on its spot limits alone (the receiver 15-100
out, within 70 of the middle, the pass 39-110 across and under 130): most of what it turns down is where people stand,
not how open.

**Correction to the pass diagnosis above:** bot_pass_probe.py counts the next player to take the puck, so a pass that
became a one-timer shot, saved or blocked and then gathered by a defender, shows as "an opponent". 32's slot passes
were the bot's one-timers: 41 (with them, on looser limits) had 4.8 one-timer tries and 1.5 one-timer goals a game,
near the experts' 5.0 / 1.8; taking them out (46) cut its one-timers to 0.9. The game counts no one-timer as a
completed pass, for people too. Next (48): the slot pass back, on people's spots and coverage.

### Versions 48-50: one-timers on people's spots (chunk 3, step 8)

- **48** (47 with 32's slot pass back and open_mate on people's spots: the receiver 30-140 out, within 60 of the
  middle, the pass 30-130 across and under 170, the receiver open by 15, the lane by 5; PEOPLE48), 8 games: **one-timer
  tries 9.1 a game, 1.2 goals** (experts 5.0 / 1.8: too many, too poor: 13% scoring against 36%), passes 52.6, 40%
  credited (one-timers are never "completed"), penalty minutes 5.2, goals 1.9 to 1.4 (5 of 8 won).
- **49** (48 without 32's slot pass: the one-timer only from people_carry's offer, 35% every 6 frames), 8 games: still
  9.1 tries and 1.4 goals (15%); shots 17.0, passes 59.2 (45% credited), penalty minutes 3.2, goals 2.8 to 1.1 (6 of 8
  won). The offer alone, on people's loose spots, fires as often as both did.
- **50** (49 offering the one-timer 20% of the time, only with the goalie drawn 4+ toward the passer's side, as 15
  required; PEOPLE50), 8 games: **one-timer tries 6.0, goals 1.0** (17% scoring; experts 5.0 / 1.8, 36%), **passes
  tried 44.8** (experts 43.5), 51% credited, goals 3.4 to 1.2 (7 of 8 won), shots 18.4 (13.7), checks 23.1 (31),
  penalty minutes 5.0 (2.4). The number of one-timers is near the experts' now; their finish is not: people's
  one-timer passes scored 33% with receivers as covered, so the gap is likely in the strike (the C timing, ARRIVE 14
  frames before the puck reaches him) rather than in the choice of pass.

### NOSE4Web's lock on Exit Shootout, played (2026-11-11, 51876ae; `snes_shootout_lock_check.py`)

PauseExitGame's jsl AskExitGame goes to a stub that answers No while $7E:F0F0 is set. On NHL94_shootout.smc,
NHL94_shootout_after_period_3.smc and the Classic copies, with pad 1 on the home team from the controller screen's
default (setting cont1team after the start doesn't let START pause), the same on all four:
- **A regular game:** the mark 0; START, Down to the last line (Exit Game, item 15), B: the "Exit Game?" prompt
  (AskExitGame ran: curitem set to 0); Down, B: Game Setup, as before.
- **The shootout's opening menu** (pmenulist 3): Down to Exit Shootout (item 5), B, Down, B: no prompt, the menu still
  up (sflags $0401); Up to Start Shootout, B: the shootout started (round 0 to 1).
- **Its pause menu between shooters** (pmenulist 4, START once a shot was over: the 6th press): Exit Shootout, B,
  Down, B: no prompt, still paused in the shootout; Resume Shootout: play on.
- **Then** B every second to the end: rounds 1 to 6, the score 2-3, the game over (gsp 4), the mark cleared.
- The after-overtime builds needed START at overtime's start (a person's game waits for it), as in any game.

### The overnight sweep: version 50's settings against the experts (2026-11-12; `bot_sweep.py`, version 51)

Version 50 with six settings drawn from a grid: the one-timer's C timing (ARRIVE: 8, 11, 14, 17, 20 frames before the
pass arrives), how far out its receiver may be (100, 120, 140), how often it is offered (0.1-0.3), whether the goalie
must be drawn (0 or 4), the CB share of the bursts (0.1-0.3) and the shot share of the attacking holds (0.4-0.8). There
were 40 settings (version 50's own among them), 8 games each against the computer on seeds 0-7, scored against the
85-90% coaches by the mean of ((bot - expert) / scale)^2 over shots, one-timer tries and share scored, checks, penalty
minutes, passes tried and share completed, attack-zone time and breakaways (lower is closer). The best 3 then played
16 more games each (seeds 8-23). It took about 3 hours, two games at a time, and every capture was deleted once it was
measured.

| Setting (C timing, out, offer, drawn, CB, shoot) | Games | Score | Shots | OT tries | OT scored | Checks | PIM | Passes | Credited | AZT | Breakaways | GF-GA | Won |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Experts | | | 13.7 | 5.0 | 36% | 31 | 2.4 | 43.5 | 65% | 337 | 2.2 | 5.1-3.3 | |
| **17, 100, 0.1, 0, 0.3, 0.4 (version 51)** | 24 | **1.91** | 11.8 | 3.5 | 25% | 18.8 | 3.8 | 37.7 | 54% | 376 | 1.2 | 2.2-1.1 | 17 |
| 17, 140, 0.15, 4, 0.1, 0.8 | 24 | 2.35 | 15.9 | 5.6 | 24% | 19.0 | 4.2 | 44.2 | 47% | 375 | 1.4 | 3.6-1.3 | 21 |
| 20, 120, 0.1, 4, 0.1, 0.8 | 24 | 2.42 | 16.7 | 4.7 | 21% | 19.3 | 3.5 | 41.5 | 51% | 409 | 1.5 | 3.1-1.2 | 19 |
| 14, 140, 0.2, 4, 0.2, 0.6 (version 50) | 8 | 2.31 | 18.4 | 6.0 | 17% | 23.1 | 5.0 | 44.8 | 51% | 379 | 1.4 | 3.4-1.2 | 7 |

The full table of all 40 settings is in `runs/sweep1/report.md`; `python bot_sweep.py --report OUT` makes it again.

- **8 games is too few to rank on.** The first-8 leaders fell back on 16 new games. 20/120/0.1/4/0.1/0.8 went from
  1.83 to 2.80, and 17/140 went to 2.63. The winner went from 1.73 to 2.30 on its new games alone, which is version
  50's level. Its 24-game 1.91 beats version 50's 8-game 2.31, but much of that gap may be noise.
- **A later C may help.** The three settings replayed on 24 games all use 17-20 frames, not 14, and they score 21-25%
  of their one-timers against version 50's 17% (the experts score 36%). The weak point is that the 8-game leaders also
  include 8 and 11 frames.
- **What no setting reaches:** checks (15-23 a game against 31) and passes credited (47-55% against 65%). Neither
  changes much across the grid, so the CB share and the offer rate are not where these gaps come from. They are the
  next targets, and they need new behaviour rather than different settings.
- **Version 51** = 50 with the winner's settings (bot.py `SWEEP1`; an env override of any of them still wins). It is
  now `bot_run.py`'s default, replacing 32, so `bot_record.py` and `bot_run.py` play it unless NHL94_BOT_VERSION says
  otherwise. Its smoke game finished 2-1 with a one-timer goal.

### Ron Barr's text editor, played (2026-11-12, NOSE4Web 6806a72; `scouting_script.py`, `scouting_text_check.py`, `scouting_hot_rate.py`)

`scouting_script.py ROM [ROM2]` prints the script as a ROM holds it, found the way NOSE4Web finds it, and compares two
ROMs. `scouting_text_check.py ROM OUT` plays the matchup screen and reads the text box from video memory every 6
frames, through each ROM's own font map. It follows the box as it scrolls, so it gets the whole text as typed, row by
row. It then looks for each shown line, with its stand-ins as wildcards, and draws the glyph each punctuation mark
gets.
- **The bytes.** On all three builds (nhl94_ronbarr.bin, NHL94_ronbarr.smc, nhl94snes_SA1_ronbarr.sfc) the script
  starts and ends where the original's does: Genesis $4B5C0-$4B7A0, SNES $B88DC-$B8BBB. The rest of the room is filled
  with $0D (48 and 83 more empty lines). Outside the room the only changes are the checksum (Genesis $18E, SNES $7FDC),
  and on the Genesis NOSE4Web's usual removal of the boot checksum test ($300 `jsr $FFAC0` turned to nops, $FFAC0
  `bra *`). Every league ROM in the folder has the same removal.
- **Every line types out complete, in order, and wraps cleanly.** On all three builds each shown line was found whole
  in the typed text, no row is longer than the box (Genesis 30, SNES 19 columns), and no word is cut at a row's end.
  - The welcome line's added space works on both systems. On the Genesis it shows as a one-column indent
    (" Montreal Forum is sold out ..."). The SNES drops spaces at a row's start (ScoutTypeWord), so there it doesn't
    show.
  - The Genesis goalies line (28) is empty and is never shown, as before.
  - On the SNES builds the emptied team places (lines 0-27) change nothing: %H and %V still type the team's place
    (GetTeamLongName reads TeamList, or LongNYI / LongNYR). So %H is the place name ("Montreal", or "New York
    Islanders"), not city and nickname as NOSE4Web's label says.
- **The punctuation, by font** (the glyphs drawn from video memory):
  - Genesis (SmallFontMap): ! ? " - / : all show. ( and ) show as small angle brackets, like ⟨ ⟩.
  - SNES (SmallFontMap+6; the same on 1 MB and SA-1): ! ? " ( ) - / : all show.
  - On both, **& has no glyph** (font word 0, the space's), so it shows as a blank. On the SNES, an & that lands at a
    row's start leaves the row indented, because it isn't a real space and isn't dropped ("  Los Angeles?").
- **The screens after are unchanged.** The Genesis Game Setup screen (GameSetUpMap, still at $4B7A0) is identical to
  the original's pixel for pixel. The SNES song after PregameText (SongRallyTime at 97:8BBB) decodes the same, byte
  for byte, on all four SNES ROMs (`snes_song_streams.py`).
- **CDL and the other ROMs with one line fewer** (CDL_Season_12, CDL_dynasty_03_FINAL, DPWM3RegularSeason, IDL5_v02,
  RGDL_S01_FINAL: 35 lines, 27 and 28 merged; each keeps the original paragraph list).
  - On CDL_Season_12, played, **the home team's hot / cold line (now line 29) is typed between every pair of
    paragraphs**, six times in all.
  - Every later paragraph is off by one. The home hot / cold slot shows the visitors' line, the visitors' slot the
    crowd record, the crowd slot "Hit the start button ...", and the last slot shows "Lately California has been
    playing well." even though no team was hotter that time.
  - **Line 35 ("extremely well") is read past the script's end, and that freezes the game.** In a scratch copy with
    CompareHotColdTotals replaced by `moveq #$23,d0`, the player read on into the Game Setup picture's data. It
    typed blank rows and stray " and ! marks. Bytes of $80 and up are print's control codes (new attribute, map
    and position), so letters were printed across the matchup screen outside the box. Then the game stopped: no
    work RAM word changes from one frame to the next, START does nothing, and in the 600 frames (10 s real) after
    it not one byte of work RAM changes. The unpatched CDL keeps running, and START leaves.
  - **How often:** in 200 boots each with Game Setup's own teams (`scouting_hot_rate.py`), line 35 never came up,
    and line 34 came up 1 time in 200 on CDL and 24 in 200 on retail. It needs the two teams' hot / cold totals
    $BD apart, so it is rare, but on these five ROMs it hangs the game whenever it comes up.

### NOSE4Web's SNES shootout on the SA-1 and 32-team builds, played (2026-11-12, add97a6)

`snes_shootout_check.py` (now also on the 2 MB builds: the extra stats seeded at period 3's last second and read at
the end, the fight state, and on the SA-1 BW-RAM $40:4800-$5FFF watched every 10 frames; `--pad` keeps pad 1 on its
team) and `snes_shootout_lock_check.py` (now with the SA-1 builds' menus). ROMs: nhl94snes_SA1_shootout.sfc (after
one overtime), nhl94snes_SA1_shootout_after_period_3.sfc, nhl94_2026_shootout.sfc (SA-1, 32 teams),
nhl94snes_2026_shootout.sfc (LoROM, 32 teams).
- **With a pad on a team (a person's game, as every league game is), all four pass.** A tied regular-season game goes
  to the shootout (after overtime, or at once on the after-period-3 build). It plays to its end, the score is the tie
  plus one (2-3), and the game ends normally.
  - Lock check: Exit Shootout does nothing in both shootout menus, Start Shootout and Resume Shootout work, the
    regular game's Exit Game still asks and leaves for Game Setup, and the mark is 0 in a regular game and after the
    shootout.
  - Untied games end at the horn and playoff ties go to overtime, with no shootout (all four builds, computer
    only).
  - The team stats and scoring summary put back: the words that differ from period 3's last second are an ordinary
    game end's (touches, energies, box slots) and, after overtime, overtime's own play (a faceoff won, a check, a
    pass, the crowd average).
- **Computer on both sides, two builds crash in round 1.** The SA-1 after-period-3 build crashed 4 times out of 4
  (also when reached through real period ends), and the LoROM 32-team build twice: the screen fills with junk tiles
  as the first shooter's turn loads, and low RAM fills with repeated words (round 257 / 1664 / 17184, scores 32898-6
  ...). **The unmodified nhl94snes_2026.sfc does the same in its own Shootout mode** (yesterday's RAM tour, computer
  only: round 257 and junk scores in the first turn), so on the LoROM build it is not NOSE4Web's code. The SA-1
  after-overtime build and the SA-1 32-team build played computer-only shootouts to the end. (Said here at first: the
  SA-1 base build's own Shootout mode had played cleanly in the RAM tour. Wrong: that run never left the menu; see
  below.) The hooks were ruled out as far as they could
  be: the shared code after $9F:FF70 is byte for byte the after-overtime build's, the period-3 hook's test is sound,
  and turning off the after-overtime build's other change ($9F:8CC0 `beq` to nops) in a scratch copy changes nothing.
- **SA-1: BW-RAM $40:4800-$5FFF.** In every case only $40:4811-$40:5318 changed, at the frame the shootout began (the
  saved blocks, $4810-$4F8F, $4F90-$5317 and lastperiod $5318). Nothing touched the room in untied or playoff games.
- **The 2 MB builds' extra stats are lost in a shootout.** StartGame_go's ClearTeamStats calls ClearPlayerChecks
  (players' checks for $E788 and against $E7BC, posts $E7F0) and ClearPlayerIceTime ($E800). The block isn't in the
  saved ranges. Seeded at period 3's last second (153 checks for, 155 against, posts 3-4, 6,538 s of ice time), the
  checks and posts read 0 at the game's end on all four builds (the 32-team SA-1 build kept the shootout's own post,
  1-0), and the ice time 0 on the SA-1 builds. The LoROM build never changed $E800 in any case, so its ice time isn't
  kept there. The fight
  state (FightGameStart: fighton, ChkCnt, pchecks, fightinj) is cleared too. Fighting was Off in these games; at a
  game's end that state no longer matters. Untied and playoff games keep everything.
- **The LoROM 32-team build's RAM** (`snes_ram_use_check.py`, a whole game and a Shootout-mode game): work RAM never
  written from $7E:F03F to $FFFF ($FC1), and $7E:E7F1-$EFFF, $7F:A7C0-$C7FF, $7F:F240-$FFFF. The mark $7E:F0F0 and the
  saved blocks ($7E:F100-$F87F, $F880-$FC07, lastperiod $FC08) are inside that free room.

### NOSE4Web's SNES bodycheck statistics, played (2026-11-12, 5c9609b; `snes_bodycheck_check.py`, `analysis/snes_bodycheck_recorded.py`)

NHL94_bodychecks.smc (retail), SDL16_bodychecks.smc, nhl94snes_SA1_bodychecks.sfc.
- **The bytes.** The counting routine (retail $9E:FFC8, 56 bytes) is NHL94_Classic's, byte for byte. FallDown's `lda
  tmchecks,y` becomes `jsr $FFC8`. The display changes are the stats list's `lda ppenmin,x` to $168E, the heading PM
  to Cf, the sort title "Penalties" to " Checks  ", and ComparePlayerStats' two reads to $168E. On SDL16, which already
  had the Vault's display, only the compare changes. The SA-1 build has the same at +$6000.
- **A whole computer game on each** (penalties on), watched every 2 frames: 50 checks (retail), 72 (SA-1) and 205
  (SDL16). **Every check raised exactly one given byte, of a player of the checking team, and one taken byte, of the
  other team's player**, the two 16-17 apart on median and 40 at most. At every sample the given sums equal the
  team checks and the taken sums the other team's. No other write was ever made in $168E-$16F5.
  - The team checks are the game's own, unchanged (`lda tmchecks,y` is done after the counting).
  - On the SA-1 an idle object can keep an old pnum (two objects with pnum 17, one of them with SPA 0), so the check
    takes the nearer.
- **Player Stats** (the end-of-game menu, five down): the "Cf" column shows the checks given. Sorted by Checks, the
  rows go by Cf: retail Montreal 8, 8, 5, 4, 3, 1, 0 and Los Angeles 7, 3, 3, 3, 3, 1, 1, every player's number his
  roster place's byte (Muller and Desjardins 8 ... McSorley 7); SDL16 Toronto 35, 33, 27, 22, 21 and Vancouver 21,
  16, 9, 8, 7, 4, 2.
- **The counts start at 0:** at the first sample of play, and in the next game after a 50-check game (0 and 0 at 4:56
  of its first period).
- **pnum's high byte:** in play it is 0 for every object with a player, and $FFFF for an empty slot (a skater in the
  box, a pulled goalie), in the 28 recorded league games (every 6th sample) and in all three test games. An empty slot
  is never a checker or the player hit (no count went astray in 327 checks), so the word read is safe. Were $FFFF ever
  read, `inc $168E,x` would land in bank $7F.
- **The overlap with PenSum:** PenSum holds $41 entries of 4 bytes ($163E-$1741), and InProgress writes one at
  4 x PenSumLength while that is below $41. The counts take entries 20-45. Nothing else in the disassembly names
  $1680-$1700 (only PenSum and its two users, InProgress and FillPenaltyPage). A 21st penalty would write over the
  first count bytes, and counted checks would change log entries 20 on. **No game has come near:** in 36,392 SNES
  league games the most penalties in one game is 14 (mean 2.5); the 28 recordings reach 6 log entries, the test games
  12 (SDL16).
- **The recorded games** (Classic-based league ROM, the same code): in 28 of 29 recordings the given sums equal the
  team checks and the taken sums the other team's at the end of the game. Matching by player against the converter's
  knockdowns proves little: it finds 1,178 knockdowns against the game's 1,476 checks.
- **Through a shootout:** $168E-$16F5 is inside the saved $15D3-$1D52, which StartGame_go clears and the shootout code
  puts back. The shootout runs above found that block back as it was, apart from the game's own changes. No ROM has
  both hacks, so it wasn't played.

### NOSE4Web's fixes, played (2026-11-12, d6ce48d)

- **Ron Barr's missing line put back** (CDL_Season_12_lines_fixed.bin, IDL5_v02_lines_fixed.bin; `scouting_script.py`,
  `scouting_text_check.py`).
  - Both scripts have 36 lines again: line 29 is empty, and the paragraphs are at 30-35 where the list reads them.
    The room ends where it did ($4B7A0, the picture's bytes after it unchanged), and outside it only the checksum
    changed.
  - CDL's greeting padding is 21 spaces (22 before). IDL5's welcome line lost the double space after "sold out
    ^.". The editor also rewrote the welcome line's `+` and `_` as `}` and `{`, which run the same code.
  - Played, **each paragraph is typed once**, in order, with an empty row between: greeting, welcome, (the hotter
    team when there is one: IDL5's run had "Lately Los Angeles has been playing well."), home hot / cold, visitors'
    hot / cold, crowd record, "Hit the start button". Nothing repeats between them.
  - **Line 35 forced** (scratch copies, CompareHotColdTotals replaced by `moveq #$23,d0`): "Lately San Jose / Houston
    has been playing extremely well." in its place, everything after it as normal. The game runs on (work RAM
    counting down every frame), and START leaves the screen.
  - **CDL's greeting with 21 spaces:** "Ace here." alone on row 1, "Tonight's goalies are" starting row 2 with no
    indent. (The 22-space version read the same way in this morning's run: no indent there either.)
- **The 2 MB builds' stats through a shootout** (the four rebuilt shootout ROMs, `snes_shootout_check.py --pad tie`:
  the extra stats seeded at period 3's last second). All four go to the shootout and end 2-3.
  - **Checks for and against and posts come back exactly as seeded** (153, 155, 3-4) on all four.
  - **Ice time:** SA-1 builds 6,526 s seeded. At the end it reads 6,622 s on the after-overtime builds and 6,562 s
    on the after-period-3 build: the seeded time plus the regulation and overtime seconds played after it. The
    untied runs earlier grew by 24-36 s in the same last seconds. The LoROM build has no ice time ($E800 unchanged).
  - SA-1 BW-RAM: the bytes written run from $40:4811 to $40:53FE, only at the shootout's start. That includes the
    new $40:5320-$53FF save, and nothing in untied or playoff games.

### How people check, and bot versions 52-53 (2026-11-12; `analysis/check_profile.py`, `analysis/knockdown_approach.py`)

The user: don't chase the experts' check count exactly; some top coaches pad it with checks after the whistle,
which count in unmodified ROMs. So this is about how people knock players down, not a number to match.
- **Who knocks players down** (people's Genesis recordings, sides matched to coach ratings; the bot's 8-game
  recordings). Coaches rated 80%+ against an average coach (28 side-games): game's checks 29.5. The skater they
  control knocks down 17.3 a game: 13.5 with a thrown check (shoulder, hip, cross-check), 3.9 without one; 11.4 on
  the carrier, 6.0 off the puck. Teammates add 7.3. Under 80% (8 side-games): 19.6 and 10.8. Version 51: 20.4 and 11.0
  (thrown 10.2, plain 0.8, off the puck 3.9), teammates 7.9, from 34.9 check attempts a game (people 23).
- **The knockdowns without a check animation are pokes.** Of the strong coaches' 3.6 a game without a C press in the
  1.5 s before, 3.3 follow a B press. 95 such knockdowns: the poker in front of the man (his heading within 60 degrees
  of the poker in 52 of 78 with a heading, from the side 20, behind 6), 26 away at the press (20 on the carrier), the
  man slow. Only 0.14 a game were followed by a penalty within 3 s (4%). The bot stopped poking in version 44 (trips);
  versions 31-43 held B on and off every frame inside poke range, many pokes an approach.
- **Thrown checks:** at the C press before a knockdown, strong coaches are 36.5 away (median) and closing at 1.6 a
  frame; the bot 29.8 and 1.3.
- **Version 52** (51 ramming the carrier without C on half its approaches, and off-puck hits from 130 away within 400
  of our goal line, every 8 frames), 8 games: checks 16.5, plain-contact knockdowns still 0.8. Skating into the
  carrier without C knocks nobody down, and the approaches spent ramming lost their C bursts. Dropped.
- **Version 53** (51 with people's pokes: one B press per approach at a carrier within 28, slower than 1.6, heading
  within 75 degrees of the bot, on 60% of approaches, at most one every 60 frames), 8 games: plain knockdowns 1.8
  (0.8), thrown 8.9 (10.2), checks 19.4 (20.4), penalty minutes 1.8 (3.5; experts 2.4), 2.9 goals for and 1.4 against.
- A sweep of 53's C timing (the closing rate needed, how often it may press: `NHL94_DEF45`) was stopped half done to
  make room for NOSE4Web's retests.

### Bot version 54: shooting from where people shoot (2026-11-12)

- **The shots** (ordinary shots, not one-timers). Coaches rated 80%+ (28 side-games): 12.6 a game, xG 0.216 a shot,
  18% scored, 26% slapshots; out from the goal line 2.5 a game within 40, 5.4 at 40-80, 2.9 at 80-130 (xG 0.155, 21%
  scored), 1.3 farther. Version 51: 16.0 a game, xG 0.135, 9% scored, 39% slapshots, 4.9 a game at 80-130 out (xG
  0.008, none scored) and 2.6 farther. Its slapshots came from the hold running out anywhere 90-175 up the ice
  (PEOPLE40 "slap" 0.35). People's long shots are against a person in goal; the computer goalie saves nearly all of
  them (the xG model counts that), so part of the gap is the opponent. Still, the bot shot from far out twice as often.
- **Version 54** = 53 with the hold's slapshot only within 110 of the goal line and on 20% of holds (PEOPLE54), the
  same 16 seeds as 53: goals 3.6 a game (53: 2.4), ordinary shots 14.1 (19.3), xG 0.190 a shot (0.101), 16% scored
  (6%), slapshots 7% (32%; people 26%), shots at 80-130 out 4.6 (6.2), farther 1.1 (3.4). Passes completed 23.1 a game
  (20.4). Penalty minutes 4.5 (2.6): 36 penalties in 16 games against 23, most of them codes 22 and 24 and the
  computer teammates' too. It isn't explained by the shot rule; to watch. **Version 54 is now bot_run.py's default**,
  and so bot_live.py's.
- **Passing, measured as the game counts it** (the same coaches, 28 side-games): the game's counter 56% completed
  (league 85-90% band: 65%), the converter's 62%. Version 51: 48% and 58%. Both credit 83-84% of the passes that reach
  a teammate. The bot's passes are shorter and are intercepted more when the receiver is covered (42% within 30 of an
  opponent, people 32%).

### The SA-1 base build's own Shootout mode, computer on both sides (2026-11-12, for NOSE4Web)

Shootout mode from power-on (Play Mode 4), the computer on both sides, B once at the shootout's menu:
- **Retail NHL94.smc:** five rounds, 1-0, the shootout over.
- **nhl94snes_SA1.sfc** (unmodified) **and nhl94_2026.sfc:** round 1 starts, then nothing for 30,000 frames. The
  screen goes nearly black with one small sprite. On nhl94snes_SA1.sfc no byte of work RAM or BW-RAM changes over 120
  frames: the game is hung.
- **nhl94snes_SA1.sfc with pad 1 left on a team:** rounds 1 to 8 played (0-0, pad 1's shooter standing still) and
  memory changing.

So **the 2 MB builds' computer-only shootouts fail without any NOSE4Web code** (the LoROM build's own Shootout mode
crashed the same way). Computer-only shootouts on these builds say nothing about NOSE4Web's hooks, and with a person
on a team they play.

### The SNES scouting box's row width, played (2026-11-12, for NOSE4Web's editor: it wraps at 21)

A scratch copy of NHL94.smc, the team places emptied and the greeting replaced by "abcdefghijklmnopqrs X
ABCDEFGHIJKLMNOPQRST abcdefghijklmnopqrstu Z" (`scouting_text_check.py`, the box read from column 2 to its right edge):
- the 19-letter word, then "X" on the **next** row: ScoutTypeWord starts a new row once a word would end past column 20
  (the 21st cell), so two words never fill more than 20 cells;
- the 20-letter word on a row of its own, filling columns 2-21: **20 letters fit**;
- the 21-letter word printed whole on one row, its last letter in column 22, **on top of the box's right edge**. The
  scroll (ScrollDisplayUp: $28 bytes, 20 cells a row) moves columns 2-21 only, so that letter stays where it was as
  the text scrolls up, a stray "u" on the frame.
So the editor's wrap and its longest word should be **20**, not 21. The rows of at most 19 seen before were the
text's own words, not the limit.

### A "-" in a SNES banner name, played (2026-11-12, for NOSE4Web ff0ff52: the commissioner's jumbled matchup screen)

A scratch copy of retail NHL94.smc with Montreal's TeamPlaceNames entry "Montreal" made "Mon-real" (file $E16DD;
screenshots of both ROMs on the same presses, `runs/banner_hyphen`). PrintTeamSprites sends a character outside A-Z,
0-9, space, "." and "@" through `and #$DF / sbc #$41`: a negative letter index, so DrawSprite draws another sprite
frame in its place, at a width from before LetterWidths. In the game:
- **Game Setup** and **Player Select**: Montreal's banner reads "MON REAL" with a gap, and **a whole skater sprite**
  (a falling player in Montreal's colours) is drawn over the banner and the logo box above it;
- **the matchup screen**: the same skater over Montreal's "Overall 73", at the top right of the screen: the jumble
  the commissioner saw;
- **the playoff bracket**: "MON:REAL", with dots and a small orange sprite piece in the gap;
- the game then plays normally (a faceoff and play, 1-0 after a few minutes).
So one hyphen in a banner name explains it, as NOSE4Web read from the code; an apostrophe or any other character the
routine doesn't know would go the same way (a different stray frame for each).

### Bot version 55: slapshots by the shooter's Shot Power, and 16 matchups (2026-11-12)

- **People's slapshots by the shooter's roster Shot Power** (people's Genesis games, ordinary shots by a person's
  skater): Shot Power 2: 1 slapshot in 41 shots; 3: 20%; 4: 25% (19-35% of them scored, against people in goal); 5: 51%,
  from farther out (median 109 against 76-85) and 5% scored. Coaches rated 80%+ the same: 0%, 19%, 26%, 50%.
- **The working Shot Power** (record +$6C, which the bot now reads) is about 5 times the roster rating, moved by hot and
  cold (roster 2: 7-12, 3: 12-17, 4: 17-22, 5: 24-27, 6: 30), so the bot takes the shooter's class as round(working / 5).
- **Version 55** = 54 with the hold's slapshot chance "slap" 0.9 times a factor by class (2 and below 0.1, 3 0.8, 4 1.0, 5
  and up 2.0), never above "cap" 0.5 (the user: a top player doesn't slap every time with a strong shooter), and for
  class 5 and up from as far as 150 out (PEOPLE55).
- **The bot's test games now vary the teams** (the user: playing the same team each time would be dull; ratings now
  matter): `bot_states.py all` saves 16 matchups (cvc_record.teams_for), and `bot_record.py` with NHL94_BOT_TEAMS=1
  starts game n from matchup n % 16. On them, 16 games each: version 54 2.8 goals, 14.6 shots, penalty minutes 3.8;
  version 55 2.4, 14.2, 5.5. Version 55's slapshots by class: 2: 3%, 3: 9%, 4: 11%, 5: 21% (54: 0%, 8%, 6%, 0%). That is
  people's pattern at half their rate. None of either version's slapshots scored against the computer goalie. The goal
  and penalty differences are within the noise of 16 games (the same version's penalty minutes moved 1-2 a game
  between runs). Montreal, the old fixed team, had flattered the bot: version 54 scored 3.6 a game with it.
- **Version 55 is now the default** (bot_run.py, bot_live.py), for the user's games against it.

### The close-in moves, and bot versions 56-57: shooting when the goalie is off the line (2026-11-12; `analysis/scoring_moves.py`)

The user: does the bot try EA Specials, cross-crease goals, dekes? `scoring_moves.py` sorts every ordinary shot by the
shooter's movement in the second before it: an EA Special attempt (the converter's `flip`); cross-crease (within 90 of
the goal line, crossing the middle, moving across faster than 1 a frame); a deke (within 80, his facing turned two or
more steps in the 0.6 s before a wrist shot); else by distance. Coaches rated 80%+ (28 side-games) against version 55
(16 games on the 16 matchups), a game, share scored, xG a shot:

| Move | Strong coaches | Bot 55 | Bot 57 |
|---|---|---|---|
| EA Special attempt | 0.79, 0% (its goal is the follow-up shot), 0.057 | 0.25 | 0.06 |
| cross-crease | 0.86, 33%, 0.379 | 0.69, 9%, 0.116 | 0.19, 0%, 0.057 |
| deke | 3.14, 23%, 0.302 | 5.38, 14%, 0.260 | 3.88, 26%, 0.353 |
| in close (within 60) | 2.61, 21%, 0.265 | 2.94, 21%, 0.297 | 3.25, 19%, 0.233 |
| slot (60-110) | 2.96, 19%, 0.194 | 5.50, 0%, 0.026 | 5.75, 1%, 0.030 |
| farther | 2.21, 8%, 0.059 | 2.62, 0%, 0.016 | 2.50, 0%, 0.014 |

- **The slot.** People's slot shots came at speed 18,050 (median), 45 of 83 slapshots; the bot's at 9,800, 76 of 88
  wrist shots, 65 of them aimed at one side. The wind-up is not it: people hold C a median 5 frames for a wrist shot
  (quartiles 4-7), and their wrist shots are as slow (10,500). The goalie mostly the computer for people too (72 of 83).
- **Version 56** = 55 with the slapshot window where people use it (40-110 out, 150 for big shooters), and 32's wrist
  shot turned into the slapshot by the same chances: 16 games, goals 2.5, the slot still 0% (xG 0.040). Slapshots don't
  beat the computer goalie from there either.
- **The goalie off the line** (shots within 110, the converter's gOff): people (all recorded, 489 shots) 0-2: 1%
  scored, 2-5: 8%, 5-10: 21%, 10-20: 37%, 20+: 47%; bot 55 + 56 (428): 1%, 0%, 14%, 35%, 40%. The same once he is
  off the line, but 56% of the bot's shots came with him within 5 of it, people's 47%. People shoot when he has been
  pulled across.
- **Version 57** = 56 with 32's wrist shot (or 56's slapshot in its place) only when the goalie is 5+ off the line from
  the shooter to the middle of the net, else each frame with chance 0.03 (people take some anyway; not rote): 16 games
  on the 16 matchups, **goals 3.7 a game** (55: 2.4, 56: 2.5; strong coaches 4.2), one-timer goals 1.8 (0.9, 0.5;
  league top band 1.8), its dekes 3.88 a game at 26% scored (people's 3.14 at 23%), penalty minutes 3.4. The slot is
  still poor: those shots come from another path (people_carry's hold running out) and are the next thing to look at.
  The EA Special and the cross-crease are now rare (0.06 and 0.19 a game, people 0.79 and 0.86): to bring back on purpose.
- **Version 57 is now the default** (bot_run.py, bot_live.py).

### NOSE4Web's original-layout SNES hacks in the 2 MB builds, played (2026-11-12, bbe2758; `snes_2mb_hacks_check.py`)

`snes_2mb_hacks_check.py ORIGINAL HACK OUT [part ...]` runs `snes_vault_hacks_test.py`'s parts on a 2 MB build: each ROM
boots through its menus with pad 1 on the home team (snes_shootout_lock_check.person_start) and plays on until the
clock runs, and every read and write goes through faceoff_fix_test.Snes (the SA-1 builds' low RAM in BW-RAM). The pick
list's text is read with each build's font offset (lower case 1 before retail's tile on the SA-1 builds, 2 past it on
the LoROM 32-team build; capitals and digits one further). `faceoff_fix_test.Snes` now boots any 2 MB ROM instead of
loading the retail states; `snes_injury_risk_check.py` takes a count SPEC in BW-RAM as "40:BASE:...".
- **nhl94snes_2026_five.sfc (LoROM 32-team): everything passes.**
  - L+R: pulls at every hold from 2 frames to 120, 12 of 12 each. Pressed again it brings the goalie back. Nothing
    happens in a stoppage, and presses during a whistle or a pause don't pull him once play resumes. With both pads
    on the home team only pad 1 has it, as on retail. (The original LoROM build pulls on a 120-frame hold by itself:
    its own feature.)
  - Any position: every row of every line (Best Line, Scoring 1, Pen. Kill 1 and 2) lists all 22 skaters. No pick
    puts a player on twice or drops one; the original lists 7 or 15 and does both.
  - The extra attacker fix: a forward edited into LD plays LD, and when the goalie is pulled the old LD comes on as
    the extra attacker.
  - Injury counts (word a player, the away team +$40, at $7E:F040): $5A written over them at Game Setup reads 0 when
    play starts, and counts of 7, 10 and 255 read 3, 5 and 127 after an intermission.
- **nhl94snes_2026_maxboost.sfc: passes.** In the LD pick list 77 of 77 rating cells read 100 exactly when that
  player's hot / cold value for the rating is negative. Status, Overall, Energy, Handed and Weight are untouched.
- **nhl94snes_SA1_five.sfc: three of the four fail.**
  - L+R never pulls: 0 of 12 at every hold length, both pads, twice from fresh boots. The press is seen: the count
    at BW $7EF0 goes to 24 on the first frame of L+R and counts down to 0, which on the LoROM build is followed by the
    pull within 15 frames. Here tmgoalie never changes, in BW-RAM ($77AA) or work RAM ($17AA).
  - Edit Lines lists all 22 skaters, but picking one already on the line leaves him on it twice and drops another
    (4-5 of the 22 picks a row, on every line).
  - The extra attacker isn't swapped: the line [18, 17, 7, 3, 12, 4] with 4 (the extra attacker) picked at LD reads
    [4, 17, 7, 3, 12, 4].
  - The new code's `jsl` targets match the LoROM build's routine for routine (the same code, variables +$6000). The
    beep's target on the SA-1 build is its SNES-only wrapper.
  - Injury counts (BW $40:5400): cleared at the start of a game, and halved at an intermission (3, 5, 127): pass.
- **nhl94snes_SA1_maxboost.sfc: fails.** 41 of 88 rating cells right. All 47 wrong ones are cold players showing their
  ordinary rating (Agility 65 for a -10, Speed 49 for a -7 ...). Its code is the LoROM build's but for the store
  ($60A5 for $00A5): `lda $16 / cmp #$80 / bcs` to `lda #100 / sta`. Whether direct page $16 holds the hot / cold
  value there on the SA-1 build is the question.
- **The hot / cold bug is in all four builds** (the `lsr / lsr / bit #$00 / beq / ora #$00` bytes: $FD34B in the SA-1
  builds, $FD279 in the LoROM ones, as retail's $FD237), so show max boost means the same there.
- **RAM.**
  - In a whole computer game nothing writes the SA-1 builds' BW $40:7EF0-7EF3 (the L+R counts) or $40:5400-547F (the
    injury counts), nor the LoROM build's $7E:F040-F0BF or work RAM $1EF0-1EF3 (`snes_ram_use_check.py` masks).
  - In the Shootout-mode runs (the computer-only Shootout mode that hangs or crashes on these builds) BW $7EF0 and
    $7EF3 were written on nhl94snes_SA1.sfc, $7EF2-7EF3 on nhl94_2026.sfc, and work RAM $1EF0-1EF3 on all three 2 MB
    builds; never on retail or Classic.
  - At boot the game clears them. Junk (23) written at power-on over the L+R and injury counts, and at BW $40:F000,
    was still there after the first frame and gone (0) by Game Setup, on both five builds. So a stale count can't
    carry over from an earlier session's save memory.

### Bot versions 58-59, and what 16 games can tell apart (2026-11-12)

- **People's slot slapshots** (138 from 40-130 out): skating across 0.5+ a frame 26% scored, standing 15%. Aimed at a
  post 20-29% (far 28%, near 29% for the moving ones: 29 and 49 shots), at the middle 0 of 20. The user: the best are
  taken skating across, aimed at the far post. Their wind-up: C held a median 36 frames (quartiles 32-38), speed
  23,600 at 35+ frames; by Shot Power 3 18,300, 4 22,100, 5 25,200. The bot's slapshot held Down (the low middle) and
  wound up 20 frames.
- **Version 58** = 57 with the slapshot aimed at the far post (aim code 2 is the +x post at the +y net, 6 the -x post;
  the reverse at the -y net) when skating across, else at the post away from the goalie, and standing a third as often.
  48 of its slapshots skating across went at the far post.
- **Version 59** = 58 with a 36-frame wind-up, and the slapshot (people_carry's and in place of 32's wrist shot) with
  the goalie square on 57's test only 30% as often.
- **The noise.** Version 57's first 16 games scored 3.69 a game, its next 16 2.06; over 32 games each, version 57 2.81
  ±0.38 goals and 3.33 ±0.25 xG a game, version 58 2.94 ±0.27 and 3.47 ±0.27, version 59 (16 games) 2.62 ±0.42 and
  3.58 ±0.38. Goals vary by about 2 from game to game, so 16 games can't tell versions apart by half a goal, and the
  "3.7" for version 57 above was mostly luck. Since version 54 the bot's goals against the computer have stayed at about
  2.5-3.1 a game; the changes since have made it shoot more like people (by Shot Power, at the posts, with their
  wind-up, when the goalie is pulled across), which the computer goalie, who saves nearly every long shot, doesn't
  reward. **Version 59 is the default**: equal on results, the most like people. Further changes: compare on xG over
  32-48 games a side, and on the user's games against it.

### All-Star teams on the original SNES matchup screen (2026-11-12, for NOSE4Web: the commissioner's glitch was an empty team Name)

Retail NHL94.smc, Game Setup's Home and Visitor stepped to the All-Star teams (26 East, 27 West; HomeTeam $1C98 /
VisTeam $1C9A), screenshots of the matchup screen every 240 frames as the text types (`runs/allstar`): East against
West, East at home to Montreal, Montreal at home to West. **No glitch in any of them.** The text types out whole from
"Hi, I'm Ron Barr" to "Press Start to begin": "Welcome to a sold out Madison Square Garden. Tonight's National Hockey
League game features the All Stars West and All Stars East.", "All Stars West has been playing extremely well
recently.", "For All Stars East Kirk Muller, ...", "...features the Montreal Canadiens and All Stars East." The
All-Star teams' empty name adds nothing and the box carries on (no stray text, the top of the screen as usual). So the
original game types an All-Star matchup cleanly; the commissioner's empty name must differ from the All-Stars' in some
way the text player cares about.

### NOSE4Web's SA-1 fix (9ac24df), played: the failures stand (2026-11-12)

The rebuilt nhl94snes_SA1_five.sfc / _maxboost.sfc and the SA-1 32-team nhl94_2026_five.sfc / _maxboost.sfc. The three
references are fixed in the bytes (`sta $00A5` at the max boost site, `adc $00AF` at $DFFF2, `ldy $0091` at $F7FAC), the
changed places the same as before. Played on nhl94snes_SA1_five / _maxboost (`snes_2mb_hacks_check.py`, the boot states
made again from the new ROMs), **every result is as before the fix**:
- L+R: 0 of 12 at every hold length. By hand: the count at BW $7EF0 goes to 24 on the first frame of L+R and down to 0,
  and tmgoalie stays 0 in BW-RAM ($77AA) and work RAM ($17AA).
- Edit Lines: 22 skaters a row, 4-5 of the 22 picks a row leaving a player on twice. The extra attacker isn't swapped:
  picking him (4) at LD gives the home line in BW-RAM [1, 4, 17, 7, 3, 12, 4, 0], player 4 twice. Work RAM's $1CE4 stays
  all zeros, so the game keeps its lines only in BW-RAM, and this isn't a read of the wrong memory.
- Max boost: 41 of 88 cells right, the same cells and values as the unfixed build (the hot / cold rolls are the same each
  boot here): every cold player shows his ordinary rating.
- The injury counts work on both SA-1 builds. On nhl94_2026_five (BW $40:5400): $5A over them at Game Setup is 0 at play,
  and counts of 7, 10 and 255 are 3, 5 and 127 after an intermission (read at the same addresses: by then the away object
  holds another player, so reading by the object's player gave 0 for the away one).
- Boot clears the counts on nhl94_2026_five as on the others ($40:7EF0-7EF3 and $40:5400-547F junk at power-on: 0 by
  Game Setup).

### Bot version 60 (EA Special and cross-crease) and passing, measured (2026-11-12; `bot_compare.py`)

- **`bot_compare.py 59 60 32`** (paired on the same 32 seeds and matchups): xG 3.62 ±0.24 against 3.28 ±0.36 a game
  (difference -0.35 ±0.41), goals 2.78 against 2.56 (-0.22 ±0.40), shots on goal 12.8 against 11.1 (-1.7 ±0.9), xG
  against 2.90 against 2.15 (-0.74 ±0.37, the only difference near 2 standard errors). Pairing narrows the spread
  little: the same seed gives a different game once the bot plays differently.
- **Its plays** (`scoring_moves.py`): EA Special attempts 0.16 a game (people 0.79: version 8's line, started from a
  plan drawn on 6% of zone entries, rarely reaches its release spot), cross-crease 0.69 a game (people 0.86) but 5%
  scored, xG 0.124 (people 33%, 0.379): its run across isn't the fast one in close that leaves the goalie behind.
  **Version 59 stays the default.**
- **Passing is not a gap.** Version 59's passes (32 games) against the coaches rated 80%+ (28 side-games): reached a
  teammate (completed, one-timer, pass shot) 71% and 71%, intercepted 25% and 24%; the game credits 84% of the
  completed ones for both; one-timer passes 4.5 a game for both (never counted completed). The bot passes less (46 a
  game against 53), so the uncredited one-timers weigh more in its share: the game's counter 50% against 56%. It is
  intercepted more in the attacking zone (36% against 31%) and less in its own (15% against 25%). Left as it is.

### The bot's cross-crease, diagnosed and rebuilt (2026-11-12, version 61)

The user: improve the bot's cross-crease, after finding what fails. The move (GENESIS_GUIDE, GENESIS_SHOOTING 5.7):
straight across the front of the net close in at full speed, the computer goalie trailing the puck's line by more than
his reach; people shoot while he catches up.
- **People's move, traced** (their 57 cross-crease shots, all recorded games, back 1.5 s, across measured in the
  direction of travel): 1.5 s before, on the wing (-66 across, 164 out) coming at 1.29 toward the net and not across;
  1.0 s -53, 124 out, 0.86 across; 0.6 s -27, 98 out, 1.28 across; 0.3 s at the middle, 74 out, 1.53 across; at the shot
  +24, 51 out, 1.31 across and 1.28 toward the net. **A cut across the slot at speed, not a stop and a slide.** Against
  the computer goalie (32 of the shots): 34% scored, xG 0.282, 57 out, 25 across, speed 12,000 (median), 21 aimed the way
  they move, 17 high, the goalie 5.8 off the line; against a person in net (25) 28%.
- **Version 60's play, traced** (the bot's own log, 8 games, 26 plans): down the wing straight at the net (about 2 a
  frame), set up only 40 out, then across at 0.06-0.65 a frame while still carrying its speed in; 24 of 26 lost the
  puck in the crease 25-35 out, before any shot.
- **Version 61, step by step** (8-game recordings with the cross-crease on half the zone entries, its shots against
  people's against the computer goalie):
  - the d-pad held sideways: the speed toward the net carried on, the run slid to the goal line (shots 22 behind it);
  - a stop near the dot, then steered by velocity (the d-pad toward the wanted velocity less his own, as version 8's EA
    Special): held 39 out, but crossed at 0.8 a frame; the goalie kept up and the puck was lost;
  - **people's cut**, steered by velocity, no stop: 1.5 across and 1.35 toward the net from the wing (35+ across,
    95-175 out); its shots now 1.4 across a frame, but none of 60 scored;
  - **the aim**: the wrist shot's own rule (the half away from the goalie) sent 36 of 58 back against the motion, all
    mid height, xG 0.032 with the goalie 8 off the line; aimed high the way he moves (code 1 high +x at the +y net, 7 high
    -x, reversed at the -y net): 50 of 55 so, 1 scored;
  - **where it shoots**: deciding inside 60 out, the run had carried it 57 across (xG 0.066); deciding at the middle,
    the puck leaves about 30 past it (the release ~20 frames after the decision);
  - **the shot's speed**: on target (60 of 64 saved), but slow (9,300 against 12,000). C held 4 -> 8 -> 12 frames:
    speed 10,700 -> 12,100, scored 5 of 60 -> 4 of 40, xG 0.102 -> 0.150. Deciding 10 before the middle with the long hold:
    the goalie not yet pulled across (4.7 off the line), 2 of 38.
- **Version 61's settings** (CROSS61): the cut above, the shot decided at the middle with the goalie off the line or 8
  past it anyway, aimed high with the motion, C held 12 frames; drawn on 6% of zone entries (people about 0.9 a game).
  The cross-crease went from 0% scored (xG 0.03) to about 10% (xG 0.15) of its shots; people 34% (0.28). Measured
  against 59 with bot_compare.py (below).

### NOSE4Web's 36d0a51 and the probes (2026-11-12)

- **L+R pull, fixed**: nhl94snes_SA1_five.sfc and nhl94_2026_five.sfc pull at every hold from 2 frames to 120 (12 of 12),
  a second press brings the goalie back, nothing in a stoppage, nothing after L+R in a whistle or a pause, and with both
  pads on the home team only pad 1 has it, as on retail and the LoROM build.
- **Probes** (scratch copies: the hook's jump sent to a probe in free ROM, $9B:CDFE and $9F:FC48, that saves registers
  and direct-page bytes at BW $40:F000 up and goes on to NOSE4Web's code):
  - the extra attacker code ($9B:FFBE) is reached, once a pick, with **D = $3000, S = $1FE9, DB = $9F**; dp $A5 (d0) =
    $7CE5 (the line's LD slot) and a3 ($95-$97) = $00:7CE4, the line in BW-RAM; absolute $00A5 read through DB $9F
    gives $0000;
  - the max boost code ($9F:FFEF) is reached once a rating cell, with D = $3000, S = $1FC3, DB = $9F; **$16 is the hot /
    cold byte** (Agility's 246, 247, 250 = -10, -9, -6, and 12, 1, 2 for players 16-23, as the table) and $14 its value
    divided by 4.
  - So these routines run with D = $3000, not $0000: absolute $00xx operands (the 3-byte forms NOSE4Web's fixes used)
    miss the variables; direct-page operands follow D.
- **Version 61 against 59** (`bot_compare.py 59 61 32`, paired): xG 3.30 against 3.62 a game (-0.32 ±0.27), goals 2.62
  against 2.78 (-0.16 ±0.34), xG against 2.38 against 2.90 (-0.51 ±0.35): equal within the noise. Its cross-crease
  (`scoring_moves.py`, 32 games): 1.22 a game (people 0.86), 13% scored, xG 0.187 a shot (59's shots that happened to
  cross the middle: 0.53 a game, 12%, 0.174; people against the computer goalie 34%, 0.282). **Version 61 is the
  default**: equal on results, the move strong coaches use about once a game in people's shape, aim and wind-up.

### NOSE4Web's "energy from hits only" builds, whole games (2026-11-12, 83f3f14)

nhl94_hits_only.bin (SHA-1 02a9199e...; skating free, burst 0, knockdown 1,365, hold 683) and NHL94_hits_only.smc (SHA-1
e7887ef4...; skating free, free burst, energy takes all of the speed, the same costs), against nhl94.bin and NHL94.smc:
`gen_injury_baseline.py` / `snes_injury_baseline.py` (the computer against itself, 12 games each, the same seeds,
5-minute periods, line changes on), with `energy_track.py`'s per-skater figures (full energy 4,096; a third 1,365;
each game second of running clock). Means a game (original -> hits only; ± standard errors):

| | Genesis | SNES |
|---|---|---|
| Shift ends (line changes) | 88.7 -> 92.4 (+0.6 se) | 114.5 -> 116.5 (+0.3 se) |
| Mean energy on the ice | 3,656 -> 3,672 | 3,731 -> 3,707 |
| Lowest energy anyone reached | 1,568 -> 0 (11 of 12 games 0) | 1,573 -> 57 (10 of 12 at 0 or 1) |
| Skaters below a third | 0.6 -> 4.1 | 0.3 -> 3.3 |
| Skaters at empty (0) | 0 -> 1.4 | 0 -> 1.2 |
| Longest a skater stayed on the ice below a third (game s) | 7 -> 100 (44-233) | 7 -> 71 (22-128) |
| Longest bench stint of a skater who had played (game s) | 319 -> 337 | 463 -> 579 (+1.7 se) |
| Knockdowns | 22.4 -> 30.2 | 29.2 -> 39.4 |
| Held / hooked | 24.6 -> 21.9 | 14.2 -> 15.8 |
| Injuries (12 games) | 0 -> 1 | 5 -> 7 |

So the computer changes lines as often as before and the average skater on the ice is as fresh, but three knockdowns
empty a skater, and the computer leaves the one or two it has worn down on the ice a long time: every hits-only game had
a skater below a third for 22 game s or more (most 44-233 on the Genesis, 22-128 on the SNES, where that energy is his
speed), where the originals had none past 61. Knockdowns rose by a third on both (more players worn down: not measured
why). The longest bench stints are skaters who played early and then sat (a whole period and more on both ROMs).

### The bot's cross-crease shots, sorted by the play behind them; versions 65 and 66 (2026-11-12)

`bot_record.py` with NHL94_BOT_LOG=1 now keeps the bot's log beside the matches, each entry stamped with the emulator
frame (`ef`), so a match file's shots can be tied to the bot's decision behind them. People's cross-crease shots
(`scoring_moves.py`'s rule; coaches rated 80%+): 24, 33% scored; against the computer goalie 14, 29% (xG 0.31 a
shot, 65 out, 35 across at release, shot speed 15,100, 36% slapshots), against a person's goalie 10, 40% (41 out, all
wrist shots).
- **Version 63's (32 games: 145, 7% scored, xG 0.111):** 47 across at release (the far post), speed 11,300. In 9
  logged games 22 of 39 were 32's ordinary wrist shot fired while sliding across (decided at 44 across, speed 9,700, 0
  scored), 10 the planned cut (48 across, 23 frames after its decision, 1 scored). The user: "if you wait until you're
  past the far post, that's too late for the cross crease shot to be taken."
- **Version 65** (the cut decided 12-16 short of the middle, CROSS65): against 63 goals -0.12 ±0.37, its
  cross-crease shots 140, 5% scored, median 40 across: the timing of the planned cut alone changes little.
- **Version 66** (CROSS66: no ordinary wrist shot while moving across 1.0+ a frame once 15 past the middle; before
  it the cut's 12-frame wind-up, high the way he moves; the cut decided 20-24 short of the middle): against 63 (32
  paired games) xG 5.07 against 5.58 (-0.52 ±0.53), goals 2.53 against 2.97 (-0.44 ±0.30), shots on goal -3.0 ±0.9.
  Its cross-crease shots now in people's shape (94: 36 across, speed 14,100, 35% slapshots, 78% at the far post) but
  **1 scored** (xG 0.117 a shot). **63 stays the default.** People's 29% against the computer goalie rests on 4 goals;
  the xG model rates their shots 0.31 to the bot's 0.12 for reasons not in these measures.

### Bot version 67: the slot instead of the crease (2026-11-12)

`analysis/bot_games_report.py --test` on version 63's 32 compared games against the coaches rated 80%+: ordinary
shots 29.8 a game (people 12.6; the bot plays the computer), 11.2 of them from within 40 of the goal line (people 2.5),
7% scored (18%), slapshots 13% of them (26%), one-timers tried 3.6 (5.0). In 9 logged games the drive at the net
(version 62's zone_hold with a clear lane) shot 9.9 times a game from within 40 out and scored 3 of 89; the wrist
shots from 40-80 out scored 8 of 77. **Version 67** (SLOT67): a clear lane takes the carrier to the slot (62 out);
there an open teammate across gets the one-timer pass, else the shot (wrist or slapshot by Shot Power). Against 63 (32
paired games): goals 3.00 against 2.97 (+0.03 ±0.48), xG 5.92 against 5.58 (+0.34 ±0.43), shots on goal +2.4 ±1.1;
shots within 40 out 6.7 a game (63 11.2), 40-80 out 17.1 (10.8), one-timers tried 4.0 (3.6), one-timer shots 4.2 (3.7),
slapshots 15% of ordinary shots. **Version 67 is the default**: equal on results, closer to people's attack.

### Bot version 68: slapshots on the forehand (2026-11-12)

The bot's slapshot share (13-15% of its ordinary shots; strong coaches 26%) mattered less than their quality: from
40-130 out the coaches' slapshots scored 35% (54 against the computer goalie: 35%; xG 0.30), the bot's (67) 4% of 109
(xG 0.17), at a median speed of 21,500 against 17,200. People hold C for a median 0.56 s (real) on a slapshot (the
pads in the match files), the bot 36 frames: the same. A shot is a backhand, a quarter weaker, when the net lies
45-180 degrees round to the backhand side of the shooter's facing (GENESIS_SHOOTING 4.3); in the recordings that rule
splits slapshots into fast (forehand, the net straight ahead or up to 135 degrees round toward the forehand: about
19,000-25,000) and slow (about 14,500-19,500). People took 54 of 70 on the forehand, the bot (67) 46 of 109. **Version
68** (SLAP68) slaps only with the net on the forehand when C goes down (else the wrist shot), at twice the chance (at
most 0.9). Against 67 (32 paired games): goals 3.41 against 3.00 (+0.41 ±0.39), xG equal, xG against -0.20 ±0.24; its
slapshots from 40-130 out 68% on the forehand at the shot, median 19,500, 6% scored (5 of 84); the slapshot share still
14%. **68 is the default.** **Version 69** (SLAP69): the aim held through the wind-up turns the skater (32% of 68's
slapshots were backhands at the release): C alone, the aim only in the last 6 frames. Against 68: on 32 paired games its slapshots from 40-130 out
scored 12 of 82 (68: 5 of 84), 72% on the forehand; on 64 goals +0.31 ±0.27 but goals against +0.33 ±0.15 (xG against
+0.21 ±0.15), even overall (with no direction held through the wind-up the shooter stops skating, perhaps out of
position for the way back: not checked). **68 stays the default.** Checked (2026-11-13): 69's goals against don't follow
its slapshots (1 of 84 within 6 s real of one; the other team's shots in the 15 s real after them 92 against 68's 107);
the extra goals against were power-play goals (8 -> 18) and one-timers (20 -> 30). On 127 paired games: slapshot goals 44
against 29 (xG 90 against 94), but goals +0.10 ±0.19, goals against +0.18 ±0.12 (xG against +0.12 ±0.10): even. Where
the goals against differ (paired, 127 games): the computer's breakaways are as many (3.04 against 3.06 a game) but
scored more (0.17 against 0.10, +1.75 SE); the bot's penalties as many (1.98 / 1.93) but more power-play goals against
(+0.12 ±0.06); one-timer xG against +0.12 ±0.05 (2.3 SE) with every other xG against equal (1.90 / 1.90), and those
extra one-timers came away from the bot's shots (none within 10 s real: 238 against 208, xG 45.8 against 32.9; after
its slapshots 13 against 18). Nothing ties them to 69's change (the wind-up only), so most likely chance across many
measures; no defensive fix suggests itself.

### Icing options played: Genesis hybrid 82a9a22, SNES crease window and hybrid b98739a (2026-11-13)

`gen_hybrid_icing_check.py` / `snes_hybrid_icing_check.py` (computer games, penalties on, line changes on, the away
skaters' Aggression raised; every frame the icing flags: each arming, each crossing with both teams' distances by the
build's rule, the outcome, the stoppage and the faceoff spot), 19 Genesis games on the hybrid builds (11 nhl94, 8 CDL),
2 retail; 11 SNES on NHL94_icing.smc, 8 on the SA-1 build, 4 retail. `snes_icing_crease_test.py`: the crease window
forced.
- **Calls (Genesis 11, SNES 20):** at the crossing (the clock stopped 0-1 frames later), the defenders as near or
  nearer every time (ties called: 0-0, 36-36), the faceoff at the icing team's end-zone dot, but once: a delayed
  penalty against the other team already in PenBuf ($1A on away object 10) when the icing went in, and the faceoff went
  where that penalty put it (the neutral dot, y -65): the game's own handling of two stoppages, not the hack.
- **Wave-offs (Genesis 9, SNES 7):** the attackers nearer every time; play went on (the next stoppage 94-2,646
  frames later).
- **"Open for a frame":** a crossing read with ifcgl set and ifok still set, decided the frame after (Genesis CDL once,
  waved; SNES once, called): the games' logic isn't locked to the video frame, so a read can fall between the build's
  bset and its decision. Both came out right.
- **Short-handed:** no team was ever armed while short-handed. Once (CDL) a team at tmap 5 against 6 was called at
  the crossing: equal when the puck was shot (the arming), a man came out of the box while it travelled.
- **Line changes on, players in the box (tmap 5 cases), the goalie pulled (not seen):** nothing odd.
- **The SNES crease window (forced, both builds and retail; a puck at x, sent fast across either goal line with
  icing armed):** |x| 40 and 44 dropped (ifok cleared, no crossing), 46, 48 and 60 crossed; retail crossed at all of
  them. Within |x| 20 the net and goalie stop the puck on all three. In play the window can't be told from
  updateplayers' early wave-off (a defender or the goalie within 30 of a slow puck), which kills most SNES icings
  before the line (about 35-60 a game in computer games, retail too).

### NOSE4Web's SNES shootout injury skip 8212db9, played (2026-11-13)

`snes_shootout_injury_check.py` on NHL94_shootout_injuries.smc and nhl94snes_SA1_shootout_injuries.sfc (the tied
game into the season shootout after one overtime; listed shooters marked $FFFC in the saved tmpdst, $7E:F37F / $40:4A8F;
the shootout kept level to round 7-8; each turn's BA_Skater_Offset against the entry the build should take):
- **default** (home entries 1 and 5, away entry 3 injured): round 1 home took entry 2; round 5 entry 5 out, 1 out, so
  2; round 6 (entry 1) 2; away round 3 and round 8 entry 4. Every turn as expected, both ROMs.
- **picked** (home entry 2 replaced by another skater, as the lineup screen would, and him injured): rounds 2 and 7
  took entry 3.
- **unmarked** (the mark $7E:F0F0 cleared at the shootout's start): every listed shooter shot, injured or not (the
  original, as in Shootout mode).
- The recorder's shooter is BA_Skater_Offset, so it logs the stand-in.
- **20149ad, fightinj kept** (copied to $7E:FE00 on the LoROM 2 MB build, $40:5800 on SA-1, by a hook on PlayShootout's
  `jsl StartGame_go` while the mark is set; the skip passes a player whose copied byte is set): nhl94snes_SA1_
  shootout_injuries.sfc (1d1e8f76...) and nhl94snes_2026_shootout_injuries.sfc (ad23ce98..., LoROM 2 MB), the three
  cases above plus **fight**: home entries 1 and 4 hurt in a fight (fightinj and fightinjany set) with their majors
  still running at the end of overtime (tmpdst box time $00B4, not $FFFC). At the shootout the copy held exactly those
  two roster places, the saved tmpdst still box time, and both were skipped through round 8 (round 4 to entry 5, round
  1 and 6 to entry 2). All four cases right on both ROMs.

### NOSE4Web's fighting penalty time e5238ca, played (2026-11-13)

`fight_time_check.py genesis|snes` (computer games with fights; every box stay followed: its word, the seconds served
by the clock, the penalty minutes before and after, both teams' tmap while in; a fight's two fighters paired by the
clock when they went in). All builds at 120 s:
- **Genesis** (nhl94_fight_time.bin 9 fights, the same with the injury roll forced 6, nhl94_fighting_blood.bin 12 as
  the baseline): 120 s ($2078 -> $6078 coincidental -> $4078), served 120-125 by the clock (baseline 300, served
  304-309), 5 PIM each, the teams' strength while they sit as with ordinary fights (mostly 6-on-6; 5-on-6 from other
  penalties, as in the baseline). Minors 120 s, and 60 s on nhl94_fight_time_pt30.bin. No fight injury came up in
  the forced games, so a loser's $1000 under the new time wasn't seen.
- **SNES** (NHL94_fight_time.smc with every fighting rating at 14, nhl94snes_2026_fight_time.sfc, its pt30 copy, the
  SA-1 build; nhl94snes_2026.sfc the baseline): 120 s, served 118-120 (baseline 300 / 299), 5 PIM each, minors 120 s
  (60 s on pt30). **But on the 2 MB build fights no longer keep full strength:** the baseline's fighters sat with both
  teams at tmap 6 (9 of 10 fights), the fight-time build's at 5 / 5 (4-on-4) and sometimes 4 / 5. McMarkis's
  FightCoincidental (InProgress, after the store; SA-1 source e3398fc2) marks two fighting majors coincidental only
  when the new word is $212C ((5*60)|$2000) and the other's time is 300, so a fight time of anything else never pairs.
  Its two constants want the set seconds. The 1 MB fighting (McMarkis's d862d933, before e3398fc2) has no pairing at
  all: its fights are 4-on-4 with or without the new time.

### NOSE4Web's Genesis shootout injury skip f4ad85d, played (2026-11-13)

`gen_shootout_injury_check.py` on nhl94_shootout_injuries.bin (e43d7d4b...) and nhl94_shootout_injuries_fighting.bin
(82650eed...): a tied overtime into the season shootout, kept level to round 7 (14 turns a case), each turn's
BA_Skater_Offset against the expected entry, and the helper's reading (genesis.View, Recording.shootout_attempt)
alongside. Home list (roster) 11, 2, 6, 16, 17; away 12, 3, 7, 17, 16. All right on both ROMs:
- **default** (saved tmpdst: home 11 $FFFC, 17 $1000 (a served fight major); away 7 $512C (one running)): rounds 1 and 6
  home 2 for 11; round 5 home 17 out, wraps past 11 to 2; away round 3 17 for 7.
- **picked** (home entry 1 replaced by roster 3 and him $FFFC): rounds 2 and 7 took 6.
- **mode** (Shootout mode from the menu, home 11 marked $FFFC): the original order, 11 shot.
- **fight** (in overtime, before the save: home 11's live tmpdst $512C, 16's $1000): the saved words read $512C and
  $1000, and both were skipped (11 by 2 in rounds 1 and 6, 16 by 17 in round 4).
- The recorder's shooters were the stand-ins every turn. The fight words were set in RAM, not made by a fight.

### chaos's Genesis fight injury ($112C) over a game (2026-11-13, `gen_fight_injury_track.py`)

nhl94_fighting_blood.bin, computer games, Fighting On, the fight ratings at 14 and (`--force`) every +$75 at $7F so the
patch's roll hurts the loser (4 normal games gave none). The patch puts the loser through setInjuryType ($FFFD / $FFFC)
and overwrites his tmpdst with $112C ($1000: not counted against tmap; 300 s). Four fight injuries (P2 once, P3 three
times, one into overtime), all alike: the fight's coincidental major goes on top at once ($712C: AddPenalty keeps bit
$1000 of a word already in the box), $512C at the faceoff ($2000 "just called" cleared), counting down a second at a
time with $4000 | $1000 kept; when the 300 s run out, updatepentime's coincidental path finds bit $1000 gone from the
borrow ($5000 -> $4FFF) and sets **exactly $1000**, off the box list (an ordinary coincidental penalty borrows into
$3FFF, finds the bit and clears the word to 0: back on the bench). $1000 stays across period breaks and into overtime;
he never came back on the ice. Only at the end of the game ClearPenalties (clockcont_0 `.eog`) puts everyone at
$FFFE. A tied regular-season overtime takes `.eog` too (`tst OptPlayMode / beq.s .eog` at $7C4C), which would clear
every tmpdst before the shootout; NOSE4Web's season-shootout build NOPs that branch, so the words reach the shootout's
save intact. Not seen: a fight major that isn't coincidental (it would count the whole word down past $1000 and leave
the team a man short from $0FFF on). Nothing in the original code sets $1000 on a positive word except keeping it,
so a positive word with $1000 set is chaos's fight injury.

### NOSE4Web's hybrid icing 82a9a22 (Genesis), read (2026-11-13)

nhl94_hybrid_icing.bin (SHA-256 9f377e58...) and CDL_Season_12_hybrid_icing.bin (1e8bfbea...). Their reading of the
icing code agrees with the one below. The bytes (capstone over each against its original):
- **nhl94:** $102A0's `bset #ifcgl,(iflags).w` made `jsr $FFAC6` (the `rts` after it kept); the new code at
  $FFAC6-$FFB6B over the boot checksum routine at $FFAC0, whose call at $300 is three NOPs (header checksum updated).
- **CDL:** the same code, byte for byte, at $1ED0BC; an earlier hack's block moved from $1E2B5A to $1ED032 (the same
  bytes, its one branch PC-relative) and its three jsrs ($1018C, $1494E, $F6CE8) moved with it, entry points $1ED032
  and $1ED046.
- **The code:** saves d0-d4/a0; the bset; the line y = +206 when ifdir (the top end) else -206; for each team (the
  icing team by icingPlayer < 6: objects 0-5 home, else 6-11) its skaters' least distance to the line, in y only
  (past it: 0), skipping `position` <= 0 (the word: goalie 0, off the ice negative, as the game's own loops test it) and
  pf2unav (pflags2 +$63 bit 2); defender <= attacker: registers back, a3 = the icing player's record (pushed / popped),
  `move.w #$C,d0 / jsr AddPenalty ($11F2C)`; else `bclr #ifok` and registers back. AddPenalty keeps d1/a0/a1 and only
  queues it (PenBuf); checkfornewpen stops play on the next PenaltyManager pass. Ties go to the defenders (called).
- **Points to watch in play:** the distance is y only (a skater on the far boards counts as near as one by the dot);
  a skater already past the line counts 0 on either side, so a deep attacker ties a deep defender (called).

### How each game calls icing, for a hybrid icing option (2026-11-12, for NOSE4Web; code readings)

**Genesis** (logic94.asm; nhl94.bin): iflags $FFBF80 (bit 0 ifcgl crossed, 1 ifdir must cross the top line, 2 ifok
armed), icingPlayer the byte after it.
- **Armed on every touch** (a2touchpuck's `.notice`, after the touch bookkeeping): iflags cleared, icingPlayer = the
  toucher; ifdir set if he shoots up; armed (ifok) only if the puck is in his own half (y toward the goal he attacks
  not positive) and his team isn't short-handed (its tmap not below the other's).
- **The crossing** (`PuckIChk` at $10246, from pucknorm while nobody has the puck): armed and not yet crossed, the
  loose puck past the far goal line (Blueline + goalline): **within 44 of the middle (|x| <= $2C) icing is waved off**
  (the puck went at the net); outside it ifcgl is set.
- **The call** (the same a2touchpuck code, next touch): crossed, and the toucher is a skater of the other team (not a
  goalie): `move.w #PenIcing,d0 / bsr AddPenalty` at $101EE for icingPlayer. A touch by the icing team's skater or
  either goalie re-arms from that touch instead (waved off). PenIcing ($C) is always called (AddPenalty skips the
  penalties-off test), has no minutes, so checkfornewpen stops play at once (`Stop4Pen`): the faceoff y is +-600 by the
  icing player's goal, clamped to the end-zone dot (y +-206, x +-70 on the puck's side), then `limitfo`.
- **Also reads it:** the computer goalie (checkanim `.22`) goes out to a loose puck only when no icing is pending.
  Cleared at every faceoff setup and period start.

**SNES** (NHL94SNES routines; NHL94.smc): iflags $7E:0CF1, the same bits; icingPlayer its high byte.
- Armed the same way (a2touchpuck, the same own-half and not-short-handed tests).
- **The crossing** (`PuckIChk`, from pucknorm): **any** crossing of the far goal line ($108) sets ifcgl (`tsb` at
  $9E:F783); no window in the middle.
- **A wave-off the Genesis lacks** (`updateplayers`, $9F:88BD-$9F:88F0): before the crossing, a player of the team
  that didn't ice within 30 of the puck while it is low (z < 13) and slow (|vy| < $2400) cancels it (he could have
  played it). (2026-11-13) The within-30 test runs for every object below $18 after the nearest-player bookkeeping,
  which alone skips goalies, off-ice and unavailable players: so **a goalie counts** (the defending goalie by his net
  with a slow, low puck coming waves it off). The crease: updateplayers keeps a goalie in it at x $FFD5-$2B and y
  +-$E5 (`.t3x`), so the Genesis's +-$2C window fits the SNES too.
- The call, the faceoff spot (`Stop4Pen`: +-600 by the icing player's goal, then the dot) and the computer goalie
  staying in while icing is pending (`assgoalie`) as on the Genesis; cleared at puckfaceoff2.

**For hybrid icing:** the natural moment is the crossing (Genesis where `PuckIChk` sets ifcgl; SNES at $9E:F783). Every
object's position and speed are there (Genesis +$00 / +$14, +$28 / +$2A; SNES $0D55 / $0DB7, $0EC3 / $0EE3), the teams
by object (Genesis 0-5 / 6-11; SNES pfteam), goalies by position 0. A race to the dot on the puck's side (x +-70, y
+-206 at that end): the icing team's best time against the other team's; the other team first: call it then
(AddPenalty with PenIcing for icingPlayer, as the touch does); the icing team first: clear ifok (waved off). The
short-handed exception stays in the arming (3-on-3 overtime's tmap counts included).

### NOSE4Web's 3-on-3 overtime 92801c0 (each team at most the other's tmap + 2; the SNES code moved), played (2026-11-12)

nhl94_3on3_ot.bin 2152ba0c..., CDL_Season_12_3on3_ot.bin 734dbe47..., NHL94_3on3_ot.smc 13e8077b...,
nhl94snes_SA1_3on3_ot.sfc 46249978... `gen_3on3_ot_check.py` / `snes_3on3_ot_check.py` with NHL94_AGR_UNTIL_CROWDED=1
(the away team's aggression stops once three of a team are in the box, so they can come out).
- **Genesis, 6 overtimes:** 5-on-3 (tmap 6 against 4, two in the box) in four of them; **three in one box: 4-on-2**
  (tmap 5 against 3: the other team's +2 now limited to the penalized team's tmap + 2), OT 7:52 and 6:59 in seed 5,
  with 5-on-3 between them when one came out (7:40); from 5-on-3 back to 4-on-3 as the penalties ran out (seed 3). The
  full return to 3-on-3 after a crowded box didn't come up before the runs' end (15,000 frames). No short draw.
- **SNES (all its code moved; 4 retail, 3 SA-1 forced, 4 retail and 2 SA-1 ordinary):** 3-on-3 at every even
  draw, 4-on-3 both ways on both ROMs, coincidental back to 3-on-3 and the return after a power play (SA-1 seed 2:
  4-on-3, 3-on-3 with one in each box, 4-on-3 the other way, 3-on-3 at 1:14); a penalty shot (tmap 1 for both, 4 after);
  the power-play clock counting down in step ("LA Pwr Play" 1:08 at OT 2:36, 0:53 at 2:21, SA-1). No 5-on-3 or three in
  one box: the computer's SNES penalties barely respond to the Aggression held in RAM (seed 1 played the same at 18 and
  19), so they don't pile up. No short draw.

### NOSE4Web's SNES 3-on-3 overtime (e95d330), played (2026-11-12)

NHL94_3on3_ot.smc (SHA-1 3748ff0f..., every overtime) and nhl94snes_SA1_3on3_ot.sfc (31e6b645..., regular season
only), `snes_3on3_ot_check.py` (snes_60fps_cvc's boot, the computer on both sides, the third period run out at 0-0
into overtime, the away skaters' Aggression ($1443) at 18 in overtime so penalties come; every 4 frames each team's
skaters by position, tmap $17A6 and its boxed players; each draw; screenshots, a burst of 8 when a power play
starts). 13 overtimes: retail line changes off (3, and 3 more for the bursts) and on (3), a home minor carried over
(1; a second run never reached overtime), SA-1 regular season (2), line changes off (2), playoffs (1).
- **3-on-3:** every even-strength draw C, LW and RD a side, both ROMs, line changes on and off.
- **Penalties:** 4-on-3 on both ROMs; at the expiry the released player comes on (4-on-4) until the next whistle. The
  carried minor opened overtime 4-on-3. A penalty shot in overtime set tmap 1 for both and 4 again after; one went in
  and ended the game. No 5-on-3 and no three in the box came up (penalties stack far less here than on the Genesis).
- **The power-play clock:** the scoreboard alternates the overtime clock with the power-play display; at 4-on-3 it
  read "MTL Pwr Play 0:09" at OT 1:38 for a penalty called at 2:02 and served until 1:31 (penalties scale with 5-minute
  periods: about 30 game s): right.
- **SA-1, playoffs:** 5-on-5 (the opening draw 5 a side; 5-on-4 and 5-on-3 power plays by the usual counts).
- **No short draw** in any of them.
- **Forced (Aggression 19 in overtime; 4 retail overtimes, 3 SA-1):** the cap (tmap at most 6 minus all a team's
  boxed players, at least 3) works: retail seed 2, the away team with three in the box at six draws (OT 2:25 to 0:45),
  each at tmap 3 with the goalie, C and LW. **At the same draws the home team was at tmap 6 (+2 for the away team's
  penalties): five skaters against two, a 5-on-2** (the NHL keeps a team at three skaters at least, so 5-on-3 at most).
  With one more home penalty, 4-on-2 (5 against 3 in tmap). A 5-on-3 proper (tmap 6 against 4) and the return to
  3-on-3 after three in the box didn't come up (that overtime stayed crowded to its end). No short draw; the SA-1
  build's overtimes 3-on-3 and 4-on-3 as before.

### NOSE4Web's 3-on-3 overtime (a91a6f8), played (2026-11-12)

nhl94_3on3_ot.bin (SHA-1 b00d6e60...) and CDL_Season_12_3on3_ot.bin (24882ae1..., regular season only),
`gen_3on3_ot_check.py` (the computer on both sides, the third period run out at 0-0 into overtime, the away team's
Aggression at 38 in overtime so penalties come; every 4 frames each team's skaters by position and tmap; each faceoff
drop's players and spots; screenshots). Cases: line changes off (3 overtimes) and on (3), a home minor carried over
from the third (2), regular season without the extra aggression (1), CDL regular season (2) and playoffs (1).
- **3-on-3:** every overtime's opening draw and the draws after whistles at even strength were C, LW and RD a side
  (both ROMs, line changes on and off; the units stayed C, LW, RD through the computer's changes), the C taking the
  draw, LW and RD on either side (screenshots).
- **Penalties:** one penalty 4-on-3 (the power-play team's LD comes on), two 5-on-3; at an expiry the released player
  comes back (4-on-4, or 5-on-4 from 5-on-3) until the next whistle, then the count goes back (3-on-3 / 4-on-3). A minor
  carried over from the third period: overtime opened 4-on-3. In play a team at tmap 4 also had a fourth skater (LD)
  for 556 and 904 frames, most likely the extra attacker on a delayed call's goalie pull (not confirmed: the goalie
  flag read was unreliable).
- **A faceoff 4-on-2:** off seed 2, OT 6:32: the away team had three in the box (4, its line 1 C; 5, the line's extra
  attacker; 18, its RD), tmap 4: on the ice its goalie, LW 8 and RD 21 (for 18), and no centre, although centre 6 (line
  3) was on the bench and free (tmpdst $FFFE); 1,088 frames stopped, then the draw 4-on-2.
- **The power-play clock:** right at 5-on-3 (1:30 shown), **0:00 at 4-on-3** (every 4-on-3 screenshot, the carried
  penalty's too): GetLowestPen's `cmpi #6,tmap` (the power-play team at 6) as expected.
- **CDL:** regular season 3-on-3 (all draws 3 a side); playoffs 5-on-5 (OT 5:00, the opening draw 5 a side, penalties
  by the usual 6-based counts).
- **Not tested:** a shootout (neither ROM has one), a person's goalie pull.
- **The rebuild (0c544c0: GetLowestPen's test at $12A50 counts the box in overtime)** changes the timing, so seed 2 no
  longer replays. `gen_3on3_ot_trace.py`, 12 overtimes on each ROM: **the build, seed 11, OT 9:01, the away team at
  the drop with its goalie, LW 9 and RD 18 only.** Its line 1: G 1, LD 17, RD 18, LW 8, C 4, RW 13, EA 5; in the box 4
  and 8 (tmpdst $78), 5 on the bench ($FFFE), tmap 4. SetPlList's centre slot tried 4 (refused) and **accepted 5**
  about 200 frames before the drop. PlList read all 0 at the drop (setpersonel clears each slot it gives an object),
  so 5 was given one, yet the objects were 18 (RD), 8 and 4 (in the box, position $FF), the goalie, an empty one
  (pnum $FF) and 9 (LW). setpersonel's second pass gives a player the first object not asked for this time that has a
  position (`tst.w position(a3)` / `dbpl`), else the last free one; a boxed player's object counts as free too, so 5
  most likely went onto a boxed object. Retail, 12 overtimes the same way: no short draw (the even-strength case with
  C, EA and a D in the box at tmap 4 was not set up).
- **The cause, caught again with every object tracked** (24 more overtimes; seeds don't replay: the core keeps some
  state from game to game): seed 21, OT 8:12, the away team at tmap 4 with its goalie, LW 10 and RD 17 only.
  SetPlList's centre slot refused 4, 5 and 6 (all in the box) and **accepted 15** (line 6's C); the LW slot took 10 for
  the boxed 9. No object took 15: **all six away objects were in use**, the goalie, LW 10, RD 17 and three players
  sitting in the box with their objects (18, 8 and 22; position $FFFF). The goalie, three skaters and three boxed
  players make seven objects for six, so the third skater has none. The first catch had three in the box too (4, 5,
  18); seed 11's had two and an empty object (not explained). With the overtime count the penalized team stays at
  tmap 4 however many are in the box, so this comes up whenever three of a team's players sit at once. Retail, 12
  overtimes with every draw counted: no draw with three of a team's players sitting in the box with objects (the 5-on-5
  rules give the power play instead), so retail's own case is still untested.
- **The fix (562f559: in overtime each team's tmap is at most 6 minus all its boxed players, at least 3; the faceoff
  takes row 0)**, nhl94_3on3_ot.bin 8cd044d8...: 24 overtimes, **no short draw**; all 33 draws with three of a team's
  players sitting in the box had tmap 3 with the goalie, C and LW on the ice. Seed 19 shows the return: G, C, LW from
  OT 8:13; at 7:13 a boxed player came out and joined play (three skaters), and the next draw (7:10) was 3 skaters at
  tmap 4. (The other crowded overtimes stayed crowded to their end: the away team at Aggression 38 is called all the
  time.) The seed-11 variant (two boxed, an empty object) did not come up.
- **The original game loses a skater the same way** (`gen_box_crowd_check.py`: retail, regulation, the away team at
  Aggression 38, every draw): game 1, period 3 at 3:22, the away team at tmap 4 with three boxed players holding objects
  (5, 17, 18; five boxed in all): on the ice the goalie, C and RD only, no LD; game 3, period 3 at 1:11, the same (4,
  20, 22 sitting; eight boxed): C and RD only. All 6 games: 8 draws with three of the away team sitting in the box,
  **all 8 a skater short** (tmap 4, the goalie, C and RD on the ice, no LD), in 4 of the 6 games. tmap's floor of 4
  (goalie and three) with three sitting needs seven objects for six.
- **The ordinary stacked case** (NOSE4Web: the commissioner has never seen a team down to two skaters): the same tool,
  8 retail games, the away team at Aggression 36, every draw with exactly three of a team's players in the box (two
  serving, one waiting at a full 2:00, tmpdst $78): **25 such draws, none short**; every time tmap 4 with the goalie, C,
  LD and RD on the ice. Of the three in the box at most two held a sort object (two in 18 draws, one in 5, none in 2),
  and the one waiting sometimes held one and sometimes not. So the limit bites only in pile-ups where three boxed
  players still hold objects (the Aggression 38 games: five or eight boxed over the game).

### NOSE4Web's "Calls during a delayed penalty" (86e06ef), played (2026-11-12)

nhl94_delayed_calls.bin (SHA-1 8b27117b...; from nhl94.bin: `bra.w` at $13EC4 to the rts, the usual boot checksum
NOPs), `gen_delayed_calls_check.py`:
- **Whole games** (the computer against itself, penalties On Except Off-sides, line changes off, 5-minute periods,
  every skater's Aggression held at 38 so checks are often called): the build 6 games, 181 penalties, 2 called on a
  team while the other's minor was pending (roughing, interference); retail on the same seeds 0 (6 games, 184
  penalties). Both cross calls ended in a whistle with both teams sent off. The penalty log (PenSumLength / 4) equals
  the teams' penalty counts in every game, both ROMs.
- **From a moment with one minor pending and both teams at six** (8 games, 10 trials each, the team with the puck at
  Aggression 38): the build called that team 4 times in 80 (cross-checking, slashing, charging, interference), retail
  once (interference: goalie interference skips checkagr, as before). **The fouling team holding the puck: play
  stopped the same frame (2 of 2); a loose puck: delayed, stopped 38 frames later when it was touched (2 of 2), as for
  any delayed call. After the whistle 5 and 5 on the ice (4-on-4) in all 4**; the goalies back in after every trial
  but one, the same on both ROMs. The pending call's goalie pull: frames with gmpendel up and a goalie out came for
  both teams, as on retail.
- **A goal with a penalty pending:** in the games, a goal against a full-strength team with its own penalty pending
  wiped it (PenGoalStuff clears PenBuf), as retail does. The scoring team can't have one pending: it must hold the
  puck to shoot, which calls its own pending penalty at once.
- Not looked at: the referee's arm on screen (gmpendel is one bit, so it is raised once).

### Calls during a delayed penalty, and 3-on-3 overtime: code readings (2026-11-12, for NOSE4Web; nothing played)

**Calls during a delayed penalty (known bug 12).**
- **Genesis: the block is in `checkagr`** (collide94, the penalty roll of Bcheck, CCStart's checks and holdcheck),
  `.teamchk` at **$13EBE**: a home checker with DelayedPen ($FFC300) bit 2 (visitors pending) set, or an away checker
  with bit 1 set, gets d0 = $7F (`move.w #$7F,d0` at $13EDC), no penalty. `btst #2,($C300).w` at $13EC4, `bne` at
  $13ECA, `bra .end` at $13ECE, `btst #1,($C300).w` at $13ED2, `beq .end` at $13ED8, rts at $13EE0. To allow the call:
  `bra.w` to the rts at $13EC4 (`6000 001A`). Goalie interference and the injury roughing call AddPenalty without
  checkagr, so they already get through. The rest holds two teams' calls: **PenBuf** 32 entries (penalty, player),
  any team; **DelayedPen** a bit per team (and only checkagr reads bits 1-2); `checkfornewpen` calls an entry at once
  when the guilty player's team has the puck, else delays it, entry by entry, so the second team's foul with the puck
  stops play at once and both go to the box at that whistle; the box list `tmboxlist` per team; the penalty log
  PenSum 59 entries. **At the whistle**, `InProgress` matches as coincidental only a **5-minute** penalty against the
  same time on the other team; two minors are both served, `InProgress_ap` counts each team's players off (never below
  4 = goalie and three) and the power play comes from the tmap difference (`updatepwrplay`): two minors give **4-on-4**
  with no power-play display. **One-penalty assumptions:** gmpendel is one bit (the referee's arm is raised once,
  `SetPA $2C`); `ChkGoalies` pulls the goalie of whichever team has the puck while gmpendel is set, without asking
  whose penalty it is (a team with its own penalty pending can't hold the puck without being called, so no harm);
  `PenGoalStuff` clears the whole PenBuf on a goal against a full-strength team.
- **SNES: no block.** `checkagr` (routines/collide/checkagr.asm) has no team test, and the recordings have two
  whistles with both teams called (SNES_MECHANICS 8.3). Coincidental matching: the $4000 bit is tested
  (InProgress_ap, updatepentime, GetLowestPen, PenGoalStuff) but nothing in the penalty code sets it, so two minors are
  both served (4-on-4, the floor 4 the same). The delayed-penalty goalie pull (`ChkGoalies`) is the Genesis's.

**3-on-3 overtime.**
- **The fewer-skater ROMs** (1-on-1, 2-on-2, 3-on-3) are team data: empty line slots (0). `SetPlList` takes each
  position's player from the current line in priority order and leaves an empty slot empty (no substitute). The
  NOSE4Web builds also changed the Edit Lines / Team Roster row counts (above). No playing code changed.
- **The game already plays short-handed by `tmap`** (players on the ice with the goalie, 6 at full strength):
  `SetPlList` fills `tmap` places in `priolist` order (0 G, 1 LD, 2 RD, 4 C, 3 LW, 5 RW, 6 the extra attacker), so tmap
  4 is G, LD, RD and C. The SNES penalty shot sets tmap 1 on both sides. The lines are in RAM on both (Genesis
  `tmlines(a2)`, SNES `GetTeamLines`), so emptying two slots per line at overtime would also work, but tmap is simpler
  and leaves the lines whole: a power play can then add a skater (tmap 5 adds the line's LW) and no line needs
  cutting, with line changes on or off.
- **Where:** overtime is **gsp 3** on the Genesis (periods from 0; gsp 4 is the game's end); `StartPer` ($7870 `bset
  #1,($C2FC).w`, overtime) runs at each overtime's start, the overtime-until-a-goal build's extra overtimes too.
  `restoreteams` sets tmap 6 ($7800); `InProgress_ap` recounts after every penalty from 6 (`moveq #6,d1`) with the
  floor `cmp.w #4,d1` at **$DA88** ($FA1A, $12404 ... are other compares). A 3-on-3 hook: tmap 4 for both at
  StartPer in overtime, and InProgress_ap counting from 4 in overtime (with the NHL's 4-on-3: the other team +1 per
  player off rather than the penalized team -1).
- **The 3vs3 GENS ROM** (NHL94 3vs3 [Spring 2006 GENS].bin) against nhl94.bin: every change is below $10000 (the team
  data: lines with LD and RW 0, ratings), plus the ROM name, the boot checksum call ($301 NOPs, its routine at $FFAC0
  blanked) and one code word: ResetClock's regular-season overtime **10:00 -> 5:00** (`move.w #$258,d0` -> `#$12C` at
  $782C). priolist, the faceoff table and InProgress_ap are as retail. So it is 3-on-3 all game by empty slots. A
  reading (not played): a penalty takes tmap to 5, which drops the priolist's last place, RW, already empty, so **one
  penalty costs the team no skater**; a second (tmap 4) drops LW (2 skaters). Emptying LD and RW in RAM at overtime
  would play the same way, and leaves no player for a 4-on-3. **An overtime priority list** G, C, LW, RD, LD, RW,
  extra (`0,4,3,2,1,5,6`; SetPlList's `movea.l #priolist,a0`) with tmap 4 gives the same three skaters with the lines
  untouched (nothing to restore), and tmap 5 for the power-play team brings on its LD (4-on-3).
- **Assumptions of six:** the faceoff formation table (`.apl`, logic94 before `.ptab`) has rows for 6, 5 and 4
  players only: tmap 3 (a penalized team 2-on-3) would read past it into `.ptab`; so 4-on-3 (5 against 4) is the safe
  way. `PenGoalStuff` (`cmpi #6,tmap(a1)` at $1284E) and `GetLowestPen` (`cmpi #6,tmap(a3)`) take 6 as full strength
  (a goal ends overtime; the power-play time shown might be off). `CompLine` takes the power-play / penalty-kill lines
  on any tmap difference. Icing (`PuckIChk`) is waved off for the team with fewer on the ice. Not checked: the
  shootout hacks (they set their own players; tmap should be put back), the SNES faceoff formation.

### Which way a skater turns around: his hand (2026-11-12, for NOSE4Web's line builder)

`doplayeracc` turns the facing toward the wanted direction the shorter way (its .ftab: wanted - facing 1-3 clockwise,
5-7 counter-clockwise; Genesis logic94.asm, SNES routines/logic/skating/doplayeracc.asm). **Only a straight reversal
(the wanted direction exactly opposite the facing) goes to `noturn0`**: moving along the facing he brakes first
(`dostop`), then turns one step a call: `addq #1,facedir` (clockwise: 0 up, 2 right on the screen, so to his own
right), and with the mirrored sprite (Genesis attribute bit 3, set for right-handers in collide94.asm; SNES attribute
$0800, set for right-handers in setplayer.asm) `subq #2`, counter-clockwise (to his left). Once a step is taken the
rest of the turn is the short way, so the whole reversal keeps that sense. Skating backwards (pfrev) swaps straight and
opposite. And in his own half, with the wanted direction straight back toward his goal and the puck within a step of
straight ahead of him, he skates backwards instead (pfrev) and doesn't turn.
**Played (Genesis retail, the 16 bot start states, pad 1's skater: UP 50 frames then DOWN 60, and DOWN then UP):**
every straight reversal of a left-hander turned clockwise (19), of a right-hander counter-clockwise (8); the one other
turn started facing 6 (not a reversal: the short way). So **a left-handed LD and a right-handed RD turn toward the
middle** when they turn around; the opposite hands turn toward the boards. **SNES, played** (retail, the harness's
live state, pad 1's skater at six moments, UP 50 frames then DOWN 70 and the reverse, with his own attribute and with
$0800 flipped): every clean reversal of an unmirrored skater (left-handed: setplayer sets $0800 for right-handers)
turned clockwise (7), of a mirrored one counter-clockwise (6); the rest weren't reversals (play stopped, the facing not
straight back, or the goalie, whose turning is goalieacc's).

### Where the computer decides to change lines (2026-11-12, for NOSE4Web; from the disassemblies, retail addresses)

**Genesis** (logic94.asm; nhl94.bin):
- **On the fly: `chk4lc` at $E1F4**, called at $E04E from the computer puck carrier's decisions (each time his decision
  timer runs out, with `checkob` and before the shot checks). It changes lines only if all of these hold: sflags7
  ($FFC2FC) bit 4 clear (bit 4 is Auto line changes: then never on the fly); the puck ($FFB75E pucky, negated so that
  plus is toward the goal he attacks) between the red line and $58 (88) up the ice: **the computer's own carrier, in
  the neutral zone past centre**; HVcount ($C00008) & 3 = 0 (a quarter of the checks); the carrier not in line change
  mode (pflags2 +$63 bit 3); and **`AvgCline` ($12EF6) <= $C00** (`cmp.w #$C00,d0` at $E24C, `bhi` exit at $E250).
  AvgCline is the **average** tmpde (team struct +$32, a word a roster player) of the team's six objects with position >
  0: the skaters on the ice, goalie left out. Then `CompLine` ($F790), `setpersonel` ($15788), `printscores1` ($12C04)
  and `bra CompShoot` ($E412): the carrier dumps the puck in.
- **At every faceoff** (line changes On, OptLine $FFD058 = 0; or Auto for every team): `SetFaceoffComputerLine` ($F594)
  runs `CompLine` whatever the energy.
- **`CompLine` ($F790)**: with a man advantage or shorthanded, the fresher (by `getlinee`, $12EB4) of lines 3-4 (or
  5-6); at even strength, the line the order table pairs with the other team's line (by period 3's score: tied,
  leading, trailing), kept if its `getlinee` > $C00 ($F808, home only); else up to three lines in the away row's order,
  the first > $C00 ($F86C), else the last tried. `getlinee` is also an **average** (the line's skaters, by tmap /
  priolist, goalie out).

**SNES** (NHL94SNES routines; NHL94.smc, LoROM, no header):
- **`chk4lc` at $9F:DBD0**, called from `asspuckc` (the computer puck carrier, with chk4shot) after the breakaway
  check: the same rule, except OptLine ($7E:34C6: 0 Off, 1 On, 2 Automatic) must be 1; pucky ($0DD3) 0 to $57 toward
  the attacked goal; `seed` & 3 = 0; the team not in line change mode (tmflags bit 3); **`AvgCline` ($9F:DD19) < $C01**
  (`cmp #$0C01 / bcs` at $9F:DC2B); no penalty shot. Then `CompLine` ($9F:DA53), `setpersonel` ($9F:D407),
  `printscores1` ($9F:9B36), `jml CompShoot` ($9E:E10B).
- **At faceoffs**: `puckfaceoff` runs `CompLine` for a team no pad plays.
- **`CompLine` ($9F:DA53)**: as the Genesis, the paired line kept if `getlinee` ($9F:DF0C) >= $C01 ($9F:DB23); the
  fallback loop asks **>= $F34 (95%)** ($9F:DBA7), stricter than the Genesis's $C00. `getlinee` reads the lines from the
  team's data in ROM (TeamList, bank $83).

**Why one drained skater stays out:** both decisions use averages. Four skaters at 4,096 and one at 0 average 3,277,
above $C00 (3,072); and on the fly the computer only looks while its own carrier has the puck between the red line and
the blue line it attacks, a quarter of the times it checks: a team defending, or holding the puck in either zone, never
changes until the next faceoff, and there a line whose average is above 3/4 can be sent out with the drained skater on it.
With skating and bursts free (the hits-only builds) the other four stay near full, so the average seldom drops.

### The user's two games against version 61, and versions 62 and 63 (2026-11-12)

The user played version 61 twice (BOS against the bot's LA, PHI against the bot's CHI; `bot_live.py play`) and saw:
its goalie seldom passed after claiming the puck and skated about; no slapshots across the slot despite Sandstrom,
Robitaille and Roenick; a few close one-timers across the slot; no cross-crease; carriers deep in the zone skating all
the way back out to the neutral zone, even on a breakaway ("no human would do that"); and in the intermissions the bot
held Down, moving the menu. Measured (8 bot_record.py games a version against the computer; people: the coaches rated
80%+, 28 side-games):
- **The goalie** (a goalie's hold over 0.1 s (real), then who touches the puck next within 2 s (real)):

  | | Holds | Held (real, median) | A teammate next | Pass length (median) | An opponent next | Nobody (a whistle) |
  |---|---|---|---|---|---|---|
  | Strong coaches | 210 | 1.3 s | 67% | 130 | 19% (178 away) | 15% |
  | Version 61 | 77 | 0.3 s | 34% | 31 | 4% | 62% |
  | Version 62 | 79 | 0.3 s | 58% | 72 | 15% (39 away) | 27% |

  Through 61 the goalie held the d-pad toward the nearest teammate (skating) and tapped B once at 20 frames; in the
  user's games (the helper's recordings) he held 3.1 s (real, median), half his holds ending in a whistle. 62 stands
  still 10 frames, then taps B every 16 frames toward the teammate farthest from any opponent. People's goalies lose it
  to an opponent too (19%), but far up the ice; 62's are picked off near the net (39 away): it passes into the
  forecheck, ignoring the lane. **63**: still for 45 frames unless an opponent comes within 35, then B toward the
  teammate farthest up the ice whose lane has no opponent within 22 of it (else 62's choice; GOALIE63).
- **Carrying back out of the attacking zone** (a carry that got within 140 of the goal line, then crossed back over
  the blue line with the same carrier): strong coaches 8 of 1,008 (1%), and the user notes it is people's mistake, not
  a play; version 61 42 of 421 (10%); **62** 7 of 421 (2%). The cause: past the deke's gate with no shot on, version
  32's carry swung back out to (GATE - 20, GATE - 70), 194 out, beyond the blue line. 62 instead (`zone_hold`): with a
  lane clear of opponents (30 from the line to the net) it drives in and shoots inside 40; else it cycles across the
  slot 115 out. A trace (`zone exit` in the bot's log, phase, buttons, the nearest opponent) found 2 exits in 3 games,
  both just after picking up a loose puck while skating out, turning back in as the line was crossed.
- **Slapshots across the slot**: shooters of Shot Power 4+ on the roster scale (working value / 5) cut across the slot
  on 15% of zone entries (others 6%), and on 60% of those cuts slap, wound up before the middle (30 before it), aimed at
  the far post (the post he skates toward; the user: the most effective slot slapshots). 62: 4 cross-crease slapshots in
  8 games; cross-crease shots 35 (61: 38), EA Specials 8 (4), dekes 37 (20).
- **Intermissions**: `bot_live.py`'s "in play" was the helper's live flag (screen byte 0, players on the ice), true
  through the end of a period and the intermission (the clock at 0 for about 6 s (real) with the period unchanged, then
  the next period with the clock at 0). Now the bot lets every key go while the clock reads 0.
- `bot_live.py` keeps the bot's own log of each play session (`%USERPROFILE%\NHL94_scoring_map\bot_live_logs`), and
  `tools/bot_games.py` counts a game as the bot's from 10 minutes before the session's start (the user's BOS-LA game
  began a minute before bot_live.py was started and was missed).
- **Compared** (`bot_compare.py`, 32 paired games against the computer): 62 against 61 xG 5.11 against 3.30 (+1.81
  ±0.52), goals 2.59 against 2.62 (-0.03 ±0.36), shots on goal 20.8 against 12.9; 63 against 62 goals 2.97 against 2.59
  (+0.38 ±0.34), xG 5.58 (+0.47 ±0.48), shots on goal 21.6, xG against 2.29 and 2.30, penalties 1.97 and 1.59 (+0.38
  ±0.34). Traced (3 games each, bot_run.py's seeds): shots on goal 14.7 (61), 25.0 (62), 18.0 (63); drive shots 0, 14.7,
  9.7; carried back out of the zone 9.3, 0.7, 0.7 a game. Version 64 (the drive shot only with the goalie off his line)
  still drove and shot 14.7 a game: in close the computer goalie is nearly always off the line from the shooter to the
  middle of the net, so that gate does little; dropped. Shots on goal against the computer are no measure of
  human-likeness: people's four recorded games against the computer had 4-59 (mean 34.8), and against the user version
  61 had 10 and 13 (strong coaches against people 11.4). **Version 63 is the default.**

### NOSE4Web's c04618e (direct-page forms on the SA-1 builds), played: everything passes (2026-11-12)

nhl94snes_SA1_five / _maxboost and the SA-1 32-team nhl94_2026_five / _maxboost (`snes_2mb_hacks_check.py`, boot states
made again from the new ROMs):
- **Extra attacker:** the forward picked at LD swaps with the old LD (SA-1 [18, 17, 7, 3, 12, 4] -> [4, 17, 7, 3, 12,
  18]; 32-team [18, 19, 5, 3, 4, 6] -> [6, 19, 5, 3, 4, 18]), and with the goalie pulled the old LD comes on as the extra
  attacker (position 6).
- **Any position:** every row of every line (Best Line, Scoring 1, Pen. Kill 1 and 2) lists the 22 skaters; no pick
  leaves a player twice or drops one (both builds).
- **L+R:** 12 of 12 at every hold from 2 to 120 frames, a second press brings him back, nothing in a stoppage, nothing
  after L+R in a whistle or a pause, pad 1 only with both pads on the home team (both builds).
- **Max boost:** 88 of 88 rating cells (SA-1) and 77 of 77 (32-team) read 100 exactly when the player's hot / cold
  value for the rating is negative. (The 32-team build's pick list reads 3 characters high with the SA-1 offset: its
  font sits 3 tiles further on; shifted back for the check.)
- Injury counts (start at 0, halved at intermissions) and the boot clearing were already passing on both.
