# Остановить French Learning (ярлык «French Learning — остановить»).
# Находит процесс, который слушает порт 8000, и завершает его.
$connections = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
Add-Type -AssemblyName System.Windows.Forms
if (-not $connections) {
    [System.Windows.Forms.MessageBox]::Show("Приложение не запущено.", "French Learning") | Out-Null
    exit 0
}
foreach ($pid_ in ($connections | Select-Object -ExpandProperty OwningProcess -Unique)) {
    Stop-Process -Id $pid_ -Force -ErrorAction SilentlyContinue
}
[System.Windows.Forms.MessageBox]::Show("Приложение остановлено.", "French Learning") | Out-Null
