# Başka bir Windows bilgisayarda ROTA GCS

Windows 10/11 **x64**, internete erişim ve güncel ekran kartı sürücüsü gerekir. Gazebo render ve fizik hesabını bilgisayarınızda çalıştırır; kamera hızı donanıma bağlıdır. İlk kurulum birkaç GB indirir. WSL ve ROS gerekmez.

Bu revizyon **`hafta-03-mission-planner`** dalındadır. GitHub'da bu dalı seçerek **Code → Download ZIP** kullanın veya Git ile alın:

```powershell
git clone --branch hafta-03-mission-planner --single-branch https://github.com/esrefsamilzamanoglu/uav-course.git C:\uav-course
```

## İlk kurulum

1. Depoyu klonlayın veya GitHub **Code → Download ZIP** ile indirin. ZIP'i açıp depo kökünü **`C:\uav-course`** olarak adlandırın. Klasör yolunda boşluk ve Türkçe karakter olmasın. ZIP içinden çalıştırmayın.
2. Kök klasördeki **`Kur.cmd`** dosyasını açın. Eksik Pixi ve Visual C++ Build Tools 2022 + SDK 26100 bileşenlerini WinGet ile kurar. Windows kurucularının yönetici/UAC istemlerini tamamlayın. Yeniden başlatma istenirse yeniden başlatıp aynı dosyayı tekrar açın.
3. Aynı yardımcı, Gazebo Jetty 10.5.0 ortamını `windows/pixi.lock` ile kurar, sabitlenmiş ArduPilot Gazebo kaynağını indirip derler ve SHA-256 denetimli ArduCopter 4.7.3 SITL dosyalarını hazırlar. ROTA Python ortamını ve yük/kamera eklentilerini kurar; dünyayı bu bilgisayarın yollarıyla üretir. Son olarak Mission Planner'ı resmî MSI ile kurar.
4. **`Kontrol.cmd`** ile dosyaları, Python bağımlılıklarını, SITL hash'lerini, arayüzü ve dünya kaynaklarını denetleyin.

Hazır arayüz depoda bulunduğundan **Node.js gerekmez**. Git ve VS Code kod geliştirmek için isteğe bağlıdır. Kurulum dosyaları, sanal ortamlar ve uçuş kayıtları `.local` / `.pixi` altında bu bilgisayarda tutulur. Başka bilgisayardan bu klasörleri kopyalamayın; o bilgisayarda `Kur.cmd` çalıştırın.

WinGet yoksa veya kurum politikası kurulumu engelliyorsa şu resmî kurucuları kullanın:

