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
.\.local\venv\Scripts\python.exe .\tools\reconstruct_3d.py "UCUS_KLASORU"
```

İlk komut **tarla haritalama**, ikinci komut **bina haritalama** uçuşundan sonra çalıştırılır. Sonuçlar uçuş klasöründeki `products` altına yazılır. Sabit kanat görüntü analizi menüden seçildiğinde kendiliğinden çalışır; örnek olaylar `products/motion` içindedir.

**Çıktıların anlamı:** tarla mozaiği bilinen simülasyon kamera pozlarıyla düzlem projeksiyonudur; bina çıktısı görüntü eşleşmelerinden seyrek nokta bulutudur. Bunlar tam DEM/yoğun mesh iş akışı veya ölçülmüş gerçek saha doğruluğu değildir. İlaçlama kaplaması gerçek pompa çıkışından hesaplanan ideal geometrik iş genişliğidir; damlacık fiziği ölçümü değildir. Hareket işçisi insan sınıflandırıcısı değildir; hareket adayları üretir ve yanlış alarm verebilir.

## Dosyalar

`worlds/`: üç taşınabilir dünya; `models/`: yerel 3D nesneler ve dokular; `missions/`: AUTO görevleri; `params/`: doğrulanan parametreler; `tools/`: kayıt ve görüntü işleme araçları. İndirmeler resmî sunuculardandır ve SHA256 ile kontrol edilir. Hazır EXE/DLL veya ZIP dağıtılmaz; yerel çıktılar `.local` içinde kalır.
