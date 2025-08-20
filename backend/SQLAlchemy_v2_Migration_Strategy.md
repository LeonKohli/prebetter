# SQLAlchemy v2 Migration Strategy

## Executive Summary

Your backend is currently using SQLAlchemy 2.0.36 but with v1-style syntax patterns. This migration will modernize the codebase to use SQLAlchemy v2's recommended patterns, improving type safety, IDE support, and future compatibility.

### Current State Analysis
- **SQLAlchemy Version**: 2.0.36 (v2 installed, using v1 syntax)
- **Files Affected**: 15+ Python files
- **Query Patterns**: 60+ legacy queries
- **Model Definitions**: 2 declarative bases, 1 user model, multiple automap models
- **Risk Level**: Low-Medium (v2 maintains backward compatibility)
- **Estimated Timeline**: 2-3 days for complete migration

## Phase 1: Foundation Migration (4-6 hours)

### 1.1 Update Declarative Base Pattern

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/database/config.py`

```python
# BEFORE (Lines 2, 41-42)
from sqlalchemy.orm import sessionmaker, Session, declarative_base

PreludeBase = declarative_base(metadata=prelude_metadata)
PrebetterBase = declarative_base(metadata=prebetter_metadata)

# AFTER
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy import MetaData

class PreludeBase(DeclarativeBase):
    metadata = prelude_metadata

class PrebetterBase(DeclarativeBase):
    metadata = prebetter_metadata
```

### 1.2 Migrate User Model

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/models/users.py`

```python
# BEFORE
from sqlalchemy import Boolean, Column, String, DateTime
from sqlalchemy.sql import func
from app.database.config import PrebetterBase

class User(PrebetterBase):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

# AFTER
from sqlalchemy import Boolean, String, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped
from app.database.config import PrebetterBase
from typing import Optional
from datetime import datetime

class User(PrebetterBase):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
```

### Testing Checkpoint 1
```bash
# Run after Phase 1
pytest tests/test_user.py -v
pytest tests/test_auth.py -v
pytest tests/test_user_edge_cases.py -v
```

## Phase 2: Query Pattern Migration (6-8 hours)

### 2.1 UserService Query Updates

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/services/users.py`

```python
# Add new imports at top
from sqlalchemy import select, func, delete

# Pattern transformations:

# BEFORE (Line 21)
return self.db.query(User).filter(User.id == user_id).first()

# AFTER
return self.db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()

# BEFORE (Line 33)
return self.db.query(User).offset(skip).limit(limit).all()

# AFTER
return list(self.db.scalars(select(User).offset(skip).limit(limit)).all())

# BEFORE (Line 37)
return self.db.query(User).count()

# AFTER
return self.db.scalar(select(func.count(User.id)))
```

### 2.2 Query Builder Updates

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/database/query_builders.py`

```python
# Update imports
from sqlalchemy import select, func, and_, literal_column, tuple_, text, case, literal

# Pattern transformation for build_alert_base_query (Lines 48-108)
# BEFORE
query = (
    db.query(
        Alert._ident,
        DetectTime.time.label("detect_time"),
        # ... more columns
    )
    .join(DetectTime, Alert._ident == DetectTime._message_ident)
    # ... more joins
)

# AFTER
query = (
    select(
        Alert._ident,
        DetectTime.time.label("detect_time"),
        # ... more columns
    )
    .select_from(Alert)
    .join(DetectTime, Alert._ident == DetectTime._message_ident)
    # ... more joins
)
# Note: Execute with db.execute(query) instead of direct query execution
```

### 2.3 Route Handler Updates

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/api/v1/routes/alerts.py`

```python
# Add imports
from sqlalchemy import select, func

# Update count patterns
# BEFORE (Line 145)
total_count = count_query.scalar()

# AFTER
total_count = db.scalar(count_query)

# Update result fetching
# BEFORE (Line 153)
results = query.all()

# AFTER
results = db.execute(query).all()
```

### Testing Checkpoint 2
```bash
# Run after each service file update
pytest tests/test_alerts.py -v
pytest tests/test_statistics.py -v
pytest tests/test_reference.py -v
pytest tests/test_heartbeats.py -v
```

## Phase 3: Cleanup and Optimization (2-4 hours)

### 3.1 Import Consolidation

```python
# Update all files - consolidate imports
# BEFORE
from sqlalchemy.sql import func
from sqlalchemy.sql import distinct

