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
sets another port. The helper claims its port exclusively (Windows otherwise let a second helper listen on 9494 too,
and the page reached either), so a second copy says it is already running. It listens on ::1 as well as 127.0.0.1: Windows resolves
"localhost" to ::1 first, and with only 127.0.0.1 open each request waited about 2 s for the fallback, and the user
often could not connect at all. Not yet tried on another computer; an
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
   That flip only applies to the original picture. By default (toolbar "Overhead", remembered) the viewer instead
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
5. Save game file (footer): writes one self-contained page to send to someone - this page's own source (kept as
   `PAGE_SOURCE` when it loads) with the rink picture, the bench masks, and the match and sprite library gzipped and
   base64'd inside (`window.NHL94_PACKED`, unpacked with DecompressionStream on opening). `capture6_netplay_bos_stl`
   makes a 5.2 MB file that opens on its own from any folder with everything working (sprites, overhead rink, maps,
   stats, clips).
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
with a trimmed-down menu configuration. The user's install: `C:\Users\USER\RetroArch-1.17-Win64`.
ROM in use: NHL '94, crc32 `9438f5dd`.

## SNES version

The user wants a SNES version too. The community plays it in RetroArch with the Snes9x core
(`cores\snes9x_libretro.dll`); ROMs are in `C:\Users\USER\RetroArch-1.17-Win64\ROMs\SNES`: `NHL94.smc` (the base
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
  Not known yet: puck height, the hook.

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
shots, stats, penalties, both teams' controlled skaters (+$62 set on one record per team almost throughout), no
sign of netplay's rollbacks in positions or the clock. Periods read 0-2 for the three periods, then 3 and 4 at the
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

The ROM is at `C:\Users\USER\RetroArch-1.17-Win64\ROMs\Genesis\nhl94.bin` (the same folder has edited variants;
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
Special" (a goal tag, like one-timer). Genesis games only: the SNES goalie saves differently and is not pushed back
by a wrist shot (the user). `eaDive`: the goalie went into his dive ($02F4) within 2 s after the save, as Genesis
goalies often do on an EA Special (diving for a puck he is nowhere near, out of the play for a couple of seconds); a
detail, not a condition (none of the recordings' attempts has one). Only a person's skater makes an attempt (the
user: the computer never tries one): the shooter carried the controlled-skater marker (`ctrl`) at the release or up
to 6 samples before; the rebound may be anyone's. Always a forehand (the user): the shooter's last shooting animation
before the release is the forehand $07FC (genesis ACTIONS "forehand"; $092E is the backhand), from his forehand side
as the attacker sees it (right-handed, drawn mirrored, from the left; left-handed from the right); and not a
follow-up (no attempt by his team in the 3 s before). The user reviewed the nine attempts the rules found before the
last three: one real (capture3_bos_la P2 3:59, Oates, "not the best example but it meets the criteria"), the rest
rebound put-backs (CGY-BOS P2 4:42 and 2:22, capture6 P1 2:36), breakaway or skate-in dekes and shots (capture1 P1
2:57, capture6 P1 1:17, P1 4:33, P2 0:26) and a backhand from in front (capture6 P2 2:27); with the three rules only
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

## Not yet known

- Animations still unidentified: the individual goalie save types, what separates $07FC from $092E, and the
  unknown rows in the table. A penalty shot was captured (`capture3_bos_la`, Boston, 2nd 3:54: Oates' slapshot with
  the clock stopped, saved, not counted as a shot on goal); the shot list does not tag it yet. No penalty-shot goal
  has been captured.
- The `full_buttons` capture's labelled taps: A at 5.6-12.1 s, B at 13.9-19.7 s, C at 21.1-26.8 s (the C taps came
  while the skater was down, then while controlling the goalie).
- Whether capture works during netplay, and whether a netplay spectator can do the capturing.
- Injuries (2026-10-16): they happen now and then, for the rest of the period or the game; no recording has one
  yet. The user will record Genesis and SNES games with injuries (the disassemblies name injury animations: Genesis
  $145C injuryfall, $1AF4 injury1).
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
