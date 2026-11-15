"""Panel HUD AxonScoreboard (tryb „Panel”): tablica jako napis bossbara, ustawiana przez shader.

Jak to działa (szczegóły w AxonScoreboard, klasa hud/HudLayout i w shaderze rendertype_text):
- plugin wysyła cały panel jako tytuł jednego bossbara (pasek różowego bossbara jest w tej paczce
  przezroczysty); szerokość tytułu to 0, więc klient zaczyna go dokładnie na środku ekranu, y = 3,
- każda linia ma własną czcionkę axon:hud_<k> (tytuł: axon:hud_t), w której te same znaki co w vanilli
  i ikony z tablicy są przesunięte w dół o wysokość linii (ascent mniejszy o 18 + 9k),
- shader rozpoznaje znaki panelu po kolorze (R 64–111: tekst, tło, linia oddzielająca; prawdziwy
  kolor tekstu jest w G i B jako RGB 4-4-4 plus 4 bity sumy kontrolnej, żeby nie łapać zwykłych napisów),
  przenosi je do wybranego rogu ekranu i skaluje; cień napisu plugin wyłącza (shadow_color 0),
- tło panelu to jeden znak skinu (U+E100 + numer): kafel 2×2 z kolorami tła, nagłówka i akcentów
  (alfa 253 w tle to znak rozpoznawczy kafla),
  który shader rozciąga do rozmiaru panelu i rysuje z zaokrągleniem, cieniem i paskiem akcentu.

Skiny muszą się zgadzać z AxonScoreboard (HudLayout.SKINS)."""
import io
import json

from PIL import Image

from . import tablica

FONT_DIR = 'assets/axon/textures/font/hud/'
FONT_REF = 'axon:font/hud/'

# kolejność = numer skinu w pluginie; kolory jak w config.yml (skory): tło, nagłówek, akcent, akcent2
SKINY = [
    ('grafit', '14171F', '262B38', 'FF7A1F', 'FFC640', False),
    ('lod', '0F1A22', '1B3442', '38C6E0', 'A8F0FF', False),
    ('szmaragd', '0C1A13', '173B29', '3DDC84', 'B8FFD6', False),
    ('ametyst', '160F22', '2F1B47', 'B072FF', 'E2C8FF', False),
    ('korona', '1A1408', '3E2C0A', 'FFB02E', 'FFF0B8', True),
    ('zorza', '0A1020', '14234A', '3DF5C8', 'B072FF', True),
]
SKIN_CHAR = 0xE100

LINES = 15
TITLE_TOP = 5          # górny brzeg tekstu tytułu w panelu (px GUI)
FIRST_LINE_TOP = 18    # górny brzeg pierwszej linii
LINE_H = 9

VANILLA = json.load(open(__file__.replace('hud.py', 'maly_znaki.json'), encoding='utf-8'))
VANILLA_ASCENT = {  # plik: (wysokość, ascent) jak w vanilli
    'minecraft:font/nonlatin_european.png': (8, 7),
    'minecraft:font/accented.png': (12, 10),
    'minecraft:font/ascii.png': (8, 7),
}

# Znaki spoza czcionek-bitmap vanilli (klient bierze je z unifontu, którego nie da się przesunąć w dół).
# Te, których używa AxonScoreboard, są tu jako bitmapy z GNU Unifont 16 (licencja SIL OFL 1.1 / GPL
# z wyjątkiem dla czcionek): wiersze 16 px zapisane szesnastkowo, szerokość 8 albo 16 px.
UNIFONT = {
    0x2582: '000000000000000000000000FFFFFFFF',
    0x2586: '00000000FFFFFFFFFFFFFFFFFFFFFFFF',
    0x265B: '000000000808492A2A5D2A3E3E3E0000',
    0x26C1: '0000000007E0181821842184381C2FF42A543A5C2FF42A541A5807E000000000',
    0x2708: '000008000F00060007C0C380E3C07FFE7FFEE3C0C38007C006000F0008000000',
    0x2716: '101038387C7CFEFE7FFC3FF81FF00FE01FF03FF87FFCFEFE7C7C383810100000',
    0x271A: '07C007C007C007C007C0FFFEFFFEFFFEFFFEFFFE07C007C007C007C007C00000',
    0x2726: '01000380038007C007C01FF07FFCFFFE7FFC1FF007C007C00380038001000000',
    0x272A: '07C01FF03EF87EFC7C7CC006F01EF83EF01EF11E67CC6FEC3FF81FF007C00000',
    0x27A1: '000000000000002000300038FFFCFFFEFFFC0038003000200000000000000000',
    0x2B05: '0000000000000000080018003FFC7FFC3FFC1800080000000000000000000000',
    0x2B06: '000010387CFE38383838383838380000',
    0x2B07: '00003838383838383838FE7C38100000',
    0x2B08: '00000000000001F801F800F801F803F807D80F801F003E001C00080000000000',
    0x2B09: '0000000000003F003F003E003F003F8037C003E001F000F80070002000000000',
    0x2B0A: '00000000000008001C003E001F000F8007D803F801F800F801F801F800000000',
    0x2B0B: '0000000000000020007000F801F003E037C03F803F003E003F003F0000000000',
}


