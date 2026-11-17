"""Plakietki rang przy nicku (czat, lista graczy, nad głową): pikselowe tabliczki jako znaki czcionki.

Każda ranga to jeden znak z prywatnego obszaru Unicode w czcionce minecraft:default (U+EC00–U+EC1F):
kwadratowy żeton z ikoną i obok tabliczka z nazwą. Jeden znak, więc prefix w LuckPerms to po prostu
ten znak i spacja; EssentialsChat ({PREFIX}), TAB (%luckperms-prefix%) i nametagi biorą go same.

Rysunek jest w potrójnej rozdzielczości (27 px obrazka = 9 px GUI), więc napisy i ikony są drobniejsze
od zwykłego tekstu, ale dalej pikselowe. Znak ma wysokość 9 i ascent 8: wystaje 1 px nad wielkie litery
i 1 px pod linię bazową, więc mieści się w wierszu czatu (9 px) i nie nachodzi na sąsiednie.

Litery to własna czcionka 5×7 kropek (kropka = 2 px obrazka), z polskimi znakami.
Tabliczki i kody znaków muszą się zgadzać z AxonScoreboard (pack/RankBadges.java).

`pliki()` zwraca {ścieżka w zipie: bajty} i `providers()` wpisy do font/default.json;
woła je tablica.pliki() (ten sam default.json), więc build_pack.py i dodaj_tablice.py biorą je same."""
import io

from PIL import Image

FONT_DIR = 'assets/axon/textures/font/rangi/'
FONT_REF = 'axon:font/rangi/'
H = 27            # wysokość obrazka (3× GUI)
HEIGHT = 9        # wysokość znaku w GUI
ASCENT = 8
D = 2             # kropka czcionki = 2 px obrazka

# ---------------------------------------------------------------------------------------------
# czcionka 5×7 (kropki), akcenty nad literą w wierszach -2..-1
FONT = {
    'A': ['01110', '11011', '11011', '11111', '11011', '11011', '11011'],
    'B': ['11110', '11011', '11011', '11110', '11011', '11011', '11110'],
    'C': ['01111', '11000', '11000', '11000', '11000', '11000', '01111'],
    'D': ['11110', '11011', '11011', '11011', '11011', '11011', '11110'],
    'E': ['11111', '11000', '11000', '11110', '11000', '11000', '11111'],
    'F': ['11111', '11000', '11000', '11110', '11000', '11000', '11000'],
    'G': ['01111', '11000', '11000', '11011', '11011', '11011', '01111'],
    'H': ['11011', '11011', '11011', '11111', '11011', '11011', '11011'],
    'I': ['11', '11', '11', '11', '11', '11', '11'],
    'J': ['00011', '00011', '00011', '00011', '11011', '11011', '01110'],
    'K': ['11011', '11011', '11110', '11100', '11110', '11011', '11011'],
    'L': ['1100', '1100', '1100', '1100', '1100', '1100', '1111'],
    'M': ['0110110', '1111111', '1111111', '1101011', '1101011', '1100011', '1100011'],
    'N': ['110011', '111011', '111011', '111111', '110111', '110111', '110011'],
    'O': ['01110', '11011', '11011', '11011', '11011', '11011', '01110'],
    'P': ['11110', '11011', '11011', '11110', '11000', '11000', '11000'],
    'R': ['11110', '11011', '11011', '11110', '11110', '11011', '11011'],
    'S': ['01111', '11000', '11000', '01110', '00011', '00011', '11110'],
    'T': ['111111', '001100', '001100', '001100', '001100', '001100', '001100'],
    'U': ['11011', '11011', '11011', '11011', '11011', '11011', '01110'],
    'V': ['11011', '11011', '11011', '11011', '11011', '01110', '00100'],
    'W': ['1100011', '1100011', '1101011', '1101011', '1111111', '1111111', '0110110'],
    'X': ['11011', '11011', '01110', '00100', '01110', '11011', '11011'],
    'Y': ['11011', '11011', '11011', '01110', '00100', '00100', '00100'],
    'Z': ['11111', '00011', '00110', '01100', '11000', '11000', '11111'],
    '+': ['000', '000', '010', '111', '010', '000', '000'],
    ' ': ['00', '00', '00', '00', '00', '00', '00'],
}
# Ł: L z kreską, Ś/Ć/Ń/Ź: akcent nad literą
FONT['Ł'] = ['011000', '011000', '011011', '011110', '111000', '011000', '011111']
ACUTE = {'Ś': 'S', 'Ć': 'C', 'Ń': 'N', 'Ź': 'Z', 'Ó': 'O'}

