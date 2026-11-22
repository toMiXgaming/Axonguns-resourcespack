#!/usr/bin/env python3
"""Dodatki AxonGuns widoczne na broni: tłumik, kompensator, chwyt przedni, latarka, luneta,
kolimator, laser, dwójnóg, powiększony magazynek i nakładka na kolbę.

Każdy dodatek to osobny model ustawiony na konkretnej broni (wylot lufy, spód łoża, szyna), z tym samym
układem współrzędnych co model broni z gen.py, więc pasuje do niego w każdym widoku. Definicja axon:bron
(gen_axonguns.py) rysuje broń jako `composite`: model broni + modele dodatków włączane flagami
custom_model_data, które ustawia AxonGuns (FLAG niżej).

Pliki:
- assets/axon/models/dodatki/<broń>_<dodatek>.json  (+ warianty <wariant>/... z display wariantu broni),
- assets/qualityarmory/textures/axon/dod_<broń>_<dodatek>.png  (ten sam atlas co bronie),
- assets/axon/items/dodatek_<dodatek>.json + models/item/dodatek_<dodatek>.json: dodatek jako przedmiot.

Wołane z gen_axonguns.pliki().
"""
import io
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen  # noqa: E402
from render import rot_xyz  # noqa: E402

DODATKI = ['tlumik', 'kompensator', 'chwyt', 'latarka', 'luneta', 'kolimator', 'laser', 'dwojnog', 'magazynek',
           'kolba', 'lufa_dluga', 'holo', 'chwyt_katowy', 'magazynek_szybki']
# laser został usunięty z AxonGuns; zostaje na liście tylko po to, żeby nie przesunąć numerów flag
USUNIETE = {'laser'}
# flagi custom_model_data ustawiane przez AxonGuns (Attachment.LOOKS w tej samej kolejności, od flagi 2)
FLAG = {d: i + 2 for i, d in enumerate(DODATKI)}
NAZWY = {'tlumik': 'Tłumik', 'kompensator': 'Kompensator', 'chwyt': 'Chwyt przedni',
         'latarka': 'Latarka taktyczna', 'luneta': 'Luneta 4x', 'kolimator': 'Kolimator',
         'laser': 'Celownik laserowy', 'dwojnog': 'Dwójnóg', 'magazynek': 'Powiększony magazynek',
         'kolba': 'Nakładka na kolbę', 'lufa_dluga': 'Przedłużona lufa', 'holo': 'Celownik holograficzny',
         'chwyt_katowy': 'Chwyt kątowy', 'magazynek_szybki': 'Szybki magazynek'}
BEZ_CELOWANIA = {'luneta', 'kolimator', 'holo'}   # przy celowaniu zamiast modelu jest widok celownika (celowniki.py)
gen.MATS.setdefault('laser_red', dict(kind='flat', base=(214, 34, 30), wear=(250, 90, 80), edge=0.0))
PISTOLETY = {'glock', 'makarov', 'deagle', 'sw1911', 'p30'}
MODEL_DIR = 'assets/axon/models/dodatki/'
TEX_DIR = 'assets/qualityarmory/textures/axon/'
BEZ_DODATKOW = {'rpg'}
PRZEDMIOT = 'ak47'        # na jakiej broni liczyć dodatek pokazywany jako przedmiot (GUI, ziemia, ręka)


# ------------------------------------------------------------------ geometria (jednostki gen.py: u wzdłuż broni
# od wylotu, v w górę, w w bok; oś lufy to v = 0, w = 0)

def _profile(g, u, wmax=1.2):
    """Najniższe i najwyższe v elementów broni nad/pod osią w przekroju u (blisko środka)."""
    lo, hi = None, None
    for e in g.els:
        if e.lo[2] <= u <= e.hi[2] and e.lo[0] <= wmax and e.hi[0] >= -wmax:
            lo = e.lo[1] if lo is None else min(lo, e.lo[1])
            hi = e.hi[1] if hi is None else max(hi, e.hi[1])
    return (lo or -0.5), (hi or 0.5)


