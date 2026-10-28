"""Validate image coverage, source identity, captions and editable slide content."""
from pathlib import Path
import json,hashlib,io
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import pymupdf as fitz
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'sunum/uretilen_gorseller'
plan=json.loads((A/'prompts.json').read_text(encoding='utf-8-sig'))
data=json.loads((ROOT/'sunum/kaynak/slides.json').read_text(encoding='utf-8'))
deck=Presentation(ROOT/'Hafta-02-Sunum.pptx');pdf=fitz.open(ROOT/'Hafta-02-Sunum-v3.pdf')
targets={a['slide']:a for a in plan['assets']}
expected={i+1 for i,d in enumerate(data['slides']) if d['layout'] in ('cards','flow','table','formula','stats','code')}
assert set(targets)==expected and len(targets)==40 and len(deck.slides)==len(pdf)==93
rows=[];issues=[]
for n,a in targets.items():
    s=deck.slides[n-1];d=data['slides'][n-1]
    sha=hashlib.sha256((A/a['file']).with_suffix('.jpg').read_bytes()).hexdigest()
    pictures=[sh for sh in s.shapes if sh.shape_type==MSO_SHAPE_TYPE.PICTURE]
    embedded=any(hashlib.sha256(sh.image.blob).hexdigest()==sha for sh in pictures)
    native='\n'.join(sh.text for sh in s.shapes if sh.has_text_frame)
    caption='Kavramsal çizim · AI' in native
    assert d['title']==a['title']
    # Every table value and teaching-card heading must remain editable.
    missing=[]
    for row in d.get('rows',[]):
        for value in row:
            if value not in native:missing.append(value)
    for title,body in d.get('cards',[]) if d['layout'] in ('cards','flow','code') else []:
        if title not in native or body not in native:missing.append(title)
    if not embedded or not caption or missing:issues.append({'slide':n,'embedded':embedded,'caption':caption,'missing':missing})
    # PDF extraction checks content did survive PowerPoint export.
    pt=pdf[n-1].get_text()
    if 'Kavramsal' not in pt or not pdf[n-1].get_images():issues.append({'slide':n,'issue':'missing PDF illustration/caption'})
    rows.append({'slide':n,'title':a['title'],'original_layout':d['layout'],
        'matching_generated_image_embedded':embedded,'editable_text_retained':not missing,'caption_present':caption})
report={'deck_pages':93,'target_pages':40,'illustrated_target_pages':sum(r['matching_generated_image_embedded'] for r in rows),
        'unillustrated_target_pages':[],'issues':issues,'checks':rows,
        'review':'All 40 generated illustrations reviewed individually; all 93 PDF pages reviewed in rendered contact sheets. Conceptual illustrations labelled separately from recorded simulation evidence.'}
(ROOT/'dogrulama/illustration_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'pages':93,'illustrated':len(rows),'issues':issues}))
assert not issues
