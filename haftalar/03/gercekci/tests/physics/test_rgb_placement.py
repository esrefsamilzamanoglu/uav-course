"""Independent geometry, actual image contours and gentle-release contracts."""
import json,math,sys,threading,time,types,unittest
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
import vision,control
from vision import select_drop_point,Camera
from control import Controller
from execution_trace import ExecutionTracer
from test_backend_contract import fixture,meta

def triangle(center=(0,0),angle=0):
    angles=np.arange(3)*2*np.pi/3+angle
    return np.array(center)+np.column_stack((np.cos(angles),np.sin(angles)))/math.sqrt(3)

def inside_margin(point,polygon):
    return cv2.pointPolygonTest(np.asarray(polygon,np.float32).reshape((-1,1,2)),tuple(map(float,point[:2])),True)

class RGBPlacementTests(unittest.TestCase):
    def test_reserved_then_free_points_fit_translated_rotated_triangle_both_windings(self):
        for angle in (0,.371,1.2):
            for reverse in (False,True):
                center=[13.5,-21.75,0.];polygon=triangle(center[:2],angle)
                if reverse:polygon=polygon[::-1]
                first=select_drop_point(center,polygon,margin=.18,reserve=True)
                second=select_drop_point(center,polygon,occupied=first,margin=.17,separation=.28)
                self.assertGreaterEqual(inside_margin(first,polygon),.1799)
                self.assertGreaterEqual(inside_margin(second,polygon),.1699)
                self.assertGreaterEqual(np.linalg.norm(np.array(first[:2])-second[:2]),.28)
                self.assertGreater(np.linalg.norm(np.array(first[:2])-center[:2]),.17)
                self.assertEqual(center,[13.5,-21.75,0.])
    def test_center_occupied_triangle_and_too_small_polygon_have_no_safe_fallback(self):
        with self.assertRaises(ValueError):select_drop_point([0,0,0],triangle(),occupied=[0,0,.1])
        with self.assertRaises(ValueError):select_drop_point([0,0,0],triangle()*.2)
        with self.assertRaises(ValueError):select_drop_point([0,0,0],[[0,0],[1,0],[0,0]])
    def test_large_hexagon_placement_uses_free_interior(self):
        angles=np.arange(6)*np.pi/3;polygon=np.column_stack((2*np.cos(angles),2*np.sin(angles)))+[125,-73]
        point=select_drop_point([125,-73,0],polygon,occupied=[125,-73,.1])
        self.assertGreaterEqual(inside_margin(point,polygon),.17)
        self.assertGreaterEqual(math.dist(point[:2],[125,-73]),.28)
        self.assertLess(math.dist(point[:2],[125,-73]),.4)
    def test_actual_pixels_produce_polygon_and_existing_load_then_free_placement(self):
        image=fixture();m=meta();f=960/(2*math.tan(math.radians(35)))
        # Independent blue .16m cube footprint on the red triangle. Ground truth
        # is used only to render this test image; planner receives pixels/pose.
        center=np.array([-2.80,-2.]);world=center+np.array([[-.08,-.08],[.08,-.08],[.08,.08],[-.08,.08]])
        pixels=np.column_stack((480+world[:,0]*f/12,360-world[:,1]*f/12)).round().astype(np.int32)
        cv2.fillPoly(image,[pixels],(225,42,25))
        targets={d['kind']:d for d in vision.detect(image,m)}
        self.assertIn('red_triangle',targets)
        polygon=targets['red_triangle']['polygon_enu']
        self.assertEqual(len(polygon),3)
        existing=vision.detect(image,m,payload_color='blue',near=[-3,-2,0])
        self.assertEqual(len(existing),1)
        np.testing.assert_allclose(existing[0]['position_enu'][:2],center,atol=.04)
        point=select_drop_point(targets['red_triangle']['position_enu'],polygon,occupied=existing[0]['position_enu'])
        self.assertGreaterEqual(inside_margin(point,np.asarray(polygon)[:,:2]),.17-1e-5)
        self.assertGreaterEqual(math.dist(point[:2],existing[0]['position_enu'][:2]),.28)
    def test_camera_polygon_is_copy_and_expires_with_actual_frame_time(self):
        camera=Camera('unused');m=meta();image=fixture()
        with patch.object(vision,'read_frame',return_value=(m,image,1)):camera.update()
        polygon=camera.target_polygon('red_triangle');self.assertIsNotNone(polygon)
        polygon[0][0]=999
        self.assertNotEqual(camera.target_polygon('red_triangle')[0][0],999)
        with patch.object(vision.time,'time',return_value=m['wall_time']+2.1):
            self.assertIsNone(camera.target_polygon('red_triangle'))
    def release_fixture(self):
        c=object.__new__(Controller);c.mission={'id':'G3'};c.delivery_log=[]
        c.camera=types.SimpleNamespace(pickup_color=None,pickup_near=None,pickup_estimate=None,pickup_seen_at=0)
        center=[10.,-7.,0.];polygon=triangle(center[:2]);c.camera.target_polygon=lambda *args,**kwargs:polygon.tolist()
        state={'position':[10,-7,4.],'attached':True,'swing':2.,'velocity':[.03,0,0]};goals=[];conditions=[]
        c.vehicle=lambda:{'position_enu':state['position']}
        c.grips=lambda:{'red':dict(payload='carried',attached=state['attached'],swing_deg=state['swing'],position_xyz=(np.array(state['position'])+np.array([.16,0,-.6])).tolist())}
        c.mechanics={'payloads':[{'id':'carried','velocity_xyz':state['velocity']}]}
        def paired():
            c.mechanics['vehicle_pose']={'position_xyz':list(state['position'])}
            c.mechanics['grippers']=[dict(id='red',position_xyz=(np.array(state['position'])+np.array([.16,0,-.6])).tolist())]
        paired()
        def goto(goal,**kwargs):state['position']=list(goal);goals.append((list(goal),kwargs));paired()
        def wait(condition,timeout,description):
            if description.startswith('Güncel RGB'):
                c.camera.pickup_estimate=[10.21,-7,.1];c.camera.pickup_seen_at=time.time()
            if description.startswith('Yük salınımı'):conditions.append(condition)
            self.assertTrue(condition(),description)
        c.goto=goto;c.wait=wait;c.phase=lambda *args:None;c.event=lambda *args:None
        c.servo=lambda channel,pwm:state.update(attached=False)
        return c,center,state,goals,conditions
    def test_release_uses_original_identity_rgb_occupancy_and_low_strict_settle(self):
        c,center,state,goals,conditions=self.release_fixture()
        with patch.object(control.time,'sleep'):c.release('red',center,kind='red_triangle',occupied='rgb')
        record=c.delivery_log[0]
        self.assertEqual(record['target'],center);self.assertEqual(record['kind'],'red_triangle')
        self.assertGreaterEqual(math.dist(record['drop_point'][:2],record['occupied_rgb'][:2]),.28)
        self.assertIsNone(c.camera.pickup_color)
        self.assertTrue(all(abs(goal[2]-1.25)<1e-9 and options['radius']==.02 for goal,options in goals[1:]))
        self.assertEqual(len(goals[1:]),3)
        self.assertTrue(conditions[0]())
        state['velocity'][0]=.05;self.assertFalse(conditions[0]())
        state['velocity'][0]=.03;state['swing']=3.1;self.assertFalse(conditions[0]())
    def test_g2_without_reservation_keeps_original_center(self):
        c,center,state,goals,conditions=self.release_fixture();c.mission['id']='G2'
        c.camera.target_polygon=lambda *args,**kwargs:(_ for _ in ()).throw(AssertionError('G2 needs no polygon plan'))
        with patch.object(control.time,'sleep'):c.release('red',center,kind='blue_hexagon')
        self.assertEqual(c.delivery_log[0]['drop_point'],center)
        self.assertIsNone(c.delivery_log[0]['occupied_rgb'])
        np.testing.assert_allclose(goals[-1][0],[center[0]-.16,center[1],1.25])

    def test_truth_coordinate_argument_is_rejected_before_servo(self):
        c,center,state,goals,conditions=self.release_fixture();commands=[]
        c.servo=lambda *args:commands.append(args)
        with self.assertRaises(ValueError):c.release('red',center,kind='red_triangle',occupied=[10,-7,.1])
        self.assertEqual(commands,[])
        self.assertEqual(c.delivery_log,[])

    def test_no_room_aborts_before_servo_and_clears_perception_request(self):
        c,center,state,goals,conditions=self.release_fixture();commands=[]
        c.servo=lambda *args:commands.append(args)
        def wait(condition,*args):
            c.camera.pickup_estimate=list(center);c.camera.pickup_seen_at=time.time()
            self.assertTrue(condition())
        c.wait=wait
        with self.assertRaises(ValueError):c.release('red',center,kind='red_triangle',occupied='rgb')
        self.assertEqual(commands,[]);self.assertEqual(c.delivery_log,[])
        self.assertEqual(len(goals),1);self.assertEqual(goals[0][0][2],4)
        self.assertIsNone(c.camera.pickup_color)

    def test_new_helper_is_exposed_by_actual_source_catalog(self):
        source=ExecutionTracer(ROOT/'backend').source('vision.py')
        helper=next(fn for fn in source['functions'] if fn['name']=='select_drop_point')
        self.assertIn('RGB',helper['explanation'])
        self.assertIn('select_drop_point',source['lines'][helper['line']-1])

    def test_g3_preserves_target_identity_and_reserves_only_initial_triangle(self):
        for order in (('blue_hexagon','red_triangle'),('red_triangle','blue_hexagon')):
            c=object.__new__(Controller);c.home=np.array([-24.,0.,.9]);c.mission={'id':'G3','steps':[{} for _ in range(6)]}
            centers={'blue_hexagon':[-4,-15,0],'red_triangle':[6,20,0]}
            c.camera=types.SimpleNamespace(estimates={k:centers[k] for k in order},pickup_color=None)
            c.runtime=types.SimpleNamespace(run=None);c.delivery_log=[];records=[];position=[0,0,4]
            c.vehicle=lambda:{'armed':True,'position_enu':position};c.phase=lambda *args:None
            c.servo=lambda *args:None;c.takeoff=lambda *args:None;c.mode=lambda *args:None;c.event=lambda *args:None
            def goto(goal,**kwargs):position[:]=list(goal)
            c.goto=goto
            def wait(*args,**kwargs):
                c.camera.pickup_estimate=list(centers[order[0]]);c.camera.pickup_seen_at=time.time()
            c.wait=wait
            c.grips=lambda:{color:dict(attached=True,position_xyz=position) for color in ('red','blue')}
            def release(color,target,**kwargs):
                records.append(dict(color=color,target=list(target),**kwargs))
                c.delivery_log.append(dict(color=color,target=list(target),kind=kwargs['kind'],drop_point=[target[0]+.2,*target[1:]],channel=9 if color=='red' else 10))
            c.pickup=lambda *args,**kwargs:None
            c.release=release;c.cancel=threading.Event();c.connected=True
            with patch.object(control.time,'sleep'):c.run_mission('G3')
            self.assertEqual(c.mission['status'],'completed')
            self.assertEqual(len(records),3)
            self.assertEqual([r['reserve'] for r in records[:2]],[k=='red_triangle' for k in order])
            self.assertEqual(records[-1]['kind'],order[1]);self.assertEqual(records[-1]['occupied'],'rgb')
            self.assertEqual(records[-1]['target'],centers[order[1]])

if __name__=='__main__':unittest.main(verbosity=2)
