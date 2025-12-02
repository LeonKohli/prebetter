"""Prebetter_Pair accelerator for Prelude IDS database.

This utility creates a helper table and triggers that maintain a canonical
source/target IP pair per message, enabling fast grouped list/count queries
without heavy joins. It can also backfill data for a given time window.

Usage:
    uv run python -m app.scripts.prelude_pair_accelerator [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import typer
from sqlalchemy import text

from app.database.config import prelude_engine

app = typer.Typer(
    help="Prelude pair accelerator", no_args_is_help=True, add_completion=False
)
logger = logging.getLogger(__name__)


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS Prebetter_Pair (
  _message_ident BIGINT PRIMARY KEY,
  source_ip INT UNSIGNED NOT NULL,
  target_ip INT UNSIGNED NOT NULL,
  pair_key BIGINT UNSIGNED AS (source_ip * 4294967296 + target_ip) PERSISTENT,
  KEY idx_pair_key (pair_key),
  KEY idx_source (source_ip),
  KEY idx_target (target_ip)
) ENGINE=InnoDB;
"""


TRIGGER_AI_SQL = """
CREATE TRIGGER prebetter_pair_ai AFTER INSERT ON Prelude_Address
FOR EACH ROW
BEGIN
  DECLARE s INT UNSIGNED;
  DECLARE t INT UNSIGNED;
  SET s = NULL; SET t = NULL;

  IF NEW.category = 'ipv4-addr' AND NEW._index = -1 AND NEW._parent0_index = 0 THEN
    IF NEW._parent_type = 'S' THEN
      SET s = INET_ATON(NEW.address);
      SELECT INET_ATON(a.address) INTO t
        FROM Prelude_Address a
       WHERE a._message_ident = NEW._message_ident
         AND a._parent_type = 'T'
         AND a._parent0_index = 0
         AND a._index = -1
         AND a.category = 'ipv4-addr'
       LIMIT 1;
    ELSEIF NEW._parent_type = 'T' THEN
      SET t = INET_ATON(NEW.address);
      SELECT INET_ATON(a.address) INTO s
        FROM Prelude_Address a
       WHERE a._message_ident = NEW._message_ident
         AND a._parent_type = 'S'
         AND a._parent0_index = 0
         AND a._index = -1
         AND a.category = 'ipv4-addr'
       LIMIT 1;
    END IF;

    IF s IS NOT NULL AND t IS NOT NULL THEN
      INSERT IGNORE INTO Prebetter_Pair(_message_ident, source_ip, target_ip)
      VALUES (NEW._message_ident, s, t);
    END IF;
  END IF;
END;
"""


TRIGGER_AU_SQL = """
CREATE TRIGGER prebetter_pair_au AFTER UPDATE ON Prelude_Address
FOR EACH ROW
BEGIN
  DECLARE s INT UNSIGNED;
  DECLARE t INT UNSIGNED;
  SET s = NULL; SET t = NULL;

  IF NEW.category = 'ipv4-addr' AND NEW._index = -1 AND NEW._parent0_index = 0 THEN
    IF NEW._parent_type = 'S' THEN
      SET s = INET_ATON(NEW.address);
      SELECT INET_ATON(a.address) INTO t
        FROM Prelude_Address a
       WHERE a._message_ident = NEW._message_ident
         AND a._parent_type = 'T'
         AND a._parent0_index = 0
         AND a._index = -1
         AND a.category = 'ipv4-addr'
       LIMIT 1;
    ELSEIF NEW._parent_type = 'T' THEN
      SET t = INET_ATON(NEW.address);
      SELECT INET_ATON(a.address) INTO s
        FROM Prelude_Address a
       WHERE a._message_ident = NEW._message_ident
         AND a._parent_type = 'S'
         AND a._parent0_index = 0
         AND a._index = -1
         AND a.category = 'ipv4-addr'
       LIMIT 1;
    END IF;

    IF s IS NOT NULL AND t IS NOT NULL THEN
      INSERT IGNORE INTO Prebetter_Pair(_message_ident, source_ip, target_ip)
      VALUES (NEW._message_ident, s, t);
    END IF;
  END IF;
END;
"""


# Delete trigger on Prelude_Alert to automatically clean up Prebetter_Pair
# This prevents stale cache entries when alerts are deleted outside the app
TRIGGER_AD_SQL = """
CREATE TRIGGER prebetter_pair_ad AFTER DELETE ON Prelude_Alert
FOR EACH ROW
BEGIN
  DELETE FROM Prebetter_Pair WHERE _message_ident = OLD._ident;
END;
"""


