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

### prelude_index_maintenance.py
Audits critical Prelude database indexes and creates any that are missing.

```bash
# Show current index status
uv run python -m app.scripts.prelude_index_maintenance check

# Create any missing indexes (with confirmation)
uv run python -m app.scripts.prelude_index_maintenance apply

# Non-interactive creation
uv run python -m app.scripts.prelude_index_maintenance apply --yes
```

### prelude_pair_accelerator.py
Installs and manages the Prebetter_Pair accelerator (pair hash) for faster grouped
count/list queries without heavy joins.

```bash
# Install table + triggers
uv run python -m app.scripts.prelude_pair_accelerator install

# Backfill the last 7 days
uv run python -m app.scripts.prelude_pair_accelerator backfill-days --days 7

# Backfill an explicit window
uv run python -m app.scripts.prelude_pair_accelerator backfill --start 2025-09-22T22:00:00Z --end 2025-09-30T21:59:59Z

# Check status
uv run python -m app.scripts.prelude_pair_accelerator status

# Remove triggers (and optionally table)
uv run python -m app.scripts.prelude_pair_accelerator uninstall
uv run python -m app.scripts.prelude_pair_accelerator uninstall --drop-table
```

## Security Notes

- No default credentials are created automatically
- Passwords must be at least 8 characters
- Superuser accounts have full admin privileges
