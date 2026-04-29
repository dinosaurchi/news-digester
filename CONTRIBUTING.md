# Contributing to SME News Admin

First off, thank you for considering a contribution! SME News Admin is a full-stack admin dashboard for managing AI-powered news intelligence workspaces. We welcome bug fixes, features, documentation improvements, and ideas.

## Getting Started

### Prerequisites

| Tool | Version |
|------|---------|
| [Node.js](https://nodejs.org/) | 18+ (CI uses 20) |
| [Python](https://www.python.org/) | 3.11+ (CI uses 3.12) |
| [Docker](https://www.docker.com/) | Latest stable |
| [Docker Compose](https://docs.docker.com/compose/) | v2+ |
| [Git](https://git-scm.com/) | 2.x |

### Clone and Configure

```bash
git clone https://github.com/dinosaurchi/sme-news-admin.git
cd sme-news-admin
cp .env.example .env       # create your local env file
npm ci                     # install frontend dependencies
```

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

## Development Setup

### Frontend (React + Vite)

```bash
make dev          # starts Vite dev server with hot reload
# or
npm run dev
```

The frontend runs at [http://localhost:3000](http://localhost:3000) by default.

### Backend (FastAPI)

```bash
make backend      # starts uvicorn with auto-reload on port 8000
```

API docs are available at [http://localhost:8000/api/docs](http://localhost:8000/api/docs).

### Full Stack with Docker

```bash
make up           # build and start all services
make logs         # stream container logs
make down         # stop all services
```

This spins up PostgreSQL, Redis, the backend, Celery worker/beat, the frontend, and supporting infrastructure.

### Database

```bash
make db-migrate   # run pending Alembic migrations
make db-seed      # seed initial data
```

### Useful Make Targets

| Target | Description |
|--------|-------------|
| `make dev` | Start the Vite dev server |
| `make backend` | Start the FastAPI server with reload |
| `make worker` | Start the Celery worker |
| `make beat` | Start the Celery beat scheduler |
| `make install` | Install frontend dependencies (`npm ci`) |
| `make clean` | Remove `dist/`, `node_modules/`, `.vite` |

## Development Workflow

### Branch Naming

Create a branch from `main` using one of these prefixes:

- `feat/` — new features (`feat/add-workspace-export`)
- `fix/` — bug fixes (`fix/feed-sort-order`)
- `docs/` — documentation changes (`docs/update-readme`)
- `refactor/` — code refactoring without behavior changes
- `test/` — adding or updating tests
- `chore/` — maintenance tasks

### Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): short description

optional longer description
```

Common types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`.

Examples:

```
feat(feeds): add RSS feed validation endpoint
fix(auth): resolve session expiry redirect loop
docs: update contributing guide
```

### Pull Request Process

1. **Fork** the repository (or create a branch if you have push access).
2. **Create a feature branch** from `main`.
3. **Make your changes** with clear, focused commits.
4. **Add or update tests** for any changed behavior.
5. **Run the full CI suite** locally before pushing:

   ```bash
   make ci
   ```

6. **Open a pull request** against the `main` branch.
7. Ensure all CI checks pass on the PR.

## Code Style

### Frontend (TypeScript / React)

- **ESLint** — run with `make lint` or `npm run lint`
- **TypeScript strict mode** — `strict: true` is enabled in `tsconfig.json`; run `make typecheck` or `npx tsc --noEmit` to verify
- **Formatting** — follow the existing code style in the repository; keep formatting consistent with surrounding code

### Backend (Python / FastAPI)

- Follow [PEP 8](https://peps.python.org/pep-0008/) conventions
- Keep functions focused and modules organized by domain (see `backend/app/` structure)
- Use type hints for function signatures

## Testing

### Run the Full Suite

```bash
make ci
```

This runs linting, type checking, frontend tests, the production build, and backend tests — the same pipeline that CI enforces.

### Frontend Tests (Vitest)

```bash
make test              # single run
make test-watch        # watch mode
# or directly
npm run test -- --run  # single run
npm run test           # watch mode
```

Frontend tests are located alongside source files or in `src/` directories with `*.test.ts(x)` naming.

### Backend Tests (pytest)

```bash
make backend-test
# or directly
cd backend && python -m pytest
```

Backend tests live in `backend/app/tests/`. Tests use an in-memory SQLite database and set `TESTING=1` to skip auto-migrations.

### Integration Tests

```bash
make integration-test
```

These run from `tests/integration/` and exercise cross-cutting scenarios.

### Writing New Tests

- **Frontend**: use [Vitest](https://vitest.dev/) and [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/). Place test files next to the module they cover, named `<module>.test.ts(x)`.
- **Backend**: use [pytest](https://docs.pytest.org/). Add test files to `backend/app/tests/` following the `test_*.py` naming convention. Fixtures and helpers belong in `conftest.py`.

## Pull Request Checklist

Before submitting a PR, verify:

- [ ] `make ci` passes locally with no errors
- [ ] New code includes tests covering the happy path and edge cases
- [ ] Existing tests still pass — no regressions
- [ ] Linting and type checking are clean (`make lint && make typecheck`)
- [ ] Commit messages follow conventional commit format
- [ ] No secrets, `.env` files, or data files are committed
- [ ] Documentation updated if behavior changed (README, docstrings, etc.)

## Reporting Bugs

Open an issue at [github.com/dinosaurchi/sme-news-admin/issues](https://github.com/dinosaurchi/sme-news-admin/issues) with:

- A clear, descriptive title
- Steps to reproduce
- Expected vs. actual behavior
- Relevant logs, screenshots, or error messages
- Environment details (OS, Node.js version, Python version, Docker version)

## Questions

- **Bug reports and feature requests**: [GitHub Issues](https://github.com/dinosaurchi/sme-news-admin/issues)
- **Pull requests**: [GitHub Pull Requests](https://github.com/dinosaurchi/sme-news-admin/pulls)

---

Thank you for contributing to SME News Admin! Your effort helps make this project better for everyone.
