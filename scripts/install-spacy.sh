#!/bin/bash
# scripts/install-spacy.sh

echo "🔧 Installation SpaCy pour mode approfondi..."

# Installation dans le conteneur backend
docker-compose exec backend pip install spacy

# Téléchargement des modèles français (du plus précis au plus léger)
echo "📥 Téléchargement modèles SpaCy français..."

# Essayer d'installer le meilleur modèle en premier
docker-compose exec backend python -m spacy download fr_core_news_lg || \
docker-compose exec backend python -m spacy download fr_core_news_md || \
docker-compose exec backend python -m spacy download fr_core_news_sm

# Vérification
echo "✅ Vérification installation..."
docker-compose exec backend python -c "import spacy; print('SpaCy:', spacy.__version__)"

# Test des modèles disponibles
echo "📋 Modèles français disponibles:"
docker-compose exec backend python -c "
import spacy
models = ['fr_core_news_lg', 'fr_core_news_md', 'fr_core_news_sm']
for model in models:
    try:
        nlp = spacy.load(model)
        print(f'✅ {model} - {len(nlp.vocab)} vocabulaire')
    except:
        print(f'❌ {model} - non installé')
"

echo "🎉 Installation SpaCy terminée!"
echo "🔄 Redémarrez le backend: docker-compose restart backend"