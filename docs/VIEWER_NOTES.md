# NHL '94 match viewer: viewer, stats and broadcast notes

The development notes for what the viewer, the season page and the live broadcast show and how each is worked out, moved out of [PROJECT_NOTES.md](PROJECT_NOTES.md) on 2026-10-26 (the memory layout, workflow and files are there; the studies in [STUDY_NOTES.md](STUDY_NOTES.md)).

## Goals and the viewer's layout

- The converter builds `goals` from the stat snapshots: when a team's goal count rises, the skater whose goals rose
  is the scorer and those whose assists rose (looking up to two seconds on) are the helpers; the team's power-play,
  shorthanded, breakaway, one-timer and penalty-shot goal counters tag the kind. Each entry carries the scorer's and
  helpers' game totals at that moment. No scoring summary was looked for in RAM; this matched every goal checked.
- Layout: left panel = Home lineup, controller, legend, scoring summary; right panel = Away lineup, team stats,
  penalty box and summary. The player card is a floating pop-up (`#popover`), shown on hovering a lineup row and
  put away by clicking that row (or Escape), so it never pushes the panels around. Hovering players on the ice was
  tried and removed at the user's request: the card covered the play.
- Breakaway and one-timer tags are drawn in the accent colour, as notable moments rather than skater actions.
- Banners over the ice (`#callout`): goals (scorer and helpers with game totals, as the game shows them), penalties
  from the moment of the foul, penalty shots awarded.

## Shot map and heat map

