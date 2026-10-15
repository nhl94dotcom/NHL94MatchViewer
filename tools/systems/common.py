"""What every game system shares: where the project's files live, and the shape of the match file's stats.

A system module (genesis.py, snes.py) turns its own memory layout into these; everything after that (the analysis in
export_match.py, the viewer) is the same whatever the game ran on.
"""
import os
from pathlib import Path

# Where games, replays, sprites and settings live: the project folder, or NHL94_HOME (the packaged helper sets it to
# a folder in Documents, since a single .exe cannot write beside its own files).
ROOT = Path(os.environ["NHL94_HOME"]) if os.environ.get("NHL94_HOME") else Path(__file__).resolve().parent.parent.parent
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"
PLAYERS = 12  # six skaters a side, records 0-5 Home and 6-11 Away

# A stat snapshot in the match file starts with these team values, in this order (the viewer reads them by
# position), then 8 values per roster place: goals, assists, shots, checks or penalty minutes, the second check byte
# (see find_hits), ice time, energy, penalty word.
STAT_FIELDS = ("shots", "goals", "faceoffs", "checks", "passTried", "passMade", "attackZone",
               "breakTried", "breakGoals", "oneTimerTried", "oneTimerGoals", "psTried", "psGoals",
               "ppGoals", "ppTries", "penalties", "pim", "shGoals")

# What the analysis needs to know about the players' animations, by name. Each system maps these to its own
# animation words (four hex digits, as the match file's `anim` stores them).
ACTIONS = ("shoot", "pass", "goalie_pass", "poke", "hook", "lunge", "down", "dive", "goalie_save")


def overall(attrs, goalie):
    """The overall rating the game shows on its roster screens (formula from the NOSE editor)."""
    weights = [2.25, 0, 0, 2.25, 2.25, 0, 0, 0, 0, 0.5, 0.5, 0.5, 0.5] if goalie else [1, 1.5, 1.5, 1, 0.5, 1, 0, 1.5, 1, 0.5, 0, 0.5, 0]
    rating = 0
    for weight, value in zip(weights, attrs[1:]):
        rating += value * weight
        if goalie and weight == 2.25 and value % 2:  # the game rounds these down to the nearest half
            rating -= 0.25
    return int(rating + max(0, rating - 25) + 25)
