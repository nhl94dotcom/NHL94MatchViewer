# The video reader's working scripts

Moved here from the scoring-map work folder (2026-11-21). They read a Genesis game from a video of the session alone
(the renderer inverted: `../inverse.py`, `../camera_track.py`, `../rink_render.py`, `../hud_read.py`), and score the read
against the game's recording. History and results: `docs/VIEWER_NOTES.md` (the video reader sections).

| Script | Does |
|---|---|
| `track_play.py VIDEO TIMELINE ROM OUT.npz [FIRST COUNT]` | the every-frame camera track of the live play (needs `tools/video_sync.py`'s timeline) |
| `track_test.py` | the reader's set-up (video, ROM, camera, the transitions learnt from other games) and the per-frame read; at the start it measures the rink line-up (`RINK_DX`) and warns when nothing lines up |
| `run_reader.py FIRST COUNT OUT.json` | the reader over a stretch of video frames, one gentle worker |
| `join_reads.py A.json B.json ... OUT.json` | stretches read by separate workers joined (track ids kept apart) |
| `pseudo_run_any.py READ.json` | the read turned into a match and its events compared with the recording's |
| `ctrl_acc_any.py READ.json` | how often the person's skater was read in the right place |

Settings (environment): `NHL94_INV_VIDEO`, `NHL94_INV_ROM`, `NHL94_INV_CAM` (from track_play), `NHL94_INV_TIMELINE`,
`NHL94_INV_STATIC`, `NHL94_INV_TRANS_GAMES` (the games the transitions are learnt from, comma-separated),
`NHL94_INV_MAPS`, `TEST_GAME` (the timeline's game read: never learnt from), `NHL94_INV_DX` (the rink line-up, to
override the measurement). Unset, they default to the BOS-CHI session (2026-11-13). Work files (camera tracks, HUD
templates, masks, reads) stay in `%USERPROFILE%\NHL94_scoring_map\runs\vision`.

A new session, whole: `video_sync.py` (timeline) -> `track_play.py` (camera) -> `run_reader.py` per half on two
workers -> `join_reads.py` -> `pseudo_run_any.py` and `ctrl_acc_any.py`.
