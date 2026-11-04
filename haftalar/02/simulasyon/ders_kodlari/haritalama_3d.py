"""AUTO orbit fotoğrafları → initialization → 3D Gaussian training → hold-out.

Uçuş rotası, kamera trigger ve ROI görev dosyasıyla ArduPilot'ta yürütülür.
Bu dosya uçuş sonrasında fotoğrafları işler; araca bağlantı veya komut yoktur.
Derste önce train() içindeki dört aşamayı, sonra eğitim döngüsünü inceleyin.
"""
from __future__ import annotations

if __package__:
    from . import _ortak
else:
    import _ortak

import argparse
import json
import os
from pathlib import Path
import subprocess
import time

# Kalibrasyon, SfM initialization ve araç indirmesi ayrı altyapı yardımcıları.
from export_splat_dataset import export
from gaussian_metrics import evaluate
from install_gaussian import install

EGITIM_ADIMI = 6000
GORUNTU_GENISLIGI = 640
EN_FAZLA_GAUSSIAN = 45000


def brush_komutu(exe, dataset, training, steps, width, max_splats):
    """Python optimizer yazmaz; resmi Brush optimizer'ını bu ayarlarla çağırır."""
    return [
        str(exe), str(dataset),
        '--total-steps', str(steps),
        '--max-splats', str(max_splats),
        '--max-resolution', str(width),
        '--sh-degree', '2',
        '--refine-every', '100',
        '--growth-stop-iter', str(round(steps * .8)),
        '--growth-select-fraction', '0.3',
        '--eval-split-every', '8',  # Her 8. kare hold-out; initialization'a da girmez.
        '--eval-every', '1000',
        '--eval-save-to-disk',
        '--export-every', '1000',
        '--export-path', str(training),
    ]


def egitimi_calistir(komut, training, log_yolu, steps):
    """Checkpoint'leri izle; hata veya Ctrl+C durumunda yalnız kendi işini kapat."""
    baslangic = time.monotonic()
    son_checkpoint = 0
    son_mesaj = baslangic
    pencere = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with log_yolu.open('wb') as log:
        islem = subprocess.Popen(komut, stdout=log, stderr=subprocess.STDOUT, creationflags=pencere)
        try:
            while islem.poll() is None:
                checkpoints = [int(p.stem.split('_')[-1]) for p in training.glob('export_*.ply')]
                guncel = max(checkpoints, default=0)
                if guncel > son_checkpoint:
                    print(f'Checkpoint: {guncel}/{steps}', flush=True)
                    son_checkpoint = guncel
                if time.monotonic() - son_mesaj > 30:
                    dakika = (time.monotonic() - baslangic) / 60
                    print(f'Training: {dakika:.1f} dakika | checkpoint {guncel}/{steps}', flush=True)
                    son_mesaj = time.monotonic()
                time.sleep(3)
        except BaseException:
            islem.terminate()
            islem.wait(timeout=20)
            raise
        if islem.returncode:
            raise RuntimeError(f'Brush durdu. Ayrıntı: {log_yolu}')


def train(run, steps=EGITIM_ADIMI, width=GORUNTU_GENISLIGI,
          max_splats=EN_FAZLA_GAUSSIAN, viewer=False):
    ucus = Path(str(run).strip('"')).resolve()
    if ucus.is_file():
        ucus = ucus.parent
    if not (ucus / 'photo_manifest.json').is_file():
        raise RuntimeError('Bina uçuşunun RESULT klasörünü seçin.')
    # Checkpoint ve değerlendirme bu ders akışında 1000 adım aralıklarıyladır.
    if steps < 1000 or steps % 1000 or width < 64 or max_splats < 100:
        raise ValueError('steps en az 1000 ve 1000 katı; width ≥64; max_splats ≥100 olmalı.')
    cikti = ucus / 'products/gaussian'
    training = cikti / 'training'
    if training.exists():
        raise RuntimeError('Bu uçuşun 3D çıktısı zaten var; yeni uçuş veya ayrı kopya kullanın.')

    # 1) Resmî araç + RGB/pose dataset. Pozlar simülatörden bilinir.
    exe = install()
    dataset = export(ucus, cikti / 'dataset', width=width)
    # export(), train karelerinden image-derived sparse initialization üretir.
    # Kaynak bina mesh'i okunmaz; hold-out görüntüler initialization'a verilmez.

    # 2) Sparse noktalar final ürün değildir: Gaussian optimizer başlatılır.
    training.mkdir(parents=True)
    komut = brush_komutu(exe, dataset, training, steps, width, max_splats)
    baslangic = time.monotonic()
    print('3D Gaussian training başladı. Uçuşa komut gönderilmez.', flush=True)
    egitimi_calistir(komut, training, cikti / 'brush.log', steps)

    # 3) Training'de görülmeyen açılarda render kalitesi: PSNR / SSIM.
    metrikler = evaluate(dataset, training, steps)
    (cikti / 'session.json').write_text(json.dumps({
        'command': komut, 'elapsed_s': time.monotonic() - baslangic,
        'source_run': ucus.name, 'metrics_passed': metrikler['passed'],
        'flight_control_commands_sent': 0,
    }, indent=2), encoding='utf-8')

    # 4) Gaussian görünüş modelini viewer'da orbit/zoom ile incele.
    model = training / f'export_{steps}.ply'
    if not model.is_file():
        raise RuntimeError(f'Beklenen Gaussian model oluşmadı: {model}')
    print('GAUSSIAN_RESULT=' + str(model), flush=True)
    if viewer:
        subprocess.Popen([str(exe), str(model), '--with-viewer'],
                         creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', nargs='?', help='Bina uçuşunun RESULT klasörü')
    parser.add_argument('--steps', type=int, default=EGITIM_ADIMI)
    parser.add_argument('--width', type=int, default=GORUNTU_GENISLIGI)
    parser.add_argument('--max-splats', type=int, default=EN_FAZLA_GAUSSIAN)
    parser.add_argument('--viewer', action='store_true')
    args = parser.parse_args()
    run = args.run or input('Bina uçuş klasörünü yapıştırın: ')
    train(run, args.steps, args.width, args.max_splats, args.viewer)


if __name__ == '__main__':
    main()
