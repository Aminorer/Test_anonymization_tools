# Guide de distribution et de déploiement

Ce guide détaille deux scénarios fréquents pour partager l'application :

1. **Alléger le dépôt pour un déploiement sur Streamlit Cloud**.
2. **Fournir un dossier Windows prêt à l'emploi via un script `.bat`.**

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
| `requirements-full.txt`, `fix_quick.py` | Dépendances lourdes (PyTorch/Transformers) ou scripts ponctuels. | Les bibliothèques IA avancées dépassent souvent les limites du Cloud ; gardez-les uniquement pour un usage local. |

> 💡 Astuce : créez une branche `streamlit-cloud` allégée qui ne contient que les fichiers nécessaires. Vous pouvez utiliser `git sparse-checkout` ou un workflow GitHub Action pour générer l'archive légère automatiquement.

## 2. Fournir un dossier Windows prêt à l'emploi

L'approche recommandée pour un public non technique est de livrer l'application accompagnée d'un script d'installation automatique (`install_and_run.bat`). Ce script :

- vérifie la présence de Python et le télécharge au besoin ;
- crée un environnement virtuel local (`venv/`) ;
- installe les dépendances via `requirements.txt` ;
- crée les dossiers de travail (`temp/`, `logs/`, `exports/`, `data/`);
- installe un raccourci `Anonymiseur.lnk` sur le bureau ;
- démarre automatiquement Streamlit.

### Étapes côté développeur

1. Générer l'archive de distribution (`anonymiseur.zip`) contenant :
   - `install_and_run.bat` et `run_app.bat` ;
   - `README_UTILISATEUR.txt` ;
   - `main.py`, `run.py`, `requirements.txt`, le dossier `src/` et les éventuelles ressources nécessaires (`data/`, `exports/` vides, etc.).
2. Tester le script sur une machine Windows (ou VM) pour vérifier l'installation automatique.
3. Envoyer l'archive aux utilisatrices avec un rappel : première ouverture via `install_and_run.bat`, lancements suivants via le raccourci bureau ou `run_app.bat`.

### Bonnes pratiques

- Préparer l'archive depuis un environnement propre pour éviter les fichiers temporaires inutiles.
- Conserver `requirements-full.txt` à part pour les utilisations avancées (IA) et ne pas l'inclure si la cible ne dispose pas d'une connexion rapide.
- Mettre à jour le champ de contact dans `README_UTILISATEUR.txt` avant l'envoi.

## 3. Résumé rapide

- **Streamlit Cloud** : conservez seulement `main.py`, `run.py`, `src/`, `requirements.txt` et les fichiers de configuration indispensables. Supprimez les jeux de données volumineux, les tests et les scripts d'installation avancés.
- **Utilisateur Windows** : distribuez l'archive contenant les scripts `.bat`. L'installation est automatique et ne nécessite aucune compilation PyInstaller.

Ces deux approches couvrent la majorité des cas d'usage sans obliger votre utilisatrice à manipuler PyInstaller ou des outils de packaging complexes.
