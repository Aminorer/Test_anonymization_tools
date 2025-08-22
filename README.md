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
- 📤 **Export avancé** : DOCX avec filigrane et rapport d'audit
- 🛡️ **Conformité RGPD** : Standards CNIL respectés

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
# Installer les dépendances
pip install -r requirements.txt
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
- **Options** : Filigrane personnalisable, rapport d'audit
- **Format** : DOCX préservant la structure originale
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
export_path = anonymizer.export_anonymized_document(
    "contrat.txt", options={"format": "txt"}, audit=True
)
```

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
```

### **Personnalisation des Entités**
Modifiez `src/config.py` pour :
- Ajouter des patterns regex personnalisés
- Modifier les couleurs des types d'entités
- Personnaliser les remplacements par défaut
- Créer des préréglages métier

### **