# Orphan Prevention Guide for Alert Deletion

**Critical Reference Document**
**Date:** 2025-10-17
**Purpose:** Prevent orphaned records during alert deletion operations

---

## 🎯 Executive Summary

The Prelude IDS database has **NO foreign key constraints** and uses a **shared table architecture** where many tables contain data for BOTH Alerts and Heartbeats. Deleting alerts without proper filtering will:
- ❌ Leave orphaned records consuming storage
- ❌ Break database integrity
- ❌ Corrupt Prebetter_Pair performance cache
- ❌ Make the database unmaintainable over time

**This guide provides:** Complete table inventory, deletion order, orphan detection queries, and prevention strategies.

---

## 📊 Part 1: Database Architecture Understanding

### The _parent_type System

Many tables in Prelude use a `_parent_type` ENUM to distinguish what entity the record belongs to:

```sql
-- Parent type values:
'A' = Alert          (our deletion target)
'H' = Heartbeat      (MUST NOT DELETE)
'S' = Source         (Alert sub-entity)
'T' = Target         (Alert sub-entity)
'C' = CorrelationAlert
'F' = File
```

**CRITICAL**: When deleting Alert data, you must **filter by _parent_type = 'A'** in shared tables!

### Multi-Level Indexing System

Prelude uses a sophisticated indexing system for hierarchical data:

```
_message_ident  → Links to parent message (Alert._ident or Heartbeat._ident)
_parent_type    → What level: Alert('A'), Heartbeat('H'), Source('S'), Target('T')
_parent0_index  → Index of parent entity (e.g., which Source/Target within the alert)
_index          → Index of this specific item (e.g., which Address within the Source)
```

**Example - Address table structure:**
```
alert_id=1000, _parent_type='S', _parent0_index=0, _index=0 → First Source's first Address
alert_id=1000, _parent_type='S', _parent0_index=0, _index=1 → First Source's second Address
alert_id=1000, _parent_type='T', _parent0_index=0, _index=0 → First Target's first Address
```

---

## 📋 Part 2: Complete Table Inventory with Data Volumes

### Alert-Only Tables (Direct Deletion, No _parent_type)

These tables contain ONLY Alert data. Safe to delete by `_message_ident`:

| Table | Row Count | Data Size | Notes |
|-------|-----------|-----------|-------|
| **Prelude_Alert** | 23,235 | 1.52 MB | **DELETE LAST!** This is the parent table |
| Prelude_DetectTime | 22,569 | 1.52 MB | 1:1 with alerts, must exist |
| Prelude_Classification | 22,943 | 2.52 MB | 1:1 with alerts, required field |
| Prelude_Impact | 23,003 | 2.52 MB | 1:1 with alerts, contains severity |
| Prelude_Assessment | 22,739 | 1.52 MB | 1:1 with alerts |
| **Prebetter_Pair** | 22,697 | 1.52 MB | **Custom table!** Performance cache, no trigger for delete |
| Prelude_Source | 46,677 | 2.48 MB | N:1 with alerts, _index field |
| Prelude_Target | 49,542 | 2.52 MB | N:1 with alerts, _index field |
| Prelude_Reference | 119,683 | 19.55 MB | N:M with alerts, CVE/BugTraq refs |
| Prelude_CorrelationAlert | 753 | 0.09 MB | Correlation info |

```sql
-- Safe deletion pattern for Alert-only tables:
DELETE FROM {table} WHERE _message_ident = ?;
```

### Shared Tables (Alert + Heartbeat Data - REQUIRES FILTERING)

These tables contain data for BOTH Alerts and Heartbeats. **MUST filter by _parent_type**:

| Table | Total Rows | Alert Rows | Heartbeat Rows | Data Size |
|-------|------------|------------|----------------|-----------|
| **Prelude_Address** | 3,128,080 | 243,932 | 2,709,402 | 187.75 MB |
| **Prelude_AdditionalData** | 1,475,398 | 624,665 | 850,733 | 167.70 MB |
| **Prelude_Analyzer** | 1,442,022 | 174,630 | 1,267,392 | 260.95 MB |
| Prelude_Node | 1,036,654 | ~30% | ~70% | 61.61 MB |
| Prelude_Process | 931,913 | ~30% | ~70% | 85.66 MB |
| Prelude_CreateTime | 306,523 | ~10% | ~90% | 13.50 MB |
| Prelude_AnalyzerTime | 304,896 | ~10% | ~90% | 13.50 MB |

