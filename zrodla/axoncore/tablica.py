"""Tablica wyników AxonScoreboard: panel, logo, ikony i paski jako znaki czcionki.

Wszystko trafia do czcionki minecraft:default jako znaki z prywatnego obszaru Unicode
(U+EA00–U+EA5F obrazki, U+EB00–U+EB1F odstępy). Klient łączy pliki font/default.json ze wszystkich
paczek, więc vanilla zostaje bez zmian, a tych znaków nie ma w żadnej innej czcionce.

Jak to działa w grze (szczegóły w AxonScoreboard, klasa pack/PanelDecorator):
- tytuł tablicy zaczyna się od tła nagłówka, akcentu i logo; tekst tytułu ma szerokość panelu,
  więc klient ustawia nagłówek dokładnie nad liniami,
- każda linia zaczyna się od kafla wiersza (ostatnia od kafla stopki), cofniętego ujemnym odstępem;
  kafel jest szerszy niż tablica i wychodzi za prawą krawędź ekranu, więc zakrywa szare tło vanilli,
- linia oddzielająca, pasek boczny, logo i paski postępu są białe: kolor tekstu je barwi,
  dlatego wszystko przyjmuje akcent ze skina GUI gracza,
- ikony są jednokolorowe (białe z cieniowaniem) i też przyjmują kolor linii.

Wymiary i szerokości (advance) muszą się zgadzać z AxonScoreboard (PackGlyphs.java);
`sprawdz()` liczy je tak jak klient i porównuje z ADVANCE.

`pliki()` zwraca {ścieżka w zipie: bajty}; woła ją gen_axoncore.pliki() i dodaj_tablice.py."""
import io
import json
import math

from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_DIR = 'assets/axon/textures/font/tablica/'
FONT_REF = 'axon:font/tablica/'

PANEL = (17, 19, 25, 236)        # tło wierszy
PANEL_TOP = (31, 34, 44, 244)    # nagłówek u góry
PANEL_EDGE = (58, 63, 78, 255)   # jaśniejsza krawędź z lewej
WIDE = 255                       # kafle wychodzą za prawą krawędź ekranu
HH = 16                          # wysokość nagłówka: od 7 px nad wierszem tytułu do początku linii

# znak: (nazwa, wysokość, ascent) – wysokość i ascent w pikselach GUI, jak w definicji czcionki
GLYPHS = {
    0xEA00: ('naglowek', HH, HH - 2),
    0xEA01: ('naglowek_akcent', HH, HH - 2),
    0xEA02: ('logo', 10, 9),
    0xEA03: ('wiersz', 9, 7),
    0xEA04: ('stopka', 12, 7),
    0xEA05: ('linia', 9, 7),
    0xEA06: ('krawedz', 9, 7),
}
IKONY = ['profil', 'kasa', 'staty', 'aktywnosc', 'dzialka', 'serwer', 'swiat', 'rajd', 'zrzut', 'wipe',
         'pvp', 'oaza', 'kompas_dzialka', 'kompas_struktura', 'serce', 'elita']
for i, n in enumerate(IKONY):
    GLYPHS[0xEA10 + i] = ('ikona_' + n, 8, 7)
PASKI = 21                       # 0%, 5%, ..., 100%
for i in range(PASKI):
    GLYPHS[0xEA40 + i] = ('pasek_%02d' % i, 6, 6)

# Odstępy: U+EB00+k = -(2^k), U+EB10+k = +(2^k), k = 0..8
SPACES = {}
for k in range(9):
    SPACES[chr(0xEB00 + k)] = -(1 << k)
    SPACES[chr(0xEB10 + k)] = 1 << k

# advance, które musi znać plugin (PackGlyphs.java)
ADVANCE = {'naglowek': 256, 'naglowek_akcent': 256, 'wiersz': 256, 'stopka': 256, 'linia': 256,
           'krawedz': 3, 'logo': 64, 'ikona': 9, 'pasek': 31}

SS = 4  # nadpróbkowanie hi-res znaków (logo, ikony)


def _png(img):
    b = io.BytesIO()
    img.save(b, 'PNG', optimize=True)
    return b.getvalue()


def _rounded_left(img, top_r, bottom_r):
    """Zaokrąglenie lewych rogów (prawy brzeg i tak jest za ekranem)."""
    w, h = img.size
    px = img.load()
    for r, ys in ((top_r, range(0, top_r)), (bottom_r, range(h - bottom_r, h))):
        for y in ys:
            for x in range(r):
                cy = r - 0.5 - (y if y < r else (h - 1 - y))
                cx = r - 0.5 - x
                d = math.hypot(cx, cy) - r + 0.5
                if d > 0:
                    a = max(0.0, 1.0 - d)
                    c = px[x, y]
                    px[x, y] = (c[0], c[1], c[2], int(c[3] * a))


