# diary-md Makefile

.PHONY: help install dev test lint clean install-completion install-completion-user install-completion-system

PYTHON ?= python3
VENV = venv
COMPLETION_DIR_USER = $(HOME)/.local/share/bash-completion/completions
COMPLETION_DIR_SYSTEM = /usr/share/bash-completion/completions

help:
	@echo "diary-md - Tools for markdown-based diary entries"
	@echo ""
	@echo "Development:"
	@echo "  make install                       Install package"
	@echo "  make dev                           Install in development mode"
	@echo "  make test                          Run tests"
	@echo "  make lint                          Run linter"
	@echo "  make clean                         Clean build artifacts"
	@echo ""
	@echo "Shell Completion:"
	@echo "  make install-completion            Enable tab completion (user-local)"
	@echo "  sudo make install-completion-system  Enable tab completion (system-wide)"

# Create virtual environment
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		$(VENV)/bin/pip install --upgrade pip; \
	fi

# Install package
install: venv
	@$(VENV)/bin/pip install .

# Install in development mode
dev: venv
	@echo "Installing in development mode..."
	@$(VENV)/bin/pip install -e ".[dev]"
	@echo ""
	@echo "Installed! Commands available:"
	@echo "  $(VENV)/bin/diary-digest --help"
	@echo "  $(VENV)/bin/diary-update --help"
	@echo "  $(VENV)/bin/diary-reconcile --help"

# Run tests
test: venv
	@$(VENV)/bin/pip install -e ".[dev]" 2>/dev/null || true
	@$(VENV)/bin/pytest tests/ -v

# Run linter
lint: venv
	@$(VENV)/bin/pip install -e ".[dev]" 2>/dev/null || true
	@$(VENV)/bin/ruff check .

# Clean build artifacts
clean:
	@rm -rf $(VENV) build dist *.egg-info src/*.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Shell Tab Completion (click-based)
# =============================================================================

install-completion: install-completion-user

install-completion-user:
	@echo "Installing shell completion for current user..."
	@mkdir -p "$(COMPLETION_DIR_USER)"
	@_DIARY_DIGEST_COMPLETE=bash_source diary-digest > "$(COMPLETION_DIR_USER)/diary-digest" 2>/dev/null || \
		$(VENV)/bin/python -c "import click; from diary_md.cli.digest import digest; print(click.shell_completion.get_completion_class('bash')(digest, {}, 'diary-digest', '_DIARY_DIGEST_COMPLETE').source())" > "$(COMPLETION_DIR_USER)/diary-digest"
	@_DIARY_UPDATE_COMPLETE=bash_source diary-update > "$(COMPLETION_DIR_USER)/diary-update" 2>/dev/null || \
		$(VENV)/bin/python -c "import click; from diary_md.cli.update import update; print(click.shell_completion.get_completion_class('bash')(update, {}, 'diary-update', '_DIARY_UPDATE_COMPLETE').source())" > "$(COMPLETION_DIR_USER)/diary-update"
	@_DIARY_RECONCILE_COMPLETE=bash_source diary-reconcile > "$(COMPLETION_DIR_USER)/diary-reconcile" 2>/dev/null || \
		$(VENV)/bin/python -c "import click; from diary_md.cli.reconcile import reconcile; print(click.shell_completion.get_completion_class('bash')(reconcile, {}, 'diary-reconcile', '_DIARY_RECONCILE_COMPLETE').source())" > "$(COMPLETION_DIR_USER)/diary-reconcile"
	@echo "Completion scripts installed to $(COMPLETION_DIR_USER)/"
	@echo "Restart your shell or run: source $(COMPLETION_DIR_USER)/diary-digest"

install-completion-system:
	@echo "Installing shell completion system-wide..."
	@_DIARY_DIGEST_COMPLETE=bash_source diary-digest > "$(COMPLETION_DIR_SYSTEM)/diary-digest"
	@_DIARY_UPDATE_COMPLETE=bash_source diary-update > "$(COMPLETION_DIR_SYSTEM)/diary-update"
	@_DIARY_RECONCILE_COMPLETE=bash_source diary-reconcile > "$(COMPLETION_DIR_SYSTEM)/diary-reconcile"
	@echo "Completion scripts installed to $(COMPLETION_DIR_SYSTEM)/"
