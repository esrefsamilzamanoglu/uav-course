"""Read the separate, actual Gazebo spectator sensor and request view modes.

Mode requests are file-to-Transport input. Reported modes come only from native
feedback matched to a rendered frame, never from the requested UI value.
"""
from __future__ import annotations
import json,os,threading,time,uuid
from pathlib import Path
import cv2

MODES=(
    dict(id='chase',label='Takip',description='Aracın arkasından yumuşak takip.'),
    dict(id='orbit',label='Yörünge',description='Uçan aracın çevresinde yavaşça döner.'),
    dict(id='side',label='Yan',description='Gövde ve asılı yükleri yandan izler.'),
    dict(id='top',label='Üst',description='Aracı üstten izler; sabit saha haritasından ayrıdır.'),
)
LABELS={row['id']:row['label'] for row in MODES}

class FollowCamera:
    @staticmethod
    def empty_state():
        return dict(available=False,mode=None,mode_label='Görüntü bekleniyor',width=640,height=360,
            age_s=None,frame_id=0,source='Gazebo external follow camera',sim_time=None,
            modes=[dict(row) for row in MODES],requested_mode=None,pending=False,
            eye_enu=None,target_enu=None,quaternion_xyzw=None,pose_delta_s=None)

    def __init__(self,bridge_dir,max_age=2.):
        self.directory=Path(bridge_dir);self.max_age=float(max_age)
        self.lock=threading.RLock();self.meta={};self._jpeg=None;self._stamp=None;self.requested_mode=None

    def _update(self):
        frame=self.directory/'follow.ppm';metadata=self.directory/'follow.json'
        try:
            fs0,ms0=frame.stat(),metadata.stat();stamp=(fs0.st_mtime_ns,ms0.st_mtime_ns)
            if stamp==self._stamp or ms0.st_mtime_ns<fs0.st_mtime_ns:return
            meta=json.loads(metadata.read_text(encoding='utf-8'))
            if meta.get('mode') not in LABELS or meta.get('pose_delta_s',999)>.1:return
            image=cv2.imread(str(frame));fs1,ms1=frame.stat(),metadata.stat()
            if image is None or image.shape[:2]!=(meta.get('height'),meta.get('width')):return
            if stamp!=(fs1.st_mtime_ns,ms1.st_mtime_ns):return
            ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,88])
            if not ok:return
            self.meta=meta;self._jpeg=jpeg.tobytes();self._stamp=stamp
        except (OSError,ValueError,TypeError,cv2.error):return

    def state(self):
        with self.lock:
            self._update();meta=self.meta
            age=max(0.,time.time()-meta['wall_time']) if meta.get('wall_time') else None
            mode=meta.get('mode');native=meta.get('native_state',{})
            return dict(available=bool(self._jpeg and age is not None and age<=self.max_age),
                mode=mode,mode_label=LABELS.get(mode,'Görüntü bekleniyor'),
                width=meta.get('width',640),height=meta.get('height',360),age_s=age,
                frame_id=meta.get('frame',0),source=meta.get('source','Gazebo external follow camera'),
                sim_time=meta.get('sim_time'),modes=[dict(row) for row in MODES],
                requested_mode=self.requested_mode,
                pending=self.requested_mode is not None and self.requested_mode!=mode,
                eye_enu=native.get('eye_enu'),target_enu=native.get('target_enu'),
                quaternion_xyzw=native.get('camera_pose',{}).get('quaternion_xyzw'),
                pose_delta_s=meta.get('pose_delta_s'))

    def jpeg(self):
        with self.lock:
            state=self.state()
            return self._jpeg if state['available'] else None

    def set_mode(self,mode):
        if not isinstance(mode,str) or mode not in LABELS:raise ValueError('Kamera modu: chase, orbit, side veya top')
        with self.lock:
            self.directory.mkdir(parents=True,exist_ok=True)
            request=dict(mode=mode,request_id=uuid.uuid4().hex,requested_at=time.time())
            target=self.directory/'follow-control.json';temp=target.with_suffix('.'+request['request_id']+'.next')
            try:
                temp.write_text(json.dumps(request,ensure_ascii=False),encoding='utf-8');os.replace(temp,target)
            finally:
                try:temp.unlink(missing_ok=True)
                except OSError:pass
            self.requested_mode=mode
            return self.state()
