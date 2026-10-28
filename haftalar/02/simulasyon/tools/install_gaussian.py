"""Optional, local-only official Brush install. No CUDA or global environment changes."""
from pathlib import Path
import json,hashlib,urllib.request,zipfile,subprocess,os,time
ROOT=Path(__file__).resolve().parents[1];LOCAL=ROOT/'.local/gaussian'
def install():
    spec=json.loads((ROOT/'gaussian-downloads.json').read_text());LOCAL.mkdir(parents=True,exist_ok=True)
    archive=LOCAL/'brush-app-x86_64-pc-windows-msvc.zip';dest=LOCAL/'brush'
    if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=spec['sha256']:
        print('Brush resmî sunucudan indiriliyor (~159 MB)...',flush=True)
        part=archive.with_suffix('.zip.download')
        for attempt in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(spec['url'],headers={'User-Agent':'uav-course'}),timeout=60) as src,part.open('wb') as out:
                    while chunk:=src.read(1024*1024):out.write(chunk)
                assert hashlib.sha256(part.read_bytes()).hexdigest()==spec['sha256'],'Brush SHA256 dogrulamasi basarisiz'
                part.replace(archive);break
            except OSError:
                if attempt==2:raise
                time.sleep(2)
            finally:part.unlink(missing_ok=True)
    with zipfile.ZipFile(archive) as z:
        for entry in z.infolist():
            target=(dest/entry.filename).resolve()
            if not target.is_relative_to(dest.resolve()):raise RuntimeError('Archive path is outside local tool folder')
            z.extract(entry,dest)
    exe=dest/spec['archive_member'];assert exe.is_file()
    subprocess.run([str(exe),'--version'],check=True,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    print('Brush hazir: '+str(exe),flush=True)
    return exe
if __name__=='__main__':install()
