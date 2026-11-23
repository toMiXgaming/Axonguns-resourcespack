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
import gen_menu_akcesoriow  # noqa: E402
import celowniki  # noqa: E402

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


def _flaga(dod, on_true, on_false):
    return {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': gen_dodatki.FLAG[dod],
            'on_true': on_true, 'on_false': on_false}


# Przyrządy (muszka i szczerbinka) chowane, gdy na broni jest celownik: elementy fs_*, fsb_*, rs_*, buis_*
# bez podstaw i obejm, które są częścią lufy albo komory.
PRZYRZADY = ('fs_', 'fsb_', 'rs_', 'buis_')
ZOSTAJA = ('_base', '_collar', '_block', '_lug', '_swivel', '_tower_lo')
OPTYKA = ('kolimator', 'holo', 'luneta')
BEZ_PRZYRZADOW = set()       # nazwy modeli broni, które mają wariant bez przyrządów (wypełnia pliki())


def bez_przyrzadow(model):
    """Model broni bez muszki i szczerbinki albo None, gdy nie ma czego chować."""
    els = [e for e in model.get('elements', [])
           if not (str(e.get('name', '')).startswith(PRZYRZADY) and not str(e.get('name', '')).endswith(ZOSTAJA))]
    if len(els) == len(model.get('elements', [])):
        return None
    m = dict(model)
    m['elements'] = els
    return m


def _bron(wariant, name):
    model = {'type': 'minecraft:model', 'model': 'axon:bron/%s/%s' % (wariant, name)}
    if name not in BEZ_PRZYRZADOW:
        return model
    bez = {'type': 'minecraft:model', 'model': 'axon:bron/%s_bez/%s' % (wariant, name)}
    for dod in OPTYKA:
        model = _flaga(dod, bez, model)
    return model


def _dispatch(guns, wariant, dostepne=None):
    entries = []
    cel = wariant.startswith('cel')
    for cmd, ref in guns:
        name = ref.split('/')[-1]
        model = _bron(wariant, name)
        dod = gen_dodatki.nakladki(name, wariant, dostepne or {})
        if cel and gen_dodatki.PRZESUNIECIE.get(name.split('_')[0]):
            # kolimator/holo: model 3D celownika na broni, cała broń przesunięta (kropka na środku ekranu)
            ow = gen_dodatki.OPT_WARIANTY[wariant]
            opt = _bron(ow, name)
            dod_opt = gen_dodatki.nakladki(name, ow, dostepne or {})
            if dod_opt:
                opt = {'type': 'minecraft:composite', 'models': [opt] + dod_opt}
            if dod:
                model = {'type': 'minecraft:composite', 'models': [model] + dod}
            model = _flaga('kolimator', opt, _flaga('holo', opt, model))
            dod = []
        if dod:
            model = {'type': 'minecraft:composite', 'models': [model] + dod}
        if cel:
            # luneta: sama nakładka lunety zamiast broni (AWP i Dragunov zawsze, mają lunetę w modelu)
            scope = {'type': 'minecraft:model', 'model': celowniki.ref('luneta', wariant)}
            model = scope if name.split('_')[0] in SCOPES else _flaga('luneta', scope, model)
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
    return {'model': {'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': 1,
                      'on_true': _cel_albo(guns, 'cel_u', 'biodro_u', dostepne),
                      'on_false': _cel_albo(guns, 'cel', 'biodro', dostepne)}}


def _bbox(model):
    pts = np.array([e['from'] for e in model['elements']] + [e['to'] for e in model['elements']], float)
    return pts.min(0) / 16.0 - 0.5, pts.max(0) / 16.0 - 0.5


# Luneta przy celowaniu (wariant „cel” to pełny model zamiast samego display):
# czarna osłona wokół okularu zasłania świat na rogach ekranu, a krzyż jest cienki i bez środka.
SCOPES = {'awp', 'dragunov'}       # przy celowaniu nakładka z celowniki.py (luneta() zostaje dla podglądów)
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


# Materiały wybuchowe AxonGuns (wybuchowe.yml): item_model axon:wybuchowy_<id> -> modele qualityarmory:misc/*
WYBUCHOWE = {'granat': 'grenade', 'granat_zapalajacy': 'incendarygrenade', 'molotow': 'molotov',
             'granat_dymny': 'smokegrenade', 'flashbang': 'flashbang', 'c4': 'c4', 'mina': 'proxymine'}


BLYSK_STOPNIE = 8   # ile stopni siły błysku niosą znaki czcionki axon:blysk


