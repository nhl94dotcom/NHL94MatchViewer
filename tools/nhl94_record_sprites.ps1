# Records what NHL '94 is drawing, for building the sprite library: work RAM plus the sprite list and the tile
# graphics those sprites use, read from the emulator's video memory. Read-only on the emulator.
# sprites.bin, about 30 samples a second, each:
#   [int64 ms][RAM $B000-$CBFF][uint16 n][n x 8-byte sprite entries][uint16 t][t x (uint16 tile number, 32 bytes)]
# Words are in the emulator's byte order (little-endian); a byte at address A is at offset A XOR 1.
param([int]$Seconds = 180, [string]$OutDir = "C:\Users\tdemorest\NHL94_Viewer\captures\sprites_$(Get-Date -Format 'yyyyMMdd_HHmmss')")

Add-Type -TypeDefinition @'
using System; using System.IO; using System.Diagnostics; using System.Threading; using System.Collections.Generic; using System.Runtime.InteropServices;
public static class RecSprites {
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
          if (hdr != null && hdr[0] == (byte)'E' && hdr[1] == (byte)'S' && hdr[2] == (byte)'A' && hdr[3] == (byte)'G') return p;
        }
      }
      a = rb + rs;
    }
    return 0;
  }
  // In this build of the core the video RAM sits a fixed distance after work RAM, and the game keeps its sprite
  // table at $DC00 in video RAM with a copy at $C018 in work RAM. A match between the two confirms the location.
  public const long VramFromRam = 0x2023560; public const int SatBase = 0xDC00; public const int SatCopy = 0xC018;
  public static bool VramLooksRight(IntPtr h, long ram) {
    for (int attempt = 0; attempt < 20; attempt++) {
      var a = Read(h, ram + SatCopy, 16); var b = Read(h, ram + VramFromRam + SatBase, 16);
      if (a == null || b == null) return false;
      bool same = true, blank = true; for (int i = 0; i < 16; i++) { if (a[i] != b[i]) same = false; if (a[i] != 0) blank = false; }
      if (same && !blank) return true;
      Thread.Sleep(7);
    }
    return false;
  }
  public static string Record(IntPtr h, long ram, string dir, int seconds) {
    int count = 0; long tiles = 0; var sw = Stopwatch.StartNew();
    using (var f = new FileStream(Path.Combine(dir, "sprites.bin"), FileMode.Create, FileAccess.Write, FileShare.Read, 1 << 20)) {
      while (sw.ElapsedMilliseconds < seconds * 1000L) {
        long ms = sw.ElapsedMilliseconds;
        var mem = Read(h, ram + 0xB000, 0x1C00); var vram = Read(h, ram + VramFromRam, 0x10000);
        if (mem == null || vram == null) return "stopped early: emulator memory became unreadable after " + count + " samples";
        var sprites = new List<int>(); var seen = new HashSet<int>(); var wanted = new SortedSet<int>(); int i = 0;
        while (seen.Add(i) && sprites.Count < 80) {
          int o = SatBase + 8 * i; sprites.Add(o);
          int w1 = BitConverter.ToUInt16(vram, o + 2), attr = BitConverter.ToUInt16(vram, o + 4);
          int size = (w1 >> 8) & 0xF, n = ((size >> 2) + 1) * ((size & 3) + 1), first = attr & 0x7FF;
          for (int t = 0; t < n; t++) wanted.Add((first + t) & 0x7FF);
          i = w1 & 0x7F; if (i == 0) break;
        }
        f.Write(BitConverter.GetBytes(ms), 0, 8); f.Write(mem, 0, mem.Length);
        f.Write(BitConverter.GetBytes((ushort)sprites.Count), 0, 2);
        foreach (int o in sprites) f.Write(vram, o, 8);
        f.Write(BitConverter.GetBytes((ushort)wanted.Count), 0, 2);
        foreach (int t in wanted) { f.Write(BitConverter.GetBytes((ushort)t), 0, 2); f.Write(vram, t * 32, 32); }
        count++; tiles += wanted.Count;
        Thread.Sleep(28);
      }
    }
    return "recorded " + count + " samples over " + sw.ElapsedMilliseconds / 1000 + " s, " + (count > 0 ? tiles / count : 0) + " tiles per sample on average";
  }
}
'@

$proc = Get-Process retroarch -ErrorAction Stop | Select-Object -First 1
$mod = $proc.Modules | Where-Object { $_.ModuleName -like '*genesis_plus_gx*' } | Select-Object -First 1
if (-not $mod) { throw 'Genesis Plus GX core is not loaded' }
$h = [RecSprites]::OpenProcess(0x410, $false, $proc.Id)
$ram = [RecSprites]::FindWorkRam($h, [long]$mod.BaseAddress, [long]$mod.BaseAddress + $mod.ModuleMemorySize)
if ($ram -eq 0) { throw 'work RAM not found' }
if (-not [RecSprites]::VramLooksRight($h, $ram)) { throw 'video RAM is not where expected (different core build, or no sprites on screen)' }
New-Item -ItemType Directory -Force $OutDir | Out-Null
"recording to $OutDir for $Seconds s, started $(Get-Date -Format 'HH:mm:ss')"
[RecSprites]::Record($h, $ram, $OutDir, $Seconds)
[void][RecSprites]::CloseHandle($h)
