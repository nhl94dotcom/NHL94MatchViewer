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
