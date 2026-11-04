"""AUTO uçuş sürerken hareketli kameradan hareket adayları çıkar.

Derste okuma sırası: Detector.process() → özellik eşleme → homography →
hizalanmış görüntü farkı → aday bölgeler → zamansal takip → olay kaydı.

Girdi yalnız RGB kareler ve okunmuş görev/irtifa bilgisidir. MAVLink bağlantısı
kurulmaz; rota, mod veya setpoint komutu gönderilmez. Bu bir insan sınıflandırıcısı
değildir: ağaçlar, parallax ve gölgeler yanlış alarm üretebilir.
"""
from __future__ import annotations

if __package__:
    from . import _ortak
else:
    import _ortak

import argparse
import bisect
import json
from pathlib import Path
import time

import cv2
import numpy as np

# Bu yardımcı yalnız olay bulunduktan SONRA çağrılır; Detector bunu kullanmaz.
from motion_evaluation import evaluate_bbox

EN_AZ_ESLESME = 25
RANSAC_HATASI_PIKSEL = 2.5
EN_AZ_IRTIFA_M = 25
KARE_ARALIGI_S = .38
AYNI_OLAY_ARALIGI_S = 2


class Detector:
    """Kamera hareketini telafi et; zemine göre hareket eden küçük bölgeleri izle."""

    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=4000, fastThreshold=3, edgeThreshold=12)
        self.match = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.tracks = []
        self.next_id = 1

    def kamera_hareketi(self, previous, current, stats):
        """1) ORB + ratio test + RANSAC ile baskın zemin dönüşümünü bul."""
        gri_once = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
        gri_simdi = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
        noktalar_a, tanimlar_a = self.orb.detectAndCompute(gri_once, None)
        noktalar_b, tanimlar_b = self.orb.detectAndCompute(gri_simdi, None)
        stats.update(keypoints_previous=len(noktalar_a), keypoints_current=len(noktalar_b))
        if tanimlar_a is None or tanimlar_b is None:
            stats['skip'] = 'few_features'
            return None

        ikililer = self.match.knnMatch(tanimlar_a, tanimlar_b, k=2)
        iyi = [pair[0] for pair in ikililer
               if len(pair) == 2 and pair[0].distance < .74 * pair[1].distance]
        stats['matches'] = len(iyi)
        if len(iyi) < EN_AZ_ESLESME:
            stats['skip'] = 'few_matches'
            return None

        kaynak = np.float32([noktalar_a[m.queryIdx].pt for m in iyi])
        hedef = np.float32([noktalar_b[m.trainIdx].pt for m in iyi])
        homography, inliers = cv2.findHomography(
            kaynak, hedef, cv2.RANSAC, RANSAC_HATASI_PIKSEL,
            maxIters=2500, confidence=.995,
        )
        if homography is None or inliers is None or np.mean(inliers) < .5:
            stats['skip'] = 'unstable_homography'
            return None
        stats.update(inliers=int(np.sum(inliers)), inlier_fraction=float(np.mean(inliers)))
        return homography

    @staticmethod
    def hareket_maskesi(previous, current, homography, stats):
        """2) Önce kamerayı hizala; sonra kalan renk farkına adaptif eşik uygula."""
        h, w = current.shape[:2]
        hizali = cv2.warpPerspective(previous, homography, (w, h))
        gecerli = cv2.warpPerspective(np.ones((h, w), np.uint8) * 255, homography, (w, h))
        gecerli = cv2.erode(gecerli, np.ones((11, 11), np.uint8))
        gecerli[:12] = gecerli[-12:] = 0
        gecerli[:, :12] = gecerli[:, -12:] = 0

        once = cv2.GaussianBlur(hizali, (3, 3), .65).astype(np.int16)
        simdi = cv2.GaussianBlur(current, (3, 3), .65).astype(np.int16)
        fark = np.max(np.abs(once - simdi), axis=2).astype(np.uint8)
        degerler = fark[gecerli > 0]
        if not len(degerler):
            stats['skip'] = 'no_overlap'
            return None
        medyan = float(np.median(degerler))
        mad = float(np.median(np.abs(degerler - medyan)))
        esik = max(19, medyan + 6 * max(mad, 1))
        stats['threshold'] = esik
        maske = ((fark > esik) & (gecerli > 0)).astype(np.uint8) * 255
        return cv2.morphologyEx(maske, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

    @staticmethod
    def aday_bolgeler(maske):
        """3) Çok küçük/büyük bölgeleri ele; henüz insan etiketi verme."""
        _, _, bolgeler, _ = cv2.connectedComponentsWithStats(maske)
        adaylar = []
        for x, y, w, h, alan in bolgeler[1:]:
            if 7 <= alan <= 700 and 2 <= w <= 60 and 4 <= h <= 75 and .10 < w / max(h, 1) < 3:
                adaylar.append({
                    'bbox': [int(x), int(y), int(w), int(h)],
                    'center': np.array([x + w / 2, y + h / 2]), 'area': int(alan),
                })
        return adaylar

    def takip_et(self, adaylar, homography):
        """4) Aynı aday birkaç karede kalıyor ve zemine göre yer değiştiriyor mu?"""
        eslesenler = set()
        dogrulananlar = []
        for iz in self.tracks:
            merkez = iz['center'].reshape(1, 1, 2).astype(np.float32)
            tahmin = cv2.perspectiveTransform(merkez, homography)[0, 0]
            secenekler = [(float(np.linalg.norm(a['center'] - tahmin)), i)
                         for i, a in enumerate(adaylar) if i not in eslesenler]
            uzaklik, index = min(secenekler, default=(1e9, None))
            if uzaklik < 23:
                aday = adaylar[index]
                eslesenler.add(index)
                iz.update(center=aday['center'], bbox=aday['bbox'], hits=iz['hits'] + 1, lost=0)
                iz['motion'] += uzaklik
                if iz['hits'] >= 2 and iz['motion'] >= 1.2:
                    dogrulananlar.append(dict(iz))
            else:
                iz['center'] = tahmin
                iz['lost'] += 1
        self.tracks = [iz for iz in self.tracks if iz['lost'] < 3]
        for i, aday in enumerate(adaylar):
            if i not in eslesenler:
                self.tracks.append({
                    'id': self.next_id, 'center': aday['center'], 'bbox': aday['bbox'],
                    'hits': 1, 'lost': 0, 'motion': 0.,
                })
                self.next_id += 1
        return dogrulananlar

    def process(self, previous, current):
        """Ana algoritma: kamera hareketi → fark → aday → takip."""
        stats = {}
        homography = self.kamera_hareketi(previous, current, stats)
        if homography is None:
            self.tracks = []
            return [], None, stats
        maske = self.hareket_maskesi(previous, current, homography, stats)
        if maske is None:
            return [], None, stats
        adaylar = self.aday_bolgeler(maske)
        bulunanlar = self.takip_et(adaylar, homography)
        stats.update(residual_candidates=len(adaylar), confirmed=len(bulunanlar))
        return bulunanlar, maske, stats


def json_satirlarini_oku(path):
    """Canlı kaydın son satırı henüz bitmemiş olabilir; tamamını bekle."""
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def olay_kaydet(out, index, det, image, frame, state, mask):
    """5) Tam kare, yakın kırpım ve residual kaydet; uçuşa komut gönderme."""
    x, y, w, h = det['bbox']
    pad = 9
    x0, y0 = max(x - pad, 0), max(y - pad, 0)
    x1, y1 = min(x + w + pad, image.shape[1]), min(y + h + pad, image.shape[0])
    box = [x0, y0, x1 - x0, y1 - y0]
    annotated = image.copy()
    cv2.rectangle(annotated, (x0, y0), (x1, y1), (55, 225, 110), 2)
    cv2.putText(annotated, f'MOTION CANDIDATE {det["id"]} - AUTO route unchanged',
                (max(10, x0 - 20), max(25, y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX,
                .5, (55, 225, 110), 1, cv2.LINE_AA)
    cv2.imwrite(str(out / f'event_{index:04d}.png'), annotated)
    cv2.imwrite(str(out / 'crops' / f'{index:04d}.png'), image[y0:y1, x0:x1])
    if mask is not None:
        cv2.imwrite(str(out / f'residual_{index:04d}.png'), mask)
    # Simülatör kişi konumu SADECE bu son değerlendirmede kullanılır.
    evaluation = evaluate_bbox(box, frame)
    return {
        'index': index, 'track': det['id'], 'sim_time': frame['sim_time'],
        'source': frame['frame'], 'source_wall_time': frame['wall_time'],
        'detected_wall_time': time.time(), 'source_mission_seq': state['seq'],
        'source_mavlink_mode': state['mode'], 'bbox': box, 'hits': det['hits'],
        'relative_motion_pixels': det['motion'], 'evaluation_only': evaluation,
    }


def run_detector(run, follow=False, output_name='motion'):
    """Kayıt üstünde tekrar işle veya --follow ile canlı dosyaları takip et."""
    run = Path(str(run).strip('"')).resolve()
    out = run / 'products' / output_name
    if Path(output_name).name != output_name or output_name in ('', '.', '..'):
        raise ValueError('output-name yalnız bir klasör adı olmalı.')
    out.mkdir(parents=True, exist_ok=False)  # Önceki olayların üzerine yazma.
    (out / 'crops').mkdir()
    mission = json.loads((run / 'mission.json').read_text())
    scan_sequences = {a['seq'] for a in mission['items'] if a['label'].startswith('SCAN_')}
    detector = Detector()
    previous = previous_frame = None
    seen, events, stats, last_emit = set(), [], [], {}
    ignored = 0
    idle_since = time.monotonic()
    calibration = run / 'camera_calibration.json'
    fov = json.loads(calibration.read_text())['horizontal_fov'] if calibration.exists() else None

    while True:
        telemetry = json_satirlarini_oku(run / 'telemetry.jsonl')
        flight = {}
        try:
            flight = json.loads((run / 'flight.json').read_text())
        except (OSError, json.JSONDecodeError):
            pass
        if not telemetry:
            telemetry = flight.get('telemetry', [])
        if not telemetry:
            if follow:
                time.sleep(.5)
                continue
            raise RuntimeError('Tarama fazını ayırmak için kayıtlı telemetri gerekli.')
        clocks = [t['wall_time'] for t in telemetry]
        progressed = False

        for frame in json_satirlarini_oku(run / 'camera.jsonl'):
            if fov is not None:
                frame['horizontal_fov'] = fov
            if frame['frame'] in seen:
                continue
            if follow and frame['wall_time'] > clocks[-1] + .4:
                break  # Bu karenin telemetrisi henüz dosyaya yazılmamış.
            seen.add(frame['frame'])
            index = max(0, bisect.bisect_right(clocks, frame['wall_time']) - 1)
            state = telemetry[index]

            # AUTO tarama bacağı dışında takip sıfırlanır; rota değiştirilmez.
            if state['seq'] not in scan_sequences or not state['armed']:
                ignored += 1
                previous = previous_frame = None
                detector.tracks = []
                continue
            if state['altitude_m'] < EN_AZ_IRTIFA_M:
                continue
            if previous_frame and frame['sim_time'] - previous_frame['sim_time'] < KARE_ARALIGI_S:
                continue
            image = cv2.imread(str(run / frame['frame']))
            if image is None:
                continue
            progressed = True

            if previous is not None:
                detections, mask, info = detector.process(previous, image)
                stats.append({'sim_time': frame['sim_time'], **info})
                for det in detections:
                    if frame['sim_time'] - last_emit.get(det['id'], -1e6) < AYNI_OLAY_ARALIGI_S:
                        continue
                    last_emit[det['id']] = frame['sim_time']
                    event = olay_kaydet(out, len(events), det, image, frame, state, mask)
                    events.append(event)
                    with (out / 'events.jsonl').open('a') as stream:
                        stream.write(json.dumps(event) + '\n')
                    print(json.dumps({'motion_event': event['index'], 'sim_time': frame['sim_time'],
                                      'bbox': event['bbox']}), flush=True)
            previous, previous_frame = image, frame

        if progressed:
            idle_since = time.monotonic()
        finished = bool(flight) and flight.get('status') != 'running'
        if not follow or (finished and not progressed and time.monotonic() - idle_since > 3):
            break
        time.sleep(.5)

    report = {
        'method': 'ORB + RANSAC ground homography + compensated residual + temporal persistence',
        'processed_pairs': len(stats), 'events': len(events),
        'true_positive_events_against_independent_simulator_truth': sum(
            e['evaluation_only']['true_positive'] for e in events),
        'flight_commands_sent': 0, 'uses_ground_truth_for_detection': False,
        'uses_ground_truth_for_evaluation': True, 'uses_simulator_target_positions_for_detection': False,
        'analysis_state_source': 'read-only autopilot mission index and altitude',
        'active_auto_mission_sequences': sorted(scan_sequences), 'transit_frames_ignored': ignored,
        'limitations': 'Motion candidates, not a human classifier. Parallax, shadows and poor homographies can cause false positives.',
    }
    (out / 'metrics.json').write_text(json.dumps(report, indent=2))
    (out / 'processing.json').write_text(json.dumps(stats, indent=2))
    print(json.dumps(report), flush=True)
    if not events or report['true_positive_events_against_independent_simulator_truth'] < 1:
        raise RuntimeError('Doğrulanmış hareket olayı bulunamadı; kayıt ve eşikleri inceleyin.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Sabit kanat uçuşunun RESULT klasörü')
    parser.add_argument('--follow', action='store_true', help='Canlı yazılan RGB ve telemetriyi izle')
    parser.add_argument('--output-name', default='motion', help='products altında yeni çıktı klasörü')
    args = parser.parse_args()
    run_detector(args.run, args.follow, args.output_name)


if __name__ == '__main__':
    main()
