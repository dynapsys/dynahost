# DynaHost Makefile
.PHONY: help install dev test test-unit test-integration test-examples test-watch lint format docs docs-serve clean docker-test security release pre-commit coverage-report benchmark check-deps update-deps free-port-80 example-simple example-api example-fullstack example-clean dynadock-up dynadock-down dynadock-logs dynadock-health build-dist check-dist publish publish-testpypi

PYTHON := python3
UV := uv
PROJECT_NAME := dynahost
# Read version dynamically from src/dynahost/__init__.py (__version__ = "x.y.z")
VERSION := $(shell awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py)

# Colours
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)DynaHost Development Commands$(NC)" && echo "" && \
	grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}' | \
	sort

install: ## Install runtime dependencies only
	@echo "$(YELLOW)Installing runtime dependencies...$(NC)"
	$(UV) pip install .
	@echo "$(GREEN)✓ Installed$(NC)"

dev: ## Install development dependencies
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	$(UV) pip install -e .
	$(UV) pip install pytest pytest-cov pytest-asyncio pytest-docker black ruff mypy pytest-watch bandit safety pytest-timeout requests twine
	@chmod +x scripts/test_runner.sh
	@echo "$(GREEN)✓ Development environment ready$(NC)"


test: ## Run all tests with coverage
	@echo "$(YELLOW)Running tests...$(NC)"
	@if command -v uv >/dev/null 2>&1; then \
		uv run pytest tests/ -v --cov=src/dynahost --cov-report=term-missing --cov-report=html; \
	else \
		python3 -c 'import sys; import importlib.util; sys.exit(0 if importlib.util.find_spec("pytest") else 1)' || pip3 install -q pytest pytest-cov requests pytest-timeout; \
		python3 -m pytest tests/ -v --cov=src/dynahost --cov-report=term-missing --cov-report=html; \
	fi
	@$(MAKE) test-examples
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/ -v -m integration

test-examples: ## Run tests for all example applications
	@echo "$(YELLOW)Testing example applications...$(NC)"
	@chmod +x scripts/test_runner.sh
	@./scripts/test_runner.sh all
	@echo "$(GREEN)✓ Example tests complete$(NC)"

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch tests/ -v

lint: ## Run linting checks (ruff + mypy)
	@echo "$(YELLOW)Running linters...$(NC)"
	$(UV) run ruff check src/ tests/
	$(UV) run mypy src/dynahost --ignore-missing-imports
	@echo "$(GREEN)✓ Linting complete$(NC)"

format: ## Format code with black and ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	$(UV) run black src/ tests/
	$(UV) run ruff check --fix src/ tests/
	@echo "$(GREEN)✓ Code formatted$(NC)"

docs: ## Build static documentation
	@echo "$(YELLOW)Building documentation...$(NC)"
	cd docs && $(UV) run mkdocs build
	@echo "$(GREEN)✓ Documentation built in docs/site/$(NC)"

docs-serve: ## Serve documentation locally at http://localhost:8000
	cd docs && $(UV) run mkdocs serve

clean: ## Clean build, cache and temporary files
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .env.dynahost Caddyfile
	# Attempt to remove .dynahost. Some subpaths (caddy/*) may be root-owned; ignore errors.
	rm -rf .dynahost 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@$(MAKE) example-clean 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

clean-caddy: ## Remove Caddy data that may require sudo
	@echo "$(YELLOW)Stopping Caddy and purging .dynahost/caddy...$(NC)"
	-@docker rm -f dynahost-caddy >/dev/null 2>&1 || true
	@sudo rm -rf .dynahost/caddy || true
	@echo "$(GREEN)✓ Caddy data removed$(NC)"

docker-test: ## Run integration tests inside Docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml up -d
	$(UV) run pytest tests/integration/ -v -m docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml down -v

security: ## Run security scanners (bandit & safety)
	$(UV) run bandit -r src/dynahost
	$(UV) run safety check

release: ## Build and publish a release
	@echo "$(YELLOW)Creating release $(VERSION)...$(NC)"
	uv build
	docker build -t $(PROJECT_NAME):$(VERSION) -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)✓ Release artifacts built$(NC)"

# ---------------------------
# PyPI publishing helpers
# ---------------------------

build-dist: ## Build sdist and wheel into dist/
	uv build

