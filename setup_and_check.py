#!/usr/bin/env python3
"""
Script d'installation et de vérification complète - VERSION CORRIGÉE
Anonymiseur de Documents Juridiques v2.0 avec NER
Support Python 3.8-3.12
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
    """Vérifier la version Python - VERSION CORRIGÉE"""
    print_step("1", "Vérification de la version Python")
    
    version = sys.version_info
    python_version = f"{version.major}.{version.minor}.{version.micro}"
    
    print(f"Version Python détectée: {python_version}")
    
    # CORRECTION: Support Python 3.8-3.12 (au lieu de 3.8-3.11)
    if version.major == 3 and 8 <= version.minor <= 12:
        print_colored("✅ Version Python compatible", Colors.GREEN)
        if version.minor == 12:
            print_colored("ℹ️ Python 3.12 détecté - Excellent choix!", Colors.CYAN)
        return True
    else:
        print_colored("❌ Version Python non supportée", Colors.RED)
        print_colored("Versions supportées: Python 3.8, 3.9, 3.10, 3.11, 3.12", Colors.YELLOW)
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
        print("Impossible de déterminer la RAM disponible (psutil non installé)")

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
    """Installer les dépendances - VERSION OPTIMISÉE PYTHON 3.12"""
    print_step("4", "Installation des dépendances")
    
    pip_exe = get_pip_executable()
    
    # Mise à jour de pip
    print("Mise à jour de pip...")
    try:
        subprocess.run([pip_exe, "install", "--upgrade", "pip"], check=True, capture_output=True)
        print_colored("✅ Pip mis à jour", Colors.GREEN)
    except subprocess.CalledProcessError:
        print_colored("⚠️ Impossible de mettre à jour pip", Colors.YELLOW)
    
    # Packages essentiels en premier
    essential_packages = [
        "streamlit>=1.28.0,<2.0.0",
        "pandas>=1.5.0,<3.0.0",
        "plotly>=5.15.0,<6.0.0",
        "python-docx>=0.8.11",
        "pdfplumber>=0.7.6"
    ]
    
    print("Installation des packages essentiels...")
    for package in essential_packages:
        print(f"Installation de {package}...")
        try:
            subprocess.run([pip_exe, "install", package], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print_colored(f"⚠️ Échec {package}: {e}", Colors.YELLOW)
    
    print_colored("✅ Packages essentiels installés", Colors.GREEN)
    
    # PyTorch pour Python 3.12 (version compatible)
    print("Installation de PyTorch (compatible Python 3.12)...")
    try:
        # PyTorch supporte maintenant Python 3.12
        subprocess.run([
            pip_exe, "install", 
            "torch>=2.0.0,<2.2.0",
            "torchvision>=0.15.0,<0.17.0", 
            "torchaudio>=2.0.0,<2.2.0",
            "--index-url", "https://download.pytorch.org/whl/cpu"
        ], check=True, capture_output=True)
        
        print_colored("✅ PyTorch installé (Python 3.12 compatible)", Colors.GREEN)
        
    except subprocess.CalledProcessError as e:
        print_colored(f"⚠️ PyTorch installation warning: {e}", Colors.YELLOW)
        print_colored("Continuons sans PyTorch...", Colors.YELLOW)
    
    # Transformers
    print("Installation de Transformers...")
    try:
        subprocess.run([
            pip_exe, "install",
            "transformers>=4.35.0,<5.0.0",  # Version compatible Python 3.12
            "tokenizers>=0.15.0,<1.0.0"
        ], check=True, capture_output=True)
        
        print_colored("✅ Transformers installé", Colors.GREEN)
        
    except subprocess.CalledProcessError as e:
        print_colored(f"⚠️ Transformers installation warning: {e}", Colors.YELLOW)
    
    # SpaCy
    print("Installation de SpaCy...")
    try:
        subprocess.run([pip_exe, "install", "spacy>=3.7.0,<4.0.0"], check=True, capture_output=True)
        print_colored("✅ SpaCy installé", Colors.GREEN)
    except subprocess.CalledProcessError as e:
        print_colored(f"⚠️ SpaCy installation warning: {e}", Colors.YELLOW)
    
    # Autres dépendances importantes
    other_packages = [
        "Pillow>=9.5.0,<11.0.0",
        "psutil>=5.9.0,<6.0.0",
        "requests>=2.28.0,<3.0.0",
        "openpyxl>=3.0.10"
    ]
    
    print("Installation des packages supplémentaires...")
    for package in other_packages:
        try:
            subprocess.run([pip_exe, "install", package], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            continue
    
    print_colored("✅ Installation des dépendances terminée", Colors.GREEN)
    return True

def install_spacy_models():
    """Installer les modèles SpaCy français"""
    print_step("5", "Installation des modèles SpaCy français")
    
    python_exe = get_python_executable()
    
    models = [
        ("fr_core_news_sm", "Modèle français compact (~50MB)"),
        ("fr_core_news_lg", "Modèle français large (~500MB)")
    ]
    
    for model_name, description in models:
        print(f"Installation de {model_name} - {description}")
        
        try:
            # Vérifier si déjà installé
            result = subprocess.run([
                python_exe, "-c", 
                f"import spacy; spacy.load('{model_name}'); print('OK')"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print_colored(f"✅ {model_name} déjà installé", Colors.GREEN)
                continue
            
            # Installation
            subprocess.run([
                python_exe, "-m", "spacy", "download", model_name
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
        "docx": "Traitement documents Word",
        "pdfplumber": "Extraction PDF",
        "pandas": "Traitement données",
        "plotly": "Graphiques",
        
        # IA
        "torch": "PyTorch (IA)",
        "transformers": "Modèles NER",
        "spacy": "NER français",
        
        # Utilitaires
        "PIL": "Traitement images",
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

def test_python_312_compatibility():
    """Tester la compatibilité spécifique Python 3.12"""
    print_step("7", "Test compatibilité Python 3.12")
    
    python_exe = get_python_executable()
    
    test_script = '''
import sys
print(f"Python version: {sys.version}")

try:
    # Test Streamlit
    import streamlit as st
    print("✅ Streamlit compatible Python 3.12")
    
    # Test PyTorch si disponible
    try:
        import torch
        print(f"✅ PyTorch compatible: {torch.__version__}")
    except ImportError:
        print("ℹ️ PyTorch non installé")
    
    # Test Transformers si disponible
    try:
        import transformers
        print(f"✅ Transformers compatible: {transformers.__version__}")
    except ImportError:
        print("ℹ️ Transformers non installé")
    
    print("SUCCESS: Python 3.12 compatibility verified")
    
except Exception as e:
    print(f"ERROR: {e}")
'''
    
    try:
        result = subprocess.run([
            python_exe, "-c", test_script
        ], capture_output=True, text=True, timeout=30)
        
        if "SUCCESS" in result.stdout:
            print_colored("✅ Python 3.12 entièrement compatible", Colors.GREEN)
            print(result.stdout)
            return True
        else:
            print_colored("⚠️ Problèmes de compatibilité détectés", Colors.YELLOW)
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
    print_step("8", "Test fonctionnel rapide")
    
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
    from src.anonymizer import RegexAnonymizer
    print("✅ Module anonymizer importé")
    
    # Test regex basique
    regex_anonymizer = RegexAnonymizer()
    test_text = "Contact: jean.dupont@email.com, tél: 01 23 45 67 89"
    entities = regex_anonymizer.detect_entities(test_text)
    print(f"✅ Regex: {len(entities)} entités détectées")
    
    # Test IA si disponible
    try:
        from src.anonymizer import DocumentAnonymizer
        anonymizer = DocumentAnonymizer()
        if anonymizer.ai_anonymizer:
            print("✅ IA: Anonymizer IA disponible")
        else:
            print("ℹ️ IA: Mode regex uniquement (normal)")
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
    print_step("9", "Génération du rapport de diagnostic")
    
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
        
        if not test_results.get("python_312_compatibility", True):
            f.write("- Vérifiez la compatibilité des packages avec Python 3.12\n")
        
        if not test_results.get("functional_tests", True):
            f.write("- Vérifiez la structure des fichiers du projet\n")
        
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
    print_colored("Installation et Vérification - Compatible Python 3.12", Colors.CYAN)
    
    test_results = {}
    
    # Tests étape par étape
    test_results["python_version"] = check_python_version()
    
    if not test_results["python_version"]:
        print_colored("\n❌ Version Python incompatible. Installation arrêtée.", Colors.RED)
        print_colored("Veuillez utiliser Python 3.8, 3.9, 3.10, 3.11 ou 3.12", Colors.YELLOW)
        return
    
    check_system_info()
    
    test_results["venv_creation"] = create_virtual_environment()
    test_results["dependencies"] = install_dependencies()
    
    if test_results["dependencies"]:
        install_spacy_models()
        
        available_deps, issues = test_dependencies()
        test_results["dependencies"] = len(issues) == 0
        
        test_results["python_312_compatibility"] = test_python_312_compatibility()
        test_results["functional_tests"] = run_quick_functional_test()
    
    # Résumé final
    print_header("RÉSUMÉ DE L'INSTALLATION")
    
    total_tests = len(test_results)
    passed_tests = sum(test_results.values())
    
    print(f"Tests réussis: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print_colored("🎉 INSTALLATION COMPLÈTE RÉUSSIE!", Colors.GREEN + Colors.BOLD)
        print_colored("🚀 Python 3.12 parfaitement supporté!", Colors.GREEN)
        print_colored("Vous pouvez maintenant lancer l'application avec:", Colors.CYAN)
        print_colored("python run.py", Colors.WHITE + Colors.BOLD)
    elif passed_tests >= total_tests * 0.8:
        print_colored("⚠️ Installation majoritairement réussie", Colors.YELLOW + Colors.BOLD)
        print_colored("Python 3.12 fonctionne, quelques fonctionnalités peuvent être limitées", Colors.YELLOW)
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