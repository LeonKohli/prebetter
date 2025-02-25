# Prebetter Backend Development Guide

This document contains important information about the codebase structure, coding patterns, and useful commands.

## Project Structure

The backend is organized into the following components:

- **app/api/**: Contains all API route definitions
  - **api/v1/routes/**: Individual route files for different domain areas
- **app/core/**: Core configuration and utilities
- **app/database/**: Database configuration and query utilities
  - **database/config.py**: DB connection, common query patterns
  - **database/query_builders.py**: Reusable query construction functions
  - **database/models.py**: Utility functions for model transformations
- **app/models/**: SQLAlchemy database models
- **app/schemas/**: Pydantic schemas for API input/output
- **app/services/**: Business logic layer

## Common Commands

### Development

```bash
# Start dev server
uvicorn app.main:app --reload

# Run tests
pytest -v

# Run specific test file
pytest tests/test_alerts.py -v

# Run with coverage
pytest --cov=app
```

### Database

```bash
# Load database
gunzip < prelude.sql.gz | mysql -u root -p prelude

# Connect to DB
mysql -u <username> -p prelude
```

## Code Patterns

### Query Construction Pattern

When creating new endpoints that query the database, follow this pattern:

1. Use query builders from `database/query_builders.py` to construct base queries
2. Apply standard filters using `apply_standard_alert_filters` function
3. Apply sorting using the `apply_sorting` helper function
4. Use model conversion utilities from `database/models.py` to transform results

Example:

```python
# Get base query from query builder
query, models = build_alert_base_query(db)

# Apply standard filters
query = apply_standard_alert_filters(
    query=query,
    severity=severity,
    classification=classification,
    start_date=start_date,
    end_date=end_date,
    source_ip=source_ip,
    target_ip=target_ip,
    analyzer_model=analyzer_model,
    **models,
    Impact=Impact,
    Classification=Classification,
    DetectTime=DetectTime,
    Analyzer=Analyzer
)

# Apply sorting - always use string keys in sort_options
sort_options = {
    "detect_time": DetectTime.time,
    "severity": Impact.severity,
    "classification": Classification.text,
    # ... other options
}
query = apply_sorting(query, sort_by, sort_order, sort_options, default_column=Alert._ident)

# Process results
items = [alert_result_to_list_item(result) for result in results]
```

### Creating New Query Builders

When adding new query functionality:

1. Define a function in `database/query_builders.py`
2. Return both the query and any model aliases used
3. Document parameters and return values

Example:

```python
def build_new_query(db: Session, param1: str):
    """
    Build a query for some new functionality.
    
    Args:
        db: SQLAlchemy database session
        param1: Some parameter
        
    Returns:
        SQLAlchemy query object and a dict of model aliases
    """
    # Create model aliases
    some_alias = aliased(SomeModel)
    
    # Build query
    query = (
        db.query(
            # ... query fields
        )
        .join(...)
        .outerjoin(...)
    )
    
    return query, {"some_alias": some_alias}
```

### Adding Model Converters

When adding new model conversion functions to `database/models.py`:

1. Create strongly-typed functions with comprehensive docstrings
2. Handle edge cases (None values, missing attributes)
3. Follow naming pattern: `*_to_*` or `build_*`

Example:

```python
def some_result_to_schema(result: Row) -> SomeSchema:
    """
    Convert a query result to a schema object.
    
    Args:
        result: Query result row
        
    Returns:
        Populated schema object
    """
    return SomeSchema(
        id=result.id,
        name=result.name,
        # ... other fields
    )
```

## Common Utilities

### Join Conditions

The application uses common join conditions for various tables. These are centralized in `database/config.py`:

- `get_analyzer_join_conditions`: For Analyzer table joins
- `get_source_address_join_conditions`: For source Address table joins
- `get_target_address_join_conditions`: For target Address table joins
- `get_node_join_conditions`: For Node table joins

### Query Helpers

The application provides helper functions for common query operations:

- `apply_standard_alert_filters`: Apply standard filters to a query
- `apply_sorting`: Apply sorting to a query based on sort field and order

### Processing Large Result Sets

For operations that process a large number of records, always consider:

1. Using `limit()` to restrict the total number of records
2. Use `.distinct()` when appropriate to eliminate duplicates
3. For raw data export, use generators like in `generate_csv()` function
4. Consider adding early exit conditions in processing functions

## Troubleshooting Common Issues

### Query Performance

If queries are slow:

1. Check if the correct indexes are being used in MySQL (use `EXPLAIN`)
2. Consider if the query can be optimized (fewer joins, more specific conditions)
3. Look at fetching only the specific columns needed
4. Add appropriate limits to queries:
   ```python
   # Limit results to a reasonable number
   query = query.limit(1000)
   ```
5. Use `.distinct()` to eliminate duplicate rows
6. For grouped data, ensure that group_by clauses come before limit/offset clauses
7. For exports and large datasets, use `yield_per()` to process in batches:
   ```python
   # Process in batches instead of loading all at once
   results = query.yield_per(1000)
   ```

### SQLAlchemy Join Conditions

For complex join conditions, remember the pattern:

```python
.outerjoin(
    Entity,
    and_(
        Entity._message_ident == Parent._message_ident,
        Entity._parent_type == "A",
        # Additional conditions...
    ),
)
```

### Enum Handling

When working with Enum values:

1. Always use string keys in dictionaries, not Enum values:
```python
# Correct
sort_options = {
    "detect_time": DetectTime.time,
    "severity": Impact.severity,
}

# Incorrect - will lead to errors
sort_options = {
    SortField.DETECT_TIME: DetectTime.time,
    SortField.SEVERITY: Impact.severity,
}
```

2. Convert Enum values to strings when using as keys:
```python
# Extract string value from enum
sort_key = sort_by
if hasattr(sort_by, "value"):
    sort_key = sort_by.value
```