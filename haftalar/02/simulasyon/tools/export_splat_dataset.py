"""Export real Gazebo RGB + recorded poses to Nerfstudio/Brush format.

Known simulator poses replace SfM pose estimation in this teaching dataset.
The image-derived sparse point cloud seeds optimization; no source mesh is read.
"""
from __future__ import annotations
import vision_bootstrap
import argparse,json,shutil,hashlib,math
from pathlib import Path
import numpy as np
from PIL import Image
from vision_geometry import geometry,load_frames

def export(run:Path,out:Path,width=640,eval_every=8,train_only_init=True):
    run=Path(run);out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'images').mkdir(exist_ok=True)
    raw=load_frames(run);frames=[];seen=set();manifest=[];selected=[]
    for f in raw:
        if f['frame'] in seen or f['position'][2]<14:continue
        seen.add(f['frame']);K,C,R,_=geometry(f)
        # Exclude return-to-home and transit; only the two ROI orbits.
        radius=np.linalg.norm(C[:2]-[0,45])
        if not 20<radius<32:continue
        im=Image.open(run/f['photo']).convert('RGB');ratio=width/im.width;h=round(im.height*ratio)
        im=im.resize((width,h),Image.Resampling.LANCZOS)
        name=f'images/{len(frames):04d}.png';im.save(out/name)
        c2w=np.eye(4);c2w[:3,:3]=R@np.diag([1,-1,-1]);c2w[:3,3]=C
        frames.append({'file_path':name,'transform_matrix':c2w.tolist()})
        selected.append(f)
        manifest.append({'image':name,'source':f['photo'],'source_sha256':hashlib.sha256((run/f['photo']).read_bytes()).hexdigest(),'sim_time':f['sim_time']})
    assert len(frames)>=40
    cfg={'camera_model':'OPENCV','w':width,'h':h,'fl_x':float(K[0,0]*ratio),'fl_y':float(K[1,1]*h/f['height']),'cx':width/2,'cy':h/2,'k1':0,'k2':0,'p1':0,'p2':0,'ply_file_path':'init.ply','frames':frames}
    (out/'transforms.json').write_text(json.dumps(cfg,indent=2))
    if train_only_init:
        from reconstruct_3d import reconstruct
        seed_frames=[f for i,f in enumerate(selected) if i%eval_every!=0]
        reconstruct(run,output=out/'sparse_init',frames=seed_frames)
        seed=out/'sparse_init/bina_seyrek_nokta_bulutu.ply'
    else:seed=run/'products/bina_seyrek_nokta_bulutu.ply'
    if not seed.is_file():raise RuntimeError('Run reconstruct_3d.py first to make the image-derived initialization')
    shutil.copy2(seed,out/'init.ply')
    (out/'provenance.json').write_text(json.dumps({'method':'Real Gazebo RGB; known simulator camera poses; image-derived SIFT seed; no building mesh','run':run.name,'eval_split_every':eval_every,'initialization_uses_only_training_photos':train_only_init,'train_images':len([i for i in range(len(frames)) if i%eval_every!=0]),'eval_images':len([i for i in range(len(frames)) if i%eval_every==0]),'images':manifest},indent=2))
    print(json.dumps({'dataset':str(out),'frames':len(frames),'resolution':[width,h],'camera_convention':'Nerfstudio OpenGL camera-to-world; original ENU world'}),flush=True)
    return out
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);p.add_argument('output',type=Path);p.add_argument('--width',type=int,default=640);p.add_argument('--eval-every',type=int,default=8);a=p.parse_args();export(a.run,a.output,a.width,a.eval_every)
