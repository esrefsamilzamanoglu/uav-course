"""Own local Gazebo/SITL processes; never connect to an external vehicle."""
from __future__ import annotations
import argparse, contextlib, datetime as dt, hashlib, json, os, shutil, socket
import subprocess, time, xml.etree.ElementTree as E
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
LOCAL=ROOT/'.local'
PARTITION='uav_course_week2'

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def native_config():
    options=[(REPO/'windows/.pixi/envs/default',REPO/'windows/pixi.toml',REPO/'windows/.local/ardupilot_gazebo',REPO/'windows/.local/sitl')]
    options.append((Path.home()/'gz-ws/.pixi/envs/default',Path.home()/'gz-ws/pixi.toml',REPO/'gazebo_windows/ardupilot_gazebo',REPO/'gazebo_windows/sitl_native'))
    for prefix,manifest,source,sitl in options:
        if (prefix/'python.exe').is_file() and (source/'build-windows/ArduPilotPlugin.dll').is_file() and (sitl/'ArduCopter.exe').is_file():
            pixi=shutil.which('pixi') or str(Path.home()/'.pixi/bin/pixi.exe')
            return {'prefix':prefix,'manifest':manifest,'source':source,'sitl':sitl,'pixi':Path(pixi),'plugin':source/'build-windows'}
    raise RuntimeError('Once ilk haftanin native Windows kurulumunu tamamlayin.')

def environment(c):
    e=os.environ.copy();prefix=c['prefix']/'Library'
    e.update(GZ_PARTITION=PARTITION,GZ_VERSION='jetty',
             GZ_SIM_SYSTEM_PLUGIN_PATH=os.pathsep.join([str(LOCAL/'build'),str(c['plugin'])]),
             GZ_SIM_RESOURCE_PATH=os.pathsep.join([str(ROOT/'models'),str(c['source']/'models')]),
             QT_QPA_PLATFORM_PLUGIN_PATH=str(prefix/'lib/qt6/plugins/platforms'),
             QML2_IMPORT_PATH=str(prefix/'lib/qt6/qml'),QT_PLUGIN_PATH=str(prefix/'lib/qt6/plugins'))
    e['PATH']=os.pathsep.join([str(prefix/'bin'),str(c['prefix']),str(c['sitl']),e.get('PATH','')])
    return e

