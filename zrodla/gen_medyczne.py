#!/usr/bin/env python3
"""Przedmioty medyczne AxonCore (system zdrowia w Axon-items): bandaż, opaska uciskowa, apteczka mała,
apteczka wojskowa, szyna, środki przeciwbólowe i zestaw chirurgiczny.

Modele 3D z prostopadłościanów z własną teksturą 256x256 (silnik z gen_narzedzia.py, jak granaty i apteczka
QualityArmory w gen_przedmioty.py). Przedmiot w grze to `axon:<nazwa>` (komponent item_model), model
`axon:block/<nazwa>`, tekstura `axon:item/med_<nazwa>`.

python3 gen_medyczne.py [nazwa ...]  ->  build/med_<nazwa>.json|png
Do zipów: python3 dodaj_medyczne.py (pełna przebudowa: gen_axoncore.pliki() bierze je z build/)."""
import json, os, sys
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen_narzedzia as N
import gen_przedmioty  # noqa: F401  (materiały: plastic, canvas, rag, redcross, label)
from gen_narzedzia import Tool, MATS
from gen_przedmioty import octo

OUT = N.OUT
NAMES = ['bandage', 'tourniquet', 'first_aid_kit', 'military_medkit', 'splint', 'painkillers', 'surgical_kit']

MATS.update({
    'gauze': dict(kind='t_cloth', base=(226, 222, 206), wear=(244, 242, 232), edge=0.25, stain=(196, 186, 160)),
    'gauze_d': dict(kind='t_cloth', base=(196, 190, 170), wear=(222, 218, 200), edge=0.25, stain=(160, 150, 120)),
    'blood': dict(kind='t_cloth', base=(120, 22, 20), wear=(150, 40, 34), edge=0.2, stain=(80, 12, 12)),
    'strap': dict(kind='t_cloth', base=(36, 38, 36), wear=(70, 72, 70), edge=0.3, stain=(24, 26, 24)),
    'strap_o': dict(kind='t_cloth', base=(64, 70, 46), wear=(100, 106, 76), edge=0.3, stain=(44, 48, 32)),
    'tab_red': dict(kind='t_rubber', base=(178, 36, 30), wear=(214, 72, 60), edge=0.3),
    'pouch_red': dict(kind='t_cloth', base=(150, 44, 36), wear=(186, 76, 62), edge=0.3, stain=(104, 30, 24)),
    'pouch_red_d': dict(kind='t_cloth', base=(116, 32, 28), wear=(150, 56, 46), edge=0.3, stain=(80, 22, 18)),
    'white_patch': dict(kind='t_rubber', base=(232, 230, 222), wear=(250, 250, 244), edge=0.2),
    'pill': dict(kind='t_rubber', base=(196, 112, 36), wear=(232, 158, 72), edge=0.25),
    'cap_white': dict(kind='t_rubber', base=(222, 222, 214), wear=(244, 244, 238), edge=0.3),
    'enamel': dict(kind='t_rubber', base=(206, 208, 198), wear=(236, 238, 230), edge=0.35),
})

# wspólny układ w ręce, na ziemi i w ekwipunku (model leży w kratce 0..16, spodem na y = 0)
DISPLAY = {
    'gui': {'rotation': [30, 45, 0], 'translation': [0, 0, 0], 'scale': [0.9, 0.9, 0.9]},
    'ground': {'translation': [0, 2, 0], 'scale': [0.5, 0.5, 0.5]},
    'fixed': {'translation': [0, 0, 0], 'scale': [0.9, 0.9, 0.9]},
    'firstperson_righthand': {'rotation': [0, -25, 0], 'translation': [1.5, 3.5, 0], 'scale': [0.55, 0.55, 0.55]},
    'firstperson_lefthand': {'rotation': [0, 25, 0], 'translation': [1.5, 3.5, 0], 'scale': [0.55, 0.55, 0.55]},
    'thirdperson_righthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [0.45, 0.45, 0.45]},
    'thirdperson_lefthand': {'rotation': [75, 45, 0], 'translation': [0, 2.5, 0], 'scale': [0.45, 0.45, 0.45]},
    'head': {'translation': [0, 14, 0], 'scale': [0.8, 0.8, 0.8]},
}


