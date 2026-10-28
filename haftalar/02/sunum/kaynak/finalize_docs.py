"""Refresh only the source catalogue and week index; keep reviewed lesson prose."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
data=json.loads((ROOT/'sunum/kaynak/slides.json').read_text(encoding='utf-8'))
text='# 2. hafta — kaynaklar\n\n28 Ekim 2026 revizyonu. Teknik davranışlar için resmî kaynaklar; sayısal sonuçlar için gerçek Gazebo/SITL kayıtlarımız kullanıldı.\n\n'
names={'auto':'Copter AUTO','gazebo':'ArduPilot + Gazebo','windows':'Gazebo native Windows','commands':'MAVLink mission commands','grid':'Mission Planner Survey(Grid) ve camera trigger','plan':'Mission Planner görev planlama','mount':'Servo gimbal','roi':'Mount ROI targeting','spray':'Sprayer','takeoff':'Plane automatic takeoff','land':'Plane automatic landing','landstart':'DO_LAND_START','orb':'OpenCV ORB','homography':'OpenCV feature matching ve homography','triangulate':'OpenCV camera geometry / triangulation','sfm':'COLMAP: SfM ve dense reconstruction','repo':'Ders deposu','gs':'Kerbl ve diğerleri: 3D Gaussian Splatting (SIGGRAPH2023)','brush':'Brush0.3.0: training ve native viewer'}
for key,url in data['sources'].items():text+=f'- [{names.get(key,key)}]({url})\n'
text+='\n## Gerçek deney ve görsel kökenleri\n\n[Uçuş doğrulama özeti](dogrulama/final_summary.json) · [Gaussian hold-out metrikleri](dogrulama/gaussian_validation.json) · [Temel simülasyon görselleri](sunum/gorseller/provenance.json) · [Gaussian render kökenleri](sunum/gorseller/gaussian-provenance.json) · [Çalışma şemaları](sunum/gorseller/explainers-provenance.json).\n\nÖnceki v2 şemaları kodla çizildi; PNG görsellerin düzenlenebilir SVG kaynakları `sunum/semalar` içindedir. Gerçek sensör kaydı, gerçek model render’ı ve kavramsal şema birbirinden ayrılır. PSNR/SSIM görünüş ölçüsüdür; geometric accuracy iddiası değildir.\n\nv3 için built-in image_gen ile 40 ayrı açıklayıcı çizim üretildi. [Görseller ve tam promptlar](sunum/uretilen_gorseller/README.md) · [AI görsel kökenleri](sunum/uretilen_gorseller/provenance.json). Bu çizimler gerçek simülasyon kanıtlarından ayrı etiketlenir.\n\nArduPilot Gazebo kaynak sürümü `082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5`; SITL4.7.2 kaynak sürümü `fbd0a3160c90a557c24ce4c38c16975532652536`. Resmî Brush0.3.0 release URL ve hash değeri `simulasyon/gaussian-downloads.json` içinde. [Model / araç kökenleri](simulasyon/UPSTREAM.md).\n'
(ROOT/'KAYNAKLAR.md').write_text(text,encoding='utf-8')
index=ROOT.parents[1]/'README.md';current=index.read_bytes().decode('utf-8');rows=current.splitlines(keepends=True)
for i,row in enumerate(rows):
    if row.startswith('| 2. hafta |'):
        ending='\r\n' if row.endswith('\r\n') else '\n'
        rows[i]='| 2. hafta | AUTO görevler ve Gaussian Splatting (v3 · görsel anlatım) | [PDF’yi aç](haftalar/02/Hafta-02-Sunum-v3.pdf) · [PowerPoint](haftalar/02/Hafta-02-Sunum.pptx) · [Uygulamalar](haftalar/02/README.md) |'+ending
index.write_bytes(''.join(rows).encode('utf-8'))
print(json.dumps({'slides':data['count'],'sources':len(data['sources']),'first_week_content':'preserved'}))
