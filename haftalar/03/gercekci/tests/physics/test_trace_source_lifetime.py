"""A world reset must retain source matching the process-imported Python code."""
from pathlib import Path
import sys,tempfile,types,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import server
from control import Controller
from execution_trace import ExecutionTracer

class InlineThread:
    def __init__(self,target,**kwargs):self.target=target
    def start(self):self.target()

class FakeCamera:
    def __init__(self,*args):pass
    def update(self):pass
    def start(self):pass
    def close(self):pass

class SourceLifetimeTests(unittest.TestCase):
    def test_service_reuses_import_source_across_world_resets_and_rebinds_context(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'control.py'
            original='def step():\n    return 1\n'
            path.write_text(original,encoding='utf-8',newline='\n')
            namespace={};exec(compile(original,str(path),'exec'),namespace)
            with patch.object(server,'ExecutionTracer',side_effect=lambda *_:ExecutionTracer(root)):
                service=server.Service();cached=service.execution
                sha=cached.source('control.py')['sha256']
                with patch.object(service.runtime,'start',return_value=root), \
                     patch.object(service.runtime,'close'), \
                     patch.object(server,'Camera',FakeCamera), \
                     patch.object(Controller,'start'), \
                     patch.object(server.threading,'Thread',InlineThread):
                    service.start();first=service.controller
                    self.assertIs(first.execution,cached)
                    service.close()
                    changed='# changed after Python import\n'+original
                    path.write_text(changed,encoding='utf-8',newline='\n')
                    service.start();second=service.controller
                    self.assertIsNot(first,second)
                    self.assertIs(second.execution,cached)
                    self.assertEqual(second.execution.source('control.py')['lines'],original.splitlines())
                    self.assertEqual(second.execution.source('control.py')['sha256'],sha)
                    self.assertTrue(second.execution.source('control.py')['source_changed'])
                    second.mission.update(id='G3',phase='second-controller',status='running')
                    with cached.capture('G3'):namespace['step']()
                    self.assertEqual(cached.summary()['current']['context']['phase'],'second-controller')
                    self.assertEqual(cached.summary()['current']['line'],2)
                    service.close()
                # A newly constructed service has a new startup source cache.
                # Loading edited executable modules requires a full Python restart.
                fresh=server.Service()
                self.assertIsNot(fresh.execution,cached)
                self.assertEqual(fresh.execution.source('control.py')['lines'],changed.splitlines())
                self.assertNotEqual(fresh.execution.source('control.py')['sha256'],sha)
                self.assertFalse(fresh.execution.source('control.py')['source_changed'])

if __name__=='__main__':unittest.main(verbosity=2)