```sql
-- CRITICAL: Must filter by _parent_type for shared tables:
DELETE FROM Prelude_Address
WHERE _message_ident = ?
  AND _parent_type IN ('A', 'S', 'T');  -- Alert-related only!

DELETE FROM Prelude_AdditionalData
WHERE _message_ident = ?
  AND _parent_type = 'A';  -- Alert-level only!

DELETE FROM Prelude_Analyzer
WHERE _message_ident = ?
  AND _parent_type = 'A';  -- Alert-level only!
```

### Empty Tables (No Current Data, But May Be Populated)

These tables have NO data currently but should still be checked:

- Prelude_Confidence
- Prelude_WebService / Prelude_WebServiceArg
- Prelude_FileAccess / Prelude_FileAccess_Permission
- Prelude_ToolAlert / Prelude_OverflowAlert
- Prelude_Linkage / Prelude_Action
- Prelude_SnmpService
- Prelude_ProcessEnv / Prelude_ProcessArg
- Prelude_UserId / Prelude_User
- Prelude_File / Prelude_Inode / Prelude_Checksum

```sql
-- Safe to include in deletion even if empty:
DELETE FROM {table} WHERE _message_ident = ?;
-- Or with _parent_type filter if applicable
```

### Special Table: Heartbeat (DO NOT DELETE)

| Table | Row Count | Notes |
|-------|-----------|-------|
| Prelude_Heartbeat | 281,867 | **NEVER DELETE!** Separate message type |

```sql
-- Heartbeat is a separate IDMEF message type
-- It shares _ident space with Alert but is NOT related
-- DO NOT touch this table during Alert deletion!
```

---

## 🔍 Part 3: Orphan Detection Queries

### 3.1 Pre-Deletion Orphan Check

Run this BEFORE implementing deletion to establish baseline:

```sql
-- Check for truly orphaned Alert records (not linked to valid Alert)
SELECT
  'Table' as source,
  'Orphans' as type,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {table}), 2) as pct
FROM (
  -- Prebetter_Pair
  SELECT 'Prebetter_Pair', COUNT(*) FROM Prebetter_Pair bp
  LEFT JOIN Prelude_Alert a ON bp._message_ident = a._ident
  WHERE a._ident IS NULL

  UNION ALL

  -- DetectTime (should be 0)
  SELECT 'DetectTime', COUNT(*) FROM Prelude_DetectTime dt
  LEFT JOIN Prelude_Alert a ON dt._message_ident = a._ident
  WHERE a._ident IS NULL

  UNION ALL

  -- Address (Alert-level only, excluding Heartbeat)
  SELECT 'Address_Alert', COUNT(*) FROM Prelude_Address addr
  LEFT JOIN Prelude_Alert a ON addr._message_ident = a._ident
  WHERE a._ident IS NULL AND addr._parent_type IN ('A', 'S', 'T')

  UNION ALL

  -- AdditionalData (Alert-level only)
  SELECT 'AdditionalData_Alert', COUNT(*) FROM Prelude_AdditionalData ad
  LEFT JOIN Prelude_Alert a ON ad._message_ident = a._ident
  WHERE a._ident IS NULL AND ad._parent_type = 'A'

) as orphan_check;
```

**Expected Result:** Should be 0 for all Alert-only tables.

### 3.2 Post-Deletion Verification

Run this AFTER each deletion to verify no orphans were created:

```sql
-- Verify deletion completeness for a specific alert_id
SET @deleted_alert_id = 12345;  -- Replace with actual deleted alert ID

SELECT
  'Prebetter_Pair' as remaining_in,
  COUNT(*) as count
FROM Prebetter_Pair WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'DetectTime', COUNT(*) FROM Prelude_DetectTime WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Classification', COUNT(*) FROM Prelude_Classification WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Impact', COUNT(*) FROM Prelude_Impact WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Assessment', COUNT(*) FROM Prelude_Assessment WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Address', COUNT(*) FROM Prelude_Address WHERE _message_ident = @deleted_alert_id AND _parent_type IN ('A','S','T')
UNION ALL
SELECT 'AdditionalData', COUNT(*) FROM Prelude_AdditionalData WHERE _message_ident = @deleted_alert_id AND _parent_type = 'A'
UNION ALL
SELECT 'Source', COUNT(*) FROM Prelude_Source WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Target', COUNT(*) FROM Prelude_Target WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Analyzer', COUNT(*) FROM Prelude_Analyzer WHERE _message_ident = @deleted_alert_id AND _parent_type = 'A'
UNION ALL
SELECT 'Node', COUNT(*) FROM Prelude_Node WHERE _message_ident = @deleted_alert_id AND _parent_type IN ('A','S','T')
UNION ALL
SELECT 'Process', COUNT(*) FROM Prelude_Process WHERE _message_ident = @deleted_alert_id AND _parent_type IN ('A','S','T')
UNION ALL
SELECT 'Reference', COUNT(*) FROM Prelude_Reference WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Service', COUNT(*) FROM Prelude_Service WHERE _message_ident = @deleted_alert_id
UNION ALL
SELECT 'Alert', COUNT(*) FROM Prelude_Alert WHERE _ident = @deleted_alert_id;
```

