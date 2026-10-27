# 2. hafta — eğitmen uygulama rehberi

## Dersten önce

İlk hafta kurulumunu açıp kapatın. Depoyu güncelleyin; bu haftanın `simulasyon/Kur.cmd` adımını tamamlayın. Birden fazla Gazebo/SITL oturumu açmayın. İlk hafta çalışma dosyaları değiştirilmez; ikinci haftanın ayrı yerel çalışma alanı `.local` altındadır.

Sunum 86 sayfadır. Slayt başına tek ana fikir, gerçek simülasyon görselleri, düzenlenebilir şemalar ve ayrıntılı konuşmacı notları vardır. Canlı uçuşlar sırasında ilgili sonuç slaydına geri dönüp öğrencinin kendi ölçümünü referans sonuçla karşılaştırın.

## Canlı ders sırası

| Slaytlar | Uygulama | Bakılacak kanıt |
| --- | --- | --- |
| 8–16 | Menü0: araç/kamera | 8m; −90/−45/−20°; AUTO iniş |
| 22–32 | Menü1: ilaçlama | Şerit başında aç; dönüşte kapat; 9 PWM bloğu |
| 33–45 | Menü2: tarla haritalama | Mesafe tetiği; fotoğraf sayısı; mozaik |
| 46–59 | Menü3: bina | İki orbit; sabit ROI; fotoğraflardan seyrek bulut |
| 60–78 | Menü4: sabit kanat | AUTO kalkış/iniş; canlı olay; sabit rotanın korunması |
| 79–86 | Değerlendirme | Ürün, metrik, hata/düzeltme ve kapsam |

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
.\.local\venv\Scripts\python.exe .\tools\reconstruct_3d.py "BINA_UCUS_KLASORU"
```

Hareket analizini aynı gerçek kayıtta tekrar denemek için farklı çıktı adı kullanın; mevcut kanıtın üzerine yazılmaz:

```powershell
.\.local\venv\Scripts\python.exe .\tools\motion_detect.py "PLANE_UCUS_KLASORU" --output-name motion_tekrar
```

İki bağlantılı operatör/gözlemci kontrolü `tools/check_operator_flow.py` ile yapılabilir. Bu kontrol yerel simülasyonda operatörü otomatikleştirir; gözlemci komut sayısının sıfır kaldığını doğrular.

## Başarı ölçütleri

Ortak: normal arm, silahlıyken yalnız AUTO, uçuş setpointi yok, LAND ve gerçek disarm. İlaçlama raporunda ideal kaplama en az%95; bina ROI hata dağılımında %95 değeri5° altında. Haritalamada yeterli gerçek tetik fotoğrafı ve mozaik; binada görüntü eşleşmelerinden üretilmiş PLY; sabit kanatta canlı hareket olayı ve olaydan sonra AUTO görevin devamı. Sayılar bilgisayarın örnekleme zamanlamasına göre değişebilir.

Hareket olayları için gerçek kişi konumları **yalnız sonradan değerlendirmede** kullanılır. Küçük/dolgulu kutularda IoU>0,06 ilişkilendirmesi uygulanır. Aynı kişi birden çok olay üretebilir. Bu deney genel precision/recall ölçümü değildir. Tam kare, kırpım ve yanlış alarm örneğini birlikte gösterin.

## Ürünlerin teknik sınırı

- Mozaik: gerçek RGB, bilinen kamera pozları, z=0 projeksiyonu. GSD ile konumsal doğruluğu karıştırmayın.
- Bina: SIFT + RANSAC + bilinen pozlarla üçgenleme; poz kestirimi/bundle adjustment/yoğun mesh yok.
- İlaçlama: gerçek pompa PWM'i + gerçek iz + ideal8m iş genişliği; damlacık veya doz doğrulaması yok.
- Gimbal: ArduPilot çıkışlarıyla ideal yönelim; mekanik gecikme/atalet yok.
- Sabit kanat: rüzgârsız referans Zephyr, fiziksel hava hız sensörü yok. Bu iniş/kalkış ayarlarını gerçek araca doğrudan taşımayın.

## Sunumu yeniden üretme

Paylaşılan görseller ve `dogrulama/final_summary.json` ile `sunum/kaynak/build_slides.py` çalıştırılır (`python-pptx`, Pillow gerekir). Üretici tüm simülasyonların geçtiğini kontrol etmeden sunum yapmaz. Windows'ta PowerPoint ve pywin32 kuruluysa `export_pdf.py` PDF üretir; `check_pdf.py` PyMuPDF ile sayfa ve sayfa dışı metin kontrolü yapar.

`prepare_evidence.py` yalnız eğitmenin ham yerel kayıtlarından kanıtları yeniden seçmesi içindir; öğrenci için gerekli değildir. Ham kayıtlar depoda paylaşılmaz. Sunumda kullanılan karelerin kökenleri `sunum/gorseller/provenance.json` içinde tutulur.
