#!/usr/bin/env bash
# Script d'installation automatisée de l'anonymiseur
# Crée un environnement virtuel et installe les dépendances

set -e

PYTHON=${PYTHON:-python3}
VENV_DIR=.venv

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Python3 est requis mais introuvable." >&2
    exit 1
fi

# Création de l'environnement virtuel
if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Activation de l'environnement
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r requirements.txt

echo "Installation terminée. Activez l'environnement avec 'source $VENV_DIR/bin/activate' et lancez 'python run.py'"
