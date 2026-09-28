' Запуск PowerShell-скрипта без окна консоли (для ярлыков на рабочем столе).
' Использование: wscript.exe run-hidden.vbs <имя-скрипта.ps1>
Dim shell, fso, folder, script
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(folder, WScript.Arguments(0))
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & script & """", 0, False
