#!/usr/bin/env python3
"""Dane menu akcesoriów AxonGuns (okno w stylu /ustawienia z bronią z boku).

Menu pokazuje prawdziwy model broni (ItemDisplay w oku gracza, kontekst NONE). Shader
rendertype_item_entity_translucent_cull przypina go do ekranu, a plugin przesuwa i skaluje go tak, żeby
środek broni stał w tym samym miejscu, a broń miała tę samą długość. Do tego potrzebuje:
- srodek: środek prostopadłościanu broni w blokach (układ przedmiotu: model / 16 - 0,5),
- dlugosc, wysokosc: rozmiar broni wzdłuż x i y w blokach (plugin dopasowuje broń do miejsca na ekranie),
- kotwice: miejsce → punkt na broni [u, v] w długościach broni od środka (u w prawo = w stronę lufy,
  v w górę); tu kończą się linie od kafelków miejsc.

Kotwica to środek modelu dodatku z gen_dodatki (lufa: tłumik albo kompensator, luneta: luneta albo
kolimator). Plik trafia do AxonGuns (src/main/resources/menu_bronie.json).
"""
import json

import numpy as np

WYGLADY = {'lufa': ('tlumik', 'kompensator'), 'luneta': ('luneta', 'kolimator'), 'chwyt': ('chwyt',),
           'latarka': ('latarka',), 'laser': ('laser',), 'magazynek': ('magazynek',), 'kolba': ('kolba',),
           'dwojnog': ('dwojnog',)}
PLIK = 'axonguns_menu.json'


def _pudlo(model):
    pts = np.array([e['from'] for e in model['elements']] + [e['to'] for e in model['elements']], float)
    return pts.min(0) / 16.0 - 0.5, pts.max(0) / 16.0 - 0.5


def dane(bronie, modele, dodatki, dostepne):
    """bronie: [(numer, ref)], modele: ref -> model JSON broni, dodatki: pliki z gen_dodatki.pliki()."""
    out = {}
    for cmd, ref in bronie:
        nazwa = ref.split('/')[-1]
        baza = nazwa.split('_')[0]
        m = modele.get(ref)
        if not m or not m.get('elements'):
            continue
        lo, hi = _pudlo(m)
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
                a, b = _pudlo(dm)
                p = (a + b) / 2
                kotwice[miejsce] = [round(float(p[0] - c[0]) / dl, 4), round(float(p[1] - c[1]) / dl, 4)]
                break
        out[str(cmd)] = {'model': nazwa, 'srodek': [round(float(x), 4) for x in c], 'dlugosc': round(dl, 4),
                         'wysokosc': round(float(hi[1] - lo[1]), 4), 'kotwice': kotwice}
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
