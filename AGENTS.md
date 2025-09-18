# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: FastAPI API (`app/` routes, services, middleware, database). Tests in `backend/tests/`.
- `frontend/`: Nuxt 4 + Vue 3 app. Components in `frontend/app/components/`, composables in `frontend/app/composables/`, public assets in `frontend/public/`. Tests in `frontend/test/`.
- CI: Ruff lint in `.github/workflows/ruff.yml`. Additional docs in `README.md`, `backend/README.md`, and `CLAUDE.md`.

## Build, Test, and Development Commands
- Backend
  - Install/run: `cd backend && uv sync && fastapi dev` (hot-reload).
  - Tests: `uv run pytest --cov` (pytest + asyncio strict mode).
  - Lint/format: `ruff check .` and `ruff format .`.
- Frontend
  - Install/dev: `cd frontend && bun install && bun run dev`.
  - Build/preview: `bun run build` then `bun run preview`.
  - Tests/typecheck: `bun run test` (Vitest) and `bun run typecheck` (vue-tsc).

## Coding Style & Naming Conventions
- Python (backend)
  - Indentation 4 spaces, type hints required for new code.
  - Names: `snake_case` functions/vars, `PascalCase` classes, modules lowercase.
  - Use `ruff format` and keep `ruff check` clean before pushing.
- Vue/TypeScript (frontend)
  - Components `PascalCase.vue` under `app/components/` (e.g., `Button.vue`).
  - Composables start with `use` (e.g., `useAlertTableContext.ts`).
  - Prefer `<script setup lang="ts">`; keep exports via local `index.ts` where present.

## Testing Guidelines
- Backend: place tests in `backend/tests/` as `test_*.py`; cover new routes/services and edge cases. Run `uv run pytest --cov` locally.
- Frontend: Vitest with `happy-dom`; place tests in `frontend/test/*.test.ts`. Run `bun run test`.

## Commit & Pull Request Guidelines
- Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `style:` (see `git log`).
- PRs: include a clear description, linked issues (`Closes #123`), and screenshots/GIFs for UI changes.
- CI must be green (lint, tests). Update docs when modifying APIs, routes, or config.
- Do not include “Co-Authored-By: Claude” lines in commits.

## Security & Configuration
- Backend: create `.env` with DB creds and secrets (`SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `ENVIRONMENT`, `LOG_LEVEL`).
- Frontend: copy `frontend/.env.example` to `.env` and set session/API values.
