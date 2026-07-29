SHELL := /bin/bash

# Called by full path so the targets work without activating the venv.
PYTEST := backend/.venv/bin/pytest
PIP    := backend/.venv/bin/pip

.PHONY: dev test test-bugs test-cov test-install

dev:
	@trap 'kill 0' SIGINT; \
	(cd backend && source .venv/bin/activate && uvicorn main:app --reload) & \
	(cd backend && source .venv/bin/activate && arq app.core.worker.WorkerSettings) & \
	(cd frontend && npm run dev) & \
	wait

# One-time: install pytest & friends into the backend venv.
test-install:
	$(PIP) install -r backend/requirements-dev.txt

# Whole suite. Tests live in tests/ at the repo root — see tests/README.md.
test:
	$(PYTEST)

# Every bug reproduction. These PASS on purpose: they pin the wrong behaviour
# documented in BUG_REPORT.md, so a fix makes them fail.
test-bugs:
	$(PYTEST) -m bug -v

# Coverage for the three modules this suite targets.
test-cov:
	$(PYTEST) --cov=app.modules.goals --cov=app.modules.roadmap \
		--cov=app.modules.notifications --cov-report=term-missing
