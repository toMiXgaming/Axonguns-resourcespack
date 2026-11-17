"""Czcionka i logo okien UI Axon (/ustawienia, później warsztat, działka i inne).

- axon:ui       Inter Medium (TTF), dla zwykłych napisów okien,
- axon:ui_bold  Inter Bold (TTF), dla tytułów,
- w obu U+EA40 to logo AXONCORE (emblemat z AxonGuns i napis Inter Bold, rysowane 3× gęściej).
Znaki, których Inter nie ma, biorą się z czcionki vanilli (reference minecraft:include/default).

Rozmiar TTF w Minecrafcie (FreeType, FT_Set_Pixel_Sizes) to wielkość kwadratu em w pikselach czcionki,
więc SIZE dobiera wysokość wielkich liter Inter (1490/2048 em) równą 7 px, jak w vanilli.
Szerokości liter dla pluginu (Axon-items, src/main/resources/ui/inter.tsv) liczy szerokosci() tym
samym wzorem; po zmianie SIZE trzeba je wygenerować od nowa (python3 axoncore/ui.py inter.tsv).

Inter: SIL Open Font License 1.1 (axoncore/czcionki/OFL.txt), (c) The Inter Project Authors.
"""
import io
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, 'czcionki')
MEDIUM = os.path.join(FONTS, 'Inter-Medium.ttf')
BOLD = os.path.join(FONTS, 'Inter-Bold.ttf')
EMBLEM = os.path.join(FONTS, 'axoncore-emblem.png')   # z AxonGuns (paczka/logo.png)

SIZE = 9.6           # em w px czcionki: wielkie litery mają wtedy 7 px
OVERSAMPLE = 4.0     # okna UI są w skali 2-3 px ekranu na px czcionki
SHIFT_Y = 0.0        # przesunięcie w dół, żeby linia bazowa była tam, gdzie w vanilli
LOGO = ''
LOGO_SS = 3          # logo rysowane 3× gęściej (glif musi się zmieścić na stronie atlasu 256 px)
ACCENT = (110, 220, 190)
WHITE = (236, 240, 246)


def logo():
    """Emblemat AxonCore (zielony sześciokąt z A, z paczki AxonGuns) i napis AXON (biały) CORE (akcent).
    Wysokość 10 px (emblemat), linia bazowa napisu na 8."""
    s = LOGO_SS
    h = 10 * s
    font = ImageFont.truetype(BOLD, 10 * s)   # Inter Bold, wielkie litery ~7 px
    img = Image.new('RGBA', (200 * s, h), (0, 0, 0, 0))
    em = Image.open(EMBLEM).convert('RGBA')
    ew = round(em.width * h / em.height)
    img.alpha_composite(em.resize((ew, h), Image.LANCZOS), (0, 0))
    d = ImageDraw.Draw(img)
    x = ew + 3 * s
    y = 8 * s - font.getbbox('H')[3]          # dół wielkich liter na 8 px
    spacing = 0.7 * s
    for i, ch in enumerate('AXONCORE'):
        col = WHITE if i < 4 else ACCENT
        d.text((x, y), ch, font=font, fill=col + (255,))
        x += font.getlength(ch) + spacing
    bbox = img.getbbox()
    out = img.crop((0, 0, bbox[2] + 1, h))
    assert out.width <= 256, 'logo nie zmieści się w atlasie czcionki (256 px)'
    return out


def _png(img):
    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def _font(ttf):
    return json.dumps({'providers': [
        {'type': 'bitmap', 'file': 'axon:font/ui/logo.png', 'height': 10, 'ascent': 8, 'chars': [LOGO]},
        {'type': 'ttf', 'file': 'axon:ui/' + ttf, 'size': SIZE, 'oversample': OVERSAMPLE,
         'shift': [0.0, SHIFT_Y], 'skip': ''},
        {'type': 'reference', 'id': 'minecraft:include/default'},
    ]}, indent=2, ensure_ascii=True).encode()


def pliki():
    return {
        'assets/axon/font/ui/inter-medium.ttf': open(MEDIUM, 'rb').read(),
        'assets/axon/font/ui/inter-bold.ttf': open(BOLD, 'rb').read(),
        'assets/axon/font/ui/ofl.txt': open(os.path.join(FONTS, 'OFL.txt'), 'rb').read(),
        'assets/axon/font/ui.json': _font('inter-medium.ttf'),
        'assets/axon/font/ui_bold.json': _font('inter-bold.ttf'),
        'assets/axon/textures/font/ui/logo.png': _png(logo()),
    }


def szerokosci():
    """Szerokości znaków (px czcionki) tak jak liczy je klient: advance × SIZE / unitsPerEm."""
    from fontTools.ttLib import TTFont
    out = {}
    for path, col in ((MEDIUM, 0), (BOLD, 1)):
        f = TTFont(path)
        scale = SIZE / f['head'].unitsPerEm
        hmtx = f['hmtx']
        for cp, glyph in f.getBestCmap().items():
            if cp > 0xFFFF:
                continue
            out.setdefault(cp, [None, None])[col] = round(hmtx[glyph][0] * scale, 4)
    logo_w = logo().width / LOGO_SS + 1
    out[ord(LOGO)] = [logo_w, logo_w]
    return out


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'inter.tsv'
    rows = szerokosci()
    with open(target, 'w') as fh:
        fh.write('# kod\tInter Medium\tInter Bold (px czcionki axon:ui przy SIZE=%s), z axoncore/ui.py\n' % SIZE)
        for cp in sorted(rows):
            m, b = rows[cp]
            if m is None or b is None:
                continue
            fh.write('%x\t%s\t%s\n' % (cp, m, b))
    print('zapisano', target, len(rows))
