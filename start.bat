@echo off
:: Relance automatiquement en administrateur si necessaire
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Relancement en administrateur...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo Corrector Ollama demarre en administrateur.
echo Raccourci : Ctrl+Shift+Espace
echo Ferme cette fenetre, l'app continue dans le systray.
echo.
cd /d "%~dp0"
python main.py
pause
