# Prebetter

Prebetter is a dashboard for Snort IDS alerts stored in OpenSearch. Nuxt serves the UI and owns authentication through Better Auth. FastAPI verifies Better Auth JWTs and reads alerts from OpenSearch; it never writes.

## Work by component

- For frontend changes, read [frontend/CLAUDE.md](frontend/CLAUDE.md).
- For backend changes, read [backend/CLAUDE.md](backend/CLAUDE.md).
- For installation and verification, use [README.md](README.md) and the component READMEs.
- Use Bun for JavaScript and uv for Python. Keep both lockfiles in the commit when dependencies change.

## Contracts

- Browser requests use Nuxt `/api/*` routes. The API proxy obtains a JWT from the Better Auth session and forwards it to FastAPI.
- Better Auth owns login, sessions, password management, and user administration. Its schema lives in the Prebetter MySQL database, which only the frontend uses.
- FastAPI verifies the JWT signature, issuer, audience, and subject through Better Auth's JWKS endpoint. Keep `BETTER_AUTH_URL` consistent between components.
- Alerts live in daily OpenSearch indices with a strict mapping that the ingest pipeline owns. `backend/tests/index_template.json` is a copy of that mapping; a field the backend reads must exist there and in the pipeline first.
- The request line of an HTTP alert lives in a companion document in a second set of daily indices (`OPENSEARCH_REQUEST_INDEX`, mapping copy in `backend/tests/requests_template.json`), keyed by a hash of the alert's identity fields (`backend/app/opensearch/request_line.py`).
- Response field names (`source_ipv4`, `classification_text`, `analyzer`) are the frontend's names. `backend/app/opensearch/documents.py` is the one place that maps them to document fields; `frontend/shared/types/alerts.ts` mirrors the responses.
- Session lifetime and JWT lifetime are configured in `frontend/server/utils/auth.ts`.
- Provision the Better Auth schema explicitly. Application startup installs nothing.

## Verification

Run the relevant checks documented in each component README. Backend tests need a disposable OpenSearch node (`compose.opensearch.yml`) and an index pattern that starts with `prebetter-test-`. Frontend end-to-end tests need a disposable auth database.

This repository is public. Keep real hostnames, addresses, and credentials out of code, tests, fixtures, and documentation.
