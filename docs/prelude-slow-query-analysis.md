# Prelude Slow Query Analysis (2025-09-29)

## Summary

- Repeated slow queries (≈30 s runtime, >23 M rows examined) originate from the
  grouped alerts endpoint in `backend/app/api/v1/routes/alerts.py` using
  `build_grouped_alerts_query()`.
- Root causes:
  - `Prelude_Address` fan-out: each alert yields two address rows per source/target
    index (`_index=-1` and `_index=0`), plus up to 130 target records per alert.
  - Grouping is performed after joining all address rows, causing large
    intermediate result sets and heavy `COUNT(DISTINCT ...)` aggregation.
  - The count endpoint wraps the grouped query in a derived table subselect,
    forcing MariaDB to materialise the entire 24 M-row dataset before counting.
- Applying canonical joins (`Source._index = 0`, `Target._index = 0`, address
  `_index = -1`) reduced runtime of the list query from ~30 s to ~4 s and the
  count query to ~3.8 s in ad-hoc testing (same date range).
- Replaced the derived-table pagination count with `COUNT(DISTINCT source, target)`
  so the backend no longer materialises the full grouped dataset just to count rows.
- Additional wins came from dropping expensive `GROUP_CONCAT(DISTINCT ...)` from
  the primary grouped list query and moving all per-classification/analyzer
  strings into the detail query only. The list now returns just:
  `source_ipv4`, `target_ipv4`, `total_count`, `latest_time`. Sorting by
  `severity`/`classification`/`analyzer` still works via lightweight aggregates
  (e.g. `MAX(...)`) applied only when requested.

## Slow Query Samples

From `/var/log/mariadb/mysqld-log-slow-queries.log` (29 Sep 2025):

```
# Query_time: 30.63  Rows_examined: 23,919,887
SELECT source_addr.address AS source_ipv4, target_addr.address AS target_ipv4,
       COUNT(DISTINCT Prelude_Alert._ident) AS total_count,
       TIMESTAMPADD(SECOND, MAX(Prelude_DetectTime.gmtoff), MAX(Prelude_DetectTime.time)) AS latest_time,
       MAX(Prelude_Impact.severity) AS max_severity,
       GROUP_CONCAT(DISTINCT Prelude_Classification.text) AS latest_classification,
       GROUP_CONCAT(DISTINCT Prelude_Analyzer.name) AS analyzer_name
FROM Prelude_Alert
JOIN Prelude_DetectTime ON Prelude_Alert._ident = Prelude_DetectTime._message_ident
LEFT JOIN Prelude_Impact ...
LEFT JOIN Prelude_Address AS source_addr ON source_addr._parent_type = 'S'
LEFT JOIN Prelude_Address AS target_addr ON target_addr._parent_type = 'T'
WHERE source_addr.address IS NOT NULL
  AND target_addr.address IS NOT NULL
  AND Prelude_DetectTime.time BETWEEN '2025-09-21 22:00:00' AND '2025-09-29 21:59:59.999000'
GROUP BY source_addr.address, target_addr.address
ORDER BY MAX(Prelude_DetectTime.time) DESC
LIMIT 0, 100;
```

The count query simply wraps this SQL inside `SELECT COUNT(*) FROM (...)`.

## Experimental Optimisations

### Canonical joins, DetectTime anchor, and address filters

1. Restrict sources/targets to `_index = 0` (primary entry) and address rows to
   `_index = -1`.
2. Enforce the `_parent0_index` join to tie each address to its owning
   Source/Target row.

```sql
SELECT source_addr.address  AS source_ipv4,
       target_addr.address  AS target_ipv4,
       COUNT(*)             AS total_count,
       TIMESTAMPADD(SECOND, MAX(dt.gmtoff), MAX(dt.time)) AS latest_time
FROM Prelude_DetectTime AS dt
JOIN Prelude_Source AS src
  ON src._message_ident = a._ident
 AND src._index = 0
LEFT JOIN Prelude_Address AS source_addr
  ON source_addr._message_ident  = a._ident
 AND source_addr._parent_type   = 'S'
 AND source_addr._parent0_index = src._index
 AND source_addr._index         = -1
 AND source_addr.category       = 'ipv4-addr'
JOIN Prelude_Target AS tgt
  ON tgt._message_ident = a._ident
 AND tgt._index = 0
LEFT JOIN Prelude_Address AS target_addr
  ON target_addr._message_ident  = dt._message_ident
 AND target_addr._parent_type   = 'T'
 AND target_addr._parent0_index = tgt._index
 AND target_addr._index         = -1
 AND target_addr.category       = 'ipv4-addr'
WHERE source_addr.address IS NOT NULL
  AND target_addr.address IS NOT NULL
  AND dt.time BETWEEN '2025-09-21 22:00:00' AND '2025-09-29 21:59:59.999000'
GROUP BY source_addr.address, target_addr.address
ORDER BY latest_time DESC
LIMIT 100;
```

