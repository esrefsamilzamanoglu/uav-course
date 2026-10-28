# 2. hafta — eğitmen uygulama rehberi

## Dersten önce

İlk hafta kurulumunu açıp kapatın. Depoyu güncelleyin; bu haftanın `simulasyon/Kur.cmd` adımını tamamlayın. Birden fazla Gazebo/SITL oturumu açmayın. İlk hafta çalışma dosyaları değiştirilmez; ikinci haftanın ayrı yerel çalışma alanı `.local` altındadır.

Sunum 93 sayfadır. Slayt başına tek ana fikir, gerçek simülasyon görselleri, çalışma şemaları ve konuşmacı notları vardır. v3'te yalnız metin/tablo/işlem/formül/sayısal kart içeren 40 sayfanın tamamına built-in image_gen ile açıklayıcı çizimler eklendi. Tablolar ve komutlar düzenlenebilir metindir. “Kavramsal çizim · AI” etiketli görseller mekanizmayı açıklar; ölçülmüş geometri, gerçek uçuş ekranı veya model kalitesinin kanıtı değildir. Gerçek rota ve ürünler ilgili kayıt/grafik/render sayfalarında gösterilir. Bölüm açılışları, büyük görüntüler, zoom/crop, checkpoint ve reference/render karşılaştırmaları kullanılır. Yerleşik İngilizce terimler ilk geçtiğinde kısa Türkçe açıklamayla tanıtılır.

## Canlı ders sırası

| Slaytlar | Uygulama | Bakılacak kanıt |
| --- | --- | --- |
| 9–17 | Menü0: araç/kamera | 8m; −90/−45/−20°; AUTO iniş |
| 23–33 | Menü1: ilaçlama | Şerit başında aç; dönüşte kapat; 9 PWM bloğu |
| 34–46 | Menü2: tarla haritalama | Mesafe tetiği; fotoğraf sayısı; mozaik |
| 47–66 | Menü3: bina /3DGS | İki orbit; ROI; gerçek Gaussian training; viewer |
| 67–85 | Menü4: sabit kanat | AUTO kalkış/iniş; canlı olay; sabit rotanın korunması |
| 86–93 | Değerlendirme | Ürün, metrik, hata/düzeltme ve kapsam |

Öğrenci menüsü **uçuş komutu göndermez**. Gözlemci5762'den kayıt alır. Mission Planner5760'da görevi yazıp sensörlerin hazır olmasını bekleyen operatör **AUTO → ARM** yapar. Test edilen bu simülasyon ayarlarında `AUTO_OPTIONS3` normal AUTO arm ve kalkışa izin verir. Gerçek araç konfigürasyonu önerisi değildir.

## Tekrar edilebilir öğretmen testleri

PowerShell'i `haftalar/02/simulasyon` klasöründe açın. Aşağıdaki ilk komut **yalnız yerel simülasyonu** açar, görevi otomatik yükler ve normal arm/start uygular. İlk argümanı `intro`, `spray`, `mapping`, `building` veya `plane` yapabilirsiniz. İkinci bir SITL'ye bağlanmaz. Öğrenci menüsünden farklı olarak operatör adımlarını otomatikleştirir.

```powershell
.\.local\venv\Scripts\python.exe .\tools\fly_auto.py mapping --gui
```

Sabit kanatta canlı işçiyi de açmak için:

```powershell
.\.local\venv\Scripts\python.exe .\tools\fly_auto.py plane --gui --vision
```

Terminaldeki `RESULT=.../flight.json` yolunun bulunduğu klasörü aşağıda kullanın. Her komut tek satırdır:

```powershell
.\.local\venv\Scripts\python.exe .\tools\report_run.py "UCUS_KLASORU"
.\.local\venv\Scripts\python.exe .\tools\mosaic_2d.py "HARITALAMA_UCUS_KLASORU"
.\.local\venv\Scripts\python.exe .\tools\reconstruct_gaussian.py "BINA_UCUS_KLASORU" --viewer
```

Hareket analizini aynı gerçek kayıtta tekrar denemek için farklı çıktı adı kullanın; mevcut kanıtın üzerine yazılmaz:

```powershell
.\.local\venv\Scripts\python.exe .\tools\motion_detect.py "PLANE_UCUS_KLASORU" --output-name motion_tekrar
```

İki bağlantılı operatör/gözlemci kontrolü `tools/check_operator_flow.py` ile yapılabilir. Bu kontrol yerel simülasyonda operatörü otomatikleştirir; gözlemci komut sayısının sıfır kaldığını doğrular.

## Başarı ölçütleri

