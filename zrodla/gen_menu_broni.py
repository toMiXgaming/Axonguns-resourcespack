#!/usr/bin/env python3
"""Menu akcesoriów broni AxonGuns (Shift+F): grafika okna jako czcionka axon:bron_menu.

Okno to zwykła skrzynia 6 rzędów (176×222 px GUI). Plugin składa tytuł okna z kafelków tła
(U+E000…), etykiety trybu ognia (U+E020…) i odstępów (U+E100…), a potem dopisuje nazwę broni
czcionką axon:ui_bold. Kafelki mają najwyżej 252×252 px, bo glif musi się zmieścić na stronie
atlasu czcionki (256 px). Rysowane 3× gęściej niż piksele GUI (ostre przy skali GUI 3).

Przy otwartym menu plugin wysyła graczowi czas gry z oknem AXON_GUN_MENU_TIME (jak AxonMap),
a shadery chowają wtedy tło skrzyni (generic_54.png ze znacznikiem w pikselu 255,255) i
przyciemnienie świata, żeby broń w pozie oglądania była widoczna przez okno.

Układ (miejsca, przyciski, kody znaków) musi zgadzać się z pl.axonguns.menu.MenuLayout.
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
CZCIONKI = os.path.join(HERE, 'axoncore', 'czcionki')
BOLD = os.path.join(CZCIONKI, 'Inter-Bold.ttf')
MEDIUM = os.path.join(CZCIONKI, 'Inter-Medium.ttf')

S = 3                       # pikseli tekstury na piksel GUI
TILE = 84                   # bok kafelka w px GUI (252 px tekstury)
X0, Y0 = -120, -10          # lewy górny róg tła względem okna skrzyni
COLS, ROWS = 5, 3           # 420 × 252 px GUI
TITLE_X, TITLE_Y = 8, 6     # gdzie klient rysuje tytuł okna

FONT = 'axon:bron_menu'
TEX = 'axon:font/bron_menu/'
TILE_CHAR = 0xE000          # kafelek (wiersz, kolumna) = TILE_CHAR + wiersz * COLS + kolumna
MODE_CHAR = 0xE020          # etykieta trybu ognia: auto, seria, pojedynczy
SPACE_CHAR = 0xE100         # odstępy ±2^k: E100+k dodatni, E110+k ujemny (k = 0…9)
MODES = [('auto', 'Ogień ciągły'), ('seria', 'Seria 3'), ('pojedynczy', 'Pojedynczy')]

# kolory motywu warsztatu AxonCore
BG = (36, 38, 40)
TILE_BG = (52, 55, 60)
EDGE = (60, 64, 68)
TEAL = (40, 120, 110)
ORANGE = (216, 127, 51)
TXT = (236, 240, 246)
SUB = (160, 166, 172)

# miejsca na akcesoria: (miejsce, podpis, kolumna, wiersz) w siatce 9×6 okna
SLOTS = [('luneta', 'Luneta', 0, 0), ('lufa', 'Lufa', 0, 1), ('latarka', 'Latarka', 0, 2), ('laser', 'Laser', 0, 3),
         ('chwyt', 'Chwyt', 8, 0), ('magazynek', 'Magazynek', 8, 1), ('kolba', 'Kolba', 8, 2), ('dwojnog', 'Dwójnóg', 8, 3)]
CLOSE = (0, 5)
MODE_BUTTON = (2, 6, 5)     # kolumny 2–6 w wierszu 5
STRIP = (8, 5)              # zdejmij wszystko
MODE_LABEL_X = 46           # lewa krawędź etykiety trybu (px GUI)


def cell(c, r):
    """Lewy górny róg ramki slotu (18×18) w px GUI względem okna."""
    return 7 + 18 * c, 17 + 18 * r


def _font(path, px):
    return ImageFont.truetype(path, round(px * S))


class Canvas:
    def __init__(self):
        self.img = Image.new('RGBA', (COLS * TILE * S, ROWS * TILE * S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    def xy(self, x, y):
        return round((x - X0) * S), round((y - Y0) * S)

    def rect(self, x, y, w, h, fill, outline=None, r=3.0, width=1.0, alpha=230):
        x0, y0 = self.xy(x, y)
        x1, y1 = self.xy(x + w, y + h)
        self.d.rounded_rectangle([x0, y0, x1 - 1, y1 - 1], round(r * S), fill=fill + (alpha,),
                                 outline=None if outline is None else outline + (255,), width=round(width * S))

    def text(self, x, y, s, font, fill, anchor='ls'):
        self.d.text(self.xy(x, y), s, font=font, fill=fill + (255,), anchor=anchor)

    def text_w(self, s, font):
        return self.d.textlength(s, font=font) / S


def slot_tile(cv, c, r, border=TEAL, fill=TILE_BG, alpha=110):
    x, y = cell(c, r)
    cv.rect(x, y, 18, 18, fill, border, r=3, width=1, alpha=alpha)


def tlo():
    cv = Canvas()
    label = _font(BOLD, 6.5)
    small = _font(MEDIUM, 6)
    # nagłówek: nazwę broni dopisuje plugin czcionką axon:ui_bold od x = 12
    cv.rect(1, -2, 174, 17, BG, EDGE, r=4, width=0.67, alpha=190)
    cv.rect(5, 2, 2, 9, ORANGE, None, r=1, alpha=255)
    sub = 'Akcesoria · Shift+F'
    cv.text(171 - cv.text_w(sub, small), 9.5, sub, small, SUB)
    # miejsca na akcesoria z podpisami na zewnątrz okna
    for slot, name, c, r in SLOTS:
        x, y = cell(c, r)
        w = cv.text_w(name, label) + 8
        px = x - 3 - w if c == 0 else x + 21
        cv.rect(px, y + 3, w, 12, BG, None, r=6, alpha=205)
        cv.text(px + 4, y + 11.5, name, label, TXT)
        slot_tile(cv, c, r)
    # przyciski w wierszu 5
    x, y = cell(*CLOSE)
    cv.rect(x, y, 18, 18, (70, 30, 32), (150, 60, 60), r=3, alpha=230)
    a, b = cv.xy(x + 5.5, y + 5.5)
    e, f = cv.xy(x + 12.5, y + 12.5)
    cv.d.line([a, b, e, f], fill=(255, 170, 170, 255), width=round(1.5 * S))
    cv.d.line([a, f, e, b], fill=(255, 170, 170, 255), width=round(1.5 * S))
    c0, c1, r = MODE_BUTTON
    x, y = cell(c0, r)
    x1, _ = cell(c1, r)
    cv.rect(x, y, x1 + 18 - x, 18, (70, 48, 30), ORANGE, r=4, alpha=230)
    x, y = cell(*STRIP)
    cv.rect(x, y, 18, 18, TILE_BG, TEAL, r=3, alpha=230)
    # strzałka w dół: zdejmij wszystko do ekwipunku
    cv.d.polygon([cv.xy(x + 9, y + 13.5), cv.xy(x + 5, y + 9), cv.xy(x + 7.5, y + 9), cv.xy(x + 7.5, y + 4.5),
                  cv.xy(x + 10.5, y + 4.5), cv.xy(x + 10.5, y + 9), cv.xy(x + 13, y + 9)], fill=TXT + (255,))
    cv.rect(x + 5, y + 14.5, 8, 1.2, TXT, None, r=0.5, alpha=255)
    # ekwipunek gracza (napis „Ekwipunek” rysuje klient w (8, 128))
    cv.rect(1, 126, 174, 95, BG, EDGE, r=5, width=0.67, alpha=225)
    for r in range(3):
        for c in range(9):
            cv.rect(7 + 18 * c, 139 + 18 * r, 18, 18, TILE_BG, (66, 70, 74), r=2.5, alpha=200)
    for c in range(9):
        cv.rect(7 + 18 * c, 197, 18, 18, TILE_BG, (66, 70, 74), r=2.5, alpha=200)
    return cv.img


def etykieta(text):
    """Napis trybu ognia: obraz TILE×18 px GUI wyśrodkowany na przycisku (lewa krawędź MODE_LABEL_X)."""
    c0, c1, r = MODE_BUTTON
    bx, _ = cell(c0, r)
    bx1, _ = cell(c1, r)
    center = (bx + bx1 + 18) / 2 - MODE_LABEL_X
    img = Image.new('RGBA', (TILE * S, 18 * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = _font(BOLD, 7)
    small = _font(MEDIUM, 6)
    a = 'Tryb: '
    wa = d.textlength(a, font=small)
    wb = d.textlength(text, font=f)
    x = center * S - (wa + wb) / 2
    d.text((x, 12.5 * S), a, font=small, fill=SUB + (255,), anchor='ls')
    d.text((x + wa, 12.5 * S), text, font=f, fill=TXT + (255,), anchor='ls')
    return img


def _png(img):
    out = io.BytesIO()
    img.save(out, 'PNG', optimize=True)
    return out.getvalue()


def _ascent(top):
    """Ascent glifu bitmapowego, którego górna krawędź ma być na y = top (px GUI) w oknie."""
    return TITLE_Y + 7 - top


def font_json():
    providers = []
    for r in range(ROWS):
        chars = ''.join(chr(TILE_CHAR + r * COLS + c) for c in range(COLS))
        providers.append({'type': 'bitmap', 'file': TEX + 'tlo_%d.png' % r, 'height': TILE,
                          'ascent': _ascent(Y0 + r * TILE), 'chars': [chars]})
    _, y = cell(MODE_BUTTON[0], MODE_BUTTON[2])
    for i, (mode, _) in enumerate(MODES):
        providers.append({'type': 'bitmap', 'file': TEX + 'tryb_%s.png' % mode, 'height': 18,
                          'ascent': _ascent(y), 'chars': [chr(MODE_CHAR + i)]})
    advances = {}
    for k in range(10):
        advances[chr(SPACE_CHAR + k)] = 2 ** k
        advances[chr(SPACE_CHAR + 0x10 + k)] = -(2 ** k)
    providers.append({'type': 'space', 'advances': advances})
    return json.dumps({'providers': providers}, ensure_ascii=False, indent=1) + '\n'


def generic_54_marker(src):
    """Tło skrzyni ze znacznikiem w pikselu (255, 255): po nim shader rozpoznaje tę teksturę."""
    img = Image.open(io.BytesIO(src)).convert('RGBA')
    img.putpixel((255, 255), (1, 2, 3, 4))
    return _png(img)


def pliki(generic_54=None):
    files = {}
    img = tlo()
    for r in range(ROWS):
        row = img.crop((0, r * TILE * S, COLS * TILE * S, (r + 1) * TILE * S))
        files['assets/axon/textures/font/bron_menu/tlo_%d.png' % r] = _png(row)
    for mode, text in MODES:
        files['assets/axon/textures/font/bron_menu/tryb_%s.png' % mode] = _png(etykieta(text))
    files['assets/axon/font/bron_menu.json'] = font_json().encode()
    # niewidoczny przedmiot na wolne miejsca i przyciski (opis widać po najechaniu)
    files['assets/axon/textures/item/menu_pusty.png'] = _png(Image.new('RGBA', (16, 16), (0, 0, 0, 0)))
    files['assets/axon/models/item/menu_pusty.json'] = (json.dumps(
        {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'axon:item/menu_pusty'}}) + '\n').encode()
    files['assets/axon/items/menu_pusty.json'] = (json.dumps(
        {'model': {'type': 'minecraft:model', 'model': 'axon:item/menu_pusty'}}) + '\n').encode()
    # miejsce, którego ta broń nie ma: ciemna kłódka
    lock = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(lock)
    d.rectangle([1, 1, 14, 14], fill=(20, 22, 24, 170))
    d.rectangle([5, 7, 10, 11], fill=(120, 124, 128, 255))
    d.arc([5, 3, 10, 9], 180, 360, fill=(120, 124, 128, 255), width=1)
    files['assets/axon/textures/item/menu_zablokowane.png'] = _png(lock)
    files['assets/axon/models/item/menu_zablokowane.json'] = (json.dumps(
        {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'axon:item/menu_zablokowane'}}) + '\n').encode()
    files['assets/axon/items/menu_zablokowane.json'] = (json.dumps(
        {'model': {'type': 'minecraft:model', 'model': 'axon:item/menu_zablokowane'}}) + '\n').encode()
    if generic_54 is not None:
        files['assets/minecraft/textures/gui/container/generic_54.png'] = generic_54_marker(generic_54)
    return files


def podglad(path):
    """Podgląd tła w skali GUI 3 (do sprawdzenia układu bez gry)."""
    img = tlo()
    bg = Image.new('RGBA', img.size, (98, 128, 74, 255))
    bg.alpha_composite(img)
    lab = etykieta('Ogień ciągły')
    _, y = cell(MODE_BUTTON[0], MODE_BUTTON[2])
    bg.alpha_composite(lab, ((MODE_LABEL_X - X0) * S, (y - Y0) * S))
    bg.save(path)


if __name__ == '__main__':
    import sys
    podglad(sys.argv[1] if len(sys.argv) > 1 else 'menu_broni.png')
