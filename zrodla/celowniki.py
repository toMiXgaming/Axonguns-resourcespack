#!/usr/bin/env python3
"""Widok przez celownik przy celowaniu (AxonGuns): luneta, kolimator i celownik holograficzny.

Zamiast patrzeć przez model lunety (rura, która zasłania pół ekranu) przy celowaniu klient rysuje płaską
nakładkę tuż przed kamerą, zawsze na środku ekranu, niezależnie od broni:
- luneta: czarna osłona z dużym okrągłym oknem (85% wysokości ekranu) i cienką siatką (grube ramiona
  na brzegach, cienki krzyż w środku); broni wtedy nie widać, jak w prawdziwej lunecie,
- kolimator: sama czerwona kropka na środku, broń i przyrządy widać dalej,
- holo: czerwony pierścień z kropką.

Nakładkę włącza flaga dodatku w custom_model_data (ta sama co model dodatku na broni, gen_dodatki.FLAG).
AWP i Dragunov mają lunetę w modelu, więc przy celowaniu zawsze dostają nakładkę lunety.

Ustawienie: przedmiot w pierwszej osobie ma stały FOV 70 (nie zmienia się z przybliżeniem), więc
nakładka w odległości ODL bloku przed okiem zawsze zajmuje to samo miejsce na ekranie.
Wariant „cel” to naładowana kusza (klient dokłada przesunięcie i obrót o 10°), „cel_u” zwykły przedmiot.
"""
import io
import json
import math

import numpy as np
from PIL import Image

from render import rot_axis

ODL = 0.12                      # bloki od oka do nakładki (bliska płaszczyzna klienta to 0,05)
SKALA = 0.14                    # 1 jednostka modelu = SKALA/16 bloku
POL_EKRANU = ODL * math.tan(math.radians(35))      # połowa wysokości ekranu na tej odległości (FOV ręki 70)
JEDN = SKALA / 16.0
R_OKNA = 0.85 * POL_EKRANU / JEDN                   # promień okna lunety w jednostkach modelu
ZASIEG = 24.0                   # osłona sięga ±24 jednostek od środka (szeroki ekran 21:9 też zakryty)
C = 8.0                         # środek modelu
Z0, Z1 = 8.0, 8.05

TEX = 'qualityarmory:axon/celownik'
TEX_PLIK = 'assets/qualityarmory/textures/axon/celownik.png'
MODEL_DIR = 'assets/axon/models/celownik/'
RODZAJE = ('luneta', 'kolimator', 'holo')

ARM_R = np.array([0.56, -0.52, -0.72])
CHARGED_T = np.array([-0.641864, 0.0, 0.0])
CHARGED_R = rot_axis('y', 10.0)

# tekstura 8×4: jeden kolor na kolumnę (uv w jednostkach 0–16, po 2 na kolumnę)
KOLORY = [(10, 10, 12, 255),       # 0 czerń (osłona, siatka)
          (46, 48, 53, 255),       # 1 obudowa
          (255, 40, 30, 255),      # 2 czerwień (kropka)
          (120, 175, 215, 46),     # 3 szybka
          (18, 19, 22, 255),       # 4 tubus przy oku
          (34, 36, 41, 255),       # 5 tubus w środku
          (58, 61, 68, 255),       # 6 tubus przy soczewce
          (96, 100, 108, 255),     # 7 obręcz soczewki
          ]


def _uv(i):
    return [2 * i, 0, 2 * i + 2, 16]


CZARNY, OBUDOWA, CZERWONY, SZYBKA = _uv(0), _uv(1), _uv(2), _uv(3)
TUBUS = [_uv(4), _uv(5), _uv(6)]
OBRECZ = _uv(7)


def _tekstura():
    img = Image.new('RGBA', (len(KOLORY), 4))
    for x, c in enumerate(KOLORY):
        for y in range(4):
            img.putpixel((x, y), c)
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def _box(x0, x1, y0, y1, uv, z0=Z0, z1=Z1):
    face = {'uv': uv, 'texture': '#t'}
    return {'from': [round(C + x0, 4), round(C + y0, 4), z0], 'to': [round(C + x1, 4), round(C + y1, 4), z1],
            'shade': False, 'faces': {k: dict(face) for k in ('north', 'south', 'east', 'west', 'up', 'down')}}