Ortak: normal arm, silahlıyken yalnız AUTO, uçuş setpointi yok, LAND ve gerçek disarm. İlaçlama raporunda ideal kaplama en az%95; bina ROI hata dağılımında %95 değeri5° altında. Haritalamada gerçek tetik fotoğrafları ve mozaik; binada **optimize edilmiş Gaussian PLY + hold-out render**; sabit kanatta canlı hareket olayı ve olaydan sonra AUTO devamı. Sayılar bilgisayarın örnekleme zamanlamasına göre değişebilir.

### Yeni bina iş akışı

Öğrenci `3D_Uret.cmd` ile uçuş klasörünü verir. Script resmî Brush0.3.0 aracını yerelde hazırlar, gerçek RGB ve Gazebo camera pose'larını Nerfstudio formatına aktarır. Her8.kare hold-out seçilir. Sparse initialization yalnız94train görüntüsüyle yapılır;14hold-out kare bu aşamaya da girmez. Sonra6 000step, SH degree2, max45 000Gaussians ile training çalışır. `gaussian_metrics.py` final checkpoint'in Gaussian parametreleri taşıdığını ve14ayrılmış açıdan görünüş kalitesini kontrol eder. PSNR/SSIM bir görünüş ölçümüdür; geometric accuracy değildir.

Derste önce `3D_Goster.cmd` ile hazır modeli açın; öğrenciler orbit/zoom yapabilsin. Yeni training donanıma göre zaman alabilir; görev anlatımı sırasında arka planda ilerletilebilir. Full RGB kullanıldı, semantic mask verilmedi. Camera önündeki airframe parçaları ve uzak zeminde blur/floaters görülebilir; bu sınırlar sonuçla birlikte anlatılır.

Hareket olayları için gerçek kişi konumları **yalnız sonradan değerlendirmede** kullanılır. Küçük/dolgulu kutularda IoU>0,06 ilişkilendirmesi uygulanır. Aynı kişi birden çok olay üretebilir. Bu deney genel precision/recall ölçümü değildir. Tam kare, kırpım ve yanlış alarm örneğini birlikte gösterin.

## Ürünlerin teknik sınırı

- Mozaik: gerçek RGB, bilinen kamera pozları, z=0 projeksiyonu. GSD ile konumsal doğruluğu karıştırmayın.
- Bina: SIFT initialization sonrası **3D Gaussian Splatting**. Camera pose bilinir; SfM pose estimation yok. Gaussian model triangle mesh değildir.
- İlaçlama: gerçek pompa PWM'i + gerçek iz + ideal8m iş genişliği; damlacık veya doz doğrulaması yok.
- Gimbal: ArduPilot çıkışlarıyla ideal yönelim; mekanik gecikme/atalet yok.
- Sabit kanat: rüzgârsız referans Zephyr, fiziksel hava hız sensörü yok. Bu iniş/kalkış ayarlarını gerçek araca doğrudan taşımayın.

## Sunumu yeniden üretme

Paylaşılan görseller, `dogrulama/final_summary.json` ve `dogrulama/gaussian_validation.json` ile `sunum/kaynak/build_slides.py` çalıştırılır (`python-pptx`, Pillow gerekir). Aktif revizyon `revise_curriculum.py` ve `gaussian_curriculum.py` içindedir. Üretici hem AUTO hem Gaussian doğrulaması geçmeden güncel sunumu yapmaz. Windows'ta PowerPoint ve pywin32 ile `export_pdf.py` PDF üretir; `check_pdf.py` PyMuPDF ile sayfa ve sayfa dışı metin kontrolü yapar. `build_explainers.py` şemaları PNG ve düzenlenebilir SVG olarak üretir; simülasyon Python ortamının bilimsel paketlerini kullanır.

v3 çizimleri `sunum/uretilen_gorseller` içindedir; yeniden sunum üretmek için görsel üretim servisi gerekmez. Özgün PNG ve aynı çözünürlükte JPEG kopyaları paylaşılır. `encode_slide_assets.ps1` yalnız Windows JPEG kodlayıcısıyla dosya boyutunu azaltır, içerik çizmez veya değiştirmez. `finalize_generated_assets.py` SHA256 ve boyut kökenlerini kaydeder. Promptlar `prompts.json`, düzeltme promptları `generation-record.json`, köken listesi `provenance.json` içindedir. Sunumun tüm 40 hedef sayfasında doğru JPEG'nin gömülü olduğu `check_illustrations.py` ile doğrulanır.

`prepare_evidence.py` yalnız eğitmenin ham yerel kayıtlarından kanıtları yeniden seçmesi içindir; öğrenci için gerekli değildir. Ham kayıtlar depoda paylaşılmaz. Sunumda kullanılan karelerin kökenleri `sunum/gorseller/provenance.json` içinde tutulur.
