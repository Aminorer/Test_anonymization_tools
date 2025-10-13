# Guide de distribution et de déploiement

Ce guide détaille deux scénarios fréquents pour partager l'application :

1. **Alléger le dépôt pour un déploiement sur Streamlit Cloud**.
2. **Produire un exécutable Windows auto-suffisant pour une utilisation hors-ligne**.

Les recommandations ci-dessous s'appuient sur la structure existante du projet (`main.py`, `run.py`, dossier `src/` et dépendances décrites dans `requirements.txt`).

## 1. Préparer une version légère pour Streamlit Cloud

Streamlit Cloud impose une limite stricte sur la taille du dépôt (environ 1 Go compressé) et sur la durée d'installation des dépendances. Le cœur de l'application ne requiert que les éléments suivants :

- `main.py` : interface principale Streamlit avec configuration PyTorch optionnelle et interactions UI.【F:main.py†L1-L118】
- `run.py` : script de lancement qui vérifie les dépendances minimales et démarre Streamlit.【F:run.py†L1-L120】
- `src/` : modules métier (`DocumentAnonymizer`, gestion des entités, utilitaires, etc.).
- `requirements.txt` : dépendances adaptées à Streamlit Cloud.【F:requirements.txt†L1-L36】

Les ressources suivantes sont uniquement utiles pour le développement local, les tests ou la démonstration et peuvent être supprimées de la branche destinée à Streamlit Cloud :

| Ressource | Rôle | Pourquoi la retirer pour le Cloud |
|-----------|------|-----------------------------------|
| `data/benchmark/` | Corpus JSON utilisé par le script de benchmark CLI.【F:benchmark.py†L1-L15】 | Plusieurs centaines de fichiers JSON qui augmentent fortement la taille du dépôt sans être nécessaires à l'exécution en ligne. |
| `benchmark.py` | Script CLI pour évaluer l'anonymiseur sur le corpus local.【F:benchmark.py†L1-L15】 | Inexploitable sur Streamlit Cloud faute de corpus et d'accès CLI ; peut être conservé dans une branche séparée. |
| `tests/`, `test_installation.py` | Suite de tests automatisés. | Non utilisés en production ; les conserver dans une branche de développement. |
| `docs/` volumineux (captures, rapports PDF, etc.) | Documentation interne ou historique. | À conserver localement ; n'impacte pas l'app en ligne. |
| `scripts/`, `setup_and_check.py`, `check_environment.py` | Scripts d'installation avancés pour environnements locaux. | Ne sont pas lancés par Streamlit Cloud, donc inutiles sur la version déployée. |
| `requirements-full.txt`, `fix_pytorch.bat`, `fix_quick.py` | Dépendances lourdes (PyTorch/Transformers) ou scripts Windows. | Les bibliothèques IA avancées dépassent souvent les limites du Cloud ; gardez-les uniquement pour un usage local. |

> 💡 Astuce : créez une branche `streamlit-cloud` allégée qui ne contient que les fichiers nécessaires. Vous pouvez utiliser `git sparse-checkout` ou un workflow GitHub Action pour générer l'archive légère automatiquement.

## 2. Fournir un exécutable Windows autonome

Pour une utilisatrice Windows sans Python ni VS Code, vous pouvez produire un exécutable `.exe` qui embarque Python et toutes les dépendances :

1. **Préparer un environnement propre sur votre machine de développement**
   ```bash
   # Facultatif : créer un environnement virtuel
   python -m venv .venv
   .venv\\Scripts\\activate

   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. **Installer PyInstaller** (il crée des exécutables auto-suffisants)
   ```bash
   pip install pyinstaller
   ```

3. **Générer l'exécutable à partir de `run.py`**
   ```bash
   pyinstaller run.py \
     --name AnonymiseurJurique \
     --onefile \
     --noconsole \
     --hidden-import streamlit.web.cli \
     --collect-all streamlit
   ```

   - `run.py` orchestre déjà les vérifications, la création des dossiers (`temp/`, `logs/`, `exports/`) et le lancement de Streamlit.【F:run.py†L55-L120】【F:run.py†L200-L230】
   - Les options `--hidden-import` et `--collect-all` évitent les erreurs de ressources manquantes de Streamlit.
   - Le binaire généré se trouve dans `dist/AnonymiseurJurique.exe`.

4. **Préparer le dossier à livrer**
   - Copiez `dist/AnonymiseurJurique.exe` dans un dossier vierge.
   - Ajoutez un sous-dossier `app/` contenant :
     - `main.py`.
     - Le dossier `src/` complet.
     - Éventuellement un dossier `data/` minimal si vous fournissez des exemples (sinon laissez-le vide : `run.py` le crée).【F:run.py†L70-L120】
   - Créez un fichier `Lisez-moi.txt` avec les instructions :
     1. Double-cliquer sur `AnonymiseurJurique.exe`.
     2. Patienter pendant l'ouverture du navigateur sur `http://localhost:8501`.
     3. Importer un document et suivre l'interface.

5. **Tester sur une machine Windows vierge** (ou une machine virtuelle) pour vérifier que l'antivirus ne bloque pas le binaire et que les dossiers temporaires se créent correctement.

6. **Distribution**
   - Compressez le dossier (`AnonymiseurJurique.zip`).
   - Envoyez-le à l'utilisatrice ; elle n'aura qu'à extraire l'archive et lancer l'exécutable.

### Conseils supplémentaires

- Pour réduire la taille du `.exe`, désactivez les modules IA avancés en retirant `torch` et `transformers` de l'environnement avant d'exécuter PyInstaller ; l'application basculera automatiquement en mode Regex grâce au mécanisme de fallback dans `main.py`.【F:main.py†L41-L64】
- Si vous souhaitez fournir le mode IA, ajoutez `pip install -r requirements-full.txt` avant PyInstaller, mais prévenez que le binaire dépassera probablement 1 Go.
- Pensez à signer numériquement l'exécutable pour éviter les alertes SmartScreen.

## 3. Résumé rapide

- **Streamlit Cloud** : conservez seulement `main.py`, `run.py`, `src/`, `requirements.txt` et les fichiers de configuration indispensables. Supprimez les jeux de données volumineux, les tests et les scripts d'installation avancés.
- **Utilisateur Windows** : empaquetez `run.py` avec PyInstaller, distribuez le binaire accompagné des sources nécessaires (`main.py`, `src/`). Aucun prérequis n'est nécessaire côté utilisatrice.

Ces deux approches vous permettent de couvrir la majorité des cas d'usage sans obliger votre utilisatrice à installer Python ou VS Code.
