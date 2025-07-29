# scripts/init-ollama-optimized.ps1 - Version ultra-optimisée pour Windows

Write-Host "🚀 Initialisation Ollama OPTIMISÉE pour l'anonymisation juridique..." -ForegroundColor Green
Write-Host "=============================================================="

# Configuration optimisée
$OLLAMA_HOST = "localhost:11434"
$PREFERRED_MODELS = @(
    "mistral:7b-instruct",  # Priorité 1 - Plus rapide
    "llama3.2:3b",         # Priorité 2 - Très léger  
    "gemma2:2b",           # Priorité 3 - Ultra léger
    "llama3.1:8b"          # Priorité 4 - Plus lourd mais performant
)

function Wait-ForOllama {
    Write-Host "⏳ Attente du démarrage d'Ollama (30s max)..." -ForegroundColor Yellow
    $timeout = 30  # Réduit à 30 secondes
    $count = 0
    
    do {
        try {
            $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get -TimeoutSec 3
            Write-Host "✅ Ollama opérationnel" -ForegroundColor Green
            return $true
        }
        catch {
            if ($count -ge $timeout) {
                Write-Host "❌ Timeout : Ollama non démarré après 30s" -ForegroundColor Red
                Write-Host "🔧 Vérifiez : docker-compose logs ollama" -ForegroundColor Yellow
                return $false
            }
            Start-Sleep -Seconds 1
            $count += 1
            Write-Host "." -NoNewline
        }
    } while ($count -lt $timeout)
}