def naglowek():
    img = Image.new('RGBA', (WIDE, HH))
    px = img.load()
    for y in range(HH):
        t = y / (HH - 1)
        c = tuple(int(PANEL_TOP[i] * (1 - t) + PANEL[i] * t) for i in range(3))
        for x in range(WIDE):
            px[x, y] = c + (246,)
    for y in range(HH):                      # jaśniejsza krawędź z lewej
        px[0, y] = PANEL_EDGE
    for x in range(WIDE):                    # ciemna kreska na dole: odcina nagłówek od wierszy
        px[x, HH - 1] = (10, 11, 15, 250)
    _rounded_left(img, 4, 0)
    return img


def naglowek_akcent():
    """Biały akcent (barwiony kolorem tekstu): pasek u góry i poświata w dół."""
    img = Image.new('RGBA', (WIDE, HH))
    px = img.load()
    for x in range(WIDE):
        fade = 1.0 if x < 140 else max(0.35, 1 - (x - 140) / 160)
        px[x, 0] = (255, 255, 255, int(255 * fade))
        px[x, 1] = (255, 255, 255, int(150 * fade))
        for y in range(2, 9):
            px[x, y] = (255, 255, 255, int(38 * fade * (1 - (y - 2) / 7)))
    _rounded_left(img, 4, 0)
    return img


def wiersz(stopka=False):
    h = 12 if stopka else 9
    img = Image.new('RGBA', (WIDE, h))
    px = img.load()
    for y in range(h):
        for x in range(WIDE):
            px[x, y] = PANEL if y < 9 or stopka else (0, 0, 0, 0)
        px[0, y] = PANEL_EDGE
    if stopka:
        for x in range(WIDE):
            px[x, h - 1] = (10, 11, 15, 250)
        _rounded_left(img, 0, 4)
    return img


def linia():
    img = Image.new('RGBA', (WIDE, 9))
    px = img.load()
    for x in range(4, WIDE):
        t = (x - 4) / 140
        a = 210 if t < 0.15 else max(40, int(210 * (1 - (t - 0.15))))
        px[x, 4] = (255, 255, 255, a)
    return img


def krawedz():
    img = Image.new('RGBA', (2, 9))
    for y in range(9):
        img.putpixel((0, y), (255, 255, 255, 255))
        img.putpixel((1, y), (255, 255, 255, 90))
    return img


def _font(size):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def logo():
    """AXONCORE: litery z odstępami, biało-szary gradient z góry na dół, romb przed napisem."""
    S = 3   # logo: 3× zamiast 4×, żeby zmieściło się w 256 px
    H = 10 * S
    text = 'AXONCORE'
    f = _font(int(H * 0.74))
    spacing = int(S * 1.6)
    widths = [f.getlength(ch) for ch in text]
    total = int(sum(widths) + spacing * (len(text) - 1)) + 9 * S
    img = Image.new('L', (total + S, H))
    d = ImageDraw.Draw(img)
    # romb
    cx, cy, r = 3.2 * S, H / 2, 3.0 * S
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=255)
    x = 8.5 * S
    top = (H - f.getbbox('A')[3] - f.getbbox('A')[1]) / 2
    for ch, w in zip(text, widths):
        d.text((x, top - f.getbbox('A')[1] / 2), ch, font=f, fill=255)
        x += w + spacing
    out = Image.new('RGBA', img.size)
    po, pi = out.load(), img.load()
    for y in range(img.height):
        shade = int(255 - 70 * (y / img.height) ** 1.5)
        for xx in range(img.width):
            if pi[xx, y]:
                po[xx, y] = (shade, shade, shade, pi[xx, y])
    return _trim_right(out)


def _trim_right(img):
    bbox = img.getbbox()
    return img.crop((0, 0, bbox[2], img.height))


# ---------------------------------------------------------------- ikony 8×8 (rysowane w 32×32)

def _canvas():
    return Image.new('L', (8 * SS * 4, 8 * SS * 4))   # 128×128, zmniejszane do 32×32


