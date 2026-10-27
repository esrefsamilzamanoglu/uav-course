"""Build editable 16:9 week-2 slides from validated Gazebo evidence.
Requires: python-pptx, Pillow. Run prepare_evidence.py only when revalidating.
"""
from pathlib import Path
import json,math,re
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE,MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from PIL import Image
from curriculum import SLIDES,SOURCES
def typography(v):
    if isinstance(v,str):
        return re.sub(r'(?<=[0-9])(?=[a-zçğıöşü])',' ',v)
    if isinstance(v,dict):return {k:(val if k in ('image','images','sources','code','diagram','layout','section') else typography(val)) for k,val in v.items()}
    if isinstance(v,(tuple,list)):return [typography(x) for x in v]
    return v
SLIDES=typography(SLIDES)
ROOT=Path(__file__).resolve().parents[2];ASSETS=ROOT/'sunum/gorseller'
assert json.loads((ROOT/'dogrulama/final_summary.json').read_text(encoding='utf-8'))['all_required_passed'], 'Validate simulations before making slides'
assert 1<len(SLIDES)<=100
P=Presentation();P.slide_width=Inches(13.333333);P.slide_height=Inches(7.5)
P.core_properties.title='İHA Yazılımı ve Simülasyonu — 2. Hafta: AUTO Görevler'
P.core_properties.author='Arş. Gör. Eşref Şamil Zamanoğlu'
P.core_properties.subject='Birlik Akademi · Bilişim Programları · 2026 Güz Dönemi'
BG='EDF3FF';NAVY='18365D';TEAL='238B88';GOLD='D79A29';INK='263D56';MUTED='61758C';WHITE='FFFFFF';PALE='DCE8F7';RED='B74A47'
def rgb(v):return RGBColor.from_string(v)
def rect(s,x,y,w,h,fill=WHITE,line=None,radius=False):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill)
    if line:sh.line.color.rgb=rgb(line)
    else:sh.line.fill.background()
    if radius:
        try:sh.adjustments[0]=.09
        except Exception:pass
    return sh
def text(s,value,x,y,w,h,size=20,color=INK,bold=False,align=None,font='Century Gothic'):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame;tf.clear();tf.word_wrap=True
    tf.margin_left=tf.margin_right=Inches(.03);tf.margin_top=Inches(.02);tf.margin_bottom=0
    for i,line in enumerate(str(value).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name=font;p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=rgb(color);p.space_after=Pt(6)
        if align is not None:p.alignment=align
    return sh
def image(s,name,x,y,w,h,fill=False):
    path=ASSETS/name
    if fill:s.shapes.add_picture(str(path),Inches(x),Inches(y),Inches(w),Inches(h));return
    iw,ih=Image.open(path).size;k=min(w/iw,h/ih);ww,hh=iw*k,ih*k
    s.shapes.add_picture(str(path),Inches(x+(w-ww)/2),Inches(y+(h-hh)/2),Inches(ww),Inches(hh))
def line(s,x1,y1,x2,y2,color=TEAL,width=2):
    sh=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));sh.line.color.rgb=rgb(color);sh.line.width=Pt(width);return sh
def circle(s,x,y,d,fill=TEAL):
    sh=s.shapes.add_shape(MSO_SHAPE.OVAL,Inches(x),Inches(y),Inches(d),Inches(d));sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill);sh.line.fill.background();return sh
def arrow(s,x,y,w=.4,h=.3):
    a=s.shapes.add_shape(MSO_SHAPE.CHEVRON,Inches(x),Inches(y),Inches(w),Inches(h));a.fill.solid();a.fill.fore_color.rgb=rgb(TEAL);a.line.fill.background()
def card(s,title,body,x,y,w,h=1.22,n=None):
    rect(s,x,y,w,h,WHITE,radius=True)
    text(s,title,x+.18,y+.13,w-.36,.45,20,NAVY,True)
    text(s,body,x+.18,y+.64,w-.36,h-.67,17,INK)
