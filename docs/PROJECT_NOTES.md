# NHL '94 match viewer: full project notes

The complete research and development log, moved out of CLAUDE.md on 2026-10-21 (CLAUDE.md is now a short brief).
Newest sections were added near the end of each chapter; search it for an address, routine, feature or date.

Goal: capture live game state from NHL '94 (Sega Genesis) running in RetroArch, and replay matches in a viewer
(full-ice top-down first; rotatable views later). A first top-down viewer exists and plays recorded captures;
there is no live view yet.

Split on 2026-10-26: the viewer, stats and broadcast features are in [VIEWER_NOTES.md](VIEWER_NOTES.md); the studies' working notes (game mechanics from the disassemblies, the scoring map's run notes, the user's games) in [STUDY_NOTES.md](STUDY_NOTES.md). This file keeps the technical reference: workflow, memory, sprites, ROM data, stats blocks, the SNES version, files and open questions.

## Workflow

The easy way: double-click `NHL94 Helper.bat` (runs `python tools/nhl94_helper.py` with `NHL94_HOME` set to
`Documents\NHL94 Viewer`, the exe's folder, and copies the pages and rink pictures there; until 2026-10-23 it used the
project folder, and the day's three BOS-LA games had to be copied across) and leave its window open while
playing. It waits for RetroArch with NHL '94, records each game from the opening faceoff to the final horn (live play
only: $FFF7 = 0; pauses and instant replays are left out, timeline included), converts it as
`<date>_<time>_<HOME>-<AWAY>`, and lists games at http://localhost:9494/helper.html (bound to this computer only;
it also serves the viewer, so the browser's local-file restrictions do not apply there): Watch, Make game file /
Game file, Delete, and tick boxes with "Export N games to ZIP" (2026-10-27: `/api/game-set` runs
`share_season.make_share` into `shared/NHL94 <matchups> <dates>` and its zip; the packaged helper makes the share's
season data by running itself with `--season`; this replaced the old "game file after every game" setting). Recordings are gzipped (`fast.bin.gz`, about 23 KB per second of play; `full.bin.gz`, all of RAM every 10 s for research only - the converter does not use it: converting the CGY-BOS game without it gives an identical match; about 16 MB a game in all) and the ROM is copied
out of the emulator into `roms/<fingerprint>.bin` for the converter, so no ROM folder is needed. The list is
`matches/games.json`. Tested offline by feeding it `captures/explore1_menus` through a fake emulator (with a made-up
final horn): it waited through the menus, started at the faceoff, marked the pause and replay, stopped 3 s after the
horn, converted; not yet tested on a live game. Python modules: `tools/nhl94_memory.py` (reads the emulator, like the
PowerShell recorders), `tools/share_game.py` (the shareable file; also `python tools/share_game.py <match>`).
The helper also writes what its window shows to `helper_log.txt` (appended per start, restarted past 2 MB), for
testers to send back. The project is a git repository (branch main; recordings, matches, ROMs, sprites, build output
and `rink_gens.js` are ignored, see `.gitignore`; `README.md` is the public summary).
For league members without Python: `dist\NHL94 Helper.exe` (about 15 MB; build it with `tools\build_helper.bat`,
which needs PyInstaller; it also makes `dist\NHL94 Helper.zip`, the exe plus `tools/tester_readme.txt` as
"Read me first.txt", the package to hand out). It is the same helper with the converter, sprite extractor and viewer inside; it keeps
games in Documents\NHL94 Viewer (`NHL94_HOME` overrides; the pages bundled in it are copied there on each start)
and converts in-process. Tested: `"NHL94 Helper.exe" --convert <folder>` converted the CGY-BOS recording in 8 s in a
fresh folder (ROM copy found, sprites built), and its page served the list, viewer, match and sprites. `NHL94_PORT`
sets another port. Closing the helper's window (2026-10-18): Windows 11 opens console programs in Windows Terminal,
and closing that tab took the console away without stopping the program, so both processes of the onefile exe
(PyInstaller's launcher and the helper) stayed running and blocked rebuilding the exe (the user ended them in Task
Manager). `exit_with_console` checks every 2 s; GetConsoleProcessList returns 0 once the console is gone (probed by
killing a test's conhost), and the helper calls os._exit, the launcher following. Checked: both gone within 5 s of the
console host ending, where before they stayed. The helper claims its port exclusively (Windows otherwise let a second helper listen on 9494 too,
and the page reached either), so a second copy says it is already running. It listens on ::1 as well as 127.0.0.1: Windows resolves
"localhost" to ::1 first, and with only 127.0.0.1 open each request waited about 2 s for the fallback, and the user
often could not connect at all. Security (review 2026-10-16): the helper answers only requests whose Host header names
it (localhost / 127.0.0.1 / [::1] with its port; anything else 403, which stops "DNS rebinding" websites from reading the
games or the ROM copies), and a POST must carry `X-NHL94: 1` (a header other websites cannot send without a CORS
preflight the helper never grants) and, when the browser gives one, the helper's own Origin; bodies over 5 MB, bad JSON
and a seasons request without a list are refused (so a malformed request never clears the seasons). The pages' POSTs
send the header. Not yet tried on another computer; an
unsigned .exe that reads another program's memory may draw a SmartScreen or antivirus warning.

By hand:

1. Record: with a game running in RetroArch, `Invoke-Expression (Get-Content -Raw tools\nhl94_record.ps1)`
   (4 minutes by default, into a new folder under `captures`).
2. Convert: `python tools/export_match.py captures/<folder>` writes `matches/<folder>.js`. Names, ratings,
   colours, the centre-ice logo and the player sprites all come from the ROM that was played. The recorder stores
   a fingerprint of that ROM in `capture.json` (CRC-32 of its first and second megabytes) and the converter looks
   for the matching `.bin` beside the default ROM; captures without a fingerprint are assumed to be `nhl94.bin`.
   `--rom` overrides; `--home` / `--away` override the team names. Confirmed working on `capture5_league30`.
3. Watch: open `viewer.html` and choose or drop the match file, or open `viewer.html?match=<folder>` directly
   (`&t=<seconds>` starts at that point). Space plays/pauses; arrow keys step 1 s (5 s with Shift).
   The view can turn to any angle and zoom (toolbar at the stage's bottom right; R / Shift+R turn 90 degrees,
   Shift+wheel 5 degrees, wheel zooms about the pointer, drag pans, F follows the puck loosely: a TV-style camera that holds still while the puck stays in the middle half of the
   screen and otherwise moves on a critically damped spring (smooth starts and stops); on rushes it eases the puck
   toward the trailing side so the net shows early. The camera never shows past the rink picture's edges (at any zoom or
   angle; when following, it slows to a stop at an edge, so deep in a zone the whole zone stays in view), except that
   the puck itself is always kept on screen. Settings and how they were tuned are in `FOLLOW` in viewer.html.
   The user found a tight follow nauseating, a slow one late on rushes, and an aggressive one jerky, 0 or double-click resets;
   `&rot=<deg>&zoom=<n>&follow` in the address). The rink turns as a picture; sprites, numbers and tags stay
   upright, and each sprite is swapped for the same moment of its animation facing the turned way (nearest 45
   degrees), using the ROM's animation table (see Game sprites). The picture's TV-shaped pixels (18% wider than tall)
   keep their stretch across the screen when turned: game X is drawn (ux/uy)^cos(2 x angle) times as wide as game Y,
   so 0 and 180 degrees are as before, 90 and 270 swap the stretch onto the rink's length, 45 is square.
   The picture is drawn as seen from below the screen (glass leaning over the ice at the bottom end). Past 90 degrees
   either way it is drawn mirrored top to bottom about the red line (row 777; goal lines and boards are symmetric
   about it), with the bench strip and the penalty-box strip (`RINK_SIDES`) pasted back unmirrored, so the near end
   always leans in. At exactly 90 / 270 the end walls still show the picture's top-down perspective sideways.
   That flip only applies to the original picture. The toolbar's "Event tags" (remembered; `&tags=0` turns it
   off) shows or hides the pop-ups for what happens on the ice - players' actions (pass, shot, poke check, failed
   one-timer ...), breakaways, posts - while the player labels (34 LD) stay. By default (toolbar "Overhead", remembered) the viewer instead
   draws `buildOverheadRink`: the picture rebuilt at load on a canvas as if seen from straight above. It keeps the
   picture's ice inside an outline 6 units in from the side boards and 13 from the end boards (outside that, the
   picture has its old kick line, glass posts and curved boards), the side stands, benches and penalty boxes. The
   bottom end's ice (under the leaning glass and the tilted net) is the top end mirrored about the red line with the
   top net patched out. Boards (ice edge X = +/-132, Y = +/-303, corner radius 46), glass, a walkway and both nets
   (posts at X = +/-20, 15 deep) are drawn flat; the side margins are a clean ice column stretched sideways (so the
   blue and red lines reach the boards), ends and corners plain ice (#7ee2f5, sampled), goal lines drawn across;
   the end stands are crowd tiled from the picture's top stands. Angle, zoom and follow are remembered in localStorage.
4. Clips: the footer's "Clip" button saves a stretch of the replay (pick a goal for 7 s before to 3 s after, or set
   the times) as a video or an animated GIF, at normal or half speed, small/medium/large. The frames are the ice
   canvas as shown (angle, zoom, follow, sprites, map) under a scoreboard strip, with the banner drawn in. Video is
   recorded in real time as the clip plays (MediaRecorder: MP4 in current Edge, else WebM); GIFs are drawn frame by
   frame (20 a second) and encoded in the page (median-cut palette of 255 colours, LZW), with the follow camera fed
   a steady clock. Clips are cropped to the rink (boards and a little of the stands, as placed on screen at the clip's
   start; the whole canvas when zoomed in), sized by the rink's longer side (Small 480, Medium 720, Large 1080), and
   enlarged without smoothing so the sprites stay sharp. After the first, each GIF frame holds only the box around
   what changed, with unchanged pixels see-through (index 255): the 3.5 s Jeff Brown clip went from 3.9 MB (whole
   stage, 14 fps, every frame whole) to 0.8 MB Small and 1.2 MB Medium at 20 fps. A zoomed, following camera changes
   every pixel, so such GIFs stay big (4.5 MB Small); video suits those. Saving needs `rink_gens.js` (`python tools/embed_rink.py`): the rink picture as a data URL, because a
   canvas that has drawn a picture loaded from a local file cannot be read back or recorded. The GIFs decode correctly (checked by decoding and stacking the frames); the video
   path starts cleanly in headless Edge (MP4 supported) but could not be run to the end there (no animation frames).
