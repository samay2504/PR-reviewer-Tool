# PR Agent CLI - Quick Start Guide

## Installation

The CLI is automatically installed when you install the PR Agent package:

```bash
pip install -e .
```

This creates two commands:
- `pr-agent` - Main CLI interface
- `pr-agent-server` - Direct server startup (if needed)

## Usage

### 1. Interactive Mode (Recommended)

Simply run `pr-agent` to enter interactive mode:

```bash
pr-agent
```

Then paste any of these formats:
- Full URL: `https://github.com/django/django/pull/20316`
- Repo URL: `https://github.com/facebook/react` (lists PRs to select)
- Repo name: `django/django` (lists PRs to select)
- Space-separated: `django/django 20316`

### 2. Direct Analysis

Analyze a specific PR directly:

```bash
# Using repo name and PR number
pr-agent analyze django/django 20316

# Using full GitHub URL
pr-agent analyze https://github.com/facebook/react/pull/31000

# Get markdown output (for PR comments)
pr-agent analyze django/django 20316 --format markdown
```

### 3. List PRs from a Repository

List and select from available PRs:

```bash
# List open PRs (default)
pr-agent list django/django

# List closed PRs
pr-agent list django/django --state closed

# List all PRs
pr-agent list django/django --state all
```

### 4. Quick Analysis (Non-Interactive)

For scripting or automation:

```bash
pr-agent quick facebook/react 31000
```

### 5. Server Management

Start the API server:

```bash
pr-agent server start

# Custom port
pr-agent server start --port 8080

# Custom host
pr-agent server start --host 0.0.0.0 --port 8080
```

Check server status:

```bash
pr-agent server status
```

## Examples

### Example 1: Interactive Mode with Repo Listing

```bash
$ pr-agent

🤖 PR Agent - Interactive Mode
====================================================================================================

🔗 Enter GitHub URL or repo: django/django

🔍 Fetching open PRs from django/django...

📋 Found 20 open PR(s):

#      Title                                                        State      Author              
----------------------------------------------------------------------------------------------------
18234  Fix query optimization for nested aggregates                 open       django-contributor  
18233  Add support for PostgreSQL JSONB operations                  open       postgres-dev        
18232  Improve migration performance                                open       core-team           
...

🎯 Enter PR number to analyze (or 'q' to quit): 18234

🔬 Analyzing django/django PR #18234...
⏳ This may take a few seconds...

[Analysis results displayed]
```

### Example 2: Direct URL Analysis

```bash
$ pr-agent analyze https://github.com/facebook/react/pull/31000

🔬 Analyzing facebook/react PR #31000...
⏳ This may take a few seconds...

====================================================================================================
📊 Analysis Result for facebook/react/31000
====================================================================================================

📁 Files Analyzed: 1
🔍 Issues Found: 5
🤖 Provider: groq_llama-3.1-8b-instant
💾 From Cache: No

📈 By Severity:
   Critical: 0
   High: 0
   Medium: 0
   Low: 5

📝 Executive Summary:
----------------------------------------------------------------------------------------------------
The code change has moderate quality with security issues detected...
----------------------------------------------------------------------------------------------------

⚠️ Recommendation: Approve With Suggestions
```

### Example 3: Markdown Output for PR Comments

```bash
$ pr-agent analyze django/django 20316 --format markdown

# 🤖 PR Analysis Summary

## 📊 Overview
- **Files Analyzed:** 1
- **Issues Found:** 5
- **Recommendation:** ⚠️ APPROVE_WITH_SUGGESTIONS

## 🎯 Severity Breakdown
- Critical: 0
- High: 2
- Medium: 2
- Low: 1

[Full markdown output...]
```

## Tips

1. **First Time Setup**: Make sure your `GITHUB_TOKEN` is set in `.env`
2. **Server Must Be Running**: The CLI communicates with the API server at `localhost:8000`
3. **Start Server First**: Run `pr-agent server start` in a separate terminal before using analysis commands
4. **Cached Results**: Second analysis of the same PR will be instant (retrieved from cache)
5. **Ctrl+C to Exit**: Press Ctrl+C anytime to gracefully exit

## Comparison: Old vs New

### Old Way (Complex)
```powershell
# Start server manually
python -m pr_agent.api.main

# In another terminal, craft complex PowerShell request
$body = '{"repo": "facebook/react", "pr_number": 31000}'
Invoke-RestMethod -Uri "http://localhost:8000/analyze" -Method Post -Body $body -ContentType "application/json"
```

### New Way (Simple)
```bash
# Start server
pr-agent server start

# In another terminal, simple command
pr-agent analyze facebook/react 31000

# Or even simpler - interactive mode
pr-agent
# Then paste: facebook/react 31000
```

## Environment Variables

Required in `.env`:
```bash
GITHUB_TOKEN=your_github_token_here
```

Optional:
```bash
# LLM Provider settings
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Redis (optional, falls back to disk cache)
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Troubleshooting

### "Failed to connect to API server"
- Make sure the server is running: `pr-agent server status`
- Start it if needed: `pr-agent server start`

### "No matching distribution found"
- Update requirements.txt version if needed
- Run: `pip install -e . --no-deps`

### "Permission denied" or "Command not found"
- Make sure package is installed: `pip install -e .`
- Try running with: `python -m pr_agent.cli` instead

## Advanced Usage

### Integration with Scripts

```python
# analyze_prs.py
import subprocess
import json

repos = [
    ("django/django", 20316),
    ("facebook/react", 31000),
]

for repo, pr_num in repos:
    result = subprocess.run(
        ["pr-agent", "quick", repo, str(pr_num)],
        capture_output=True,
        text=True
    )
    print(f"Analyzed {repo} PR #{pr_num}")
```

### Continuous Integration

```yaml
# .github/workflows/pr-review.yml
name: Auto PR Review
on: [pull_request]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install PR Agent
        run: pip install -e .
      - name: Start Server
        run: pr-agent server start &
      - name: Analyze PR
        run: |
          pr-agent analyze ${{ github.repository }} ${{ github.event.pull_request.number }} --format markdown > review.md
      - name: Post Comment
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const review = fs.readFileSync('review.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: review
            });
```
