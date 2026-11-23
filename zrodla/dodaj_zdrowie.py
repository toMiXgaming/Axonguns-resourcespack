#!/usr/bin/env python3
"""Dopisuje do gotowych zipów system zdrowia AxonCore:
- przedmioty medyczne axon:<nazwa> (modele 3D z build/, najpierw python3 gen_medyczne.py),
- sylwetkę gracza i ikonki stanów (axoncore/zdrowie.py) w czcionkach minecraft:default i axon:hud.

Czcionki default.json i hud.json są pisane od nowa z generatora tablicy (axoncore/tablica.py i hud.py),
więc razem z sylwetką trafia do zipów wszystko, co generator ma, a czego zip jeszcze nie miał.
Pełna przebudowa (build_pack.py -> gen_axoncore.pliki()) robi to samo."""
import os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_medyczne
from axoncore import tablica

ZIPY = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def pliki(nakladka_1_21_0=True):
    files = gen_medyczne.pliki(nakladka_1_21_0=nakladka_1_21_0)
    for fn, data in tablica.pliki().items():
        if '/font/' in fn:
            files[fn] = data
    return files


def patch(path):
    with zipfile.ZipFile(path) as z:
        overlay = any(n.startswith('axon_1_21_0/') for n in z.namelist())
    files = pliki(overlay)
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            if info.filename not in files:
                zout.writestr(info, zin.read(info.filename))
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 23, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    os.replace(tmp, path)
    print('zdrowie: %s, %d plików' % (os.path.basename(path), len(files)))


if __name__ == '__main__':
    zips = sys.argv[1:] or [os.path.join(HERE, '..', n) for n in ZIPY]
    for z in zips:
        patch(z)
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, 'sprawdz_paczke.py')] + zips, check=True)
