"""Flight/coverage/ROI figures from recorded telemetry and actual camera poses."""
from __future__ import annotations
import vision_bootstrap
import argparse,json,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy.spatial.transform import Rotation
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from vision_geometry import load_frames

def xy(row):return (row['longitude']-149.165237)*111319.49079*math.cos(math.radians(-35.363262)),(row['latitude']+35.363262)*111319.49079
def report(run):
    run=Path(run);data=json.loads((run/'flight.json').read_text());rows=data['telemetry'];out=run/'products';out.mkdir(exist_ok=True)
    pts=np.array([xy(r) for r in rows]);alt=np.array([r['altitude_m'] for r in rows]);ts=np.array([r['wall_time']-rows[0]['wall_time'] for r in rows]);armed=np.array([r['armed'] for r in rows])
    expected=10 if data['scenario']=='plane' else 3
    modes=sorted({r['mode'] for r in rows if r['armed']});cmds=[r['command'] for r in data['gcs_command_longs']]
    metrics={'scenario':data['scenario'],'flight_status':data['status'],'armed_modes':modes,'expected_auto_mode':expected,'only_auto_while_armed':modes==[expected],
             'gcs_command_longs':cmds,'flight_setpoints_sent':data['gcs_flight_setpoints_sent'],'force_arm_used':data['force_arm_used'],
             'recorded_seconds':float(ts[-1]),'maximum_altitude_m':float(alt.max()),'final_ground_distance_from_home_m':float(np.linalg.norm(pts[-1])),
             'final_disarmed':not rows[-1]['armed'] or any(e['event']=='auto_landed' for e in data['events'])}
    fig,axs=plt.subplots(1,2,figsize=(12,5),facecolor='#edf3ff')
    for ax in axs:ax.set_facecolor('#edf3ff');ax.grid(alpha=.25)
    axs[0].plot(pts[:,0],pts[:,1],color='#18365d',lw=1.5);axs[0].scatter([0],[0],marker='*',s=100,color='#d79a29',label='Home');axs[0].set(xlabel='East (m)',ylabel='North (m)',title='Recorded AUTO trajectory');axs[0].set_aspect('equal',adjustable='datalim')
    axs[1].plot(ts,alt,color='#238b88',lw=1.5);axs[1].set(xlabel='Wall time (s)',ylabel='Relative altitude (m)',title='Takeoff - task - landing')
    fig.tight_layout();fig.savefig(out/'ucus_izleri.png',dpi=170);plt.close(fig)
    if data['scenario']=='spray':
        ppm=15;bounds=(-38,12,38,74);x0,y0,x1,y1=bounds;shape=(round((x1-x0)*ppm),round((y1-y0)*ppm))
        counts=np.zeros((shape[1],shape[0]),np.uint8);segment=Image.new('L',shape);draw=ImageDraw.Draw(segment);segments=0;last=None;on_seconds=0.;flow=[]
        def pix(p):return round((p[0]-x0)*ppm),round((y1-p[1])*ppm)
        for i,row in enumerate(rows):
            on=row['pump_pwm']>1100 and row['altitude_m']>1
            if on:
                p=tuple(pts[i]);draw.ellipse((pix(p)[0]-4*ppm,pix(p)[1]-4*ppm,pix(p)[0]+4*ppm,pix(p)[1]+4*ppm),fill=1)
                if last is not None:draw.line([pix(last),pix(p)],fill=1,width=8*ppm)
                last=p
                if i:on_seconds+=min(row['wall_time']-rows[i-1]['wall_time'],.5)
            elif last is not None:
                counts+=np.array(segment);segments+=1;segment=Image.new('L',shape);draw=ImageDraw.Draw(segment);last=None
        if last is not None:counts+=np.array(segment);segments+=1
        crop=counts[round((y1-67)*ppm):round((y1-19)*ppm),round((-31-x0)*ppm):round((31-x0)*ppm)]
        palette=np.zeros((*counts.shape,3),np.uint8);palette[counts==0]=[232,238,247];palette[counts==1]=[72,163,130];palette[counts>=2]=[229,174,62]
        im=Image.fromarray(palette);dr=ImageDraw.Draw(im);dr.rectangle([pix((-31,67)),pix((31,19))],outline=(24,54,93),width=3);im.save(out/'ilaclama_kaplama.png')
        metrics.update(pump_on_segments=segments,pump_on_seconds=on_seconds,ideal_working_width_m=8,planned_crop_bounds_enu_m=[-31,19,31,67],
                       crop_covered_fraction=float(np.mean(crop>0)),crop_overlap_fraction=float(np.mean(crop>1)),
                       coverage_note='Ideal 8m geometric swath inferred from real pump PWM and vehicle trajectory; not droplet/chemical deposition measurement.')
        fig,ax=plt.subplots(figsize=(11,3),facecolor='#edf3ff');ax.set_facecolor('#edf3ff');ax.plot(ts,[r['pump_pwm'] for r in rows],color='#238b88');ax.set(xlabel='Wall time (s)',ylabel='Pump PWM (us)',title='ArduPilot sprayer output');ax.grid(alpha=.25);fig.tight_layout();fig.savefig(out/'pompa_pwm.png',dpi=170);plt.close(fig)
    if data['scenario']=='building':
        angles=[]
        for f in load_frames(run):
            p=np.array(f['position']);radius=np.linalg.norm(p[:2]-[0,45])
            if not (p[2]>14 and 20<radius<32):continue
            aim=np.array([0,45,7])-p;aim/=np.linalg.norm(aim);forward=Rotation.from_quat(f['quaternion_xyzw']).as_matrix()[:,0]
            angles.append(float(np.degrees(np.arccos(np.clip(aim@forward,-1,1)))))
        metrics.update(roi_samples=len(angles),roi_median_error_deg=float(np.median(angles)) if angles else None,roi_p95_error_deg=float(np.percentile(angles,95)) if angles else None,
                       gimbal_model='Ideal kinematic servo mount driven by actual ArduPilot mount outputs; no mechanical latency/inertia calibration.')
    (out/'validation.json').write_text(json.dumps(metrics,indent=2))
    print(json.dumps(metrics),flush=True)
    if data['status']!='auto_mission_passed' or modes!=[expected] or data['force_arm_used'] or data['gcs_flight_setpoints_sent']:raise RuntimeError('AUTO flight audit failed')
    if data['scenario']=='spray' and metrics['crop_covered_fraction']<.95:raise RuntimeError('Grid misses crop boundaries: expand/overlap the strips and repeat')
    if data['scenario']=='building' and (not angles or metrics['roi_p95_error_deg']>5):raise RuntimeError('ROI pointing test failed')
    return metrics
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);report(p.parse_args().run)
