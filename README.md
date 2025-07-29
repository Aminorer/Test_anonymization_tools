# 🛡️ Anonymiseur Juridique RGPD v2.0

Application web d'anonymisation de documents juridiques français, **100% conforme RGPD** avec traitement local uniquement.

## 🆕 Nouvelles fonctionnalités v2.0

- **✏️ Modification d'entités** : Éditez le texte à anonymiser (ex: "1 Rue du Maréchal Joffre" → "1 Rue du Maréchal")
- **🔗 Groupement d'entités** : Anonymisez plusieurs variantes par le même remplacement (ex: "Monsieur OULHADJ" + "Monsieur Saïd OULHADJ" → "Monsieur X")
- **⚡ Architecture simplifiée** : Suppression des LLM pour plus de rapidité et de fiabilité
- **🧠 SpaCy NER optimisé** : Détection avancée des noms et organisations en mode approfondi

## 🎯 Fonctionnalités

- **Analyse hybride optimisée** : Patterns regex français + SpaCy NER pour une détection précise
- **8 types d'entités** : Personnes, adresses, téléphones, emails, SIRET/SIREN, etc.
- **Interface de contrôle avancée** : Modification, groupement et validation manuelle des entités
- **Format préservé** : Sortie DOCX avec mise en forme intacte
- **Conformité RGPD** : Traitement 100% local, suppression automatique des données
- **OCR intégré** : Support des PDF scannés avec Tesseract

## 🏗️ Architecture Simplifiée

### Backend (Python)
- **FastAPI** : API REST moderne et performante
- **spaCy** : Analyse NLP avec modèle français `fr_core_news_lg`
- **python-docx** : Manipulation des documents Word
- **pytesseract** : OCR pour les PDF scannés
- **Redis** : Cache de session sécurisé

### Frontend (React)
- **React 18 + TypeScript** : Interface utilisateur moderne
- **Tailwind CSS** : Design system cohérent
- **Zustand** : Gestion d'état simplifiée
- **react-dropzone** : Upload par glisser-déposer

## 🚀 Installation et Lancement

### Prérequis
- Docker et Docker Compose
- 2GB de RAM minimum (pour le modèle spaCy)

### 1. Cloner le projet
```bash
git clone <repository-url>
cd anonymizer-juridique
```

### 2. Lancement avec Docker Compose
```bash
# Construire et démarrer tous les services
docker-compose up --build

# En arrière-plan
docker-compose up -d --build
```

### 3. Accès aux services
- **Frontend** : http://localhost:9992
- **API Backend** : http://localhost:9991
- **Documentation API** : http://localhost:9991/docs
- **Redis** : localhost:9993

### 4. Arrêt des services
```bash
docker-compose down
```

### 5. Vérification de l'installation
```powershell
pwsh -File scripts/health-check.ps1   # Vérification des conteneurs
```

## 📋 Guide d'utilisation

### Étape 1 : Upload du document
1. Accéder à l'interface web : http://localhost:9992
2. Glisser-déposer un fichier PDF ou DOCX (max 50MB)
3. Choisir le mode d'analyse :
   - **Standard** : Regex seul (5-15s), optimal pour données structurées
   - **Approfondi** : Regex + SpaCy NER (15-45s), pour noms et organisations

### Étape 2 : Contrôle avancé des entités
1. **Révision** : Vérifier les entités détectées automatiquement
2. **Modification** : Cliquer sur ✏️ pour éditer le texte à anonymiser
3. **Groupement** : Activer le mode groupement et sélectionner les entités similaires
4. **Personnalisation** : Ajuster les remplacements
5. **Ajout manuel** : Ajouter des entités non détectées

### Étape 3 : Génération
1. Cliquer sur "Générer document anonymisé"
2. Le document DOCX anonymisé se télécharge automatiquement
3. Un log d'audit RGPD est généré pour traçabilité

## 🔧 Types d'entités détectées

| Type | Exemples | Mode | Icône |
|------|----------|------|-------|
| **Personnes** | Maître Dupont, M. Martin | Approfondi | 👤 |
| **Organisations** | SARL EXEMPLE, Tribunal de Paris | Approfondi | 🏢 |
| **Adresses** | 123 rue de la Paix 75001 Paris | Standard/Approfondi | 🏠 |
| **Téléphones** | 01 23 45 67 89, +33 1 23 45 67 89 | Standard/Approfondi | 📞 |
| **Emails** | contact@exemple.fr | Standard/Approfondi | 📧 |
| **Sécurité Sociale** | 1 85 12 75 123 456 78 | Standard/Approfondi | 🆔 |
| **SIRET/SIREN** | 12345678901234, RCS Paris 123456789 | Standard/Approfondi | 🏭 |
| **Références** | Dossier n°2023/123, N°RG 456789 | Standard/Approfondi | ❓ |

