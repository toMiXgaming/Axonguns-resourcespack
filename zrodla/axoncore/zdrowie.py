"""System zdrowia AxonCore: sylwetka gracza z 7 części ciała i ikonki stanów (HUD i okno „Zdrowie”).

Każda część ciała to osobny biały znak tej samej wielkości (te same płótno i ascent), więc znaki położone
jeden na drugim (plugin wstawia między nie ujemne odstępy) składają się w sylwetkę, a każdą część barwi
kolor tekstu: zielony, żółty, pomarańczowy, czerwony, czarny (część zniszczona). Pod spodem jest znak
obrysu (ciemny cień), żeby sylwetka była czytelna na jasnym tle.

Znaki w minecraft:default (tablica, czat, okna) i w czcionce panelu HUD axon:hud (hud.py dokłada je na
końcu listy znaków, żeby nie przesuwać numerów, które zna już AxonScoreboard):

| Znak | Co |
|---|---|
| U+EE00 | obrys (cień) całej sylwetki |
| U+EE01–U+EE07 | głowa, klatka, brzuch, lewa ręka, prawa ręka, lewa noga, prawa noga |
| U+EE10–U+EE15 | ikonki 8×8: krwawienie, mocne krwawienie, złamanie, ból, szyna, środki przeciwbólowe |

Sylwetka stoi przodem do patrzącego, więc lewa ręka i lewa noga gracza są po prawej stronie obrazka
(tak jak w Tarkovie). Wysokość znaku to SYL_H px GUI, szerokość SYL_W (advance SYL_W + 1)."""
import io

from PIL import Image, ImageDraw, ImageFilter

FONT_DIR = 'assets/axon/textures/font/zdrowie/'
FONT_REF = 'axon:font/zdrowie/'

SYL_W, SYL_H = 16, 36          # px GUI
SYL_SS = 4                     # gęstość tekstury (64×144), ostra w każdej skali GUI i w oknie powiększonym ×4
SYL_ASCENT = 7                 # góra sylwetki równo z górą tekstu w linii

CZESCI = ['glowa', 'klatka', 'brzuch', 'reka_lewa', 'reka_prawa', 'noga_lewa', 'noga_prawa']
OBRYS = 0xEE00
CZESC_CP = {n: 0xEE01 + i for i, n in enumerate(CZESCI)}

IKONY = ['krwawienie', 'krwawienie_mocne', 'zlamanie', 'bol', 'szyna', 'przeciwbolowe']
IKONA_CP = {n: 0xEE10 + i for i, n in enumerate(IKONY)}
IKONA_H, IKONA_ASCENT = 8, 7

# Kolory stanu części (do pluginów, tu tylko do podglądu): ułamek HP -> kolor
KOLORY = [(0.75, (110, 220, 120)), (0.5, (232, 214, 80)), (0.25, (240, 150, 60)), (0.0001, (226, 64, 52)),
          (0.0, (40, 40, 44))]

# Kształty w siatce 16 × 36 (px GUI). Szczeliny ok. 0,6 px między częściami, żeby kolory się nie zlewały.
def _ksztalty(d, u, czesc):
    def R(x0, y0, x1, y1, r):
        d.rounded_rectangle([x0 * u, y0 * u, x1 * u, y1 * u], radius=r * u, fill=255)

    def poly(*pts):
        d.polygon([(x * u, y * u) for x, y in pts], fill=255)

    if czesc == 'glowa':
        d.ellipse([5.3 * u, 0.3 * u, 10.7 * u, 6.6 * u], fill=255)
    elif czesc == 'klatka':
        poly((4.4, 8.2), (5.6, 7.4), (10.4, 7.4), (11.6, 8.2), (11.2, 14.4), (4.8, 14.4))
        R(4.4, 7.4, 11.6, 10.0, 1.2)
    elif czesc == 'brzuch':
        R(4.9, 15.0, 11.1, 19.6, 1.0)
    elif czesc in ('reka_prawa', 'reka_lewa'):
        # ręka prawa gracza = lewa strona obrazka
        poly((1.0, 18.8), (2.6, 8.4), (3.9, 7.9), (3.9, 13.0), (2.9, 19.2))
        R(0.6, 18.4, 3.0, 21.4, 1.1)          # dłoń
    elif czesc in ('noga_prawa', 'noga_lewa'):
        poly((4.9, 20.2), (7.7, 20.2), (7.5, 34.0), (5.4, 34.0), (5.0, 27.0))
        R(4.6, 33.4, 7.7, 35.6, 0.8)          # stopa


