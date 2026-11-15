#!/usr/bin/env python3
"""Beczka z Minecrafta (blok `barrel` i `barrel_open`) jako pełna kostka z teksturą okrągłej beczki AxonCore.

Dlaczego: gra uznaje blok beczki za pełny i nieprzezroczysty, więc nie rysuje ścian sąsiadów, które do niej
przylegają (ziemi pod spodem, ścian obok, drugiej beczki w stosie). Okrągły model z gen_pojemniki.py nie
wypełniał narożników kostki, więc przez te narożniki było widać pustkę: niebo, jaskinie albo wnętrze świata
(„prześwitujące beczki”). Płaszczyzny `axon_wnetrze` (PR 48) tylko zamieniały to na czarną kostkę (PR 58).

Teraz model bloku to zwykła kostka (`cube_bottom_top`, jak w vanilli), a jej trzy tekstury są „zdjęciem”
okrągłej beczki: rzut z boku, z góry i z dołu tego samego modelu i tej samej tekstury co `axon:beczka`.
Okrągły model 3D zostaje bez zmian dla pojemników AXON-Structure (wyświetlacz przedmiotu nie zasłania sąsiadów).

Użycie: python3 beczka_blok.py [zip ...]   (bez argumentów: trzy zipy paczki i modele/axoncore)
gen_pojemniki.pliki() woła kostka(), więc podmien_pojemniki.py i pełna przebudowa dają to samo."""
import io
import json
import os
import sys
import zipfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']
VANILLA_BLOCKS = {'barrel': 'beczka', 'barrel_open': 'beczka_otwarta'}
RES = 64            # piksele tekstury na 16 jednostek modelu (4 na piksel modelu)
STARE = 'assets/axon/textures/block/vanilla/poj_%s.png'   # tekstura dawnego okrągłego modelu bloku (już nieużywana)


def _sample(tex, uv, a, b):
    """Piksel tekstury dla punktu (a, b) w [0, 1] na ścianie z danym uv (w jednostkach 0–16)."""
    h, w = tex.shape[:2]
    u = uv[0] + (uv[2] - uv[0]) * a
    v = uv[1] + (uv[3] - uv[1]) * b
    x = min(w - 1, max(0, int(u * w / 16)))
    y = min(h - 1, max(0, int(v * h / 16)))
    return tex[y, x]


def _rzut(model, tex, widok):
    """Rzut prostokątny modelu na ścianę kostki. Zwraca (rgb float RES×RES×3, głębia, maska pokrycia)."""
    rgb = np.zeros((RES, RES, 3))
    depth = np.full((RES, RES), np.inf)
    els = []
    for e in model['elements']:
        if e.get('rotation') and e['rotation'].get('angle', 0):
            continue                                 # w beczkach nie ma obróconych elementów; na wszelki wypadek pomijamy
        f = e['faces'].get({'bok': 'north', 'gora': 'up', 'dol': 'down'}[widok])
        if f is None or f.get('rotation', 0):
            continue
        els.append((e['from'], e['to'], f['uv']))
    for r in range(RES):
        for c in range(RES):
            p = (c + .5) * 16 / RES
            q = (r + .5) * 16 / RES
            for (x1, y1, z1), (x2, y2, z2), uv in els:
                if widok == 'bok':                    # patrzymy na północną ścianę: lewo = wschód (+x), góra = +y
                    x, y = 16 - p, 16 - q
                    if not (x1 <= x <= x2 and y1 <= y <= y2) or z1 >= depth[r, c]:
                        continue
                    d, a, b = z1, (x2 - x) / (x2 - x1), (y2 - y) / (y2 - y1)
                elif widok == 'gora':                 # z góry: u = x, v = z
                    x, z = p, q
                    if not (x1 <= x <= x2 and z1 <= z <= z2) or 16 - y2 >= depth[r, c]:
                        continue
                    d, a, b = 16 - y2, (x - x1) / (x2 - x1), (z - z1) / (z2 - z1)
                else:                                 # z dołu: u = x, v = 16 - z
                    x, z = p, 16 - q
                    if not (x1 <= x <= x2 and z1 <= z <= z2) or y1 >= depth[r, c]:
                        continue
                    d, a, b = y1, (x - x1) / (x2 - x1), (z2 - z) / (z2 - z1)
                px = _sample(tex, uv, a, b)
                if px[3] == 0:
                    continue
                depth[r, c] = d
                rgb[r, c] = px[:3]
    return rgb, depth, np.isfinite(depth)


