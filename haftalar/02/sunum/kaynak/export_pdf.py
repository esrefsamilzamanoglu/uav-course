"""Export only this presentation; preserve other open PowerPoint documents."""
from pathlib import Path
import json,time,os
import pythoncom,win32com.client
ROOT=Path(__file__).resolve().parents[2]
pythoncom.CoInitialize();app=win32com.client.DispatchEx('PowerPoint.Application')
existing=app.Presentations.Count;pres=None
try:
    pres=app.Presentations.Open(str(ROOT/'Hafta-02-Sunum.pptx'),True,False,False)
    count=pres.Slides.Count
    assert count<=100
    temporary=ROOT/'simulasyon/.local/research'/('Hafta-02-export-'+str(time.time_ns())+'.pdf')
    temporary.parent.mkdir(parents=True,exist_ok=True)
    pres.SaveAs(str(temporary),32)
    os.replace(temporary,ROOT/'Hafta-02-Sunum-v2.pdf')
    print(json.dumps({'slides':count,'pdf':str(ROOT/'Hafta-02-Sunum-v2.pdf')},ensure_ascii=False))
finally:
    if pres is not None:pres.Close()
    if existing==0 and app.Presentations.Count==0:app.Quit()
    pythoncom.CoUninitialize()
