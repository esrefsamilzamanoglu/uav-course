try {
    . (Join-Path $PSScriptRoot 'Ortak.ps1')
    Assert-CoursePath
    $script:Pixi = Find-Pixi
    $vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (-not (Test-Path -LiteralPath $vswhere)) { throw 'Visual C++ Build Tools 2022 ve Windows 11 SDK kurulumunu tamamlayin.' }
    $vsRoot = Invoke-Checked $vswhere @('-latest','-products','*','-version','[17.0,18.0)','-requires','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','Microsoft.VisualStudio.Component.Windows11SDK.26100','-property','installationPath')
    if (-not $vsRoot) { throw 'Build Tools 2022: MSVC v143 x64/x86 ve Windows 11 SDK 10.0.26100 secilmeli.' }
    Import-Module (Join-Path $vsRoot 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll')
    Enter-VsDevShell -VsInstallPath $vsRoot -SkipAutomaticLocation -DevCmdArguments '-arch=amd64 -host_arch=amd64' | Out-Null
    New-Item -ItemType Directory -Path $LocalRoot -Force | Out-Null

    Write-Host '[1/4] Gazebo ve derleme araclari resmi conda-forge kaynagindan kuruluyor...'
    Invoke-Checked $Pixi @('install','--manifest-path',$Manifest)
    Set-GazeboEnvironment

    Write-Host '[2/4] Resmi ArduPilot Gazebo kaynagi ve Windows uyarlamasi hazirlaniyor...'
    $commit = '082a0fe231f6e63bc8d1598f1cba461d9e2ea7f5'
    $patch = Join-Path $WindowsRoot 'windows-core.patch'
    if (-not (Test-Path -LiteralPath $SourceRoot)) {
        Invoke-Pixi git init $SourceRoot
        Invoke-Pixi git -C $SourceRoot remote add origin https://github.com/ArduPilot/ardupilot_gazebo.git
    }
    if (-not (Test-Path -LiteralPath (Join-Path $SourceRoot '.git'))) { throw 'Kaynak klasoru Git deposu degil. .local/ardupilot_gazebo klasorunu kontrol edin.' }
    # This upstream revision mixes CRLF/LF blobs; Git's Windows conversion keeps patch checks consistent.
    Invoke-Pixi git -C $SourceRoot config core.autocrlf true
    if (-not (Test-PixiCommand git -C $SourceRoot rev-parse --verify --quiet HEAD)) {
        Invoke-Pixi git -C $SourceRoot fetch --depth 1 origin $commit
        Invoke-Pixi git -C $SourceRoot -c advice.detachedHead=false checkout --detach FETCH_HEAD
    }
    $head = Invoke-Pixi git -C $SourceRoot rev-parse HEAD
    if ($head -ne $commit) { throw 'Kaynak commit farkli. .local/ardupilot_gazebo icindeki calismanizi kontrol edin.' }
    if (-not (Test-PixiCommand git -C $SourceRoot apply --reverse --check $patch)) {
        Invoke-Pixi git -C $SourceRoot apply --check $patch
        Invoke-Pixi git -C $SourceRoot apply $patch
    }
    Invoke-Pixi cmake -S $SourceRoot -B $BuildRoot -G Ninja -DBUILD_GSTREAMER_PLUGIN=OFF -DCMAKE_BUILD_TYPE=RelWithDebInfo "-DCMAKE_PREFIX_PATH=$(Join-Path $WindowsRoot '.pixi\envs\default\Library')"
    Invoke-Pixi cmake --build $BuildRoot --target ArduPilotPlugin --parallel 2

    Write-Host '[3/4] Windows ArduCopter ve gerekli dosyalar resmi ArduPilot sunucusundan indiriliyor...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    foreach ($entry in (Get-Downloads)) {
        if (Test-DownloadFile $entry) { continue }
        $destination = Join-Path $SitlRoot $entry.file
        New-Item -ItemType Directory -Path (Split-Path $destination -Parent) -Force | Out-Null
        $partial = $destination + '.download'
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $entry.url -OutFile $partial
            if ((Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash -ne $entry.sha256) {
                throw "Resmi indirme surumu degismis: $($entry.file). Rehberdeki hash listesinin yenilenmesi gerekiyor. Kuruluma devam edilmedi."
            }
            Move-Item -LiteralPath $partial -Destination $destination -Force
        } finally {
            if (Test-Path -LiteralPath $partial) { Remove-Item -LiteralPath $partial -Force }
        }
    }
    Assert-Runtime

    Write-Host '[4/4] Iris dunyasi bu bilgisayarin yollarina gore hazirlaniyor...'
    Invoke-Pixi python (Join-Path $WindowsRoot 'resolve_world.py') --source (Join-Path $WindowsRoot 'iris.sdf') --models (Join-Path $SourceRoot 'models') --output $WorldFile
    Invoke-Pixi gz sdf -k $WorldFile
    $defaultGui = Join-Path $WindowsRoot '.pixi\envs\default\Library\share\gz\gz-sim\gui\gui.config'
    $gui = Get-Content -LiteralPath $defaultGui -Raw
    if ($gui -notmatch '<camera_pose>[^<]+</camera_pose>') { throw 'Gazebo GUI kamera ayari bulunamadi.' }
    $gui = [regex]::Replace($gui, '<camera_pose>[^<]+</camera_pose>', '<camera_pose>6 -6 4 0 0.45 2.35619449019</camera_pose>')
    [IO.File]::WriteAllText($GuiFile, $gui, (New-Object Text.UTF8Encoding($false)))
    Write-Host 'Kurulum tamamlandi. Baslat.cmd dosyasina cift tiklayin.' -ForegroundColor Green
} catch {
    Write-Host ("Kurulum durdu: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
