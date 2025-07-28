# scripts/init-ollama.ps1 - Initialisation Ollama pour Windows

Write-Host "🚀 Initialisation d'Ollama pour l'anonymisation juridique..." -ForegroundColor Green

# Configuration
$OLLAMA_HOST = "localhost:11434"
$SELECTED_MODEL = "mistral:7b-instruct"

# Test de connexion
Write-Host "🔍 Test de connexion à Ollama..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/tags" -Method Get -TimeoutSec 10
    Write-Host "✅ Ollama est accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama non accessible. Vérifiez que docker-compose est lancé" -ForegroundColor Red
    exit 1
}

# Vérifier si le modèle existe
Write-Host "🔍 Vérification du modèle $SELECTED_MODEL..." -ForegroundColor Yellow
$models = $response.models
$modelExists = $models | Where-Object { $_.name -eq $SELECTED_MODEL }

if ($modelExists) {
    Write-Host "✅ Modèle $SELECTED_MODEL déjà installé" -ForegroundColor Green
} else {
    Write-Host "📥 Téléchargement du modèle $SELECTED_MODEL (4GB - patience...)..." -ForegroundColor Yellow
    try {
        $body = @{
            name = $SELECTED_MODEL
            stream = $false
        } | ConvertTo-Json
        
        $downloadResponse = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/pull" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 1800
        Write-Host "✅ Modèle téléchargé avec succès" -ForegroundColor Green
    } catch {
        Write-Host "❌ Erreur lors du téléchargement: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Test du modèle
Write-Host "🧪 Test du modèle avec un exemple juridique..." -ForegroundColor Yellow
try {
    $testBody = @{
        model = $SELECTED_MODEL
        prompt = "Identifie les entités dans ce texte juridique : 'Maître Jean Dupont, 123 rue de la Paix 75001 Paris.' Réponds en JSON."
        stream = $false
        options = @{
            temperature = 0.1
            max_tokens = 300
        }
    } | ConvertTo-Json -Depth 3
    
    $testResponse = Invoke-RestMethod -Uri "http://$OLLAMA_HOST/api/generate" -Method Post -Body $testBody -ContentType "application/json" -TimeoutSec 60
    
    if ($testResponse.response) {
        Write-Host "✅ Test réussi !" -ForegroundColor Green
        Write-Host "📋 Exemple de réponse:" -ForegroundColor Cyan
        Write-Host $testResponse.response.Substring(0, [Math]::Min(200, $testResponse.response.Length)) -ForegroundColor White
    }
} catch {
    Write-Host "❌ Test échoué: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "⚠️  Le modèle est installé mais peut ne pas répondre correctement" -ForegroundColor Yellow
}

# Résumé final
Write-Host ""
Write-Host "📊 Résumé de l'installation:" -ForegroundColor Cyan
Write-Host "================================"
Write-Host "🤖 Modèle: $SELECTED_MODEL" -ForegroundColor White
Write-Host "🌐 URL: http://$OLLAMA_HOST" -ForegroundColor White
Write-Host "✅ Status: Prêt pour l'anonymisation juridique" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Votre système d'anonymisation est opérationnel !" -ForegroundColor Green
Write-Host "💡 Accédez à l'interface: http://localhost:9992" -ForegroundColor Yellow