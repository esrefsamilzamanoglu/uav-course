$ErrorActionPreference = 'Stop'
$realisticSource = $PSScriptRoot
$realisticBuild = Join-Path $realisticSource '.local/build'
$realisticRepo = (Resolve-Path (Join-Path $realisticSource '../../../..')).Path
$realisticEnvironments = @(
    [pscustomobject]@{prefix=(Join-Path $realisticRepo 'windows/.pixi/envs/default/Library'); manifest=(Join-Path $realisticRepo 'windows/pixi.toml')},
    [pscustomobject]@{prefix=(Join-Path $env:USERPROFILE 'gz-ws/.pixi/envs/default/Library'); manifest=(Join-Path $env:USERPROFILE 'gz-ws/pixi.toml')}
)
$realisticEnvironment = $realisticEnvironments | Where-Object {
    (Test-Path -LiteralPath $_.prefix) -and (Test-Path -LiteralPath $_.manifest)
} | Select-Object -First 1
if (-not $realisticEnvironment) {throw 'Complete the first-week Windows Gazebo installation first.'}
$realisticPrefix = $realisticEnvironment.prefix
$realisticManifest = $realisticEnvironment.manifest
$realisticPixiCommand = Get-Command pixi -ErrorAction SilentlyContinue
$realisticPixi = if ($realisticPixiCommand) {$realisticPixiCommand.Source} else {Join-Path $env:USERPROFILE '.pixi/bin/pixi.exe'}
if (-not (Test-Path -LiteralPath $realisticPixi)) {throw 'Pixi is not installed or not on PATH.'}
$realisticVsWhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
if (-not (Test-Path -LiteralPath $realisticVsWhere)) {throw 'Visual C++ Build Tools 2022 required; run the root Kur.cmd.'}
$realisticVsDir = & $realisticVsWhere -latest -products '*' -version '[17.0,18.0)' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 Microsoft.VisualStudio.Component.Windows11SDK.26100 -property installationPath
if (-not $realisticVsDir) {throw 'MSVC v143 and Windows SDK 26100 required; see KURULUM.md.'}
$realisticVcVars = Join-Path $realisticVsDir 'VC/Auxiliary/Build/vcvars64.bat'
if (-not (Test-Path -LiteralPath $realisticVcVars)) {throw 'MSVC C++ Build Tools required.'}
New-Item -ItemType Directory -Force -Path (Join-Path $realisticSource '.local') | Out-Null
$realisticCommands = @(
    '@echo off',
    'chcp 65001 >nul',
    ('call "' + $realisticVcVars + '"'),
    'if errorlevel 1 exit /b %errorlevel%',
    ('"' + $realisticPixi + '" run --manifest-path "' + $realisticManifest + '" cmake -S "' + $realisticSource + '" -B "' + $realisticBuild + '" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo "-DCMAKE_PREFIX_PATH=' + $realisticPrefix + '"'),
    'if errorlevel 1 exit /b %errorlevel%',
    ('"' + $realisticPixi + '" run --manifest-path "' + $realisticManifest + '" cmake --build "' + $realisticBuild + '" --parallel 2'),
    'exit /b %errorlevel%'
)
$realisticBatch = Join-Path $realisticSource '.local/build.cmd'
[System.IO.File]::WriteAllLines($realisticBatch, $realisticCommands, [System.Text.UTF8Encoding]::new($false))
& cmd.exe /d /c $realisticBatch
if ($LASTEXITCODE -ne 0) {throw 'Native Gazebo mechanics build failed.'}
Write-Host ('Plugin and bridge: ' + $realisticBuild)
