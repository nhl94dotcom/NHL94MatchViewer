"""Replay a goal from goal_types.py exactly and save the game's own frames: python goal_frames.py SYSTEM RUN TYPE N OUT
(the N-th goal of that type with a path: a PNG of four key frames, cropped to the net and scaled 3x, and the
path as JSON beside it). Used for the write-up's pictures of each kind of goal."""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

from paths import RUNS

FONT = "C:/Windows/Fonts/segoeui.ttf"


def grab(e):
    data, w, h, pitch = e.frame
    if getattr(e, "pixfmt", 0) == 2:
        return Image.frombuffer("RGB", (w, h), data, "raw", "BGR;16", pitch, 1)
    return Image.frombuffer("RGBX", (w, h), data, "raw", "BGRX", pitch, 1).convert("RGB")


def replay(system, g):
    """The goal again, frame by frame: [(image, state)] from the release to the goal."""
    import goal_types as G
    G._init(system)
    o = G.S["o"]
    net = g["net"]
    sy = g["y"] if net == "top" else -g["y"]
    h = o.h[net]
    if system == "genesis":
        h.setup(g["x"], sy, settle=g["settle"], clock=g["clock"])
    else:
        h.setup(g["x"], sy, settle=g["settle"], clock=g["clock"], seed=g["seed0"])
    pre = o.shoot(net, g["aim"], G.KINDS[system][g["kind"]])
    o.fire(net, pre, g["aim"], g["seed"])
    s0 = o.score0(net)
    out = [(None, o.state(net), None)]
    extra = [goalie_frame(h.e, system)]
    for f in range(160):
        img = frame(h, lambda: o.step(net))
        out.append((img, o.state(net), net_on_screen(h.e, system, net, img)))
        extra.append(goalie_frame(h.e, system))
        if o.scored(net, s0):
            for _ in range(20):                       # a moment past the goal: the light, the puck in the net
                img = frame(h, lambda: h.e.run(1))
                out.append((img, o.state(net), net_on_screen(h.e, system, net, img)))
                extra.append(goalie_frame(h.e, system))
            return out, extra
    raise RuntimeError("the replay didn't score: not the same shot")


def frame(h, step):
    h.e.want_frame = True
    step()
    h.e.want_frame = False
    return grab(h.e)


def goalie_frame(e, system):
    """The goalie's sprite frame and facing (for his save areas in the diagrams)."""
    if system == "genesis":
        g = 0xB04A + 11 * 0x80
        return e.w(g + 0x06), e.b(g + 0x55)
    return e.w(0x0D97 + 22), e.w(0x1163 + 22)


def net_on_screen(e, system, net, img=None):
    """Where the middle of the goal line is drawn (pixels). Genesis: from the camera words at BD18 / BD1C (offsets read
    off frames with the puck in the open). SNES: the rink never scrolls sideways (the net's middle is column 128), and
    the screen follows the rink layer's own scroll (07DC, a ring buffer), not the game's camera (Vpos 0D37, which runs
    up to 9 pixels off it and made the first SNES animations jerk), so the goal line's row is read off the frame
    itself: the row with the most goal-line red. Without a frame, or with the line hidden, the Vpos estimate."""
    gl = 268 if net == "top" else -268
    if system == "genesis":
        return 126.5 - e.sw(0xBD1C), e.sw(0xBD18) - gl + 118
    row = goal_line_row(img) if img is not None else None
    return 128, row if row is not None else e.sw(0x0D37) - gl + 114


def genesis_vram(e):
    """Where the Genesis video memory sits in the core's save state: right after its 1 KB copy of the sprite table,
    whose bytes reappear inside video memory at the sprite table's address (found, not assumed, per core version)."""
    s = e.serialize()
    i = s.find(bytes(e.ram[:4096]))                   # work RAM
    for a in range(i + 65536, i + 65536 + 40000):
        blk = s[a:a + 512]
        if blk.count(0) <= 400 and s.find(blk, a + 0x400, a + 0x400 + 0x10000) > 0:
            return a + 0x400
    raise RuntimeError("video memory not found in the state")


