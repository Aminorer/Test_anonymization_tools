# scripts/init-ollama.ps1 - Version PowerShell pour Windows

Write-Host "🚀 Initialisation d'Ollama pour l'anonymisation juridique..." -ForegroundColor Green
Write-Host "=================================================="

# Configuration
$OLLAMA_HOST = "localhost:11434"
$SELECTED_MODEL = "mistral:7b-instruct"

# Fonction d'attente
function Wait-ForOllama {
    Write-Host "⏳ Attente du démarrage d'Ollama..." -ForegroundColor Yellow
    $timeout = 300  # 5 minutes
    $count = 0
    
    do {
        try {
            $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get -TimeoutSec 5
            Write-Host "✅ Ollama est opérationnel" -ForegroundColor Green
            return $true
        }
        catch {
            if ($count -ge $timeout) {
                Write-Host "❌ Timeout : Ollama n'est pas démarré après 5 minutes" -ForegroundColor Red
                Write-Host "🔧 Vérifiez : docker-compose logs ollama" -ForegroundColor Yellow
                return $false
            }
            Start-Sleep -Seconds 2
            $count += 2
            Write-Host "." -NoNewline
        }
    } while ($count -lt $timeout)
}

# Fonction de téléchargement
function Download-Model {
    param($model)
    
    Write-Host "📥 Téléchargement du modèle $model..." -ForegroundColor Yellow
    
    # Vérifier si le modèle existe déjà
    try {
        $tags = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get
        if ($tags.models | Where-Object { $_.name -eq $model }) {
            Write-Host "✅ Modèle $model déjà présent" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "❌ Erreur lors de la vérification des modèles" -ForegroundColor Red
        return $false
    }
    
    # Télécharger le modèle
    Write-Host "⬇️  Téléchargement en cours (cela peut prendre plusieurs minutes)..." -ForegroundColor Yellow
    
    try {
        $body = @{
            name = $model
            stream = $false
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/pull" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 1800
        Write-Host "✅ Modèle $model téléchargé avec succès" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Erreur lors du téléchargement de $model" -ForegroundColor Red
        Write-Host "Erreur: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Fonction de test
function Test-Model {
    param($model)
    
    Write-Host "🧪 Test du modèle $model..." -ForegroundColor Yellow
    
    try {
        $body = @{
            model = $model
            prompt = "Identifie les entités dans ce texte juridique français : 'Maître Jean Dupont, avocat au barreau de Paris, domicilié 123 rue de la Paix 75001 Paris.' Réponds uniquement en JSON avec les champs: text, type, confidence."
            stream = $false
            options = @{
                temperature = 0.1
                max_tokens = 500
            }
        } | ConvertTo-Json -Depth 3
        
        $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
        
        if ($response.response) {
            Write-Host "✅ Test réussi pour $model" -ForegroundColor Green
            Write-Host "📋 Exemple de réponse :" -ForegroundColor Cyan
            Write-Host $response.response.Substring(0, [Math]::Min(200, $response.response.Length))
            return $true
        }
    }
    catch {
        Write-Host "❌ Test échoué pour $model" -ForegroundColor Red
        Write-Host "Erreur: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Fonction principale
function Main {
    Write-Host "🔍 Vérification de l'environnement..." -ForegroundColor Cyan
    
    # Vérifier Docker Compose
    try {
        $composeStatus = docker-compose ps 2>$null
        if ($composeStatus -match "ollama.*Up") {
            Write-Host "✅ Service ollama détecté" -ForegroundColor Green
        } else {
            Write-Host "❌ Le service ollama n'est pas démarré" -ForegroundColor Red
            Write-Host "💡 Lancez d'abord : docker-compose up -d" -ForegroundColor Yellow
            return
        }
    }
    catch {
        Write-Host "❌ Erreur avec Docker Compose" -ForegroundColor Red
        return
    }
    
    # Attendre Ollama
    if (-not (Wait-ForOllama)) {
        return
    }
    
    # Télécharger le modèle
    Write-Host "📦 Installation du modèle principal..." -ForegroundColor Cyan
    if (Download-Model $SELECTED_MODEL) {
        Write-Host "✅ Modèle principal installé" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Tentative avec modèle de fallback..." -ForegroundColor Yellow
        $SELECTED_MODEL = "llama3.1:8b"
        if (-not (Download-Model $SELECTED_MODEL)) {
            Write-Host "❌ Impossible d'installer un modèle" -ForegroundColor Red
            return
        }
    }
    
    # Tester le modèle
    if (Test-Model $SELECTED_MODEL) {
        Write-Host "🎉 Configuration réussie !" -ForegroundColor Green
    } else {
        Write-Host "❌ Problème avec le modèle $SELECTED_MODEL" -ForegroundColor Red
        return
    }
    
    # Statut final
    Write-Host ""
    Write-Host "📊 Résumé de l'installation :" -ForegroundColor Cyan
    Write-Host "================================"
    Write-Host "🤖 Modèle actif : $SELECTED_MODEL" -ForegroundColor White
    Write-Host "🌐 URL Ollama : http://$OLLAMA_HOST" -ForegroundColor White
    Write-Host ""
    Write-Host "🚀 Ollama est prêt pour l'anonymisation juridique !" -ForegroundColor Green
}

# Lancer le script
Main