def _finish(mask):
    small = mask.resize((8 * SS, 8 * SS), Image.LANCZOS)
    out = Image.new('RGBA', small.size)
    po, pm = out.load(), small.load()
    for y in range(small.height):
        shade = int(255 - 60 * y / small.height)      # lekko ciemniej u dołu
        for x in range(small.width):
            if pm[x, y]:
                po[x, y] = (shade, shade, shade, pm[x, y])
    # pełna szerokość 32 (ostatnia kolumna niepusta = stały advance 9)
    a = out.getpixel((31, 31))
    out.putpixel((31, 31), (a[0], a[1], a[2], max(a[3], 1)))
    return out


def ikona(nazwa):
    m = _canvas()
    d = ImageDraw.Draw(m)
    S = m.width
    u = S / 16.0

    def P(*pts):
        return [(x * u, y * u) for x, y in pts]

    if nazwa in ('profil',):
        d.ellipse(P((5, 1.5), (11, 7.5)), fill=255)
        d.chord(P((2, 8.5), (14, 20)), 180, 360, fill=255)
    elif nazwa == 'kasa':
        for i, y in enumerate((10.5, 7.5, 4.5)):
            d.ellipse(P((2, y), (14, y + 4)), fill=255)
            d.ellipse(P((3, y + 0.6), (13, y + 2.6)), fill=150)
        d.ellipse(P((2, 1.5), (14, 5.5)), fill=255)
    elif nazwa in ('staty', 'rajd'):
        for flip in (False, True):
            pts = [(2, 2), (4, 2), (13, 11), (11, 13), (2, 4)]
            if flip:
                pts = [(16 - x, y) for x, y in pts]
            d.polygon(P(*pts), fill=255)
            g = [(10.5, 14.5), (14.5, 10.5)] if not flip else [(5.5, 14.5), (1.5, 10.5)]
            d.line(P(*g), fill=255, width=int(2 * u))
        if nazwa == 'rajd':
            d.ellipse(P((6, 5), (10, 9)), fill=255)
    elif nazwa == 'aktywnosc':
        d.ellipse(P((1.5, 1.5), (14.5, 14.5)), fill=255)
        d.ellipse(P((3.3, 3.3), (12.7, 12.7)), fill=0)
        d.line(P((8, 8), (8, 4.5)), fill=255, width=int(1.7 * u))
        d.line(P((8, 8), (11, 9.5)), fill=255, width=int(1.7 * u))
    elif nazwa in ('dzialka', 'kompas_dzialka'):
        d.polygon(P((8, 1.5), (15, 8), (13, 8), (13, 14.5), (3, 14.5), (3, 8), (1, 8)), fill=255)
        d.rectangle(P((6.5, 9.5), (9.5, 14.5)), fill=0)
    elif nazwa == 'serwer':
        d.polygon(P((9.5, 1), (3, 9), (7.5, 9), (6, 15), (13, 6.5), (8.5, 6.5), (10.5, 1)), fill=255)
    elif nazwa == 'swiat':
        d.ellipse(P((1.5, 1.5), (14.5, 14.5)), fill=255)
        d.ellipse(P((3, 3), (13, 13)), fill=0)
        d.ellipse(P((5.5, 1.5), (10.5, 14.5)), outline=255, width=int(1.4 * u))
        d.line(P((2, 8), (14, 8)), fill=255, width=int(1.4 * u))
    elif nazwa == 'zrzut':
        d.pieslice(P((1.5, 1), (14.5, 12)), 180, 360, fill=255)
        d.line(P((2.5, 6.5), (6.5, 11)), fill=255, width=int(1.2 * u))
        d.line(P((13.5, 6.5), (9.5, 11)), fill=255, width=int(1.2 * u))
        d.rectangle(P((5.5, 10.5), (10.5, 15)), fill=255)
    elif nazwa == 'wipe':
        d.polygon(P((3, 1.5), (13, 1.5), (8.6, 8), (13, 14.5), (3, 14.5), (7.4, 8)), fill=255)
        d.polygon(P((4.8, 3), (11.2, 3), (8, 7)), fill=0)
        d.polygon(P((5.2, 13), (10.8, 13), (8, 10.5)), fill=0)
    elif nazwa == 'pvp':
        d.ellipse(P((2, 1.5), (14, 11.5)), fill=255)
        d.rectangle(P((4.5, 9), (11.5, 14.5)), fill=255)
        d.ellipse(P((4, 5), (7.3, 8.3)), fill=0)
        d.ellipse(P((8.7, 5), (12, 8.3)), fill=0)
        for x in (6.2, 8, 9.8):
            d.line(P((x, 11.5), (x, 14.5)), fill=0, width=int(0.8 * u))
    elif nazwa == 'oaza':
        d.rectangle(P((6, 1.5), (10, 14.5)), fill=255)
        d.rectangle(P((1.5, 6), (14.5, 10)), fill=255)
    elif nazwa == 'kompas_struktura':
        d.rectangle(P((3, 1.5), (4.6, 15)), fill=255)
        d.polygon(P((4.6, 2), (14, 4.5), (4.6, 8.5)), fill=255)
    elif nazwa == 'serce':
        d.ellipse(P((1.5, 2.5), (8.5, 9.5)), fill=255)
        d.ellipse(P((7.5, 2.5), (14.5, 9.5)), fill=255)
        d.polygon(P((1.9, 7.5), (14.1, 7.5), (8, 14.5)), fill=255)
    elif nazwa == 'elita':
        d.polygon(P((1.5, 5), (5, 8), (8, 2), (11, 8), (14.5, 5), (13, 13), (3, 13)), fill=255)
        d.rectangle(P((3, 13.5), (13, 15)), fill=255)
    return _finish(m)