# ---------------------------------------------------------------------------------------------
# ikony 10×10 kropek: znaki = indeks w palecie ikony
ICONS = {
    'korona': [
        '..........',
        '.3..3..3..',
        '.33.33.33.',
        '.11111111.',
        '.11211211.',
        '.11111111.',
        '.11111111.',
        '..........',
        '.33333333.',
        '..........',
    ],
    'tarcza': [
        '.11111111.',
        '.13333331.',
        '.13322331.',
        '.13222231.',
        '.13322331.',
        '.13322331.',
        '..133331..',
        '..113311..',
        '...1111...',
        '..........',
    ],
    'apteczka': [
        '...1111...',
        '...1..1...',
        '1111111111',
        '1111221111',
        '1111221111',
        '1122222211',
        '1122222211',
        '1111221111',
        '1111221111',
        '1111111111',
    ],
    'gwiazda': [
        '....11....',
        '...1331...',
        '...1311...',
        '1111111111',
        '.11111111.',
        '..111111..',
        '..111111..',
        '.111..111.',
        '.11....11.',
        '..........',
    ],
    'diament': [
        '..........',
        '..111111..',
        '.11211211.',
        '1111111111',
        '.11111111.',
        '..111111..',
        '...1111...',
        '....11....',
        '..........',
        '..........',
    ],
    'maska': [
        '..111111..',
        '.11111111.',
        '1122112211',
        '1122112211',
        '1111111111',
        '.11133111.',
        '..133331..',
        '..133331..',
        '...1111...',
        '..........',
    ],
}

# ---------------------------------------------------------------------------------------------
# rangi: znak, napis, ikona, kolor tabliczki, kolor napisu, kolory ikony {1,2,3}
# Grupa LuckPerms -> znak jest w AxonScoreboard (config: plakietki).
RANGI = [
    # (klucz,     znak,   napis,        ikona,      tabliczka,  napis-kolor,  ikona 1,   ikona 2,   ikona 3)
    ('wlasciciel', 0xEC00, 'WŁAŚCICIEL', 'korona',  (38, 34, 40), (255, 205, 70), (255, 196, 46), (200, 40, 60), (255, 236, 150)),
    ('moderator',  0xEC01, 'MOD',        'tarcza',  (40, 115, 215), (235, 245, 255), (220, 235, 255), (255, 255, 255), (40, 100, 200)),
    ('pomocnik',   0xEC02, 'POMOCNIK',   'apteczka', (55, 165, 70), (240, 255, 235), (240, 240, 240), (215, 40, 40), None),
    ('elita',      0xEC03, 'ELITA',      'gwiazda', (230, 160, 25), (255, 250, 220), (255, 215, 60), (255, 255, 200), (255, 250, 210)),
    ('vip',        0xEC04, 'VIP',        'diament', (140, 70, 210), (250, 240, 255), (110, 230, 255), (230, 255, 255), None),
    ('gracz',      0xEC05, 'OCALAŁY',    'maska',    (105, 110, 118), (235, 235, 230), (125, 140, 100), (150, 220, 255), (70, 75, 70)),
]


def _mix(c, k):
    """k>0 rozjaśnia do bieli, k<0 przyciemnia do czerni."""
    if k >= 0:
        return tuple(int(v + (255 - v) * k) for v in c[:3]) + (255,)
    return tuple(int(v * (1 + k)) for v in c[:3]) + (255,)


def _plate(img, x0, w, base):
    """Tabliczka: ciemny obrys, ścięte rogi, jaśniejsza góra, ciemniejszy dół, połysk."""
    px = img.load()
    out = _mix(base, -0.72)
    top, mid, bot = _mix(base, 0.18), base[:3] + (255,), _mix(base, -0.25)
    for y in range(H):
        for x in range(x0, x0 + w):
            lx, rx = x - x0, x0 + w - 1 - x
            ey = min(y, H - 1 - y)
            ex = min(lx, rx)
            if ex + ey < 2:          # ścięty róg
                continue
            if ex < 2 or ey < 2 or ex + ey < 4:
                px[x, y] = out
                continue
            if y < 4:
                c = _mix(base, 0.45)                     # górny połysk
            elif y >= H - 5:
                c = _mix(base, -0.45)                    # dolny cień
            else:
                t = (y - 4) / (H - 9)
                c = top if t < 0.35 else mid if t < 0.75 else bot
            if ex < 4 and 2 <= y < H - 2:
                c = _mix(c, 0.2 if lx < rx else -0.2)    # boki jak fazka
            px[x, y] = c
    # połysk: krótkie jasne kreski w lewym górnym rogu
    for i in range(3):
        px[x0 + 4 + i * 2, 4] = _mix(base, 0.75)


