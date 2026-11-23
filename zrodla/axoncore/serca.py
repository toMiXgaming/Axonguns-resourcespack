"""Schowane serca gracza: puste (przezroczyste) sprite'y serc z paska zdrowia.

HP pokazuje kafel zdrowia AxonScoreboard (sylwetka z 7 częściami ciała, axoncore/zdrowie.py), a zwykłe
zdrowie pod spodem to tylko suma części. Serca wierzchowca (vehicle_*) zostają."""
import io
from PIL import Image

RODZAJE = ['', 'hardcore_', 'poisoned_', 'poisoned_hardcore_', 'withered_', 'withered_hardcore_',
           'absorbing_', 'absorbing_hardcore_', 'frozen_', 'frozen_hardcore_']
STANY = ['full', 'full_blinking', 'half', 'half_blinking']
POJEMNIKI = ['container', 'container_blinking', 'container_hardcore', 'container_hardcore_blinking']
KATALOG = 'assets/minecraft/textures/gui/sprites/hud/heart/'


def nazwy():
    return POJEMNIKI + [r + s for r in RODZAJE for s in STANY]


def pliki():
    buf = io.BytesIO()
    Image.new('RGBA', (9, 9), (0, 0, 0, 0)).save(buf, 'PNG', optimize=True)
    png = buf.getvalue()
    return {KATALOG + n + '.png': png for n in nazwy()}