def _muzzle(g):
    """u wylotu i promień lufy (najwyższy element przecinający oś tuż przy wylocie, bez muszki i zamka)."""
    u0 = min(e.lo[2] for e in g.els)
    r = 0.0
    for e in g.els:
        if e.lo[2] <= u0 + 0.6 and e.lo[0] <= 0 <= e.hi[0] and e.lo[1] <= 0 <= e.hi[1]:
            r = max(r, min(e.hi[1], -e.lo[1], 1.0))
    return u0, max(0.3, min(r, 0.8))


def _szerokosc(g, u, v0, v1):
    """Połowa szerokości broni w przekroju u między v0 i v1."""
    w = 0.3
    for e in g.els:
        if e.lo[2] <= u <= e.hi[2] and e.lo[1] < v1 and e.hi[1] > v0:
            w = max(w, e.hi[0], -e.lo[0])
    return w


LOZE = {'awp': (8.0, 30.0), 'm4a1s': (12.5, 23.0), 'remmington': (13.0, 21.0), 'kar98k': (10.0, 22.0)}     # ręczne zakresy łoża tam, gdzie heurystyka się myli


def _loze(g, nazwa):
    """(u_przód, u_tył) łoża: najdłuższy odcinek najniższego spodu przed magazynkiem/chwytem."""
    if nazwa in LOZE:
        return LOZE[nazwa]
    u0, _ = _muzzle(g)
    gu = g.grip[0] if g.grip else u0 + 20
    us = [u0 + 2.0 + 0.5 * i for i in range(int((gu - u0 - 2.0) / 0.5))]
    prof = []
    for u in us:
        lo, _ = _profile(g, u)
        if lo < -2.3:
            break
        prof.append((u, lo))
    if not prof:
        return u0 + 0.3 * (gu - u0), u0 + 0.5 * (gu - u0)
    mn = min(lo for _, lo in prof)
    best, cur = None, []
    for u, lo in prof + [(None, 0.0)]:
        if u is not None and lo <= mn + 0.35:
            cur.append(u)
        else:
            if cur and (best is None or cur[-1] - cur[0] > best[1] - best[0]):
                best = (cur[0], cur[-1])
            cur = []
    return best


def _ma_lunete(g):
    return any(e.name.startswith(('scope', 'ocular', 'obj')) for e in g.els)


def _magazynek(g):
    """Elementy magazynka (bez gniazda, zatrzasku i rury strzelby); pusta lista = broń bez magazynka."""
    return [e for e in g.els if e.name.startswith('mag') and not e.name.startswith(
        ('magwell', 'mag_release', 'mag_btn', 'mag_catch', 'mag_paddle', 'magtube', 'magcap'))]


def _kolba(g):
    return [e for e in g.els if e.name.startswith(('stock', 'butt'))]


