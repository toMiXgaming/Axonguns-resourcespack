#!/usr/bin/env python3
"""Dopisuje tablicę wyników AxonScoreboard (axoncore/tablica.py: panel, logo, ikony i paski jako znaki
czcionki minecraft:default, U+EA00–U+EA5F i odstępy U+EB00–U+EB18) do gotowych zipów, bez przebudowy całej
paczki. Stare pliki o tych samych ścieżkach są zastępowane. build_pack.py (przez gen_axoncore.pliki()) robi
to samo przy pełnej przebudowie.

Bez argumentów łata QualityArmory-21-axon.zip, jego kopię -1.21.11.zip i QualityArmory-21-axon-1.21.11-shadery.zip."""
import hashlib, os, sys, zipfile

from axoncore.tablica import pliki

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def patch(path, files):
    zin = zipfile.ZipFile(path)
    names = set(zin.namelist())
    if not any(n.startswith('axon_1_21_0/') for n in names):
        files = {k: v for k, v in files.items() if not k.startswith('axon_1_21_0/')}
    # stare czcionki panelu HUD (hud_t, hud_0…) zastąpiła jedna axon:hud
    stale = lambda n: n.startswith('assets/axon/font/hud_') and n.endswith('.json')
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files and not stale(i.filename)]
    zin.close()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 15, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('tablica: %s, %d plików, sha1 %s' % (os.path.basename(path), len(files),
                                             hashlib.sha1(open(path, 'rb').read()).hexdigest()))


def main():
    files = pliki()
    paths = sys.argv[1:] or [os.path.join(ROOT, z) for z in ZIPS]
    for p in paths:
        patch(p, dict(files))
    from sprawdz_paczke import main as sprawdz
    if sprawdz(paths):
        raise SystemExit('paczka nie przeszła sprawdz_paczke.py')


if __name__ == '__main__':
    main()
