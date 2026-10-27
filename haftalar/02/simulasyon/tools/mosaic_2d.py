"""Flat-ground mosaic from real trigger images and recorded simulator camera poses.

This teaches coverage/calibration. It is not a terrain-corrected survey orthophoto.
No source terrain texture is used to construct the result.
"""
from __future__ import annotations
import vision_bootstrap
import argparse,json
from pathlib import Path
import cv2,numpy as np
from vision_geometry import ground_corners,load_frames

def build(run):
    run=Path(run);out=run/'products';out.mkdir(exist_ok=True)
    bounds=(-38,12,38,74);ppm=12;x0,y0,x1,y1=bounds
    width,height=round((x1-x0)*ppm),round((y1-y0)*ppm)
    total=np.zeros((height,width,3),np.float64);weight=np.zeros((height,width),np.float64);count=np.zeros((height,width),np.uint16)
    footprints=np.zeros((height,width,3),np.uint8);used=[];seen=set()
    for frame in load_frames(run):
        if frame['frame'] in seen or frame['position'][2]<8:continue
        seen.add(frame['frame']);corners=ground_corners(frame)
        if corners is None:continue
        path=run/frame['photo'];image=cv2.imread(str(path))
        if image is None:raise RuntimeError('Missing actual Gazebo image '+str(path))
        h,w=image.shape[:2];dest=np.column_stack(((corners[:,0]-x0)*ppm,(y1-corners[:,1])*ppm)).astype(np.float32)
        src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
        H=cv2.getPerspectiveTransform(src,dest)
        yy,xx=np.mgrid[:h,:w];feather=np.minimum(np.minimum(xx+1,w-xx),np.minimum(yy+1,h-yy)).astype(np.float32);feather/=feather.max()
        warped=cv2.warpPerspective(image.astype(np.float32)*feather[:,:,None],H,(width,height))
        ww=cv2.warpPerspective(feather,H,(width,height));total+=warped;weight+=ww;count+=(ww>.1).astype(np.uint16)
        cv2.polylines(footprints,[dest.astype(np.int32)],True,(127,210,246),1,cv2.LINE_AA)
        used.append({'photo':frame['photo'],'ground_corners_enu':corners.tolist()})
    result=np.zeros_like(total,dtype=np.uint8);valid=weight>.001;result[valid]=np.clip(total[valid]/weight[valid,None],0,255).astype(np.uint8)
    cv2.imwrite(str(out/'tarla_mozaik.png'),result);cv2.imwrite(str(out/'foto_ayak_izleri.png'),footprints)
    coverage=cv2.applyColorMap(np.clip(count/8*255,0,255).astype(np.uint8),cv2.COLORMAP_VIRIDIS);coverage[~valid]=0
    cv2.imwrite(str(out/'ortusme_haritasi.png'),coverage)
    field=count[round((y1-67)*ppm):round((y1-18)*ppm),round((-30-x0)*ppm):round((30-x0)*ppm)]
    metrics={'method':'calibrated flat-plane projection from actual Gazebo RGB trigger images','images_used':len(used),
             'output_shape':[height,width],'pixels_per_meter':ppm,'bounds_local_enu_m':bounds,'field_covered_fraction':float(np.mean(field>0)),
             'field_overlap_3plus_fraction':float(np.mean(field>=3)),'maximum_observations':int(count.max()),'source_ground_texture_used':False,
             'limitations':'Known simulator camera poses; z=0 plane; not a DEM orthophoto or centimetre accuracy claim.'}
    (out/'mosaic_metrics.json').write_text(json.dumps(metrics,indent=2));(out/'mosaic_sources.json').write_text(json.dumps(used,indent=2))
    (out/'tarla_mozaik.pgw').write_text(f'{1/ppm}\n0\n0\n{-1/ppm}\n{x0+.5/ppm}\n{y1-.5/ppm}\n')
    if len(used)<12 or metrics['field_covered_fraction']<.85:raise RuntimeError('Mosaic coverage test failed: '+json.dumps(metrics))
    print(json.dumps(metrics),flush=True)
    return metrics
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);build(p.parse_args().run)