The footer's "Map" menu draws a shot map or a heat map on the ice, under the players, for both teams, one team or one
player (`?map=shots|heat&who=t0|t1|p<team>:<roster index>` in the address). Both build up as the match plays. Teams
change ends between periods, so each team is kept attacking the end it attacks in the period being shown (found from
Home's goalie: `ends` in the viewer), and the maps line up with the live play.
- Shots (`shotList` in the match file, from `find_shots` in the converter): the game keeps only totals, so a shot is
  a shooting animation ($07FC/$092E) whose player loses the puck, or for a one-timer (he never has it) a loose puck
  beside him that changes course hard (velocity change over 5000; the speed alone may barely change). Then goals,
  shots-on-goal rises and posts are credited in time order, each to the latest unused shot of that team: a goal also
  raises shots on goal (paired within 1.5 s), and the game counts a post as a shot on goal. Counted events with no
  shooting animation (deflections, scrambles) become kind 'other' where the puck last changed course; the rest are
  misses (wide or blocked). In all five captures saves + goals + posts equal the game's shots on goal and goals equal
  the score, for both teams. Roenick's point-blank wraparound post in `capture5_league30` (1st period 2:57) needed the
  post to match a release one sample after it, and a release at a post frame is ignored (the bounce is not a shot).
- Pass shots (the community's name): a B-button pass ($0718/$078A) used as a shot. With no obvious target the puck
  flies off quickly the way the player pressed. Neely's goal in `capture6_netplay_bos_stl` (2nd period 3:16) is one:
  B + Down, the pass animation, the puck at 22900 straight into the net. A pass counts as a pass shot when it is
  released at least 20 units in front of the goal line, its line crosses that goal line within 40 of the middle of
  the net the other team defends, and it reaches the goal mouth (within 40) or that goalie before a teammate takes
  or one-times it. 40, not 30: pass shots are aimed by direction only, and the user's two wide attempts in that game
  (Neely, 3rd period 1:47, from behind centre ice; Oates, 3rd 0:09, from the slot) crossed at 35 and 30.2. The
  20-unit rule drops a pass along the goal line beside the net (Ruzicka in `capture5_league30`).
  The game does not count a pass shot as a shot on goal unless it scores (the user's league says so too): every goal
  in every capture comes with a shot on goal, Neely's included, but the two pass shots goalies stopped (Fedorov in
  `capture2_away`, Roenick in `capture5_league30`) left the count alone. So each shot in `shotList` has `counted`
  (did the game count it), and a pass shot the goalie stopped reads 'save' with counted false, judged from the play
  (the goalie got the puck or it changed course beside him). Only two such saves have been seen so far.
  The viewer shows pass shots as squares on the shot map, a "Pass shot" tag, a "Pass shots" team stat and a PASS
  SHOT goal tag.
- Duplicates (fixed 2026-10-16): one shot per player and release (a shooting animation in two pieces had found
  Oates's release in capture6 P1 1:17 twice), and a goal the game credits to a player with no fresh shot of his is
  looked for only after his last credited shot (capture3's rebound goal 2 s after a saved one-timer had been
  credited to the saved one-timer again); now at the rebound. Counted shots and goals still equal the game's.
- Who shot: every shot the game counted is credited to the player the game credits (the scorer it names, or whose per-player
  shots, +$E8, went up). With that, every skater's shots on goal in all six captures equal the game's, and goals
  are always credited to the game's scorer (before, a one-timer missed by the finder could hand a goal to the
  previous shot). The team stats also show "Shot attempts" (everything in the shot list, including misses).
- Every attempt ends one way: on goal (the game counted it: goal, save or post), saved but not counted, wide or
  blocked. Blocked: an opposing skater (not the goalie) got the puck, or it changed course beside one, before the
  goal line; wide otherwise. The team stats show Shots on goal (the game's), Shot attempts, Wide, Blocked and, when
  any, Saved, not counted; they add up in every capture. The game does not count every stopped shot: of 92 goalie
  stops in the captures, 15 were not counted (both pass shots among them, and 13 ordinary shots, many aimed inside
  the posts, such as Neely's 23000 shot from the right circle at 2:50 of the 2nd in `capture6_netplay_bos_stl`).
  Distance, speed, aim, height and the goalie's animation do not separate them; why is unknown.
- Possession (the user's definition: which team controls the puck) is counted in game seconds: each second the
  game clock ticks off goes to Home, Away or Transition, so the three add up to the game time played (15:00 for
  `capture6_netplay_bos_stl`: Boston 7:26, St. Louis 4:41, Transition 2:53). With the puck on a stick, that team's.
  Loose: by who had it before and who gets it next within the same stretch of play (a whistle - the puck hidden -
  or a new period ends one): same team, theirs (passes are not punished); other team, Transition; nobody before
  (off a faceoff), the team that wins it; nobody after (before a whistle), the team that had it. A second counts
  when the clock reaches a new low in the period, at most 3 at a time: the game sets the clock (0:00 before a
  period's 5:00; 10:00 then 0:00 after the final horn) and netplay blipped it back once. The player card's "With the
  puck" is game seconds with the puck on that player's stick. Each team's possession is split by zone in its own
  view (attacking / neutral / defensive; the three add up to its possession) with the blue lines at Y = +/-89
  (`ZONE_LINE`): with that line, the puck's seconds in each end, whoever has it, match the game's attack-zone time
  (+$0A) within 1-3 s in all five full recordings (best fit 88-90). So the game's "Attack zone" is puck-in-zone time,
  not possession; capture6 Boston: 3:01 / 2:45 / 1:40 of 7:26.
- Turnovers: Turnovers (`turnovers` in the match file, from `find_turnovers`): control passing to the other
  team with no whistle between (a hidden puck or a new period marks one) and not by a shot. Takeaway when the other
  team poke-checked ($0B24), hooked ($1122) or checked ($0C5E, or the carrier went down, $0DD8/$0D26; credited to
  the nearest opposing skater) within 0.5 s, or an opponent on top of him took it at once ('stolen'); otherwise a
  giveaway: a pass picked off, or the puck lost. A pass the goalie collects is a dump-in, neither (as the NHL
  counts). `capture6_netplay_bos_stl`: Boston 15 giveaways, 23 takeaways (Bourque 11).
  Shown in the team stats, the player card and the "Turnovers" map (hollow triangles: giveaways in the loser's
  colour; filled: takeaways in the winner's).
- Failed one-timers (`failedOneTimers`, from `find_failed_one_timers`): a player goes into a shooting animation
  without the puck within 1.5 s of a teammate's pass (C pressed while it travels) and no shot of his comes of it -
  the puck never got close enough. In every capture, every puck-less swing followed a teammate's pass. The game's
  own one-timers-tried count only has ones that connected (6 and 7 in `capture6_netplay_bos_stl`, against 6 and 8
  connected and 11 and 2 failed here). Shown as a team stat, on the player card and as a "Failed one-timer" tag.
- Goalie report ("Goalie report" map, one or both goalies): every shot that reached the goalie (goals, saves the
  game counted and saves it did not), with save rates overall and as the game counts them, by distance from the net
  (under 60, 60-120, farther) and by type (wrist or slap by how long the shot was wound up, 800 ms or more = slap;
  one-timers, pass shots, deflections, rebounds), and what happened after each save (held or whistle, rebound to the
  shooters, cleared by his team, loose). Human or CPU goalie (the user's community often takes the goalie by hand):
  `gctl` on each shot is 'human' when the defending goalie's record carries the controlled-player marker (+$62 bit
  $08) at the release, else 'cpu'. The release decides because control moves to a goalie by itself when he gets the
  puck (so a CPU save often ends with the human holding him); taking him is a B press with the puck loose or the
  other team's (nearly every such switch in the button captures). About five shots in the seven recordings were
  grabbed in flight and count as CPU. Shown, for teams a human played, in the goalie report, the goalie's card
  (game-counted shots, posts as saves, so they add up to his Saves) and shot tooltips. CGY-BOS: Boston's Moog
  3 saves on 7 human-controlled, 4 on 6 CPU. Shots carry `type`, `goalie` (roster index of the goalie faced), `gctl`,
  `after` (saves) and `rebound` (the same team's previous shot was saved and they got the puck back within 3 s).
- Passes (`passes`, find_passes): every pass animation ($0718/$078A; goalie $0366) whose player loses the puck, with
  where it ended: completed (receiver), one-timer, intercepted, failed, pass shot; `counted` = the game's passes-tried
  count rose with it. The game counts only targeted passes: B presses with no target and goalie passes are not
  counted (20 of the user's 62 in 2026-10-14_1540_CGY-BOS); 92-98% of the game's counted passes match one here.
  Shown on the player card and the "Passes" map. Faceoffs (`faceoffs`): drop spot, winner (the first faceoff count to rise
  after the whistle, up to the next stoppage or 6 s after the drop, whichever is later: the game credits whoever first
  takes the puck, 7.8 s later in one SNES scramble, 2.4 s after a drop whistled dead at 0.6 s in another; 2026-10-21, was 'within 6 s'; with the SNES drop flicker smoothed, steady_puck, matches the game everywhere) and zone (Home's view;
  |Y| < 100 neutral), split in the team stats. Icings (`icings`): touch-up icing - released in own half, crossed the far goal
  line untouched, whistle when a defender touches it (or play stops), faceoff back in that team's zone. Confirmed on the
  user's two in 2026-10-14_1540_CGY-BOS (Juneau, Sweeney, 2nd period); also finds Shanahan in capture6 (P1 1:44, unconfirmed). Shown as a team stat and a banner. Overtime is period index 3 ("OT"; 10 min).
  The helper's first live game (2026-10-14_1540_CGY-BOS, CGY 6-5 BOS in OT) was recorded, ended and converted correctly.
- Hits (`hits`, find_hits): every check that landed, thrower and target. The thrower from whichever byte counts checks
  thrown (+$11C original, +$102 hack ROMs); the target is the nearest opponent going down ($0DD8/$0D26) within 0.8 s,
  else the nearest opponent. On `capture5_league30` (hack ROM, which records both) every one of the 23 hits goes to
  the player the game says took it; team totals match the game everywhere. Player card: Checks, Hits taken, and
  Pen. minutes on original ROMs.
- Bumped off the puck (`bumps`, find_bumps, 2026-10-16; the user asked for pucks lost when a carrier and a defender
  rub into each other with no check delivered, and then for losses skating into a goalie, tracked apart). A skater's
  possession (held at least BUMP_HELD 0.15 s; shorter touches are crease scrambles) ends, not across a whistle, not
  by a shot or pass (a pass animation counts even when the pass list missed the pass: an intercepted pass the user
  caught), the puck not leaving faster than BUMP_FAST 70 (shot or flipped: Taglianeti's flip down the ice left at
  121; carried pucks go up to about 55), no poke check or hook by an opponent within 35 of the puck, he did not go
  down, and he does not have it back within 0.3 s. Then `kind`:
  'goalie' if the puck came within GOALIE_PUCK 15 of a goalie (his own or the other team's, `own`) from 0.15 s before
  the loss to 0.2 s after, with the carrier within GOALIE_BODY 33 of him (the user's: Samuelsson into his own
  Barrasso, P3 3:31, puck 12 / body 23; Lemieux into Moog, P2 1:45, 10 / 17; Lemieux P3 0:12, 14 / 32, the puck out
  on his stick, Juneau close too: the user judged it the goalie, a mix-up there 'not a disaster'); else 'skater' if an opposing skater
  was within CONTACT 17.5 in the 0.5 s before (bodies stop about 16 apart: opposing skaters spend thousands of
  samples at 16-17 and a handful closer) and no check landed on him within 0.7 s (the hit list; a lunge that did
  not land still counts). `next`: who had the puck next (opponent / teammate / himself / none = whistle first), `by`
  the opponent or goalie, `human` (skater kind) that opponent was a person's. Review of 2026-10-16_1314_BOS-PIT's
  first list: every verdict now matches (rows 1 flip and 3 pass gone; Jagr P1 2:05 "probably"); the goalie rule
  added Lemieux into Moog P1 4:37 and Samuelsson into Barrasso P2 4:45 (both confirmed); 33 instead of 25 added
  Stevens into Moog P3 2:56 (unreviewed) and turned three CGY-BOS skater bumps into goalie ones. Shown as a tag over the carrier
  ("Bumped off the puck" / "Lost it on the goalie"), team stats (Physical: pucks lost on contact, to the other team,
  pucks lost on a goalie), the card (Bumped off puck / Bumped puck loose / Lost puck on goalie) and the season page
  (team BMP and ONG a game; skater BMP lost · forced and ONG; summary VERSION 8). Turnovers are unchanged.
- Bobbled passes (`bobbles`, find_bobbles, 2026-10-16; the user: a pass the receiver's stick was in place for that
  bounced away instead): the first thing a pass hits (its speed changing by BOBBLE_KICK 50, hundreds) is a teammate
  skater within BOBBLE_NEAR 22 with no opponent as close (within his distance + 8); not when he played it (a shooting
  or passing move within 0.4 s: one-timers bounce the puck the same way), caught it (his within 0.1 s), an opponent
  had it within 60 ms (picked off), the puck was at the boards (a pass that missed), or the receiver is a goalie.
  Recovering it afterwards still counts (the user). The user reviewed 21 candidates in 2026-10-16_1540_CHI-TOR: the
  rule finds exactly the 10 real ones. That review also found the SNES one-timer swings $EF6E and $F020 (never with
  the puck; every "led to a one-timer" candidate met one), now in snes ACTIONS "shoot": SNES one-timers are found at
  last (game 2: 7 plus 6 failed against the game's 11 tried; counted shots still equal the game's in all three SNES
  games). find_passes now keeps one pass per player and release (a passing move in two pieces had listed 6 twice in
  2026-10-16_1528_TOR-CHI; no Genesis pass changed). The pass-count gap (2026-10-21): the converter had matched 178
  fewer passes than the game's passes tried across the recordings. The carrier often loses the puck a sample or two
  before his pass animation shows (goalies' passes too: the game counts a goalie's pass that has a target, through the
  same passto), and an opponent can have it on the very next sample; find_passes now looks from 120 ms before the
  animation and takes any change of owner. Now 4,416 of 4,449 across both folders (most of the rest in old project
  copies with no recording to re-convert). Each bobbled pass carries `bobble` {f, idx, x, y}: the passes map draws
  it to that spot with an orange bobble ring, then a thinner line on to its outcome (the user asked for that; the
  tooltip says "bobbled, then ..."). Also shown: a "Bobbled" tag over the receiver,
  team stats (Bobbled passes, under Pass %), the card, Help, and the season page (team BOB a game, skater BOB;
  summary VERSION 9). 1-11 a game in the recordings. On the Genesis, bobbles mostly come from short passes (50 units
  or less) or a long pass catching up with a teammate skating away from it, often bouncing straight back off him (the
  user; 28 of the 35 Genesis bobbles fit one or the other). Labelling bobbles by those kinds was tried and removed: the
  user wants them shown simply as bobbles.
- Pass direction and zones (`add_pass_shape`, 2026-10-16; the user: who passes a lot in the attacking zone rather than
  skating, who passes a lot in his own zone): each pass's `dir`, the puck's direction leaving the stick against the
  way the team attacks (away from its own goalie, `own_end`): 'forward' (within 30 degrees), 'diagonal forward'
  (30-60), 'sideways' (within 30 of straight across: a little forward or back still counts), 'diagonal back',
  'backward' (PASS_DIRS); `zone` (where it was passed from) and `toZone` (the bobble, catch, interception or where it
  stopped), 'def' / 'neu' / 'att' in the passing team's view (ZONE_LINE). BOS-PIT: 26 forward, 20 diagonal forward,
  26 sideways, 6 diagonal back, 4 backward; most passes stay in a zone (D>D 25, D>N 17, O>O 16, N>N 16, N>O 6).
  Season summaries (VERSION 10) per skater: `passDir` (zone x direction, 15), `passZones` (from x to, 9) and
  `puckZone` (game seconds with the puck on his stick in each zone, as the viewer's possession counts them: each new
  low of the clock, the clock being reset when it jumps up more than 3). Season page, Play style: "Passing by zone"
  (zone picker; passes, /GP, time with the puck, passes a minute of it - Oates 32 in the attacking zone, Roenick 3.7 -
  direction shares, passes out of the zone). Viewer: team stats group "Passing by zone and direction" (closed at
  first), the card's "Passes att / neu / def" and "Pass direction" (ahead / across / back), Help.
- Who carries the puck (2026-10-16; the user: some people carry with their wingers, some the centre, some the
  defence): the team's game seconds with the puck on a skater's stick by the position he was playing then (role at that
  sample, so line changes count right), as the viewer's possession counts seconds. Season summaries (VERSION 11), per
  team: `puckPos` (zone x LD, RD, LW, C, RW: 15) and `entryPos` (carried zone entries by the carrier's position);
  season.py `puck_seconds_by_zone`, `carried_entries_by_position`. Season page, Play style: "Who carries the puck"
  (zone picker; time with the puck a game, D / C / W shares, LD / RD / LW / RW shares, carried entries D / C / W),
  noting that equal use would be D 40%, C 20%, W 40%. Viewer: Puck control's "Carried by D / C / W", with "· LD / RD" and
  "· LW / RW" under it (2026-10-17, the user: each side's share of all carrying time, so the pairs add up to D and W). BOS-PIT: Boston
  32 / 16 / 52 (the left wing alone 122 s, 10 of 24 carried entries), Pittsburgh 35 / 23 / 42; CHI-TOR: Chicago
  21 / 33 / 46.
- Nets knocked off (`netsOff`, find_dislodged_nets, 2026-10-16; the user: any skater can dislodge either net, much
  more often on the SNES; an attacker knocking the other team's net off gets the faceoff moved to a dot just outside
  that zone, a defender knocking his own keeps it in the zone). Both readers keep `nets`: [frame, top x, y, bottom x,
  y] whenever a net moves (Genesis records 12 / 13, SNES objects 12 / 13; the game parks both at (0, 0) for a moment
  as a period starts, which is ignored). A net off (0, +/-268) until it is back; the game stops play. Side from the
  next faceoff (|Y| 40-100 on that side: attacker; 100+: defender), whoever: the nearest player of that side
  (goalie included) to the net as it starts to move; with no telling faceoff (period end, goal, centre) the nearest
  skater within NET_REACH 45. `goal`: the attackers scored within 2 s (Courtnall, P3 2:17: net off with the goal).
  The user's SDL16 game 2026-10-16_2018_PHI-VAN (single player, PHI Home; the first SDL16 game recorded live: ROM
  named SDL16 correctly): six, all of Vancouver's net, slid 29-41 units over 2.6-8.4 s; Smith, Courtnall twice,
  Damphousse (attackers, faceoffs at the neutral dots), Vancouver's goalie John Blue (faceoff in his zone), Fedorov at
  the P1 buzzer. None in any other recording. Shown: a banner (not for one that came with a goal), team stats
  "Nets knocked off (theirs / own)", the card, Help, season NET (team: theirs · own a game; skater). The viewer
  draws each net where the game has it (2026-10-16, the user agreed): `netsAt(f)` from match.nets. Overhead
  rink: the nets aren't baked into the rebuilt picture; `drawFlatNet` draws both every frame (in game units,
  between the ice and the players), so a loose net slides and its goal line shows empty. Rink picture: while a net is
  off, its painted net is covered from `netlessPicture` (built at load: the top net covered with the ice beside it,
  PAINTED_NETS.top [388, 150, 124, 70]; the bottom one, [385, 1285, 130, 75], with the netless top end mirrored about
  the red line, so crease and goal line line up), choosing the painted net shown at that end (mirrored past 90
  degrees), and the game's own net picture is drawn where the net is: NET_FRAMES front view at the top of the screen,
  from behind at the bottom (Genesis 405 / 406, SNES 406 / 407; SNES frames 406-408 now take palette 2 like the puck,
  `PUCK_FRAMES` 395-408, white and red instead of green and orange: SNES sprite libraries rebuilt), or a flat net
  without game sprites. Checked in headless Edge: Smith's (top, picture and overhead), Courtnall's P2 3:18 (bottom
  net pushed back to the end boards, picture; and turned 180). `&overhead=0` in the address shows the rink picture.
  Summary VERSION 13.
- Goal spots, shot speeds, checks that pay off, goalie giveaways (2026-10-16, the user asked for all four):
  - `add_goal_spots`: each goal's `net` {x, z, end}: where it crossed the goal line, x across the mouth as the shooter
    sees it (negative = his left, posts +/-20), z the puck's height (both systems). The game
    counts the goal a moment before the puck reaches the line and then puts the puck at a resting spot in the net, so
    the crossing is projected from the last two different positions before the line (consecutive samples repeat).
    Found for 60 of 72 goals; Genesis heights 5.7-13.2. Viewer: a little net (shooter's view, crossbar at 16 units)
    beside the goal banner's text and on each scoring-summary line, with a tooltip ("In the shooter's left, low");
    a goal without a height (none now) gets a dashed line over the net's height.
  - Shot speed: PUCK_SPEED_SCALE 0.015 game units a (real) second per unit of the shot list's `speed` (measured from
    loose pucks' movement: 0.0145-0.0155 on both systems; a 23000 shot = 78 mph). Viewer `shotMph`: shot tooltips, the
    card (average and hardest); season summaries `shotMphSum` / `shotMphN` / `shotTop` (the season keeps the max), the
    Skaters tab's SHOT MPH and TOP. BOS-PIT: Bourque 71 average, 99 top; Neely 34 (quick wrist shots).
  - `add_check_payoff`: each hit's `onCarrier` (the player hit had the puck in the 0.5 s before), `gain` (his team had
    the puck within CHECK_GAIN_MS 2 s, before the other team), `shotAfter` (an attempt within 5 s of the gain), and for a
    check on the carrier `goalAfter` (a goal within CHECK_GOAL_MS 8 s, the other team never having the puck): that goal
    gets the kind 'off a check' (8 in the recordings, 3-7 s after the check; without the carrier rule it was 13).
    Team stats (Physical: · on the puck carrier, · -> puck / shot / goal), card, season (team CHK->G, skater CHK->).
  - `add_goalie_giveaways`: a goalie's pass picked off (turnover 'pass picked off' whose giver is a goalie; not a
    poke check or a hit on him) and the other team scoring within GIVEAWAY_GOAL_MS 6 s with at most GIVEAWAY_PASSES 2
    passes, his team never getting it back: the turnover's `goalAfterFast`, the goal's kind 'goalie giveaway' (4 in
    the recordings, each 1-2 s after the pick-off: Moog twice, Joseph, Belfour). Goalie card, season GV->G (goalie),
    GK GV->G (team). Summary VERSION 14. None of the four reviewed by the user yet.
- Shot aim (2026-10-16; the user: "I really like adding where each shot was aimed"). Both games send every shot at
  one of nine points: SNES `doshot` (NHL94SNES disassembly) indexes `shotsets` ($9E:E43F, found from the code's
  `LDY #$0108` / `LDY #$FEF8` goal-side loads, then `LDA passdir; ASL; ASL; LDA #$9E; LDA #$E43F`) by `passdir` ($0D03);
  the Genesis code at ROM $C3B6 indexes the table at $C542 by RAM $BEDC. Same keypad grid on both: (0,12) (s,12)
  (s,6) (s,0) (0,0) (-s,0) (-s,6) (-s,12) (0,6) for directions 0 up, 1 up-right ... 7 up-left, 8 none; s = 15 SNES, 16
  Genesis; the second word is the height row (0 = no lift, else puckvz from distance and power, capped $1800). Then
  random scatter (doshot: none when gmode bit $0010 is set; under 201 units from the target only if a roll in
  16 + shotacc comes under 15; size grows with power, distance, poor accuracy, capped). The direction is the stick's
  SCREEN direction (checked at every person's shot in four Genesis and two SNES games: $BEDC / passdir = the stick, the
  same whichever end is attacked), so attacking down the screen the stick's left is the shooter's right, and up is
  always high: likely why SNES goals into the top net went in higher (people push toward the net), while Genesis
  shooters mostly held plain left / right (middle height) either way. Readers keep `aim` [frame, direction] whenever it
  changes (`AIM_DIR` / `PASS_DIR`, `AIM_TABLE` per system; Genesis only where fast.bin covers $BEDC, not capture1 /
  capture2); `add_shot_aim` gives shots and one-timers `aim` {d, x (shooter's view, as goal.net), z (row)} and goals
  their scoring shot's. Goals' aims and their projected crossing points agree closely (e.g. aimed (-16, 6), in at
  (-17.1, 6.0)), which confirms both. Viewer: shot tooltips ("aimed high, the shooter's right"), a dashed blue ring
  for the aim on each goal's net picture beside the yellow crossing dot, the card's "Aimed high / middle / ice";
  season summaries `aimShots` / `aimGoals` (3 x 3, rows high / middle / ice, columns his left / middle / right;
  VERSION 15) and the Play style tab's "Where shots are aimed". Early numbers: aimed high 7 goals in 20, middle 17 in 99.
- Zone entries (`zoneEntries`, find_zone_entries): the puck crossing a blue line (Y = +/-89) from the neutral zone
  into the zone a team attacks with that team last to touch it; 'carried' (on a stick), 'passed' (a counted pass
  across), 'dumped' (anything else; `recovered` if they got it back first). Hysteresis: the puck must be back under
  |Y| 83 before another. Icings are left out. `end` = when the puck left the zone (or a whistle); the viewer counts
  an entry as leading to a shot attempt if the team had one in [f, end]. Team stats (count, carried/passed/dumped,
  led to a shot), player card, and the "Zone entries" map (disc carried, diamond passed, hollow dumped, accent ring
  = led to a shot). capture6: Boston 35 (27 carried), 21 led to a shot attempt.
- Skating (viewer, `findSkating`): distance from straight-line moves over 0.1 s windows; top speed over 0.5 s of live
  play. A window restarts at a recording gap (> 150 ms), a new period, or a one-sample jump over 12 units (the game
  moving a player: bench steps, the box, penalty-shot set-up, period line-ups - these had produced 125 mph). Real
  seconds, 536/178 units per foot. Busy skaters go about 2 miles in a 5-minute-period game; top speeds 29-44 mph
  (the puck's slapshots come out at 80-95 mph on the same scale). Card: Skated, Top speed; team stats: Distance skated.
- On the ice (viewer, `onIceStats`): shot attempts and goals for/against while a skater was on (at the release or
  the goal), and plus/minus as the NHL counts it (power-play and penalty-shot goals count for neither side).
- Game flow (footer button, remembered; `drawFlow`): a strip over the footer, replay time across like the seek bar:
  each team's shot attempts as step lines in the team colours with goals as dots, power plays shaded (a team with a
  player serving, from the stat snapshots), played periods marked (the index going to 3 and 4 after a regulation
  final horn is not shown as OT). Builds up as the replay plays; hover gives the time, score and counts (only time
  past the replay's position, no spoilers); click seeks.
- Sound (2026-10-15): `sounds/<ROM crc32>.js` (made with the sprites when a game is converted; not in git) holds a
  ROM's sampled sounds as base64 8-bit PCM. Genesis (`genesis.build_sounds`): the 11 PCM samples the Genesis
  disassembly locates (puckget, pass, shotfh, shotbh, check, check2, hithigh, playerwall, crowdcheer, crowdboo,
  oooh: 8-bit unsigned, centred on $80, ended by zero bytes); all 63 NHL '94 ROMs in the ROM folder keep them in the
  same places. The horn, whistles, beeps and music are FM synthesis (would need a YM2612 emulator) and are not
  there. SNES (`snes.build_sounds`): the 42 BRR samples of the sound chip's upload blocks (decoded with the SNES
  filters), unnamed in the SNES disassembly, so numbered s01-s42; `snes.SOUND_ROLES` maps event names to them once
  the user has identified them by ear (empty so far). The playback rates are not worked out (set from the note the
  driver plays): 10 kHz and 16 kHz are guesses, adjustable in the viewer's sound panel (remembered per system).
  The viewer plays them as the replay passes their moments (`findSoundEvents`): passes, shots (forehand/backhand by
  the shooter's animation), puck pickups, checks (big hits louder, boards crash), goal cheers, post "oooh", boos at
  home penalties. Footer "Sound" toggle (remembered) and a panel with each sound, speed and volume. Game files carry
  the sounds.
- Heat map: a "Skating / With the puck" menu beside whose map (remembered; `&heat=puck` in the address). Skating
  (the default): where the skaters went, puck or not - a team's five skaters (goalies left out) or one player, while
  on the ice in live play (the user found a skater's puck-only map too thin: a defenceman carries it for under a
  minute a game). With the puck: where the puck was while that team or player had it (puck owner). A 5-unit grid of
  real time (the puck hidden at whistles is left out), blurred, scaled to the 97th percentile (skating maps with more
  contrast, power 1.6 instead of 0.7, since skaters cover the whole ice); both teams in their own colours (the busier
  team per cell), one team or player on a yellow-to-red scale. Filters beside it (not remembered; in the address as
  `&period=1..4` (4 = OT), `&strength=even|pp|sh`, `&puck=ours|theirs|loose`): the period; strength as seen by each
  team (players serving a penalty, not delayed calls, from the stat snapshots, as the game flow's power plays: more
  of theirs in the box = power play); and, for skating maps, who has the puck (that team: attacking; the other:
  defending; nobody: loose, by the puck owner). The time shown under the title is the time the filters let through.
  Both teams (2026-10-16) is drawn as the difference: each spot in the colour of the team that spent more time
  there, by how much (97th percentile of the gaps, power 1.4, small gaps faded out), so neither team hides the other.
  The footer wraps onto a second row when it runs out of
  room, and the seek bar keeps at least 140 px, a map on it included.
- Player card (2026-10-17, the user saw values run past the card's right edge): its two stat columns are
  minmax(0, 1fr), so a long value can't widen the left column and push the right one out; a stat whose label
  and value pass 21 characters takes the whole width (`.stat.wide`, its value wrapping), and short stats fill the gaps
  around it (grid-auto-flow dense). Checked in headless Edge on skater and goalie cards of 2026-10-17_2246_DAL-BOS.

## More team stats (2026-10-18)

The user picked eight things the match files had but the team stats did not tally (all in fillTeamStats, each with a
STAT_HELP explanation): Shooting: Posts and Own goals (into own net) when any, Wrist shots / Slapshots (G / att, by
`type`), Aimed shots (G / att) with · high / · middle / · at the ice (`aim.z` 12 / 6 / 0), Shot speed (avg / top mph,
shots and one-timers as the card); Advanced: Saves: held / rebound / cleared (the team's goalies, shots' `after`);
Puck control: Giveaways · picked off / lost and Takeaways · hit / poke / hook / steal (turnovers' `how`); Physical:
Body checks · shoulder / hip / cross-check (hits' `how`; unseen ones left out), Injuries caused when any. EA Specials
were already there (Advanced, Genesis games with an attempt). Five BOS-DAL games: aimed high 10 goals in 35, middle 25
in 90, at the ice 2 in 33. Checked in headless Edge on 2026-10-17_2246_DAL-BOS: every split adds up to its parent.

## Shots on goal by direction; the puck meeting a skater (2026-10-18)

The user's box-score database has about 10% more shots on goal going up the screen than down. checkpuckcoll: the stick
(puckstick) only plays a puck at height <= 5 with Zvel <= $200, within 14 (cstick) of the frame's hot spot (7 while
the puck's nopuck timer runs; a goalie 8); a shot (sf2shot) slower than 13000 ($32C8) is caught (puckglue; a goalie's
catch calls ChkShotStat), faster deflects (a2touchpuck clears the flag: never counted); passes / loose 13000 + 350 x
Stk. Recordings (13 Genesis games, shots and one-timers that reached the goalie): uncounted aimed at the ice 9/22, middle
21/189, high 2/61; people's aim going up high 35% / middle 53% / ice 12%, going down 16% / 59% / 25% (they push toward
the net). Predicted counted share 0.88 up against 0.83 down (about 6%), part of the 10%; but in the recordings middle
aims were uncounted 16% up against 7% down (unexplained), so they show no overall gap. Skater bodies (puckbody, circle 8,
not goalies, not a one-timer swing): puck above 16 ($10) skips all collisions; height <= 8 hits the body only when
distance^2 & $F == 0 (about 1 frame in 16); 9-16 always: bounce out from his centre at offset x 256, SPAcatch if slower
than $3000, FallDown if faster and above 12. Recordings (fast loose puck within 8 of a skater): 0-5 passed through 82%,
taken 10%, course changed 8% (470); 6-8 through 94% (35); 17+ over 100% (21). In GENESIS_SHOOTING.md 4.7 and GENESIS_MECHANICS.md 13.5,
GENESIS_GUIDE.md 6.

The same on the SNES (2026-10-18, NHL94SNES checkpuckcoll / _ccx, puckstick, puckbody, ChkShotStat): collisions only
with puckz < 16; skater stick: puckz < 5, puckvz < $100, within 14 of GetHot, d^2 <= $C4 (/4 while the puck's nopuck
runs); body: circle 8 (d^2 <= $40), puckz >= 8 always, lower only when d^2 & $F == 0; FallDown at speed^2 >= $9000000
and z >= 12, else SPAcatch. puckstick's limit is 10000 + (no shot flag: 700 x Stk) + 3000 when `position,x` is 0 or x
is passReceiverPlayerNum, but x is the puck there (curobj), whose position word reads 0 (707 of 707 samples): every
stick gets the 3000, and a faster puck always
deflects. Shots on goal as on the Genesis (puckgoalie / goalie puckglue call ChkShotStat; a2touchpuck clears $1000;
after a goalie's stick deflection the body box test runs but the flag is gone). The goalie's hot-area height window
(xg_snes RomData.hot): ready none, stick saves about 0-6, glove saves 7-15 (r6), one stick save facing down -2-8 r8
against 2-5 r2 facing up. Recordings (5 SNES games): uncounted high 6/29, middle 15/104, ice 2/14; aim going up high
49% / middle 46% / ice 5%, going down 2% / 88% / 10%; uncounted up 12/70, down 11/77; pass-bys < 5 high: through 81%,
taken 13%, course 7% (291); 5-7 through 6/6; 8-15 hit 5/5. SNES_SHOOTING 4.6, SNES_MECHANICS 6.2, 7.5; SNES_GUIDE 6.

Home / away and up / down (2026-10-18, the user: Home wins about 51% in their data): setplayer's HmAwBonus = team data
(+8 offset) byte 2, home high nibble added, away low nibble subtracted (byte 1: PP low nibble, PK high nibble); nhl94.bin
per team listed in GENESIS_MECHANICS 13.6 (average home +1, away -1.1). Faceoff roll 17/33 Home at equal timing. Camera
($BD18) lead over the carried puck toward the attacked net: up median 43 / mean 33.5, down 36 / 24.1 (9,330 / 9,872
samples, all Genesis captures). Home goes up in P1 and P3.

Checks by a person or the computer per skater (2026-10-18, the user: Bourque surely checks more than computer skaters):
the hit's `human` (the controlled-skater marker within 0.3 s, add_play_context). Card "Checks: person / CPU"; season
summary skater `checksHuman` (VERSION 19); Skaters tab CHK PERSON (person · computer). Documents games: Bourque 62
checks in 6 games, 27 a person's, 35 the computer's; Neal Broten 20, all a person's.

Shooting study (2026-10-18, docs/SHOOTING_STUDY.md; analysis/shot_table.py writes matches/shot_study.json, then
analysis/shot_study.py prints the tables): 13 Genesis games / 387 shots and one-timers, 5 SNES / 189. Exact-shot test
(the flight projected to the aim line within 2 of the aim point): a person's shots within 200 went exact 60/124 Genesis
(rule predicts 68), 25/49 SNES (22); beyond 200 none. Findings: goals don't depend on up / down; home and away shoot the
same for person-played teams (20% / 20%); backhands score more (21% against 14%, xG agrees: slower, less scatter);
rebound shots 8/17 Genesis; a person in net faces harder shots (xG 32% against 23%); off-wing shooters a little better.

Home / away x up / down (2026-10-21, the user asked for the four cells): analysis/shot_table.py now also writes
matches/shot_study_periods.json (each team's game seconds per period and direction) and a shot's `person_team` (the
team had a ctrl bit in most samples; BOS-WPG had people on both sides); analysis/home_direction_study.py prints
SHOOTING_STUDY's first section: per cell game minutes, attempts / shots on goal / goals per 5:00, rates, xG, uncounted
stops, aims, exact shots, and rate ratios with 95% ranges. 19 Genesis / 8 SNES games: every range includes 1.00; Away
going up (period 2) weakest on both systems; Genesis up / down shots on goal 0.89 (0.73-1.09); SNES home goals 1.52
(0.93-2.47). Home attacks up in P1 and P3, down in P2 and OT (all games).

Study part 2 (2026-10-18, analysis/direction_study.py, SHOOTING_STUDY.md part 2): count per team-period (Home goes up 2
periods, and a person mostly played Home, so raw up / down totals mix in the person's team). Genesis per period up /
down: shots on goal 3.8 / 4.3, goals 1.2 / 1.3, checks 6.9 / 6.4 (34 team-periods each): no clear direction effect
(about 100 whole games needed to see 10%). Home bonus visible: working ShA - 5 x rating +0.87 home, -0.78 away.
Faceoff count: away 88-77 (Genesis), 39-35 (SNES): the built-in home edge doesn't show (the count is first possession,
and mashing dominates).

## Screen sides by direction (2026-10-18)

Someone pointed out to the user that people (maybe the computer too) may favour a side of the SCREEN whichever way
they attack. season.py `screen_sides` (summary VERSION 18, per team `sides`: 2 x 19 numbers, going up then down, from
own_end: a team's goalie at -Y = going up): carrying game seconds by position (LD, RD, LW, C, RW) and by the puck's
half of the screen (x < 0 left), shot attempts from the screen's left / middle / right (SIDE_MIDDLE 20) and goals,
shots aimed at the screen's left / middle / right (aim.d 5-7 / 0, 4, 8 / 1-3: the stick on the screen) and goals.
Season page Play style: "Screen sides, going up and going down" (a row per team and direction). Viewer: team stats
group "Screen sides" (closed at first) with the same numbers live (`ends[f] === team` = going up), each a total and
· going up / · going down. The five BOS-DAL games together: aimed goals going up 7/36 screen-left, 11/34 right; going
down 11/32 left, 4/35 right: the shooter's right both ways, not a screen side (small samples).

## Deserve to Win meter (2026-10-18)

After MoneyPuck's (moneypuck.com/about.htm#meter; the user asked for it). tools/deserve.py (the season page) and
viewer.html deserveToWin (keep in step; checked equal on three games): exact, not simulated. Unblocked attempts with
their xG; without one FALLBACK (pass shot 0.19; shot / one-timer the system's average; deflection / other 0.25 flat,
because the converter finds those only at counted events, so their recorded rate is mostly goals); a team's shots
within FLURRY_MS 3 s = one chance (1 - product of misses); regulation goals as exact distributions; a tie goes to
sudden death: real OT flurries in order, then (game over) the unplayed OT (OT_SECONDS: Genesis 600, SNES 300, the
user) as a race at each team's regulation xG per game second; still level = tie. Mid-game (viewer before the last
frame): shots so far, no OT: deserved to be ahead. Viewer: Advanced "Deserve to win" and "· a tie", a dotted line on
the Game flow strip (home share = win + tie / 2, home up) and in its tooltip, Help. Season: summary team `dtw` [win,
OT win, tie, OT loss] (VERSION 20), standings DESERVED (2 x win + tie) and +/- DESERVED. The user's leagues give no
point for an overtime loss, so PTS is 2 x W + T too, and a game's two teams share 2 points. Recorded games:
Dallas 5-2 Boston 65% / 34% (Dallas finished above its chances), Calgary 6-5 Boston OT 45 / 48, tie 7%; Boston 8 points
against 8.6 deserved.

One-timer study (2026-10-18, analysis/one_timer_study.py, SHOOTING_STUDY.md part 3, GENESIS_GUIDE 7): Genesis 91
one-timers: goalie 10+ off the puck-to-net line at the strike 68% scored, 0-4 off 11%; pass moving the puck 40-90 across
47%, crossing the middle 18%, under 0.5 s in the air 33%; inside 100 units 44%, beyond 10%; xG agrees throughout. SNES 55,
no clear pass effect.

SNES goalie hold (2026-10-18, NHL94SNES puckgoalie): hold when |vx| and |vy| < randoma((2 + shotspd) << 9) + $2000
(shotspd = PkC for goalies), not pflags $1000; else bounce (velocity = offset bytes, y sign set against his Yvel); a
diving goalie lets puckz >= 5 through; save-rating lookups unused. Recordings (102 saves): faster component 17000+ held
at once 4/41, 8192-17000 28/45, under 8192 10/16. SNES_SHOOTING 5.4, SNES_GUIDE 11.1. SNES steals (puckstick .t1):
stick within d^2 < $25 of a carried puck; randoma(36 + Stk carrier - Stk stealer, makepde) < 3 -> deflect, both nopuck
Stk + 20; a goalie always steals, never robbed; no slot rule (SNES_MECHANICS 6.4).

Open nets (2026-10-18; the user: accuracy drops when the other goalie is pulled or far out). Code: ReadGoaliePulled
(tst.w tmgoalie of the SHOOTER's team; tmgoalie = -1 in a delayed penalty for the fouled team, and for a computer team
down 1-2 in the last minute of P3 after a faceoff outside its own zone: CPgoalie) is only used for the shooter's team;
shotdiradj aims high middle (passdir 0) when the goalie heads 44+ off the crease, 8 with none. So no penalty for an open
net; misses come from distance (never exact beyond 200, wide scatter), upward-only scatter (high aims clear the bar),
and the screen-direction aim. CORRECTION (the user: the misses were one-timers, Genesis only): shotdiradj gives
one-timers (and computer shooters) passdir 0, high middle, when |sum of CalcAngleOffset over both posts| > $2C, i.e. the
net's middle more than 22 units off the line from the puck to the goalie's predicted spot; target z 12, crossbar 13,
upward-only scatter: an exact one goes in under the bar, a scattered one over it (empty net, 40-60 units: about 60% vs
100% aimed mid-middle). Recordings: 10 such one-timers, 7 goals at heights 10-13, 1 over at 16 (2257 P1 0:57), 2 saved.
SNES one-timers follow the stick (not affected). GENESIS_SHOOTING 4.4, GENESIS_GUIDE 7. Empty-net chances by aim and distance from each system's scatter rule in
GENESIS_MECHANICS / SNES_SHOOTING 4.2 and the guides' shooting tips; recordings: 5 shots with the goalie far out or
pulled (an empty-net test is in NEEDS_FROM_YOU).

SNES penalties by move (2026-10-18; checkcheck, Bcheck, holdcheck, checkagr): R = (20 - GGSleft) x 16, asl.b for a
person, lsr.b within 40 of the puck, randomd0(R); check up -> $18 / $1A on 0, check down -> $1C / $1E on 0, poke / body
in front (always trips with OptPen on; off: a person's needs randoma8(16 + aggress - target legstr) >= 12) -> $22 under
5, hook / hold -> $20 / $28 on 0; breakaway -> $24 (PenShotChk). Recordings: 15 penalties (one code $30 unread).
SNES_MECHANICS 8.5, SNES_GUIDE 10.1.

SNES breakaways and injuries (2026-10-18): CheckBreakaway = carrier in his attacking half and no opposing skater
more than 4 nearer the goal (teammates ignored); StartBreakaway at the blue line counts it; doshot re-tests (a caught-up
breakaway ends: no breakaway goal); PenShotChk re-tests at a foul. Injury (FallDown): the carrier only, SPAfallback,
facedir & 3 == 0, hitter a skater, randoma8(150) x 2 < impact, clock running; setInjuryType $FFFD (period) or 1 in 7
$FFFC (game); roughing $14 with penalties on. SNES_MECHANICS 10.0, 10.9.

SNES one-timers (2026-10-18, asspassrec): request = a person's new A ($0080 in padnew) while waiting (B $8000 cancels),
or a computer team in the attacking zone (|Y| past $58) on RandomWord & $80; the swing (SPAonetimerf / b by Findhittype)
starts at once, tmOneTimerSwings counted; while SPAnum < $10, nopuck 10 and a strike when ApproxLength(blade - puck)
< 8: puckc = him, passdir = paddir (person) or 8, passspeed $24, tmOneTimers (clock running), a2touchpuck, doshot.
Recordings (pad C bit = SNES A): connected 0-590 ms after the press (median 199), failed swings ended median 465;
Genesis 0-870 / 585. SNES_SHOOTING 4.5, SNES_GUIDE 7.

SNES faceoffs confirmed (2026-10-18, analysis/snes_faceoffs.py): stage = 8 x the (frame, time) pair index of the
centre's current animation (assfaceoffpl SPAnum / 4 + 1, +3 for handed 0, table 0,8,16,0,8,16); winner from the puck's
Yvel after the drop (32 x dirtab + / - $800); 70 draws: home 36 vs 38.7 expected; stage diff -8 / 0 / +8: 20% / 48% / 74%
(model 28 / 53 / 78). doinput passes padnew, so a swing needs a new B press. People's stages 27 / 45 / 28%.

Goalie study (2026-10-18, the user's list; analysis/goalie_study.py; GENESIS_SHOOTING 5.5-5.9, SNES_SHOOTING 5.5-5.7,
both guides). Genesis C for a person's goalie (doinput_cbut): faces the puck, goaliesave's move, speed / 4, locked ~0.57 s
(pad stack 0.72); reach unchanged (15) except a pad stack (18, jumps 6 and slides toward the middle, away from his side:
shift by goalie x sign); in a save move the in-close hold quartering is skipped (computer goalies held 62/100 in a move,
32/89 standing). A person's goalie out of view ($74 / $64 from the camera) runs checkanim (assgoaliectrl). Person C
shots 7 goals / 19 (xG 0.21) vs 18 / 45 (0.37): too few. SNES: a person's goalie makes a save move while A ($0080) is
HELD (assgoalie .5x), every rethink, no shot needed; the save frames add a hot area 12-28 to one side (standing: body
box only), so on the SNES it does make him bigger. Genesis wind-up rule (checkanim): shot mode (sflags bit 3) with
|pucky| > 208 and the goalie |x| <= 20 -> goaliesave at once, only when bit 1 of the seconds left (gameclock $C468) is
clear; the ellipse widens to 34 x 26 during wind-ups. Recordings: 35 of 100 shots within 60 at computer goalies had an
early save (13 goals, 37%) vs 65 (8, 12%); 33 / 35 with the clock bit clear; 27 pad stacks, 22 / 23 slid toward the
middle; 11 / 11 such goals went in on the shooter's side. Positioning target x = halfway between carrier and puck
(TmpPuckX). Goalie lag behind the puck-net line within 30 of the goal line: 18 units at 110+ units/s across. SNES: no
wind-up save; a carrier in SPAshotf..$F020 skating mostly up / down zeroes the goalie's speed once (goaliestopped);
ellipse 26 x 20 -> 34 x 28 in a wind-up. Long slapshots (xg.py rules, recorded CPU-goalie states): power dominates (16-23%
from 120 out at 24000-28000, a few % below 20000), far ~ near only at 24000+; ShA doubles 10 -> 20% at 120; the user's
far-post claim not shown (asked for examples). Goalie pushed in with the puck: Genesis checkgoal takes a carried puck off
its carrier (nopuck 8) at the goal box, goalie included, so the loose puck can then be nudged in; SNES checkgoal returns
when puckc is a goalie. None recorded.

SNES computer positioning and line changes (2026-10-18, SNES_MECHANICS 12.1 / 12.4): every SNES assignment checks
possession at its top every frame (assreplace to the other side's job when the other team has the puck), so awareness
only paces spot re-picks; the Genesis waits for the tick. After turnovers, computer skaters skating up the ice turned
back a median 900 / 885 / 780 ms (D / W / C) vs Genesis 1159 / 1050 / 952 (466 SNES, 831 Genesis cases). Spots as the
Genesis except: assdefo y by puck zone (98 att, -78 neutral, -216 own, -98 offside); assdefd 40 behind the deepest
attacker (Yvel >> 5, only toward his net), -220 once past -190, check4check; asswingd y = puck y outside -78, -158 with
the puck in his zone, goal line behind it, -78 vs a goalie carrier or offside; asswingo neutral (100, 60 +/- 10);
assnearest waits at the blue line when the other goalie holds it. chk4lc as the Genesis (OptLine 1 = on on the SNES);
CompLine: PP / PK fresher unit, even strength rotation tables (3rd-period lead / trail variants), fallback first line
>= $F34 energy.

Blue lines and the step-out move (2026-10-18, analysis/blue_line_study.py, GENESIS_MECHANICS 12.5): positioning reads
the puck's zone (88; 78 for defending wingers) and possession; Genesis assdefo only while the puck is in the attacking
zone, else assdefd. Defending D sit 50 (SNES 40) behind the deepest attacker at DfA ticks, so a step-out draws them only
once the attacking forwards leave (asswingo / asscentero neutral boxes at their ticks); defending W / C come out with
the puck every frame. Recordings: 17 Genesis carries out and back in within 4 s, untouched; 16 under 1.2 s with the
deepest teammate still in the zone and the D unmoved (median 63 from their goal line vs 149 at plain carried entries);
the 1.8 s one (2219 P1 3:59) drew the D from 42 / 103 to 100 / 162; 8 / 17 shot attempts in 4 s (plain 53%). Offsides
off: the flag never sets; on: re-entry with a teammate 10+ inside flags the team, any touch past 104 is whistled.

## Live broadcast (2026-10-18)

The user asked for a URL others can watch live, "on par with clicking Play on a full match file". `tools/live_broadcast.py`
+ the helper's `--broadcast <channel> --bucket <bucket>` ("NHL94 Helper - Live.bat", user-specific, not in git):
- While recording, the helper sync-flushes fast.bin.gz every 2 s (LIVE_FLUSH_S); the broadcaster thread every
  INTERVAL_S 3 s (2026-10-19; was 5 with a full conversion of about 8 s at a game's end) asks its worker for an update:
  `export_match.py <recording> --live --name --out captures/_live_work/out` (in the exe `--export --live ...`), one
  process per game at below-normal priority, stdin "update" -> stdout "ok n" / "wait" / "error ...". The worker keeps a
  GrowingCapture (decompressobj over only the bytes fast.bin.gz / full.bin.gz grew by) and the system's MatchReader
  (genesis / snes: read_match split into feed(cap, final, count, checks_known) and result(); feed holds back the last
  0.5 s, which the rollback test needs), then runs export_match.analyse (everything after read_match) and writes the
  match. xg.py / xg_snes.py cache each shot's result by all its inputs. Checked: all 28 recordings convert byte for
  byte as before; feeding in 300-sample pieces equals one go (two Genesis, two SNES); the 5x test of 2219 WPG-BOS: 37
  updates, 0.12-0.5 s each (max 1.7), the last one identical to the final conversion; SNES 1934 BOS-PIT: 42 updates, up
  to 1.36 s at the end (result()'s read_penalties and goal scan run over the whole game), the live arrays a prefix of the
  final ones (the last 0.5 s held back). Then it uploads to s3://<bucket>/live/<channel>/: data/<game>/s<n>.json (whole match,
  every SNAPSHOT_EVERY 6 updates) or c<n>.json (a diff: per key {s} / {p, v} common-prefix tail / {d} / {x}),
  gzip with Content-Encoding, then live.json (no-cache manifest: status waiting / live / final, game, seq, snapshot).
  At start it uploads index.html (viewer.html with window.NHL94_LIVE = 'live.json'), the rink pictures / js and bench
  masks; sprites/<rom>.js and sounds/<rom>.js with a game's first update. After the helper's normal conversion the
  finished match goes up as the final snapshot. Uploads: boto3, else the AWS CLI (`aws s3 cp`).
- viewer.html live mode (window.NHL94_LIVE): polls live.json every 2 s, joins from the newest snapshot plus later
  diffs, applies new diffs and re-runs load() keeping the moment, the map's who and the highlights panel (30-40 ms a
  reload for a 15-minute game in Edge); plays liveDelay() (at least 6 s, 1.4 x the longest gap between updates + 2 s) behind the newest data and holds
  at the end instead of stopping; footer LIVE / Go live / Final button; the stats tab polls too; a game file saved
  from the live page has the live line removed. Help: "Watching live".
- Live smoothness (2026-10-21, the user: play got choppier as each game went on). Measured end to end (the live test
  of 2026-10-21_1147_NYI-BOS at 1x into a folder, served locally, the page watched in headless Edge over the DevTools
  protocol, every animation frame logged): drawing stays at 0.2-2 ms a frame all game; what grew was each update's
  reload, load() over the whole game (9 ms early, 35-38 ms late, half of it findSkating, then findLineChanges and
  findPossession) plus livePatch copying every list, every 3 s, with playback stopped: 27 frames over 50 ms in the
  last 4 minutes. Now findSkating and findLineChanges carry on from the last reload's samples (resumeScan: same game,
  same first and last-seen sample; checked equal to a full pass on a Genesis and a SNES game fed in four pieces),
  livePatch extends lists in place, and updates wait (livePending) until playback is within LIVE_LEAD_MS 1.5 s of the
  loaded end or LIVE_HOLD_MS 12 s have passed (at once when not following). Same test: 108 reloads instead of 169,
  8-13 ms each at the end, 9 frames over 50 ms in the last 4 minutes. The long holds at the end of the data in that
  test are the recording's own breaks (intermissions, pauses: no samples for 80 s at a time), not lag.
- Tested: `python tools/live_broadcast.py --test <capture> <folder> --speed N` (a recorded game fed in at N x into a
  growing gzip, uploads written to a folder; served with http.server, NHL94_LIVE_UNZIP since it sends no
  Content-Encoding): 2246 DAL-BOS at 10x, 12 updates, the page joined mid-game and played 11 s behind with all stats;
  snapshot + diffs rebuild the match exactly; final 5-8 equals the real conversion. The helper end to end with the
  fake emulator (tests/helper_live.py): 6 live updates and the final.

Posts (2026-10-18, the user): the card's "Posts" (his shots with result 'post', live-knowledge aware), season summaries
VERSION 21 (team posts / postsA, skater posts), season page Skaters POST and Team stats POST a game (· against). The
team stats already had Posts. The live launcher sets NHL94_HOME to Documents/NHL94 Viewer and copies the current pages
there first (the Python helper doesn't copy pages; the exe does).

Review of the user's two live test games (2026-10-18_1934_BOS-PIT, 2026-10-18_2006_CHI-LA, both SNES on
NHL94_Classic): shots on goal, goals, checks and faceoffs equal the game's; counted passes 45/50, 45/47, 62/65 (the
known gap). From them:
- SNES penalty shots: snes.View.on_ice needs each team's on-ice roster places to differ, and in a penalty shot the
  parked players (x = -240) can share one, so parked objects are left out of that test (433 samples: pre-faceoff
  moments). Replaying snes_2026-10-15_1755 through the helper (tests/helper_snes_penalty_shots.py) records both
  penalty shots. The puck shows during the shooter's run and hides after the shot (gmclock).
- add_own_goals skips penalty-shot goals and hidden-puck samples (a defender holding the puck at the whistle before a
  penalty shot would otherwise read as an own goal: Wesley in BOS-PIT, Steve Smith in CHI-CGY).
- Posts: a puck coming out from behind the net past its side isn't a post: both readers want |y| <= 268 and the puck
  not behind the goal line (268) in the half second before (28 posts over all recordings); shots on goal equal the
  game's everywhere.
- Goal heights projected above the crossbar (up to 13.9) are capped at 12.9.
- SNES puck frame 406 (a net picture) in the puck's frame word: the viewer shows the puck at rest for any frame
  wider than 12.
Not changed: Stevens' P3 4:52 goal had xG 0.0 (a person in net, emulated as the computer goalie); CHI-LA's 13
"lost it on the goalie" bumps are unreviewed.

## Quirky Events (2026-10-19)

The user asked for the game's oddities in their own team-stats group, "Quirky Events" (viewer fillTeamStats, STAT_HELP,
Help "Quirky events"). export_match `add_quirks` (after add_tapestries; Genesis only): goal kind 'five-hole' (in the second
before the goal the loose puck at height <= 5 passed within FIVE_HOLE_NEAR 7 of the defending goalie's centre while he was
in $021E / $01EC: GENESIS_SHOOTING 5.5's blind stick ring), 'goalie bobble' (the defending goalie held it in a shoulder
save $148E / $14C0 in the 2 s before, nobody else after: 5.3), pass `rocket` (leaving faster than ROCKET_SPEED 26000, not a
pass shot: 6.1), `runaways` [start, end, team, roster index, top] from genesis MatchReader's new `fast` ([frame, record,
speed / 100] for a person's skater with pflags bit 0 over 12000), kept above RUNAWAY_SPEED 15500 (3.4). On-ice tags
"Rocket pass" and "Runaway!", goal tags "through the legs" / "shoulder-save bobble". Found: ANA-ATL goals P1 2:48, 2:11,
P3 2:24 five-hole and P3 4:00 bobble (exactly the user's); runaways 2149 BOS-WPG, 2158 BOS-WPG and a new one in 2219
WPG-BOS (15,900); rocket passes 0-5 a game; no five-hole or bobble goal in any other recording.
SNES side (analysis/snes_runaway_study.py, SNES_MECHANICS 3.3 / 6.1): the same friction-off flag (pflags bit 0, table .22)
exists, set only by asspassrec and cleared by any stick touch (puckstick), the wait ending, assnearest and faceoffs;
FallDown never sets it: 791 stretches in eight games, median 0.3 s, max 2.7 s, fastest 10,156, so no runaways (15 games
by 2026-10-21: 1,683 stretches, max 2.9 s, fastest 11,553 for 0.6 s). Pass
lift = distance x 8 (median peak 1.4 at 100-149 units, 3.3 at 200-249); no rocket pass, through-the-legs or bobble
(already in SNES_SHOOTING 5.1 / SNES_MECHANICS 6.1).

## Diagrams (2026-10-19)

The user asked for visuals of the mechanics. `tools/make_diagrams.py` draws SVGs into docs/img, to scale from the game's
numbers (white background, so they read on GitHub's light and dark themes): saves_reach (reach 12 / 15 / 18 against the
mouth), through_the_legs_goalie (renamed from through_the_legs.svg so GitHub shows the new version at once; body 13, blade (11, -2.3), the 8-14 ring, the puck a frame at 22,700), aim_points_genesis /
_snes (both attack directions; SNES post band 17-22), shot_scatter (doshot's s by distance for working ShA 0-30, exact
chance), faceoff_timing (the 18-frame swing, average value 176 / (18 + gap), the win table). Placed in GENESIS_GUIDE 4, 6,
12.1, 12.2; GENESIS_SHOOTING 4.1, 4.2, 5.1, 5.5, GENESIS_MECHANICS 9.1; SNES_GUIDE 6; SNES_SHOOTING 4.1. Rerun the script after a number
changes. Second set (the same day): weight_bug (CCStart's knockdown number by weight difference, person 240 wrapping in a
byte vs computer 120), shoulder_bobble (ghighr / ghighl hold points, top vs bottom net), rocket_pass (passtoa0 speed vs
distance at an ideal 15,000), computer_positions (asswingo / asscentero / assdefo boxes by puck zone), rink_feet; in
GENESIS_GUIDE 9.1, 12.1, 8, 14 and both guides' Distances and speeds, GENESIS_MECHANICS 7.2, GENESIS_SHOOTING 5.3, GENESIS_MECHANICS 6.1, 12.2 and both
mechanics' Units. Third set: one_timers (press-to-strike ranges both systems; Genesis scoring by goalie offset, pass
across, distance from SHOOTING_STUDY part 3), faceoff_directions (dirtab x 32 + 2,048 toward the winner's end, the five
random directions), penalty_chances (Genesis 5 / R, R = ((40 - Agr) / 2) x 13, person x 2; SNES 1 / R with the person's
byte wrap, Agr 12 every hit), flip_spots (OneTimerTarget spots, goal-mouth box, over-the-glass strips); in both guides'
7 and penalties sections, GENESIS_GUIDE 4 and 8, GENESIS_SHOOTING 4.8, GENESIS_MECHANICS 6.3, 8, 9.2, SNES_SHOOTING 4.5, SNES_MECHANICS 8. Fourth set:
through_the_legs now overlays the game's own frame 480 (the butterfly, $021E) at 0.6 opacity, the blade at its real hot
point (9, -2) from the ANA-ATL goals (`sprite()` reads sprites/<rom>.js here or in Documents; GOALIE_PALETTE is that
game's Atlanta away palette; without a library the diagram draws without it: so a fresh clone can regenerate the
others); empty_net (MECHANICS 4.2 tables, both systems), computer_defence (assdefd / asswingd / asscenterd spots for
three puck positions); in both guides' shooting lists and both mechanics 4.2, GENESIS_GUIDE 14, GENESIS_MECHANICS 12.2. Fifth set: the game's own goalie frames on saves_reach (gready
facing down, 419) and shoulder_bobble (ghighl 667 facing down / 659 facing up; hold points from HotList (+10, +14) and
(-9, +14)); snes_flip (DumpInTarget spots and Passing scatter) in SNES_GUIDE
8.2 and SNES_MECHANICS 6.3. Sixth set: early_save (the wind-up rule with gstackr frame 454, its body
test 6 to the slide side, reach 18, the seconds-left bit-1 strip, recorded rates) in GENESIS_GUIDE 6 and GENESIS_SHOOTING
5.6; open_net_one_timer (the sightline test and the high-middle aim under the bar, the 4.4 table) in GENESIS_GUIDE 7 and
GENESIS_SHOOTING 4.4. Frames 453 / 465 are the pad stacks' first (upright) frames, 454 / 466 the sprawls (left / right). Seventh set:
puck_meets_skater (frame 1 standing facing up, blade (-4, +20) from HotList; skating with the puck 24-28 ahead; the 22 walk
band, the stick's 14 ring with the part past 22 untested, body 8, the height bands) in GENESIS_GUIDE 8 and GENESIS_MECHANICS
6.2; penalty_shot (the Genesis stages with the code's bugs under them, the SNES retake) in both guides' and both mechanics'
penalty-shot chapters. SNES set (2026-10-19, the user: whatever SNES graphics are missing): snes_saves
(six goalie frames facing down from NHL94_Classic in Toronto's away colours, SNES_PALETTE; body box -11..10; each save
frame's hot circle and height band from xg_snes RomData.hot: ready 546 none, glove 547, stick 606, pad stack 581,
butterfly 732, sprawl 780), snes_shot_scatter (doshot with passspeed = speed / 136, a 15,000 shot), snes_hot_cold (shown
18n +/- floor(3|b| / 4) squashed under 50 vs played: maxed for b < 0), snes_goalie_hold (puckgoalie's hold chance by the
faster component and PkC, recorded rates); in SNES_GUIDE 1.2, 6, 11.1 and SNES_MECHANICS 2.5, SNES_SHOOTING 4.2, 5.1, 5.4. sprite()
takes a palette and library list.

## Advanced stats (2026-10-16)

As the NHL's analysts count them, from the shot list, goals, faceoffs and who was on the ice (role and roster at the
release, the goal or the drop): Corsi (CF / CA: every shot attempt in the shot list), Fenwick (FF / FA: those not
blocked), shots on goal as the game counts them (SF / SA: `counted`, or a goal), goals (GF / GA), PDO (on-ice
shooting % + save %, x 100), zone starts (faceoffs on the ice for, in the team's attacking / neutral / defensive zone;
faceoff `zone` is in Home's view) and OZS% (attacking over attacking + defensive), and CF% rel (his CF% minus his
team's while he was off the ice). Even strength = as many players serving penalties on each side (`penCount` /
`penalty_counts`, from the stat snapshots). Viewer (`onIceStats`, idx null = the team): the card's Corsi, CF%,
Fenwick, FF%, CF% rel, PDO, zone starts, OZS%; team stats' "Advanced" group (CF% and FF% all and even strength, PDO).
Season summaries (VERSION 3): per skater `oi` / `oiEv` ([CF, CA, FF, FA, SF, SA, GF, GA]), `zs`, `bench` / `benchEv`
(the team's numbers while he was off); per team `adv` / `advEv`; the season page's "Advanced" tab (teams and skaters,
all situations or even strength). capture6: Boston CF 28-17 (62%), PDO 98.2 (31.6% shooting + 66.7% saving). With
line changes off (the online leagues' usual setting) a skater's on-ice numbers are mostly his team's, and CF% rel is
blank for players who never left the ice. So the card shows the on-ice block (Corsi, Fenwick, CF% rel, PDO, zone
starts) only for a team that changed lines: more than 12% of its skaters' ice time beyond its five busiest (without
line changes the game still sends out power-play and penalty-kill units: 0-7.4% in the recordings; with: 15-55%).
The season tab leads with individual numbers (iCF, iCF/GP, on goal %, S%, share of the team's attempts and of its
goals) and keeps on-ice columns behind "On-ice stats (for leagues with line changes)" (remembered).

Shot context (2026-10-16; EA Special naming 2026-10-16, `add_shot_context` in export_match.py, after the other event lists; every other field of
all eight re-converted recordings unchanged): each shot's `danger` - 'high' within 60 units of the net and no wider
than 50 (about 20 ft; 20 of 60 such attempts scored in the recordings against 14% of the rest; 50 x 40 scored 38% but
held one attempt in seven), 'medium' within 100 and 70, else 'low'; `assist` (a shot assist: the last pass before the
shot, completed or one-timed to the shooter within 4 s, the other team never having the puck between); `flip` /
`afterFlip`: an "EA Special", the user's Genesis community's name (after the player "EA" who invented it, not
Electronic Arts) for skating down the side, usually a winger, flipping a wrist shot on goal so the goalie bobbles it
and is pushed back, then the shooter or an onrushing teammate scores into the open part of the net. `flip` marks an
EA Special attempt (the user's definition): a wrist shot (never a slapshot: goalies hold those far more often) from
within 70 units and at least 20 off the middle, shot at a goalie in position - within 12 units (EA_GOALIE_LINE) of the
puck's line to the net at the release (on the saves in the recordings he stood 2-15 off it; on wrist shots that went
straight in, 15-51) - and saved, so not a try to score directly. `afterFlip`: the same team's next attempt, later
and within 2 s, from within 65 units. An attempt followed by a goal is an EA Special; the goal gets the kind "EA
Special" (a goal tag, like one-timer). From 2026-10-16_1314_BOS-PIT (the user's deliberate ones: P3 4:26 Oates, flip
saved, Oates scored 0.8 s later; P2 4:26 Oates, flip saved, Pittsburgh's Taglianeti collected it and put it into his
own net, an attempt only): "from the side" is an angle, at least 20 off the middle and 0.4 x the distance, up to
EA_MAX_DISTANCE 130 (those two came from 94 and 120 units, the faceoff dot and the half-boards); and a rebound a
defending skater had is not a success. The user then reviewed the whole game and listed its 14 attempts: the rule
had found 12 of them and nothing else; it missed two flips judged blocked (Juneau P1 4:51) and wide (Oates P1 4:26),
so any result counts but a goal straight from the shot; and the user added that the shooter must not be skating away
from the goal (toward his own end; standing is fine): EA_BACKWARD 50 units/s over the half second before the release
(Sweeney's real one drifted back at 30; Juneau's P3 4:09, not one, skated back at 80). With those the rule finds
exactly the user's 14, one of them an EA Special. The user ruled out the last two in the older games, giving two
more rules: not moving out toward the side (EA_OUTWARD 15 units/s; CGY-BOS OT 9:02 went from in front of the net
toward the side at 59, every real one moved in toward the middle at 9-81) and a set play, not a scramble (carried
at least EA_CARRIED 0.6 s; capture6 P2 0:08 shot 0.3 s after winning a loose puck, the real ones carried 0.9 s or
more). Now every reviewed shot reads as the user judged it: 15 attempts (14 in BOS-PIT, capture3 P2 3:59 Oates),
one EA Special. Genesis games only: the SNES goalie saves differently and is not pushed back
by a wrist shot (the user). `eaDive`: the goalie went into his dive ($02F4) within 2 s after the save, as Genesis
goalies often do on an EA Special (diving for a puck he is nowhere near, out of the play for a couple of seconds); a
detail, not a condition (none of the recordings' attempts has one). Only a person's skater makes an attempt (the
user: the computer never tries one): the shooter carried the controlled-skater marker (`ctrl`) at the release or up
to 6 samples before; the rebound may be anyone's. Always a forehand (the user): the shooter's last shooting animation
before the release is the forehand $07FC (genesis ACTIONS "forehand"; $092E is the backhand), from his forehand side
as the attacker sees it (right-handed, drawn mirrored, from the left; left-handed from the right); and not a
follow-up (no attempt by his team in the 3 s before). The user reviewed the nine attempts the rules found before the
last three: one real (capture3_bos_la P2 3:59, Oates, "not the best example but it meets the criteria"), the rest
rebound put-backs (CGY-BOS P2 4:42 and 2:22), breakaway or skate-in dekes and shots (capture1 P1 2:57, capture6 P1
2:36, P1 1:17, P2 0:26), a plain shot on goal (capture6 P1 4:33) and a backhand from in front (capture6 P2 2:27);
with the three rules only
the real one is left. The breakaway dekes were also skated in faster (about 125 units/s against 69), not used yet with
one real example. Ciccarelli's goal in capture2_away (P1 14:28), which the user called a good example of the play,
was the computer's (Detroit; the person played Philadelphia), so no EA Special is in the recordings yet; each turnover's `shotAfter` / `goalAfter` (the gaining team's attempt within 5 s,
no whistle between). Expected goals was put off until there are thousands of shots (about 250 now).
Shown: shot tooltips (high danger, rebound, flip, set up by), the card (High-danger att., Shot assists, Rebounds,
Costly giveaways), team stats' Advanced group (high-danger and rebound goals / attempts, EA Specials when any,
attempts off a pass, turnovers -> shot against), the season Goalies tab (HD SV%, Reb%: saves that gave a rebound),
and the Advanced tab (a "Chances, rebounds and turnovers" team table: HDCF, HDCA, HDCF%, HDGF, HDGA, HD SV%, rebound
goals, rebounds allowed, EA Specials, attempts off a pass, turnovers -> shot, zone entries carried / all and how many led to
an attempt; skater columns HD att, HD G, Shot ast, Reb G, EA Sp., Costly GV, Entries, Entry->shot). Summary VERSION 4.

Play context (2026-10-16, `add_play_context` in export_match.py, after add_shot_context; all other fields unchanged):
- `human` on hits, penalties (at the foul, `called`; else in the 3 s before the listing), shots and passes: the player
  carried the controlled-skater marker (`ctrl`) within 0.3 s. The person always has the puck carrier (the user; a
  very rare Genesis glitch aside), so shots and passes are the person's; checks and penalties are where the computer's
  skaters show (capture6 Boston: checks 23 person / 15 CPU). The user found tracking defender switches useless and
  penalties drawn not worth it.
- Shot `origin`: 'rush' (within RUSH_MS = 5 s of the team's zone entry, puck still in the zone), 'zone' (later in that
  stay: sustained pressure), 'faceoff' (no entry: off a faceoff in that zone, no whistle between), 'other'. About
  three quarters of attempts are off the rush in NHL '94.
- Zone entry `odd`: [attackers level with or ahead of the puck or up to 60 behind it, defenders back between the puck
  and their net] as the puck crosses the blue line; an odd-man rush is a carried or passed entry with more attackers
  than defenders and at least two (1-on-0 is a breakaway; a dump-in leaves the attackers behind). Boston had 25 in two
  games; the user finds about 12 a game plausible, the CPU defending so poorly (not reviewed rush by rush).
- Shot `wrap`: from within 45 of the middle near the goal line, the shooter having had the puck behind that goal line
  in the 1.5 s before (one goal in capture5).
- `m.habits[team]` for each team a person played (pad / pad2 with padTeam / pad2Team): minutes of live play, A / B / C
  presses (rising edges), bursts (C without the puck, $0C5E: speed burst and check lunge in one), checks landed by the
  controlled skater, poke checks and hooks with the takeaways they made, the goalie's dives and the time a person had
  the goalie (hooks not known on the SNES).
Shown: shot tooltips (rush / sustained / faceoff, wraparound); viewer team stats groups "How chances were made", "Person
vs computer" (checks, penalties, saves with a person / the CPU in net) and "Controller (whole game)"; season summaries
(VERSION 5: persHits, persPen, origin, oddMan, wrap, habits, humanPasses, pass `pairs` "passer>receiver": [passes with
a receiver, completed, shot attempts off them] - a picked-off pass has no known target - and `shotMap` per team:
[x, y turned to attack up, result letter, goalie faced, type, flags r rebound / e EA Special rebound / h high danger /
x wraparound]); the season page's "Play style" tab (how chances were made, person vs computer, controller habits, the
passing network of the picked team or My team) and, on the Goalies tab, "Where goalies get beaten" (every shot that
reached a goalie or a team's goalies on the half rink, goals in red, and goals and SV% by type, high danger, rebounds,
EA Specials, wraparounds).

## Layout and help (2026-10-16)

From a review of the pages at 1920x1080, 1366x768 and phone width (the user chose all four changes):
- Viewer side panels: `clamp(256px, 19vw, 340px)` wide, from the top; the team stats in collapsible groups (click a
  heading; `closedGroups`, remembered; Physical, How chances were made, Person vs computer and Controller start closed).
- Footer in three groups: playback (Play, seek, time, speed), the Map menu and its filters, then Game flow,
  Highlights, Clip, Save game file and "&#9881; View": a menu with the on/off switches (Game sprites, Event tags,
  Overhead rink, Follow the puck, Sound with its settings, Live knowledge), moved out of the footer and the on-ice
  toolbar (which keeps rotate, zoom and reset). Sound is a checkbox now (`showSound`).
- Phones and windows under 900 px: the rink on top (64vh), tabs Lineups / Team stats / Scoring under it (`showPane`,
  remembered, `&pane=` in the address) showing parts of the two lineup panels (CSS on main.m-*), the footer compact
  and stuck to the bottom. Headless Edge will not lay out narrower than about 490-500 px: screenshots at 412 are
  cropped, so check at 504.
- Phones, fixed 2026-10-17 (the user, on Android, could not find the stats): the rink (touch-action none) took every
  swipe, so the page could not be scrolled down to the tabs; it is now pan-y unless zoomed in (`applyView`). Tapping
  a tab scrolls it into view. Lineup rows open cards on `pointerenter` from a mouse only: a tap's emulated mouseenter
  opened the card and its click closed it again. A tap or click outside the card and rows closes it; #popover keeps
  to the screen (max-height, scrolls). Checked in headless Edge at 504 px with simulated taps, then by the user on
  an Android phone (game files from an S3 bucket): works. iPhone not reported yet.
- Two tabs (2026-10-18, the user: the view can feel cluttered): View menu "Stats in a second tab" opens this page again
  with `layout=stats` (body.layout-stats: no stage, game flow or footer; the lineup panels side by side; header note
  "Following the rink tab") and puts this tab in layout-rink (no side panels). The stats tab follows the rink tab's
  clock: draw() calls sendTime (postMessage to the stats window, 10 a second while playing, on any change otherwise),
  which works between game-file tabs from a folder too. The stats tab says hello to window.opener until it hears the
  time (so reloading either tab reconnects); a stats tab without its own match is sent the match object. "Stats back in
  this tab" sends 'bye' (the stats tab closes itself). `&layout=rink` / `&layout=stats` in the address. Checked in
  headless Edge: the rink layout, and the stats layout in a test page standing in for the rink tab (match handed over,
  time followed); not yet two real tabs.
- One bar on the games list and the season page (NHL '94 Viewer, Games, Season stats, Help); the viewer's scoreboard
  has "&larr; Games" (hidden in a shared game file) and "? Help". The games list shows each game's system and ROM name
  (from /api/season) and keeps recordings under a minute (save-state previews, tests) in a closed list below. The
  season page's filters stack on phones.
- Help (`#help` in viewer.html, so it is in game files too; `viewer.html#help` from the other pages, `showHelp`):
  getting started, watching a game, maps, highlights / clips / game files, season stats, a glossary of every stat,
  community terms (EA Special, pass shot) and troubleshooting, with a contents list and a search that keeps matching
  entries. Keep it in step with the features.

Time units (2026-10-16, the user's rule): every time in the stats is game-clock time except skating (distance, top
speed: real time, so mph are real-world) and the controller's rates (presses / bursts a minute of live play: real
time). export_match.py `clock_ticks(m)` is the one rule for game seconds (a new low of the clock in the period, at
most 3 at a time; a set clock or a blip back up is not play; the viewer's findPossession is the same) and
`game_weights(m)` gives each sample's game milliseconds (each tick shared over the samples it took, by real length;
a long wait before a tick only shares its last 1.25 typical game seconds; nothing while the clock is stopped; they add
up to exactly 900 s for a 15-minute game). Moved to game time: goalie control time (habits.goalieSeconds), heat maps
(viewer: `gameWeights`; season heat files HEAT_VERSION 2). Already game time: possession and its zones, with the
puck, carried by D / C / W, ice time, attack zone, penalties.
Attack-zone possession per goal (the user): a team's attacking-zone possession (game seconds) / its goals, and its
opponents' attacking-zone possession / its goals against; one game's numbers are the same seen from either side, a
season's tell offence from defence. season.py `possession_by_zone` (the viewer's possession rule, by zone in each
team's view; BOS-PIT matches the viewer to the second) gives the summaries' `possZones`, `possAtt`, `possAttAgainst`
(VERSION 12); season Team stats columns ATT POSS/GF and OPP POSS/GA; viewer Puck control "Attack-zone possession per
goal". BOS-PIT Boston 0:38 a goal; CHI-TOR Chicago 0:46, Toronto 0:43.

Stat explanations on hover (2026-10-16, the user asked): `STAT_HELP` in viewer.html explains every team-stat row and
player-card stat (what it is and how it is worked out); break-down rows are looked up under their parent
("Possession|· attacking zone"), card stats that share a team stat's name as "card|<label>". The label shows a
help cursor and a dotted underline on hover (`.has-help`). Checked: every row of both team-stat panels, all groups
open, has one. The season page's tables fall back to `HEAD_HELP` (by heading text) for columns without their own
title. Keep both in step when adding a stat.

## Three stars and highlights

The footer's "Highlights" button (`&highlights` opens it) shows the game's three stars and its highlights.
- Stars by a game score after the analysts' Game Score (Luszczyszyn), with what the recordings know: 0.75 a goal, 0.7
  a first assist, 0.55 a second, 0.075 a shot on goal, 0.05 a hit, 0.1 a takeaway (credited to `by`, as the card),
  -0.1 a giveaway, -0.15 a penalty, 0.05 per on-ice shot attempt for / against and 0.15 per on-ice goal for /
  against; goalies 0.2 a save, -0.5 a goal against, +1 for a shutout (the user's choices; Game Score has 0.1, -0.75, no bonus) (`gameScores`). capture6: Bourque (1 G 3 A, 17 hits, 11
  takeaways), Neely (3 G 1 A), Juneau.
- Highlights (`findHighlights`): each from 5 s before its key moment to 2 s after (the user's choice): every goal, up to 4 saves of danger 3 or more (distance
  under 45 / 75 / 110 from the net for 3 / 2 / 1, plus one each for a one-timer, a rebound, 18000 speed), posts,
  up to 4 big hits (upended first), breakaways that came to a shot but not a goal; overlapping stretches joined.
  Click one to watch it; "Play all" plays them in turn (checked by stepping the clock by hand in headless Edge: it
  jumps from each stretch's end to the next one's start); "Save as video" records them as one video in real time
  with the clip tool's frame (scoreboard strip, banner), like Clip's video, not run to the end in headless Edge.


**Harness facts and corrections (2026-10-25).**
- **The test goalie is Kelly Hrudey** (Los Angeles; retail Agility 3, Speed 3, Defensive Awareness 4, Puck Control 4)
  with the game's single hot / cold value at -2: working 13 / 13 / 18 / 18. A mid-pack retail starter, not a backup.
- **Record +$6B is `aidef`, not Defensive Awareness:** setplayer stores 15 - (DfA + bonus) / 4, 7-15 (collide94.asm);
  the computer goalie's reaction timer is aidef / 4 frames (checks94.asm). The SNES stores a goalie's as
  (30 - DfA) / 2 on its 0-15 scale (setplayer.asm, `.t1x`). `NHL94_GOALIE` wrote its third value there raw until
  2026-10-25, so the first goalie runs (10 / 20 / 30) also gave the goalie 2 / 5 / 7-frame reactions; now it converts.
- **Raising only the test goalie's Agility to 20** took the far-post slapshot from the middle (35 ft, top net, the
  shooter 4 / 4) from 58% to 3%, the best aim over the 18 slapcore spots from 19% to 9% (`rt_g1_agl20_slap`).
- **A skater put in place by writing his position has no body** until he moves under his own speed: the game finds
  player collisions through its y-sorted object list (OOlist / Ylist, collide94 `checkplcoll`), which it updates only
  as a player moves, so a placed skater with no speed stays where the list last had him and the others pass through
  him. `def_run.py` gives a held defender a creep of 1/64 unit a frame toward the shooter, and then he blocks.
- **A puck carried into the net counts as a goal**: deke_run counted any puck gone before the shot as lost; a fast
  skater (working Agility / Speed 30) carried it in at 78 of 120 such moments. Now counted (`carried`).
- **The Genesis test skater is left-handed** by the bit the game reads (attribute +$04 bit 3 clear; +$76 bit 0 set).
  ea_run's spots at +x are his right (his off-wing); the docs had called them his forehand side (question to the user).
- **CDL goalie edit** (`CDL_Season_12.bin` against `nhl94.bin`): 43 of 48 goalies have +1 Agility, Defensive
  Awareness and Puck Control (Joseph and Potvin already at 6 in DfA), Fuhr +1 Agility only, Roy and Belfour unchanged;
  stick and glove ratings unchanged. No goalie on either ROM has Speed above 4 (working 20).

## Season stats (stats across games)

`season.html` totals any set of games (2026-10-15). `tools/season.py` makes a small summary of each converted game,
`matches/<name>.summary.json` (a few KB; remade when the match file is newer or `VERSION` changes), and
`season.season()` gathers them all. The helper serves them at `/api/season` and rewrites `matches/season.js`
(`window.NHL94_SEASON`) after every conversion and delete, so the page also works opened from the folder
(`python tools/season.py` writes it by hand). The games page has a "Season stats" button.
- A summary: result, `overtime` (the clock ran in period index 3), `finished` (the index reached 4, or 3 with the
  score not tied), `fromStart` (period 0 at 0-0 at the first sample), game seconds, which teams people played
  (padTeam / pad2Team, else the joystick marker over half the game), `you` (padTeam: controller 1's team), team
  numbers (game counts from the last stat snapshot plus the event lists: attempts, faceoffs, penalties and minutes
  from the rule table, big hits, turnovers) and a line per player who played. Skaters: goals, assists and shots on
  goal from the game's per-player counts; plus/minus from who was on the ice at each goal (role and roster at the
  goal's frame; not PPG or penalty-shot goals, as the viewer's card); attempts, PPG / SHG from the goal kinds, the
  game-winning goal (the winner's goal that passed the loser's final total), PIM from the penalties, checks and hits
  taken from `hits`, takeaways / giveaways, ice time. Goalies: shots and goals against (the game's), and every shot
  that reached him split by `gctl` (a person or the computer in net at the release); the goalie with the most ice
  time gets the decision (W, L, OTL, T) and a shutout.
- Checked on the three whole games: Moog in 2026-10-14_1540_CGY-BOS faced 7 shots with a person in net (4 goals)
  and 6 with the computer (2), as the goalie report says; MacInnis's OT winner is the GWG; Boston 1-0-1 over the two
  Genesis games.
- The page: filters by ROM (the system and the sprite library's crc; defaults to the ROM of the most recent whole
  game, since a league season is played on one ROM), team, and whole games only (on by default: recordings that
  began late or stopped early, and save-state previews, are left out), "My team" and team; tabs Standings (with "Your
  team" on top: record, goals, home / away, last five), Skaters, Goalies (save % overall, with a person in net and with the computer), Team stats (a
  game), Head to head (a grid of records, or just the matchups past 12 teams) and Games (untick one to leave it out;
  Watch links). Every column sorts; `?tab=` and `?rom=` (a key or `all`) in the address. Players are matched across
  games by team abbreviation and name.
- Seasons (named): in the user's online leagues a player's season is one team on one ROM, and one ROM carries many
  seasons (every GENS Classic season is played on nhl94.bin, every SNES Classic one on NHL94_Classic). So a season is
  saved by name in `matches/seasons.json` (id, name, rom = the page's ROM key, team, start, optional end, the games
  unticked in it): its games are the ROM's from its start until its end or the same ROM's next season's start. The
  page's New season / Edit season form posts the whole list to `/api/seasons` (the helper only; opened from the folder
  the seasons are read-only, from season.js). `/api/season` also gives `romTeams`: every team of each ROM in roms/
  (read with the system's read_teams, keyed system:crc32 as the converter computes it), so a season can pick a team
  that has not played yet. Without a season ("No season: browse all games") the page filters by ROM and a "My team"
  kept per ROM in the browser's storage (until chosen, the one team that played every game is guessed and said so).
  The season's team is marked in every table. It doesn't go by controller 1 (the summary's `you`): on the Genesis player 1 is
  always Home and player 2 Away (the user), so an Away game is played on controller 2; on the SNES a screen before the
  game lets each player pick the side to control, and both may take the same team.
- Season heat maps (the page's "Heat maps" tab): `season.heat_file` writes `matches/heat/<name>.js` per game (a folder
  of its own so nothing listing match files takes them for games; remade when the match file is newer or
  HEAT_VERSION changes; deleted with the game; about 140 KB a game), made by `season()` for any game lacking one.
  Time in live play in tenths of a second on a 10-unit grid (26 x 60), each team turned to attack up; slices skate,
  att, def, pp, sh, puck for teams and skate, att, def, puck for players (keyed by roster index), stored sparse as
  (cells skipped, value) pairs. Its totals agree with the viewer's (capture6: Boston's power play 41.8 s, Bourque on
  the ice 7:43). The tab loads the files for the games in view as scripts (so it works from the folder too), adds
  them up for a team or one skater (matched by name), and draws them over the system's rink picture, blurred and
  scaled as the viewer does. `&team=BOS&player=<name>&heat=puck&situation=att|def|pp|sh` in the address.
- ROM names (2026-10-16, `tools/romnames.py`): the page shows a ROM by its file name in RetroArch (NHL94_Classic,
  SDL16, nhl94) instead of its checksum. RetroArch's content history (`content_history.lpl` in its folder, or where
  retroarch.cfg's content_history_path says; newest first) lists the files loaded. When the helper attaches it
  names the ROM loaded now: the newest history entry for that system's core whose file has the same checksum as the
  copy it made (`note_loaded`, into roms/names.json; it also keeps RetroArch's folder, from the process, in
  roms/retroarch.json). Other ROMs are named by scanning the folders of the history's files and RetroArch's
  ROMs/Genesis and ROMs/SNES for a file with the same key (cached in roms/names_scan.json; about 1 s the first
  time for the 110 ROMs here). Keys as the page's: genesis:crc32 of the file; snes:crc32 without the copier header,
  and of its first megabyte (the helper's copy of SDL15/16 is only that). `/api/season` gives `romNames`. A
  season's ROM is fixed once made (the edit form shows it locked; to play another ROM, a new season); its name,
  team and dates can change.
- Choosing games (2026-10-18, the user: a practice game among league games; stats for one set against one opponent):
  an Against filter (my team's opponents; only games between my team and that one; `?against=DAL`), unticked games
  remembered in this browser without a season too (localStorage nhl94.season.excluded; a season keeps its own), and
  Count all these / Count none on the Games tab. Checked on the Documents games: 6 games, 5 against Dallas.
- Sharing a season (2026-10-18, the user's league opponent, no helper): `tools/share_season.py "<out folder>" <name
  patterns>` copies the pages, rink files, the chosen match files, their sprites and sounds and roms/names*.json (no
  recordings, no ROMs) into a new folder, runs season.py there (NHL94_HOME = that folder: summaries, heat maps,
  season.js) and zips it. The source is NHL94_HOME or the project. Made "Documents/NHL94 League share" (.zip 18 MB) from
  the five BOS-DAL games; season.html and viewer.html?match= work opened from the folder in Edge without
  --allow-file-access-from-files (both fall back to script tags). The pages' Games links point at helper.html, which
  says the helper isn't running there. The tool prints the folder it read the games from: the user ran it in PowerShell,
  where `set NHL94_HOME=...` does nothing, and got the three test copies in the project's matches/ instead of the five
  Documents games. For the user, "Documents/Make league share.bat" (not in git) sets NHL94_HOME and runs it for the
  BOS-DAL games: double-click.
- Not there yet: people
  as such (a game knows teams and controllers, not who held them), a shareable season file.

## Live knowledge (preparing for a live view)

Some derived stats depend on what happens next, so a live view cannot settle them at once. The match file records
when each could first be known, and the footer's "Live knowledge" switch (or `&live`) makes the replay show only that,
as a live view would:
- Shots: `known` (the release; a pass shot only when it reached the net or the goalie; a shot found from a counted
  event, at that event) and `resolved` (when its result could be known: the game's count, a post, the goalie's stop,
  a block, the goal line). Until resolved it shows as "still in play" (dashed ring on the shot map). Results settle
  a median 0.2-0.3 s after the release, at most about 2 s.
- Failed one-timers: `known` when the swing is over with nothing hit (about 0.5-0.7 s after it starts). Until then the
  tag says "One-timer"; a pass shot's tag says "Pass" until it is known.
- Turnovers: known when the other team gains control (`f`).
- Possession: the seconds of the loose-puck stretch under way show as "undecided" until someone gets the puck or a
  whistle goes, then go to that team or Transition.
- Known at once: the game's own counts (shots on goal, goals, breakaways, penalties), hits, the hot-shot trail. A
  goal's scorer and assists come from the game's stats up to 2 s after.
For a live view the analysis in `export_match.py` (find_shots, find_turnovers, find_failed_one_timers) should run
incrementally over the stream (a reader in Python feeding the page), giving out each item when it is known and
again when it is resolved; these fields say what that must reproduce, and the replay with live knowledge on shows
what such a view will look like.

## Posts

There is no post counter in work RAM that was found (the game counts a post shot as a shot). The converter marks
a post when the loose puck turns back out of the end zone right beside a post: |X| 14-28, |Y| 252-272, moving
away from the goal line, at least 1500 speed units, at most one per second. Calibrated on Roenick's post shot at
2:57 of period 1 in `capture5_league30` (the user saw it), where the release and the bounce fall within one
sample. Across all captures it fires three times: that one, `capture5_league30` 4:47 of period 3, and
`capture3_bos_la` 2:32 of period 2; the last two are unconfirmed. Posts sit at about (+/-20, +/-265).

## SNES expected goals and xG map (2026-10-17)

`tools/xg_snes.py` (export_match calls it for SNES games with the ROM's bytes; snes.read_match now keeps `work`
[frame, object, weight $12C3, legstr $12E3, legspd $1303, aidef $1343, shotspd $1363, shotacc $1383]). Read from the
NHL94SNES disassembly: doshot (aim at y +/-$108 = 264, ApproxLength distances, perfect when d3 < 201 and randoma8(16 +
ShA) >= 15, scatter ((passspeed >> 3) - ShA + 16) x d3 >> 6, halved under 251, cap $88, Y halved shooting down, height
up only; velocity 2 x passspeed x 68 x d / d3, so passspeed = speed / 136; lift + (0xB33 x d3 / passspeed) / 2),
updateplayers (velstep d7 x 16, gravstep d7 x 96: pos += vel / 4096 a frame, gravity 96; friction table .21 0xFD /
0xFA / 0xF7 by timestep, mostly 2 frames a step: timestep 2 in 3458 of 4922 samples), checkgoal (front at y 259, goal
|x| <= 17 under 13, post to 22, no puck radius added), checkpuckcoll_ccx (body: goalie - puck within -11 .. 10 both
ways, any height; goalie stick / glove: GetHot / GetFrameHot from the sprite frame record (index frame - 1, bytes
+$12-$15: hot point and second point), circle of radius |x2 - x1| around the hot point, height band from TWO_THIRDS),
pucknorm (puckcross every 5 frames, like findpc), assgoalie (rethink every aidef >> 1 frames; target puck + vy/341 ...;
ellipse 26 x 20; crossing within 35 frames -> its x, under 19 -> save move from GoalieSaveList, speed halved; StopNA
halves a computer goalie's speed; save moves set pfalock, not pf2aip, so he keeps rethinking and skating through
them), playeracc (32 - weight / 8 + 1.5 x legstr + 8; dir
steps 6 / 4; vmax (20 + legspd) x 261), vtoa (diagonal when neither part is more than twice the other: VTOA_TABLE). The goalies' sprite flip bit $1000 was never set (so hot y is negated);
mirror never set for goalies. Checks: emulated goalie vs recorded at arrival median 0.8 units (100 computer-goalie
shots); geometry with the recorded goalie path: posts 17.6 / 18; final 175 shots: 40.1 xG / 32 goals (264 aim; 35.6
with 268, but log loss 0.27 vs 0.31), GOALIE_SPREAD 2 (0-6 tried). The map tables (ready and save frames, hot areas)
are the same in every NHL '94 SNES ROM in the ROM folder. Viewer: XG_SNES (JS port between "SNES xG model" comments,
checked against Python: largest difference 0.028 at 3,000 tries), XG_SNES_ROM, XG_SNES_GOALIE_STATES (cpu 93, person
30, onetimer 55; regenerate with `python tools/xg_snes.py <rom> matches/<snes games>.js`); the SNES map's one-timer is
a slapshot against the goalies of recorded one-timers. Docs: SNES_SHOOTING 4.7, 5.1-5.3; SNES_GUIDE 11.3.

## Expected goals and penalty-shot flags (2026-10-17)

xG map (2026-10-17, the user asked; Genesis now, SNES once modelled): viewer Map menu "xG map" with xgShot (wrist
13000 / slap 20000 / one-timer 20000, auto-aim, reach 12), xgAcc (Shot Accuracy step 0-6, working 5 x step) and
xgGoalie (cpu / set / person); &map=xg&xgshot=&xgacc=&xggoalie= in the address. The model is a JavaScript port of
tools/xg.py (XG in viewer.html, between "xG model" comments; keep the two in step: checked against Python on 12 spots x
9 aims, largest difference 0.009). Spots every 8 units, y 92-252 at both ends (the bottom end differs a little: doshot
halves the Y scatter shooting down), 120 tries per aim, best of the nine aims, a light 3 x 3 smoothing, drawn as one
small picture per end; worked out in 30 ms slices (about 1.2 s) and kept per setting. Map cells are hover-only hits
(f = -1: no click-to-replay). A set goalie made every spot nearly hopeless (wrist best 0.04), unlike real shots
(about 0.2): the recorded goalies at the release were a median 6.7 units off their set spot (0-3 units: 1 goal in 31,
10+: 22 in 59), so "as in games" draws each try's goalie offset and velocity from the recorded shots
(XG_GOALIE_STATES, 173 computer / 35 person; regenerate with `python tools/xg.py matches/<games>.js`).

The user asked for both. Penalty-shot flags: genesis.BLOCKS gained (0xC2E0, 0x110) and (0xD400, 0x60), so new
recordings keep gmode, BA_PS_flags ($C2F2) and the penalty shot's shooter / goalie / clock ($D406-$D454); View unpacks
blocks[:2]. Checked on capture3's penalty shot (full.bin): bit 3 at the award (206 s), bit 2 with shootoutclock 25
counting down (211 s), bit 5 at Oates' shot, all cleared after. The next "penalty shot ends at once" can be traced.
SNES penalty-shot words were already inside its block.
Expected goals (`tools/xg.py`, called by export_match after add_shot_aim; Genesis only): genesis.read_match now keeps
`work` [frame, record, weight, Agility, Speed, aidef, Shot Power, Shot Accuracy] whenever a record's working values
(+$67, $68, $69, $6B, $6C, $6D) change. Each shot / one-timer is played out 400 times (seeded by name, frame, team,
shooter, so re-conversions agree): aim from the recorded stick (human shooters) or shotdiradj's auto-aim (one-timers,
computer shooters; it agrees with the recorded passdir 69 of 88 times); doshot's perfect roll and scatter with the
recorded speed (passspeed = speed / 68) and working ShA; flight at v / 4096 units a frame (findpc confirms the scale),
lift cancelling gravity; checkgoal: goal when the centre crosses |x| <= 20 (16 + puck radius 5, less 1) below 13 at the
net's front (y 261); the goalie's body at reach (.cbg by Agility + 2, 15 person, 12 one-timer, 18 pad stack). The goalie
is emulated as the computer one (xg.Goalie: checkanim .nofo / .de5, findpc, playeracc, stopna; target the predicted
puck on a 26 x 18 ellipse, or the crossing x within 34 frames; save move and speed / 4 at 12 frames; re-aim every
aidef >> 2 frames): with the recorded puck it lands a median 1.1 units from the recorded goalie (120 shots), so it is
used for a person in net too (that fit better: log loss 0.311 against 0.321 standing still). GOALIE_SPREAD 4 (the only
fitted number; 2-7 tried). Without the goalie moving the model said 61 expected against 31 goals; with the recorded
goalie path 35.2. Final, all seven recordings: 191 unblocked shots, 39.4 xG / 34 goals (CPU 28.6 / 23, person 10.8 /
11), log loss 0.30 (0.46 for one rate). Extra stick reach for low pucks was tried (+2 matched the totals but worsened
the log loss) and left out. Viewer: shot tooltip "xG 0.34", card xG (skaters) / xG against and "Saved above exp."
(goalies), team stats Advanced "Expected goals (xG)", "· xG share", "· goals above xG" (with "(4/6)" when some goals,
deflections or pass shots, have no xG), STAT_HELP and Help. Season summaries VERSION 17: team `xg` [xGF, goals from
those shots, xGA, goals against from those], skater `xg` [xG, G], goalie `xga` [xGA, GA] (keys absent without xG);
season page Skaters xG and G-xG, Goalies xGA and GSAx, Advanced chances table xGF, xGA, xGF%, G-xG. season.html's team
summing now adds numbers only (a null had turned an array into a string). Documented in GENESIS_SHOOTING.md 4.9 and 5.3
(the goalie's movement) and GENESIS_GUIDE.md 12.3. Not yet: the SNES (its goalie is a different box).
