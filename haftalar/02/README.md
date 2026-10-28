# 2. hafta — AUTO görevler ve uygulamalar

[Güncel sunumu aç (v3 PDF · 93 sayfa)](Hafta-02-Sunum-v3.pdf) · [Düzenlenebilir PowerPoint](Hafta-02-Sunum.pptx) · [Eğitmen notları](Hafta-02-Egitmen-Notlari.txt)

İlk haftanın anlatım düzeniyle: **aracı ve kamerayı tanı → görevi planla → simülasyonda uygula → veriden ürün çıkar → sonucu değerlendir**. Önerilen süre: 80 dakika anlatım, 30 dakika canlı uygulama, 10 dakika değerlendirme.

| Uygulama | AUTO içinde yapılan | Görüntü / analiz çıktısı |
| --- | --- | --- |
| Araç ve kamera tanıtımı | 8m kalkış, üç gimbal açısı, bekleme, iniş | Gerçek RGB ve telemetri |
| Tarla ilaçlama | 9 şerit, pompa aç/kapa, dönüş, iniş | PWM ve ideal geometrik kaplama |
| Aynı tarlada 2D haritalama | Grid ve mesafeye bağlı kamera tetiği | Bilinen pozlarla düzlem mozaiği |
| 3D bina haritalama | İki orbit, sürekli ROI, mesafeli çekim | Trained Gaussian model ve novel-view render |
| Sabit kanatla kırsal gözlem | Otomatik kalkış, sabit tarama, otomatik iniş | Canlı hareket olayı, tam kare ve kırpım |

## Başlayın

1. İlk haftanın native Windows kurulumunu tamamlayın; VS Code'dan depoyu güncelleyin (**Git: Pull**).
2. [simulasyon/Kur.cmd](simulasyon/Kur.cmd) dosyasını bir kez çalıştırın.
3. [simulasyon/Baslat.cmd](simulasyon/Baslat.cmd) ile uygulamayı seçin.
4. Mission Planner'dan **TCP → 127.0.0.1 → 5760** ile bağlanın. İlgili `.waypoints` dosyasını açıp **Write WPs** ile araca yazın. Sensörler hazırken **AUTO → ARM** uygulayın.

Ayrıntılı ve kısa kullanım adımları: [Simülasyon rehberi](simulasyon/README.md). Hazır EXE/DLL veya ZIP paylaşılmaz; araçlar resmî adreslerden indirilir, kaynaklar bilgisayarınızda derlenir. Bu haftanın uçuş ve kurulum doğrulaması **Windows x64, Gazebo Jetty10.5.0, ArduCopter/ArduPlane4.7.2** üzerinde yapıldı. Linux'ta bu haftanın başlatıcısı doğrulanmış değildir.

## Doğrulanan sonuçlar

Tüm sahneler ve görevler **sunum hazırlanmadan önce** gerçek Gazebo/SITL uçuşlarıyla denendi. Son kayıtların tümünde silahlı uçuş AUTO modundaydı; görevler LAND ve disarm ile tamamlandı. Force-arm veya uçuş konum/hız setpointi kullanılmadı. Öğrenci başlatıcısı pasiftir; uçuşu Mission Planner operatörü başlatır. Python uçuş rotasını değiştirmez.

- **İlaçlama:** 9 pompa açık bölümü; 8m ideal iş genişliğiyle hedef alanın %100 kaplaması. İlk denemedeki %82,86 kaplama, şerit sayısı ve uç noktalar değiştirilip yeniden uçularak düzeltildi.
- **2D tarla:** 81 tetik / 81 gerçek fotoğraf, %100 alan kaplama; en az üç görüntülü alan %99,53. Mozaik 912×744 piksel.
- **Bina:** 108 fotoğraf; 94training /14hold-out. Sparse noktalar yalnız initialization içindir; ana çıktı **3D Gaussian Splatting** modelidir. İdeal gimbalda ROI doğrultu hatası medyan0,318°, %95 değeri0,724°. [Güncel Gaussian metrikleri](dogrulama/gaussian_validation.json) ve [hazır model](ornekler/Bina-Gaussian.ply).
- **Sabit kanat:** canlı analizde 23 hareket olayı; 19 olay sonradan bağımsız simülasyon kişi kutusuyla ilişkilendirildi, 4 yanlış alarm görüldü. İlk olaydan yaklaşık317s sonra AUTO iniş tamamlandı; hedefe son yatay uzaklık4,11m.
- **Kurulum:** ayrı öğrenci Python ortamında ilk kurulum ve tekrar kurulum; GUI; operatör5760 + pasif gözlemci5762 akışı denendi.

Metrikler ve kanıt özeti: [dogrulama/final_summary.json](dogrulama/final_summary.json). Görsellerin hangi gerçek kayıttan geldiği ve SHA256 değerleri: [provenance.json](sunum/gorseller/provenance.json).

**28 Ekim revizyonu:** bina örneği sparse point cloud yerine gerçek Gaussian Splatting optimizasyonuna geçirildi. Sunumda yerleşik İngilizce teknik terimler korundu; camera footprint, overlap, NAV/DO zamanlaması, Gaussian projection, alpha compositing ve motion compensation için yeni şemalar eklendi. Tekrarlanan kart düzenleri; bölüm açılışları, büyük görseller, zoom/crop, checkpoint ve reference/render karşılaştırmalarıyla çeşitlendirildi.

**Görsel anlatım revizyonu (v3):** yalnız tablo, liste, işlem adımları, formül veya sayılardan oluşan **40 sayfanın tamamına**, built-in **image_gen** ile konuya özel açıklayıcı çizimler üretildi. Tablolar, komutlar ve açıklamalar düzenlenebilir metin olarak korundu; görseller yanlarına yerleştirildi. Sunum **93 sayfa** olarak kaldı. Çizimler “Kavramsal çizim · AI” etiketi taşır; gerçek simülasyon kaydı veya ölçülmüş çıktı olarak sunulmaz. [Görseller ve üretim promptları](sunum/uretilen_gorseller/README.md) · [Görsel kökenleri](sunum/uretilen_gorseller/provenance.json).

**Sonuçların kapsamı:** mozaik düz zemin ve bilinen simülasyon pozlarını kullanır; DEM ortofotosu veya ölçülmüş saha doğruluğu değildir. Gaussian model görünüş üretir; triangle mesh değildir. Kamera pozları Gazebo'dan bilinir; image-estimated SfM yapılmış gibi sunulmaz. Gimbal ideal kinematiktir. İlaçlama damlacık fiziği veya gerçek debi ölçümü değildir. Hareket işçisi insan sınıflandırıcısı değildir; olay sayıları kişi sayısı veya genel precision/recall sonucu değildir.

**3D'yi hemen açın:** `simulasyon/3D_Goster.cmd`. Kendi bina uçuşunuzdan üretin: `simulasyon/3D_Uret.cmd`.

## Eğitmen için

[Uygulama ve test adımları](EGITMEN.md) · [Hazırlık / iterasyon kaydı](CALISMA_KAYDI.md) · [Kaynaklar](KAYNAKLAR.md) · [Sunum üretim kaynağı](sunum/kaynak/)

Öğrenci teslimi: değiştirilmiş görev dosyası, uçuş grafiği/iniş kanıtı, bir uygulama ürünü, bir sayısal ölçüm ve bir sınırlama. Ham kayıtların tamamını paylaşmak gerekmez.