def prepare():
    c=native_config();LOCAL.mkdir(exist_ok=True);(LOCAL/'worlds').mkdir(exist_ok=True);(LOCAL/'params').mkdir(exist_ok=True)
    for f in (ROOT/'worlds').glob('*.sdf'):
        tree=E.parse(f)
        for tag in ('mesh/uri','albedo_map'):
            for node in tree.getroot().findall('.//'+tag):
                uri=(node.text or '').strip()
                if uri.startswith('model://'):
                    relative=uri[8:];matches=[p/relative for p in (ROOT/'models',c['source']/'models') if (p/relative).is_file()]
                    if len(matches)!=1:raise RuntimeError('Kaynak bulunamadi: '+uri)
                    node.text=matches[0].resolve().as_posix()
        E.indent(tree,space='  ');tree.write(LOCAL/'worlds'/f.name,encoding='utf-8',xml_declaration=True)
    # Official Windows Plane binary and its shared runtime; no existing SITL cache is changed.
    plane=LOCAL/'sitl/plane';plane.mkdir(parents=True,exist_ok=True)
    source=LOCAL/'research/ArduPlane.exe'
    if not source.is_file():raise RuntimeError('Resmi ArduPlane indirmesi eksik.')
    if digest(source)!='8efc03f8c72433ef19db028f0c59a62ff3b48a67b680d94bed084b5e19fb798c':raise RuntimeError('ArduPlane surumu degismis.')
    shutil.copy2(source,plane/'ArduPlane.exe')
    for dll in c['sitl'].glob('*.dll'):shutil.copy2(dll,plane/dll.name)
    copter=(c['sitl']/'default_params/copter.parm').read_text()
    copter+='\n'+(c['sitl']/'default_params/gazebo-iris.parm').read_text()
    (LOCAL/'params/copter-base.parm').write_text(copter)
    shutil.copy2(LOCAL/'research/gazebo-zephyr.parm',LOCAL/'params/plane-base.parm')
    camera='''
# Course ideal servo gimbal and servo shutter; all are real ArduPilot outputs.
MNT1_TYPE 1
MNT1_DEFLT_MODE 1
MNT1_PITCH_MIN -90
MNT1_PITCH_MAX 0
MNT1_ROLL_MIN -30
MNT1_ROLL_MAX 30
MNT1_YAW_MIN -180
MNT1_YAW_MAX 180
MNT1_NEUTRAL_X 0
MNT1_NEUTRAL_Y -90
MNT1_NEUTRAL_Z 0
SERVO9_FUNCTION 8
SERVO10_FUNCTION 7
SERVO11_FUNCTION 6
SERVO9_MIN 1000
SERVO9_MAX 2000
SERVO10_MIN 1000
SERVO10_MAX 2000
SERVO11_MIN 1000
SERVO11_MAX 2000
CAM1_TYPE 1
CAM1_FEEDBAK_PIN -1
CAM1_DURATION 0.1
CAM1_SERVO_ON 1900
CAM1_SERVO_OFF 1100
CAM1_INTRVAL_MIN 0.3
SERVO13_FUNCTION 10
CAM_AUTO_ONLY 1
LOG_DISARMED 1
FS_GCS_ENABLE 0
'''
    common=camera+'''
AUTO_OPTIONS 3
WP_YAW_BEHAVIOR 0
WP_SPD 4.5
WP_ACC 1.5
WP_RADIUS_M 1
RTL_ALT_M 18
SPRAY_ENABLE 1
SERVO12_FUNCTION 22
SERVO12_MIN 1000
SERVO12_MAX 2000
SPRAY_PUMP_RATE 20
SPRAY_PUMP_MIN 10
SPRAY_SPEED_MIN 50
PLND_ENABLED 0
'''
    plane_parms=camera.replace('MNT1_NEUTRAL_Y -90','MNT1_NEUTRAL_Y -55')+'''
SERVO3_MIN 1100
SERVO3_MAX 1900
SERVO3_TRIM 1100
SERVO1_MIN 1100
SERVO1_MAX 1900
SERVO2_MIN 1100
SERVO2_MAX 1900
TKOFF_THR_MINACC 0
TKOFF_THR_MINSPD 0
TKOFF_THR_DELAY 0
TKOFF_ROTATE_SPD 0
TKOFF_THR_MAX 100
TKOFF_THR_SLEW 100
TKOFF_TDRAG_ELEV 0
LAND_FLARE_ALT 2
LAND_FLARE_SEC 2
LAND_PITCH_DEG 5
LAND_DISARMDELAY 5
RTL_AUTOLAND 2
WP_RADIUS 35
ROLL_LIMIT_DEG 45
AIRSPEED_CRUISE 17
TECS_SINK_MAX 5
'''
    (ROOT/'params').mkdir(exist_ok=True)
    (ROOT/'params/copter-course.parm').write_text(common)
    (ROOT/'params/plane-course.parm').write_text(plane_parms)
    (LOCAL/'runtime.json').write_text(json.dumps({k:str(v) for k,v in c.items()},indent=2))
    print('Native runtime/world paths prepared.',flush=True)
    return c

def port_free(port,kind=socket.SOCK_STREAM):
    if os.name=='nt' and kind==socket.SOCK_STREAM:
        # Winsock permits a specific-address bind beside Cygwin's wildcard
        # SO_REUSEADDR listener. Inspect LISTEN sockets without connecting.
        import ctypes
        from ctypes import wintypes
        class Row(ctypes.Structure):
            _fields_=[(name,wintypes.DWORD) for name in ('state','local_addr','local_port','remote_addr','remote_port','pid')]
        api=ctypes.WinDLL('iphlpapi').GetExtendedTcpTable
        size=wintypes.ULONG(0);api(None,ctypes.byref(size),True,socket.AF_INET,3,0)
        buf=ctypes.create_string_buffer(size.value)
        if api(buf,ctypes.byref(size),True,socket.AF_INET,3,0)!=0:raise OSError('Cannot inspect local TCP listeners')
        count=ctypes.cast(buf,ctypes.POINTER(wintypes.DWORD)).contents.value
        for i in range(count):
            row=Row.from_buffer_copy(buf,4+i*ctypes.sizeof(Row))
            if socket.ntohs(row.local_port&65535)==port:return False
        return True
    with socket.socket(socket.AF_INET,kind) as s:
        if os.name=='nt':s.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        try:s.bind(('127.0.0.1',port));return True
        except OSError:return False

def stop_tree(p):
    if p is None or p.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:p.terminate()
    with contextlib.suppress(subprocess.TimeoutExpired):p.wait(timeout=8)

