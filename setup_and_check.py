#!/usr/bin/env python3
"""
Script d'installation et de vérification complète
Anonymiseur de Documents Juridiques v2.0 avec NER
"""

import os
import sys
import subprocess
import importlib
import platform
import time
from pathlib import Path

class Colors:
    """Couleurs pour l'affichage console"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_colored(text, color=Colors.WHITE):
    """Afficher du texte coloré"""
    print(f"{color}{text}{Colors.END}")

def print_header(title):
    """Afficher un en-tête stylisé"""
    border = "=" * len(title)
    print_colored(f"\n{border}", Colors.CYAN)
    print_colored(title, Colors.CYAN + Colors.BOLD)
    print_colored(border, Colors.CYAN)

def print_step(step_num, description):
    """Afficher une étape"""
    print_colored(f"\n[{step_num}] {description}", Colors.BLUE + Colors.BOLD)

def check_python_version():
    """Vérifier la version Python"""
    print_step("1", "Vérification de la version Python")
    
    version = sys.version_info
    python_version = f"{version.major}.{version.minor}.{version.micro}"
    
    print(f"Version Python détectée: {python_version}")
    
    if version.major == 3 and 8 <= version.minor <= 11:
        print_colored("✅ Version Python compatible", Colors.GREEN)
        return True
    else:
        print_colored("❌ Version Python non supportée", Colors.RED)
        print_colored("Versions supportées: Python 3.8, 3.9, 3.10, 3.11", Colors.YELLOW)
        return False

def check_system_info():
    """Afficher les informations système"""
    print_step("2", "Informations système")
    
    print(f"Système d'exploitation: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Processeur: {platform.processor()}")
    
    # Mémoire RAM
    try:
        import psutil
        memory = psutil.virtual_memory()
        memory_gb = memory.total / (1024**3)
        print(f"Mémoire RAM: {memory_gb:.1f} GB")
        
        if memory_gb >= 8:
            print_colored("✅ RAM suffisante pour toutes les fonctionnalités", Colors.GREEN)
        elif memory_gb >= 4:
            print_colored("⚠️ RAM limitée - considérez les modèles légers", Colors.YELLOW)
        else:
            print_colored("❌ RAM insuffisante - fonctionnalités limitées", Colors.RED)
    except ImportError:
        print("Impossible de déterminer la RAM disponible")

def create_virtual_environment():
    """Créer un environnement virtuel"""
    print_step("3", "Création de l'environnement virtuel")
    
    venv_path = Path("venv_anonymizer")
    
    if venv_path.exists():
        print_colored("📁 Environnement virtuel existant détecté", Colors.YELLOW)
        response = input("Voulez-vous le recréer? (y/N): ").lower()
        
        if response == 'y':
            print("Suppression de l'ancien environnement...")
            import shutil
            shutil.rmtree(venv_path)
        else:
            print_colored("✅ Utilisation de l'environnement existant", Colors.GREEN)
            return True
    
    try:
        print("Création de l'environnement virtuel...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
        print_colored("✅ Environnement virtuel créé", Colors.GREEN)
        
        # Instructions d'activation
        if platform.system() == "Windows":
            activate_cmd = f"{venv_path}\\Scripts\\activate"
        else:
            activate_cmd = f"source {venv_path}/bin/activate"
        
        print_colored(f"💡 Pour activer: {activate_cmd}", Colors.CYAN)
        return True
        
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Erreur création environnement: {e}", Colors.RED)
        return False

def get_pip_executable():
    """Obtenir l'exécutable pip approprié"""
    venv_path = Path("venv_anonymizer")
    
    if platform.system() == "Windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"
    
    if pip_exe.exists():
        return str(pip_exe)
    else:
        return "pip"  # Fallback