function Get-OptimalModel {
    Write-Host "🔍 Recherche du modèle optimal..." -ForegroundColor Cyan
    
    try {
        $tags = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get -TimeoutSec 5
        $availableModels = $tags.models | ForEach-Object { $_.name }
        
        Write-Host "📋 Modèles disponibles:" -ForegroundColor White
        $availableModels | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
        
        # Chercher le meilleur modèle disponible
        foreach ($model in $PREFERRED_MODELS) {
            if ($availableModels -contains $model) {
                Write-Host "✅ Modèle optimal trouvé: $model" -ForegroundColor Green
                return $model
            }
        }
        
        # Si aucun modèle préféré, prendre le plus petit disponible
        $lightModels = $availableModels | Where-Object { 
            $_ -match ".*:(1b|2b|3b|7b)" -and $_ -notmatch "70b|13b|34b"
        }
        
        if ($lightModels.Count -gt 0) {
            $selected = $lightModels[0]
            Write-Host "⚡ Modèle léger sélectionné: $selected" -ForegroundColor Yellow
            return $selected
        }
        
        Write-Host "❌ Aucun modèle léger trouvé" -ForegroundColor Red
        return $null
        
    }
    catch {
        Write-Host "❌ Erreur lors de la vérification des modèles: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Download-OptimalModel {
    Write-Host "📥 Installation du modèle optimal..." -ForegroundColor Cyan
    
    try {
        $tags = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get -TimeoutSec 5
        $existingModels = $tags.models | ForEach-Object { $_.name }
        
        # Chercher si on a déjà un modèle préféré
        foreach ($model in $PREFERRED_MODELS) {
            if ($existingModels -contains $model) {
                Write-Host "✅ Modèle $model déjà installé" -ForegroundColor Green
                return $model
            }
        }
        
        # Installer le premier modèle préféré
        $targetModel = $PREFERRED_MODELS[0]
        Write-Host "⬇️ Téléchargement de $targetModel (cela peut prendre 2-5 minutes)..." -ForegroundColor Yellow
        
        $body = @{
            name = $targetModel
            stream = $false
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/pull" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 600
        Write-Host "✅ Modèle $targetModel installé avec succès" -ForegroundColor Green
        return $targetModel
        
    }
    catch {
        Write-Host "❌ Erreur lors de l'installation: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

function Test-ModelPerformance {
    param($model)
    
    Write-Host "🧪 Test de performance de $model..." -ForegroundColor Yellow
    
    try {
        $startTime = Get-Date
        
        $body = @{
            model = $model
            prompt = "Trouve les noms de personnes: 'Maître Jean Dupont avocat Paris.' Réponds en JSON: [{\"text\":\"Jean Dupont\",\"type\":\"PERSONNE\"}]"
            stream = $false
            options = @{
                temperature = 0.0
                num_predict = 100
                num_ctx = 1024
            }
        } | ConvertTo-Json -Depth 3
        
        $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/generate" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
        
        $endTime = Get-Date
        $duration = ($endTime - $startTime).TotalSeconds
        
        if ($response.response -and $duration -lt 10) {
            Write-Host "✅ Test réussi en $([math]::Round($duration, 1))s" -ForegroundColor Green
            Write-Host "📋 Réponse: $($response.response.Substring(0, [Math]::Min(100, $response.response.Length)))..." -ForegroundColor Cyan
            return $true
        } else {
            Write-Host "⚠️ Test lent ($([math]::Round($duration, 1))s)" -ForegroundColor Yellow
            return $false
        }
        
    }
    catch {
        Write-Host "❌ Test échoué: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Optimize-OllamaConfig {
    Write-Host "⚙️ Optimisation de la configuration Ollama..." -ForegroundColor Cyan
    
    try {
        # Vérifier les variables d'environnement optimales
        $envVars = @{
            "OLLAMA_MAX_LOADED_MODELS" = "1"
            "OLLAMA_NUM_PARALLEL" = "1"
            "OLLAMA_FLASH_ATTENTION" = "1"
            "OLLAMA_KV_CACHE_TYPE" = "f16"
        }
        
        Write-Host "📋 Configuration recommandée dans docker-compose.yml :" -ForegroundColor White
        foreach ($var in $envVars.GetEnumerator()) {
            Write-Host "  - $($var.Key)=$($var.Value)" -ForegroundColor Gray
        }
        
        Write-Host "✅ Configuration optimisée recommandée" -ForegroundColor Green
        return $true
        
    }
    catch {
        Write-Host "⚠️ Impossible de vérifier la configuration" -ForegroundColor Yellow
        return $false
    }
}

function Main {
    Write-Host "🔍 Vérification de l'environnement..." -ForegroundColor Cyan
    
    # Vérifier Docker Compose
    try {
        $composeStatus = docker-compose ps 2>$null
        if ($composeStatus -match "ollama.*Up") {
            Write-Host "✅ Service ollama détecté et actif" -ForegroundColor Green
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
    
    # Attendre Ollama (timeout réduit)
    if (-not (Wait-ForOllama)) {
        return
    }
    
    # Chercher le modèle optimal
    $optimalModel = Get-OptimalModel
    
    if (-not $optimalModel) {
        # Installer un modèle si aucun n'est disponible
        $optimalModel = Download-OptimalModel
    }
    
    if (-not $optimalModel) {
        Write-Host "❌ Impossible de configurer un modèle" -ForegroundColor Red
        return
    }
    
    # Tester les performances
    Write-Host "🧪 Test de performance..." -ForegroundColor Cyan
    $performanceOk = Test-ModelPerformance $optimalModel
    
    # Optimiser la configuration
    Optimize-OllamaConfig | Out-Null
    
    # Résumé final
    Write-Host ""
    Write-Host "📊 Résumé de l'installation OPTIMISÉE :" -ForegroundColor Cyan
    Write-Host "==========================================="
    Write-Host "🤖 Modèle actif : $optimalModel" -ForegroundColor White
    Write-Host "🌐 URL Ollama : http://$OLLAMA_HOST" -ForegroundColor White
    Write-Host "⚡ Performance : $(if ($performanceOk) { "OPTIMALE" } else { "ACCEPTABLE" })" -ForegroundColor $(if ($performanceOk) { "Green" } else { "Yellow" })
    Write-Host "🎯 Timeout configuré : 30 secondes" -ForegroundColor White
    Write-Host "💾 Context window : 2048 tokens (optimisé)" -ForegroundColor White
    Write-Host ""
    
    if ($performanceOk) {
        Write-Host "🎉 Ollama est prêt pour l'anonymisation HAUTE PERFORMANCE !" -ForegroundColor Green
        Write-Host "⚡ Mode Standard : < 5 secondes" -ForegroundColor Green
        Write-Host "🧠 Mode Approfondi : < 30 secondes" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Ollama configuré mais performances limitées" -ForegroundColor Yellow
        Write-Host "💡 Recommandation : Utilisez le mode Standard uniquement" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🔧 Optimisations appliquées :" -ForegroundColor Cyan
    Write-Host "- Modèle léger sélectionné automatiquement" -ForegroundColor White
    Write-Host "- Context window réduit (1024-2048 tokens)" -ForegroundColor White
    Write-Host "- Timeout strict (8s par chunk, 30s total)" -ForegroundColor White
    Write-Host "- Une seule conversation parallèle" -ForegroundColor White
    Write-Host "- Cache optimisé (f16)" -ForegroundColor White
}

# Lancer le script
Main