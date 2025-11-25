"""Setup script for PR Review Agent."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="pr-review-agent",
    version="1.0.0",
    author="PR Review Agent Contributors",
    author_email="samay.m2504@gmail.com",
    description="Automated Pull Request Review System with Multi-Agent Analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pr-review-agent",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/pr-review-agent/issues",
        "Documentation": "https://github.com/yourusername/pr-review-agent#readme",
        "Source Code": "https://github.com/yourusername/pr-review-agent",
    },
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.12.0",
            "ruff>=0.1.7",
            "black>=23.12.0",
            "isort>=5.13.2",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "pr-agent=pr_agent.cli:main",
            "pr-agent-server=pr_agent.api.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "pr_agent": ["templates/*.yaml"],
    },
    zip_safe=False,
)