def pasek(i):
    """Pasek postępu 30×6 GUI (60×12 px): biały wypełniony (barwiony kolorem), ciemny pusty, zaokrąglony."""
    W, H = 30 * 2, 6 * 2
    frac = i / (PASKI - 1)
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 2, W - 1, H - 3), radius=4, fill=(70, 74, 86, 255))
    d.rounded_rectangle((1, 3, W - 2, H - 4), radius=3, fill=(38, 41, 50, 255))
    fill_w = int(round((W - 2) * frac))
    if fill_w > 0:
        mask = Image.new('L', (W, H))
        ImageDraw.Draw(mask).rounded_rectangle((1, 3, W - 2, H - 4), radius=3, fill=255)
        bar = Image.new('RGBA', (W, H))
        bp = bar.load()
        for y in range(H):
            shade = 255 if y < 6 else 205
            for x in range(1, 1 + fill_w):
                bp[x, y] = (shade, shade, shade, 255)
        img.paste(bar, (0, 0), Image.composite(mask, Image.new('L', (W, H)), mask))
    return img


# ---------------------------------------------------------------- definicja czcionki

def obrazy():
    out = {'naglowek': naglowek(), 'naglowek_akcent': naglowek_akcent(), 'logo': logo(),
           'wiersz': wiersz(), 'stopka': wiersz(True), 'linia': linia(), 'krawedz': krawedz()}
    for n in IKONY:
        out['ikona_' + n] = ikona(n)
    for i in range(PASKI):
        out['pasek_%02d' % i] = pasek(i)
    return out


def advance(img, height):
    """Jak klient (BitmapProvider): ostatnia niepusta kolumna × skala, zaokrąglone, +1."""
    w, h = img.size
    a = img.split()[3].load()
    actual = 0
    for x in range(w - 1, -1, -1):
        if any(a[x, y] for y in range(h)):
            actual = x + 1
            break
    return int(0.5 + actual * height / h) + 1


def sprawdz(imgs=None):
    imgs = imgs or obrazy()
    bledy = []
    for cp, (name, height, ascent) in GLYPHS.items():
        img = imgs[name]
        if img.width > 256 or img.height > 256:
            bledy.append('%s: obrazek %s większy niż 256 px' % (name, img.size))
        if ascent > height:
            bledy.append('%s: ascent %d > height %d' % (name, ascent, height))
        key = 'ikona' if name.startswith('ikona_') else 'pasek' if name.startswith('pasek_') else name
        adv = advance(img, height)
        if ADVANCE.get(key) != adv:
            bledy.append('%s: advance %d, w ADVANCE %s' % (name, adv, ADVANCE.get(key)))
    return bledy


def pliki():
    imgs = obrazy()
    bledy = sprawdz(imgs)
    if bledy:
        raise SystemExit('tablica: ' + '; '.join(bledy))
    files = {}
    providers = [{'type': 'space', 'advances': SPACES}]
    for cp, (name, height, ascent) in sorted(GLYPHS.items()):
        files[FONT_DIR + name + '.png'] = _png(imgs[name])
        providers.append({'type': 'bitmap', 'file': FONT_REF + name + '.png', 'height': height,
                          'ascent': ascent, 'chars': [chr(cp)]})
    files['assets/minecraft/font/default.json'] = json.dumps({'providers': providers}, ensure_ascii=True,
                                                             indent=1).encode()
    return files


if __name__ == '__main__':
    imgs = obrazy()
    for cp, (name, h, a) in sorted(GLYPHS.items()):
        print('%04X %-20s %s adv %d' % (cp, name, imgs[name].size, advance(imgs[name], h)))
    print(sprawdz(imgs) or 'OK')
