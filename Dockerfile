# Image de base légère avec Python
FROM python:3.10-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie des fichiers de dépendances
COPY requirements.txt ./

# Installation des dépendances système (si nécessaire) et Python
# L'option --no-cache-dir réduit la taille de l'image
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copie du reste du code source
COPY . .

# Exposition du port utilisé par Streamlit
EXPOSE 8501

# Commande de démarrage par défaut
CMD ["streamlit", "run", "run.py", "--server.port=8501", "--server.address=0.0.0.0"]