def _drop_triggers(conn) -> None:
    """Drop existing pair accelerator triggers.

    Args:
        conn: Database connection
    """
    conn.execute(text("DROP TRIGGER IF EXISTS prebetter_pair_ai"))
    conn.execute(text("DROP TRIGGER IF EXISTS prebetter_pair_au"))
    conn.execute(text("DROP TRIGGER IF EXISTS prebetter_pair_ad"))


@app.command()
def install() -> None:
    """Create Prebetter_Pair table and install triggers.

    This creates the helper table and database triggers that automatically
    maintain source/target IP pairs for each message. Includes:
    - AFTER INSERT on Prelude_Address: populate cache for new alerts
    - AFTER UPDATE on Prelude_Address: update cache on IP changes
    - AFTER DELETE on Prelude_Alert: clean cache when alerts are deleted
    """
    try:
        with prelude_engine.begin() as conn:
            typer.echo("Creating Prebetter_Pair table...")
            conn.execute(text(CREATE_TABLE_SQL))

            typer.echo("Installing triggers...")
            _drop_triggers(conn)
            conn.execute(text(TRIGGER_AI_SQL))
            conn.execute(text(TRIGGER_AU_SQL))
            conn.execute(text(TRIGGER_AD_SQL))

        typer.secho(
            "✓ Prebetter_Pair installed successfully (table + 3 triggers)",
            fg=typer.colors.GREEN,
            bold=True,
        )

    except Exception as e:
        logger.error(f"Installation failed: {e}")
        typer.secho(f"✗ Installation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def uninstall(
    drop_table: bool = typer.Option(
        False, "--drop-table", help="Also drop the Prebetter_Pair table"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Remove triggers and optionally drop the helper table.

    By default, only triggers are removed. Use --drop-table to also
    remove the Prebetter_Pair table and all its data.
    """
    if drop_table and not yes:
        confirm = typer.confirm(
            "This will delete the Prebetter_Pair table and all data. Continue?",
            default=False,
        )
        if not confirm:
            typer.echo("Cancelled.")
            raise typer.Exit(code=0)

    try:
        with prelude_engine.begin() as conn:
            typer.echo("Removing triggers...")
            _drop_triggers(conn)

            if drop_table:
                typer.echo("Dropping table...")
                conn.execute(text("DROP TABLE IF EXISTS Prebetter_Pair"))

        message = "✓ Triggers removed"
        if drop_table:
            message += " and table dropped"

        typer.secho(message, fg=typer.colors.YELLOW, bold=True)

    except Exception as e:
        logger.error(f"Uninstall failed: {e}")
        typer.secho(f"✗ Uninstall failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def backfill(
    start: datetime = typer.Option(..., "--start", help="Start datetime (ISO format)"),
    end: datetime = typer.Option(..., "--end", help="End datetime (ISO format)"),
) -> None:
    """Backfill Prebetter_Pair for a date range.

    This command populates the Prebetter_Pair table with historical data
    for the specified time range. It is idempotent - running it multiple
    times will not create duplicates.
    """
    typer.echo(f"Backfilling from {start:%Y-%m-%d %H:%M:%S} to {end:%Y-%m-%d %H:%M:%S}")

    sql = text(
        """
        INSERT IGNORE INTO Prebetter_Pair (_message_ident, source_ip, target_ip)
        SELECT dt._message_ident,
               INET_ATON(sa.address) AS s,
               INET_ATON(ta.address) AS t
        FROM Prelude_DetectTime AS dt
        JOIN Prelude_Source  AS src ON src._message_ident = dt._message_ident AND src._index = 0
        JOIN Prelude_Target  AS tgt ON tgt._message_ident = dt._message_ident AND tgt._index = 0
        LEFT JOIN Prelude_Address AS sa ON sa._message_ident = dt._message_ident AND sa._parent_type='S' AND sa._parent0_index=src._index AND sa._index=-1 AND sa.category='ipv4-addr'
        LEFT JOIN Prelude_Address AS ta ON ta._message_ident = dt._message_ident AND ta._parent_type='T' AND ta._parent0_index=tgt._index AND ta._index=-1 AND ta.category='ipv4-addr'
        WHERE sa.address IS NOT NULL AND ta.address IS NOT NULL
          AND dt.time BETWEEN :start AND :end
        """
    )

    try:
        with prelude_engine.begin() as conn:
            conn.execute(sql, {"start": start, "end": end})
            # result.rowcount may be -1 for INSERT IGNORE; fetch affected with ROW_COUNT()
            inserted = conn.execute(text("SELECT ROW_COUNT() AS inserted")).scalar()

        typer.secho(
            f"✓ Backfill complete. Inserted ~{inserted:,} rows.",
            fg=typer.colors.GREEN,
            bold=True,
        )

    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        typer.secho(f"✗ Backfill failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def backfill_days(
    days: int = typer.Option(
        7, "--days", "-d", min=1, max=365, help="Number of days to backfill"
    ),
) -> None:
    """Backfill Prebetter_Pair for the last N days.

    Convenience command to backfill recent data without specifying
    exact start and end dates.
    """
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    typer.echo(f"Backfilling last {days} day(s)")
    backfill(start=start, end=end)


@app.command()
def status() -> None:
    """Check Prebetter_Pair installation status.

    Shows whether the table exists and provides statistics about
    the number of pairs stored.
    """
    try:
        with prelude_engine.connect() as conn:
            # Check if table exists
            exists = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name = 'Prebetter_Pair'"
                )
            ).scalar()

            if not exists:
                typer.secho(
                    "✗ Prebetter_Pair table not found", fg=typer.colors.RED, bold=True
                )
                typer.echo("Run 'install' command to create the table and triggers")
                raise typer.Exit(code=1)

            # Get row count
            row_count = conn.execute(
                text("SELECT COUNT(*) FROM Prebetter_Pair")
            ).scalar()

            # Check triggers
            triggers = conn.execute(
                text(
                    "SELECT trigger_name FROM information_schema.triggers "
                    "WHERE trigger_schema = DATABASE() "
                    "AND trigger_name IN ('prebetter_pair_ai', 'prebetter_pair_au', 'prebetter_pair_ad')"
                )
            ).fetchall()

            trigger_names = {t[0] for t in triggers}

            typer.secho("✓ Prebetter_Pair Status", fg=typer.colors.GREEN, bold=True)
            typer.echo("\nTable: Present")
            typer.echo(f"Rows: {row_count:,}")
            typer.echo("\nTriggers:")
            typer.echo(
                f"  • prebetter_pair_ai (INSERT): {'✓' if 'prebetter_pair_ai' in trigger_names else '✗ Missing'}"
            )
            typer.echo(
                f"  • prebetter_pair_au (UPDATE): {'✓' if 'prebetter_pair_au' in trigger_names else '✗ Missing'}"
            )
            typer.echo(
                f"  • prebetter_pair_ad (DELETE): {'✓' if 'prebetter_pair_ad' in trigger_names else '✗ Missing'}"
            )

            if len(trigger_names) < 3:
                typer.secho(
                    "\n⚠ Some triggers are missing. Run 'install' to fix.",
                    fg=typer.colors.YELLOW,
                )

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        typer.secho(f"✗ Status check failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def cleanup(
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show orphans without deleting"
    ),
) -> None:
    """Remove orphaned entries from Prebetter_Pair cache.

    Finds and removes cache entries that reference alerts which no longer
    exist in Prelude_Alert. This handles stale data from alerts deleted
    outside the application (e.g., direct database operations).

    Use --dry-run to preview without making changes.
    """
    try:
        with prelude_engine.begin() as conn:
            # Count orphans first
            count_sql = text("""
                SELECT COUNT(*)
                FROM Prebetter_Pair pp
                LEFT JOIN Prelude_Alert pa ON pp._message_ident = pa._ident
                WHERE pa._ident IS NULL
            """)
            orphan_count = conn.execute(count_sql).scalar() or 0

            if orphan_count == 0:
                typer.secho(
                    "✓ No orphaned cache entries found",
                    fg=typer.colors.GREEN,
                    bold=True,
                )
                return

            typer.echo(f"Found {orphan_count:,} orphaned cache entries")

            if dry_run:
                typer.secho(
                    f"⚠ Dry run: would delete {orphan_count:,} rows",
                    fg=typer.colors.YELLOW,
                )
                # Show sample of orphaned IDs
                sample_sql = text("""
                    SELECT pp._message_ident
                    FROM Prebetter_Pair pp
                    LEFT JOIN Prelude_Alert pa ON pp._message_ident = pa._ident
                    WHERE pa._ident IS NULL
                    LIMIT 10
                """)
                samples = [row[0] for row in conn.execute(sample_sql).fetchall()]
                if samples:
                    typer.echo(f"Sample orphan IDs: {samples}")
                return

            # Delete orphans
            delete_sql = text("""
                DELETE pp FROM Prebetter_Pair pp
                LEFT JOIN Prelude_Alert pa ON pp._message_ident = pa._ident
                WHERE pa._ident IS NULL
            """)
            conn.execute(delete_sql)

            typer.secho(
                f"✓ Deleted {orphan_count:,} orphaned cache entries",
                fg=typer.colors.GREEN,
                bold=True,
            )

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        typer.secho(f"✗ Cleanup failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the script."""
    logging.basicConfig(level=logging.INFO)
    app()


if __name__ == "__main__":
    main()
