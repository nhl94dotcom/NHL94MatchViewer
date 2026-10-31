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
