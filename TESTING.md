# Testing Guide - Lease Accounting API

Comprehensive testing implementation following Python and PostgreSQL best practices.

## Overview

This project includes a complete test suite with:
- ✅ Unit tests for database models
- ✅ Integration tests for business logic
- ✅ API endpoint tests
- ✅ Calculator accuracy tests
- ✅ Database transaction management
- ✅ Test isolation and cleanup

## Quick Start

```bash
# Install test dependencies
pip install ".[test]"

# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test types
make test-unit          # Fast unit tests
make test-integration   # Integration tests
make test-api          # API endpoint tests
```

## Test Architecture

### PostgreSQL Best Practices Implemented

1. **Persistent Test Database**
   - Starts (or reuses) a PostgreSQL container configured in tests/.env.test
   - Uses Alembic migrations to set up schema
   - Transaction rollback for test isolation
   - Each test runs in its own transaction that rolls back

2. **Transaction Rollback Pattern**
   ```python
   # Each test runs in a transaction that rolls back
   connection = engine.connect()
   transaction = connection.begin()
   session = SessionLocal()

   # ... test code ...

   session.close()
   transaction.rollback()  # Automatic cleanup
   ```

3. **Schema Management**
   - Tests use `kontracts` schema like production
   - Automatic schema creation in test setup
   - Proper cleanup after test session

4. **Connection Pooling**
   - Proper pool management with `StaticPool` for SQLite
   - Regular pooling for PostgreSQL with `pool_pre_ping`

5. **Foreign Key and Cascade Testing**
   - Tests verify cascade delete behavior
   - Tests verify referential integrity

6. **Constraint Validation**
   - Tests verify unique constraints
   - Tests verify NOT NULL constraints
   - Tests verify check constraints

## Test Organization

```
tests/
├── conftest.py              # Fixtures and configuration
├── test_models.py           # Model unit tests
├── test_api_leases.py       # Lease endpoint tests
├── test_api_schedules.py    # Schedule endpoint tests
├── test_calculators.py      # Calculator integration tests
└── README.md                # Test documentation
```

## Test Coverage

### Models (test_models.py)
- ✅ Lease model creation and validation
- ✅ Finance vs Operating lease types
- ✅ Required field enforcement
- ✅ Default values
- ✅ Cascade deletes
- ✅ Relationships
- ✅ User model with unique constraints
- ✅ Journal entry models
- ✅ Payment and document models
- ✅ Schedule models

### API Endpoints (test_api_leases.py, test_api_schedules.py)
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Pagination and filtering
- ✅ Error handling (404, 422, 400)
- ✅ Input validation
- ✅ Edge cases (negative values, missing data)
- ✅ Concurrent operations
- ✅ Schedule generation and retrieval
- ✅ Schedule deletion

### Calculators (test_calculators.py)
- ✅ Present value calculations
- ✅ ROU asset calculations
- ✅ Schedule generation for ASC 842
- ✅ Schedule generation for IFRS 16
- ✅ Interest calculation accuracy
- ✅ Liability amortization
- ✅ Edge cases (zero costs, high rates, long terms)
- ✅ Payment frequency variations

## Python Best Practices

### 1. Fixtures for Test Data
```python
@pytest.fixture
def sample_lease_data():
    """Reusable test data"""
    return {
        "lease_name": "Office Space Lease",
        "periodic_payment": 5000.00,
        # ...
    }
```

### 2. Parametrized Tests
```python
@pytest.mark.parametrize("payment,term,expected", [
    (1000, 12, 12000),
    (5000, 36, 180000),
])
def test_total_payments(payment, term, expected):
    assert payment * term == expected
```

### 3. Test Markers
```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.slow         # Slow tests to skip
```

### 4. Proper Assertions
```python
# Specific assertions
assert lease.id is not None
assert lease.status == "active"
assert abs(value - expected) < Decimal("0.01")

# Exception testing
with pytest.raises(IntegrityError):
    db_session.commit()
```

### 5. Test Isolation
- Each test is independent
- No shared state between tests
- Automatic database cleanup

### 6. Descriptive Test Names
```python
def test_create_lease_with_negative_payment_fails()
def test_schedule_generation_for_finance_lease()
def test_cascade_delete_removes_related_entries()
```

## PostgreSQL-Specific Tests

### 1. Schema Tests
```python
def test_tables_in_correct_schema(db_session):
    """Verify tables are in kontracts schema"""
    # Test implementation
```

### 2. Constraint Tests
```python
def test_username_unique_constraint(db_session):
    """Test PostgreSQL unique constraint"""
    with pytest.raises(IntegrityError):
        # Create duplicate
```

