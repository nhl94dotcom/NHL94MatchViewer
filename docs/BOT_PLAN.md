# The scripted bot: development plan

The scripted Genesis bot (`analysis/scoring_map/bot.py`; its history and findings in [STUDY_NOTES](STUDY_NOTES.md)
"A scripted bot") plays the user's scoring moves in whole games against the computer in the headless harness. This is
the plan for taking it further (2026-10-31).

## The user's choices (2026-10-31)

- **The strongest possible bot first.** Its difficulty can be dialled back later.
- **The recorded games may be used,** as a bank of real situations to test the bot in (positions only; they stay in
  the work folder, out of the repo).
- **No installs for pressing buttons in RetroArch yet** (no virtual-pad driver). The bot only ever reads RetroArch's
  memory, and never plays in league or netplay games.
- Big runs in about one-hour chunks, each approved; gentle mode.

## What twelve versions taught

1. **A move that works standing can fail in play.** The EA Special scored 23-29 of 32 from its line in the standing
   check and 18% of tries in games; the right-hander's deke on the right side 12 of 12 standing, about one goal from
   43 tries in games. Defenders, speed and lost pucks decide what happens in play.
2. **Twenty games can't separate versions.** Goals a game vary by about 2.4 from game to game, so a 20-game mean is
   good to about +-0.5 (versions 9, 11 and 12: 6.15, 6.20, 6.00 are the same).

## Phases

1. **Measure better.** A bank of real situations from the recorded games (`bot_situations.py`: every carried zone
   entry, all 12 skaters and the puck), placed in the harness and played on by the bot (`bot_scenario.py`), every
   version from the same situations with the same seed, compared pair by pair (`bot_scen_report.py`). More kinds of
   situation (a carrier under pressure in the middle, a loose puck by the net, a breakout). Whole games only to
   confirm, 60 or more a version.
2. **Rebuild the bot's structure.** Perception (puck, zone, threats, where each skater will be a few frames on, open
   lanes); the plays (deke, EA Special, one-timer pass, wrist shot, slapshot, carry on, relief pass, dump), each saying
   when it can be made; controllers (the velocity controller from the EA work, path following, the frame-timed move
   scripts); switchable features in place of version numbers.
3. **Offence by value.** Choose among the plays by an estimated value fitted from the situation bank (the defenders'
   distances, the carrier's speed, hand and side, the goalie's position): the scripts decide how, the fit decides
   when. Then the leaks: pucks lost carrying (about 420 in 20 games), one-timer set-ups, the EA Special's bottom-net
   turn.
4. **Defence and goaltending.** Position (goal-side, the gap at the blue line), the B button's switches and pokes,
   checking with the weight bug in mind, the goalie in manual-goalie games; DEFENCE_PLAN and the coach report's
   measures that go with winning.
5. **Harder opponents.** Other teams, the league ROM's ratings and settings (penalties, line changes, period length),
   the bot against itself on both pads; a fixed benchmark set.