def _wypelnij(rgb, mask, cieniuj_boki):
    """Domyka teksturę do pełnej kostki: piksele poza obrysem beczki dostają kolor najbliższego piksela beczki
    w tym samym wierszu (bok, jak cień na krzywiźnie) albo piksel bliżej środka (narożniki góry i dołu),
    przyciemniony."""
    out = rgb.copy()
    mid = (RES - 1) / 2
    for r in range(RES):
        for c in range(RES):
            if mask[r, c]:
                continue
            if cieniuj_boki:
                cols = np.nonzero(mask[r])[0]
                if len(cols) == 0:
                    continue
                src = (r, cols[np.argmin(np.abs(cols - c))])
            else:                                    # narożnik góry/dołu: ten sam materiał wzięty bliżej środka
                src = (int(round(mid + (r - mid) * 0.55)), int(round(mid + (c - mid) * 0.55)))
                if not mask[src]:
                    continue
            out[r, c] = rgb[src] * 0.55
    return out


def _png(rgb):
    img = np.clip(np.round(rgb), 0, 255).astype(np.uint8)
    alpha = np.full(img.shape[:2] + (1,), 255, np.uint8)
    b = io.BytesIO()
    Image.fromarray(np.concatenate([img, alpha], axis=2), 'RGBA').save(b, 'PNG', optimize=True)
    return b.getvalue()


def tekstury(model, png):
    """Trzy tekstury kostki (bok, góra, dół) z okrągłego modelu i jego tekstury."""
    tex = np.array(Image.open(io.BytesIO(png)).convert('RGBA')).astype(float)
    out = {}
    for widok in ('bok', 'gora', 'dol'):
        rgb, depth, mask = _rzut(model, tex, widok)
        if widok == 'bok':                           # krzywizna: ściany dalej od patrzącego są ciemniejsze
            d = depth[mask]
            k = np.ones_like(depth)
            k[mask] = 1 - 0.3 * (d - d.min()) / max(1e-6, d.max() - d.min())
            rgb = rgb * k[..., None]
        rgb = _wypelnij(rgb, mask, widok == 'bok')
        out[widok] = _png(rgb)
    return out


def kostka(n, model, png):
    """Ścieżka w zipie -> bajty: tekstury kostki dla beczki `n` (beczka / beczka_otwarta)."""
    return {'assets/axon/textures/block/vanilla/poj_%s_%s.png' % (n, w): b for w, b in tekstury(model, png).items()}


def model_bloku(n):
    t = 'axon:block/vanilla/poj_%s_' % n
    return (json.dumps({'parent': 'minecraft:block/cube_bottom_top',
                        'textures': {'top': t + 'gora', 'bottom': t + 'dol', 'side': t + 'bok', 'particle': t + 'bok'}},
                       indent=1) + '\n').encode()


def pliki(read):
    """Wszystkie pliki bloków beczki; read(ścieżka w zipie) zwraca bajty okrągłego modelu axon:beczka i jego tekstury."""
    f = {}
    for vanilla, n in VANILLA_BLOCKS.items():
        model = json.loads(read('assets/axon/models/block/%s.json' % n))
        png = read('assets/axon/textures/item/poj_%s.png' % n)
        f.update(kostka(n, model, png))
        f['assets/minecraft/models/block/%s.json' % vanilla] = model_bloku(n)
    return f


def patch_zip(path):
    with zipfile.ZipFile(path) as z:
        files = {i.filename: (i, z.read(i.filename)) for i in z.infolist()}
    new = pliki(lambda p: files[p][1])
    for n in VANILLA_BLOCKS.values():
        files.pop(STARE % n, None)
    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, (info, data) in files.items():
            if name not in new:
                zout.writestr(info, data)
        for name, data in new.items():
            zout.writestr(name, data)
    os.replace(tmp, path)
    return len(new)


def patch_dir(base):
    new = pliki(lambda p: open(os.path.join(base, p), 'rb').read())
    for n in VANILLA_BLOCKS.values():
        stara = os.path.join(base, STARE % n)
        if os.path.exists(stara):
            os.remove(stara)
    for name, data in new.items():
        dst = os.path.join(base, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(data)
    return len(new)


if __name__ == '__main__':
    args = sys.argv[1:]
    for p in args or [os.path.join(ROOT, n) for n in DEFAULT]:
        print(os.path.basename(p), patch_zip(p), 'plików')
    if not args:
        print('modele/axoncore', patch_dir(os.path.join(ROOT, 'modele', 'axoncore')), 'plików')
