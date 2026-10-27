$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$pythonPaths = @((Join-Path $repoRoot 'windows\.pixi\envs\default\python.exe'),(Join-Path $env:USERPROFILE 'gz-ws\.pixi\envs\default\python.exe'))
$coursePython = $pythonPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $coursePython) { Write-Host 'Once ilk haftanin Gazebo kurulumunu tamamlayin.'; exit 1 }
& $coursePython -u (Join-Path $PSScriptRoot 'install.py')
exit $LASTEXITCODE
