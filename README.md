# UAV Course — 1. Hafta Kurulum

İlk hafta için **Git, VS Code, yer kontrol istasyonu, Gazebo ve ArduPilot SITL** kurulumu. Programlar kendi resmî kaynaklarından indirilir. İşletim sisteminizin bölümünü sırayla izleyin; bir adım hata verirse sonraki adıma geçmeyin.

| Sistem | Kullanılacak yol |
| --- | --- |
| Windows 11, x64 | Güncel Mission Planner + Gazebo Jetty |
| Ubuntu 24.04 Desktop, amd64 | Güncel QGroundControl + Gazebo Harmonic + ArduPilot SITL |

İnternet bağlantısı ve birkaç GB boş alan gerekir. ROS kurulumu gerekmiyor.

## Windows

**1.** PowerShell'i **yönetici olarak** açın. [Git](https://git-scm.com/install/windows), [VS Code](https://code.visualstudio.com/download) ve Gazebo'nun kullandığı [Pixi](https://pixi.prefix.dev/latest/installation/) paket yöneticisini kurun:

```powershell
winget install --id Git.Git --exact --source winget --accept-package-agreements --accept-source-agreements
winget install --id Microsoft.VisualStudioCode --exact --source winget --accept-package-agreements --accept-source-agreements
winget install --id prefix-dev.pixi --exact --source winget --accept-package-agreements --accept-source-agreements
```

`winget` bulunamazsa [App Installer](https://apps.microsoft.com/detail/9nblggh4nns1) yükleyin. Kurulumdan sonra PowerShell'i kapatıp yeniden yönetici olarak açın; böylece `git` ve `pixi` komutları tanınır.

**2.** Ders deposunu alın:

```powershell
Set-Location $env:USERPROFILE
git clone https://github.com/esrefsamilzamanoglu/uav-course.git
Set-Location .\uav-course
```

**3.** [Mission Planner'ın güncel resmî kurucusunu](https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi) indirin. Açılan kurulum sihirbazını tamamlayın:

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -UseBasicParsing -Uri 'https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi' -OutFile "$env:TEMP\MissionPlanner-latest.msi"
Start-Process msiexec.exe -ArgumentList "/i `"$env:TEMP\MissionPlanner-latest.msi`"" -Wait
```

**4.** [Gazebo Jetty'yi resmî Windows yöntemiyle](https://gazebosim.org/docs/jetty/install_windows/) kurun. Yeni kurulum için boşluksuz `C:\gz-course` klasörünü kullanın:

```powershell
New-Item -ItemType Directory -Path C:\gz-course
Set-Location C:\gz-course
@'
[workspace]
name = "gazebo-course"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["win-64"]

[dependencies]
gz-sim = "10.*"

[target.win-64.activation.env]
QT_QPA_PLATFORM_PLUGIN_PATH = "%CONDA_PREFIX%\\Library\\lib\\qt6\\plugins\\platforms"
QML2_IMPORT_PATH = "%CONDA_PREFIX%\\Library\\lib\\qt6\\qml"
'@ | Set-Content -LiteralPath .\pixi.toml -Encoding ascii
pixi install
pixi run gz sim -v4 shapes.sdf
```

Şekillerin bulunduğu Gazebo penceresi açılmalı. Sonraki açılışlarda aynı klasörde yalnızca son komutu çalıştırın.

**5.** ArduPilot SITL için Mission Planner'ı açın: **SIMULATION → Multirotor**. Sürüm sorulursa **Stable** seçin. İlk açılışta gereken simülasyon dosyalarını Mission Planner resmî sunucudan indirir; indirme ve bağlantının tamamlanmasını bekleyin. [Resmî SITL yönergesi](https://ardupilot.org/planner/docs/mission-planner-simulation.html).

Windows'ta bu adımlar Gazebo'yu ve Mission Planner SITL'yi ayrı ayrı çalıştırır. Gazebo–ArduPilot bağlantısı ayrıca eklenti gerektirir; upstream eklentinin native Windows kurulumu belgelenmiyor. Aşağıdaki Linux yolu eklentiyle bağlantıyı da kurar. Gazebo'nun Windows desteği deneysel olarak sunuluyor.

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

- **Windows'ta Gazebo indirmesi yarım kaldı:** `C:\gz-course` içinde `pixi install` komutunu yeniden çalıştırın.
- **Linux'ta eklenti/model bulunamadı:** Gazebo terminalinde `source "$HOME/uav-course/course-env.sh"` çalıştırıp Gazebo'yu yeniden açın.
- **Gazebo siyah ekran veriyor:** Grafik sürücüsünü güncelleyin. Linux'ta tanılama için `LIBGL_ALWAYS_SOFTWARE=1 gz sim -v4 -r iris_runway.sdf` deneyin.
- **Linux'ta telemetri gelmiyor:** Gazebo ve SITL açık olmalı; önceki oturumları kapatın. QGroundControl için UDP `14550` kullanılır.

Ek araç modelleri gerektiğinde [ArduPilot/SITL_Models](https://github.com/ArduPilot/SITL_Models) deposundan alınabilir. İlk Iris denemesinde eklentiyle gelen modeller yeterlidir.

İndirme adresleri ve komut sözdizimi kontrol edildi; bu rehber için temiz bilgisayarda tam kurulum testi yapılmadı.
