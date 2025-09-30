"""CLI utility to audit and enforce critical Prelude DB indexes."""

from __future__ import annotations

import typer
from dataclasses import dataclass
from typing import Iterable
from sqlalchemy import text

from app.database.config import prelude_engine

app = typer.Typer(help="Prelude index maintenance", no_args_is_help=True)


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
    query = text(
        "SELECT index_name FROM information_schema.statistics "
        "WHERE table_schema = :schema AND table_name = :table"
    )
    rows = conn.execute(query, {"schema": "prelude", "table": table}).all()
    return {row[0] for row in rows}


def _missing_indexes(conn) -> list[RequiredIndex]:
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
    """List required indexes and show which ones are missing."""
    with prelude_engine.connect() as conn:
        missing = _missing_indexes(conn)

    if not missing:
        typer.secho("All required Prelude indexes are present.", fg=typer.colors.GREEN)
        return

    typer.secho("Missing Prelude indexes:", fg=typer.colors.YELLOW)
    for index in missing:
        typer.echo(f"- {index.table}.{index.name}")


@app.command()
def apply(yes: bool = typer.Option(False, "--yes", help="Apply without confirmation.")) -> None:
    """Create any missing indexes declared by this utility."""
    with prelude_engine.begin() as conn:
        missing = _missing_indexes(conn)
        if not missing:
            typer.secho("All required Prelude indexes are already present.", fg=typer.colors.GREEN)
            return

        typer.secho("The following indexes will be created:", fg=typer.colors.YELLOW)
        for index in missing:
            typer.echo(f"- {index.table}.{index.name}")

        if not yes:
            confirm = typer.confirm("Proceed with index creation?", default=False)
            if not confirm:
                typer.echo("Aborted.")
                return

        for index in missing:
            typer.echo(f"Creating {index.table}.{index.name} ...", nl=False)
            conn.execute(text(index.create_sql))
            typer.echo(" done.")

    typer.secho("Index creation complete.", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