- Runtime (measured via `/usr/bin/time`) dropped from ~30 s to ~4–5 s for a
  two‑month range, and ~0.2 s for a 7‑day range.
- `EXPLAIN` shows `eq_ref` lookups for Source/Target/Address tables (rows=1) and
  only the `Prelude_DetectTime` range scan remains (≈170 k rows examined vs 24 M).
- `COUNT(DISTINCT ...)` can now be replaced with plain `COUNT(*)` because the
  joins ensure one row per alert.

### Count query rewrite

`SELECT COUNT(DISTINCT source_addr.address, target_addr.address)` produces the
same result as the derived-table count but avoids materialising the full subquery.
Combined with the canonical joins above, the count executes in ~3.8 s instead of
~30 s.

### Suggested SQLAlchemy updates

In `build_grouped_alerts_query()`:

- join `Prelude_Source` and `Prelude_Target` with `_index = 0`.
- join addresses with `_parent0_index = selected._index` and `_index = -1`.
- reduce aggregation to `count()` instead of `count(distinct())`.

Likewise, `build_grouped_alerts_detail_query()` should reuse the same joins to
prevent cross-product blow-up when fetching classifications/analyzers.

### Index recommendations

To support the new join filter on Prelude_Address, add a covering index:

```sql
ALTER TABLE Prelude_Address
  ADD INDEX idx_parent_index_msg (
    _parent_type,
    _index,
    _parent0_index,
    _message_ident,
    category,
    address(32)
  );
```

This will allow the optimiser to use `eq_ref` lookups without relying on the
current prefix-only address index (`prelude_address_index_address`).

Additionally, to reduce table lookups and speed the DetectTime range scan,
add a composite index that covers the columns we use:

```sql
CREATE INDEX idx_dt_time_ident_gmtoff
ON Prelude_DetectTime(time, _message_ident, gmtoff);
```

This lets the optimiser read `time`, `gmtoff`, and `_message_ident` directly from
the index during the range scan, removing many primary-key lookups. In testing,
this shaved ~10–20% off large range queries.

## Next Steps for Code Changes

1. Update `build_grouped_alerts_query()` and `build_grouped_alerts_detail_query()`
   to implement the canonical joins (done), and make classification/analyzer/impact
   joins conditional so the hot path stays lean (done).
2. Adjust `SortField.alert_id` / `total_count` sort logic to use `func.count()`
   matches the new aggregation.
3. Add Flyway/SQL migration for `idx_parent_index_msg` index if not already present.
4. Re-run profiling (slow query log + `EXPLAIN`) to confirm the new list + count
   stay under ~5 s for two months; with 7–14 days ranges expect sub‑second.

Automation help: run `uv run python -m app.scripts.prelude_index_maintenance
check|apply` to audit/apply the required indexes after deployment.

## Pair Key Accelerator

To avoid multi-table joins and multi-column DISTINCT in hot paths, we added a
helper table `Prebetter_Pair` maintained by triggers on `Prelude_Address` that
stores one canonical `(source_ip, target_ip)` per message along with a single
`pair_key` (BIGINT).

- Count: `COUNT(DISTINCT pair_key)` becomes a single-column distinct over a
  joined DetectTime range and runs ~1.1 s for 8 days (vs ~3.5 s).
- List: grouping on `pair_key` with `INET_NTOA(source_ip/target_ip)` runs ~1.1 s
  for 8 days (vs ~3.6–4.2 s).
- Details remain DetectTime‑anchored and join Classification/Analyzer as needed.
  Node join (analyzer_hosts) is disabled by default for performance because the
  frontend does not render it currently; the column is returned as NULL.

Install/maintain via script:

```bash
uv run python -m app.scripts.prelude_pair_accelerator install
uv run python -m app.scripts.prelude_pair_accelerator backfill-days --days 7
```

The backend requires `Prebetter_Pair` and will fail startup if it is missing. No
Address-based fallback is used anymore — this avoids unpredictable performance
and guarantees all grouped paths run on the fast pair-key plan.

### Prebetter_Pair Design & Behavior

