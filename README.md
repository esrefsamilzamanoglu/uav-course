# UAV Course — 1. Hafta Kurulum

İlk hafta için **Git, VS Code, yer kontrol istasyonu, Gazebo ve ArduPilot SITL** kurulumu. Programlar kendi resmî kaynaklarından indirilir. İşletim sisteminizin bölümünü sırayla izleyin; bir adım hata verirse sonraki adıma geçmeyin.

| Sistem | Kullanılacak yol |
| --- | --- |
| Windows 10/11, x64 | Gazebo + ArduPilot Gazebo eklentisi + SITL → Mission Planner TCP |
| Ubuntu 24.04 Desktop, amd64 | Güncel QGroundControl + Gazebo Harmonic + ArduPilot SITL |

İnternet bağlantısı ve birkaç GB boş alan gerekir. ROS kurulumu gerekmiyor.

## Windows — Gazebo + ArduPilot + Mission Planner

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

## Linux — Ubuntu 24.04 Desktop

Normal **Ubuntu Terminali** kullanın; conda/venv etkin olmasın. Komutları `sudo su` içinde çalıştırmayın.

**1.** Temel araçları, VS Code'u ve ders deposunu alın:

```bash
sudo apt update
sudo apt install -y git build-essential cmake pkg-config curl ca-certificates lsb-release gnupg
cd "$HOME"
git clone https://github.com/esrefsamilzamanoglu/uav-course.git
cd "$HOME/uav-course"
mkdir -p tools src
curl -fL --retry 3 https://update.code.visualstudio.com/latest/linux-deb-x64/stable -o tools/vscode.deb
sudo apt install -y ./tools/vscode.deb
```

**2.** [Gazebo Harmonic](https://gazebosim.org/docs/harmonic/install_ubuntu/) ve eklenti bağımlılıklarını kurun. Eski Gazebo Classic/`gazebo11` kuruluysa bu adımı uygulamadan önce sürüm çakışmasını çözün:

```bash
sudo curl -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
printf 'deb [arch=%s signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable noble main\n' "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
sudo apt update
sudo apt install -y gz-harmonic libgz-sim8-dev rapidjson-dev libopencv-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl
```

**3.** [ArduPilot SITL](https://ardupilot.org/dev/docs/building-setup-linux.html) kurun. Önkoşul betiğinin önüne `sudo` eklemeyin:

```bash
cd "$HOME/uav-course/src"
git clone --branch Copter-4.7.2 --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot
DO_AP_STM_ENV=0 Tools/environment_install/install-prereqs-ubuntu.sh -y
. "$HOME/.profile"
./waf configure --board sitl
./waf copter -j2
```

**4.** [Resmî ArduPilot–Gazebo eklentisini](https://github.com/ArduPilot/ardupilot_gazebo) derleyip ortam dosyasını oluşturun:

```bash
cd "$HOME/uav-course/src"
git clone https://github.com/ArduPilot/ardupilot_gazebo.git
cd ardupilot_gazebo
export GZ_VERSION=harmonic
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j2
cat > "$HOME/uav-course/course-env.sh" <<'EOF'
export GZ_VERSION=harmonic
export GZ_SIM_SYSTEM_PLUGIN_PATH="$HOME/uav-course/src/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$HOME/uav-course/src/ardupilot_gazebo/models:$HOME/uav-course/src/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}"
EOF
```

**5.** [QGroundControl'un güncel kararlı sürümünü](https://docs.qgroundcontrol.com/Stable_V5.1/en/qgc-user-guide/getting_started/download_and_install.html) indirin. Bu hazır sürüm Ubuntu 24.04 veya üzeri gerektirir:

```bash
sudo apt install -y libfuse2t64 libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor0
cd "$HOME/uav-course/tools"
curl -fL --retry 3 https://github.com/mavlink/qgroundcontrol/releases/latest/download/QGroundControl-x86_64.AppImage -o QGroundControl.AppImage
chmod +x QGroundControl.AppImage
```

**6.** Üç ayrı terminal açın; her birinde ilgili bloğu çalıştırın:

Terminal 1 — Gazebo:

```bash
source "$HOME/uav-course/course-env.sh"
gz sim -v4 -r iris_runway.sdf
```

Terminal 2 — ArduPilot SITL:

```bash
. "$HOME/.profile"
cd "$HOME/uav-course/src/ardupilot"
./Tools/autotest/sim_vehicle.py -v ArduCopter -f gazebo-iris --model JSON --no-extra-ports --out=127.0.0.1:14550 -j2
```

Terminal 3 — yer kontrol istasyonu:

```bash
"$HOME/uav-course/tools/QGroundControl.AppImage"
```

QGroundControl aracı UDP `14550` üzerinden otomatik bulmalı. Gazebo'da araç, yer istasyonunda telemetri göründüğünde ilk hafta kurulumu tamamdır. Sonraki açılışlarda yalnızca **6. adımı** tekrarlayın.

## Takılırsanız

- **Windows'ta kurulum yarım kaldı:** `windows\Kur.cmd` dosyasını yeniden açın. Derleyici bulunamadıysa Build Tools kurulumundaki C++ ve SDK bileşenlerini kontrol edin.
- **Windows'ta TCP bağlantısı kurulamıyor:** `windows\Baslat.cmd` açık olmalı; IP `127.0.0.1`, port `5760` olmalı. Önceki simülasyon oturumunu kapatın.
- **Linux'ta eklenti/model bulunamadı:** Gazebo terminalinde `source "$HOME/uav-course/course-env.sh"` çalıştırıp Gazebo'yu yeniden açın.
- **Gazebo siyah ekran veriyor:** Grafik sürücüsünü güncelleyin. Linux'ta tanılama için `LIBGL_ALWAYS_SOFTWARE=1 gz sim -v4 -r iris_runway.sdf` deneyin.
- **Linux'ta telemetri gelmiyor:** Gazebo ve SITL açık olmalı; önceki oturumları kapatın. QGroundControl için UDP `14550` kullanılır.

Ek araç modelleri gerektiğinde [ArduPilot/SITL_Models](https://github.com/ArduPilot/SITL_Models) deposundan alınabilir. İlk Iris denemesinde eklentiyle gelen modeller yeterlidir.

Windows yardımcıları ayrı bir klasörde yeni ortam kurarak, eklentiyi derleyerek ve Gazebo + TCP telemetri bağlantısını açarak denendi. Önceki Windows kurulumunda kalkış, yaklaşık 5 m irtifada bekleme ve iniş kaydı da vardır. Temiz bilgisayar ve Linux uçtan uca kurulum testi yapılmadı.