def cross(t, x0, x1, y0, y1, z, sg, mat='redcross', bg=None):
    """Krzyż na ściance z = z (sg = -1 przód, +1 tył), opcjonalnie na białej łacie."""
    a, b = (z - 0.1, z) if sg < 0 else (z, z + 0.1)
    if bg:
        a2, b2 = (z - 0.06, z) if sg < 0 else (z, z + 0.06)
        t.box((x0 - 0.5, y0 - 0.5, a2), (x1 + 0.5, y1 + 0.5, b2), bg, 'patch')
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w = (x1 - x0) / 3
    t.box((cx - w / 2, y0, a), (cx + w / 2, y1, b), mat, 'cross')
    t.box((x0, cy - w / 2, a), (x1, cy + w / 2, b), mat, 'cross')


def cross_top(t, x0, x1, z0, z1, y, mat='redcross', bg=None):
    """Krzyż na wierzchu (płaszczyzna y)."""
    if bg:
        t.box((x0 - 0.5, y, z0 - 0.5), (x1 + 0.5, y + 0.06, z1 + 0.5), bg, 'patch')
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    w = (x1 - x0) / 3
    t.box((cx - w / 2, y, z0), (cx + w / 2, y + 0.1, z1), mat, 'cross')
    t.box((x0, y, cz - w / 2), (x1, y + 0.1, cz + w / 2), mat, 'cross')


def bandage():
    """Rolka gazy z odwiniętym końcem i papierową banderolą."""
    t = Tool('med_bandage')
    x, z = 7.2, 7.6
    octo(t, x, z, 0.0, 5.0, 3.4, 'gauze', 'roll')
    octo(t, x, z, 0.3, 4.7, 3.52, 'gauze_d', 'layer')          # warstwy na brzegu rolki
    t.vcyl(x, z, 5.0, 5.08, 1.1, 'black', k=0.72, tag='hole')            # gilza w środku
    octo(t, x, z, 1.7, 3.3, 3.62, 'label', 'band')            # banderola
    t.box((x - 1.3, 2.1, z - 3.68), (x + 1.3, 2.9, z - 3.62), 'redcross', 'stripe')
    # odwinięty koniec leżący na ziemi
    t.box((x + 2.4, 0.0, z - 1.8), (x + 8.2, 0.25, z + 1.6), 'gauze', 'tail')
    t.box((x + 2.2, 0.25, z - 1.8), (x + 2.6, 3.6, z + 1.6), 'gauze', 'tailup')
    t.box((x + 6.6, 0.25, z - 1.2), (x + 7.6, 0.32, z + 0.4), 'blood', 'stain')
    return t


def tourniquet():
    """Opaska uciskowa: czarna taśma w pętli, drążek skręcający i czerwona zakładka."""
    t = Tool('med_tourniquet')
    x0, x1, z0, z1 = 2.0, 14.0, 4.0, 12.0
    h = 1.6
    t.box((x0, 0.0, z0), (x1, h, z0 + 1.0), 'strap', 'strap')
    t.box((x0, 0.0, z1 - 1.0), (x1, h, z1), 'strap', 'strap')
    t.box((x0, 0.0, z0 + 1.0), (x0 + 1.0, h, z1 - 1.0), 'strap', 'strap')
    t.box((x1 - 1.0, 0.0, z0 + 1.0), (x1, h, z1 - 1.0), 'strap', 'strap')
    for xs in (4.0, 6.0, 8.0, 10.0, 12.0):                                 # przeszycia na taśmie
        t.box((xs, h, z0 + 0.2), (xs + 0.25, h + 0.04, z0 + 0.8), 'strap_o', 'stitch')
    t.box((6.0, h, z0 - 0.3), (10.0, h + 0.9, z0 + 1.3), 'black', 'clip')    # klamra z drążkiem
    t.box((7.6, h + 0.9, z0 - 3.0), (8.4, h + 1.7, z0 + 4.2), 'black_e', 'rod')
    t.box((7.4, h + 0.8, z0 - 3.2), (8.6, h + 1.9, z0 - 2.6), 'black', 'rodend')
    t.box((7.4, h + 0.8, z0 + 3.9), (8.6, h + 1.9, z0 + 4.5), 'black', 'rodend')
    t.box((x1 - 3.2, 0.0, z1 - 0.2), (x1 + 1.4, 0.9, z1 + 1.6), 'tab_red', 'tab')      # zakładka do ciągnięcia
    t.box((x1 - 2.6, 0.9, z1 + 0.2), (x1 - 1.2, 0.95, z1 + 1.3), 'white_patch', 'tabmark')
    t.box((x0 + 0.2, h, z1 - 0.8), (x0 + 3.2, h + 0.06, z1 - 0.2), 'white_patch', 'label')   # pole na godzinę
    return t


