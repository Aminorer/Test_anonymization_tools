@echo off
setlocal enabledelayedexpansion
REM Forcer l'encodage Windows par defaut (pas UTF-8)
REM chcp 65001 > nul

REM -----------------------------------------------------------------
REM  Script d'installation - Version robuste
REM -----------------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%logs"

REM Creer le dossier logs en premier
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\install_and_run.log"

REM Fonction de log simplifiee (pas de caracteres speciaux)
echo ================================================ > "%LOG_FILE%"
echo Installation Anonymiseur - %date% %time% >> "%LOG_FILE%"
echo ================================================ >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo ================================================
echo   Installation Anonymiseur de Documents
echo ================================================
echo.
echo Le journal detaille est disponible ici :
echo %LOG_FILE%
echo.

REM Verification Python
echo [ETAPE 1/6] Verification de Python...
echo [%time%] Verification de Python... >> "%LOG_FILE%"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERREUR : Python n'est pas installe ou pas dans le PATH
    echo.
    echo Telechargement automatique de Python...
    echo [%time%] Python non trouve - Telechargement... >> "%LOG_FILE%"
    
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile 'python_installer.exe'}" 2>> "%LOG_FILE%"
    if %errorlevel% neq 0 (
        echo ERREUR lors du telechargement de Python
        echo Verifiez votre connexion internet
        echo Details dans : %LOG_FILE%
        pause
        exit /b 1
    )
    
    echo Installation de Python en cours (peut prendre 3-5 minutes)...
    echo [%time%] Installation de Python... >> "%LOG_FILE%"
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 2>> "%LOG_FILE%"
    if %errorlevel% neq 0 (
        echo ERREUR lors de l'installation de Python
        echo Essayez d'installer Python manuellement depuis python.org
        echo Details dans : %LOG_FILE%
        pause
        exit /b 1
    )
    
    del python_installer.exe
    echo.
    echo Python installe avec succes !
    echo IMPORTANT : FERMEZ cette fenetre et RELANCEZ install_and_run.bat
    echo [%time%] Python installe - Relancer necessaire >> "%LOG_FILE%"
    pause
    exit /b 0
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo OK - %PYTHON_VERSION% detecte
echo [%time%] Python OK : %PYTHON_VERSION% >> "%LOG_FILE%"
echo.

REM Creation environnement virtuel
echo [ETAPE 2/6] Creation de l'environnement virtuel...
echo [%time%] Creation venv... >> "%LOG_FILE%"
if not exist "%SCRIPT_DIR%venv" (
    python -m venv "%SCRIPT_DIR%venv" 2>> "%LOG_FILE%"
    if %errorlevel% neq 0 (
        echo ERREUR lors de la creation de l'environnement virtuel
        echo Details dans : %LOG_FILE%
        pause
        exit /b 1
    )
    echo OK - Environnement cree
    echo [%time%] Venv cree >> "%LOG_FILE%"
) else (
    echo OK - Environnement deja existant
    echo [%time%] Venv existe deja >> "%LOG_FILE%"
)
echo.

REM Activation et installation
echo [ETAPE 3/6] Activation de l'environnement...
echo [%time%] Activation venv... >> "%LOG_FILE%"
call "%SCRIPT_DIR%venv\Scripts\activate.bat" 2>> "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo ERREUR lors de l'activation de l'environnement
    echo Details dans : %LOG_FILE%
    pause
    exit /b 1
)
echo OK - Environnement active
echo [%time%] Venv active >> "%LOG_FILE%"
echo.

echo [ETAPE 4/6] Mise a jour de pip...
echo [%time%] Mise a jour pip... >> "%LOG_FILE%"
python -m pip install --upgrade pip --quiet 2>> "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo AVERTISSEMENT : pip n'a pas pu etre mis a jour
    echo L'installation continue...
    echo [%time%] Avertissement pip >> "%LOG_FILE%"
) else (
    echo OK - pip mis a jour
    echo [%time%] pip OK >> "%LOG_FILE%"
)
echo.

echo [ETAPE 5/6] Installation des dependances...
echo Cette etape peut prendre 2-5 minutes selon votre connexion...
echo [%time%] Installation requirements.txt... >> "%LOG_FILE%"
pip install -r "%SCRIPT_DIR%requirements.txt" >> "%LOG_FILE%" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo ERREUR lors de l'installation des dependances
    echo Verifiez :
    echo   - Votre connexion internet
    echo   - Le fichier requirements.txt existe
    echo   - Les details dans : %LOG_FILE%
    echo.
    pause
    exit /b 1
)
echo OK - Dependances installees
echo [%time%] Requirements OK >> "%LOG_FILE%"
echo.

REM Creation dossiers
echo [ETAPE 6/6] Creation des dossiers necessaires...
echo [%time%] Creation dossiers... >> "%LOG_FILE%"
for %%d in (temp logs exports data) do (
    if not exist "%SCRIPT_DIR%%%d" (
        mkdir "%SCRIPT_DIR%%%d" 2>> "%LOG_FILE%"
        echo - Dossier %%d cree
    ) else (
        echo - Dossier %%d deja present
    )
)
echo [%time%] Dossiers OK >> "%LOG_FILE%"
echo.

REM Raccourci bureau
echo Creation du raccourci sur le bureau...
echo [%time%] Creation raccourci... >> "%LOG_FILE%"
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Anonymiseur.lnk'); $Shortcut.TargetPath = '%SCRIPT_DIR%run_app.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = 'shell32.dll,48'; $Shortcut.Save()" 2>> "%LOG_FILE%"
if %errorlevel% neq 0 (
    echo AVERTISSEMENT : Raccourci non cree (non bloquant)
    echo [%time%] Avertissement raccourci >> "%LOG_FILE%"
) else (
    echo OK - Raccourci cree sur le bureau
    echo [%time%] Raccourci OK >> "%LOG_FILE%"
)
echo.

echo ================================================
echo   INSTALLATION TERMINEE AVEC SUCCES !
echo ================================================
echo.
echo L'application va demarrer dans 5 secondes...
echo Un raccourci "Anonymiseur" a ete cree sur votre bureau.
echo.
echo Pour les prochains lancements, utilisez :
echo   - Le raccourci bureau "Anonymiseur"
echo   - Ou run_app.bat dans ce dossier
echo.
echo [%time%] Installation complete >> "%LOG_FILE%"

timeout /t 5 >nul

REM Lancement
echo [%time%] Lancement application... >> "%LOG_FILE%"
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
start "" http://localhost:8501
streamlit run "%SCRIPT_DIR%main.py" --server.headless true --server.port 8501 2>> "%LOG_FILE%"

echo.
echo L'application s'est arretee.
echo Appuyez sur une touche pour fermer cette fenetre...
pause >nul
exit /b 0
