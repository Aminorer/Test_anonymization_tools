# 🛡️ Anonymiseur Juridique RGPD

Application web d'anonymisation de documents juridiques français, **100% conforme RGPD** avec traitement local uniquement.

## 🎯 Fonctionnalités

- **Analyse IA hybride** : Patterns regex français + spaCy pour une détection précise
- **8 types d'entités** : Personnes, adresses, téléphones, emails, SIRET/SIREN, etc.
- **Interface de contrôle** : Validation manuelle et personnalisation des remplacements  
- **Format préservé** : Sortie DOCX avec mise en forme intacte
- **Conformité RGPD** : Traitement 100% local, suppression automatique des données
- **OCR intégré** : Support des PDF scannés avec Tesseract

## 🏗️ Architecture

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
- 4GB de RAM minimum (pour le modèle spaCy)

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
- **Frontend** : http://localhost:3000
- **API Backend** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **Redis** : localhost:6379

### 4. Arrêt des services
```bash
docker-compose down
```

### 5. Vérification de l'installation (Windows)
Des scripts PowerShell sont fournis pour initialiser les modèles et vérifier les services :
```powershell
pwsh -File scripts/init-ollama.ps1    # Téléchargement du modèle Ollama
pwsh -File scripts/health-check.ps1   # Vérification des conteneurs
```

## 📋 Guide d'utilisation

### Étape 1 : Upload du document
1. Accéder à l'interface web : http://localhost:3000
2. Glisser-déposer un fichier PDF ou DOCX (max 50MB)
3. Choisir le mode d'analyse :
   - **Standard** : Rapide (5-30s), optimal pour la plupart des cas
   - **Approfondi** : Précis (30s-2min), pour documents complexes

### Étape 2 : Contrôle des entités
1. Réviser les entités détectées automatiquement
2. Cocher/décocher les entités à anonymiser
3. Personnaliser les remplacements si nécessaire
4. Ajouter des entités manuelles si besoin

### Étape 3 : Génération
1. Cliquer sur "Générer document anonymisé"
2. Le document DOCX anonymisé se télécharge automatiquement
3. Un log d'audit RGPD est généré pour traçabilité

## 🔧 Types d'entités détectées

| Type | Exemples | Icône |
|------|----------|-------|
| **Personnes** | Maître Dupont, M. Martin | 👤 |
| **Adresses** | 123 rue de la Paix 75001 Paris | 🏠 |
| **Téléphones** | 01 23 45 67 89, +33 1 23 45 67 89 | 📞 |
| **Emails** | contact@exemple.fr | 📧 |
| **Sécurité Sociale** | 1 85 12 75 123 456 78 | 🆔 |
| **SIRET/SIREN** | 12345678901234, RCS Paris 123456789 | 🏭 |
| **Organisations** | SARL EXEMPLE, Tribunal de Paris | 🏢 |
| **Références** | Dossier n°2023/123, N°RG 456789 | ❓ |

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

# Ou installation locale selon votre OS
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
- ✅ **Audit trail** : Log complet des modifications
- ✅ **Minimisation des données** : Seules les données nécessaires sont traitées

### Configuration RGPD
```python
RGPD_CONFIG = {
    "data_processing": "local_only",
    "external_apis": False,
    "data_retention": 0,  # Suppression immédiate
    "audit_logging": True,
    "user_consent": "explicit"
}
```

## 📊 Performance

### Temps de traitement moyens
- **Document 10 pages** : 10-30 secondes (mode standard)
- **Document 50 pages** : 1-3 minutes (mode approfondi)
- **PDF scanné** : +50% (OCR requis)

### Ressources système recommandées
- **RAM** : 4GB minimum, 8GB recommandé
- **CPU** : 2 cœurs minimum
- **Stockage** : 2GB pour les modèles IA
- **Réseau** : Local uniquement (pas d'accès Internet requis)

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

#### Erreur OCR Tesseract
```bash
# Vérifier l'installation Tesseract
docker-compose exec backend tesseract --version

# Le Dockerfile installe automatiquement tesseract-ocr-fra
```

#### Frontend ne se connecte pas au backend
- Vérifier que les ports 3000 et 8000 sont libres
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

## 🧪 Tests

### Tests backend
```bash
# depuis la racine du projet
pip install -r backend/requirements.txt
python -m pytest backend/tests -v
```

### Tests frontend
```bash
cd frontend
npm run test
```

### Test de charge
```bash
# Installer Artillery
npm install -g artillery

# Test de charge
artillery quick --count 10 --num 5 http://localhost:8000/health
```

## 📈 Monitoring

### Métriques disponibles
- **GET /health** : Statut de santé de l'API
- **GET /api/stats** : Statistiques des sessions actives
- **Redis INFO** : Utilisation mémoire et connexions

### Surveillance recommandée
- Utilisation mémoire (modèles spaCy volumineux)
- Espace disque temporaire (fichiers uploadés)
- Connexions Redis (sessions actives)

## 🔧 Configuration avancée

### Variables d'environnement
```bash
# Backend
ENVIRONMENT=production
REDIS_URL=redis://redis:6379/0
SESSION_EXPIRE_MINUTES=30
MAX_FILE_SIZE=52428800  # 50MB

# Frontend
VITE_API_URL=http://localhost:8000
```

### Personnalisation des entités
Modifier `backend/app/models/entities.py` pour ajouter de nouveaux types d'entités ou patterns regex.

### Déploiement production
1. Utiliser un proxy inverse (Nginx)
2. Configurer HTTPS/TLS
3. Augmenter les limites de ressources
4. Configurer la sauvegarde Redis
5. Mettre en place la surveillance

## 📞 Support

### Documentation
- **API** : http://localhost:8000/docs (Swagger)
- **Code source** : Commentaires détaillés dans le code
- **Architecture** : Diagrammes dans `/docs/`

### Problèmes techniques
1. Vérifier les logs : `docker-compose logs`
2. Consulter la documentation API
3. Tester avec des documents simples d'abord

## 📄 Licence

Ce projet est sous licence propriétaire. Utilisation autorisée pour des fins légitimes d'anonymisation de documents juridiques dans le respect du RGPD.

---

**Version** : 1.0.0  
**Dernière mise à jour** : 2024  
**Conformité RGPD** : ✅ Certifiée