6. **Learn from people.** The helper records button presses: the moves strong players use and how often each works,
   into the bot's plays; its choices against people's (the coach report's decision measures).
7. **RetroArch.** Read memory with the helper's reader; press buttons by keystrokes to RetroArch's window (no
   install). First measure in the harness how much 1-2 frames of input delay costs each move (the helper isn't
   frame-locked) and make the moves robust to it. Offline only.
8. **SNES** later, the same structure on the Snes9x harness.

Along the way: GIFs of each new play, and each guide tip checked in play.

## Status

- Phase 1 started 2026-10-31: 472 carried zone entries from 16 recorded Genesis games (the 2v2 games have none).
  The carrier is given pad 1 through `c1playernum` ($C320, found by watching it follow the controlled record) and his
  pflags joystick bit. Played on for 6 seconds against the computer from a live-play state (MTL v LA, so the recorded
  players' ratings aren't carried over), the first run (`scen1`): versions 11, 6, 9 and 12 scored 10.0%, 10.2%, 10.0%,
  10.6% (+-1.4) of the entries; 46% lost to a skater, 22% held by the goalie, 22% nothing within 6 s. Versions 6, 9
  and 11 differ in one situation of 472 (their changes seldom come up in an entry's first 6 seconds); 12 against 11:
  13 scored where 11 didn't, 10 the other way (+0.6 points +-1.0). **The people in those games, from the same entries
  against people defending: 15.5% scored within 6 s, 34% got a shot on goal.** The bot is well short of the league's
  players from the same spots, and against a softer defence.
- **How the people scored from the same entries** (the match files' shots within 6 s): goals came fast (half within
  1.9 s of the blue line). Wrist shots 30 goals from 136, nearly all from the middle of the slot (within 30 of the
  middle: 40-80 units out 15 of 40, inside 40 out 10 of 22; many of them likely dekes, which the converter calls wrist
  shots); one-timers 27 of 73 (37%), from the middle 40-120 out 17 of 35, and set up mostly by a sideways pass (17 of 37).
- **Version 13: the one-timer as people play it** (the pass from 100 up the ice, to a receiver within 100 of the goal
  line and 70 of the middle, moving 39-110 across; 11 otherwise). From the 472 entries (`scen2`): one-timers struck 83
  times (version 11: 52), goals 50 against 47 (+0.6 points +-1.3: no difference). The bot's strikes scored 15 of 81
  situations (18%), people's 37%. The strikes logged (`scen3`, position, the goalie's, the puck's speed): the passes
  came mostly from the high slot and the points (70-130 out) to a receiver 50-100 out, the puck at 3.5-4.6 a frame
  and 10-25 frames on its way, and at the strike the goalie was set in the middle of his net nearly every time. The
  guide's finding is that a one-timer scores when the goalie is still sliding (a quick pass across); the bot's long,
  slow passes let him set. Next: quicker passes across from lower down (the carrier low on one side, the receiver
  across), and the close-in plays from the guide (the cross-crease, the slapshot wind-up that drops the goalie).
- **The one-timer from people's own passes** (situation kind "pass": every one-timer in the recorded Genesis games, 117,
  placed 2 samples before its pass with the passer holding the puck; the bot makes the pass with B toward the same
  receiver, then its one-timer). A puck placed in flight doesn't work: the game starts a one-timer only for a pass it
  made itself (`passReceiverPlayerNum`, the intended receiver; C pressed on the passer's pad while the receiver isn't
  the pad's skater, logic94 `doinput`, assignment $23 `assonetimer`), so the first try struck 9 of 117. Made by the
  bot: struck 85 of 117, scored 30 (25.6%); the people scored 45 (38%). Per strike the bot's 35% is about the people's
  38% (and against the computer goalie their one-timers scored 45 of 127, 35%). C 14, 24 or 40 frames before the puck
  arrives: 30, 30, 29 goals; 4 frames: 12 (too late). **So the strike is fine; the bot's 18% from entries is its
  set-ups** (where and when it passes), plus the 32 of people's passes that the bot's B didn't turn into a strike.
- **Versions 14-15: the one-timer pass by people's numbers, no gain.** In people's 117 one-timer passes, passes 130+
  long scored 7 of 36 (shorter 38 of 81); passers stayed within 120 of the goal line. Version 14 (13 with those limits
  and no defender within 20 of the receiver): 49 goals from the 472 entries against version 11's 47 (+0.4 +-1.1).
  Strikes from people's passes against the bot's own: the receiver nearer the middle (median 27 off it against 39)
  and the goalie drawn farther over (median 9 against 5); who struck was the same (mostly the centre, each scoring less
  from the bot's own passes). Version 15 (14 passing only to a receiver within 40 of the middle with the goalie drawn
  4+ toward the passer): 50 (+0.6 +-1.1). The one-timer is too small a part of the bot's play to move its 10%.
- **Where the gap to people is.** From the same entries people lost the puck *more* often (59% touched by an opponent
  skater within 6 s, 16% held by the goalie; any touch counts there, 20 frames for the bot) and scored no sooner (the
  bot's goals a median 2.2 s after the entry, people's 1.9 s). People got a shot on goal from 34% of the entries and
  scored 15.5%; the bot shot about as often (224 shots on goal from 472) but scored 10%. **The gap is the bot's shots**:
  its slapshots (125 in the run, about none in) and its wrist shots from the sides (7%), against people's wrist shots
  from the middle of the slot and one-timers. Next: no slapshot under pressure, the close-in wrist shot only from the
  middle (cut in to it), and the guide's close-in plays.
- **Version 16: the bot's shots (from the 472 entries, +7.0 points).** No slapshot under pressure, and the close-in
  wrist shot (away from the goalie) as soon as the carrier is 170 up the ice (94 out from the goal line), instead of
  200. The zone tried (`bot.WRIST16`, within `mid` of the middle, cutting in to it from the sides, from `ay` up the
  ice): mid 25 / 35 / 50 / 70 / no limit at 170: 58 / 64 / 74 / 78 / 80 goals; 50 at 145: 66; 70 at 195: 55. So
  cutting in to the middle cost goals, and the gain is shooting sooner and not winding up under pressure. **16 against
  11: 80 goals (16.9%) against 47, scored where 11 didn't 57, the other way 24: +7.0 points +-1.9**, past people's
  15.5% from the same entries (people faced people; the bot the computer). Two numbers tuned on the same entries, so
  whole games next to confirm it.
- **Version 16 confirmed and made the default.** Whole games (20, the same seeds as before): 20-0, **8.50 goals a game
  to 1.05** (version 11: 6.20 - 0.65; +2.3 a game +-0.7). 37.9 close-in wrist shots a game, 9% a shot; the deke 45% a
  shot; no slapshots; one-timer passes fell to 1.6 a game (the wrist shot comes first). The check on situations it
  wasn't tuned on (kind "zone": 122 possessions already in the attacking zone, 0.5 s in, away from entries): 17 goals
  against version 11's 15 (+1.6 points +-3.1, too few to settle).
- **Version 17: the close-in slapshot wind-up (GENESIS_GUIDE 6: the computer goalie drops early and slides to the
  middle; recorded 37% when he dropped), worse.** In close (200+ up the ice) and more than 20 off the middle, C held 12
  frames (or 8) and released at the carrier's own side: from the 472 entries 69 goals (8 frames: 75) against version
  16's 80 (17 against 16: -2.3 points +-1.1). Version 16's quick wrist shot beats it; 16 stays the default.
- **Where version 16 still fails (the 472 entries).** Most entries end after a shot: an opponent took the rebound
  (172) or the goalie held it (92); 581 wrist shots, 41 dekes. The wrist shot's aim (`bot.WRIST_AIM`, env
  NHL94_WRIST_AIM): the far side at middle height (16's) 80 goals; high 46, low 37, nothing held 39, the goalie's
  side 30. By where the carrier entered, the bot against people from the same entries: the left 42 of 192 (people
  29), the right 31 of 196 (29), **the middle 7 of 84 (15)**: from the middle 16 swung out to the deke's lane across
  the defenders.
- **Version 18: straight up the middle.** A carry that begins in the middle of the zone (within 25 of it, 60-170 up
  the ice) goes straight up to the wrist shot. The middle entries 15 of 84 (people 15); all 472: 88 goals (18.6%)
  against 16's 80 (+1.7 points +-0.8). The zone check (122): 16 against 16's 17 (it seldom applies there). Whole games
  next before it becomes the default.
- **Version 18 in whole games: not confirmed.** 20 games: 7.65 goals a game to 0.95, against 16's 8.50 (-0.85 a game
  +-0.65), though it led by 1.7 points from the entries. 16 stays the default; the middle-entry rule helps there and
  may cost elsewhere in a game (a middle carry that isn't an entry).
- **Version 19: chasing its own rebounds** (after a shot, at the loose puck a few frames ahead instead of the
  defence's rules, B switching to a teammate much nearer it): from the entries 90 goals against 18's 88 (+0.4 +-1.1).
  The opponents are nearer the rebounds to begin with.
- **Defence, from the same entries turned round** (`bot_scenario.py` NHL94_SCEN_DEFEND: the entering team becomes the
  Away team, attacking our net; results against / won / covered by our goalie / stoppage / time). The computer
  attacking is too weak to test a defence: against version 16 it scored from 14 of the 472 (3%). **The bot against
  itself** (NHL94_SCEN_DEFEND=bot: the attackers on pad 2, `cont2team` $C32A and `c2playernum` $C322, played by the bot,
  version 16): 55 of 472 (11.7%) got past version 16's defence (the same attacker scores 16.9% against the computer's).
  Version 20 (the faceoff rule's B-mash only just after a faceoff drop; 16 did it at any still puck near him): 55, no
  change. **Version 21 (20 with the CB check: B tapped 4 frames into each burst, so the computer's checking formula
  decides the hit, not the person's weight bug, GENESIS_GUIDE 9.2): 47; only 16 let in 13, only 21 let in 5 (-1.7
  points +-0.9).** With penalties on the CB check doubles the penalty risk (the bot's games have penalties off).

## The long test plan (2026-10-31; approved: about 4 hours, blocks 1-2)

So the user doesn't have to approve each test version: a queue of experiments with fixed rules for keeping a change,
run in gentle mode within an agreed total budget, reported block by block; it stops early only for a decision only
the user can make.

**League settings first** (the user, 2026-10-31: the Genesis leagues play Penalties "On, Except Off-sides", Line
Changes Off, Goalies Manual Control). `bot_states.py` now builds bot_start.state with them (OptPen $D056 = 2, OptLine
$D058 = 1, OptGoalie $D050 = 0, checked), 5-minute periods; every bank and game from here uses them (the earlier
results above were with penalties off). Baselines again under them (versions 16 and 21). `bot_run.py`
NHL94_BOT_VS="A,B" plays the bot against itself in whole games (B on pad 2, the sides swapped every other game, each
seed twice) and counts each side's penalties, penalty minutes and power plays.

**How a change is judged** (no approval needed per version):
- The banks: offence (the 472 zone entries against the computer's defence, plus the 122 zone possessions), defence
  (the 472 entries turned round, the bot attacking on pad 2), one-timers (people's 117 passes).
- A change is **kept** if it beats the current best on its bank by 2 standard errors or more (paired, situation by
  situation) and costs no other bank more than 1; then it must hold in **whole games, the bot against itself** (20
  games new against current, 10 with each side at home): kept if the goal difference is in its favour.
- Penalties counted in every run (minutes per game), since a move that draws calls costs power plays.
- Every experiment written into this file's "Status" with its numbers, committed and pushed.

**The queue** (in order; each block about 1-3 hours of gentle-mode running):
1. Baselines under league settings: versions 16 and 21 on every bank; 21 against 16 in whole games.
2. Defence: the poke's distance and timing, the burst's distance and how often, the goal-side spot (how far in front
   of the carrier), when to switch (B) to a nearer teammate, one defender holding the slot; penalties drawn by each.
3. Offence under the bot's defence (not just the computer's): the wrist-shot zone and the deke's gate re-tuned
   against it; the one-timer pass; what to do with a defender on the carrier.
4. Special teams: power play and penalty kill (5 on 4) as their own banks from the recorded games' penalties.
5. Whole-game checks of the best version every block, and a final 40-game bot-against-itself match, newest against
   version 16.

**Reports:** a short summary after each block (what was kept, by how much); the bot never stops waiting for a go-ahead
inside the budget. **Stops** when the budget is used, the queue is done, or something needs the user (a league rule,
a setting, a result that changes the plan).

### The long test plan: results

- **Block 1, whole games (league settings, the bot against itself):** version 21 against 16, 20 games, each seed
  played twice with the sides swapped: 10 wins each, 6.65 goals a game each (difference 0 +-0.78), penalties 3.4 a
  game against 3.25. The CB check's gain on the defence bank (-1.7 points, penalties off) doesn't show in whole
  games, and it draws hardly more calls.
- A setup fault found on the way: with penalties on the first live-play state was saved in the stoppage after a
  call (the clock still), so every situation timed out; the state is now saved only with the clock running and no
  penalty standing, and block 1's banks were run again.
- **Block 1, the banks under league settings** (versions 16 and 21): zone entries 83 goals of 472 (17.6%) for both
  (with penalties off 16 had 80); zone possessions 17 of 122 for both; the defence bank (the bot attacking) 50 against
  16 and 49 against 21 (-0.2 points +-0.6; with penalties off 55 and 47); the attacking bot's plays there: 465 wrist
  shots, 29 dekes, 20 passes, 16 one-timers. People's one-timer passes made by the bot: 13 goals of 117 (11%; 88
  struck), against 30 (26%) with penalties off: with penalties on the computer's defenders seem to break up passes
  and strikes more (to look into). So under league settings 21's CB check gains nothing in the banks or in games; 16
  stays the default and block 2 varies 21's defence (22).
- **Block 2, the defence's numbers (version 22: one number of 21's changed at a time; the defence bank, the bot
  attacking, league settings; 21: 49 against):** poke within 20 / 34: 61 / 52; burst within 30 / 60: 51 / 50; burst
  every 15 / 45 frames: 49 / 49; the goal-side gap 8 / 24: 64 / 60; switch margin 30 / 80: 56 / 57. Paired against 21
  none is better (from +0.0 to +3.2 points worse); the gap (+3.2 and +2.3 +-1.3), the poke at 20 (+2.5 +-1.2) and the
  switch margin (+1.5 / +1.7) are clearly worse either way. **21's numbers are a local best; none kept.** The plan's
  approved budget (about 4 hours, blocks 1-2) is used; next blocks need the user's go-ahead. What the blocks point to:
  the defence's numbers are tuned, so further gains need new behaviour (the attacking bot scores nearly all with quick
  wrist shots from the slot: covering the slot, not the carrier), and the one-timer drop with penalties on.
- **The test setup corrected (2026-10-31).** People's one-timer passes scored 30-31 of 117 from the old live-play
  state and 13 from the new one, whichever bot version (11 or 16), penalties on or off, the goalie's ratings or the
  score. Copying halves of work RAM from one state into the other found it: the records' computer-AI bytes ($2E-$65:
  the assignment and its list, its working values, impacts, animation lock, flags) carried over into every placed
  situation. Now each placed player gets a clean state (his position's assignment for his side, the carrier the
  puck-carrier one, those values cleared), which brought the two states to 20 and 31; and each bank is spread over
  four saved moments of play (situation n in moment n mod 4). Earlier banks used one moment: comparisons between
  versions on them stand, their absolute rates were partly that moment's. **New baselines, version 16:** zone entries
  101 of 472 (21.4%), zone possessions 20 of 122, people's one-timer passes 24 of 117 (20.5%), the defence bank 61
  against (version 21 also 61).
- **Version 23, covering the slot** (in our end, the defender stands in the carrier's shooting lane `hold` out from our
  net instead of chasing him, from when the carrier is within `zone` of our goal line; SLOT23): against 21's 61 on the
  defence bank, zone 140 with hold 28 / 40 / 55 / 75: 68 / 55 / 62 / 62; hold 55 with zone 100 / 180: 63 / 67. Paired
  against 21 the best, hold 40, is -1.3 points +-1.2: nothing kept. With the defence's numbers tuned and the slot not
  helping, the one skater the bot controls has little say over goals against: the other four are the computer's.
- **Offence against the bot's defence** (`bot_scenario.py` NHL94_SCEN_DEFENDER=21: the 472 entries, the defence
  played by version 21 on pad 2 instead of the computer, which let in 21%): version 16 76 goals (16.1%); the wrist shot
  from 190 up the ice 80 (+0.8 +-1.7), from 150 67 (-1.9 +-1.8); version 11 68 (-1.7 +-1.7); **version 18, straight up
  the middle, 68 (-1.7 +-0.7)**. Version 18 led against the computer's defence (+1.7) but lost in whole games (-0.85 a
  game), and it loses here too: **this bank, the bot defending, is the better guide to whole games**; use it for offence
  from now on. Version 16 stays the default.
- **New offence behaviour against the bot's defence (versions 24-26, each one change on 16; 20-22's defence, which
  is 16's in games).** Against 16's 76 goals of 472: 24, the right-hander's deke on the right side (12's): 80 (+0.8
  +-0.7); 25, no one-timer passes: 76 (+0.0 +-0.7: the bot's one-timer passes add nothing); **26, a looser deke entry
  (the gate 26 wide instead of 16, 0-1.1 across instead of 0.2-0.9, 1.2 up the ice instead of 1.5): 88 (+2.5 +-0.9),
  75 dekes against 49.** 26 on the other banks: entries against the computer 117 against 101 (+3.4 +-1.2), zone
  possessions 19 against 20 (-0.8 +-1.4). Whole games, the bot against itself, 20 (each seed twice, sides swapped):
  26 won 11-9, 6.7 goals a game against 6.4 (+0.3 +-1.0), penalties 3.55 against 4.0. **Version 26 is the default.**
- Further, against the bot's defence and 26's 88: 27, the deke entry looser still (36 wide, -0.2 to 1.3 across, 1.0
  up the ice): 92 (+0.8 +-0.9); 28, 26 with 24's right-side deke: 89 (+0.2 +-0.8). Neither kept: the entry has given
  what it can.