Samples (2026-10-16): `samples/` in the repository holds three game files made with `share_game.make_game_file` (the
user chose to include the ROMs' sprites and sounds): Genesis_Calgary_6-5_Boston_OT (2026-10-14_1540_CGY-BOS),
Genesis_Boston_6-3_St_Louis_netplay (capture6_netplay_bos_stl), SNES_Toronto_1-5_Pittsburgh (snes_2026-10-15_1755);
about 5 MB each. They embed the viewer as it was when made, so remake them (same names) after viewer changes worth
showing. The README's "Try it" section points to them.

5. Save game file (footer): writes one self-contained page to send to someone - this page's own source (kept as
   `PAGE_SOURCE` when it loads) with the rink picture, the bench masks, and the match and sprite library gzipped and
   base64'd inside (`window.NHL94_PACKED`, unpacked with DecompressionStream on opening). `capture6_netplay_bos_stl`
   makes a 5.2 MB file that opens on its own from any folder with everything working (sprites, overhead rink, maps,
   stats, clips).
   On an iPhone (2026-10-17, the user's opponent): a game file opened from Messages, Mail or Files is shown as a
   Quick Look preview, which draws the page without running scripts, so it showed the empty "Open a match file".
   Game files now carry a style line (PACKED_NOTE_STYLE in viewer.html, the same line in share_game.py) that swaps
   the drop panel's text for a `.packed-note` saying what happened and what to do (open on a computer, or a web
   link); the scripts hide it again when they run. A small script before the main one reports any error that stops
   the viewer starting ("This browser could not run the viewer: ..."). Checked in headless Edge: the game file opens
   as before, a copy with its scripts stripped shows the note, the plain viewer is unchanged.
   Game files are made fresh on every click (2026-10-18, the user's choice): the games list has one "Game file" button
   that asks the helper to make the file (POST /api/game-file) and then downloads it. Before, once a game had a file,
   the button handed out that file, so files made before a viewer change lacked the newest stats.
6. Click-to-replay: markers on the shot map, turnover map and goalie report can be pointed at (a tooltip says what
   it was) and clicked to jump to four seconds before and play. A press that moves under 4 pixels is a click; more
   is a drag (pans).

The viewer was checked by rendering still frames in headless Edge
(`msedge --headless=new --screenshot=out.png "file:///.../viewer.html?match=capture1&t=103"`).
The ice surface is `rink_gens.png` (900 x 1440, supplied by the user, centre logo blurred). Game coordinates map to
it as `px = 450.4 + 2.459 * X`, `py = 777 - 2.079 * Y`:
- Y from the picture's goal lines (rows 219.6 and 1333.9) against the nets at Y = +/-268; the ice then ends at
  Y = +/-299, matching the puck's range.
- X from the faceoff dots (columns 278.3 and 622.5) against faceoff X = +/-70; the boards land at X = +/-129.
- The picture is about 18% wider per unit than tall, which fits the game running 256 pixels wide on a 4:3 screen.
  Markers are drawn in an unstretched frame so they stay round.
- Faceoff pucks rest at (0,0), (+/-70, +/-65) and (+/-70, +/-206), but the painted dots sit at Y = +/-73 and +/-212
  under this mapping, so vertical placement may be off by up to about 8 units (17 image pixels) somewhere, or the
  game simply drops the puck inside the dots. Bench line changes, creases and the centre dot all look right.
Benches: Home sits on the lower bench and in the lower penalty box, Away on the upper ones (the user). The bench
players are part of the picture; `tools/bench_mask.py` picks out their uniform pixels (the picture's blue on the
upper bench, its red trim on the lower) into `rink_benches.js`, and the viewer repaints those pixels in each
match's colours (Away: helmet/body ramp, strip colours 13/11/12; Home: trim, 8/9). It is precomputed because
browsers refuse to read pixels back from a local image. Home jerseys stay white, so the lower bench changes less.
If the picture is missing the viewer falls back to a drawn rink whose blue lines and centre circle are placed by
real-rink proportions (about 3 units per foot).

The user is part of an NHL '94 online community that standardizes on RetroArch 1.17 + the Genesis Plus GX core,
with a trimmed-down menu configuration. The user's install: `%USERPROFILE%\RetroArch-1.17-Win64`.
ROM in use: NHL '94, crc32 `9438f5dd`.

## SNES version

The user wants a SNES version too. The community plays it in RetroArch with the Snes9x core
(`cores\snes9x_libretro.dll`); ROMs are in `%USERPROFILE%\RetroArch-1.17-Win64\ROMs\SNES`: `NHL94.smc` (the base
game, crc32 42212a77 without header), `NHL94_Classic.smc` (a small hack that tracks checks per player), league ROMs
such as `SDL-S14.smc`. SNES hacking is less advanced than Genesis hacking. A colleague is mapping the SNES RAM
from the Genesis memory map doc. The user's old SNES save-state parser is `reference/snes_savestate_stats.txt` (see below).
- Some files have a 512-byte copier header (size % 1024 == 512); strip it. Base, Classic and SDL-S14 are LoROM with
  the internal title "NHL '94" at $7FC0 and a valid checksum. SDL15/SDL16 (1.1 MB) have a copier header too, plus
  extra code past the first megabyte (their reset jumps to $208000), so their size is not 512 past a multiple of 1024:
  `strip_header` now tells a header by where the internal header's checksum pair (adding to $FFFF) sits, as Snes9x
  does. SDL16 is NHL94_Classic's code (its check-tracking patches byte for byte) plus league rosters, 1-minute minors
  and the stats screen's "Penalties" column renamed "Checks"; everything else in the first megabyte is the base
  game's. All 47 NHL '94 SNES ROMs in the ROM folder read (28 teams each). On the 42 SDL15 and 47 SDL16 save states
  the per-player goals add up to the score (all but one state, mid-goal), per-player checks ($168E) to the team's,
  and the scoring summary names real players; `snes_preview.py` shows SDL15/16 states correctly.
- Team data uses the Genesis format with little-endian lengths: players as (length word = name length + 2, name,
  jersey byte in decimal digits, 7 rating bytes), the list closed by a length word of 2, then the name strings
  (city, abbreviation, nickname, arena) in the same length-prefixed form. Boston's roster ends at $E2E0C in
  NHL94.smc (file offset, no header) with "Boston" / "BOS" / "Bruins" / "Boston Garden" after it. The team
  pointer table has not been found yet.
- Code layout (2026-10-15): `tools/systems/` holds one module per system. `genesis.py` has everything Genesis:
  addresses and record layout, ACTIONS (animation words by name: shoot, pass, goalie_pass, poke, hook, lunge, down,
  dive, goalie_save), `fixed` (position format), the memory reader (`Emulator`, on `process.Attached`), what the
  helper records and reads (`BLOCKS`, `View`: screen, period, clock, score, teams, in_menus, in_game, live), the ROM
  readers (teams, logos, animation table, `find_rom`) and `read_match` (recording -> match file without the
  analysis). `common.py`: ROOT, STAT_FIELDS (the order of the team values in stat snapshots, which the viewer reads
  by position), overall(). `process.py`: Windows process reading shared by all. `snes.py`: what is known so far
  (stat addresses, scoring summary, ROM header handling); `attach` returns None and `read_match` is not written.
  `systems.of_capture` picks the module from capture.json's "system" (absent = genesis); match files carry
  "system". The analysis in export_match.py asks `actions(m)` for animation words. Checked: all seven Genesis
  recordings convert to exactly the same match files as before the split (only "system" added), the helper ran
  a fake-emulator game end to end, and the packaged exe converts in a fresh folder.
- SNES rink: `rink_snes.png` (900 x 1440, from the user; the original with Montreal's logo is
  `reference/rink_snes_original.png`, cleared with `tools/clear_centre_logo.py`). Laid out like the Genesis
  picture (benches, penalty boxes, stands, nets in the same places), so the viewer's `RINKS.snes` reuses
  RINK_SIDES, PENALTY_BOXES and the overhead rebuild with its own measurements (cx 449.2, cy 776.2, ux 2.451,
  uy 2.076 from goal lines at rows 219.5 / 1332.5 and dots at columns 278.6 / 622.2) and colours (ice #bfdaf7).
  These assume SNES game units equal the Genesis ones; not checked. `rink_snes.js` (embed_rink.py) and
  `rink_benches_snes.js` (bench_mask.py: Home red trim as on the Genesis; Away in grey-green, picked inside the
  bench only) load when a SNES match opens; `?rink=snes` shows it with any match. Game files carry only their
  system's rink. Bench recolouring needs SNES palettes (not read yet).
- Save states: `states\Snes9x\NHL94_Classic.state*` (446 of them). A RetroArch state is a 16-byte `RASTATE` wrapper
  around a Snes9x snapshot (`#!s9xsnp:0011`, then blocks `XXX:nnnnnn:` + data: NAM, CPU, REG, PPU, DMA, VRA 64 KB,
  RAM 128 KB, SRA, FIL, SND, CTL, TIM). The RAM block's data starts 68505 bytes into the snapshot (68521 into the
  RetroArch file). The user's parser (`reference/snes_savestate_stats.txt`) indexes the bare snapshot, so
  RAM address = its offset - 68505: with that, per-period goals add up to goals and the scoring summary has 6 bytes
  per goal in all 444 states with goals.
- SNES work RAM (bank $7E), from that parser. Stats are home/away pairs of little-endian words, away 2 bytes after
  home (the Genesis keeps one block per team instead):

  | Home / Away | Stat |
  |---|---|
  | $178E / $1790 | Goals |
  | $176A, $176E, $1772, $1776 (+2 Away) | Shots in P1, P2, P3, OT (no total word in the parser) |
  | $177E, $1782, $1786, $178A (+2 Away) | Goals in P1, P2, P3, OT |
  | $1742 / $1744, $1746 / $1748 | Power-play goals, power plays |
  | $1762 / $1764 | Shorthanded goals |
  | $174A / $174C, $174E / $1750 | Penalties, penalty minutes |
  | $1752 / $1754 | Attack-zone time, game seconds |
  | $1792 / $1794 | Faceoffs won |
  | $17B6 / $17B8 | Body checks |
  | $17BA / $17BC, $17BE / $17C0 | Passes completed, passes tried |
  | $17C2 / $17C4, $17C6 / $17C8 | Breakaways tried, breakaway goals |
  | $17CA / $17CC, $17CE / $17D0 | Penalty shots tried, penalty-shot goals |
  | $17D6 / $17D8, $17DA / $17DC | One-timers tried, one-timer goals |
  | $1C98 / $1C9A | Team index (the parser's team-code table) |

  Scoring summary: byte count at $313A, then 6 bytes per goal from $313C: a word (period << 14 | seconds into the
  period; period 0-3, 3 = OT), a byte (bit 7 = Away; low bits strength: 0 SH two men short, 1 SH, 2 even, 3 PP,
  4 PP two men up), then scorer, first and second assist as roster indices ($FF = none; all 3334 goals in the states
  fit). The Genesis may have a similar summary; it was never looked for (goals are worked out from stat changes).
- The NHL94SNES disassembly (github.com/abdulahmad/NHL94SNES; the user pointed to the Mhopkinsinc fork, now stale) rebuilds `NHL94.smc` byte for
  byte (same SHA-1), so its addresses hold for the base ROM. `src/ram94s.asm` (ram94snes.asm before 2026-10-21) names RAM; `docs/name_map.csv`
  every address; `src/data/teamdata94s.asm` the team database. Its sibling NHLPA93SNES has a fuller RAM list
  (`src/ram93snes.asm`; different addresses, same names and flag meanings). Its agent instructions are for that
  project, not this one.
- Objects as on the Genesis, but stored as arrays of 16 words (index = object * 2): Xpos $0D55, Ypos $0DB7 (integer,
  Genesis units), position $0F43 (Genesis codes, negative = off), facing $1163, animation SPA $11A3, pflags $1283
  (bit $0008 joystick controlled, the Genesis +$62 bit), roster place pnum $12A3, team pfteam $1503. Objects 0-5
  Home, 6-11 Away, 12/13 nets at (0, +/-268), 14 puck, 15 shadow. Period gsp $1630 (from 0), clock $1632, joypad
  $0776. Checked on the 445 save states (all of them, league ROMs SDL13-16 included): goalies at about +/-243,
  exactly one controlled skater per team. The disassembly's blueline is Y = $58 = 88 (ours from the attack-zone
  fit: 89). Who has the puck: not found (NHLPA '93's carrier assignment did not show).
- ROM teams (`snes.read_teams`): TeamList at $9CA5E7 (LoROM: file offset = (bank & $7F) * $8000 + (address &
  $7FFF)), 28 long pointers; records as described above; uniform palettes $96CD4E (home) / $96C9CE (away), 16 SNES
  colours per team. Goalies by their ratings (slots 6, 8, 9 empty: exact for all 65 Genesis goalies). Works on
  NHL94.smc, NHL94_Classic and SDL-S14; all 603 SNES players are on the Genesis rosters, but five teams lack a backup
  goalie the Genesis has (EDM, NYI, NYR, STL, TOR: the SNES rosters differ). SDL15 and SDL16 read too (see the
  header note above).
- Sprites (`snes.build_sprites`, the same library format as the Genesis one, `sprites/<crc32 of the ROM without
  header>.js`, 976 frames): SpriteFrames at $828000 (see the comment in snes.py for the frame and piece layout; SNES
  planar 4-bit tiles; 16x16 pieces are tiles N, N+1, N+16, N+17). Palette 4 is the team's uniform (Away's is 5);
  fixed palettes 2 (puck and nets; ROM $D50B6), 0 and 1 (vary in play; their most common colours from the save
  states, whose colour memory copy is work RAM $7E34B4). A contact sheet looked right (skaters, falls, goalies,
  arrows, stars, puck).
