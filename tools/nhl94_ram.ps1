# Reads NHL '94 work RAM ($FF0000-$FFFFFF) out of a running RetroArch + Genesis Plus GX process. Read-only.
param([int]$Samples = 10, [int]$IntervalMs = 500)

Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class Mem {
  [StructLayout(LayoutKind.Sequential)] public struct MBI { public IntPtr BaseAddress; public IntPtr AllocationBase; public uint AllocationProtect; public uint Pad1; public IntPtr RegionSize; public uint State; public uint Protect; public uint Type; public uint Pad2; }
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, IntPtr size, out IntPtr read);
  [DllImport("kernel32.dll")] public static extern IntPtr VirtualQueryEx(IntPtr h, IntPtr addr, out MBI mbi, IntPtr len);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  public static byte[] Read(IntPtr h, long addr, int size) { var b = new byte[size]; IntPtr r; if (!ReadProcessMemory(h, (IntPtr)addr, b, (IntPtr)size, out r)) return null; return b; }
  // The 68000 memory map has 32 consecutive 40-byte entries ($E0-$FF) sharing one base pointer: the work RAM.
  // A hit is confirmed by following entry 0 to the cartridge and checking for the "SEGA" header (byte-swapped in host memory).
  public static long FindWorkRam(IntPtr h, long start, long end) {
    long a = start;
    while (a < end) {
      MBI m; if (VirtualQueryEx(h, (IntPtr)a, out m, (IntPtr)Marshal.SizeOf(typeof(MBI))) == IntPtr.Zero) break;
      long rb = (long)m.BaseAddress, rs = (long)m.RegionSize;
      if (m.State == 0x1000 && (m.Protect == 0x04 || m.Protect == 0x08) && rs < 0x40000000) {
        var buf = Read(h, rb, (int)rs);
        if (buf != null) for (int i = 0xE0 * 40; i + 40 * 32 <= buf.Length; i += 8) {
          long p = BitConverter.ToInt64(buf, i); if (p < start || p >= end) continue;
          bool ok = true; for (int k = 1; k < 32 && ok; k++) if (BitConverter.ToInt64(buf, i + 40 * k) != p) ok = false;
          if (!ok) continue;
          long rom = BitConverter.ToInt64(buf, i - 0xE0 * 40);
          var hdr = Read(h, rom + 0x100, 4);
          if (hdr != null && hdr[0] == (byte)'E' && hdr[1] == (byte)'S' && hdr[2] == (byte)'A' && hdr[3] == (byte)'G') return p;
        }
      }
      a = rb + rs;
    }
    return 0;
  }
}
'@

$proc = Get-Process retroarch -ErrorAction Stop | Select-Object -First 1
$mod = $proc.Modules | Where-Object { $_.ModuleName -like '*genesis_plus_gx*' } | Select-Object -First 1
if (-not $mod) { throw 'Genesis Plus GX core is not loaded' }
$h = [Mem]::OpenProcess(0x410, $false, $proc.Id)
$ram = [Mem]::FindWorkRam($h, [long]$mod.BaseAddress, [long]$mod.BaseAddress + $mod.ModuleMemorySize)
if ($ram -eq 0) { throw 'work RAM not found' }
"work RAM found at module offset 0x$('{0:X}' -f ($ram - [long]$mod.BaseAddress))"

# Host memory holds each 16-bit word in native order, so a plain little-endian read returns the Genesis value.
function U16($b, $o) { [BitConverter]::ToUInt16($b, $o) }
function I16($b, $o) { [BitConverter]::ToInt16($b, $o) }

function I8($b, $o) { [sbyte]($b[$o -bxor 1] -band 0x7F) - ($b[$o -bxor 1] -band 0x80) }  # byte at a Genesis address (pairs are swapped in host memory)

# Puck record: words from $B766 to $B77C, then the low bytes smozoma's code reads as speed ($B773/$B775), then $0EE0/$0F00.
'{0}  | {1,5} {2,5} | {3,6} {4,6}' -f ((0..11 | ForEach-Object { '{0,6:X}' -f (0xB766 + 2 * $_) }) -join ' '), 'B773', 'B775', '0EE0', '0F00'
for ($n = 0; $n -lt $Samples; $n++) {
  $b = [Mem]::Read($h, $ram, 0x10000)
  '{0}  | {1,5} {2,5} | {3,6} {4,6}' -f ((0..11 | ForEach-Object { '{0,6}' -f (I16 $b (0xB766 + 2 * $_)) }) -join ' '), (I8 $b 0xB773), (I8 $b 0xB775), (I16 $b 0x0EE0), (I16 $b 0x0F00)
  Start-Sleep -Milliseconds $IntervalMs
}
''
'{0,6} {1,6} {2,6} {3,7} {4,7} {5,7} {6,7} {7,7} {8,7} {9,5} {10,5} {11,5} {12,5}' -f 'C466','C468','C46A','puckX','puckY','BDE4','BDEC','BE00','B04A','p1sc','p2sc','p1sh','p2sh'
for ($n = 0; $n -lt $Samples; $n++) {
  $b = [Mem]::Read($h, $ram, 0x10000)
  '{0,6} {1,6} {2,6} {3,7} {4,7} {5,7} {6,7} {7,7} {8,7} {9,5} {10,5} {11,5} {12,5}' -f (U16 $b 0xC466), (U16 $b 0xC468), (U16 $b 0xC46A), (I16 $b 0xB766), (I16 $b 0xB76A), (I16 $b 0xBDE4), (I16 $b 0xBDEC), (I16 $b 0xBE00), (I16 $b 0xB04A), (U16 $b 0xC6DA), (U16 $b 0xCA3E), (U16 $b 0xC6CC), (U16 $b 0xCA30)
  Start-Sleep -Milliseconds $IntervalMs
}
[void][Mem]::CloseHandle($h)
