#!/usr/bin/env python3
"""Dane menu akcesoriów AxonGuns (okno w stylu /ustawienia z bronią z boku).

Menu pokazuje prawdziwy model broni (ItemDisplay w oku gracza, kontekst NONE). Shader
rendertype_item_entity_translucent_cull przypina go do ekranu, a plugin przesuwa i skaluje go tak, żeby
środek broni stał w tym samym miejscu, a broń miała tę samą długość. Do tego potrzebuje:
- srodek: środek prostopadłościanu broni w blokach (układ przedmiotu: model / 16 - 0,5),
- dlugosc, wysokosc: rozmiar broni wzdłuż x i y w blokach (plugin dopasowuje broń do miejsca na ekranie),
- kotwice: miejsce → punkt na broni [u, v] w długościach broni od środka (u w prawo = w stronę lufy,
  v w górę); tu kończą się linie od kafelków miejsc,
- obrot: obrót modelu wokół osi y w stopniach (90/270 = model leży wzdłuż osi z, np. AWP i Uzi z QA; bez tego
  menu pokazuje taką broń od przodu; 180/270 = lufa modelu jest po stronie +x). Środek, rozmiary i kotwice są już po obrocie.

Rozmiary liczą się z narożników elementów po ich obrotach (część obrócona o 45° wystaje poza from/to).

Kotwica to środek modelu dodatku z gen_dodatki (lufa: tłumik albo kompensator, luneta: luneta albo
kolimator). Plik trafia do AxonGuns (src/main/resources/menu_bronie.json).
"""
import json

import numpy as np

WYGLADY = {'lufa': ('tlumik', 'kompensator'), 'luneta': ('luneta', 'kolimator'), 'chwyt': ('chwyt',),
           'latarka': ('latarka',), 'laser': ('laser',), 'magazynek': ('magazynek',), 'kolba': ('kolba',),
           'dwojnog': ('dwojnog',)}
PLIK = 'axonguns_menu.json'


def _narozniki(e):
    """8 narożników elementu po jego obrocie (rotation: origin, axis, angle), w jednostkach modelu."""
    a = np.array(e['from'], float)
    b = np.array(e['to'], float)
    pts = np.array([[x, y, z] for x in (a[0], b[0]) for y in (a[1], b[1]) for z in (a[2], b[2])])
    r = e.get('rotation')
    if r and r.get('angle'):
        t = np.radians(float(r['angle']))
        o = np.array(r.get('origin', [8, 8, 8]), float)
        c, s = np.cos(t), np.sin(t)
        q = pts - o
        if r.get('axis') == 'x':
            q = np.stack([q[:, 0], q[:, 1] * c - q[:, 2] * s, q[:, 1] * s + q[:, 2] * c], 1)
        elif r.get('axis') == 'y':
            q = np.stack([q[:, 0] * c + q[:, 2] * s, q[:, 1], -q[:, 0] * s + q[:, 2] * c], 1)
        else:
            q = np.stack([q[:, 0] * c - q[:, 1] * s, q[:, 0] * s + q[:, 1] * c, q[:, 2]], 1)
        pts = q + o
    return pts


def _obrocone(pts, obrot):
    """Punkty po obrocie modelu wokół y o 0/90/180/270° (jak AxisAngle w AxonItems): (x, y, z) → R_y · p."""
    if obrot == 90:
        return np.stack([pts[:, 2], pts[:, 1], -pts[:, 0]], 1)
    if obrot == 180:
        return np.stack([-pts[:, 0], pts[:, 1], -pts[:, 2]], 1)
    if obrot == 270:
        return np.stack([-pts[:, 2], pts[:, 1], pts[:, 0]], 1)
    return pts


def _punkty(model, obrot=0):
    """Narożniki wszystkich elementów w blokach (model / 16 - 0,5), po obrocie modelu."""
    return _obrocone(np.concatenate([_narozniki(e) for e in model['elements']]) / 16.0 - 0.5, obrot)


