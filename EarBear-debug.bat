@echo off
cd /d "%~dp0"
set TCL_LIBRARY=%~dp0python\tcl\tcl8.6
set TK_LIBRARY=%~dp0python\tcl\tk8.6
"%~dp0python\python.exe" earbear.py
pause
