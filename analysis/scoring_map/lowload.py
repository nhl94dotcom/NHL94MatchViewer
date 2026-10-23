"""Gentle mode for long runs: few worker processes, each at below-normal priority, so the computer stays quiet and
anything the user is doing comes first. The fan follows how many cores are busy, not the priority, so WORKERS is the
main lever; NHL94_SMAP_WORKERS overrides it."""
import ctypes
import os
import sys

WORKERS = int(os.environ.get("NHL94_SMAP_WORKERS") or 6)
BELOW_NORMAL = 0x4000


def gentle():
    """Lower this process's priority (Windows; elsewhere nice it)."""
    if sys.platform == "win32":
        k = ctypes.windll.kernel32
        k.SetPriorityClass(k.GetCurrentProcess(), BELOW_NORMAL)
    else:
        os.nice(10)
