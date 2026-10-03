# Запуск French Learning одним щелчком (ярлык на рабочем столе).
# Если приложение уже работает — просто открывает его в браузере; иначе запускает сервер
# в фоне (без окна терминала), ждёт готовности и открывает браузер.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Url = "http://127.0.0.1:8000/"
$LogDir = Join-Path $env:LOCALAPPDATA "french-learning"

function Test-App {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 10 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-App)) {
    $uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (-not (Test-Path $uv)) { $uv = "uv" }
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    Start-Process -FilePath $uv -ArgumentList "run", "python", "-m", "french_learning.cli", "serve" `
        -WorkingDirectory $Root -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir "server.log") `
        -RedirectStandardError (Join-Path $LogDir "server-errors.log")
    $deadline = (Get-Date).AddSeconds(90)
    while (-not (Test-App) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 700 }
}

if (Test-App) {
    Start-Process $Url
} else {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        "Приложение не запустилось за 90 секунд.`nПодробности — в файле:`n$LogDir\server-errors.log",
        "French Learning") | Out-Null
}
