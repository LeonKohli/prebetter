# Prebetter

Prebetter is a Prelude IDS dashboard. Nuxt serves the UI and owns authentication through Better Auth. FastAPI verifies Better Auth JWTs and serves IDS data from MySQL.

## Work by component

- For frontend changes, read [frontend/CLAUDE.md](frontend/CLAUDE.md).
- For backend changes, read [backend/CLAUDE.md](backend/CLAUDE.md).
- For installation and verification, use [README.md](README.md) and the component READMEs.
- Use Bun for JavaScript and uv for Python. Keep both lockfiles in the commit when dependencies change.

## Contracts

- Browser requests use Nuxt `/api/*` routes. The API proxy obtains a JWT from the Better Auth session and forwards it to FastAPI.
- Better Auth owns login, sessions, password management, and user administration. Its schema lives in the Prebetter database.
- FastAPI verifies the JWT signature, issuer, audience, and subject through Better Auth's JWKS endpoint. Keep `BETTER_AUTH_URL` consistent between components.
- The Prelude database contains IDS data and the required `Prebetter_Pair` accelerator. Alert deletion and maintenance write to this database.
- Session lifetime and JWT lifetime are configured in `frontend/server/utils/auth.ts`.
- Provision schemas explicitly. Application startup does not install Better Auth tables or the Prelude accelerator.

## Verification

Run the relevant checks documented in each component README. Database tests need disposable databases; backend fixtures execute DDL before their rollback-protected seed transactions.
