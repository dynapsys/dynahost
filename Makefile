# ARPx Makefile
.PHONY: help install install-user install-system uninstall-user uninstall-system dev test test-unit test-integration test-watch lint format docs docs-serve clean docker-test security release pre-commit coverage-report benchmark check-deps update-deps free-port-80 example-cli example-api example-docker example-podman example-clean test-examples build-dist check-dist publish publish-testpypi

PYTHON := python3
UV := uv
PROJECT_NAME := arpx
# Read version dynamically from src/arpx/__init__.py (__version__ = "x.y.z")
VERSION := $(shell awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py)
INSTALL_EXTRAS ?= compose,mdns

# Colours
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)ARPx Development Commands$(NC)" && echo "" && \
	grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "  %-25s %s\n", $$1, $$2}' | \
	sort

install: ## Install arpx CLI for current user and link system-wide (ensures 'sudo arpx' works)
	@echo "$(YELLOW)Installing arpx CLI (user) with extras: [$(INSTALL_EXTRAS)]...$(NC)"
	@set -e; \
	if ! command -v arpx >/dev/null 2>&1; then \
		if command -v $(UV) >/dev/null 2>&1; then \
			$(UV) tool install --force ".[${INSTALL_EXTRAS}]" || $(UV) tool install --force .; \
		elif command -v pipx >/dev/null 2>&1; then \
			pipx install --force ".[${INSTALL_EXTRAS}]" || pipx install --force .; \
		else \
			$(PYTHON) -m pip install --user ".[${INSTALL_EXTRAS}]" || $(PYTHON) -m pip install --user .; \
		fi; \
	else \
		printf "arpx already present at %s\n" "$$(command -v arpx)"; \
	fi; \
	ARPX_BIN=$$(command -v arpx || true); \
	if [ -z "$$ARPX_BIN" ] && [ -x "$$HOME/.local/bin/arpx" ]; then \
		ARPX_BIN="$$HOME/.local/bin/arpx"; \
	fi; \
	if [ -n "$$ARPX_BIN" ]; then \
		# Link in /usr/local/bin (commonly in PATH)
		if ! sudo sh -lc 'test -x "/usr/local/bin/arpx"'; then \
			echo "Linking /usr/local/bin/arpx -> $$ARPX_BIN (sudo may prompt)"; \
			sudo ln -sf "$$ARPX_BIN" /usr/local/bin/arpx; \
		else \
			printf "/usr/local/bin/arpx exists (%s)\n" "$$(/usr/bin/readlink -f /usr/local/bin/arpx || /bin/ls -l /usr/local/bin/arpx)"; \
		fi; \
		# If sudo PATH doesn't include /usr/local/bin, ensure fallback in /usr/bin
		if ! sudo sh -lc 'command -v arpx >/dev/null 2>&1'; then \
			echo "'/usr/local/bin' not in sudo PATH; adding fallback /usr/bin/arpx"; \
			sudo ln -sf "$$ARPX_BIN" /usr/bin/arpx; \
		fi; \
		printf "\n$(GREEN)✓ arpx ready. Try: sudo arpx --help$(NC)\n"; \
	else \
		echo "$(RED)!! arpx not found after install. Consider: make install-system$(NC)"; \
		exit 1; \
	fi

install-user: ## Install arpx CLI to ~/.local/bin (uv tool -> pipx -> pip --user)
	@set -e; \
	if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) tool install --force ".[${INSTALL_EXTRAS}]" || $(UV) tool install --force .; \
	elif command -v pipx >/dev/null 2>&1; then \
		pipx install --force ".[${INSTALL_EXTRAS}]" || pipx install --force .; \
	else \
		$(PYTHON) -m pip install --user ".[${INSTALL_EXTRAS}]" || $(PYTHON) -m pip install --user .; \
	fi

install-system: ## Install arpx system-wide (console script in /usr/local/bin)
	@echo "$(YELLOW)Installing arpx system-wide via pip ($(PYTHON)) with extras: [$(INSTALL_EXTRAS)]...$(NC)"
	sudo $(PYTHON) -m pip install ".[${INSTALL_EXTRAS}]"
	@echo "$(GREEN)✓ Installed system-wide. Try: sudo arpx --help$(NC)"

uninstall-user: ## Uninstall user-level arpx CLI and remove system link
	-$(UV) tool uninstall arpx || true
	-rm -f $$HOME/.local/bin/arpx || true
	-sudo rm -f /usr/local/bin/arpx || true

uninstall-system: ## Uninstall system-wide arpx
	-sudo $(PYTHON) -m pip uninstall -y arpx || true
	-sudo rm -f /usr/local/bin/arpx || true

dev: ## Install development dependencies
	@echo "$(YELLOW)Setting up development environment...$(NC)"
	$(UV) pip install -e .
	$(UV) pip install pytest pytest-cov pytest-asyncio pytest-docker black ruff mypy pytest-watch bandit safety pytest-timeout requests twine
	@echo "$(GREEN)✓ Development environment ready$(NC)"


