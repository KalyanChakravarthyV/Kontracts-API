.PHONY: help install test test-unit test-integration test-api test-cov clean dev db-reset lint format

# Default target
help:
	@echo "Lease Accounting API - Makefile Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install dependencies"
	@echo "  make dev              Run development server"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-api         Run API tests only"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make test-watch       Run tests in watch mode"
	@echo ""
	@echo "Database:"
	@echo "  make db-reset         Reset database (drop and recreate)"
	@echo "  make db-migrate       Create new migration"
	@echo "  make db-upgrade       Run pending migrations"
	@echo "  make db-downgrade     Rollback last migration"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linting checks"
	@echo "  make format           Format code with black"
	@echo "  make type-check       Run type checking with mypy"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove build artifacts and caches"

# Installation
install:
	pip install .

install-dev:
	pip install ".[test,dev]"

# Development
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

dev-debug:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 --log-level debug

# Testing
test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-api:
	pytest -m api

test-database:
	pytest -m database

test-calculator:
	pytest -m calculator

test-cov:
	pytest --cov=app --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

test-cov-xml:
	pytest --cov=app --cov-report=xml

test-watch:
	pytest-watch

test-fast:
	pytest -m "not slow"

test-failed:
	pytest --lf

test-verbose:
	pytest -v -s

# Database operations
db-reset:
	python scripts/drop_all_tables.py
	alembic upgrade head

db-migrate:
	alembic revision --autogenerate -m "$(message)"

db-upgrade:
	alembic upgrade head

db-downgrade:
	alembic downgrade -1

db-history:
	alembic history

db-current:
	alembic current

# Code quality
lint:
	flake8 app tests
	pylint app

format:
	black app tests
	isort app tests

format-check:
	black --check app tests
	isort --check app tests

type-check:
	mypy app

# Cleanup
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage 2>/dev/null || true

clean-db:
	rm -f *.db 2>/dev/null || true
	rm -rf alembic/versions/*.pyc 2>/dev/null || true

# Docker operations (if using Docker)
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

# CI/CD
ci-test:
	pytest --cov=app --cov-report=xml --cov-report=term-missing -v

ci-lint:
	flake8 app tests --count --show-source --statistics

# Documentation
docs-serve:
	mkdocs serve

docs-build:
	mkdocs build

# Security
security-check:
	bandit -r app
	safety check

# All checks (useful for pre-commit)
check-all: format-check lint type-check test

# Quick checks
quick-check: format lint test-fast
