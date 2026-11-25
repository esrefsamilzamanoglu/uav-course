"""Spectator bridge contract tests; fixture pixels are not mission evidence."""
import json,sys,tempfile,time,unittest
from pathlib import Path
import cv2
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from follow_camera import FollowCamera

class FollowCameraTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name);self.camera=FollowCamera(self.folder)
    def tearDown(self):self.temp.cleanup()
    def frame(self,mode='chase',age=0,delta=.02):
        cv2.imwrite(str(self.folder/'follow.ppm'),np.full((45,80,3),127,np.uint8))
        meta=dict(frame=7,sim_time=12.5,wall_time=time.time()-age,width=80,height=45,mode=mode,
                  pose_delta_s=delta,native_state=dict(eye_enu=[1,2,3],target_enu=[4,5,6]))
        (self.folder/'follow.json').write_text(json.dumps(meta),encoding='utf-8')
    def test_missing_frame_unavailable(self):self.assertFalse(self.camera.state()['available']);self.assertIsNone(self.camera.jpeg())
    def test_actual_frame_jpeg(self):
        self.frame();s=self.camera.state();self.assertTrue(s['available']);self.assertEqual(s['mode'],'chase')
        self.assertTrue(self.camera.jpeg().startswith(b'\xff\xd8'));self.assertEqual(s['eye_enu'],[1,2,3])
    def test_request_is_not_feedback(self):
        self.frame();s=self.camera.set_mode('top');self.assertEqual(s['mode'],'chase');self.assertTrue(s['pending'])
        self.assertEqual(json.loads((self.folder/'follow-control.json').read_text())['mode'],'top')
        time.sleep(.002);self.frame('top');s=self.camera.state();self.assertEqual(s['mode'],'top');self.assertFalse(s['pending'])
    def test_stale_image_rejected(self):self.frame(age=3);self.assertFalse(self.camera.state()['available']);self.assertIsNone(self.camera.jpeg())
    def test_mismatched_pose_rejected(self):self.frame(delta=.11);self.assertFalse(self.camera.state()['available'])
    def test_unknown_mode_rejected_without_file(self):
        with self.assertRaises(ValueError):self.camera.set_mode('servo')
        self.assertFalse((self.folder/'follow-control.json').exists())
    def test_native_feedback_required(self):self.frame(mode=None);self.assertFalse(self.camera.state()['available'])
    def test_partial_image_pair_rejected(self):
        self.frame();time.sleep(.002);cv2.imwrite(str(self.folder/'follow.ppm'),np.zeros((45,80,3),np.uint8))
        self.assertFalse(self.camera.state()['available'])

if __name__=='__main__':unittest.main()
