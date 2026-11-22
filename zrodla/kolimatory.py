#!/usr/bin/env python3
"""Tekstury kolimatora i celownika holograficznego (widok przy celowaniu), w stylu okularu lunety.

Każdy to mała kwadratowa karta przed kamerą, na środku ekranu. Poza rysunkiem tekstura jest
przezroczysta, więc broń i świat widać dalej. Gęstość pikseli jak w okular.py (ok. 250 pikseli
na wysokość ekranu), z tym samym nadpróbkowaniem i posteryzacją.

- kolimator: rura jak Aimpoint widziana od tyłu: matowa obudowa z rantem, pokrętło jasności z prawej,
  montaż pod spodem, szkło z lekką niebieską powłoką i odblaskiem, czerwona kropka z poświatą,
- holo: prostokątna rama jak EOTech z daszkiem, przyciski i bateria w podstawie, szkło,
  czerwony pierścień z kropką i poświatą.
"""
import io

import numpy as np
from PIL import Image

from okular import L, POZIOMY, _over, _rect, _smooth

N = 128                         # bok tekstury
SS = 4
CZERWIEN = np.array([1.0, 0.16, 0.10])
JASNY = np.array([1.0, 0.78, 0.70])


def _siatka():
    h = N * SS
    ys, xs = np.mgrid[0:h, 0:h].astype(np.float64)
    x = (xs + 0.5 - h / 2) / h - 0.5 / N
    y = (ys + 0.5 - h / 2) / h - 0.5 / N
    return x, y, 1.2 / h


