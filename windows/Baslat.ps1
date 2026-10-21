$gazebo = $sitl = $null
try {
    . (Join-Path $PSScriptRoot 'Ortak.ps1')
    Assert-CoursePath
    $script:Pixi = Find-Pixi
    foreach ($required in @((Join-Path $BuildRoot 'ArduPilotPlugin.dll'), $WorldFile, $GuiFile)) {
        if (-not (Test-Path -LiteralPath $required)) { throw 'Once Kur.cmd dosyasini calistirin.' }
    }
    Assert-Runtime
    if ((Get-NetTCPConnection -LocalPort 5760 -State Listen -ErrorAction SilentlyContinue) -or (Get-NetUDPEndpoint -LocalPort 9002 -ErrorAction SilentlyContinue)) {
        throw '5760 veya 9002 portu kullanimda. Once acik simulasyon oturumunu kapatin.'
    }
    Set-GazeboEnvironment
    $logs = Join-Path $LocalRoot 'logs'
    $run = Join-Path $SitlRoot 'run'
    New-Item -ItemType Directory -Path $logs,$run -Force | Out-Null
    $gzArgs = @('run','--manifest-path',$Manifest,'gz','sim','-r','-v3','--gui-config',$GuiFile,$WorldFile)
    $gazebo = Start-Process -FilePath $Pixi -ArgumentList (Quote-ProcessArgs $gzArgs) -WorkingDirectory $WindowsRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'gazebo.out.log') -RedirectStandardError (Join-Path $logs 'gazebo.err.log') -PassThru
    $null = $gazebo.Handle
    Write-Host 'Gazebo aciliyor...'
    $deadline = (Get-Date).AddSeconds(90)
    do {
        Start-Sleep -Milliseconds 500
        $gazebo.Refresh()
        if ($gazebo.HasExited) { throw "Gazebo kapandi. Ayrinti: $logs\gazebo.err.log" }
        $ready = Get-NetUDPEndpoint -LocalPort 9002 -ErrorAction SilentlyContinue
    } while (-not $ready -and (Get-Date) -lt $deadline)
    if (-not $ready) { throw "Gazebo eklentisi baslatilamadi. Ayrinti: $logs\gazebo.err.log" }
    $defaults = (Join-Path $SitlRoot 'default_params\copter.parm').Replace('\','/') + ',' + (Join-Path $SitlRoot 'default_params\gazebo-iris.parm').Replace('\','/')
    $sitlArgs = @('--model','JSON','--speedup','1','--defaults',$defaults,'--serial0','tcp:0','--base-port','5760','--sim-address','127.0.0.1','--sim-port-out','9002')
    $sitl = Start-Process -FilePath (Join-Path $SitlRoot 'ArduCopter.exe') -ArgumentList (Quote-ProcessArgs $sitlArgs) -WorkingDirectory $run -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'sitl.out.log') -RedirectStandardError (Join-Path $logs 'sitl.err.log') -PassThru
    $null = $sitl.Handle
    Write-Host 'Mission Planner: TCP -> 127.0.0.1 -> 5760' -ForegroundColor Green
    Write-Host 'Bu pencere acik kalsin. Bitirince Gazebo penceresini kapatin veya Ctrl+C kullanin.'
    do {
        Start-Sleep -Milliseconds 500
        $gazebo.Refresh()
        $sitl.Refresh()
    } while (-not $gazebo.HasExited -and -not $sitl.HasExited)
    if ($sitl.HasExited) {
        $sitl.WaitForExit()
        if ($null -eq $sitl.ExitCode -or $sitl.ExitCode -ne 0) { throw "ArduCopter kapandi (kod: $($sitl.ExitCode)). Ayrinti: $logs\sitl.err.log" }
    }
} catch {
    Write-Host ("Baslatilamadi: " + $_.Exception.Message) -ForegroundColor Red
    exit 1
} finally {
    if (Get-Command Stop-OwnedTree -ErrorAction SilentlyContinue) {
        Stop-OwnedTree $sitl
        Stop-OwnedTree $gazebo
    }
}
