# SQLAlchemy v2 Migration Status

## Current Branch: `sqlalchemy-v2-migration`

## Progress Summary

### ✅ Completed
1. **Phase 1: Foundation Migration**
   - ✅ Updated DeclarativeBase pattern in `database/config.py`
   - ✅ Migrated User model from `Column()` to `mapped_column()` with type hints
   - ✅ All user and auth tests passing (19/19)

2. **Phase 2.1: UserService Migration**
   - ✅ Updated all `db.query()` to `select()` statements
   - ✅ Replaced `.filter()` with `.where()`
   - ✅ Updated `.first()` to `.scalar_one_or_none()`
   - ✅ Updated `.count()` to use `func.count()`
   - ✅ All tests passing (13/13)

### ⚠️ Partially Completed
3. **Phase 2.2: Query Builders**
   - ✅ `build_alert_base_query` - Migrated to `select()`
   - ✅ `build_alert_count_query` - Migrated to `select()`
   - ✅ `build_grouped_alerts_query` - Migrated to `select()`
   - ⚠️ `build_alerts_statistics_query` - Partially migrated, `with_entities` patterns need refactoring
   - ❌ `build_heartbeats_*` functions - Still using old patterns
   - ❌ Complex queries with `with_entities` need complete refactoring

4. **Phase 2.3: Route Handlers**
   - ✅ `alerts.py::list_alerts` - Working with new patterns
   - ❌ `alerts.py::get_alert_detail` - Needs migration
   - ❌ Other routes - Not started

### ❌ Not Started
5. **Phase 3: Cleanup**
   - Import consolidation
   - Remove deprecated patterns
   - Final testing

## Test Status

```bash
# Passing Tests
✅ tests/test_user.py - 9/9 passed
✅ tests/test_auth.py - 4/4 passed
✅ tests/test_user_edge_cases.py - 6/6 passed
✅ tests/test_alerts.py::test_list_alerts - Passing

# Failing Tests
❌ tests/test_alerts.py::test_alert_detail - 500 error (query pattern issue)
❌ Other alert tests - Not tested yet
```

## Key Issues Encountered

1. **`with_entities` Pattern**: SQLAlchemy v2's `select()` doesn't have `with_entities()`. Need to refactor to use separate `select()` statements for each projection.

2. **Query Execution**: Routes need to use `db.execute(query)` or `db.scalar()` instead of `query.all()` or `query.scalar()`.

3. **Count Queries**: Need to use subqueries or separate count statements instead of `query.with_entities(func.count())`.

## Next Steps

### Immediate (High Priority)
1. Complete migration of remaining query builders
2. Fix all route handlers to work with new patterns
3. Update remaining test fixtures if needed

### Short Term
1. Complete cleanup phase
2. Run full test suite
3. Test with backend server running

### Migration Strategy Recommendations

1. **For `with_entities` patterns**:
   ```python
   # Old
   query.with_entities(Model.field1, func.count())
   
   # New
   select(Model.field1, func.count()).select_from(Model)
   ```

2. **For query execution**:
   ```python
   # Old
   results = query.all()
   
   # New
   results = db.execute(query).all()
   ```

3. **For scalar results**:
   ```python
   # Old
   count = query.scalar()
   
   # New
   count = db.scalar(query)
   ```

## Files Modified

- `app/database/config.py` - DeclarativeBase pattern
- `app/models/users.py` - mapped_column with type hints
- `app/services/users.py` - Query patterns updated
- `app/database/init_db.py` - Query pattern updated
- `app/database/query_builders.py` - Partially migrated
- `app/api/v1/routes/alerts.py` - Partially migrated

## Commands for Testing

```bash
# Run specific test suites
cd backend
uv run pytest tests/test_user.py -v
uv run pytest tests/test_auth.py -v
uv run pytest tests/test_alerts.py::test_list_alerts -v

# Run all tests (will show failures)
uv run pytest -v

# Start backend to test manually
uv run fastapi dev
```

## Rollback Instructions

If needed to rollback:
```bash
git checkout main
git branch -D sqlalchemy-v2-migration
```

## Time Invested
- Phase 1: ~20 minutes
- Phase 2.1: ~15 minutes
- Phase 2.2: ~30 minutes (incomplete)
- Phase 2.3: ~20 minutes (incomplete)

## Estimated Time to Complete
- Complete query builders: 2-3 hours
- Complete route handlers: 2-3 hours
- Testing and cleanup: 1-2 hours
- **Total**: 5-8 hours

## Conclusion

The migration is progressing well but is more complex than initially estimated due to:
1. Extensive use of `with_entities` patterns throughout the codebase
2. Complex query builders that need careful refactoring
3. Multiple route handlers that depend on old query patterns

The foundation is solid (models and basic queries work), but completing the migration requires systematic refactoring of all query builders and route handlers.