# Dev convenience. See README.md for first-time setup.
.PHONY: help setup setup-backend setup-frontend backend frontend seed seed-pools test build docker

help:
	@echo "Targets:"
	@echo "  make setup         install backend venv + frontend deps"
	@echo "  make dev           run BOTH servers together (Ctrl+C stops both)"
	@echo "  make backend       run the API at :8000 (reload)"
	@echo "  make frontend      run the Vite dev server at :5173"
	@echo "  make seed          create the student"
	@echo "  make seed-pools    generate Week 1 Days 1-3 pools (needs ANTHROPIC_API_KEY)"
	@echo "  make test          run the backend test suite"
	@echo "  make docker        build + run the single container (needs root .env)"

setup: setup-backend setup-frontend

setup-backend:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt

setup-frontend:
	cd frontend && npm install

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload

frontend:
	cd frontend && npm run dev

# Run backend (:8000) and frontend (:5173) together; Ctrl+C stops both.
dev:
	@echo "▶ backend :8000  +  frontend :5173   (Ctrl+C stops both)"
	@trap 'kill 0' EXIT INT TERM; \
	  ( cd backend && . .venv/bin/activate && exec uvicorn app.main:app --reload ) & \
	  ( cd frontend && exec npm run dev ) & \
	  wait

seed:
	cd backend && . .venv/bin/activate && python seed.py

seed-pools:
	cd backend && . .venv/bin/activate && python seed_pools.py

test:
	cd backend && . .venv/bin/activate && pytest

build:
	cd frontend && npm run build

docker:
	docker compose up --build
