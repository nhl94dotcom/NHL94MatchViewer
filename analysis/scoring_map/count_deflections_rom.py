"""Builds the test copy for count_deflections_test.py (2026-11-08): the retail Genesis ROM with a "count stick
deflections" hook, for testing only (NOSE4Web builds the real option). Like NOSE4Web's builds, the checksum check's
call at $300 is turned off and its routine at $FFAC0 replaced, the hook going after it at $FFAC6.

At $151D6, .stdef's `bsr.w a2touchpuck / bra.w deflect` (8 bytes) becomes `jsr $FFAC6 / nop`. The hook:
  tst.w $34(a2)            ; the toucher a goalie?          (position)
  bne.s .touch
  btst #0,$C2EA / bne.s    ; clock stopped (gmclock): no count, as ChkShotStat
  btst #4,$C2EA / bne.s    ; highlight (gmhl)
  bclr #4,$C2EE / beq.s    ; sf2shot: a shot standing? (cleared: it counts once)
  pea .touch(pc)           ; ChkShotStat's own frame, then into its .addShot ($12FD0) with d0 = shotplayer
  movem.l d0-d1/a1-a3,-(sp)  ; ($BED8): the team, power-play, period, shooter and goalie-against counts, without
  move.w $BED8,d0            ; .Cwdupdate's crowd boost (Crowdlevel +100, CwdExciteLvl +10), which play reads
  jmp $12FD0                 ; through the crowd meter; its movem pop and rts come back to .touch
.touch:
  jsr a2touchpuck ($1013E) ; what .stdef did
  addq.l #4,sp             ; drop the hook's return: deflect's rts goes back to puckstick's caller, as before
  jmp deflect ($15704)

python count_deflections_rom.py RETAIL_ROM OUT_ROM"""
import sys

HOOK = bytes.fromhex(
    "4a6a0034" "662a" "08380000c2ea" "6622" "08380004c2ea" "661a" "08b80004c2ee" "6712"
    "487a0010" "48e7c070" "3038bed8" "4ef900012fd0" "4eb90001013e" "588f" "4ef900015704")


def main():
    d = bytearray(open(sys.argv[1], "rb").read())
    assert d[0x300:0x306] == bytes.fromhex("4eb9000ffac0"), "not the retail ROM"
    assert d[0x151D6:0x151D8] == bytes.fromhex("6100") and d[0x151DA:0x151DC] == bytes.fromhex("6000")
    d[0x300:0x306] = bytes.fromhex("4e714e714e71")
    d[0xFFAC0:0xFFAC2] = bytes.fromhex("60fe")
    d[0xFFAC6:0xFFAC6 + len(HOOK)] = HOOK
    d[0x151D6:0x151DE] = bytes.fromhex("4eb9000ffac64e71")
    open(sys.argv[2], "wb").write(d)


if __name__ == "__main__":
    main()