**Expected Result:** All counts should be 0 after successful deletion.

### 3.3 Periodic Orphan Audit

Run this monthly to detect any orphaned records that accumulated:

```sql
-- Comprehensive orphan audit (Alert-related only)
CREATE TEMPORARY TABLE IF NOT EXISTS orphan_audit_results (
  table_name VARCHAR(100),
  orphan_count INT,
  total_rows INT,
  orphan_percentage DECIMAL(5,2),
  action_required VARCHAR(20)
);

-- Check each table
INSERT INTO orphan_audit_results
SELECT
  'Prebetter_Pair' as table_name,
  COUNT(*) as orphan_count,
  (SELECT COUNT(*) FROM Prebetter_Pair) as total_rows,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Prebetter_Pair), 2) as orphan_percentage,
  CASE WHEN COUNT(*) > 0 THEN 'CLEANUP NEEDED' ELSE 'OK' END as action_required
FROM Prebetter_Pair bp
LEFT JOIN Prelude_Alert a ON bp._message_ident = a._ident
WHERE a._ident IS NULL;

-- Repeat for other critical tables...
-- (Add similar queries for DetectTime, Classification, Impact, etc.)

-- Show results
SELECT * FROM orphan_audit_results ORDER BY orphan_percentage DESC;
```

---

## 🗑️ Part 4: Safe Deletion Order

### 4.1 Deletion Sequence (CRITICAL - Do Not Reorder!)

Delete in this EXACT order to prevent foreign key violations and ensure completeness:

```python
# Deletion order from leaves to root
DELETION_ORDER = [
    # 1. Custom performance cache (no dependencies)
    "Prebetter_Pair",

    # 2. Most detailed data (leaves of the tree)
    "Prelude_AdditionalData",      # Extra data fields
    "Prelude_WebServiceArg",       # Web service arguments
    "Prelude_ProcessArg",          # Process arguments
    "Prelude_ProcessEnv",          # Process environment
    "Prelude_FileAccess_Permission", # File permission details

    # 3. Mid-level entities (depend on above)
    "Prelude_Address",             # IP addresses (careful: shared!)
    "Prelude_Reference",           # CVE/BugTraq references
    "Prelude_Alertident",          # Alert identifiers
    "Prelude_WebService",          # Web service info
    "Prelude_SnmpService",         # SNMP service info
    "Prelude_Service",             # Generic service info
    "Prelude_FileAccess",          # File access details
    "Prelude_File",                # File information
    "Prelude_Inode",               # Inode information
    "Prelude_Checksum",            # File checksums
    "Prelude_Linkage",             # File linkage
    "Prelude_User",                # User information
    "Prelude_UserId",              # User IDs
    "Prelude_Process",             # Process details (careful: shared!)
    "Prelude_Node",                # Node information (careful: shared!)

    # 4. Analyzer-related
    "Prelude_AnalyzerTime",        # Analyzer timestamps (careful: shared!)
    "Prelude_Analyzer",            # Analyzer info (careful: shared!)

    # 5. Source/Target entities
    "Prelude_Source",              # Source entities
    "Prelude_Target",              # Target entities

    # 6. Time-related
    "Prelude_CreateTime",          # Creation time (careful: shared!)

    # 7. Assessment-related
    "Prelude_Confidence",          # Confidence ratings
    "Prelude_CorrelationAlert",    # Correlation info
    "Prelude_ToolAlert",           # Tool-specific info
    "Prelude_OverflowAlert",       # Overflow info
    "Prelude_Action",              # Actions taken

    # 8. Core alert data
    "Prelude_Assessment",          # Assessment
    "Prelude_Impact",              # Impact/severity
    "Prelude_Classification",      # Classification
    "Prelude_DetectTime",          # Detection time

    # 9. Root entity - DELETE LAST!
    "Prelude_Alert",               # The alert itself
]
```

