"""Moving-camera motion candidates: ORB/RANSAC ego-motion + residual + tracking.

Processes actual RGB files; never connects to MAVLink and never changes a route.
Simulator target positions are used only by a separate evaluation function.
"""
from __future__ import annotations
import vision_bootstrap
import argparse,bisect,json,math,time
from pathlib import Path
import cv2,numpy as np
from vision_geometry import project

class Detector:
    def __init__(self):
        self.orb=cv2.ORB_create(nfeatures=4000,fastThreshold=3,edgeThreshold=12)
        self.match=cv2.BFMatcher(cv2.NORM_HAMMING);self.tracks=[];self.next_id=1
    def process(self,previous,current):
        ga=cv2.cvtColor(previous,cv2.COLOR_BGR2GRAY);gb=cv2.cvtColor(current,cv2.COLOR_BGR2GRAY)
        ka,da=self.orb.detectAndCompute(ga,None);kb,db=self.orb.detectAndCompute(gb,None)
        stats={'keypoints_previous':len(ka),'keypoints_current':len(kb)}
        if da is None or db is None:self.tracks=[];return [],None,{**stats,'skip':'few_features'}
        pairs=self.match.knnMatch(da,db,k=2);good=[p[0] for p in pairs if len(p)==2 and p[0].distance<.74*p[1].distance]
        stats['matches']=len(good)
        if len(good)<25:self.tracks=[];return [],None,{**stats,'skip':'few_matches'}
        a=np.float32([ka[m.queryIdx].pt for m in good]);b=np.float32([kb[m.trainIdx].pt for m in good])
        H,inliers=cv2.findHomography(a,b,cv2.RANSAC,2.5,maxIters=2500,confidence=.995)
        if H is None or np.mean(inliers)<.5:self.tracks=[];return [],None,{**stats,'skip':'unstable_homography'}
        stats['inliers']=int(np.sum(inliers));stats['inlier_fraction']=float(np.mean(inliers))
        h,w=gb.shape;warped=cv2.warpPerspective(previous,H,(w,h));valid=cv2.warpPerspective(np.ones((h,w),np.uint8)*255,H,(w,h))
        valid=cv2.erode(valid,np.ones((11,11),np.uint8));valid[:12]=0;valid[-12:]=0;valid[:,:12]=0;valid[:,-12:]=0
        aa=cv2.GaussianBlur(warped,(3,3),.65).astype(np.int16);bb=cv2.GaussianBlur(current,(3,3),.65).astype(np.int16)
        difference=np.max(np.abs(aa-bb),axis=2).astype(np.uint8)
        values=difference[valid>0]
        if not len(values):return [],None,{**stats,'skip':'no_overlap'}
        median=float(np.median(values));mad=float(np.median(np.abs(values-median)));threshold=max(19,median+6*max(mad,1))
        mask=((difference>threshold)&(valid>0)).astype(np.uint8)*255
        mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        count,_,components,_=cv2.connectedComponentsWithStats(mask)
        candidates=[]
        for x,y,ww,hh,area in components[1:]:
            if 7<=area<=700 and 2<=ww<=60 and 4<=hh<=75 and .10<ww/max(hh,1)<3:
                candidates.append({'bbox':[int(x),int(y),int(ww),int(hh)],'center':np.array([x+ww/2,y+hh/2]),'area':int(area)})
        matched=set();confirmed=[]
        for track in self.tracks:
            pred=cv2.perspectiveTransform(track['center'].reshape(1,1,2).astype(np.float32),H)[0,0]
            options=[(float(np.linalg.norm(c['center']-pred)),i) for i,c in enumerate(candidates) if i not in matched]
            distance,index=min(options,default=(1e9,None))
            if distance<23:
                c=candidates[index];matched.add(index);track.update(center=c['center'],bbox=c['bbox'],hits=track['hits']+1,lost=0)
                track['motion']+=distance
                if track['hits']>=2 and track['motion']>=1.2:confirmed.append(dict(track))
            else:track['center']=pred;track['lost']+=1
        self.tracks=[t for t in self.tracks if t['lost']<3]
        for i,c in enumerate(candidates):
            if i not in matched:
                self.tracks.append({'id':self.next_id,'center':c['center'],'bbox':c['bbox'],'hits':1,'lost':0,'motion':0.});self.next_id+=1
        stats.update(threshold=threshold,residual_candidates=len(candidates),confirmed=len(confirmed))
        return confirmed,mask,stats

def evaluate_bbox(bbox,frame):
    """Evaluation only: model coordinates are not inputs to Detector.process."""
    x,y,w,h=bbox;best=0;bestid=None;truth=[];t=frame['sim_time']
    for i in range(3):
        phase=t*(.8+.1*i)+8*i;east=(-30+35*i)+16*math.sin(phase/16);north=150+70*i+3*math.sin(phase/7)
        uv,depth=project([[east+dx,north+dy,z] for dx in (-.35,.35) for dy in (-.35,.35) for z in (0,1.8)],frame)
        if np.min(depth)<=0:continue
        lo=uv.min(axis=0);hi=uv.max(axis=0);truth.append({'walker':i+1,'bbox':[*lo,*(hi-lo)]})
        ix=max(0,min(x+w,hi[0])-max(x,lo[0]));iy=max(0,min(y+h,hi[1])-max(y,lo[1]));intersection=ix*iy
        iou=intersection/max(w*h+(hi[0]-lo[0])*(hi[1]-lo[1])-intersection,1)
        if iou>best:best=float(iou);bestid=i+1
    return {'best_walker':bestid,'iou':best,'true_positive':best>.06,'truth_boxes':truth}

