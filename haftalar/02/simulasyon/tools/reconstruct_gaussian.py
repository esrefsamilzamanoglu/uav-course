"""Reconstruct an AUTO building flight using real 3D Gaussian optimization."""
import argparse,json,subprocess,sys,time,os
from pathlib import Path
from export_splat_dataset import export
from install_gaussian import install
from gaussian_metrics import evaluate

def train(run,steps=6000,width=640,max_splats=45000,viewer=False):
    run=Path(str(run).strip('"')).resolve()
    if run.is_file():run=run.parent
    if not (run/'photo_manifest.json').is_file():raise RuntimeError('Bina ucusunun RESULT klasorunu secin.')
    out=run/'products/gaussian'
    if (out/'training').exists():raise RuntimeError('Bu ucusun Gaussian ciktisi zaten var; yeni ucus kullanin veya onceki klasoru ayri saklayin.')
    exe=install();dataset=export(run,out/'dataset',width=width)
    training=out/'training';training.mkdir(parents=True)
    args=[str(exe),str(dataset),'--total-steps',str(steps),'--max-splats',str(max_splats),'--max-resolution',str(width),'--sh-degree','2','--refine-every','100','--growth-stop-iter',str(round(steps*.8)),'--growth-select-fraction','0.3','--eval-split-every','8','--eval-every','1000','--eval-save-to-disk','--export-every','1000','--export-path',str(training)]
    started=time.time();last=0;last_status=started
    print('Gaussian Splatting training basladi. Ucus kontrolune komut gonderilmez.',flush=True)
    with (out/'brush.log').open('wb') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        try:
            while p.poll() is None:
                checkpoints=[int(f.stem.split('_')[-1]) for f in training.glob('export_*.ply')]
                current=max(checkpoints,default=0)
                if current>last:print(f'Checkpoint: {current}/{steps}',flush=True);last=current
                if time.time()-last_status>30:
                    print(f'Training devam ediyor: {(time.time()-started)/60:.1f} dakika | son checkpoint {current}/{steps}',flush=True);last_status=time.time()
                time.sleep(3)
        except BaseException:p.terminate();p.wait(timeout=20);raise
        if p.returncode:raise RuntimeError('Brush durdu; '+str(out/'brush.log'))
    metrics=evaluate(dataset,training,steps)
    (out/'session.json').write_text(json.dumps({'command':args,'elapsed_s':time.time()-started,'source_run':run.name,'metrics_passed':metrics['passed']},indent=2))
    result=training/f'export_{steps}.ply';print('GAUSSIAN_RESULT='+str(result),flush=True)
    if viewer:subprocess.Popen([str(exe),str(result),'--with-viewer'],creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',nargs='?');p.add_argument('--steps',type=int,default=6000);p.add_argument('--width',type=int,default=640);p.add_argument('--max-splats',type=int,default=45000);p.add_argument('--viewer',action='store_true');a=p.parse_args();train(a.run or input('Bina ucus klasorunu yapistirin: '),a.steps,a.width,a.max_splats,a.viewer)
