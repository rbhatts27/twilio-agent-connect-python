.PHONY: help install install-dev test lint format type-check pre-commit clean build publish example

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in the current environment
	pip install -e .

install-dev: ## Install development dependencies with Poetry
	poetry install

test: ## Run tests
	poetry run pytest

lint: ## Run linting (black and isort check)
	poetry run black --check .
	poetry run isort --check-only .

format: ## Format code with black and isort
	poetry run black .
	poetry run isort .

type-check: ## Run type checking with mypy
	poetry run mypy taf

pre-commit: ## Run pre-commit hooks on all files
	poetry run pre-commit run --all-files

install-pre-commit: ## Install pre-commit hooks
	poetry run pre-commit install

check: lint type-check test ## Run all checks (lint, type-check, test)

clean: ## Clean up cache and build artifacts
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build the package
	poetry build

publish: ## Publish to PyPI (requires authentication)
	poetry publish

example: ## Run the basic usage example
	python examples/basic_usage.py

dev-setup: install-dev install-pre-commit ## Complete development environment setup

ci: check ## Run CI checks locally