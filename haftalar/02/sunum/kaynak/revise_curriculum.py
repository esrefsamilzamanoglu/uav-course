"""Active v2 curriculum: new 3DGS lesson, technical English and visual variety."""
from pathlib import Path
from copy import deepcopy
import json
from gaussian_curriculum import building
ROOT=Path(__file__).resolve().parents[2]

def revise(base,sources):
    sources.update(gs='https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/',brush='https://github.com/ArthurBrussee/brush/tree/v0.3.0')
    metrics=json.loads((ROOT/'dogrulama/gaussian_validation.json').read_text(encoding='utf-8'))
    assert metrics['passed'],'Finish Gaussian validation before making the revised lecture'
    slides=deepcopy(base)
    slides[1]['cards'][2]=('Değerlendir','Kaplama, mozaik, Gaussian model ve hareket olayını yorumla.')
    slides[6]['rows'][3]=['Görüntü /3Dişleme','OpenCV · SciPy · Brush','Mosaic ·3DGS · motion events']
    # Change repeated card layouts into full visual explanations and actual-data views.
    visuals={5:('visual','ex_system.png'),12:('visual','ex_camera_height.png'),20:('visual','ex_nav_do.png'),25:('visual','ex_swath.png'),35:('visual','ex_overlap.png'),42:('visual','ex_mosaic.png'),68:('visual','ex_homography.png'),69:('visual','ex_motion_stages.png'),70:('visual','ex_parallax.png'),77:('visual','ex_event_timeline.png')}
    for number,(layout,image) in visuals.items():slides[number-1].update(layout=layout,image=image)
    slides[12].update(layout='gallery',images=['kamera_90.png','kamera_45.png','kamera_20.png'],cards=[('Nadir · −90°','Doğrudan zemin'),('Oblique · −45°','Zemin + ileri alan'),('Forward · −20°','Güçlü perspective')])
    for number,chapter,subtitle in [(22,'01','Grid trajectory + sprayer ON/OFF'),(33,'02','Grid capture + overlap + planar mosaic'),(60,'04','AUTO takeoff + fixed scan + motion events + landing')]:
        slides[number-1].update(layout='chapter',chapter=chapter,subtitle=subtitle)
    slides[30].update(layout='formula',formula='Q = D × V × W / 600',example='20 L/ha × 10,8 km/h × 8 m / 600 = 2,88 L/min',legend=[('D','Target volume · L/ha'),('V','Groundspeed · km/h'),('W','Working width · m')])
    slides[43].update(layout='spotlight',image='tarla_mozaik.png',stats=[('100%','field coverage'),('99,53%','3+ image overlap'),('81','real RGB photos')])
    slides[72].update(layout='zoom',image='hareket.png',zoom='hareket_kirpim.png',bbox=[594,125,34,32],zoom_title='Motion candidate',zoom_caption='34 × 32 px · büyütülmüş crop')
    slides[74].update(layout='stats',stats=[('23','motion events'),('19','evaluation-only person overlaps'),('4','false alarms')])
    slides[75].update(layout='zoom',image='yanlis_alarm.png',zoom='yanlis_alarm_kirpim.png',zoom_title='False positive',zoom_caption='Parallax / alignment residual')
    # Update aggregate results and references outside the replaced building section.
    slides[3]['rows'][2][2]='Trained Gaussian model + novel-view render'
    slides[78]['rows'][4][1]='Mosaic · Gaussian PLY · motion events'
    slides[80]['rows'][3][2]='108 RGB · trained Gaussian PLY'
    slides[80]['notes']='AUTO uçuşlar27Ekim2026tarihinde doğrulandı. Gaussian Splatting ve sunum revizyonu28Ekim2026tarihinde eklendi. Bina modelinin train/hold-out ayrımı initialization aşamasından başlar. Güncel metrikler dogrulama/gaussian_validation.json içindedir. Önceki sparse point cloud artık nihai3Dürün değildir.'
    slides[83]['notes']=slides[83]['notes'].replace('yönelim ve seyrek bulut','yönelim, Gaussian PLY ve hold-out render').replace('seyrek bulut','Gaussian model')
    slides[85]['rows'][3]=['3D Gaussian Splatting','INRIA3DGS paper · Brush0.3.0 · OpenCV / COLMAP']
    slides[85]['sources']=list(sources)
    # Rebuild the 3D section as a coherent twenty-slide explanation.
    slides[45:59]=building(metrics)
    glossary=dict(title='Terimleri arayüzde gördüğümüz gibi kullanalım',message='İngilizce terimi koru; ne yaptığını kısa Türkçe açıklamayla anlat.',section='BAŞLANGIÇ',layout='table',headers=['Terim','Burada neyi ifade ediyor?'],rows=[['Waypoint / trajectory','Görev noktası / uçuş yolu'],['Footprint / overlap / GSD','Görülen alan / ortak görüntü alanı / piksel örneklemesi'],['ROI / gimbal / camera trigger','Bakılacak hedef / kamera yönelimi / çekim komutu'],['Feature matching / inlier / RANSAC','Ayrıntı eşleme / uyumlu eşleşme / hatalıları süzme'],['Gaussian / splat / opacity / render','3D primitive / ekran footprint’i / görünürlük / görüntü üretimi']],notes='Yerleşik terimleri Türkçeye zorla çevirmek yerine ilk geçtiği yerde İngilizce terim ve kısa işlev açıklaması verilir. Böylece Mission Planner, Brush ve OpenCV dokümanları ile dersteki kelimeler eşleşir. Her terimin fiziksel veya işlem karşılığını görselle ilişkilendirin. Örneğin footprint yalnız sözlük maddesi değil kameranın zeminde gördüğü alandır; splat ise3DGaussian’ın görüntü düzlemine projeksiyonudur.',sources=['commands','gs','brush'])
    slides.insert(4,glossary)
    def english(v):
        if isinstance(v,str):
            for a,b in [('içerdeş','inlier'),('İçerdeş','Inlier'),('ayak izi','footprint'),('Ayak izi','Footprint'),('yeniden izdüşüm hatası','reprojection error'),('üçgenleme','triangulation')]:v=v.replace(a,b)
            return v
        if isinstance(v,list):return [english(x) for x in v]
        if isinstance(v,tuple):return tuple(english(x) for x in v)
        if isinstance(v,dict):return {k:(val if k in ('image','images','sources','code') else english(val)) for k,val in v.items()}
        return v
    slides=english(slides)
    assert len(slides)==93 and len(slides)<=100
    return slides
