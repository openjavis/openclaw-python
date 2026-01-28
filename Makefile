.PHONY: help install test test-fast test-cov lint format clean build dev docs

help:  ## Show this help
	@egrep -h '\s##\s' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	uv sync

install-all:  ## Install with all optional dependencies
	uv sync --all-extras

test:  ## Run tests
	uv run pytest

test-fast:  ## Run tests in parallel
	uv run pytest -n auto

test-cov:  ## Run tests with coverage
	uv run pytest --cov=clawdbot --cov-report=html --cov-report=term

test-integration:  ## Run integration tests only
	uv run pytest tests/integration/ -v

lint:  ## Run linters
	uv run ruff check clawdbot/ tests/
	uv run mypy clawdbot/ --ignore-missing-imports

format:  ## Format code
	uv run black clawdbot/ tests/ examples/
	uv run ruff check --fix clawdbot/ tests/

format-check:  ## Check formatting
	uv run black --check clawdbot/ tests/
	uv run ruff check clawdbot/ tests/

clean:  ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info htmlcov/ .coverage .pytest_cache/ .ruff_cache/ .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:  ## Build package
	uv build

dev:  ## Run in development mode
	uv run python -m clawdbot api start

docs:  ## Generate documentation
	@echo "Documentation available in docs/"
	@echo "API docs: http://localhost:8000/docs (when server running)"

run-example:  ## Run example (usage: make run-example EXAMPLE=01_basic_agent.py)
	uv run python examples/$(EXAMPLE)

docker-build:  ## Build Docker image
	docker build -t clawdbot-python:latest .

docker-run:  ## Run Docker container
	docker run -it --rm -p 8000:8000 clawdbot-python:latest

docker-test:  ## Test Docker image
	./test-docker-safe.sh
