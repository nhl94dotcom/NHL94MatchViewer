# Scans NHL '94 work RAM for records laid out like the puck's: X (4 bytes, 16.16), Y (4), Z (4), then X/Y speed words.
# A location qualifies when its X/Y stay in rink range, move, and move in the direction its speed words say. Read-only.
param([int]$Samples = 80, [int]$IntervalMs = 50)

Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class Mem2 {
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
  static int I16(byte[] b, int o) { return BitConverter.ToInt16(b, o); }
  static long Pos(byte[] b, int o) { return ((long)BitConverter.ToInt16(b, o) << 16) | BitConverter.ToUInt16(b, o + 2); }
  public static List<string> Scan(List<byte[]> s) {
    var outp = new List<string>(); int n = s.Count;
    for (int o = 0; o + 16 <= 0x10000; o += 2) {
      int minx = 99999, maxx = -99999, miny = 99999, maxy = -99999; bool inRange = true;
      for (int t = 0; t < n && inRange; t++) {
        int x = I16(s[t], o), y = I16(s[t], o + 4);
        if (x < -200 || x > 200 || y < -400 || y > 400) inRange = false;
        if (x < minx) minx = x; if (x > maxx) maxx = x; if (y < miny) miny = y; if (y > maxy) maxy = y;
      }
      if (!inRange || (maxx - minx) + (maxy - miny) < 8) continue;
      int agree = 0, disagree = 0;
      for (int t = 1; t < n; t++) {
        long dx = Pos(s[t], o) - Pos(s[t - 1], o), dy = Pos(s[t], o + 4) - Pos(s[t - 1], o + 4);
        int vx = I16(s[t], o + 12) + I16(s[t - 1], o + 12), vy = I16(s[t], o + 14) + I16(s[t - 1], o + 14);
        if (Math.Abs(dx) > 0x4000 && vx != 0) { if ((dx > 0) == (vx > 0)) agree++; else disagree++; }
        if (Math.Abs(dy) > 0x4000 && vy != 0) { if ((dy > 0) == (vy > 0)) agree++; else disagree++; }
      }
      if (agree >= 12 && agree >= 9 * disagree)
        outp.Add(String.Format("${0:X4}  x {1,4}..{2,-4} y {3,4}..{4,-4}  now ({5,4},{6,4})  speed words ({7,6},{8,6})  direction match {9}/{10}", o, minx, maxx, miny, maxy, I16(s[n - 1], o), I16(s[n - 1], o + 4), I16(s[n - 1], o + 12), I16(s[n - 1], o + 14), agree, agree + disagree));
    }
    return outp;
  }
}
'@

$proc = Get-Process retroarch -ErrorAction Stop | Select-Object -First 1
$mod = $proc.Modules | Where-Object { $_.ModuleName -like '*genesis_plus_gx*' } | Select-Object -First 1
$h = [Mem2]::OpenProcess(0x410, $false, $proc.Id)
$ram = [Mem2]::FindWorkRam($h, [long]$mod.BaseAddress, [long]$mod.BaseAddress + $mod.ModuleMemorySize)
if ($ram -eq 0) { throw 'work RAM not found' }
$snaps = New-Object 'System.Collections.Generic.List[byte[]]'
$sw = [Diagnostics.Stopwatch]::StartNew()
for ($n = 0; $n -lt $Samples; $n++) { $snaps.Add([Mem2]::Read($h, $ram, 0x10000)); Start-Sleep -Milliseconds $IntervalMs }
"captured $($snaps.Count) snapshots in $([int]$sw.ElapsedMilliseconds) ms; clock word `$C468 went $([BitConverter]::ToUInt16($snaps[0], 0xC468)) -> $([BitConverter]::ToUInt16($snaps[$snaps.Count-1], 0xC468))"
[Mem2]::Scan($snaps)
[void][Mem2]::CloseHandle($h)
