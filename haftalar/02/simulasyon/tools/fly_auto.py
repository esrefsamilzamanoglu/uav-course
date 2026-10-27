"""Local SITL test GCS: upload a mission, start AUTO once, then only observe.

No GUIDED, RC overrides, position targets, velocity targets or in-flight route edits.
Run only the SITL process owned by runtime.Session, on localhost TCP5760.
"""
from __future__ import annotations
import argparse,collections,json,math,os,shutil,subprocess,sys,time,traceback
from pathlib import Path
os.environ['MAVLINK20']='1'
from pymavlink import mavutil
from runtime import ROOT,LOCAL,Session,port_free

MISSIONS={'intro':'00_kamera_tanitimi','spray':'01_tarla_ilaclama','mapping':'02_tarla_2d_haritalama','building':'03_bina_3d_haritalama','plane':'04_sabit_kanat_gozetim'}
def safe(v):
    if isinstance(v,bytes):return v.decode(errors='replace')
    if isinstance(v,float) and not math.isfinite(v):return None
    if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)):return [safe(x) for x in v]
    return v
class GCS:
    def __init__(self,session,port=5760):
        self.s=session;self.last={};self.params={};self.messages=collections.Counter();self.acks=[];self.sent=[]
        self.events=[];self.telemetry=[];self.photos=[];self.start=time.time();self.last_heartbeat=0;self.last_sample=0
        self.maxalt=0;self.link=None;self.armed_once=False;self.current_seq=0;self.max_seq=0;self.status='running'
        self.port=port
    def event(self,name,**data):
        row={'wall_time':time.time(),'t':round(time.time()-self.start,3),'event':name,**safe(data)};self.events.append(row)
        if os.environ.get('UAV_COURSE_STUDENT')=='1':
            if name=='navigation_ready':print('Sensorler hazir. Mission Planner uzerinden gorevi baslatabilirsiniz.',flush=True)
            elif name=='waiting_for_mission_planner':print('Mission Planner TCP127.0.0.1:5760 baglantisi ve AUTO/ARM bekleniyor.',flush=True)
            elif name=='operator_started_auto':print('AUTO gorevi basladi; Python yalniz kayit ve goruntu isleme yapiyor.',flush=True)
            elif name=='auto_landed':print('Gorev tamamlandi ve arac indi.',flush=True)
            elif name=='photos_matched':print('Kaydedilen fotograf: '+str(data['actual_gazebo_photos']),flush=True)
            elif name in ('failure','integration_failure'):print('Islem durdu: '+str(data.get('error','')),flush=True)
            elif name=='status_text' and data.get('text','').startswith(('PreArm:','Arm:','Crash')):print(data['text'],flush=True)
        else:print(json.dumps(row),flush=True)
    def connect(self):
        deadline=time.monotonic()+70
        while port_free(self.port):
            if self.s.sitl.poll() is not None:raise RuntimeError('SITL exited: '+str(self.s.run/'sitl.log'))
            if time.monotonic()>deadline:raise RuntimeError('Owned SITL TCP5760 not ready')
            time.sleep(.2)
        self.link=mavutil.mavlink_connection('tcp:127.0.0.1:'+str(self.port),source_system=254 if self.port==5762 else 255,source_component=190,autoreconnect=False)
        self.until(lambda:'HEARTBEAT' in self.last,20)
        self.system=self.last['HEARTBEAT'].get_srcSystem();self.component=1
        self.link.mav.request_data_stream_send(self.system,self.component,mavutil.mavlink.MAV_DATA_STREAM_ALL,10,1)
        self.link.mav.param_request_list_send(self.system,self.component)
        self.until(lambda:len(self.params)>200 and len(self.params)>=getattr(self.last.get('PARAM_VALUE'),'param_count',100000),35,strict=False)
        (self.s.run/'parameters.json').write_text(json.dumps(self.params,indent=2))
        self.event('connected',params=len(self.params),firmware_texts=[x for x in self.events if x['event']=='status_text'][:8])
    def tick(self):
        now=time.time()
        if now-self.last_heartbeat>=1:
            self.link.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS,mavutil.mavlink.MAV_AUTOPILOT_INVALID,0,0,0)
            self.last_heartbeat=now
        items=[]
        for _ in range(500):
            msg=self.link.recv_match(blocking=False)
            if msg is None:break
            typ=msg.get_type();self.last[typ]=msg;self.messages[typ]+=1;items.append(msg)
            if typ=='STATUSTEXT':
                text=msg.text.rstrip('\0')
                self.event('status_text',severity=msg.severity,text=text)
            elif typ=='COMMAND_ACK':self.acks.append(msg.to_dict())
            elif typ=='PARAM_VALUE':self.params[str(msg.param_id).rstrip('\0')]=msg.param_value
            elif typ=='MISSION_CURRENT':
                if self.current_seq!=msg.seq:self.event('mission_current',seq=msg.seq)
                self.current_seq=msg.seq
                self.max_seq=max(self.max_seq,msg.seq)
            elif typ=='CAMERA_FEEDBACK':self.photos.append({'wall_time':now,**safe(msg.to_dict())})
        hb=self.last.get('HEARTBEAT');pos=self.last.get('GLOBAL_POSITION_INT');att=self.last.get('ATTITUDE');servo=self.last.get('SERVO_OUTPUT_RAW')
        if hb and pos and now-self.last_sample>=.2:
            armed=bool(hb.base_mode&mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED);self.armed_once|=armed
            alt=pos.relative_alt/1000;self.maxalt=max(self.maxalt,alt)
            self.telemetry.append({'wall_time':now,'boot_s':pos.time_boot_ms/1000,'latitude':pos.lat/1e7,'longitude':pos.lon/1e7,
                                   'altitude_m':alt,'vx':pos.vx/100,'vy':pos.vy/100,'vz':pos.vz/100,'heading_deg':pos.hdg/100,
                                   'mode':hb.custom_mode,'armed':armed,'seq':self.current_seq,
                                   'roll':getattr(att,'roll',0),'pitch':getattr(att,'pitch',0),'yaw':getattr(att,'yaw',0),
                                   'pump_pwm':getattr(servo,'servo12_raw',0),'gimbal_pitch_pwm':getattr(servo,'servo10_raw',0),'gimbal_yaw_pwm':getattr(servo,'servo11_raw',0)})
            self.last_sample=now
            with (self.s.run/'telemetry.jsonl').open('a') as stream:stream.write(json.dumps(self.telemetry[-1])+'\n')
        return items
    def until(self,condition,seconds,strict=True):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.tick()
            if condition():return True
            for p in self.s.processes:
                if p.poll() is not None:raise RuntimeError('Owned simulator process exited: '+str(p.pid))
            time.sleep(.02)
        if strict:raise TimeoutError('Condition not met after '+str(seconds)+' s')
        return False
    def ready(self):
        def ok():
            g=self.last.get('GPS_RAW_INT');e=self.last.get('EKF_STATUS_REPORT');p=self.last.get('GLOBAL_POSITION_INT')
            ss=self.last.get('SYS_STATUS');flag=1<<28
            checks=ss and (bool(ss.onboard_control_sensors_health&flag) if ss.onboard_control_sensors_present&flag else p is not None and p.time_boot_ms>=32000)
            return g and g.fix_type>=3 and e and e.flags&55==55 and p and p.lat!=0 and p.time_boot_ms>=22000 and checks
        self.until(ok,100)
        self.event('navigation_ready',gps=self.last['GPS_RAW_INT'].to_dict(),ekf=self.last['EKF_STATUS_REPORT'].to_dict(),system_health=self.last['SYS_STATUS'].to_dict())
    def upload(self,mission):
        items=mission['items'];self.link.mav.mission_count_send(self.system,self.component,len(items),0)
        received=set();deadline=time.monotonic()+45;accepted=False
        while time.monotonic()<deadline:
            for msg in self.tick():
                if msg.get_type() in ('MISSION_REQUEST','MISSION_REQUEST_INT'):
                    a=items[msg.seq];received.add(msg.seq)
                    self.link.mav.mission_item_int_send(self.system,self.component,a['seq'],a['frame'],a['command'],1 if a['seq']==0 else 0,1,*a['params'],round(a['latitude']*1e7),round(a['longitude']*1e7),a['altitude'],0)
                elif msg.get_type()=='MISSION_ACK':
                    if msg.type!=mavutil.mavlink.MAV_MISSION_ACCEPTED:raise RuntimeError('Mission rejected '+str(msg.type))
                    accepted=True
            if accepted:break
            time.sleep(.02)
        if not accepted or len(received)!=len(items):raise RuntimeError('Incomplete mission upload')
        self.event('mission_uploaded',count=len(items),all_items_requested=True)
        self.link.mav.mission_set_current_send(self.system,self.component,1)
        self.until(lambda:self.current_seq==1,10)
    def command(self,cmd,*params):
        p=list(params)+[0]*(7-len(params));self.sent.append({'wall_time':time.time(),'command':cmd,'params':p})
        self.link.mav.command_long_send(self.system,self.component,cmd,0,*p)
    def start_auto(self,plane):
        mode=10 if plane else 3
        self.link.mav.set_mode_send(self.system,mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,mode)
        self.until(lambda:self.last['HEARTBEAT'].custom_mode==mode,15)
        for attempt in range(4):
            self.command(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,1)
            if self.until(lambda:bool(self.last['HEARTBEAT'].base_mode&128),8,strict=False):break
            self.event('arming_retry',attempt=attempt+1)
        if not self.last['HEARTBEAT'].base_mode&128:raise RuntimeError('Normal (unforced) arming was rejected')
        self.command(mavutil.mavlink.MAV_CMD_MISSION_START,1,0)
        self.event('auto_started',mode=mode,force_arm=False,route_setpoints_sent=False)
    def observe(self,plane,lastseq,timeout):
        expected=10 if plane else 3
        lastprint=time.monotonic();wrongmode_since=None
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            self.tick();hb=self.last['HEARTBEAT'];armed=bool(hb.base_mode&128)
            if armed and hb.custom_mode!=expected:
                wrongmode_since=wrongmode_since or time.monotonic()
                if time.monotonic()-wrongmode_since>4:raise RuntimeError('Vehicle left AUTO while armed')
            else:wrongmode_since=None
            if self.telemetry and abs(self.telemetry[-1]['altitude_m'])>180:raise RuntimeError('Unexpected simulation altitude')
            if plane and self.maxalt<3 and self.telemetry:
                pos=self.telemetry[-1];north=(pos['latitude']+35.363262)*111319.49;east=(pos['longitude']-149.165237)*111319.49*math.cos(math.radians(-35.363262))
                if math.hypot(north,east)>200:raise RuntimeError('Runway takeoff travelled 200m without climbing; revise airframe/rotation setup')
            if self.armed_once and not armed and self.maxalt>2 and self.max_seq>=lastseq:
                if abs(self.telemetry[-1]['altitude_m'])>1:raise RuntimeError('Disarmed above ground')
                self.last_sample=0;self.tick()
                self.event('auto_landed',final_seq=self.max_seq,post_disarm_seq=self.current_seq,max_altitude=self.maxalt,camera_events=len(self.photos));return
            if self.armed_once and not armed and self.maxalt>2 and self.max_seq<lastseq:raise RuntimeError('Disarmed before finishing mission')
            if time.monotonic()-lastprint>12:
                progress={'progress':self.current_seq,'altitude':round(self.telemetry[-1]['altitude_m'],2) if self.telemetry else None,'photos':len(self.photos),'armed':armed}
                print(('Gorev satiri: '+str(progress['progress'])+' | Irtifa: '+str(progress['altitude'])+'m | Fotograf: '+str(progress['photos'])) if os.environ.get('UAV_COURSE_STUDENT')=='1' else json.dumps(progress),flush=True);lastprint=time.monotonic();self.save()
            if any(p.poll() is not None for p in self.s.processes):raise RuntimeError('Simulator process stopped during AUTO')
            time.sleep(.025)
        raise TimeoutError('AUTO mission did not complete in '+str(timeout)+' seconds')
    def harvest(self):
        meta=self.s.run/'camera.jsonl'
        frames=[json.loads(line) for line in meta.read_text().splitlines() if line.strip()] if meta.exists() else []
        photos=self.s.run/'photos';photos.mkdir(exist_ok=True);selected=[]
        for event in self.photos:
            if not frames:break
            frame=min(frames,key=lambda f:abs(f['wall_time']-event['wall_time']))
            delta=abs(frame['wall_time']-event['wall_time'])
            if delta>1:continue
            name=f"{len(selected):04d}.png";shutil.copy2(self.s.run/frame['frame'],photos/name)
            selected.append({**frame,'photo':'photos/'+name,'camera_feedback':event,'event_frame_wall_delta_s':delta})
        (self.s.run/'photo_manifest.json').write_text(json.dumps(selected,indent=2))
        self.event('photos_matched',feedback_events=len(self.photos),actual_gazebo_photos=len(selected),max_wall_delta_s=max((r['event_frame_wall_delta_s'] for r in selected),default=None))
        return selected
    def save(self):
        d={'status':self.status,'scenario':self.s.scenario,'platform':'native Windows','events':self.events,'telemetry':self.telemetry,'camera_feedback':self.photos,'mavlink_message_counts':dict(self.messages),'gcs_command_longs':self.sent,'gcs_flight_setpoints_sent':0,'max_altitude_m':self.maxalt,'max_mission_seq':self.max_seq,'force_arm_used':False}
        (self.s.run/'flight.json').write_text(json.dumps(safe(d),indent=2),encoding='utf-8')
    def close(self):
        self.save()
        if self.link:self.link.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('scenario',choices=MISSIONS);p.add_argument('--gui',action='store_true');p.add_argument('--dry-run',action='store_true');p.add_argument('--timeout',type=int);p.add_argument('--observe-only',action='store_true');p.add_argument('--vision',action='store_true');a=p.parse_args()
    if a.vision and (a.scenario!='plane' or a.dry_run):p.error('--vision requires a Plane mission')
    s=Session(a.scenario,a.gui);g=GCS(s,5762 if a.observe_only else 5760);vision=None
    try:
        s.start();g.connect();g.ready()
        if a.dry_run:
            g.until(lambda:False,10,strict=False);g.status='ground_camera_check_passed';g.event('ground_check',camera_frames=len(list((s.run/'camera').glob('*.png'))))
        else:
            mission=json.loads((ROOT/'missions'/f'{MISSIONS[a.scenario]}.json').read_text());(s.run/'mission.json').write_text(json.dumps(mission,indent=2))
            if a.vision:
                with (s.run/'vision-console.log').open('w') as log:vision=subprocess.Popen([sys.executable,str(ROOT/'tools/motion_detect.py'),str(s.run),'--follow'],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            if a.observe_only:
                g.event('waiting_for_mission_planner',connect='TCP127.0.0.1:5760',observer_commands_sent=0)
                g.until(lambda:bool(g.last['HEARTBEAT'].base_mode&128) and g.last['HEARTBEAT'].custom_mode==(10 if a.scenario=='plane' else 3),900)
                g.event('operator_started_auto',observer_commands_sent=0)
            else:g.upload(mission);g.start_auto(a.scenario=='plane')
            g.observe(a.scenario=='plane',len(mission['items'])-1,a.timeout or (1200 if a.scenario=='plane' else 650))
            images=g.harvest()
            if a.scenario in ('mapping','building') and len(images)<12:raise RuntimeError('Too few real camera-trigger images')
            g.status='auto_mission_passed'
            g.save()
            if vision is not None and vision.wait(timeout=120)!=0:raise RuntimeError('Flight landed but image processing validation failed; inspect vision-console.log')
    except BaseException as ex:
        g.status='failed';g.event('failure',error=str(ex),trace=traceback.format_exc());raise
    finally:
        if vision is not None and vision.poll() is None:vision.terminate();vision.wait(timeout=10)
        g.close();s.close();print('RESULT='+str(s.run/'flight.json'),flush=True)
if __name__=='__main__':main()
