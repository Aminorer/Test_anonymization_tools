# scripts/health-check.ps1 - Vérification complète du système

Write-Host "🏥 Vérification de santé du système d'anonymisation" -ForegroundColor Green
Write-Host "================================================="

$issues = 0

# Test des services
function Test-Service {
    param($name, $port, $description)
    
    Write-Host "🔍 $description... " -NoNewline
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$port" -Method Get -TimeoutSec 5 -UseBasicParsing
        Write-Host "✅ [OK]" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "❌ [KO]" -ForegroundColor Red
        return $false
    }
}

# Test Ollama spécifique
function Test-Ollama {
    Write-Host "🤖 Ollama LLM... " -NoNewline
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 10
        $modelCount = $response.models.Count
        Write-Host "✅ [OK] - $modelCount modèle(s)" -ForegroundColor Green
        
        # Vérifier si Mistral est disponible
        $mistralModel = $response.models | Where-Object { $_.name -eq "mistral:7b-instruct" }
        if ($mistralModel) {
            Write-Host "  └─ ✅ Modèle mistral:7b-instruct disponible" -ForegroundColor Green
        } else {
            Write-Host "  └─ ⚠️  Modèle mistral:7b-instruct manquant" -ForegroundColor Yellow
            return $false
        }
        return $true
    } catch {
        Write-Host "❌ [KO]" -ForegroundColor Red
        return $false
    }
}

Write-Host "🔍 Vérification des services..." -ForegroundColor Cyan

# Vérifier Docker Compose
Write-Host "🐳 Docker Compose... " -NoNewline
try {
    $composeStatus = docker-compose ps 2>$null
    if ($composeStatus) {
        Write-Host "✅ [OK]" -ForegroundColor Green
    } else {
        Write-Host "❌ [KO]" -ForegroundColor Red
        $issues++
    }
} catch {
    Write-Host "❌ [KO]" -ForegroundColor Red
    $issues++
}

# Tests des services individuels
if (-not (Test-Service "backend" 9991 "Backend API")) { $issues++ }
if (-not (Test-Service "frontend" 9992 "Frontend React")) { $issues++ }
if (-not (Test-Service "redis" 9993 "Redis Cache")) { $issues++ }
if (-not (Test-Ollama)) { $issues++ }

Write-Host ""
Write-Host "📊 Informations système:" -ForegroundColor Cyan

# Conteneurs Docker
Write-Host "🐳 Conteneurs Docker:"
try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-Object -Skip 1
    foreach ($container in $containers) {
        if ($container -match "anonymizer-juridique") {
            Write-Host "  $container" -ForegroundColor White
        }
    }
} catch {
    Write-Host "  Erreur lors de la récupération des conteneurs" -ForegroundColor Yellow
}

# Utilisation ressources
Write-Host ""
Write-Host "💾 Utilisation mémoire:"
try {
    $stats = docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}" | Select-Object -Skip 1 | Select-Object -First 5
    foreach ($stat in $stats) {
        if ($stat -match "anonymizer-juridique") {
            Write-Host "  $stat" -ForegroundColor White
        }
    }
} catch {
    Write-Host "  Erreur lors de la récupération des stats" -ForegroundColor Yellow
}

# Test complet de l'application
Write-Host ""
Write-Host "🧪 Test fonctionnel complet:" -ForegroundColor Cyan
try {
    # Test de l'endpoint health du backend
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:9991/health" -Method Get -TimeoutSec 10
    Write-Host "✅ Backend health check OK" -ForegroundColor Green
    
    # Test de l'endpoint stats
    $statsResponse = Invoke-RestMethod -Uri "http://localhost:9991/api/stats" -Method Get -TimeoutSec 10
    Write-Host "✅ Backend API stats OK" -ForegroundColor Green
    Write-Host "  └─ Sessions actives: $($statsResponse.sessions.active_sessions)" -ForegroundColor White
    
} catch {
    Write-Host "❌ Test fonctionnel échoué" -ForegroundColor Red
    $issues++
}

# Résumé final
Write-Host ""
Write-Host "📋 Résumé:" -ForegroundColor Cyan
if ($issues -eq 0) {
    Write-Host "🎉 Système entièrement opérationnel !" -ForegroundColor Green
    Write-Host "🚀 Prêt pour l'anonymisation de documents" -ForegroundColor Green
    Write-Host "🌐 Interface web: http://localhost:9992" -ForegroundColor Yellow
    Write-Host "📚 API docs: http://localhost:9991/docs" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  $issues problème(s) détecté(s)" -ForegroundColor Yellow
    Write-Host "🔧 Vérifiez les logs avec: docker-compose logs [service]" -ForegroundColor Yellow
    Write-Host "🔄 Redémarrage suggéré: docker-compose restart" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "💡 Commandes utiles:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f        # Voir tous les logs" -ForegroundColor White
Write-Host "  docker-compose restart        # Redémarrer tous les services" -ForegroundColor White
Write-Host "  .\scripts\init-ollama.ps1     # Réinitialiser Ollama" -ForegroundColor White

exit $issues