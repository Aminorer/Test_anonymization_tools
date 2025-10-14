@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul

REM -----------------------------------------------------------------
REM  Journalisation des actions pour faciliter le diagnostic
REM -----------------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
set "LOG_DIR=%SCRIPT_DIR%logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\install_and_run.log"

call :log "════════════════════════════════════════════════════════════"
call :log "  🛡️ Anonymiseur de Documents - Installation Automatique"
call :log "════════════════════════════════════════════════════════════"
call :log "Le journal détaillé est disponible ici : %LOG_FILE%"
echo.

REM Vérification de Python
call :log "🔍 Vérification de l'installation de Python..."
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log "❌ Python n'est pas installé. Téléchargement en cours..."
    echo.
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile 'python_installer.exe'}"
    call :ensure_success "Téléchargement de Python"
    call :log "⏳ Installation de Python (cela peut prendre quelques minutes)..."
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    call :ensure_success "Installation de Python"
    del python_installer.exe
    call :log "✅ Python installé avec succès !"
    call :log "⚠️ Veuillez FERMER cette fenêtre et RELANCER install_and_run.bat"
    pause
    exit /b 0
)

for /f "tokens=*" %%i in ('python --version') do set "PYTHON_VERSION=%%i"
call :log "✅ Python détecté : !PYTHON_VERSION!"
echo.

REM Création de l'environnement virtuel
if not exist "%SCRIPT_DIR%venv" (
    call :log "📦 Création de l'environnement virtuel..."
    python -m venv "%SCRIPT_DIR%venv"
    call :ensure_success "Création de l'environnement virtuel"
    call :log "✅ Environnement créé"
) else (
    call :log "✅ Environnement virtuel déjà existant"
)
echo.

REM Activation et installation des dépendances
call :log "📥 Installation des dépendances (cela peut prendre 2-5 minutes)..."
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
call :ensure_success "Activation de l'environnement virtuel"
python -m pip install --upgrade pip
call :ensure_success "Mise à jour de pip"
pip install -r "%SCRIPT_DIR%requirements.txt"
call :ensure_success "Installation des dépendances"
call :log "✅ Dépendances installées"
echo.

REM Création des dossiers nécessaires
for %%d in (temp logs exports data) do (
    if not exist "%SCRIPT_DIR%%%d" (
        mkdir "%SCRIPT_DIR%%%d"
        call :log "📁 Dossier %%d créé"
    ) else (
        call :log "✅ Dossier %%d déjà présent"
    )
)
echo.

REM Création du raccourci bureau
call :log "🖇️ Création d'un raccourci sur le bureau..."
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Anonymiseur.lnk'); $Shortcut.TargetPath = '%SCRIPT_DIR%run_app.bat'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = 'shell32.dll,48'; $Shortcut.Save()"
call :ensure_success "Création du raccourci"
call :log "✅ Raccourci créé sur le bureau"
echo.

call :log "════════════════════════════════════════════════════════════"
call :log "  ✅ INSTALLATION TERMINÉE AVEC SUCCÈS !"
call :log "════════════════════════════════════════════════════════════"
call :log "🚀 L'application va démarrer dans 3 secondes..."
call :log "📌 Un raccourci Anonymiseur a été créé sur votre bureau"
echo.

timeout /t 3 >nul

REM Lancement de l'application
call "%SCRIPT_DIR%venv\Scripts\activate.bat"
call :ensure_success "Activation de l'environnement virtuel"
start "" http://localhost:8501
call :log "🌐 Ouverture du navigateur sur http://localhost:8501"
streamlit run "%SCRIPT_DIR%main.py" --server.headless true --server.port 8501
call :ensure_success "Lancement de l'application"

call :log "ℹ️ Le script s'est terminé correctement. Fermez cette fenêtre pour quitter."
pause
exit /b 0

:ensure_success
set "last_error=%errorlevel%"
if not "%last_error%"=="0" (
    call :log "❌ %~1 (code %last_error%)"
    echo.
    echo Une erreur est survenue pendant l'étape : %~1
    echo Consultez le journal pour plus de détails : %LOG_FILE%
    pause
    exit /b %last_error%
) else (
    call :log "✅ %~1"
)
exit /b 0

:log
set "timestamp=%date% %time%"
echo [%timestamp%] %~1>>"%LOG_FILE%"
echo %~1
exit /b 0
