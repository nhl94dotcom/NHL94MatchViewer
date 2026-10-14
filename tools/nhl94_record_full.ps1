# Records ALL of NHL '94's work RAM at full rate, for finding where something lives. Read-only on the emulator.
# ram.bin: every ~16 ms, [int64 ms][all 64 KB]. About 4 MB per second, so keep it short.
param([int]$Seconds = 75, [string]$OutDir = "C:\Users\USER\NHL94_Viewer\captures\full_$(Get-Date -Format 'yyyyMMdd_HHmmss')")

Add-Type -TypeDefinition @'
using System; using System.IO; using System.Diagnostics; using System.Threading; using System.Runtime.InteropServices;
public static class RecFull {
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
  public static string Record(IntPtr h, long ram, string dir, int seconds) {
    int count = 0; var sw = Stopwatch.StartNew();
    using (var f = new FileStream(Path.Combine(dir, "ram.bin"), FileMode.Create, FileAccess.Write, FileShare.Read, 1 << 20)) {
      while (sw.ElapsedMilliseconds < seconds * 1000L) {
        long ms = sw.ElapsedMilliseconds;
        var all = Read(h, ram, 0x10000);
        if (all == null) return "stopped early: emulator memory became unreadable after " + count + " samples";
        f.Write(BitConverter.GetBytes(ms), 0, 8); f.Write(all, 0, all.Length); count++;
        Thread.Sleep(15);
      }
    }
    return "recorded " + count + " full-RAM samples over " + sw.ElapsedMilliseconds / 1000 + " s";
  }
}
'@

$proc = Get-Process retroarch -ErrorAction Stop | Select-Object -First 1
$mod = $proc.Modules | Where-Object { $_.ModuleName -like '*genesis_plus_gx*' } | Select-Object -First 1
if (-not $mod) { throw 'Genesis Plus GX core is not loaded' }
$h = [RecFull]::OpenProcess(0x410, $false, $proc.Id)
$ram = [RecFull]::FindWorkRam($h, [long]$mod.BaseAddress, [long]$mod.BaseAddress + $mod.ModuleMemorySize)
if ($ram -eq 0) { throw 'work RAM not found' }
New-Item -ItemType Directory -Force $OutDir | Out-Null
"recording to $OutDir for $Seconds s, started $(Get-Date -Format 'HH:mm:ss')"
[RecFull]::Record($h, $ram, $OutDir, $Seconds)
[void][RecFull]::CloseHandle($h)
