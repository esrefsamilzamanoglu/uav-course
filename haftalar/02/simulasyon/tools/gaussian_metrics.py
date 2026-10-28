"""Appearance evaluation on images excluded from 3DGS training and initialization."""
import vision_bootstrap
import argparse,json,math
from pathlib import Path
import cv2,numpy as np

def ply_header(path):
    with Path(path).open('rb') as f:
        header=[]
        while True:
            row=f.readline().decode('ascii').strip();header.append(row)
            if row=='end_header':break
            if len(header)>200:raise RuntimeError('Bad PLY header')
    return header
def ssim(a,b):
    a=a.astype(np.float64)/255;b=b.astype(np.float64)/255
    ma=cv2.GaussianBlur(a,(11,11),1.5);mb=cv2.GaussianBlur(b,(11,11),1.5)
    va=cv2.GaussianBlur(a*a,(11,11),1.5)-ma*ma;vb=cv2.GaussianBlur(b*b,(11,11),1.5)-mb*mb
    cov=cv2.GaussianBlur(a*b,(11,11),1.5)-ma*mb
    q=((2*ma*mb+.01**2)*(2*cov+.03**2))/((ma*ma+mb*mb+.01**2)*(va+vb+.03**2))
    return float(np.mean(q[5:-5,5:-5]))
def psnr(a,b):
    mse=float(np.mean(((a.astype(np.float64)-b)/255)**2));return -10*math.log10(max(mse,1e-12))
def evaluate(dataset,training,steps=6000,require=True):
    dataset=Path(dataset);training=Path(training);cfg=json.loads((dataset/'transforms.json').read_text());prov=json.loads((dataset/'provenance.json').read_text())
    assert prov['initialization_uses_only_training_photos'],'Hold-out leakage in sparse initialization'
    header=ply_header(training/f'export_{steps}.ply')
    for prop in ['opacity','rot_0','scale_0','f_dc_0']:
        assert any(row.endswith(' '+prop) for row in header),('Not a Gaussian model',prop)
    n=int(next(row.split()[-1] for row in header if row.startswith('element vertex ')))
    rows=[]
    for i,frame in enumerate(cfg['frames']):
        if i%prov['eval_split_every']:continue
        target=dataset/frame['file_path'];render=training/f'eval_{steps}'/Path(frame['file_path']).name
        a=cv2.imread(str(target));b=cv2.imread(str(render));assert a is not None and b is not None and a.shape==b.shape
        h,w=a.shape[:2];crop=(slice(round(h*.10),round(h*.95)),slice(round(w*.23),round(w*.77)))
        early=training/'eval_1000'/Path(frame['file_path']).name;e=cv2.imread(str(early))
        rows.append({'image':frame['file_path'],'psnr_db':psnr(a,b),'ssim':ssim(a,b),'central_building_roi_psnr_db':psnr(a[crop],b[crop]),'step1000_psnr_db':psnr(a,e) if e is not None else None})
    report={'method':'3D Gaussian Splatting / Brush0.3.0','steps':steps,'gaussians':n,'training_images':prov['train_images'],'holdout_images':len(rows),'resolution':[cfg['w'],cfg['h']],
            'mean_holdout_psnr_db':float(np.mean([r['psnr_db'] for r in rows])),'mean_holdout_ssim':float(np.mean([r['ssim'] for r in rows])),
            'mean_central_building_roi_psnr_db':float(np.mean([r['central_building_roi_psnr_db'] for r in rows])),
            'mean_step1000_psnr_db':float(np.mean([r['step1000_psnr_db'] for r in rows if r['step1000_psnr_db'] is not None])),
            'holdout_used_in_training':False,'holdout_used_in_sparse_initialization':False,'camera_poses':'known Gazebo poses; not image-estimated SfM poses','source_mesh_read':False,
            'flight_control_commands_sent':0,'images':rows,'limitations':'Appearance metrics on synthetic images, not geometric survey accuracy. A Gaussian radiance representation is not a watertight mesh. Central ROI is a fixed image crop, not a semantic ground-truth mask.'}
    report['passed']=bool(len(rows)>=10 and n>10000 and report['mean_holdout_psnr_db']>19 and report['mean_central_building_roi_psnr_db']>19)
    (training/'gaussian_metrics.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='images'}),flush=True)
    if require and not report['passed']:raise RuntimeError('Gaussian appearance quality gate failed; revise capture/training before publishing')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',type=Path);p.add_argument('training',type=Path);p.add_argument('--steps',type=int,default=6000);a=p.parse_args();evaluate(a.dataset,a.training,a.steps)
