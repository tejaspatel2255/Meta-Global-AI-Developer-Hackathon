PYTHON ?= python
FRONTEND ?= frontend

.PHONY: setup dev test test-live lint schemas eval

setup:
	$(PYTHON) -m pip install -e ".[dev]"
	cd $(FRONTEND) && npm install

dev:
	$(PYTHON) scripts/dev.py

test:
	$(PYTHON) -m pytest backend/tests -q

test-live:
	$(PYTHON) -m pytest backend/tests -m live -q

lint:
	$(PYTHON) -m ruff check backend
	$(PYTHON) -m ruff format --check backend
	$(PYTHON) -m mypy
	cd $(FRONTEND) && npx tsc --noEmit

schemas:
	$(PYTHON) -m benchguard.contracts.export_schema --out $(FRONTEND)/src/contracts

eval:
	@echo "eval harness is Phase 6"
	@exit 1