class Session:
    def __init__(self,scenario,gui=False,run_name=None):
        self.scenario=scenario;self.world={'intro':'farm','spray':'farm','mapping':'farm','building':'building','plane':'rural','camera':'farm'}[scenario]
        self.gui=gui;self.config=native_config();self.env=environment(self.config);self.processes=[]
        stamp=dt.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.run=LOCAL/'runs'/(run_name or f'{stamp}-{scenario}')
        self.run.mkdir(parents=True,exist_ok=False)
        (self.run/'sitl').mkdir()
        self.started=time.time()
    def launch(self,args,log,cwd=None):
        with (self.run/log).open('w') as out:
            p=subprocess.Popen([str(a) for a in args],stdout=out,stderr=subprocess.STDOUT,cwd=cwd or ROOT,env=self.env,
                               stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        self.processes.append(p);return p
    def start(self,sitl=True):
        if not port_free(5760) or not port_free(9002,socket.SOCK_DGRAM):raise RuntimeError('5760/9002 kullanimda; mevcut oturumu kapatin.')
        c=self.config
        self.bridge=self.launch([LOCAL/'build/course_camera_bridge.exe',self.run],'bridge.log')
        command=[c['pixi'],'run','--manifest-path',c['manifest'],'gz','sim','-r','-v3']
        if not self.gui:command+=['-s']
        else:
            default=(c['prefix']/'Library/share/gz/gz-sim/gui/gui.config').read_text()
            import re
            pose={'farm':'73 -45 76 0 0.602 2.292','building':'75 -30 60 0 0.46 2.35','rural':'320 -250 310 0 0.55 2.2'}[self.world]
            default=re.sub(r'<camera_pose>[^<]+</camera_pose>','<camera_pose>'+pose+'</camera_pose>',default)
            (self.run/'gui.config').write_text(default);command+=['--gui-config',self.run/'gui.config']
        self.gz=self.launch(command+[LOCAL/'worlds'/f'{self.world}.sdf'],'gazebo.log')
        deadline=time.monotonic()+90
        while port_free(9002,socket.SOCK_DGRAM):
            if self.gz.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Gazebo baslatilamadi: '+str(self.run/'gazebo.log'))
            time.sleep(.3)
        if sitl:
            plane=self.scenario=='plane'
            binary=LOCAL/'sitl/plane/ArduPlane.exe' if plane else c['sitl']/'ArduCopter.exe'
            defaults=[LOCAL/'params'/('plane-base.parm' if plane else 'copter-base.parm'),ROOT/'params'/('plane-course.parm' if plane else 'copter-course.parm')]
            self.sitl=self.launch([binary,'--model','JSON','--speedup','1','--defaults',','.join(p.as_posix() for p in defaults),'--serial0','tcp:0','--base-port','5760','--sim-address','127.0.0.1','--sim-port-out','9002','--home','-35.363262,149.165237,584,0'], 'sitl.log',self.run/'sitl')
        rgb=E.parse(LOCAL/'worlds'/f'{self.world}.sdf').getroot().find("./world/model[@name='course_camera']/link/sensor/camera")
        (self.run/'camera_calibration.json').write_text(json.dumps({'horizontal_fov':float(rgb.findtext('horizontal_fov')),'width':int(rgb.findtext('image/width')),'height':int(rgb.findtext('image/height'))},indent=2))
        (self.run/'session.json').write_text(json.dumps({'scenario':self.scenario,'platform':'native Windows','world':self.world,'world_sha256':digest(LOCAL/'worlds'/f'{self.world}.sdf'),'started':self.started,'own_pids':[p.pid for p in self.processes],'gui':self.gui},indent=2))
        print('SESSION='+str(self.run),flush=True)
        return self
    def close(self):
        for p in reversed(self.processes):stop_tree(p)
    def __enter__(self):return self.start()
    def __exit__(self,*_):self.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','camera']);p.add_argument('--gui',action='store_true');a=p.parse_args()
    if a.action=='prepare':prepare()
    else:
        s=Session('camera',a.gui)
        try:
            s.start(sitl=False);time.sleep(35)
            frames=list((s.run/'camera').glob('*.png'));over=list((s.run/'overview').glob('*.png'))
            print(json.dumps({'camera_frames':len(frames),'overview_frames':len(over),'run':str(s.run)}),flush=True)
            if not frames or not over:raise RuntimeError('Gercek kamera goruntusu eksik.')
        finally:s.close()