check-dist: ## Check built distributions with twine
	$(UV) run --with twine twine check dist/*



build:
	$(PY) -m build

test-e2e:
	@echo "Using PY=$(PY)"
	@echo "LIBVIRT_DEFAULT_URI=$(LIBVIRT_DEFAULT_URI)"
	@echo "dynadock_TEST_IMAGE=$(dynadock_TEST_IMAGE)"
	@echo "dynadock_TEST_OS_VARIANT=$(dynadock_TEST_OS_VARIANT)"
	$(PY) -m pytest -v tests/test_e2e.py

# Versioning
version-show:
	@awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py


version-patch:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$major.$$minor.$$((patch + 1))"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/dynahost/__init__.py; \
	echo "✅ Version updated to $$new_version"


version-minor:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$major.$$((minor + 1)).0"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/dynahost/__init__.py; \
	echo "✅ Version updated to $$new_version"


version-major:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$((major + 1)).0.0"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/dynahost/__init__.py; \
	echo "✅ Version updated to $$new_version"

# Development tools
dev-setup: install
	@echo "🔧 Setting up the development environment..."
	$(PIP) install flake8 black isort
	@echo "✅ Development environment ready"

# Publishing with automatic versioning

publish: clean version-patch build-dist check-dist
	@echo "📦 Publishing package to PyPI..."
	@new_version=$$(awk -F\" '/^__version__/ {print $$2}' src/dynahost/__init__.py); \
	echo "Publishing version $$new_version"; \
	$(UV) run --with twine twine upload dist/*; \
	echo "✅ Version $$new_version published to PyPI"

publish-testpypi: ## Upload package to TestPyPI (requires TESTPYPI_TOKEN env var)
	uv build
	$(UV) run --with twine twine check dist/*
	$(UV) run --with twine twine upload -r testpypi dist/*

publish-pypi: version-patch ## Upload package to PyPI (requires PYPI_TOKEN env var)
	uv build
	$(UV) run --with twine twine check dist/*
	$(UV) run --with twine twine upload dist/*

pre-commit: format lint test ## Run all checks before committing
	@echo "$(GREEN)✓ Ready to commit!$(NC)"

coverage-report: ## Generate HTML coverage report and open it
	$(UV) run pytest tests/ --cov=src/dynahost --cov-report=html
	@echo "$(GREEN)✓ Coverage HTML generated at htmlcov/index.html$(NC)"

benchmark: ## Run performance benchmarks
	$(UV) run pytest tests/benchmarks/ -v --benchmark-only

check-deps: ## List outdated dependencies
	$(UV) pip list --outdated

update-deps: ## Upgrade dependencies to latest versions
	$(UV) pip install --upgrade pip
	$(UV) pip install -e . --upgrade

free-port-80: ## Free up port 80 for Caddy
	@echo "$(YELLOW)Freeing port 80...$(NC)"
	@sudo lsof -t -i :80 -sTCP:LISTEN | xargs -r sudo kill -9 || true
	@docker ps --filter "publish=80" --format "{{.ID}}" | xargs -r docker stop || true
	@echo "$(GREEN)✓ Port 80 is now free$(NC)"

example-simple: ## Run the simple-web example
	@echo "$(YELLOW)Starting simple-web example...$(NC)"
	cd examples/simple-web && dynadock up --enable-tls

example-api: ## Run the REST API example
	@echo "$(YELLOW)Starting REST API example...$(NC)"
	cd examples/rest-api && dynadock up --enable-tls

example-fullstack: ## Run the fullstack example
	@echo "$(YELLOW)Starting fullstack example...$(NC)"
	cd examples/fullstack && dynadock up --enable-tls

example-clean: ## Clean all example Docker resources
	@echo "$(YELLOW)Cleaning example resources...$(NC)"
	@for dir in examples/*/; do \
		if [ -f "$$dir/docker-compose.yaml" ]; then \
			cd "$$dir" && dynadock down -v 2>/dev/null || true; \
		fi; \
	done
	@echo "$(GREEN)✓ Examples cleaned$(NC)"

dynadock-up: ## Start DynaDock with current docker-compose.yaml
	@echo "$(YELLOW)Starting DynaDock services...$(NC)"
	dynadock up --enable-tls

dynadock-down: ## Stop DynaDock services
	@echo "$(YELLOW)Stopping DynaDock services...$(NC)"
	dynadock down

dynadock-logs: ## View DynaDock service logs
	dynadock logs -f

dynadock-health: ## Run health checks on DynaDock services
	@echo "$(YELLOW)Running health checks...$(NC)"
	$(PYTHON) health_check.py
	@echo "$(GREEN)✓ Health check complete$(NC)"

.DEFAULT_GOAL := help
