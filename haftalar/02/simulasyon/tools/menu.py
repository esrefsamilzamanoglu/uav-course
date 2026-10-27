"""Student launcher: the operator starts AUTO in Mission Planner."""
import os,subprocess,sys
from pathlib import Path
items={'0':('intro','Kamera ve arac tanitimi','00_kamera_tanitimi.waypoints'),'1':('spray','Tarla ilaclama','01_tarla_ilaclama.waypoints'),'2':('mapping','2D tarla haritalama','02_tarla_2d_haritalama.waypoints'),'3':('building','3D bina haritalama','03_bina_3d_haritalama.waypoints'),'4':('plane','Sabit kanat gozetim','04_sabit_kanat_gozetim.waypoints')}
for key,(_,label,_) in items.items():print(key+' - '+label)
choice=input('Uygulama numarasi: ').strip()
if choice not in items:raise SystemExit('Gecersiz secim.')
scenario,_,mission=items[choice];root=Path(__file__).resolve().parents[1]
print('\nMission Planner: TCP -> 127.0.0.1 -> 5760')
print('Plan ekraninda su gorevi acin ve araca yazin: '+str(root/'missions'/mission))
print('Sensorler hazir olunca AUTO secin ve ARM edin. Bu baslatici ucusu baslatmaz.')
args=[sys.executable,str(root/'tools/fly_auto.py'),scenario,'--observe-only','--gui']
if scenario=='plane':args.append('--vision')
raise SystemExit(subprocess.call(args))
