"""The scoring map's test hooks, applied to build.py's copy of the Genesis disassembly (never the clone itself). Size-neutral: the dead
lead-time block in doinput_cbut .press (gameclock .. the six branchless cmpi, 164 bytes; its results are overwritten
before use) is replaced by two subroutines and padding, 8 bytes shorter, and doshot gains two 4-byte bsr.w calls.
RAM $FFFFE000-$E02F (never used by the game: the gap between PALflag and the stack):
  E000 w override flag; E002/4/6 w puckvx/vy/vz to use instead of the game's
  E010 w doshot count; E012 l seed at entry; E016 passspeed at entry; E018 passdir; E01A/C puckx/pucky
  E020/2/4 w the game's own puckvx/vy/vz; E026 final passspeed; E028 l seed at exit; E02E / E030 the SPA of records 11 / 5 (the goalies) at doshot"""
import sys
p = sys.argv[1]
s = open(p, encoding="latin-1").read()
start = "\tmove.w\t(gameclock).w,d0\n\tandi.w\t#7,d0\n\tasl.w\t#4,d0\n\taddi.w\t#$A0,d0\n"
end = "\tcmpi.w\t#$FEF8,(pucky).w\n"
i = s.index(start)
j = s.index(end, i) + len(end)
block = """SMAPBLK
\tbra.w\tSMAPSKIP
SMAPIN
\taddq.w\t#1,($FFFFE010).w
\tmove.l\t(seed).w,($FFFFE012).w
\tmove.w\t(passspeed).w,($FFFFE016).w
\tmove.w\t(passdir).w,($FFFFE018).w
\tmove.w\t(puckx).w,($FFFFE01A).w
\tmove.w\t(pucky).w,($FFFFE01C).w
\tmove.w\t($FFFFB622).w,($FFFFE02E).w
\tmove.w\t($FFFFB322).w,($FFFFE030).w
\trts
SMAPEX
\tmove.w\t(puckvx).w,($FFFFE020).w
\tmove.w\t(puckvy).w,($FFFFE022).w
\tmove.w\t(puckvz).w,($FFFFE024).w
\tmove.w\t(passspeed).w,($FFFFE026).w
\tmove.l\t(seed).w,($FFFFE028).w
\ttst.w\t($FFFFE000).w
\tbeq.s\tSMAPEXNO
\tmove.w\t($FFFFE002).w,(puckvx).w
\tmove.w\t($FFFFE004).w,(puckvy).w
\tmove.w\t($FFFFE006).w,(puckvz).w
SMAPEXNO
\trts
\tdcb.b\t156-(*-SMAPBLK),0
SMAPSKIP
"""
s = s[:i] + block + s[j:]
a = "doshot\t\t\t\t\t\t\t\t;stick is at puck so launch puck toward goal\n\tmovem.l\td0-d7/a0-a3,-(sp)\n"
assert s.count(a) == 1
s = s.replace(a, a + "\tbsr.w\tSMAPIN\n")
b = ".ex\t\t\t\t\t\t\t\t\t;play the shot sound and return\n\tbsr.w\tsfx"
assert s.count(b) == 1, s.count(b)
s = s.replace(b, ".ex\t\t\t\t\t\t\t\t\t;play the shot sound and return\n\tbsr.w\tSMAPEX\n\tbsr.w\tsfx")
open(p, "w", encoding="latin-1").write(s)
print("patched", j - i, "source chars replaced")