- Schema (MariaDB):
  - `_message_ident BIGINT PRIMARY KEY` — references the alert/heartbeat message._ident
  - `source_ip INT UNSIGNED`, `target_ip INT UNSIGNED` — IPv4 encoded via `INET_ATON()`
  - `pair_key BIGINT UNSIGNED` — persistent generated column: `source_ip * 4294967296 + target_ip`
  - Indexes: `PRIMARY(_message_ident)`, `idx_pair_key(pair_key)`, `idx_source(source_ip)`, `idx_target(target_ip)`

- Triggers (on `Prelude_Address`):
  - AFTER INSERT/UPDATE, for canonical rows only: `category='ipv4-addr'`, `_index=-1`, `_parent0_index=0`.
  - If the new row is for the Source side (`_parent_type='S'`), resolve the Target canonical address for the same message; if Target, resolve Source. When both exist, `INSERT IGNORE` into `Prebetter_Pair`.
  - Behavior is idempotent and safe under concurrency.

- Why it helps:
  - Replaces multi-table address joins + `COUNT(DISTINCT source, target)` with a single-column grouping `pair_key`.
  - Eliminates row multiplication from address fan-out, and allows integer comparisons for filters/sorts (index-friendly).
  - Keeps the hot-path list/count queries lean; details can still join Classification/Analyzer as needed.

- Limitations & assumptions:
  - IPv4-only (current dataset). To support IPv6 later, add `VARBINARY(16)` columns and a different hash, or dual-key grouping.
  - Canonical Source/Target row is `_index=0` and canonical address row is `_index=-1` (empirically true on current dataset). If business logic requires per-index grouping, extend triggers and queries accordingly.

### Backend Integration Details

- Detection: builders reflect the presence of `Prebetter_Pair`; if found, list/count/details use the pair-key path, otherwise they fall back to Address joins.

- List (pairs):
  - `SELECT INET_NTOA(source_ip), INET_NTOA(target_ip), MAX(TIMESTAMPADD(SECOND, gmtoff, time)), COUNT(*) FROM DetectTime JOIN Prebetter_Pair … GROUP BY pair_key`.
  - Sort-by source/target uses `INET_NTOA(source_ip/target_ip)`; severity/classification/analyzer sorts use `MAX(...)` aggregates only when requested (conditional joins).

- Count (pairs):
  - `SELECT COUNT(DISTINCT pair_key) FROM DetectTime JOIN Prebetter_Pair …` — fast, no derived table materialization.

- Details (per pair):
  - Given page pairs, compute their `pair_key`s and aggregate: `GROUP BY pair_key, Classification.text`. Analyzer hosts (Node) are disabled by default for performance (frontend doesn’t render them currently).
  - Analyzer names under alerts often aren’t present (≈5% coverage). We relaxed joins to `Analyzer._parent_type='A'` (any index), grouping names via `GROUP_CONCAT(DISTINCT ...)` to improve coverage when present.

- Filtering improvements:
  - Source/target IP filters leverage integer columns when using `Prebetter_Pair`: `source_ip = INET_ATON(:ip)`. The fallback path continues to filter on `Address.address`.
  - Date filtering is anchored on `DetectTime.time`; timestamps are adjusted with `TIMESTAMPADD(SECOND, gmtoff, time)` where needed for presentation.

### Operations & Troubleshooting

- Install / Backfill / Uninstall:
  - `uv run python -m app.scripts.prelude_pair_accelerator install` → creates table + triggers.
  - `uv run python -m app.scripts.prelude_pair_accelerator backfill-days --days 7` or `backfill --start ... --end ...` → idempotent population for a window.
  - `uv run python -m app.scripts.prelude_pair_accelerator status` → presence + row count.
  - `uv run python -m app.scripts.prelude_pair_accelerator uninstall [--drop-table]` → remove triggers, optionally table.

- Verifying coverage:
  - For a target window, `COUNT(*)` of `DetectTime` rows should match `JOIN Prebetter_Pair` rows when canonical S/T address rows exist (as validated on the current dataset).
  - Slow-log: list/count queries should no longer show tuple `IN` or multi-column `DISTINCT`; look for `COUNT(DISTINCT pair_key)` and `GROUP BY pair_key` patterns.

