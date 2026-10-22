# UAV Course

Haftalık ders sunumları ve Windows/Linux kurulum rehberi.

## Haftalık sunumlar

| Hafta | Konu | Sunum |
| --- | --- | --- |
| 1. hafta | İHA Yazılımı ve Simülasyonu (v12) | [PDF'yi aç](haftalar/01/Hafta-01-Sunum.pdf) · [İndir](https://github.com/esrefsamilzamanoglu/uav-course/raw/refs/heads/main/haftalar/01/Hafta-01-Sunum.pdf) |

Sonraki haftaların sunumları da burada, `haftalar/02`, `haftalar/03` sırasıyla paylaşılacak.

## 1. hafta kurulumu

İlk hafta için **Git, VS Code, yer kontrol istasyonu, Gazebo ve ArduPilot SITL** kurulumu. Programlar kendi resmî kaynaklarından indirilir. İşletim sisteminizin bölümünü sırayla izleyin; bir adım hata verirse sonraki adıma geçmeyin.

| Sistem | Kullanılacak yol |
| --- | --- |
| Windows 10/11, x64 | Gazebo + ArduPilot Gazebo eklentisi + SITL → Mission Planner TCP |
| Ubuntu 24.04 Desktop, amd64 | Aynı Jetty 10.5.0 + ArduCopter 4.7.2 → QGroundControl TCP |

İnternet bağlantısı ve birkaç GB boş alan gerekir. ROS kurulumu gerekmiyor.

### Windows — Gazebo + ArduPilot + Mission Planner

Bu bilgisayarda çalışan düzen: **Gazebo Jetty 10.5.0 + ArduCopter 4.7.2 + Windows ArduPilot Gazebo eklentisi**. WSL gerekmez.

**1. Programları resmî adreslerinden indirip kurun:**

| Program | İndirme |
| --- | --- |
| Git | [Windows kurucusu](https://git-scm.com/install/windows) |
| VS Code | [Windows indirme sayfası](https://code.visualstudio.com/download) |
| Mission Planner | [Güncel MSI kurucusu](https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi) |
| Pixi — Gazebo paket yöneticisi | [Güncel Windows x64 MSI](https://github.com/prefix-dev/pixi/releases/latest/download/pixi-x86_64-pc-windows-msvc.msi) |
| Visual C++ Build Tools 2022 — eklentiyi derlemek için | [Microsoft kurucusu](https://aka.ms/vs/17/release/vs_BuildTools.exe) |

Build Tools kurucusunda **C++ ile masaüstü geliştirme** iş yükünü; **MSVC v143 x64/x86** ve **Windows 11 SDK 10.0.26100** bileşenlerini seçin. Kurulumlar bittikten sonra bilgisayarı yeniden başlatın.

**2. Ders deposunu alın:** VS Code'u açın → `Ctrl+Shift+P` → **Git: Clone** → bu adresi yapıştırın:

```text
https://github.com/esrefsamilzamanoglu/uav-course.git
```

Kayıt konumu olarak **`C:\`** seçin; depo **`C:\uav-course`** klasörüne alınır. Klasör yolunda boşluk kullanmayın.

**3. Gazebo, eklenti ve SITL'yi kurun:** Dosya Gezgini'nde `C:\uav-course\windows\Kur.cmd` dosyasına çift tıklayın; başarı mesajını bekleyin. İlk indirmeler ve derleme zaman alabilir.

Bu adım [resmî Gazebo Windows yöntemiyle](https://gazebosim.org/docs/jetty/install_windows/) Gazebo'yu, [ArduPilot deposundan](https://github.com/ArduPilot/ardupilot_gazebo) eklenti kaynağını ve [resmî SITL sunucusundan](https://firmware.ardupilot.org/Tools/MissionPlanner/sitl/CopterStable/) uçuş yazılımını indirir. Bu bilgisayardaki çalışan eklentinin [Windows kaynak uyarlaması](windows/README.md) da uygulanır; derleme komutlarını elle yazmanız gerekmez.

**4. Simülasyonu açın:** `C:\uav-course\windows\Baslat.cmd` dosyasına çift tıklayın. Gazebo'da Iris aracı ve SITL oturumu açılmalı.

**5. Mission Planner'dan bağlanın:** Üstteki bağlantı türünü **TCP** seçin → **CONNECT** → IP **`127.0.0.1`** → port **`5760`**. Araç bilgileri ve telemetri geldiğinde bağlantı hazırdır; uçuş komutları Mission Planner'dan verilir.

Bu akışta Mission Planner'ın **SIMULATION** sekmesinden ikinci SITL açmayın. Oturumu bitirmek için başlatıcıda `Ctrl+C` kullanın. Sonraki kullanımlarda yalnızca **4 ve 5. adımları** uygulayın.

### Linux — Ubuntu 24.04 Desktop amd64

Windows ile aynı **Gazebo Jetty 10.5.0**, **ArduCopter 4.7.2** ve **ArduPilot Gazebo eklentisi kaynak sürümü** kullanılır. Linux yer kontrol istasyonu **QGroundControl 5.1.5**'tir; bağlantı burada da **TCP 127.0.0.1:5760** üzerinden yapılır.

**1. Git, VS Code ve Pixi'yi hazırlayın:** [VS Code](https://code.visualstudio.com/download) ve [Pixi](https://pixi.prefix.dev/latest/installation/) resmî kaynaklarından kurulur. Gazebo ve QGroundControl'u 3. adımdaki yardımcı otomatik kurar.

Normal Ubuntu Terminali'nde şu başlangıç adımlarını sırayla çalıştırın:

```bash
sudo apt update
sudo apt install -y git curl libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor0
curl -fL --retry 3 https://update.code.visualstudio.com/latest/linux-deb-x64/stable -o /tmp/uav-code.deb
sudo apt install -y /tmp/uav-code.deb
curl -fsSL https://pixi.sh/install.sh | bash
```

Terminali kapatıp yeniden açın. Kurulum ve başlatma yardımcılarını normal kullanıcıyla çalıştırın; önlerine `sudo` eklemeyin.

**2. Ders deposunu alın:** VS Code → `Ctrl+Shift+P` → **Git: Clone** → `https://github.com/esrefsamilzamanoglu/uav-course.git`. Kayıt konumu olarak kendi ev klasörünüzü seçin; depo `~/uav-course` altına alınır.

**3. Gazebo, eklenti, SITL ve QGroundControl'u kurun:**

```bash
cd "$HOME/uav-course"
bash linux/kur.sh
```

Sürümler sabitlenir; dosyalar resmî sunuculardan indirilip SHA256 ile doğrulanır. Eklenti otomatik derlenir. İlk kurulum zaman alabilir; yarıda kalırsa aynı komutu yeniden çalıştırın. [Linux kurulum notları](linux/README.md).

**4. Simülasyonu açın:**

```bash
cd "$HOME/uav-course"
bash linux/baslat.sh --qgc
```

Gazebo'da Iris, ayrıca QGroundControl açılmalı. QGroundControl'da **Application Settings → Comm Links → Add** açın. **Name: Iris**, **Type: TCP**, **Server Address: `127.0.0.1`**, **Port: `5760`** girin → **Save → Connect**. Sonraki açılışlarda yalnızca bu adımı uygulayın.

Terminal açık kalsın. Bitirince Gazebo'yu kapatın veya terminalde `Ctrl+C` kullanın. Başlatıcı kendi açtığı süreçleri kapatır.

### Takılırsanız

- **Windows'ta kurulum yarım kaldı:** `windows\Kur.cmd` dosyasını yeniden açın. Derleyici bulunamadıysa Build Tools kurulumundaki C++ ve SDK bileşenlerini kontrol edin.
- **Windows'ta TCP bağlantısı kurulamıyor:** `windows\Baslat.cmd` açık olmalı; IP `127.0.0.1`, port `5760` olmalı. Önceki simülasyon oturumunu kapatın.
- **Linux'ta kurulum yarım kaldı:** `bash linux/kur.sh` komutunu yeniden çalıştırın. Gazebo'yu `bash linux/baslat.sh --qgc` ile açın; ortam yolları otomatik yüklenir.
- **Gazebo siyah ekran veriyor:** Grafik sürücüsünü güncelleyin. Linux'ta tanılama için `LIBGL_ALWAYS_SOFTWARE=1 bash linux/baslat.sh --qgc` deneyin.
- **Linux'ta telemetri gelmiyor:** Başlatıcı terminalini kontrol edin; QGroundControl bağlantısı TCP `127.0.0.1:5760` olmalı. Aynı anda ikinci bir SITL açmayın.

Ek araç modelleri gerektiğinde [ArduPilot/SITL_Models](https://github.com/ArduPilot/SITL_Models) deposundan alınabilir. İlk Iris denemesinde eklentiyle gelen modeller yeterlidir.

Windows yardımcıları ayrı bir klasörde yeni ortam kurarak, eklentiyi derleyerek ve Gazebo + TCP telemetri bağlantısını açarak denendi. Önceki Windows kurulumunda kalkış, yaklaşık 5 m irtifada bekleme ve iniş kaydı da vardır. Linux yardımcıları Ubuntu 24.04.3 (WSL2) üzerinde ayrı ortamda kuruldu; tekrar kurulum, Gazebo ve QGroundControl açılışı, TCP üzerinden heartbeat/yönelim/konum verileri ve kapatıldığında süreçlerin temizlenmesi doğrulandı.
