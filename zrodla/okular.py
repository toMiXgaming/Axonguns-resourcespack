#!/usr/bin/env python3
"""Tekstura okularu lunety snajperskiej (widok przy celowaniu), rysowana proceduralnie.

Jedna płaska karta 2:1 przed kamerą: gruby, gumowy okular z bliska, za nim korpus lunety z nitami
(bez pokręteł), w środku okrągłe okno ze szkłem (lekko przyciemnione
przy brzegu) i cienką siatką. Poza rysunkiem tekstura jest przezroczysta, więc dookoła widać świat.

Rysowane w podwójnej rozdzielczości i zmniejszane, żeby krawędzie były gładkie.
"""
import io

import numpy as np
from PIL import Image

W, H = 512, 256                 # wysokość tekstury = wysokość karty; mało pikseli, żeby zostało trochę minecraftowej pikselozy
SS = 4                          # nadpróbkowanie (gładkie krawędzie w obrębie piksela)
POZIOMY = 20                    # posteryzacja kolorów (po POZIOMY odcieni na kanał), krycie co 1/8

# promienie i wymiary w ułamkach wysokości karty
R_OKNO = 0.300                  # okno ze szkłem
R_OBR = 0.322                   # metalowa obręcz soczewki
R_MUSZLA = 0.485                # zewnętrzny brzeg gumowej muszli

L = np.array([-0.45, -0.6, 0.66])
L = L / np.linalg.norm(L)


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def _over(dst, rgb, a):
    """Nakłada kolor rgb (H,W,3 lub 3) z kryciem a (H,W) na dst (H,W,4, premultiplied)."""
    a = np.clip(a, 0, 1)[..., None]
    rgb = np.broadcast_to(np.asarray(rgb, dtype=np.float64), dst[..., :3].shape)
    dst[..., :3] = rgb * a + dst[..., :3] * (1 - a)
    dst[..., 3:] = a + dst[..., 3:] * (1 - a)


def _rect(x, y, x0, x1, y0, y1, px):
    """Krycie prostokąta z wygładzonym brzegiem."""
    return (_smooth(x0 - px, x0 + px, x) * (1 - _smooth(x1 - px, x1 + px, x)) *
            _smooth(y0 - px, y0 + px, y) * (1 - _smooth(y1 - px, y1 + px, y)))


def _walec_poziomy(y, y0, y1):
    """Cieniowanie walca o osi poziomej (widać jego bok): jasno u góry, ciemno na dole."""
    t = np.clip((y - y0) / (y1 - y0), 0, 1)
    ny = np.cos(np.pi * t)          # składowa normalnej w górę (+) i w dół (-)
    nz = np.sin(np.pi * t)
    return np.clip(0.30 + 0.55 * (ny * 0.6 + nz * 0.66) + 0.25 * np.exp(-((t - 0.28) / 0.07) ** 2), 0.08, 1.4)


