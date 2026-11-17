#!/usr/bin/env python3
"""Podgląd plakietek rang (axoncore/rangi.py): czat w skali GUI 3 i wszystkie plakietki powiększone.
python3 preview_rangi.py [wyjscie.png]   (domyślnie ../podglady/rangi-czat.png)"""
import os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from axoncore import rangi

HERE = os.path.dirname(os.path.abspath(__file__))
S = 3   # skala GUI: 1 px GUI = 3 px ekranu = 1 px obrazka plakietki

CZAT = [
    ('wlasciciel', 'Tomek', 'witajcie na Axoncore!'),
    ('admin', 'Blaze_Kid', 'restart serwera za 5 minut'),
    ('moderator', 'Frostbyte', 'bez spamu na czacie'),
    ('pomocnik', 'Redstoner', 'warsztat jest pod /warp baza'),
    ('budowniczy', 'Sky_Sailor', 'nowa struktura gotowa'),
    ('elita', 'Lord_Pebble', 'kto idzie na zrzut?'),
    ('vip', 'PixelPanda', 'ja! czekajcie przy oazie'),
    ('gracz', 'Moonwalker', 'gdzie znajde siarke?'),
]


def font(size, bold=False):
    f = '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf' % ('-Bold' if bold else '')
    return ImageFont.truetype(f, size)


def tlo(w, h):
    """Rozmyty "świat" pod czatem: niebo, wzgórza, ziemia."""
    img = Image.new('RGB', (w, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(70 + 60 * t), int(110 + 50 * t), int(150 + 30 * t)))
    d.polygon([(0, h * 0.55), (w * 0.3, h * 0.35), (w * 0.55, h * 0.5), (w * 0.8, h * 0.3), (w, h * 0.45), (w, h), (0, h)],
              fill=(70, 95, 60))
    d.rectangle([0, h * 0.75, w, h], fill=(95, 75, 55))
    return img.filter(ImageFilter.GaussianBlur(18))


def czat(imgs):
    line = 9 * S
    pad = 2 * S
    width = 320 * S
    h = len(CZAT) * line + 2 * pad
    out = tlo(width + 40 * S, h + 40 * S)
    box = Image.new('RGBA', (width, h), (0, 0, 0, 128))
    d = ImageDraw.Draw(box)
    f = font(8 * S - 2)
    for i, (key, nick, msg) in enumerate(CZAT):
        y = pad + i * line
        x = pad
        img = imgs[key]
        # znak: ascent 8, wiersz tekstu ma linię bazową 7 px pod górą wiersza (+1 px odstępu)
        box.alpha_composite(img, (x, y))
        x += (rangi.advance(img) + 4) * S   # advance znaku + spacja (4 px)
        for txt, col in ((nick, (255, 255, 255)), ('  »  ', (120, 120, 120)), (msg, (230, 230, 230))):
            d.text((x + S, y + S + 1), txt, font=f, fill=(40, 40, 40, 255))
            d.text((x, y + 1), txt, font=f, fill=col + (255,))
            x += int(d.textlength(txt, font=f))
    out = out.convert('RGBA')
    out.alpha_composite(box, (20 * S, 20 * S))
    return out


def galeria(imgs, k=4):
    gap = 12
    w = max(i.width for i in imgs.values()) * k + 2 * gap + 300
    h = len(imgs) * (rangi.H * k + gap) + gap
    out = Image.new('RGBA', (w, h), (28, 30, 36, 255))
    d = ImageDraw.Draw(out)
    f = font(22)
    for i, (key, img) in enumerate(imgs.items()):
        y = gap + i * (rangi.H * k + gap)
        out.alpha_composite(img.resize((img.width * k, img.height * k), Image.NEAREST), (gap, y))
        cp = next(r[1] for r in rangi.RANGI if r[0] == key)
        d.text((w - 290, y + 30), 'U+%04X  %s' % (cp, key), font=f,
               fill=(200, 205, 215))
    return out


def main():
    dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'podglady', 'rangi-czat.png')
    imgs = rangi.obrazy()
    a, b = czat(imgs), galeria(imgs)
    w = max(a.width, b.width)
    out = Image.new('RGBA', (w, a.height + b.height), (28, 30, 36, 255))
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (0, a.height))
    out.convert('RGB').save(dst)
    print(dst, out.size)


if __name__ == '__main__':
    main()
