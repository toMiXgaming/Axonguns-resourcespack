#!/usr/bin/env python3
"""Modele broni dla pluginu AxonGuns: poza kuszy (oburącz) i celowanie bez podmiany przedmiotu.

QualityArmory trzyma broń jako *naładowaną kuszę* (crossbow + custom_model_data), dlatego postać trzyma ją
oburącz, a `firstperson_righthand` modeli jest ustawione pod dodatkowe przesunięcie, które klient robi dla
naładowanej kuszy (x -0.641864, obrót Y 10°). Celowanie w QA to przełożenie broni do lewej ręki
(`firstperson_lefthand` = widok przez przyrządy) i przedmiot „aiming” (kusza 68) w prawej.

AxonGuns nie zmienia przedmiotu w trakcie strzelania, więc celowanie robi definicja przedmiotu `axon:bron`:
- `keybind_down` key.sneak (Shift) albo, gdy flaga 0 jest ustawiona (sterowanie „lpm”), key.use (PPM)
  przełącza na wariant „cel”. Klient przełącza go od razu, bez czekania na serwer.
- flaga 1 = broń nie jest naładowaną kuszą (sterowanie „uzywanie”, materiał IRON_HORSE_ARMOR): warianty
  „_u” mają poprawkę na brak przesunięcia kuszy w pierwszej osobie i obrót broni dla zwykłej pozy ręki.
- custom_model_data (float 0) = 10000 + numer broni z QualityArmory. Inny numer niż w QA, żeby QA nie
  brało broni AxonGuns za swoją (QA rozpoznaje broń po materiale i numerze).

Warianty to małe modele z `parent` = model broni z QA i samym `display` (assets/axon/models/bron/<wariant>/<broń>.json).
Wariant „biodro” na kuszy to po prostu model QA.

Użycie: python3 zrodla/gen_axonguns.py plik.zip [...] (build_pack.py i buduj_1_21_11.py wołają patch()).
"""
import json
import math
import os
import sys
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from render import rot_axis, rot_xyz, arm_pose_world, CROSSBOW_R  # noqa: E402

ITEM = 'assets/axon/items/bron.json'
CROSSBOW = 'assets/minecraft/items/crossbow.json'
OLD_CROSSBOW = 'axon_1_21_0/assets/minecraft/models/item/crossbow.json'
OLD_ITEM = 'axon_1_21_0/assets/axon/models/item/bron.json'
PREFIX = 'assets/axon/models/bron/'
OFFSET = 10000
ARM_R = np.array([0.56, -0.52, -0.72])
ARM_L = np.array([-0.56, -0.52, -0.72])
CHARGED_T = np.array([-0.641864, 0.0, 0.0])
CHARGED_R = rot_axis('y', 10.0)
ITEM_POSE_PITCH = -18.0          # ręka przy zwykłym trzymaniu przedmiotu (xRot -π/10)
HAND_OFF = np.array([-1 / 16.0, 0.125, -0.625])   # ItemInHandLayer, prawa ręka
B = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float).T
FALLBACK = {'type': 'minecraft:model', 'model': 'minecraft:item/crossbow'}


# ------------------------------------------------------------------ transformacje

def unpack(d, left=False):
    """display -> (t w blokach, R, S) tak jak ItemTransform.apply (lewa ręka: lustro)."""
    r = list(d.get('rotation', [0, 0, 0]))
    t = list(d.get('translation', [0, 0, 0]))
    if left:
        r = [r[0], -r[1], -r[2]]
        t = [-t[0], t[1], t[2]]
    return np.array(t, float) / 16.0, rot_xyz(r), list(d.get('scale', [1, 1, 1]))


def pack(t, R, S):
    """(t, R, S) prawej ręki -> wpis display; sprawdza zakresy klienta (translacja ±80)."""
    eb = math.asin(max(-1.0, min(1.0, R[0, 2])))
    if abs(math.cos(eb)) > 1e-6:
        ec = math.atan2(-R[0, 1], R[0, 0])
        ea = math.atan2(-R[1, 2], R[2, 2])
    else:                          # gimbal: obrót x i z na tej samej osi
        ec = 0.0
        ea = math.atan2(R[2, 1], R[1, 1])
    e = [math.degrees(ea), math.degrees(eb), math.degrees(ec)]
    assert np.allclose(rot_xyz(e), R, atol=1e-5), (e, R)
    tt = t * 16.0
    assert np.all(np.abs(tt) <= 80), tt
    return {'rotation': [round(x, 3) + 0.0 for x in e],
            'translation': [round(float(x), 3) + 0.0 for x in tt],
            'scale': [float(x) for x in S]}


def fp_ads_charged(lh):
    """Widok z lewej ręki QA (bez kuszy) odtworzony w prawej ręce z naładowaną kuszą."""
    tL, RL, S = unpack(lh, left=True)
    Rinv = CHARGED_R.T
    return pack(Rinv @ (ARM_L + tL - ARM_R - CHARGED_T), Rinv @ RL, S)


def fp_ads_plain(lh):
    """Widok z lewej ręki QA w prawej ręce, gdy broń nie jest kuszą."""
    tL, RL, S = unpack(lh, left=True)
    return pack(ARM_L + tL - ARM_R, RL, S)


def fp_hip_plain(rh):
    """Biodro QA (ustawione pod naładowaną kuszę) dla przedmiotu, który kuszą nie jest."""
    t, R, S = unpack(rh)
    return pack(CHARGED_T + CHARGED_R @ t, CHARGED_R @ R, S)


