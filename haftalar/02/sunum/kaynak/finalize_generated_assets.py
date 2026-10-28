"""Record provenance for built-in image generation; never draws or edits images."""
from pathlib import Path
import json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'sunum/uretilen_gorseller'
plan=json.loads((A/'prompts.json').read_text(encoding='utf-8-sig'))
records={x['slide']:x for x in json.loads((A/'generation-record.json').read_text(encoding='utf-8-sig'))['assets']}
assets=[]
for item in plan['assets']:
    png=A/item['file'];jpg=png.with_suffix('.jpg')
    assert png.is_file() and jpg.is_file()
    with Image.open(png) as im:dimensions=im.size
    with Image.open(jpg) as im:assert im.size==dimensions
    assets.append({'slide':item['slide'],'title':item['title'],'kind':'AI-generated conceptual teaching illustration',
        'mode':'built-in image_gen','is_simulation_evidence':False,'geometry':'schematic, not measured flight geometry',
        'source':png.name,'source_sha256':hashlib.sha256(png.read_bytes()).hexdigest(),
        'slide_copy':jpg.name,'slide_copy_sha256':hashlib.sha256(jpg.read_bytes()).hexdigest(),
        'dimensions':dimensions,'encoding':'Windows JPEG codec quality 92, original dimensions, no content edits',
        **{k:v for k,v in records[item['slide']].items() if k!='slide'}})
assert len(assets)==40 and len({a['slide'] for a in assets})==40
manifest={'mode':'built-in image_gen','illustrated_pages':40,'deck_pages':93,
    'scope':'All previously cards/table/flow/code/formula/stats-only pages now include a subject-specific illustration.',
    'limitations':'Conceptual drawings explain mechanisms; exact route geometry and performance claims come from recorded simulation evidence, not these images.',
    'prompts':'prompts.json','edits':'generation-record.json','assets':assets}
(A/'provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'generated_illustrations':len(assets),'source_png_bytes':sum((A/a['source']).stat().st_size for a in assets),
                  'slide_jpeg_bytes':sum((A/a['slide_copy']).stat().st_size for a in assets)}))
