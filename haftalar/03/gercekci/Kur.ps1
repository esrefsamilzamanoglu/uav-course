$ErrorActionPreference = 'Stop'
$rotaRoot = $PSScriptRoot
$rotaRepo = (Resolve-Path (Join-Path $rotaRoot '../../..')).Path
$rotaPython = Join-Path $rotaRoot '.local/venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $rotaPython)) {
    $rotaCandidates = @((Join-Path $rotaRepo 'windows/.pixi/envs/default/python.exe'), (Join-Path $env:USERPROFILE 'gz-ws/.pixi/envs/default/python.exe'))
    $rotaBase = $rotaCandidates | Where-Object {Test-Path -LiteralPath $_} | Select-Object -First 1
    if (-not $rotaBase) {throw 'Once 1. haftanin Windows Gazebo/ArduPilot kurulumunu tamamlayin.'}
    & $rotaBase -m venv (Join-Path $rotaRoot '.local/venv')
    if ($LASTEXITCODE -ne 0) {throw 'Python ortami olusturulamadi.'}
}
& $rotaPython -m pip install --disable-pip-version-check -r (Join-Path $rotaRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) {throw 'Python paket kurulumu basarisiz.'}
& (Join-Path $rotaRoot 'plugin/build.ps1')
if ($LASTEXITCODE -ne 0) {throw 'Gazebo eklentisi derlenemedi.'}
& $rotaPython (Join-Path $rotaRoot 'world/build_world.py') --source (Join-Path $rotaRepo 'windows/.local/ardupilot_gazebo') --plugin-path (Join-Path $rotaRoot 'plugin/.local/build')
if ($LASTEXITCODE -ne 0) {throw 'Dunya hazirlanamadi.'}
if (-not (Test-Path -LiteralPath (Join-Path $rotaRoot 'gcs/frontend/dist/index.html'))) {
    Push-Location -LiteralPath (Join-Path $rotaRoot 'gcs/frontend')
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) {throw 'Node.js LTS ve npm kurulumu gerekli.'}
        & npm.cmd run build
        if ($LASTEXITCODE -ne 0) {throw 'GCS arayuzu derlenemedi.'}
    } finally {Pop-Location}
}
& $rotaPython (Join-Path $rotaRoot 'tools/check_install.py')
if ($LASTEXITCODE -ne 0) {throw 'Kurulum kontrolu basarisiz.'}
Write-Host 'ROTA GCS hazir. Baslat.cmd dosyasini acin.'
