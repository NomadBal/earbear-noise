# EarBear icon generator
# Copyright (C) 2026 NomadBal
# SPDX-License-Identifier: GPL-3.0-or-later
# Bear head with headphones on an orange disc, drawn at 1024 px and scaled down for every icon size.
# Usage: python make_icon.py <out.ico>   (writes the multi-size icon; needs numpy and Pillow)
import math, sys
import numpy as np
from PIL import Image, ImageDraw

S = 1024
ORANGE, BEAR, CUP, HILITE, WHITE, MUZZLE = (255, 117, 24), (21, 23, 28), (40, 44, 56), (82, 90, 109), (255, 255, 255), (246, 240, 230)
LINE = 24


def rounded(pts, radii, steps=24):
    """Polygon with each corner replaced by an arc of the given radius."""
    n, out = len(pts), []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        a = (p0[0] - p1[0], p0[1] - p1[1]); b = (p2[0] - p1[0], p2[1] - p1[1])
        la, lb = math.hypot(*a), math.hypot(*b)
        a, b = (a[0] / la, a[1] / la), (b[0] / lb, b[1] / lb)
        ang = math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1])))
        r = radii[i]
        t = r / math.tan(ang / 2)
        s, e = (p1[0] + a[0] * t, p1[1] + a[1] * t), (p1[0] + b[0] * t, p1[1] + b[1] * t)
        bis = (a[0] + b[0], a[1] + b[1]); lbis = math.hypot(*bis)
        h = r / math.sin(ang / 2)
        c = (p1[0] + bis[0] / lbis * h, p1[1] + bis[1] / lbis * h)
        a0, a1 = math.atan2(s[1] - c[1], s[0] - c[0]), math.atan2(e[1] - c[1], e[0] - c[0])
        da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        out += [(c[0] + r * math.cos(a0 + da * k / steps), c[1] + r * math.sin(a0 + da * k / steps)) for k in range(steps + 1)]
    return out


def dilate(m, n):
    for k in range(n):
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        if k % 2:
            g[1:, 1:] |= m[:-1, :-1]; g[:-1, :-1] |= m[1:, 1:]; g[1:, :-1] |= m[:-1, 1:]; g[:-1, 1:] |= m[1:, :-1]
        m = g
    return m


def make(cups, eyes):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for cx, cy, r in ((252, 292, 108), (772, 292, 108)):                      # ears
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=BEAR)
    d.ellipse((512 - 328, 568 - 324, 512 + 328, 568 + 324), fill=BEAR)        # head
    cx, cy, R, w = 512, 572, 342, 58                                           # headband with its light top edge
    d.arc((cx - R, cy - R, cx + R, cy + R), 212, 328, fill=CUP, width=w)
    d.arc((cx - R, cy - R, cx + R, cy + R), 214, 326, fill=HILITE, width=10)
    for side in (-1, 1):
        m = (lambda x: x) if side < 0 else (lambda x: S - x)
        if cups == 'orig':
            x0, x1 = sorted((m(92), m(248)))
            d.rounded_rectangle((x0, 416, x1, 740), 60, fill=CUP)
        else:                                                                  # tall against the head, flat outer face
            pts = [(m(88), 444), (m(250), 404), (m(250), 752), (m(88), 712)]
            if side > 0:
                pts = pts[::-1]
            d.polygon(rounded(pts, [58, 42, 42, 58]), fill=CUP)
    d.ellipse((512 - 140, 690 - 106, 512 + 140, 690 + 106), fill=MUZZLE)      # muzzle, nose, mouth
    d.ellipse((512 - 52, 636 - 34, 512 + 52, 636 + 34), fill=BEAR)
    d.line((512, 668, 512, 708), fill=BEAR, width=12)
    d.arc((512 - 44, 686, 512, 730), 20, 160, fill=BEAR, width=12)
    d.arc((512, 686, 512 + 44, 730), 20, 160, fill=BEAR, width=12)
    if eyes:
        for x in (396, 628):
            d.ellipse((x - 30, 566 - 30, x + 30, 566 + 30), fill=WHITE)
    m = dilate(np.array(img)[..., 3] > 0, LINE)                                # one white outline around the figure
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, S - 1, S - 1), fill=ORANGE)
    out.paste(Image.new('RGBA', (S, S), WHITE + (255,)), (0, 0), Image.fromarray((m * 255).astype(np.uint8)))
    out.alpha_composite(img)
    return out


if __name__ == '__main__':
    master = make('phones', False)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    imgs = {s: master.resize((s, s), Image.LANCZOS) for s in sizes}
    imgs[256].save(sys.argv[1], sizes=[(s, s) for s in sizes], append_images=[imgs[s] for s in sizes if s != 256])