def install_dependencies():
    """Installer les dépendances"""
    print_step("4", "Installation des dépendances")
    
    pip_exe = get_pip_executable()
    
    # Mise à jour de pip
    print("Mise à jour de pip...")
    try:
        subprocess.run([pip_exe, "install", "--upgrade", "pip"], check=True, capture_output=True)
        print_colored("✅ Pip mis à jour", Colors.GREEN)
    except subprocess.CalledProcessError:
        print_colored("⚠️ Impossible de mettre à jour pip", Colors.YELLOW)
    
    # Installation des dépendances principales
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print_colored("❌ Fichier requirements.txt non trouvé", Colors.RED)
        return False
    
    print("Installation des dépendances principales...")
    try:
        # Installation par étapes pour éviter les conflits
        essential_packages = [
            "streamlit>=1.28.0",
            "python-docx>=0.8.11",
            "pdfplumber>=0.7.6",
            "pandas>=1.5.0",
            "plotly>=5.15.0"
        ]
        
        for package in essential_packages:
            print(f"Installation de {package}...")
            subprocess.run([pip_exe, "install", package], check=True, capture_output=True)
        
        print_colored("✅ Packages essentiels installés", Colors.GREEN)
        
        # Installation PyTorch (critique pour éviter conflits)
        print("Installation de PyTorch...")
        subprocess.run([
            pip_exe, "install", 
            "torch>=1.12.0,<2.1.0",
            "torchvision>=0.13.0,<0.16.0", 
            "torchaudio>=0.12.0,<0.15.0",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ], check=True, capture_output=True)
        
        print_colored("✅ PyTorch installé", Colors.GREEN)
        
        # Installation Transformers
        print("Installation de Transformers...")
        subprocess.run([
            pip_exe, "install",
            "transformers>=4.21.0,<5.0.0",
            "tokenizers>=0.13.0,<1.0.0"
        ], check=True, capture_output=True)
        
        print_colored("✅ Transformers installé", Colors.GREEN)
        
        # Installation du reste
        print("Installation des dépendances restantes...")
        subprocess.run([pip_exe, "install", "-r", str(requirements_file)], check=True, capture_output=True)
        
        print_colored("✅ Toutes les dépendances installées", Colors.GREEN)
        return True
        
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Erreur installation: {e}", Colors.RED)
        return False

