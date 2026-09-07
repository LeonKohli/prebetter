# Backend development

Read [README.md](README.md) for setup, API groups, and verification commands.

## API and authentication

- Add routes through `app/api/base.py` and the matching module in `app/api/v1/routes/`.
- Use `CurrentUser` or `CurrentSuperuser` from `app/api/deps.py` for protected operations.
- Better Auth owns users and sessions in Nuxt. FastAPI consumes verified JWT claims and does not issue access or refresh tokens.
- Deployment settings live in `app/core/config.py`. Keep environment examples aligned with required fields.

## Database work

- Use `AlertRepository` for alert queries. Keep filtering in `AlertFilterParams` and the existing query builders.
- Convert database rows through `app/database/models.py` into Pydantic response models.
- Preserve Prelude's compound join keys, including parent type and index fields. Reuse the join helpers in `app/database/config.py`.
- Use string keys for sort option dictionaries.
- Keep pagination bounded. Stream exports in batches instead of materializing the full result.
- Use timezone-aware UTC values through `app/core/datetime_utils.py`.
- The `Prebetter_Pair` accelerator is required at startup. Read [the maintenance guide](app/scripts/README.md) before changing its table, triggers, or indexes.

## Checks

Use `uv run ruff check .` and the relevant pytest tests. Run database tests only against a disposable schema. `tests/conftest.py` loads `.env.test`, creates the accelerator table, and seeds data inside rollback-protected transactions. Exported environment variables take precedence over the file.
