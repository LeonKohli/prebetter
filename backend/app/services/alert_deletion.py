"""
Alert Deletion Service

Provides safe deletion of alerts from the Prelude IDS database with:
- Transaction safety and automatic rollback on errors
- Orphan prevention via proper deletion order
- Heartbeat data protection via _parent_type filtering
- Comprehensive audit logging and statistics

Based on analysis in:
- /docs/alert-deletion-analysis.md
- /docs/orphan-prevention-guide.md
- /docs/deletion-transaction-test-results.md
"""

import time
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status


logger = logging.getLogger(__name__)


class AlertDeletionService:
    """
    Service for safely deleting alerts with comprehensive transaction support.

    This service implements the deletion procedure validated in the transaction test,
    ensuring no orphaned records and no impact on Heartbeat monitoring data.
    """

    # Deletion order: from leaves to root (36 steps total)
    # CRITICAL: This order prevents foreign key violations and orphans
    DELETION_ORDER = [
        # Step 1: Custom performance cache (no FK constraints)
        "Prebetter_Pair",
        # Steps 2-7: Leaf-level detailed data
        "Prelude_AdditionalData",
        "Prelude_WebServiceArg",
        "Prelude_ProcessArg",
        "Prelude_ProcessEnv",
        "Prelude_FileAccess_Permission",
        # Steps 8-23: Mid-level entities
        "Prelude_Address",
        "Prelude_Reference",
        "Prelude_Alertident",
        "Prelude_WebService",
        "Prelude_SnmpService",
        "Prelude_Service",
        "Prelude_FileAccess",
        "Prelude_File",
        "Prelude_Inode",
        "Prelude_Checksum",
        "Prelude_Linkage",
        "Prelude_User",
        "Prelude_UserId",
        "Prelude_Process",
        "Prelude_Node",
        # Steps 24-25: Analyzer data
        "Prelude_AnalyzerTime",
        "Prelude_Analyzer",
        # Steps 26-27: Source/Target entities
        "Prelude_Source",
        "Prelude_Target",
        # Steps 28-35: Alert metadata
        "Prelude_CreateTime",
        "Prelude_Confidence",
        "Prelude_CorrelationAlert",
        "Prelude_ToolAlert",
        "Prelude_OverflowAlert",
        "Prelude_Action",
        "Prelude_Assessment",
        "Prelude_Impact",
        "Prelude_Classification",
        "Prelude_DetectTime",
        # Step 36: ROOT - Must be deleted LAST
        "Prelude_Alert",
    ]

    # Shared tables that require _parent_type filtering to protect Heartbeat data
    # Format: table_name -> list of allowed _parent_type values for Alerts
    # Only tables that ACTUALLY have the _parent_type column!
    SHARED_TABLES = {
        "Prelude_Address": ["A", "S", "T"],  # Alert, Source, Target levels
        "Prelude_AdditionalData": ["A"],  # Alert level only
        "Prelude_Analyzer": ["A"],  # Alert level only
        "Prelude_AnalyzerTime": ["A"],  # Alert level only
        "Prelude_CreateTime": ["A"],  # CRITICAL: Filter to prevent deleting Heartbeat timestamps
        "Prelude_Node": ["A", "S", "T"],  # Multiple levels
        "Prelude_Process": ["A", "S", "T"],  # Multiple levels
        "Prelude_ProcessArg": ["A", "S", "T"],  # Multiple levels
        "Prelude_ProcessEnv": ["A", "S", "T"],  # Multiple levels
        "Prelude_User": ["A", "S", "T"],  # Multiple levels
        "Prelude_UserId": ["A", "S", "T"],  # Multiple levels
    }

    # Alert-only tables (no _parent_type filtering needed)
    ALERT_ONLY_TABLES = {
        "Prelude_Alert",
        "Prebetter_Pair",
        "Prelude_DetectTime",
        "Prelude_Classification",
        "Prelude_Impact",
        "Prelude_Assessment",
        "Prelude_Action",
        "Prelude_OverflowAlert",
        "Prelude_ToolAlert",
        "Prelude_CorrelationAlert",
        "Prelude_Confidence",
        "Prelude_Source",
        "Prelude_Target",
        "Prelude_Service",
        "Prelude_SnmpService",
        "Prelude_WebService",
        "Prelude_Alertident",
        "Prelude_Reference",
        # File-related tables (don't have _parent_type column)
        "Prelude_File",
        "Prelude_FileAccess",
        "Prelude_FileAccess_Permission",
        "Prelude_Inode",
        "Prelude_Linkage",
        "Prelude_Checksum",
        "Prelude_WebServiceArg",
    }

    def __init__(self, db: Session):
        """Initialize the deletion service with a database session."""
        self.db = db

    def delete_single_alert(
        self, alert_id: int, username: str
    ) -> Dict:
        """
        Delete a single alert with all associated data.

        Args:
            alert_id: The alert ID to delete
            username: Username performing the deletion (for audit)

        Returns:
            Dictionary with deletion statistics and audit info

        Raises:
            HTTPException: If alert not found or deletion fails
        """
        return self._delete_alerts([alert_id], username, "single")

    def delete_bulk_alerts(
        self, alert_ids: List[int], username: str
    ) -> Dict:
        """
        Delete multiple alerts with all associated data.

        Args:
            alert_ids: List of alert IDs to delete
            username: Username performing the deletion (for audit)

        Returns:
            Dictionary with deletion statistics and audit info

        Raises:
            HTTPException: If any alert not found or deletion fails
        """
        return self._delete_alerts(alert_ids, username, "bulk")

    def delete_grouped_alerts(
        self,
        source_ip: str,
        target_ip: str,
        username: str,
    ) -> Dict:
        """
        Delete all alerts for a specific IP pair (grouped alerts).

        Args:
            source_ip: Source IP address
            target_ip: Target IP address
            username: Username performing the deletion (for audit)

        Returns:
            Dictionary with deletion statistics and audit info

        Raises:
            HTTPException: If no alerts found for IP pair or deletion fails
        """
        # Find all alerts for this IP pair using Prebetter_Pair table
        query = text("""
            SELECT DISTINCT _message_ident
            FROM Prebetter_Pair
            WHERE source_ip = INET_ATON(:source_ip)
              AND target_ip = INET_ATON(:target_ip)
        """)

        result = self.db.execute(query, {"source_ip": source_ip, "target_ip": target_ip})
        alert_ids = [row[0] for row in result.fetchall()]

        if not alert_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No alerts found for IP pair {source_ip} -> {target_ip}",
            )

        logger.info(
            f"Found {len(alert_ids)} alerts for IP pair {source_ip} -> {target_ip}"
        )

        return self._delete_alerts(alert_ids, username, "grouped")

    def _delete_alerts(
        self,
        alert_ids: List[int],
        username: str,
        deletion_type: str,
    ) -> Dict:
        """
        Internal method to delete alerts with full transaction support.

        Args:
            alert_ids: List of alert IDs to delete
            username: Username performing deletion
            deletion_type: Type of deletion (single/bulk/grouped)

        Returns:
            Dictionary with statistics and audit info
        """
        start_time = time.time()
        stats: Dict[str, int] = {}
        total_rows_deleted = 0

        try:
            # Verify all alerts exist before starting deletion
            self._verify_alerts_exist(alert_ids)

            logger.info(
                f"Starting {deletion_type} deletion of {len(alert_ids)} alert(s) "
                f"by user {username}"
            )

            # Execute deletion in correct order
            for table in self.DELETION_ORDER:
                rows_deleted = self._delete_from_table(table, alert_ids)
                if rows_deleted > 0:
                    stats[table] = rows_deleted
                    total_rows_deleted += rows_deleted
                    logger.debug(f"Deleted {rows_deleted} rows from {table}")

            # Verify no orphans created
            orphan_check = self._check_for_orphans(alert_ids)
            if orphan_check["has_orphans"]:
                raise Exception(
                    f"Orphan records detected after deletion: {orphan_check['orphans']}"
                )

            # Commit transaction
            self.db.commit()

            duration = time.time() - start_time

            logger.info(
                f"Successfully deleted {len(alert_ids)} alert(s) "
                f"({total_rows_deleted} total rows) in {duration:.2f}s"
            )

            return {
                "success": True,
                "alert_ids_deleted": alert_ids,
                "total_alerts_deleted": len(alert_ids),
                "total_rows_deleted": total_rows_deleted,
                "table_stats": stats,
                "duration_seconds": duration,
                "deletion_type": deletion_type,
                "deleted_by": username,
            }

        except HTTPException:
            # Re-raise HTTP exceptions (like 404)
            self.db.rollback()
            raise
        except Exception as e:
            # Rollback on any error
            self.db.rollback()
            duration = time.time() - start_time

            logger.error(
                f"Alert deletion failed after {duration:.2f}s: {str(e)}",
                exc_info=True,
            )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Alert deletion failed: {str(e)}",
            )

    def _verify_alerts_exist(self, alert_ids: List[int]) -> None:
        """
        Verify all alert IDs exist before deletion.

        Args:
            alert_ids: List of alert IDs to verify

        Raises:
            HTTPException: If any alert not found
        """
        # Build placeholders for IN clause
        placeholders = ", ".join([f":id{i}" for i in range(len(alert_ids))])
        params = {f"id{i}": aid for i, aid in enumerate(alert_ids)}

        query = text(f"""
            SELECT _ident
            FROM Prelude_Alert
            WHERE _ident IN ({placeholders})
        """)

        result = self.db.execute(query, params)
        found_ids = {row[0] for row in result.fetchall()}

        missing_ids = set(alert_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert(s) not found: {sorted(missing_ids)}",
            )

    def _delete_from_table(self, table: str, alert_ids: List[int]) -> int:
        """
        Delete records from a specific table for given alert IDs.

        Handles both alert-only tables and shared tables with proper
        _parent_type filtering to protect Heartbeat data.

        Args:
            table: Table name to delete from
            alert_ids: List of alert IDs

        Returns:
            Number of rows deleted
        """
        # Build placeholders for IN clause
        placeholders = ", ".join([f":id{i}" for i in range(len(alert_ids))])
        params = {f"id{i}": aid for i, aid in enumerate(alert_ids)}

        # Build DELETE query based on table type
        if table in self.SHARED_TABLES:
            # Shared table: MUST filter by _parent_type to protect Heartbeat data
            parent_types = self.SHARED_TABLES[table]
            type_placeholders = ", ".join(
                [f":type{i}" for i in range(len(parent_types))]
            )
            type_params = {f"type{i}": pt for i, pt in enumerate(parent_types)}
            params.update(type_params)

            query = text(f"""
                DELETE FROM {table}
                WHERE _message_ident IN ({placeholders})
                  AND _parent_type IN ({type_placeholders})
            """)
        else:
            # Alert-only table: Simple deletion by _message_ident or _ident
            id_column = "_ident" if table == "Prelude_Alert" else "_message_ident"
            query = text(f"""
                DELETE FROM {table}
                WHERE {id_column} IN ({placeholders})
            """)

        result = self.db.execute(query, params)
        return result.rowcount

    def _check_for_orphans(self, alert_ids: List[int]) -> Dict:
        """
        Check if any orphaned records exist after deletion.

        Args:
            alert_ids: List of alert IDs that were deleted

        Returns:
            Dictionary with orphan check results
        """
        orphans = {}

        # Build placeholders for IN clause
        placeholders = ", ".join([f":id{i}" for i in range(len(alert_ids))])
        params = {f"id{i}": aid for i, aid in enumerate(alert_ids)}

        # Check each table in deletion order (reverse to catch dependents)
        for table in reversed(self.DELETION_ORDER):
            if table == "Prelude_Alert":
                # Alert table should be empty for these IDs
                query = text(f"""
                    SELECT COUNT(*) as count
                    FROM {table}
                    WHERE _ident IN ({placeholders})
                """)
                result = self.db.execute(query, params)
            else:
                # Check for remaining records (alert-level only)
                if table in self.SHARED_TABLES:
                    parent_types = self.SHARED_TABLES[table]
                    type_placeholders = ", ".join(
                        [f":type{i}" for i in range(len(parent_types))]
                    )
                    type_params = {f"type{i}": pt for i, pt in enumerate(parent_types)}
                    params_copy = {**params, **type_params}

                    query = text(f"""
                        SELECT COUNT(*) as count
                        FROM {table}
                        WHERE _message_ident IN ({placeholders})
                          AND _parent_type IN ({type_placeholders})
                    """)
                    result = self.db.execute(query, params_copy)
                else:
                    query = text(f"""
                        SELECT COUNT(*) as count
                        FROM {table}
                        WHERE _message_ident IN ({placeholders})
                    """)
                    result = self.db.execute(query, params)

            count = result.scalar()
            if count > 0:
                orphans[table] = count

        return {
            "has_orphans": len(orphans) > 0,
            "orphans": orphans,
        }
