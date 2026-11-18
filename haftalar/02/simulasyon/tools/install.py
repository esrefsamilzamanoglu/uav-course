"""One-time native Windows course extension, using official downloads only."""
from __future__ import annotations
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
from runtime import ROOT,REPO,LOCAL,digest,native_config,prepare,environment

def checked(*args,**kwargs):return subprocess.run([str(x) for x in args],check=True,**kwargs)
def get_download(entry):
    p=LOCAL/entry['file'];p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_file() and digest(p)==entry['sha256']:return
    temp=p.with_suffix(p.suffix+'.download')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(entry['url'],headers={'User-Agent':'uav-course'}),timeout=60) as response,temp.open('wb') as output:
                while chunk:=response.read(1024*1024):output.write(chunk)
            if digest(temp)!=entry['sha256']:raise RuntimeError('Resmi indirme surumu degismis; ders sorumlusuna bildirin: '+entry['file'])
            temp.replace(p);return
        except OSError:
            if attempt==2:raise
            time.sleep(2)
        finally:temp.unlink(missing_ok=True)
def compiler():
    direct=Path('C:/BuildTools/VC/Auxiliary/Build/vcvars64.bat')
    if direct.is_file():return direct
    vswhere=Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'Microsoft Visual Studio/Installer/vswhere.exe'
    if vswhere.is_file():
        result=checked(vswhere,'-latest','-products','*','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath',capture_output=True,text=True)
        p=Path(result.stdout.strip())/'VC/Auxiliary/Build/vcvars64.bat'
        if p.is_file():return p
    raise RuntimeError('Ilk haftadaki Visual C++ Build Tools kurulumu eksik.')
def main():
    c=native_config();LOCAL.mkdir(exist_ok=True)
    copter_downloads = json.loads((REPO / 'windows/downloads.json').read_text(encoding='utf-8'))
    for entry in copter_downloads:
        path = c['sitl'] / entry['file']
        if not path.is_file() or digest(path) != entry['sha256']:
            raise RuntimeError(
                f"Eksik/eski Windows SITL dosyasi: {entry['file']}. "
                'Once windows/Kur.cmd dosyasini yeniden calistirin.'
            )
    copter_version = next(entry['version'] for entry in copter_downloads if entry['file'] == 'ArduCopter.exe')
    print('[1/4] Goruntu isleme ortami hazirlaniyor...',flush=True)
    venv=LOCAL/'venv';py=venv/'Scripts/python.exe'
    if not py.is_file():checked(c['prefix']/'python.exe','-m','venv','--system-site-packages',venv)
    checked(py,'-m','pip','install','--disable-pip-version-check','-r',ROOT/'requirements.txt',stderr=subprocess.STDOUT)
    probe="import sys;sys.path.insert(0,"+repr(str(ROOT/'tools'))+");import vision_bootstrap,numpy as n,cv2;from scipy.spatial.transform import Rotation;assert n.allclose(n.linalg.inv(n.eye(3)),n.eye(3));print('Numerical/image ABI check OK:',cv2.__version__)"
    checked(py,'-c',probe,stderr=subprocess.STDOUT)
    plane_downloads = json.loads((ROOT / 'downloads.json').read_text(encoding='utf-8'))
    plane_version = next(entry['version'] for entry in plane_downloads if entry['file'] == 'research/ArduPlane.exe')
    print(f'[2/4] Resmi ArduPlane {plane_version} ve parametreler dogrulaniyor...', flush=True)
    for entry in plane_downloads:
        get_download(entry)
    print('[3/4] Gazebo kamera/sahne eklentisi yerelde derleniyor...',flush=True)
    batch=LOCAL/'build-course.cmd';build=LOCAL/'build'
    lines=['@echo off',f'call "{compiler()}"','if errorlevel 1 exit /b %errorlevel%',
           f'"{c["pixi"]}" run --manifest-path "{c["manifest"]}" cmake -S "{ROOT/"src"}" -B "{build}" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo "-DCMAKE_PREFIX_PATH={c["prefix"]/"Library"}"',
           'if errorlevel 1 exit /b %errorlevel%',f'"{c["pixi"]}" run --manifest-path "{c["manifest"]}" cmake --build "{build}" --parallel 2','exit /b %errorlevel%']
    batch.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    checked('cmd.exe','/d','/c',batch,env=environment(c),stderr=subprocess.STDOUT)
    print('[4/4] Uc dunya ve bes AUTO gorev hazirlaniyor...',flush=True)
    prepare()
    (LOCAL/'installed.json').write_text(json.dumps({'gazebo':'10.5.0','arducopter':copter_version,'arduplane':plane_version,'source':'official servers; local build','python':str(py)},indent=2))
    print('Kurulum tamamlandi. Baslat.cmd dosyasini acin.',flush=True)
if __name__=='__main__':
    try:main()
    except (OSError,RuntimeError,subprocess.CalledProcessError) as e:print('Kurulum durdu: '+str(e),file=sys.stderr);raise SystemExit(1)