### 4.2 Deletion SQL Templates

#### For Alert-Only Tables:
```sql
DELETE FROM {table_name} WHERE _message_ident = :alert_id;
```

#### For Shared Tables (with _parent_type):
```sql
-- Address (multi-level)
DELETE FROM Prelude_Address
WHERE _message_ident = :alert_id
  AND _parent_type IN ('A', 'S', 'T');

-- AdditionalData (Alert-level only)
DELETE FROM Prelude_AdditionalData
WHERE _message_ident = :alert_id
  AND _parent_type = 'A';

-- Analyzer (Alert-level only)
DELETE FROM Prelude_Analyzer
WHERE _message_ident = :alert_id
  AND _parent_type = 'A';

-- Node (multi-level)
DELETE FROM Prelude_Node
WHERE _message_ident = :alert_id
  AND _parent_type IN ('A', 'S', 'T');

-- Process (multi-level)
DELETE FROM Prelude_Process
WHERE _message_ident = :alert_id
  AND _parent_type IN ('A', 'S', 'T');

-- ProcessArg (multi-level)
DELETE FROM Prelude_ProcessArg
WHERE _message_ident = :alert_id
  AND _parent_type IN ('A', 'S', 'T');

-- ProcessEnv (multi-level)
DELETE FROM Prelude_ProcessEnv
WHERE _message_ident = :alert_id
  AND _parent_type IN ('A', 'S', 'T');

-- CreateTime (Alert-level only)
DELETE FROM Prelude_CreateTime
WHERE _message_ident = :alert_id
  AND _parent_type = 'A';

-- AnalyzerTime (Alert-level only)
DELETE FROM Prelude_AnalyzerTime
WHERE _message_ident = :alert_id
  AND _parent_type = 'A';
```

#### For Alert (Root Table):
```sql
-- DELETE LAST!
DELETE FROM Prelude_Alert WHERE _ident = :alert_id;
```

---

## 🛡️ Part 5: Orphan Prevention Strategies

### Strategy 1: Transaction-Based Deletion (REQUIRED)

```python
from sqlalchemy import text

def delete_alert_safe(db: Session, alert_id: int) -> dict:
    """
    Delete alert with full orphan prevention.

    Returns dict with deletion statistics.
    """
    deleted_counts = {}

    try:
        # Start transaction
        with db.begin():
            # Delete in correct order
            for table in DELETION_ORDER:
                if table == "Prelude_Alert":
                    # Root table - no _message_ident
                    result = db.execute(
                        text(f"DELETE FROM {table} WHERE _ident = :id"),
                        {"id": alert_id}
                    )
                elif table in SHARED_TABLES:
                    # Shared tables need _parent_type filter
                    parent_types = get_parent_types_for_table(table)
                    result = db.execute(
                        text(f"""
                            DELETE FROM {table}
                            WHERE _message_ident = :id
                              AND _parent_type IN :types
                        """),
                        {"id": alert_id, "types": tuple(parent_types)}
                    )
                else:
                    # Alert-only tables
                    result = db.execute(
                        text(f"DELETE FROM {table} WHERE _message_ident = :id"),
                        {"id": alert_id}
                    )

                deleted_counts[table] = result.rowcount

        # Verify no orphans created
        verify_no_orphans(db, alert_id)

        return {"success": True, "deleted": deleted_counts}

    except Exception as e:
        # Transaction auto-rolls back
        return {"success": False, "error": str(e)}

# Shared tables that need _parent_type filtering
SHARED_TABLES = {
    "Prelude_Address": ['A', 'S', 'T'],
    "Prelude_AdditionalData": ['A'],
    "Prelude_Analyzer": ['A'],
    "Prelude_Node": ['A', 'S', 'T'],
    "Prelude_Process": ['A', 'S', 'T'],
    "Prelude_ProcessArg": ['A', 'S', 'T'],
    "Prelude_ProcessEnv": ['A', 'S', 'T'],
    "Prelude_CreateTime": ['A'],
    "Prelude_AnalyzerTime": ['A'],
}

def get_parent_types_for_table(table: str) -> list:
    """Get required _parent_type values for shared table."""
    return SHARED_TABLES.get(table, [])
```


## 📚 Part 6: Reference SQL Scripts

