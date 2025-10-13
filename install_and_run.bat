@echo off
chcp 65001 > nul

echo ════════════════════════════════════════════════════════════
echo   🛡️ Anonymiseur de Documents - Installation Automatique
echo ════════════════════════════════════════════════════════════
echo.

REM Vérification de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python n'est pas installé. Téléchargement en cours...
    echo.
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile 'python_installer.exe'}"
    echo Installation de Python (cela peut prendre quelques minutes)...
    python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
    echo.
    echo ✅ Python installé avec succès!
    echo ⚠️ Veuillez FERMER cette fenêtre et RELANCER install_and_run.bat
    pause
    exit
)

echo ✅ Python détecté:
python --version
echo.

REM Création de l'environnement virtuel
if not exist "venv" (
    echo 📦 Création de l'environnement virtuel...
    python -m venv venv
    echo ✅ Environnement créé
) else (
    echo ✅ Environnement virtuel déjà existant
)
echo.

REM Activation et installation des dépendances
echo 📥 Installation des dépendances (cela peut prendre 2-5 minutes)...
call venv\Scripts\activate
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo ✅ Dépendances installées
echo.

REM Création des dossiers nécessaires
if not exist "temp" mkdir temp
if not exist "logs" mkdir logs
if not exist "exports" mkdir exports
if not exist "data" mkdir data
echo ✅ Dossiers créés
echo.

REM Création du raccourci bureau
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%USERPROFILE%\Desktop\Anonymiseur.lnk'); $Shortcut.TargetPath = '%CD%\run_app.bat'; $Shortcut.WorkingDirectory = '%CD%'; $Shortcut.IconLocation = 'shell32.dll,48'; $Shortcut.Save()"
echo ✅ Raccourci créé sur le bureau
echo.

echo ════════════════════════════════════════════════════════════
echo   ✅ INSTALLATION TERMINÉE AVEC SUCCÈS !
echo ════════════════════════════════════════════════════════════
echo.
echo 🚀 L'application va démarrer dans 3 secondes...
echo 📌 Un raccourci "Anonymiseur" a été créé sur votre bureau
echo.

timeout /t 3 >nul

REM Lancement de l'application
call venv\Scripts\activate
start "" http://localhost:8501
streamlit run main.py --server.headless true --server.port 8501

pause
