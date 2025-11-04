.PHONY: help install test lint format type-check pre-commit clean build server ngrok sync dev-setup ci check install-pre-commit

sync:
	uv sync --all-extras --all-packages

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in the current environment
	pip install -e .

test: ## Run tests with coverage
	uv run pytest

lint: ## Run linting with ruff
	uv run ruff check .

format: ## Format code with ruff
	uv run ruff format .
	uv run ruff check --fix .

type-check: ## Run type checking with mypy
	uv run mypy src/taf examples

pre-commit: ## Run pre-commit hooks on all files
	uv run pre-commit run --all-files

install-pre-commit: ## Install pre-commit hooks
	uv run pre-commit install

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
	uv build

server: ## Start the webhook test server on port 8000
	python examples/channels/sms.py --port 8000

exec-demo: ## Start the exec_demo server with hot reloading (watches both examples and src)
	cd examples/exec_demo && uv run uvicorn server:app --host 0.0.0.0 --port 8000 --reload --reload-dir . --reload-dir ../../src/taf

ngrok: ## Start ngrok tunnel to local server with custom domain
	ngrok http 8000 --domain=taf-voice-local.ngrok.dev

dev-setup: sync install-pre-commit ## Complete development environment setup

ci: check ## Run CI checks locally