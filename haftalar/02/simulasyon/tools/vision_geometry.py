"""Calibrated Gazebo RGB projection. World ENU; optical x right,y down,z forward."""
import vision_bootstrap
import json,math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation

OPTICAL_TO_GZ=np.array([[0,0,1],[-1,0,0],[0,-1,0]],dtype=float)
def calibration(frame,hfov=None):
    hfov=hfov or frame.get('horizontal_fov',1.22173)
    w,h=frame['width'],frame['height'];f=w/(2*math.tan(hfov/2))
    return np.array([[f,0,w/2],[0,f,h/2],[0,0,1]],dtype=float)
def geometry(frame,hfov=None):
    K=calibration(frame,hfov);C=np.array(frame['position'],dtype=float)
    R=Rotation.from_quat(frame['quaternion_xyzw']).as_matrix()@OPTICAL_TO_GZ
    P=K@np.hstack((R.T,-R.T@C.reshape(3,1)))
    return K,C,R,P
def project(points,frame,hfov=None):
    K,C,R,P=geometry(frame,hfov);pts=np.asarray(points,dtype=float).reshape(-1,3)
    cam=(R.T@(pts-C).T).T;uv=(K@cam.T).T
    return uv[:,:2]/uv[:,2:3],cam[:,2]
def ground_corners(frame):
    K,C,R,_=geometry(frame);w,h=frame['width'],frame['height']
    pixels=np.array([[0,0,1],[w-1,0,1],[w-1,h-1,1],[0,h-1,1]],dtype=float)
    rays=(R@np.linalg.inv(K)@pixels.T).T
    if C[2]<2 or np.any(rays[:,2]>=-.03):return None
    return C[None,:]-C[2]*rays/rays[:,2:3]
def load_frames(run,photos=True):
    p=Path(run)/('photo_manifest.json' if photos else 'camera.jsonl')
    frames=json.loads(p.read_text()) if photos else [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    cfg=Path(run)/'camera_calibration.json'
    if cfg.exists():
        fov=json.loads(cfg.read_text())['horizontal_fov']
        for f in frames:f['horizontal_fov']=fov
    return frames
