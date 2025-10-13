"""Unified Prelude database cleanup utility.

This script trims alert and heartbeat data older than a configurable
retention window and removes orphaned heartbeat artifacts left by previous
maintenance jobs. It is intended to be scheduled (e.g., nightly via cron)
using the application's existing database configuration.

Usage:
    uv run python -m app.scripts.prelude_cleanup [COMMAND] [OPTIONS]
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, Iterable, Tuple

import typer
from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.datetime_utils import get_current_time
from app.database.config import prelude_engine

app = typer.Typer(help="Prelude DB cleanup utility", no_args_is_help=True, add_completion=False)
logger = logging.getLogger(__name__)

ALERT_TMP_TABLE = "tmp_alert_ids"
HEARTBEAT_TMP_TABLE = "tmp_heartbeat_ids"

# Alert child table deletions executed in order each batch
ALERT_DELETE_STATEMENTS: Tuple[Tuple[str, str], ...] = (
    (
        "process_args",
        f"DELETE pa FROM Prelude_ProcessArg pa JOIN {ALERT_TMP_TABLE} ta ON pa._message_ident = ta.id WHERE pa._parent_type IN ('A','S','T')",
    ),
    (
        "process_env",
        f"DELETE pe FROM Prelude_ProcessEnv pe JOIN {ALERT_TMP_TABLE} ta ON pe._message_ident = ta.id WHERE pe._parent_type IN ('A','S','T')",
    ),
    (
        "process",
        f"DELETE pp FROM Prelude_Process pp JOIN {ALERT_TMP_TABLE} ta ON pp._message_ident = ta.id WHERE pp._parent_type IN ('A','S','T')",
    ),
    (
        "additional_data",
        f"DELETE pad FROM Prelude_AdditionalData pad JOIN {ALERT_TMP_TABLE} ta ON pad._message_ident = ta.id WHERE pad._parent_type = 'A'",
    ),
    (
        "analyzer_time",
        f"DELETE pat FROM Prelude_AnalyzerTime pat JOIN {ALERT_TMP_TABLE} ta ON pat._message_ident = ta.id WHERE pat._parent_type = 'A'",
    ),
    (
        "analyzer",
        f"DELETE pan FROM Prelude_Analyzer pan JOIN {ALERT_TMP_TABLE} ta ON pan._message_ident = ta.id WHERE pan._parent_type = 'A'",
    ),
    (
        "address",
        f"DELETE paddr FROM Prelude_Address paddr JOIN {ALERT_TMP_TABLE} ta ON paddr._message_ident = ta.id WHERE paddr._parent_type IN ('A','S','T')",
    ),
    (
        "node",
        f"DELETE pn FROM Prelude_Node pn JOIN {ALERT_TMP_TABLE} ta ON pn._message_ident = ta.id WHERE pn._parent_type IN ('A','S','T')",
    ),
    (
        "service",
        f"DELETE ps FROM Prelude_Service ps JOIN {ALERT_TMP_TABLE} ta ON ps._message_ident = ta.id WHERE ps._parent_type IN ('S','T')",
    ),
    (
        "source",
        f"DELETE psrc FROM Prelude_Source psrc JOIN {ALERT_TMP_TABLE} ta ON psrc._message_ident = ta.id",
    ),
    (
        "target",
        f"DELETE pt FROM Prelude_Target pt JOIN {ALERT_TMP_TABLE} ta ON pt._message_ident = ta.id",
    ),
    (
        "action",
        f"DELETE pact FROM Prelude_Action pact JOIN {ALERT_TMP_TABLE} ta ON pact._message_ident = ta.id",
    ),
    (
        "confidence",
        f"DELETE pconf FROM Prelude_Confidence pconf JOIN {ALERT_TMP_TABLE} ta ON pconf._message_ident = ta.id",
    ),
    (
        "impact",
        f"DELETE pimp FROM Prelude_Impact pimp JOIN {ALERT_TMP_TABLE} ta ON pimp._message_ident = ta.id",
    ),
    (
        "assessment",
        f"DELETE passess FROM Prelude_Assessment passess JOIN {ALERT_TMP_TABLE} ta ON passess._message_ident = ta.id",
    ),
    (
        "classification",
        f"DELETE pclass FROM Prelude_Classification pclass JOIN {ALERT_TMP_TABLE} ta ON pclass._message_ident = ta.id",
    ),
    (
        "reference",
        f"DELETE pref FROM Prelude_Reference pref JOIN {ALERT_TMP_TABLE} ta ON pref._message_ident = ta.id",
    ),
    (
        "alertident",
        f"DELETE paid FROM Prelude_Alertident paid JOIN {ALERT_TMP_TABLE} ta ON paid._message_ident = ta.id",
    ),
    (
        "correlation_alert",
        f"DELETE pcorr FROM Prelude_CorrelationAlert pcorr JOIN {ALERT_TMP_TABLE} ta ON pcorr._message_ident = ta.id",
    ),
    (
        "linkage",
        f"DELETE plink FROM Prelude_Linkage plink JOIN {ALERT_TMP_TABLE} ta ON plink._message_ident = ta.id",
    ),
    (
        "checksum",
        f"DELETE pchk FROM Prelude_Checksum pchk JOIN {ALERT_TMP_TABLE} ta ON pchk._message_ident = ta.id",
    ),
    (
        "file_access_permission",
        f"DELETE pfap FROM Prelude_FileAccess_Permission pfap JOIN {ALERT_TMP_TABLE} ta ON pfap._message_ident = ta.id",
    ),
    (
        "file_access",
        f"DELETE pfa FROM Prelude_FileAccess pfa JOIN {ALERT_TMP_TABLE} ta ON pfa._message_ident = ta.id",
    ),
    (
        "file",
        f"DELETE pf FROM Prelude_File pf JOIN {ALERT_TMP_TABLE} ta ON pf._message_ident = ta.id",
    ),
    (
        "inode",
        f"DELETE pin FROM Prelude_Inode pin JOIN {ALERT_TMP_TABLE} ta ON pin._message_ident = ta.id",
    ),
    (
        "tool_alert",
        f"DELETE ptool FROM Prelude_ToolAlert ptool JOIN {ALERT_TMP_TABLE} ta ON ptool._message_ident = ta.id",
    ),
    (
        "overflow_alert",
        f"DELETE pover FROM Prelude_OverflowAlert pover JOIN {ALERT_TMP_TABLE} ta ON pover._message_ident = ta.id",
    ),
    (
        "webservice_arg",
        f"DELETE pwsarg FROM Prelude_WebServiceArg pwsarg JOIN {ALERT_TMP_TABLE} ta ON pwsarg._message_ident = ta.id",
    ),
    (
        "webservice",
        f"DELETE pws FROM Prelude_WebService pws JOIN {ALERT_TMP_TABLE} ta ON pws._message_ident = ta.id",
    ),
    (
        "snmp_service",
        f"DELETE psnmp FROM Prelude_SnmpService psnmp JOIN {ALERT_TMP_TABLE} ta ON psnmp._message_ident = ta.id",
    ),
    (
        "user_id",
        f"DELETE puid FROM Prelude_UserId puid JOIN {ALERT_TMP_TABLE} ta ON puid._message_ident = ta.id",
    ),
    (
        "user",
        f"DELETE pu FROM Prelude_User pu JOIN {ALERT_TMP_TABLE} ta ON pu._message_ident = ta.id",
    ),
    (
        "create_time",
        f"DELETE pct FROM Prelude_CreateTime pct JOIN {ALERT_TMP_TABLE} ta ON pct._message_ident = ta.id WHERE pct._parent_type = 'A'",
    ),
    (
        "detect_time",
        f"DELETE pdt FROM Prelude_DetectTime pdt JOIN {ALERT_TMP_TABLE} ta ON pdt._message_ident = ta.id",
    ),
    (
        "alert",
        f"DELETE pa FROM Prelude_Alert pa JOIN {ALERT_TMP_TABLE} ta ON pa._ident = ta.id",
    ),
)

HEARTBEAT_DELETE_STATEMENTS: Tuple[Tuple[str, str], ...] = (
    (
        "heartbeat_process_args",
        f"DELETE pha FROM Prelude_ProcessArg pha JOIN {HEARTBEAT_TMP_TABLE} ta ON pha._message_ident = ta.id WHERE pha._parent_type = 'H'",
    ),
    (
        "heartbeat_process_env",
        f"DELETE phe FROM Prelude_ProcessEnv phe JOIN {HEARTBEAT_TMP_TABLE} ta ON phe._message_ident = ta.id WHERE phe._parent_type = 'H'",
    ),
    (
        "heartbeat_process",
        f"DELETE php FROM Prelude_Process php JOIN {HEARTBEAT_TMP_TABLE} ta ON php._message_ident = ta.id WHERE php._parent_type = 'H'",
    ),
    (
        "heartbeat_additional_data",
        f"DELETE phad FROM Prelude_AdditionalData phad JOIN {HEARTBEAT_TMP_TABLE} ta ON phad._message_ident = ta.id WHERE phad._parent_type = 'H'",
    ),
    (
        "heartbeat_analyzer_time",
        f"DELETE phat FROM Prelude_AnalyzerTime phat JOIN {HEARTBEAT_TMP_TABLE} ta ON phat._message_ident = ta.id WHERE phat._parent_type = 'H'",
    ),
    (
        "heartbeat_analyzer",
        f"DELETE phan FROM Prelude_Analyzer phan JOIN {HEARTBEAT_TMP_TABLE} ta ON phan._message_ident = ta.id WHERE phan._parent_type = 'H'",
    ),
    (
        "heartbeat_address",
        f"DELETE phaddr FROM Prelude_Address phaddr JOIN {HEARTBEAT_TMP_TABLE} ta ON phaddr._message_ident = ta.id WHERE phaddr._parent_type = 'H'",
    ),
    (
        "heartbeat_node",
        f"DELETE phn FROM Prelude_Node phn JOIN {HEARTBEAT_TMP_TABLE} ta ON phn._message_ident = ta.id WHERE phn._parent_type = 'H'",
    ),
    (
        "heartbeat_create_time",
        f"DELETE phct FROM Prelude_CreateTime phct JOIN {HEARTBEAT_TMP_TABLE} ta ON phct._message_ident = ta.id WHERE phct._parent_type = 'H'",
    ),
    (
        "heartbeat",
        f"DELETE ph FROM Prelude_Heartbeat ph JOIN {HEARTBEAT_TMP_TABLE} ta ON ph._ident = ta.id",
    ),
)

HEARTBEAT_ORPHAN_TASKS: Tuple[Tuple[str, str, str], ...] = (
    (
        "orphan_heartbeat_additional_data",
        "DELETE FROM Prelude_AdditionalData "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_AdditionalData._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_AdditionalData "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_AdditionalData._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_address",
        "DELETE FROM Prelude_Address "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Address._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_Address "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Address._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_analyzer",
        "DELETE FROM Prelude_Analyzer "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Analyzer._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_Analyzer "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Analyzer._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_analyzer_time",
        "DELETE FROM Prelude_AnalyzerTime "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_AnalyzerTime._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_AnalyzerTime "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_AnalyzerTime._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_node",
        "DELETE FROM Prelude_Node "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Node._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_Node "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Node._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_process",
        "DELETE FROM Prelude_Process "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Process._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_Process "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_Process._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_process_args",
        "DELETE FROM Prelude_ProcessArg "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_ProcessArg._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_ProcessArg "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_ProcessArg._message_ident"
        ")",
    ),
    (
        "orphan_heartbeat_process_env",
        "DELETE FROM Prelude_ProcessEnv "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_ProcessEnv._message_ident"
        ") LIMIT :limit",
        "SELECT COUNT(*) FROM Prelude_ProcessEnv "
        "WHERE _parent_type = 'H' AND NOT EXISTS ("
        "SELECT 1 FROM Prelude_Heartbeat ph "
        "WHERE ph._ident = Prelude_ProcessEnv._message_ident"
        ")",
    ),
)


def _normalize_rowcount(value: Any) -> int:
    if value is None or value == -1:
        return 0
    return int(value)


def _populate_tmp_table(
    conn: Connection,
    table_name: str,
    insert_sql: str,
    cutoff,
    batch_size: int,
) -> int:
    conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {table_name}"))
    conn.execute(
        text(
            f"CREATE TEMPORARY TABLE {table_name} (id BIGINT UNSIGNED PRIMARY KEY) ENGINE=MEMORY"
        )
    )
    conn.execute(text(insert_sql), {"cutoff": cutoff, "limit": batch_size})
    batch = conn.scalar(text(f"SELECT COUNT(*) FROM {table_name}"))
    if not batch:
        conn.execute(text(f"DROP TEMPORARY TABLE IF EXISTS {table_name}"))
        return 0
    return int(batch)


def _delete_batches(
    conn: Connection,
    temp_table: str,
    insert_sql: str,
    delete_statements: Iterable[Tuple[str, str]],
    cutoff,
    batch_size: int,
) -> Tuple[int, Dict[str, int]]:
    total_parents = 0
    child_counts: Dict[str, int] = defaultdict(int)
    batch_number = 0

    while True:
        with conn.begin():
            batch = _populate_tmp_table(
                conn, temp_table, insert_sql, cutoff, batch_size
            )
            if batch == 0:
                break

            batch_number += 1
            for name, stmt in delete_statements:
                result = conn.execute(text(stmt))
                affected = _normalize_rowcount(result.rowcount)
                if affected:
                    child_counts[name] = child_counts.get(name, 0) + affected

            total_parents += batch
        typer.echo(
            f"Removed batch #{batch_number} from {temp_table}: {batch} parent rows"
        )

    return total_parents, dict(child_counts)


def _cleanup_orphans(
    conn: Connection,
    tasks: Iterable[Tuple[str, str, str]],
    batch_size: int,
) -> Dict[str, int]:
    removed: Dict[str, int] = defaultdict(int)

    for name, delete_sql, _ in tasks:
        loop = 0
        while True:
            with conn.begin():
                result = conn.execute(text(delete_sql), {"limit": batch_size})
                affected = _normalize_rowcount(result.rowcount)
            if affected == 0:
                break
            loop += 1
            removed[name] = removed.get(name, 0) + affected
            typer.echo(f"Removed {affected} rows for {name} (loop {loop})")

    return dict(removed)


def _gather_preview(
    conn: Connection,
    alert_cutoff,
    heartbeat_cutoff,
    include_orphans: bool,
) -> Dict[str, Any]:
    """Gather preview statistics for cleanup operation.

    Args:
        conn: Database connection
        alert_cutoff: Cutoff datetime for alerts
        heartbeat_cutoff: Cutoff datetime for heartbeats
        include_orphans: Whether to include orphan counts

    Returns:
        Dictionary with preview statistics
    """
    preview: Dict[str, Any] = {}

    alert_count = conn.scalar(
        text("SELECT COUNT(*) FROM Prelude_DetectTime WHERE time < :cutoff"),
        {"cutoff": alert_cutoff},
    )
    heartbeat_count = conn.scalar(
        text(
            "SELECT COUNT(*) FROM Prelude_CreateTime "
            "WHERE _parent_type = 'H' AND time < :cutoff"
        ),
        {"cutoff": heartbeat_cutoff},
    )
    preview["alerts_due"] = int(alert_count or 0)
    preview["heartbeats_due"] = int(heartbeat_count or 0)

    if include_orphans:
        for name, _, count_sql in HEARTBEAT_ORPHAN_TASKS:
            count = conn.scalar(text(count_sql))
            preview[name] = int(count or 0)

    return preview


@app.command()
def run(
    alert_retention_days: int = typer.Option(
        30, "--alert-retention", "-a", min=1, max=365, help="Days of alert data to retain"
    ),
    heartbeat_retention_days: int = typer.Option(
        None, "--heartbeat-retention", "-h", min=1, max=365, help="Days of heartbeat data to retain (defaults to alert retention)"
    ),
    batch_size: int = typer.Option(
        50000, "--batch-size", "-b", min=1000, max=200000, help="Rows processed per batch"
    ),
    cleanup_orphans: bool = typer.Option(
        True, "--cleanup-orphans/--no-cleanup-orphans", help="Remove heartbeat orphaned rows"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview what would be deleted without making changes"
    ),
) -> None:
    """Execute cleanup with separate alert (-a) and heartbeat (-h) retention.

    Remove old alerts and heartbeats with independent retention policies.
    Heartbeats default to alert retention if -h not specified.

    Examples:
        run -a 30           # Keep 30 days of both
        run -a 30 -h 7      # Keep 30d alerts, 7d heartbeats
        run -a 60 -h 14 --dry-run
    """
    # Default heartbeat retention to alert retention if not specified
    if heartbeat_retention_days is None:
        heartbeat_retention_days = alert_retention_days

    alert_cutoff_dt = (get_current_time() - timedelta(days=alert_retention_days)).replace(
        tzinfo=None
    )
    heartbeat_cutoff_dt = (get_current_time() - timedelta(days=heartbeat_retention_days)).replace(
        tzinfo=None
    )

    typer.secho("Prelude Database Cleanup", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"Alert retention: {alert_retention_days} days (cutoff: {alert_cutoff_dt:%Y-%m-%d %H:%M:%S} UTC)")
    typer.echo(f"Heartbeat retention: {heartbeat_retention_days} days (cutoff: {heartbeat_cutoff_dt:%Y-%m-%d %H:%M:%S} UTC)")
    typer.echo(f"Batch size: {batch_size:,}")
    typer.echo(f"Cleanup orphans: {'Yes' if cleanup_orphans else 'No'}")

    if dry_run:
        typer.secho("\nDRY RUN MODE - No changes will be made", fg=typer.colors.YELLOW, bold=True)

    insert_alert_sql = (
        "INSERT INTO tmp_alert_ids (id) "
        "SELECT dt._message_ident AS id FROM Prelude_DetectTime dt "
        "WHERE dt.time < :cutoff ORDER BY dt.time LIMIT :limit"
    )
    insert_heartbeat_sql = (
        "INSERT INTO tmp_heartbeat_ids (id) "
        "SELECT ct._message_ident AS id FROM Prelude_CreateTime ct "
        "WHERE ct._parent_type = 'H' AND ct.time < :cutoff "
        "ORDER BY ct.time LIMIT :limit"
    )

    try:
        with prelude_engine.connect() as conn:
            conn.execute(text("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            conn.commit()

            if dry_run:
                preview = _gather_preview(
                    conn, alert_cutoff_dt, heartbeat_cutoff_dt, include_orphans=cleanup_orphans
                )
                typer.echo("\nPreview (no changes applied):")
                for key, value in preview.items():
                    typer.echo(f"  {key}: {value:,}")
                conn.rollback()
                return

            conn.commit()

            typer.echo()
            alert_total, alert_children = _delete_batches(
                conn,
                ALERT_TMP_TABLE,
                insert_alert_sql,
                ALERT_DELETE_STATEMENTS,
                alert_cutoff_dt,
                batch_size,
            )
            typer.secho(
                f"✓ Removed {alert_total:,} alerts older than {alert_retention_days} days",
                fg=typer.colors.GREEN,
            )

            heartbeat_total, heartbeat_children = _delete_batches(
                conn,
                HEARTBEAT_TMP_TABLE,
                insert_heartbeat_sql,
                HEARTBEAT_DELETE_STATEMENTS,
                heartbeat_cutoff_dt,
                batch_size,
            )
            typer.secho(
                f"✓ Removed {heartbeat_total:,} heartbeats older than {heartbeat_retention_days} days",
                fg=typer.colors.GREEN,
            )

            orphan_stats: Dict[str, int] = {}
            if cleanup_orphans:
                orphan_stats = _cleanup_orphans(conn, HEARTBEAT_ORPHAN_TASKS, batch_size)
                if orphan_stats:
                    typer.secho(f"✓ Removed {sum(orphan_stats.values()):,} orphaned rows", fg=typer.colors.GREEN)

            typer.echo("\n" + "=" * 60)
            typer.secho("Cleanup Summary", fg=typer.colors.CYAN, bold=True)
            typer.echo("=" * 60)
            typer.echo(f"  Alerts removed: {alert_total:,}")
            typer.echo(f"  Heartbeats removed: {heartbeat_total:,}")
            typer.echo(f"  Alert child rows: {sum(alert_children.values()):,}")
            typer.echo(f"  Heartbeat child rows: {sum(heartbeat_children.values()):,}")
            if cleanup_orphans:
                typer.echo(f"  Orphan rows: {sum(orphan_stats.values()):,}")
            typer.echo(f"  Total rows removed: {alert_total + heartbeat_total + sum(alert_children.values()) + sum(heartbeat_children.values()) + sum(orphan_stats.values()):,}")

            if alert_children:
                typer.echo("\nAlert child breakdown:")
                for table, count in sorted(
                    alert_children.items(), key=lambda x: x[1], reverse=True
                ):
                    typer.echo(f"  {table}: {count:,}")
            if heartbeat_children:
                typer.echo("\nHeartbeat child breakdown:")
                for table, count in sorted(
                    heartbeat_children.items(), key=lambda x: x[1], reverse=True
                ):
                    typer.echo(f"  {table}: {count:,}")
            if cleanup_orphans and orphan_stats:
                typer.echo("\nOrphan breakdown:")
                for table, count in sorted(
                    orphan_stats.items(), key=lambda x: x[1], reverse=True
                ):
                    typer.echo(f"  {table}: {count:,}")

            typer.echo("=" * 60)
            typer.secho("✓ Cleanup complete!", fg=typer.colors.GREEN, bold=True)

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        typer.secho(f"\n✗ Cleanup failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command()
def status(
    alert_retention_days: int = typer.Option(
        30, "--alert-retention", "-a", min=1, max=365, help="Days of alert data to retain"
    ),
    heartbeat_retention_days: int = typer.Option(
        None, "--heartbeat-retention", "-h", min=1, max=365, help="Days of heartbeat data to retain (defaults to alert retention)"
    ),
) -> None:
    """Show cleanup preview with alert (-a) and heartbeat (-h) retention.

    Check how many records would be deleted without making changes.

    Examples:
        status -a 30        # Preview 30 days for both
        status -a 30 -h 7   # Preview different retentions
    """
    # Default heartbeat retention to alert retention if not specified
    if heartbeat_retention_days is None:
        heartbeat_retention_days = alert_retention_days

    alert_cutoff_dt = (get_current_time() - timedelta(days=alert_retention_days)).replace(
        tzinfo=None
    )
    heartbeat_cutoff_dt = (get_current_time() - timedelta(days=heartbeat_retention_days)).replace(
        tzinfo=None
    )

    typer.secho("Cleanup Status", fg=typer.colors.CYAN, bold=True)
    typer.echo(f"Alert retention: {alert_retention_days} days (cutoff: {alert_cutoff_dt:%Y-%m-%d %H:%M:%S} UTC)")
    typer.echo(f"Heartbeat retention: {heartbeat_retention_days} days (cutoff: {heartbeat_cutoff_dt:%Y-%m-%d %H:%M:%S} UTC)")

    try:
        with prelude_engine.connect() as conn:
            preview = _gather_preview(
                conn, alert_cutoff_dt, heartbeat_cutoff_dt, include_orphans=True
            )

            typer.echo("\nData eligible for cleanup:")
            typer.echo(f"  Alerts: {preview.get('alerts_due', 0):,}")
            typer.echo(f"  Heartbeats: {preview.get('heartbeats_due', 0):,}")

            orphan_total = sum(
                count for key, count in preview.items()
                if key not in ('alerts_due', 'heartbeats_due')
            )
            if orphan_total > 0:
                typer.echo(f"  Orphaned records: {orphan_total:,}")

            total = preview.get('alerts_due', 0) + preview.get('heartbeats_due', 0)
            if total == 0:
                typer.secho("\n✓ No data needs cleanup", fg=typer.colors.GREEN, bold=True)
            else:
                typer.secho(f"\n⚠ Total records eligible: {total:,}", fg=typer.colors.YELLOW, bold=True)
                typer.echo("Run 'run --dry-run' with the same retention settings to see detailed preview")

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        typer.secho(f"✗ Status check failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


def main() -> None:
    """Entry point for the script."""
    logging.basicConfig(level=logging.INFO)
    app()


if __name__ == "__main__":
    main()
