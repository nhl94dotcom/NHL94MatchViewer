"""Reads NHL '94's memory out of a running RetroArch (Genesis Plus GX core), read-only, on Windows.

The same method as tools/nhl94_record.ps1, in Python so the helper is one program: find retroarch.exe and the core
loaded in it, scan the core's writable data for the 68000 memory map (32 consecutive 40-byte entries, $E0-$FF, sharing
one base pointer: work RAM), and confirm it by the cartridge header ("ESAG", byte-swapped "SEGA") behind entry 0.
Work RAM is $FF0000-$FFFFFF; host memory keeps each 16-bit word in native order, so a single byte at Genesis address
A is at offset A XOR 1, and a little-endian word read gives the Genesis value.

    emu = Emulator.attach()          # None if RetroArch or the core is not running, or no game is loaded
    block = emu.read(0xB000, 0x1000) # work RAM offsets, bytes in host order (as the recorders store them)
"""
import ctypes
import ctypes.wintypes as wt
import struct
import zlib

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


def find_module(pid, prefix="genesis_plus_gx"):
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


class Emulator:
    def __init__(self, pid, handle, ram, rom):
        self.pid, self.handle, self.ram, self.rom = pid, handle, ram, rom

    @classmethod
    def attach(cls):
        """The running emulator with NHL '94 (or any Genesis game) loaded, or None."""
        pid = find_process()
        if not pid:
            return None
        module = find_module(pid)
        if not module:
            return None
        handle = kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle:
            return None
        found = cls._find_work_ram(handle, module[0], module[0] + module[1])
        if not found:
            kernel32.CloseHandle(handle)
            return None
        return cls(pid, handle, *found)

    @staticmethod
    def _raw(handle, address, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(handle, ctypes.c_void_p(address), buf, size, ctypes.byref(got)) or got.value != size:
            return None
        return buf.raw

    @classmethod
    def _find_work_ram(cls, handle, start, end):
        mbi, address = MEMORY_BASIC_INFORMATION(), start
        while address < end:
            if not kernel32.VirtualQueryEx(handle, ctypes.c_void_p(address), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base, size = mbi.BaseAddress or 0, mbi.RegionSize
            if mbi.State == MEM_COMMIT and mbi.Protect in (PAGE_READWRITE, PAGE_WRITECOPY) and size < 0x40000000:
                data = cls._raw(handle, base, size)
                if data:
                    for i in range(0xE0 * 40, len(data) - 40 * 32 + 1, 8):
                        p = struct.unpack_from("<Q", data, i)[0]
                        if not start <= p < end:
                            continue
                        if all(struct.unpack_from("<Q", data, i + 40 * k)[0] == p for k in range(1, 32)):
                            rom = struct.unpack_from("<Q", data, i - 0xE0 * 40)[0]
                            if cls._raw(handle, rom + 0x100, 4) == b"ESAG":
                                return p, rom
            address = base + size
        return None

    def read(self, offset, size):
        """Work RAM bytes at offset ($0000-$FFFF), in host order; None if the emulator went away."""
        return self._raw(self.handle, self.ram + offset, size)

    def word(self, offset):
        data = self.read(offset, 2)
        return struct.unpack("<H", data)[0] if data else None

    def byte(self, offset):
        data = self.read(offset ^ 1, 1)
        return data[0] if data else None

    def rom_fingerprint(self):
        """CRC-32 of the cartridge's first and second megabytes as the ROM file has them (the emulator keeps each
        pair of bytes swapped), as the recorder stores it so the converter can find the ROM file."""
        out = []
        for part in range(2):
            data = self._raw(self.handle, self.rom + part * 0x100000, 0x100000)
            if data is None:
                return None
            swapped = bytearray(len(data))
            swapped[0::2], swapped[1::2] = data[1::2], data[0::2]
            out.append(f"{zlib.crc32(bytes(swapped)):08x}")
        return out

    def alive(self):
        return self.read(0, 2) is not None

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None


if __name__ == "__main__":
    emu = Emulator.attach()
    if not emu:
        print("RetroArch with the Genesis Plus GX core and a game loaded was not found")
    else:
        print(f"work RAM at {emu.ram:#x}, cartridge at {emu.rom:#x}, ROM {emu.rom_fingerprint()}")
        print(f"period {emu.word(0xC466)}, clock {emu.word(0xC468)}, score {emu.word(0xC6DA)}-{emu.word(0xCA3E)}")