def _pudlo(model, obrot=0):
    pts = _punkty(model, obrot)
    return pts.min(0), pts.max(0)


def _obrot(model, lufa=None):
    """Obrót, po którym broń leży wzdłuż x lufą w stronę -x (jak reszta): 90/270, gdy model jest dłuższy
    wzdłuż z; 180/270, gdy lufa (model tłumika albo kompensatora, {@code lufa}) wypada po stronie +x."""
    lo, hi = _pudlo(model)
    wzdluz_z = hi[2] - lo[2] > hi[0] - lo[0]
    obrot = 90 if wzdluz_z else 0
    if lufa is not None and lufa.get('elements'):
        c = (lo + hi) / 2
        a, b = _pudlo(lufa)
        p = (a + b) / 2
        if (p[2] - c[2] if wzdluz_z else p[0] - c[0]) > 0:
            obrot += 180
    return obrot


def dane(bronie, modele, dodatki, dostepne):
    """bronie: [(numer, ref)], modele: ref -> model JSON broni, dodatki: pliki z gen_dodatki.pliki()."""
    out = {}
    for cmd, ref in bronie:
        nazwa = ref.split('/')[-1]
        baza = nazwa.split('_')[0]
        m = modele.get(ref)
        if not m or not m.get('elements'):
            continue
        lufa = None
        for w in WYGLADY['lufa']:
            plik = 'assets/axon/models/dodatki/%s_%s.json' % (baza, w)
            if dostepne.get((baza, w)) and plik in dodatki:
                lufa = json.loads(dodatki[plik])
                break
        obrot = _obrot(m, lufa)
        lo, hi = _pudlo(m, obrot)
        c = (lo + hi) / 2
        dl = float(hi[0] - lo[0])
        kotwice = {}
        for miejsce, wyglady in WYGLADY.items():
            for w in wyglady:
                plik = 'assets/axon/models/dodatki/%s_%s.json' % (baza, w)
                if not dostepne.get((baza, w)) or plik not in dodatki:
                    continue
                dm = json.loads(dodatki[plik])
                if not dm.get('elements'):
                    continue
                a, b = _pudlo(dm, obrot)
                p = (a + b) / 2
                kotwice[miejsce] = [round(float(p[0] - c[0]) / dl, 4), round(float(p[1] - c[1]) / dl, 4)]
                break
        out[str(cmd)] = {'model': nazwa, 'srodek': [round(float(x), 4) for x in c], 'dlugosc': round(dl, 4),
                         'wysokosc': round(float(hi[1] - lo[1]), 4), 'kotwice': kotwice}
        if obrot:
            out[str(cmd)]['obrot'] = obrot
    return (json.dumps({'bronie': out}, indent=1, ensure_ascii=False, sort_keys=True) + '\n').encode()


def pliki():
    """Przedmiot axon:gs_link: jeden kwadrat z kolorem z custom_model_data. Shader rysuje z niego linię
    od kafelka do kropki na broni (axon_gs.glsl), więc linia rysuje się po broni (przedmioty idą po napisach)."""
    item = {'model': {'type': 'minecraft:model', 'model': 'axon:item/gs_link',
                      'tints': [{'type': 'minecraft:custom_model_data', 'index': 0, 'default': 16777215}]}}
    model = {'textures': {'t': 'minecraft:block/white_concrete', 'particle': 'minecraft:block/white_concrete'},
             'elements': [{'from': [0, 0, 8], 'to': [16, 16, 8], 'shade': False,
                           'faces': {'south': {'uv': [0, 0, 16, 16], 'texture': '#t', 'tintindex': 0}}}]}
    return {'assets/axon/items/gs_link.json': (json.dumps(item, indent=1) + '\n').encode(),
            'assets/axon/models/item/gs_link.json': (json.dumps(model, indent=1) + '\n').encode()}