def first_aid_kit():
    """Mała apteczka: czerwona saszetka na zamek z białym krzyżem."""
    t = Tool('med_first_aid_kit')
    x0, x1, y0, y1, z0, z1 = 3.0, 13.0, 0.0, 3.6, 4.5, 11.5
    t.box((x0, y0, z0), (x1, y1, z1), 'pouch_red', 'body')
    t.box((x0 - 0.2, 0.3, z0 + 0.3), (x1 + 0.2, y1 - 0.3, z1 - 0.3), 'pouch_red', 'side')
    t.box((x0 + 0.3, y1, z0 + 0.3), (x1 - 0.3, y1 + 0.3, z1 - 0.3), 'pouch_red', 'top')
    t.box((x0 - 0.25, 1.65, z0 - 0.05), (x1 + 0.25, 1.95, z1 + 0.05), 'black', 'zip')     # zamek dookoła
    t.box((x1 + 0.2, 1.4, z0 + 1.0), (x1 + 0.9, 2.2, z0 + 1.6), 'steel', 'puller')
    t.box((x1 + 0.9, 1.5, z0 + 1.1), (x1 + 1.9, 2.1, z0 + 1.5), 'strap', 'pullcord')
    cross_top(t, 6.0, 10.0, 6.0, 10.0, y1 + 0.3, mat='white_patch')
    t.box((x0 + 0.6, y1 + 0.3, z1 - 1.4), (x0 + 3.0, y1 + 0.36, z1 - 0.7), 'label', 'label')
    t.box((5.5, y1 + 0.3, z0 - 0.4), (10.5, y1 + 0.7, z0 + 0.4), 'strap', 'loop')          # uchwyt
    return t


def military_medkit():
    """Apteczka wojskowa: oliwkowa ładownica z klapą, taśmami MOLLE, sprzączkami i naszywką z krzyżem."""
    t = Tool('med_military_medkit')
    x0, x1, z0, z1 = 2.0, 14.0, 4.0, 12.0
    t.box((x0, 0.0, z0), (x1, 6.0, z1), 'canvas', 'body')
    t.box((x0 - 0.2, 0.3, z0 + 0.3), (x1 + 0.2, 5.7, z1 - 0.3), 'canvas', 'side')
    t.box((x0 + 0.1, 6.0, z0 - 0.1), (x1 - 0.1, 7.0, z1 + 0.1), 'canvas_d', 'flap')        # klapa
    t.box((x0 + 0.1, 3.8, z0 - 0.2), (x1 - 0.1, 7.0, z0 + 0.1), 'canvas_d', 'flapfront')
    t.box((x0 + 0.4, 3.8, z0 - 0.26), (x1 - 0.4, 4.0, z0 - 0.2), 'black', 'flapedge')
    for xs in (3.6, 11.4):                                                                  # taśmy ze sprzączkami
        t.box((xs - 0.6, 1.2, z0 - 0.32), (xs + 0.6, 6.95, z0 - 0.2), 'strap_o', 'strap')
        t.box((xs - 0.8, 2.6, z0 - 0.5), (xs + 0.8, 3.4, z0 - 0.3), 'black', 'buckle')
    for yy in (1.0, 2.6, 4.2):                                                              # MOLLE z tyłu
        t.box((x0 + 0.5, yy, z1), (x1 - 0.5, yy + 0.8, z1 + 0.15), 'strap_o', 'molle')
    cross(t, 6.0, 10.0, 4.4, 6.6, z0 - 0.26, -1, mat='redcross', bg='white_patch')
    cross_top(t, 6.5, 9.5, 6.5, 9.5, 7.0, mat='redcross', bg='white_patch')
    t.box((7.0, 7.0, z1 - 0.8), (9.0, 7.6, z1 + 0.6), 'strap_o', 'pull')                   # uchwyt do wyrwania
    t.box((x0 - 0.3, 0.0, z0 + 0.4), (x0, 5.8, z1 - 0.4), 'canvas_d', 'edge')
    t.box((x1, 0.0, z0 + 0.4), (x1 + 0.3, 5.8, z1 - 0.4), 'canvas_d', 'edge')
    return t


