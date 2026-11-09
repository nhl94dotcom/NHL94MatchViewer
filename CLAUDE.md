# NHL '94 match viewer

Records NHL '94 (Sega Genesis and SNES) played in RetroArch by reading the emulator's memory, converts each game into a
match file, and replays it in a browser viewer with full stats, maps, clips, season stats and a live broadcast. Built
for the user's online league community (RetroArch 1.17, Genesis Plus GX and Snes9x cores).

**This file is the short brief. The full history and every finding (addresses, routines, checks, dates) is in
`docs/PROJECT_NOTES.md` (the technical reference), `docs/VIEWER_NOTES.md` (the viewer, stats and broadcast) and
`docs/STUDY_NOTES.md` (the studies' working notes): search them before re-deriving anything.** Other docs:

- Game mechanics: `GENESIS_GUIDE.md` / `SNES_GUIDE.md` (plain English), `GENESIS_MECHANICS.md` / `SNES_MECHANICS.md` (in
  detail; sections 4-5, shooting and goaltending, in `GENESIS_SHOOTING.md` / `SNES_SHOOTING.md`), `XG_MODELS.md` (the xG
  models' inputs, units and use outside the project).
- Studies: `SHOOTING_STUDY.md`; `LEAGUE_RESULTS.md` (the league result databases); the scoring maps, shots played in the
  real game (`SCORING_MAP.md` the overview, `SCORING_GENESIS.md`, `SCORING_GENESIS_DEKES.md`, `SCORING_GENESIS_EA.md`,
  `SCORING_SNES.md`); `FACEOFF_PLACEMENT.md` (where faceoffs are held and where the rules put them).
- Plans: `DEFENCE_PLAN.md` (the defence studies), `BOT_PLAN.md` (the scripted bot), `GAME_VARIABLES_PLAN.md`
  (the forum's "game variables": what's known, what to study). Open questions for the user:
  `NEEDS_FROM_YOU.md`.

## Rules (from the user)

- The repository is public (nhl94dotcom/NHL94MatchViewer, branch main). No personal details, no user-specific paths in
  committed files (use `Path.home()` / `%USERPROFILE%`). User-specific .bat files stay out of git.
- Never put credentials, the S3 bucket name or the AWS profile name in committed files.
- Only ever read the user's emulator's memory (our own headless core copies may be poked). Never kill the user's
  processes. Don't rebuild the exe while "NHL94 Helper.exe" is running (check with `tasklist | grep -i nhl94`).
- NOSE4Web (`C:\D\GenAI\NOSE_source_1.2b_wboy\nose-web`, the user's ROM editor) is read-only reference; where it and
  the disassemblies disagree, trust the disassemblies. Its test builds sit in `C:\D\GenAI\NOSE_source_1.2b_wboy` beside
  the original ROMs and may be run for testing (never change them; a scratch copy for a test is fine). NOSE4Web keeps
  `NHL94_known_bugs.md`: give findings, don't edit it.
- League rules: no point for an overtime loss; overtime is 10 minutes on the Genesis, 5 on the SNES.
- Commit and push when work is done; check `git status -sb` before mentioning unpushed commits (the user pushes too).
- Keep this file, the docs and `docs/NEEDS_FROM_YOU.md` up to date; add questions only the user can settle to the last.
- Durations in reports, write-ups and docs are game seconds (the game clock: 1 game second = 24 frames = 0.4 s of real
  time, both systems; `tools/gametime.py`). Windows keep their real length and are labelled in game seconds (5 s real =
  12.5 game s). Split-second timings (button presses, a pass's lead, air time, reactions) stay real seconds, marked (real).
- Long emulator runs and batch jobs in gentle mode (`analysis/scoring_map/lowload.py`: at most 2 workers at idle
  priority, each resting as long as it works; the user's fan).

## After changes

- Viewer / season page changed: copy `viewer.html` and `season.html` to `Documents\NHL94 Viewer`; upload the live page
  (live_broadcast `S3Target` + the index.html transform with `window.NHL94_LIVE = 'live.json'`; never `publish_page`,
  which resets the manifest); rebuild the exe (`cmd /c "tools\build_helper.bat < nul"`) if the helper isn't running;
  remake `samples/` (`share_game.make_game_file`) when the change is worth showing.
- Converter changed: `python tools/reconvert.py` re-converts the recordings in both game folders (only those that
  already have a match file: other capture folders are tests or pieces of merged games), gently, and rebuilds the
  season once in each. It reuses each recording's cached read (`captures/<name>/read_cache.json.gz`, keyed on the
  recording, the ROM and the code in `tools/systems/`), so after an analysis change a game takes about 2 s, not
  6-12 s; `--no-cache` reads everything again. A viewer-only change needs no re-convert. `python
  tests/check_matches.py` checks goals, shots on goal, checks and faceoffs against the game's own counts, and `python
  tests/check_season.py` that every summary is current, in season.js and agrees with its match file.
- Keep in step: viewer `STAT_HELP` / Help (`#help`) with every stat; season.html `HEAD_HELP`; season.py `VERSION` bump
  when summaries change; `tools/xg.py` with the viewer's XG port, `tools/xg_snes.py` with XG_SNES, `tools/deserve.py`
  with the viewer's `deserveToWin` (`python tests/xg_parity.py` compares all three).
- Check viewer changes by rendering in headless Edge
  (`msedge --headless=new --screenshot=out.png --window-size=W,H "file:///.../viewer.html?match=<name>&t=<s>"`;
  narrowest usable width about 504). `python tests/viewer_smoke.py` loads every match many ways and reports script
  errors; `python tests/viewer_stat_sums.py` checks that every team-stat break-down adds up to its row (each folder's
  own viewer.html: copy it to Documents first).
- Helper or a system's `View` changed: run a fake-emulator test (`tests/helper_*.py`).

## Where things are

- Two game folders: the project (`captures/`, `matches/`, used when `tools/nhl94_helper.py` runs on its own: tests)
  and `Documents\NHL94 Viewer` (the real games: the exe's home, and every launcher .bat sets `NHL94_HOME` to it, as
  any tool can). Recordings, matches, ROM copies, sprites, sounds and build output are git-ignored.
- `NHL94 Helper.bat` / `dist\NHL94 Helper.exe`: `tools/nhl94_helper.py` waits for RetroArch, records each game (live
  play only), converts it, serves http://localhost:9494/helper.html (games list, viewer, season page). Live broadcast:
  `--broadcast <channel> --bucket <bucket>` with `tools/live_broadcast.py` (user's launcher not in git).
  `tools\build_helper.bat nobroadcast` builds `dist\nobroadcast\` for people who won't broadcast (no `live_broadcast`,
  and the viewer's Help without "Watching live", between `<!-- broadcast` markers).
- `tools/export_match.py`: recording -> `matches/<name>.js` (`--live` worker mode for the broadcast). `analyse()` runs
  every finder after the system's `read_match` (shots, passes, turnovers, hits, check attempts, passing out of a
  check, entries, xG ...).
- `tools/systems/`: `genesis.py`, `snes.py` (memory layout, `View` for the helper, `MatchReader`, ROM readers, sprites,
  sounds), `snes_layout.py` (SA-1 / 2 MB builds), `genesis_settings.py` / `snes_settings.py` (league ROM settings and
  the NOSE4Web / NHL94SNESVault fixes and options: `romSettings`; the viewer and xG follow them), `common.py`,
  `process.py`.
- `viewer.html` (one page: rink, sprites, maps, team stats, cards, clips, highlights, game files, live mode, Help),
  `season.html` + `tools/season.py` (per-game summaries, `matches/season.js`), `helper.html`.
- `tools/`: `reconvert.py` (re-convert the library, above), `xg.py`, `xg_snes.py` (`make_xg_figures.py` draws
  XG_MODELS' figures), `deserve.py`, `share_game.py` (self-contained game files), `share_season.py`,
  `merge_recordings.py` (join a game the helper split), `make_diagrams.py` (docs/img SVGs), `romnames.py`,
  `extract_sprites.py`, `embed_rink.py`, `bench_mask.py`.
- `tests/`: fake-emulator tests of the helper (`helper_genesis.py`, `helper_snes.py`, `helper_live.py`,
  `helper_snes_penalty_shots.py`, `helper_snes_sa1.py` ...: a recording played back as if RetroArch were running it),
  and the checks under After changes. `samples/`: three game files for the README.
- Disassemblies (rebuild the ROMs byte for byte), cloned in `%USERPROFILE%\NHL94_disasm`; all change daily (names,
  comments), so `git pull` before reading and cite names from the current copy: Genesis github.com/abdulahmad/NHL94Genesis
  (`src/frames94.asm` animation names, `src/ram94.asm` RAM names), SNES github.com/abdulahmad/NHL94SNES
  (`src/ram94s.asm`; Mhopkinsinc's NHL94SNES is a stale fork), and the SA-1 / 2 MB builds' source
  github.com/Mhopkinsinc/NHL94SNES-SA1.

### analysis/ (each script documents itself at the top; reports go to the git-ignored `reports/`)

- Match and set reports: `match_report.py <match> ...` (a standard match report per game: chances and luck, hot / cold,
  goaltending, faceoff timing, C vs CB against the weight bug, pokes, rush defence, leading / trailing, slot defence
  from `slot_defence.py`, post luck, check attempts from `check_outcomes.py`, passing out of a check);
  `play_by_play.py <match>` (each goal's build-up, big saves, posts, hits, injuries, rushes, the flow by minute: the raw
  material for a written match story; check every detail of a story against it, never add colour it doesn't show);
  `set_report.py <TEAM> <TEAM> <match> ...` (both systems; its docstring lists the rules a write-up keeps) and
  `set_deep.py` (Genesis, deeper); `coach_report.py` (how the two people played, Genesis; league tables from
  `coach_models.py`) and `coach_predict.py`; `check_pass.py <match> ... | --all [ABBR]` (passing out of a check, both
  systems: the converter's `find_check_passes`); `assist_loss_study.py` (assists lost to a2touchpuck's same-player exit); `knockdown_study.py` (knockdowns, poke trips,
  holds and injuries per game, both systems). `reports/<set>_writeup.md` are the written analyses.
- Moment tools: `goal_trace.py <capture> <period> <m:ss>` (any moment frame by frame), `b_button_study.py`; the older
  BOS-NYI series scripts (`matchup_review.py`, `bos_nyi_*.py`, `person_play.py`, `person_defense.py`); shot / one-timer
  / passing / pickup / goalie studies; `bug_frequency.py` (how often NOSE4Web's fixed bugs happen in the recordings);
  `momentum_study.py` (shooting by shot order in the recorded games).
- League databases (every league game since 2013, both systems, real players' names, so never in the repo):
  `%USERPROFILE%\NHL94_League_Data\All_Games_GENS.csv`, `All_Games_SNES.csv`. Scripts print or commit aggregates only:
  `league_home_study.py`, `league_momentum.py`, `direction_by_level.py` ...; `coach_rating.py` (a strength per coach;
  its named table, `coach_guide.py`'s coach pages, `coach_history.py` and `coach_movers.py` go to that private folder
  only); handouts `classic_team_guide.py` (`docs/TEAM_GUIDE_*.md`), `classic_player_guide.py`
  (`docs/PLAYER_GUIDE_*.md`), `classic_draft_guide.py` (`docs/DRAFT_GUIDE_CLASSIC.md`); `coach_team_levels.py`;
  `league_ratings.py` (`docs/LEAGUE_RATINGS.md`; method `docs/COACH_RATING.md`). `classic_season_report.py LEAGUE COACH` (one coach's season against
  their league) and `classic_league_report.py PREFIX|LEAGUE [--coaches]` (every league of a season: standings, groups,
  leaders, head to head, notable games and a good word for every coach), both to that private folder. `python analysis/update_all.py`
  rebuilds them all in order and ends with `tests/check_league_outputs.py` (`--list`, `--from NAME`, `--tests`). A
  Classic league's name starts `Classic_Spring`, `Classic_Summer` or `Classic_Fall`; in a season, the league with the
  most As is the top one.
- `analysis/scoring_map/`: the game itself, headless (a libretro frontend over copies of the cores; work files in
  `%USERPROFILE%\NHL94_scoring_map`; `build.py`'s docstring is the how-to).
  - Scoring maps: a Genesis test ROM built from the disassembly with a doshot hook (GENESIS_SHOOTING 4.10); the SNES
    retail ROM with no hook (`snes_*.py`, SNES_SHOOTING 4.8); both take recorded goalie states for a goalie "as in
    games" (map_run.py's 7th argument, NHL94_SNES_GOALIES; NHL94_SMAP_SUBSET=coarse). `goal_types.py`,
    `goal_frames.py` / `goal_diagram.py`, `animate.py` (GIFs of makes and misses).
  - The bot: `bot.py` (a scripted Genesis player, the user's scoring moves), `bot_run.py` (whole games against the
    computer), `bot_situations.py` / `bot_scenario.py` / `bot_scen_report.py` (from recorded situations; BOT_PLAN),
    `bot_live.py` (controller 2 of the user's RetroArch by key presses while it has the focus; `test` and `play` only
    with the user there).
  - Replays with one thing changed: `check_pass_timing.py` / `snes_check_pass_timing.py` (the B timing),
    `check_pass_ratings.py` / `snes_check_pass_ratings.py` (one rating), `snes_period_cvc.py` (the SNES computer
    against itself by period; pad 1 moved with c1playernum, playerpad $19D4 and the person flag),
    `snes_60fps_cvc.py` (the SNES computer against itself, seeded, penalties set on; `--make-30` runs McMarkis's SA-1
    build at 30 frames a second), `snes_penalty_rolls.py` (each penalty roll counted through stubs) and
    `snes_fight_capture.py` (a 2 MB build's computer games, Fighting On, until a fight: a recording of it) and
    `snes_fight_rate.py` (fights a game with Fighting On / After Whistle, computer against computer).
  - NOSE4Web's builds and ROM edits (results in STUDY_NOTES):
    - Fixes: `fix_check.py ROM` (which tested fixes a build has by their bytes, any other changed bytes, and each
      fix's in-game test against the original) and the per-fix tests (`*_fix_test.py`, `*_test.py`);
      `gen_onetimer_assist_test.py` (the Genesis one-timer assist bug: a fix, built and played; `builds` lays
      NOSE4Web's builds over the test ROM).
    - Graphics: score-box logos (`snes_score_logo_check.py` / `gen_score_logo_check.py`: what the original leaves
      free; `snes_score_logo_build_check.py` / `gen_score_logo_build_check.py`: a logo build against its original;
      `gen_lc_box_check.py`: the line-change box), `snes_banner_check.py` (team-block colours on every block screen),
      `snes_logo_overlap.py` (which piece of a big logo is in front), `gen_injury_check.py` / `gen_blood_check.py`
      (Genesis injuries forced in a scratch copy; the head blood builds).
    - Lines and options: `gen_line_dup_check.py` / `snes_line_dup_check.py` (the same skater twice on one line),
      `gen_line_editor_cursor.py` (the Genesis line editor's reachable slots), `gen_1on1_edit_lines.py` (Edit Lines and
      Team Roster on a ROM dressing fewer skaters), `gen_energy_shifts.py` / `snes_energy_shifts.py` (energy over shifts with line changes on), `gen_injury_baseline.py` / `snes_injury_baseline.py` (injuries, knockdowns, holds and tiredness a game, the computer against itself, line changes on), `gen_hit_energy_check.py` / `snes_hit_energy_check.py` (the hit energy option against the unchanged game, trial by trial; `--natural` the SNES computer's own knockdowns), `gen_net_colour_check.py` (sprite edits compared from one shared play state, in play and the replay), `gen_setup_screen.py` (the Game Setup screen's video memory, colours and how much background shows), `gen_ot_check.py` (period lengths in the menu and overtime lengths, played; `snes_ot_check.py` the SNES's), `gen_looks_check.py` (intro waits, puck friction, puck and fan colours), `snes_credits_check.py` (the SNES title credits: a screenshot at each rest, the roll's end), `gen_songs_check.py` / `snes_songs_check.py` (organ songs by home
      team and slot), `gen_leadsong_check.py` (the power-play songs after a real penalty), `gen_pad34_goalie.py`
      (pads 3 and 4 through EA's 4-Way Play: `emu.Emu(fourway=True)`), `gen_assist_repro.py` / `snes_regain_assist_test.py` (the
      lost-assist bug reproduced, and its fix), `snes_vault_hacks_test.py` (the
      NHL94SNESVault hacks: Edit Lines lists, max boost display, L+R goalie pull, the computer's pull),
      `a130f1_test.py` (Genesis save memory switching on big ROMs).
    - `menu_shots.py ROM OUT SCRIPT`: screenshots of the game's own screens from power-on by a script of presses, for
      edits outside play (photos, logos). Genesis Plus GX's video memory is read from its saved state (VRAM_AT in
      gen_score_logo_check.py, little-endian words); Snes9x's from memory id 3.

## How it reads the games

- Genesis: `ReadProcessMemory` on retroarch.exe; work RAM found through Genesis Plus GX's 68000 memory map (entries
  $E0-$FF sharing one base, cartridge header `ESAG`). Words read little-endian; a byte at address A is at A XOR 1.
- SNES: Snes9x's memory map (one pointer per 4 KB); work RAM bank $7E, cartridge at bank $80 + $8000.
  SA-1 / 2 MB builds: low RAM in BW-RAM, laid back over work RAM by `snes.Emulator.read`; ROM tables and animation
  words found by `tools/systems/snes_layout.py` (match files keep the retail words); no SNES xG on SA-1 games yet (60
  frames a second). docs/PROJECT_NOTES.md "SNES SA-1 and 2 MB builds".
- Sampled about 60 times a second on our own clock (not frame-locked). Netplay rollback samples are dropped by the
  frame counter (Genesis $B03E, SNES $0764). Pauses / instant replays are left out (Genesis screen $FFF7 = 0 is play;
  SNES sflags $15D8). Intermission highlights of other games (Genesis) are left out by team ids.

## Genesis memory (work RAM $FFxxxx)

Object records $80 bytes from $B04A: 0-5 Home, 6-11 Away, 12/13 nets, 14 puck, 15 puck shadow / goal light.

| Offset | Field |
|---|---|
| +$00 / +$14 / +$18 | X, Y, Z now (the match file reads +$1C / +$20 / +$24, the previous frame's, 16.16) |
| +$06 | Sprite frame (ROM frame table $9E724; tiles $5DE84) |
| +$28 / +$2A / +$2C | X / Y / Z speed (a puck at 23,000 is about 78 mph; position moves speed / 4096 a frame) |
| +$35 | Position 0 G, 1 LD, 2 RD, 3 LW, 4 C, 5 RW, $FF off |
| +$55 | Facing 0-7 (0 = up the screen) |
| +$58 | Animation word (names in the Genesis disassembly's frames94.asm) |
| +$5E | No-touch timer |
| +$60 / +$61 | Puck: $00 carried / $FF loose; last carrier's record |
| +$62 | pflags: bit 0 deceleration off, bit 3 controlled by a person, bit 5 locked in an animation |
| +$66 | Roster index |
| +$67-$75 | Working ratings (weight, Agl, Spd, OfA, DfA, ShP, ShA, Pas, ..., Chk) |
| +$76 | Bit 0 shoots left (clear: drawn mirrored) |

Globals: period $C466 (0-based), clock $C468 (seconds left; 2.5 x real time), score $C6DA / $CA3E, shots $C6CE / $CA32,
team ids $C6F7 / $CA5B, controllers $BEEF / $BEF1, cont1team / cont2team $C328 / $C32A, aim direction $BEDC, camera
$BD18 / $BD1C, scoring summary $C472, penalty summary $C5DC, crowd $B8A2, screen $FFF7. Team stat blocks $C6CE (Home) /
$CA32 (Away), $364 bytes (offsets in docs/PROJECT_NOTES.md "Team and player stats"). Stick hot points: HotList ROM
$A44C8 (x, y bytes per frame; x negated when mirrored, y negated). Home attacks up in periods 1 and 3.

## SNES memory (bank $7E)

Objects as 16-word arrays (index = object x 2): Xpos $0D55, Ypos $0DB7, frame $0D97, attribute $0E03 (bit $0800
mirrored), position $0F43, facing $1163, SPA $11A3, pflags $1283 (bit $0008 person), pnum $12A3, pfteam $1503, nopuck
$1203; working ratings $12C3-$1483. Puck carrier $0AE7 / puckc $0AD9, puckz $0DF9, period $1630, clock $1632, clock
stopped $15D6, sflags $15D8 (bit 0 paused, $0800 replay), controllers $0776 / $0778, scoring summary $313A, penalties
$15DE / box state $1852, hot / cold table $1A12, pause menu item psitem $0D15. Team stats are home / away word pairs
($178E goals ...; table in docs/PROJECT_NOTES.md "SNES version").

## The match file (what the viewer reads)

Per sample: `t`, `period`, `clock`, `score`, `shots`, `puck` (x, y, z), `puckV`, `owner`, `ctrl` (bitmask of
person-controlled records), and per record `pos`, `role`, `roster`, `anim`, `frame`, `mirror`, `facing`; `stats`
snapshots (STAT_FIELDS order); rosters, palettes, `romSettings`, sprite library id (`rom`). Event lists from the
analysis: `goals`, `shotList` (kind shot / one-timer / pass shot / other, result, counted, xg, aim, danger, origin,
gctl, gOff (the goalie off the shot line) ...), `passes`, `turnovers`, `hits`, `checkAttempts`, `checkPasses`
(passing out of a check), `zoneEntries`, `faceoffs`, `penalties`, `bumps`, `bobbles`, `netsOff`, `runaways`, `habits`,
SNES `flips` (the Y dump-in, kept apart from the passes), SNES `fights` and on 2 MB builds `gameStats` (both shown
by the viewer: a Fight banner and highlight, a Fights section, the game's own counts, Fighting on the card) (the game's own
posts, checks for / against, ice time) and more (each documented where it is made in
export_match.py).

## Notable findings to know

- Ratings in play: Genesis uses one hot / cold value (byte 0) for all ratings; SNES maxes every "cold" rating (sign
  bug). Hidden home / away, power-play and (backwards) third-period bonuses.
- Saves are geometry (Genesis body circle 12-15, 18 pad stack; SNES body box plus save-frame areas); shots within 200
  can go exactly where aimed, otherwise scatter upward only; one-timers are auto-aimed on the Genesis.
- Genesis bugs and quirks the viewer counts ("Quirky Events", each left out on a ROM with its fix): through-the-legs
  (the stick's blind ring), the top net's shoulder-save bobble, rocket passes (meeting time rounded down), runaway
  speed (deceleration-off left on); the weight bug in checking; the CB check.
- B without the puck (Genesis): on release, the skater nearest the puck's spot 16 frames ahead is chosen; the one you
  control pokes, else control switches (locked: switches at once). SNES: on the press, by distance plus goal-side.
- No momentum in the ROM: shooting early in a game doesn't carry on (LEAGUE_RESULTS "Momentum").

## Known gaps

- Settled, don't redo: SNES faceoffs (timing, SNES_MECHANICS 9), SNES pass speed (by distance, no rocket pass), SNES
  hooks / holds / pokes (7.3), upends (7.2), goalie poke / dive (5.3), puck physics (7.8), the crowd (both systems).
- Open: the open-questions sections of both mechanics docs; some studies need more games; no SNES xG on SA-1 games.
