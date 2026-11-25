"""Perception from actual Gazebo camera frames and time-matched camera pose.

No target or payload scene positions enter this module. Gazebo camera coordinates
are X forward, Y left, Z up. The calibrated pinhole ray is (1,-du/f,-dv/f).
"""
from __future__ import annotations
import json,math,threading,time
from pathlib import Path
import cv2
import numpy as np

def rotation(q):
    x,y,z,w=np.asarray(q,float);n=x*x+y*y+z*z+w*w
    if n<1e-12:raise ValueError('Invalid camera quaternion')
    x,y,z,w=np.array([x,y,z,w])/math.sqrt(n)
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def project(u,v,meta,ground=0.):
    width=meta.get('width',960);height=meta.get('height',720)
    f=width/(2*math.tan(float(meta.get('hfov',math.radians(70)))/2))
    p=np.asarray(meta.get('position_xyz',meta.get('position',meta.get('position_enu'))),float)
    q=meta.get('quaternion_xyzw',meta.get('quaternion'))
    ray=rotation(q)@np.array([1.,-(u-width/2)/f,-(v-height/2)/f])
    if ray[2]>=-.01:return None
    t=(ground-p[2])/ray[2]
    if t<0:return None
    return (p+t*ray).tolist()

def masks(image):
    hsv=cv2.cvtColor(image,cv2.COLOR_BGR2HSV)
    return {'blue':cv2.inRange(hsv,(90,90,40),(137,255,255)),
            'red':cv2.inRange(hsv,(0,105,45),(13,255,255))|cv2.inRange(hsv,(167,105,45),(179,255,255))}

def detect(image,meta,payload_color=None,near=None):
    answer=[];h,w=image.shape[:2]
    for color,mask in masks(image).items():
        for c in cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)[0]:
            area=cv2.contourArea(c)
            if area<25:continue
            x,y,bw,bh=cv2.boundingRect(c)
            if x<2 or y<2 or x+bw>=w-2 or y+bh>=h-2:continue
            approx=cv2.approxPolyDP(c,.035*cv2.arcLength(c,True),True)
            m=cv2.moments(c)
            if not m['m00']:continue
            u,v=m['m10']/m['m00'],m['m01']/m['m00']
            pos=project(u,v,meta,ground=.1 if payload_color else 0.)
            if pos is None:continue
            corners=[project(float(p[0][0]),float(p[0][1]),meta) for p in approx]
            valid=[p for p in corners if p is not None]
            if len(valid)<3:continue
            span=max(np.linalg.norm(np.array(a[:2])-np.array(b[:2])) for a in valid for b in valid)
            if payload_color:
                if color!=payload_color or not (.07<span<.65):continue
                if near is not None and np.linalg.norm(np.array(pos[:2])-np.array(near[:2]))>3:continue
                kind=color+'_payload'
            else:
                if not cv2.isContourConvex(approx):continue
                if color=='blue' and len(approx)==6 and 2.5<span<5.5:kind='blue_hexagon'
                elif color=='red' and len(approx)==3 and .65<span<1.5:kind='red_triangle'
                else:continue
            # A geometric consistency measure, not a learned model probability.
            confidence=min(.99,.65+.3*min(1,area/800))
            answer.append(dict(kind=kind,color=color,confidence=round(confidence,3),bbox=[x,y,bw,bh],
                               center_px=[u,v],position_enu=pos,area_px=area,vertices=len(approx),span_m=span,
                               polygon_enu=[list(p) for p in valid],
                               source='Gazebo RGB + calibrated ray-plane intersection'))
    return answer

def select_drop_point(center, polygon, occupied=None, *, margin=.17, separation=.28, reserve=False, step=.02):
    """RGB hedef çokgeninde kenarlardan ve görülen yükten uzak bırakma noktası seçer.

    Edge clearance protects the whole cube footprint. Reserved first placement
    uses an inset corner; later placement maximizes edge margin away from the
    observed existing load. No scene or Gazebo payload position is consulted.
    """
    center=np.asarray(center,float);vertices=np.asarray(polygon,float)
    if center.ndim!=1 or center.size<2 or vertices.ndim!=2 or vertices.shape[0]<3 or vertices.shape[1]<2:
        raise ValueError('Geçersiz RGB hedef çokgeni')
    vertices=vertices[:,:2]
    if not np.isfinite(vertices).all() or not np.isfinite(center).all() or not np.isfinite([margin,separation,step]).all() or margin<=0 or separation<=0 or step<=0:
        raise ValueError('Geçersiz bırakma geometrisi')
    edges=np.roll(vertices,-1,axis=0)-vertices;length=np.linalg.norm(edges,axis=1)
    if np.any(length<1e-6):raise ValueError('RGB hedef çokgeni dejenere')
    cross=edges[:,0]*np.roll(edges,-1,axis=0)[:,1]-edges[:,1]*np.roll(edges,-1,axis=0)[:,0]
    signed_area=np.sum(vertices[:,0]*np.roll(vertices,-1,axis=0)[:,1]-vertices[:,1]*np.roll(vertices,-1,axis=0)[:,0])
    orientation=1. if signed_area>0 else -1.
    if abs(signed_area)<1e-6 or np.any(orientation*cross<-1e-8):raise ValueError('RGB hedef çokgeni dışbükey olmalı')
    low=vertices.min(axis=0);high=vertices.max(axis=0)
    # Keep tracing/CPU work bounded even if a badly scaled polygon arrives.
    resolution=max(float(step),math.sqrt(float(np.prod(high-low))/80000))
    gx,gy=np.meshgrid(np.arange(low[0],high[0]+resolution*.5,resolution),np.arange(low[1],high[1]+resolution*.5,resolution))
    points=np.vstack((np.column_stack((gx.ravel(),gy.ravel())),center[:2],vertices.mean(axis=0)))
    delta=points[:,None,:]-vertices[None,:,:]
    distances=orientation*(edges[None,:,0]*delta[:,:,1]-edges[None,:,1]*delta[:,:,0])/length[None,:]
    clearance=distances.min(axis=1);valid=clearance>=float(margin)
    if occupied is not None:
        blocked=np.asarray(occupied,float)
        if blocked.ndim!=1 or blocked.size<2 or not np.isfinite(blocked).all():raise ValueError('Geçersiz RGB doluluk konumu')
        valid &= np.linalg.norm(points-blocked[:2],axis=1)>=float(separation)
    choices=np.flatnonzero(valid)
    if not len(choices):raise ValueError('RGB hedef çokgeninde güvenli boş bırakma alanı yok')
    squared=np.sum((points[choices]-center[:2])**2,axis=1)
    score=squared if reserve else clearance[choices]-1e-6*squared
    result=points[choices[int(np.argmax(score))]]
    return [float(result[0]),float(result[1]),float(center[2]) if center.size>2 else 0.]

