"""Independent geometry/freshness/actuator tests; no simulator ports are opened."""
from __future__ import annotations
import copy,json,math,os,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
import vision
from control import Controller

def meta(**extra):
    d=dict(frame=1,sim_time=1.,wall_time=time.time(),width=960,height=720,
           position_xyz=[0.,0.,12.],quaternion_xyzw=[-.5,.5,.5,.5],pose_delta_s=.003)
    d.update(extra);return d

def fixture():
    """Known analytic pinhole target fixture, not Gazebo execution evidence."""
    im=np.full((720,960,3),(70,90,75),np.uint8);f=960/(2*math.tan(math.radians(35)))
    for center,sides,side,color in [((2.,1.),6,2.,(225,42,25)),((-3.,-2.),3,1.,(25,40,225))]:
        radius=side/(2*math.sin(math.pi/sides));angle=np.arange(sides)*2*math.pi/sides
        world=np.array(center)+radius*np.column_stack((np.cos(angle),np.sin(angle)))
        pts=np.column_stack((480+world[:,0]*f/12,360-world[:,1]*f/12))
        cv2.fillPoly(im,[np.round(pts).astype(np.int32)],color)
    return im

class ProjectionTests(unittest.TestCase):
    def test_nadir_centre_and_pixel_axis_scale(self):
        m=meta(position_xyz=[12.,-8.,10.]);f=960/(2*math.tan(math.radians(35)))
        np.testing.assert_allclose(vision.project(480,360,m),[12,-8,0],atol=1e-9)
        np.testing.assert_allclose(vision.project(580,360,m),[12+1000/f,-8,0],atol=1e-9)
        np.testing.assert_allclose(vision.project(480,460,m),[12,-8-1000/f,0],atol=1e-9)
    def test_camera_tilt_moves_centre_ray(self):
        a=math.pi/2+.2;m=meta(position_xyz=[12,-8,10],quaternion_xyzw=[0,math.sin(a/2),0,math.cos(a/2)])
        np.testing.assert_allclose(vision.project(480,360,m),[12-10*math.tan(.2),-8,0],atol=1e-9)
    def test_horizon_upward_and_zero_quaternion(self):
        self.assertIsNone(vision.project(480,360,meta(quaternion_xyzw=[0,0,0,1])))
        self.assertIsNone(vision.project(480,360,meta(quaternion_xyzw=[0,-math.sqrt(.5),0,math.sqrt(.5)])))
        with self.assertRaises(ValueError):vision.project(480,360,meta(quaternion_xyzw=[0,0,0,0]))
    def test_scaled_quaternion_does_not_change_projection(self):
        np.testing.assert_allclose(vision.project(570,430,meta()),vision.project(570,430,meta(quaternion_xyzw=[-5,5,5,5])),atol=1e-9)
    def test_pixels_recover_two_unknown_target_centres(self):
        detections={d['kind']:d for d in vision.detect(fixture(),meta())}
        self.assertEqual(set(detections),{'blue_hexagon','red_triangle'})
        np.testing.assert_allclose(detections['blue_hexagon']['position_enu'][:2],[2,1],atol=.04)
        np.testing.assert_allclose(detections['red_triangle']['position_enu'][:2],[-3,-2],atol=.04)

class FreshnessTests(unittest.TestCase):
    def camera(self,directory,m):
        p=Path(directory);cv2.imwrite(str(p/'latest.ppm'),fixture())
        (p/'camera.json').write_text(json.dumps(m),encoding='utf-8')
        c=vision.Camera(p);c.perception_enabled=True;return c
    def update(self,c):
        try:c.update()
        except ValueError:pass  # rejecting invalid calibration is also acceptable
    def test_pose_image_mismatch_over_100ms_is_not_used_for_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.camera(d,meta(pose_delta_s=.2));self.update(c)
            self.assertEqual(c.detections,[],'Image/pose mismatch >100ms reached detector/navigation')
    def test_stale_frame_is_not_used_for_navigation(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.camera(d,meta(wall_time=time.time()-5));self.update(c)
            self.assertEqual(c.detections,[],'Five-second-old frame reached navigation')
    def test_dimension_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.camera(d,meta(width=1280,height=800));self.update(c)
            self.assertEqual(c.detections,[],'Wrong camera calibration dimensions reached navigation')
    def test_old_metadata_cannot_be_paired_with_new_atomic_image(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.camera(d,meta());p=Path(d)
            stamp=time.time();os.utime(p/'camera.json',(stamp-1,stamp-1));os.utime(p/'latest.ppm',(stamp,stamp))
            self.update(c);self.assertEqual(c.detections,[],'Metadata was older than the separately committed RGB frame')
    def test_display_age_increases_after_stream_stops(self):
        with tempfile.TemporaryDirectory() as d:
            now=time.time();c=self.camera(d,meta(wall_time=now));self.update(c)
            with patch.object(vision.time,'time',return_value=now+5):state,_=c.state()
            self.assertGreater(state.get('age_s') or 0,4.5,'Camera age froze at the last update')

class ActuatorTests(unittest.TestCase):
    def test_only_supported_servo_channels_and_pwm_are_accepted(self):
        c=object.__new__(Controller);sent=[];c.command=lambda *a,**k:sent.append(a);c.event=lambda *a:None
        for channel,pwm in [(9,1100),(10,1900)]:c.servo(channel,pwm)
        self.assertEqual(sent,[(183,9,1100),(183,10,1900)])
        for channel,pwm in [(1,1900),(8,1100),(11,1900),(9,1500),(10,0)]:
            with self.assertRaises(ValueError):c.servo(channel,pwm)
    def test_low_approach_does_not_accept_35cm_height_error(self):
        c=object.__new__(Controller);c.mission={};c.home=np.array([0,0,.9]);c.cancel=threading.Event();c.pause=threading.Event();c.connected=True;c.command_count=0
        c.send=lambda *a:None
        c.vehicle=lambda:dict(position_enu=[0,0,1.1],velocity_enu=[0,0,0])
        with self.assertRaises(TimeoutError):c.goto([0,0,.75],radius=.09,timeout=.02)

if __name__=='__main__':
    stream=__import__('io').StringIO();suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    output=Path(__file__).resolve().parent/'backend-contract-tests.txt';output.write_text(stream.getvalue(),encoding='utf-8')
    report=dict(tests=result.testsRun,passed=result.wasSuccessful(),failures=[str(t) for t,_ in result.failures],errors=[str(t) for t,_ in result.errors],
                scope='Generated pinhole fixtures, file freshness and local controller contracts; no live command was sent')
    output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(stream.getvalue());print(json.dumps(report))
    raise SystemExit(not result.wasSuccessful())
