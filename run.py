#!/usr/bin/env python3
"""
Script de lancement pour l'Anonymiseur de Documents Juridiques
Usage: python run.py [--dev] [--port PORT] [--host HOST]
"""

import os
import sys
import logging
import argparse
import subprocess
import importlib.util
from pathlib import Path


def is_frozen():
    """Détecter si l'application est exécutée depuis un exécutable PyInstaller."""

    return getattr(sys, "frozen", False)

def setup_logging():
    """Configuration du logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('anonymizer.log')
        ]
    )

def _is_module_available(module_names):
    """Retourne True si l'un des modules listés est importable."""

    for module_name in module_names:
        if importlib.util.find_spec(module_name) is not None:
            return True
    return False


def check_dependencies():
    """Vérifier les dépendances critiques"""

    if is_frozen():
        print(
            "🔒 Exécution dans un exécutable PyInstaller — vérification des dépendances "
            "critiques désactivée."
        )
        return True

    required_packages = {
        'streamlit': ['streamlit'],
        # python-docx est importable via le module "docx"
        'python-docx': ['docx'],
        'pdfplumber': ['pdfplumber'],
        'pdf2docx': ['pdf2docx']
    }

    missing = [
        package
        for package, module_names in required_packages.items()
        if not _is_module_available(module_names)
    ]

    if missing:
        print(f"❌ Dépendances manquantes: {', '.join(missing)}")
        print("📦 Installez avec: pip install -r requirements.txt")
        return False

    print("✅ Toutes les dépendances critiques sont installées")
    return True

def check_optional_dependencies():
    """Vérifier les dépendances optionnelles"""
    optional_packages = {
        'transformers': 'Mode IA (NER) désactivé',
        'torch': 'Mode IA (NER) désactivé', 
        'plotly': 'Graphiques avancés désactivés',
        'pandas': 'Fonctionnalités d\'analyse limitées'
    }
    
    for package, message in optional_packages.items():
        try:
            __import__(package)
            print(f"✅ {package} disponible")
        except ImportError:
            print(f"⚠️ {package} manquant - {message}")

def create_directories():
    """Créer les répertoires nécessaires"""
    directories = [
        'temp',
        'logs', 
        'exports',
        'data'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"📁 Répertoire créé/vérifié: {directory}")

def check_streamlit_config():
    """Vérifier et créer la configuration Streamlit"""
    config_dir = Path.home() / '.streamlit'
    config_file = config_dir / 'config.toml'
    
    config_dir.mkdir(exist_ok=True)
    
    if not config_file.exists():
        config_content = """
[server]
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[logger]
level = "info"
"""
        config_file.write_text(config_content.strip())
        print("⚙️ Configuration Streamlit créée")
    else:
        print("⚙️ Configuration Streamlit existante")

def run_streamlit(host='localhost', port=8501, dev_mode=False):
    """Lancer l'application Streamlit"""
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'main.py',
        '--server.address', host,
        '--server.port', str(port),
        '--server.headless', 'true'
    ]
    
    if dev_mode:
        cmd.extend(['--server.runOnSave', 'true'])
        print("🔧 Mode développement activé")
    
    print(f"🚀 Lancement de l'application sur http://{host}:{port}")
    print("⏹️ Arrêt: Ctrl+C")
    print("-" * 60)
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Application arrêtée")
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")

def display_info():
    """Afficher les informations de l'application"""
    print("=" * 60)
    print("🛡️ ANONYMISEUR DE DOCUMENTS JURIDIQUES")
    print("=" * 60)
    print("📋 Fonctionnalités:")
    print("   • Anonymisation PDF et DOCX")
    print("   • Détection Regex et IA (NER)")
    print("   • Interface intuitive Streamlit")
    print("   • Gestion d'entités et groupes")
    print("   • Export avec options avancées")
    print("   • Conformité RGPD")
    print("=" * 60)

def display_usage_info(host, port):
    """Afficher les informations d'utilisation"""
    print("\n📖 GUIDE D'UTILISATION:")
    print(f"1. Ouvrez votre navigateur sur http://{host}:{port}")
    print("2. Uploadez un document PDF ou DOCX")
    print("3. Choisissez le mode d'analyse (Regex ou IA)")
    print("4. Lancez l'analyse et attendez les résultats")
    print("5. Gérez les entités détectées si nécessaire")
    print("6. Exportez le document anonymisé")
    print("\n💡 CONSEILS:")
    print("   • Mode Regex: Rapide, idéal pour documents standardisés")
    print("   • Mode IA: Plus précis, pour documents complexes")
    print("   • Vérifiez toujours les entités avant l'export final")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(
        description="Anonymiseur de Documents Juridiques - Streamlit"
    )
    parser.add_argument(
        '--host',
        default='localhost',
        help='Adresse d\'écoute (défaut: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8501,
        help='Port du serveur (défaut: 8501)'
    )
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Mode développement avec auto-reload'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Vérifier uniquement les dépendances'
    )
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Ne pas ouvrir le navigateur automatiquement'
    )
    
    args = parser.parse_args()
    
    # Configuration du logging
    setup_logging()
    
    # Affichage des informations
    display_info()
    
    # Vérifications préliminaires
    print("\n🔍 VÉRIFICATIONS SYSTÈME:")
    
    if not check_dependencies():
        sys.exit(1)
    
    check_optional_dependencies()
    
    if args.check_only:
        print("\n✅ Vérifications terminées")
        sys.exit(0)
    
    # Préparation de l'environnement
    print("\n⚙️ PRÉPARATION:")
    create_directories()
    check_streamlit_config()
    
    # Informations d'utilisation
    display_usage_info(args.host, args.port)
    
    # Lancement de l'application
    print(f"\n🚀 LANCEMENT:")
    
    # Ouvrir le navigateur si demandé
    if not args.no_browser and args.host in ['localhost', '127.0.0.1']:
        import webbrowser
        import threading
        import time
        
        def open_browser():
            time.sleep(2)  # Attendre que le serveur soit prêt
            webbrowser.open(f'http://{args.host}:{args.port}')
        
        threading.Thread(target=open_browser, daemon=True).start()
    
    # Démarrage de Streamlit
    run_streamlit(args.host, args.port, args.dev)

if __name__ == "__main__":
    main()