def read_frame(directory,max_age=2.,max_pose_delta=.1):
    """Read an atomically committed image/metadata pair, rejecting stale poses."""
    directory=Path(directory);frame=directory/'latest.ppm';mp=directory/'camera.json'
    fs0,ms0=frame.stat(),mp.stat()
    if ms0.st_mtime_ns<fs0.st_mtime_ns:return None
    meta=json.loads(mp.read_text(encoding='utf-8'));image=cv2.imread(str(frame))
    fs1,ms1=frame.stat(),mp.stat()
    if fs0.st_mtime_ns!=fs1.st_mtime_ns or ms0.st_mtime_ns!=ms1.st_mtime_ns:return None
    if image is None or image.shape[:2]!=(meta.get('height'),meta.get('width')):return None
    if time.time()-meta.get('wall_time',0)>max_age or meta.get('pose_delta_s',999)>max_pose_delta:return None
    if 'position_xyz' not in meta or 'quaternion_xyzw' not in meta:return None
    return meta,image,fs1.st_mtime_ns

class Camera:
    def __init__(self,bridge_dir,hfov=math.radians(70)):
        self.directory=Path(bridge_dir);self.lock=threading.Lock();self.last_mtime=0
        self.frame_id=0;self.image=None;self.meta={};self.detections=[];self.observations={};self.estimates={}
        self.jpeg=None;self.age_s=None;self.running=False;self.stop_event=threading.Event()
        self.perception_enabled=True;self.pickup_color=None;self.pickup_near=None;self.pickup_estimate=None;self.pickup_seen_at=0
        self.hfov=hfov
        self.track_times={};self.track_confidence={};self.target_polygons={};self.polygon_times={}
    def start(self):
        self.running=True;self.stop_event.clear();threading.Thread(target=self.loop,daemon=True,name='GazeboRGB').start()
    def close(self):self.stop_event.set();self.running=False
    def loop(self):
        while not self.stop_event.wait(.12):
            try:self.update()
            except (OSError,ValueError,KeyError,IndexError,json.JSONDecodeError,cv2.error):continue
    def update(self):
        pair=read_frame(self.directory)
        if pair is None:return
        meta,image,mtime=pair
        if mtime==self.last_mtime:return
        meta.setdefault('width',image.shape[1]);meta.setdefault('height',image.shape[0])
        meta['hfov']=self.hfov
        detections=detect(image,meta) if self.perception_enabled else []
        pickup=detect(image,meta,self.pickup_color,self.pickup_near) if self.pickup_color else []
        if pickup:self.pickup_estimate=pickup[0]['position_enu'];self.pickup_seen_at=meta['wall_time']
        with self.lock:
            self.frame_id+=1;self.last_mtime=mtime;self.image=image;self.meta=meta;self.detections=detections+pickup
            for d in detections:
                self.track_times[d['kind']]=meta['wall_time'];self.track_confidence[d['kind']]=d['confidence']
                self.target_polygons[d['kind']]=[list(p) for p in d['polygon_enu']];self.polygon_times[d['kind']]=meta['wall_time']
                bucket=self.observations.setdefault(d['kind'],[])
                bucket.append(d['position_enu']);del bucket[:-25]
                if len(bucket)>=3:self.estimates[d['kind']]=np.median(bucket,axis=0).tolist()
            ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,88]);self.jpeg=jpeg.tobytes() if ok else None
            self.age_s=max(0,time.time()-meta['wall_time'])
    def state(self):
        with self.lock:
            age=max(0,time.time()-self.meta['wall_time']) if self.meta.get('wall_time') else None
            fresh=age is not None and age<=2
            return dict(available=self.jpeg is not None and fresh,frame_id=self.frame_id,width=self.meta.get('width',960),
                        height=self.meta.get('height',720),age_s=age,source='Gazebo · RGB',
                        confidence_description='Renk/şekil tutarlılığı; model olasılığı değildir'),list(self.detections) if fresh else []
    def target_polygon(self,kind,max_age=2.):
        """Araç RGB'sinden izdüşürülen güncel hedef çevresinin kopyasını döndürür."""
        with self.lock:
            stamp=self.polygon_times.get(kind)
            polygon=self.target_polygons.get(kind)
            if stamp is None or time.time()-stamp>max_age or polygon is None:return None
            return [list(p) for p in polygon]
    def confirmed(self):
        with self.lock:
            return [dict(kind=k,color='blue' if k.startswith('blue') else 'red',position_enu=list(p),
                         observations=len(self.observations.get(k,[])),last_seen=self.track_times.get(k),confidence=self.track_confidence.get(k))
                    for k,p in self.estimates.items()]