def zbuduj(nazwa, dodatek):
    """Gun (gen.py) z samym dodatkiem dla broni `nazwa`, albo None, gdy dodatek tu nie ma sensu."""
    g = gen.BUILDERS[nazwa]()
    a = gen.Gun(nazwa + '_' + dodatek, g.qa)
    a.frame = g.frame
    u0, rb = _muzzle(g)
    grip_u = g.grip[0] if g.grip else u0 + 20
    pistol = nazwa in PISTOLETY
    if dodatek == 'tlumik':
        r = rb + (0.35 if pistol else 0.45)
        L = 5.5 if pistol else 7.5
        a.cyl('supp_body', (u0 - L, u0 + 0.8), 0.0, r, 'supp')
        a.cyl('supp_cap', (u0 - L - 0.25, u0 - L + 0.1), 0.0, r * 0.82, 'black')
        a.cyl('supp_bore', (u0 - L - 0.3, u0 - L - 0.2), 0.0, rb * 0.45, 'black')
        for i in range(3):
            uu = u0 - L + 1.2 + i * (L - 1.6) / 2
            a.cyl('supp_ring%d' % i, (uu, uu + 0.22), 0.0, r + 0.05, 'black')
    elif dodatek == 'kompensator':
        r = rb + 0.12
        L = 2.0 if pistol else 2.9
        a.cyl('comp_body', (u0 - L, u0 + 0.25), 0.0, r, 'black')
        for i in range(3 if not pistol else 2):
            uu = u0 - L + 0.45 + i * 0.75
            a.b('comp_port_t%d' % i, (uu, uu + 0.32), (r - 0.05, r + 0.02), r * 0.5, 'parts')
            a.b('comp_port_r%d' % i, (uu, uu + 0.32), (-r * 0.35, r * 0.35), (r - 0.05, r + 0.02), 'parts')
            a.b('comp_port_l%d' % i, (uu, uu + 0.32), (-r * 0.35, r * 0.35), (-r - 0.02, -r + 0.05), 'parts')
        a.cyl('comp_crown', (u0 - L - 0.15, u0 - L + 0.05), 0.0, r * 0.75, 'parts')
    elif dodatek == 'chwyt':
        if pistol:
            return None
        lf, lb = _loze(g, nazwa)
        uc = lf + 0.55 * (lb - lf)
        lo, _ = _profile(g, uc)
        a.b('fg_mount', (uc - 0.9, uc + 0.9), (lo - 0.35, lo + 0.05), 0.55, 'rail')
        a.b('fg_body', (uc - 0.55, uc + 0.55), (lo - 3.4, lo - 0.3), 0.5, 'polymer')
        for i in range(4):
            vv = lo - 0.8 - i * 0.65
            a.b('fg_rib%d' % i, (uc + 0.5, uc + 0.62), (vv - 0.18, vv), 0.42, 'polymer')
        a.b('fg_cap', (uc - 0.62, uc + 0.62), (lo - 3.6, lo - 3.4), 0.56, 'rubber')
    elif dodatek == 'latarka':
        L = 2.4 if pistol else 3.2
        if pistol:
            # pod szkieletem, przed kabłąkiem
            uc = u0 + 0.35 * (grip_u - u0)
            lo, _ = _profile(g, uc)
            vc, wc = lo - 0.75, 0.0
            a.b('fl_mount', (uc - 0.7, uc + 0.7), (vc + 0.3, lo + 0.05), 0.4, 'rail')
        else:
            # z prawej strony przodu łoża
            lf, lb = _loze(g, nazwa)
            uc = lf + L / 2 + 0.9
            lo, hi = _profile(g, uc)
            vc = max(lo + 0.6, min(0.0, hi - 0.6))
            ws = _szerokosc(g, uc, vc - 0.5, vc + 0.5)
            wc = ws + 0.72
            a.b('fl_mount', (uc - 0.7, uc + 0.7), (vc - 0.35, vc + 0.35), (ws - 0.05, wc - 0.3), 'rail')
        a.cyl('fl_body', (uc - L / 2, uc + L / 2), vc, 0.55, 'black', dw=wc)
        a.cyl('fl_head', (uc - L / 2 - 0.6, uc - L / 2), vc, 0.72, 'black', dw=wc)
        a.cyl('fl_lens', (uc - L / 2 - 0.66, uc - L / 2 - 0.58), vc, 0.55, 'glass', dw=wc)
        a.b('fl_switch', (uc + L / 2 - 0.5, uc + L / 2), (vc - 0.3, vc + 0.3), (wc + 0.5, wc + 0.68), 'rubber')
    elif dodatek == 'luneta':
        if _ma_lunete(g) or pistol or not g.sight:
            return None
        rear, front = g.sight['rear'][0], g.sight['front'][0]
        L = min(9.0, 0.55 * abs(rear - front))
        uc = rear - 0.45 * abs(rear - front) if rear > front else rear + 0.45 * abs(rear - front)
        _, hi = _profile(g, uc, 0.8)
        vc = max(hi, g.sight['rear'][1]) + 1.15
        a.cyl('sc_tube', (uc - L / 2, uc + L / 2), vc, 0.62, 'black')
        a.cyl('sc_obj', (uc - L / 2 - 1.8, uc - L / 2), vc, 0.92, 'black')
        a.cyl('sc_obj_lens', (uc - L / 2 - 1.86, uc - L / 2 - 1.78), vc, 0.78, 'glass')
        a.cyl('sc_eye', (uc + L / 2, uc + L / 2 + 1.6), vc, 0.8, 'black')
        a.b('sc_turret', (uc - 0.5, uc + 0.5), (vc + 0.55, vc + 1.05), 0.4, 'parts')
        a.b('sc_turret_w', (uc - 0.5, uc + 0.5), (vc - 0.4, vc + 0.4), (0.55, 1.0), 'parts')
        for nm, du in (('sc_ring_f', -L / 2 + 1.0), ('sc_ring_r', L / 2 - 1.6)):
            a.cyl(nm, (uc + du, uc + du + 0.6), vc, 0.72, 'black')
            a.b(nm + '_base', (uc + du, uc + du + 0.6), (hi - 0.05, vc - 0.6), 0.42, 'black')
    elif dodatek == 'kolimator':
        if _ma_lunete(g) or not g.sight:
            return None
        rear, front = g.sight['rear'][0], g.sight['front'][0]
        uc = rear - 0.25 * (rear - front)
        _, hi = _profile(g, uc, 0.8)
        L = 1.6 if pistol else 2.4
        base = max(hi, g.sight['rear'][1] - 0.3)
        a.b('rd_mount', (uc - L / 2 - 0.2, uc + L / 2 + 0.2), (base - 0.05, base + 0.35), 0.5, 'rail')
        a.b('rd_body', (uc - L / 2, uc + L / 2), (base + 0.35, base + 0.75), 0.55, 'black')
        a.b('rd_hood_l', (uc - L / 2, uc - L / 2 + 0.45), (base + 0.75, base + 1.75), (-0.55, -0.4), 'black')
        a.b('rd_hood_r', (uc - L / 2, uc - L / 2 + 0.45), (base + 0.75, base + 1.75), (0.4, 0.55), 'black')
        a.b('rd_hood_t', (uc - L / 2, uc - L / 2 + 0.45), (base + 1.6, base + 1.8), 0.55, 'black')
        a.b('rd_glass', (uc - L / 2 + 0.15, uc - L / 2 + 0.25), (base + 0.75, base + 1.6), 0.4, 'glass')
        a.b('rd_dot', (uc - L / 2 + 0.1, uc - L / 2 + 0.14), (base + 1.12, base + 1.24), 0.06, 'laser_red')
        a.b('rd_knob', (uc + 0.1, uc + 0.6), (base + 0.4, base + 0.7), (0.55, 0.75), 'parts')
    elif dodatek == 'laser':
        L = 1.4 if pistol else 2.0
        if pistol:
            uc = u0 + 0.5 * (grip_u - u0)
            lo, _ = _profile(g, uc)
            vc = lo + 0.25
            ws = _szerokosc(g, uc, vc - 0.3, vc + 0.3)
            wc = -(ws + 0.3)
        else:
            lf, lb = _loze(g, nazwa)
            uc = lf + L / 2 + 0.9
            lo, hi = _profile(g, uc)
            vc = max(lo + 0.6, min(0.0, hi - 0.6))
            ws = _szerokosc(g, uc, vc - 0.5, vc + 0.5)
            wc = -(ws + 0.45)
        a.b('ls_mount', (uc - 0.5, uc + 0.5), (vc - 0.25, vc + 0.25), (wc + 0.2, -ws + 0.05), 'rail')
        a.b('ls_body', (uc - L / 2, uc + L / 2), (vc - 0.32, vc + 0.32), (wc - 0.3, wc + 0.3), 'tan')
        a.b('ls_lens', (uc - L / 2 - 0.08, uc - L / 2), (vc - 0.12, vc + 0.12), (wc - 0.12, wc + 0.12), 'laser_red')
        a.b('ls_btn', (uc + L / 2 - 0.4, uc + L / 2 - 0.1), (vc + 0.32, vc + 0.45), (wc - 0.15, wc + 0.15), 'rubber')
    elif dodatek == 'dwojnog':
        if pistol or any(e.name.startswith('bipod') for e in g.els):
            return None
        lf, lb = _loze(g, nazwa)
        uc = lf + 0.6
        lo, _ = _profile(g, uc)
        a.b('bp_mount', (uc - 0.7, uc + 0.7), (lo - 0.45, lo + 0.05), 0.6, 'rail')
        a.b('bp_hinge', (uc - 0.4, uc + 0.4), (lo - 0.75, lo - 0.45), 0.75, 'parts')
        for side in (-1, 1):
            a.b('bp_leg%d' % (side + 1), (uc + 0.2, uc + 6.0), (lo - 0.8, lo - 0.5), (side * 0.75 - 0.15, side * 0.75 + 0.15),
                'black')
            a.b('bp_foot%d' % (side + 1), (uc + 5.8, uc + 6.4), (lo - 0.95, lo - 0.45), (side * 0.75 - 0.2, side * 0.75 + 0.2),
                'rubber')
    elif dodatek == 'magazynek':
        mag = _magazynek(g)
        if not mag or any(e.name.startswith('drum') for e in g.els):
            return None
        low = min(mag, key=lambda e: e.lo[1])
        v0 = low.lo[1]
        du = 0.25 if pistol else 0.5        # dół magazynka zwykle jest pochylony do przodu
        H = 1.2 if pistol else 2.2
        w = max(abs(low.lo[0]), abs(low.hi[0]))
        a.b('xm_body', (low.lo[2] - du, low.hi[2] - du), (v0 - H, v0 + 0.05), w, 'magsteel')
        a.b('xm_rib', (low.lo[2] - du + 0.3, low.hi[2] - du - 0.3), (v0 - H + 0.4, v0 - 0.3), w + 0.04, 'magsteel')
        a.b('xm_plate', (low.lo[2] - du - 0.15, low.hi[2] - du + 0.15), (v0 - H - 0.3, v0 - H), w + 0.1, 'polymer')
        a.b('xm_tab', (low.hi[2] - du - 0.2, low.hi[2] - du + 0.35), (v0 - H - 0.25, v0 - H + 0.15), w * 0.6, 'rubber')
    elif dodatek == 'kolba':
        st = _kolba(g)
        if pistol or not st:
            return None
        ue = max(e.hi[2] for e in st)
        rear = [e for e in st if e.hi[2] >= ue - 2.5]
        top = max(e.hi[1] for e in rear)
        bot = min(e.lo[1] for e in rear)
        w = max(max(abs(e.lo[0]), abs(e.hi[0])) for e in rear)
        a.b('ck_riser', (ue - 5.0, ue - 1.0), (top - 0.05, top + 0.55), w * 0.85, 'polymer')
        a.b('ck_strap_f', (ue - 4.6, ue - 4.2), (top - 0.4, top + 0.6), w + 0.08, 'band')
        a.b('ck_strap_r', (ue - 1.8, ue - 1.4), (top - 0.4, top + 0.6), w + 0.08, 'band')
        a.b('ck_pad', (ue - 0.05, ue + 0.55), (bot - 0.1, top + 0.1), w + 0.1, 'rubber')
    elif dodatek == 'lufa_dluga':
        if pistol:
            return None
        L = 5.0
        r = max(0.3, rb * 0.8)
        a.cyl('ld_barrel', (u0 - L, u0 + 0.4), 0.0, r, 'black')
        a.cyl('ld_collar', (u0 - 0.2, u0 + 0.6), 0.0, r + 0.18, 'parts')
        a.cyl('ld_crown', (u0 - L - 0.25, u0 - L + 0.05), 0.0, r + 0.12, 'parts')
        a.cyl('ld_bore', (u0 - L - 0.3, u0 - L - 0.2), 0.0, r * 0.45, 'black')
        a.b('ld_sight', (u0 - L + 0.3, u0 - L + 0.75), (r - 0.05, r + 0.55), 0.12, 'black')
    elif dodatek == 'holo':
        if _ma_lunete(g) or not g.sight:
            return None
        rear, front = g.sight['rear'][0], g.sight['front'][0]
        uc = rear - 0.25 * (rear - front)
        _, hi = _profile(g, uc, 0.8)
        L = 2.2 if pistol else 3.2
        W = 0.6 if pistol else 0.75
        base = max(hi, g.sight['rear'][1] - 0.3)
        a.b('hl_mount', (uc - L / 2 - 0.2, uc + L / 2 + 0.2), (base - 0.05, base + 0.35), W - 0.1, 'rail')
        a.b('hl_body', (uc - L / 2, uc + L / 2), (base + 0.35, base + 0.85), W, 'black')
        a.b('hl_batt', (uc + L / 2 - 1.1, uc + L / 2), (base + 0.35, base + 0.95), (W, W + 0.35), 'black')
        a.b('hl_hood_l', (uc - L / 2, uc + 0.2), (base + 0.85, base + 2.1), (-W, -W + 0.15), 'black')
        a.b('hl_hood_r', (uc - L / 2, uc + 0.2), (base + 0.85, base + 2.1), (W - 0.15, W), 'black')
        a.b('hl_hood_t', (uc - L / 2, uc + 0.2), (base + 1.95, base + 2.15), W, 'black')
        a.b('hl_glass_f', (uc - L / 2 + 0.15, uc - L / 2 + 0.25), (base + 0.85, base + 1.95), W - 0.15, 'glass')
        a.b('hl_glass_r', (uc + 0.05, uc + 0.15), (base + 0.85, base + 1.95), W - 0.15, 'glass')
        a.b('hl_dot', (uc - L / 2 + 0.1, uc - L / 2 + 0.14), (base + 1.34, base + 1.46), 0.06, 'laser_red')
        a.b('hl_btn', (uc + 0.4, uc + 0.8), (base + 0.85, base + 1.0), 0.2, 'rubber')
    elif dodatek == 'chwyt_katowy':
        if pistol:
            return None
        lf, lb = _loze(g, nazwa)
        uc = lf + 0.5 * (lb - lf)
        lo, _ = _profile(g, uc)
        a.b('afg_mount', (uc - 1.8, uc + 1.8), (lo - 0.3, lo + 0.05), 0.5, 'rail')
        # pochylona płytka: z przodu przy łożu, z tyłu niżej (pod kciuk), obrót 22,5° wokół osi w
        rot = (22.5, (uc, lo - 0.3))
        a.b('afg_body', (uc - 1.9, uc + 1.9), (lo - 1.5, lo - 0.3), 0.48, 'polymer', rot=rot)
        a.b('afg_lip', (uc + 1.5, uc + 2.0), (lo - 2.3, lo - 0.6), 0.48, 'polymer', rot=rot)
        a.b('afg_grip', (uc - 1.6, uc + 1.4), (lo - 1.7, lo - 1.5), 0.5, 'rubber', rot=rot)
    elif dodatek == 'magazynek_szybki':
        mag = _magazynek(g)
        if not mag or any(e.name.startswith('drum') for e in g.els):
            return None
        low = min(mag, key=lambda e: e.lo[1])
        v0 = low.lo[1]
        w = max(abs(low.lo[0]), abs(low.hi[0]))
        uf, ub = low.lo[2], low.hi[2]
        a.b('qm_plate', (uf - 0.05, ub + 0.05), (v0 - 0.2, v0 + 0.02), w + 0.06, 'rubber')
        a.b('qm_loop_f', (uf + 0.2, uf + 0.45), (v0 - 1.1, v0 - 0.2), w * 0.5, 'band')
        a.b('qm_loop_b', (ub - 0.45, ub - 0.2), (v0 - 1.1, v0 - 0.2), w * 0.5, 'band')
        a.b('qm_loop_d', (uf + 0.2, ub - 0.2), (v0 - 1.3, v0 - 1.1), w * 0.5, 'band')
    if not a.els:
        return None
    return a


