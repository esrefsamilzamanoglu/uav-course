"""Synchronous gripper offsets and bounded stationary RGB pickup contracts."""
import json,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from control import Controller
import control


class PairedPickupTests(unittest.TestCase):
    def controller(self):
        c=object.__new__(Controller)
        c.mechanics={'vehicle_pose':{'position_xyz':[-4.268625,-15.281030,1.964523]},
            'grippers':[dict(id='red',position_xyz=[-4.109512,-15.294437,1.360843],swing_deg=.8,attached=False)]}
        c.mechanics_updated_at=time.monotonic()
        c.vehicle=lambda:dict(position_enu=[-4.182632,-14.983517,1.202499],velocity_enu=[0,0,0])
        return c

    def test_real_failure_offsets_use_one_native_snapshot_not_asynchronous_LP(self):
        c=self.controller()
        np.testing.assert_allclose(c.gripper_offset('red')[:2],[.159113,-.013407],atol=1e-8)
        self.assertFalse(c.pickup_ready('red',1.2))
        point=np.array([-4.022382,-14.995716])
        np.testing.assert_allclose(point-c.gripper_offset('red')[:2],[-4.181495,-14.982309],atol=1e-8)
        c.vehicle=lambda:(_ for _ in ()).throw(AssertionError('offset must not read MAVLink position'))
        np.testing.assert_allclose(c.gripper_offset('red')[:2],[.159113,-.013407],atol=1e-8)

    def test_missing_pair_never_falls_back_and_ready_requires_height_swing_pose_freshness(self):
        c=self.controller();body=[-4,0,1.2]
        c.mechanics['vehicle_pose']['position_xyz']=body
        c.mechanics['grippers'][0]['position_xyz']=[-3.84,0,.6]
        c.vehicle=lambda:dict(position_enu=body,velocity_enu=[.03,0,0])
        self.assertTrue(c.pickup_ready('red',1.2))
        c.mechanics['grippers'][0]['swing_deg']=4;self.assertFalse(c.pickup_ready('red',1.2))
        c.mechanics['grippers'][0]['swing_deg']=0;c.mechanics_updated_at=time.monotonic()-2
        self.assertFalse(c.pickup_ready('red',1.2))
        c.mechanics['vehicle_pose']={}
        with self.assertRaises(RuntimeError):c.gripper_offset('red')

    def test_reading_unchanged_JSON_does_not_refresh_mechanics_age(self):
        c=self.controller()
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'bridge').mkdir();p=root/'bridge/state.json'
            c.runtime=types.SimpleNamespace(run=root);c.mechanics={}
            p.write_text(json.dumps({'sim_time':1}),encoding='utf-8')
            with patch.object(control.time,'monotonic',return_value=100):c.read_mechanics()
            self.assertEqual(c.mechanics_updated_at,100)
            with patch.object(control.time,'monotonic',return_value=200):c.read_mechanics()
            self.assertEqual(c.mechanics_updated_at,100)
            p.write_text(json.dumps({'sim_time':2}),encoding='utf-8')
            with patch.object(control.time,'monotonic',return_value=200):c.read_mechanics()
            self.assertEqual(c.mechanics_updated_at,200)

    def test_visual_lock_needs_three_fresh_consistent_frames(self):
        c=self.controller();c.camera=types.SimpleNamespace(pickup_estimate=None,pickup_seen_at=0)
        def wait(condition,*args):
            for i in range(3):
                c.camera.pickup_estimate=[-4+.004*i,-15-.003*i,.1]
                c.camera.pickup_seen_at=time.time()-.4+i*.05
                if condition():return
            raise TimeoutError('fixture observation did not lock')
        c.wait=wait;point,seen=c.visual_pickup_lock([-4,-15,0])
        np.testing.assert_allclose(point,[-3.996,-15.003,.1])
        self.assertLess(time.time()-seen,1.5)
        def stale(condition,*args):
            c.camera.pickup_estimate=[-4,-15,.1];c.camera.pickup_seen_at=time.time()-3
            self.assertFalse(condition());raise TimeoutError('stale')
        c.wait=stale
        with self.assertRaises(TimeoutError):c.visual_pickup_lock([-4,-15,0])
        fixed_seen=time.time()-.2
        def repeated(condition,*args):
            for _ in range(5):
                c.camera.pickup_estimate=[-4,-15,.1];c.camera.pickup_seen_at=fixed_seen
                self.assertFalse(condition(),'One camera frame cannot count three times')
            raise TimeoutError('same frame')
        c.wait=repeated
        with self.assertRaises(TimeoutError):c.visual_pickup_lock([-4,-15,0])
        clock=[100.]
        def aged(condition,*args):
            for i in range(3):
                clock[0]=100.+i
                c.camera.pickup_estimate=[-4,-15,.1];c.camera.pickup_seen_at=clock[0]-.2
                self.assertFalse(condition(),'Old observations must age out before the third arrives')
            raise TimeoutError('old frame in window')
        c.wait=aged
        with patch.object(control.time,'time',side_effect=lambda:clock[0]):
            with self.assertRaises(TimeoutError):c.visual_pickup_lock([-4,-15,0])

    def pickup_fixture(self,first_low_error=0):
        c=self.controller();point=[-4.,-15.,.1];state={'position':[-4,-15,4.],'attached':False}
        goals=[];commands=[];low_count=[0]
        c.camera=types.SimpleNamespace(pickup_color=None,pickup_near=None,pickup_estimate=None,pickup_seen_at=0)
        def paired():
            c.mechanics={'vehicle_pose':{'position_xyz':list(state['position'])},
                'grippers':[dict(id='red',position_xyz=(np.array(state['position'])+[.16,0,-.6]).tolist(),swing_deg=0,attached=state['attached'])]}
            c.mechanics_updated_at=time.monotonic()
        paired()
        c.vehicle=lambda:dict(position_enu=list(state['position']),velocity_enu=[0,0,0])
        def goto(goal,**kwargs):
            state['position']=list(goal)
            if goal[2]==.89:
                low_count[0]+=1
                if low_count[0]==1:state['position'][0]+=first_low_error
            goals.append((list(goal),kwargs));paired()
        def wait(condition,*args):
            for i in range(5):
                c.camera.pickup_estimate=list(point);c.camera.pickup_seen_at=time.time()-.2+i*.01
                if condition():return
            raise TimeoutError('fixture condition failed')
        def servo(channel,pwm):
            end=c.gripper_pair('red')[1]
            self.assertLess(np.linalg.norm(end[:2]-point[:2]),.025)
            commands.append((channel,pwm));state['attached']=True;paired()
        c.goto=goto;c.wait=wait;c.servo=servo
        return c,point,goals,commands,low_count

    def test_final_descent_uses_locked_RGB_and_realigns_without_ground_pose(self):
        c,point,goals,commands,low=self.pickup_fixture(first_low_error=.045)
        c.pickup('red',[-4,-15,0],9)
        self.assertEqual(commands,[(9,1900)])
        self.assertEqual(low[0],2)
        self.assertTrue(all(g[1]['timeout']<=15 for g in goals if g[0][2]==.89))
        self.assertTrue(all(abs(g[0][0]+4.16)<1e-8 and abs(g[0][1]+15)<1e-8 for g in goals[1:]))
        self.assertIsNone(c.camera.pickup_color)
        self.assertNotIn('payloads',c.mechanics)

    def test_expired_final_visual_lock_never_closes_servo(self):
        c,point,goals,commands,low=self.pickup_fixture()
        c.visual_pickup_lock=lambda near:(point,time.time()-15.1)
        with self.assertRaises(TimeoutError):c.pickup('red',[-4,-15,0],9)
        self.assertEqual(commands,[]);self.assertEqual(low[0],0)
        self.assertIsNone(c.camera.pickup_color)


if __name__=='__main__':unittest.main(verbosity=2)
