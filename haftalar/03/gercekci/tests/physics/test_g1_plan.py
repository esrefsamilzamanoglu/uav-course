"""Route regression: G1 returns from P2, while G2 keeps its P1 outside return."""
import sys,threading,types,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'backend'))
from control import Controller
from flight_geometry import winding,lobes

class G1PlanTests(unittest.TestCase):
    def run_plan(self,mission):
        c=object.__new__(Controller);c.home=np.array([-24.,0.,.9]);c.mission={'steps':[{} for _ in range(6)]}
        c.camera=types.SimpleNamespace(estimates={'blue_hexagon':[-4,-15,0],'red_triangle':[6,20,0]},pickup_color=None)
        c.runtime=types.SimpleNamespace(run=None);c.delivery_log=[];points=[];options=[]
        c.vehicle=lambda:{'armed':True};c.phase=lambda *a:None;c.servo=lambda *a:None;c.takeoff=lambda *a:None
        def goto(goal,**kw):points.append(list(goal));options.append(kw)
        c.goto=goto;c.mode=lambda *a:None;c.wait=lambda *a,**kw:None;c.event=lambda *a:None
        c.release=lambda color,target,**kwargs:c.delivery_log.append(dict(color=color,target=target))
        c.cancel=threading.Event();c.connected=True;c.run_mission(mission)
        self.assertEqual(c.mission['status'],'completed');self.options=options;return points
    def test_g1_returns_directly_after_p2_outer_exit(self):
        p=self.run_plan('G1')
        np.testing.assert_allclose(p[-2],[-40,-110,12.9]);np.testing.assert_allclose(p[-1],[-24,0,12.9])
        self.assertFalse(any(abs(x[0]+24)<1e-8 and abs(x[1]-105)<1e-8 for x in p))
        self.assertEqual(len(p[2:-2]),73)
        self.assertTrue(all(o.get('radius')==8 and o.get('settle') is False for o in self.options[2:-2]))
        for pole in [(0,75),(0,-75)]:
            self.assertGreaterEqual(min(np.linalg.norm(np.array(q[:2])-pole) for q in p[2:-2]),25-1e-8)
    def test_g2_retains_p1_outside_return(self):
        p=self.run_plan('G2');np.testing.assert_allclose(p[-2],[-24,105,12.9]);np.testing.assert_allclose(p[-1],[-24,0,12.9])
        self.assertFalse(any(o.get('radius')==8 for o in self.options))
    def test_grouped_circles_cannot_replace_two_alternating_eights(self):
        a=np.linspace(0,4*np.pi,200)
        grouped=np.vstack((np.column_stack((20*np.cos(a),-75+20*np.sin(a))),np.column_stack((20*np.cos(-a),75+20*np.sin(-a)))))
        self.assertNotEqual(lobes(grouped),[-1,1,-1,1,-1])
        theta=np.linspace(-np.pi/2,7*np.pi/2,300)
        eight=np.column_stack((38*np.sin(2*theta),100*np.sin(theta)))
        self.assertEqual(lobes(eight),[-1,1,-1,1,-1]);self.assertAlmostEqual(abs(winding(eight,(0,75))),2,places=6)

if __name__=='__main__':unittest.main(verbosity=2)
