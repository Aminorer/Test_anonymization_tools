@echo off
echo === CORRECTION PYTORCH POUR PYTHON 3.12 ===

echo Activation de l'environnement virtuel...
call venv_anonymizer\Scripts\activate

echo.
echo Installation de PyTorch compatible Python 3.12...
pip install torch>=2.0.0 torchvision>=0.15.0 torchaudio>=2.0.0 --index-url https://download.pytorch.org/whl/cpu

echo.
echo Test de PyTorch...
python -c "import torch; print('PyTorch version:', torch.__version__); print('✅ PyTorch installé avec succès!')"

echo.
echo Installation terminée!
pause