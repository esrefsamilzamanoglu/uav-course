"""Local-only MAVLink controller and autonomous competition procedures.

One receive thread owns parsing. Serialized sends and condition waits allow HTTP
and mission threads to stay responsive. Servo commands go through ArduPilot.
"""
from __future__ import annotations
import collections,json,math,os,threading,time
from pathlib import Path
os.environ['MAVLINK20']='1'
from pymavlink import mavutil
import numpy as np
from execution_trace import ExecutionTracer,traced_wait
from vision import select_drop_point

MODES={0:'STABILIZE',3:'AUTO',4:'GUIDED',5:'LOITER',6:'RTL',9:'LAND',16:'POSHOLD',17:'BRAKE'}
STEPS=['Hazırlık ve kalkış','Görev alanına geçiş','Hedef arama','Yaklaşma ve yük bırakma','İlk yükü geri al ve aktar','Dönüş ve iniş']

def mission_steps(mid):
    labels={
        'G1':['Yüksüz hazırlık ve kalkış','Direk 2 dış geçişi','Birinci sekiz turu','İkinci sekiz turu','Direk 2 dış çıkışı','Dönüş ve iniş'],
        'G2':['Hazırlık ve kalkış','Direk 2 dış geçişi','Hedefleri görüntüden bul','İlk hedefe yük bırak','Diğer hedefe yük bırak','Dönüş ve iniş'],
        'G3':['Hazırlık ve kalkış','Direk 2 dış geçişi','Hedefleri bul ve iki yükü bırak','İlk yükü RGB ile bul ve kavra','Diğer hedefe taşı ve bırak','Dönüş ve iniş']}
    return [dict(id=str(i),label=label,status='pending') for i,label in enumerate(labels[mid])]

