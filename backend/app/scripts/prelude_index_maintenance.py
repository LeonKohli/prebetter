"""Prelude database index maintenance utility.

This script audits and enforces critical indexes on Prelude database tables
to ensure optimal query performance for the Prebetter IDS dashboard.

Usage:
    uv run python -m app.scripts.prelude_index_maintenance [COMMAND]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import typer
from sqlalchemy import text

from app.database.config import prelude_engine

app = typer.Typer(
    help="Prelude index maintenance", no_args_is_help=True, add_completion=False
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequiredIndex:
    table: str
    name: str
    create_sql: str


REQUIRED_INDEXES: tuple[RequiredIndex, ...] = (
    RequiredIndex(
        table="Prelude_Address",
        name="idx_parent_index_msg",
        create_sql=(
            "ALTER TABLE Prelude_Address "
            "ADD INDEX idx_parent_index_msg "
            "(_parent_type, _index, _parent0_index, _message_ident, category, address(32))"
        ),
    ),
    RequiredIndex(
        table="Prelude_DetectTime",
        name="idx_dt_time_ident_gmtoff",
        create_sql=(
            "CREATE INDEX idx_dt_time_ident_gmtoff "
            "ON Prelude_DetectTime(time, _message_ident, gmtoff)"
        ),
    ),
)


def _get_existing_index_names(conn, table: str) -> set[str]:
    """Get all existing index names for a table.

    Args:
        conn: Database connection
        table: Table name to check

    Returns:
        Set of index names
    """
    query = text(
        "SELECT index_name FROM information_schema.statistics "
        "WHERE table_schema = DATABASE() AND table_name = :table"
    )
    rows = conn.execute(query, {"table": table}).all()
    return {row[0] for row in rows}


def _missing_indexes(conn) -> list[RequiredIndex]:
    """Identify which required indexes are missing.

    Args:
        conn: Database connection

    Returns:
        List of missing RequiredIndex objects
    """
    missing: list[RequiredIndex] = []
    cache: dict[str, set[str]] = {}

    for index in REQUIRED_INDEXES:
        if index.table not in cache:
            cache[index.table] = _get_existing_index_names(conn, index.table)
        if index.name not in cache[index.table]:
            missing.append(index)

    return missing


@app.command()
def check() -> None:
    """Check for missing required indexes.

    Lists all required indexes and identifies which ones are missing
    from the Prelude database.
    """
    try:
        with prelude_engine.connect() as conn:
            missing = _missing_indexes(conn)

        if not missing:
            typer.secho(
                "✓ All required Prelude indexes are present.",
                fg=typer.colors.GREEN,
                bold=True,
            )
            typer.echo(f"\nTotal indexes checked: {len(REQUIRED_INDEXES)}")
            return

        typer.secho(
            f"⚠ Missing Prelude indexes ({len(missing)}):",
            fg=typer.colors.YELLOW,
            bold=True,
        )
        for index in missing:
            typer.echo(f"  • {index.table}.{index.name}")

        typer.echo("\nRun 'apply' command to create missing indexes.")

    except Exception as e:
        logger.error(f"Index check failed: {e}")
        typer.secho(f"✗ Index check failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def apply(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Create any missing required indexes.

    This command will create all missing indexes that are declared as required
    by this utility. Index creation may take time on large tables.
    """
    try:
        with prelude_engine.begin() as conn:
            missing = _missing_indexes(conn)

            if not missing:
                typer.secho(
                    "✓ All required Prelude indexes are already present.",
                    fg=typer.colors.GREEN,
                    bold=True,
                )
                return

            typer.secho(
                f"The following {len(missing)} index(es) will be created:",
                fg=typer.colors.CYAN,
                bold=True,
            )
            for index in missing:
                typer.echo(f"  • {index.table}.{index.name}")

            if not yes:
                typer.echo(
                    "\nNote: Index creation may take several minutes on large tables."
                )
                confirm = typer.confirm("Proceed with index creation?", default=False)
                if not confirm:
                    typer.echo("Cancelled.")
                    raise typer.Exit(code=0)

            typer.echo()
            for idx, index in enumerate(missing, 1):
                typer.echo(
                    f"[{idx}/{len(missing)}] Creating {index.table}.{index.name} ... ",
                    nl=False,
                )
                conn.execute(text(index.create_sql))
                typer.secho("done", fg=typer.colors.GREEN)

        typer.echo()
        typer.secho(
            f"✓ Index creation complete! Created {len(missing)} index(es).",
            fg=typer.colors.GREEN,
            bold=True,
        )

    except Exception as e:
        logger.error(f"Index creation failed: {e}")
        typer.secho(f"\n✗ Index creation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def list() -> None:
    """List all required indexes defined by this utility.

    Shows the complete list of indexes that this utility manages,
    regardless of whether they are currently present or missing.
    """
    typer.secho(
        f"Required Prelude indexes ({len(REQUIRED_INDEXES)}):",
        fg=typer.colors.CYAN,
        bold=True,
    )

    for idx, index in enumerate(REQUIRED_INDEXES, 1):
        typer.echo(f"\n[{idx}] {index.table}.{index.name}")
        typer.echo(f"    SQL: {index.create_sql}")


def main() -> None:
    """Entry point for the script."""
    logging.basicConfig(level=logging.INFO)
    app()


if __name__ == "__main__":
    main()
