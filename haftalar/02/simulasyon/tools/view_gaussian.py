from pathlib import Path
import subprocess,sys,os
from install_gaussian import install
root=Path(__file__).resolve().parents[2]
model=Path(sys.argv[1]) if len(sys.argv)>1 else root/'ornekler/Bina-Gaussian.ply'
if not model.is_file():raise SystemExit('Model bulunamadi: '+str(model))
exe=install()
subprocess.Popen([str(exe),str(model.resolve()),'--with-viewer'],creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
