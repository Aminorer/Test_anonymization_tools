@echo off
chcp 65001 > nul

echo 🚀 Démarrage de l'Anonymiseur...
call venv\Scripts\activate
start "" http://localhost:8501
streamlit run main.py --server.headless true --server.port 8501
