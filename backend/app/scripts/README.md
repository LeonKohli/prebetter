# Prebetter Management Scripts

Management commands for Prebetter.

## Available Commands

### create_user.py
Creates users for the system.

```bash
python -m app.scripts.create_user
```

The script will prompt for:
- Username
- Email
- Password (hidden input, min 8 chars)
- Whether to create as superuser (admin)

### prelude_cleanup.py
Unified maintenance command for the Prelude IDS database. Deletes alerts and
heartbeats beyond a retention window and purges orphaned heartbeat artifacts.

```bash
# Preview counts only
uv run python -m app.scripts.prelude_cleanup --dry-run

# Execute cleanup with default retention (30 days)
uv run python -m app.scripts.prelude_cleanup

# Example: keep 14 days, process smaller batches, skip orphan sweep
uv run python -m app.scripts.prelude_cleanup --retention-days 14 --batch-size 20000 --no-cleanup-orphans
```

Required environment variables:
- `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_HOST`, `MYSQL_PORT`

Optional flags:
- `--retention-days`: Days of data to retain (default 30)
- `--batch-size`: Rows processed per loop (default 50,000)
- `--no-cleanup-orphans`: Skip orphan heartbeat sweep
- `--dry-run`: Report counts without making changes

## Security Notes

- No default credentials are created automatically
- Passwords must be at least 8 characters
- Superuser accounts have full admin privileges
