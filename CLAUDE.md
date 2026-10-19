# NHL '94 match viewer

Goal: capture live game state from NHL '94 (Sega Genesis) running in RetroArch, and replay matches in a viewer
(full-ice top-down first; rotatable views later). A first top-down viewer exists and plays recorded captures;
there is no live view yet.

## Workflow

The easy way: double-click `NHL94 Helper.bat` (runs `python tools/nhl94_helper.py`) and leave its window open while
playing. It waits for RetroArch with NHL '94, records each game from the opening faceoff to the final horn (live play
only: $FFF7 = 0; pauses and instant replays are left out, timeline included), converts it as
`<date>_<time>_<HOME>-<AWAY>`, and lists games at http://localhost:9494/helper.html (bound to this computer only;
it also serves the viewer, so the browser's local-file restrictions do not apply there): Watch, Make game file /
Game file, Delete, and a setting (off by default, saved in `helper_settings.json`) to make a shareable game file after
every game. Recordings are gzipped (`fast.bin.gz`, about 23 KB per second of play; `full.bin.gz`, all of RAM every 10 s for research only - the converter does not use it: converting the CGY-BOS game without it gives an identical match; about 16 MB a game in all) and the ROM is copied
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
- The NHL94SNES disassembly (github.com/Mhopkinsinc/NHL94SNES; the user pointed to it) rebuilds `NHL94.smc` byte for
  byte (same SHA-1), so its addresses hold for the base ROM. `src/ram94snes.asm` names RAM; `docs/name_map.csv`
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
  in the NHL94SNES disassembly's ram94snes.asm; also puckvz $0E01, shadowz $0DFB), now the match file's puck height
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
+$58 word) and every RAM variable in `src/stubinc/ram_addrs.inc` (its `src/ram94.asm` is an old 93 list: wrong
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
  Shown on the player card and the "Passes" map. Faceoffs (`faceoffs`): drop spot, winner (the faceoff count rising
  between the whistle and 6 s after the drop; matches the game exactly in all captures) and zone (Home's view;
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
  2026-10-16_1528_TOR-CHI; no Genesis pass changed). Known gap: in 2026-10-16_1528_TOR-CHI the game counts 56 / 52
  passes tried, the converter matches 55 / 49 (before these changes too). Each bobbled pass carries `bobble` {f, idx, x, y}: the passes map draws
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
  rink: the nets are no longer baked into the rebuilt picture; `drawFlatNet` draws both every frame (in game units,
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
  room, and the seek bar keeps at least 140 px (with a map on it used to be squeezed away).
- Player card (2026-10-17, the user saw values run past the card's right edge): its two stat columns are
  minmax(0, 1fr), so a long value can no longer widen the left column and push the right one out; a stat whose label
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
taken 10%, course changed 8% (470); 6-8 through 94% (35); 17+ over 100% (21). In GENESIS_MECHANICS.md 4.7 and 13.5,
GENESIS_GUIDE.md 6.

The same on the SNES (2026-10-18, NHL94SNES checkpuckcoll / _ccx, puckstick, puckbody, ChkShotStat): collisions only
with puckz < 16; skater stick: puckz < 5, puckvz < $100, within 14 of GetHot, d^2 <= $C4 (/4 while the puck's nopuck
runs); body: circle 8 (d^2 <= $40), puckz >= 8 always, lower only when d^2 & $F == 0; FallDown at speed^2 >= $9000000
and z >= 12, else SPAcatch. puckstick's limit is 10000 + (no shot flag: 700 x Stk) + 3000 when `position,x` is 0 or x
is passReceiverPlayerNum, but x is the puck there (curobj), whose position word reads 0 (707 of 707 samples): every
stick gets the 3000 (corrects "the intended receiver or a goalie" in the earlier bobble note), and a faster puck always
deflects. Shots on goal as on the Genesis (puckgoalie / goalie puckglue call ChkShotStat; a2touchpuck clears $1000;
after a goalie's stick deflection the body box test runs but the flag is gone). The goalie's hot-area height window
(xg_snes RomData.hot): ready none, stick saves about 0-6, glove saves 7-15 (r6), one stick save facing down -2-8 r8
against 2-5 r2 facing up. Recordings (5 SNES games): uncounted high 6/29, middle 15/104, ice 2/14; aim going up high
49% / middle 46% / ice 5%, going down 2% / 88% / 10%; uncounted up 12/70, down 11/77; pass-bys < 5 high: through 81%,
taken 13%, course 7% (291); 5-7 through 6/6; 8-15 hit 5/5. SNES_MECHANICS 4.6, 6.2, 7.5; SNES_GUIDE 6.

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
point for an overtime loss, so PTS is 2 x W + T too (it had counted 1 an OTL), and a game's two teams share 2 points. Recorded games:
Dallas 5-2 Boston 65% / 34% (Dallas finished above its chances), Calgary 6-5 Boston OT 45 / 48, tie 7%; Boston 8 points
against 8.6 deserved.

One-timer study (2026-10-18, analysis/one_timer_study.py, SHOOTING_STUDY.md part 3, GENESIS_GUIDE 7): Genesis 91
one-timers: goalie 10+ off the puck-to-net line at the strike 68% scored, 0-4 off 11%; pass moving the puck 40-90 across
47%, crossing the middle 18%, under 0.5 s in the air 33%; inside 100 units 44%, beyond 10%; xG agrees throughout. SNES 55,
no clear pass effect.

SNES goalie hold (2026-10-18, NHL94SNES puckgoalie): hold when |vx| and |vy| < randoma((2 + shotspd) << 9) + $2000
(shotspd = PkC for goalies), not pflags $1000; else bounce (velocity = offset bytes, y sign set against his Yvel); a
diving goalie lets puckz >= 5 through; save-rating lookups unused. Recordings (102 saves): faster component 17000+ held
at once 4/41, 8192-17000 28/45, under 8192 10/16. SNES_MECHANICS 5.4, SNES_GUIDE 11.1. SNES steals (puckstick .t1):
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
SNES one-timers follow the stick (not affected). GENESIS_MECHANICS 4.4, GENESIS_GUIDE 7. Empty-net chances by aim and distance from each system's scatter rule in
GENESIS_MECHANICS / SNES_MECHANICS 4.2 and the guides' shooting tips; recordings: 5 shots with the goalie far out or
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
Genesis 0-870 / 585. SNES_MECHANICS 4.5, SNES_GUIDE 7.

SNES faceoffs confirmed (2026-10-18, analysis/snes_faceoffs.py): stage = 8 x the (frame, time) pair index of the
centre's current animation (assfaceoffpl SPAnum / 4 + 1, +3 for handed 0, table 0,8,16,0,8,16); winner from the puck's
Yvel after the drop (32 x dirtab + / - $800); 70 draws: home 36 vs 38.7 expected; stage diff -8 / 0 / +8: 20% / 48% / 74%
(model 28 / 53 / 78). doinput passes padnew, so a swing needs a new B press. People's stages 27 / 45 / 28%.

Goalie study (2026-10-18, the user's list; analysis/goalie_study.py; GENESIS_MECHANICS 5.5-5.9, SNES_MECHANICS 5.5-5.7,
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
- Tested: `python tools/live_broadcast.py --test <capture> <folder> --speed N` (a recorded game fed in at N x into a
  growing gzip, uploads written to a folder; served with http.server, NHL94_LIVE_UNZIP since it sends no
  Content-Encoding): 2246 DAL-BOS at 10x, 12 updates, the page joined mid-game and played 11 s behind with all stats;
  snapshot + diffs rebuild the match exactly; final 5-8 equals the real conversion. The helper end to end with the
  fake emulator (scratchpad helper_test_live.py): 6 live updates and the final.

Posts (2026-10-18, the user): the card's "Posts" (his shots with result 'post', live-knowledge aware), season summaries
VERSION 21 (team posts / postsA, skater posts), season page Skaters POST and Team stats POST a game (· against). The
team stats already had Posts. The live launcher sets NHL94_HOME to Documents/NHL94 Viewer and copies the current pages
there first (the Python helper doesn't copy pages; the exe does).

Review of the user's two live test games (2026-10-18_1934_BOS-PIT, 2026-10-18_2006_CHI-LA, both SNES on
NHL94_Classic): shots on goal, goals, checks and faceoffs equal the game's; counted passes 45/50, 45/47, 62/65 (the
known gap). Found and fixed:
- SNES penalty shots were never recorded by the helper: snes.View.on_ice needs each team's on-ice roster places to
  differ, and in a penalty shot the parked players (x = -240) can share one (research capture: 4297 in-game samples
  skipped, both penalty shots). Parked objects are now left out of the test (433 skipped: pre-faceoff moments).
  Replaying snes_2026-10-15_1755 through the helper (scratchpad helper_test_snes_ps.py) now records both penalty
  shots. The puck shows during the shooter's run and hides after the shot (gmclock).
- The two SNES "own goals" (Wesley in BOS-PIT, Steve Smith in CHI-CGY) were those unrecorded penalty-shot goals: a
  defender holding the puck at the whistle before. add_own_goals skips penalty-shot goals and hidden-puck samples.
- Posts: the puck coming out from behind the net past its side read as a post (|y| up to 272). Both readers now
  want |y| <= 268 and the puck not behind the goal line (268) in the half second before: 43 -> 28 posts over all
  recordings, every removal one of those; shots on goal still equal the game's everywhere.
- Goal heights projected above the crossbar (up to 13.9) are capped at 12.9.
- SNES puck frame 406 (a net picture) in the puck's frame word: the viewer shows the puck at rest for any frame
  wider than 12.
Not changed: Stevens' P3 4:52 goal had xG 0.0 (a person in net, emulated as the computer goalie); CHI-LA's 13
"lost it on the goalie" bumps are unreviewed.

## Things needed from the user

`docs/NEEDS_FROM_YOU.md` (the user asked for it to be kept, 2026-10-18): recordings to make, things to note when they
happen, questions for the user or league, checks on the user's box-score database, replays to review. Add to it
whenever a question can only be settled by the user; strike items off as they're answered.

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
Uncounted saves explained in GENESIS_MECHANICS 4.7 (analysis/uncounted_study.py); by direction the recordings show
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
frames add 12-28 hit areas. GENESIS_MECHANICS 5.5 and 6.1, GENESIS_GUIDE 8 and 12.2.

Runaway speed (2026-10-19, the user, Genesis): pfdoff (pflags bit 0, friction >> 9 instead of >> 6) set by asspassrec and
FallDown's boards / bench fall; cleared by asspassrec .exit, puckstick, assnearest insertion, not by assexit (a person
taking over the receiver) or getting up. Bursts (+~6,300) then stack: 2158 BOS-WPG P3 ~1:24 (boards fall, 20,079), 2149
BOS-WPG P2 ~0:22 (taken over mid-pass, 19,413). Flag set 765 times (690 passes, 65 boards falls); a person with it on
> 0.5 s 44 times, runaway only with 2+ bursts. GENESIS_MECHANICS 3.4, GENESIS_GUIDE 5.

## Quirky Events (2026-10-19)

The user asked for the game's oddities in their own team-stats group, "Quirky Events" (viewer fillTeamStats, STAT_HELP,
Help "Quirky events"). export_match `add_quirks` (after add_tapestries; Genesis only): goal kind 'five-hole' (in the second
before the goal the loose puck at height <= 5 passed within FIVE_HOLE_NEAR 7 of the defending goalie's centre while he was
in $021E / $01EC: GENESIS_MECHANICS 5.5's blind stick ring), 'goalie bobble' (the defending goalie held it in a shoulder
save $148E / $14C0 in the 2 s before, nobody else after: 5.3), pass `rocket` (leaving faster than ROCKET_SPEED 26000, not a
pass shot: 6.1), `runaways` [start, end, team, roster index, top] from genesis MatchReader's new `fast` ([frame, record,
speed / 100] for a person's skater with pflags bit 0 over 12000), kept above RUNAWAY_SPEED 15500 (3.4). On-ice tags
"Rocket pass" and "Runaway!", goal tags "through the legs" / "shoulder-save bobble". Found: ANA-ATL goals P1 2:48, 2:11,
P3 2:24 five-hole and P3 4:00 bobble (exactly the user's); runaways 2149 BOS-WPG, 2158 BOS-WPG and a new one in 2219
WPG-BOS (15,900); rocket passes 0-5 a game; no five-hole or bobble goal in any other recording.
SNES side (analysis/snes_runaway_study.py, SNES_MECHANICS 3.3 / 6.1): the same friction-off flag (pflags bit 0, table .22)
exists, set only by asspassrec and cleared by any stick touch (puckstick), the wait ending, assnearest and faceoffs;
FallDown never sets it: 791 stretches in eight games, median 0.3 s, max 2.7 s, fastest 10,156, so no runaways. Pass
lift = distance x 8 (median peak 1.4 at 100-149 units, 3.3 at 200-249); no rocket pass, through-the-legs or bobble
(already in SNES_MECHANICS 5.1 / 6.1).

## Diagrams (2026-10-19)

The user asked for visuals of the mechanics. `tools/make_diagrams.py` draws SVGs into docs/img, to scale from the game's
numbers (white background, so they read on GitHub's light and dark themes): saves_reach (reach 12 / 15 / 18 against the
mouth), through_the_legs_goalie (renamed from through_the_legs.svg so GitHub shows the new version at once; body 13, blade (11, -2.3), the 8-14 ring, the puck a frame at 22,700), aim_points_genesis /
_snes (both attack directions; SNES post band 17-22), shot_scatter (doshot's s by distance for working ShA 0-30, exact
chance), faceoff_timing (the 18-frame swing, average value 176 / (18 + gap), the win table). Placed in GENESIS_GUIDE 4, 6,
12.1, 12.2; GENESIS_MECHANICS 4.1, 4.2, 5.1, 5.5, 9.1; SNES_GUIDE 6; SNES_MECHANICS 4.1. Rerun the script after a number
changes. Second set (the same day): weight_bug (CCStart's knockdown number by weight difference, person 240 wrapping in a
byte vs computer 120), shoulder_bobble (ghighr / ghighl hold points, top vs bottom net), rocket_pass (passtoa0 speed vs
distance at an ideal 15,000), computer_positions (asswingo / asscentero / assdefo boxes by puck zone), rink_feet; in
GENESIS_GUIDE 9.1, 12.1, 8, 14 and both guides' Distances and speeds, GENESIS_MECHANICS 7.2, 5.3, 6.1, 12.2 and both
mechanics' Units. Third set: one_timers (press-to-strike ranges both systems; Genesis scoring by goalie offset, pass
across, distance from SHOOTING_STUDY part 3), faceoff_directions (dirtab x 32 + 2,048 toward the winner's end, the five
random directions), penalty_chances (Genesis 5 / R, R = ((40 - Agr) / 2) x 13, person x 2; SNES 1 / R with the person's
byte wrap, Agr 12 every hit), flip_spots (OneTimerTarget spots, goal-mouth box, over-the-glass strips); in both guides'
7 and penalties sections, GENESIS_GUIDE 4 and 8, GENESIS_MECHANICS 4.8, 6.3, 8, 9.2, SNES_MECHANICS 4.5, 8. Fourth set:
through_the_legs now overlays the game's own frame 480 (the butterfly, $021E) at 0.6 opacity, the blade at its real hot
point (9, -2) from the ANA-ATL goals (`sprite()` reads sprites/<rom>.js here or in Documents; GOALIE_PALETTE is that
game's Atlanta away palette; without a library the diagram draws without it: so a fresh clone can regenerate the
others); empty_net (MECHANICS 4.2 tables, both systems), computer_defence (assdefd / asswingd / asscenterd spots for
three puck positions); in both guides' shooting lists and both mechanics 4.2, GENESIS_GUIDE 14, GENESIS_MECHANICS 12.2. Fifth set: the game's own goalie frames on saves_reach (gready
facing down, 419) and shoulder_bobble (ghighl 667 facing down / 659 facing up; hold points from HotList (+10, +14) and
(-9, +14), replacing the earlier (-10, +15) / (+9, +14)); snes_flip (DumpInTarget spots and Passing scatter) in SNES_GUIDE
8.2 and SNES_MECHANICS 6.3. Sixth set: early_save (the wind-up rule with gstackr frame 454, its body
test 6 to the slide side, reach 18, the seconds-left bit-1 strip, recorded rates) in GENESIS_GUIDE 6 and GENESIS_MECHANICS
5.6; open_net_one_timer (the sightline test and the high-middle aim under the bar, the 4.4 table) in GENESIS_GUIDE 7 and
GENESIS_MECHANICS 4.4. Frames 453 / 465 are the pad stacks' first (upright) frames, 454 / 466 the sprawls (left / right). Seventh set:
puck_meets_skater (frame 1 standing facing up, blade (-4, +20) from HotList; skating with the puck 24-28 ahead; the 22 walk
band, the stick's 14 ring with the part past 22 untested, body 8, the height bands) in GENESIS_GUIDE 8 and GENESIS_MECHANICS
6.2; penalty_shot (the Genesis stages with the code's bugs under them, the SNES retake) in both guides' and both mechanics'
penalty-shot chapters. SNES set (2026-10-19, the user: whatever SNES graphics are missing): snes_saves
(six goalie frames facing down from NHL94_Classic in Toronto's away colours, SNES_PALETTE; body box -11..10; each save
frame's hot circle and height band from xg_snes RomData.hot: ready 546 none, glove 547, stick 606, pad stack 581,
butterfly 732, sprawl 780), snes_shot_scatter (doshot with passspeed = speed / 136, a 15,000 shot), snes_hot_cold (shown
18n +/- floor(3|b| / 4) squashed under 50 vs played: maxed for b < 0), snes_goalie_hold (puckgoalie's hold chance by the
faster component and PkC, recorded rates); in SNES_GUIDE 1.2, 6, 11.1 and SNES_MECHANICS 2.5, 4.2, 5.1, 5.4. sprite()
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
  The season's team is marked in every table. It no longer goes by controller 1 (the summary's `you`): on the Genesis player 1 is
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

## Game mechanics from the disassemblies (2026-10-17)

Read from the commented Genesis disassembly (github.com/abdulahmad/NHL94Genesis: src/crowd94.asm, collide94.asm,
input94.asm, checks94.asm) and the SNES one (Mhopkinsinc/NHL94SNES: src/routines/hockey/setplayer.asm,
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
  HotColdRaised $19CE: the crowd meter reaching 110 dB raises four bytes of each entry by 2 until it drops under 105.
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
  ice (pulled) get puckvzadj ("in-close top shelf"; corrected 2026-10-18 from chaos's forum post, topic 36095): it
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
  counted saves also look like stick deflections (sampling). GENESIS_MECHANICS 4.7.
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
- Penalties (SNES): checkagr R = (20 - Agr) x 16 (Agr = the working value in GGSleft $1443 for skaters: rating byte 7 low
  nibble, hot / cold index 11), doubled for a person with asl.b and halved near the puck with lsr.b, both on the low byte
  only, so they wrap: person ranges by Agr 0-15: 384 352 320 288 256 224 192 160 128 96 64 32 0 224 192 160, i.e. Agr 12
  gives R = 0 and (callers penalise d0 < 1) a penalty at every roll; Agr 9-11 several times the computer's rate (not
  confirmed: people were at 12 for a few dozen samples). SNES codes as in the SNES section. Recordings: 11 of 14 SNES
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
  targets 70), so Passing sets flip accuracy on the SNES. No SNES flip in the recordings yet (the lofted pucks there are
  lifted shots).
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
- What each rating does (SNES; working ratings 0-15, arrays a word per object; NB the array named aggress holds
  Checking and GGSleft holds a skater's Aggression): Weight: acceleration (playeracc: 32 - Wgt + 1.5 x Agl, so a Weight
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
  puckgoalie, then overwritten before use, so unused as on the Genesis. Fighting (fightagg): never read.
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
  (out of the zone if need be), 158 with it in their zone, the goal line with it behind (corrected 2026-10-18);
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
  SPAhook2 $F3D8. snes ACTIONS "hook" = {"f864"} now; SAVE_MOVES corrected from the disassembly's names (e246 stick,
  e2aa pad stack, sprawls e862 / e7d0, butterfly e73e; three had been wrong), with "sprawl" / "butterfly" in the viewer.

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
them: the fix that took the model from 46 to 37.7 expected goals), playeracc (32 - weight / 8 + 1.5 x legstr + 8; dir
steps 6 / 4; vmax (20 + legspd) x 261), vtoa (diagonal when neither part is more than twice the other: VTOA_TABLE; the
exact-angle version picked wrong save moves). The goalies' sprite flip bit $1000 was never set (so hot y is negated);
mirror never set for goalies. Checks: emulated goalie vs recorded at arrival median 0.8 units (100 computer-goalie
shots); geometry with the recorded goalie path: posts 17.6 / 18; final 175 shots: 40.1 xG / 32 goals (264 aim; 35.6
with 268, but log loss 0.27 vs 0.31), GOALIE_SPREAD 2 (0-6 tried). The map tables (ready and save frames, hot areas)
are the same in every NHL '94 SNES ROM in the ROM folder. Viewer: XG_SNES (JS port between "SNES xG model" comments,
checked against Python: largest difference 0.028 at 3,000 tries), XG_SNES_ROM, XG_SNES_GOALIE_STATES (cpu 93, person
30, onetimer 55; regenerate with `python tools/xg_snes.py <rom> matches/<snes games>.js`); the SNES map's one-timer is
a slapshot against the goalies of recorded one-timers. Docs: SNES_MECHANICS 4.7, 5.1-5.3; SNES_GUIDE 11.3.

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
summing now adds numbers only (a null had turned an array into a string). Documented in GENESIS_MECHANICS.md 4.9 and 5.3
(the goalie's movement) and GENESIS_GUIDE.md 12.3. Not yet: the SNES (its goalie is a different box).

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
