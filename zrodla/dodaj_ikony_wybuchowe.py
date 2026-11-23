#!/usr/bin/env python3
"""Dopisuje do gotowych zipów ikony części materiałów wybuchowych (axoncore/items.py):
korpus_granatu, zapalnik, plastik, uklad_czasowy. To samo robi dodaj_axoncore.py przy pełnej
przebudowie (potrzebuje build/ z gen_narzedzia.py), ten skrypt działa bez niej."""
import io, json, os, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from axoncore.items import ITEMS

NAZWY = ['korpus_granatu', 'zapalnik', 'plastik', 'uklad_czasowy']
ZIPY = ['QualityArmory-21-axon.zip', 'QualityArmory-21-axon-1.21.11.zip', 'QualityArmory-21-axon-1.21.11-shadery.zip']


def _json(data):
    return (json.dumps(data, indent=2, ensure_ascii=False) + '\n').encode()


def pliki(nakladka_1_21_0=True):
    files = {}
    for name in NAZWY:
        buf = io.BytesIO()
        ITEMS[name].save(buf, 'PNG', optimize=True)
        files['assets/axon/textures/item/%s.png' % name] = buf.getvalue()
        files['assets/axon/models/block/%s.json' % name] = _json(
            {'parent': 'minecraft:item/generated', 'textures': {'layer0': 'axon:item/' + name}})
        files['assets/axon/items/%s.json' % name] = _json(
            {'model': {'type': 'minecraft:model', 'model': 'axon:block/' + name}})
        if nakladka_1_21_0:
            files['axon_1_21_0/assets/axon/models/item/%s.json' % name] = json.dumps(
                {'parent': 'axon:block/' + name}, indent=2).encode()
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
    print('ikony wybuchowe: %s, %d plików' % (os.path.basename(path), len(files)))


if __name__ == '__main__':
    for z in sys.argv[1:] or [os.path.join(HERE, '..', n) for n in ZIPY]:
        patch(z)
