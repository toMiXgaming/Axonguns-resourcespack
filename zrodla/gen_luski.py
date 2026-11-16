#!/usr/bin/env python3
"""Łuski AxonGuns: przedmioty axon:luska_pistolet, axon:luska_karabin, axon:luska_srut.

AxonGuns wyrzuca przy strzale łuskę jako przedmiot na ziemi (bez podnoszenia, znika po 2 s). Bez modelu
gracze widzieli zwykły materiał (sztabkę złota, czerwony barwnik). Plugin daje łusce item_model
axon:luska_<rodzaj>; tu są modele 3D (mosiężna łuska z szyjką, pistoletowa krótsza, czerwona łuska śrutowa
z mosiężnym denkiem) i jedna tekstura 16×16 axon:item/luski.

Użycie: python3 zrodla/gen_luski.py plik.zip [...] (build_pack.py i buduj_1_21_11.py wołają patch()).
"""
import io
import json
import os
import sys
import zipfile

from PIL import Image

TEX = 'assets/axon/textures/item/luski.png'
TEX_REF = 'axon:item/luski'

# kolory na teksturze 16×16: (x0, y0, x1, y1) w pikselach
MOSIADZ = (0, 0, 8, 8)
MOSIADZ_CIEMNY = (8, 0, 16, 8)
CZERWONY = (0, 8, 8, 16)
SPLONKA = (8, 8, 16, 16)


def tekstura():
    im = Image.new('RGBA', (16, 16))
    px = im.load()
    for y in range(16):
        for x in range(16):
            if x < 8 and y < 8:          # mosiądz z lekkim połyskiem
                c = (214, 170, 72) if (x + y) % 5 else (238, 204, 112)
            elif y < 8:                  # ciemniejszy mosiądz (krawędź, szyjka)
                c = (160, 118, 44)
            elif x < 8:                  # czerwony plastik śrutu
                c = (178, 34, 30) if (x * 3 + y) % 4 else (204, 52, 44)
            else:                        # spłonka
                c = (120, 112, 104) if (x - 12) ** 2 + (y - 12) ** 2 > 4 else (196, 160, 90)
            px[x, y] = c + (255,)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def _uv(r):
    return [r[0], r[1], r[2], r[3]]


def _box(fr, to, side, end=None):
    end = end or side
    faces = {}
    for f in ('north', 'south', 'east', 'west', 'up', 'down'):
        faces[f] = {'uv': _uv(end if f in ('north', 'south') else side), 'texture': '#0'}
    return {'from': fr, 'to': to, 'faces': faces}


def _round(cx, cy, z0, z1, r, side, end=None):
    """Prawie okrągły przekrój: krzyż z dwóch prostopadłościanów."""
    a = r * 0.6
    return [_box([cx - r, cy - a, z0], [cx + r, cy + a, z1], side, end),
            _box([cx - a, cy - r, z0], [cx + a, cy + r, z1], side, end)]


def modele():
    c = 8.0
    karabin = (_round(c, c, 5.6, 6.2, 1.15, MOSIADZ_CIEMNY, SPLONKA)       # kryza
               + _round(c, c, 6.2, 9.4, 1.05, MOSIADZ)                    # korpus
               + _round(c, c, 9.4, 10.0, 0.8, MOSIADZ_CIEMNY)             # zbieżność
               + _round(c, c, 10.0, 11.2, 0.6, MOSIADZ))                  # szyjka
    pistolet = (_round(c, c, 6.8, 7.3, 1.0, MOSIADZ_CIEMNY, SPLONKA)
                + _round(c, c, 7.3, 9.4, 0.95, MOSIADZ))
    srut = (_round(c, c, 5.4, 6.0, 1.55, MOSIADZ_CIEMNY, SPLONKA)
            + _round(c, c, 6.0, 7.2, 1.45, MOSIADZ)
            + _round(c, c, 7.2, 10.8, 1.4, CZERWONY))
    display = {
        'ground': {'rotation': [0, 0, 0], 'translation': [0, 1.5, 0], 'scale': [1.4, 1.4, 1.4]},
        'gui': {'rotation': [30, 45, 0], 'translation': [0, 0, 0], 'scale': [2.2, 2.2, 2.2]},
        'fixed': {'rotation': [0, 0, 0], 'translation': [0, 0, 0], 'scale': [2.0, 2.0, 2.0]},
        'thirdperson_righthand': {'rotation': [0, 0, 0], 'translation': [0, 2, 1], 'scale': [0.8, 0.8, 0.8]},
        'firstperson_righthand': {'rotation': [0, -20, 0], 'translation': [0, 3, 0], 'scale': [1.0, 1.0, 1.0]},
    }
    out = {}
    for nazwa, els in (('pistolet', pistolet), ('karabin', karabin), ('srut', srut)):
        model = {'credit': 'AXON - gen_luski.py', 'texture_size': [16, 16],
                 'textures': {'0': TEX_REF, 'particle': TEX_REF}, 'elements': els, 'display': display}
        out['assets/axon/models/item/luska_%s.json' % nazwa] = model
        out['assets/axon/items/luska_%s.json' % nazwa] = {
            'model': {'type': 'minecraft:model', 'model': 'axon:item/luska_%s' % nazwa}}
    return out


def pliki():
    out = {fn: (json.dumps(m, indent=1) + '\n').encode() for fn, m in modele().items()}
    out[TEX] = tekstura()
    return out


def patch(path):
    files = pliki()
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            if i.filename not in files:
                zout.writestr(i, zin.read(i.filename))
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 16, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    os.replace(tmp, path)
    print('gen_luski: %s, %d plików' % (os.path.basename(path), len(files)))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        patch(p)