- Sprite frame of an object: $0D97 (a word per object, as the Genesis record's +$06; every value a real frame in the
  first recording; the puck's entry 397 / 401 ...). Mirrored (right-handed): attribute $0E03 bit $0800 (exact).
  At first the frame was looked up from SPA ($11A3, an address in bank $9D, the animation table $9DE0FC: 8 direction
  pointers to (frame, time) lists) + SPAnum ($11C3, 4 bytes per pair) + facing; that turned right-handed skaters the
  wrong way (the user saw it): the game looks up direction (8 - d) for them before mirroring, as the Genesis does.
  Picture facing vs direction of travel for moving skaters: right-handed 54% within 45 degrees with the lookup, 78%
  with $0D97 (left-handed 79%; the rest is skating backwards, turning, gliding). The lookup (`animation_frame`) is
  kept for save-state stills.
- `snes.read_match` builds a match from samples of SNES RAM (positions, puck, control, roster, role, facing,
  animation, frame, mirror, clock, period, score, shots, rosters, palettes, anims, sprites); `snes.SaveStates` reads
  save states as samples and `tools/snes_preview.py <state>` makes a one-moment match (matches/snes_*.js) from one:
  NHL94_Classic.state10 (Chicago 7-3 St. Louis) shows correctly on the SNES rink with SNES sprites.
- Live reading (2026-10-15, the user's first online SNES match): `snes.Emulator` finds work RAM through Snes9x's
  memory map in the core's writable data (one pointer per 4 KB of SNES address space: bank $7E = 16 equal entries,
  $7F the next 16 at +64 KB; the cartridge at the bank $80 entry + $8000); attaches in 0.01 s. `tools/snes_record.py`
  is a research recorder (work RAM $0000-$3FFF about 60 times a second, all 128 KB a second, everything incl. menus).
  `captures/snes_2026-10-15_1755`: Toronto (home) 1-5 Pittsburgh, 5-minute periods, online, both teams human; two
  penalty shots (Andreychuk missed in P1 at about 67 s of the recording; Samuelsson scored, P3 4:26), two instant
  replays in P3, one Pittsburgh pass shot, a few posts, both teams penalised after one whistle, Game Stats viewed
  after the final horn (per the user). Converts with `python tools/export_match.py captures/snes_2026-10-15_1755`
  (played on NHL94_Classic.smc, per the user; its capture.json was given the fingerprint afterwards. SNES
  recordings store `rom_crc32` = crc32 of the cartridge's first megabyte without copier header, from the
  emulator's memory: assumes Snes9x keeps the ROM without the header, not yet checked live): positions, sprites, teams, controlled
  players and goals all show right (penalty shots: only shooter and goalie on the ice, the rest at (-240, 0)).
- Goals: the scoring summary's count rises before the entry is written, so goal moments come from the count and the
  contents from the longest summary (the count goes to 0 back at the menus); penalty-shot goals from the psGoals
  words rising within 3 s. All six goals right (Lemieux 3, one PPG; Stevens; Samuelsson PS; Borshevsky).
- Who has the puck: $0AE7 (object number, 15 = nobody; "nobody" in 456 of 457 clearly loose moments, the puck mover
  in all 608 clearly carried ones). It drops to 15 for a moment hundreds of times while a player skates with the
  puck, so gaps under 0.15 s with the same player on both sides are bridged; puck held 48% of the time. Also:
  a2touchpuck writes the last toucher to $7E30F6 (object), $30F8/$30FA (x, y) and each team's tmtouch list.
- Animations, from the release behaviour and by matching Genesis timing patterns (`match_anims` approach): shots
  $ED4A (puck leaves at a median 15500, up to 27000) and $EE5C (forehand / backhand presumably); passes $EC66 /
  $ECD8; stop $EC14; sweep (poke) check $F208; checks/burst $F27A-$F342 (Genesis order: shoulder L, shoulder R, hip L,
  hip R, burst); falls $F49C (forward) / $F54E (back); faceoff $F600 / $F62A; upended $F6C0; stumble $F7B2; goalie
  ready $E0FE, saves $E1E2-$E2FC, gswing $E34E, dive $E4B6 (some by order, not all checked). Most common, still
  unnamed: $EAFE, $EBB0, $EBE2 (skating), $EA1A / $EA4C.
- SNES analysis (on): ACTIONS confirmed from controller 1's presses ($0776; it drove Toronto, the user's team: 210
  action answers against Pittsburgh's 100): A = shoot ($ED4A/$EE5C, plus $F196, a swing without the puck: one-timer)
  or burst/check ($F342, $F2AC); B = pass ($EC66/$ECD8; goalie $E34E) or poke ($F208). Hook not identified. The
  hidden puck (the analysis's whistle marker) is the clock-stopped flag gmclock $15D6 (puck height given as -256).
  Posts by the Genesis rule; team stat snapshots in STAT_FIELDS order (no per-player values, so find_hits uses the
  team checks: the checking skater nearest an opponent going down). The recording is cut where the game's numbers
  last stood (it runs on into the menus). Against the game's own counts: shots on goal 10/10 and 12/12, checks 24/24
  and 29/29, counted passes 53/53 and 49/48, faceoffs won 5/5 and 8/8. A goal with no shots-on-goal rise (the SNES
  penalty-shot goal) now reads counted false (no change on the Genesis recordings). Pass shots: Pittsburgh's 2 (the penalty-shot goal,
  and a save) are right per the user; Toronto's 'wide' one was Andreychuk's pass round the net to Gill (36 wide of
  the middle at the goal line, Gill had it behind the net 0.45 s later), so the pass-shot rule now also asks: a puck
  wide of the posts (more than 22 from the middle) that a teammate takes within 1 s, before the goalie or the other
  team, was a pass. No Genesis pass shot changed.
- Penalties (`snes.read_penalties`): the buffer at $15DE holds (penalty number, object) byte pairs; an entry
  appears at the foul (play may go on: a delayed penalty), gets bit 7 of the object byte at the whistle, and is
  cleared once listed. The box state ($1852: a word per roster place, Home's 26 then Away's; $FFFE bench, $FFFF
  ice, $FFFD out, $FFFC none, else seconds left, 120 for a minor) turning into seconds is the listing. Penalty
  numbers index the ROM's rule table (Genesis layout; $53EB in NHL94_Classic, found by its rule 1 "Period Over";
  number = 2 x rule): $14/$1C Roughing, $18 Charging, $1A Slashing, $1E Cross Check, $20 Hooking, $22 Tripping,
  $24 Penalty Shot (its object is the fouler), $26 Interference, $28 Holding, $2A/$2C Fighting, $2E Instigator.
  Also: $1636 = the penalized player listed last (roster place, bit 15 Away), $18BA the box queue (2 x roster
  place), $1624 players in the boxes (Home x 16 + Away), $1C82 period length. In the first recording: Gill
  Interference (P1, foul 42.1 s, listed 48.5 s), Andreychuk Interference and Samuelsson Cross Check (P3 2:45, one
  whistle; Samuelsson's foul first, delayed), penalty shots awarded to Toronto (62.7 s) and Pittsburgh (366 s).
- Per-player stats: bytes per roster place, Home's 26 then Away's 26, the Genesis order: goals $18EE (goalies:
  against), assists $1922, shots $1956 (goalies: against), penalty minutes $198A; checks thrown $168E in
  NHL94_Classic (aligned by timing: at 49 of 54 rises of a team's checks the slot of a player of that team who was
  checking rose; used only where its totals equal the team checks); energy $17EA (word, high byte, 16 fresh).
  Ice time not found. Checked: Lemieux 3 goals, Murphy 2 assists, Potvin 12 shots against / 5 goals, Barrasso
  10 / 1; Murphy 10 checks, Samuelsson 9. Stat snapshots now carry 8 values per roster place like the Genesis
  ones, so cards, penalty boxes and find_hits (per-player path: 53 = 24 + 29) work.
- Pause and replay: sflags $15D8 bit $0001 = paused (pause menu; replays are watched from it), bit $0800 = replay
  playing (the user's two replays in P3: 383.8-395.1 s and 424.4-435.0 s, each inside a pause). The converter leaves
  paused samples out and closes the timeline over them (`LivePlay`): 48 s fewer, no count changed.
- First live SNES games with the helper (2026-10-16, the user's TOR vs CHI twice on NHL94_Classic, cd85e387, online
  against a league opponent; Home then Away): `2026-10-16_1528_TOR-CHI` (7-2) and `2026-10-16_1540_CHI-TOR` (5-3),
  in Documents\NHL94 Viewer. Three problems, fixed: (1) the SNES Emulator lacked `pid` (the ROM-name step), so the
  helper failed at attach; (2) at the menus the SNES roster bytes can all read 0, not $FF, so the helper took the
  menus' default MTL vs LA for a game under way (`on_ice` now needs each team's places to hold different players,
  and a recording is renamed after the teams that played when it closes); (3) the SNES shots-on-goal word flickered
  2 -> 3 -> 2 -> 3 within 80 ms (twice in game 1), counting one shot twice: `steady_stats` in export_match.py smooths a
  count that changes back within FLICKER_MS 250 (team counts other than attack-zone time, each player's first five
  values, and the per-sample score and shots words; never ice time, energy or the penalty word, which really do flip
  at line changes). Genesis recordings unchanged; the first SNES recording's counted passes went from 49 to the game's
  48. Both new games then match the game exactly: shots on goal 15/10 and 16/5, checks 35/27 and 32/31, goals; the
  power-play and shorthanded tags agree with the penalties. Roenick's goal in game 2 (P1 1:22) raised no shots-on-goal
  count, so it reads counted false, as the SNES penalty-shot goal did. No injury yet.
- The helper records SNES games itself (2026-10-15): `snes.View` (period, clock, score, teams, on_ice from the roster
  bytes = $FF before the faceoff and at intermissions, in_game = not paused / not menus, in_menus = teams and score
  cleared), BLOCKS [$0000-$3FFF], `Emulator.dump_rom` (roms/<fingerprint>.smc). At the final horn the SNES game sets
  the period to 4 and the clock back to the period length; View reports the clock as 0 then, so the helper's
  end-of-game test serves both systems. Tested by replaying snes_2026-10-15_1755 through the helper as a fake
  Snes9x at 6x speed: it waited, recorded TOR vs PIT, left out the replays, converted (6 goals, 3 penalties, shots
  10/12, 53 hits, Classic found by fingerprint). Not yet tried live.
- Controllers: $0776 controller 1, $0778 controller 2 (its presses answered by Pittsburgh's skater 149 times to 75;
  controller 1 Toronto 210 to 100). Kept in the match file in the Genesis bit layout by what the buttons do (SNES B
  = Genesis B, A = C, Y/X = A, Start, D-pad), with `padLabels` {A: Y, B: B, C: A} so the viewer shows the SNES
  letters; padTeam and pad2Team from whose controlled skater answers the presses (the SNES has no cont1team).
- Ice time: no per-player array was found (no 26-word arrays summing to about 6 x the game time), so the converter
  counts it: each second the clock ticks off goes to everyone on the ice (goalies 901 s of a 900 s game; team sums
  5171 / 5287, short of 5400 by the penalties).
- SNES sounds identified by the user by ear: 3 boo, 4 oooh, 8 cheer, 9 pass or shot, 11 probably the puck off the
  boards, 17 the puck off a post, 23 a check into the boards, 26 a big hit, 32 a slapshot, 34 skating (unused),
  35 the whistle (`snes.SOUND_ROLES`). Playing speeds by ear: SNES 11 kHz, Genesis 7 kHz (now the defaults). The
  viewer gained sound moments for slapshots (shot type), posts, the whistle (play stopping, not a period's end) and
  the puck off the boards (a loose puck near the boards turning back); a library without a sample for one plays its
  nearest (slapshot -> shotfh) or nothing.
- The SNES puck: its frames (395-405) are stored with palette 0 but drawn with palette 2 (black puck, white shine,
  blue edge and shadow); 396 is its shadow and 397 the puck at rest (the Genesis's 394 / 395). SNES frame 394 is the
  instant replay's crosshair corners, which the viewer drew under the puck (the user saw it) until the sprite library
  gained `puck: {shadow, onIce}` for the viewer to use; a puck frame of 0 shows the puck at rest (SNES frame 0 is a
  skater).
  Puck height (2026-10-16, after the user asked for SNES goal heights): `puckz` $0DF9 with its fraction $0DFD (named
  in the NHL94SNES disassembly's ram94s.asm; also puckvz $0E01, shadowz $0DFB), now the match file's puck height
  as on the Genesis: goals cross the line at 0-13 (Genesis 0-13), the puck is in the air about a fifth of the time,
  dump-ins reach 45. Nothing else changed (shots, checks, passes, bobbles, bumps). Not known yet: the hook.

## Reading game memory live

RetroArch's network commands do not work for this core: `READ_CORE_MEMORY` answers "no memory map defined", and
`READ_CORE_RAM` returns -1 even with achievements on (no RetroAchievements account was tried).

What works: `ReadProcessMemory` on `retroarch.exe`. The 64 KB work RAM ($FF0000-$FFFFFF) is found by scanning the
writable data of `genesis_plus_gx_libretro.dll` for the 68000 memory map: 32 consecutive 40-byte entries ($E0-$FF)
sharing one base pointer. Entry 0's base leads to the cartridge, whose header at +$100 reads `ESAG` (byte-swapped
"SEGA"), which confirms the hit. Host memory holds each 16-bit word in native order, so a little-endian 16-bit read
gives the Genesis value; a single byte at Genesis address A is at host offset A XOR 1.

Limits: Windows only, sampled on its own clock (not locked to game frames).

Netplay works: `captures/capture6_netplay_bos_stl` is a full online game (the user Boston, Home, against a human
St. Louis; 6-3, 5-minute periods), recorded on the user's machine with
`powershell -ExecutionPolicy Bypass -File tools
hl94_record.ps1 -Seconds 1800`. Everything read normally: scores,
shots, stats, penalties, both teams' controlled skaters (+$62 set on one record per team almost throughout).
Netplay's rollback does show (2026-10-16; the user saw skaters jump a few pixels and straight back in
2026-10-16_1540_CHI-TOR): RetroArch runs the game a few frames ahead on guessed input, then rewinds and replays them,
and a read made while it was ahead shows every object a few frames on. The SNES games recorded by the helper online
had about 240 such samples each, the first SNES game 17, capture6 21. Each system's read_match leaves out a sample
when the frame counter (Genesis $B03E, SNES $0764: up 1-3 between reads in 92-95% of samples) shows the same frame
again or up to ROLLBACK_FRAMES 30 earlier within the next half second; the time those samples covered is kept (not
closed up like pauses). That also drops the earlier of two reads of one frame (a read in the middle of the frame):
about 6-10% of samples. After it: no there-and-back jumps left (one in CHI-TOR); shots on goal, checks, goals,
penalties, injuries, EA Special attempts and the reviewed bumps and bobbles unchanged (on the SNES, bobbles now look
at the puck one sample after the bounce too, since its position can trail its speed: CHI-TOR then finds the user's 10
plus three unreviewed, P1 3:59, P2 1:36, P2 0:53); new: a bump in BOS-PIT (Bourque by Lemieux, P1 4:35) and a
bobble in capture1; a counted pass lost in each new SNES game. Periods read 0-2 for the three periods, then 3 and 4 at the
end. $BEEF holds the local player's controller; the converter works out which team it drives (`padTeam`: the team
whose controlled skater answers the presses, 222 against 102 of 617 here) so the viewer shows the buttons in
two-player games too.

## Memory layout (work RAM offsets, i.e. $FFxxxx)

Object records are 128 bytes ($80). Record k starts at `$B04A + $80*k`.

| Record | Start | What |
|---|---|---|
| 0-5 | $B04A-$B2CA | Home team's six players, in no fixed order (see +$35) |
| 6-11 | $B34A-$B5CA | Away team's six players, in no fixed order |
| 12, 13 | $B64A, $B6CA | The nets, fixed at (0, +268) and (0, -268) |
| 14 | $B74A | Puck |
| 15 | $B7CA | The puck's shadow: at the puck's X/Y with height 0, frame 394. After a goal it moves behind that net (0, +/-300, height about 14) and runs frames 563-576, the goal light (a red lamp: its flash turning, then its beam), for 7-9 s; at the end boards behind the net (0, +/-300, height 14) or in the net. The converter keeps it as `lights` and the viewer draws it |

Fields within a record:

| Offset | Size | Field |
|---|---|---|
| +$06 | 2 | Animation frame number, 1-845: an index into the ROM's frame table (see Game sprites). +$08 is a second copy that changes slightly earlier |
| +$1C | 4 | X, 16.16 fixed point (integer word first) |
| +$20 | 4 | Y, same format |
| +$24 | 4 | Z / height (seen on the puck, up to about 10) |
| +$28 | 2 | X speed (signed) |
| +$2A | 2 | Y speed (signed) |
| +$2C | 2 | Probably Z speed |
| +$35 | 1 | Position: 0 G, 1 LD, 2 RD, 3 LW, 4 C, 5 RW (the ROM's line order); $FF = off the ice (bench, mid line change) |
| +$53 | 1 | The record's own number (0-15) |
| +$55 | 1 | Facing, 0-7: 0 = +Y, 2 = +X, 4 = -Y, 6 = -X; +1 = 45 degrees clockwise on screen |
| +$58 | 2 | Animation word: one value per action, the same whatever the facing. See the table below |
| +$60 | 1 | Puck record only: $00 while a player has the puck, $FF while it is loose |
| +$61 | 1 | Puck record only: record number of the player who has (or last had) the puck |
| +$66 | 1 | Player's index in the team's roster, 0-based, in ROM roster order ($FF during intermission) |
| +$67 | 1 | Weight (per the weight-bug code in the editor's hacks; not checked against values) |
| +$68.. | | About a dozen bytes that look like the player's ratings (not decoded) |
| +$76 | 1 | Bit 0 set = shoots left; clear = shoots right, and his picture is drawn mirrored |
| +$62 | 1 | Bit $08 set = the human-controlled skater (at most one per human team; seen on Home and on Away) |

- Coordinates: +Y is up the screen, +X is right. Rink spans about -130..130 in X and -300..300 in Y.
  Goal lines at Y = +/-268; goalies sit near +/-242.
- At the opening faceoff each team's records are in the order RW, LW, C, RD, LD, G, but that does not last: with
  line changes on, and from the second period, players occupy different slots (the goalie was seen in slots 4 and
  5 for Home, 10 and 11 for Away). Always take position from +$35. Untested with a pulled goalie or penalties.
- After an on-the-fly line change the game can give two players the same position: in `capture5_league30` at
  1:52 of period 1 the incoming Seattle defenceman got LD while the other defenceman was already LD (Helsingin
  showed the same at that moment), and it stays that way until the next whistle. That is the game's own value;
  the viewer shows it as is and lists both players. $CB9C does not match who is on the ice, so it is not the
  current line.
- Possession: use puck +$60/+$61. (While carried, the puck's speed words also equal the carrier's, but that test
  misses about half of the frames the marker catches.)
- Facing changes often: skaters pass through intermediate values while turning, and it need not match travel direction.
- Speed words are proportional to movement (about 250 speed units per position unit per quarter second of sampling);
  the exact per-frame scale has not been pinned down.

Animation words (record +$58). "Tapped" = the user pressed that button at a known time; the rest are inferred from
statistics over the three captures (what the puck did, who was near, what came before and after).

| Value | Meaning | Basis |
|---|---|---|
| $1122 | Hook (A without the puck), about 0.5 s; often followed by $1154 | Tapped, 4 of 4 |
| $0718, $078A | Pass (B with the puck), about 0.5 s | Pressed: 8 each of 18 B presses with the puck; the player loses the puck in about 90% of runs |
| $07FC, $092E | Shooting (C): forehand and backhand (named in the disassembly). Runs 0.5-0.7 s for a tapped wrist shot, 0.9-1.1 s for a held slapshot | Pressed: 19 of 19 C presses with the puck; long holds gave peak puck speeds of 15000-23600, taps 11400-13700 |
| $0C5E | Speed burst / body-check lunge (C without the puck), under 0.1 s; usually followed by $0B96 for about 0.4 s | Pressed: 20 of 43 C presses without the puck |
| $0B24 | Poke check (B without the puck, near the carrier), about 0.3 s; goalies do it too | Pressed: 26 B presses; 85% human overall |
| $0DD8, $0D26 | Knocked down, about 2.2 s. After a $0C5E lunge, a nearby opponent entering one of these means the check landed (29 of about 200 lunges) | Inferred |
| $01EC, $021E, $148E | Goalie save attempts: start with the puck loose, close, and at shot speed (15000-18000) | Inferred; $148E also followed a C press while controlling the goalie |
| $0FEA, $1014 | Faceoff stance (the two centres alternate between them) | Inferred |
| $050C | Standing or gliding | Inferred |
| $0694, $0662, $06C6, $05D0 | Skating ($05D0 never has the puck) | Inferred |
| $053E | Skating with the puck | Inferred: has the puck in 100% of runs |
| $0002 | Goalie ready | Inferred |
| $02F4 | Goalie dive (A while the goalie is moving), about 1.2 s | Pressed: 7 of 8 A presses while controlling the goalie in `capture5_league30` (the user dived after two Seattle goals, at 261-263 s and 298-300 s). Computer goalies did it twice, each time with the puck loose 5-6 units away, and failed to claim it both times, as the user describes |
| $0366 | Goalie passes the puck out (B as goalie with the puck) | Pressed, 4 of 5 |
| $03D8, $1684, $02A2, $0250, $14F2, $0146, $14C0 | Other goalie actions, not told apart | Unknown |
| $0A92, $0E8A | Computer-only, without the puck | Unknown |
| $0B96, $0BC8, $0CF4, $1154, $0EFC, $0A60 | Unknown (after-effects of checks and hooks, most likely) | Unknown |

The Genesis disassembly (github.com/abdulahmad/NHL94Genesis, the user pointed to it; it rebuilds the user's nhl94.bin,
crc32 9438f5dd, byte for byte) names every animation in `src/frames94.asm` (SPA<name> = offset, i.e. the record's
+$58 word) and every RAM variable in `src/ram94.asm` (since 2026-10-21; before, `src/stubinc/ram_addrs.inc`, when ram94.asm was an old 93 list with wrong
offsets). The names, which settle the table above:
$0002 gready, $0114 gready2, $0146 gglover, $0178 gglovel, $01AA gglovel2, $01EC gstickr, $021E gstickl, $0250 gstackr,
$02A2 gstackl, $02F4 gdive, $0366 gswing (the goalie's pass), $03D8 gskate, $046A pflip, $050C glide, $053E skatewp
(with the puck), $05D0 skate, $0662 turnl, $0694 turnr, $06C6 stop, $0718 passf, $078A passb, $07FC shotf (forehand),
$092E shotb (backhand), $0A60 glideback, $0A92 skateback, $0B24 sweepchk (poke), $0B96 shoulderchkl, $0BC8
shoulderchkr, $0BFA hipchkl, $0C2C hipchkr, $0C5E burst (speed burst), $0C90 Hold, $0CC2 Hold2, $0CF4 flail, $0D26
fallfwd, $0DD8 fallback, $0E8A celebrate, $0EFC pump, $0F6E wallright, $0FAC wallleft, $0FEA faceoff, $1014 faceoffr,
$102E siren, $1078 bglass, $109E stanley, $10D0 catch, $1122 hook, $1154 hook2, $11E6 stumble, $1298 fake, $136A flip,
$145C injuryfall, $148E ghighr, $14C0 ghighl, $14F2 gstick2r, $1544 gstick2l, $1596 gslamtop, $1684 gslambot,
$1776/$17E8/$185A/$18CC boardfront/right/back/left, $193E/$1A00 benchcheckl/r, $1AC2 crosscheck, $1AF4 injury1.
Used (2026-10-15): shots carry `save`, the goalie's first save move from the release to 0.25 s after the result
(genesis.SAVE_MOVES: glove, stick, pad stack, high, dive, slam, or none = stood his ground; of 115 saves in the
recordings: stick 62, high 14, pad stack 12, dive 5, glove 2, none 20), shown in tooltips and the goalie report
(split human / CPU). Hits carry `how` (the thrower's check animation within 0.7 s: shoulder 111, cross-check 14, hip
2, unseen 48 -> 'check') and `outcome` (the target's: knocked down, upended, into the boards, into the bench, else
stayed up). Big hits (upended, boards, bench) get a banner ("Bourque upends Shanahan (shoulder check)"), a team stat
and a card stat; the card lists check types.
From the same map, checked on `capture6_netplay_bos_stl`: controller 2's held buttons are the byte at $BEF1 (lj2;
ours, $BEEF, is lj1's low byte): its presses were answered by St. Louis's controlled skater 308 times against 91
(controller 1: Boston 222, St. Louis 103), so both players' buttons are in every recording. cont1team / cont2team
($C328 / $C32A, 0 none, 1 Home, 2 Away) read 1 and 2 there (outside fast.bin; full.bin has them). The converter
keeps controller 2 as `pad2` and sets padTeam / pad2Team from cont1team / cont2team (the old press-matching guess
stays as the fallback); the viewer shows each team's controller (`teamPads`).
Goals take `strength` from ScoreSum (matched in order to find_goals' goals; for recordings that began mid-game, its
last entries); all goals in all seven recordings agree; two-men-up / -down goals get a "5 on 3" / "3 on 5" kind.
ScoreSum: a byte count at $C472, then 6 bytes per goal from $C474 (big-endian word period << 14 | seconds into the
period; a byte, bit 7 Away, low bits strength as on the SNES: 2 even, 3 power play; scorer, first and second
assist, $FF none): all 9 goals of capture6 match find_goals. Also there: joypuckcarrier $C318, c1/c2playernum
$C320/$C322, OptGoalie $D052, goaliemode1/2 $D05A/$D05C, replayactive $BE1E, sflags $C2EC (bit 0 pause).

One-timers: the receiver starts a shooting animation while the pass is still on its way, and the puck's possession
bytes never name him (the last-touch byte stays on the passer). The user confirmed the game has one-timers and
scored some in these captures; `capture1` at 103.8 s is one (Damphousse to Bellows). The viewer calls a shooting
animation a one-timer when the player does not have the puck in its first 100 ms; that also counts attempts where
the pass never arrives.

B without the puck switches the controlled skater unless it produces a poke check. "Pressed" rows come from
`capture3_bos_la`, by matching each button press to the controlled skater's next animation.

Globals:

| Address | Field |
|---|---|
| $C466 | Period index, 0-based (2 bytes) |
| $C468 | Seconds left in the period (2 bytes) |
| $C6DA / $CA3E | Score, Home / Away (2 bytes). Both confirmed |
| $C6CC / $CA30 | Shots, Home / Away (4 bytes; the low words at $C6CE / $CA32 change). Both confirmed |
| $C6F7 / $CA5B | Team index, Home / Away (1 byte; index into the ROM's team table) |
| $CB9C | Away's current line as roster numbers, 1-based: G, LD, RD, LW, C, RW, extra (Home's is presumably $C838) |
| $BD18 / $BD1C | Camera Y / X in world units (2 bytes each). Screen pixel = (128 + X - camX, 112 - Y + camY); the screen is 256 x 224 and one world unit is one pixel. (`tools/sprite_frames.py` uses 120, which is 8 too low; it only affects where its cut-outs are centred) |
| $BD28 | The four 16-colour palettes in use (32 bytes each). Line 2 ($BD68) is the Home team's ROM palette at team +$0C, line 3 ($BD88) the Away team's at team +$2C |
| $C018 | The game's sprite table, copied to video RAM $DC00 every frame |
| $BEEF | Controller 1, buttons held now (1 byte): $80 Start, $40 A, $20 C, $10 B, $08 Right, $04 Left, $02 Down, $01 Up |
| $DEDE, $DEE2 | Hold pointers to record starts (purpose unknown) |

## Game states (for the helper)

From `captures/explore1_menus` (all of RAM at about 52 Hz for 4 minutes: start-up, menus, team select, pre-game, play,
a goal, pause, instant replay, play, pause) and the once-a-second snapshots of `capture6_netplay_bos_stl`:
- $FFF7 (byte; $FFF6 is 125 while paused) is the screen: 1 start-up, 15 menus and team select, 124 / 144 the pre-game
  screens, 0 the game itself (play, whistles, faceoffs, intermissions), 80 the pause menu (76 entering it, 84 / 90 as
  its cursor moves), 100 the instant replay (108 leaving it). Single-sample values in between are transitions.
- $FEED is 1 while paused (menu or replay), 0 in play; other values in the menus.
- Team select: $C6F7 / $CA5B change as teams are chosen. Pre-game: the clock is already set (300) but the player
  records' roster index (+$66) is still $FF; it gets set at the opening faceoff (67.3 s there).
- The instant replay does not touch positions or the clock, but it does animate the records' frame numbers (+$06,
  +$08) and a few other record bytes; the replay's own state is around $B94D-$B9C3 (e.g. $B9BC 0 during it). So
  samples while $FFF7 is not 0 must be skipped, or the replay shows as players changing poses on the spot.
- End of game: the period index goes past the third period with the clock at 0 (3, then 4, in capture6), and $FFF7
  stays 0 then. The user cannot quit a game to the menu mid-game. Overtime (period 3 while tied) is untested.

## Game sprites

The viewer's "Game sprites" checkbox (on by default; turning it off is remembered) draws players with the game's own pictures, extracted from the ROM by
`tools/extract_sprites.py` into `sprites/<ROM crc32>.js` (845 frames, about 870 KB). There is one library per ROM
because the 30-team league ROMs repaint the players; the converter builds a ROM's library the first time it
sees it and writes the checksum into the match file as `rom`, which is how the viewer finds it.

- Tile bank at ROM `$5DE84`: uncompressed 8x8 tiles, 32 bytes each, 4 bits per pixel, numbered from 0.
- Frame table at ROM `$9E724`: word N is the offset from `$9E724` to frame N's pieces (word 0 is unused; frames
  1-845). The pieces of frame N run up to frame N+1's offset. Each piece is 8 bytes: x, y (signed words, relative
  to the player's position, y down), first tile number, attributes (bits 13-14 palette line, bit 12 vertical flip,
  bit 11 horizontal flip, bits 0-3 hardware sprite size: width-1 in bits 2-3, height-1 in bits 0-1). Tiles within
  a piece run down each column, then across. Earlier pieces are drawn on top.
- A player record's frame word (+$06) indexes that table directly; the frame already includes the direction faced.
  The game mirrors the whole picture left-to-right when bit 0 of record +$76 is clear (bit 3 of +$04 agrees with
  it). That bit is handedness: it was set for every left-shooting skater and clear for every right-shooting one
  in `capture3_bos_la`, going by the ROM's Handed/Fighting value. The frames are drawn left-handed.
- Palette line 2 in the table means "the team's colours": the game loads Home's ROM palette (team +$0C) into line 2
  and Away's (team +$2C) into line 3. Lines 0 and 1 are the rink's 32 colours at ROM `$59924`, the same for
  every team (they equal what work RAM $BD28/$BD48 held in the captures).
- Frames below about 400 are skaters, about 400-560 goalies; the table also holds non-player pictures (some pieces
  use palette lines 0 and 1), which the viewer does not use yet.
- Verified with `python tools/extract_sprites.py --check captures/sprites1`: 2396 of 2545 pictures the game drew
  for players alone on screen match the ROM frame pixel for pixel (the rest are timing skew between reads).
- Frame 0 = no picture (seen for a second or two while the game repositions players, e.g. after a penalty); the
  viewer keeps the player's last real frame instead of falling back to a disc.
- The puck is drawn from the game too: its record's frame (+$06) is 395 or 399 on the ice and 396-404 tumbling in
  the air, in the rink's fixed colours; the viewer draws the shadow (frame 394) at its position and the puck raised by
  its height (+$24). The puck's height reads -256 while the game hides it (3-5 s at each stoppage before the
  faceoff), and the viewer hides it then too. The converter stores the frames as `puckFrame`. The nets are frames
  405 and 406 (records 12 and 13).
- Not drawn from the game: player shadows, nets, referees.
- Hot shots: the converter keeps the puck's speed words (+$28/+$2A, in hundreds) as `puckV`. The viewer streaks a loose
  puck that is heading at a net (on its line it would cross that goal line within 45 units of the middle) when its
  speed is at least 13000 (orange) or 18000 (white-hot). Speed alone does not separate shots from hard passes and
  deflections (both reach 14000-20000); with the heading test, 23 of 29 shots on goal in `capture5_league30` get a
  streak (the rest are slower), and about two-thirds of streaks come with a counted shot (the others are mostly
  shots that miss, which the game does not count). Puck speed from positions tops out near 340-420 units/s and is
  too noisy for this.
- Animation table at ROM `$5B1C` (original ROM; `$7490` in the 30-team ROMs; the converter finds it by the standing
  animation's offsets 18, 22 ... 46 at +$50C). Record +$58 (the animation word) is an offset into it. Each animation
  starts with 8 word offsets, one per direction (0 = up the screen, +1 = 45 degrees clockwise), from the animation's
  start to a list of (frame, duration) word pairs that ends at a negative duration (a loop back). Examples: $050C
  standing = frames 1 + 5d; $053E skating with the puck = 2-5 + 5d; $0002 goalie ready = 407 + 3d then 539-...;
  $0FEA faceoff has only up (dir 0) and down (dirs 1-7 share one list). Right-handed (mirrored) players use the
  list for direction (8 - d) mod 8, then the picture is flipped. The animation word can be a moment out of step with
  the frame (records with $0694 showed $05D0's frames 42-45), so the viewer looks frames up across the whole table.
  The converter writes it to the match file as `anims`; it covers 99.5% of drawn frames in `capture5_league30`
  (not frames 377-380 and some above 700).

How the layout was found: `tools/nhl94_record_sprites.ps1` records work RAM $B000-$CBFF plus the on-screen sprite
list and the tiles it uses from the emulator's video RAM (in this core build it sits $2023560 bytes after work RAM;
the sprite table at video RAM $DC00 matches the game's copy at work RAM $C018). `tools/sprite_capture.py` reads
that file and `tools/sprite_frames.py` cuts out each player's picture. `captures/sprites1` (82 MB) is that recording.
The tiles turned out to be verbatim in the ROM, and the frame table was found by searching for one frame's tile
numbers.

## The NOSE4Web editor (reference)

`C:\D\GenAI\NOSE_source_1.2b_wboy\nose-web` is the user's web ROM editor (TypeScript, based on wboy's NOSE, with
smozoma's smozROM hacks; GPL). Read it for ROM facts; do not change it from this project. Useful files in `src/core`:

- `team.ts` - the team block, which agrees with the layout below and adds: +$4C three bytes of team ratings then a
  byte of forward/defence counts, +$50 two goalie bytes, free bytes of $FF before the roster, and the roster closed
  by a length word of 2. Palette: home strip then away strip.
- `games.ts` - per-ROM settings. Player ratings are 14 values of 0-15, two per byte after the jersey number, in the
  order Wgt, Agl, Spd, OfA, DfA, ShP, Chk, H/F, StH, ShA, End, Rgh, Pas, Agr (goalies: Wgt, Agl, Spd, OfA, DfA, PkC,
  -, GlH, -, -, StR, StL, GvR, GvL). H/F is odd for a right-hand shot. Also the strip's 16 colour uses, line names
  (NLC, Sc1, Sc2, Chk, PP1, PP2, PK1, PK2), the rink palette offset, and the 30-team and EVO variants (team count
  differs; the team table is still at $30E).
- `rating.ts` - the overall-rating formula. `teamratings.ts` - the six team ratings.
- `graphics.ts` - the picture block format, and where the centre-ice logo of each team is (a table found through
  the pointer at ROM $FEA5A; 6 x 4 tiles).
- `hacks.ts` - code addresses for gameplay (weight bug, checking, goalie range, energy, speed burst, clock). Its
  byte patterns show record +$66 as the roster index and +$67 as weight, and the clock constant of $18 = 24 frames
  per game second.

Used here so far: the home team's centre-ice logo (drawn at centre ice in its home palette), each player's
ratings and overall rating (in the lineup panels; point at a row for the full card), and the team count for
30-team and EVO ROMs. The converter and sprite extractor were run over every NHL '94 ROM in the RetroArch ROM
folder (4 original-layout, 46 thirty-team): all parse, all have the frame table at the same address, and the
30-team ones have different sprite graphics. `captures/capture5_league30` (7 minutes on `CDL_dynasty_03_FINAL.bin`,
Helsingin Home and human vs Seattle, line changes on, three periods) shows a 30-team ROM uses the same work RAM
layout: scores, periods, rosters (12-player league rosters), positions, the controlled-skater marker, goalies
switching ends and animation frames all read correctly. Roster index and frame read $FF / 0 during
intermissions. NHL '95-based ROMs in that folder (code T-50856) are not supported.

## ROM data (names and numbers)

The ROM is at `%USERPROFILE%\RetroArch-1.17-Win64\ROMs\Genesis\nhl94.bin` (the same folder has edited variants;
names must come from whichever ROM was being played). All values big-endian.

- `$30E`: 28 four-byte team pointers, alphabetical by city (Anaheim = 0 ... Winnipeg = 25, All Stars East, West).
- Team block starts with two-byte offsets: +0 players, +2 palette, +4 name strings, +6 lines.
- Players: two-byte length (name length + 2), name, one byte jersey number as decimal digits ($88 = 88), 7 bytes
  of ratings. Goalies first. The list ends at a length that is not 3-40.
- Name strings use the same length-prefixed form: city, abbreviation, nickname, arena.
- Lines: 8 lines of 8 bytes: G, LD, RD, LW, C, RW, extra attacker, 0. Roster numbers, 1-based.

Team stat blocks are $364 bytes apart ($C6xx for Home, $CAxx for Away).

## How this was established

- One 4-minute capture, 1 human (Home, Montreal) vs CPU (Away, Los Angeles). Home attacks up in periods 1 and 3.
- A second 4-minute capture (`captures/capture2_away`), 1 human as Away (Philadelphia) vs CPU Home (Detroit), all in
  period 1: the controlled-skater marker appeared only on records 6-11, Away's three goals raised $CA3E with the puck
  at the -Y net, and Home's goal raised $C6DA at the +Y net. So the slots follow Home/Away, not human/CPU.
- That game used 20-minute periods (clock starts at 1200); the first capture used a shorter setting.
- The game clock runs at 2.5x real time while it is running: both captures measure a median of 401 ms per game
  second (24 frames at 60 fps), matching what the user's community has found. It stops during stoppages.
- Orientation: Home's period-1 goal was at the +Y net and its period-2 goal at the -Y end.
- Facing and the controlled-skater marker: the user spun the controlled skater clockwise, then counterclockwise;
  +$55 counted up, then down, on the one record carrying the +$62 marker.

Outside sources, both partly unreliable:
- https://www.stableretro.com/nhl-94-ram-map (stable-retro project; has duplicate and conflicting entries).
- A code snippet from community member smozoma treating $B773/$B775 as puck speed bytes and mentioning $B7E6/$B7EA.
  In RetroArch's byte order those single bytes are the low halves of the speed words at $B772/$B774.

## Team and player stats

Each team has a stat block of $364 bytes, cleared before a game (`CLEAR` in the editor's hacks.ts): Home at $C6CE,
Away at $CA32. Decoded from `capture5_league30` and checked: every player's goals add up to the score, each goalie's
shots against equal the other team's shots, per-player checks sum to the team's checks, ice time equals game time.

| Offset | Size | Field |
|---|---|---|
| +$00 | word | Shots |
| +$02 / +$04 | word | Power-play goals / power plays |
| +$06 / +$08 | word | Penalties / penalty minutes |
| +$0A | word | Attack-zone time, game seconds |
| +$0C | word | Goals |
| +$0E | word | Faceoffs won |
| +$10 | word | Body checks (the editor's checks hack increments it) |
| +$12 / +$14 | word | Passes tried / passes completed. The game does not count a pass that becomes a one-timer as completed; at the user's request the viewer adds one-timer attempts (+$35C) to completed passes, capped at passes tried |
| +$16 | word | 0-2, cycles with line changes (probably the forward line on the ice) |
| +$26 | byte | $FF while this team has a delayed penalty coming: set the moment the other side fouls, cleared when play resumes after the whistle. Also set for a foul that earns a penalty shot |
| +$32 + 2i | byte | Energy of roster place i, 16 = fresh; reset at intermissions |
| +$66 + 2i | word | Penalty: $FFxx = none. Otherwise high byte $20 = called with play still going (delayed), $00 = serving; low byte = seconds left (120 for a minor). How a 5-minute major fits a byte is untested |
| +$9A | bytes | The team's penalty queue: 2 x roster index per penalized player, ended by $FF |
| +$B4 + i | byte | Goals; for a goalie, goals against |
| +$CE + i | byte | Assists (goalies can have them) |
| +$E8 + i | byte | Shots; for a goalie, shots against |
| +$102 + i | byte | Penalty minutes in the original game; checks in ROMs with smozROM's bodycheck hack (ROM $12302 = 4E71 4E71 instead of D532 0000). The converter tells them apart |
| +$11C + i | byte | In the original game: checks THROWN (its team sums equal the team's checks, +$10, and the player is mid-check when it rises; it was shown as "hits taken" until 2026-10-15). In ROMs with the bodycheck hack: hits taken (checks thrown are then at +$102). `find_hits` rebuilds both sides of every hit |
| +$136 + 2i | word | Ice time, game seconds |
| +$343 + 2p / +$34B + 2p | byte | Goals / shots in period p (0-based) |
| +$358 / +$35A | word | Breakaways tried / breakaway goals. The game counts a breakaway (and dings) when the puck carrier crosses the offensive blue line ahead of every defender (the user's description; Fedorov's two in `capture5_league30` fit it exactly). The viewer tags the moment the count goes up |
| +$35C / +$35E | word | One-timers tried / one-timer goals (the two goals whose scorer never had the puck; also Bellows' one-timer in `capture1`) |
| +$356 | word | Shorthanded goals |
| +$360 / +$362 | word | Penalty shots tried / penalty-shot goals (confirmed by the user's save-state parser; Boston's went to 1 in `capture3_bos_la` at 2nd period 3:54, six seconds after a Boston breakaway) |

Power-play, penalty and shorthanded offsets come from the user's old save-state parser (`reference/genesis_savestate_stats.txt`;
save-state offset = work RAM address + $10, low byte of each word), which also matches everything decoded here.
Not yet identified: +$18-$1D, +$2B-$30.

## Penalties

- Penalty summary at $C5DC: a word giving the bytes used, then 4 bytes per penalty in the order called: a word
  (period << 14 | seconds into the period), a byte (team: $80 = Away, | rule code), a byte (roster index).
  Penalty-shot fouls do not appear in it.
- Rule code = 2 x rule number in the ROM's rule-message table at $18E0C (the editor's rulesOffset): word N is the
  offset of rule N from $18E0C; each rule is two bytes (the second is the minutes; $FF on rules 23-30, which repeat
  penalty names and are probably the penalty-shot versions) then a length-prefixed name. Codes seen: $12 and $1A
  Roughing, $20 Tripping.
- The penalized player's record goes to role $FF at (-240, 0) while he serves.
- The moment of the foul: the summary entry and the player's penalty word are only written after the whistle,
  but the fouled team's +$26 flag goes up at the foul (Bourque's check on Gretzky in `capture3_bos_la`: flag at
  177.88 s, whistle 182.31 s, summary 185.71 s). The converter matches each penalty to the flag that was up when
  it was listed and stores the flag's frame as `called`. A flag with no penalty listed, followed by the team's
  penalty-shot count going up, is a penalty shot awarded (Boston's at 206.17 s, shot at 211.11 s).
- The viewer draws serving players in the rink picture's penalty boxes on the far side (Home lower at about
  (147, -30), Away upper at about (147, 58), per the user), using the game's standing,
  facing-the-ice frame (31, or 11 mirrored for right-handed shooters).
- Penalty lengths come from the ROM: the 46 thirty-team league ROMs in the ROM folder have 1-minute minors.
- Checked on `capture1` (Los Angeles: Blake roughing before the recording began, Robitaille tripping; Montreal
  2 power-play goals on 2) and `capture3_bos_la` (Bourque roughing, Los Angeles 1 power-play goal on 1). The
  viewer shows a callout when a penalty is called, a penalty box with delayed / clock, and a running summary.

Shots are the game's own shots-on-goal counters, not button presses. Shooting % = goals / shots, so it can pass
100% (a goal without a counted shot) or be undefined; the viewer shows a dash for no shots.

Away's block runs to $CD95, past fast.bin's old end of $CBFF. The recorder now keeps $C400-$CDFF; for older
captures the converter reads anything fast.bin lacks from full.bin (once a second).

## Things needed from the user

`docs/NEEDS_FROM_YOU.md` (the user asked for it to be kept, 2026-10-18): recordings to make, things to note when they
happen, questions for the user or league, checks on the user's box-score database, replays to review. Add to it
whenever a question can only be settled by the user; strike items off as they're answered.

## Intermission highlights and split recordings (2026-10-21)

Between periods the Genesis sometimes shows highlights of ANOTHER game (the user); during a long BOS-NYI intermission
the recording held 26 s of a WSH-FLA game at 5-4 in P3 (team ids 24 / 8 instead of 1 / 13), which made the helper
rename it WSH-FLA and, when the real game came back at P2 with a lower period, split it as a "new game". Fixed:
nhl94_helper Recording.step: once live play is recorded, samples with other teams are not recorded or compared; they
end the recording only as a new game's opening faceoff (P1, 0-0, clock >= 290); teams update only before the first
sample. genesis MatchReader._sample: game_teams = the first on-ice sample's team ids; later samples with other teams
are left out (only ANA-ATL's one misread sample and explore1_menus are affected elsewhere). Tested by feeding the two
pieces through Recording.step (tests/helper_highlights.py): one recording, BOS-NYI, 5-4. tools/merge_recordings.py
joins split pieces (times shifted end to end) and converts: game 1 is now Documents 2026-10-21_1054_BOS-NYI (the
fragments' match files removed from the list; their captures kept). The user's BOS-NYI playoff series is 1137 NYI 4-2,
1147 NYI 6-3, 1156 BOS 2-3 NYI (project matches/: the helper ran from Python that day); the 1054 / 1121 Boston wins
were left out of the series for technical reasons.

## League ROM settings and hot / cold on the card (2026-10-17)

From the NOSE4Web editor (github.com/nhl94dotcom/NOSE4Web, src/core/hacks.ts; the user asked to use what it knows):
`tools/systems/genesis_settings.py` reads a Genesis ROM's gameplay settings the way the editor recognises them
(rating scale, hot / cold in play and in Edit Lines, weight fix, C-then-B fix, bodycheck stats, second assist,
plus-minus, three stars, base weight, goalie hold / range / whistle line, stamina, energy drain / recovery, speed burst,
turn rate, real-time clock), only for product code GM T-50656 ROMs (the original game and the 30-team ROMs);
`python tools/systems/genesis_settings.py <roms>` lists what differs from the original. Over the 65 Genesis ROMs in the
user's ROM folder: all NHL '94-based ones are 0-6, original clock, no weight fix; the CDL / IDL / DPWM / RGDL league ROMs
show hot / cold as played in Edit Lines, widen the goalie range (40 / 224), keep checks per player (the earlier hack),
fix the second assist, keep plus-minus and use the fuller three stars; WJ2025 fixes hot / cold per rating and the
C-then-B check; Plablegs04 and 2on2 turn hot / cold off. The converter (genesis.read_match) stores them as
`romSettings`; read_teams uses the editor's average-based overall for 0-15 ROMs (none seen). Hot / cold as played, per
roster entry: Genesis `hc` (one value, int(byte 0 / 3), the original code) or `hcr` (per rating in roster order, ROMs
with the per-rating fix), none when the ROM turns them off (genesis.add_hot_cold, team block +$1A2, read mid-game);
SNES `hcs` (per rating: byte >> 2, or "max" for a negative byte, snes.add_hot_cold, $1A12, read while HotColdRaised
$19CE is 0). Viewer: the card's "Hot / cold (as played)", the ROM's base weight and rating scale for the weight and
bars, a tooltip on every rating saying what it does in play (RATING_HELP), the skater rating once labelled Roughness
now "Shoot bias" (the pass / shoot bias), and the help's "This game's ROM" (fillRomSettings). Checked in headless Edge:
BOS-PIT Oates "cold: -3 on every rating", TOR-CHI Gilmour "maxed: Speed, Off. aware, Stick hand., Aggression ...",
the CDL game's settings list. All recordings re-converted (nothing else changed; full_buttons had not been re-converted
since the rollback filter), the exe rebuilt, the Documents games re-converted, the samples remade.

## Not yet known

- Animations still unidentified: the individual goalie save types, what separates $07FC from $092E, and the
  unknown rows in the table. A penalty shot was captured (`capture3_bos_la`, Boston, 2nd 3:54: Oates' slapshot with
  the clock stopped, saved, not counted as a shot on goal); the shot list does not tag it yet. No penalty-shot goal
  has been captured.
- The `full_buttons` capture's labelled taps: A at 5.6-12.1 s, B at 13.9-19.7 s, C at 21.1-26.8 s (the C taps came
  while the skater was down, then while controlling the goalie).
- Whether capture works during netplay, and whether a netplay spectator can do the capturing.
- Injuries (2026-10-16): `find_injuries`, from each player's availability code: when not serving a penalty, the low
  byte of his penalty word (team block +$66 + 2i; in the stat snapshots' 8th value per player) is $FE on the bench,
  $FF on the ice and $FD out (the SNES box state $1852 uses the same codes). Out for the period clears at the period's
  end; out for the game never does. Found in `2026-10-16_1314_BOS-PIT` (the user's first .exe game, single player,
  copied here from Documents/NHL94 Viewer): Jagr hurt by Neely's shoulder check (also a penalty) at P3 4:01, $FD
  until the horn (527.9 s), then $FE with everyone - out for the period, as the user confirmed; the computer simply
  did not send him back, so coming back on the ice says nothing (a first version that judged by that got it wrong).
  The moment and cause come from the injury animation (Genesis ACTIONS "injury": $1AF4 injury1, $145C injuryfall)
  in the 3 s before the code turned $FD, and the opponent's hit in the 1.5 s before. Also found: capture1's
  Desjardins, out through period 1 from before the recording began (`atStart`: shown on his card, not as a banner or
  highlight, not counted). The disassembly's InjCntDown ($C3EC) only counts game seconds from the last injury.
  Shown as a banner, a highlight, the card's "Injured" (until it clears), and the season's INJ column (injured and
  injuries caused). No SNES recording has an injury yet.
- Most team stat words (passing, checks, faceoffs, attack-zone time) are unverified.

## Files

- `tools/nhl94_ram.ps1` - prints the puck record, clock, scores and shots twice a second.
- `tools/nhl94_find_objects.ps1` - scans RAM for records that move the way their speed words say.
- `tools/nhl94_record.ps1` - records RAM to `fast.bin` (about 60 Hz: 8-byte ms timestamp, $B000-$BFFF, $C400-$CDFF)
  and `full.bin` (1 Hz: 8-byte ms timestamp, all 64 KB), plus `capture.json` listing fast.bin's blocks. Captures
  made before `capture.json` existed (`capture1`, `capture2_away`) hold only $B000-$B8FF, so they have no buttons.
- `tools/nhl94_record_full.ps1` - records all 64 KB at about 50 Hz to `ram.bin` (about 3 MB per second), for
  finding where something lives. The converter accepts these captures too.
- `tools/export_match.py` - converts a capture's `fast.bin` into `matches/<name>.js` (drops repeated samples).
- `tools/systems/` - one module per game system (genesis.py, snes.py) plus common.py and process.py; see "SNES version".
- `rink_gens.js` - the rink picture as a data URL (from `tools/embed_rink.py`), so clips can be saved.
- `viewer.html` - the top-down viewer; one page, plus `rink_gens.png` beside it for the ice and
  `sprites/<ROM crc32>.js` for the game sprites (on unless turned off; `?sprites` in the address forces them on).
- `tools/extract_sprites.py` - builds a ROM's sprite library by hand (`--rom`); the converter normally does it.
- `tools/png_read.py` - small PNG reader used to measure the rink picture (no image library is installed).
- `matches/*.js` - the captures as match files.
- `captures/capture3_bos_la/` - 6 minutes, Boston (Home, human) vs Los Angeles, 5-minute periods, line changes on,
  into the second period; has buttons. The source of the "Pressed" animation rows and of the slot-shuffling finding.
- `captures/full_buttons/` - 75 s of full RAM (237 MB) with the labelled button taps; continues the Detroit vs
  Philadelphia game. `analysis/find_buttons.py` is the search that was run on it.
- `analysis/analyze1.py` .. `analyze5.py` - one-off passes over a capture (stat timeline, pointer search, facing search,
  marker search, turn detection, possession search in `analyze6.py`). Each takes the capture folder as its first
  argument. `analyze5.py` prints a lot.
- `captures/capture1/` - the 4-minute capture described above (paused for its first 48 seconds).

The PowerShell scripts were run with `Invoke-Expression (Get-Content -Raw <script>)`; all of them only read from the emulator.

## Full review (2026-10-21)

A review of everything so far, with checks that stay in tests/ (see CLAUDE.md, After changes). Every recording in both
game folders re-converted identically to its match file before the fixes, and every match now passes
tests/check_matches.py (goals, per-player goals, shots on goal, checks, faceoffs against the game's own counts; the
pass count's known small gap is shown, not failed). Fixed:
- SNES: the clock-stopped flag (which hides the puck) can flicker at a drop, which made duplicate faceoffs in three games
  (2026-10-16_1528_TOR-CHI, 2026-10-19_2246_TOR-NYI, 2026-10-20_2138_CGY-TOR): `steady_puck`. The faceoff winner is
  now the first faceoff-count rise up to the next stoppage or 6 s after the drop (a scramble took 7.8 s; a quick whistle
  had the count 2.4 s after the drop).
- A check by a player whose position read $FF (mid line change; Tkachuk, 2026-10-18_2149_BOS-WPG) had no hit.
- Passes are matched to the game's passes-tried count in time order (no total changed).
- The helper flushes its recording every 2 s always (not only when broadcasting), marks each recording `unconverted`
  until it is converted and converts any left so at the next start (the helper closed mid-game; tested with the exe);
  the converter reads a cut-off gzip up to the cut; the new-game test no longer assumes 5-minute periods; a bad
  Content-Length is refused; a game-file request for a missing game answers with an error the page shows.
- Live broadcast: begin() waits for the last game's update loop; the viewer's deserve-to-win treats a live game as
  over only when the broadcast says final, and its cached clock lengths follow the growing match.
- share_season.py no longer puts roms/names_scan.json in the share (it lists every ROM file's full path, the Windows
  user name included); the two league shares in Documents were remade without it. It also refuses to delete an output
  folder that is not empty and not an earlier share.
- Season page: the PTS help (no point for an overtime loss) and five headings without help.
- analysis/matchup_review.py read the summaries' high-danger and rebound lists crossed (not quoted in any answer);
  match_report.py: played periods only, blocked shots out of the score-state xG, Genesis-only sections say so on SNES
  games; bos_nyi_deep.py used a piece of the joined game; snes_runaway_study.py had no default recordings.
Checked and fine: the viewer's xG, SNES xG and deserve-to-win ports against the Python (tests/xg_parity.py); 192 viewer
loads over every match with no script error (tests/viewer_smoke.py); every team-stat break-down adds up
(tests/viewer_stat_sums.py; recordings that began mid-game differ by design); every team-stat row and season heading
has help; the season page's tabs; the repository and its whole history hold no bucket, profile, home path or key.
The disassemblies' new commits (Genesis 150+, SNES 100+ since our copies) are names and comments; none changes a
mechanics finding, and three new comments disagree with their code (NEEDS_FROM_YOU).
