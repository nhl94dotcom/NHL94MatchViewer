"""Game time, for every duration a report or write-up shows (2026-11-06, the user: durations in game time, not real time;
split-second timings stay in real time, marked as such).

The game clock ticks one game second every 24 frames, 0.40 s of real time, on both systems: the median gap between ticks
in every recorded game is 405 ms (Genesis and SNES alike, our ~60 Hz sampling), the mean 401. So one real second of
play is 2.5 game seconds. The clock stops at whistles; a window measured from the samples' own times runs on through a
stoppage, so the analyses end their windows at whistles or faceoffs where it matters.

Convention: windows and durations of a second or more of real time are given in game seconds (a real window of
5 s is 12.5 game s: the window's length is unchanged, only the label). Split-second timings (button presses, a pass's
lead before a check, a one-timer pass's time in the air, reaction times under a second) stay in real seconds, written
"s (real)"."""

RATE = 2.5          # game seconds per real second of play
NOTE = ("Durations are game seconds (the game clock: 1 game second = 0.4 s of real time, and the clock stops at "
        "whistles); split-second timings are real seconds, marked (real).")


def gsec(ms):
    """Real milliseconds -> game seconds."""
    return ms / 1000 * RATE


def gs(real_s):
    """Real seconds -> game seconds."""
    return real_s * RATE


def window(ms):
    """A window's label: real milliseconds as game seconds, e.g. 5000 -> '12.5 game s', 6000 -> '15 game s'."""
    v = gsec(ms)
    return f"{v:g} game s"