def _koniec(img):
    img = img.reshape(N, SS, N, SS, 4).mean(axis=(1, 3))
    a = img[..., 3:]
    rgb = np.where(a > 0, img[..., :3] / np.maximum(a, 1e-6), 0)
    rgb = np.round(np.clip(rgb, 0, 1) * (POZIOMY - 1)) / (POZIOMY - 1)
    a = np.round(a * 8) / 8
    out = np.concatenate([rgb, a], -1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def _png(img):
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _szum(shape, seed=3):
    rng = np.random.default_rng(seed)
    s = rng.normal(0, 1, (shape[0] // 4 + 1, shape[1] // 4 + 1))
    return np.kron(s, np.ones((4, 4)))[:shape[0], :shape[1]]


def _swiatlo_plaskie(x, y, x0, x1, y0, y1, faz):
    """Płaska ścianka z fazowanymi brzegami: jaśniej na górnej i lewej fazie, ciemniej na dolnej i prawej."""
    g = _smooth(y0, y0 + faz, y) * 0 + 1.0
    g = g + 0.55 * (1 - _smooth(y0, y0 + faz, y)) + 0.30 * (1 - _smooth(x0, x0 + faz, x))
    g = g - 0.45 * _smooth(y1 - faz, y1, y) - 0.30 * _smooth(x1 - faz, x1, x)
    return g


def _kropka(img, x, y, px, cx, cy, r, glow, wn):
    d = np.hypot(x - cx, y - cy)
    _over(img, CZERWIEN, wn * 0.55 * np.exp(-(d / glow) ** 2))
    _over(img, CZERWIEN, wn * (1 - _smooth(r - px, r + px, d)))
    _over(img, JASNY, wn * (1 - _smooth(0.45 * r - px, 0.45 * r + px, d)))


def _szklo(img, x, y, wn, odl_brzegu, glare_mask):
    """Szkło: lekko niebieskie, ciemniejsze przy brzegu, z odblaskiem."""
    _over(img, [0.30, 0.55, 0.75], wn * 0.10)
    _over(img, [0.01, 0.02, 0.05], wn * 0.55 * (1 - _smooth(0.0, 0.05, odl_brzegu)))
    _over(img, [0.88, 0.95, 1.0], wn * 0.28 * glare_mask)


def kolimator():
    x, y, px = _siatka()
    r = np.hypot(x, y)
    img = np.zeros(x.shape + (4,))
    R_O, R_W, R_Z = 0.255, 0.275, 0.335     # okno, rant soczewki, obudowa
    obud = np.array([0.15, 0.155, 0.17])
    szum = _szum(x.shape)

    # montaż pod spodem: noga i zacisk szyny
    noga = _rect(x, y, -0.16, 0.16, 0.25, 0.42, px)
    _over(img, obud[None, None] * (0.95 - 0.5 * _smooth(0.25, 0.42, y))[..., None], noga)
    zac = _rect(x, y, -0.24, 0.24, 0.40, 0.49, px)
    _over(img, (obud * 0.7)[None, None] * _swiatlo_plaskie(x, y, -0.24, 0.24, 0.40, 0.49, 0.015)[..., None], zac)
    for sx in (-0.18, 0.18):                 # śruby zacisku
        d = np.hypot(x - sx, y - 0.445)
        _over(img, [0.40, 0.41, 0.44], 1 - _smooth(0.018 - px, 0.018 + px, d))
        _over(img, [0.08, 0.08, 0.09], _rect(x, y, sx - 0.012, sx + 0.012, 0.442, 0.448, px))

    # pokrętło jasności z prawej (walec o osi pionowej)
    t = np.clip((x - 0.30) / 0.11, 0, 1)
    shx = 0.45 + 0.75 * np.sin(np.pi * t) * (1.1 - t)
    ryf = np.where(np.abs(y) < 0.075, 0.82 + 0.18 * np.cos(2 * np.pi * y / 0.024), 1.0)
    _over(img, obud[None, None] * (shx * ryf)[..., None], _rect(x, y, 0.30, 0.41, -0.09, 0.09, px))
    _over(img, (obud * 0.8)[None, None] * shx[..., None], _rect(x, y, 0.30, 0.43, -0.10, -0.07, px))

    # obudowa: torus z oświetleniem z lewej góry, cień od rantu
    tt = np.clip((r - R_W) / (R_Z - R_W), 0, 1)
    dn = -np.sin(np.pi * (tt - 0.5))
    with np.errstate(invalid='ignore', divide='ignore'):
        ux, uy = np.where(r > 0, x / r, 0), np.where(r > 0, y / r, 0)
    n = np.stack([ux * dn, uy * dn, np.clip(np.cos(np.pi * (tt - 0.5)), 0.1, 1)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    dif = np.clip(n @ L, 0, 1)
    kol = obud[None, None] * (0.45 + 1.4 * dif)[..., None] + 0.008 * szum[..., None]
    kol *= (1 - 0.35 * np.exp(-((r - 0.31) / 0.004) ** 2))[..., None]        # rowek
    _over(img, kol, _smooth(R_W - px, R_W + px, r) * (1 - _smooth(R_Z - px, R_Z + px, r)))

    # rant soczewki: jasny metal po stronie cienia (wnętrze odbija światło z przeciwnej strony)
    strona = np.clip(0.5 + 0.5 * (ux * L[0] + uy * L[1]) / np.hypot(L[0], L[1]), 0, 1)
    _over(img, np.array([0.22, 0.23, 0.25])[None, None] * (0.5 + 1.2 * (1 - strona))[..., None],
          _smooth(R_O - px, R_O + px, r) * (1 - _smooth(R_W - px, R_W + px, r)))

    # szkło i kropka
    wn = 1 - _smooth(R_O - px, R_O + px, r)
    ang = np.arctan2(y, x)
    glare = np.exp(-((r - 0.80 * R_O) / 0.02) ** 2) * np.exp(-((ang + 2.3) / 0.45) ** 2)
    _szklo(img, x, y, wn, R_O - r, glare)
    _kropka(img, x, y, px, 0.0, 0.0, 2.2 / N, 7.0 / N, wn)
    return _koniec(img)


def holo():
    x, y, px = _siatka()
    img = np.zeros(x.shape + (4,))
    obud = np.array([0.16, 0.165, 0.18])
    szum = _szum(x.shape, 5)
    WX, WY0, WY1 = 0.34, -0.22, 0.24          # okno
    FX, FY0, FY1 = 0.42, -0.33, 0.33          # rama (FY0 = daszek)

    # podstawa z baterią i przyciskami
    pod = _rect(x, y, -0.44, 0.44, FY1 - 0.01, 0.48, px)
    _over(img, obud[None, None] * _swiatlo_plaskie(x, y, -0.44, 0.44, FY1, 0.48, 0.02)[..., None]
          + 0.008 * szum[..., None], pod)
    for bx in (0.17, 0.30):                   # przyciski z prawej
        b = _rect(x, y, bx - 0.045, bx + 0.045, 0.37, 0.44, px)
        _over(img, np.array([0.07, 0.07, 0.08])[None, None] *
              _swiatlo_plaskie(x, y, bx - 0.045, bx + 0.045, 0.37, 0.44, 0.012)[..., None], b)
    _over(img, [0.08, 0.08, 0.09], _rect(x, y, -0.36, -0.06, 0.395, 0.415, px))   # pokrywa baterii
    _over(img, [0.30, 0.31, 0.34], _rect(x, y, -0.36, -0.06, 0.39, 0.395, px))

    # rama: słupki po bokach, pasek pod oknem, daszek nad oknem
    rama = np.maximum.reduce([_rect(x, y, -FX, -WX, FY0, FY1, px), _rect(x, y, WX, FX, FY0, FY1, px),
                              _rect(x, y, -WX, WX, WY1, FY1, px), _rect(x, y, -WX, WX, FY0, WY0, px)])
    g = _swiatlo_plaskie(x, y, -FX, FX, FY0, FY1, 0.025)
    # wewnętrzna faza wokół okna: jasna na dole i z prawej (światło z lewej góry)
    wew = (_smooth(WY1, WY1 + 0.02, y) * (1 - _smooth(WY1 + 0.02, WY1 + 0.03, y)) * (np.abs(x) < WX + 0.02) +
           _smooth(WX, WX + 0.02, x) * (1 - _smooth(WX + 0.02, WX + 0.03, x)) * (y > WY0) * (y < WY1 + 0.02))
    g = g + 0.6 * wew
    _over(img, obud[None, None] * g[..., None] + 0.008 * szum[..., None], rama)
    # daszek: wystający pasek z zaokrąglonymi rogami
    qx = np.maximum(np.abs(x) - (FX + 0.02 - 0.05), 0)
    qy = np.maximum(np.abs(y - (FY0 - 0.01)) - (0.045 - 0.04), 0)
    dasz = 1 - _smooth(0.04 - px, 0.04 + px, np.hypot(qx, qy))
    _over(img, (obud * 0.9)[None, None] * (1.25 - 0.6 * _smooth(FY0 - 0.06, FY0 + 0.04, y))[..., None], dasz)

    # szkło: prostokątne, z odblaskiem po skosie
    wn = _rect(x, y, -WX, WX, WY0, WY1, px)
    odl = np.minimum(np.minimum(x + WX, WX - x), np.minimum(y - WY0, WY1 - y))
    glare = np.exp(-(((x + y) + 0.30) / 0.03) ** 2) * (x < 0)
    _szklo(img, x, y, wn, odl, glare * 0.9)

    # pierścień i kropka
    d = np.hypot(x, y)
    R = 0.13
    _over(img, CZERWIEN, wn * 0.45 * np.exp(-((d - R) / (3.0 / N)) ** 2))
    _over(img, CZERWIEN, wn * np.exp(-((d - R) / (0.55 / N)) ** 2))
    _kropka(img, x, y, px, 0.0, 0.0, 1.6 / N, 5.0 / N, wn)
    return _koniec(img)


def png(rodzaj):
    return _png({'kolimator': kolimator, 'holo': holo}[rodzaj]())


if __name__ == '__main__':
    import sys
    kolimator().save(sys.argv[1] + '/kolimator.png')
    holo().save(sys.argv[1] + '/holo.png')
