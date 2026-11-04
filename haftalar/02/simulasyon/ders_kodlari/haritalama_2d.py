"""AUTO çekimlerinden 2D tarla mozaiği üret.

Derste okuma sırası:
  1. Kamera köşelerinin zemindeki karşılığını bul.
  2. Her RGB fotoğrafı ortak harita düzlemine taşı.
  3. Örtüşmede en merkezi bakışı seç; ortalama mozaiği de karşılaştırma için sakla.
  4. Görüntüyü ve kapsama ölçümlerini kaydet.

Girdi: uçuş klasöründeki photo_manifest.json ve photos/*.png.
Çıktı: products/tarla_mozaik.png, örtüşme haritası ve JSON ölçümleri.
Kamera pozları Gazebo'dan bilinir. z=0 varsayımı kullanılır; DEM üretmeyiz.
Tarla dokusu veya bitkilerin senaryo stres değerleri bu koda verilmez.
"""
from __future__ import annotations

if __package__:
    from . import _ortak
else:
    import _ortak

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from vision_geometry import ground_corners, load_frames

# Yerel ENU: x doğu, y kuzey. Bunlar uçuş komutu değil, çıktı alanıdır.
HARITA_SINIRLARI = (-38, 12, 38, 74)
PIKSEL_METRE = 12  # Çıktı rasteri: 1 piksel ≈ 8,33 cm. Kamera GSD'si değildir.


def kenar_agirliklari(yukseklik, genislik):
    """Fotoğraf merkezini güçlü, kenarlarını düşük ağırlıkla birleştir."""
    y, x = np.mgrid[:yukseklik, :genislik]
    kenara_uzaklik = np.minimum(
        np.minimum(x + 1, genislik - x),
        np.minimum(y + 1, yukseklik - y),
    ).astype(np.float32)
    return kenara_uzaklik / kenara_uzaklik.max()


def harita_pikselleri(zemin_koseleri, sinirlar, piksel_metre):
    """Metre cinsinden zemin noktalarını mozaikteki piksele dönüştür."""
    bati, _, _, kuzey = sinirlar
    # Haritada kuzey yukarıda; görüntünün y ekseni aşağı doğru büyür.
    x = (zemin_koseleri[:, 0] - bati) * piksel_metre
    y = (kuzey - zemin_koseleri[:, 1]) * piksel_metre
    return np.column_stack((x, y)).astype(np.float32)