def obraz():
    h, w = H * SS, W * SS
    px = 1.2 / h                                        # szerokość wygładzania w ułamkach wysokości
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    # środek w (0, 0) na środku piksela tekstury (cienka siatka ma wtedy równo 1 piksel), y w dół
    x = (xs + 0.5 - w / 2) / h - 0.5 / H
    y = (ys + 0.5 - h / 2) / h - 0.5 / H
    r = np.hypot(x, y)
    img = np.zeros((h, w, 4))

    # --- korpus lunety za okularem (siodło z nitami) ---
    stal = np.array([0.20, 0.21, 0.23])
    sh = _walec_poziomy(y, -0.31, 0.31)
    # siodło z zaokrąglonymi rogami
    qx, qy = np.maximum(np.abs(x) - (0.58 - 0.08), 0), np.maximum(np.abs(y) - (0.31 - 0.08), 0)
    siod = 1 - _smooth(0.08 - px, 0.08 + px, np.hypot(qx, qy))
    _over(img, stal[None, None] * sh[..., None], siod)
    # nity na siodle
    for sx in (-0.52, 0.52):
        for sy in (-0.25, 0.25):
            d = np.hypot(x - sx, y - sy)
            _over(img, [0.42, 0.43, 0.46], 1 - _smooth(0.012 - px, 0.012 + px, d))
            _over(img, [0.70, 0.71, 0.74], 1 - _smooth(0.005 - px, 0.005 + px, np.hypot(x - sx + 0.004, y - sy + 0.004)))

    # cień okularu rzucony na korpus
    cien = (1 - _smooth(R_MUSZLA, R_MUSZLA + 0.07, r)) * (r > R_MUSZLA - 0.01)
    img[..., :3] *= (1 - 0.65 * cien)[..., None]

    # okno: nic z korpusu nie prześwituje przez szkło
    img *= _smooth(R_OKNO - px, R_OKNO + px, r)[..., None]

    # --- gumowa muszla oczna: torus z oświetleniem z lewej góry ---
    t = np.clip((r - R_OBR) / (R_MUSZLA - R_OBR), 0, 1)
    prof = np.cos(np.pi * (t - 0.42) / 1.16)            # kształt przekroju, szczyt bliżej okna
    dn = -np.sin(np.pi * (t - 0.42) / 1.16)              # nachylenie na zewnątrz (+) / do środka (-)
    with np.errstate(invalid='ignore', divide='ignore'):
        ux, uy = np.where(r > 0, x / r, 0), np.where(r > 0, y / r, 0)
    n = np.stack([ux * dn, uy * dn, np.clip(prof, 0.05, 1)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    dif = np.clip(n @ L, 0, 1)
    spec = np.clip(n @ (L + np.array([0, 0, 1])) / np.linalg.norm(L + np.array([0, 0, 1])), 0, 1) ** 24
    guma = np.array([0.095, 0.095, 0.105])
    # drobna faktura gumy
    rng = np.random.default_rng(7)
    szum = rng.normal(0, 1, (h // 4 + 1, w // 4 + 1))
    szum = np.kron(szum, np.ones((4, 4)))[:h, :w]
    kol = guma[None, None] * (0.45 + 1.9 * dif)[..., None] + 0.10 * spec[..., None] + 0.006 * szum[..., None]
    # rowki na muszli
    for rr in (0.395, 0.445):
        kol *= (1 - 0.45 * np.exp(-((r - rr) / 0.004) ** 2))[..., None]
    _over(img, kol, _smooth(R_OBR - px, R_OBR + px, r) * (1 - _smooth(R_MUSZLA - px, R_MUSZLA + px, r)))

    # --- metalowa obręcz soczewki ---
    t = np.clip((r - R_OKNO) / (R_OBR - R_OKNO), 0, 1)
    swiat = np.clip(0.5 - 0.5 * (ux * L[0] + uy * L[1]) / np.hypot(L[0], L[1]), 0, 1)  # jasno po stronie przeciwnej do światła (wnętrze)
    kol = np.array([0.20, 0.21, 0.23])[None, None] * (0.6 + 0.9 * swiat * (1 - t))[..., None]
    _over(img, kol, _smooth(R_OKNO - px, R_OKNO + px, r) * (1 - _smooth(R_OBR - px, R_OBR + px, r)))

    # --- szkło: przezroczyste w środku, ciemniejsze i lekko niebieskie przy brzegu ---
    wn = 1 - _smooth(R_OKNO - px, R_OKNO + px, r)
    vin = _smooth(0.55 * R_OKNO, R_OKNO, r) ** 1.6
    _over(img, [0.01, 0.02, 0.04], wn * (0.03 + 0.75 * vin))
    # odblask w lewym górnym rogu szkła
    ang = np.arctan2(y, x)
    luk = np.exp(-((r - 0.86 * R_OKNO) / 0.018) ** 2) * np.exp(-((ang + 2.25) / 0.38) ** 2)
    _over(img, [0.85, 0.92, 1.0], wn * 0.22 * luk)

    # --- siatka: cienki krzyż, grube ramiona przy brzegu, kropki mil-dot ---
    cz = [0.02, 0.02, 0.02]
    cien_l, gr = 0.5 / H, 1.5 / H
    w_gr = 0.62 * R_OKNO
    siat = np.zeros((h, w))
    siat = np.maximum(siat, _rect(x, y, -R_OKNO, R_OKNO, -cien_l, cien_l, px * 0.7))
    siat = np.maximum(siat, _rect(x, y, -cien_l, cien_l, -R_OKNO, R_OKNO, px * 0.7))
    for a, b in ((-R_OKNO, -w_gr), (w_gr, R_OKNO)):
        siat = np.maximum(siat, _rect(x, y, a, b, -gr, gr, px))
        siat = np.maximum(siat, _rect(x, y, -gr, gr, a, b, px))
    for k in range(1, 6):
        for sx, sy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            d = np.hypot(x - sx * 8 / H, y - sy * 8 / H)
            siat = np.maximum(siat, 1 - _smooth(1.0 / H - px, 1.0 / H + px, d))
    _over(img, cz, siat * wn)
    # czerwony punkt w środku
    _over(img, [1.0, 0.12, 0.08], 1 - _smooth(0.6 / H - px, 0.6 / H + px, r))

    # zmniejszenie (premultiplied → zwykłe RGBA)
    img = img.reshape(H, SS, W, SS, 4).mean(axis=(1, 3))
    a = img[..., 3:]
    rgb = np.where(a > 0, img[..., :3] / np.maximum(a, 1e-6), 0)
    rgb = np.round(np.clip(rgb, 0, 1) * (POZIOMY - 1)) / (POZIOMY - 1)
    a = np.round(a * 8) / 8
    out = np.concatenate([rgb, a], -1)
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), 'RGBA')


def png():
    buf = io.BytesIO()
    obraz().save(buf, 'PNG', optimize=True)
    return buf.getvalue()


if __name__ == '__main__':
    import sys
    obraz().save(sys.argv[1] if len(sys.argv) > 1 else 'okular.png')