# AFTER
from sqlalchemy import func, distinct
```

### 3.2 Mixed Pattern Files

**File**: `/home/leon/Documents/GitHub/prebetter/backend/app/database/cleanup.py`

```python
# This file has mixed patterns - update remaining v1 queries
# BEFORE (Lines 50-57)
inactive_count = (
    db.query(AnalyzerTime)
    .filter(AnalyzerTime.time < threshold)
    .count()
)

# AFTER
inactive_count = db.scalar(
    select(func.count(AnalyzerTime._ident))
    .where(AnalyzerTime.time < threshold)
)

# BEFORE (Lines 65-72)
deleted_count = (
    db.query(AnalyzerTime)
    .filter(AnalyzerTime.time < threshold)
    .delete(synchronize_session=False)
)

# AFTER
result = db.execute(
    delete(AnalyzerTime)
    .where(AnalyzerTime.time < threshold)
)
deleted_count = result.rowcount
```

## Automation Scripts

### Find/Replace Patterns (use with caution)

```bash
# Find all db.query patterns
grep -r "db\.query(" backend/app --include="*.py"

# Find all Column imports
grep -r "from sqlalchemy import.*Column" backend/app --include="*.py"

# Find all .filter( patterns
grep -r "\.filter(" backend/app --include="*.py"
```

### Regex Patterns for IDE Find/Replace

```regex
# Convert simple queries
Find: db\.query\((\w+)\)\.filter\((.+?)\)\.first\(\)
Replace: db.execute(select($1).where($2)).scalar_one_or_none()

# Convert count queries
Find: db\.query\((\w+)\)\.count\(\)
Replace: db.scalar(select(func.count($1.id)))

# Convert all() queries
Find: \.query\((\w+)\)(.*?)\.all\(\)
Replace: .scalars(select($1)$2).all()
```

## Testing Strategy

### Unit Tests
1. Run individual test files after each module update
2. Focus on database interaction tests
3. Verify authentication flows remain intact

### Integration Tests
```bash
# Full test suite after each phase
pytest --cov=app

# API endpoint testing
uvicorn app.main:app --reload
# Then test with curl or Postman
```

### Performance Testing
```python
# Add timing to critical queries
import time

start = time.time()
result = db.execute(select(User).where(User.id == user_id))
print(f"Query time: {time.time() - start}s")
```

## Rollback Procedures

### Git-based Rollback
```bash
# Before starting each phase
git checkout -b sqlalchemy-v2-migration-phase-X
git add -A && git commit -m "Pre-migration checkpoint"

# If issues arise
git checkout main
```

### Database Compatibility
- No database schema changes required
- Both v1 and v2 syntax work with existing data
- Can run both patterns simultaneously during transition

## Best Practices

### Feature Flags (Optional)
```python
# config.py
USE_V2_QUERIES = os.getenv("USE_V2_QUERIES", "false").lower() == "true"

# In service files
if USE_V2_QUERIES:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
else:
    return db.query(User).filter(User.id == user_id).first()
```

### Gradual Migration
1. Start with read-only queries (safer)
2. Then update write operations
3. Finally update complex aggregations

### Code Review Checklist
- [ ] All `Column()` replaced with `mapped_column()`
- [ ] All `db.query()` replaced with `select()`
- [ ] Type hints added to model attributes
- [ ] Imports consolidated and cleaned
- [ ] Tests passing for modified modules
- [ ] No performance degradation

## Timeline Recommendation

**Day 1**:
- Morning: Phase 1 (Foundation)
- Afternoon: Begin Phase 2 (UserService)

**Day 2**:
- Morning: Complete Phase 2 (Query Builders)
- Afternoon: Phase 2 (Route Handlers)

**Day 3**:
- Morning: Phase 3 (Cleanup)
- Afternoon: Final testing and documentation

## Benefits of Migration

1. **Type Safety**: Better IDE support and type checking
2. **Future Compatibility**: Aligned with SQLAlchemy's direction
3. **Performance**: More efficient query compilation
4. **Maintainability**: Cleaner, more readable code
5. **Consistency**: Single query pattern throughout codebase

## Risk Mitigation

- **Low Risk**: Basic CRUD operations (90% of queries)
- **Medium Risk**: Complex joins and aggregations (10%)
- **Mitigation**: Incremental updates with testing after each change
- **Fallback**: v1 syntax still works in SQLAlchemy 2.0

## Conclusion

This migration is highly recommended despite SQLAlchemy 2.0's backward compatibility. The v2 syntax provides better type safety, clearer intent, and positions the codebase for future SQLAlchemy updates. The incremental approach ensures system stability throughout the migration process.