| Önkoşul | Resmî kaynak |
| --- | --- |
| Pixi x64 | [Windows MSI](https://github.com/prefix-dev/pixi/releases/latest/download/pixi-x86_64-pc-windows-msvc.msi) |
| Build Tools **2022** | [Microsoft kurucusu](https://aka.ms/vs/17/release/vs_BuildTools.exe) |
| Mission Planner | [ArduPilot MSI](https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi) |

Build Tools kurucusunda **MSVC v143 x64/x86** ve **Windows 11 SDK 10.0.26100** seçilmelidir. Build Tools zaten kurulu fakat bu bileşenler eksikse **Visual Studio Installer → Modify/Değiştir → Individual components/Tek tek bileşenler** üzerinden ekleyin. Ardından `Kur.cmd` dosyasını yeniden açın. Pixi/derleyici kurulumu tamamlandığında `powershell -NoProfile -ExecutionPolicy Bypass -File Kur.ps1 -SadeceKontrol` yalnız önkoşulları denetler.

## Uçuş ve Mission Planner

1. Kök **`Baslat.cmd`** dosyasını açın; tarayıcıda `http://127.0.0.1:8787` açılır. ROTA'da **Simülasyonu Başlat** seçin. Gazebo fiziği ve gerçek kameralar arka planda çalışır. Gazebo'nun 3B penceresini de açmak için `haftalar\03\gercekci\Baslat-3B.cmd` kullanın.
2. GPS/EKF ve kamerayı bekleyin. **G1, G2 veya G3** seçip görevi başlatın. Her bağımsız deneme öncesinde simülasyonu durdurup yeniden başlatın; yükler başlangıç düzenine döner.
3. Mission Planner'da **TCP → CONNECT → IP `127.0.0.1` → port `5762`** seçin. ROTA açık kalır. Port **5760 ROTA'ya ayrılmıştır**. Mission Planner'ın **SIMULATION** sekmesinden ikinci SITL başlatmayın.
4. Mission Planner'da araç konumu, HUD, uçuş modu, sensörler, parametreler ve servo telemetrisi izlenebilir. Görev aşaması, kameralar, salınım ve Python bloklarını ROTA'dan izleyin. Bu görevler GUIDED komutlarıyla Python'dan yürür; Mission Planner'ın AUTO waypoint listesi görev adımlarını göstermez.

| Kullanım | Adres |
| --- | --- |
| ROTA web arayüzü | `http://127.0.0.1:8787` |
| ROTA → ArduPilot | TCP `127.0.0.1:5760`, GCS sistem kimliği **253** |
| Mission Planner → aynı ArduPilot | TCP `127.0.0.1:5762`, varsayılan GCS sistem kimliği **255** |

Görev sürerken uçuş komutlarını ROTA'dan verin. Mission Planner'dan mod/servo/konum komutu verilmesi aynı aracı etkiler. Müdahale için önce ROTA'da **Beklet** veya **İniş** kullanın; iki uygulamadan eşzamanlı görev komutu vermeyin. Bağlantı kaybı denetimi ROTA'nın heartbeat'ini izler (`MAV_GCS_SYSID=253`, `FS_GCS_ENABLE=5`, zaman aşımı 5 s); Mission Planner'ın kapanması bu kaynağı değiştirmez. ROTA bağlantısının kaybı ArduPilot'un ayarlanan iniş davranışını tetikler.

## Bağlantı denetimi ve sorunlar

Mission Planner'ın bağlantısını kapattıktan sonra, simülasyon açıkken **`Kontrol.cmd --live`** kullanabilirsiniz. İkinci porttan heartbeat/parametre okur ve ROTA'nın bağlı kaldığını doğrular; uçuş komutu göndermez. Port 5762'ye aynı anda tek istemci bağlanır.

| Belirti | Çözüm |
| --- | --- |
| `5760 / 5762 / 9002 kullanımda` | Açık diğer SITL oturumunu kendi başlatıcısından kapatın. Bu yardımcı başka uygulamanın sürecini sonlandırmaz. |
| Parametreler gelmiyor | Önce ROTA'da simülasyonu başlatın; Mission Planner'ın 5762 kullandığını kontrol edin. Port denetimi yapan diğer istemciyi kapatın. |
| Kurulum hash hatası | Resmî sunucudaki dosya sürümü değişmiştir. Kontrolü atlamayın; güncel ders deposunu alın. |
| Kamera görüntüsü yavaş | Ekran kartı sürücüsünü güncelleyin, diğer 3B uygulamaları kapatın. GCS'deki kare yaşı ve simülasyon zamanı ile duvar zamanı farklıdır. |
| `npm` bulunamıyor | Hazır `gcs/frontend/dist` klasörü indirilmemiştir. Deponun tamamını indirin. Yalnız arayüz kaynağını değiştirecekseniz Node.js kurun. |

Python paketleri `haftalar/03/gercekci/requirements.txt`, arayüz paketleri `package-lock.json`, Gazebo ortamı `windows/pixi.lock`, uçuş yazılımı `windows/downloads.json` ile sabitlenir. Kurulum yarıda kalırsa hata nedenini giderip aynı `Kur.cmd` dosyasını tekrar çalıştırın.

Bu başlatıcı Windows içindir. İlk iki haftanın [Linux kurulumu](linux/README.md) ayrı bir uygulamadır; üçüncü haftanın ROTA kurucusu Linux desteği sağlamaz.

Teknik başvurular: [ArduPilot SITL UART kaynağı (4.7.2)](https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/libraries/AP_HAL_SITL/UARTDriver.cpp), [MAVLink GCS kimliği ve failsafe kaynağı](https://github.com/ArduPilot/ardupilot/blob/Copter-4.7.2/libraries/GCS_MAVLink/GCS.cpp), [Microsoft kurucu parametreleri](https://learn.microsoft.com/en-us/visualstudio/install/use-command-line-parameters-to-install-visual-studio?view=vs-2022), [Pixi kurulumu](https://pixi.prefix.dev/latest/installation/).
