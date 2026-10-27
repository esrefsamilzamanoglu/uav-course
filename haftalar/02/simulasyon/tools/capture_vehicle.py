"""Render a close observer view of the real Iris model; never arm the vehicle."""
from __future__ import annotations
import json,math,time,xml.etree.ElementTree as E
from runtime import Session,LOCAL
from fly_auto import GCS
def main():
    tree=E.parse(LOCAL/'worlds/farm.sdf');pose=tree.getroot().find("./world/model[@name='overview']/pose")
    pos=(1.65,-2.3,1.5);target=(0,0,.2);dx,dy,dz=[b-a for a,b in zip(pos,target)]
    pose.text=' '.join(map(str,(*pos,0,math.atan2(-dz,math.hypot(dx,dy)),math.atan2(dy,dx))))
    tree.write(LOCAL/'worlds/vehicle.sdf',encoding='utf-8',xml_declaration=True)
    s=Session('intro');s.world='vehicle';g=GCS(s)
    try:
        s.start();g.connect();g.until(lambda:False,12,strict=False)
        if any(t['armed'] for t in g.telemetry):raise RuntimeError('Unexpected armed state in read-only vehicle capture')
        g.status='disarmed_vehicle_capture_passed';g.event('capture_complete',run=str(s.run),camera='overview',flight_commands_sent=0)
    finally:g.close();s.close()
if __name__=='__main__':main()