def build(run):
    """Gerçek RGB çekimlerini oku, projekte et, birleştir ve ölç."""
    ucus = Path(str(run).strip('"')).resolve()
    if not (ucus / 'photo_manifest.json').is_file():
        raise RuntimeError('Tarla uçuşunun photo_manifest.json içeren RESULT klasörünü seçin.')
    cikti = ucus / 'products'
    cikti.mkdir(exist_ok=True)
    bati, guney, dogu, kuzey = HARITA_SINIRLARI
    genislik = round((dogu - bati) * PIKSEL_METRE)
    yukseklik = round((kuzey - guney) * PIKSEL_METRE)

    # RGB toplamı / ağırlık toplamı = ağırlıklı ortalama mozaik.
    renk_toplami = np.zeros((yukseklik, genislik, 3), np.float64)
    agirlik_toplami = np.zeros((yukseklik, genislik), np.float64)
    gozlem_sayisi = np.zeros((yukseklik, genislik), np.uint16)
    ayak_izleri = np.zeros((yukseklik, genislik, 3), np.uint8)
    en_iyi_agirlik = np.zeros((yukseklik, genislik), np.float32)
    secilen_rgb = np.zeros((yukseklik, genislik, 3), np.uint8)
    kullanilanlar = []
    gorulen_kareler = set()

    for kare in load_frames(ucus):
        if kare['frame'] in gorulen_kareler or kare['position'][2] < 8:
            continue
        gorulen_kareler.add(kare['frame'])

        # 1) Kalibrasyon + kamera pozu → dört köşenin z=0 ile kesişimi.
        koseler = ground_corners(kare)
        if koseler is None:
            continue
        fotograf = cv2.imread(str(ucus / kare['photo']))
        if fotograf is None:
            raise RuntimeError(f"RGB fotoğraf bulunamadı: {kare['photo']}")

        # 2) Fotoğraf pikseli → harita pikseli: planar homography.
        h, w = fotograf.shape[:2]
        kaynak = np.float32([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]])
        hedef = harita_pikselleri(koseler, HARITA_SINIRLARI, PIKSEL_METRE)
        homography = cv2.getPerspectiveTransform(kaynak, hedef)

        # 3) RGB ile ağırlık AYRI taşınır; sonra oranları alınır.
        agirlik = kenar_agirliklari(h, w)
        tasinan_renk = cv2.warpPerspective(
            fotograf.astype(np.float32) * agirlik[:, :, None],
            homography, (genislik, yukseklik),
        )
        tasinan_agirlik = cv2.warpPerspective(agirlik, homography, (genislik, yukseklik))
        renk_toplami += tasinan_renk
        agirlik_toplami += tasinan_agirlik
        gozlem_sayisi += (tasinan_agirlik > 0.1).astype(np.uint16)
        # Uzun bitkiler düzlem üstündedir: ortalama, yaprakları çift gösterebilir.
        # Her piksel için en merkezi fotoğrafı seçmek bu gölgelenmeyi azaltır.
        daha_iyi = (tasinan_agirlik > en_iyi_agirlik) & (tasinan_agirlik > .001)
        secilen_rgb[daha_iyi] = np.clip(
            tasinan_renk[daha_iyi] / tasinan_agirlik[daha_iyi, None], 0, 255,
        ).astype(np.uint8)
        en_iyi_agirlik[daha_iyi] = tasinan_agirlik[daha_iyi]
        cv2.polylines(ayak_izleri, [hedef.astype(np.int32)], True, (127, 210, 246), 1, cv2.LINE_AA)
        kullanilanlar.append({'photo': kare['photo'], 'ground_corners_enu': koseler.tolist()})

    gecerli = agirlik_toplami > 0.001
    mozaik = np.zeros_like(renk_toplami, dtype=np.uint8)
    mozaik[gecerli] = np.clip(
        renk_toplami[gecerli] / agirlik_toplami[gecerli, None], 0, 255,
    ).astype(np.uint8)

    # 4) RGB mozaik ile gözlem sayısı farklı çıktılardır.
    cv2.imwrite(str(cikti / 'tarla_mozaik.png'), secilen_rgb)
    cv2.imwrite(str(cikti / 'tarla_mozaik_ortalama.png'), mozaik)
    cv2.imwrite(str(cikti / 'foto_ayak_izleri.png'), ayak_izleri)
    kaplama = cv2.applyColorMap(
        np.clip(gozlem_sayisi / 8 * 255, 0, 255).astype(np.uint8), cv2.COLORMAP_VIRIDIS,
    )
    kaplama[~gecerli] = 0
    cv2.imwrite(str(cikti / 'ortusme_haritasi.png'), kaplama)

    tarla = gozlem_sayisi[
        round((kuzey - 67) * PIKSEL_METRE):round((kuzey - 18) * PIKSEL_METRE),
        round((-30 - bati) * PIKSEL_METRE):round((30 - bati) * PIKSEL_METRE),
    ]
    metrikler = {
        'method': 'calibrated flat-plane projection from actual Gazebo RGB trigger images',
        'images_used': len(kullanilanlar), 'output_shape': [yukseklik, genislik],
        'pixels_per_meter': PIKSEL_METRE, 'bounds_local_enu_m': HARITA_SINIRLARI,
        'field_covered_fraction': float(np.mean(tarla > 0)),
        'field_overlap_3plus_fraction': float(np.mean(tarla >= 3)),
        'maximum_observations': int(gozlem_sayisi.max()),
        'source_ground_texture_used': False, 'scenario_stress_values_used': False,
        'flight_commands_sent': 0,
        'rgb_compositing': 'highest center-weight observation per pixel; weighted mean also saved for comparison',
        'limitations': 'Known simulator poses; z=0 plane, plant-height parallax; RGB appearance is not measured crop stress or NDVI.',
    }
    for ad, veri in [('mosaic_metrics.json', metrikler), ('mosaic_sources.json', kullanilanlar)]:
        (cikti / ad).write_text(json.dumps(veri, indent=2), encoding='utf-8')
    (cikti / 'tarla_mozaik.pgw').write_text(
        f'{1 / PIKSEL_METRE}\n0\n0\n{-1 / PIKSEL_METRE}\n{bati + .5 / PIKSEL_METRE}\n{kuzey - .5 / PIKSEL_METRE}\n',
    )
    if len(kullanilanlar) < 12 or metrikler['field_covered_fraction'] < .85:
        raise RuntimeError('Mozaik kapsaması yetersiz; uçuşu ve çekim kayıtlarını kontrol edin.')
    print(json.dumps(metrikler), flush=True)
    return metrikler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', nargs='?', help='AUTO tarla uçuşunun RESULT klasörü')
    build(parser.parse_args().run or input('Tarla uçuş klasörünü yapıştırın: '))


if __name__ == '__main__':
    main()
