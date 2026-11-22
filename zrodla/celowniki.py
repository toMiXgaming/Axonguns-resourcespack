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

CZARNY = [0, 0, 8, 16]
CZERWONY = [8, 0, 16, 16]


def _tekstura():
    img = Image.new('RGBA', (4, 4), (10, 10, 12, 255))
    for x in (2, 3):
        for y in range(4):
            img.putpixel((x, y), (255, 36, 28, 255))
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    return buf.getvalue()


def _box(x0, x1, y0, y1, uv, z0=Z0, z1=Z1):
    face = {'uv': uv, 'texture': '#t'}
    return {'from': [round(C + x0, 4), round(C + y0, 4), z0], 'to': [round(C + x1, 4), round(C + y1, 4), z1],
            'shade': False, 'faces': {k: dict(face) for k in ('north', 'south', 'east', 'west', 'up', 'down')}}


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
    # siatka: grube ramiona od brzegu okna do 40% promienia, cienki krzyż w środku z małą przerwą
    gr, cn, gap = 0.09, 0.022, 0.12
    w = 0.4 * R
    z = (Z0 - 0.02, Z0)
    els += [_box(-gr, gr, w, R, CZARNY, *z), _box(-gr, gr, -R, -w, CZARNY, *z),
            _box(-R, -w, -gr, gr, CZARNY, *z), _box(w, R, -gr, gr, CZARNY, *z),
            _box(-cn, cn, gap, w, CZARNY, *z), _box(-cn, cn, -w, -gap, CZARNY, *z),
            _box(-w, -gap, -cn, cn, CZARNY, *z), _box(gap, w, -cn, cn, CZARNY, *z)]
    # kreski odległości na dolnym ramieniu
    for k in (1, 2, 3):
        y = -gap - k * (w - gap) / 4
        els.append(_box(-0.12, 0.12, y - cn, y + cn, CZARNY, *z))
    return els


def _kropka(r=0.05):
    return [_box(-r, r, -r, r, CZERWONY, Z0 - 0.02, Z0)]


def _holo():
    els = _kropka(0.045)
    R, t = 1.1, 0.035
    for i in range(64):
        a = 2 * math.pi * i / 64
        x, y = R * math.cos(a), R * math.sin(a)
        els.append(_box(x - t, x + t, y - t, y + t, CZERWONY, Z0 - 0.02, Z0))
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
    els = {'luneta': _luneta, 'kolimator': _kropka, 'holo': _holo}[rodzaj]()
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
