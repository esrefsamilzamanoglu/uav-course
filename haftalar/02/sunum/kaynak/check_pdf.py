from pathlib import Path
import json,math,re
import fitz
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'simulasyon/.local/research/pdf_review';OUT.mkdir(parents=True,exist_ok=True)
doc=fitz.open(ROOT/'Hafta-02-Sunum.pdf');data=json.loads((ROOT/'sunum/kaynak/slides.json').read_text(encoding='utf-8'))
assert len(doc)==data['count']<=100
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16);issues=[]
for i,p in enumerate(doc):
    txt=p.get_text();expected=data['slides'][i]
    if len(txt)<100:issues.append({'slide':i+1,'issue':'too little text'})
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for sp in l['spans']:
                x0,y0,x1,y1=sp['bbox']
                if x0<0 or y0<0 or x1>p.rect.width+1 or y1>p.rect.height+1:issues.append({'slide':i+1,'issue':'off-page text','text':sp['text']})
    pm=p.get_pixmap(matrix=fitz.Matrix(.72,.72),alpha=False);im=Image.frombytes('RGB',[pm.width,pm.height],pm.samples);im.save(OUT/f'{i+1:03d}.png')
for start in range(0,len(doc),12):
    sheet=Image.new('RGB',(1600,760),'#ffffff');dr=ImageDraw.Draw(sheet)
    for j in range(start,min(start+12,len(doc))):
        im=Image.open(OUT/f'{j+1:03d}.png');im.thumbnail((392,220));x=(j-start)%4*400;y=(j-start)//4*253
        sheet.paste(im,(x,y));dr.text((x+6,y+223),f'{j+1:02d}',fill='#18365d',font=font)
    sheet.save(OUT/f'contact_{start+1:03d}.jpg')
report={'pdf_pages':len(doc),'max_pages':100,'off_page_text_issues':issues,'page_text_lengths':[len(p.get_text()) for p in doc]}
(ROOT/'dogrulama/presentation_check.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
assert not issues