def wybuchowe():
    out = {'assets/axon/items/wybuchowy_%s.json' % i: (json.dumps(
        {'model': {'type': 'minecraft:model', 'model': 'qualityarmory:misc/' + m}}, indent=1) + '\n').encode()
        for i, m in WYBUCHOWE.items()}
    # Błysk flashbanga: biały znak czcionki axon:blysk na cały ekran (tytuł, AxonGuns Explosives.flash).
    # 8 znaków \ue100-\ue107 to siła błysku. Bez shaderów każdy z nich jest po prostu bielą, a shader
    # rendertype_text (axonFlashVertex) czyta siłę z alfy rogów glifu: 240 + siła, obok 239.
    import io
    from PIL import Image
    img = Image.new('RGBA', (64 * BLYSK_STOPNIE, 16), (255, 255, 255, 255))
    for k in range(BLYSK_STOPNIE):
        # każdy róg glifu: piksel w rogu = 240 + siła, sąsiad w stronę środka = 239 (wierzchołek czyta swój róg)
        for x, dx in ((64 * k, 1), (64 * k + 63, -1)):
            for y in (0, 15):
                img.putpixel((x, y), (255, 255, 255, 240 + k))
                img.putpixel((x + dx, y), (255, 255, 255, 239))
    buf = io.BytesIO()
    img.save(buf, 'PNG')
    out['assets/axon/textures/font/blysk.png'] = buf.getvalue()
    znaki = ''.join(chr(0xe100 + k) for k in range(BLYSK_STOPNIE))
    out['assets/axon/font/blysk.json'] = (json.dumps({'providers': [
        {'type': 'bitmap', 'file': 'axon:font/blysk.png', 'ascent': 128, 'height': 256, 'chars': [znaki]}]},
        indent=1) + '\n').encode()
    return out


def pliki(z):
    names = set(z.namelist())
    guns = bronie(z)
    out = {}
    gen_dodatki.PRZESUNIECIE.clear()
    dod, dostepne = gen_dodatki.pliki(z, warianty, guns)
    for cmd, ref in guns:
        name = ref.split('/')[-1]
        display = _display(z, ref, names)
        w = warianty(display, name)
        delta = gen_dodatki.PRZESUNIECIE.get(name.split('_')[0])
        if delta:
            # celowanie przez kolimator/holo: broń przesunięta, kropka na środku ekranu
            w.update({gen_dodatki.OPT_WARIANTY[v]: gen_dodatki._z_przesunieciem(w[v], delta[v])
                      for v in gen_dodatki.OPT_WARIANTY})
        for wariant, disp in w.items():
            model = {'parent': ref, 'display': disp}
            out[PREFIX + '%s/%s.json' % (wariant, name)] = (json.dumps(model, indent=1) + '\n').encode()
        try:
            bez = bez_przyrzadow(_model(z, ref))
        except (KeyError, ValueError):
            bez = None
        if bez is not None:
            BEZ_PRZYRZADOW.add(name)
            out[PREFIX + '_bez/%s.json' % name] = (json.dumps(bez) + '\n').encode()
            for wariant, disp in w.items():
                child = {'parent': 'axon:bron/_bez/%s' % name, 'display': disp}
                out[PREFIX + '%s_bez/%s.json' % (wariant, name)] = (json.dumps(child, indent=1) + '\n').encode()
    out.update(dod)
    out.update(celowniki.pliki())
    out.update(wybuchowe())
    out[ITEM] = (json.dumps(definicja(guns, dostepne), indent=1) + '\n').encode()
    # menu akcesoriów (AxonGuns + okno AxonItems): środek, długość i kotwice miejsc każdej broni
    modele = {}
    for cmd, ref in guns:
        try:
            modele[ref] = _model(z, ref)
        except (KeyError, ValueError):
            pass
    MENU[0] = gen_menu_akcesoriow.dane(guns, modele, dod, dostepne)
    out.update(gen_menu_akcesoriow.pliki())
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


MENU = [None]
# po starym menu akcesoriów w oknie skrzyni (czcionka axon:bron_menu, podmienione tło skrzyni)
STARE = ('assets/axon/font/bron_menu.json', 'assets/axon/textures/font/bron_menu/',
         'assets/axon/items/menu_pusty.json', 'assets/axon/models/item/menu_pusty.json',
         'assets/axon/textures/item/menu_pusty.png', 'assets/axon/items/menu_zablokowane.json',
         'assets/axon/models/item/menu_zablokowane.json', 'assets/axon/textures/item/menu_zablokowane.png',
         'assets/minecraft/textures/gui/sprites/container/slot_highlight_',
         'assets/minecraft/textures/gui/container/generic_54.png')


def patch(path):
    with zipfile.ZipFile(path) as z:
        files = pliki(z)
    if MENU[0] is not None:
        with open(os.path.join(HERE, '..', gen_menu_akcesoriow.PLIK), 'wb') as f:
            f.write(MENU[0])
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for i in zin.infolist():
            if i.filename in files or i.filename.startswith((PREFIX, gen_dodatki.MODEL_DIR, celowniki.MODEL_DIR) + STARE):
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
