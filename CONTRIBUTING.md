# Contributing to PR Review Agent

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/yourusername/pr-review-agent.git
cd pr-review-agent
```

### 2. Set Up Environment

**Windows:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pre-commit install
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run Tests

```bash
pytest --cov=pr_agent --cov-report=term
```

## Code Standards

### Style Guide

- **Python**: Follow PEP 8
- **Line length**: 100 characters
- **Docstrings**: Google style
- **Type hints**: Required for public APIs

### Tools

- **black**: Code formatting
- **ruff**: Fast linting
- **isort**: Import sorting
- **mypy**: Type checking

Run all formatters:
```bash
make format
```

Run all linters:
```bash
make lint
```

## Testing

### Writing Tests

- Place tests in `src/pr_agent/tests/`
- Name test files `test_*.py`
- Name test functions `test_*`
- Aim for 90%+ coverage
- Use fixtures from `conftest.py`

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest src/pr_agent/tests/test_cache.py

# With coverage
pytest --cov=pr_agent --cov-report=html

# Fast fail
pytest -x
```

## Project Structure

```
src/pr_agent/
├── api/            # FastAPI application
├── agents/         # Analysis agents
├── cache/          # Caching layer
├── core/           # Orchestrator
├── llm/            # LLM provider integration
├── templates/      # Template manager
├── utils/          # Utilities
└── tests/          # Test suite
```

## Creating a New Agent

1. Create file in `src/pr_agent/agents/your_agent.py`:

```python
from .base import BaseAgent, AgentResult, ReviewComment

class YourAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(name="your_agent", *args, **kwargs)
    
    def analyze(self, context: Dict[str, Any]) -> AgentResult:
        # Your analysis logic
        pass
```

2. Add to `src/pr_agent/agents/__init__.py`
3. Register in orchestrator
4. Write tests in `tests/test_your_agent.py`
5. Create template in `templates/your_agent_v1.yaml`

## Creating a New Template

Create `templates/your_template.yaml`:

```yaml
id: your_template_v1
version: "1.0.0"
description: "Description of your template"
variables:
  - name: var1
    type: str
  - name: var2
    type: str
template: |
  Your prompt here using {var1} and {var2}
```

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code
- Add tests
- Update documentation
- Run tests and linters

### 3. Commit

```bash
git add .
git commit -m "feat: add your feature"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `chore:` Maintenance

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

### PR Checklist

- [ ] Tests pass locally
- [ ] Code coverage ≥90%
- [ ] Linters pass
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Pre-commit hooks pass

## Common Tasks

### Adding a Dependency

1. Add to `requirements.txt`
2. Update `README.md` if needed
3. Test cross-platform compatibility
4. Document in CONTRIBUTING.md

### Updating Templates

Templates support hot reload in development:
1. Edit YAML file in `templates/`
2. Changes reflect immediately (no restart needed)
3. Test via API: `GET /templates/{id}`

### Debugging

Enable debug mode:
```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
python -m pr_agent.api.main
```

View logs:
```bash
# Docker
docker-compose logs -f app

# Local
# Logs to console
```

## Architecture Decisions

### LLM Provider Priority

1. Google Gemini - Best free tier
2. Groq - Fastest inference
3. OpenAI - Most reliable
4. HuggingFace - Open models
5. Fallback - Rule-based

### Cache Strategy

- Redis primary (distributed)
- Disk cache fallback (local)
- TTLs: Analysis (24h), Templates (1w), Agent State (10m)

### Agent Design

- Agents are independent
- Each has LLM + rule-based modes
- Orchestrator runs agents concurrently
- Results aggregated by orchestrator

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/pr-review-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pr-review-agent/discussions)
- **Documentation**: See `README.md` and `docs/`

## Code of Conduct

- Be respectful
- Be inclusive
- Be constructive
- Follow project guidelines

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
