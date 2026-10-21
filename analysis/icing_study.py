"""Genesis icing against the game's own flags (2026-10-21; GENESIS_MECHANICS 8.7). iflags $BF80: bit 0 ifcgl (crossed the
goal line: icing pending), bit 1 ifdir, bit 2 ifok (armed). At each frame where an armed loose puck reaches a goal line,
whether the game set it pending or cancelled it, by how far from the middle it crossed (PuckIChk cancels within 44).
python analysis/icing_study.py"""
import sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,"tools")
import systems
from export_match import Capture
PUCK=0xB04A+0x80*14
 
c=Counter(); ex=[]
seen=set()
for folder in (Path("captures"), Path.home()/"Documents/NHL94 Viewer/captures"):
    for d in sorted(folder.glob("*")):
        if d.name in seen or not (d/"capture.json").exists() or not (d.parent.parent/"matches"/f"{d.name}.js").exists(): continue
        s=systems.of_capture(d)
        if s.NAME!="genesis": continue
        seen.add(d.name)
        cap=Capture(d,s)
        sw=lambda v: v-65536 if v>=32768 else v
        prevf=None
        for i in range(1,cap.count):
            if cap.byte(i,0xFFF7)!=0: continue
            f0=cap.byte(i-1,0xBF80); f1=cap.byte(i,0xBF80)
            if (f0&4) and not (f0&1) and ((f1&1) or not (f1&4)) and f1!=0 and abs(sw(cap.word(i,PUCK+0x14)))>=262 and cap.word(i,0xB04A+0x80*14+0x60)&0xFF00:
                x=sw(cap.word(i,PUCK)); y=sw(cap.word(i,PUCK+0x14))
                res="pending (ifcgl set)" if f1&1 else "cancelled (ifok cleared)"
                c[("|x|<=44" if abs(x)<=44 else "|x|>44",res)]+=1
                ex.append((d.name,i,x,y,res))
            if (f0&4) and not (f0&1) and f1==0:
                c["cleared to 0 (a touch)"]+=1
for k,v in sorted(c.items(),key=str): print(k,v)
for e in ex:
    if e[4].startswith("cancelled") or abs(e[2]) <= 50: print(e)
