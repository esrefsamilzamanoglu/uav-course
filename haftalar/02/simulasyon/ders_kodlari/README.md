# Derste inceleyeceğimiz kodlar

Bu klasörde **çalışan algoritmaların asıl kodları** bulunur. Kurulum, Gazebo,
telemetri kaydı ve kalibrasyon yardımcıları `../tools/` içinde tutulur.
Üç uygulama da görüntü verisi işler; uçuş rotasını ArduPilot AUTO görevi yürütür.

| Dosya | Derste okuma sırası | Çıktı |
| --- | --- | --- |
| [haritalama_2d.py](haritalama_2d.py) | `build` → `harita_pikselleri` → `kenar_agirliklari` | RGB mozaik ve örtüşme haritası |
| [haritalama_3d.py](haritalama_3d.py) | `train` → `brush_komutu` → `egitimi_calistir` | Trained Gaussian PLY ve hold-out metrikleri |
| [hareketli_unsur_tespiti.py](hareketli_unsur_tespiti.py) | `Detector.process` → dört işlem adımı → `olay_kaydet` | Hareket adayı, tam kare ve kırpım |

## Çalıştırma

Önce ilgili AUTO görevini uçurun ve terminaldeki `RESULT` klasörünü saklayın.
2D için `../2D_Uret.cmd`, 3D için `../3D_Uret.cmd` açılır; uçuş klasörü yapıştırılır.
Sabit kanat menüsündeki canlı analiz doğrudan buradaki hareket kodunu çalıştırır.

Elle denemek için **simulasyon klasöründe** PowerShell açın:

```powershell
.\.local\venv\Scripts\python.exe .\ders_kodlari\haritalama_2d.py "UCUS_KLASORU"
.\.local\venv\Scripts\python.exe .\ders_kodlari\haritalama_3d.py "BINA_UCUS_KLASORU"
.\.local\venv\Scripts\python.exe .\ders_kodlari\hareketli_unsur_tespiti.py "SABIT_KANAT_UCUS_KLASORU" --output-name motion_tekrar
```

Hareket analizini tekrar çalıştırırken yeni bir `--output-name` seçin; eski olaylar
ezilmez. `--follow` canlı yazılan dosyaları izler. `_ortak.py` yalnız yerel yardımcı
modüllerin/DLL'lerin yolunu açar; derste algoritma anlatımına dahil edilmesi gerekmez.
Eski `tools/mosaic_2d.py`, `reconstruct_gaussian.py` ve `motion_detect.py` komutları
uyumluluk için aynı kodlara yönlendirilir; algoritmanın ikinci bir kopyası yoktur.

## Deneyde değiştirebileceğimiz noktalar

- **2D:** `PIKSEL_METRE` raster boyutunu değiştirir. Fotoğraf sayısı ve örtüşme AUTO
  görevindeki trigger/grid ile belirlenir. RGB mozaik, senaryo stres verisini okumaz.
- **3D:** aynı capture ile `--steps`, `--width`, `--max-splats`; eşit bütçede veri
  kalitesinin etkisini karşılaştırın. Pozlar Gazebo'dan bilinir; source mesh okunmaz.
- **Hareket:** ORB FAST, RANSAC ve residual eşiği. Önce `kamera_hareketi`, sonra
  `hareket_maskesi`, `aday_bolgeler`, `takip_et` fonksiyonlarını sırayla inceleyin.
  Gerçek kişi konumları yalnız kaydedilmiş olayın sonradan değerlendirmesinde kullanılır.

Tarla renkleri ve boyutları sentetik senaryodur; RGB görünüşü gerçek NDVI veya
tarımsal stres ölçümü değildir. Mozaik düz zemin varsayar; bitki yüksekliği parallax
oluşturabilir. Gaussian görünüş modeli mesh değildir; hareket adayı da insan etiketi değildir.