def splint():
    """Szyna z dwóch deszczułek owiniętych bandażem (PRL: z tego, co pod ręką)."""
    t = Tool('med_splint')
    for z0 in (5.2, 9.0):
        t.box((1.0, 0.0, z0), (15.0, 0.9, z0 + 1.8), 'w_light', 'slat')
        t.box((1.0, 0.9, z0 + 0.2), (15.0, 1.0, z0 + 1.6), 'w_old', 'grain')
    for xs, w in ((2.6, 1.4), (7.4, 1.6), (12.2, 1.4)):                                     # owijki z gazy
        t.box((xs, -0.0, 5.0), (xs + w, 1.3, 11.0), 'gauze', 'wrap')
        t.box((xs + 0.2, 1.3, 5.1), (xs + w - 0.2, 1.4, 10.9), 'gauze_d', 'wrapline')
    t.box((8.0, 0.0, 11.0), (9.6, 0.25, 14.4), 'gauze', 'tail')                            # luźny koniec
    t.box((1.0, 0.0, 7.0), (15.0, 0.6, 9.0), 'rag', 'padding')                             # podkładka
    return t


def painkillers():
    """Słoiczek tabletek z białą nakrętką i etykietą, obok dwie tabletki."""
    t = Tool('med_painkillers')
    x, z = 7.0, 7.4
    octo(t, x, z, 0.0, 6.6, 2.4, 'pill', 'jar')
    octo(t, x, z, 6.6, 8.4, 2.55, 'cap_white', 'cap')
    for yy in (6.9, 7.5, 8.1):                                                              # rowki nakrętki
        octo(t, x, z, yy, yy + 0.2, 2.62, 'plastic_g', 'ridge')
    octo(t, x, z, 1.6, 5.2, 2.48, 'label', 'label')
    t.box((x - 1.4, 3.6, z - 2.56), (x + 1.4, 4.4, z - 2.5), 'redcross', 'stripe')
    t.box((x - 1.0, 2.2, z - 2.56), (x + 1.0, 2.6, z - 2.5), 'black', 'text')
    for px, pz in ((11.6, 6.0), (12.4, 9.4)):                                               # tabletki
        t.box((px - 0.8, 0.0, pz - 0.8), (px + 0.8, 0.6, pz + 0.8), 'cap_white', 'pill')
        t.box((px - 0.6, 0.6, pz - 0.05), (px + 0.6, 0.64, pz + 0.05), 'plastic_g', 'score')
    return t


