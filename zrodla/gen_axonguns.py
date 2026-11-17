#!/usr/bin/env python3
"""Modele broni dla pluginu AxonGuns: poza kuszy (oburącz) i celowanie bez podmiany przedmiotu.

Modele broni QA (`firstperson_righthand`) są ustawione pod zwykłą, nienaładowaną kuszę. AxonGuns trzyma broń
jako *naładowaną* kuszę, żeby postać trzymała ją oburącz, a klient przesuwa naładowaną kuszę w pierwszej osobie
(x -0.641864, obrót Y 10°). Bez poprawki broń była za bardzo po lewej (sprawdzone w grze 16.11), więc wariant
„biodro” cofa to przesunięcie. Celowanie w QA to przełożenie broni do lewej ręki
(`firstperson_lefthand` = widok przez przyrządy) i przedmiot „aiming” (kusza 68) w prawej.

AxonGuns nie zmienia przedmiotu w trakcie strzelania, więc celowanie robi definicja przedmiotu `axon:bron`:
- `keybind_down` key.sneak (Shift) albo, gdy flaga 0 jest ustawiona (sterowanie „lpm”), key.use (PPM)
  przełącza na wariant „cel”. Klient przełącza go od razu, bez czekania na serwer.
- flaga 1 = broń nie jest naładowaną kuszą (sterowanie „uzywanie”, materiał IRON_HORSE_ARMOR): warianty
  „_u” mają poprawkę na brak przesunięcia kuszy w pierwszej osobie i obrót broni dla zwykłej pozy ręki.
- custom_model_data (float 0) = 10000 + numer broni z QualityArmory. Inny numer niż w QA, żeby QA nie
  brało broni AxonGuns za swoją (QA rozpoznaje broń po materiale i numerze).

Warianty to małe modele z `parent` = model broni z QA i samym `display` (assets/axon/models/bron/<wariant>/<broń>.json).
Na 1.21–1.21.3 (bez definicji przedmiotów) naładowana kusza pokazuje wariant „biodro”.

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
import gen_dodatki  # noqa: E402
import gen_menu_broni  # noqa: E402

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


# Poprawki biodra w widoku z pierwszej osoby (bloki; x w prawo, y w górę, z do tyłu), po zrzutach Tomka 16.11.
# Klucz to nazwa broni bez skina (ak47_zloto -> ak47).
HIP_TWEAK = {
    'ak47': (0.0, 0.0, -0.08),      # minimalnie do przodu
    'awp': (0.0, 0.06, 0.0),        # lekko do góry
    'spas': (0.07, 0.05, 0.0),      # lekko w prawo i trochę do góry
}


def tweak(name):
    return np.array(HIP_TWEAK.get(name.split('_')[0], (0.0, 0.0, 0.0)), float)


def fp_hip_charged(rh, v=np.zeros(3)):
    """Biodro QA (ustawione pod zwykłą kuszę) w prawej ręce z naładowaną kuszą: cofamy przesunięcie klienta.
    v = dodatkowe przesunięcie w widoku kamery."""
    t, R, S = unpack(rh)
    Rinv = CHARGED_R.T
    return pack(Rinv @ (t + v - CHARGED_T), Rinv @ R, S)


def fp_hip_plain(rh, v):
    t, R, S = unpack(rh)
    return pack(t + v, R, S)


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


# Oględziny (menu akcesoriów AxonGuns, flaga OGL_FLAG): broń bokiem na środku ekranu, lufą w lewo,
# lekko pochylona do gracza, jakby postać ją oglądała. Ręka w pierwszej osobie ma zawsze FOV 70,
# więc położenie na ekranie nie zależy od ustawienia FOV gracza.
OGL_FLAG = 15
OGL_DEPTH = 0.62          # odległość od kamery (bloki)
OGL_WIDTH = 0.64          # szerokość broni jako część szerokości ekranu 16:9
OGL_Y = 0.17              # środek broni nad środkiem ekranu (bloki na głębokości OGL_DEPTH; pół wysokości = 0.434)
OGL_YAW = 90.0            # lufa w lewo, widać lewy bok broni
OGL_TILT = 12.0           # pochylenie górą do gracza
OGL_ROLL = -4.0           # lufa minimalnie w dół
OGL_HEIGHT = 0.42         # najwyżej taka część wysokości ekranu (pistolety są wysokie)
TAN_V = math.tan(math.radians(35.0))
TAN_H = TAN_V * 16.0 / 9.0
_BOXES = {}               # nazwa broni -> (min, max) elementów modelu w blokach (x/16 - 0.5)


def fp_inspect(hip, name, charged=True):
    """display oględzin z display biodra (już przeliczonego pod naładowaną kuszę albo zwykły przedmiot)."""
    t, R, S = unpack(hip)
    S = np.array(S, float)
    Rcam = (CHARGED_R @ R) if charged else R
    Rv = rot_axis('z', OGL_ROLL) @ rot_axis('x', OGL_TILT) @ rot_axis('y', OGL_YAW)
    Rdes = Rv @ Rcam
    lo, hi = _BOXES.get(name.split('_')[0] if name.split('_')[0] in _BOXES else name, (np.full(3, -0.5), np.full(3, 0.5)))
    corners = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    cam = (corners * S) @ Rdes.T
    width = cam[:, 0].max() - cam[:, 0].min()
    height = cam[:, 1].max() - cam[:, 1].min()
    k = min((2 * OGL_DEPTH * TAN_H * OGL_WIDTH) / max(width, 1e-6),
            (2 * OGL_DEPTH * TAN_V * OGL_HEIGHT) / max(height, 1e-6))
    depth = OGL_DEPTH
    k_max = 3.99 / float(S.max())        # klient obcina skalę display do 4
    if k > k_max:
        # mały model (pistolet): największa skala i broń bliżej kamery, żeby na ekranie była tak samo duża
        depth = OGL_DEPTH * k_max / k
        k = k_max
    S2 = S * k
    m = (lo + hi) / 2
    c0 = np.array([0.0, OGL_Y * depth / OGL_DEPTH, -depth])
    base = ARM_R + (CHARGED_T if charged else 0)
    Rinv = CHARGED_R.T if charged else np.eye(3)
    tt = Rinv @ (c0 - base - Rdes @ (S2 * m))
    return pack(tt, Rinv @ Rdes, [round(float(x), 4) for x in S2])


def warianty(display, name=''):
    # brak wpisu = przekształcenie tożsamościowe (tak robi klient, np. AWP nie ma firstperson_righthand)
    rh = display.get('firstperson_righthand', {})
    lh = display.get('firstperson_lefthand', rh)
    tp = display.get('thirdperson_righthand', {})
    v = tweak(name)
    w = {'biodro': {'firstperson_righthand': fp_hip_charged(rh, v)},
         'cel': {'firstperson_righthand': fp_ads_charged(lh)},
         'biodro_u': {'firstperson_righthand': fp_hip_plain(rh, v)} if v.any() else {},
         'cel_u': {'firstperson_righthand': fp_ads_plain(lh)}}
    w['ogl'] = {'firstperson_righthand': fp_inspect(w['biodro']['firstperson_righthand'], name, True)}
    w['ogl_u'] = {'firstperson_righthand': fp_inspect(w['biodro_u'].get('firstperson_righthand', rh), name, False)}
    tpu = tp_item_pose(tp)
    w['ogl_u']['thirdperson_righthand'] = tpu
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


def _dispatch(guns, wariant, dostepne=None):
    entries = []
    for cmd, ref in guns:
        name = ref.split('/')[-1]
        model = {'type': 'minecraft:model', 'model': 'axon:bron/%s/%s' % (wariant, name)}
        dod = gen_dodatki.nakladki(name, wariant, dostepne or {})
        if dod:
            model = {'type': 'minecraft:composite', 'models': [model] + dod}
        entries.append({'threshold': OFFSET + cmd, 'model': model})
    return {'type': 'minecraft:range_dispatch', 'property': 'minecraft:custom_model_data', 'index': 0,
            'fallback': FALLBACK, 'entries': entries}


def _cel_albo(guns, cel, biodro, dostepne=None):
    """Shift zawsze celuje; PPM celuje tylko przy fladze 0 (sterowanie „lpm”)."""
    hip = _dispatch(guns, biodro, dostepne)
    ads = _dispatch(guns, cel, dostepne)
    return {'type': 'minecraft:condition', 'property': 'minecraft:keybind_down', 'keybind': 'key.sneak',
            'on_true': ads,
            'on_false': {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': 0,
                         'on_true': {'type': 'minecraft:condition', 'property': 'minecraft:keybind_down',
                                     'keybind': 'key.use', 'on_true': ads, 'on_false': hip},
                         'on_false': hip}}


def definicja(guns, dostepne=None):
    """Flaga OGL_FLAG (menu akcesoriów) wygrywa ze wszystkim: broń w pozie oględzin, bez celowania."""
    def tryb(cel, biodro, ogl):
        return {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': OGL_FLAG,
                'on_true': _dispatch(guns, ogl, dostepne), 'on_false': _cel_albo(guns, cel, biodro, dostepne)}
    return {'model': {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': 1,
                      'on_true': tryb('cel_u', 'biodro_u', 'ogl_u'),
                      'on_false': tryb('cel', 'biodro', 'ogl')}}


def _bbox(model):
    pts = np.array([e['from'] for e in model['elements']] + [e['to'] for e in model['elements']], float)
    return pts.min(0) / 16.0 - 0.5, pts.max(0) / 16.0 - 0.5


# Luneta przy celowaniu (wariant „cel” to pełny model zamiast samego display):
# czarna osłona wokół okularu zasłania świat na rogach ekranu, a krzyż jest cienki i bez środka.
SCOPES = {'awp'}
RET_HALF = 0.008      # połowa grubości kreski (jednostki modelu; luneta AWP ma skalę 2,2)
RET_GAP = 0.12        # pusty środek krzyża (od środka do początku kreski)
PLATE = 9.0           # zasięg osłony od osi lunety


def _box(fr, to, face):
    faces = {k: dict(face) for k in ('north', 'south', 'east', 'west', 'up', 'down')}
    return {'from': [round(x, 4) for x in fr], 'to': [round(x, 4) for x in to], 'faces': faces}


def luneta(model):
    els = [e for e in model['elements'] if not e.get('name', '').startswith('ret_')]
    by = {e.get('name'): e for e in model['elements']}
    ret = by.get('ret_v')
    oc_t, oc_r = by.get('ocular_t'), by.get('ocular_r')
    if ret is None or oc_t is None or oc_r is None:
        return None
    black = dict(next(iter(oc_t['faces'].values())))
    black.pop('cullface', None)
    lines = dict(next(iter(ret['faces'].values())))
    lines.pop('cullface', None)
    cx = (ret['from'][0] + ret['to'][0]) / 2
    cy = (by['ret_h_l']['from'][1] + by['ret_h_l']['to'][1]) / 2
    z0, z1 = ret['from'][2], ret['to'][2]
    rr = (ret['to'][1] - ret['from'][1]) / 2        # długość ramion krzyża = wnętrze tubusu
    ri = rr                                          # okno osłony = najwęższe miejsce tubusu (bez prześwitów w rogach)
    a, g = RET_HALF, RET_GAP
    out = list(els)
    for nm, fr, to in (('ret_t', (cx - a, cy + g, z0), (cx + a, cy + rr, z1)),
                       ('ret_b', (cx - a, cy - rr, z0), (cx + a, cy - g, z1)),
                       ('ret_l', (cx - rr, cy - a, z0), (cx - g, cy + a, z1)),
                       ('ret_p', (cx + g, cy - a, z0), (cx + rr, cy + a, z1))):
        b = _box(fr, to, lines); b['name'] = nm; out.append(b)
    zf, zb = oc_r['from'][2], oc_r['from'][2] + 0.05   # osłona na początku okularu
    P = PLATE
    for nm, fr, to in (('oslona_g', (cx - P, cy + ri, zf), (cx + P, cy + P, zb)),
                       ('oslona_d', (cx - P, cy - P, zf), (cx + P, cy - ri, zb)),
                       ('oslona_l', (cx - P, cy - ri, zf), (cx - ri, cy + ri, zb)),
                       ('oslona_p', (cx + ri, cy - ri, zf), (cx + P, cy + ri, zb))):
        b = _box(fr, to, black); b['name'] = nm; out.append(b)
    for e in out:
        for k in (0, 1, 2):
            assert -16 <= e['from'][k] <= 32 and -16 <= e['to'][k] <= 32, e
    m = dict(model)
    m['elements'] = out
    return m


def _model(z, ref):
    ns, p = ref.split(':', 1)
    return json.loads(z.read('assets/%s/models/%s.json' % (ns, p)))


def pliki(z):
    names = set(z.namelist())
    guns = bronie(z)
    out = {}
    for cmd, ref in guns:
        name = ref.split('/')[-1]
        try:
            _BOXES[name] = _bbox(_model(z, ref))
        except (KeyError, ValueError):
            pass
    for cmd, ref in guns:
        name = ref.split('/')[-1]
        display = _display(z, ref, names)
        w = warianty(display, name)
        for wariant, disp in w.items():
            model = {'parent': ref, 'display': disp}
            if wariant in ('cel', 'cel_u') and name.split('_')[0] in SCOPES:
                full = luneta(_model(z, ref))
                if full is not None:
                    full['display'] = dict(display, **disp)
                    model = full
            out[PREFIX + '%s/%s.json' % (wariant, name)] = (json.dumps(model, indent=1) + '\n').encode()
    dod, dostepne = gen_dodatki.pliki(z, warianty, guns)
    out.update(dod)
    out[ITEM] = (json.dumps(definicja(guns, dostepne), indent=1) + '\n').encode()
    # menu akcesoriów (Shift+F): grafika okna jako czcionka i tło skrzyni ze znacznikiem dla shadera
    out.update(gen_menu_broni.pliki(open(os.path.join(HERE, 'menu_broni', 'generic_54.png'), 'rb').read()))
    # 1.21-1.21.3: bez definicji przedmiotów; 1.21.2-1.21.3 czytają item_model jako models/item/bron,
    # 1.21-1.21.1 widzą zwykłą kuszę z numerem 10000+n. Tam tylko model biodra.
    if OLD_CROSSBOW in names:
        old = json.loads(z.read(OLD_CROSSBOW))
        ov = [o for o in old.get('overrides', []) if o.get('predicate', {}).get('custom_model_data', 0) < OFFSET]
        extra = [{'predicate': {'custom_model_data': OFFSET + cmd}, 'model': 'axon:bron/biodro/' + ref.split('/')[-1]}
                 for cmd, ref in guns]
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
            if i.filename in files or i.filename.startswith((PREFIX, gen_dodatki.MODEL_DIR)):
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
