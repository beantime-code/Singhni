"""Draft category glyphs for the weapons menu: KATAR, TALWAR, KUKRI, HEAVY (gada). White silhouettes on transparent,
the same style as the game's ACVI_UIicons_Menu_Weapon_*_Map type icons (the katar one in k2 was a white render
silhouette at 64 px, rotated 35 degrees). Drawn as vector shapes at 1024 px and reduced, so they stay crisp.

    python3 category_icons.py OUT_DIR            # icon_<name>_64.png, _256.png, sheet.png, mockup.png

These are drafts for the user to approve. katar_icons.py (acs_kit) pastes an approved PNG into every copy of the
texture; the tab icons are 4,222-byte records (ACVI_UIicons_Menu_Weapon_{Kukri,Canes,BrassKnucks}_Map).
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

S = 1024
WHITE = (255, 255, 255, 255)


def _arc(cx, cy, r, a0, a1, n=48):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]


def katar():
    im = Image.new('RGBA', (S, S))
    d = ImageDraw.Draw(im)
    # blade: long isoceles triangle with a strong central rib, pointing up
    d.polygon([(512, 70), (612, 560), (412, 560)], fill=WHITE)
    d.polygon([(412, 560), (612, 560), (640, 600), (384, 600)], fill=WHITE)
    # H grip: two side bars running back along the forearm, two cross grips between them
    for x in (300, 676):
        d.rounded_rectangle([x, 600, x + 48, 960], 20, fill=WHITE)
    for y in (700, 800):
        d.rounded_rectangle([348, y, 676, y + 40], 18, fill=WHITE)
    d.polygon([(384, 600), (640, 600), (676, 640), (348, 640)], fill=WHITE)
    return im


def _band(p0, p1, p2, width, n=80, offset=None):
    """polygon of a curved band along a quadratic Bezier; width(t) in px, offset(t) shifts it along the normal"""
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]
        dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
        dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy / L, dx / L
        w, o = width(t) / 2, (offset(t) if offset else 0)
        left.append((x + nx * (o + w), y + ny * (o + w)))
        right.append((x + nx * (o - w), y + ny * (o - w)))
    return left + right[::-1]


def talwar():
    im = Image.new('RGBA', (S, S))
    d = ImageDraw.Draw(im)
    # sabre blade from the guard (bottom) curving forward to the tip (top left); flat back, curved edge
    d.polygon(_band((600, 760), (690, 330), (300, 60), lambda t: 70 * (1 - t) ** 0.6 + 4), fill=WHITE)
    # crossguard with the central langet, grip, the talwar's disc pommel with its small finial
    d.rounded_rectangle([470, 755, 730, 800], 20, fill=WHITE)
    d.polygon([(570, 760), (630, 760), (606, 680)], fill=WHITE)
    d.rounded_rectangle([572, 800, 628, 930], 16, fill=WHITE)
    d.ellipse([510, 925, 690, 975], fill=WHITE)
    d.polygon([(585, 930), (615, 930), (600, 1010)], fill=WHITE)
    # knuckle guard: from the front quillon down and round to the pommel disc
    d.line(_arc(600, 860, 128, -10, 80, 40), fill=WHITE, width=26, joint='curve')
    return im


def kukri():
    im = Image.new('RGBA', (S, S))
    d = ImageDraw.Draw(im)
    # blade: rises from the handle, then droops forward; widest near the belly, ending in a point
    d.polygon(_band((330, 690), (430, 250), (960, 430),
                    lambda t: (56 + 150 * t) * min(1.0, (1 - t) / 0.3) ** 0.75 + 2,
                    offset=lambda t: 30 * t), fill=WHITE)
    d.polygon([(318, 650), (352, 668), (322, 690)], fill=(0, 0, 0, 0))          # the cho notch
    d.polygon([(250, 660), (420, 715), (405, 755), (235, 700)], fill=WHITE)     # bolster
    d.polygon([(248, 705), (400, 755), (345, 905), (318, 960), (215, 935), (222, 860)], fill=WHITE)
    return im


def heavy():
    im = Image.new('RGBA', (S, S))
    d = ImageDraw.Draw(im)
    # gada: long shaft, collar rings, a big ribbed spherical head and a small finial on top
    d.rounded_rectangle([487, 470, 537, 990], 22, fill=WHITE)
    d.ellipse([462, 960, 562, 1010], fill=WHITE)
    for y in (470, 520):
        d.rounded_rectangle([455, y, 569, y + 26], 12, fill=WHITE)
    d.ellipse([292, 150, 732, 500], fill=WHITE)
    for k in range(-2, 3):           # flutes: thin transparent cuts so the head reads as ribbed
        x = 512 + k * 82
        d.line([(x, 175), (x + k * 18, 480)], fill=(0, 0, 0, 0), width=10)
    d.polygon([(512, 40), (556, 160), (468, 160)], fill=WHITE)
    return im


ICONS = {'katar': katar, 'talwar': talwar, 'kukri': kukri, 'heavy': heavy}


def fit(im, size, margin=0.06, rotate=0):
    if rotate:
        im = im.rotate(rotate, resample=Image.BICUBIC, expand=True)
    bb = im.getchannel('A').getbbox()
    im = im.crop(bb)
    s = size * (1 - 2 * margin) / max(im.size)
    im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
    c = Image.new('RGBA', (size, size))
    c.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return c


def font(sz, bold=True):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/System/Library/Fonts/Helvetica.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def mockup(icons, out):
    """weapons page sketch: four category tabs over the item grid (the game's own grid icons are not drawn)"""
    W, H = 1280, 720
    im = Image.new('RGBA', (W, H), (18, 20, 24, 255))
    d = ImageDraw.Draw(im)
    d.text((60, 40), 'WEAPONS', font=font(34), fill=(235, 230, 220, 255))
    tabs = [('KATAR', 'katar', 'punch dagger'), ('TALWAR', 'talwar', 'sword'), ('KUKRI', 'kukri', 'blade'),
            ('HEAVY', 'heavy', 'gada, two-handed')]
    x = 60
    for i, (label, key, kind) in enumerate(tabs):
        on = i == 1
        box = [x, 110, x + 270, 200]
        d.rounded_rectangle(box, 10, fill=(178, 34, 34, 255) if on else (40, 44, 52, 255))
        im.alpha_composite(fit(icons[key], 64, 0.08), (x + 14, 123))
        d.text((x + 92, 128), label, font=font(26), fill=(255, 255, 255, 255))
        d.text((x + 92, 162), kind, font=font(16, False), fill=(200, 200, 200, 255))
        x += 290
    d.text((60, 220), 'TALWAR  ·  one-handed sword  ·  Unity sword moves', font=font(18, False),
           fill=(210, 200, 180, 255))
    for r in range(3):
        for c in range(6):
            bx, by = 60 + c * 195, 260 + r * 140
            filled = (r, c) == (0, 0)
            d.rounded_rectangle([bx, by, bx + 180, by + 125], 8, outline=(90, 95, 105, 255), width=2,
                                fill=(52, 46, 40, 255) if filled else (30, 33, 38, 255))
            if filled:
                im.alpha_composite(fit(icons['talwar'], 96, 0.05, rotate=-35), (bx + 42, by + 8))
                d.text((bx + 10, by + 100), 'TALWAR', font=font(16), fill=(255, 255, 255, 255))
    d.text((60, 690), 'Draft: tabs = the game\'s Knuckles / Cane / Kukri tabs re-labelled, plus a HEAVY tab only if '
           'test W0 shows tabs come from data', font=font(14, False), fill=(150, 150, 150, 255))
    im.convert('RGB').save(out)


def main(out):
    os.makedirs(out, exist_ok=True)
    icons = {k: f() for k, f in ICONS.items()}
    sheet = Image.new('RGBA', (4 * 280, 330), (24, 26, 30, 255))
    d = ImageDraw.Draw(sheet)
    for i, (k, im) in enumerate(icons.items()):
        fit(im, 64, 0.04, rotate=35 if k != 'heavy' else 20).save(os.path.join(out, f'icon_{k}_64.png'))
        big = fit(im, 256, 0.04)
        big.save(os.path.join(out, f'icon_{k}_256.png'))
        sheet.alpha_composite(big, (12 + i * 280, 12))
        d.text((12 + i * 280 + 90, 285), k.upper(), font=font(24), fill=(255, 255, 255, 255))
    sheet.convert('RGB').save(os.path.join(out, 'sheet.png'))
    mockup(icons, os.path.join(out, 'mockup.png'))
    print('wrote', sorted(os.listdir(out)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'icons_out')