def _w_granicach(model):
    for e in model['elements']:
        for k in (0, 1, 2):
            if not (-16 <= e['from'][k] <= 32 and -16 <= e['to'][k] <= 32):
                return False
    return True


def _png(img):
    buf = io.BytesIO()
    Image.fromarray(img, 'RGBA').save(buf, 'PNG')
    return buf.getvalue()


def _wycentrowany(model, gui_scale=None):
    """display dla dodatku jako przedmiotu: środek dodatku w środku slotu, rozmiar dopasowany."""
    pts = np.array([e['from'] for e in model['elements']] + [e['to'] for e in model['elements']], float)
    lo, hi = pts.min(0), pts.max(0)
    c = (lo + hi) / 2 / 16.0 - 0.5
    size = float((hi - lo).max()) / 16.0
    out = {}
    for ctx, rot, target in (('gui', [25, -45, 0], 0.85), ('ground', [0, 0, 0], 0.35), ('fixed', [0, 90, 0], 0.7),
                             ('thirdperson_righthand', [0, 90, 0], 0.3), ('thirdperson_lefthand', [0, 90, 0], 0.3),
                             ('firstperson_righthand', [0, 70, 0], 0.4), ('firstperson_lefthand', [0, 70, 0], 0.4),
                             ('head', [0, 0, 0], 0.5)):
        s = min(4.0, target / max(size, 1e-3))
        R = rot_xyz(rot)
        t = -(R @ (c * s)) * 16.0
        if ctx == 'ground':
            t[1] += 2.0
        if ctx.startswith('thirdperson'):
            t += np.array([0, 2.5, 1.5])
        if ctx.startswith('firstperson'):
            t += np.array([0, 3.0, 0])
        out[ctx] = {'rotation': rot, 'translation': [round(float(x), 3) for x in np.clip(t, -80, 80)],
                    'scale': [round(s, 4)] * 3}
    return out


