"""4 Kasım: güncel RGB tarla görünüşü ve derste incelenecek gerçek kod yolları."""
from pathlib import Path
import json


def revise_farm(slides):
    root=Path(__file__).resolve().parents[2]
    metrics=json.loads((root/'dogrulama/mapping-product.json').read_text(encoding='utf-8'))
    overlap=f"{100*metrics['field_overlap_3plus_fraction']:.2f}".replace('.',',')
    for slide in slides:
        slide['notes']=slide['notes'].replace('99,53',overlap)
        title=slide['title']
        if title=='Aynı dünya iki göreve hizmet ediyor':
            slide['cards'][0]=('3D bitkiler','Bölgesel sararma, farklı boy ve yaprak yönü.')
            slide['notes']+=' 4 Kasım revizyonunda 1 575 bitkiye bölgesel ve bireysel renk/boyut çeşitliliği eklendi. Renkler senaryo tasarımıdır; NDVI veya ölçülmüş stres değildir.'
        elif title=='Sonuç: aynı tarlanın tek mozaik görüntüsü':
            slide['message']='Gerçek RGB mozaikte yeşil, sararmış ve küçük bitki bölgeleri görülür.'
            slide['notes']+=' En merkezi fotoğraf pikselini seçen mozaik kullanılır; tarla_mozaik_ortalama.png karşılaştırma içindir. Senaryo stres bilgisi algoritmaya verilmez.'
        elif title=='Haritalama sonucunu nasıl puanlarız?':
            slide['stats']=[('100%','field coverage'),(overlap+'%','3+ image overlap'),(str(metrics['images_used']),'real RGB photos')]
        elif title=='Uygulama: mozaik üretin ve karşılaştırın':
            slide['code']=slide['code'].replace('tools\\mosaic_2d.py','ders_kodlari\\haritalama_2d.py')
            slide['notes']+=' Derste ders_kodlari/haritalama_2d.py dosyasında build, harita_pikselleri ve kenar_agirliklari adımlarını açın. En merkezi bakış ile ortalama çıktıyı karşılaştırın.'
        elif title=='Dosyaları nerede bulacağız?':
            slide['rows'].insert(0,['ders_kodlari/','2D · 3D · hareket algoritmaları','Derste gerçek kodu açıp incele'])
        elif title=='Son denemeler: ne doğrulandı?':
            slide['notes']+=' Tarla görsel revizyonu ve 81 fotoğraflık AUTO uçuş 4 Kasım 2026 tarihinde tekrar doğrulandı.'
    return slides