def surgical_kit():
    """Zestaw chirurgiczny: emaliowana kaseta z zatrzaskami, krzyżem i taśmą."""
    t = Tool('med_surgical_kit')
    x0, x1, z0, z1 = 1.5, 14.5, 4.0, 12.0
    t.box((x0, 0.0, z0), (x1, 2.2, z1), 'enamel', 'case')
    t.box((x0 - 0.1, 2.2, z0 - 0.1), (x1 + 0.1, 3.4, z1 + 0.1), 'enamel', 'lid')
    t.box((x0 - 0.15, 2.1, z0 - 0.15), (x1 + 0.15, 2.3, z1 + 0.15), 'steel_d', 'seam')
    t.box((x0 + 0.6, 3.4, z0 + 0.6), (x1 - 0.6, 3.5, z1 - 0.6), 'enamel', 'lidtop')
    for xl in (3.6, 11.4):                                                                  # zatrzaski
        t.box((xl - 0.7, 1.2, z0 - 0.3), (xl + 0.7, 3.0, z0 - 0.1), 'steel_l', 'latch')
        t.box((xl - 0.3, 1.6, z0 - 0.4), (xl + 0.3, 2.0, z0 - 0.3), 'steel_d', 'latch')
    for xh in (4.0, 12.0):                                                                  # zawiasy z tyłu
        t.box((xh - 0.8, 2.0, z1 + 0.1), (xh + 0.8, 2.6, z1 + 0.35), 'steel', 'hinge')
    cross_top(t, 6.3, 9.7, 6.3, 9.7, 3.5, mat='redcross')
    t.box((x0 + 0.8, 3.5, z0 + 1.0), (x0 + 3.4, 3.56, z0 + 2.2), 'label', 'label')
    # skalpel i nici leżące obok
    t.box((3.0, 0.0, 13.0), (9.0, 0.35, 13.6), 'steel_l', 'scalpel')
    t.box((9.0, 0.0, 13.05), (11.2, 0.3, 13.55), 'edge', 'blade')
    t.vcyl(12.6, 13.6, 0.0, 0.7, 1.0, 'cord', k=0.72, tag='thread')
    return t


def center(model):
    """Środek bryły w (8, 8, 8): w slocie i w ręce przedmiot nie siedzi przy dolnej krawędzi."""
    els = model['elements']
    for a in range(3):
        lo = min(e['from'][a] for e in els)
        hi = max(e['to'][a] for e in els)
        d = round(8 - (lo + hi) / 2, 3)
        for e in els:
            e['from'][a] = round(e['from'][a] + d, 4)
            e['to'][a] = round(e['to'][a] + d, 4)
            if 'rotation' in e:
                e['rotation']['origin'][a] = round(e['rotation']['origin'][a] + d, 4)


BUILD = {n: globals()[n] for n in NAMES}


def render(n):
    t = BUILD[n]()
    model, img, dens, nf = t.save('axon:item/med_' + n, DISPLAY, tool_rot=False)
    center(model)
    json.dump(model, open(os.path.join(OUT, 'med_%s.json' % n), 'w'), indent=1)
    Image.fromarray(img, 'RGBA').save(os.path.join(OUT, 'med_%s.png' % n))
    print(n, 'elements', len(model['elements']), 'faces', nf, 'density', dens, flush=True)


def pliki(src=None, nakladka_1_21_0=True):
    """Ścieżka w zipie -> bajty (z build/ albo z podanego katalogu)."""
    src = src or OUT
    files = {}
    for n in NAMES:
        files['assets/axon/models/block/%s.json' % n] = open(os.path.join(src, 'med_%s.json' % n), 'rb').read()
        files['assets/axon/textures/item/med_%s.png' % n] = open(os.path.join(src, 'med_%s.png' % n), 'rb').read()
        files['assets/axon/items/%s.json' % n] = json.dumps(
            {'model': {'type': 'minecraft:model', 'model': 'axon:block/' + n}}, indent=2).encode()
        if nakladka_1_21_0:
            files['axon_1_21_0/assets/axon/models/item/%s.json' % n] = json.dumps(
                {'parent': 'axon:block/' + n}, indent=2).encode()
    return files


def main(want=()):
    os.makedirs(OUT, exist_ok=True)
    for n in NAMES:
        if not want or n in want:
            render(n)


if __name__ == '__main__':
    main(sys.argv[1:])
