# Обновить рабочее приложение до принятой версии (ветка main на GitHub).
# Запускается в папке рабочего приложения (C:\Users\Kate\source\french_learning_app) агентом
# после приёмки: остановить сервер → git pull (только вперёд) → uv sync → запустить в фоне.
# Браузер не открывается и окон-сообщений нет. Код в этой папке руками не меняют.
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Url = "http://127.0.0.1:8000/"
$LogDir = Join-Path $env:LOCALAPPDATA "french-learning"
$uv = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
if (-not (Test-Path $uv)) { $uv = "uv" }

$branch = (git -C $Root rev-parse --abbrev-ref HEAD).Trim()
if ($branch -ne "main") { throw "В папке приложения должна быть ветка main, сейчас: $branch" }

# 1. Остановить сервер на порту 8000 (иначе uv sync не сможет заменить файлы окружения)
$connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
foreach ($id in ($connections | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

# 2. Принятая версия с GitHub — только перемотка вперёд, чужих правок здесь быть не должно
git -C $Root pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { throw "git pull не удался — папку приложения меняли вручную?" }

# 3. Библиотеки по uv.lock
Push-Location $Root
try {
    & $uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw "uv sync не удался" }
} finally {
    Pop-Location
}

# 4. Запустить в фоне и дождаться ответа
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Start-Process -FilePath $uv -ArgumentList "run", "french-learning", "serve" `
    -WorkingDirectory $Root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "server.log") `
    -RedirectStandardError (Join-Path $LogDir "server-errors.log")
$deadline = (Get-Date).AddSeconds(90)
$ok = $false
while (-not $ok -and (Get-Date) -lt $deadline) {
    Start-Sleep -Milliseconds 700
    try { Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5 | Out-Null; $ok = $true } catch {}
}
if (-not $ok) { throw "Приложение не ответило за 90 секунд, см. $LogDir\server-errors.log" }
Write-Output "Обновлено и запущено: $(git -C $Root log -1 --format='%h %s')"