def install_spacy_models():
    """Installer les modèles SpaCy français"""
    print_step("5", "Installation des modèles SpaCy français")
    
    pip_exe = get_pip_executable()
    
    models = [
        ("fr_core_news_sm", "Modèle français compact (~50MB)"),
        ("fr_core_news_lg", "Modèle français large (~500MB)")
    ]
    
    for model_name, description in models:
        print(f"Installation de {model_name} - {description}")
        
        try:
            # Vérifier si déjà installé
            result = subprocess.run([
                get_python_executable(), "-c", 
                f"import spacy; spacy.load('{model_name}'); print('OK')"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_colored(f"✅ {model_name} déjà installé", Colors.GREEN)
                continue
            
            # Installation
            subprocess.run([
                get_python_executable(), "-m", "spacy", "download", model_name
            ], check=True, capture_output=True)
            
            print_colored(f"✅ {model_name} installé", Colors.GREEN)
            
        except subprocess.CalledProcessError:
            print_colored(f"⚠️ Impossible d'installer {model_name}", Colors.YELLOW)
            print("Vous pouvez l'installer manuellement plus tard.")

def get_python_executable():
    """Obtenir l'exécutable Python approprié"""
    venv_path = Path("venv_anonymizer")
    
    if platform.system() == "Windows":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    if python_exe.exists():
        return str(python_exe)
    else:
        return sys.executable

def test_dependencies():
    """Tester toutes les dépendances"""
    print_step("6", "Test des dépendances")
    
    dependencies = {
        # Obligatoires
        "streamlit": "Interface utilisateur",
        "docx": "Traitement documents Word",  # Note: module s'appelle 'docx' pas 'python-docx'
        "pdfplumber": "Extraction PDF",
        "pandas": "Traitement données",
        "plotly": "Graphiques",
        
        # IA
        "torch": "PyTorch (IA)",
        "transformers": "Modèles NER",
        "spacy": "NER français",
        
        # Utilitaires
        "PIL": "Traitement images",  # Note: Pillow s'importe comme PIL
        "psutil": "Informations système",
        "requests": "Requêtes HTTP"
    }
    
    available = {}
    issues = []
    
    python_exe = get_python_executable()
    
    for module_name, description in dependencies.items():
        try:
            result = subprocess.run([
                python_exe, "-c", f"import {module_name}; print('OK')"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                available[module_name] = True
                print_colored(f"✅ {module_name}: {description}", Colors.GREEN)
            else:
                available[module_name] = False
                print_colored(f"❌ {module_name}: {description}", Colors.RED)
                issues.append(module_name)
                
        except Exception as e:
            available[module_name] = False
            print_colored(f"❌ {module_name}: Erreur test - {e}", Colors.RED)
            issues.append(module_name)
    
    return available, issues

def test_spacy_models():
    """Tester les modèles SpaCy"""
    print_step("7", "Test des modèles SpaCy")
    
    python_exe = get_python_executable()
    
    models = [
        "fr_core_news_sm",
        "fr_core_news_lg"
    ]
    
    available_models = []
    
    for model in models:
        try:
            result = subprocess.run([
                python_exe, "-c",
                f"import spacy; nlp = spacy.load('{model}'); print('OK')"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_colored(f"✅ {model} fonctionnel", Colors.GREEN)
                available_models.append(model)
            else:
                print_colored(f"❌ {model} non disponible", Colors.RED)
                
        except Exception as e:
            print_colored(f"❌ {model} erreur: {e}", Colors.RED)
    
    return available_models

def test_pytorch_streamlit_compatibility():
    """Tester la compatibilité PyTorch/Streamlit"""
    print_step("8", "Test compatibilité PyTorch/Streamlit")
    
    python_exe = get_python_executable()
    
    test_script = '''
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

try:
    import torch
    torch.set_num_threads(1)
    print("PyTorch OK")
    
    import transformers
    print("Transformers OK")
    
    # Test basique
    from transformers import pipeline
    print("Pipeline OK")
    
    print("SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
'''
    
    try:
        result = subprocess.run([
            python_exe, "-c", test_script
        ], capture_output=True, text=True, timeout=30)
        
        if "SUCCESS" in result.stdout:
            print_colored("✅ PyTorch/Streamlit compatible", Colors.GREEN)
            return True
        else:
            print_colored("❌ Problème de compatibilité détecté", Colors.RED)
            print("Sortie:", result.stdout)
            print("Erreur:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print_colored("⚠️ Test de compatibilité timeout", Colors.YELLOW)
        return False
    except Exception as e:
        print_colored(f"❌ Erreur test compatibilité: {e}", Colors.RED)
        return False

def run_quick_functional_test():
    """Exécuter un test fonctionnel rapide"""
    print_step("9", "Test fonctionnel rapide")
    
    python_exe = get_python_executable()
    
    test_script = '''
import sys
import os

# Configuration anti-conflit
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "1"

try:
    # Test imports
    import streamlit as st
    print("✅ Streamlit importé")
    
    # Ajouter le chemin du projet
    sys.path.insert(0, ".")
    
    # Test anonymizer
    from src.anonymizer import DocumentAnonymizer, RegexAnonymizer
    print("✅ Modules anonymizer importés")
    
    # Test regex
    regex_anonymizer = RegexAnonymizer()
    test_text = "Contact: jean.dupont@email.com, tél: 01 23 45 67 89"
    entities = regex_anonymizer.detect_entities(test_text)
    print(f"✅ Regex: {len(entities)} entités détectées")
    
    # Test IA (si disponible)
    try:
        anonymizer = DocumentAnonymizer()
        if anonymizer.ai_anonymizer:
            ai_entities = anonymizer.ai_anonymizer.detect_entities_ai(test_text, 0.7)
            print(f"✅ IA: {len(ai_entities)} entités détectées")
        else:
            print("ℹ️ IA non disponible (normal)")
    except Exception as e:
        print(f"⚠️ Test IA échoué: {e}")
    
    print("SUCCESS: Tests fonctionnels réussis")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
'''
    
    try:
        result = subprocess.run([
            python_exe, "-c", test_script
        ], capture_output=True, text=True, timeout=60)
        
        if "SUCCESS" in result.stdout:
            print_colored("✅ Tests fonctionnels réussis", Colors.GREEN)
            print(result.stdout)
            return True
        else:
            print_colored("❌ Tests fonctionnels échoués", Colors.RED)
            print("Sortie:", result.stdout)
            print("Erreur:", result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print_colored("⚠️ Tests fonctionnels timeout", Colors.YELLOW)
        return False
    except Exception as e:
        print_colored(f"❌ Erreur tests fonctionnels: {e}", Colors.RED)
        return False

def generate_report(test_results):
    """Générer un rapport de diagnostic"""
    print_step("10", "Génération du rapport de diagnostic")
    
    report_path = Path("installation_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Rapport d'Installation - Anonymiseur de Documents\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Informations Système\n")
        f.write(f"- Système: {platform.system()} {platform.release()}\n")
        f.write(f"- Python: {sys.version}\n")
        f.write(f"- Architecture: {platform.machine()}\n\n")
        
        f.write("## Résultats des Tests\n")
        for test_name, result in test_results.items():
            status = "✅ RÉUSSI" if result else "❌ ÉCHOUÉ"
            f.write(f"- {test_name}: {status}\n")
        
        f.write("\n## Recommandations\n")
        
        if not test_results.get("dependencies", True):
            f.write("- Réinstallez les dépendances manquantes\n")
        
        if not test_results.get("pytorch_compatibility", True):
            f.write("- Vérifiez la compatibilité PyTorch/Streamlit\n")
            f.write("- Essayez de réinstaller torch en premier\n")
        
        if not test_results.get("spacy_models", True):
            f.write("- Installez les modèles SpaCy manuellement:\n")
            f.write("  ```bash\n")
            f.write("  python -m spacy download fr_core_news_sm\n")
            f.write("  python -m spacy download fr_core_news_lg\n")
            f.write("  ```\n")
        
        f.write("\n## Commandes Utiles\n")
        f.write("```bash\n")
        f.write("# Activer l'environnement virtuel\n")
        if platform.system() == "Windows":
            f.write("venv_anonymizer\\Scripts\\activate\n")
        else:
            f.write("source venv_anonymizer/bin/activate\n")
        f.write("\n# Lancer l'application\n")
        f.write("streamlit run main.py\n")
        f.write("```\n")
    
    print_colored(f"✅ Rapport généré: {report_path}", Colors.GREEN)

def main():
    """Fonction principale"""
    print_colored("🛡️ ANONYMISEUR DE DOCUMENTS JURIDIQUES v2.0", Colors.MAGENTA + Colors.BOLD)
    print_colored("Installation et Vérification Complète avec NER", Colors.CYAN)
    
    test_results = {}
    
    # Tests étape par étape
    test_results["python_version"] = check_python_version()
    
    if not test_results["python_version"]:
        print_colored("\n❌ Version Python incompatible. Installation arrêtée.", Colors.RED)
        return
    
    check_system_info()
    
    test_results["venv_creation"] = create_virtual_environment()
    test_results["dependencies"] = install_dependencies()
    
    if test_results["dependencies"]:
        install_spacy_models()
        
        available_deps, issues = test_dependencies()
        test_results["dependencies"] = len(issues) == 0
        
        spacy_models = test_spacy_models()
        test_results["spacy_models"] = len(spacy_models) > 0
        
        test_results["pytorch_compatibility"] = test_pytorch_streamlit_compatibility()
        test_results["functional_tests"] = run_quick_functional_test()
    
    # Résumé final
    print_header("RÉSUMÉ DE L'INSTALLATION")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"Tests réussis: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print_colored("🎉 INSTALLATION COMPLÈTE RÉUSSIE!", Colors.GREEN + Colors.BOLD)
        print_colored("Vous pouvez maintenant lancer l'application avec:", Colors.CYAN)
        print_colored("streamlit run main.py", Colors.WHITE + Colors.BOLD)
    elif passed_tests >= total_tests * 0.8:
        print_colored("⚠️ Installation majoritairement réussie", Colors.YELLOW + Colors.BOLD)
        print_colored("Quelques fonctionnalités peuvent être limitées", Colors.YELLOW)
    else:
        print_colored("❌ Installation incomplète", Colors.RED + Colors.BOLD)
        print_colored("Consultez le rapport pour les solutions", Colors.RED)
    
    # Générer le rapport
    generate_report(test_results)
    
    print_colored("\n📋 Rapport détaillé sauvegardé dans installation_report.md", Colors.CYAN)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n⏹️ Installation interrompue par l'utilisateur", Colors.YELLOW)
        sys.exit(1)
    except Exception as e:
        print_colored(f"\n\n❌ Erreur inattendue: {e}", Colors.RED)
        import traceback
        traceback.print_exc()
        sys.exit(1)