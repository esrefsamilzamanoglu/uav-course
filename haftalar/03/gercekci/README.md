# ROTA GCS — Gazebo görev laboratuvarı

Gerçek RGB kamera, ArduPilot servo çıkışları ve fiziksel yüklerle G1/G2/G3 görevlerini çalıştırın. Harita, kamera tespitleri, konum/sensörler, yük salınımı, görev aşamaları ve çalışan Python satırları aynı arayüzdedir.

## Başlatma

İlk kullanımda depo kökündeki **Kur.cmd**, ardından **Kontrol.cmd** çalıştırın. Tam yönerge: [başka bilgisayarda kurulum](../../../KURULUM.md). `Baslat.cmd` ROTA'yı açar; arayüzde **Simülasyonu Başlat** seçilir. `Baslat-3B.cmd` ayrıca Gazebo penceresini açar.

GCS: **http://127.0.0.1:8787**. Mission Planner: **TCP 127.0.0.1:5762**. İki uygulama aynı ArduPilot oturumuna ayrı MAVLink kanallarından bağlanır. **5760 ROTA'ya ayrılmıştır.** Bağlantı bilgileri arayüzün **Sistem** bölümünde de bulunur.

Görev sırasında uçuş komutlarını ROTA'dan verin; Mission Planner'da telemetriyi ve parametreleri inceleyin. Görevler Python'dan GUIDED komutlarıyla çalışır, AUTO waypoint listesi değildir. Bağlantı kaybı denetimi ROTA'nın 253 numaralı GCS kimliğini izler. Mission Planner'ın bağlanması veya ayrılması bu kimliği değiştirmez.

## Ders ekranı

**G1/G2/G3** seçimi, **Takip / Yörünge / Yandan / Üstten** üçüncü şahıs kamerası ve **Canlı Kod** ekranı için [ders rehberini](CANLI_DERS.md) izleyin. Canlı kod, gerçek `sys.settrace` olaylarından üretilen kısa adlı renkli blokları takip eder. Ayrıntıda çalışan satır ve çağrı yığını açılır.

Her bağımsız görev öncesinde simülasyonu durdurup yeniden başlatın. İki 0,30 kg yük ve mekanik ön yükleme düzeni yeniden hazırlanır. G3, G2'nin ilk iki teslimatını kendi akışında yapar.

| Klasör | Öğreneceğiniz bölüm |
| --- | --- |
| `backend/control.py` | MAVLink alımı, komut onayı, GUIDED uçuş, görsel hizalama, teslimat ve geri alma. |
| `backend/vision.py` | Gerçek RGB üzerinden renk/şekil tespiti, kamera izdüşümü ve yük bulma. |
| `backend/native_runtime.py` | Sahip olunan Gazebo/SITL süreçleri, iki GCS portu ve uçuş parametreleri. |
| `backend/execution_trace.py` | Görev ve görüntü işleme iş parçacıklarında gerçek Python izlemesi. |
| `backend/server.py` | Yerel HTTP API, komutlar, kameralar ve hazır React arayüzünün sunulması. |
| `gcs/frontend/src` | TypeScript/React ekranları, renkli kod blokları ve harita. |
| `plugin` | Servo PWM → fiziksel kavrama kısıtı; gerçek kamera ve fizik durumu köprüsü. |
| `world` / `models` | Saha üretimi, drone, yükler, hedefler, nesneler ve doku. |

Yükler DART eklemleriyle sallanır. Kavrama; yakınlık, bağıl hız ve çene koşulları sağlandığında fiziksel bağlantı kurar. Bırakma bağlantıyı kaldırır; yük yerçekimi ve temasla hareket eder. Detaylı yumuşak çene/halat esnekliği modellenmez. [Mekanik arayüz](plugin/README.md) · [Dünya ve varlıklar](world/ASSETS.md).

## Kod değiştirme ve denetim

Python ortamı `.local/venv`, derlenen native bileşenler `plugin/.local/build`, uçuş kayıtları `.local/runs/TARIH-SAAT` altındadır. Bu dosyalar her bilgisayarda yeniden oluşturulur. Backend kaynakları değiştiğinde uçuşu bitirip servisi kapatın, sonra yeniden açın; canlı kaynak hash'i çalışan sürümü denetler.

Arayüzü değiştirmek için Node.js kurun; `gcs/frontend` içinde `npm.cmd ci` ve `npm.cmd run build` çalıştırın. Normal ders kullanımı için Node.js gerekmez. Tarayıcı testi için `npx playwright install chromium`, `npm.cmd run dev` ve başka terminalde `npm.cmd run qa` kullanın; bunlar arayüz fikstür testleridir. Gerçek uçuş başarısı kanıtı değildir.

Python denetimleri:

```powershell
.local\venv\Scripts\python.exe -m unittest discover -s tests/physics -p "test_*.py" -q
.local\venv\Scripts\python.exe -m unittest discover -s tests -p "test_follow_camera.py" -q
```

Kök `Kontrol.cmd --live`, Mission Planner bağlantısı kapalıyken 5762 portundan salt okunur bir ikinci GCS denetimi yapar. Sadece `Kontrol.cmd` ise kurulu dosya ve dünya kaynaklarını denetler.
