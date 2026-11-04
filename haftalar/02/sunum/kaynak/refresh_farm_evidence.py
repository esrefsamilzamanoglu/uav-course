"""Promote only the tested revised farm record; preserve other experiments."""
from pathlib import Path
import argparse,json,hashlib,shutil

ROOT=Path(__file__).resolve().parents[2];SIM=ROOT/'simulasyon';A=ROOT/'sunum/gorseller';V=ROOT/'dogrulama'


def refresh(run):
    run=Path(run).resolve()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    validation=read(run/'products/validation.json');metrics=read(run/'products/mosaic_metrics.json')
    assert validation['flight_status']=='auto_mission_passed' and validation['only_auto_while_armed']
    assert validation['final_disarmed'] and not validation['force_arm_used']
    assert validation['flight_setpoints_sent']==0 and metrics['field_covered_fraction']==1
    manifest=read(A/'provenance.json')
    updates={'mapping_dunya.png':run/'overview/000030.png','mapping_kamera.png':run/'photos/0020.png',
             'mapping_ucus.png':run/'products/ucus_izleri.png','tarla_mozaik.png':run/'products/tarla_mozaik.png',
             'tarla_mozaik_ortalama.png':run/'products/tarla_mozaik_ortalama.png'}
    for name,source in updates.items():
        shutil.copy2(source,A/name)
        manifest=[r for r in manifest if r['file']!=name]
        manifest.append({'file':name,'source':source.relative_to(SIM.resolve()).as_posix(),
                         'sha256':hashlib.sha256((A/name).read_bytes()).hexdigest(),'revision':'2026-11-04'})
    (A/'provenance.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    summary=read(V/'final_summary.json')
    summary.setdefault('previous_mapping_runs',[])
    if summary['tests']['mapping']['run']!=run.name:
        summary['previous_mapping_runs'].append({'test':summary['tests']['mapping'],'product':summary['mapping_product']})
    summary['tests']['mapping']={'run':run.name,**validation}
    summary['mapping_product']=metrics;summary['mapping_updated_on']='2026-11-04'
    # Gaussian, spray, plane and their recorded metrics remain untouched.
    (V/'final_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    for source,dest in [('products/validation.json','mapping-validation.json'),('products/mosaic_metrics.json','mapping-product.json'),
                        ('mission.json','mapping-mission.json'),('camera_calibration.json','mapping-camera_calibration.json')]:
        shutil.copy2(run/source,V/dest)
    examples=ROOT/'ornekler/Tarla-2D';examples.mkdir(exist_ok=True)
    for source,dest in [('products/tarla_mozaik.png','Tarla-RGB-Mozaik.png'),
                        ('products/tarla_mozaik_ortalama.png','Tarla-Ortalama-Mozaik.png'),
                        ('products/ortusme_haritasi.png','Goruntu-Ortusmesi.png'),
                        ('products/mosaic_metrics.json','metrikler.json'),('overview/000030.png','Gazebo-Tarla.png')]:
        shutil.copy2(run/source,examples/dest)
    # Refresh only the diagram that actually embeds the changed RGB products.
    import build_explainers
    build_explainers.mosaic()
    diagrams=read(A/'explainers-provenance.json')
    diagrams=[r for r in diagrams if r['file']!='ex_mosaic.png']+build_explainers.manifest
    (A/'explainers-provenance.json').write_text(json.dumps(diagrams,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'promoted_run':run.name,'mapping_metrics':metrics,'images':list(updates)}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);refresh(p.parse_args().run)