def run_detector(run,follow=False,output_name='motion'):
    run=Path(run);out=run/'products'/output_name;out.mkdir(parents=True,exist_ok=False);(out/'crops').mkdir(exist_ok=True)
    detector=Detector();previous=None;previous_frame=None;seen=set();events=[];stats=[];last_emit={};idle_since=time.monotonic()
    mission=json.loads((run/'mission.json').read_text())
    scan_sequences={a['seq'] for a in mission['items'] if a['label'].startswith('SCAN_')}
    transit_frames_ignored=0;flight_data={}
    while True:
        live=run/'telemetry.jsonl'
        if live.exists():
            telemetry=[]
            for line in live.read_text().splitlines():
                try:telemetry.append(json.loads(line))
                except json.JSONDecodeError:pass
        else:
            try:flight_data=json.loads((run/'flight.json').read_text())
            except (OSError,json.JSONDecodeError):pass
            telemetry=flight_data.get('telemetry',[])
        if not telemetry:
            if follow:time.sleep(.5);continue
            raise RuntimeError('Read-only mission telemetry is required for the scan-phase gate')
        clocks=[t['wall_time'] for t in telemetry]
        meta=run/'camera.jsonl'
        lines=meta.read_text().splitlines() if meta.exists() else []
        frames=[]
        for line in lines:
            try:frames.append(json.loads(line))
            except json.JSONDecodeError:pass
        progressed=False
        for frame in frames:
            calibration_file=run/'camera_calibration.json'
            if calibration_file.exists():frame['horizontal_fov']=json.loads(calibration_file.read_text())['horizontal_fov']
            name=frame['frame']
            if name in seen:continue
            if follow and frame['wall_time']>clocks[-1]+.4:break
            seen.add(name)
            state=telemetry[max(0,bisect.bisect_right(clocks,frame['wall_time'])-1)]
            if state['seq'] not in scan_sequences or not state['armed']:
                transit_frames_ignored+=1;previous=None;previous_frame=None;detector.tracks=[];continue
            if state['altitude_m']<25:continue
            if previous_frame and frame['sim_time']-previous_frame['sim_time']<.38:continue
            image=cv2.imread(str(run/name))
            if image is None:continue
            progressed=True
            if previous is not None:
                detections,mask,info=detector.process(previous,image);stats.append({'sim_time':frame['sim_time'],**info})
                for det in detections:
                    if frame['sim_time']-last_emit.get(det['id'],-1e6)<2:continue
                    last_emit[det['id']]=frame['sim_time'];x,y,w,h=det['bbox'];pad=9;x0=max(x-pad,0);y0=max(y-pad,0);x1=min(x+w+pad,image.shape[1]);y1=min(y+h+pad,image.shape[0])
                    box=[x0,y0,x1-x0,y1-y0];crop=image[y0:y1,x0:x1];index=len(events)
                    annotated=image.copy();cv2.rectangle(annotated,(x0,y0),(x1,y1),(55,225,110),2)
                    cv2.putText(annotated,f'MOTION CANDIDATE {det["id"]} - AUTO route unchanged',(max(10,x0-20),max(25,y0-10)),cv2.FONT_HERSHEY_SIMPLEX,.5,(55,225,110),1,cv2.LINE_AA)
                    cv2.imwrite(str(out/f'event_{index:04d}.png'),annotated);cv2.imwrite(str(out/'crops'/f'{index:04d}.png'),crop)
                    if mask is not None:cv2.imwrite(str(out/f'residual_{index:04d}.png'),mask)
                    evaluation=evaluate_bbox(box,frame)
                    event={'index':index,'track':det['id'],'sim_time':frame['sim_time'],'source':name,'source_wall_time':frame['wall_time'],'detected_wall_time':time.time(),'source_mission_seq':state['seq'],'source_mavlink_mode':state['mode'],'bbox':box,'hits':det['hits'],'relative_motion_pixels':det['motion'],'evaluation_only':evaluation}
                    events.append(event)
                    with (out/'events.jsonl').open('a') as f:f.write(json.dumps(event)+'\n')
                    print(json.dumps({'motion_event':index,'sim_time':frame['sim_time'],'bbox':box,'evaluation_true_positive':evaluation['true_positive']}),flush=True)
            previous=image;previous_frame=frame
        if progressed:idle_since=time.monotonic()
        flight=run/'flight.json';finished=False
        if flight.exists():
            try:finished=json.loads(flight.read_text()).get('status')!='running'
            except json.JSONDecodeError:pass
        if not follow or (finished and not progressed and time.monotonic()-idle_since>3):break
        if time.monotonic()-idle_since>120 and finished:break
        time.sleep(.5)
    report={'method':'ORB + RANSAC ground homography + compensated residual + temporal persistence','processed_pairs':len(stats),'events':len(events),
            'true_positive_events_against_independent_simulator_truth':sum(e['evaluation_only']['true_positive'] for e in events),
            'flight_commands_sent':0,'uses_ground_truth_for_detection':False,'uses_ground_truth_for_evaluation':True,
            'uses_simulator_target_positions_for_detection':False,'analysis_state_source':'read-only autopilot mission index and altitude',
            'active_auto_mission_sequences':sorted(scan_sequences),'transit_frames_ignored':transit_frames_ignored,
            'limitations':'Motion candidates, not a human classifier. Parallax, shadows and poorly estimated homographies can cause false positives.'}
    (out/'metrics.json').write_text(json.dumps(report,indent=2));(out/'processing.json').write_text(json.dumps(stats,indent=2))
    print(json.dumps(report),flush=True)
    if not events or report['true_positive_events_against_independent_simulator_truth']<1:raise RuntimeError('No verified moving-person detection; revise detector/scene before using in lesson')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('--follow',action='store_true');p.add_argument('--output-name',default='motion');a=p.parse_args();run_detector(a.run,a.follow,a.output_name)
