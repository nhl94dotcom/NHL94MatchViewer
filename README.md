# NHL '94 Match Viewer

Records NHL '94 games played in RetroArch and replays them from above in the browser: the Sega Genesis version
(Genesis Plus GX core) and the Super Nintendo version (Snes9x core).

The replay has the game's sprites, a rotatable and zoomable rink, a follow camera, team and player stats, shot, heat,
turnover and pass maps, a goalie report, clips (video or GIF) and single-file game pages to share. A season page
totals any set of games: standings, skater and goalie stats, team stats and head-to-head records.

Written in Python and JavaScript. The viewer runs in any browser, and shared game files are single HTML pages that
open on any system, phones included. The converter is plain Python with no extra libraries. Only the live recorder
is Windows-only for now, because it reads the game's memory out of RetroArch with a Windows call (read only);
Mac and Linux recording is being worked on.

## Try it

The [`samples`](samples) folder has three recorded games as single-file game pages. Download one (on GitHub, open it
and use "Download raw file") and double-click it: it opens in your browser with nothing to install.

- `Genesis_Calgary_6-5_Boston_OT.html`: a Genesis game that went to overtime, recorded by the helper.
- `Genesis_Boston_6-3_St_Louis_netplay.html`: an online Genesis game with a person on each team.
- `SNES_Toronto_1-5_Pittsburgh.html`: an online SNES game, with two penalty shots.

Things to try: Play, the Map menu (shot map, heat maps, goalie report), Highlights (three stars and a highlight
reel), Game flow, and pointing at a player in the lineups for his card.

## Use it

- **With Python 3**: double-click `NHL94 Helper.bat` and leave its window open while you play. Games are listed at
  http://localhost:9494/helper.html. Run `python tools/embed_rink.py` once first, to make `rink_gens.js`. Games are
  kept in `Documents\NHL94 Viewer`, the same folder the exe uses (`python tools/nhl94_helper.py` on its own keeps them
  in the project folder, for testing).
- **Without Python**: build `dist\NHL94 Helper.exe` with `tools\build_helper.bat` (needs
  `python -m pip install pyinstaller`). It also writes `dist\NHL94 Helper.zip`, the exe with
  `tools/tester_readme.txt` as "Read me first.txt", which is what to hand to someone else.

## Not in this repository

- Recordings (`captures/`), converted games (`matches/`) and game files (`shared/`): large, and personal to whoever played.
- ROMs, and the sprites extracted from them (`roms/`, `sprites/`): the helper copies the ROM out of the emulator and
  builds the sprites from it on each player's own computer. (The sample games carry their ROM's sprites and sounds
  inside, so they look and sound as the game does.)

## More

How NHL '94 really plays, read from the games' code and checked against recorded games (ratings, saves, checks,
penalties, faceoffs, the computer players and the bugs), one document per system:
[Genesis](docs/GENESIS_MECHANICS.md) and [SNES](docs/SNES_MECHANICS.md). The player's versions (how to read the ratings
screen, how to pick a lineup, what works on the ice): [Genesis guide](docs/GENESIS_GUIDE.md) and
[SNES guide](docs/SNES_GUIDE.md). A study of the recorded games' shooting and goaltending, up and down the screen and
home and away: [shooting study](docs/SHOOTING_STUDY.md). Shots played in the real game, headless, to map where a set
goalie can be beaten and show how each kind of goal goes in: [scoring maps](docs/SCORING_MAP.md).

`docs/PROJECT_NOTES.md` is the detailed record: how the game's memory is laid out, the ROM formats, how each stat is worked out
and how it was checked.