def tp_item_pose(rh):
    """Trzecia osoba: model QA jest ustawiony pod pozę kuszy (ręka wyciągnięta przed siebie).
    Przy zwykłej pozie (ręka w dół) obracamy broń wokół dłoni tak, żeby lufa szła tam, gdzie przy kuszy."""
    t, R, S = unpack(rh)
    Rc = arm_pose_world(*CROSSBOW_R)
    Ri = rot_axis('x', ITEM_POSE_PITCH)
    Q = B.T @ Ri.T @ Rc @ B            # w układzie przedmiotu: obrót „kusza -> zwykła poza”
    # dłoń = początek układu przedmiotu po translacji (punkt HAND_OFF w układzie ręki) zostaje na miejscu
    return pack(Q @ t, Q @ R, S)


# ------------------------------------------------------------------ paczka

def _display(z, ref, names):
    """display modelu z dziedziczeniem po parent (każdy kontekst osobno, jak w kliencie)."""
    out = {}
    seen = 0
    while ref and seen < 10:
        ns, p = ref.split(':', 1) if ':' in ref else ('minecraft', ref)
        path = 'assets/%s/models/%s.json' % (ns, p)
        if path not in names:
            break
        m = json.loads(z.read(path))
        for k, v in (m.get('display') or {}).items():
            out.setdefault(k, v)
        ref = m.get('parent')
        seen += 1
    return out


def warianty(display):
    # brak wpisu = przekształcenie tożsamościowe (tak robi klient, np. AWP nie ma firstperson_righthand)
    rh = display.get('firstperson_righthand', {})
    lh = display.get('firstperson_lefthand', rh)
    tp = display.get('thirdperson_righthand', {})
    w = {'cel': {'firstperson_righthand': fp_ads_charged(lh)},
         'biodro_u': {'firstperson_righthand': fp_hip_plain(rh)},
         'cel_u': {'firstperson_righthand': fp_ads_plain(lh)}}
    tpu = tp_item_pose(tp)
    w['biodro_u']['thirdperson_righthand'] = tpu
    w['cel_u']['thirdperson_righthand'] = tpu
    return w


def bronie(z):
    """(numer QA, model) dla każdej broni (qualityarmory:gun/*) na kuszy."""
    items = json.loads(z.read(CROSSBOW))
    out = []
    for e in items['model']['entries']:
        m = e['model']
        ref = m.get('model', '') if m.get('type', '').split(':')[-1] == 'model' else ''
        if ref.startswith('qualityarmory:gun/'):
            out.append((int(e['threshold']), ref))
    return out


def _dispatch(guns, wariant):
    entries = []
    for cmd, ref in guns:
        model = ref if wariant == 'biodro' else 'axon:bron/%s/%s' % (wariant, ref.split('/')[-1])
        entries.append({'threshold': OFFSET + cmd, 'model': {'type': 'minecraft:model', 'model': model}})
    return {'type': 'minecraft:range_dispatch', 'property': 'minecraft:custom_model_data', 'index': 0,
            'fallback': FALLBACK, 'entries': entries}


def _cel_albo(guns, cel, biodro):
    """Shift zawsze celuje; PPM celuje tylko przy fladze 0 (sterowanie „lpm”)."""
    hip = _dispatch(guns, biodro)
    ads = _dispatch(guns, cel)
    return {'type': 'minecraft:condition', 'property': 'minecraft:keybind_down', 'keybind': 'key.sneak',
            'on_true': ads,
            'on_false': {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': 0,
                         'on_true': {'type': 'minecraft:condition', 'property': 'minecraft:keybind_down',
                                     'keybind': 'key.use', 'on_true': ads, 'on_false': hip},
                         'on_false': hip}}


def definicja(guns):
    return {'model': {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': 1,
                      'on_true': _cel_albo(guns, 'cel_u', 'biodro_u'),
                      'on_false': _cel_albo(guns, 'cel', 'biodro')}}


def pliki(z):
    names = set(z.namelist())
    guns = bronie(z)
    out = {}
    for cmd, ref in guns:
        w = warianty(_display(z, ref, names))
        name = ref.split('/')[-1]
        for wariant, disp in w.items():
            out[PREFIX + '%s/%s.json' % (wariant, name)] = (json.dumps({'parent': ref, 'display': disp}, indent=1) + '\n').encode()
    out[ITEM] = (json.dumps(definicja(guns), indent=1) + '\n').encode()
    # 1.21-1.21.3: bez definicji przedmiotów; 1.21.2-1.21.3 czytają item_model jako models/item/bron,
    # 1.21-1.21.1 widzą zwykłą kuszę z numerem 10000+n. Tam tylko model biodra.
    if OLD_CROSSBOW in names:
        old = json.loads(z.read(OLD_CROSSBOW))
        ov = [o for o in old.get('overrides', []) if o.get('predicate', {}).get('custom_model_data', 0) < OFFSET]
        extra = [{'predicate': {'custom_model_data': OFFSET + cmd}, 'model': ref} for cmd, ref in guns]
        old['overrides'] = ov + extra
        out[OLD_CROSSBOW] = (json.dumps(old, indent=1) + '\n').encode()
        item = {k: v for k, v in old.items() if k != 'overrides'}
        item['overrides'] = extra
        out[OLD_ITEM] = (json.dumps(item, indent=1) + '\n').encode()
    return out


def patch(path):
    with zipfile.ZipFile(path) as z:
        files = pliki(z)
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            if i.filename in files or i.filename.startswith(PREFIX):
                continue
            zout.writestr(i, zin.read(i.filename))
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 16, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    os.replace(tmp, path)
    print('gen_axonguns: %s, %d plików' % (os.path.basename(path), len(files)))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        patch(p)