def pliki(z, warianty, bronie):
    """Pliki dodatków dla broni z gen.BUILDERS, które są na kuszy.

    warianty(display, nazwa) -> {wariant: display} z gen_axonguns; bronie = [(numer, ref)].
    Zwraca (pliki, dostepne) gdzie dostepne[(nazwa_bazowa, dodatek)] = True."""
    names = set(z.namelist())
    out = {}
    dostepne = {}
    bazy = sorted(({ref.split('/')[-1].split('_')[0] for _, ref in bronie} & set(gen.BUILDERS)) - BEZ_DODATKOW)
    for nazwa in bazy:
        path = 'assets/qualityarmory/models/gun/%s.json' % nazwa
        if path not in names:
            continue
        display = json.loads(z.read(path)).get('display', {})
        w = warianty(display, nazwa)
        for dod in DODATKI:
            if dod in USUNIETE:
                continue
            a = zbuduj(nazwa, dod)
            if a is None:
                continue
            ref = 'qualityarmory:axon/dod_%s_%s' % (nazwa, dod)
            model, img, _, _ = gen.build_model(a, ref, display)
            if not _w_granicach(model):
                print('gen_dodatki: %s/%s poza granicami modelu, pomijam' % (nazwa, dod))
                continue
            model['credit'] = 'AXON - gen_dodatki.py'
            out[MODEL_DIR + '%s_%s.json' % (nazwa, dod)] = (json.dumps(model, indent=1) + '\n').encode()
            out[TEX_DIR + 'dod_%s_%s.png' % (nazwa, dod)] = _png(img)
            for wariant, disp in w.items():
                if dod in BEZ_CELOWANIA and wariant.startswith('cel'):
                    continue          # celowanie idzie przez przyrządy broni; luneta zasłaniałaby widok
                child = {'parent': 'axon:dodatki/%s_%s' % (nazwa, dod), 'display': disp}
                out[MODEL_DIR + '%s/%s_%s.json' % (wariant, nazwa, dod)] = (json.dumps(child, indent=1) + '\n').encode()
            dostepne[(nazwa, dod)] = True
            if nazwa == PRZEDMIOT or ((PRZEDMIOT, dod) not in dostepne
                                      and 'assets/axon/items/dodatek_%s.json' % dod not in out):
                item = dict(model)
                item['display'] = _wycentrowany(model)
                out['assets/axon/models/item/dodatek_%s.json' % dod] = (json.dumps(item, indent=1) + '\n').encode()
                out['assets/axon/items/dodatek_%s.json' % dod] = (json.dumps(
                    {'model': {'type': 'minecraft:model', 'model': 'axon:item/dodatek_%s' % dod}}, indent=1) + '\n').encode()
    return out, dostepne


def nakladki(nazwa_broni, wariant, dostepne):
    """Modele dodatków do composite dla danej broni (skin bierze dodatki broni bazowej)."""
    baza = nazwa_broni.split('_')[0]
    out = []
    for dod in DODATKI:
        if dod in USUNIETE or not dostepne.get((baza, dod)):
            continue
        if dod in BEZ_CELOWANIA and wariant.startswith('cel'):
            continue
        out.append({'type': 'minecraft:condition', 'property': 'minecraft:custom_model_data', 'index': FLAG[dod],
                    'on_true': {'type': 'minecraft:model', 'model': 'axon:dodatki/%s/%s_%s' % (wariant, baza, dod)},
                    'on_false': {'type': 'minecraft:empty'}})
    return out
