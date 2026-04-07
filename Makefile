.PHONY: lint build test dev up down logs clean

# Default target
all: lint build test

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
