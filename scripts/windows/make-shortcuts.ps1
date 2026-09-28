# Ярлыки на рабочем столе: «French Learning» (запустить и открыть) и
# «French Learning — остановить». Запуск: powershell -ExecutionPolicy Bypass -File make-shortcuts.ps1
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Icon = Join-Path $Root "src\french_learning\web\static\favicon.ico"
$Vbs = Join-Path $PSScriptRoot "run-hidden.vbs"
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell

function New-Shortcut($Name, $Script, $Description) {
    $link = $Shell.CreateShortcut((Join-Path $Desktop "$Name.lnk"))
    $link.TargetPath = "$env:WINDIR\System32\wscript.exe"
    $link.Arguments = "`"$Vbs`" $Script"
    $link.WorkingDirectory = $Root
    $link.IconLocation = $Icon
    $link.Description = $Description
    $link.Save()
    Write-Output "Ярлык: $(Join-Path $Desktop "$Name.lnk")"
}

New-Shortcut "French Learning" "start-app.ps1" "Запустить и открыть приложение"
New-Shortcut "French Learning — остановить" "stop-app.ps1" "Остановить приложение"
