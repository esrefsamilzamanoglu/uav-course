"""Basic sparse multi-view reconstruction from real Gazebo RGB photographs.

SIFT matches + calibrated triangulation + reprojection filtering. Camera poses
come from the simulator (known-pose reconstruction); they are not estimated by
a full SfM/bundle-adjustment pipeline. No building mesh is read by this script.
"""
from __future__ import annotations
import vision_bootstrap
import argparse,json,math
from pathlib import Path
import cv2,numpy as np
from vision_geometry import geometry,load_frames

def reconstruct(run,output=None,frames=None):
    run=Path(run);out=Path(output) if output is not None else run/'products';out.mkdir(parents=True,exist_ok=True)
    photos=[];seen=set()
    for frame in (frames if frames is not None else load_frames(run)):
        if frame['frame'] not in seen and frame['position'][2]>12:
            photos.append(frame);seen.add(frame['frame'])
    sift=cv2.SIFT_create(nfeatures=5000,contrastThreshold=.025);matcher=cv2.BFMatcher(cv2.NORM_L2)
    cache={};points=[];colors=[];reports=[];best=None
    def features(i):
        if i not in cache:
            image=cv2.imread(str(run/photos[i]['photo']));gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
            kp,desc=sift.detectAndCompute(gray,None);cache[i]=(image,kp,desc)
        return cache[i]
    for i in range(len(photos)-1):
        for gap in (2,4):
            j=i+gap
            if j>=len(photos):continue
            K,Ca,Ra,Pa=geometry(photos[i]);_,Cb,Rb,Pb=geometry(photos[j]);baseline=np.linalg.norm(Ca-Cb)
            if not .8<baseline<12:continue
            ima,ka,da=features(i);imb,kb,db=features(j)
            if da is None or db is None:continue
            pairs=matcher.knnMatch(da,db,k=2);matches=[p[0] for p in pairs if len(p)==2 and p[0].distance<.72*p[1].distance]
            if len(matches)<12:continue
            a=np.float64([ka[m.queryIdx].pt for m in matches]);b=np.float64([kb[m.trainIdx].pt for m in matches])
            _,inlier=cv2.findFundamentalMat(a,b,cv2.FM_RANSAC,1.5,.999)
            if inlier is None:continue
            keep=inlier.ravel().astype(bool);a,b=a[keep],b[keep];kept=[m for m,k in zip(matches,keep) if k]
            if len(a)<8:continue
            h=cv2.triangulatePoints(Pa,Pb,a.T,b.T);xyz=(h[:3]/h[3]).T
            qa=(Pa@np.column_stack((xyz,np.ones(len(xyz)))).T).T;qb=(Pb@np.column_stack((xyz,np.ones(len(xyz)))).T).T
            err=np.maximum(np.linalg.norm(qa[:,:2]/qa[:,2:3]-a,axis=1),np.linalg.norm(qb[:,:2]/qb[:,2:3]-b,axis=1))
            valid=np.isfinite(xyz).all(axis=1)&(qa[:,2]>0)&(qb[:,2]>0)&(err<2.0)
            valid&=(np.abs(xyz[:,0])<12)&(xyz[:,1]>32)&(xyz[:,1]<58)&(xyz[:,2]>.4)&(xyz[:,2]<17)
            good=xyz[valid];pixels=np.round(a[valid]).astype(int);pixels[:,0]=np.clip(pixels[:,0],0,ima.shape[1]-1);pixels[:,1]=np.clip(pixels[:,1],0,ima.shape[0]-1)
            rgb=ima[pixels[:,1],pixels[:,0],::-1]
            if len(good):points.append(good);colors.append(rgb)
            row={'a':photos[i]['photo'],'b':photos[j]['photo'],'baseline_m':float(baseline),'ratio_matches':len(matches),'ransac_inliers':len(a),'valid_points':len(good),'median_reprojection_px':float(np.median(err[valid])) if valid.any() else None};reports.append(row)
            if best is None or len(good)>best[0]:best=(len(good),ima,imb,ka,kb,[m for m,v in zip(kept,valid) if v])
        if i%10==0:print('Reconstruct pair group '+str(i)+'/'+str(len(photos)),flush=True)
        # Bound memory when processing many high-resolution images.
        if i>8:cache.pop(i-8,None)
    if not points:raise RuntimeError('No image-derived 3D points survived filtering')
    pts=np.vstack(points);rgb=np.vstack(colors)
    # 8 cm voxel decimation of independently triangulated points.
    _,idx=np.unique(np.round(pts/.08).astype(np.int64),axis=0,return_index=True);pts=pts[idx];rgb=rgb[idx]
    with (out/'bina_seyrek_nokta_bulutu.ply').open('w') as f:
        f.write('ply\nformat ascii 1.0\nelement vertex '+str(len(pts))+'\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
        for p,c in zip(pts,rgb):f.write(' '.join(map(str,[*np.round(p,5),*map(int,c)]))+'\n')
    if best:
        _,ima,imb,ka,kb,matches=best
        view=cv2.drawMatches(ima,ka,imb,kb,matches[:70],None,flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
        cv2.imwrite(str(out/'bina_sift_eslesmeleri.png'),view)
    # Evaluation against analytic dimensions is separate from reconstruction.
    surface=np.minimum.reduce([np.abs(pts[:,0]-7),np.abs(pts[:,0]+7),np.abs(pts[:,1]-39),np.abs(pts[:,1]-51),np.abs(pts[:,2]-14.1)])
    metrics={'method':'SIFT + image matching + known-pose calibrated triangulation; sparse reconstruction',
             'photos':len(photos),'pairs':len(reports),'vertices':len(pts),'height_span_m':float(np.ptp(pts[:,2])),
             'median_distance_to_main_building_surfaces_m':float(np.median(surface)),
             'camera_poses_source':'recorded Gazebo camera poses, not estimated SfM poses','source_mesh_read':False,
             'limitations':'No dense mesh, texture baking or bundle adjustment; simulator poses supply scale.'}
    (out/'reconstruction_metrics.json').write_text(json.dumps(metrics,indent=2));(out/'reconstruction_pairs.json').write_text(json.dumps(reports,indent=2))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig=plt.figure(figsize=(11,8),facecolor='#edf3ff');ax=fig.add_subplot(111,projection='3d',facecolor='#edf3ff')
    ax.scatter(pts[:,0],pts[:,1]-45,pts[:,2],s=2,c=rgb/255,depthshade=False)
    ax.set(xlabel='East (m)',ylabel='North offset (m)',zlabel='Height (m)',title='Image-derived sparse building reconstruction')
    ax.view_init(elev=23,azim=-55);ax.set_box_aspect((24,26,17));fig.tight_layout();fig.savefig(out/'bina_3d_rekonstruksiyon.png',dpi=180);plt.close(fig)
    if len(pts)<100 or metrics['height_span_m']<7:raise RuntimeError('Sparse reconstruction validation failed: '+json.dumps(metrics))
    print(json.dumps(metrics),flush=True);return metrics
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);reconstruct(p.parse_args().run)