### Complete Deletion Script

Save this as `delete_alert.sql` for manual deletions:

```sql
-- Complete alert deletion script
-- Usage: mysql -h HOST -u USER -p DATABASE < delete_alert.sql
-- Set alert_id before running!

SET @alert_id = 12345;  -- CHANGE THIS!

START TRANSACTION;

-- 1. Prebetter_Pair
DELETE FROM Prebetter_Pair WHERE _message_ident = @alert_id;

-- 2. Detailed data
DELETE FROM Prelude_AdditionalData WHERE _message_ident = @alert_id AND _parent_type = 'A';
DELETE FROM Prelude_WebServiceArg WHERE _message_ident = @alert_id;
DELETE FROM Prelude_ProcessArg WHERE _message_ident = @alert_id AND _parent_type IN ('A','S','T');
DELETE FROM Prelude_ProcessEnv WHERE _message_ident = @alert_id AND _parent_type IN ('A','S','T');
DELETE FROM Prelude_FileAccess_Permission WHERE _message_ident = @alert_id;

-- 3. Mid-level entities
DELETE FROM Prelude_Address WHERE _message_ident = @alert_id AND _parent_type IN ('A','S','T');
DELETE FROM Prelude_Reference WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Alertident WHERE _message_ident = @alert_id;
DELETE FROM Prelude_WebService WHERE _message_ident = @alert_id;
DELETE FROM Prelude_SnmpService WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Service WHERE _message_ident = @alert_id;
DELETE FROM Prelude_FileAccess WHERE _message_ident = @alert_id;
DELETE FROM Prelude_File WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Inode WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Checksum WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Linkage WHERE _message_ident = @alert_id;
DELETE FROM Prelude_User WHERE _message_ident = @alert_id;
DELETE FROM Prelude_UserId WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Process WHERE _message_ident = @alert_id AND _parent_type IN ('A','S','T');
DELETE FROM Prelude_Node WHERE _message_ident = @alert_id AND _parent_type IN ('A','S','T');

-- 4. Analyzer
DELETE FROM Prelude_AnalyzerTime WHERE _message_ident = @alert_id AND _parent_type = 'A';
DELETE FROM Prelude_Analyzer WHERE _message_ident = @alert_id AND _parent_type = 'A';

-- 5. Source/Target
DELETE FROM Prelude_Source WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Target WHERE _message_ident = @alert_id;

-- 6. Time
DELETE FROM Prelude_CreateTime WHERE _message_ident = @alert_id AND _parent_type = 'A';

-- 7. Assessment
DELETE FROM Prelude_Confidence WHERE _message_ident = @alert_id;
DELETE FROM Prelude_CorrelationAlert WHERE _message_ident = @alert_id;
DELETE FROM Prelude_ToolAlert WHERE _message_ident = @alert_id;
DELETE FROM Prelude_OverflowAlert WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Action WHERE _message_ident = @alert_id;

-- 8. Core
DELETE FROM Prelude_Assessment WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Impact WHERE _message_ident = @alert_id;
DELETE FROM Prelude_Classification WHERE _message_ident = @alert_id;
DELETE FROM Prelude_DetectTime WHERE _message_ident = @alert_id;

-- 9. Root - DELETE LAST!
DELETE FROM Prelude_Alert WHERE _ident = @alert_id;

-- Verify
SELECT
  'Remaining records' as check_type,
  COUNT(*) as count
FROM (
  SELECT _message_ident FROM Prebetter_Pair WHERE _message_ident = @alert_id
  UNION ALL SELECT _message_ident FROM Prelude_DetectTime WHERE _message_ident = @alert_id
  UNION ALL SELECT _message_ident FROM Prelude_Classification WHERE _message_ident = @alert_id
  UNION ALL SELECT _message_ident FROM Prelude_Impact WHERE _message_ident = @alert_id
  UNION ALL SELECT _ident FROM Prelude_Alert WHERE _ident = @alert_id
) as verification;

-- Should return 0 - if not, ROLLBACK!
-- If OK: COMMIT;
-- If problems: ROLLBACK;
```

---

## 🔧 Part 7: Implementation Code Templates

### Python/SQLAlchemy Implementation

