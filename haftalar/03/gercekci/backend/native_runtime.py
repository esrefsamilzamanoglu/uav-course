"""Launch only owned native Gazebo/ArduPilot/bridge processes on localhost."""
from pathlib import Path
import datetime as dt,hashlib,json,os,socket,subprocess,sys,time

BASE=Path(__file__).resolve().parents[1];REPO=BASE.parents[2]
sys.path.insert(0,str(REPO/'haftalar/02/simulasyon/tools'))
from runtime import native_config,environment,port_free,stop_tree

class NativeRuntime:
    def __init__(self,event):
        self.event=event;self.processes=[];self.run=None;self.env=None;self.running=False
        self.status='stopped';self.error=None;self.gui=False
    def start(self,gui=False):
        if self.running:raise RuntimeError('Simülasyon zaten açık')
        if not all(port_free(p) for p in (5760,5762)) or not port_free(9002,socket.SOCK_DGRAM):raise RuntimeError('5760 / 5762 / 9002 kullanımda. Açık simülasyonu kapatın.')
        self.status='starting';self.gui=gui;self.error=None
        c=native_config();self.run=BASE/'.local/runs'/dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.run.mkdir(parents=True,exist_ok=False)
        plugin=BASE/'plugin/.local/build';bridge=plugin/'realistic_bridge.exe'
        if not (plugin/'PayloadMechanics.dll').is_file() or not bridge.is_file():raise RuntimeError('Önce gerçekçi laboratuvarın Kur.cmd dosyasını çalıştırın: yerel Gazebo eklentisi eksik.')
        self.env=environment(c);self.env['GZ_PARTITION']='uav_course_realistic_'+str(os.getpid())
        self.env['GZ_SIM_SYSTEM_PLUGIN_PATH']=os.pathsep.join([str(plugin),str(c['plugin'])])
        self.env['GZ_SIM_RESOURCE_PATH']=os.pathsep.join([str(BASE/'models'),str(c['source']/'models'),str(REPO/'haftalar/02/simulasyon/models')])
        generator=BASE/'world/build_world.py'
        subprocess.run([sys.executable,str(generator),'--out',str(self.run/'competition.sdf'),'--source',str(c['source']),'--plugin-path',str(plugin)],check=True,env=self.env,cwd=BASE)
        defaults=(c['sitl']/'default_params/copter.parm').read_text()+'\n'+(c['sitl']/'default_params/gazebo-iris.parm').read_text()
        defaults+='''\n# Actual servo outputs are consumed by the native ArduPilot Gazebo COMMAND controls.
SERVO9_FUNCTION 0
SERVO10_FUNCTION 0
SERVO9_MIN 1000
SERVO9_MAX 2000
SERVO9_TRIM 1900
SERVO10_MIN 1000
SERVO10_MAX 2000
SERVO10_TRIM 1900
AUTO_OPTIONS 3
PLND_ENABLED 0
WP_SPD 6
WP_ACC 2
WP_JERK 4
WP_RADIUS_M 1.5
WP_YAW_BEHAVIOR 0
LOG_DISARMED 1
# Separate MAVLink2 UART for Mission Planner; failsafe follows ROTA (system 253).
SERIAL1_PROTOCOL 2
SIM_ADSB_COUNT -1
MAV_GCS_SYSID 253
MAV_GCS_SYSID_HI 0
MAV_OPTIONS 0
FS_GCS_ENABLE 5
FS_GCS_TIMEOUT 5
LAND_SPEED 40
'''
        params=self.run/'competition.parm';params.write_text(defaults,encoding='ascii')
        self.launch([bridge,'--output-dir',self.run/'bridge','--udp-port','9109'],'bridge.log')
        cmd=[c['pixi'],'run','--manifest-path',c['manifest'],'gz','sim','-r','-v3']
        if not gui:cmd.append('-s')
        self.gz=self.launch(cmd+[self.run/'competition.sdf'],'gazebo.log')
        deadline=time.monotonic()+100
        while port_free(9002,socket.SOCK_DGRAM):
            if self.gz.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Gazebo başlatılamadı; gazebo.log dosyasını inceleyin.')
            time.sleep(.25)
        working=self.run/'sitl';working.mkdir()
        self.sitl=self.launch([c['sitl']/'ArduCopter.exe','--model','JSON','--speedup','1','--defaults',params.resolve().as_posix(),
                               '--serial0','tcp:0','--serial1','tcp:5762','--base-port','5760','--sim-address','127.0.0.1','--sim-port-out','9002',
                               '--home','-35.363262,149.165237,584,0'],'sitl.log',working)
        deadline=time.monotonic()+30
        while any(port_free(p) for p in (5760,5762)):
            if self.sitl.poll() is not None or time.monotonic()>deadline:raise RuntimeError('ArduPilot MAVLink portları açılamadı; sitl.log dosyasını inceleyin.')
            time.sleep(.25)
        self.running=True;self.status='running'
        (self.run/'provenance.json').write_text(json.dumps(dict(owned_pids=[p.pid for p in self.processes],partition=self.env['GZ_PARTITION'],
                   hashes={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in {
                       'world_sdf':self.run/'competition.sdf','payload_mechanics':plugin/'PayloadMechanics.dll','rgb_bridge':bridge,
                       'ArduCopter':c['sitl']/'ArduCopter.exe','quad_model':BASE/'models/competition_quad/model.sdf'}.items()},
                   camera='Actual Gazebo rendering',payload='DART joints, masses, inertia and collision',servo_path='MAVLink → ArduPilot → native JSON servo output → Gazebo COMMAND → gated detachable joint'),indent=2),encoding='utf-8')
        self.event('info','Gazebo ve ArduPilot hazır · Mission Planner: TCP 127.0.0.1:5762')
        return self.run
    def launch(self,args,name,cwd=None):
        with (self.run/name).open('w',encoding='utf-8') as out:
            p=subprocess.Popen([str(a) for a in args],cwd=cwd or BASE,env=self.env,stdin=subprocess.DEVNULL,stdout=out,stderr=subprocess.STDOUT,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.processes.append(p);return p
    def close(self):
        for p in reversed(self.processes):stop_tree(p)
        self.processes=[];self.running=False;self.status='stopped'
        self.event('info','Simülasyon oturumu kapatıldı')
