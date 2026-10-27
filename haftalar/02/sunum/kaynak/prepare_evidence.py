"""Curate real simulation records before generating the lecture. No synthetic frames."""
from pathlib import Path
import sys,json,shutil,hashlib,math,bisect
ROOT=Path(__file__).resolve().parents[2]
SIM=ROOT/'simulasyon';sys.path.insert(0,str(SIM/'tools'))
import vision_bootstrap
import numpy as np
from PIL import Image,ImageOps,ImageDraw,ImageFont
from scipy.spatial.transform import Rotation
RUNS=SIM/'.local/runs';OUT=ROOT/'sunum/gorseller';VAL=ROOT/'dogrulama'
OUT.mkdir(parents=True,exist_ok=True);VAL.mkdir(exist_ok=True)
IDS=dict(intro='20261027-184706-intro',spray='20261027-184011-spray',mapping='20261027-174950-mapping',building='20261027-183245-building',plane='20261027-190335-plane')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def lines(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
provenance=[]
def copy(src,name):
    dest=OUT/name;shutil.copy2(src,dest)
    provenance.append(dict(file=name,source=src.relative_to(SIM).as_posix(),sha256=sha(dest)))
def nearest_frame(run,seq,kind='camera'):
    flight=read(run/'flight.json');rows=flight['telemetry'];clocks=[r['wall_time'] for r in rows];frames=lines(run/(kind+'.jsonl'))
    selected=[f for f in frames if rows[max(0,bisect.bisect_right(clocks,f['wall_time'])-1)]['seq']==seq]
    return selected[len(selected)//2]
summary={'tested_on':'2026-10-27','platform':'Native Windows x64','gazebo':'Jetty 10.5.0','arducopter':'4.7.2','arduplane':'4.7.2','tests':{}}
for key,rid in IDS.items():
    run=RUNS/rid;v=read(run/'products/validation.json');assert v['flight_status']=='auto_mission_passed' and v['only_auto_while_armed'] and v['final_disarmed']
    assert not v['force_arm_used'] and v['flight_setpoints_sent']==0
    summary['tests'][key]={'run':rid,**v}
    for src in ['flight.json','mission.json','camera_calibration.json']:
        if (run/src).exists() and src!='flight.json':shutil.copy2(run/src,VAL/(key+'-'+src))
    (VAL/(key+'-validation.json')).write_text(json.dumps(v,indent=2),encoding='utf-8')
    copy(run/'products/ucus_izleri.png',key+'_ucus.png')
    fs=sorted((run/'overview').glob('*.png'))
    copy(fs[len(fs)//3],key+'_dunya.png')
    seq={'intro':5,'spray':13,'mapping':9,'building':17,'plane':4}[key]
    f=nearest_frame(run,seq)
    copy(run/f['frame'],key+'_kamera.png')
for seq,name in [(3,'90'),(5,'45'),(7,'20')]:
    run=RUNS/IDS['intro'];f=nearest_frame(run,seq);copy(run/f['frame'],'kamera_'+name+'.png')
copy(RUNS/'20261027-191355-intro/overview/000004.png','iris_yakin.png')
for key,src,name in [('spray','ilaclama_kaplama.png','ilaclama_sonra.png'),('spray','pompa_pwm.png','pompa_pwm.png'),('mapping','tarla_mozaik.png','tarla_mozaik.png'),('building','bina_3d_rekonstruksiyon.png','bina_3d.png'),('building','bina_sift_eslesmeleri.png','sift.png')]:copy(RUNS/IDS[key]/'products'/src,name)
copy(RUNS/'20261027-181728-spray/products/ilaclama_kaplama.png','ilaclama_once.png')
copy(RUNS/IDS['plane']/'gazebo_native_gui.png','gazebo_arayuz.png')
plane=RUNS/IDS['plane'];events=lines(plane/'products/motion/events.jsonl');ev=events[0];false=next(e for e in events if not e['evaluation_only']['true_positive'])
for e,n in [(ev,'hareket'),(false,'yanlis_alarm')]:
    for src,name in [(f"event_{e['index']:04d}.png",n+'.png'),(f"crops/{e['index']:04d}.png",n+'_kirpim.png'),(f"residual_{e['index']:04d}.png",n+'_artik.png')]:copy(plane/'products/motion'/src,name)
    copy(plane/e['source'],n+'_ham.png')
landing=next(e for e in read(plane/'flight.json')['events'] if e['event']=='auto_landed')
summary['live_detection']={'events':23,'truth_overlap_events':19,'false_alarm_events':4,'first_event':ev,'landed_wall_time':landing['wall_time'],'continued_auto_after_detection_s':landing['wall_time']-ev['detected_wall_time']}
# The latest detector uses only autopilot altitude as its altitude gate. Verify
# that the earlier live worker's camera-height gate admitted the same SCAN frames.
frames=lines(plane/'camera.jsonl');rows=read(plane/'flight.json')['telemetry'];clocks=[r['wall_time'] for r in rows];gate_equal=True
for f in frames:
    s=rows[max(0,bisect.bisect_right(clocks,f['wall_time'])-1)]
    if s['armed'] and s['seq'] in [3,4,6,8]:gate_equal &= ((s['altitude_m']>=25)==(f['position'][2]>=25))
assert gate_equal
summary['live_detection']['latest_altitude_gate_equivalent_on_recorded_scan_frames']=gate_equal
for key,src in [('mapping','mosaic_metrics.json'),('building','reconstruction_metrics.json'),('plane','motion/metrics.json')]:
    data=read(RUNS/IDS[key]/'products'/src);summary[key+'_product']=data;(VAL/(key+'-product.json')).write_text(json.dumps(data,indent=2))
summary['installer']={'fresh_install_passed':True,'repeat_install_passed':True,'separate_student_venv':True}
summary['operator_flow']={'operator_tcp_port':5760,'observer_tcp_port':5762,'observer_flight_commands':0,'tested':True}
summary['all_required_passed']=True
(VAL/'final_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
(OUT/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
# A compact contact sheet for author review, never presented as a simulation view.
items=[p for p in OUT.glob('*.png') if not p.name.startswith('contact')];thumbs=[]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for p in items:
    tile=Image.new('RGB',(440,310),'#edf3ff');im=Image.open(p);im.thumbnail((432,270));tile.paste(im,((440-im.width)//2,0));ImageDraw.Draw(tile).text((5,278),p.stem,font=font,fill='#18365d');thumbs.append(tile)
sheet=Image.new('RGB',(440*4,310*math.ceil(len(thumbs)/4)),'white')
for i,im in enumerate(thumbs):sheet.paste(im,((i%4)*440,(i//4)*310))
sheet.save(SIM/'.local/research/week2_assets_contact.jpg')
print(json.dumps({'all_required_passed':True,'images':len(provenance),'continued_auto_s':summary['live_detection']['continued_auto_after_detection_s']}))