def hide_genesis_hud(e, vram):
    """Blank the clock and score boxes for the next frame drawn: they are rows 23-27 of the front tile layer (plane A,
    map at VmMAP1, 64 columns), which doesn't scroll; every other tile there is the transparent 07FF. Only what is
    drawn changes: the game never reads video memory back."""
    s = bytearray(e.serialize())
    a = vram + e.w(0xB004) + 2 * 64 * 23              # VmMAP1
    s[a:a + 2 * 64 * 5] = bytes([0xFF, 0x07]) * (64 * 5)   # 07FF, stored low byte first
    e.unserialize(bytes(s))


def goal_line_row(img):
    """The SNES goal line's row: the row where most pixels are its red (a full-width line; the circles and the crease
    have far fewer). None if no row is at least 40% red."""
    from PIL import ImageChops
    r, g, b = img.convert("RGB").split()
    red = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v > 180 else 0),
                                                  g.point(lambda v: 255 if v < 120 else 0)),
                              b.point(lambda v: 255 if v < 140 else 0))
    rows = list(red.resize((1, img.height), Image.BOX).getdata())
    best = max(range(len(rows)), key=lambda y: rows[y])
    return best if rows[best] >= 0.4 * 255 else None


def key_frames(out, typ):
    """Four frames that tell the goal: on the way, reaching the goalie, past him (or held), in the net."""
    states = [s for _, s, _ in out]
    n_goal = len(out) - 21                            # the frame the score changed
    near = min(range(1, n_goal), key=lambda i: (states[i][0] - states[i][5]) ** 2 + (states[i][1] - states[i][6]) ** 2)
    if typ.startswith("Held"):
        catch = next(i for i in range(1, len(out)) if states[i][8])
        return ([max(1, catch - 4), catch, (catch + n_goal) // 2, n_goal + 5],
                ["On its way", "Caught high", "Dragged back", "Over the line"])
    if near + 2 >= n_goal:                            # he's at the goal line: the puck is past him as it crosses
        return ([max(1, near - 10), max(1, near - 5), near, n_goal + 5],
                ["On its way", "Reaching him", "Past him", "In the net"])
    return ([max(1, near - 4), near, min(n_goal - 1, near + 3), n_goal + 5],
            ["On its way", "Reaching him", "Past him", "In the net"])


def strip(out, idx, labels, path, top):
    """A 2 x 2 grid of the frames, each cropped to the net and the ice in front of it, scaled 3x."""
    crops = []
    W, H, Z = 200, 120, 3
    for i in idx:
        im = out[i][0]
        cx, gy = out[i][2]
        x0 = int(max(0, min(im.width - W, cx - W / 2)))
        y0 = int(max(0, min(im.height - H, gy - 45 if top else gy - H + 45)))
        crops.append(im.crop((x0, y0, x0 + W, y0 + H)).resize((W * Z, H * Z), Image.NEAREST))
    w, h = crops[0].width, crops[0].height
    pad, cap = 14, 40
    img = Image.new("RGB", (2 * w + 3 * pad, 2 * (h + cap) + 3 * pad), "white")
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 24)
    for k, (im, lab) in enumerate(zip(crops, labels)):
        x, y = pad + (k % 2) * (w + pad), pad + (k // 2) * (h + cap + pad)
        img.paste(im, (x, y))
        d.text((x + 2, y + h + 6), f"{k + 1}. {lab}  (frame {idx[k]} after the release)", fill="#1f2933", font=f)
    img.save(path)


def main():
    system, run, typ, n, out_png = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
    data = json.load(open(RUNS / run / f"goal_types_{system}.json"))
    goals = [g for g in data["goals"] if g["type"] == typ and "path" in g]
    g = goals[n]
    out, extra = replay(system, g)
    idx, labels = key_frames(out, typ)
    strip(out, idx, labels, out_png, g["net"] == "top")
    json.dump(dict(goal={k: v for k, v in g.items() if k != "path"}, key=idx,
                   path=[s for _, s, _ in out], goalie=extra), open(out_png.rsplit(".", 1)[0] + ".json", "w"))
    print(out_png, idx, g["net"], g["x"], g["y"], g["kind"], g["aim"])


if __name__ == "__main__":
    main()
