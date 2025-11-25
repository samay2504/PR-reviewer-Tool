"""
Project structure verification script
Checks that all required files and directories are in place
"""

import sys
from pathlib import Path


def check_path(path: Path, description: str, required: bool = True) -> bool:
    """Check if a path exists."""
    exists = path.exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {description}: {path}")
    return exists or not required


def main():
    """Run verification checks."""
    print("🔍 PR Review Agent - Project Structure Verification")
    print("=" * 60)
    print()
    
    root = Path(__file__).parent
    all_good = True
    
    # Core files
    print("📄 Core Configuration Files:")
    all_good &= check_path(root / "requirements.txt", "Requirements")
    all_good &= check_path(root / ".env.example", "Environment template")
    all_good &= check_path(root / "README.md", "README")
    all_good &= check_path(root / "LICENSE", "License")
    all_good &= check_path(root / "setup.py", "Setup script")
    all_good &= check_path(root / "pyproject.toml", "PyProject config")
    print()
    
    # Docker
    print("🐳 Docker Files:")
    all_good &= check_path(root / "Dockerfile", "Dockerfile")
    all_good &= check_path(root / "docker-compose.yml", "Docker Compose")
    print()
    
    # CI/CD
    print("⚙️ CI/CD Configuration:")
    all_good &= check_path(root / ".github" / "workflows" / "ci.yml", "GitHub Actions")
    all_good &= check_path(root / ".pre-commit-config.yaml", "Pre-commit hooks")
    print()
    
    # Source code structure
    print("📦 Source Code Structure:")
    src = root / "src" / "pr_agent"
    all_good &= check_path(src, "Main package")
    all_good &= check_path(src / "__init__.py", "Package init")
    all_good &= check_path(src / "api" / "main.py", "API application")
    all_good &= check_path(src / "agents" / "base.py", "Base agent")
    all_good &= check_path(src / "agents" / "security_agent.py", "Security agent")
    all_good &= check_path(src / "agents" / "performance_agent.py", "Performance agent")
    all_good &= check_path(src / "agents" / "style_agent.py", "Style agent")
    all_good &= check_path(src / "cache" / "__init__.py", "Cache client")
    all_good &= check_path(src / "core" / "orchestrator.py", "Orchestrator")
    all_good &= check_path(src / "llm" / "llm_provider.py", "LLM provider")
    all_good &= check_path(src / "llm" / "llm_adapter.py", "LLM adapter")
    all_good &= check_path(src / "templates" / "__init__.py", "Template manager")
    all_good &= check_path(src / "utils" / "config.py", "Configuration")
    all_good &= check_path(src / "utils" / "logging.py", "Logging")
    all_good &= check_path(src / "utils" / "diff_parser.py", "Diff parser")
    print()
    
    # Tests
    print("🧪 Test Suite:")
    tests = src / "tests"
    all_good &= check_path(tests / "conftest.py", "Test fixtures")
    all_good &= check_path(tests / "test_diff_parser.py", "Diff parser tests")
    all_good &= check_path(tests / "test_cache.py", "Cache tests")
    all_good &= check_path(tests / "test_security_agent.py", "Security agent tests")
    all_good &= check_path(tests / "test_api.py", "API tests")
    print()
    
    # Templates
    print("📋 Templates:")
    templates = root / "templates"
    all_good &= check_path(templates, "Templates directory")
    all_good &= check_path(templates / "pr_review_v1.yaml", "PR review template")
    all_good &= check_path(templates / "security_analysis_v1.yaml", "Security template")
    all_good &= check_path(templates / "performance_analysis_v1.yaml", "Performance template")
    all_good &= check_path(templates / "style_readability_v1.yaml", "Style template")
    print()
    
    # Developer tools
    print("🛠️ Developer Tools:")
    all_good &= check_path(root / "cli.py", "CLI tool")
    all_good &= check_path(root / "example_usage.py", "Example usage")
    all_good &= check_path(root / "example_diff.txt", "Example diff")
    all_good &= check_path(root / "quickstart.ps1", "Windows quickstart")
    all_good &= check_path(root / "quickstart.sh", "Linux/macOS quickstart")
    all_good &= check_path(root / "Makefile", "Makefile")
    print()
    
    # Documentation
    print("📚 Documentation:")
    all_good &= check_path(root / "README.md", "Main README")
    all_good &= check_path(root / "CONTRIBUTING.md", "Contributing guide")
    all_good &= check_path(root / "IMPLEMENTATION_SUMMARY.md", "Implementation summary")
    print()
    
    # Summary
    print("=" * 60)
    if all_good:
        print("✅ All required files and directories are in place!")
        print()
        print("Next steps:")
        print("  1. Run: pip install -r requirements.txt")
        print("  2. Copy .env.example to .env and configure")
        print("  3. Run: pytest")
        print("  4. Run: python -m pr_agent.api.main")
        return 0
    else:
        print("❌ Some required files or directories are missing!")
        print("   Please check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
