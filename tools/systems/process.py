"""Reading a running RetroArch's memory, read-only, on Windows: the part every system shares.

Find retroarch.exe and the emulator core loaded in it (a DLL whose name starts with the system's module_prefix), then
let the system's Attached subclass find the game's RAM in the core's writable data (`find`). Reads go through
ReadProcessMemory; nothing is ever written.
"""
import ctypes
import ctypes.wintypes as wt
import struct

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_VM_READ, PROCESS_QUERY_INFORMATION = 0x0010, 0x0400
TH32CS_SNAPPROCESS, TH32CS_SNAPMODULE, TH32CS_SNAPMODULE32 = 0x2, 0x8, 0x10
MEM_COMMIT, PAGE_READWRITE, PAGE_WRITECOPY = 0x1000, 0x04, 0x08


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("cntUsage", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wt.DWORD), ("cntThreads", wt.DWORD),
                ("th32ParentProcessID", wt.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wt.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", wt.DWORD), ("th32ModuleID", wt.DWORD), ("th32ProcessID", wt.DWORD),
                ("GlblcntUsage", wt.DWORD), ("ProccntUsage", wt.DWORD), ("modBaseAddr", ctypes.c_void_p),
                ("modBaseSize", wt.DWORD), ("hModule", wt.HMODULE), ("szModule", ctypes.c_wchar * 256),
                ("szExePath", ctypes.c_wchar * 260)]


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p), ("AllocationProtect", wt.DWORD),
                ("PartitionId", wt.WORD), ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD), ("Protect", wt.DWORD),
                ("Type", wt.DWORD)]


kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
kernel32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]
kernel32.VirtualQueryEx.restype = ctypes.c_size_t
INVALID_HANDLE = wt.HANDLE(-1).value


def find_process(name="retroarch.exe"):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE:
        return None
    try:
        entry = PROCESSENTRY32W(); entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == name:
                return entry.th32ProcessID
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return None


def process_path(pid):
    """The full path of a process's program (retroarch.exe), or None."""
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return None
    try:
        buf, size = ctypes.create_unicode_buffer(1024), wt.DWORD(1024)
        return buf.value if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)) else None
    finally:
        kernel32.CloseHandle(handle)


def find_module(pid, prefix):
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    if snap == INVALID_HANDLE:
        return None
    try:
        entry = MODULEENTRY32W(); entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Module32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szModule.lower().startswith(prefix):
                return entry.modBaseAddr, entry.modBaseSize
            ok = kernel32.Module32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)
    return None


class Attached:
    """A game's RAM (and cartridge) inside the running core. Subclasses set system and module_prefix and implement
    find(start, end) -> (ram address, rom address) or None, searching the core's module between start and end."""
    system = None
    module_prefix = None

    def __init__(self, pid, handle):
        self.pid, self.handle, self.ram, self.rom = pid, handle, None, None

    @classmethod
    def attach(cls):
        """The running emulator with this system's core and a game loaded, or None."""
        pid = find_process()
        if not pid:
            return None
        module = find_module(pid, cls.module_prefix)
        if not module:
            return None
        handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            return None
        emu = cls(pid, handle)
        found = emu.find(module[0], module[0] + module[1])
        if not found:
            emu.close()
            return None
        emu.ram, emu.rom = found
        return emu

    def raw(self, address, size):
        """Bytes at a host address in the emulator's process, or None."""
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.handle, ctypes.c_void_p(address), buf, size, ctypes.byref(got)) or got.value != size:
            return None
        return buf.raw

    def writable_regions(self, start, end):
        """(base address, bytes) of each committed, writable region between start and end."""
        mbi, address = MEMORY_BASIC_INFORMATION(), start
        while address < end:
            if not kernel32.VirtualQueryEx(self.handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base, size = mbi.BaseAddress or 0, mbi.RegionSize
            if mbi.State == MEM_COMMIT and mbi.Protect in (PAGE_READWRITE, PAGE_WRITECOPY) and size < 0x40000000:
                data = self.raw(base, size)
                if data:
                    yield base, data
            address = base + size

    def read(self, offset, size):
        """RAM bytes at offset, in host order (as the recorders store them); None if the emulator went away."""
        return self.raw(self.ram + offset, size)

    def word(self, offset):
        data = self.read(offset, 2)
        return struct.unpack("<H", data)[0] if data else None

    def alive(self):
        return self.read(0, 2) is not None

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None
