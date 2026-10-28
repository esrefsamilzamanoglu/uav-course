# 2. hafta — hazırlık ve test kaydı

## 28 Ekim 2026 — görsel anlatım v3

- Önceki sunumun 40 metin/tablo/liste/işlem/formül/sayısal sonuç sayfası tarandı; her birine ayrı built-in image_gen çağrısıyla ilgili mekanizmayı anlatan çizim üretildi.
- Kurulumdaki yerel yazılım bağlantısı, CONDITION/DO ayrımı, mesafeli tetik ve sabit kanat çizimleri görsel kontrolün ardından image_gen ile düzeltildi.
- 40 özgün PNG, sunum için aynı çözünürlükte JPEG kopyaları, tam prompt seti, düzeltme promptları ve SHA256 köken listesi paylaşıldı. API/CLI fallback kullanılmadı.
- Sayfa sayısı 93 kaldı. Tablolar/komutlar metin olarak korundu; çizimler ayrı yerleşimlerle yanlarına eklendi. Tüm yeni görseller kavramsal çizim olarak etiketlendi.
- Yeni PDF `Hafta-02-Sunum-v3.pdf`; eski public `Hafta-02-Sunum.pdf` bağlantısı da güncel PDF içeriğine yönelir.

## 28 Ekim 2026 — önceki v2

- Bina ana çıktısı sparse point cloud yerine gerçek **3D Gaussian Splatting / Brush0.3.0** oldu.
- Aynı gerçek AUTO capture:108 RGB.94train /14hold-out; initialization yalnız train karelerinden1298nokta.
- Öğrenci Python ortamındaki tam pipeline geçti:640×427,6 000steps,45 000Gaussians, SH degree2. Training16dk38s sürdü.
- Hold-out ortalama PSNR27,996dB; SSIM0,913738. Merkez bina crop PSNR30,612dB.1 000step PSNR22,076dB.
- Kaynak bina mesh'i okunmadı; camera pose simülatörden bilinir. Uçuş kontrolüne komut yok.
- Native Brush penceresi açıldı. Otomatik masaüstü görüntüsü doğrulanamadı; sunumda sahte UI yerine gerçek hold-out render'lar kullanıldı.
- Sunum93sayfa:20sayfalık yeni3DGS bölümü,18yeni açıklayıcı şema, teknik İngilizce terimler, bölüm açılışları, zoom/crop, checkpoint ve reference/render karşılaştırmaları.
- Şemaların düzenlenebilir SVG kaynakları ve görsel köken listeleri paylaşıldı.
- Eski yerel PDF yazmaya kilitli olduğundan güncel PDF **Hafta-02-Sunum-v2.pdf** adıyla kaydedildi; ana indeks bu sürüme yönelir.

## 27 Ekim — önceki hazırlık ve uçuş doğrulamaları

27 Ekim 2026. Önce dünyalar, nesneler, görevler ve scriptler hazırlandı; son uçuşlar ve ürünler doğrulandıktan sonra sunum üretildi. İlk hafta dosyaları değiştirilmedi.

## Tamamlanan işler

- [x] Üç dünya ve yerel 3D varlıklar: tarla, bina, kırsal pist.
- [x] ArduPilot gerçek motor çıkışlarıyla fiziksel uçuş; uçak pozunu zorla ayarlama yok.
- [x] Gerçek RGB köprüsü, kalibrasyon/poz/zaman kaydı; mount servo PWM'leriyle ideal gimbal.
- [x] Beş AUTO görevi: kamera tanıtımı, ilaçlama, tarla haritalama, bina, sabit kanat.
- [x] Normal arm; silahlıyken yalnız AUTO; LAND/disarm. Uçuş setpointi ve force-arm yok.
- [x] İlaçlama: ilk %82,86 kaplama sonrası grid düzeltildi ve yeniden uçuldu; son ideal kaplama%100.
- [x] Tarla: 81 tetik ve gerçek RGB; düzlem mozaik üretildi.
- [x] Bina: 108 fotoğraf, sürekli ROI; SIFT ve bilinen pozlarla1787 nokta üretildi.
- [x] Sabit kanat: AUTO pist kalkışı, üç tarama, AUTO iniş; canlı23 hareket olayı.
- [x] İlk canlı olaydan sonra yaklaşık317s AUTO devam; LAND/disarm kaydı.
- [x] Ayrı öğrenci venv'inde ilk ve tekrar kurulum, yerel derleme ve sayısal DLL kontrolü.
- [x] Native Gazebo GUI ve iki bağlantılı operatör/gözlemci akışı denendi.
- [x] Gerçek kayıtlarla86 sayfalık PPTX/PDF, eğitmen notları, kaynaklar ve kullanım rehberleri.

