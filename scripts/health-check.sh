# scripts/health-check.ps1 - Vérification de santé pour Windows

Write-Host "🏥 Vérification de santé du système d'anonymisation" -ForegroundColor Green
Write-Host "================================================="

function Test-Service {
    param($service, $port, $name)
    
    Write-Host "🔍 Test $name... " -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port" -Method Get -TimeoutSec 5 -UseBasicParsing
        Write-Host "✅ [OK]" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ [KO]" -ForegroundColor Red
        return $false
    }
}

function Test-OllamaModel {
    param($model)
    
    Write-Host "🤖 Modèle $model... " -NoNewline
    
    try {
        $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 10
        if ($tags.models | Where-Object { $_.name -eq $model }) {
            Write-Host "✅ Disponible" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Manquant" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ Erreur" -ForegroundColor Red
        return $false
    }
}

function Main {
    $issues = 0
    
    Write-Host "🔍 Vérification des services..." -ForegroundColor Cyan
    
    # Vérifier Docker Compose
    try {
        docker-compose ps | Out-Null
        Write-Host "✅ Docker Compose [OK]" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Docker Compose [KO]" -ForegroundColor Red
        $issues++
    }
    
    # Vérifier les services
    if (-not (Test-Service "backend" 9991 "Backend API")) { $issues++ }
    if (-not (Test-Service "frontend" 9992 "Frontend React")) { $issues++ }
    if (-not (Test-Service "redis" 9993 "Redis Cache")) { $issues++ }
    if (-not (Test-Service "ollama" 11434 "Ollama LLM")) { $issues++ }
    
    Write-Host ""
    Write-Host "🤖 Vérification des modèles Ollama..." -ForegroundColor Cyan
    if (-not (Test-OllamaModel "mistral:7b-instruct")) { $issues++ }
    Test-OllamaModel "llama3.1:8b" | Out-Null
    
    Write-Host ""
    Write-Host "🐳 Conteneurs Docker :" -ForegroundColor Cyan
    try {
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | Select-Object -First 6
    }
    catch {
        Write-Host "Erreur lors de la récupération des stats Docker" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "📊 Résumé :" -ForegroundColor Cyan
    if ($issues -eq 0) {
        Write-Host "🎉 Système entièrement opérationnel !" -ForegroundColor Green
        Write-Host "🚀 Prêt pour l'anonymisation de documents" -ForegroundColor Green
    } else {
        Write-Host "⚠️  $issues problème(s) détecté(s)" -ForegroundColor Yellow
        Write-Host "🔧 Consultez les logs : docker-compose logs [service]" -ForegroundColor Yellow
    }
    
    return $issues
}

Main