### 3. Cascade Delete Tests
```python
def test_lease_delete_cascades(db_session):
    """Test ON DELETE CASCADE behavior"""
    # Verify related records are deleted
```

### 4. Transaction Tests
```python
def test_transaction_rollback(db_session):
    """Test that errors rollback transaction"""
    # Verify atomicity
```

## Running Tests

### Basic Commands

```bash
# All tests
pytest

# Specific file
pytest tests/test_models.py

# Specific test
pytest tests/test_models.py::TestLeaseModel::test_create_lease

# With coverage
pytest --cov=app --cov-report=html

# Stop on first failure
pytest -x

# Verbose output
pytest -v

# Show print statements
pytest -s
```

### Using Makefile

```bash
make test              # All tests
make test-unit         # Unit tests only
make test-integration  # Integration tests only
make test-api         # API tests only
make test-cov         # With coverage report
make test-fast        # Skip slow tests
```

### Database Setup

```bash
# 1. Configure tests/.env.test for the container
cat <<'EOF' > tests/.env.test
TEST_POSTGRES_IMAGE=postgres:15-alpine
TEST_POSTGRES_DB=kontracts_test
TEST_POSTGRES_USER=kontracts
TEST_POSTGRES_PASSWORD=kontracts
TESTCONTAINERS_RYUK_DISABLED=true
TESTCONTAINERS_REUSE_ENABLE=true
TEST_PRESERVE_DB=true
EOF

# 2. Run tests
make test

# Or directly with pytest
pytest
```

The test suite will automatically:
- Start an ephemeral PostgreSQL container
- Create the kontracts schema
- Run Alembic migrations
- Roll back transactions after each test

Notes:
- `TESTCONTAINERS_RYUK_DISABLED=true` disables the Ryuk sidecar so the container can be reused between test runs.
- `TESTCONTAINERS_REUSE_ENABLE=true` allows reusing the same container instead of recreating it.
- `TEST_PRESERVE_DB=true` preserves the schema after the test session; test data is still rolled back per test.

**Requirements**: Docker must be running

## Test Data

### Fixtures Available

- `db_session` - Database session with auto-rollback
- `client` - FastAPI test client
- `sample_lease_data` - Sample operating lease data
- `sample_lease` - Created operating lease
- `sample_finance_lease_data` - Sample finance lease data
- `sample_finance_lease` - Created finance lease
- `sample_user_data` - Sample user data
- `sample_user` - Created user
- `sample_journal_entry_data` - Sample journal entry
- `cleanup_database` - Manual cleanup fixture

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_lease_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install ".[test]"

      - name: Run tests
        env:
          TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_lease_db
        run: pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Performance Considerations

1. **SQLite for Speed**: Default SQLite in-memory for fast unit tests
2. **PostgreSQL for Realism**: Use for integration tests
3. **Parallel Execution**: Can use `pytest-xdist` for parallel tests
4. **Selective Testing**: Use markers to run subsets

## Troubleshooting

### Issue: Tests fail with import errors
**Solution**: Ensure PYTHONPATH includes project root
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Database connection errors
**Solution**: Check TEST_DATABASE_URL
```bash
echo $TEST_DATABASE_URL
```

### Issue: Schema doesn't exist
**Solution**: Create kontracts schema
```sql
CREATE SCHEMA IF NOT EXISTS kontracts;
```

### Issue: Tests leave data behind
**Solution**: Verify transaction rollback in conftest.py

## Coverage Goals

- **Overall**: >80%
- **Models**: >90%
- **API Endpoints**: >85%
- **Calculators**: >85%
- **Services**: >80%

View coverage report:
```bash
make test-cov
open htmlcov/index.html
```

## Adding New Tests

### Model Test Template

```python
@pytest.mark.unit
@pytest.mark.database
class TestMyModel:
    def test_create(self, db_session):
        model = MyModel(field="value")
        db_session.add(model)
        db_session.commit()
        assert model.id is not None
```

### API Test Template

```python
@pytest.mark.api
def test_my_endpoint(client):
    response = client.get("/api/v1/endpoint")
    assert response.status_code == 200
    assert "expected_field" in response.json()
```

### Integration Test Template

```python
@pytest.mark.integration
def test_my_workflow(db_session, sample_lease):
    calculator = MyCalculator(sample_lease)
    result = calculator.process(db_session)
    assert result.is_valid()
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing Guide](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html)
- [PostgreSQL Testing Best Practices](https://www.postgresql.org/docs/current/regress.html)
