"""Install and manage the Prebetter_Pair accelerator (pair hash) for Prelude.

This utility creates a helper table and triggers that maintain a canonical
source/target pair per message, enabling fast grouped list/count queries
without heavy joins. It can also backfill data for a given time window.
"""

from __future__ import annotations

import typer
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from app.database.config import prelude_engine

app = typer.Typer(help="Prelude pair accelerator", no_args_is_help=True)


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


def _drop_triggers(conn) -> None:
    conn.execute(text("DROP TRIGGER IF EXISTS prebetter_pair_ai"))
    conn.execute(text("DROP TRIGGER IF EXISTS prebetter_pair_au"))


@app.command()
def install() -> None:
    """Create Prebetter_Pair table and install triggers."""
    with prelude_engine.begin() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        _drop_triggers(conn)
        # MariaDB needs DELIMITER only in client; we send exact bodies
        conn.execute(text(TRIGGER_AI_SQL))
        conn.execute(text(TRIGGER_AU_SQL))
    typer.secho("Prebetter_Pair installed (table + triggers).", fg=typer.colors.GREEN)


@app.command()
def uninstall(drop_table: bool = typer.Option(False, help="Drop table as well")) -> None:
    """Remove triggers, optionally drop helper table."""
    with prelude_engine.begin() as conn:
        _drop_triggers(conn)
        if drop_table:
            conn.execute(text("DROP TABLE IF EXISTS Prebetter_Pair"))
    typer.secho("Prebetter_Pair triggers removed." + (" Table dropped." if drop_table else ""), fg=typer.colors.YELLOW)


@app.command()
def backfill(
    start: datetime = typer.Option(..., help="Start datetime (ISO)"),
    end: datetime = typer.Option(..., help="End datetime (ISO)"),
) -> None:
    """Backfill Prebetter_Pair for a time range (idempotent)."""
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
    with prelude_engine.begin() as conn:
        result = conn.execute(sql, {"start": start, "end": end})
        # result.rowcount may be -1 for INSERT IGNORE; fetch affected with ROW_COUNT()
        inserted = conn.execute(text("SELECT ROW_COUNT() AS inserted")).scalar()
    typer.secho(f"Backfill complete. Inserted ~{inserted} rows.", fg=typer.colors.GREEN)


@app.command()
def backfill_days(days: int = typer.Option(7, help="Backfill the last N days")) -> None:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    # Reuse the same logic as the explicit backfill command
    backfill(start=start, end=end)


@app.command()
def status() -> None:
    with prelude_engine.connect() as conn:
        exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = 'Prebetter_Pair'"
            )
        ).scalar()
        pairs = conn.execute(text("SELECT COUNT(*) FROM Prebetter_Pair")) if exists else None
    if not exists:
        typer.secho("Prebetter_Pair absent.", fg=typer.colors.RED)
    else:
        typer.secho(
            f"Prebetter_Pair present. Rows: {pairs.scalar()}.", fg=typer.colors.GREEN
        )


if __name__ == "__main__":
    app()
