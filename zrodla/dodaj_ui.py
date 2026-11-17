#!/usr/bin/env python3
"""Dopisuje czcionkę okien UI (axon:ui, axon:ui_bold: Inter z paczki) i logo AXONCORE (axoncore/ui.py)
do gotowych zipów, bez przebudowy całej paczki. Stare pliki o tych samych ścieżkach są zastępowane.
build_pack.py (przez gen_axoncore.pliki()) robi to samo przy pełnej przebudowie.

Bez argumentów łata QualityArmory-21-axon.zip i QualityArmory-21-axon-1.21.11.zip."""
import hashlib, os, sys, zipfile

from axoncore.ui import pliki

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip']


def patch(path, files):
    zin = zipfile.ZipFile(path)
    entries = [(i, zin.read(i.filename)) for i in zin.infolist() if i.filename not in files]
    zin.close()
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for info, data in entries:
            zout.writestr(info, data)
        for fn, data in sorted(files.items()):
            zi = zipfile.ZipInfo(fn, date_time=(2026, 11, 17, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, data)
    print('ui: %s, %d plików, sha1 %s' % (os.path.basename(path), len(files),
                                         hashlib.sha1(open(path, 'rb').read()).hexdigest()))


def main():
    files = pliki()
    for path in sys.argv[1:] or [os.path.join(ROOT, z) for z in ZIPS]:
        if os.path.exists(path):
            patch(path, files)


if __name__ == '__main__':
    sys.exit(main())