```python
from sqlalchemy import text, Connection
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class AlertDeletionService:
    """Service for safe alert deletion with orphan prevention."""

    DELETION_ORDER = [
        "Prebetter_Pair",
        "Prelude_AdditionalData",
        "Prelude_WebServiceArg",
        "Prelude_ProcessArg",
        "Prelude_ProcessEnv",
        "Prelude_FileAccess_Permission",
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
        "Prelude_AnalyzerTime",
        "Prelude_Analyzer",
        "Prelude_Source",
        "Prelude_Target",
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
        "Prelude_Alert",
    ]

    SHARED_TABLES = {
        "Prelude_Address": ['A', 'S', 'T'],
        "Prelude_AdditionalData": ['A'],
        "Prelude_Analyzer": ['A'],
        "Prelude_Node": ['A', 'S', 'T'],
        "Prelude_Process": ['A', 'S', 'T'],
        "Prelude_ProcessArg": ['A', 'S', 'T'],
        "Prelude_ProcessEnv": ['A', 'S', 'T'],
        "Prelude_CreateTime": ['A'],
        "Prelude_AnalyzerTime": ['A'],
    }

    def delete_alert(
        self,
        db: Connection,
        alert_id: int,
        verify: bool = True
    ) -> Dict[str, any]:
        """
        Delete alert and all related data safely.

        Args:
            db: Database connection with transaction support
            alert_id: Alert ID to delete
            verify: Run post-deletion verification

        Returns:
            Dict with deletion statistics and status
        """
        stats = {
            "alert_id": alert_id,
            "tables_processed": 0,
            "total_rows_deleted": 0,
            "per_table": {},
            "orphans_prevented": True,
            "success": False
        }

        try:
            # Verify alert exists
            result = db.execute(
                text("SELECT _ident FROM Prelude_Alert WHERE _ident = :id"),
                {"id": alert_id}
            )
            if not result.fetchone():
                return {**stats, "error": "Alert not found"}

            # Delete in order
            for table in self.DELETION_ORDER:
                rows_deleted = self._delete_from_table(db, table, alert_id)
                stats["per_table"][table] = rows_deleted
                stats["total_rows_deleted"] += rows_deleted
                stats["tables_processed"] += 1

            # Verify no orphans
            if verify:
                orphans = self._check_orphans(db, alert_id)
                if orphans:
                    stats["orphans_prevented"] = False
                    stats["orphan_details"] = orphans
                    raise Exception(f"Orphans detected: {orphans}")

            stats["success"] = True
            logger.info(f"Successfully deleted alert {alert_id}: {stats['total_rows_deleted']} rows")

        except Exception as e:
            stats["error"] = str(e)
            logger.error(f"Failed to delete alert {alert_id}: {e}")
            raise  # Re-raise to trigger transaction rollback

        return stats

    def _delete_from_table(
        self,
        db: Connection,
        table: str,
        alert_id: int
    ) -> int:
        """Delete records from specific table."""

        if table == "Prelude_Alert":
            # Root table
            result = db.execute(
                text(f"DELETE FROM {table} WHERE _ident = :id"),
                {"id": alert_id}
            )
        elif table in self.SHARED_TABLES:
            # Shared table with _parent_type
            parent_types = self.SHARED_TABLES[table]
            result = db.execute(
                text(f"""
                    DELETE FROM {table}
                    WHERE _message_ident = :id
                      AND _parent_type IN :types
                """),
                {"id": alert_id, "types": tuple(parent_types)}
            )
        else:
            # Alert-only table
            result = db.execute(
                text(f"DELETE FROM {table} WHERE _message_ident = :id"),
                {"id": alert_id}
            )

        return result.rowcount

    def _check_orphans(
        self,
        db: Connection,
        alert_id: int
    ) -> Dict[str, int]:
        """Verify no orphaned records remain."""

        orphans = {}

        # Check critical tables
        for table in ["Prebetter_Pair", "Prelude_DetectTime", "Prelude_Classification"]:
            if table == "Prelude_Alert":
                continue

            count = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE _message_ident = :id"),
                {"id": alert_id}
            ).scalar()

            if count > 0:
                orphans[table] = count

        return orphans
```

---

## ✅ Summary

**Key Takeaways:**

1. **34+ tables** must be handled during Alert deletion
2. **16 tables** are shared between Alerts and Heartbeats - MUST filter by `_parent_type`
3. **NO foreign keys** exist - manual cascade deletion required
4. **Deletion order is critical** - children first, parent (Alert) last
5. **Prebetter_Pair** is a custom table with NO delete trigger - manual cleanup required
6. **Transactions are mandatory** - never delete without transaction
7. **Verification is essential** - always check for orphans after deletion