# 2. hafta — simülasyonu çalıştırın

İlk haftanın **Windows x64 · Gazebo Jetty 10.5.0 · ArduCopter 4.7.2** kurulumunu kullanın. ArduPlane 4.7.2 ve ek araçlar resmî adreslerinden alınır.

## Kurulum ve uçuş

1. Açık simülasyon oturumunu kapatın, **Kur.cmd** dosyasını bir kez çalıştırın. Kamera/görüntü işleme ortamı ve yerel Gazebo eklentisi hazırlanır.
2. **Baslat.cmd** dosyasını açıp uygulamayı seçin.
3. Mission Planner'dan **TCP → 127.0.0.1 → 5760** ile bağlanın.
4. **Plan** ekranında aşağıdaki görev dosyasını açın; **Write WPs** ile araca yazın.
5. Sensörler hazırken **AUTO** modunu seçip **ARM** edin. Kalkıştan inişe kadar görevi ArduPilot yürütür.

| Menü | Uygulama | Görev dosyası |
| --- | --- | --- |
| 0 | Kamera tanıtımı | `missions/00_kamera_tanitimi.waypoints` |
| 1 | Tarla ilaçlama | `missions/01_tarla_ilaclama.waypoints` |
| 2 | 2D tarla haritalama | `missions/02_tarla_2d_haritalama.waypoints` |
| 3 | 3D ev haritalama | `missions/03_bina_3d_haritalama.waypoints` |
| 4 | Sabit kanat gözlem | `missions/04_sabit_kanat_gozetim.waypoints` |

Mission Planner'ın SIMULATION sekmesinden ikinci SITL açmayın. Başlatıcı görevi kendiliğinden başlatmaz; Python pasif telemetri/görüntü kaydı yapar. Uçuş sonunda terminalde **RESULT** klasörünü saklayın. Oturumu bitirmek için terminalde `Ctrl+C` kullanın.

## Görüntülerden sonuç üretin

- **Tarla:** `2D_Uret.cmd` açın; tarla haritalama uçuşunun RESULT klasörünü yapıştırın. `products/tarla_mozaik.png` RGB mozaiğidir. Ortalama mozaik ve örtüşme haritasını da karşılaştırın.
- **Ev:** `3D_Uret.cmd` açın; ev uçuşunun RESULT klasörünü yapıştırın. Gerçek fotoğraflardan sparse initialization ve Gaussian training yapılır. Biten model viewer'da açılır.
- **Hazır 3D model:** `3D_Goster.cmd` açın; yeniden eğitim beklemeden [ders örneğini](../ornekler/README.md) inceleyin.
- **Sabit kanat:** menüde görüntü analizini seçin. Olay görüntüleri uçuş klasöründeki `products/motion` içine kaydedilir; araç AUTO görevine devam eder.

Asıl algoritmalar [ders_kodlari](ders_kodlari/README.md) klasöründedir. Kurulum, kayıt ve geometri yardımcıları `tools/`; dünyalar `worlds/`; 3D nesneler/dokular `models/`; AUTO görevleri `missions/` içindedir. `src/` yerelde derlenecek kamera/sahne eklentisidir ve kurulum için gereklidir. Kendi kayıtlarınız `.local/` içinde kalır.

## Çıktıları yorumlayın

Tarla 1 575 bitki ve bölgesel renk/boy çeşitliliği içerir. Mozaik yalnız kaydedilmiş RGB'yi kullanır; sentetik sararma gerçek NDVI veya tarımsal stres ölçümü değildir. Düz zemin varsayımı bitkilerde parallax bırakabilir.

Ev, taş/sıva cepheli, kiremit çatılı, panjurlu ve balkonlu gerçek 3D geometridir. Varsayılan Gaussian çalışması **640×427 RGB, 6 000 steps, en fazla 45 000 Gaussians, SH degree 2** kullanır. Referans uçuşta 108 fotoğrafın 94'ü train, 14'ü hold-out'tur; hold-out fotoğraflar initialization'a da verilmez. Kamera pozları Gazebo'dan bilinir, bina mesh'i eğitimde okunmaz. `products/gaussian/training` içinde PLY, render ve metrikler oluşur. Model görünüş üretir; watertight mesh değildir.

[Brush 0.3.0](https://github.com/ArthurBrussee/brush/releases/tag/v0.3.0) otomatik indirilip SHA256 ile doğrulanır. CUDA kurulumu gerekmez; eğitim süresi ve çalışabilirlik GPU/sürücüye bağlıdır. Referans deneme Intel UHD 730 ile yapılmıştır. İlaçlama sonucu ideal iş genişliğidir, damlacık fiziği değildir. Hareket kodu hareket adaylarını işaretler; insan tanıma modeli değildir.
