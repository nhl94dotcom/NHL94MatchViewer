"""Cuts each on-screen player's picture out of a sprite capture: which hardware sprites are his, composed around his position."""
from sprite_capture import BASE, SIZE

CAM_X, CAM_Y = 0xBD1C, 0xBD18  # camera position in world units
W, H, AX, AY = 80, 80, 40, 60  # picture size, and where the player's position falls in it
REACH_X, REACH_UP, REACH_DOWN = 30, 50, 14  # how far from his position a player's sprites can be
TEAM_PALETTE = (2, 3)  # sprite palette line for Home, Away


def screen(smp, x, y):
    """World position -> screen pixel (the screen is 256 wide, 224 tall)."""
    return 128 + x - smp.sword(CAM_X), 120 - y + smp.sword(CAM_Y)


def players(smp):
    """(record number, role, world x, y, screen x, y) for every player on the ice."""
    out = []
    for k in range(12):
        r = BASE + SIZE * k
        role = smp.byte(r + 0x35)
        if role > 5:
            continue
        x, y = smp.sword(r + 0x1C), smp.sword(r + 0x20)
        sx, sy = screen(smp, x, y)
        out.append((k, role, x, y, sx, sy))
    return out


def picture(smp, k, sx, sy, palettes):
    """The composed picture of the sprites around (sx, sy) in the given palettes, as a tuple of rows, or None."""
    canvas = [[0] * W for _ in range(H)]
    found = False
    for s in smp.sprites:
        if s["pal"] not in palettes:
            continue
        left, top = s["x"] - sx, s["y"] - sy
        right, bottom = left + s["w"] * 8, top + s["h"] * 8
        if right <= -REACH_X or left >= REACH_X or bottom <= -REACH_UP or top >= REACH_DOWN:
            continue
        pix = smp.pixels(s)
        if pix is None or AX + left < 0 or AX + right > W or AY + top < 0 or AY + bottom > H:
            return None
        found = True
        for j, row in enumerate(pix):
            target = canvas[AY + top + j]
            for i, v in enumerate(row):
                if v and not target[AX + left + i]:  # earlier sprites in the list are drawn on top
                    target[AX + left + i] = v
    return tuple(bytes(r) for r in canvas) if found else None


def isolated(smp, k, everyone):
    """True when no other player is close enough for his sprites to be confused with this player's."""
    me = next(p for p in everyone if p[0] == k)
    if not (REACH_X <= me[4] <= 256 - REACH_X and REACH_UP <= me[5] <= 224 - REACH_DOWN):
        return False
    return all(p[0] == k or abs(p[4] - me[4]) > 2 * REACH_X or abs(p[5] - me[5]) > REACH_UP + REACH_DOWN for p in everyone)
