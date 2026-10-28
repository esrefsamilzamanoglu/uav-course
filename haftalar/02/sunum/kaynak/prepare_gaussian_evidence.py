"""Promote only a passed, real Gaussian training run into the teaching assets."""
from pathlib import Path
import json,shutil,hashlib
from PIL import Image,ImageChops,ImageEnhance
ROOT=Path(__file__).resolve().parents[2];SIM=ROOT/'simulasyon';RUN=SIM/'.local/runs/20261027-183245-building';G=RUN/'products/gaussian';TRAIN=G/'training';A=ROOT/'sunum/gorseller';VAL=ROOT/'dogrulama'
report=json.loads((TRAIN/'gaussian_metrics.json').read_text())
assert report['passed'] and report['steps']==6000 and not report['holdout_used_in_sparse_initialization']
prov=[]
def copy(p,name):
    dst=A/name;shutil.copy2(p,dst);prov.append({'file':name,'kind':'actual RGB / trained Gaussian render','source':p.relative_to(SIM).as_posix(),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
copy(G/'dataset/images/0000.png','gaussian_reference.png')
copy(TRAIN/'eval_6000/0000.png','gaussian_final.png')
copy(TRAIN/'eval_1000/0000.png','gaussian_step1000.png')
copy(TRAIN/'eval_3000/0000.png','gaussian_step3000.png')
for key,index in [('a',0),('b',32),('c',72)]:
    copy(G/f'dataset/images/{index:04d}.png',f'gaussian_capture_{key}.png')
    copy(TRAIN/f'eval_6000/{index:04d}.png',f'gaussian_render_{key}.png')
ref=Image.open(A/'gaussian_reference.png').convert('RGB');render=Image.open(A/'gaussian_final.png').convert('RGB');difference=ImageEnhance.Brightness(ImageChops.difference(ref,render)).enhance(4);difference.save(A/'gaussian_difference.png')
prov.append({'file':'gaussian_difference.png','kind':'measured pixel difference, multiplied by4 for display','sources':['gaussian_reference.png','gaussian_final.png'],'sha256':hashlib.sha256((A/'gaussian_difference.png').read_bytes()).hexdigest()})
model=ROOT/'ornekler/Bina-Gaussian.ply';model.parent.mkdir(exist_ok=True);shutil.copy2(TRAIN/'export_6000.ply',model)
prov.append({'file':'../ornekler/Bina-Gaussian.ply','kind':'trained 3D Gaussian model','source':(TRAIN/'export_6000.ply').relative_to(SIM).as_posix(),'sha256':hashlib.sha256(model.read_bytes()).hexdigest()})
(A/'gaussian-provenance.json').write_text(json.dumps(prov,indent=2))
(VAL/'gaussian_validation.json').write_text(json.dumps(report,indent=2))
old=json.loads((VAL/'building-product.json').read_text())
if old.get('method','').startswith('SIFT'):
    old['role']='v1 sparse baseline; initialization concept, not current final product'
    (VAL/'building-sparse-baseline.json').write_text(json.dumps(old,indent=2))
(VAL/'building-product.json').write_text(json.dumps(report,indent=2))
summary=json.loads((VAL/'final_summary.json').read_text());summary['building_product']=report;summary['gaussian_revision']={'date':'2026-10-28','training_pipeline_passed':True,'source_capture_run':RUN.name,'poses':'known Gazebo poses','no_source_mesh':True,'no_flight_control_commands':True,'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest()};summary['all_required_passed']=summary['all_required_passed'] and report['passed'];(VAL/'final_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({'gaussians':report['gaussians'],'PSNR':report['mean_holdout_psnr_db'],'SSIM':report['mean_holdout_ssim'],'copied_assets':len(prov),'model_bytes':model.stat().st_size}))
