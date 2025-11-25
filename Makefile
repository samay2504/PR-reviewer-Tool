# Makefile for PR Review Agent

.PHONY: help install test lint format clean run docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run tests with coverage"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean cache and temp files"
	@echo "  make run          - Run the application"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"

install:
	pip install -r requirements.txt
	pre-commit install

test:
	pytest --cov=pr_agent --cov-report=term --cov-report=html -v

lint:
	ruff check src/
	black --check src/
	mypy src/pr_agent --ignore-missing-imports

format:
	black src/
	isort src/
	ruff check src/ --fix

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov .cache .mypy_cache
	rm -rf dist build *.egg-info

run:
	python -m pr_agent.api.main

docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

dev:
	uvicorn pr_agent.api.main:app --reload --host 0.0.0.0 --port 8000