test: ## Run all tests with coverage
	@echo "$(YELLOW)Running tests...$(NC)"
	@if command -v uv >/dev/null 2>&1; then \
		uv run pytest tests/ -v --cov=src/arpx --cov-report=term-missing --cov-report=html; \
	else \
		python3 -c 'import sys; import importlib.util; sys.exit(0 if importlib.util.find_spec("pytest") else 1)' || pip3 install -q pytest pytest-cov requests pytest-timeout; \
		python3 -m pytest tests/ -v --cov=src/arpx --cov-report=term-missing --cov-report=html; \
	fi
	@echo "$(GREEN)✓ All tests complete$(NC)"

test-unit: ## Run unit tests only
	$(UV) run pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only
	$(UV) run pytest tests/integration/ -v -m integration

 

test-watch: ## Run tests in watch mode
	$(UV) run pytest-watch tests/ -v

lint: ## Run linting checks (ruff + mypy)
	@echo "$(YELLOW)Running linters...$(NC)"
	$(UV) run ruff check src/ tests/
	$(UV) run mypy src/arpx --ignore-missing-imports
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
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .env.arpx Caddyfile
	# Attempt to remove .arpx. Some subpaths may be root-owned; ignore errors.
	rm -rf .arpx 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@$(MAKE) example-clean 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete$(NC)"

test-examples: ## Run smoke tests for examples (requires sudo and docker/podman where applicable)
	@chmod +x scripts/test_examples.sh || true
	@bash scripts/test_examples.sh

clean-caddy: ## Remove Caddy data that may require sudo
	@echo "$(YELLOW)Stopping Caddy and purging .arpx/caddy...$(NC)"
	-@docker rm -f arpx-caddy >/dev/null 2>&1 || true
	@sudo rm -rf .arpx/caddy || true
	@echo "$(GREEN)✓ Caddy data removed$(NC)"

docker-test: ## Run integration tests inside Docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml up -d
	$(UV) run pytest tests/integration/ -v -m docker
	docker-compose -f tests/fixtures/docker-compose.test.yaml down -v


security: ## Run security scanners (bandit & safety)
	$(UV) run bandit -r src/arpx
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

test-e2e: ## Run end-to-end tests (requires root and Docker; opt-in)
	@if command -v uv >/dev/null 2>&1; then \
		uv run pytest -v -m e2e; \
	else \
		python3 -m pytest -v -m e2e; \
	fi

# Versioning
version-show:
	@awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py


version-patch:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$major.$$minor.$$((patch + 1))"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/arpx/__init__.py; \
	echo "✅ Version updated to $$new_version"


version-minor:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$major.$$((minor + 1)).0"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/arpx/__init__.py; \
	echo "✅ Version updated to $$new_version"


version-major:
	@current_version=$$(awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py); \
	IFS='.' read -r major minor patch <<< "$$current_version"; \
	new_version="$$((major + 1)).0.0"; \
	echo "Bumping version from $$current_version to $$new_version"; \
	sed -i "s/__version__ = \"$$current_version\"/__version__ = \"$$new_version\"/" src/arpx/__init__.py; \
	echo "✅ Version updated to $$new_version"

# Development tools
dev-setup: install
	@echo "🔧 Setting up the development environment..."
	$(PIP) install flake8 black isort
	@echo "✅ Development environment ready"

# Publishing with automatic versioning

publish: clean version-patch build-dist check-dist
	@echo "📦 Publishing package to PyPI..."
	@new_version=$$(awk -F\" '/^__version__/ {print $$2}' src/arpx/__init__.py); \
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
	$(UV) run pytest tests/ --cov=src/arpx --cov-report=html
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

example-cli: ## Run CLI example (requires sudo)
	@echo "$(YELLOW)Running CLI example...$(NC)"
	@sudo bash examples/cli/run.sh

example-api: ## Run API example (requires sudo)
	@echo "$(YELLOW)Running API example...$(NC)"
	@sudo python3 examples/api/simple_api.py

example-docker: ## Start Docker example stack and bridge to LAN (requires sudo)
	@echo "$(YELLOW)Starting Docker example...$(NC)"
	@docker compose -f examples/docker/docker-compose.yml up -d
	@sudo $$(which arpx) compose -f examples/docker/docker-compose.yml

example-podman: ## Start Podman example stack and bridge to LAN (requires sudo)
	@echo "$(YELLOW)Starting Podman example...$(NC)"
	@podman-compose -f examples/podman/docker-compose.yml up -d
	@sudo $$(which arpx) compose -f examples/podman/docker-compose.yml

example-clean: ## Clean all example Docker/Podman resources
	@echo "$(YELLOW)Cleaning example resources...$(NC)"
	-@docker compose -f examples/docker/docker-compose.yml down -v 2>/dev/null || true
	-@podman-compose -f examples/podman/docker-compose.yml down -v 2>/dev/null || true
	@echo "$(GREEN)✓ Examples cleaned$(NC)"

.DEFAULT_GOAL := help
