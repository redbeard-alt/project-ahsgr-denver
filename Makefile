.DEFAULT_GOAL := help

PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

# ── setup ──────────────────────────────────────────────────────────────────

.venv:
	python3.12 -m venv .venv

install: .venv
	$(PIP) install --upgrade pip --quiet
	$(PIP) install -r requirements.txt --quiet
	@echo "✓ venv ready"

# ── AGENT_SPEC §2 required targets ─────────────────────────────────────────

## run: start the MCP server
run: .venv
	$(PYTHON) lib/ashgr_mcp_server.py

## test: run test suite
test: .venv
	$(PYTHON) -m pytest tests/ -v

## lint: run ruff linter
lint: .venv
	$(PYTHON) -m ruff check .

## clean: remove __pycache__, .venv
clean:
	find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	rm -rf .venv/
	@echo "✓ Cleaned."

## sync-identity: pull shared identity files from config-ai-agent
sync-identity:
	rsync -a $(HOME)/Laboratory/config-ai-agent/identity/ .

# ── corpus ops ─────────────────────────────────────────────────────────────

## build: rebuild docs/roster_index.csv from output/ CSVs
build: .venv
	$(PYTHON) build_roster_index.py

## build-dry: dry-run build (no writes)
build-dry: .venv
	$(PYTHON) build_roster_index.py --dry-run

# ── help ───────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "  make install     Set up venv (python3.12) + deps"
	@echo "  make run         Start FastMCP server"
	@echo "  make test        Run test suite"
	@echo "  make lint        Run ruff linter"
	@echo "  make build       Rebuild roster_index.csv from output/"
	@echo "  make build-dry   Dry-run build"
	@echo "  make clean       Remove __pycache__, .venv"
	@echo ""

.PHONY: install run test lint clean sync-identity build build-dry help
