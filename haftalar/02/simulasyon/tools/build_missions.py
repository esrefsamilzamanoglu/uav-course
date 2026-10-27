"""Create reproducible QGC WPL110 AUTO missions, directly loadable in Mission Planner.

Python plans files on the ground. It sends no position/velocity setpoints.
DO after a row-start waypoint runs on the leg to its next NAV command.
CONDITION_DISTANCE would delay it until near that next waypoint; do not add
that condition to the start/stop commands of these coverage strips.
"""
from __future__ import annotations
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LAT,LON,ALT=-35.363262,149.165237,584
def gps(east,north):return LAT+north/111319.49079327358,LON+east/(111319.49079327358*math.cos(math.radians(LAT)))
class Mission:
    def __init__(self,name):
        self.name=name;self.items=[]
        self.add(16,0,0,ALT,frame=0,label='HOME',global_coords=(LAT,LON))
    def add(self,cmd,east=0,north=0,height=0,p=(0,0,0,0),frame=3,label='',global_coords=None):
        lat,lon=global_coords or gps(east,north)
        if cmd not in (16,19,21,22,31,201):lat=lon=0
        self.items.append({'seq':len(self.items),'frame':frame,'command':cmd,'params':list(p),'latitude':lat,'longitude':lon,'altitude':height,'east':east,'north':north,'label':label})
    def wp(self,e,n,h,label=''):self.add(16,e,n,h,label=label)
    def near(self,meters=2.5):self.add(114,p=(meters,0,0,0),label='CONDITION_DISTANCE')
    def speed(self,mps,plane=False):self.add(178,p=(0 if plane else 1,mps,-1,0),label='DO_CHANGE_SPEED')
    def trigger(self,meters):self.add(206,p=(meters,0,1 if meters else 0,0),label='DO_SET_CAM_TRIGG_DIST')
    def pump(self,on):self.add(218,p=(15,2 if on else 0,0,0),label='SPRAYER_ON' if on else 'SPRAYER_OFF')
    def save(self,description):
        path=ROOT/'missions'/f'{self.name}.waypoints';path.parent.mkdir(exist_ok=True)
        lines=['QGC WPL 110']
        for a in self.items:
            lines.append('\t'.join(map(str,[a['seq'],1 if a['seq']==0 else 0,a['frame'],a['command'],*a['params'],f"{a['latitude']:.9f}",f"{a['longitude']:.9f}",f"{a['altitude']:.3f}",1])))
        path.write_text('\n'.join(lines)+'\n',encoding='ascii')
        path.with_suffix('.json').write_text(json.dumps({'name':self.name,'description':description,'home':[LAT,LON,ALT],'items':self.items},indent=2),encoding='utf-8')
        print(f'{self.name}: {len(self.items)} AUTO items')

def main():
    intro=Mission('00_kamera_tanitimi');intro.add(22,height=8,label='TAKEOFF')
    for pitch in (-90,-45,-20):
        intro.add(205,height=2,p=(pitch,0,0,0),frame=2,label=f'CAMERA_PITCH_{pitch}')
        intro.add(19,height=8,p=(8,0,0,0),label=f'CAMERA_HOLD_{pitch}')
    intro.add(205,height=2,p=(-90,0,0,0),frame=2,label='CAMERA_NADIR');intro.add(21,0,0,0,label='LAND')
    intro.save('AUTO camera introduction: takeoff8m, nadir/45deg/20deg camera holds, land; no guided setpoints.')
    spray=Mission('01_tarla_ilaclama');spray.add(22,height=4,label='TAKEOFF');spray.speed(3)
    for i,x in enumerate(range(-28,29,7)):
        start,end=(17,69) if i%2==0 else (69,17)
        spray.wp(x,start,4,f'ROW_{i+1}_START');spray.pump(True)
        spray.wp(x,end,4,f'ROW_{i+1}_END');spray.pump(False)
    spray.wp(0,8,4,'RETURN');spray.add(21,0,0,0,label='LAND')
    spray.save('9 rows with 7m spacing and 8m working width; 4m altitude; 3m/s; headland extension; onboard DO_AUX_FUNCTION15.')
    mapping=Mission('02_tarla_2d_haritalama');mapping.add(22,height=18,label='TAKEOFF');mapping.speed(4)
    for i,x in enumerate(range(-24,25,8)):
        start,end=(22,64) if i%2==0 else (64,22)
        mapping.wp(x,start,18,f'GRID_{i+1}_START')
        if i==0:mapping.trigger(4)
        mapping.wp(x,end,18,f'GRID_{i+1}_END')
    mapping.trigger(0);mapping.wp(0,8,18,'RETURN');mapping.add(21,0,0,0,label='LAND')
    mapping.save('18 m altitude, 70 deg horizontal FoV, 960x640 sensor; 8 m strips, 4 m camera distance; flat ground mosaic.')
    building=Mission('03_bina_3d_haritalama');building.add(22,height=18,label='TAKEOFF');building.speed(3)
    building.add(201,0,45,7,p=(3,0,0,0),label='DO_SET_ROI_BUILDING')
    for lap,height in enumerate((18,23)):
        for i in range(25):
            angle=-math.pi/2+2*math.pi*i/24
            building.wp(26*math.cos(angle),45+26*math.sin(angle),height,f'ORBIT_{lap+1}_{i:02}')
            if lap==0 and i==0:building.trigger(3)
    building.trigger(0);building.wp(0,8,23,'RETURN');building.add(21,0,0,0,label='LAND')
    building.save('Two AUTO waypoint orbits at 18/23 m; radius26 m; onboard DO_SET_ROI aims the servo gimbal; 3 m trigger.')
    plane=Mission('04_sabit_kanat_gozetim');plane.add(22,0,180,55,p=(15,0,0,0),label='AUTO_TAKEOFF');plane.speed(17,True)
    for e,n,h,label in [(-60,220,55,'SCAN_1_START'),(-60,420,55,'SCAN_1_END'),(0,490,55,'TURN_1'),(0,120,55,'SCAN_2_END'),(60,45,55,'TURN_2'),(60,420,55,'SCAN_3_END'),(200,440,60,'EXIT_SCAN'),(200,-450,60,'DOWNWIND')]:plane.wp(e,n,h,label)
    plane.add(189,label='DO_LAND_START');plane.wp(0,-450,60,'PRE_APPROACH');plane.wp(0,-240,30,'FINAL_APPROACH');plane.add(21,0,0,0,label='AUTO_LAND')
    plane.save('Zephyr fixed wing; mission contains TAKEOFF, three fixed scan legs, DO_LAND_START and LAND; detector never changes route.')
if __name__=='__main__':main()
