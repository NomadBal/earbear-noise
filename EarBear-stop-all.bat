@echo off
rem Stops every process that runs from this folder (EarBear.exe and its helper), so the folder can be deleted.
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('%~dp0', 'OrdinalIgnoreCase') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Done.
pause