- If performance regresses:
  - Ensure `idx_pair_key` exists (and not fragmented), and that `Prelude_DetectTime` has the composite index `idx_dt_time_ident_gmtoff(time, _message_ident, gmtoff)`.
  - Verify triggers exist and are firing (check `SHOW TRIGGERS LIKE 'Prelude_Address'`). If missing, run `install` and backfill.
  - Confirm the backend detected `Prebetter_Pair` (list/count queries in logs should reference pair_key; otherwise the fallback path is active).

### IPv6 & Future Extensions

- Extend schema with `source_ip6 VARBINARY(16)`, `target_ip6 VARBINARY(16)` and a 128-bit hash or dual-column grouping if IPv6 appears.
- If alerts legitimately need multiple S/T pairs per message, model per-index pairs by adding `_source_index`/`_target_index` in `Prebetter_Pair` and adjusting triggers/queries accordingly.

## 2025-09-30 Update: Live Results and Detail Rewrite

Current state in production (post‑switch):

- Grouped count (8 days): via `COUNT(DISTINCT pair_key)` → ~1.1–1.3 s.
- Grouped list (8 days): via `GROUP BY pair_key` → ~1.1–1.3 s.
- Grouped details: now uses the pair-key path and aggregates per
  `(pair_key, Classification.text)`; observed ~2.2–2.6 s for 8‑day ranges.
- Alerts list/count (non‑grouped endpoint): ~1.0–1.9 s for the tested window.

Slow-log observations (after clearing and re‑testing):

- No derived-subquery counts and no cartesian joins remain.
- Dominant entries are grouped details using `GROUP_CONCAT(DISTINCT ...)` over
  Analyzer/Node, which is expectedly heavier than the list/count paths.

Detail query shape (pair-key):

```sql
SELECT INET_NTOA(pp.source_ip) AS source_ipv4,
       INET_NTOA(pp.target_ip) AS target_ipv4,
       cls.text                AS classification,
       COUNT(*)                AS cnt,
       GROUP_CONCAT(DISTINCT az.name) AS analyzers,
       GROUP_CONCAT(DISTINCT n.name)  AS analyzer_hosts,
       TIMESTAMPADD(SECOND, MAX(dt.gmtoff), MAX(dt.time)) AS latest_time
FROM Prelude_DetectTime dt
JOIN Prebetter_Pair pp ON pp._message_ident = dt._message_ident
LEFT JOIN Prelude_Classification cls ON cls._message_ident = dt._message_ident
LEFT JOIN Prelude_Analyzer az ON az._message_ident = dt._message_ident
                               AND az._parent_type='A' AND az._index=-1
LEFT JOIN Prelude_Node n ON n._message_ident = dt._message_ident
                          AND n._parent_type='A' AND n._parent0_index=-1
WHERE dt.time BETWEEN :start AND :end
  AND pp.pair_key IN (:pair_keys_for_page)
GROUP BY pp.pair_key, cls.text
ORDER BY latest_time DESC
LIMIT 1000;
```

Why it’s faster than the tuple‑IN path:

- Avoids `Prelude_Address` joins and `(source_addr, target_addr) IN (...)` tuple
  matching.
- Groups on a single BIGINT key with `INET_NTOA()` only in the final projection.
  The optimizer can keep most operations index‑backed on `DetectTime` and
  `Prebetter_Pair`.

Recent DB changes tracked:

- New composite index on `Prelude_DetectTime(time, _message_ident, gmtoff)` to
  make the time range scan covering.
- `Prebetter_Pair` table + triggers on `Prelude_Address` (canonical rows) to
  populate `(source_ip, target_ip, pair_key)` without application writes.

Actionable next tweaks (optional):

- Cap detail aggregation to 25–50 pairs per request to keep detail responses
  closer to ~1–1.5 s for long ranges.
- Make the Node join optional (behind a query param) when analyzer hosts are not
  shown; this cuts two DISTINCT aggregates from the hot path.
- If you often filter by source/target IPs, the pair key path already compares
  integer IPs (`source_ip = INET_ATON(:ip)`) which is index‑friendly.

Net result:

- Grouped list/count are now consistently sub‑second to ~1.3 s in the tested
  ranges. Grouped details sit ~2.2–2.6 s; further reductions are feasible with
  the optional tweaks above if needed.

## Outstanding Questions

- Do `_index = 0` and `_index = -1` always represent the canonical address pair
  for alerts? (Empirically true on current dataset; verify against schema docs.)
- Should heartbeat data (`_parent_type = 'H'`) be included in grouped views? If
  yes, extend joins accordingly.
- Are there business cases requiring multiple source/target combinations per
  alert? If so, we may need per-Source/Target grouping instead of single
  canonical pair.
