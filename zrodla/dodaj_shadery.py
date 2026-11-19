#!/usr/bin/env python3
"""Podmienia shadery AxonMap/AxonOverlay w gotowych zipach bez pełnej przebudowy paczki.

Shadery są tylko w nakładkach (overlays), tak jak robi to build_pack.py:
- axon_shadery/        (1.21.2-1.21.5)  z zrodla/shadery,
- axon_shadery_1_21_0/ (1.21-1.21.1)   z zrodla/shadery bez przestrzeni nazw minecraft:,
- axon_shadery_1_21_11/ (1.21.11)      z zrodla/shadery_1_21_11.
pack.mcmeta jest brany z zrodla/pack.mcmeta (tam są wpisy nakładek).
Stare shadery w assets/minecraft/shaders/ (poza nakładkami) są usuwane, bo psują 1.21.11.
Na końcu przebudowuje QualityArmory-21-axon-1.21.11-shadery.zip (buduj_1_21_11.py), który AxonGuns
wysyła klientom 1.21.11.
"""
import os
from pathlib import Path
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ZIPS = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip']
CORE = '/assets/minecraft/shaders/core/'
INCLUDE = '/assets/minecraft/shaders/include/'


def _dir(name):
    # *.glsl to wspólne kawałki (#moj_import <minecraft:...>), reszta to shadery core
    return INCLUDE if name.endswith('.glsl') else CORE


def shader_files():
    files = {}
    for name in sorted(os.listdir(os.path.join(HERE, 'shadery'))):
        data = open(os.path.join(HERE, 'shadery', name), 'rb').read()
        files['axon_shadery' + _dir(name) + name] = data
        files['axon_shadery_1_21_0' + _dir(name) + name] = data.replace(b'"minecraft:core/', b'"').replace(b'<minecraft:', b'<')
    for name in sorted(os.listdir(os.path.join(HERE, 'shadery_1_21_11'))):
        files['axon_shadery_1_21_11' + _dir(name) + name] = open(os.path.join(HERE, 'shadery_1_21_11', name), 'rb').read()
    files['pack.mcmeta'] = open(os.path.join(HERE, 'pack.mcmeta'), 'rb').read()
    return files


def scanner_files():
    source = Path(HERE, "axonore")
    return {asset.relative_to(source).as_posix(): asset.read_bytes()
            for asset in (source / "assets").rglob("*") if asset.is_file()}


def main():
    files = shader_files()
    files.update(scanner_files())
    overlays = ('axon_shadery/', 'axon_shadery_1_21_0/', 'axon_shadery_1_21_11/')
    for zip_name in ZIPS:
        path = os.path.join(ROOT, zip_name)
        if not os.path.exists(path):
            continue
        tmp = path + '.tmp'
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                name = info.filename
                if name in files or name.startswith('assets/minecraft/shaders/') \
                        or (name.startswith(overlays) and '/shaders/' in name):
                    continue
                dst.writestr(info, src.read(name))
            for name, data in sorted(files.items()):
                zi = zipfile.ZipInfo(name, date_time=(2026, 10, 18, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o644 << 16
                dst.writestr(zi, data)
        shutil.move(tmp, path)
        print('zaktualizowano', zip_name, len(files), 'plików')
    # AxonGuns daje klientom 1.21.11 osobny zip z shaderami w assets/ (bez nakładek): budujemy go od nowa
    import buduj_1_21_11
    buduj_1_21_11.main()


if __name__ == '__main__':
    sys.exit(main())
