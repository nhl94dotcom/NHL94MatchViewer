NHL '94 Helper - read me first
==============================

The helper records your NHL '94 games in RetroArch and lets you replay them from above with stats, shot maps
and more. Thank you for trying it out.

WHAT YOU NEED
- Windows 10 or 11 (64-bit).
- RetroArch 1.17 (64-bit) with the Genesis Plus GX core: the league's usual setup.
- Nothing else. No Python or other installs needed. Any NHL '94 ROM works, league ROMs included
  (NHL '95-based ROMs do not).

SETTING UP
1. Unzip this folder anywhere, for example onto your Desktop.
2. Double-click "NHL94 Helper.exe".
   - Windows may say "Windows protected your PC", because the program is new and not signed.
     Click "More info", then "Run anyway".
   - Your antivirus may object, because the helper reads RetroArch's memory to see the game.
     It only reads, never changes anything. If it is blocked or deleted, please let me know what the antivirus said.
3. A black window opens and your browser opens the games page (http://localhost:9494/helper.html).
   Leave the black window open while you play. Close it when you are done.

PLAYING
4. Start RetroArch and play a game of NHL '94 as you normally would: against the computer or on netplay.
   Start the helper BEFORE the game starts. It begins recording at the opening faceoff.
   Pauses and instant replays are left out automatically.
5. At the final horn, the helper finishes the recording. After a few seconds the game appears in the list
   on the games page.
6. Click "Watch" to replay it. Try the Map menu (shot map, heat map, passes...), the team stats, and pointing at
   players in the lineups. "Make game file" creates a single file you can send to anyone; it opens in any browser.

WHERE THINGS ARE
- Everything is kept in your Documents folder, in "NHL94 Viewer". Nothing is uploaded anywhere, and the games
  page can only be opened from your own computer.
- To remove it all, delete "NHL94 Helper.exe" and the "Documents\NHL94 Viewer" folder.

WHAT TO SEND BACK
Please send:
- The file Documents\NHL94 Viewer\helper_log.txt (it records what the black window showed).
- Whether Windows or your antivirus complained, and what it said.
- Whether the recording started and stopped at the right times.
- Whether the replay looked right: players, score, and stats compared with the game's own stats screen.
- Screenshots of anything that looked wrong, with the period and time on the clock.
If a game went wrong, please also zip and send that game's folder from Documents\NHL94 Viewer\captures
(about 15-20 MB per game).
