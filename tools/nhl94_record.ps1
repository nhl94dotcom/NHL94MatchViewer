# Records NHL '94 work RAM from a running RetroArch + Genesis Plus GX for a fixed time. Read-only on the emulator.
# fast.bin: every ~16 ms, [int64 ms][$B000-$BFFF][$C400-$CDFF] (layout also written to capture.json; $CDFF covers
# both teams' whole stat blocks).
# full.bin: every ~1 s, [int64 ms][all 64 KB].
param([int]$Seconds = 240, [string]$OutDir = "$(if ($PSScriptRoot) { Join-Path $PSScriptRoot '..' } else { (Get-Location).Path })\captures\capture_$(Get-Date -Format 'yyyyMMdd_HHmmss')")

Add-Type -TypeDefinition @'
using System; using System.IO; using System.Diagnostics; using System.Threading; using System.Runtime.InteropServices;
public static class Rec {
  [StructLayout(LayoutKind.Sequential)] public struct MBI { public IntPtr BaseAddress; public IntPtr AllocationBase; public uint AllocationProtect; public uint Pad1; public IntPtr RegionSize; public uint State; public uint Protect; public uint Type; public uint Pad2; }
  [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
  [DllImport("kernel32.dll", SetLastError=true)] public static extern bool ReadProcessMemory(IntPtr h, IntPtr addr, byte[] buf, IntPtr size, out IntPtr read);
  [DllImport("kernel32.dll")] public static extern IntPtr VirtualQueryEx(IntPtr h, IntPtr addr, out MBI mbi, IntPtr len);
  [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr h);
  public static byte[] Read(IntPtr h, long addr, int size) { var b = new byte[size]; IntPtr r; if (!ReadProcessMemory(h, (IntPtr)addr, b, (IntPtr)size, out r)) return null; return b; }
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
          if (hdr != null && hdr[0] == (byte)'E' && hdr[1] == (byte)'S' && hdr[2] == (byte)'A' && hdr[3] == (byte)'G') { RomBase = rom; return p; }
        }
      }
      a = rb + rs;
    }
    return 0;
  }
  public static long RomBase;
  // CRC-32 of the cartridge's first megabyte and of its second, as the ROM file has them (the emulator keeps each
  // pair of bytes swapped), so the converter can tell which ROM file was being played.
  public static string RomFingerprint(IntPtr h) {
    var table = new uint[256];
    for (uint i = 0; i < 256; i++) { uint c = i; for (int k = 0; k < 8; k++) c = (c & 1) != 0 ? 0xEDB88320 ^ (c >> 1) : c >> 1; table[i] = c; }
    var parts = new string[2];
    for (int part = 0; part < 2; part++) {
      var b = Read(h, RomBase + part * 0x100000L, 0x100000); if (b == null) return null;
      uint crc = 0xFFFFFFFF;
      for (int i = 0; i < b.Length; i++) crc = table[(crc ^ b[i ^ 1]) & 0xFF] ^ (crc >> 8);
      parts[part] = (crc ^ 0xFFFFFFFF).ToString("x8");
    }
    return "[\"" + parts[0] + "\", \"" + parts[1] + "\"]";
  }
  public static string Record(IntPtr h, long ram, string dir, int seconds) {
    int fast = 0, full = 0; long nextFull = 0; var sw = Stopwatch.StartNew();
    using (var f = new FileStream(Path.Combine(dir, "fast.bin"), FileMode.Create))
    using (var g = new FileStream(Path.Combine(dir, "full.bin"), FileMode.Create)) {
      while (sw.ElapsedMilliseconds < seconds * 1000L) {
        long ms = sw.ElapsedMilliseconds;
        var a = Read(h, ram + 0xB000, 0x1000); var c = Read(h, ram + 0xC400, 0xA00);
        if (a == null || c == null) return "stopped early: emulator memory became unreadable after " + fast + " samples";
        f.Write(BitConverter.GetBytes(ms), 0, 8); f.Write(a, 0, a.Length); f.Write(c, 0, c.Length); fast++;
        if (ms >= nextFull) { var all = Read(h, ram, 0x10000); if (all != null) { g.Write(BitConverter.GetBytes(ms), 0, 8); g.Write(all, 0, all.Length); full++; } nextFull = ms + 1000; }
        Thread.Sleep(15);
      }
    }
    return "recorded " + fast + " fast samples and " + full + " full snapshots over " + sw.ElapsedMilliseconds / 1000 + " s";
  }
}
'@

$proc = Get-Process retroarch -ErrorAction Stop | Select-Object -First 1
$mod = $proc.Modules | Where-Object { $_.ModuleName -like '*genesis_plus_gx*' } | Select-Object -First 1
if (-not $mod) { throw 'Genesis Plus GX core is not loaded' }
$h = [Rec]::OpenProcess(0x410, $false, $proc.Id)
$ram = [Rec]::FindWorkRam($h, [long]$mod.BaseAddress, [long]$mod.BaseAddress + $mod.ModuleMemorySize)
if ($ram -eq 0) { throw 'work RAM not found' }
New-Item -ItemType Directory -Force $OutDir | Out-Null
# The converter reads this to know which parts of RAM fast.bin holds ($B000-$BFFF includes the controller byte at $BEEF)
# and which ROM was being played.
$fingerprint = [Rec]::RomFingerprint($h)
$layout = '{"blocks": [[45056, 4096], [50176, 2560]]' + $(if ($fingerprint) { ', "rom_crc32": ' + $fingerprint } else { '' }) + '}'
$layout | Out-File -Encoding ascii (Join-Path $OutDir 'capture.json')
"recording to $OutDir for $Seconds s, started $(Get-Date -Format 'HH:mm:ss')"
[Rec]::Record($h, $ram, $OutDir, $Seconds)
[void][Rec]::CloseHandle($h)
