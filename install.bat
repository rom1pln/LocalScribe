@echo off
echo.
echo  Installation de Corrector Ollama
echo  -----------------------------------
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo  Telecharge Python sur https://python.org
    pause
    exit /b 1
)

echo  [1/2] Installation des dependances Python...
pip install -r "%~dp0requirements.txt"
if %errorlevel% neq 0 (
    echo.
    echo  [ERREUR] L'installation a echoue.
    pause
    exit /b 1
)

echo.
echo  [2/2] Creation du demarrage automatique...

set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set VBSFILE=%~dp0start_hidden.vbs

echo Set oShell = CreateObject("WScript.Shell") > "%VBSFILE%"
echo oShell.Run "pythonw ""%~dp0main.py""", 0, False >> "%VBSFILE%"

powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP%\Corrector Ollama.lnk');$s.TargetPath='%VBSFILE%';$s.WorkingDirectory='%~dp0';$s.Save()"

echo.
echo  -----------------------------------
echo  Installation terminee !
echo.
echo  UTILISATION :
echo   - Lance start.bat pour demarrer maintenant
echo   - Ou redemarre Windows (demarrage auto active)
echo   - Selectionne du texte n'importe ou
echo   - Appuie sur Ctrl+Shift+Espace
echo   - Accepte ou ignore la correction dans le popup
echo.
echo  CONFIGURATION :
echo   - Modifie config.json pour changer le modele ou le raccourci
echo   - Modele par defaut : llama3.2
echo.
pause