def base(d,n):
    s=P.slides.add_slide(P.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(BG)
    rect(s,.57,.42,.1,.56,TEAL);text(s,d['title'],.85,.37,11.8,.8,29,NAVY,True)
    text(s,d.get('section','AUTO UYGULAMALARI').upper(),.61,1.12,12,.25,10,MUTED,True)
    rect(s,.6,6.55,12.1,.5,PALE,radius=True);text(s,d['message'],.78,6.64,11.75,.32,16,NAVY,True)
    text(s,'Birlik Akademi  ·  İHA Yazılımı ve Simülasyonu  ·  2. Hafta',.62,7.18,10,.2,9,MUTED)
    text(s,f'{n:02d} / {len(SLIDES):02d}',11.85,7.15,.85,.25,10,MUTED,align=PP_ALIGN.RIGHT)
    return s
def draw_table(s,headers,rows):
    x,y,w=.65,1.65,12.02;cols=len(headers);widths=[w/cols]*cols
    rh=min(.76,4.45/(len(rows)+1));pos=x
    for head,cw in zip(headers,widths):rect(s,pos,y,cw-.04,rh,NAVY);text(s,head,pos+.13,y+.13,cw-.26,rh-.12,17,WHITE,True);pos+=cw
    for j,row in enumerate(rows):
        pos=x;yy=y+(j+1)*rh
        for value,cw in zip(row,widths):rect(s,pos,yy,cw-.04,rh-.04,WHITE if j%2==0 else PALE);text(s,value,pos+.13,yy+.1,cw-.26,rh-.13,16,INK);pos+=cw
def diagram(s,kind):
    if kind=='fov':
        rect(s,1,5.7,8,.12,TEAL);circle(s,4.35,1.65,.3,NAVY)
        line(s,4.5,1.95,1.65,5.7);line(s,4.5,1.95,7.35,5.7);line(s,4.5,2.1,4.5,5.7,MUTED,1)
        text(s,'Kamera',4.8,1.65,2,.4,19,NAVY,True);text(s,'70°',4,2.7,1,.5,24,TEAL,True);text(s,'18 m',4.65,4.1,1.5,.4,20)
        text(s,'25,2 m yatay ayak izi',2.4,5.95,5,.4,20,NAVY,True)
    elif kind in ('grid','spray_grid'):
        rect(s,1.2,1.75,7.3,4.2,'D6E9D8');last=None
        count=9 if kind=='spray_grid' else 7
        for i in range(count):
            x=1.7+i*6.24/(count-1);ya,yb=(2.1,5.65) if i%2==0 else (5.65,2.1)
            if last:line(s,*last,x,ya,GOLD,3)
            line(s,x,ya,x,yb,TEAL,3)
            for yy in [2.25,2.9,3.55,4.2,4.85,5.5]:circle(s,x-.04,yy,.08,NAVY)
            last=(x,yb)
        text(s,('7' if kind=='spray_grid' else '8')+' m şerit aralığı',2.4,6,4,.35,18,NAVY,True)
    elif kind=='orbit':
        cx,cy,rx,ry=4.6,3.7,3.1,1.55
        for offset,color in [(0,TEAL),(-.65,GOLD)]:
            prev=None
            for i in range(49):
                a=2*math.pi*i/48;p=(cx+rx*math.cos(a),cy+ry*math.sin(a)+offset)
                if prev:line(s,*prev,*p,color,1.8)
                prev=p
        rect(s,3.95,2.9,1.3,1.7,NAVY);text(s,'BİNA',4.05,3.5,1.1,.35,17,WHITE,True)
        for x,y in [(1.5,3.7),(6.8,2.6),(7.3,4.4)]:circle(s,x-.08,y-.08,.17,GOLD);line(s,x,y,4.6,3.7,MUTED,1)
        text(s,'18 m / 23 m · R = 26 m',2.2,5.8,5,.4,20,NAVY,True)
    elif kind=='pipeline':pass
    elif kind=='coordinates':
        circle(s,3.4,4.8,.22,NAVY);line(s,3.5,4.9,7.7,4.9,TEAL,4);line(s,3.5,4.9,3.5,1.9,TEAL,4);line(s,3.5,4.9,1.7,3.3,GOLD,4)
        text(s,'E / x',7.8,4.65,1,.4,23,TEAL,True);text(s,'N / y',3.1,1.4,1.8,.4,23,TEAL,True);text(s,'U / z',.7,2.95,1.6,.4,23,GOLD,True);text(s,'HOME',3.15,5.25,2,.5,20,NAVY,True)
    elif kind=='landing':
        rect(s,.95,5.35,7.8,.12,NAVY)
        for p in [(1.5,2.2),(4.5,3.45),(7.8,5.35)]:circle(s,p[0]-.08,p[1]-.08,.16,TEAL)
        line(s,1.5,2.2,4.5,3.45,TEAL,3);line(s,4.5,3.45,7.8,5.35,TEAL,3)
        text(s,'60 m',1.1,1.65,1.7,.4,20,NAVY,True);text(s,'30 m',4.1,2.9,1.7,.4,20,NAVY,True);text(s,'LAND',7.1,5.65,1.8,.4,20,NAVY,True)
        text(s,'450 m',1.2,5.65,2,.4,18);text(s,'240 m',4.25,5.65,2,.4,18)
def render(d,n):
    s=base(d,n);layout=d.get('layout','photo');items=d.get('cards',[])
    if layout=='cover':
        s.background.fill.fore_color.rgb=rgb(NAVY)
        for sh in list(s.shapes):
            el=sh._element;el.getparent().remove(el)
        text(s,'İHA YAZILIMI\nVE SİMÜLASYONU',.75,.65,8,1.6,36,WHITE,True)
        text(s,'2. HAFTA  /  AUTO GÖREVLER',.8,2.4,8,.55,24,'8DD8D1',True)
        text(s,'Gerçek problemlerden simülasyon uygulamalarına',.8,3.05,11,.5,21,WHITE)
        for i,name in enumerate(['mapping_dunya.png','building_dunya.png','plane_dunya.png']):image(s,name,.8+i*4.02,3.85,3.85,2.3)
        text(s,'Birlik Akademi · Bilişim Programları  |  2026 Güz Dönemi',.8,6.33,11.8,.4,16,WHITE)
        text(s,'Arş. Gör. Eşref Şamil Zamanoğlu  ·  Birlik Vakfı Sakarya Şubesi',.8,6.85,11.8,.35,15,'C7D9EF')
    elif layout in ('photo','diagram'):
        rect(s,.65,1.55,8.3,4.75,WHITE,radius=True)
        if layout=='photo':image(s,d['image'],.72,1.61,8.16,4.61)
        else:diagram(s,d['diagram'])
        h=min(1.37,4.72/max(1,len(items)))
        for j,(title,body) in enumerate(items):card(s,title,body,9.18,1.57+j*(h+.14),3.47,h)
    elif layout=='full':
        image(s,d['image'],.65,1.5,12,4.85)
    elif layout=='compare':
        for i,name in enumerate(d['images']):
            x=.65+i*6.15;rect(s,x,1.55,5.88,4.8,WHITE,radius=True);image(s,name,x+.08,1.65,5.72,3.6)
            title,body=items[i];text(s,title,x+.15,5.35,5.55,.38,20,NAVY,True);text(s,body,x+.15,5.81,5.55,.38,16)
    elif layout=='cards':
        count=len(items)
        if count<=3:
            w=(12.02-(count-1)*.25)/count
            for j,(title,body) in enumerate(items):
                x=.65+j*(w+.25);rect(s,x,1.8,w,3.9,WHITE,radius=True);circle(s,x+.22,2.1,.56,TEAL);text(s,str(j+1),x+.32,2.17,.36,.36,20,WHITE,True)
                text(s,title,x+.22,3.02,w-.44,.8,24,NAVY,True);text(s,body,x+.22,4.05,w-.44,1.5,21)
        else:
            for j,(title,body) in enumerate(items):card(s,title,body,.65+(j%2)*6.15,1.7+(j//2)*2.22,5.86,1.98)
    elif layout=='flow':
        count=len(items);w=(12-(count-1)*.38)/count
        for j,(title,body) in enumerate(items):
            x=.65+j*(w+.38);rect(s,x,2.05,w,3.5,WHITE,radius=True);text(s,f'{j+1:02}',x+.18,2.3,w-.36,.7,32,TEAL,True);text(s,title,x+.18,3.25,w-.36,.8,22,NAVY,True);text(s,body,x+.18,4.2,w-.36,1.1,18)
            if j<count-1:arrow(s,x+w+.03,3.6,.3,.35)
    elif layout=='table':draw_table(s,d['headers'],d['rows'])
    elif layout=='code':
        rect(s,.7,1.7,11.95,2.8,NAVY,radius=True);text(s,d['code'].replace('\n  ',' '),.98,2,11.4,2.25,17,WHITE,font='Consolas')
        for i,(title,body) in enumerate(items):card(s,title,body,.7+i*6.12,4.85,5.83,1.25)
    else:raise ValueError(layout)
    notes='ANA FİKİR: '+d['message']+'\n\n'+d['notes']
    if d.get('question'):notes+='\n\nSINIFA SORU / KONTROL: '+d['question']
    if d.get('sources'):notes+='\n\nKAYNAKLAR:\n'+'\n'.join(SOURCES[k] for k in d['sources'])
    notes+='\n\nGÖRSEL: Gerçek Gazebo RGB kaydı, gerçek uçuş verisinden grafik veya düzenlenebilir öğretim şeması. Köken listesi: sunum/gorseller/provenance.json.'
    s.notes_slide.notes_text_frame.text=notes
    return notes
notes=[]
for n,d in enumerate(SLIDES,1):notes.append(f"{'='*72}\n{n:02d}. {d['title']}\n{'='*72}\n"+render(d,n))
P.save(ROOT/'Hafta-02-Sunum.pptx')
(ROOT/'Hafta-02-Egitmen-Notlari.txt').write_text('\n\n'.join(notes),encoding='utf-8')
(ROOT/'sunum/kaynak/slides.json').write_text(json.dumps({'count':len(SLIDES),'slides':SLIDES,'sources':SOURCES},indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'slides':len(SLIDES),'pptx':str(ROOT/'Hafta-02-Sunum.pptx')},ensure_ascii=False))
