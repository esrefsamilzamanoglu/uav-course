"""Exercise the teaching API through real HTTP; no native flight ports are used."""
import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

LAB = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(LAB/'backend'))
import server


class TeachingHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = server.Service()
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        cls.http.service = cls.service
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.http.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.thread.join(3)

    def request(self, path, data=None, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        request = urllib.request.Request(self.base+path,
            None if data is None else json.dumps(data).encode(), headers)
        try:
            with urllib.request.urlopen(request, timeout=4) as response:
                return response.status, response.headers.get('Content-Type'), response.read()
        except urllib.error.HTTPError as response:
            return response.code, response.headers.get('Content-Type'), response.read()

    def test_code_catalog_and_actual_source_before_simulation_start(self):
        status, mime, body = self.request('/api/code/catalog')
        self.assertEqual((status, mime.split(';')[0]), (200, 'application/json'))
        files = {x['file'] for x in json.loads(body)['files']}
        self.assertEqual(files, {'control.py','vision.py','server.py','native_runtime.py'})
        _, _, body = self.request('/api/code/source?file=control.py')
        source = json.loads(body)
        self.assertEqual(source['lines'], (LAB/'backend/control.py').read_text(encoding='utf-8').splitlines())
        self.assertFalse(source['source_changed'])

    def test_source_endpoint_rejects_traversal_and_absolute_paths(self):
        for name in ('../requirements.txt', 'C:/Windows/win.ini', 'execution_trace.py', ''):
            status, _, _ = self.request('/api/code/source?file='+urllib.parse.quote(name, safe=''))
            # An absent/blank query defaults to the documented main module.
            self.assertEqual(status, 200 if name == '' else 400)

    def test_trace_cursor_validation_and_bounded_empty_result(self):
        status, _, body = self.request('/api/code/trace?after=0&limit=120')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['events'], [])
        for query in ('after=-1', 'after=notanumber', 'limit=201', 'limit=-1'):
            self.assertEqual(self.request('/api/code/trace?'+query)[0], 400)

    def test_disconnected_state_has_separate_empty_follow_sensor(self):
        _, _, body = self.request('/api/state')
        state = json.loads(body)
        self.assertFalse(state['follow_camera']['available'])
        self.assertEqual({x['id'] for x in state['follow_camera']['modes']}, {'chase','orbit','side','top'})
        self.assertIn('execution', state)
        self.assertEqual(self.request('/api/follow.jpg')[0], 404)

    def test_mission_choice_reaches_controller_without_defaulting_to_g2(self):
        calls = []
        class FakeController:
            connected = True
            def mission_start(self, mission): calls.append(mission)
        self.service.controller = FakeController()
        try:
            for mid in ('G1','G3'):
                self.assertEqual(self.request('/api/command', dict(action='mission_start', mission=mid))[0], 200)
            self.assertEqual(calls, ['G1','G3'])
        finally: self.service.controller = None

    def test_viewer_mode_dispatch_has_no_flight_controller_dependency(self):
        calls = []
        class FakeFollow:
            def set_mode(self, mode): calls.append(mode)
        self.service.follow_camera = FakeFollow()
        try:
            self.assertEqual(self.request('/api/command', dict(action='camera_follow', mode='orbit'))[0], 200)
            self.assertEqual(calls, ['orbit'])
            self.assertEqual(self.request('/api/command', dict(action='camera_follow', mode='side'), origin='https://example.org')[0], 403)
            self.assertEqual(calls, ['orbit'])
        finally: self.service.follow_camera = None


if __name__ == '__main__': unittest.main(verbosity=2)
