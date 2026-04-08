.PHONY: lint typecheck test build ci dev up down logs clean install backend backend-test db-migrate db-seed

# Default target
all: lint build test

# CI target — runs lint, typecheck, test, and build
ci: lint typecheck test build backend-test

# Install dependencies
install:
	npm ci

# Run the Vite dev server
dev:
	npm run dev

# Lint the codebase
lint:
	npm run lint

# Type-check
typecheck:
	npx tsc --noEmit

# Run tests
test:
	npm run test -- --run

# Run tests in watch mode
test-watch:
	npm run test

# Build the production bundle
build:
	npm run build

# Build and start with docker-compose
up:
	docker compose up --build -d

# Stop docker-compose
down:
	docker compose down

# View docker-compose logs
logs:
	docker compose logs -f

# Clean build artifacts and dependencies
clean:
	rm -rf dist node_modules .vite

# Run backend locally (uvicorn with reload)
backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run backend pytest
backend-test:
	cd backend && python -m pytest

# Run alembic upgrade head
db-migrate:
	cd backend && alembic upgrade head

# Run seed script
db-seed:
	cd backend && python -m app.seed
