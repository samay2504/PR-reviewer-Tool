# PR Review Agent

> **Automated Pull Request Review System** with Multi-Agent Analysis, LLM Integration, and Redis Caching

[![GitHub](https://img.shields.io/badge/GitHub-samay2504/PR--reviewer--Tool-blue?logo=github)](https://github.com/samay2504/PR-reviewer-Tool)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

## Overview

PR Review Agent is a production-ready, open-source system for automated code review. It analyzes pull requests using multiple specialized agents (security, performance, style) powered by LLMs with robust fallback capabilities.

### Key Features

✅ **Multi-Agent Architecture** - Security, Performance, and Style agents work concurrently  
✅ **Robust LLM Integration** - Supports Google Gemini, Groq, OpenAI, HuggingFace with automatic fallback  
✅ **Dynamic Prompt Templates** - Edit templates without code changes, hot reload supported  
✅ **Redis Caching** - Low-latency repeated requests with disk-based fallback  
✅ **Cross-Platform** - Works on Windows 11, macOS, and Linux  
✅ **CI/CD Ready** - GitHub Actions with multi-OS matrix testing  
✅ **Docker Support** - Full Docker Compose setup for easy deployment  
✅ **90%+ Test Coverage** - Comprehensive unit and integration tests  

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Application                    │
├─────────────────────────────────────────────────────────────┤
│  Endpoints: /analyze, /health, /templates, /cache          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │    Orchestrator       │
         │  (Coordinates Agents) │
         └───────┬───────────────┘
                 │
         ┌───────┴────────┬──────────────┬─────────────┐
         ▼                ▼              ▼             ▼
  ┌──────────┐   ┌──────────────┐  ┌──────────┐  ┌────────┐
  │ Security │   │ Performance  │  │  Style   │  │  ...   │
  │  Agent   │   │    Agent     │  │  Agent   │  │        │
  └────┬─────┘   └──────┬───────┘  └────┬─────┘  └────────┘
       │                │               │
       └────────────────┴───────────────┘
                        │
                ┌───────┴────────┐
                │  LLM Adapter   │
                │  (with retry)  │
                └───────┬────────┘
                        │
          ┌─────────────┴─────────────┬─────────────┐
          ▼                           ▼             ▼
    ┌──────────┐              ┌──────────┐   ┌──────────┐
    │  Gemini  │              │   Groq   │   │  OpenAI  │
    └──────────┘              └──────────┘   └──────────┘
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (optional, for containerized deployment)
- **Redis** (optional, can use disk cache fallback)

### Windows 11 Setup (PowerShell)

```powershell
# 1. Clone repository
git clone https://github.com/samay2504/PR-reviewer-Tool.git
cd PR-reviewer-Tool

# 2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
Copy-Item .env.example .env
# Edit .env with your API keys (at least one LLM provider)

# 5. Run the application
python -m pr_agent.api.main
```

The API will be available at `http://localhost:8000`

### Linux / macOS Setup

```bash
# 1. Clone repository
git clone https://github.com/samay2504/PR-reviewer-Tool.git
cd PR-reviewer-Tool

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Run the application
python -m pr_agent.api.main
```

### Docker Setup

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 2. Start services (Redis + App)
docker-compose up --build

# Access at http://localhost:8000
```

---

## Configuration

### Required Environment Variables

At minimum, configure **one** LLM provider:

```bash
# Option 1: Google Gemini (Recommended - Free tier available)
GOOGLE_API_KEY=your_google_api_key

# Option 2: Groq (Fast, free tier)
GROQ_API_KEY=your_groq_api_key

# Option 3: OpenAI
OPENAI_API_KEY=your_openai_api_key

# Option 4: HuggingFace
HUGGINGFACEHUB_API_TOKEN=your_huggingface_token
```

### Optional Configuration

```bash
# LLM Provider Preference (comma-separated)
LLM_PROVIDER_PREFERENCE=google_genai,groq,openai,huggingface,fallback

# Redis (optional - falls back to disk cache)
REDIS_URL=redis://localhost:6379/0
REDIS_ENABLED=true

# Cache Settings
CACHE_DEFAULT_TTL_SECONDS=86400
CACHE_ANALYSIS_TTL=86400

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
DEBUG=false
```

---

## API Usage

### Analyze a PR Diff

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "diff_text": "diff --git a/file.py b/file.py\n...",
    "use_cache": true
  }'
```

**Response:**
```json
{
  "request_id": "uuid-here",
  "diff_hash": "sha256-hash",
  "comments": [
    {
      "file": "src/example.py",
      "line_start": 10,
      "line_end": 12,
      "severity": "HIGH",
      "category": "SECURITY",
      "message": "Potential SQL injection vulnerability",
      "suggestion_patch": "Use parameterized queries",
      "agent": "security"
    }
  ],
  "summary": {
    "total_comments": 5,
    "total_files": 2,
    "agents_run": ["security", "performance", "style"]
  },
  "provider": "google_genai_gemini-2.5-flash",
  "cached": false
}
```

### Other Endpoints

```bash
# Health check
GET /health

# List templates
GET /templates

# Get specific template
GET /templates/{template_id}

# Invalidate cache
DELETE /cache/{repo}/{pr_number}

# System stats
GET /stats
```

---

## Template System

Templates are stored in `templates/` as YAML files and can be edited without restarting the application (hot reload enabled by default).

### Example Template

```yaml
id: custom_review_v1
version: "1.0.0"
description: "Custom code review template"
variables:
  - name: code_snippet
    type: str
  - name: file_path
    type: str
template: |
  Review this code for potential issues:
  
  File: {file_path}
  Code: {code_snippet}
  
  Return JSON array with findings.
```

### Managing Templates via API

```bash
# List all templates
curl http://localhost:8000/templates

# Get specific template
curl http://localhost:8000/templates/pr_review_v1
```

---

## Testing

### Run Tests

```powershell
# Windows PowerShell
pytest --cov=pr_agent --cov-report=term --cov-report=html

# Or use the simple command
pytest
```

```bash
# Linux / macOS
pytest --cov=pr_agent --cov-report=term --cov-report=html
```

### Coverage Report

Coverage reports are generated in `htmlcov/index.html`. Open in browser to view detailed coverage.

Target: **≥90% coverage**

---

## Development

### Install Pre-commit Hooks

```bash
pre-commit install
```

This will run:
- **ruff** - Fast Python linter
- **black** - Code formatter
- **isort** - Import sorting
- **gitleaks** - Secret scanning

### Code Style

```bash
# Format code
black src/

# Lint
ruff check src/ --fix

# Type check
mypy src/pr_agent --ignore-missing-imports
```

---

## Caching Strategy

### Cache Keys

- `pr:analysis:{repo}:{pr_number}:{diff_hash}` → Analysis result (24h TTL)
- `template:{id}` → Template content (1 week TTL)
- `agent_state:{request_id}` → Ephemeral agent state (10min TTL)

### Cache Invalidation

```bash
# Invalidate specific PR cache
curl -X DELETE http://localhost:8000/cache/owner/repo/123

# Redis pub/sub used for template updates (automatic)
```

### Fallback Behavior

If Redis is unavailable, the system automatically falls back to disk-based caching using `diskcache` with the same TTL semantics.

---

## LLM Provider Details

### Provider Preference

The system tries providers in order specified by `LLM_PROVIDER_PREFERENCE`:

1. **Google Gemini** - Fast, generous free tier
2. **Groq** - Very fast inference
3. **OpenAI** - Reliable, requires paid account
4. **HuggingFace** - Open models
5. **Fallback** - Rule-based static analysis (no LLM required)

### Fallback Mode

If all LLM providers fail or are unavailable, the system uses rule-based static analysis:
- Regex pattern matching for common issues
- Security vulnerability patterns (hardcoded secrets, SQL injection, etc.)
- Performance anti-patterns (nested loops, etc.)
- Style issues (line length, naming conventions)

---

## Deployment

### Production Considerations

1. **Environment Variables**: Use secrets management (Azure Key Vault, AWS Secrets Manager, etc.)
2. **Redis**: Deploy Redis with persistence enabled for production
3. **Scaling**: Use multiple workers (`APP_WORKERS=8`) and load balancer
4. **Monitoring**: Enable Prometheus metrics endpoint (optional integration)
5. **Rate Limiting**: Configure `RATE_LIMIT_REQUESTS_PER_MINUTE`

### Docker Production

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests (optional).

---

## Troubleshooting

### Common Issues

**Issue**: `LLM provider failed`  
**Solution**: Check API keys in `.env`, ensure at least one provider is configured

**Issue**: `Redis connection failed`  
**Solution**: Set `REDIS_ENABLED=false` or start Redis with `docker-compose up redis`

**Issue**: `Template not found`  
**Solution**: Ensure `templates/` directory exists and contains YAML files

**Issue**: `Import errors`  
**Solution**: Ensure all dependencies installed: `pip install -r requirements.txt`

### Logs

```bash
# View logs (Docker)
docker-compose logs -f app

# View logs (local)
# Logs output to console by default, configure LOG_LEVEL=DEBUG for verbose
```

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Ensure pre-commit hooks pass
6. Submit a pull request

---

## License

MIT License - see [LICENSE](LICENSE) file

---

## Roadmap

- [ ] GitHub App integration (post comments directly to PRs)
- [ ] Slack/Discord notifications
- [ ] Custom agent plugins
- [ ] Web UI for review management
- [ ] Support for GitLab, Bitbucket
- [ ] Incremental analysis (only new commits)

---

## Support

- **Repository**: [GitHub](https://github.com/samay2504/PR-reviewer-Tool)
- **Issues**: [GitHub Issues](https://github.com/samay2504/PR-reviewer-Tool/issues)
- **Discussions**: [GitHub Discussions](https://github.com/samay2504/PR-reviewer-Tool/discussions)
- **Live Demo**: [GitHub Pages](https://samay2504.github.io/PR-reviewer-Tool/)

---

## Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [LangChain](https://www.langchain.com/)
- [Redis](https://redis.io/)
- [Pydantic](https://pydantic.dev/)

---

**Made with ❤️ for better code reviews**
