"""Check this checkout without starting a vehicle or changing flight state."""
from pathlib import Path
import ast
import importlib.metadata
import json
import re
import sys
import xml.etree.ElementTree as ET

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parents[2]

def main():
    errors = []
    def check(ok, label):
        print(('OK  ' if ok else 'HATA ') + label)
        if not ok: errors.append(label)
    for package in ('numpy', 'opencv-python', 'Pillow', 'pymavlink'):
        try: print(f'OK  {package} {importlib.metadata.version(package)}')
        except importlib.metadata.PackageNotFoundError: check(False, package + ' eksik')
    required = [REPO/'windows/.pixi/envs/default/python.exe',
        REPO/'windows/.local/ardupilot_gazebo/build-windows/ArduPilotPlugin.dll',
        BASE/'plugin/.local/build/PayloadMechanics.dll', BASE/'plugin/.local/build/realistic_bridge.exe',
        BASE/'models/competition_assets/textures/grass_albedo.png',
        REPO/'haftalar/02/simulasyon/tools/runtime.py']
    for path in required: check(path.is_file(), str(path.relative_to(REPO)))
    for entry in json.loads((REPO/'windows/downloads.json').read_text(encoding='utf-8-sig')):
        import hashlib
        path = REPO/'windows/.local/sitl'/entry['file']
        check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], 'SITL SHA256: ' + entry['file'])
    for path in (BASE/'backend').glob('*.py'):
        try: ast.parse(path.read_text(encoding='utf-8-sig')); check(True, 'Python: ' + path.name)
        except SyntaxError as error: check(False, str(error))
    dist = BASE/'gcs/frontend/dist'
    index = dist/'index.html'
    check(index.is_file(), 'Hazir GCS arayuzu')
    if index.is_file():
        for asset in re.findall(r'(?:src|href)="((?:\./|/)[^"?#]+)', index.read_text(encoding='utf-8')):
            check((dist/asset.lstrip('./')).is_file(), 'GCS: ' + asset)
    world = BASE/'world/competition.sdf'
    check(world.is_file(), 'Bu bilgisayarda uretilmis dunya')
    if world.is_file():
        tree = ET.parse(world)
        resources = {node.text for tag in ('uri','albedo_map','normal_map','roughness_map') for node in tree.findall('.//'+tag) if node.text}
        missing = [p for p in resources if not Path(p).is_file()]
        check(not missing, f'Dunya kaynaklari ({len(resources)} dosya)')
        for path in missing: print('     Eksik: ' + path)
    if '--live' in sys.argv:
        from check_connections import verify
        try: verify()
        except Exception as error: check(False, str(error))
    print(f'\n{len(errors)} hata. ' + ('Kur.cmd dosyasini tekrar calistirin.' if errors else 'Kurulum hazir.'))
    return int(bool(errors))

if __name__ == '__main__': sys.exit(main())
