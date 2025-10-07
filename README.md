# 🛡️ Anonymiseur de Documents Juridiques - Version Streamlit

> Interface d'anonymisation moderne et fonctionnelle avec Streamlit, gestion d'entités avancée, et conformité RGPD

## 🎯 **Vue d'ensemble**

Cette application Streamlit permet d'anonymiser automatiquement les documents juridiques (PDF et DOCX) en détectant et remplaçant les données personnelles sensibles. Contrairement à la version FastAPI précédente, cette implémentation est **fonctionnelle, testée et prête à l'emploi**.

### **✨ Fonctionnalités Principales**

- 📁 **Upload de documents** : PDF et DOCX (jusqu'à 25 MB)
- 🔍 **Double mode de détection** :
  - **Regex** : Rapide, basé sur des patterns (EMAIL, PHONE, IBAN, etc.)
  - **IA** : Intelligent avec NER pour PERSON, ORG, LOC
- 🎯 **Gestion d'entités** : Modification, groupement, validation
- 📊 **Statistiques en temps réel** : Graphiques et métriques
- 📤 **Export avancé** : DOCX et PDF avec options de filigrane, rapport d'audit et statistiques (désactivées par défaut ; PDF nécessite `fpdf`)
- 🛡️ **Conformité RGPD** : Standards CNIL respectés

## 📚 Documentation

- [Architecture](docs/architecture.md)
- [Spécification OpenAPI](docs/openapi.yaml)
- [Dockerfile](Dockerfile)
- [Script d'installation](scripts/setup.sh)
- [Guide utilisateur](docs/user_guide.md)

## 🚀 **Installation et Démarrage Rapide**

### **1. Prérequis**
```bash
Python 3.8+
4 GB RAM recommandé
2 GB d'espace disque libre
```

### **2. Installation**
```bash
# Cloner ou créer le projet
mkdir anonymizer-streamlit
cd anonymizer-streamlit

# Créer les fichiers (voir structure ci-dessous)
# Installer les dépendances minimales (compatibles Streamlit Cloud)
pip install -r requirements.txt

# Pour activer les fonctionnalités IA avancées en local
# (PyTorch, Transformers, export PDF, etc.)
pip install -r requirements-full.txt
```

### **3. Lancement**
```bash
# Démarrage simple
python run.py

# Mode développement
python run.py --dev

# Port personnalisé
python run.py --port 8080

# Vérification des dépendances uniquement
python run.py --check-only
```

### **4. Accès**
- **Interface** : http://localhost:8501
- **Auto-ouverture** du navigateur (désactivable avec `--no-browser`)

## 📁 **Structure du Projet**

```
anonymizer-streamlit/
├── main.py                 # Application Streamlit principale
├── run.py                  # Script de lancement avec vérifications
├── requirements.txt        # Dépendances Python
├── README.md              # Cette documentation
├── src/
│   ├── __init__.py
│   ├── anonymizer.py      # Modules d'anonymisation
│   ├── entity_manager.py  # Gestion des entités et groupes
│   ├── variant_manager_ui.py  # Interface de gestion des variantes
│   ├── config.py          # Configuration et constantes
│   └── utils.py           # Fonctions utilitaires
├── temp/                  # Fichiers temporaires
├── logs/                  # Logs de l'application
├── exports/               # Documents exportés
└── data/                  # Données persistantes
```

## 🔧 **Guide d'Utilisation**

### **1. Upload de Document**
- Glissez-déposez ou sélectionnez un fichier PDF/DOCX
- Vérification automatique de la taille et du format
- Prévisualisation des informations du fichier

### **2. Configuration du Traitement**
- **Mode Regex** : Détection rapide (10-30 secondes)
  - Types : EMAIL, PHONE, DATE, ADDRESS, IBAN, SIREN, SIRET, LOC
- **Mode IA** : Détection intelligente (1-3 minutes)
  - Types supplémentaires : PERSON, ORG
  - Seuil de confiance réglable (0.1 à 1.0)

### **3. Analyse des Résultats**
- **Statistiques** : Nombre total, types détectés, confiance
- **Graphiques** : Répartition par types avec couleurs
- **Badges colorés** : Visualisation rapide des types

### **4. Gestion des Entités**

#### **Onglet Entités**
- Liste filtrable par type
- Modification des remplacements personnalisés
- Suppression individuelle ou en lot
- Affichage de la confiance (mode IA)

#### **Onglet Groupes**
- Création de groupes thématiques
- Assignation d'entités par drag & drop
- Gestion collaborative des données

#### **Onglet Recherche**
- Recherche textuelle dans le document
- Surlignage des occurrences trouvées
- Navigation par extraits

### **5. Export Final**
- **Options** : Filigrane personnalisable, rapport d'audit et statistiques détaillées (désactivés par défaut)
- **Format** : DOCX ou PDF (l'export PDF nécessite le package `fpdf`)
- **Téléchargement** : Direct depuis l'interface

### **6. Rapport d'audit optionnel**
Les méthodes `process_document` et `export_anonymized_document` acceptent un paramètre `audit`.
Lorsqu'il est activé (`audit=True`), un rapport détaillant les métadonnées et les statistiques
d'anonymisation est ajouté ou généré séparément.

```python
from src.anonymizer import DocumentAnonymizer

anonymizer = DocumentAnonymizer()

# Traitement avec rapport d'audit
result = anonymizer.process_document("contrat.pdf", audit=True)

# Export en incluant le rapport
export_paths = anonymizer.export_anonymized_document(
    "contrat.txt", options={"format": "txt"}, audit=True
)
print("Chemin temporaire:", export_paths["temp_path"])
print("Chemin final:", export_paths["output_path"])
```

> 💡 Pour enregistrer une copie dans un dossier spécifique sans modifier le
> fichier source, utilisez l'option `options={"format": "txt", "output_path": "/chemin/personnalise"}`.

## ⚙️ **Configuration Avancée**

### **Variables d'Environnement**
```bash
# Configuration IA
export NER_MODEL="dbmdz/bert-large-cased-finetuned-conll03-english"
export NER_CONFIDENCE="0.7"
export NER_DEVICE="cpu"  # ou "cuda" si GPU disponible

# Configuration application
export MAX_FILE_SIZE="26214400"  # 25 MB
export TEMP_RETENTION="3600"     # 1 heure
# Normalisation des noms
export ANONYMIZER_TITLES="mr,mme,dr,me,maître"  # titres supprimés par défaut
export ANONYMIZER_SIMILARITY_THRESHOLD="0.85"     # seuil de similarité pour le regroupement
export ANONYMIZER_SIMILARITY_WEIGHTS="levenshtein=0.5,jaccard=0.3,phonetic=0.2"  # poids des composantes de similarité
```

Les mêmes paramètres peuvent être fournis directement au constructeur de
`RegexAnonymizer` :

```python
from src.anonymizer import RegexAnonymizer

anonymizer = RegexAnonymizer(
    titles=["sir", "madame"],
    score_cutoff=0.9,
)
```

Par défaut, les titres supprimés sont `mr`, `mme`, `dr`, `me`, `maître` et le
seuil de similarité est `0.85`. Les poids de similarité par défaut sont `0.5`
pour Levenshtein, `0.3` pour Jaccard et `0.2` pour la phonétique.

### **Algorithme de similarité**

L'application utilise `rapidfuzz` par défaut pour le calcul de la similarité des noms. Ce paquet est optionnel mais requis pour l'algorithme par défaut :

```bash
pip install rapidfuzz
```

Si `rapidfuzz` n'est pas disponible, installez `python-Levenshtein` et sélectionnez l'algorithme `"levenshtein"` dans les fonctions concernées :

```bash
pip install python-Levenshtein
```


```python
from src.anonymizer import RegexAnonymizer

anonymizer = RegexAnonymizer(algorithm="levenshtein")
# ou utilitaire
# similarity("Alice", "Alicia", algorithm="levenshtein")
```

Dans ce mode, le calcul de similarité repose sur l'algorithme Levenshtein.

## 📈 Tableau de bord juridique

L'interface Streamlit expose un tableau de bord juridique affichant les
entités détectées, les recommandations et les métriques de performance. Lancez
l'application avec `python run.py` puis consultez le tableau de bord dans votre
navigateur à l'adresse indiquée. Les métriques d’anonymisation peuvent être
visualisées via `perf_dashboard.py`.

## 🛠️ Configuration des templates

Les modèles spécifiques au domaine sont définis dans
`src/config.py` via la classe `LegalTemplates`. Chaque entrée précise les
entités à anonymiser, celles à conserver et une liste de mots-clés pour la
detection automatique. Ajoutez vos propres templates en étendant ce registre.

## 🤖 Intégration Ollama

`OllamaLegalAnalyzer` peut se connecter à un serveur Ollama local pour améliorer
la classification des documents et la vérification de cohérence. Installez le
serveur selon la documentation officielle puis lancez-le :

```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve
```

Vous pouvez spécifier l'URL et le modèle Ollama lors de la création de
`EnhancedDocumentAnonymizer`.

### **Personnalisation des Entités**
Modifiez `src/config.py` pour :
- Ajouter des patterns regex personnalisés
- Modifier les couleurs des types d'entités
- Personnaliser les remplacements par défaut
- Créer des préréglages métier
 
## 🧪 Benchmark

Un corpus d'exemples annotés est disponible dans `data/benchmark`. Pour
évaluer automatiquement la qualité de l'anonymiseur sur ce corpus,
exécutez :

```bash
python benchmark.py --dataset data/benchmark --output rapport.csv
```

Le script génère un fichier CSV contenant précision, rappel et F1 pour
chaque type d'entité détecté.

