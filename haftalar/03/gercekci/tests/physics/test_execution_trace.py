"""Actual source-line tracing contracts; no simulator or flight ports are used."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'backend'))
from control import Controller
from execution_trace import ExecutionTracer
import vision


class ExecutionTraceTests(unittest.TestCase):
    def controller(self):
        camera = types.SimpleNamespace(estimates={}, observations={}, perception_enabled=False,
            pickup_color=None)
        c = Controller(types.SimpleNamespace(run=None), camera, {'home_enu': [-24,0,.9]}, lambda *args:None)
        c.mission.update(id='G1', status='running')
        c.vehicle = lambda:dict(armed=True,position_enu=[-24,0,12.9],velocity_enu=[0,0,0])
        c.servo = lambda *args:None
        c.takeoff = lambda *args:None
        c.mode = lambda *args:None
        c.send = lambda *args:None
        c.connected = True
        return c

    def test_actual_g1_lines_and_branch_counts_not_synthetic_phase_mapping(self):
        c = self.controller()
        goals = []
        c.goto = lambda goal,**kwargs:goals.append(list(goal))
        c.wait = lambda *args,**kwargs:None
        previous = sys.gettrace()
        c._run_traced_mission('G1')
        self.assertIs(sys.gettrace(), previous)
        result = c.execution.snapshot(limit=500)
        lines = c.execution.source('control.py')['lines']
        curve_line = next(i+1 for i,s in enumerate(lines) if 'self.goto([38*math.sin' in s)
        pickup_line = next(i+1 for i,s in enumerate(lines) if 'self.camera.pickup_color=color' in s)
        curve = [e for e in result['events'] if e['event']=='line' and e['line']==curve_line]
        # Full event ring is intentionally bounded; request the complete ring
        # here because the 73 actual loop iterations exceed the HTTP page size.
        full = list(c.execution._events)
        self.assertEqual(sum(e['event']=='line' and e['line']==curve_line for e in full),73)
        self.assertFalse(any(e['event']=='line' and e['line']==pickup_line for e in full))
        self.assertEqual(len(goals),77)
        self.assertTrue(all(e['file']=='control.py' and e['line']==e['lineno'] for e in full))
        self.assertTrue(curve)
        self.assertEqual(result['status'],'completed')
        self.assertFalse(result['active'])
        self.assertEqual(result['source_sha256']['control.py'],hashlib.sha256((ROOT/'backend/control.py').read_bytes()).hexdigest())

    def test_real_goto_wait_stack_persists_and_other_threads_are_not_traced(self):
        c = self.controller()
        error = []
        def worker():
            try:c._run_traced_mission('G1')
            except BaseException as exc:error.append(exc)
        previous = sys.gettrace()
        thread = threading.Thread(target=worker)
        thread.start()
        try:
            deadline = time.monotonic()+3
            sample = None
            while time.monotonic()<deadline:
                sample = c.execution.summary()
                if sample['current'] and sample['current'].get('wait',{}):break
                time.sleep(.005)
            current = sample['current']
            self.assertEqual(current['wait']['kind'],'goto')
            self.assertEqual(current['wait']['goal_enu'],[-40.,-105.,12.9])
            names = [x['function'] for x in current['stack']]
            self.assertIn('Controller.run_mission',names)
            self.assertIn('Controller.goto',names)
            first_seq = sample['seq']
            time.sleep(.11)
            later = c.execution.summary()['current']
            self.assertGreaterEqual(later['wait']['elapsed_s'],.08)
            self.assertGreater(later['seq'],first_seq)
            self.assertGreater(later['wait']['distance_m'],100)
            other = threading.Thread(target=c.grips)
            other.start();other.join(1)
            events = c.execution.snapshot(limit=500)['events']
            self.assertTrue(all(e['thread_id']==thread.ident for e in events))
            self.assertFalse(any(e['function']=='Controller.grips' for e in events))
            self.assertIs(sys.gettrace(),previous)
            self.assertNotIn('events',c.execution.summary())
        finally:
            c.cancel.set();thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(error,[])
        self.assertEqual(c.execution.summary()['status'],'paused')
        self.assertIsNone(c.execution.summary()['current']['wait'])

    def fixture(self, folder, source, name='control.py', **kwargs):
        path=Path(folder)/name
        path.write_text(source,encoding='utf-8',newline='\n')
        namespace={}
        exec(compile(source,str(path),'exec'),namespace)
        return ExecutionTracer(folder,**kwargs),namespace

    def test_exception_and_previous_trace_restoration_without_locals_or_values(self):
        with tempfile.TemporaryDirectory() as folder:
            tracer,ns=self.fixture(folder,"def fail():\n    password = 'do-not-export'\n    raise ValueError(password)\n")
            original=sys.gettrace()
            def previous(frame,event,arg):return previous
            try:
                sys.settrace(previous)
                with self.assertRaises(ValueError):
                    with tracer.capture('G3'):ns['fail']()
                self.assertIs(sys.gettrace(),previous)
            finally:sys.settrace(original)
            result=tracer.snapshot()
            exceptions=[e for e in result['events'] if e['event']=='exception']
            self.assertEqual(exceptions[0]['exception_type'],'ValueError')
            self.assertEqual(result['status'],'failed')
            self.assertNotIn('do-not-export',json.dumps(result))
            self.assertTrue(all('locals' not in e and 'return_value' not in e for e in result['events']))

    def test_source_allowlist_and_cached_source_hash_survive_disk_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            original='def branch(flag):\n    if flag:\n        return 7\n    return 9\n'
            tracer,ns=self.fixture(folder,original)
            with tracer.capture('G1'):self.assertEqual(ns['branch'](True),7)
            lines=[e['line'] for e in tracer.snapshot()['events'] if e['event']=='line']
            self.assertIn(3,lines);self.assertNotIn(4,lines)
            (Path(folder)/'control.py').write_text('# modified after import\n'+original,encoding='utf-8')
            source=tracer.source('control.py')
            self.assertEqual(source['lines'],original.splitlines())
            self.assertTrue(source['source_changed'])
            self.assertEqual(source['sha256'],hashlib.sha256(original.encode()).hexdigest())
            for invalid in ('../control.py',str(Path(folder)/'control.py'),'execution_trace.py','server.py'):
                with self.assertRaises(ValueError):tracer.source(invalid)

    def test_ring_bounds_cursor_gaps_and_safe_context(self):
        with tempfile.TemporaryDirectory() as folder:
            tracer,ns=self.fixture(folder,'def repeat():\n    for i in range(100):\n        x = i * 2\n    return x\n',capacity=16)
            tracer.update_context(phase='2',password='do-not-export',goal_enu=[1,2,3])
            with tracer.capture('G1'):
                tracer.update_context(phase='2',password='do-not-export',goal_enu=[1,2,3])
                ns['repeat']()
            result=tracer.snapshot(limit=3)
            self.assertEqual(len(result['events']),3)
            self.assertGreater(result['dropped'],0)
            self.assertEqual(result['skipped'],13)
            self.assertEqual(result['events'][-1]['seq'],result['seq'])
            self.assertTrue(all(e['context']['phase']=='2' for e in result['events']))
            self.assertNotIn('do-not-export',json.dumps(result))
            self.assertEqual(tracer.snapshot(after_seq=result['seq'])['events'],[])
            self.assertEqual(tracer.snapshot(limit=0)['events'],[])

    def test_real_vision_wrapper_has_separate_lane_and_restores_on_failure(self):
        c=self.controller()
        wrapped=c.execution.wrap(vision.project,lane='vision')
        meta={'width':960,'height':720,'position_xyz':[0,0,10],
              'quaternion_xyzw':[-.5,.5,.5,.5]}
        previous=sys.gettrace()
        with c.execution.capture('G2'):
            # A real control function is the mission lane; a separate, explicit
            # camera worker is the only thread that traces the vision pipeline.
            c.grips()
            thread=threading.Thread(target=lambda:wrapped(480,360,meta))
            thread.start();thread.join(2)
            result=c.execution.summary()
            self.assertEqual(result['current']['file'],'control.py')
            self.assertEqual(result['lanes']['vision']['file'],'vision.py')
            self.assertNotEqual(result['current']['thread_id'],result['lanes']['vision']['thread_id'])
            self.assertTrue(any(e['function']=='rotation' for e in c.execution.snapshot(limit=500)['events']))
        with self.assertRaises(ValueError):wrapped(480,360,dict(meta,quaternion_xyzw=[0,0,0,0]))
        self.assertIs(sys.gettrace(),previous)
        events=c.execution.snapshot(limit=500)['events']
        self.assertTrue(any(e['lane']=='vision' and e['event']=='exception' for e in events))
        self.assertFalse(c.execution.summary()['active'])

    def test_catalog_marks_source_only_files(self):
        tracer=ExecutionTracer(ROOT/'backend')
        catalog={f['file']:f for f in tracer.catalog()['files']}
        self.assertEqual(set(catalog),{'control.py','vision.py','server.py','native_runtime.py'})
        self.assertTrue(catalog['control.py']['trace_enabled'])
        self.assertFalse(catalog['server.py']['trace_enabled'])
        goto=next(f for f in catalog['control.py']['functions'] if f['name']=='Controller.goto')
        self.assertLess(goto['line'],goto['end_line'])
        self.assertIn('ENU',goto['explanation'])

    def test_new_mission_keeps_cursor_monotonic_and_clears_old_lane_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            tracer,ns=self.fixture(folder,'def step():\n    return 1\n')
            tracer.wrap(ns['step'],lane='vision')()
            old=tracer.snapshot()
            with tracer.capture('G1'):ns['step']()
            new=tracer.snapshot(after_seq=old['seq'])
            self.assertGreater(new['seq'],old['seq'])
            self.assertTrue(new['events'])
            self.assertIsNone(new['lanes']['vision'])
            self.assertFalse(new['cursor_ahead'])


if __name__=='__main__':unittest.main(verbosity=2)
