# Backend development

Read [README.md](README.md) for setup, settings, API groups, and test commands.

## API and authentication

- Add routes through `app/api/base.py` and the matching module in `app/api/v1/routes/`. Routes are `async def` and await the repository.
- Use `CurrentUser` or `CurrentSuperuser` from `app/api/deps.py` for protected operations.
- Better Auth owns users and sessions in Nuxt. FastAPI consumes verified JWT claims and does not issue access or refresh tokens.
- Deployment settings live in `app/core/config.py`. Keep `.env.example` aligned with required fields.
- Take query parameters as one model, `Annotated[Model, Query()]`. FastAPI validates it as a whole (422) but cannot combine it with other query parameters, so `AlertListParams`, `GroupListParams`, and `TimelineParams` in `app/schemas/filters.py` extend `AlertFilterParams` and `PaginationParams`.
- Use `HTTPException` for 404 and the documented 422 limits. An unreachable OpenSearch becomes 503 through the handler in `app/main.py`. Do not wrap route bodies in `except Exception`.

## OpenSearch access

- `app/repositories/alerts.py` (`AlertRepository`) is the only code that calls OpenSearch. One method per use case. It returns Pydantic models, so the untyped client responses stop there.
- `app/opensearch/queries.py` builds request bodies and does no I/O. `app/opensearch/documents.py` maps documents and buckets to response models and holds the severity labels. Keep wire names in `documents.py`.
- One `AsyncOpenSearch` client lives in `app.state.opensearch` for the app lifetime (`app/main.py` lifespan). Routes receive the repository through `Alerts` in `app/api/deps.py`.
- Put every filter in `bool.filter`. Enumerate pairs and reference lists with the `composite` helper in the repository, not with `terms`. Keep paging within the 10,000 result window.
- Use plain dict request bodies. The client has no type information, so check its documentation before using an option.
- Use timezone-aware UTC values through `app/core/datetime_utils.py`.

## Checks

```sh
docker compose -f ../compose.opensearch.yml up -d
uv run ruff check .
uv run ruff format --check .
uv run --with pyright pyright
uv run pytest
```

Tests need a node on `OPENSEARCH_URL`, and `OPENSEARCH_INDEX` and `OPENSEARCH_REQUEST_INDEX` that start with `prebetter-test-`; `tests/conftest.py` refuses anything else. It loads `.env.test`, and exported variables take precedence. `tests/seed.py` holds the shared synthetic events; extend them when a test needs a new document shape. Test behaviour against the node. Test pure functions only where a node adds nothing.
