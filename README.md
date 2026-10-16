# NHL '94 Match Viewer

Records NHL '94 games played in RetroArch and replays them from above in the browser: the Sega Genesis version
(Genesis Plus GX core) and the Super Nintendo version (Snes9x core).

The replay has the game's sprites, a rotatable and zoomable rink, a follow camera, team and player stats, shot, heat,
turnover and pass maps, a goalie report, clips (video or GIF) and single-file game pages to share.

Written in Python and JavaScript. The viewer runs in any browser, and shared game files are single HTML pages that
open on any system, phones included. The converter is plain Python with no extra libraries. Only the live recorder
is Windows-only for now, because it reads the game's memory out of RetroArch with a Windows call (read only);
Mac and Linux recording is being worked on.

To look around without installing anything, open a sample game file from the
[Releases](https://github.com/nhl94dotcom/NHL94MatchViewer/releases) page in your browser.

## Use it

- **With Python 3**: double-click `NHL94 Helper.bat` and leave its window open while you play. Games are listed at
  http://localhost:9494/helper.html. Run `python tools/embed_rink.py` once first, to make `rink_gens.js`.
- **Without Python**: build `dist\NHL94 Helper.exe` with `tools\build_helper.bat` (needs
  `python -m pip install pyinstaller`). It also writes `dist\NHL94 Helper.zip`, the exe with
  `tools/tester_readme.txt` as "Read me first.txt", which is what to hand to someone else.

## Not in this repository

- Recordings (`captures/`), converted games (`matches/`) and game files (`shared/`): large, and personal to whoever played.
- ROMs, and the sprites extracted from them (`roms/`, `sprites/`): the helper copies the ROM out of the emulator and
  builds the sprites from it on each player's own computer.

## More

`CLAUDE.md` is the detailed record: how the game's memory is laid out, the ROM formats, how each stat is worked out
and how it was checked.
