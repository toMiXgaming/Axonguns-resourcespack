#!/usr/bin/env python3
"""Podgląd wariantów AxonGuns (gen_axonguns.py): biodro i celowanie w pierwszej osobie oraz poza w trzeciej.
Użycie: python3 zrodla/preview_axonguns.py <rozpakowana paczka> <wyjście.png> [broń ...]"""
import json, os, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render import *
from preview import fp_view, label, ortho_view, fit_ortho, light_preview, SKY
import gen_axonguns as ga


def fp(disp, q, W, H, charged):
    cv = Canvas(W, H, grad=SKY)
    cv.col[int(cv.col.shape[0] * 0.62):] = (98, 128, 74)
    xf, pr = first_person(disp, W, H, left=False, charged=charged)
    draw(cv, q, xf, pr, light_mc3d, near=0.05)
    im = cv.image()
    from PIL import ImageDraw
    d = ImageDraw.Draw(im); c = (W // 2, H // 2)
    d.line([(c[0] - 7, c[1]), (c[0] + 7, c[1])], fill=(255, 255, 255)); d.line([(c[0], c[1] - 7), (c[0], c[1] + 7)], fill=(255, 255, 255))
    return im


def tp(disp, q, W, H, crossbow):
    xf_item, _, _, _ = third_person_world(disp, crossbow=crossbow)
    gun = []
    for qq in q:
        P = qq['P']
        n = xf_item(P[:1] + qq['n'][None]) - xf_item(P[:1])
        gun.append(dict(qq, P=xf_item(P), n=n[0] / (np.linalg.norm(n[0]) + 1e-9)))
    allq = gun + player_quads(crossbow=crossbow)
    cv = Canvas(W, H, grad=SKY)
    xf, pr, _ = fit_ortho(allq, ortho_view(-125, 12), W, H, 0.06)
    draw(cv, allq, xf, pr, light_preview)
    return cv.image()


def row(root, name):
    m, q = load_model(os.path.join(root, 'assets/qualityarmory/models/gun', name + '.json'), resolver_for(root))
    d = m.get('display', {})
    w = ga.warianty(d)
    W, H = 400, 225
    ims = [label(fp(dict(d, **w['biodro']), q, W, H, True), name + ': biodro (kusza)', 14),
           label(fp(dict(d, **w['cel']), q, W, H, True), 'Shift: celowanie (kusza)', 14),
           label(tp(d, q, 225, 225, True), 'poza kuszy', 14),
           label(fp(dict(d, **w['biodro_u']), q, W, H, False), 'tryb uzywanie: biodro', 14),
           label(fp(dict(d, **w['cel_u']), q, W, H, False), 'tryb uzywanie: celowanie', 14),
           label(tp(dict(d, **w['biodro_u']), q, 225, 225, False), 'uzywanie: zwykla poza', 14)]
    out = Image.new('RGB', (2 * W + 225 + 8, 2 * H + 4), (20, 22, 26))
    for i, im in enumerate(ims):
        r, c = divmod(i, 3)
        out.paste(im, ((W + 4) * c if c < 2 else 2 * W + 8, (H + 4) * r))
    return out


if __name__ == '__main__':
    root, dst = sys.argv[1], sys.argv[2]
    rows = [row(root, n) for n in (sys.argv[3:] or ['ak47', 'glock', 'awp'])]
    out = Image.new('RGB', (rows[0].width, sum(r.height + 6 for r in rows)), (20, 22, 26))
    y = 0
    for r in rows:
        out.paste(r, (0, y)); y += r.height + 6
    out.save(dst)
    print('zapisano', dst)