class Controller:
    def __init__(self,runtime,camera,scene,event,execution=None):
        self.runtime=runtime;self.camera=camera;self.scene=scene;self.event=event
        self.link=None;self.last={};self.stamps={};self.lock=threading.RLock();self.send_lock=threading.RLock()
        self.stop=threading.Event();self.cancel=threading.Event();self.pause=threading.Event();self.acks=[];self.trail=[];self.origin=None
        self.home=np.array(scene.get('home_enu',[-24,0,.9]),float);self.local_origin_enu=None;self.system=1;self.component=1;self.last_hb=0
        self.connected=False;self.started=time.monotonic();self.mission_thread=None;self.mission_started=None
        self.mission=dict(id='G2',phase='idle',phase_label='Görev bekleniyor',status='idle',step_index=0,elapsed_s=0,paused=False,
                          steps=[dict(id=str(i),label=s,status='pending') for i,s in enumerate(STEPS)])
        self.mechanics={};self.mechanics_updated_at=0.;self.command_count=0;self.delivery_log=[]
        self.execution=execution if execution is not None else ExecutionTracer(Path(__file__).parent)
        self.execution.bind_context(lambda:{
            'mission':self.mission.get('id'),'phase':self.mission.get('phase'),
            'phase_label':self.mission.get('phase_label'),'status':self.mission.get('status'),
            'step_index':self.mission.get('step_index'),'paused':self.pause.is_set(),
            'goal_enu':self.mission.get('goal_enu')})
    def start(self):threading.Thread(target=self.loop,daemon=True,name='MAVLinkReceiver').start()
    def close(self):
        self.cancel.set();self.stop.set();self.connected=False
        if self.link:
            try:self.link.close()
            except OSError:pass
    def send(self,method,*args):
        if not self.link:raise RuntimeError('ArduPilot bağlantısı hazır değil')
        with self.send_lock:getattr(self.link.mav,method)(*args)
    def loop(self):
        deadline=time.monotonic()+90
        while not self.stop.is_set():
            try:
                self.link=mavutil.mavlink_connection('tcp:127.0.0.1:5760',source_system=253,source_component=190,autoreconnect=False)
                break
            except (OSError,ConnectionError):
                if time.monotonic()>deadline:self.event('error','ArduPilot TCP bağlantısı açılamadı');return
                self.stop.wait(.3)
        last_request=0;last_record=0
        try:
            while not self.stop.is_set():
                now=time.monotonic()
                if now-self.last_hb>1:
                    self.send('heartbeat_send',mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID,0,0,0);self.last_hb=now
                for _ in range(350):
                    msg=self.link.recv_match(blocking=False)
                    if msg is None:break
                    typ=msg.get_type()
                    if msg.get_srcComponent()!=1 or msg.get_srcSystem()!=1:continue
                    with self.lock:
                        self.last[typ]=msg.to_dict();self.stamps[typ]=time.time()
                    if typ=='HEARTBEAT':self.connected=True
                    if typ=='COMMAND_ACK':self.acks.append((time.monotonic(),msg.command,msg.result));self.acks=self.acks[-100:]
                    if typ=='STATUSTEXT':self.event('warning' if msg.severity<=4 else 'info',str(msg.text).rstrip('\0'))
                    if typ=='GLOBAL_POSITION_INT' and self.origin is None and self.last.get('GPS_RAW_INT',{}).get('fix_type',0)>=3:
                        self.origin=(msg.lat/1e7,msg.lon/1e7)
                if self.connected and now-last_request>8:
                    self.send('request_data_stream_send',1,1,mavutil.mavlink.MAV_DATA_STREAM_ALL,10,1)
                    for mid,hz in [(36,20),(33,10),(32,10),(30,10),(193,5),(1,2),(24,2)]:
                        self.send('command_long_send',1,1,511,0,mid,1e6/hz,0,0,0,0,0)
                    last_request=now
                self.read_mechanics()
                lp=self.last.get('LOCAL_POSITION_NED');vp=self.mechanics.get('vehicle_pose',{}).get('position_xyz')
                if self.local_origin_enu is None and lp and vp and not self.vehicle()['armed'] and self.vehicle().get('ekf_ok'):
                    # Calibrate the stationary launch fixture to EKF origin once.
                    # Home altitude and EKF origin are not necessarily identical.
                    self.local_origin_enu=np.array(vp)-np.array([lp['y'],lp['x'],-lp['z']])
                    (self.runtime.run/'frame-calibration.json').write_text(json.dumps(dict(origin_world_enu=self.local_origin_enu.tolist(),
                        method='Stationary launch-fixture pose minus measured LOCAL_POSITION_NED; no target coordinates',local_ned=lp),indent=2),encoding='utf-8')
                    self.event('info','EKF yerel çerçevesi kalkış platformuyla eşleştirildi')
                if now-last_record>.2:
                    state=self.vehicle();pos=state.get('position_enu')
                    if pos:
                        self.trail.append(pos);self.trail=self.trail[-1500:]
                    if self.runtime.run:
                        with (self.runtime.run/'telemetry.jsonl').open('a',encoding='utf-8') as f:
                            f.write(json.dumps(dict(wall_time=time.time(),vehicle=state,mission=self.mission),ensure_ascii=False)+'\n')
                    last_record=now
                self.stop.wait(.015)
        except (OSError,ConnectionError,TypeError) as e:
            if not self.stop.is_set():self.event('error','Telemetri bağlantısı durdu: '+str(e))
        finally:self.connected=False
    def read_mechanics(self):
        try:
            value=json.loads((self.runtime.run/'bridge/state.json').read_text(encoding='utf-8'))
            if value.get('sim_time')!=self.mechanics.get('sim_time'):self.mechanics_updated_at=time.monotonic()
            self.mechanics=value
        except (OSError,json.JSONDecodeError,TypeError):pass
    def vehicle(self):
        with self.lock:
            p=self.last.get('GLOBAL_POSITION_INT',{});a=self.last.get('ATTITUDE',{});h=self.last.get('HEARTBEAT',{})
            b=self.last.get('SYS_STATUS',{});g=self.last.get('GPS_RAW_INT',{});e=self.last.get('EKF_STATUS_REPORT',{});s=self.last.get('SERVO_OUTPUT_RAW',{})
            pos=None
            if p and self.origin:
                n=(p['lat']/1e7-self.origin[0])*111319.49
                east=(p['lon']/1e7-self.origin[1])*111319.49*math.cos(math.radians(self.origin[0]))
                pos=[self.home[0]+east,self.home[1]+n,self.home[2]+p['relative_alt']/1000]
            gps_position=pos
            lp=self.last.get('LOCAL_POSITION_NED')
            if lp and self.local_origin_enu is not None:
                pos=(self.local_origin_enu+np.array([lp['y'],lp['x'],-lp['z']])).tolist()
            return dict(armed=bool(h.get('base_mode',0)&128),mode=MODES.get(h.get('custom_mode'),'—'),
                        position_enu=pos,gps_position_enu=gps_position,velocity_enu=[p.get('vy',0)/100,p.get('vx',0)/100,-p.get('vz',0)/100] if p else None,
                        altitude_m=p.get('relative_alt',0)/1000 if p else None,speed_mps=math.hypot(p.get('vx',0),p.get('vy',0))/100 if p else None,
                        vertical_speed_mps=-p.get('vz',0)/100 if p else None,heading_deg=p.get('hdg',0)/100 if p else None,
                        latitude=p.get('lat',0)/1e7 if p else None,longitude=p.get('lon',0)/1e7 if p else None,
                        attitude_deg=[math.degrees(a.get(k,0)) for k in ('roll','pitch','yaw')] if a else None,
                        battery_percent=b.get('battery_remaining') if b.get('battery_remaining',-1)>=0 else None,
                        battery_voltage=b.get('voltage_battery',0)/1000 if b.get('voltage_battery',65535)!=65535 else None,
                        gps_fix=g.get('fix_type'),satellites=g.get('satellites_visible'),ekf_ok=(e.get('flags',0)&55)==55 if e else None,
                        servo_pwm={str(ch):s.get('servo'+str(ch)+'_raw') for ch in (9,10)},
                        last_heartbeat_age_s=time.time()-self.stamps['HEARTBEAT'] if 'HEARTBEAT' in self.stamps else None)
    @traced_wait('command')
    def command(self,cmd,*params,timeout=5):
        start=time.monotonic();p=list(params)+[0]*7
        self.send('command_long_send',1,1,cmd,0,*p[:7])
        if self.runtime.run:
            with (self.runtime.run/'commands.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(t=time.time(),command=cmd,params=p[:7]))+'\n')
        while time.monotonic()-start<timeout:
            matches=[ack for ack in self.acks if ack[0]>=start and ack[1]==cmd]
            if matches:
                result=matches[-1][2]
                if result not in (0,5):raise RuntimeError('ArduPilot komutu reddetti: '+str(cmd)+' / '+str(result))
                return
            if self.stop.wait(.04):raise RuntimeError('Oturum kapandı')
        raise TimeoutError('ArduPilot komut yanıtı alınamadı: '+str(cmd))
    @traced_wait('wait')
    def wait(self,condition,timeout=30,description='Koşul',allow_cancel=True):
        start=time.monotonic()
        while time.monotonic()-start<timeout:
            if allow_cancel and self.cancel.is_set():raise RuntimeError('Görev durduruldu')
            if allow_cancel and self.pause.is_set():time.sleep(.08);start+=.08;continue
            if not self.connected or self.stop.is_set():raise RuntimeError('Telemetri bağlantısı yok')
            if condition():return
            time.sleep(.08)
        raise TimeoutError(description+' zaman aşımı')
    def mode(self,number):
        self.send('set_mode_send',1,mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,number)
        self.wait(lambda:self.last.get('HEARTBEAT',{}).get('custom_mode')==number,10,'Uçuş modu',False)
    def servo(self,channel,pwm):
        if channel not in (9,10) or pwm not in (1100,1900):raise ValueError('Servo9/10;PWM1100/1900 kullanılabilir')
        self.command(183,channel,pwm)
        self.event('info',f'SERVO{channel} → {pwm} µs · ArduPilot komutu')
    def takeoff(self,altitude=8):
        if not 1<=altitude<=40:raise ValueError('Kalkış irtifası 1–40 m olmalı')
        if self.vehicle()['armed'] and (self.vehicle().get('altitude_m') or 0)>.7:return
        self.mode(4)
        if not self.vehicle()['armed']:self.command(400,1)
        self.wait(lambda:self.vehicle()['armed'],15,'ARM')
        self.command(22,0,0,0,0,0,0,float(altitude))
        self.wait(lambda:(self.vehicle().get('altitude_m') or 0)>=altitude-.5,60,'Kalkış')
        self.event('info',f'Kalkış tamamlandı · {altitude:g} m')
    @traced_wait('goto')
    def goto(self,goal,radius=.35,settle=True,timeout=100):
        goal=np.asarray(goal,float)
        if not (-100<=goal[0]<=100 and -150<=goal[1]<=150 and .6<=goal[2]<=60):raise ValueError('Hedef eğitim sahası dışında')
        self.mission['goal_enu']=goal.tolist();start=time.monotonic();lastsend=0
        while time.monotonic()-start<timeout:
            if self.cancel.is_set():raise RuntimeError('Görev durduruldu')
            if self.pause.is_set():time.sleep(.05);start+=.05;continue
            if not self.connected:raise RuntimeError('Telemetri bağlantısı yok')
            if time.monotonic()-lastsend>.25:
                origin=getattr(self,'local_origin_enu',None)
                if origin is None:origin=self.home
                self.send('set_position_target_local_ned_send',0,1,1,1,3576,float(goal[1]-origin[1]),float(goal[0]-origin[0]),float(-(goal[2]-origin[2])),0,0,0,0,0,0,0,0)
                self.command_count+=1;lastsend=time.monotonic()
            v=self.vehicle();pos=v.get('position_enu');vel=v.get('velocity_enu')
            if getattr(self,'execution',None) and pos:
                self.execution.update_wait(position_enu=pos,distance_m=float(np.linalg.norm(np.array(pos[:2])-goal[:2])),
                    altitude_error_m=float(goal[2]-pos[2]),speed_mps=float(np.linalg.norm(vel)) if vel is not None else None)
            ztol=.05 if goal[2]<1.3 else .3
            if pos and np.linalg.norm(np.array(pos[:2])-goal[:2])<radius and abs(pos[2]-goal[2])<ztol:
                if not settle or np.linalg.norm(vel)<.22:return
            time.sleep(.05)
        raise TimeoutError('Konum hedefi: '+str(goal.round(2).tolist()))
    def phase(self,i,label=None):
        while self.pause.is_set():
            if self.cancel.is_set():raise RuntimeError('Görev durduruldu')
            time.sleep(.08)
        self.mission.update(step_index=i,phase=str(i),phase_label=label or STEPS[i])
        if getattr(self,'execution',None):self.execution.update_context(phase=str(i),phase_label=self.mission['phase_label'],step_index=i)
        for j,s in enumerate(self.mission['steps']):s['status']='completed' if j<i else 'active' if j==i else 'pending'
        self.event('info',label or STEPS[i])
    def grips(self):return {g['id']:g for g in self.mechanics.get('grippers',[])}
    def gripper_pair(self,color):
        """Aynı fizik mesajından gövde ve kavrayıcı konumunu birlikte okur."""
        snapshot=self.mechanics
        body=snapshot.get('vehicle_pose',{}).get('position_xyz')
        grip=next((g for g in snapshot.get('grippers',[]) if g.get('id')==color),None)
        end=grip.get('position_xyz') if grip else None
        if body is None or end is None:raise RuntimeError('Eşlenmiş gövde/kavrayıcı fizik verisi yok')
        body=np.asarray(body,float);end=np.asarray(end,float)
        if body.shape!=(3,) or end.shape!=(3,) or not np.isfinite(body).all() or not np.isfinite(end).all():
            raise RuntimeError('Eşlenmiş gövde/kavrayıcı fizik verisi geçersiz')
        return body,end,grip
    def gripper_offset(self,color):
        """Kavrayıcı ofsetini aynı zamanlı iki konumdan hesaplar; LP ile karıştırmaz."""
        body,end,_=self.gripper_pair(color)
        return end-body
    def pickup_ready(self,color,height):
        """Yerel telemetri, native yükseklik ve askı durulmasının eşleşmesini bekler."""
        body,_,grip=self.gripper_pair(color);v=self.vehicle();local=v.get('position_enu');velocity=v.get('velocity_enu')
        return time.monotonic()-getattr(self,'mechanics_updated_at',0.)<1.0 and local is not None and velocity is not None and abs(body[2]-height)<.05 and \
            np.linalg.norm(body-np.asarray(local))<.08 and np.linalg.norm(velocity)<.10 and abs(grip.get('swing_deg',90))<3
    def visual_pickup_lock(self,near):
        """1,2 m'de üç güncel ve tutarlı RGB gözleminden kısa süreli sabit yük kilidi alır."""
        samples=[];last_seen=None;answer=[]
        def consistent():
            nonlocal last_seen
            point=self.camera.pickup_estimate;seen=self.camera.pickup_seen_at
            if point is None or not 0<=time.time()-seen<1.5:return False
            samples[:]=[(p,stamp) for p,stamp in samples if 0<=time.time()-stamp<1.5]
            if seen!=last_seen:
                value=np.asarray(point,float)
                if value.shape!=(3,) or not np.isfinite(value).all() or np.linalg.norm(value[:2]-np.asarray(near)[:2])>.6:return False
                samples.append((value,seen));del samples[:-3];last_seen=seen
            if len(samples)<3:return False
            values=np.array([p for p,_ in samples])
            if np.max(np.linalg.norm(values[:,:2]-np.median(values[:,:2],axis=0),axis=1))>.04:return False
            answer[:]=[np.median(values,axis=0).tolist(),samples[-1][1]]
            return True
        self.wait(consistent,12,'1,2 m’de üç tutarlı ve güncel RGB yük gözlemi')
        if not answer:raise RuntimeError('RGB yük kilidi alınamadı')
        return answer[0],answer[1]
    def pickup(self,color,near,channel):
        """RGB ile yaklaşır; son dar görüş alanında en fazla 15 s’lik kilitle hizalanır."""
        self.camera.pickup_color=color;self.camera.pickup_near=list(near);self.camera.pickup_estimate=None
        try:
            self.goto([*near[:2],4],radius=.10)
            self.wait(lambda:self.pickup_ready(color,4),30,'4 m’de eşlenmiş gövde/kavrayıcı ve askı durulması')
            for height in (2.0,1.2):
                self.wait(lambda:self.camera.pickup_estimate is not None and 0<=time.time()-self.camera.pickup_seen_at<1.5,15,'Güncel RGB yük konumu')
                point=np.asarray(self.camera.pickup_estimate);xy=point[:2]-self.gripper_offset(color)[:2]
                self.goto([*xy,height],radius=.035)
                self.wait(lambda:self.pickup_ready(color,height),30,'Yaklaşma yüksekliği ve eşlenmiş kavrayıcı verisi')
            locked,seen=self.visual_pickup_lock(near)
            deadline=time.monotonic()+max(0.,15-(time.time()-seen))
            def remaining():
                left=deadline-time.monotonic()
                if left<=0:raise TimeoutError('Son yaklaşmada RGB yük kilidinin 15 s sınırı doldu')
                return left
            aligned=False
            for _ in range(3):
                xy=np.asarray(locked[:2])-self.gripper_offset(color)[:2]
                self.goto([*xy,.89],radius=.02,timeout=remaining())
                self.wait(lambda:self.pickup_ready(color,.89),remaining(),'Son yükseklik, askı ve konum eşleşmesi')
                _,end,_=self.gripper_pair(color)
                if np.linalg.norm(end[:2]-np.asarray(locked[:2]))<.025:aligned=True;break
            if not aligned:raise RuntimeError('RGB yük kilidi üzerinde kavrayıcı hizalanamadı')
            remaining();self.servo(channel,1900)
            self.wait(lambda:self.grips().get(color,{}).get('attached',False),min(10.,remaining()),'Yakınlık/hız kapısıyla gerçek kavrama')
        finally:
            self.camera.pickup_color=None
    def release(self,color,target,kind=None,reserve=False,occupied=None):
        """Araç RGB'sindeki boş alana alçak ve yavaş bırakma için hizalanır."""
        ch=9 if color=='red' else 10
        index=(4 if len(self.delivery_log)>=2 else 2) if self.mission['id']=='G3' else (3 if not self.delivery_log else 4)
        self.phase(index,('Kırmızı' if color=='red' else 'Mavi')+' yük · yaklaşma ve bırakma')
        self.goto([*target[:2],4.0])
        drop_point=list(target);observed_occupied=None
        if reserve or occupied is not None:
            if kind not in ('red_triangle','blue_hexagon'):raise ValueError('Boş alan seçimi için RGB hedef türü gerekli')
            if occupied not in (None,'rgb'):raise ValueError('Doluluk konumu güncel araç RGB görüntüsünden alınmalı')
            if occupied=='rgb':
                self.camera.pickup_color='blue' if color=='red' else 'red'
                self.camera.pickup_near=list(target);self.camera.pickup_estimate=None;self.camera.pickup_seen_at=0
            try:
                def placement_ready():
                    return self.camera.target_polygon(kind,max_age=2.) is not None and (occupied is None or
                        self.camera.pickup_estimate is not None and time.time()-self.camera.pickup_seen_at<1.5)
                self.wait(placement_ready,20,'Güncel RGB hedef çokgeni ve yerdeki yükün görülmesi')
                polygon=self.camera.target_polygon(kind,max_age=2.)
                if polygon is None:raise RuntimeError('RGB hedef çokgeni güncelliğini kaybetti')
                if occupied is not None:
                    if time.time()-self.camera.pickup_seen_at>=1.5:raise RuntimeError('Yerdeki yükün RGB gözlemi güncelliğini kaybetti')
                    observed_occupied=list(self.camera.pickup_estimate)
                drop_point=select_drop_point(target,polygon,observed_occupied,margin=.18 if reserve else .17,reserve=reserve)
            finally:
                if occupied is not None:self.camera.pickup_color=None;self.camera.pickup_near=None
        # Only measured gripper kinematics align the chosen RGB drop point.
        for _ in range(3):
            xy=np.asarray(drop_point[:2])-self.gripper_offset(color)[:2]
            self.goto([*xy,1.25],radius=.02)
            time.sleep(1.0)
        def settled():
            grip=self.grips().get(color,{})
            payload=next((p for p in self.mechanics.get('payloads',[]) if p.get('id')==grip.get('payload')),None)
            return payload is not None and abs(grip.get('swing_deg',90))<3 and np.linalg.norm(payload.get('velocity_xyz',[99,99,99])[:2])<.04
        self.wait(settled,30,'Yük salınımı <3° ve yatay hız <0,04 m/s')
        self.servo(ch,1100)
        self.wait(lambda:not self.grips().get(color,{}).get('attached',True),8,'Yükün ayrılması')
        record=dict(color=color,target=list(target),kind=kind,drop_point=drop_point,occupied_rgb=observed_occupied,channel=ch,t=time.time())
        self.delivery_log.append(record)
        self.event('info',('Kırmızı' if color=='red' else 'Mavi')+' yük gerçek fizik ekleminden ayrıldı')
        time.sleep(2)
    def mission_start(self,mission):
        if self.mission_thread and self.mission_thread.is_alive():raise RuntimeError('Bir görev zaten çalışıyor')
        if mission not in ('G1','G2','G3'):raise ValueError('G1/G2/G3 seçin')
        self.cancel.clear();self.pause.clear();self.mission.update(id=mission,status='running',paused=False);self.delivery_log=[]
        self.mission['steps']=mission_steps(mission)
        self.mission_started=time.monotonic();self.camera.estimates={};self.camera.observations={};self.camera.perception_enabled=False
        self.camera.target_polygons={};self.camera.polygon_times={}
        self.mission_thread=threading.Thread(target=self._run_traced_mission,args=(mission,),daemon=True,name='CompetitionMission');self.mission_thread.start()
    def _run_traced_mission(self,mission):
        with self.execution.capture(mission,lane='mission'):
            self.run_mission(mission)
            self.execution.finish(self.mission.get('status','finished'))
    def run_mission(self,mission):
        try:
            self.phase(0)
            if not self.vehicle()['armed']:
                def ready():
                    v=self.vehicle();s=self.last.get('SYS_STATUS',{});flag=1<<28
                    checks=bool(s.get('onboard_control_sensors_health',0)&flag) if s.get('onboard_control_sensors_present',0)&flag else self.last.get('GLOBAL_POSITION_INT',{}).get('time_boot_ms',0)>22000
                    return v.get('ekf_ok') and (v.get('gps_fix') or 0)>=3 and checks
                self.wait(ready,90,'GPS / EKF / ARM hazırlığı')
            if mission=='G1':self.servo(9,1100);self.servo(10,1100)
            else:
                self.servo(9,1900);self.servo(10,1900)
                self.wait(lambda:all(self.grips().get(c,{}).get('attached') for c in ('red','blue')),12,'İki yükün fiziksel kavranması')
            self.takeoff(12);self.phase(1)
            self.goto([-40,-105,12+self.home[2]],radius=1,settle=False)
            self.goto([0,-105,12+self.home[2]],radius=1)
            if mission=='G1':
                self.phase(2,'G1 · iki ardışık sekiz turu')
                for index,theta in enumerate(np.linspace(-math.pi/2,7*math.pi/2,73)):
                    if index==36:self.phase(3,'G1 · ikinci sekiz turu')
                    # Advance the next GUIDED goal before braking to a stop at
                    # every node. The actual winding, field limits and deadline
                    # are checked independently from the flown trajectory.
                    self.goto([38*math.sin(2*theta),100*math.sin(theta),12+self.home[2]],radius=8,settle=False)
                self.phase(4,'İki sekiz tamamlandı')
                self.goto([-40,-110,12+self.home[2]],radius=2,settle=False)
            else:
                self.phase(2);self.camera.perception_enabled=True
                for j,east in enumerate((-11,0,11)):
                    for north in ((-55,55) if j%2==0 else (55,-55)):
                        self.goto([east,north,12+self.home[2]],radius=.7)
                    if len(self.camera.estimates)>=2:break
                self.wait(lambda:all(k in self.camera.estimates for k in ('blue_hexagon','red_triangle')),10,'Kameradan iki hedef doğrulaması')
                targets=list(self.camera.estimates.items())
                for kind,p in targets:
                    color='red' if kind=='blue_hexagon' else 'blue'
                    i=(2 if mission=='G3' else (3 if not self.delivery_log else 4))
                    self.phase(i,('Kırmızı' if color=='red' else 'Mavi')+' yük · kamera hedefi üzerine yaklaşma')
                    self.goto([*p[:2],8]);self.release(color,p,kind=kind,reserve=mission=='G3' and kind=='red_triangle')
                    self.goto([*p[:2],8])
                if mission=='G3':
                    first=self.delivery_log[0];color=first['color'];other_kind,other=next((k,p) for k,p in targets if k!=first['kind'])
                    self.phase(3,'G3 · ilk yükü kameradan yeniden bul ve kavra')
                    self.pickup(color,first['target'],first['channel'])
                    self.phase(4,'G3 · ilk yükü diğer hedefe taşı')
                    self.goto([*self.vehicle()['position_enu'][:2],8]);self.goto([*other[:2],8]);self.release(color,other,kind=other_kind,occupied='rgb')
            self.phase(5)
            # G1 has already left the far P2 through its outside corridor.
            # Return straight to the centred launch line instead of detouring
            # past P1; G2/G3 retain their P1 outside-return requirement.
            if mission!='G1':
                self.goto([self.home[0],105,12+self.home[2]],radius=1,settle=False)
            self.goto([*self.home[:2],12+self.home[2]],radius=.3)
            # Rendering the extra teaching camera can slow simulation against
            # wall time. Keep time for the physical descent and normal disarm.
            self.mode(9);self.wait(lambda:not self.vehicle()['armed'],140,'Otomatik iniş')
            self.mission.update(status='completed',phase_label='Görev tamamlandı')
            for s in self.mission['steps']:s['status']='completed'
            self.event('info',mission+' tamamlandı · iniş ve disarm doğrulandı')
        except Exception as e:
            self.mission.update(status='paused' if self.cancel.is_set() else 'failed',phase_label=str(e))
            self.event('error',str(e))
            if not self.cancel.is_set() and self.connected and self.vehicle()['armed']:
                try:self.mode(17)
                except Exception:pass
        finally:
            self.camera.pickup_color=None
            if self.runtime.run:
                (self.runtime.run/'mission-result.json').write_text(json.dumps(dict(mission=self.mission,deliveries=self.delivery_log,
                    actuator_path='ArduPilot native servo output → Gazebo gated detachable joint',camera='actual Gazebo RGB'),ensure_ascii=False,indent=2),encoding='utf-8')