def _czesc_img(czesc):
    W, H = SYL_W * SYL_SS * 4, SYL_H * SYL_SS * 4        # rysowane 4× gęściej, potem zmniejszane
    m = Image.new('L', (W, H))
    d = ImageDraw.Draw(m)
    u = SYL_SS * 4
    lustro = czesc in ('reka_lewa', 'noga_lewa')
    _ksztalty(d, u, czesc)
    if lustro:
        m = m.transpose(Image.FLIP_LEFT_RIGHT)
    return m


def _gotowe(mask, cien=False):
    small = mask.resize((SYL_W * SYL_SS, SYL_H * SYL_SS), Image.LANCZOS)
    out = Image.new('RGBA', small.size)
    po, pm = out.load(), small.load()
    for y in range(small.height):
        for x in range(small.width):
            a = pm[x, y]
            if a:
                if cien:
                    po[x, y] = (10, 12, 16, min(255, int(a * 0.85)))
                else:
                    # lekki gradient z góry na dół i jaśniejsza lewa krawędź: sylwetka nie jest płaską plamą
                    shade = int(255 - 50 * y / small.height)
                    po[x, y] = (shade, shade, shade, a)
    # stała szerokość: ostatnia kolumna niepusta (advance = SYL_W + 1 dla każdego znaku)
    a = out.getpixel((out.width - 1, out.height - 1))
    out.putpixel((out.width - 1, out.height - 1), (a[0], a[1], a[2], max(a[3], 1)))
    return out


def sylwetka():
    """Nazwa -> obrazek RGBA: 'obrys' i 7 części."""
    masks = {c: _czesc_img(c) for c in CZESCI}
    out = {c: _gotowe(m) for c, m in masks.items()}
    full = Image.new('L', masks['glowa'].size)
    for m in masks.values():
        full = Image.composite(Image.new('L', full.size, 255), full, m)
    obrys = full.filter(ImageFilter.MaxFilter(4 * 4 + 1))  # ok. 1 px GUI wokół całej sylwetki
    out['obrys'] = _gotowe(obrys, cien=True)
    return out


# ---------------------------------------------------------------- ikonki stanów 8×8 (rysowane w 128×128)