## Denemelerde öğrenilenler

| Sorun | Düzeltme | Yeniden kontrol |
| --- | --- | --- |
| Mesh renkleri Windows'ta beyaz kaldı | Açık SDF malzemeli STL parçalar | Gerçek RGB görsel incelemesi |
| DO açma şerit sonunda gecikti | Başlangıç DO'sundan CONDITION_DISTANCE kaldırıldı | Gerçek PWM / kamera olayları |
| Tarla kenarları açık kaldı | 9 şerit,7m aralık, baş-son uzatması | Kaplama%82,86 →%100 |
| LAND precision beacon bekledi | Bu haftada PLND_ENABLED0 | Home'da normal LAND/disarm |
| Sabit kanatta yer koşusu zayıftı | İdeal teker temasları ve referans ayarlar | AUTO kalkış→iniş |
| Küçük hedef ve az ORB ayrıntısı | 1280×800/70°/55° kamera, FAST3 | Aynı gerçek kayıtta eşleşme/olay |
| Transit/dönüşte parallax alarmları | Salt-okunur SCAN fazında analiz | Son canlı23 olay;4 yanlış alarm |
| Windows sayısal DLL yüklemesi | Python başlangıcında Pixi Library/bin tanıtımı | Fresh venv ve görüntü ürünleri |
| TCP bind kontrolü yanıltıcıydı | Windows gerçek listener tablosu | İki bağlantılı test |

## Son kayıt kimlikleri

| Deney | Yerel run kimliği | Sonuç |
| --- | --- | --- |
| Kamera / pasif gözlemci |20261027-184706-intro|8m, üç açı,0 gözlemci uçuş komutu |
| İlaçlama |20261027-184011-spray|9 pompa bloğu,%100 ideal alan |
| Tarla haritalama |20261027-174950-mapping|81 fotoğraf,912×744 mozaik |
| Bina |20261027-183245-building|108 fotoğraf,1787 nokta |
| Canlı sabit kanat + GUI |20261027-190335-plane|23 olay,19 kişi örtüşmesi,4 yanlış alarm |
| Disarm araç yakın planı |20261027-191355-intro|Uçuş komutu yok; gerçek RGB |

Ham kayıtlar yerel `.local/runs` altında korunur; depoya gereksiz büyük kayıtlar, runtime EXE/DLL veya ZIP yüklenmez. Seçilmiş gerçek karelerin kökeni ve SHA256 değerleri `sunum/gorseller/provenance.json` içindedir. Paylaşılan `dogrulama` özeti ve ürün metrikleri kendi kayıtlarımızdan türetilmiştir.

## Yorum sınırları

İdeal geometrik ilaçlama kaplaması gerçek doz ölçümü değildir. Gimbal kinematiktir. Mozaik z=0 ve bilinen kamera pozları kullanır. Bina seyrek üçgenlemedir; tam SfM/yoğun mesh değildir. Hareket adayı insan sınıfı değildir; olay sayıları genel precision/recall değildir. Windows referans düzeni test edilmiştir; ikinci haftanın Linux başlatıcısı doğrulanmış değildir.