def unifont_png(cp):
    """Bitmapa znaku przycięta z lewej (jak unifont w kliencie); rysowana w wysokości 8, czyli w skali 1/2."""
    h = UNIFONT[cp]
    w = len(h) // 16 * 4
    rows = [int(h[i * w // 4:(i + 1) * w // 4], 16) for i in range(16)]
    cols = [x for x in range(w) if any(r >> (w - 1 - x) & 1 for r in rows)]
    left, right = cols[0], cols[-1]
    img = Image.new('RGBA', (right - left + 1, 16))
    for y, r in enumerate(rows):
        for x in range(left, right + 1):
            if r >> (w - 1 - x) & 1:
                img.putpixel((x - left, y), (255, 255, 255, 255))
    return img


def unifont_advance(cp):
    """Advance jak w kliencie dla bitmapy: (int) (0.5 + szerokość × 8/16) + 1."""
    return int(0.5 + unifont_png(cp).width * 0.5) + 1


def _rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def skin_png(skin):
    """2×2: [tło, nagłówek; akcent, akcent2]. Alfa 253 w tle = znak kafla dla shadera, alfa 254 w akcencie2 = lśnienie (skiny Elity)."""
    _, tlo, nag, a1, a2, shine = skin
    img = Image.new('RGBA', (2, 2))
    img.putpixel((0, 0), _rgb(tlo) + (253,))   # znak rozpoznawczy kafla
    img.putpixel((1, 0), _rgb(nag) + (255,))
    img.putpixel((0, 1), _rgb(a1) + (255,))
    img.putpixel((1, 1), _rgb(a2) + (254 if shine else 255,))
    return img


def _shift(delta):
    """Czcionka, w której wszystko jest niżej o delta px GUI."""
    providers = [{'type': 'space', 'advances': dict(tablica.SPACES, **{' ': 4, '‌': 0})}]
    for cp, (name, height, ascent) in sorted(tablica.GLYPHS.items()):
        if name.startswith(('ikona_', 'pasek_')) or name == 'logo':
            providers.append({'type': 'bitmap', 'file': tablica.FONT_REF + name + '.png', 'height': height,
                              'ascent': ascent - delta, 'chars': [chr(cp)]})
    for cp in sorted(UNIFONT):
        providers.append({'type': 'bitmap', 'file': FONT_REF + 'u%04x.png' % cp, 'height': 8, 'ascent': 7 - delta,
                          'chars': [chr(cp)]})
    for plik, (height, ascent) in VANILLA_ASCENT.items():
        providers.append({'type': 'bitmap', 'file': plik, 'height': height, 'ascent': ascent - delta,
                          'chars': VANILLA[plik]})
    return providers


def pliki():
    files = {}
    title = _shift(TITLE_TOP)
    for i, skin in enumerate(SKINY):
        name = 'skin_%s.png' % skin[0]
        img = skin_png(skin)
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        files[FONT_DIR + name] = buf.getvalue()
        title.append({'type': 'bitmap', 'file': FONT_REF + name, 'height': 2, 'ascent': 0,
                      'chars': [chr(SKIN_CHAR + i)]})
    for cp in UNIFONT:
        buf = io.BytesIO()
        unifont_png(cp).save(buf, 'PNG')
        files[FONT_DIR + 'u%04x.png' % cp] = buf.getvalue()
    files['assets/axon/font/hud_t.json'] = json.dumps({'providers': title}, ensure_ascii=True).encode()
    for k in range(LINES):
        files['assets/axon/font/hud_%d.json' % k] = json.dumps(
            {'providers': _shift(FIRST_LINE_TOP + LINE_H * k)}, ensure_ascii=True).encode()
    # różowy bossbar bez paska: zostaje sam napis (panel)
    for part, size in (('pink_background', (182, 5)), ('pink_progress', (182, 5))):
        buf = io.BytesIO()
        Image.new('RGBA', size).save(buf, 'PNG')
        files['assets/minecraft/textures/gui/sprites/boss_bar/%s.png' % part] = buf.getvalue()
    return files