# Luneta 3D: osłona oka z oknem, za nią krótki tubus (w perspektywie widać jego ścianki, ciemne przy oku
# i jaśniejsze w głębi), obręcz soczewki z lekko przyciemnionym szkłem i siatka w głębi, na soczewce.
TUBUS_DL = 2.6                  # długość tubusu w jednostkach modelu (soczewka ~72% wysokości ekranu)
TUBUS_ZEW = 2.2                 # grubość ścianki tubusu (poza oknem, i tak zasłonięta osłoną)


def _luneta():
    els = []
    R, Z = R_OKNA, ZASIEG
    krok = 0.35
    n = int(math.ceil(2 * R / krok))
    for i in range(n):
        y0 = -R + i * krok
        y1 = min(R, y0 + krok)
        yc = max(abs(y0), abs(y1)) if y0 * y1 > 0 else 0.0      # zewnętrzna krawędź paska
        half = math.sqrt(max(0.0, R * R - yc * yc))
        els.append(_box(-Z, -half, y0, y1, CZARNY))
        els.append(_box(half, Z, y0, y1, CZARNY))
    els.append(_box(-Z, Z, R, Z, CZARNY))
    els.append(_box(-Z, Z, -Z, -R, CZARNY))
    # tubus: plastry od oka w głąb, coraz jaśniejsze
    zs = [Z0 - TUBUS_DL * k / 6 for k in range(7)]
    for k in range(6):
        els += _pierscien(R, R + TUBUS_ZEW, TUBUS[min(2, k // 2)], round(zs[k + 1], 4), round(zs[k], 4), krok=0.4)
    zf = round(zs[-1], 4)
    # obręcz soczewki i szkło
    rl = R - 0.45
    els += _pierscien(rl, R + 0.05, OBRECZ, zf - 0.15, zf + 0.05, krok=0.3)
    els += _pierscien(0, rl, SZYBKA, zf - 0.3, zf - 0.28, krok=0.4)
    # siatka na soczewce: grube ramiona od brzegu do 40% promienia, cienki krzyż w środku z małą przerwą
    gr, cn, gap = 0.08, 0.02, 0.11
    w = 0.4 * rl
    z = (zf - 0.25, zf - 0.23)
    els += [_box(-gr, gr, w, rl, CZARNY, *z), _box(-gr, gr, -rl, -w, CZARNY, *z),
            _box(-rl, -w, -gr, gr, CZARNY, *z), _box(w, rl, -gr, gr, CZARNY, *z),
            _box(-cn, cn, gap, w, CZARNY, *z), _box(-cn, cn, -w, -gap, CZARNY, *z),
            _box(-w, -gap, -cn, cn, CZARNY, *z), _box(gap, w, -cn, cn, CZARNY, *z)]
    for k in (1, 2, 3):
        y = -gap - k * (w - gap) / 4
        els.append(_box(-0.11, 0.11, y - cn, y + cn, CZARNY, *z))
    return els


def _kropka(r=0.09):
    return [_box(-r, r, -r, r, CZERWONY, Z0 - 0.02, Z0)]


def _pierscien(rin, rout, uv, z0, z1, krok=0.12):
    """Pierścień (rin = 0: koło) z poziomych pasków."""
    els = []
    n = int(math.ceil(2 * rout / krok))
    for i in range(n):
        y0 = -rout + i * krok
        y1 = min(rout, y0 + krok)
        ym = (y0 + y1) / 2
        if abs(ym) >= rout:
            continue
        xo = math.sqrt(rout * rout - ym * ym)
        if rin > 0 and abs(ym) < rin:
            xi = math.sqrt(rin * rin - ym * ym)
            els.append(_box(-xo, -xi, y0, y1, uv, z0, z1))
            els.append(_box(xi, xo, y0, y1, uv, z0, z1))
        else:
            els.append(_box(-xo, xo, y0, y1, uv, z0, z1))
    return els


# Kolimator (rura jak Aimpoint widziana od tyłu): obudowa wokół okna, przyciemniona szybka i jasna kropka.
KOL_OKNO, KOL_OBUDOWA = 2.3, 3.0


def _kolimator():
    els = _kropka()
    els += _pierscien(0, KOL_OKNO, SZYBKA, Z0 - 0.3, Z0 - 0.28)
    els += _pierscien(KOL_OKNO, KOL_OBUDOWA, OBUDOWA, Z0, Z1, krok=0.15)
    # pokrętło jasności z prawej i montaż pod spodem
    els.append(_box(KOL_OBUDOWA - 0.2, KOL_OBUDOWA + 0.55, -0.45, 0.45, OBUDOWA))
    els.append(_box(-1.6, 1.6, -KOL_OBUDOWA - 0.7, -KOL_OBUDOWA + 0.4, OBUDOWA))
    els.append(_box(-2.2, 2.2, -KOL_OBUDOWA - 1.1, -KOL_OBUDOWA - 0.7, CZARNY))
    return els


# Holo (prostokątne okno jak EOTech): rama z daszkiem, szybka, pierścień i kropka.
def _holo():
    els = _kropka(0.07)
    R, t = 1.3, 0.045
    for i in range(72):
        a = 2 * math.pi * i / 72
        x, y = R * math.cos(a), R * math.sin(a)
        els.append(_box(x - t, x + t, y - t, y + t, CZERWONY, Z0 - 0.02, Z0))
    wx, wy0, wy1 = 3.4, -2.4, 2.6          # okno
    fx, fy0, fy1 = 4.2, -3.2, 3.5          # rama
    els.append(_box(-wx, wx, wy0, wy1, SZYBKA, Z0 - 0.3, Z0 - 0.28))
    els += [_box(-fx, -wx, fy0, fy1, OBUDOWA), _box(wx, fx, fy0, fy1, OBUDOWA),
            _box(-wx, wx, wy1, fy1, OBUDOWA), _box(-wx, wx, fy0, wy0, OBUDOWA),
            _box(-fx - 0.2, fx + 0.2, fy1 - 0.25, fy1 + 0.2, CZARNY),               # daszek
            _box(-fx, fx, fy0 - 1.0, fy0, CZARNY)]                                   # podstawa z baterią
    return els


def _display(charged):
    """Nakładka prostopadle do osi widoku, środek modelu ODL bloku przed okiem."""
    cel = np.array([0.0, 0.0, -ODL])
    if charged:
        t = CHARGED_R.T @ (cel - ARM_R - CHARGED_T)
        rot = [0.0, -10.0, 0.0]
    else:
        t = cel - ARM_R
        rot = [0.0, 0.0, 0.0]
    t16 = [round(float(x) * 16, 4) for x in t]
    assert all(abs(x) <= 80 for x in t16), t16
    return {'firstperson_righthand': {'rotation': rot, 'translation': t16, 'scale': [SKALA] * 3}}


def model(rodzaj):
    els = {'luneta': _luneta, 'kolimator': _kolimator, 'holo': _holo}[rodzaj]()
    for e in els:
        for k in (0, 1, 2):
            assert -16 <= e['from'][k] <= 32 and -16 <= e['to'][k] <= 32, e
    return {'credit': 'AXON - celowniki.py', 'ambientocclusion': False,
            'textures': {'t': TEX, 'particle': TEX}, 'elements': els}


def ref(rodzaj, wariant):
    return 'axon:celownik/%s/%s' % (wariant, rodzaj)


def pliki():
    out = {TEX_PLIK: _tekstura()}
    for r in RODZAJE:
        out[MODEL_DIR + '%s.json' % r] = (json.dumps(model(r), indent=1) + '\n').encode()
        for wariant, charged in (('cel', True), ('cel_u', False)):
            child = {'parent': 'axon:celownik/%s' % r, 'display': _display(charged)}
            out[MODEL_DIR + '%s/%s.json' % (wariant, r)] = (json.dumps(child, indent=1) + '\n').encode()
    return out
