# NHL '94 match viewer

Records NHL '94 (Sega Genesis and SNES) played in RetroArch by reading the emulator's memory, converts each game into a
match file, and replays it in a browser viewer with full stats, maps, clips, season stats and a live broadcast. Built
for the user's online league community (RetroArch 1.17, Genesis Plus GX and Snes9x cores).

**This file is the short brief. The full history and every finding (addresses, routines, checks, dates) is in
`docs/PROJECT_NOTES.md`: search it before re-deriving anything.** Game mechanics in plain English and in detail are in
`docs/GENESIS_GUIDE.md`, `docs/SNES_GUIDE.md`, `docs/GENESIS_MECHANICS.md`, `docs/SNES_MECHANICS.md`; studies in
`docs/SHOOTING_STUDY.md`; open questions for the user in `docs/NEEDS_FROM_YOU.md`.

## Rules (from the user)

- The repository is public (nhl94dotcom/NHL94MatchViewer, branch main). No personal details, no user-specific paths in
  committed files (use `Path.home()` / `%USERPROFILE%`). User-specific .bat files stay out of git.
- Never put credentials, the S3 bucket name or the AWS profile name in committed files.
- Only ever read emulator memory. Never kill the user's processes. Don't rebuild the exe while "NHL94 Helper.exe" is
  running (check with `tasklist | grep -i nhl94`).
