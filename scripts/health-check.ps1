# scripts/health-check.ps1 - Vérification de santé SIMPLIFIÉE

Write-Host "🏥 Vérification de santé du système d'anonymisation SIMPLIFIÉ" -ForegroundColor Green
Write-Host "=============================================================="

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

function Test-SpacyModel {
    Write-Host "🧠 Modèles SpaCy... " -NoNewline
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9991/api/stats" -Method Get -TimeoutSec 10
        if ($response.success) {
            Write-Host "✅ Disponible" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Erreur API" -ForegroundColor Red
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
    
    # Vérifier les services (SANS Ollama)
    if (-not (Test-Service "backend" 9991 "Backend API")) { $issues++ }
    if (-not (Test-Service "frontend" 9992 "Frontend React")) { $issues++ }
    if (-not (Test-Service "redis" 9993 "Redis Cache")) { $issues++ }
    
    Write-Host ""
    Write-Host "🧠 Vérification SpaCy..." -ForegroundColor Cyan
    if (-not (Test-SpacyModel)) { $issues++ }
    
    Write-Host ""
    Write-Host "🐳 Conteneurs Docker :" -ForegroundColor Cyan
    try {
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | Select-Object -First 4
    }
    catch {
        Write-Host "Erreur lors de la récupération des stats Docker" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "📊 Résumé :" -ForegroundColor Cyan
    if ($issues -eq 0) {
        Write-Host "🎉 Système entièrement opérationnel !" -ForegroundColor Green
        Write-Host "🚀 Prêt pour l'anonymisation rapide et locale" -ForegroundColor Green
        Write-Host ""
        Write-Host "🆕 Nouvelles fonctionnalités disponibles :" -ForegroundColor Cyan
        Write-Host "   ✏️  Modification d'entités" -ForegroundColor White
        Write-Host "   🔗 Groupement d'entités" -ForegroundColor White
        Write-Host "   ⚡ Mode Standard : Regex seul (5-15s)" -ForegroundColor White
        Write-Host "   🧠 Mode Approfondi : Regex + SpaCy NER (15-45s)" -ForegroundColor White
    } else {
        Write-Host "⚠️  $issues problème(s) détecté(s)" -ForegroundColor Yellow
        Write-Host "🔧 Consultez les logs : docker-compose logs [service]" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "🏗️ Architecture simplifiée :" -ForegroundColor Cyan
    Write-Host "   ❌ Ollama/LLM supprimés" -ForegroundColor Red
    Write-Host "   ✅ Regex patterns français" -ForegroundColor Green
    Write-Host "   ✅ SpaCy NER pour noms/organisations" -ForegroundColor Green
    Write-Host "   ✅ Traitement 100% local et rapide" -ForegroundColor Green
    
    return $issues
}

Main