## 🆕 Nouvelles fonctionnalités détaillées

### ✏️ Modification d'entités
- **Cas d'usage** : "1 Rue du Maréchal Joffre" → garder seulement "1 Rue du Maréchal"
- **Interface** : Modal d'édition avec aperçu des modifications
- **Sélection** : Possibilité de sélectionner une partie du texte détecté

### 🔗 Groupement d'entités
- **Cas d'usage** : "Monsieur OULHADJ" + "Monsieur Saïd OULHADJ" → "Monsieur X"
- **Cohérence** : Garantit le même remplacement pour toutes les variantes
- **Interface** : Mode groupement avec sélection multiple

## 🛠️ Développement

### Installation locale (sans Docker)

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou venv\Scripts\activate  # Windows

pip install -r requirements.txt
python -m spacy download fr_core_news_lg

# Variables d'environnement
export REDIS_URL=redis://localhost:6379/0
export ENVIRONMENT=development

# Démarrage
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

#### Redis (requis)
```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Structure du projet
```
anonymizer-juridique/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Endpoints FastAPI
│   │   ├── services/          # Logique métier
│   │   ├── models/            # Modèles Pydantic
│   │   ├── core/              # Configuration
│   │   └── main.py           # Point d'entrée
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # Composants React
│   │   ├── pages/            # Pages principales
│   │   ├── stores/           # État Zustand
│   │   ├── services/         # API calls
│   │   └── types/            # Types TypeScript
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

## 🔒 Conformité RGPD

### Garanties techniques
- ✅ **Traitement 100% local** : Aucune donnée envoyée vers des serveurs externes
- ✅ **Chiffrement en transit** : HTTPS obligatoire en production
- ✅ **Suppression automatique** : Sessions supprimées après 30 minutes
- ✅ **Audit trail** : Log complet des modifications et groupements
- ✅ **Minimisation des données** : Seules les données nécessaires sont traitées

## 📊 Performance

### Temps de traitement moyens (v2.0)
- **Document 10 pages (Standard)** : 5-15 secondes
- **Document 10 pages (Approfondi)** : 15-30 secondes
- **Document 50 pages (Standard)** : 20-60 secondes  
- **Document 50 pages (Approfondi)** : 1-2 minutes
- **PDF scanné** : +50% (OCR requis)

### Améliorations v2.0
- **⚡ 3x plus rapide** : Suppression des LLM
- **🎯 Plus précis** : SpaCy NER optimisé pour le français juridique
- **💾 Moins de RAM** : 2GB au lieu de 4GB

## 🐛 Dépannage

### Problèmes courants

#### Erreur spaCy "Model not found"
```bash
# Dans le conteneur backend
docker-compose exec backend python -m spacy download fr_core_news_lg
```

#### Erreur Redis connexion
```bash
# Vérifier que Redis est démarré
docker-compose ps redis

# Redémarrer Redis si nécessaire
docker-compose restart redis
```

#### Frontend ne se connecte pas au backend
- Vérifier que les ports 9991 et 9992 sont libres
- Vérifier la configuration proxy dans `vite.config.ts`
- Redémarrer les services : `docker-compose restart`

### Logs de débogage
```bash
# Logs en temps réel
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 📈 Monitoring

### Métriques disponibles
- **GET /health** : Statut de santé de l'API
- **GET /api/stats** : Statistiques des sessions actives
- **Redis INFO** : Utilisation mémoire et connexions

## 🔧 Configuration avancée

### Variables d'environnement
```bash
# Backend
ENVIRONMENT=production
REDIS_URL=redis://redis:6379/0
SESSION_EXPIRE_MINUTES=30
MAX_FILE_SIZE=52428800  # 50MB

# Frontend
VITE_API_URL=http://localhost:9991
```

## 📞 Support

### Documentation
- **API** : http://localhost:9991/docs (Swagger)
- **Code source** : Commentaires détaillés dans le code

### Problèmes techniques
1. Vérifier les logs : `docker-compose logs`
2. Utiliser le script de santé : `pwsh scripts/health-check.ps1`
3. Tester avec des documents simples d'abord

## 📄 Licence

Ce projet est sous licence propriétaire. Utilisation autorisée pour des fins légitimes d'anonymisation de documents juridiques dans le respect du RGPD.

---

**Version** : 2.0.0  
**Dernière mise à jour** : 2024  
**Conformité RGPD** : ✅ Certifiée  
**Architecture** : ✅ Simplifiée sans LLM