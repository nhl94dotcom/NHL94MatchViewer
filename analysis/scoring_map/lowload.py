"""Gentle mode for long runs, so the computer stays cool and quiet and anything the user is doing comes first:
- WORKERS processes at most (default 2; NHL94_SMAP_WORKERS overrides it);
- each at idle priority (gentle());
- each resting between bursts of work (breathe(), called in the work loops): DUTY is the share of time spent working
  (default 0.5: rest as long as it worked; NHL94_SMAP_DUTY overrides it, 1 = no rests).
The fan follows how much the processor works in total, so WORKERS x DUTY is the lever: the default is about one core's
worth, a few percent of a 32-thread machine. Run times grow in proportion (a 30-worker hour is about 30 hours)."""
import ctypes
import os
import sys
import time

WORKERS = int(os.environ.get("NHL94_SMAP_WORKERS") or 2)
DUTY = float(os.environ.get("NHL94_SMAP_DUTY") or 0.5)
IDLE = 0x40
_since = [time.perf_counter()]


def gentle():
    """Lower this process's priority to idle (Windows; elsewhere the lowest nice)."""
    if sys.platform == "win32":
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), IDLE)
    else:
        os.nice(19)


def breathe():
    """After each quarter second or more of work, rest so that work is DUTY of the time."""
    busy = time.perf_counter() - _since[0]
    if busy >= 0.25 and DUTY < 1:
        time.sleep(busy * (1 - DUTY) / DUTY)
        _since[0] = time.perf_counter()
