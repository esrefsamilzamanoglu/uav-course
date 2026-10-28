# 2. hafta — AUTO uygulamaları

İlk haftadaki **native Windows Gazebo Jetty10.5.0 + ArduCopter4.7.2** kurulumu kullanılır. Sabit kanat için aynı sürüm ailesindeki **ArduPlane4.7.2** resmî sunucudan indirilir. İlk hafta dosyaları değiştirilmez.

## Bir kez kurun

1. İlk haftanın kurulumunu tamamlayın; açık simülasyon oturumunu kapatın.
2. Bu klasörde **`Kur.cmd`** dosyasını açın ve tamamlanmasını bekleyin. Kamera ve görüntü işleme araçları hazırlanır; ek Gazebo eklentisi bilgisayarınızda derlenir.
3. **`Baslat.cmd`** dosyasını açın ve uygulamayı seçin.

| Seçim | Uygulama | Mission Planner'a yüklenecek dosya |
| --- | --- | --- |
| 0 | Araç/kamera tanıtımı | `missions/00_kamera_tanitimi.waypoints` |
| 1 | Tarla ilaçlama | `missions/01_tarla_ilaclama.waypoints` |
| 2 | Aynı tarlada 2D haritalama | `missions/02_tarla_2d_haritalama.waypoints` |
| 3 | Bina çevresinde 3D veri toplama | `missions/03_bina_3d_haritalama.waypoints` |
| 4 | Sabit kanatla hareket gözlemi | `missions/04_sabit_kanat_gozetim.waypoints` |

## Görevi başlatın

Gazebo açılınca Mission Planner'dan **TCP → `127.0.0.1` → `5760`** ile bağlanın. **Plan** ekranında seçtiğiniz görev dosyasını açıp araca yazın. Sensörlerin hazır olduğu mesajını bekleyin; **AUTO** modunu seçip **ARM** edin.

Rotayı, kalkışı, görev komutlarını ve inişi ArduPilot yürütür. Başlatıcı uçuşu başlatmaz. Python, ikinci bağlantıdan yalnız telemetri/fotoğraf kaydeder; sabit kanat uygulamasında ayrıca görüntüleri işler. Mission Planner'ın **SIMULATION** sekmesinden ikinci SITL açmayın.

Görev tamamlandığında sonuç klasörünün yolu terminalde görünür. Tekrar uçuş için başlatıcıyı yeniden açın. Oturumu erken bitirmek için terminalde `Ctrl+C` kullanın.

## Görüntülerden ürün üretin

Uçuş bittiğinde terminaldeki `RESULT` yolunun bulunduğu klasör **uçuş klasörünüzdür**. Aşağıdaki komutlarda `UCUS_KLASORU` yerine bu klasörü yazın:

```powershell
.\.local\venv\Scripts\python.exe .\tools\mosaic_2d.py "UCUS_KLASORU"
```

Bu komut **tarla haritalama** uçuşundan sonra çalıştırılır. Sonuçlar uçuş klasöründeki `products` altına yazılır. Sabit kanat görüntü analizi menüden seçildiğinde kendiliğinden çalışır; örnek olaylar `products/motion` içindedir.

## Bina için gerçek Gaussian Splatting

1. Menü **3** ile bina AUTO görevini uçurun; LAND tamamlanınca terminaldeki uçuş klasörünü saklayın.
2. **`3D_Uret.cmd`** dosyasını açın ve bu uçuş klasörünü yapıştırın. Resmî [Brush0.3.0](https://github.com/ArthurBrussee/brush/releases/tag/v0.3.0) aracı yerelde hazırlanır; fotoğraflardan initialization, Gaussian training ve hold-out değerlendirmesi yapılır.
3. Biten model Brush viewer'da açılır. Orbit ve zoom ile cepheleri, çatıyı ve kalan artefact'ları inceleyin.

Hazır ders örneğini hemen görmek için **`3D_Goster.cmd`** dosyasını açın. [Örnek Gaussian PLY](../ornekler/Bina-Gaussian.ply), gerçek Gazebo fotoğraflarından eğitilmiş modeldir. CUDA kurulumu gerekmez; referans test Intel UHD730 bulunan bu Windows bilgisayarda yapıldı. Training süresi donanıma bağlıdır. Resmî araç arşivi otomatik indirilir ve SHA256 kontrolünden geçer; öğrenciye ZIP/EXE paketi dağıtılmaz.

Varsayılan çalışma: **640×427 RGB, 6 000 steps, en fazla45 000 Gaussians, SH degree2**. 108fotoğrafın94'ü train,14'ü hold-out'tur. Hold-out kareler sparse initialization'a da verilmez. Camera pose simülatörden bilinir; bina mesh'i okunmaz. Çıktılar `products/gaussian/training` altındadır; `export_6000.ply`, `gaussian_metrics.json` ve `eval_6000/` incelemeye hazırdır. Eski `reconstruct_3d.py` artık ana ürün yerine sparse initialization aşamasını sağlar.

**Çıktıların anlamı:** tarla mozaiği bilinen simülasyon kamera pozlarıyla düzlem projeksiyonudur. Yeni bina çıktısı optimize edilmiş **3D Gaussian radiance representation**'dır; dolu görünüş render eder, watertight triangle mesh veya ölçülmüş geometric accuracy değildir. İlaçlama kaplaması gerçek pompa çıkışından hesaplanan ideal geometrik iş genişliğidir; damlacık fiziği ölçümü değildir. Hareket işçisi insan sınıflandırıcısı değildir; hareket adayları üretir ve yanlış alarm verebilir.

## Dosyalar

`worlds/`: üç taşınabilir dünya; `models/`: yerel 3D nesneler ve dokular; `missions/`: AUTO görevleri; `params/`: doğrulanan parametreler; `tools/`: kayıt ve görüntü işleme araçları. İndirmeler resmî sunuculardandır ve SHA256 ile kontrol edilir. Hazır EXE/DLL veya ZIP dağıtılmaz; yerel çıktılar `.local` içinde kalır.
