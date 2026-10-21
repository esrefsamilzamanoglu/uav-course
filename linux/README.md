# Ubuntu 24.04: Gazebo + ArduPilot

**Ubuntu 24.04 Desktop, amd64** kullanın. Windows ile aynı **Gazebo Jetty 10.5.0**, **ArduCopter 4.7.2** ve aynı ArduPilot Gazebo kaynak sürümü kullanılır. Linux yer kontrol istasyonu **QGroundControl 5.1.5** olur.

1. [Ana rehberin Linux bölümündeki](../README.md#linux--ubuntu-2404-desktop-amd64) **1 ve 2. adımları** tamamlayın: masaüstü bağımlılıklarını, Git, VS Code ve Pixi'yi kurup ders deposunu alın.
2. VS Code'da depo klasörünü açın → **Terminal → New Terminal**. Kurulumu normal kullanıcı olarak başlatın:

   ```bash
   bash linux/kur.sh
   ```

   İndirme ve derleme bitene kadar bekleyin. İşlem yarım kalırsa aynı komutu yeniden çalıştırabilirsiniz. `sudo` kullanmayın.

3. Simülasyon ve QGroundControl'u açın:

   ```bash
   bash linux/baslat.sh --qgc
   ```

4. QGroundControl'da **Application Settings → Comm Links → Add** açın. **Name: Iris**, **Type: TCP**, **Server Address: 127.0.0.1**, **Port: 5760** girin. **Save → Connect** seçin. Gazebo'da Iris ve QGroundControl'da telemetri göründüğünde bağlantı hazırdır.

Terminal açık kalsın. Bitirince Gazebo'yu kapatın veya terminalde `Ctrl+C` kullanın. Sonraki kullanımlarda yalnızca **3 ve 4. adımları** uygulayın. QGroundControl zaten açıksa `bash linux/baslat.sh` kullanın; ikinci yer istasyonu açmayın.

- **Pixi bulunamadı:** Resmî Pixi kurulumunu tamamlayıp terminali yeniden açın.
- **TCP bağlantısı kurulamıyor:** Başlatıcı açık, IP `127.0.0.1`, port `5760` olmalı. Önceki simülasyon oturumunu kapatın.
- **Gazebo görüntüsü siyah:** Grafik sürücüsünü kontrol edin. Tanılama için `LIBGL_ALWAYS_SOFTWARE=1 bash linux/baslat.sh --qgc` deneyin.
- **Program açılmadan kapanıyor:** `linux/.local/logs` klasöründeki ilgili program günlüğünü kontrol edin. Bu kurulum Ubuntu Desktop gerektirir.

Programlar kendi resmî kaynaklarından indirilir; depoda ZIP veya hazır çalıştırılabilir dosya dağıtılmaz. Derleme/indirme çıktıları `linux/.local` ve `linux/.pixi` içinde kalır. ArduCopter'in hazır Linux sürümü kullanıldığı için tam ArduPilot geliştirme ortamı gerekmez. QGroundControl AppImage yerelde çıkarılarak çalıştırılır; FUSE kurulumu gerekmez.

Eklenti, [aynı resmî kaynak sürümünden](https://github.com/ArduPilot/ardupilot_gazebo/tree/082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5) derlenir. [Linux CMake uyarlaması](linux-core.patch), ilk hafta gerekmeyen kamera akışını kapatır, RapidJSON başlıklarını belirtir ve Jetty bağımlılıkları için C++17 kullanır. Windows ağ kodu yaması Linux'a uygulanmaz. Windows ve Linux SITL dosyalarının sürüm numarası aynıdır; platform derlemeleri ve kaynak commit'leri farklıdır.

Kaynaklar ve lisanslar: [SOURCES.txt](SOURCES.txt). Kurulum Ubuntu 24.04.3 (WSL2) üzerinde ayrı ortamda denendi: eklenti derlendi, tekrar kurulum geçti, Gazebo ve QGroundControl açıldı. TCP üzerinden heartbeat, yönelim ve konum verileri alındı; kapatıldığında süreçler ve portlar serbest kaldı. Testte uçuş veya arm komutu verilmedi.
