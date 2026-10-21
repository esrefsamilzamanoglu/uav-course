# UAV Course — 1. Hafta Kurulum

İlk hafta için **Git + VS Code + yer kontrol istasyonu + Gazebo + ArduPilot SITL** kuracağız. Kendi işletim sisteminizin bölümünü izleyin; kod bloklarını sırayla çalıştırın. Bir adım hata verirse sonraki adıma geçmeyin.

| Sistem | Kullanılacak yol |
| --- | --- |
| Windows 10/11, x64 | Mission Planner 1.3.83 + yerel Gazebo Jetty 10.5.0 ders paketi; WSL gerekmez |
| Ubuntu 22.04 Desktop, amd64 | QGroundControl 4.4.5 + Gazebo Harmonic + ArduPilot 4.7.2 |

İnternet bağlantısı ve birkaç GB boş alan gerekir. Linux komutları diğer dağıtımlar veya Ubuntu 24.04 için hazırlanmadı. ROS kurulumu gerekmiyor.

## Windows

**1.** PowerShell'i **yönetici olarak** açın. Git ve VS Code'u kurun:

```powershell
winget install --id Git.Git --exact --source winget --accept-package-agreements --accept-source-agreements
winget install --id Microsoft.VisualStudioCode --exact --source winget --accept-package-agreements --accept-source-agreements
```

`winget` bulunamazsa [App Installer](https://apps.microsoft.com/detail/9nblggh4nns1) yükleyin. Kurulumdan sonra PowerShell'i kapatıp yeniden yönetici olarak açın; böylece `git` komutu tanınır.

**2.** Ders deposunu alın:

```powershell
Set-Location $env:USERPROFILE
git clone https://github.com/esrefsamilzamanoglu/uav-course.git
Set-Location .\uav-course
```

**3.** Mission Planner'ı indirin. Açılan kurulum sihirbazını tamamlayın:

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/ArduPilot/MissionPlanner/releases/download/MissionPlanner1.3.83/MissionPlanner-1.3.83.msi' -OutFile "$env:TEMP\MissionPlanner-1.3.83.msi"
Start-Process msiexec.exe -ArgumentList "/i `"$env:TEMP\MissionPlanner-1.3.83.msi`"" -Wait
```

**4.** Ders paketini indirin ve kurun. `C:\IHA_Ders` boş olmalı; klasör yolunda boşluk kullanmayın:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/esrefsamilzamanoglu/uav-course/releases/download/hafta-1/IHA_Windows_Kurulum.zip' -OutFile "$env:TEMP\IHA_Windows_Kurulum.zip"
if ((Get-FileHash "$env:TEMP\IHA_Windows_Kurulum.zip" -Algorithm SHA256).Hash -ne '945fa05ab348607c7488948dafe736b75ad5c767d8d97f041a13d5d42a87493e') { throw 'İndirme doğrulanamadı; ZIP dosyasını yeniden indirin.' }
Expand-Archive -LiteralPath "$env:TEMP\IHA_Windows_Kurulum.zip" -DestinationPath C:\
Set-Location C:\IHA_Ders
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-Course.ps1
```

İlk kurulum Gazebo, gerekli çalışma ortamı ve ek araç modellerini indirir; uzun sürebilir. Sistem Python'u veya derleyici kurmanız gerekmez.

**5.** Kurulum başarıyla bittikten sonra:

```powershell
Set-Location C:\IHA_Ders
.\Start-Copter.cmd
```

Gazebo açılınca Mission Planner'ı başlatın: **TCP → CONNECT → `127.0.0.1` → `5760`**. Araç ve telemetri görünmeli. Harici simülasyona bağlanırken Mission Planner'ın **SIMULATION** sekmesinden ikinci simülasyon başlatmayın.

Sabit kanat için önce oturumu kapatıp `Start-Plane.cmd` çalıştırın. İki başlatıcıyı aynı anda açmayın. Ders deposunu VS Code'da normal kullanıcı oturumundan açabilirsiniz.

## Linux — Ubuntu 22.04 Desktop

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
printf 'deb [arch=%s signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable jammy main\n' "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null
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

**4.** [ArduPilot–Gazebo eklentisini](https://github.com/ArduPilot/ardupilot_gazebo/tree/082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5) derleyip ortam dosyasını oluşturun:

```bash
cd "$HOME/uav-course/src"
git clone https://github.com/ArduPilot/ardupilot_gazebo.git
cd ardupilot_gazebo
git checkout --detach 082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5
export GZ_VERSION=harmonic
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j2
cat > "$HOME/uav-course/course-env.sh" <<'EOF'
export GZ_VERSION=harmonic
export GZ_SIM_SYSTEM_PLUGIN_PATH="$HOME/uav-course/src/ardupilot_gazebo/build:${GZ_SIM_SYSTEM_PLUGIN_PATH:-}"
export GZ_SIM_RESOURCE_PATH="$HOME/uav-course/src/ardupilot_gazebo/models:$HOME/uav-course/src/ardupilot_gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}"
EOF
```

**5.** [QGroundControl](https://docs.qgroundcontrol.com/Stable_V4.4/en/qgc-user-guide/getting_started/download_and_install.html) indirin:

```bash
sudo apt install -y libfuse2 libqt5gui5 libxcb-xinerama0 libxkbcommon-x11-0
cd "$HOME/uav-course/tools"
curl -fL --retry 3 https://github.com/mavlink/qgroundcontrol/releases/download/v4.4.5/QGroundControl.AppImage -o QGroundControl-4.4.5.AppImage
chmod +x QGroundControl-4.4.5.AppImage
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
"$HOME/uav-course/tools/QGroundControl-4.4.5.AppImage"
```

QGroundControl aracı UDP `14550` üzerinden otomatik bulmalı. Gazebo'da araç, yer istasyonunda telemetri göründüğünde ilk hafta kurulumu tamamdır. Sonraki açılışlarda yalnızca **6. adımı** tekrarlayın.

## Takılırsanız

- **Windows'ta kurulum yarım kaldı:** Aynı klasörde `Install-Course.ps1` komutunu yeniden çalıştırın. Klasörü taşıdıysanız çalışma ortamını yeni yerde yeniden kurun.
- **Linux'ta eklenti/model bulunamadı:** Gazebo terminalinde `source "$HOME/uav-course/course-env.sh"` çalıştırıp Gazebo'yu yeniden açın.
- **Gazebo siyah ekran veriyor:** Grafik sürücüsünü güncelleyin. Linux'ta tanılama için `LIBGL_ALWAYS_SOFTWARE=1 gz sim -v4 -r iris_runway.sdf` deneyin.
- **Telemetri gelmiyor:** Gazebo ve SITL açık olmalı; önceki oturumları kapatın. Windows'ta TCP `5760`, Linux'ta UDP `14550` kullanın.

**Doğrulama sınırı:** Önceki Windows paketinde kurulum ve Copter/Plane telemetri başlangıcı mevcut Windows 10 bilgisayarında denenmiştir. Bu paketin yeni indirme adımı bağlantı/hash ve betik denetiminden geçti; tam kurulum yeniden çalıştırılmadı. Temiz bilgisayar ve Linux uçtan uca testleri yapılmadı. Windows eklentisi deneysel bir ders portudur; kamera/video/gimbal pakette yoktur.
