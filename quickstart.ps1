# Quick Start Script for Windows PowerShell
# Usage: .\quickstart.ps1

Write-Host "🚀 PR Review Agent - Quick Start" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "✓ Checking Python version..." -ForegroundColor Green
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python not found! Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "  $pythonVersion" -ForegroundColor Gray

# Create virtual environment
if (!(Test-Path ".venv")) {
    Write-Host "✓ Creating virtual environment..." -ForegroundColor Green
    python -m venv .venv
}

# Activate virtual environment
Write-Host "✓ Activating virtual environment..." -ForegroundColor Green
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "✓ Installing dependencies..." -ForegroundColor Green
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Check for .env file
if (!(Test-Path ".env")) {
    Write-Host "⚠ Creating .env from template..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "  Please edit .env and add your API keys!" -ForegroundColor Yellow
    Write-Host ""
}

# Check for at least one API key
$envContent = Get-Content .env -Raw
$hasApiKey = $false

if ($envContent -match 'GOOGLE_API_KEY=.+' -and $envContent -notmatch 'GOOGLE_API_KEY=$') {
    $hasApiKey = $true
    Write-Host "✓ Google API key configured" -ForegroundColor Green
}
if ($envContent -match 'GROQ_API_KEY=.+' -and $envContent -notmatch 'GROQ_API_KEY=$') {
    $hasApiKey = $true
    Write-Host "✓ Groq API key configured" -ForegroundColor Green
}
if ($envContent -match 'OPENAI_API_KEY=.+' -and $envContent -notmatch 'OPENAI_API_KEY=$') {
    $hasApiKey = $true
    Write-Host "✓ OpenAI API key configured" -ForegroundColor Green
}

if (!$hasApiKey) {
    Write-Host ""
    Write-Host "⚠ WARNING: No LLM API keys configured!" -ForegroundColor Yellow
    Write-Host "  The system will use fallback mode (rule-based analysis)" -ForegroundColor Yellow
    Write-Host "  Edit .env and add at least one API key for LLM-powered reviews" -ForegroundColor Yellow
    Write-Host ""
}

# Create necessary directories
Write-Host "✓ Creating directories..." -ForegroundColor Green
New-Item -ItemType Directory -Force -Path ".cache" | Out-Null
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

# Run tests
Write-Host ""
Write-Host "🧪 Running tests..." -ForegroundColor Cyan
$env:REDIS_ENABLED = "false"
pytest --quiet --tb=short

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ All tests passed!" -ForegroundColor Green
} else {
    Write-Host "⚠ Some tests failed (this is OK for first run)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "🎉 Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env and add your LLM API keys"
Write-Host "  2. Run: python -m pr_agent.api.main"
Write-Host "  3. Open: http://localhost:8000"
Write-Host "  4. View docs: http://localhost:8000/docs"
Write-Host ""
Write-Host "Or use Docker:" -ForegroundColor Cyan
Write-Host "  docker-compose up --build"
Write-Host ""
