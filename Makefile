SHELL := /bin/bash

.PHONY: dev

dev:
	@trap 'kill 0' SIGINT; \
	(cd backend && source .venv/bin/activate && uvicorn main:app --reload) & \
	(cd backend && source .venv/bin/activate && arq app.core.worker.WorkerSettings) & \
	(cd frontend && npm run dev) & \
	wait
