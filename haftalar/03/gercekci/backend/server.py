"""ROTA GCS local HTTP API and static React application server."""
from __future__ import annotations
import argparse,collections,datetime as dt,json,mimetypes,os,threading,time,traceback
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
import cv2
from native_runtime import BASE,NativeRuntime
from control import Controller
from vision import Camera
from execution_trace import ExecutionTracer
from follow_camera import FollowCamera

DIST=BASE/'gcs/frontend/dist'
TZ=dt.timezone(dt.timedelta(hours=3))

class Service:
    def __init__(self,gui=False):
        self.lock=threading.RLock();self.events=collections.deque(maxlen=300);self.gui=gui
        self.runtime=NativeRuntime(self.event);self.controller=None;self.camera=None;self.follow_camera=None;self.starting=False
        self.execution=ExecutionTracer(BASE/'backend')
        self.scene=json.loads((BASE/'world/scene.json').read_text(encoding='utf-8'));self.map_cache=(0,None)
        b=self.scene.get('field_bounds',{});self.scene['field_bounds']={
            'east_min':b.get('east',[-100,100])[0],'east_max':b.get('east',[-100,100])[1],
            'north_min':b.get('north',[-150,150])[0],'north_max':b.get('north',[-150,150])[1]}
        self.scene['pylons']=[dict(name='Direk '+str(i+1),position_enu=p) for i,p in enumerate(self.scene.get('pylons_enu',[]))]
        self.scene['map_view_bounds']=dict(east_min=-190,east_max=190,north_min=-190,north_max=190)
        route=[]
        import math
        for i in range(145):
            a=-math.pi/2+4*math.pi*i/144;route.append([38*math.sin(2*a),100*math.sin(a),12.9])
        self.scene['route']=route
        self.event('info','ROTA GCS hazır · yerel simülasyon bağlantısı bekleniyor')
    def event(self,level,message):
        row=dict(timestamp=dt.datetime.now(TZ).isoformat(),level=level,message=str(message))
        with self.lock:self.events.appendleft(row)
        if self.runtime.run:
            try:
                with (self.runtime.run/'gcs-events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
            except OSError:pass
    def start(self):
        with self.lock:
            if self.starting or self.runtime.running:raise RuntimeError('Simülasyon zaten açılıyor veya açık')
            self.starting=True;self.runtime.status='starting'
        def task():
            try:
                run=self.runtime.start(self.gui)
                self.camera=Camera(run/'bridge',self.scene.get('camera',{}).get('hfov_rad',1.2217304764))
                self.controller=Controller(self.runtime,self.camera,self.scene,self.event,execution=self.execution)
                self.camera.update=self.execution.wrap(self.camera.update,lane='vision')
                self.follow_camera=FollowCamera(run/'bridge')
                self.camera.start();self.controller.start()
            except Exception as e:
                self.runtime.error=str(e);self.event('error',str(e));self.runtime.close();self.runtime.status='error'
            finally:self.starting=False
        threading.Thread(target=task,daemon=True,name='SimulationLauncher').start()
    def close(self):
        if self.controller:self.controller.close()
        if self.camera:self.camera.close()
        self.runtime.close();self.controller=None;self.camera=None;self.follow_camera=None
    def snapshot(self):
        c=self.controller;vehicle=c.vehicle() if c else None
        connected=bool(c and c.connected and (vehicle.get('last_heartbeat_age_s') or 0)<4)
        camera,det=self.camera.state() if self.camera else (dict(available=False,frame_id=0,width=960,height=720,age_s=None),[])
        grips={}
        raw=c.grips() if c else {}
        for color,ch in [('red',9),('blue',10)]:
            g=raw.get(color,{})
            payload=next((p for p in (c.mechanics.get('payloads',[]) if c else []) if p.get('id')=='payload_'+color),{})
            grips[color]=dict(attached=g.get('attached'),pwm=g.get('pwm'),swing_deg=g.get('swing_deg'),
                payload_mass_kg=payload.get('mass_kg',.3),position_enu=g.get('position_xyz'),payload=g.get('payload'),
                payload_position_enu=payload.get('pose',{}).get('position_xyz'),payload_velocity_enu=payload.get('velocity_xyz'),
                reject_reason=g.get('reason'),command_source=g.get('command_source'),distance_m=g.get('distance_m'),
                relative_speed_mps=g.get('relative_speed_m_s'),attach_count=g.get('attach_count'),release_count=g.get('release_count'))
        if c and c.mission_started and c.mission.get('status')=='running':c.mission['elapsed_s']=time.monotonic()-c.mission_started
        mission=c.mission if c else dict(id='G2',phase='idle',phase_label='Görev bekleniyor',status='idle',steps=[],step_index=0,elapsed_s=0,paused=False)
        with self.lock:events=list(self.events)
        return dict(connected=connected,simulation=dict(running=self.runtime.running,status=self.runtime.status,error=self.runtime.error,
                    run_directory=str(self.runtime.run) if self.runtime.run else None),vehicle=vehicle,mission=mission,camera=camera,
                    detections=det,grippers=grips,scene=self.scene,events=events,trail=c.trail if c else [],
                    confirmed_detections=self.camera.confirmed() if self.camera and connected else [],
                    physics=c.mechanics if c else {},
                    follow_camera=self.follow_camera.state() if self.follow_camera else FollowCamera.empty_state(),
                    execution=self.execution.summary(),server_time=dt.datetime.now(TZ).isoformat())
    def execute(self,data):
        action=data.get('action')
        if action=='simulation_start':self.start();return
        if action=='simulation_stop':threading.Thread(target=self.close,daemon=True).start();return
        if action=='camera_follow':
            if not self.follow_camera:raise RuntimeError('Önce Gazebo simülasyonunu başlatın')
            self.follow_camera.set_mode(data.get('mode','chase'));return
        c=self.controller
        if not c or not c.connected:raise RuntimeError('Önce simülasyona bağlanın')
        if action=='mission_start':c.mission_start(data.get('mission','G2'));return
        if action=='mission_pause':
            if c.pause.is_set():
                c.mode(4);c.pause.clear();c.mission.update(paused=False,status='running')
            else:
                c.pause.set();c.mission.update(paused=True,status='paused');c.mode(17)
            return
        if action in ('hold','land'):
            c.cancel.set();c.mission.update(paused=True,status='paused')
            c.mode(9 if action=='land' else 17);return
        if action=='servo':c.servo(int(data.get('channel',0)),int(data.get('pwm',0)));return
        if action=='arm':c.command(400,1);return
        if action=='takeoff':
            c.cancel.clear();threading.Thread(target=self.safe_task,args=(c.takeoff,float(data.get('altitude_m',8))),daemon=True).start();return
        if action=='goto':
            if not c.vehicle()['armed']:raise RuntimeError('Araç havada olmalı')
            goal=data.get('position_enu')
            if not isinstance(goal,list) or len(goal)!=3:raise ValueError('Konum: [doğu,kuzey,yükseklik]')
            c.cancel.clear();c.mode(4);threading.Thread(target=self.safe_task,args=(c.goto,goal),daemon=True).start();return
        raise ValueError('Bilinmeyen komut')
    def safe_task(self,fn,*args):
        try:fn(*args)
        except Exception as e:self.event('error',str(e))
    def map_jpeg(self):
        if not self.runtime.run:return None
        p=self.runtime.run/'bridge/overview.ppm'
        try:
            stamp=p.stat().st_mtime_ns
            if stamp!=self.map_cache[0]:
                im=cv2.imread(str(p));ok,b=cv2.imencode('.jpg',im,[cv2.IMWRITE_JPEG_QUALITY,90]) if im is not None else (False,None)
                if ok:self.map_cache=(stamp,b.tobytes())
            return self.map_cache[1]
        except (OSError,cv2.error):return None

class Handler(BaseHTTPRequestHandler):
    server_version='ROTA-GCS/1.0'
    def log_message(self,*a):pass
    @property
    def service(self):return self.server.service
    def reply(self,status,data,mime='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False,allow_nan=False).encode('utf-8')
        if isinstance(data,str):data=data.encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        origin=self.headers.get('Origin','')
        if origin in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8787','http://localhost:8787'):
            self.send_header('Access-Control-Allow-Origin',origin);self.send_header('Access-Control-Allow-Headers','Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS')
        self.end_headers()
        try:self.wfile.write(data)
        except (BrokenPipeError,ConnectionResetError):pass
    def do_OPTIONS(self):self.reply(204,b'')
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/api/state':return self.reply(200,self.service.snapshot())
            if path=='/api/code/catalog':return self.reply(200,self.service.execution.catalog())
            if path in ('/api/code/source','/api/code/trace'):
                query=parse_qs(urlparse(self.path).query)
                try:
                    if path.endswith('source'):
                        data=self.service.execution.source(query.get('file',['control.py'])[0])
                    else:
                        after=int(query.get('after',['0'])[0]);limit=int(query.get('limit',['120'])[0])
                        if after<0 or not 0<=limit<=200:raise ValueError('Geçersiz kod izi aralığı')
                        data=self.service.execution.snapshot(after_seq=after,limit=limit)
                    return self.reply(200,data)
                except (ValueError,KeyError) as e:return self.reply(400,{'error':str(e)})
            if path=='/api/follow.jpg':
                data=self.service.follow_camera.jpeg() if self.service.follow_camera else None
                return self.reply(200,data,'image/jpeg') if data else self.reply(404,{'error':'Takip kamerasının güncel karesi bekleniyor'})
            if path=='/api/camera.jpg':
                data=self.service.camera.jpeg if self.service.camera else None
                return self.reply(200,data,'image/jpeg') if data else self.reply(404,{'error':'Kamera çerçevesi bekleniyor'})
            if path=='/api/map.jpg':
                data=self.service.map_jpeg()
                return self.reply(200,data,'image/jpeg') if data else self.reply(404,{'error':'Harita görüntüsü bekleniyor'})
            if path=='/api/health':return self.reply(200,{'ok':True,'service':'ROTA GCS','transport':'localhost only'})
            file=(DIST/path.lstrip('/')).resolve()
            if not file.is_relative_to(DIST.resolve()):return self.reply(403,{'error':'Geçersiz yol'})
            if not file.is_file():file=DIST/'index.html'
            if not file.is_file():return self.reply(503,'ROTA GCS hazırlanıyor. Önce Kur.cmd çalıştırın.','text/plain; charset=utf-8')
            return self.reply(200,file.read_bytes(),mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        except Exception as e:return self.reply(500,{'error':str(e)})
    def do_POST(self):
        if urlparse(self.path).path!='/api/command':return self.reply(404,{'error':'Bilinmeyen API'})
        origin=self.headers.get('Origin','')
        if origin and origin not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8787','http://localhost:8787'):
            return self.reply(403,{'error':'Yalnız yerel GCS kaynağı kabul edilir'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<8192:raise ValueError('Geçersiz komut boyutu')
            data=json.loads(self.rfile.read(length));self.service.execute(data)
            return self.reply(200,{'ok':True,'action':data.get('action')})
        except Exception as e:
            self.service.event('error',str(e));return self.reply(400,{'ok':False,'error':str(e)})

def main():
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8787);p.add_argument('--gui',action='store_true');p.add_argument('--start',action='store_true');p.add_argument('--open',action='store_true');a=p.parse_args()
    service=Service(a.gui);server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler);server.service=service
    print('ROTA GCS http://127.0.0.1:'+str(a.port),flush=True)
    if a.open:
        import webbrowser
        threading.Timer(.4,lambda:webbrowser.open('http://127.0.0.1:'+str(a.port))).start()
    if a.start:service.start()
    try:server.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:pass
    finally:server.server_close();service.close()
if __name__=='__main__':main()
