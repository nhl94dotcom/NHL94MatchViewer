"""Gentle mode for long runs, so the computer stays cool and quiet and anything the user is doing comes first:
- WORKERS processes at most (default 2; NHL94_SMAP_WORKERS overrides it);
- each at idle priority (gentle());
- each resting between bursts of work (breathe(), called in the work loops): DUTY is the share of time spent working
  (default 0.5: rest as long as it worked; NHL94_SMAP_DUTY overrides it, 1 = no rests);
- and resting on while the whole machine is busy with something else (another program on the same computer: the
  total CPU above BUSY, default 10%, NHL94_SMAP_BUSY; 2026-11-22). Windows also runs these windowless idle-priority
  processes on the efficiency cores at about 2 GHz (power throttling, left on by the user's choice: quiet).
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
        k.GetCurrentProcess.restype = ctypes.c_void_p        # a pseudo-handle (-1): passed as a plain int it was
        k.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]   # cut to 32 bits on 64-bit Python and the
        k.GetPriorityClass.argtypes = [ctypes.c_void_p]      # call failed silently (found 2026-10-31: runs were at
        k.SetPriorityClass(k.GetCurrentProcess(), IDLE)      # Normal priority, the fan loud)
        if k.GetPriorityClass(k.GetCurrentProcess()) != IDLE:
            print("gentle: could not lower the priority", file=sys.stderr)
    else:
        os.nice(19)


BUSY = float(os.environ.get("NHL94_SMAP_BUSY") or 0.10)   # the whole machine's CPU share above which we wait (ours ~3%)
WAIT_MAX = 60.0                                            # seconds of extra waiting at most, per rest


def _system_times():
    """(idle, total) processor time so far, all processors (Windows GetSystemTimes; None elsewhere)."""
    if sys.platform != "win32":
        return None
    ft = [ctypes.c_ulonglong() for _ in range(3)]
    if not ctypes.windll.kernel32.GetSystemTimes(*[ctypes.byref(f) for f in ft]):
        return None
    idle, kernel, user = (f.value for f in ft)
    return idle, kernel + user                             # kernel time includes the idle time


def machine_busy(sample=1.0):
    """The whole machine's CPU use over the next `sample` seconds, 0-1 (every process, ours included)."""
    a = _system_times()
    time.sleep(sample)
    b = _system_times()
    if not a or not b or b[1] == a[1]:
        return 0.0
    return 1 - (b[0] - a[0]) / (b[1] - a[1])


def breathe():
    """After each quarter second or more of work, rest so that work is DUTY of the time; then, while the machine as a
    whole is busy (above BUSY of all its processors: another program working, e.g. NOSE4Web building or testing on the
    same computer, 2026-11-22 the user's ask), rest on, checking every 2 s, up to WAIT_MAX: the total load stays near
    the quiet level whatever else runs. NHL94_SMAP_BUSY=1 turns the wait off."""
    busy = time.perf_counter() - _since[0]
    if busy >= 0.25 and DUTY < 1:
        time.sleep(busy * (1 - DUTY) / DUTY)
        if BUSY < 1:
            waited, t0 = 0.0, time.perf_counter()
            while machine_busy() > BUSY and waited < WAIT_MAX:
                time.sleep(1.0)
                waited = time.perf_counter() - t0
        _since[0] = time.perf_counter()
