@echo off
REM Script de lancement rapide - Version robuste

echo Demarrage de l'Anonymiseur...

REM Verification que venv existe
if not exist "%~dp0venv\Scripts\activate.bat" (
    echo.
    echo ERREUR : Environnement virtuel non trouve !
    echo.
    echo Lancez d'abord install_and_run.bat pour installer l'application.
    echo.
    pause
    exit /b 1
)

REM Activation
call "%~dp0venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo ERREUR lors de l'activation de l'environnement
    pause
    exit /b 1
)

REM Lancement
start "" http://localhost:8501
streamlit run "%~dp0main.py" --server.headless true --server.port 8501

pause
