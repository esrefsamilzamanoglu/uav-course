[CmdletBinding()]
param([switch]$OnkosullariKur, [switch]$MissionPlannerKur, [switch]$SadeceKontrol)
$ErrorActionPreference = 'Stop'
$courseRoot = $PSScriptRoot
. (Join-Path $courseRoot 'windows/Ortak.ps1')

function Update-CoursePath {
    $env:PATH = [Environment]::GetEnvironmentVariable('PATH','Machine') + ';' + [Environment]::GetEnvironmentVariable('PATH','User') + ';' + $env:PATH
}
function Install-CoursePackage([string]$Id, [string]$Override = '') {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'WinGet yok. KURULUM.md icindeki resmi onkosul kurucularini kurup Kur.cmd dosyasini yeniden acin.'
    }
    $packageArgs = @('install','--id',$Id,'--exact','--source','winget','--accept-source-agreements','--accept-package-agreements','--disable-interactivity')
    if ($Override) { $packageArgs += @('--override',$Override) }
    & winget.exe @packageArgs
    if ($LASTEXITCODE -eq 3010 -or $LASTEXITCODE -eq 1641) { throw 'Onkosul kuruldu; Windows yeniden baslatma istiyor. Yeniden baslatip Kur.cmd dosyasini tekrar acin.' }
    if ($LASTEXITCODE -ne 0) { throw "Onkosul kurulumu tamamlanamadi: $Id. KURULUM.md dosyasini izleyin." }
    Update-CoursePath
}
function Get-CourseBuildTools {
    $courseVswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
    if (Test-Path -LiteralPath $courseVswhere) {
        & $courseVswhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.Windows11SDK.26100 -property installationPath
    }
}
function Install-CourseMissionPlanner {
    foreach ($courseProgramFiles in @(${env:ProgramFiles(x86)},$env:ProgramFiles)) {
        if (Test-Path -LiteralPath (Join-Path $courseProgramFiles 'Mission Planner/MissionPlanner.exe')) { return }
    }
    $courseDownload = Join-Path $courseRoot '.local/installers/MissionPlanner-latest.msi'
    New-Item -ItemType Directory -Force -Path (Split-Path $courseDownload -Parent) | Out-Null
    Write-Host 'Mission Planner resmi ArduPilot sunucusundan indiriliyor...'
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing -Uri 'https://firmware.ardupilot.org/Tools/MissionPlanner/MissionPlanner-latest.msi' -OutFile $courseDownload
    $courseInstaller = Start-Process -FilePath msiexec.exe -ArgumentList @('/i',('"' + $courseDownload + '"'),'/passive','/norestart') -WindowStyle Hidden -Wait -PassThru
    if ($courseInstaller.ExitCode -eq 3010) { throw 'Mission Planner kuruldu. Windows yeniden baslatma istiyor; yeniden baslatip Baslat.cmd dosyasini acin.' }
    if ($courseInstaller.ExitCode -ne 0) { throw "Mission Planner MSI hatasi: $($courseInstaller.ExitCode). KURULUM.md dosyasindaki resmi MSI kurucusunu acin." }
}
try {
    Assert-CoursePath
    $coursePixi = $null
    try { $coursePixi = Find-Pixi } catch {}
    $courseVs = Get-CourseBuildTools
    if ($SadeceKontrol) {
        Write-Host "Depo: $courseRoot"
        Write-Host "Pixi: $coursePixi"
        Write-Host "Build Tools 2022 + SDK 26100: $courseVs"
        if (-not $coursePixi -or -not $courseVs) { throw 'Onkosullar eksik. Kur.cmd dosyasini calistirin veya KURULUM.md dosyasini izleyin.' }
        Write-Host 'Onkosullar hazir. Simulasyon dosyalari kurulum sonunda ayrica denetlenir.'
        exit 0
    }
    if (-not $coursePixi) {
        if (-not $OnkosullariKur) { throw 'Pixi eksik. Kur.cmd dosyasini calistirin.' }
        Install-CoursePackage 'prefix-dev.pixi'
        $coursePixi = Find-Pixi
    }
    if (-not $courseVs) {
        if (-not $OnkosullariKur) { throw 'Build Tools 2022 + SDK 26100 eksik. KURULUM.md dosyasini izleyin.' }
        Install-CoursePackage 'Microsoft.VisualStudio.2022.BuildTools' '--wait --passive --norestart --add Microsoft.VisualStudio.Component.VC.Tools.x86.x64 --add Microsoft.VisualStudio.Component.Windows11SDK.26100'
        $courseVs = Get-CourseBuildTools
        if (-not $courseVs) { throw 'Var olan Build Tools kurulumunda MSVC v143 ve SDK 26100 secin. KURULUM.md dosyasini izleyin.' }
    }
    # Separate PowerShell processes isolate first-week environment variables and exit codes.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $courseRoot 'windows/Kur.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'Gazebo / ArduPilot kurulumu tamamlanamadi.' }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $courseRoot 'haftalar/03/gercekci/Kur.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'ROTA GCS kurulumu tamamlanamadi.' }
    if ($MissionPlannerKur) { Install-CourseMissionPlanner }
    Write-Host 'Kurulum tamamlandi. Kok klasordeki Baslat.cmd dosyasini acin.' -ForegroundColor Green
} catch {
    Write-Host ("Kurulum durdu: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
