"""Export only this presentation; preserve other open PowerPoint documents."""
from pathlib import Path
import json,time
import pythoncom,win32com.client
ROOT=Path(__file__).resolve().parents[2]
pythoncom.CoInitialize();app=win32com.client.DispatchEx('PowerPoint.Application')
existing=app.Presentations.Count;pres=None
try:
    pres=app.Presentations.Open(str(ROOT/'Hafta-02-Sunum.pptx'),True,False,False)
    count=pres.Slides.Count
    assert count<=100
    pres.SaveAs(str(ROOT/'Hafta-02-Sunum.pdf'),32)
    print(json.dumps({'slides':count,'pdf':str(ROOT/'Hafta-02-Sunum.pdf')},ensure_ascii=False))
finally:
    if pres is not None:pres.Close()
    if existing==0 and app.Presentations.Count==0:app.Quit()
    pythoncom.CoUninitialize()
