"""Activate DLL search for a venv based on the existing Pixi Python on Windows."""
import os,sys
from pathlib import Path
_dll_handles=[]
if os.name=='nt':
    folder=Path(sys.base_prefix)/'Library/bin'
    if folder.is_dir():
        _dll_handles.append(os.add_dll_directory(str(folder)))
        os.environ['PATH']=str(folder)+os.pathsep+os.environ.get('PATH','')
