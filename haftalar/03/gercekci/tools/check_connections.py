"""Read-only second-GCS check. Close Mission Planner before using its port."""
import json
import argparse
import time
import urllib.request
from pymavlink import mavutil

def snapshot(base_url):
    with urllib.request.urlopen(base_url.rstrip('/')+'/api/state', timeout=8) as response:
        return json.load(response)

def verify(base_url='http://127.0.0.1:8787'):
    before = snapshot(base_url)
    if not before.get('connected'): raise RuntimeError('ROTA GCS: once simulasyonu baslatin, telemetriyi bekleyin.')
    link = mavutil.mavlink_connection('tcp:127.0.0.1:5762', source_system=255, source_component=190)
    try:
        if not link.wait_heartbeat(timeout=12): raise RuntimeError('5762: ArduPilot heartbeat gelmedi; Mission Planner baglantisini kapatip tekrar deneyin.')
        expected = {'SERIAL1_PROTOCOL': 2, 'MAV_GCS_SYSID': 253, 'MAV_GCS_SYSID_HI': 0, 'FS_GCS_ENABLE': 5}
        for name in expected: link.mav.param_request_read_send(1, 1, name.encode(), -1)
        values = {}; deadline = time.monotonic()+12
        while time.monotonic() < deadline and len(values) < len(expected):
            message = link.recv_match(type='PARAM_VALUE', blocking=True, timeout=.3)
            if message and message.param_id in expected: values[message.param_id] = message.param_value
        for name, value in expected.items():
            if values.get(name) != value: raise RuntimeError(f'{name}: beklenen {value}, okunan {values.get(name)}. Simulasyonu yeniden baslatin.')
        if not snapshot(base_url).get('connected'): raise RuntimeError('Ikinci baglanti sirasinda ROTA telemetrisi kesildi.')
        print('OK  ROTA TCP 5760 ve ikinci GCS TCP 5762 ayni ArduPilot oturumuna bagli.')
        print('OK  Mission Planner ayrildiginda failsafe ROTA heartbeat kaynagini izler (253).')
    finally: link.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8787')
    verify(parser.parse_args().url)
