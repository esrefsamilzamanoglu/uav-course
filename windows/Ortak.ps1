$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2
$script:WindowsRoot = $PSScriptRoot
$script:LocalRoot = Join-Path $WindowsRoot '.local'
$script:Manifest = Join-Path $WindowsRoot 'pixi.toml'
$script:SourceRoot = Join-Path $LocalRoot 'ardupilot_gazebo'
$script:BuildRoot = Join-Path $SourceRoot 'build-windows'
$script:SitlRoot = Join-Path $LocalRoot 'sitl'
$script:WorldFile = Join-Path $LocalRoot 'iris.sdf'
$script:GuiFile = Join-Path $LocalRoot 'iris_gui.config'

function Assert-CoursePath {
    if (-not [Environment]::Is64BitOperatingSystem) { throw '64 bit Windows gerekli.' }
    if ($WindowsRoot -notmatch '^[A-Za-z]:\\[A-Za-z0-9_.\\-]+$') {
        throw 'Repo yolunda bosluk/Turkce karakter olmasin. C:\uav-course kullanin.'
    }
}

function Find-Pixi {
    $command = Get-Command pixi.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    foreach ($candidate in @((Join-Path $env:LOCALAPPDATA 'pixi\bin\pixi.exe'), (Join-Path $env:USERPROFILE '.pixi\bin\pixi.exe'))) {
        if (Test-Path -LiteralPath $candidate) { return $candidate }
    }
    throw 'Once resmi Pixi x64 MSI kurulumunu tamamlayin, sonra Kur.cmd dosyasini yeniden acin.'
}

function Invoke-Checked([string]$File, [string[]]$Arguments) {
    # Windows PowerShell 5.1 treats even successful native stderr as an error.
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $File @Arguments
        $result = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }
    if ($result -ne 0) { throw "Komut tamamlanamadi ($result): $File $Arguments" }
}

function Invoke-Pixi {
    Invoke-Checked $script:Pixi (@('run','--manifest-path',$script:Manifest) + @($args))
}

function Test-PixiCommand {
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $script:Pixi run --manifest-path $script:Manifest @args >$null 2>$null
        return $LASTEXITCODE -eq 0
    } finally { $ErrorActionPreference = $savedPreference }
}

function Set-GazeboEnvironment {
    $library = Join-Path $WindowsRoot '.pixi\envs\default\Library'
    $env:QT_QPA_PLATFORM_PLUGIN_PATH = Join-Path $library 'lib\qt6\plugins\platforms'
    $env:QT_PLUGIN_PATH = Join-Path $library 'lib\qt6\plugins'
    $env:QML2_IMPORT_PATH = Join-Path $library 'lib\qt6\qml'
    $env:GZ_VERSION = 'jetty'
    $env:GZ_PARTITION = 'uav_course_windows'
    $env:GZ_SIM_SYSTEM_PLUGIN_PATH = $BuildRoot.Replace('\', '/')
    $env:GZ_SIM_RESOURCE_PATH = (Join-Path $SourceRoot 'models').Replace('\', '/')
}

function Get-Downloads {
    $entries = Get-Content -LiteralPath (Join-Path $WindowsRoot 'downloads.json') -Raw | ConvertFrom-Json
    foreach ($entry in $entries) { Write-Output $entry }
}

function Test-DownloadFile($entry) {
    $path = Join-Path $SitlRoot $entry.file
    return (Test-Path -LiteralPath $path) -and ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -eq $entry.sha256)
}

function Assert-Runtime {
    foreach ($entry in (Get-Downloads)) {
        if (-not (Test-DownloadFile $entry)) { throw "Eksik/degismis dosya: $($entry.file). Kur.cmd dosyasini calistirin." }
    }
}

function Quote-ProcessArgs([string[]]$Items) {
    # Paths are checked above; each item is still quoted for Windows CreateProcess.
    return ($Items | ForEach-Object {
        if ($_ -match '["\r\n]') { throw 'Gecersiz komut argumani.' }
        '"' + $_ + '"'
    }) -join ' '
}

function Stop-OwnedTree([System.Diagnostics.Process]$Process) {
    if (-not $Process) { return }
    $Process.Refresh()
    if ($Process.HasExited) { return }
    # taskkill /T only follows descendants of the process started by this script.
    $savedPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & "$env:SystemRoot\System32\taskkill.exe" /PID $Process.Id /T /F 2>$null | Out-Null
    } finally { $ErrorActionPreference = $savedPreference }
}
