# scripts/fix-spacy.ps1 - Installation et configuration SpaCy

Write-Host "🧠 Installation et configuration SpaCy pour le mode approfondi" -ForegroundColor Green
Write-Host "================================================================"

function Install-SpacyModel {
    Write-Host "📥 Installation du modèle SpaCy français..." -ForegroundColor Cyan
    
    try {
        # Vérifier que le conteneur backend est démarré
        $backendStatus = docker-compose ps backend 2>$null
        if (-not ($backendStatus -match "Up")) {
            Write-Host "❌ Le conteneur backend n'est pas démarré" -ForegroundColor Red
            Write-Host "💡 Lancez d'abord : docker-compose up -d" -ForegroundColor Yellow
            return $false
        }
        
        Write-Host "🔄 Installation de SpaCy dans le conteneur..." -ForegroundColor Yellow
        docker-compose exec backend pip install spacy>=3.7.2
        
        Write-Host "📦 Téléchargement du modèle français (cela peut prendre 2-3 minutes)..." -ForegroundColor Yellow
        
        # Essayer d'installer les modèles par ordre de préférence
        $models = @("fr_core_news_lg", "fr_core_news_md", "fr_core_news_sm")
        $installed = $false
        
        foreach ($model in $models) {
            Write-Host "   Tentative d'installation : $model" -ForegroundColor Gray
            $result = docker-compose exec backend python -m spacy download $model 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Modèle $model installé avec succès" -ForegroundColor Green
                $installed = $true
                break
            } else {
                Write-Host "   ⚠️ $model non disponible, tentative suivante..." -ForegroundColor Yellow
            }
        }
        
        if (-not $installed) {
            Write-Host "❌ Impossible d'installer un modèle SpaCy" -ForegroundColor Red
            return $false
        }
        
        return $true
    }
    catch {
        Write-Host "❌ Erreur lors de l'installation SpaCy: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-SpacyInstallation {
    Write-Host "🧪 Test de l'installation SpaCy..." -ForegroundColor Cyan
    
    try {
        $testResult = docker-compose exec backend python -c "
import spacy
models = ['fr_core_news_lg', 'fr_core_news_md', 'fr_core_news_sm']
for model in models:
    try:
        nlp = spacy.load(model)
        print(f'✅ {model} - OK ({len(nlp.vocab)} mots)')
        break
    except:
        print(f'❌ {model} - Non disponible')
        continue
else:
    print('❌ Aucun modèle français disponible')
" 2>$null

        if ($LASTEXITCODE -eq 0) {
            Write-Host $testResult
            return $true
        } else {
            Write-Host "❌ Test SpaCy échoué" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Erreur test SpaCy: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Restart-Backend {
    Write-Host "🔄 Redémarrage du backend pour prendre en compte SpaCy..." -ForegroundColor Cyan
    
    try {
        docker-compose restart backend
        Start-Sleep -Seconds 5
        Write-Host "✅ Backend redémarré" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Erreur redémarrage backend" -ForegroundColor Red
        return $false
    }
}

function Main {
    Write-Host "🚀 Démarrage de la configuration SpaCy..." -ForegroundColor Cyan
    
    # 1. Installer SpaCy et modèles
    if (-not (Install-SpacyModel)) {
        Write-Host "❌ Installation SpaCy échouée" -ForegroundColor Red
        return
    }
    
    # 2. Tester l'installation
    if (-not (Test-SpacyInstallation)) {
        Write-Host "❌ Test SpaCy échoué" -ForegroundColor Red
        return
    }
    
    # 3. Redémarrer le backend
    if (-not (Restart-Backend)) {
        Write-Host "❌ Redémarrage échoué" -ForegroundColor Red
        return
    }
    
    Write-Host ""
    Write-Host "🎉 SpaCy configuré avec succès !" -ForegroundColor Green
    Write-Host "✅ Mode Standard : Regex uniquement (5-15s)" -ForegroundColor Green
    Write-Host "✅ Mode Approfondi : Regex + SpaCy NER (15-45s)" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔧 Prochaines étapes :" -ForegroundColor Cyan
    Write-Host "   1. Testez l'upload d'un document" -ForegroundColor White
    Write-Host "   2. Vérifiez que le mode approfondi fonctionne" -ForegroundColor White
    Write-Host "   3. Testez les nouvelles fonctionnalités (modification/groupement)" -ForegroundColor White
}

Main