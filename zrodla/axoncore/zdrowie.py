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
(tak jak w Tarkovie). Postać ma proporcje gracza z Minecrafta (16 × 32 piksele skina, 1 px GUI na piksel),
z 1 px obrysu dookoła: znak ma SYL_W × SYL_H px GUI (advance SYL_W + 1)."""
import io

from PIL import Image, ImageDraw, ImageFilter

FONT_DIR = 'assets/axon/textures/font/zdrowie/'
FONT_REF = 'axon:font/zdrowie/'

SYL_W, SYL_H = 18, 34          # px GUI: postać 16 × 32 jak gracz z Minecrafta plus 1 px obrysu dookoła
SYL_SS = 4                     # tekstura 72×136: piksel skina = 4×4 teksele, ostry w HUD i w oknie powiększonym
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

# Postać jak gracz z Minecrafta widziany z przodu, w pikselach skina (x0, y0, x1, y1), siatka 16 × 32.
# Prawa ręka i noga gracza są po lewej stronie obrazka (postać stoi przodem). Klatka i brzuch to górna
# i dolna część tułowia (brzuch od linii paska w dół).
PROSTOKATY = {
    'glowa': (4, 0, 12, 8),
    'klatka': (4, 8, 12, 15),
    'brzuch': (4, 15, 12, 20),
    'reka_prawa': (0, 8, 4, 20),
    'reka_lewa': (12, 8, 16, 20),
    'noga_prawa': (4, 20, 8, 32),
    'noga_lewa': (8, 20, 12, 32),
}


def _odcienie(czesc):
    """Jasność każdego piksela skina części (0–255, biały do barwienia): ciemniejszy brzeg, światło z lewej
    i z góry, lekki szum jak w skinach oraz twarz, pasek i szwy."""
    import random
    import zlib
    rnd = random.Random(zlib.crc32(czesc.encode()))
    x0, y0, x1, y1 = PROSTOKATY[czesc]
    px = {}
    for y in range(y0, y1):
        for x in range(x0, x1):
            v = 232 - 30 * (y - y0) / max(1, y1 - y0 - 1) + rnd.randint(-9, 9)
            if x == x0 or y == y0:
                v += 14                                    # światło z lewej i z góry
            if x == x1 - 1 or y == y1 - 1:
                v -= 46                                    # cień na prawym i dolnym brzegu
            px[x, y] = v
    if czesc == 'glowa':
        for x in range(4, 12):                             # włosy (dwa górne rzędy) ciemniejsze
            px[x, 0] -= 50
            px[x, 1] -= 50
        px[4, 2] -= 50; px[11, 2] -= 50
        px[5, 4], px[10, 4] = 255, 255                     # białka oczu
        px[6, 4], px[9, 4] = 70, 70                        # źrenice
        px[7, 5] -= 30; px[8, 5] -= 30                     # nos
        for x in (6, 7, 8, 9):
            px[x, 6] -= 45                                 # usta
    elif czesc == 'klatka':
        px[7, 8] -= 35; px[8, 8] -= 35                     # dekolt
        px[7, 9] -= 25; px[8, 9] -= 25
    elif czesc == 'brzuch':
        for x in range(4, 12):
            px[x, 15] -= 55                                # pasek
        px[7, 15] += 60; px[8, 15] += 60                   # klamra
    elif czesc.startswith('reka'):
        for x in range(x0, x1):
            px[x, 18] += 12                                # dłoń jaśniejsza
            px[x, 19] += 12
            px[x, 17] -= 20                                # rękaw
    elif czesc.startswith('noga'):
        for x in range(x0, x1):
            px[x, 30] -= 40                                # buty
            px[x, 31] -= 40
    return {k: max(40, min(255, int(v))) for k, v in px.items()}


def _czesc(czesc):
    S = SYL_SS
    out = Image.new('RGBA', (SYL_W * S, SYL_H * S))
    d = ImageDraw.Draw(out)
    for (x, y), v in _odcienie(czesc).items():
        X, Y = (x + 1) * S, (y + 1) * S                    # +1: margines na obrys
        d.rectangle([X, Y, X + S - 1, Y + S - 1], fill=(v, v, v, 255))
    # cienki szew (1 teksel) dookoła części: ręce nie zlewają się z tułowiem przy tym samym kolorze
    x0, y0, x1, y1 = PROSTOKATY[czesc]
    px = out.load()
    for X in range((x0 + 1) * S, (x1 + 1) * S):
        for Y in range((y0 + 1) * S, (y1 + 1) * S):
            if X in ((x0 + 1) * S, (x1 + 1) * S - 1) or Y in ((y0 + 1) * S, (y1 + 1) * S - 1):
                r, g, b, a = px[X, Y]
                px[X, Y] = (r * 3 // 5, g * 3 // 5, b * 3 // 5, a)
    return out


def _stala_szerokosc(img):
    """Ostatnia kolumna niepusta: advance = SYL_W + 1 dla każdego znaku sylwetki."""
    a = img.getpixel((img.width - 1, img.height - 1))
    img.putpixel((img.width - 1, img.height - 1), (a[0], a[1], a[2], max(a[3], 1)))
    return img


def sylwetka():
    """Nazwa -> obrazek RGBA: 'obrys' i 7 części."""
    out = {c: _czesc(c) for c in CZESCI}
    S = SYL_SS
    full = Image.new('L', (SYL_W, SYL_H))
    for x0, y0, x1, y1 in PROSTOKATY.values():
        ImageDraw.Draw(full).rectangle([x0 + 1, y0 + 1, x1, y1], fill=255)
    obrys = full.filter(ImageFilter.MaxFilter(3)).resize((SYL_W * S, SYL_H * S), Image.NEAREST)
    cien = Image.new('RGBA', obrys.size)
    cien.putalpha(obrys.point(lambda v: 230 if v else 0))
    out['obrys'] = cien
    return {k: _stala_szerokosc(v) for k, v in out.items()}


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
    return out.resize((W * skala // SYL_SS, H * skala // SYL_SS), Image.NEAREST)
