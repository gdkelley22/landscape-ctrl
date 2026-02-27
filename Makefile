.PHONY: install test lint fmt typecheck check clean build

# Install dev dependencies
install:
	pip install -e ".[dev]"

# Run unit tests
test:
	pytest tests/unit/ -v --tb=short

# Run all tests with coverage
coverage:
	pytest tests/unit/ --cov=landscape_ctrl --cov-report=term-missing --cov-report=html

# Lint with ruff
lint:
	ruff check src/ tests/

# Auto-format with ruff
fmt:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Type checking with mypy
typecheck:
	mypy src/

# Run lint + typecheck + tests (pre-commit gate)
check: lint typecheck test

# Build distributable wheel
build:
	pip install build
	python -m build

# Clean build artifacts
clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info
	rm -rf htmlcov/ .coverage .mypy_cache .ruff_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