def _ikona(nazwa):
    S = 128
    m = Image.new('L', (S, S))
    d = ImageDraw.Draw(m)
    u = S / 16.0

    def P(*pts):
        return [(x * u, y * u) for x, y in pts]

    def kropla(cx, top, r):
        d.polygon(P((cx, top), (cx + r * 0.95, top + r * 1.55), (cx - r * 0.95, top + r * 1.55)), fill=255)
        d.ellipse(P((cx - r, top + r * 0.9), (cx + r, top + r * 2.9)), fill=255)

    if nazwa == 'krwawienie':
        kropla(8, 1.0, 4.6)
    elif nazwa == 'krwawienie_mocne':
        kropla(5.4, 0.8, 3.4)
        kropla(11.0, 4.6, 3.4)
    elif nazwa == 'zlamanie':
        # kość po przekątnej z dwiema gałkami na końcach, przełamana w środku (zygzak)
        for cx, cy, sx, sy in ((3.2, 3.2, -1, 1), (3.2, 3.2, 1, -1), (12.8, 12.8, -1, 1), (12.8, 12.8, 1, -1)):
            d.ellipse(P((cx + sx * 1.3 - 1.9, cy + sy * 1.3 - 1.9), (cx + sx * 1.3 + 1.9, cy + sy * 1.3 + 1.9)), fill=255)
        d.line(P((3.2, 3.2), (12.8, 12.8)), fill=255, width=int(2.8 * u))
        d.polygon(P((5.6, 9.0), (7.4, 7.0), (8.0, 8.6), (9.6, 6.6), (11.0, 7.6), (8.4, 10.4), (7.8, 8.8), (6.6, 10.4)), fill=0)
    elif nazwa == 'bol':
        d.polygon(P((9.6, 0.6), (3.2, 9.0), (7.4, 9.0), (5.8, 15.4), (12.8, 6.4), (8.4, 6.4), (10.4, 0.6)), fill=255)
    elif nazwa == 'szyna':
        d.rounded_rectangle(P((2.0, 1.0), (5.6, 15.0)), radius=1.2 * u, fill=255)
        d.rounded_rectangle(P((10.4, 1.0), (14.0, 15.0)), radius=1.2 * u, fill=255)
        for y in (3.4, 9.6):
            d.rectangle(P((1.0, y), (15.0, y + 2.4)), fill=255)
    elif nazwa == 'przeciwbolowe':
        # tabletka w kształcie kapsułki, przekątna
        caps = Image.new('L', (S, S))
        dc = ImageDraw.Draw(caps)
        dc.rounded_rectangle([3.0 * u, 5.6 * u, 13.0 * u, 10.4 * u], radius=2.4 * u, fill=255)
        dc.rectangle([7.8 * u, 5.0 * u, 8.4 * u, 11.0 * u], fill=0)
        m = caps.rotate(40, resample=Image.BICUBIC)
    small = m.resize((32, 32), Image.LANCZOS)
    out = Image.new('RGBA', small.size)
    po, pm = out.load(), small.load()
    for y in range(32):
        for x in range(32):
            if pm[x, y]:
                po[x, y] = (255, 255, 255, pm[x, y])
    a = out.getpixel((31, 31))
    out.putpixel((31, 31), (a[0], a[1], a[2], max(a[3], 1)))
    return out


def ikony():
    return {n: _ikona(n) for n in IKONY}


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def znaki():
    """(znak, plik, wysokość, ascent) wszystkich znaków systemu zdrowia."""
    out = [(OBRYS, 'obrys', SYL_H, SYL_ASCENT)]
    out += [(CZESC_CP[c], c, SYL_H, SYL_ASCENT) for c in CZESCI]
    out += [(IKONA_CP[n], 'ikona_' + n, IKONA_H, IKONA_ASCENT) for n in IKONY]
    return out


def obrazy():
    out = dict(sylwetka())
    out.update({'ikona_' + n: img for n, img in ikony().items()})
    return out


def pliki():
    """Tekstury znaków (dostawców czcionek dokładają tablica.pliki() i hud.pliki())."""
    return {FONT_DIR + name + '.png': _png(img) for name, img in obrazy().items()}


def providers(delta=0, cp_map=None):
    """Dostawcy bitmap; delta przesuwa w dół (linie panelu HUD), cp_map zamienia numery znaków."""
    out = []
    for cp, name, h, asc in znaki():
        out.append({'type': 'bitmap', 'file': FONT_REF + name + '.png', 'height': h, 'ascent': asc - delta,
                    'chars': [chr(cp_map(cp) if cp_map else cp)]})
    return out


def advance(name):
    """Szerokość znaku jak w kliencie (wszystkie mają pełną szerokość płótna)."""
    return (SYL_W if name in CZESCI or name == 'obrys' else IKONA_H) + 1


def podglad(stany=None, skala=4, tlo=(24, 27, 36)):
    """Obrazek sylwetki zabarwionej stanami (część -> ułamek HP), do podglądów i testów."""
    stany = stany or {}
    imgs = sylwetka()
    W, H = imgs['glowa'].size
    out = Image.new('RGBA', (W, H), tlo + (255,))
    out.alpha_composite(imgs['obrys'])
    for c in CZESCI:
        f = stany.get(c, 1.0)
        kol = next(k for prog, k in KOLORY if f >= prog) if f > 0 else KOLORY[-1][1]
        g = imgs[c]
        r, gg, b, a = g.split()
        tint = Image.merge('RGBA', [r.point(lambda v, k=kol[0]: v * k // 255), gg.point(lambda v, k=kol[1]: v * k // 255),
                                    b.point(lambda v, k=kol[2]: v * k // 255), a])
        out.alpha_composite(tint)
    return out.resize((W * skala // SYL_SS, H * skala // SYL_SS), Image.LANCZOS)