def _text_width(text):
    w = 0
    for ch in text:
        g = FONT[ACUTE.get(ch, ch)]
        w += len(g[0]) * D + D
    return w - D


def _text(img, x, y, text, color, shadow):
    px = img.load()
    for ch in text:
        g = FONT[ACUTE.get(ch, ch)]
        rows = [(r, row) for r, row in enumerate(g)]
        if ch in ACUTE:   # akcent: kreska nad środkiem, ukośnie
            cx = len(g[0]) // 2
            rows += [(-2, '0' * (cx + 1) + '1'), (-1, '0' * cx + '1')]
        for r, row in rows:
            for c, v in enumerate(row):
                if v != '1':
                    continue
                for dy in range(D):
                    for dx in range(D):
                        sx, sy = x + c * D + dx, y + r * D + dy
                        # cień: przesunięty o 1 px w dół i w prawo, tylko tam, gdzie nie ma litery
                        if 0 <= sy + 1 < H and 0 <= sx + 1 < img.width and px[sx + 1, sy + 1] != color:
                            px[sx + 1, sy + 1] = shadow
                        px[sx, sy] = color
        x += len(g[0]) * D + D


def _icon(img, x0, name, cols, base):
    """Kwadratowy żeton (27×27) z ikoną 10×10 kropek."""
    _plate(img, x0, H, _mix(base, -0.35))
    px = img.load()
    pal = {'1': cols[0], '2': cols[1], '3': cols[2] or cols[0]}
    shadow = _mix(base, -0.8)
    ox, oy = x0 + 3, 3
    grid = ICONS[name]
    cells = [(r, c, v) for r, row in enumerate(grid) for c, v in enumerate(row) if v != '.']
    for r, c, v in cells:   # cień o 1 px w dół i w prawo
        for dy in range(D):
            for dx in range(D):
                sx, sy = ox + c * D + dx + 1, oy + r * D + dy + 1
                if sx < x0 + H - 2 and sy < H - 2:
                    px[sx, sy] = shadow
    for r, c, v in cells:
        col = pal[v][:3] + (255,)
        for dy in range(D):
            for dx in range(D):
                px[ox + c * D + dx, oy + r * D + dy] = col


def plakietka(key):
    _, cp, text, icon, base, tcol, i1, i2, i3 = next(r for r in RANGI if r[0] == key)
    tw = _text_width(text)
    pw = tw + 14
    gap = 3
    img = Image.new('RGBA', (H + gap + pw, H))
    _icon(img, 0, icon, (i1, i2, i3), base)
    _plate(img, H + gap, pw, base)
    _text(img, H + gap + 7, 6, text, tcol[:3] + (255,), _mix(base, -0.6))
    return img


def obrazy():
    return {r[0]: plakietka(r[0]) for r in RANGI}


def advance(img):
    """Jak klient: ostatnia niepusta kolumna × skala, zaokrąglone, +1."""
    a = img.split()[3].load()
    actual = 0
    for x in range(img.width - 1, -1, -1):
        if any(a[x, y] for y in range(img.height)):
            actual = x + 1
            break
    return int(0.5 + actual * HEIGHT / img.height) + 1


def _png(img):
    b = io.BytesIO()
    img.save(b, 'PNG', optimize=True)
    return b.getvalue()


def sprawdz(imgs=None):
    imgs = imgs or obrazy()
    bledy = []
    for key, img in imgs.items():
        if img.width > 256 or img.height > 256:
            bledy.append('%s: obrazek %s większy niż 256 px' % (key, img.size))
    if len({r[1] for r in RANGI}) != len(RANGI):
        bledy.append('powtórzony znak rangi')
    if any(not 0xEC00 <= r[1] <= 0xEC1F for r in RANGI):
        bledy.append('znak rangi poza U+EC00–U+EC1F')
    return bledy


def providers():
    return [{'type': 'bitmap', 'file': FONT_REF + key + '.png', 'height': HEIGHT, 'ascent': ASCENT,
             'chars': [chr(cp)]} for key, cp, *_ in RANGI]


def pliki():
    imgs = obrazy()
    bledy = sprawdz(imgs)
    if bledy:
        raise SystemExit('rangi: ' + '; '.join(bledy))
    return {FONT_DIR + key + '.png': _png(img) for key, img in imgs.items()}


if __name__ == '__main__':
    for k, img in obrazy().items():
        print(k, img.size, 'advance', advance(img))