- NOSE4Web (`C:\D\GenAI\NOSE_source_1.2b_wboy\nose-web`, the user's ROM editor) is read-only reference. Where it and
  the disassemblies disagree, trust the disassemblies.
- League rules: no point for an overtime loss; overtime is 10 minutes on the Genesis, 5 on the SNES.
- The user pushes to GitHub themselves; check `git status -sb` before mentioning unpushed commits.
- Keep this file, the docs and `docs/NEEDS_FROM_YOU.md` up to date; add questions only the user can settle to the last.

## After changes

- Viewer / season page changed: copy `viewer.html` and `season.html` to `Documents\NHL94 Viewer`; upload the live page
  (live_broadcast `S3Target` + the index.html transform with `window.NHL94_LIVE = 'live.json'`; never `publish_page`,
  which resets the manifest); rebuild the exe (`cmd /c "tools\build_helper.bat < nul"`) if the helper isn't running.
- Converter changed: re-convert the recordings in both game folders (below) and run `tools/season.py` in each; check
  that shots on goal, goals, checks still equal the game's own counts.
- Keep in step: viewer `STAT_HELP` / Help (`#help`) with every stat; season.html `HEAD_HELP`; season.py `VERSION` bump
  when summaries change; `tools/xg.py` with the viewer's XG port, `tools/xg_snes.py` with XG_SNES, `tools/deserve.py`
  with the viewer's `deserveToWin`.
- Check viewer changes by rendering in headless Edge
  (`msedge --headless=new --screenshot=out.png --window-size=W,H "file:///.../viewer.html?match=<name>&t=<s>"`;
  narrowest usable width about 504).

## Where things are

- Two game folders: the project (`captures/`, `matches/`, used when the helper runs from Python) and
  `Documents\NHL94 Viewer` (the exe's home; `NHL94_HOME` selects it for any tool). Recordings, matches, ROM copies,
  sprites, sounds and build output are git-ignored.
- `NHL94 Helper.bat` / `dist\NHL94 Helper.exe`: `tools/nhl94_helper.py` waits for RetroArch, records each game (live
  play only), converts it, serves http://localhost:9494/helper.html (games list, viewer, season page). Live broadcast:
  `--broadcast <channel> --bucket <bucket>` with `tools/live_broadcast.py` (user's launcher not in git).
- `tools/export_match.py`: recording -> `matches/<name>.js` (`--live` worker mode for the broadcast). `analyse()` runs
  every finder after the system's `read_match` (shots, passes, turnovers, hits, entries, xG ...).
- `tools/systems/`: `genesis.py`, `snes.py` (memory layout, `View` for the helper, `MatchReader`, ROM readers,
  sprites, sounds), `genesis_settings.py` (league ROM settings), `common.py`, `process.py`.
- `viewer.html` (one page: rink, sprites, maps, team stats, cards, clips, highlights, game files, live mode, Help),
  `season.html` + `tools/season.py` (per-game summaries, `matches/season.js`), `helper.html`.
- `tools/`: `xg.py`, `xg_snes.py`, `deserve.py`, `share_game.py` (self-contained game files), `share_season.py`,
  `merge_recordings.py` (join a game the helper split), `make_diagrams.py` (docs/img SVGs), `romnames.py`,
  `extract_sprites.py`, `embed_rink.py`, `bench_mask.py`.
- `analysis/`: one-off studies (each documents itself at the top): shot / one-timer / passing / pickup / goalie studies,
  `goal_trace.py <capture> <period> <m:ss>` (any moment frame by frame), `b_button_study.py`, the BOS-NYI series
  scripts (`matchup_review.py`, `bos_nyi_*.py`, `person_play.py`, `person_defense.py`), and `match_report.py <match> ...`
  (a standard Genesis match report per game into `reports/<match>.md`, git-ignored: chances and luck, hot / cold,
  goaltending, faceoff timing, C vs CB checking against the weight bug, pokes, rush defence, leading / trailing).
- `tests/`: fake-emulator tests of the helper (`helper_genesis.py`, `helper_snes.py`, `helper_live.py`,
  `helper_snes_penalty_shots.py` ...): a recording played back as if RetroArch were running it; run one after changing
  the helper or a system's `View`.
- `samples/`: three game files for the README (remake with `share_game.make_game_file` after viewer changes worth
  showing).
- Disassemblies (rebuild the ROMs byte for byte): Genesis github.com/abdulahmad/NHL94Genesis (`src/frames94.asm`
  animation names, `src/ram94.asm` RAM names), SNES github.com/abdulahmad/NHL94SNES (`src/ram94s.asm`; the Mhopkinsinc
  repo is a stale fork). Both change daily (names, comments): clones in `%USERPROFILE%\NHL94_disasm`; `git pull` both
  before reading, and cite names from the current copy.

## How it reads the games

- Genesis: `ReadProcessMemory` on retroarch.exe; work RAM found through Genesis Plus GX's 68000 memory map (entries
  $E0-$FF sharing one base, cartridge header `ESAG`). Words read little-endian; a byte at address A is at A XOR 1.
- SNES: Snes9x's memory map (one pointer per 4 KB); work RAM bank $7E, cartridge at bank $80 + $8000.
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
$15DE / box state $1852, hot / cold table $1A12. Team stats are home / away word pairs ($178E goals ...; table in
docs/PROJECT_NOTES.md "SNES version").

## The match file (what the viewer reads)

Per sample: `t`, `period`, `clock`, `score`, `shots`, `puck` (x, y, z), `puckV`, `owner`, `ctrl` (bitmask of
person-controlled records), and per record `pos`, `role`, `roster`, `anim`, `frame`, `mirror`, `facing`; `stats`
snapshots (STAT_FIELDS order); rosters, palettes, ROM settings, sprite library id (`rom`). Event lists from the
analysis: `goals`, `shotList` (kind shot / one-timer / pass shot / other, result, counted, xg, aim, danger, origin,
gctl ...), `passes`, `turnovers`, `hits`, `zoneEntries`, `faceoffs`, `penalties`, `bumps`, `bobbles`, `netsOff`,
`runaways`, `habits` and more (each documented where it is made in export_match.py).

## Notable findings to know

- Ratings in play: Genesis uses one hot / cold value (byte 0) for all ratings; SNES maxes every "cold" rating (sign
  bug). Hidden home / away, power-play and (backwards) third-period bonuses.
- Saves are geometry (Genesis body circle 12-15, 18 pad stack; SNES body box plus save-frame areas); shots within 200
  can go exactly where aimed, otherwise scatter upward only; one-timers are auto-aimed on the Genesis.
- Genesis bugs and quirks the viewer counts ("Quirky Events"): through-the-legs (the stick's blind ring), the top
  net's shoulder-save bobble, rocket passes (meeting time rounded down), runaway speed (deceleration-off left on); the
  weight bug in checking; the CB check.
- B without the puck (Genesis): on release, the skater nearest the puck's spot 16 frames ahead is chosen; the one you
  control pokes, else control switches (locked: switches at once). SNES: on the press, by distance plus goal-side.

## Known gaps

- SNES: hook animation's effect, flip in recordings, pass-speed and faceoff timing details; some studies need more
  games. `2026-10-19_2115_LA-BUF`'s recording is cut off (gzip without its end) and won't convert.
