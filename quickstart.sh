#!/bin/bash
# Quick Start Script for Linux/macOS
# Usage: ./quickstart.sh

set -e

echo "🚀 PR Review Agent - Quick Start"
echo "================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python3 --version

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "✓ Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "✓ Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "✓ Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠ Creating .env from template..."
    cp .env.example .env
    echo "  Please edit .env and add your API keys!"
    echo ""
fi

# Check for at least one API key
HAS_API_KEY=false

if grep -q "GOOGLE_API_KEY=." .env && ! grep -q "GOOGLE_API_KEY=$" .env; then
    HAS_API_KEY=true
    echo "✓ Google API key configured"
fi
if grep -q "GROQ_API_KEY=." .env && ! grep -q "GROQ_API_KEY=$" .env; then
    HAS_API_KEY=true
    echo "✓ Groq API key configured"
fi
if grep -q "OPENAI_API_KEY=." .env && ! grep -q "OPENAI_API_KEY=$" .env; then
    HAS_API_KEY=true
    echo "✓ OpenAI API key configured"
fi

if [ "$HAS_API_KEY" = false ]; then
    echo ""
    echo "⚠ WARNING: No LLM API keys configured!"
    echo "  The system will use fallback mode (rule-based analysis)"
    echo "  Edit .env and add at least one API key for LLM-powered reviews"
    echo ""
fi

# Create necessary directories
echo "✓ Creating directories..."
mkdir -p .cache logs

# Run tests
echo ""
echo "🧪 Running tests..."
export REDIS_ENABLED=false
pytest --quiet --tb=short || echo "⚠ Some tests failed (this is OK for first run)"

echo ""
echo "================================="
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your LLM API keys"
echo "  2. Run: python -m pr_agent.api.main"
echo "  3. Open: http://localhost:8000"
echo "  4. View docs: http://localhost:8000/docs"
echo ""
echo "Or use Docker:"
echo "  docker-compose up --build"
echo ""
