@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" goto missing
".venv\Scripts\python.exe" -c "import PySide6.QtWidgets, PySide6.QtMultimedia" >nul 2>&1
if errorlevel 1 goto missing
start "Showtanz-Analyzer" ".venv\Scripts\pythonw.exe" -m analyzer.gui
exit /b 0
:missing
echo Die Windows-Oberflaeche ist noch nicht eingerichtet.
echo Anleitung: analyzer\README.md, Abschnitt Windows-Oberflaeche.
echo In PowerShell im Repository ausfuehren:
echo .\.venv\Scripts\python -m pip install -r analyzer\requirements-gui.txt
pause
exit /b 1
